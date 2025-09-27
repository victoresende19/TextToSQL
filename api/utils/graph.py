"""Agente de Text-to-SQL com ChromaDB, OpenAI e SQLAlchemy usando LangGraph."""

import os
import json
from functools import partial
from typing import Dict

# Libs de IA e Banco de Dados
from openai import OpenAI
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Supondo que seus arquivos de modelo e DB estejam estruturados assim
from model.query import SQLQuery
from model.validation import ValidationDecision
from model.state import GraphState
from db.engine import create_db_engine
from db.setup import get_dynamic_db_schemas, setup_chroma_vectorstore
from utils.colors import Colors, print_node_info

# --- 1. CONFIGURAÇÃO PRINCIPAL ---
load_dotenv()
DB_DIALECT = "sqlite"
TABLES_TO_USE = ["clientes", "produtos", "vendas"]
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-small"
TABLE_DESCRIPTIONS = {
    "clientes": "Esta tabela armazena informações sobre os clientes. Contém nome, cidade e email de cada cliente.",
    "produtos": "Esta tabela contém a lista de todos os produtos disponíveis para venda. Inclui o nome do produto e seu preço unitário.",
    "vendas": "Esta é a tabela de transações, registrando todas as vendas realizadas, conectando clientes a produtos."
}
client = OpenAI(api_key=OPENAI_API_KEY)

# --- 4. NÓS DO GRAFO ---

def route_tables_node(state: GraphState, chroma_collection) -> Dict:
    """Nó 1: Reseta o estado e seleciona as tabelas."""
    print_node_info("Roteador de Tabelas (ChromaDB) 🔎", {})
    question = state["question"]
    results = chroma_collection.query(query_texts=[question], n_results=3)
    retrieved_schemas = set(meta['schema'] for meta in results['metadatas'][0])
    selected_tables = [meta['table_name'] for meta in results['metadatas'][0]]

    if "vendas" in selected_tables:
        for table in ["clientes", "produtos"]:
            retrieved_schemas.add(chroma_collection.get(ids=[f"{table}_doc"])['metadatas'][0]['schema'])
            if table not in selected_tables:
                selected_tables.append(table)
    
    return {"tables": "\n".join(list(retrieved_schemas)), "retries": 0, "error": None}

def generate_sql_node(state: GraphState, dialect: str) -> Dict:
    """Nó 2: Gera a query SQL."""

    prompt = f"""
    Gere uma única query SQL (dialeto SQLite) para responder à pergunta: 
    '{state['question']}' 
    
    Usando os schemas:
    {state['tables']}\n{ 'Erro anterior, corrija: ' + state['error'] if state.get('error') else '' }

    Certifique-se de que a query seja sintaticamente correta e otimizada.
    Responda apenas com a query SQL, sem explicações adicionais.
    """

    response = client.chat.completions.create(
        model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "function", "function": {"name": "sql_query", "parameters": SQLQuery.model_json_schema()}}],
        tool_choice={"type": "function", "function": {"name": "sql_query"}},
    )
    sql_query = SQLQuery(**json.loads(response.choices[0].message.tool_calls[0].function.arguments)).query
    print_node_info(f"Gerador de SQL (Dialeto: {dialect}) ✍️", {"SQL Gerado": f"\n```sql\n{sql_query}\n```"})
    return {"sql_query": sql_query, "error": None}

def execute_sql_node(state: GraphState, engine) -> dict:
    """Nó 3: Executa a query SQL."""
    # ### ALTERAÇÃO ### Garante que não execute se o limite já foi atingido
    if state.get("retries", 0) >= 3:
        return {"error": "Limite de tentativas atingido."}
    try:
        with engine.connect() as conn:
            result = conn.execute(text(state["sql_query"])).mappings().all()
        result_as_dict = [dict(row) for row in result]
        print_node_info("Executor de SQL (SQLAlchemy) 🚀", {"Resultado da Execução": result_as_dict or "Query executada com sucesso, mas sem retorno."})
        return {"query_result": str(result), "error": None}
    except SQLAlchemyError as e:
        print_node_info("Executor de SQL (SQLAlchemy) 🚀", {"Erro de SQL": str(e.orig)})
        return {"error": f"Erro de banco de dados: {e.orig}", "retries": state.get("retries", 0) + 1}

def validate_relevance_node(state: GraphState) -> Dict:
    """Nó 4: Valida se o resultado responde à pergunta."""

    prompt = f"""
    A pergunta foi: "{state['question']}". 
    A query executada foi "{state['sql_query']}" e o resultado foi "{state['query_result']}". 
    Este resultado responde à pergunta? Responda 'SIM' ou 'NÃO'.
    """

    response = client.chat.completions.create(
        model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "function", "function": {"name": "validation", "parameters": ValidationDecision.model_json_schema()}}],
        tool_choice={"type": "function", "function": {"name": "validation"}},
    )
    decision = ValidationDecision(**json.loads(response.choices[0].message.tool_calls[0].function.arguments)).decision
    print_node_info("Validador de Relevância ✅", {"Decisão da Validação": decision.upper()})
    
    if decision.upper() == "NÃO":
        return {"error": "O resultado não é relevante para a pergunta.", "retries": state.get("retries", 0) + 1}
    return {"error": None}

