"""
Semantic Discovery - Main Entry Point

Combines schema indexing, semantic search, and SQL generation
into a unified interface for natural language data discovery.
"""

import os
from dataclasses import dataclass
from typing import Optional, Any
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

from .schema_indexer import SchemaIndexer
from .semantic_search import SemanticSearch, SearchResponse
from .sql_generator import SQLGenerator, GeneratedSQL, ConversationContext

load_dotenv()


@dataclass
class DiscoveryResult:
    """Complete result from semantic discovery."""

    # The natural language query
    question: str

    # Generated SQL
    sql: str
    sql_explanation: str

    # Query results
    data: Optional[pd.DataFrame]
    row_count: int

    # Natural language summary of results
    summary: str

    # Metadata
    tables_used: list[str]
    confidence: float
    warnings: list[str]
    execution_time_ms: float


class SemanticDiscovery:
    """
    Main interface for semantic data discovery.

    Provides natural language interface to query databases,
    combining vector search for schema discovery with LLM-powered
    SQL generation.

    Example:
        >>> discovery = SemanticDiscovery("postgresql://user:pass@host/db")
        >>> result = discovery.query("Show me top customers by revenue")
        >>> print(result.sql)
        >>> print(result.data)
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        pinecone_index: str = "schema-embeddings",
        model: str = "gpt-4-turbo",
        dialect: str = "snowflake"
    ):
        """
        Initialize Semantic Discovery.

        Args:
            connection_string: Database connection string
            pinecone_index: Pinecone index name for schema
            model: LLM model for SQL generation
            dialect: SQL dialect
        """
        self.connection_string = connection_string or os.getenv("DATABASE_URL")
        self.engine = create_engine(self.connection_string) if self.connection_string else None

        self.indexer = SchemaIndexer(
            self.connection_string,
            pinecone_index=pinecone_index
        ) if self.connection_string else None

        self.search = SemanticSearch(pinecone_index=pinecone_index)
        self.generator = SQLGenerator(model=model, dialect=dialect)

        # Conversation state
        self.conversation = ConversationContext(
            previous_queries=[],
            previous_tables=[],
            user_corrections=[]
        )

    def index_schema(self, schemas: Optional[list[str]] = None) -> dict:
        """
        Index database schema for semantic search.

        Args:
            schemas: List of schemas to index (None = all)

        Returns:
            Summary of indexing operation
        """
        if not self.indexer:
            raise ValueError("Database connection required for indexing")

        return self.indexer.index_all(schemas)

    def query(
        self,
        question: str,
        execute: bool = True,
        limit: int = 1000
    ) -> DiscoveryResult:
        """
        Query database using natural language.

        Args:
            question: Natural language question
            execute: Whether to execute the generated SQL
            limit: Maximum rows to return

        Returns:
            DiscoveryResult with SQL, data, and explanation
        """
        import time
        start_time = time.time()

        # Generate SQL
        generated = self.generator.generate(question, context=self.conversation)

        # Update conversation context
        self.conversation.previous_queries.append(question)
        self.conversation.previous_tables.extend(generated.tables_used)

        # Execute query if requested
        data = None
        row_count = 0
        summary = ""

        if execute and generated.sql and self.engine:
            try:
                # Add LIMIT if not present
                sql_to_execute = generated.sql
                if 'LIMIT' not in sql_to_execute.upper():
                    sql_to_execute = f"{sql_to_execute.rstrip(';')} LIMIT {limit}"

                data = pd.read_sql(text(sql_to_execute), self.engine)
                row_count = len(data)
                summary = self._generate_summary(question, data)
            except Exception as e:
                generated.warnings.append(f"Execution error: {str(e)}")

        execution_time = (time.time() - start_time) * 1000

        return DiscoveryResult(
            question=question,
            sql=generated.sql,
            sql_explanation=generated.explanation,
            data=data,
            row_count=row_count,
            summary=summary,
            tables_used=generated.tables_used,
            confidence=generated.confidence,
            warnings=generated.warnings,
            execution_time_ms=execution_time
        )

    def _generate_summary(self, question: str, data: pd.DataFrame) -> str:
        """Generate natural language summary of results."""
        if data.empty:
            return "No results found for this query."

        summary_parts = [f"Found {len(data)} results."]

        # Add basic statistics for numeric columns
        numeric_cols = data.select_dtypes(include=['number']).columns
        for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
            summary_parts.append(
                f"{col}: min={data[col].min():.2f}, max={data[col].max():.2f}, avg={data[col].mean():.2f}"
            )

        return " ".join(summary_parts)

    def search_tables(self, query: str, top_k: int = 5) -> SearchResponse:
        """
        Search for relevant tables without generating SQL.

        Args:
            query: Natural language query
            top_k: Number of results

        Returns:
            SearchResponse with matching tables
        """
        return self.search.search(query, top_k=top_k)

    def refine(self, feedback: str) -> DiscoveryResult:
        """
        Refine the last query based on user feedback.

        Args:
            feedback: User's correction or clarification

        Returns:
            New DiscoveryResult with refined query
        """
        if not self.conversation.previous_queries:
            raise ValueError("No previous query to refine")

        # Add feedback to context
        self.conversation.user_corrections.append(feedback)

        # Regenerate with context
        last_question = self.conversation.previous_queries[-1]
        return self.query(f"{last_question} ({feedback})")

    def explain(self, sql: str) -> str:
        """
        Explain a SQL query in natural language.

        Args:
            sql: SQL query to explain

        Returns:
            Natural language explanation
        """
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        model = ChatOpenAI(model="gpt-4-turbo", temperature=0)

        prompt = f"""Explain this SQL query in simple terms that a business user would understand:

