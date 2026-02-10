"""
Schema Visualizer for Semantic Data Discovery

Renders interactive database schema diagrams using Streamlit components.
"""

import streamlit as st


def render_schema_diagram(tables_info: dict) -> None:
    """
    Render an interactive schema diagram.

    Args:
        tables_info: Dictionary with table names as keys and column info as values
    """
    st.markdown("### Database Schema Diagram")

    # Create a visual representation using HTML/CSS
    diagram_html = """
    <style>
        .schema-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
        }
        .table-box {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            min-width: 200px;
            overflow: hidden;
        }
        .table-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 15px;
            font-weight: bold;
            font-size: 14px;
        }
        .table-columns {
            padding: 10px 15px;
        }
        .column-row {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #eee;
            font-size: 12px;
        }
        .column-row:last-child {
            border-bottom: none;
        }
        .column-name {
            color: #333;
        }
        .column-type {
            color: #666;
            font-size: 11px;
        }
        .key-indicator {
            margin-left: 5px;
            font-size: 10px;
        }
        .pk { color: #ffc107; }
        .fk { color: #17a2b8; }
    </style>
    <div class="schema-container">
    """

    for table_name, columns in tables_info.items():
        diagram_html += f"""
        <div class="table-box">
            <div class="table-header">{table_name}</div>
            <div class="table-columns">
        """

        for col in columns:
            col_name = col.get('name', '')
            col_type = col.get('type', 'unknown')

            key_indicator = ""
            if col.get('primary_key'):
                key_indicator = '<span class="key-indicator pk">PK</span>'
            elif col.get('foreign_key'):
                key_indicator = '<span class="key-indicator fk">FK</span>'

            diagram_html += f"""
                <div class="column-row">
                    <span class="column-name">{col_name}{key_indicator}</span>
                    <span class="column-type">{col_type}</span>
                </div>
            """

        diagram_html += """
            </div>
        </div>
        """

    diagram_html += "</div>"

    st.markdown(diagram_html, unsafe_allow_html=True)


def render_relationships_diagram() -> None:
    """Render a simplified ER diagram showing table relationships."""

    relationships_html = """
    <style>
        .er-container {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin: 15px 0;
        }
        .er-title {
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }
        .relationship-row {
            display: flex;
            align-items: center;
            padding: 8px 0;
            font-size: 13px;
        }
        .table-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
        }
        .relationship-arrow {
            color: #666;
            padding: 0 15px;
        }
        .relationship-type {
            color: #888;
            font-size: 11px;
            padding: 0 10px;
        }
    </style>
    <div class="er-container">
        <div class="er-title">Table Relationships</div>

        <div class="relationship-row">
            <span class="table-badge">customers</span>
            <span class="relationship-arrow">1 ──────── *</span>
            <span class="table-badge">orders</span>
            <span class="relationship-type">(customer_id)</span>
        </div>

        <div class="relationship-row">
            <span class="table-badge">orders</span>
            <span class="relationship-arrow">1 ──────── *</span>
            <span class="table-badge">order_items</span>
            <span class="relationship-type">(order_id)</span>
        </div>

        <div class="relationship-row">
            <span class="table-badge">products</span>
            <span class="relationship-arrow">1 ──────── *</span>
            <span class="table-badge">order_items</span>
            <span class="relationship-type">(product_id)</span>
        </div>

        <div class="relationship-row">
            <span class="table-badge">products</span>
            <span class="relationship-arrow">1 ──────── 1</span>
            <span class="table-badge">inventory</span>
            <span class="relationship-type">(product_id)</span>
        </div>

        <div class="relationship-row">
            <span class="table-badge">employees</span>
            <span class="relationship-arrow">1 ──────── *</span>
            <span class="table-badge">orders</span>
            <span class="relationship-type">(employee_id)</span>
        </div>
    </div>
    """

    st.markdown(relationships_html, unsafe_allow_html=True)


def render_mini_schema(tables: list[str], db) -> None:
    """
    Render a mini schema view for specific tables.

    Args:
        tables: List of table names to display
        db: Database instance with get_table_schema method
    """
    if not tables:
        return

    tables_info = {}
    for table in tables:
        schema = db.get_table_schema(table)
        if schema:
            tables_info[table] = schema

    if tables_info:
        render_schema_diagram(tables_info)
