import os
import json
from functools import partial
from typing import Dict, Any, List, TypedDict

# --- Libs da API ---
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# --- Libs do Agente (seu código original) ---
from openai import OpenAI
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import chromadb
from chromadb.utils import embedding_functions

# --- Modelos Pydantic para a API ---

class DBCredentials(BaseModel):
    dialect: str = Field(..., description="Dialeto do SQLAlchemy", examples=["sqlite", "postgresql+psycopg2"])
    connection_string: str = Field(..., description="String de conexão completa do SQLAlchemy", examples=["sqlite:///database.db", "postgresql+psycopg2://user:pass@host/dbname"])

class TableInfo(BaseModel):
    table_name: str
    description: str

class AgentConfiguration(BaseModel):
    db_credentials: DBCredentials
    tables: List[TableInfo]

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str

# --- Estado Global da Aplicação ---
# Armazenará o agente compilado e o histórico da conversa
app_state: Dict[str, Any] = {}
SUMMARY_THRESHOLD = 10 # Define o limite para resumir a conversa

# --- Lógica do Agente Refatorada ---

# Carrega configurações globais
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-small"
client = OpenAI(api_key=OPENAI_API_KEY)

# (Seus modelos Pydantic do agente permanecem os mesmos)
class SQLQuery(BaseModel):
    query: str = Field(description="A query SQL completa para ser executada.")

class ValidationDecision(BaseModel):
    decision: str = Field(description="Responda 'SIM' se a resposta for relevante, 'NÃO' caso contrário.")

# ### ALTERAÇÃO: Definindo um estado mais explícito para o grafo ###
class GraphState(TypedDict):
    question: str
    tables: str
    sql_query: str
    query_result: str
    final_answer: str
    error: str
    retries: int
    history: List[Dict[str, str]] # Adicionado para carregar o histórico da conversa

# (Nós do Grafo)
def route_tables_node(state: GraphState, chroma_collection) -> Dict:
    # Este nó não chama a LLM, então permanece inalterado.
    question = state["question"]
    results = chroma_collection.query(query_texts=[question], n_results=3)
    retrieved_schemas = set(meta['schema'] for meta in results['metadatas'][0])
    selected_tables = [meta['table_name'] for meta in results['metadatas'][0]]
    if "vendas" in selected_tables:
        for table in ["clientes", "produtos"]:
            if table in [t.table_name for t in app_state.get("tables_info", [])]:
                retrieved_schemas.add(chroma_collection.get(ids=[f"{table}_doc"])['metadatas'][0]['schema'])
                if table not in selected_tables: selected_tables.append(table)
    return {"tables": "\n".join(list(retrieved_schemas)), "retries": 0, "error": None}

# ### ALTERAÇÃO: Uso de system/user/assistant roles ###
def generate_sql_node(state: GraphState, dialect: str) -> Dict:
    system_prompt = f"Você é um especialista em SQL. Sua tarefa é gerar uma única e sintaticamente correta query SQL no dialeto {dialect} para responder à pergunta do usuário, utilizando os schemas de tabela fornecidos. Responda apenas com a query."
    
    user_prompt = f"Pergunta: '{state['question']}'\n\nSchemas:\n{state['tables']}\n\n{ 'Erro anterior, corrija: ' + state['error'] if state.get('error') else '' }"

    messages = [
        {"role": "system", "content": system_prompt},
        *state.get('history', []), # Adiciona o histórico da conversa
        {"role": "user", "content": user_prompt}
    ]

    response = client.chat.completions.create(
        model=CHAT_MODEL, 
        messages=messages, 
        tools=[{"type": "function", "function": {"name": "sql_query", "parameters": SQLQuery.model_json_schema()}}], 
        tool_choice={"type": "function", "function": {"name": "sql_query"}}
    )
    sql_query = SQLQuery(**json.loads(response.choices[0].message.tool_calls[0].function.arguments)).query
    return {"sql_query": sql_query, "error": None}

