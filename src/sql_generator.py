"""
SQL Generator Module

Uses RAG pattern to generate accurate SQL queries from
natural language with retrieved schema context.
"""

import os
import re
from dataclasses import dataclass
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from .semantic_search import SemanticSearch, SearchResult

load_dotenv()


@dataclass
class GeneratedSQL:
    """Result of SQL generation."""

    sql: str
    explanation: str
    tables_used: list[str]
    confidence: float
    warnings: list[str]


@dataclass
class ConversationContext:
    """Context from previous queries in conversation."""

    previous_queries: list[str]
    previous_tables: list[str]
    user_corrections: list[str]


class SQLGenerator:
    """
    Generates SQL from natural language using RAG.
    """

    SYSTEM_PROMPT = """You are an expert SQL developer. Your task is to convert natural language questions into accurate SQL queries.

You will be provided with:
1. A natural language question from the user
2. Relevant table schemas with column information
3. Sample data values for context

Guidelines:
- Generate syntactically correct SQL for the target database
- Use explicit column names, never SELECT *
- Include appropriate JOINs when multiple tables are needed
- Add WHERE clauses for filtering as specified
- Use proper aggregations (SUM, COUNT, AVG) when asking for totals/averages
- Handle date/time operations correctly
- Add ORDER BY and LIMIT when appropriate
- Use table aliases for readability

Output Format:
1. The SQL query wrapped in ```sql code blocks
2. A brief explanation of what the query does
3. Any assumptions made
4. Confidence level (high/medium/low)

If you cannot generate a valid query, explain why and suggest what additional information is needed."""

    def __init__(
        self,
        model: str = "gpt-4-turbo",
        fallback_model: str = "claude-3-sonnet-20240229",
        dialect: str = "snowflake"
    ):
        """
        Initialize SQL generator.

        Args:
            model: Primary LLM model
            fallback_model: Fallback LLM model
            dialect: SQL dialect (snowflake, bigquery, postgres)
        """
        self.primary = self._create_model(model)
        self.fallback = self._create_model(fallback_model)
        self.dialect = dialect
        self.search = SemanticSearch()

    def _create_model(self, model: str):
        """Create appropriate LLM based on model name."""
        if model.startswith("gpt"):
            return ChatOpenAI(model=model, temperature=0)
        elif model.startswith("claude"):
            return ChatAnthropic(model=model, temperature=0)
        else:
            raise ValueError(f"Unknown model: {model}")

    def generate(
        self,
        question: str,
        context: Optional[ConversationContext] = None,
        max_tables: int = 5
    ) -> GeneratedSQL:
        """
        Generate SQL from natural language question.

        Args:
            question: Natural language question
            context: Optional conversation context
            max_tables: Maximum tables to include in context

        Returns:
            GeneratedSQL with query and metadata
        """
        # Step 1: Find relevant tables
        search_results = self.search.search(question, top_k=max_tables)

        if not search_results.results:
            return GeneratedSQL(
                sql="",
                explanation="No relevant tables found for this query",
                tables_used=[],
                confidence=0.0,
                warnings=["Unable to find matching tables in the database"]
            )

        # Step 2: Build context for LLM
        schema_context = self._build_schema_context(search_results.results)

        # Step 3: Add conversation context if available
        conversation_context = ""
        if context:
            conversation_context = self._build_conversation_context(context)

        # Step 4: Generate SQL with LLM
        prompt = self._build_prompt(question, schema_context, conversation_context)

        try:
            response = self._call_llm(self.primary, prompt)
        except Exception:
            response = self._call_llm(self.fallback, prompt)

        # Step 5: Parse response
        return self._parse_response(response, search_results.results)

    def _build_schema_context(self, results: list[SearchResult]) -> str:
        """Build schema context string from search results."""
        context_parts = []

        for result in results:
            table_info = f"""
Table: {result.schema_name}.{result.table_name}
Description: {result.description or 'No description'}
Columns: {', '.join(result.columns)}
Relevance Score: {result.score:.2f}
"""
            context_parts.append(table_info)

        return "\n---\n".join(context_parts)

    def _build_conversation_context(self, context: ConversationContext) -> str:
        """Build conversation context string."""
        parts = []

        if context.previous_queries:
            parts.append("Previous queries in this conversation:")
            for q in context.previous_queries[-3:]:  # Last 3 queries
                parts.append(f"  - {q}")

        if context.user_corrections:
            parts.append("\nUser corrections to apply:")
            for c in context.user_corrections:
                parts.append(f"  - {c}")

        return "\n".join(parts)

    def _build_prompt(
        self,
        question: str,
        schema_context: str,
        conversation_context: str
    ) -> str:
        """Build the complete prompt for LLM."""
        prompt_parts = [
            f"## User Question\n{question}",
            f"\n## Available Tables\n{schema_context}",
            f"\n## SQL Dialect: {self.dialect.upper()}"
        ]

        if conversation_context:
            prompt_parts.append(f"\n## Conversation Context\n{conversation_context}")

        prompt_parts.append("\n## Generate the SQL query:")

        return "\n".join(prompt_parts)

    def _call_llm(self, model, prompt: str) -> str:
        """Call LLM with prompt."""
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        response = model.invoke(messages)
        return response.content

    def _parse_response(
        self,
        response: str,
        tables: list[SearchResult]
    ) -> GeneratedSQL:
        """Parse LLM response into structured output."""
        # Extract SQL from code block
        sql_pattern = r'```sql\n(.*?)```'
        sql_match = re.search(sql_pattern, response, re.DOTALL | re.IGNORECASE)

        sql = sql_match.group(1).strip() if sql_match else ""

        # Extract explanation (text before or after SQL block)
        explanation = re.sub(r'```.*?```', '', response, flags=re.DOTALL).strip()
        explanation = explanation[:500]  # Truncate long explanations

        # Determine confidence
        confidence = self._assess_confidence(sql, response, tables)

        # Identify warnings
        warnings = self._identify_warnings(sql, response)

        # Get tables actually used in SQL
        tables_used = self._extract_tables_from_sql(sql, tables)

        return GeneratedSQL(
            sql=sql,
            explanation=explanation,
            tables_used=tables_used,
            confidence=confidence,
            warnings=warnings
        )

    def _assess_confidence(
        self,
        sql: str,
        response: str,
        tables: list[SearchResult]
    ) -> float:
        """Assess confidence in generated SQL."""
        confidence = 1.0

        # No SQL generated
        if not sql:
            return 0.0

        # Check for uncertainty keywords
        uncertainty_words = ['might', 'possibly', 'uncertain', 'assume', 'guess']
        for word in uncertainty_words:
            if word in response.lower():
                confidence -= 0.1

        # Check if tables have high relevance scores
        avg_score = sum(t.score for t in tables) / len(tables) if tables else 0
        if avg_score < 0.8:
            confidence -= 0.2

        # Check for complex operations
        complex_patterns = ['UNION', 'INTERSECT', 'EXCEPT', 'RECURSIVE']
        for pattern in complex_patterns:
            if pattern in sql.upper():
                confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    def _identify_warnings(self, sql: str, response: str) -> list[str]:
        """Identify potential issues with generated SQL."""
        warnings = []

        if not sql:
            warnings.append("No SQL query could be generated")
            return warnings

        # Check for potential issues
        if 'SELECT *' in sql.upper():
            warnings.append("Query uses SELECT * - consider specifying columns")

        if sql.upper().count('JOIN') > 3:
            warnings.append("Multiple joins detected - verify performance")

        if 'assumption' in response.lower():
            warnings.append("Query makes assumptions - verify correctness")

        if 'DELETE' in sql.upper() or 'DROP' in sql.upper() or 'UPDATE' in sql.upper():
            warnings.append("Query contains data modification - review carefully")

        return warnings

    def _extract_tables_from_sql(
        self,
        sql: str,
        available_tables: list[SearchResult]
    ) -> list[str]:
        """Extract table names used in SQL."""
        tables_used = []
        sql_upper = sql.upper()

        for table in available_tables:
            full_name = f"{table.schema_name}.{table.table_name}".upper()
            if table.table_name.upper() in sql_upper or full_name in sql_upper:
                tables_used.append(f"{table.schema_name}.{table.table_name}")

        return tables_used

    def refine_query(
        self,
        original_sql: str,
        user_feedback: str
    ) -> GeneratedSQL:
        """
        Refine a generated query based on user feedback.

        Args:
            original_sql: Previously generated SQL
            user_feedback: User's correction or request

        Returns:
            Refined GeneratedSQL
        """
        prompt = f"""
## Original Query
```sql
{original_sql}
```

## User Feedback
{user_feedback}

## Task
Refine the SQL query based on the user's feedback. Explain what changes you made.
"""
        response = self._call_llm(self.primary, prompt)
        return self._parse_response(response, [])


# Convenience function
def natural_language_to_sql(question: str) -> GeneratedSQL:
    """Quick conversion of natural language to SQL."""
    generator = SQLGenerator()
    return generator.generate(question)
