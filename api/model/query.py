"""Modelo para a query SQL."""

from pydantic import BaseModel, Field

class SQLQuery(BaseModel):
    """Modelo para a query SQL."""
    query: str = Field(
        description="A query SQL completa para ser executada."
    )