def execute_sql_node(state: GraphState, engine) -> dict:
    # Este nó não chama a LLM, então permanece inalterado.
    if state.get("retries", 0) >= 3: return {"error": "Limite de tentativas atingido."}
    try:
        with engine.connect() as conn:
            result = conn.execute(text(state["sql_query"])).mappings().all()
        return {"query_result": str(result), "error": None}
    except SQLAlchemyError as e:
        return {"error": f"Erro de banco de dados: {e.orig}", "retries": state.get("retries", 0) + 1}

# ### ALTERAÇÃO: Uso de system/user/assistant roles ###
def validate_relevance_node(state: GraphState) -> Dict:
    system_prompt = "Você é um assistente de validação. Analise a pergunta do usuário, a query SQL executada e o resultado obtido. Sua única tarefa é decidir se o resultado responde adequadamente à pergunta original. Responda estritamente com 'SIM' ou 'NÃO'."
    
    user_prompt = f"A pergunta original foi: '{state['question']}'.\nA query SQL executada foi: '{state['sql_query']}'.\nO resultado obtido foi: '{state['query_result']}'.\n\nEste resultado responde à pergunta?"

    messages = [
        {"role": "system", "content": system_prompt},
        # O histórico não é essencial aqui, mas pode ser mantido por consistência
        # *state.get('history', []), 
        {"role": "user", "content": user_prompt}
    ]

    response = client.chat.completions.create(
        model=CHAT_MODEL, 
        messages=messages, 
        tools=[{"type": "function", "function": {"name": "validation", "parameters": ValidationDecision.model_json_schema()}}], 
        tool_choice={"type": "function", "function": {"name": "validation"}}
    )
    decision = ValidationDecision(**json.loads(response.choices[0].message.tool_calls[0].function.arguments)).decision
    if decision.upper() == "NÃO": return {"error": "O resultado não é relevante.", "retries": state.get("retries", 0) + 1}
    return {"error": None}

# ### ALTERAÇÃO: Uso de system/user/assistant roles ###
def generate_final_answer_node(state: GraphState) -> Dict:
    system_prompt = "Você é um assistente prestativo. Sua tarefa é formular uma resposta clara e concisa em linguagem natural para o usuário, com base na pergunta original e nos dados retornados pela consulta ao banco de dados."
    
    user_prompt = f"Pergunta do usuário: '{state['question']}'.\nDados obtidos: '{state['query_result']}'.\n\nFormule a resposta final."

    messages = [
        {"role": "system", "content": system_prompt},
        *state.get('history', []), # Adiciona o histórico da conversa
        {"role": "user", "content": user_prompt}
    ]

    response = client.chat.completions.create(
        model=CHAT_MODEL, 
        messages=messages
    )
    return {"final_answer": response.choices[0].message.content}

def decide_next_node(state: GraphState) -> str:
    # Inalterado
    if state.get("error"):
        if state.get("retries", 0) >= 3: return "Limite de Tentativas Atingido"
        return "Erro (SQL ou Validação)"
    return "Sucesso na Validação"

# --- Aplicação FastAPI ---
app = FastAPI(
    title="Agente Text-to-SQL Dinâmico com Memória",
    description="Uma API para conversar com bancos de dados usando linguagem natural, com gerenciamento de contexto.",
    version="1.1.0"
)

app = FastAPI()

# 2. Defina as origens permitidas (seu frontend)
origins = [
    "http://localhost:5173", # URL padrão do Vite
    "http://localhost:3000", # URL padrão do create-react-app
]

# 3. Adicione o middleware ao seu app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"], # Permite todos os cabeçalhos
)

