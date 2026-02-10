"""
Semantic Search Module

Performs vector similarity search to find relevant tables
and columns for natural language queries.
"""

import os
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SearchResult:
    """Result from semantic search."""

    table_name: str
    schema_name: str
    score: float
    columns: list[str]
    description: str
    relevance_explanation: str = ""


@dataclass
class SearchResponse:
    """Complete search response."""

    query: str
    results: list[SearchResult]
    total_matches: int
    search_time_ms: float


class SemanticSearch:
    """
    Performs semantic search over indexed database schema.
    """

    EMBEDDING_MODEL = "text-embedding-3-large"

    def __init__(
        self,
        pinecone_index: str = "schema-embeddings",
        namespace: str = "default"
    ):
        """
        Initialize semantic search.

        Args:
            pinecone_index: Name of Pinecone index
            namespace: Namespace to search in
        """
        self.openai = OpenAI()
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index(pinecone_index)
        self.namespace = namespace

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.7,
        filter_schema: Optional[str] = None
    ) -> SearchResponse:
        """
        Search for relevant tables given a natural language query.

        Args:
            query: Natural language query
            top_k: Number of results to return
            min_score: Minimum similarity score threshold
            filter_schema: Optional schema filter

        Returns:
            SearchResponse with matched tables
        """
        import time
        start_time = time.time()

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Build filter
        filter_dict = None
        if filter_schema:
            filter_dict = {"schema": {"$eq": filter_schema}}

        # Query Pinecone
        response = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=self.namespace,
            filter=filter_dict
        )

        # Process results
        results = []
        for match in response.matches:
            if match.score >= min_score:
                metadata = match.metadata or {}
                result = SearchResult(
                    table_name=metadata.get("table", "unknown"),
                    schema_name=metadata.get("schema", "unknown"),
                    score=match.score,
                    columns=metadata.get("columns", []),
                    description=metadata.get("description", ""),
                    relevance_explanation=self._explain_relevance(
                        query, metadata.get("embedding_text", "")
                    )
                )
                results.append(result)

        search_time = (time.time() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=results,
            total_matches=len(results),
            search_time_ms=search_time
        )

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for query text."""
        response = self.openai.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding

    def _explain_relevance(self, query: str, table_text: str) -> str:
        """Generate brief explanation of why this table is relevant."""
        # Simple keyword matching for explanation
        query_words = set(query.lower().split())
        table_words = set(table_text.lower().split())

        common = query_words.intersection(table_words)
        if common:
            return f"Matches keywords: {', '.join(list(common)[:5])}"
        return "Semantic similarity match"

    def find_related_tables(
        self,
        table_name: str,
        top_k: int = 5
    ) -> list[SearchResult]:
        """
        Find tables related to a given table.

        Args:
            table_name: Name of the source table
            top_k: Number of related tables to find

        Returns:
            List of related tables
        """
        # First, get the embedding for the source table
        response = self.search(
            f"Table similar to {table_name}",
            top_k=top_k + 1  # +1 to exclude self
        )

        # Filter out the source table itself
        results = [
            r for r in response.results
            if r.table_name.lower() != table_name.lower()
        ]

        return results[:top_k]

    def search_by_column(
        self,
        column_name: str,
        data_type: Optional[str] = None,
        top_k: int = 10
    ) -> SearchResponse:
        """
        Search for tables containing a specific column pattern.

        Args:
            column_name: Column name or pattern to search
            data_type: Optional data type filter
            top_k: Number of results

        Returns:
            Tables containing matching columns
        """
        query = f"Column named {column_name}"
        if data_type:
            query += f" with type {data_type}"

        return self.search(query, top_k=top_k)

    def get_join_suggestions(
        self,
        table_names: list[str]
    ) -> list[dict]:
        """
        Suggest possible joins between tables.

        Args:
            table_names: List of table names to analyze

        Returns:
            List of suggested join conditions
        """
        suggestions = []

        # Search for each table to get metadata
        table_metadata = {}
        for table in table_names:
            response = self.search(f"Table {table}", top_k=1)
            if response.results:
                table_metadata[table] = response.results[0]

        # Find common columns that might be join keys
        for i, t1 in enumerate(table_names):
            for t2 in table_names[i + 1:]:
                if t1 in table_metadata and t2 in table_metadata:
                    cols1 = set(table_metadata[t1].columns)
                    cols2 = set(table_metadata[t2].columns)
                    common = cols1.intersection(cols2)

                    for col in common:
                        # Likely join keys have _id suffix or are named 'id'
                        if col.endswith('_id') or col == 'id':
                            suggestions.append({
                                "table1": t1,
                                "table2": t2,
                                "join_column": col,
                                "confidence": "high" if col.endswith('_id') else "medium"
                            })

        return suggestions


# Convenience function
def search_tables(query: str, top_k: int = 5) -> SearchResponse:
    """Quick semantic search for tables."""
    searcher = SemanticSearch()
    return searcher.search(query, top_k=top_k)