def generate_final_answer_node(state: GraphState) -> Dict:
    """Nó 5: Gera a resposta final em linguagem natural."""
    prompt = f"Com base na pergunta '{state['question']}' e nos dados '{state['query_result']}', formule uma resposta clara em linguagem natural."
    response = client.chat.completions.create(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
    final_answer = response.choices[0].message.content
    print_node_info("Gerador de Resposta Final 🗣️", {"Resposta Final": final_answer})
    return {"final_answer": final_answer}

# --- 5. LÓGICA CONDICIONAL DO GRAFO ---
def decide_next_node(state: GraphState) -> str:
    """Decide qual o próximo passo e retorna um RÓTULO para o gráfico."""
    print_node_info("Nó de Decisão 🚦", {"Estado Atual": "Analisando..."})
    
    if state.get("error"):
        retries = state.get("retries", 0)
        if retries >= 3:
            print(f"{Colors.RED}LIMITE DE {retries} TENTATIVAS ATINGIDO. FINALIZANDO.{Colors.ENDC}")
            # Rótulo para a aresta que vai para o FIM
            return "Limite de Tentativas Atingido" 
        else:
            print(f"{Colors.YELLOW}Erro detectado. Tentativa {retries}/3. Voltando para gerar novo SQL.{Colors.ENDC}")
            # Rótulo para a aresta que volta para a geração de SQL
            return "Erro (SQL ou Validação)"
    
    print(f"{Colors.GREEN}Validação bem-sucedida. Gerando resposta final.{Colors.ENDC}")
    # Rótulo para a aresta que segue para a resposta final
    return "Sucesso na Validação"

# --- 6. EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    print(f"{Colors.BOLD}Iniciando agente para o dialeto: {DB_DIALECT}{Colors.ENDC}")

    db_engine = create_db_engine(DB_DIALECT)
    dynamic_schemas = get_dynamic_db_schemas(db_engine, TABLES_TO_USE)
    
    docs = [TABLE_DESCRIPTIONS.get(name, f"Descrição da tabela {name}") for name in dynamic_schemas.keys()]
    metas = [{"table_name": name, "schema": schema} for name, schema in dynamic_schemas.items()]
    ids = [f"{name}_doc" for name in dynamic_schemas.keys()]
    chroma_collection = setup_chroma_vectorstore(
        documents=docs, metadatas=metas, ids=ids,
        openai_api_key=OPENAI_API_KEY, embedding_model=EMBEDDING_MODEL
    )

    workflow = StateGraph(GraphState)

    # Adiciona os nós (nenhuma mudança aqui)
    workflow.add_node("route_tables", partial(route_tables_node, chroma_collection=chroma_collection))
    workflow.add_node("generate_sql", partial(generate_sql_node, dialect=DB_DIALECT))
    workflow.add_node("execute_sql", partial(execute_sql_node, engine=db_engine))
    workflow.add_node("validate_relevance", validate_relevance_node)
    workflow.add_node("generate_final_answer", generate_final_answer_node)

    # Define a estrutura do grafo
    workflow.set_entry_point("route_tables")
    workflow.add_edge("route_tables", "generate_sql")
    workflow.add_edge("generate_sql", "execute_sql")
    workflow.add_edge("execute_sql", "validate_relevance")
    workflow.add_edge("generate_final_answer", END)
    
    # ### ALTERAÇÃO PRINCIPAL AQUI ###
    # Atualiza o mapeamento de rótulos para nós
    workflow.add_conditional_edges(
        "validate_relevance",
        decide_next_node,
        {
            # Rótulo da aresta:          Próximo nó
            "Erro (SQL ou Validação)":  "generate_sql",
            "Sucesso na Validação":     "generate_final_answer",
            "Limite de Tentativas Atingido": END
        }
    )
    
    app = workflow.compile()
    
    image_bytes = app.get_graph(xray=True).draw_mermaid_png()
    with open('grafo_final.png', "wb") as f:
        f.write(image_bytes)
    print(f"\n{Colors.GREEN}Imagem do grafo salva como 'grafo_final.png'{Colors.ENDC}")

    question = "Qual o nome e email do cliente que mais gastou em janeiro de 2024? Mostre também o valor total gasto."
    initial_state = {"question": question}

    print(f"\n{Colors.BOLD}--- INICIANDO EXECUÇÃO DO AGENTE ---{Colors.ENDC}")
    print(f"{Colors.YELLOW}Pergunta:{Colors.ENDC} {Colors.GREEN}{question}{Colors.ENDC}")
 
    final_state = app.invoke(
        initial_state,
        {"recursion_limit": 15}
    )
    
    print(f"\n{Colors.BOLD}--- RESULTADO FINAL ---{Colors.ENDC}")
    if final_state.get('error'):
        print(f"{Colors.RED}O agente falhou após {final_state.get('retries')} tentativas.{Colors.ENDC}")
    else:
        print(f"Pergunta: {Colors.YELLOW}{question}{Colors.ENDC}")
        print(f"Respota: {Colors.GREEN}{final_state.get('final_answer')}{Colors.ENDC}")

    db_engine.dispose()