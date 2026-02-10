"""
Semantic Data Discovery Platform - Streamlit Demo

Natural language to SQL translation using vector embeddings and RAG architecture.
Ask questions in plain English, get accurate SQL queries.

Author: Waqas Shami
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.demo_database import DemoDatabase, get_sample_questions
from app.query_engine import QueryEngine
from app.schema_visualizer import render_schema_diagram, render_relationships_diagram

# Page configuration
st.set_page_config(
    page_title="Semantic Data Discovery",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for production look
st.markdown("""
<style>
    /* Main theme */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 20px;
        color: white;
    }
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        margin-bottom: 5px;
    }
    .main-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
    }

    /* Query input styling */
    .query-container {
        background: #f8f9fa;
        border-radius: 15px;
        padding: 25px;
        border: 2px solid #e9ecef;
    }

    /* Results cards */
    .result-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 15px;
    }

    /* Metrics */
    .metric-row {
        display: flex;
        gap: 15px;
        margin: 20px 0;
    }
    .metric-box {
        flex: 1;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: white;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.9;
    }

    /* Schema browser */
    .table-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 4px solid #667eea;
    }
    .table-name {
        font-weight: 600;
        color: #1a1a2e;
    }
    .column-list {
        font-size: 0.85rem;
        color: #666;
        margin-top: 8px;
    }

    /* SQL display */
    .sql-container {
        background: #1e1e1e;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
    }

    /* Confidence badge */
    .confidence-high { background: #28a745; }
    .confidence-medium { background: #ffc107; color: #333; }
    .confidence-low { background: #dc3545; }
    .confidence-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        color: white;
        font-size: 0.85rem;
        font-weight: 500;
    }

    /* History item */
    .history-item {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .history-item:hover {
        background: #e9ecef;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state."""
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    if 'db' not in st.session_state:
        st.session_state.db = DemoDatabase()
    if 'engine' not in st.session_state:
        st.session_state.engine = QueryEngine(st.session_state.db)
    if 'current_result' not in st.session_state:
        st.session_state.current_result = None


def render_header():
    """Render the main header."""
    st.markdown("""
    <div class="main-header">
        <div class="main-title">🔍 Semantic Data Discovery</div>
        <div class="main-subtitle">Ask questions in plain English • Get accurate SQL instantly • Powered by AI</div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render sidebar with schema browser and settings."""
    with st.sidebar:
        st.markdown("## 📊 Schema Browser")

        db = st.session_state.db
        tables = db.get_tables()

        # Table selector
        selected_table = st.selectbox(
            "Select a table to explore:",
            options=["All Tables"] + tables
        )

        if selected_table == "All Tables":
            for table in tables:
                with st.expander(f"📋 {table}", expanded=False):
                    schema = db.get_table_schema(table)
                    for col in schema:
                        col_type = col.get('type', 'unknown')
                        pk = " 🔑" if col.get('primary_key') else ""
                        fk = " 🔗" if col.get('foreign_key') else ""
                        st.markdown(f"• `{col['name']}` ({col_type}){pk}{fk}")
        else:
            st.markdown(f"### {selected_table}")
            schema = db.get_table_schema(selected_table)

            # Show columns in a table
            col_data = []
            for col in schema:
                col_data.append({
                    "Column": col['name'],
                    "Type": col.get('type', 'unknown'),
                    "Key": "PK" if col.get('primary_key') else ("FK" if col.get('foreign_key') else "")
                })
            st.dataframe(pd.DataFrame(col_data), hide_index=True, use_container_width=True)

            # Sample data
            st.markdown("**Sample Data:**")
            sample = db.get_sample_data(selected_table, limit=5)
            st.dataframe(sample, hide_index=True, use_container_width=True)

        st.divider()

        # Statistics
        st.markdown("## 📈 Database Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tables", len(tables))
        with col2:
            total_rows = sum(len(db.get_sample_data(t, 1000)) for t in tables)
            st.metric("Total Rows", f"{total_rows:,}")

        st.divider()

        # Query History
        st.markdown("## 🕐 Query History")
        if st.session_state.query_history:
            for i, item in enumerate(reversed(st.session_state.query_history[-5:])):
                if st.button(f"📝 {item['question'][:40]}...", key=f"history_{i}", use_container_width=True):
                    st.session_state.current_result = item
                    st.rerun()
        else:
            st.caption("No queries yet. Try asking a question!")

        st.divider()

        # About
        st.markdown("## 👤 Author")
        st.markdown("""
        **Waqas Shami**
        Head of Data Platform

        [LinkedIn](https://linkedin.com/in/waqas-shami) | [Website](https://waqasshami.com)
        """)


def render_query_section():
    """Render the main query input section."""
    st.markdown("### 💬 Ask a Question")

    # Sample questions
    sample_questions = get_sample_questions()

    col1, col2 = st.columns([3, 1])

    with col1:
        # Query input
        query = st.text_area(
            "Enter your question in natural language:",
            placeholder="e.g., Show me the top 10 customers by total revenue...",
            height=100,
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("**Try these:**")
        for q in sample_questions[:4]:
            if st.button(q[:35] + "...", key=f"sample_{hash(q)}", use_container_width=True):
                query = q
                st.session_state.pending_query = q

    # Check for pending query from button click
    if hasattr(st.session_state, 'pending_query'):
        query = st.session_state.pending_query
        del st.session_state.pending_query

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        search_clicked = st.button("🔍 Generate SQL", type="primary", use_container_width=True)

    with col2:
        execute_clicked = st.button("▶️ Execute Query", use_container_width=True)

    return query, search_clicked, execute_clicked


def render_results(result: dict):
    """Render query results."""
    if not result:
        return

    st.markdown("---")

    # Confidence and metadata
    col1, col2, col3, col4 = st.columns(4)

    confidence = result.get('confidence', 0.85)
    conf_class = "confidence-high" if confidence >= 0.8 else "confidence-medium" if confidence >= 0.6 else "confidence-low"

    with col1:
        st.markdown(f"""
        <div style="text-align: center;">
            <div class="confidence-badge {conf_class}">{confidence*100:.0f}% Confidence</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric("Tables Used", len(result.get('tables_used', [])))

    with col3:
        st.metric("Query Time", f"{result.get('query_time_ms', 0):.0f}ms")

    with col4:
        st.metric("Rows Returned", result.get('row_count', 0))

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Generated SQL", "📊 Results", "💡 Explanation", "🔗 Schema"])

    with tab1:
        st.code(result.get('sql', ''), language='sql')

        col1, col2 = st.columns([1, 4])
        with col1:
            st.download_button(
                "⬇️ Download SQL",
                result.get('sql', ''),
                file_name="query.sql",
                mime="text/plain"
            )

    with tab2:
        data = result.get('data')
        if data is not None and not data.empty:
            st.dataframe(data, use_container_width=True, hide_index=True)

            # Download as CSV
            csv = data.to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV",
                csv,
                file_name="results.csv",
                mime="text/csv"
            )
        else:
            st.info("No data returned or query not executed yet.")

    with tab3:
        st.markdown("### How this query was generated")
        st.markdown(result.get('explanation', 'No explanation available.'))

        if result.get('tables_used'):
            st.markdown("**Tables identified:**")
            for table in result['tables_used']:
                st.markdown(f"- `{table}`")

    with tab4:
        st.markdown("### Relevant Schema")

        # Build tables info for visualizer
        tables_info = {}
        for table in result.get('tables_used', []):
            schema = st.session_state.db.get_table_schema(table)
            if schema:
                tables_info[table] = schema

        # Render visual diagram
        if tables_info:
            render_schema_diagram(tables_info)

        # Show relationships if multiple tables
        if len(result.get('tables_used', [])) > 1:
            st.markdown("### Table Relationships")
            render_relationships_diagram()


def render_metrics_section():
    """Render the impact metrics section."""
    st.markdown("### 📈 Platform Impact")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea, #764ba2); padding: 25px; border-radius: 12px; text-align: center; color: white;">
            <div style="font-size: 2.2rem; font-weight: bold;">95%</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Faster Discovery</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f093fb, #f5576c); padding: 25px; border-radius: 12px; text-align: center; color: white;">
            <div style="font-size: 2.2rem; font-weight: bold;">5.5x</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Self-Service Adoption</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4facfe, #00f2fe); padding: 25px; border-radius: 12px; text-align: center; color: white;">
            <div style="font-size: 2.2rem; font-weight: bold;">77%</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Reduced SQL Tickets</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #43e97b, #38f9d7); padding: 25px; border-radius: 12px; text-align: center; color: white;">
            <div style="font-size: 2.2rem; font-weight: bold;">500+</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Users Enabled</div>
        </div>
        """, unsafe_allow_html=True)


def render_how_it_works():
    """Render the how it works section."""
    with st.expander("🔧 How It Works", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            ### 1️⃣ Semantic Understanding
            Your natural language question is converted into
            a vector embedding that captures its meaning.

            *Technologies: OpenAI Embeddings, Sentence Transformers*
            """)

        with col2:
            st.markdown("""
            ### 2️⃣ Schema Matching
            Vector similarity search finds the most relevant
            tables and columns in the database schema.

            *Technologies: Pinecone, FAISS, Vector Search*
            """)

        with col3:
            st.markdown("""
            ### 3️⃣ SQL Generation
            Using RAG (Retrieval Augmented Generation), an LLM
            generates accurate SQL with the retrieved context.

            *Technologies: GPT-4, Claude, LangChain*
            """)


def main():
    """Main application entry point."""
    init_session_state()
    render_header()

    # Sidebar
    render_sidebar()

    # Main content
    query, search_clicked, execute_clicked = render_query_section()

    # Process query
    if search_clicked and query.strip():
        with st.spinner("🔍 Analyzing question and generating SQL..."):
            start_time = time.time()
            result = st.session_state.engine.process_query(query, execute=False)
            result['query_time_ms'] = (time.time() - start_time) * 1000
            result['timestamp'] = datetime.now()
            result['question'] = query

            st.session_state.current_result = result
            st.session_state.query_history.append(result)

    if execute_clicked and st.session_state.current_result:
        with st.spinner("▶️ Executing query..."):
            result = st.session_state.current_result
            executed_result = st.session_state.engine.execute_query(result['sql'])
            result['data'] = executed_result['data']
            result['row_count'] = len(executed_result['data']) if executed_result['data'] is not None else 0
            st.session_state.current_result = result

    # Display results
    if st.session_state.current_result:
        render_results(st.session_state.current_result)

    st.markdown("---")

    # How it works
    render_how_it_works()

    # Metrics
    render_metrics_section()

    # Footer
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 30px; margin-top: 40px;">
        <p>🔍 Semantic Data Discovery Platform | Built with Streamlit, LangChain, and Vector Embeddings</p>
        <p style="font-size: 0.9rem;">
            <a href="https://waqasshami.com" target="_blank">waqasshami.com</a> |
            <a href="https://linkedin.com/in/waqas-shami" target="_blank">LinkedIn</a> |
            <a href="https://github.com/waqas-shami/semantic-data-discovery" target="_blank">GitHub</a>
        </p>
        <p style="font-size: 0.8rem; opacity: 0.7;">
            Demonstrating AI-powered data discovery for enterprise data platforms.
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
