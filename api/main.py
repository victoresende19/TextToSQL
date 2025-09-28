import os
import json
from functools import partial
from typing import Dict, Any, List, TypedDict
import traceback # Importe para obter mais detalhes do erro

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

# --- Modelos Pydantic (sem alterações) ---
class DBCredentials(BaseModel):
    dialect: str = Field(..., examples=["sqlite", "postgresql+psycopg2"])
    connection_string: str = Field(..., examples=["sqlite:///database.db", "postgresql+psycopg2://user:pass@host/dbname"])

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
app_state: Dict[str, Any] = {}
SUMMARY_THRESHOLD = 10

# --- Lógica do Agente ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-small"
client = OpenAI(api_key=OPENAI_API_KEY)

class SQLQuery(BaseModel):
    query: str = Field(description="A query SQL completa para ser executada.")

class ValidationDecision(BaseModel):
    decision: str = Field(description="Responda 'SIM' se a resposta for relevante, 'NÃO' caso contrário.")

class GraphState(TypedDict):
    question: str
    tables: str
    sql_query: str
    query_result: str
    final_answer: str
    error: str
    retries: int
    history: List[Dict[str, str]]

# (Nós do Grafo com correções)
def route_tables_node(state: GraphState, chroma_collection) -> Dict:
    question = state["question"]
    results = chroma_collection.query(query_texts=[question], n_results=5) # Aumentado para 5 para mais contexto
    retrieved_schemas = set(meta['schema'] for meta in results['metadatas'][0])
    return {"tables": "\n".join(list(retrieved_schemas)), "retries": 0, "error": None}

def generate_sql_node(state: GraphState, dialect: str) -> Dict:
    print("--- GERANDO SQL ---")
    system_prompt = f"Você é um especialista em SQL. Sua tarefa é gerar uma única e sintaticamente correta query SQL no dialeto {dialect} para responder à pergunta do usuário, utilizando os schemas de tabela fornecidos. Responda apenas com a query."
    user_prompt = f"Pergunta: '{state['question']}'\n\nSchemas:\n{state['tables']}\n\n{ 'Erro anterior, corrija a query: ' + state['error'] if state.get('error') else '' }"
    messages = [{"role": "system", "content": system_prompt}, *state.get('history', []), {"role": "user", "content": user_prompt}]
    
    response = client.chat.completions.create(
        model=CHAT_MODEL, 
        messages=messages, 
        tools=[{"type": "function", "function": {"name": "sql_query", "parameters": SQLQuery.model_json_schema()}}], 
        tool_choice={"type": "function", "function": {"name": "sql_query"}}
    )
    sql_query = SQLQuery(**json.loads(response.choices[0].message.tool_calls[0].function.arguments)).query
    return {"sql_query": sql_query, "error": None}

def execute_sql_node(state: GraphState, engine) -> dict:
    print(f"--- EXECUTANDO SQL (Tentativa {state.get('retries', 0) + 1}) ---")
    print(f"Query: {state['sql_query']}")
    if state.get("retries", 0) >= 3: return {"error": "Limite de tentativas atingido."}
    try:
        with engine.connect() as conn:
            result = conn.execute(text(state["sql_query"])).mappings().all()
        return {"query_result": str(result), "error": None}
    except SQLAlchemyError as e:
        # CORREÇÃO: Retorna um erro mais detalhado
        error_message = f"Erro de banco de dados ao executar a query. Detalhes: {e.orig}"
        print(f"ERRO SQL: {error_message}")
        return {"error": error_message, "retries": state.get("retries", 0) + 1}

# CORREÇÃO: Nó de validação mais robusto
def validate_relevance_node(state: GraphState) -> Dict:
    print("--- VALIDANDO RELEVÂNCIA ---")
    # Se o passo anterior deu erro, não há o que validar. Apenas passe o erro adiante.
    if state.get("error"):
        return {}
        
    system_prompt = "Você é um assistente de validação. Analise a pergunta do usuário, a query SQL executada e o resultado obtido. Sua única tarefa é decidir se o resultado responde adequadamente à pergunta original. Responda estritamente com 'SIM' ou 'NÃO'."
    user_prompt = f"A pergunta original foi: '{state['question']}'.\nA query SQL executada foi: '{state['sql_query']}'.\nO resultado obtido foi: '{state['query_result']}'.\n\nEste resultado responde à pergunta?"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    
    response = client.chat.completions.create(
        model=CHAT_MODEL, 
        messages=messages, 
        tools=[{"type": "function", "function": {"name": "validation", "parameters": ValidationDecision.model_json_schema()}}], 
        tool_choice={"type": "function", "function": {"name": "validation"}}
    )
    decision = ValidationDecision(**json.loads(response.choices[0].message.tool_calls[0].function.arguments)).decision
    if decision.upper() == "NÃO":
        return {"error": "O resultado da query não foi relevante para a pergunta.", "retries": state.get("retries", 0) + 1}
    return {"error": None}

# CORREÇÃO: Nó de resposta final mais robusto
def generate_final_answer_node(state: GraphState) -> Dict:
    print("--- GERANDO RESPOSTA FINAL ---")
    # Se chegamos aqui com um erro, significa que o limite de tentativas foi atingido.
    if state.get("error"):
        return {"final_answer": f"Desculpe, não consegui processar sua pergunta após algumas tentativas. Último erro encontrado: {state['error']}"}

    system_prompt = "Você é um assistente prestativo. Sua tarefa é formular uma resposta clara e concisa em linguagem natural para o usuário, com base na pergunta original e nos dados retornados pela consulta ao banco de dados."
    user_prompt = f"Pergunta do usuário: '{state['question']}'.\nDados obtidos: '{state['query_result']}'.\n\nFormule a resposta final."
    messages = [{"role": "system", "content": system_prompt}, *state.get('history', []), {"role": "user", "content": user_prompt}]

    response = client.chat.completions.create(model=CHAT_MODEL, messages=messages)
    return {"final_answer": response.choices[0].message.content}

