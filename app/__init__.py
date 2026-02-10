"""
Semantic Data Discovery Platform

Natural language to SQL translation using vector embeddings and RAG architecture.
"""

from app.demo_database import DemoDatabase, get_sample_questions
from app.query_engine import QueryEngine

__all__ = ["DemoDatabase", "QueryEngine", "get_sample_questions"]
__version__ = "1.0.0"
