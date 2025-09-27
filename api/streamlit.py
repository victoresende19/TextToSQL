# app.py
"""
Aplicação Streamlit para o Agente Text-to-SQL com LangGraph.
"""

import os
import json
from functools import partial
from typing import Dict

# --- Libs Principais ---
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import chromadb
from chromadb.utils import embedding_functions
from pydantic import BaseModel, Field

# --- CONFIGURAÇÃO FIXA ---
load_dotenv()
DB_DIALECT = "sqlite"
# IMPORTANTE: Crie um arquivo chamado 'database.db' no mesmo diretório
# ou altere o caminho aqui.
DB_CONNECTION_STRING = "sqlite:///db/database.db" 
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


# --- MODELOS E ESTADO DO AGENTE ---

class SQLQuery(BaseModel):
    query: str = Field(description="A query SQL completa para ser executada.")

class ValidationDecision(BaseModel):
    decision: str = Field(description="Responda 'SIM' se a resposta for relevante, 'NÃO' caso contrário.")

class GraphState(Dict):
    question: str
    tables: str
    sql_query: str
    query_result: str
    final_answer: str
    error: str
    retries: int


# --- NÓS E LÓGICA DO GRAFO (LANGGRAPH) ---

def route_tables_node(state: GraphState, chroma_collection) -> Dict:
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
    prompt = f"Gere uma única query SQL (dialeto {dialect}) para responder à pergunta '{state['question']}' usando os schemas: \n{state['tables']}\n{ 'Erro anterior, corrija: ' + state['error'] if state.get('error') else '' }"
    response = client.chat.completions.create(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}], tools=[{"type": "function", "function": {"name": "sql_query", "parameters": SQLQuery.model_json_schema()}}], tool_choice={"type": "function", "function": {"name": "sql_query"}})
    sql_query = SQLQuery(**json.loads(response.choices[0].message.tool_calls[0].function.arguments)).query
    return {"sql_query": sql_query, "error": None}

def execute_sql_node(state: GraphState, engine) -> dict:
    if state.get("retries", 0) >= 3: return {"error": "Limite de tentativas atingido."}
    try:
        with engine.connect() as conn:
            result = conn.execute(text(state["sql_query"])).mappings().all()
        return {"query_result": str(result), "error": None}
    except SQLAlchemyError as e:
        return {"error": f"Erro de banco de dados: {e.orig}", "retries": state.get("retries", 0) + 1}

def validate_relevance_node(state: GraphState) -> Dict:
    prompt = f"A pergunta foi: '{state['question']}'. A query executada foi '{state['sql_query']}' e o resultado foi '{state['query_result']}'. Este resultado responde à pergunta? Responda 'SIM' ou 'NÃO'."
    response = client.chat.completions.create(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}], tools=[{"type": "function", "function": {"name": "validation", "parameters": ValidationDecision.model_json_schema()}}], tool_choice={"type": "function", "function": {"name": "validation"}})
    decision = ValidationDecision(**json.loads(response.choices[0].message.tool_calls[0].function.arguments)).decision
    if decision.upper() == "NÃO": return {"error": "O resultado não é relevante.", "retries": state.get("retries", 0) + 1}
    return {"error": None}

