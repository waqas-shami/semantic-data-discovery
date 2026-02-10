"""
Query Engine for Semantic Data Discovery

Handles natural language to SQL translation using
pattern matching and pre-computed responses for demo mode.
"""

import re
from typing import Optional
import pandas as pd

from app.demo_database import DemoDatabase


# Pre-computed SQL responses for common queries
QUERY_TEMPLATES = {
    "top_customers_revenue": {
        "patterns": ["top.*customer.*revenue", "best.*customer", "highest.*customer.*value"],
        "sql": """SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    c.region,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(o.total_amount) AS total_revenue,
    AVG(o.total_amount) AS avg_order_value
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.customer_name, c.segment, c.region
ORDER BY total_revenue DESC
LIMIT 10""",
        "explanation": """**Query Logic:**

1. **Join Strategy**: Inner join between `customers` and `orders` to get customer purchase history
2. **Filtering**: Only completed orders are considered for revenue calculation
3. **Aggregation**: Calculates total orders, total revenue, and average order value per customer
4. **Sorting**: Orders by total revenue descending to show top customers first
5. **Limit**: Returns top 10 customers

**Tables Used:**
- `customers` - Customer master data
- `orders` - Order transactions

**Performance Notes:**
- Consider adding an index on `orders.customer_id` for large datasets
- Filter on `status` should use an index if available""",
        "tables": ["customers", "orders"],
        "confidence": 0.95
    },

    "sales_by_category": {
        "patterns": ["sales.*category", "revenue.*category", "category.*sales"],
        "sql": """SELECT
    p.category,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(oi.quantity) AS units_sold,
    SUM(oi.quantity * oi.unit_price) AS gross_revenue,
    SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)) AS net_revenue,
    AVG(oi.unit_price) AS avg_unit_price
FROM products p
INNER JOIN order_items oi ON p.product_id = oi.product_id
INNER JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'completed'
  AND o.order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
GROUP BY p.category
ORDER BY net_revenue DESC""",
        "explanation": """**Query Logic:**

1. **Three-way Join**: Products → Order Items → Orders to connect product categories to sales
2. **Time Filter**: Last month's data using DATE_TRUNC for month boundary
3. **Revenue Calculation**: Both gross (before discount) and net (after discount) revenue
4. **Aggregation**: By product category with multiple metrics

**Tables Used:**
- `products` - Product catalog with categories
- `order_items` - Line items for each order
- `orders` - Order header with dates and status

**Business Value:**
This query helps identify which product categories are performing best, supporting inventory and marketing decisions.""",
        "tables": ["products", "order_items", "orders"],
        "confidence": 0.92
    },

    "low_inventory": {
        "patterns": ["low.*inventory", "stock.*low", "reorder", "out of stock", "running low"],
        "sql": """SELECT
    p.product_id,
    p.product_name,
    p.category,
    i.quantity_on_hand,
    i.quantity_reserved,
    (i.quantity_on_hand - i.quantity_reserved) AS available_quantity,
    p.reorder_point,
    CASE
        WHEN (i.quantity_on_hand - i.quantity_reserved) <= 0 THEN 'OUT OF STOCK'
        WHEN (i.quantity_on_hand - i.quantity_reserved) <= p.reorder_point THEN 'REORDER NOW'
        WHEN (i.quantity_on_hand - i.quantity_reserved) <= p.reorder_point * 1.5 THEN 'LOW STOCK'
        ELSE 'HEALTHY'
    END AS stock_status,
    i.last_restock_date
FROM products p
INNER JOIN inventory i ON p.product_id = i.product_id
WHERE p.is_active = TRUE
  AND (i.quantity_on_hand - i.quantity_reserved) <= p.reorder_point * 1.5
ORDER BY
    CASE
        WHEN (i.quantity_on_hand - i.quantity_reserved) <= 0 THEN 1
        WHEN (i.quantity_on_hand - i.quantity_reserved) <= p.reorder_point THEN 2
        ELSE 3
    END,
    available_quantity ASC""",
        "explanation": """**Query Logic:**

1. **Stock Calculation**: Available = On Hand - Reserved quantity
2. **Status Classification**: Multi-tier status (Out of Stock, Reorder, Low, Healthy)
3. **Filtering**: Only active products below 1.5x reorder point
4. **Priority Sorting**: Out of stock items first, then by urgency

**Tables Used:**
- `products` - Product info including reorder points
- `inventory` - Current stock levels

**Operational Impact:**
Prevents stockouts by identifying products needing immediate attention.""",
        "tables": ["products", "inventory"],
        "confidence": 0.94
    },

    "orders_by_region": {
        "patterns": ["order.*region", "region.*order", "sales.*region", "region.*sales"],
        "sql": """SELECT
    c.region,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    SUM(o.total_amount) AS total_revenue,
    AVG(o.total_amount) AS avg_order_value,
    SUM(o.total_amount) / COUNT(DISTINCT o.customer_id) AS revenue_per_customer
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status IN ('completed', 'shipped')
GROUP BY c.region
ORDER BY total_revenue DESC""",
        "explanation": """**Query Logic:**

1. **Regional Analysis**: Groups all metrics by customer region
2. **Multiple Metrics**: Orders, unique customers, revenue, averages
3. **Revenue per Customer**: Key metric for regional performance comparison
4. **Status Filter**: Includes completed and shipped orders

**Tables Used:**
- `customers` - Customer region information
- `orders` - Order transactions

**Business Insight:**
Identifies high-performing regions for targeted marketing and resource allocation.""",
        "tables": ["customers", "orders"],
        "confidence": 0.91
    },

    "avg_order_by_segment": {
        "patterns": ["average.*order.*segment", "segment.*average", "order value.*segment"],
        "sql": """SELECT
    c.segment,
    COUNT(DISTINCT c.customer_id) AS customer_count,
    COUNT(o.order_id) AS total_orders,
    ROUND(AVG(o.total_amount), 2) AS avg_order_value,
    ROUND(STDDEV(o.total_amount), 2) AS order_value_stddev,
    MIN(o.total_amount) AS min_order,
    MAX(o.total_amount) AS max_order,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY o.total_amount) AS median_order
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
    AND o.status = 'completed'
GROUP BY c.segment
ORDER BY avg_order_value DESC""",
        "explanation": """**Query Logic:**

1. **Segment Analysis**: Comprehensive metrics by customer segment
2. **Statistical Measures**: Mean, standard deviation, min, max, median
3. **Left Join**: Includes segments even if no orders (for completeness)
4. **Filtered Join**: Only completed orders in aggregation

**Tables Used:**
- `customers` - Customer segment classification
- `orders` - Order amounts

**Strategic Value:**
Helps understand purchasing behavior differences across customer segments.""",
        "tables": ["customers", "orders"],
        "confidence": 0.93
    },

    "inactive_customers": {
        "patterns": ["haven't ordered", "inactive.*customer", "no order.*days", "churn", "dormant"],
        "sql": """SELECT
    c.customer_id,
    c.customer_name,
    c.email,
    c.segment,
    c.region,
    MAX(o.order_date) AS last_order_date,
    DATEDIFF(day, MAX(o.order_date), CURRENT_DATE) AS days_since_last_order,
    COUNT(o.order_id) AS total_orders,
    SUM(o.total_amount) AS lifetime_value,
    CASE
        WHEN DATEDIFF(day, MAX(o.order_date), CURRENT_DATE) > 180 THEN 'Churned'
        WHEN DATEDIFF(day, MAX(o.order_date), CURRENT_DATE) > 90 THEN 'At Risk'
        ELSE 'Cooling'
    END AS customer_status
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE c.is_active = TRUE
GROUP BY c.customer_id, c.customer_name, c.email, c.segment, c.region
HAVING DATEDIFF(day, MAX(o.order_date), CURRENT_DATE) > 90
   OR MAX(o.order_date) IS NULL
ORDER BY days_since_last_order DESC""",
        "explanation": """**Query Logic:**

1. **Inactivity Detection**: Finds customers with no orders in 90+ days
2. **Status Classification**: Churned (180+ days), At Risk (90-180), Cooling (30-90)
3. **Left Join**: Catches customers who never ordered
4. **Lifetime Value**: Included to prioritize high-value win-back campaigns

**Tables Used:**
- `customers` - Customer master data
- `orders` - Order history for recency calculation

**Business Action:**
Target list for customer win-back campaigns, prioritized by value.""",
        "tables": ["customers", "orders"],
        "confidence": 0.90
    },

    "best_selling_products": {
        "patterns": ["best.*sell", "top.*product", "popular.*product", "most sold"],
        "sql": """SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(oi.quantity) AS total_units_sold,
    COUNT(DISTINCT oi.order_id) AS number_of_orders,
    SUM(oi.quantity * oi.unit_price) AS total_revenue,
    AVG(oi.unit_price) AS avg_selling_price,
    p.price AS current_price,
    p.stock_quantity AS current_stock
FROM products p
INNER JOIN order_items oi ON p.product_id = oi.product_id
INNER JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'completed'
  AND o.order_date >= DATE_TRUNC('quarter', CURRENT_DATE)
GROUP BY p.product_id, p.product_name, p.category, p.price, p.stock_quantity
ORDER BY total_units_sold DESC
LIMIT 20""",
        "explanation": """**Query Logic:**

1. **Sales Volume**: Ranks products by total units sold
2. **Time Frame**: Current quarter for relevance
3. **Multiple Metrics**: Units, orders, revenue, pricing
4. **Stock Check**: Includes current inventory for context

**Tables Used:**
- `products` - Product catalog
- `order_items` - Sales line items
- `orders` - Order dates and status

**Merchandising Value:**
Identifies products to feature, reorder, or promote.""",
        "tables": ["products", "order_items", "orders"],
        "confidence": 0.94
    },

    "employee_performance": {
        "patterns": ["employee.*performance", "sales.*employee", "employee.*sales", "staff.*performance"],
        "sql": """SELECT
    e.employee_id,
    e.employee_name,
    e.department,
    COUNT(DISTINCT o.order_id) AS orders_handled,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    SUM(o.total_amount) AS total_sales,
    AVG(o.total_amount) AS avg_order_value,
    RANK() OVER (ORDER BY SUM(o.total_amount) DESC) AS sales_rank
FROM employees e
LEFT JOIN orders o ON e.employee_id = o.employee_id
    AND o.status = 'completed'
WHERE e.department = 'Sales'
GROUP BY e.employee_id, e.employee_name, e.department
ORDER BY total_sales DESC""",
        "explanation": """**Query Logic:**

1. **Sales Focus**: Filters to Sales department employees
2. **Performance Metrics**: Orders, customers, revenue, average order
3. **Ranking**: Adds competitive ranking by total sales
4. **Left Join**: Includes new employees with no sales yet

**Tables Used:**
- `employees` - Employee roster
- `orders` - Sales transactions

**Management Use:**
Performance reviews, incentive calculations, training needs identification.""",
        "tables": ["employees", "orders"],
        "confidence": 0.88
    },

    "monthly_trends": {
        "patterns": ["monthly.*trend", "revenue.*trend", "sales.*trend", "month over month"],
        "sql": """SELECT
    DATE_TRUNC('month', o.order_date) AS month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    SUM(o.total_amount) AS total_revenue,
    AVG(o.total_amount) AS avg_order_value,
    LAG(SUM(o.total_amount)) OVER (ORDER BY DATE_TRUNC('month', o.order_date)) AS prev_month_revenue,
    ROUND(
        (SUM(o.total_amount) - LAG(SUM(o.total_amount)) OVER (ORDER BY DATE_TRUNC('month', o.order_date)))
        / NULLIF(LAG(SUM(o.total_amount)) OVER (ORDER BY DATE_TRUNC('month', o.order_date)), 0) * 100
    , 2) AS mom_growth_pct
FROM orders o
WHERE o.status = 'completed'
  AND o.order_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', o.order_date)
ORDER BY month DESC""",
        "explanation": """**Query Logic:**

1. **Time Series**: Groups by month for trend analysis
2. **Window Functions**: LAG to calculate month-over-month growth
3. **Growth Calculation**: Percentage change from previous month
4. **12-Month Window**: Full year for seasonality visibility

**Tables Used:**
- `orders` - Order dates and amounts

**Strategic Planning:**
Identifies seasonality, growth patterns, and trend reversals.""",
        "tables": ["orders"],
        "confidence": 0.92
    }
}


