#!/usr/bin/env python
"""
Test script for Semantic Data Discovery Demo

Validates that all components work correctly before deployment.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_demo_database():
    """Test the demo database initialization and methods."""
    print("Testing DemoDatabase...")

    from app.demo_database import DemoDatabase, get_sample_questions

    db = DemoDatabase()

    # Test get_tables
    tables = db.get_tables()
    assert len(tables) == 6, f"Expected 6 tables, got {len(tables)}"
    print(f"  [PASSED] get_tables: {tables}")

    # Test get_table_schema
    schema = db.get_table_schema('customers')
    assert len(schema) > 0, "Schema should not be empty"
    print(f"  [PASSED] get_table_schema: {len(schema)} columns")

    # Test get_sample_data
    sample = db.get_sample_data('orders', limit=5)
    assert len(sample) == 5, f"Expected 5 rows, got {len(sample)}"
    print(f"  [PASSED] get_sample_data: {len(sample)} rows")

    # Test sample questions
    questions = get_sample_questions()
    assert len(questions) > 0, "Should have sample questions"
    print(f"  [PASSED] get_sample_questions: {len(questions)} questions")

    print("DemoDatabase: All tests passed!\n")


def test_query_engine():
    """Test the query engine functionality."""
    print("Testing QueryEngine...")

    from app.demo_database import DemoDatabase
    from app.query_engine import QueryEngine

    db = DemoDatabase()
    engine = QueryEngine(db)

    # Test template matching
    result = engine.process_query("Show me top customers by revenue")
    assert result['confidence'] >= 0.9, f"Expected high confidence, got {result['confidence']}"
    assert 'sql' in result, "Result should contain SQL"
    assert 'explanation' in result, "Result should contain explanation"
    print(f"  [PASSED] Template match: confidence={result['confidence']}")

    # Test fallback query
    result = engine.process_query("Some random question about nothing")
    assert result['confidence'] < 0.9, "Fallback should have lower confidence"
    print(f"  [PASSED] Fallback query: confidence={result['confidence']}")

    # Test SQL execution
    result = engine.process_query("Show me low inventory items", execute=True)
    assert 'data' in result, "Executed result should have data"
    print(f"  [PASSED] Query execution: {result['row_count']} rows")

    print("QueryEngine: All tests passed!\n")


def test_schema_visualizer():
    """Test the schema visualizer module."""
    print("Testing SchemaVisualizer...")

    from app.schema_visualizer import render_schema_diagram, render_relationships_diagram

    # Just verify imports work (actual rendering requires Streamlit context)
    assert callable(render_schema_diagram), "render_schema_diagram should be callable"
    assert callable(render_relationships_diagram), "render_relationships_diagram should be callable"
    print("  [PASSED] Module imports successful")

    print("SchemaVisualizer: All tests passed!\n")


def test_streamlit_imports():
    """Test that all Streamlit app imports work."""
    print("Testing Streamlit app imports...")

    try:
        import streamlit
        print(f"  [PASSED] Streamlit version: {streamlit.__version__}")
    except ImportError:
        print("  [SKIPPED] Streamlit not installed")
        return

    try:
        from app.demo_database import DemoDatabase, get_sample_questions
        from app.query_engine import QueryEngine
        from app.schema_visualizer import render_schema_diagram
        print("  [PASSED] All app module imports successful")
    except ImportError as e:
        print(f"  [FAILED] Import error: {e}")
        return

    print("Streamlit imports: All tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("  Semantic Data Discovery - Test Suite")
    print("=" * 60)
    print()

    try:
        test_demo_database()
        test_query_engine()
        test_schema_visualizer()
        test_streamlit_imports()

        print("=" * 60)
        print("  ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Ready to run: python run_demo.py")
        print("Or deploy to Streamlit Cloud")
        return 0

    except Exception as e:
        print(f"\n[FAILED] Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
