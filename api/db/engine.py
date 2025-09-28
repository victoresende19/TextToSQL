"""Cria o engine do banco de dados com base no dialeto."""

from sqlalchemy import create_engine

def create_db_engine(dialect: str, string_connection: str = None):
    """Cria e retorna um engine do SQLAlchemy com base no dialeto."""
    if dialect.lower() == 'sqlite':
        # Usa o arquivo de banco de dados físico
        return create_engine("sqlite:///db/database.db")

    return create_engine(string_connection)