def decide_next_node(state: GraphState) -> str:
    if state.get("error"):
        if state.get("retries", 0) >= 3:
            # CORREÇÃO: Se atingir o limite, vá para o nó de resposta final para dar um feedback útil
            return "Limite de Tentativas Atingido"
        return "Erro (SQL ou Validação)"
    return "Sucesso na Validação"

# --- Aplicação FastAPI ---
# CORREÇÃO: Instanciar o FastAPI apenas uma vez
app = FastAPI(
    title="Agente Text-to-SQL Dinâmico com Memória",
    description="Uma API para conversar com bancos de dados usando linguagem natural.",
    version="1.2.0"
)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://text-to-sql-oraculo.vercel.app"
]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# (Função de resumo e endpoints / e /tables sem alterações)
def summarize_conversation(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    prompt = f"""
    Resuma a seguinte conversa entre um usuário e um assistente de forma concisa. 
    O resumo deve capturar os principais pontos, perguntas e respostas para que o contexto seja mantido em futuras interações, mas de forma muito mais curta.

    Conversa a ser resumida:
    {history_str}
    """
    
    try:
        response = client.chat.completions.create(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
        summary = response.choices[0].message.content
        return [{"role": "system", "content": f"Resumo da conversa anterior: {summary}"}, *history[-4:]]
    except Exception as e:
        print(f"Erro ao resumir: {e}")
        return history

@app.get("/")
async def root():
    return {"message": "Text-to-SQL Agent API is running."}

@app.get("/tables", response_model=List[TableInfo], tags=["Configuração"])
def get_configured_tables():
    if "tables_info" not in app_state:
        raise HTTPException(status_code=404, detail="Agente não configurado.")
    return app_state["tables_info"]

@app.post("/configure_agent", status_code=200)
def configure_agent(config: AgentConfiguration):
    try:
        db_engine = create_engine(config.db_credentials.connection_string)
        inspector = inspect(db_engine)
        table_names = [t.table_name for t in config.tables]
        schemas = {
            name: f"CREATE TABLE {name} (\n" + ",\n".join([f"  {col['name']} {str(col['type'])}" for col in inspector.get_columns(name)]) + "\n);"
            for name in table_names if inspector.get_columns(name)
        }
        chroma_client = chromadb.Client()
        embedding_func = embedding_functions.OpenAIEmbeddingFunction(api_key=OPENAI_API_KEY, model_name=EMBEDDING_MODEL)
        chroma_collection = chroma_client.get_or_create_collection(name="dynamic_db_agent_memory", embedding_function=embedding_func)
        
        ids = [f"{t.table_name}_doc" for t in config.tables]
        if chroma_collection.count() > 0:
            existing_ids = chroma_collection.get(ids=ids)['ids']
            if existing_ids:
                chroma_collection.delete(ids=existing_ids)
        
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
        
        # CORREÇÃO: Lógica condicional ajustada
        workflow.add_conditional_edges("validate_relevance", decide_next_node, {
            "Erro (SQL ou Validação)": "generate_sql",
            "Sucesso na Validação": "generate_final_answer",
            "Limite de Tentativas Atingido": "generate_final_answer" # Manda para gerar uma resposta de erro
        })
        workflow.add_edge("generate_final_answer", END)
        
        app_state["agent"] = workflow.compile()
        app_state["db_engine"] = db_engine
        app_state["tables_info"] = config.tables
        app_state["conversation_history"] = []
        
        return {"message": "Agente configurado com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao configurar o agente: {str(e)}")


@app.post("/query", response_model=QueryResponse, tags=["Chat"])
def query_agent(request: QueryRequest):
    if "agent" not in app_state:
        raise HTTPException(status_code=400, detail="Agente não configurado.")
    
    try:
        history = app_state.get("conversation_history", [])
        if len(history) >= SUMMARY_THRESHOLD:
            history = summarize_conversation(history)
            app_state["conversation_history"] = history

        agent = app_state["agent"]
        initial_state = {"question": request.question, "history": history}
        
        final_state = agent.invoke(initial_state, {"recursion_limit": 15})
        
        # Este IF agora se torna um fallback, pois o grafo deve sempre terminar em 'generate_final_answer'
        if not final_state.get('final_answer') and final_state.get('error'):
            raise HTTPException(status_code=500, detail=f"O agente falhou. Último erro: {final_state['error']}")
        
        answer = final_state.get('final_answer', "Não foi possível gerar uma resposta.")
        
        history.append({"role": "user", "content": request.question})
        history.append({"role": "assistant", "content": answer})
        app_state["conversation_history"] = history
        
        return QueryResponse(answer=answer)
    except Exception as e:
        # CORREÇÃO: Print muito mais detalhado para depuração
        print("--- ERRO INESPERADO NO ENDPOINT /query ---")
        print(f"Tipo de Exceção: {type(e)}")
        print(f"Mensagem de Erro: {e}")
        traceback.print_exc() # Imprime o stack trace completo
        raise HTTPException(status_code=500, detail=f"Erro crítico durante a execução da query: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)