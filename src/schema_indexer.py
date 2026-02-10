"""
Schema Indexer Module

Crawls data warehouse metadata and creates vector embeddings
for semantic search over tables, columns, and relationships.
"""

import os
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ColumnMetadata:
    """Metadata for a single column."""

    name: str
    data_type: str
    description: str = ""
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    sample_values: list = field(default_factory=list)
    statistics: dict = field(default_factory=dict)


@dataclass
class TableMetadata:
    """Metadata for a database table."""

    schema_name: str
    table_name: str
    description: str = ""
    columns: list[ColumnMetadata] = field(default_factory=list)
    row_count: int = 0
    relationships: list[dict] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None


@dataclass
class EmbeddingRecord:
    """Record to store in vector database."""

    id: str
    embedding: list[float]
    metadata: dict


class SchemaIndexer:
    """
    Indexes database schema into vector database for semantic search.
    """

    EMBEDDING_MODEL = "text-embedding-3-large"
    EMBEDDING_DIMENSION = 3072

    def __init__(
        self,
        connection_string: str,
        pinecone_index: str = "schema-embeddings",
        namespace: str = "default"
    ):
        """
        Initialize the schema indexer.

        Args:
            connection_string: SQLAlchemy database connection string
            pinecone_index: Name of Pinecone index
            namespace: Namespace for organizing embeddings
        """
        self.engine = create_engine(connection_string)
        self.openai = OpenAI()
        self.namespace = namespace

        # Initialize Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self._ensure_index(pinecone_index)
        self.index = self.pc.Index(pinecone_index)

    def _ensure_index(self, index_name: str) -> None:
        """Create Pinecone index if it doesn't exist."""
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]

        if index_name not in existing_indexes:
            self.pc.create_index(
                name=index_name,
                dimension=self.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )

    def crawl_schema(self, schemas: Optional[list[str]] = None) -> list[TableMetadata]:
        """
        Crawl database schema and extract metadata.

        Args:
            schemas: List of schemas to crawl (None = all)

        Returns:
            List of TableMetadata objects
        """
        inspector = inspect(self.engine)
        tables = []

        # Get schemas to process
        if schemas is None:
            schemas = inspector.get_schema_names()

        for schema in schemas:
            # Skip system schemas
            if schema in ('information_schema', 'pg_catalog'):
                continue

            table_names = inspector.get_table_names(schema=schema)

            for table_name in table_names:
                table = self._extract_table_metadata(inspector, schema, table_name)
                tables.append(table)

        return tables

    def _extract_table_metadata(
        self,
        inspector,
        schema: str,
        table_name: str
    ) -> TableMetadata:
        """Extract metadata for a single table."""
        # Get columns
        columns = []
        pk_columns = set(inspector.get_pk_constraint(table_name, schema=schema).get('constrained_columns', []))

        for col in inspector.get_columns(table_name, schema=schema):
            column = ColumnMetadata(
                name=col['name'],
                data_type=str(col['type']),
                is_nullable=col.get('nullable', True),
                is_primary_key=col['name'] in pk_columns
            )

            # Get sample values for the column
            column.sample_values = self._get_sample_values(schema, table_name, col['name'])

            columns.append(column)

        # Get foreign keys
        fks = inspector.get_foreign_keys(table_name, schema=schema)
        relationships = [
            {
                'column': fk['constrained_columns'][0] if fk['constrained_columns'] else None,
                'ref_table': f"{fk['referred_schema']}.{fk['referred_table']}" if fk['referred_schema'] else fk['referred_table'],
                'ref_column': fk['referred_columns'][0] if fk['referred_columns'] else None
            }
            for fk in fks
        ]

        # Mark FK columns
        for rel in relationships:
            for col in columns:
                if col.name == rel['column']:
                    col.is_foreign_key = True

        # Get row count
        row_count = self._get_row_count(schema, table_name)

        return TableMetadata(
            schema_name=schema,
            table_name=table_name,
            columns=columns,
            row_count=row_count,
            relationships=relationships
        )

    def _get_sample_values(
        self,
        schema: str,
        table: str,
        column: str,
        limit: int = 5
    ) -> list:
        """Get sample values for a column."""
        try:
            query = text(f"""
                SELECT DISTINCT "{column}"
                FROM "{schema}"."{table}"
                WHERE "{column}" IS NOT NULL
                LIMIT {limit}
            """)
            with self.engine.connect() as conn:
                result = conn.execute(query)
                return [str(row[0]) for row in result]
        except Exception:
            return []

    def _get_row_count(self, schema: str, table: str) -> int:
        """Get approximate row count for a table."""
        try:
            query = text(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
            with self.engine.connect() as conn:
                result = conn.execute(query)
                return result.scalar() or 0
        except Exception:
            return 0

    def create_embedding_text(self, table: TableMetadata) -> str:
        """
        Create rich text representation for embedding.

        Combines table name, description, columns, and sample values
        into a single text for embedding.
        """
        parts = [
            f"Table: {table.schema_name}.{table.table_name}",
            f"Description: {table.description or 'No description available'}"
        ]

        # Add column information
        column_parts = []
        for col in table.columns:
            col_text = f"{col.name} ({col.data_type})"
            if col.is_primary_key:
                col_text += " [PRIMARY KEY]"
            if col.is_foreign_key:
                col_text += " [FOREIGN KEY]"
            if col.sample_values:
                col_text += f" - Examples: {', '.join(col.sample_values[:3])}"
            column_parts.append(col_text)

        parts.append("Columns: " + "; ".join(column_parts))

        # Add relationships
        if table.relationships:
            rel_text = "; ".join([
                f"{r['column']} -> {r['ref_table']}.{r['ref_column']}"
                for r in table.relationships
            ])
            parts.append(f"Relationships: {rel_text}")

        return "\n".join(parts)

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        response = self.openai.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding

    def index_table(self, table: TableMetadata) -> str:
        """
        Index a single table into vector database.

        Returns:
            ID of the indexed record
        """
        # Create embedding text
        embedding_text = self.create_embedding_text(table)

        # Generate embedding
        embedding = self.generate_embedding(embedding_text)

        # Create unique ID
        table_id = hashlib.md5(
            f"{table.schema_name}.{table.table_name}".encode()
        ).hexdigest()

        # Prepare metadata
        metadata = {
            "schema": table.schema_name,
            "table": table.table_name,
            "description": table.description,
            "columns": [col.name for col in table.columns],
            "column_types": {col.name: col.data_type for col in table.columns},
            "row_count": table.row_count,
            "pk_columns": [col.name for col in table.columns if col.is_primary_key],
            "fk_columns": [col.name for col in table.columns if col.is_foreign_key],
            "embedding_text": embedding_text[:1000]  # Truncate for metadata limits
        }

        # Upsert to Pinecone
        self.index.upsert(
            vectors=[{
                "id": table_id,
                "values": embedding,
                "metadata": metadata
            }],
            namespace=self.namespace
        )

        return table_id

    def index_all(self, schemas: Optional[list[str]] = None) -> dict:
        """
        Index all tables in the database.

        Args:
            schemas: List of schemas to index (None = all)

        Returns:
            Summary of indexed tables
        """
        tables = self.crawl_schema(schemas)

        indexed = []
        failed = []

        for table in tables:
            try:
                table_id = self.index_table(table)
                indexed.append({
                    "table": f"{table.schema_name}.{table.table_name}",
                    "id": table_id
                })
            except Exception as e:
                failed.append({
                    "table": f"{table.schema_name}.{table.table_name}",
                    "error": str(e)
                })

        return {
            "total_tables": len(tables),
            "indexed": len(indexed),
            "failed": len(failed),
            "details": {
                "indexed": indexed,
                "failed": failed
            }
        }

    def delete_index(self) -> None:
        """Delete all vectors in the namespace."""
        self.index.delete(delete_all=True, namespace=self.namespace)


# Convenience function
def index_database(connection_string: str, schemas: Optional[list[str]] = None) -> dict:
    """Quick indexing of database schema."""
    indexer = SchemaIndexer(connection_string)
    return indexer.index_all(schemas)