# ### NOVA FUNÇÃO: Resumir o histórico da conversa ###
def summarize_conversation(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Usa a LLM para criar um resumo conciso do histórico da conversa."""
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    prompt = f"""
    Resuma a seguinte conversa entre um usuário e um assistente de forma concisa. 
    O resumo deve capturar os principais pontos, perguntas e respostas para que o contexto seja mantido em futuras interações, mas de forma muito mais curta.

    Conversa a ser resumida:
    {history_str}
    """
    
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": "Você é um especialista em resumir conversas."}, {"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content
        # Retorna um novo histórico com o resumo e as últimas 4 mensagens para manter o contexto recente
        new_history = [
            {"role": "system", "content": f"Isto é um resumo da conversa até agora: {summary}"},
            *history[-4:]
        ]
        print("--- CONVERSA RESUMIDA ---")
        return new_history
    except Exception as e:
        print(f"Erro ao resumir a conversa: {e}. Mantendo o histórico antigo.")
        return history # Retorna o histórico original em caso de erro
    
@app.get("/tables", response_model=List[TableInfo], tags=["Configuração"])
def get_configured_tables():
    """
    Retorna a lista de tabelas que foram configuradas no agente.
    """
    if "tables_info" not in app_state or not app_state["tables_info"]:
        raise HTTPException(
            status_code=404, 
            detail="Nenhuma base de dados configurada. Use o endpoint /configure_agent primeiro."
        )
    # Retorna a lista de tabelas armazenada no estado da aplicação
    return app_state["tables_info"]

@app.post("/configure_agent", status_code=200)
def configure_agent(config: AgentConfiguration):
    """
    Configura o agente e inicializa/reseta o histórico da conversa.
    """
    try:
        db_engine = create_engine(config.db_credentials.connection_string)
        table_names = [t.table_name for t in config.tables]
        inspector = inspect(db_engine)
        schemas = {
            name: f"CREATE TABLE {name} (\n" + ",\n".join([f"  {col['name']} {str(col['type'])}" for col in inspector.get_columns(name)]) + "\n);"
            for name in table_names if inspector.get_columns(name)
        }

        chroma_client = chromadb.Client()
        embedding_func = embedding_functions.OpenAIEmbeddingFunction(api_key=OPENAI_API_KEY, model_name=EMBEDDING_MODEL)
        chroma_collection = chroma_client.get_or_create_collection(name="dynamic_db_agent_memory", embedding_function=embedding_func)
        
        ids = [f"{t.table_name}_doc" for t in config.tables]
        if chroma_collection.count() > 0 and chroma_collection.get(ids=ids)['ids']:
             chroma_collection.delete(ids=ids)
        
        chroma_collection.add(
            documents=[t.description for t in config.tables],
            metadatas=[{"table_name": t.table_name, "schema": schemas.get(t.table_name, "")} for t in config.tables],
            ids=ids
        )
        
        workflow = StateGraph(GraphState)
        workflow.add_node("route_tables", partial(route_tables_node, chroma_collection=chroma_collection))
        workflow.add_node("generate_sql", partial(generate_sql_node, dialect=config.db_credentials.dialect))
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
        
        app_state["agent"] = workflow.compile()
        app_state["db_engine"] = db_engine
        app_state["tables_info"] = config.tables
        # ### ALTERAÇÃO: Inicializa o histórico da conversa ###
        app_state["conversation_history"] = []
        
        return {"message": "Agente configurado com sucesso. Histórico da conversa iniciado."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao configurar o agente: {str(e)}")


@app.post("/query", response_model=QueryResponse)
def query_agent(request: QueryRequest):
    """
    Envia uma pergunta para o agente, gerenciando o histórico da conversa.
    """
    if "agent" not in app_state:
        raise HTTPException(status_code=400, detail="Agente não configurado. Por favor, chame o endpoint /configure_agent primeiro.")
    
    try:
        # ### ALTERAÇÃO: Gerenciamento do histórico ###
        history = app_state.get("conversation_history", [])
        
        # Verifica se o histórico precisa ser resumido
        if len(history) >= SUMMARY_THRESHOLD:
            history = summarize_conversation(history)
            app_state["conversation_history"] = history

        agent = app_state["agent"]
        initial_state = {
            "question": request.question,
            "history": history # Passa o histórico para o grafo
        }
        
        final_state = agent.invoke(initial_state, {"recursion_limit": 15})
        
        if final_state.get('error'):
            raise HTTPException(status_code=500, detail=f"O agente falhou após múltiplas tentativas. Último erro: {final_state['error']}")
        
        answer = final_state.get('final_answer', "Não foi possível gerar uma resposta.")
        
        # ### ALTERAÇÃO: Atualiza o histórico com a nova interação ###
        history.append({"role": "user", "content": request.question})
        history.append({"role": "assistant", "content": answer})
        app_state["conversation_history"] = history
        
        return QueryResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro durante a execução da query: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)