```sql
{sql}
```

Focus on:
1. What data is being retrieved
2. How tables are connected
3. What filters are applied
4. What the results represent
"""
        response = model.invoke([HumanMessage(content=prompt)])
        return response.content

    def suggest_queries(self, table_name: str) -> list[str]:
        """
        Suggest example queries for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of suggested natural language queries
        """
        # Search for the table
        results = self.search.search(f"Table {table_name}", top_k=1)

        if not results.results:
            return []

        table = results.results[0]
        columns = table.columns

        suggestions = [
            f"Show all records from {table_name}",
            f"Count records in {table_name}",
        ]

        # Add column-specific suggestions
        for col in columns[:5]:
            if 'date' in col.lower() or 'time' in col.lower():
                suggestions.append(f"Show {table_name} records from last month")
            elif 'amount' in col.lower() or 'price' in col.lower() or 'total' in col.lower():
                suggestions.append(f"Show total {col} from {table_name}")
            elif 'id' in col.lower() and col != 'id':
                suggestions.append(f"Count {table_name} grouped by {col}")

        return suggestions[:5]

    def reset_conversation(self) -> None:
        """Reset conversation context."""
        self.conversation = ConversationContext(
            previous_queries=[],
            previous_tables=[],
            user_corrections=[]
        )


# CLI Interface
def main():
    """Command-line interface for Semantic Discovery."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Semantic Data Discovery - Natural language to SQL"
    )
    parser.add_argument(
        "question",
        nargs="?",
        help="Natural language question"
    )
    parser.add_argument(
        "--connection",
        type=str,
        help="Database connection string"
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Index database schema"
    )
    parser.add_argument(
        "--no-execute",
        action="store_true",
        help="Generate SQL without executing"
    )

    args = parser.parse_args()

    discovery = SemanticDiscovery(connection_string=args.connection)

    if args.index:
        print("Indexing database schema...")
        result = discovery.index_schema()
        print(f"Indexed {result['indexed']} tables")
        return

    if args.question:
        result = discovery.query(args.question, execute=not args.no_execute)

        print("\n" + "=" * 60)
        print("GENERATED SQL")
        print("=" * 60)
        print(result.sql)

        print("\n" + "=" * 60)
        print("EXPLANATION")
        print("=" * 60)
        print(result.sql_explanation)

        if result.data is not None:
            print("\n" + "=" * 60)
            print("RESULTS")
            print("=" * 60)
            print(result.data.head(10).to_string())
            print(f"\n{result.summary}")

        if result.warnings:
            print("\n" + "=" * 60)
            print("WARNINGS")
            print("=" * 60)
            for w in result.warnings:
                print(f"  - {w}")


if __name__ == "__main__":
    main()
