"""Modelo para a decisão de validação."""

from pydantic import BaseModel, Field

class ValidationDecision(BaseModel):
    """Modelo para a decisão de validação."""
    decision: str = Field(
        description="Responda 'SIM' se a resposta for relevante, 'NÃO' caso contrário."
    )
