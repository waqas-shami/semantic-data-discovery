"""
Example Usage - Semantic Data Discovery

Demonstrates natural language to SQL conversion
and semantic search capabilities.
"""

from src.discovery import SemanticDiscovery
from src.semantic_search import SemanticSearch
from src.sql_generator import SQLGenerator

# Example 1: Basic Query
def demo_basic_query():
    """Demonstrate basic natural language query."""
    print("=" * 60)
    print("BASIC QUERY DEMO")
    print("=" * 60)

    # Initialize (without actual database for demo)
    generator = SQLGenerator(dialect="snowflake")

    # Example questions
    questions = [
        "Show me top 10 customers by total revenue",
        "How many orders were placed last month?",
        "What is the average order value by product category?",
        "List all customers who haven't ordered in 90 days"
    ]

    for question in questions:
        print(f"\nQuestion: {question}")
        result = generator.generate(question)
        print(f"SQL: {result.sql[:200]}..." if len(result.sql) > 200 else f"SQL: {result.sql}")
        print(f"Confidence: {result.confidence:.2f}")


# Example 2: Conversation Context
def demo_conversation():
    """Demonstrate multi-turn conversation."""
    print("\n" + "=" * 60)
    print("CONVERSATION DEMO")
    print("=" * 60)

    generator = SQLGenerator()

    # Turn 1
    print("\nTurn 1: 'Show me sales by region'")
    result1 = generator.generate("Show me sales by region")
    print(f"SQL: {result1.sql}")

    # Turn 2 - refine
    print("\nTurn 2: 'Only for Q4 2024'")
    result2 = generator.refine(
        result1.sql,
        "Only for Q4 2024"
    )
    print(f"Refined SQL: {result2.sql}")


# Example 3: Full Discovery Flow
def demo_full_discovery():
    """Demonstrate complete discovery workflow."""
    print("\n" + "=" * 60)
    print("FULL DISCOVERY FLOW")
    print("=" * 60)

    # Note: This requires actual database and Pinecone setup
    # Showing the API usage pattern

    print("""
    # Initialize with database connection
    discovery = SemanticDiscovery(
        connection_string="postgresql://user:pass@localhost/mydb"
    )

    # Index schema (one-time setup)
    discovery.index_schema()

    # Query in natural language
    result = discovery.query("Top customers by revenue last quarter")

    # Access results
    print(result.sql)           # Generated SQL
    print(result.data)          # Pandas DataFrame with results
    print(result.summary)       # Natural language summary
    print(result.confidence)    # Confidence score

    # Refine query
    refined = discovery.refine("Only include active customers")

    # Search for tables
    tables = discovery.search_tables("customer information")

    # Get suggestions
    suggestions = discovery.suggest_queries("orders")
    """)


# Example 4: Semantic Search Only
def demo_semantic_search():
    """Demonstrate semantic table search."""
    print("\n" + "=" * 60)
    print("SEMANTIC SEARCH DEMO")
    print("=" * 60)

    # Simulated search results
    print("""
    search = SemanticSearch()

    # Find tables related to customer data
    results = search.search("customer information and orders")

    for result in results.results:
        print(f"Table: {result.schema_name}.{result.table_name}")
        print(f"Relevance: {result.score:.2f}")
        print(f"Columns: {', '.join(result.columns[:5])}")
        print()

    # Find related tables
    related = search.find_related_tables("customers")

    # Get join suggestions
    joins = search.get_join_suggestions(["customers", "orders", "products"])
    """)


# Example 5: SQL Generation Patterns
def demo_sql_patterns():
    """Show various SQL generation patterns."""
    print("\n" + "=" * 60)
    print("SQL GENERATION PATTERNS")
    print("=" * 60)

    patterns = {
        "Aggregation": "Total sales by month for 2024",
        "Filtering": "Active customers from California",
        "Joining": "Customer orders with product details",
        "Window Function": "Rank customers by lifetime value",
        "Subquery": "Customers who ordered above average",
        "Date Range": "Orders between Jan and March 2024",
        "Top N": "Top 5 products by quantity sold"
    }

    generator = SQLGenerator(dialect="snowflake")

    for pattern_type, question in patterns.items():
        print(f"\n{pattern_type}: {question}")
        result = generator.generate(question)
        if result.sql:
            # Show just first line for brevity
            first_line = result.sql.split('\n')[0]
            print(f"  → {first_line}...")


if __name__ == "__main__":
    demo_basic_query()
    demo_conversation()
    demo_full_discovery()
    demo_semantic_search()
    demo_sql_patterns()