def generate_final_answer_node(state: GraphState) -> Dict:
    prompt = f"Com base na pergunta '{state['question']}' e nos dados '{state['query_result']}', formule uma resposta clara em linguagem natural."
    response = client.chat.completions.create(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
    return {"final_answer": response.choices[0].message.content}

def decide_next_node(state: GraphState) -> str:
    if state.get("error"):
        if state.get("retries", 0) >= 3: return "Limite de Tentativas Atingido"
        return "Erro (SQL ou Validação)"
    return "Sucesso na Validação"

# --- FUNÇÃO DE SETUP COM CACHE ---

@st.cache_resource
def get_compiled_agent():
    """
    Função para configurar e compilar o agente LangGraph.
    O decorator @st.cache_resource garante que isso rode apenas uma vez.
    """
    print("--- INICIANDO SETUP DO AGENTE (Executado apenas uma vez) ---")
    
    # 1. Conectar ao DB
    db_engine = create_engine(DB_CONNECTION_STRING)
    
    # 2. Obter schemas
    inspector = inspect(db_engine)
    schemas = {}
    for table_name in TABLES_TO_USE:
        columns = inspector.get_columns(table_name)
        if not columns: continue
        col_defs = [f"  {col['name']} {str(col['type'])}" for col in columns]
        schemas[table_name] = f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);"

    # 3. Configurar ChromaDB
    chroma_client = chromadb.Client()
    embedding_func = embedding_functions.OpenAIEmbeddingFunction(api_key=OPENAI_API_KEY, model_name=EMBEDDING_MODEL)
    chroma_collection = chroma_client.get_or_create_collection(name="static_db_agent", embedding_function=embedding_func)
    
    docs = [TABLE_DESCRIPTIONS.get(name, f"Tabela {name}") for name in TABLES_TO_USE]
    metas = [{"table_name": name, "schema": schemas.get(name, "")} for name in TABLES_TO_USE]
    ids = [f"{name}_doc" for name in TABLES_TO_USE]
    if chroma_collection.count() > 0: chroma_collection.delete(ids=chroma_collection.get()['ids'])
    chroma_collection.add(documents=docs, metadatas=metas, ids=ids)

    # 4. Construir o Grafo
    workflow = StateGraph(GraphState)
    workflow.add_node("route_tables", partial(route_tables_node, chroma_collection=chroma_collection))
    workflow.add_node("generate_sql", partial(generate_sql_node, dialect=DB_DIALECT))
    workflow.add_node("execute_sql", partial(execute_sql_node, engine=db_engine))
    workflow.add_node("validate_relevance", validate_relevance_node)
    workflow.add_node("generate_final_answer", generate_final_answer_node)

    workflow.set_entry_point("route_tables")
    workflow.add_edge("route_tables", "generate_sql")
    workflow.add_edge("generate_sql", "execute_sql")
    workflow.add_edge("execute_sql", "validate_relevance")
    workflow.add_conditional_edges("validate_relevance", decide_next_node, {
        "Erro (SQL ou Validação)": "generate_sql",
        "Sucesso na Validação": "generate_final_answer",
        "Limite de Tentativas Atingido": END
    })
    workflow.add_edge("generate_final_answer", END)
    
    print("--- SETUP DO AGENTE CONCLUÍDO ---")
    return workflow.compile()


# --- INTERFACE GRÁFICA (STREAMLIT) ---

st.set_page_config(page_title="Agente Text-to-SQL", layout="wide", page_icon="🤖")

st.title("🤖 Agente de Conversa com Banco de Dados")
st.write(
    "Faça uma pergunta em linguagem natural sobre os dados de vendas, clientes e produtos. "
    "O agente irá gerar uma consulta SQL, executá-la e fornecer a resposta."
)

# Carrega o agente (usando o cache)
try:
    agent = get_compiled_agent()
except Exception as e:
    st.error(f"Ocorreu um erro ao inicializar o agente: {e}")
    st.stop()


# Inicializa o histórico de chat na sessão
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe as mensagens do histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Campo de entrada para a pergunta do usuário
if prompt := st.chat_input("Qual o cliente que mais gastou?"):
    # Adiciona a pergunta do usuário ao histórico e exibe
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gera e exibe a resposta do agente
    with st.chat_message("assistant"):
        with st.spinner("Analisando sua pergunta e consultando o banco de dados... 🧠"):
            try:
                initial_state = {"question": prompt}
                final_state = agent.invoke(initial_state, {"recursion_limit": 15})
                
                if final_state.get('error'):
                    answer = f"Desculpe, não consegui responder à sua pergunta após 3 tentativas. (Erro: {final_state.get('error')} ou a pergunta não é relevante para os dados disponíveis.)"
                else:
                    answer = final_state.get('final_answer', "Não foi possível gerar uma resposta final.")
                
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as e:
                error_message = f"Ocorreu um erro inesperado: {e}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})