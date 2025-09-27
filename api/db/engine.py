"""Cria o engine do banco de dados com base no dialeto."""

from sqlalchemy import create_engine

def create_db_engine(dialect: str):
    """Cria e retorna um engine do SQLAlchemy com base no dialeto."""
    if dialect.lower() == 'sqlserver':
        connection_string = "mssql+pyodbc://<USUARIO>:<SENHA>@<SERVIDOR>/<BANCO>?driver=ODBC+Driver+17+for+SQL+Server"
        return create_engine(connection_string)
    elif dialect.lower() == 'oracle':
        connection_string = "oracle+oracledb://<USUARIO>:<SENHA>@<HOSTNAME>:<PORTA>/<SERVICE_NAME>"
        return create_engine(connection_string)
    elif dialect.lower() == 'sqlite':
        # Usa o arquivo de banco de dados físico
        return create_engine("sqlite:///db/database.db")
    else:
        raise ValueError("Dialeto não suportado.")
