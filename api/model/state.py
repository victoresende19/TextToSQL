"""Estado do gráfico para rastrear o progresso."""

from typing import TypedDict

class GraphState(TypedDict):
    """Estado do gráfico para rastrear o progresso."""
    question: str
    tables: str
    sql_query: str
    query_result: str
    final_answer: str
    error: str
    retries: int
