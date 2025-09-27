"""Funções para configurar o banco de dados e o Vectorstore dinamicamente."""

from sqlalchemy import inspect
import chromadb
from chromadb.utils import embedding_functions

def get_dynamic_db_schemas(engine, table_names: list) -> dict:
    """Inspeciona o banco e retorna os schemas DDL como strings."""
    inspector = inspect(engine)
    schemas = {}
    for table_name in table_names:
        columns = inspector.get_columns(table_name)
        if not columns: continue
        schema_str = f"CREATE TABLE {table_name} (\n"
        col_defs = [f"  {col['name']} {str(col['type'])} {'NOT NULL' if not col['nullable'] else ''}" for col in columns]
        schema_str += ",\n".join(col_defs) + "\n);"
        schemas[table_name] = schema_str
    return schemas

def setup_chroma_vectorstore(documents: list, metadatas: list, ids: list, openai_api_key: str, embedding_model: str):
    """Cria e popula um Vectorstore com ChromaDB."""
    print("--- CONFIGURANDO O VECTORSTORE CHROMA DB ---")
    chroma_client = chromadb.Client()

    ### ALTERADO: Usa a função de embedding padrão da OpenAI ###
    embedding_func = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name=embedding_model
    )

    collection = chroma_client.get_or_create_collection(name="dynamic_tables", embedding_function=embedding_func)
    if collection.count() == 0:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print("Coleção criada e populada.")
    return collection