class QueryEngine:
    """
    Engine for processing natural language queries and generating SQL.
    """

    def __init__(self, database: DemoDatabase):
        self.db = database

    def process_query(self, question: str, execute: bool = False) -> dict:
        """
        Process a natural language question and generate SQL.

        Args:
            question: Natural language question
            execute: Whether to execute the query

        Returns:
            Dict with sql, explanation, tables, confidence, and optionally data
        """
        # Find matching template
        template = self._find_template(question)

        if template:
            result = {
                "sql": template["sql"],
                "explanation": template["explanation"],
                "tables_used": template["tables"],
                "confidence": template["confidence"],
                "data": None,
                "row_count": 0
            }
        else:
            # Fallback generic query
            result = self._generate_fallback(question)

        # Execute if requested
        if execute:
            executed = self.execute_query(result["sql"])
            result["data"] = executed["data"]
            result["row_count"] = executed["row_count"]

        return result

    def _find_template(self, question: str) -> Optional[dict]:
        """Find matching query template based on patterns."""
        question_lower = question.lower()

        for template_name, template in QUERY_TEMPLATES.items():
            for pattern in template["patterns"]:
                if re.search(pattern, question_lower):
                    return template

        return None

    def _generate_fallback(self, question: str) -> dict:
        """Generate a fallback response for unmatched queries."""
        question_lower = question.lower()

        # Determine main table from question
        table_hints = {
            "customer": "customers",
            "order": "orders",
            "product": "products",
            "inventory": "inventory",
            "employee": "employees"
        }

        main_table = "orders"  # default
        for hint, table in table_hints.items():
            if hint in question_lower:
                main_table = table
                break

        sql = f"""-- Generated query for: {question}
SELECT *
FROM {main_table}
LIMIT 100"""

        return {
            "sql": sql,
            "explanation": f"""**Auto-generated Query**

This is a basic query on the `{main_table}` table. For more specific results,
try asking about:
- Customer revenue or segments
- Product sales or inventory
- Order trends or regional analysis
- Employee performance

The semantic search engine found partial matches but couldn't determine
the exact intent. The query returns sample data from the most relevant table.""",
            "tables_used": [main_table],
            "confidence": 0.5
        }

    def execute_query(self, sql: str) -> dict:
        """Execute SQL and return results."""
        try:
            data = self.db.execute_sql(sql)
            return {
                "data": data,
                "row_count": len(data) if data is not None else 0,
                "error": None
            }
        except Exception as e:
            return {
                "data": pd.DataFrame(),
                "row_count": 0,
                "error": str(e)
            }

    def get_schema_context(self, tables: list[str]) -> str:
        """Get schema context for specific tables."""
        context_parts = []
        for table in tables:
            schema = self.db.get_table_schema(table)
            cols = ", ".join([f"{c['name']} {c['type']}" for c in schema])
            context_parts.append(f"TABLE {table}: {cols}")
        return "\n".join(context_parts)
