"""
Demo Database for Semantic Data Discovery

Provides a realistic sample database schema and data
for demonstrating natural language to SQL capabilities.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


def get_sample_questions() -> list[str]:
    """Get sample questions for the demo."""
    return [
        "Show me the top 10 customers by total revenue",
        "What were the total sales by product category last month?",
        "Which products are running low on inventory?",
        "How many orders were placed in each region?",
        "What is the average order value by customer segment?",
        "Show me customers who haven't ordered in 90 days",
        "What are the best-selling products this quarter?",
        "Which employees have the highest sales performance?",
        "Show monthly revenue trends for the past year",
        "What is the customer churn rate by segment?",
    ]


class DemoDatabase:
    """
    Simulated database with realistic e-commerce schema.
    """

    def __init__(self, seed: int = 42):
        """Initialize with sample data."""
        np.random.seed(seed)
        self._generate_data()

    def _generate_data(self):
        """Generate realistic sample data."""
        n_customers = 500
        n_products = 100
        n_orders = 2000
        n_employees = 25

        # Customers table
        self.customers = pd.DataFrame({
            'customer_id': range(1, n_customers + 1),
            'customer_name': [f"Customer {i}" for i in range(1, n_customers + 1)],
            'email': [f"customer{i}@email.com" for i in range(1, n_customers + 1)],
            'segment': np.random.choice(['Enterprise', 'SMB', 'Startup', 'Consumer'], n_customers),
            'region': np.random.choice(['North', 'South', 'East', 'West', 'Central'], n_customers),
            'signup_date': [datetime.now() - timedelta(days=np.random.randint(30, 1000)) for _ in range(n_customers)],
            'lifetime_value': np.random.exponential(5000, n_customers).round(2),
            'is_active': np.random.choice([True, False], n_customers, p=[0.85, 0.15])
        })

        # Products table
        categories = ['Electronics', 'Clothing', 'Home & Garden', 'Sports', 'Books', 'Food & Beverage']
        self.products = pd.DataFrame({
            'product_id': range(1, n_products + 1),
            'product_name': [f"Product {i}" for i in range(1, n_products + 1)],
            'category': np.random.choice(categories, n_products),
            'price': np.random.uniform(10, 500, n_products).round(2),
            'cost': np.random.uniform(5, 250, n_products).round(2),
            'stock_quantity': np.random.randint(0, 500, n_products),
            'reorder_point': np.random.randint(10, 50, n_products),
            'supplier_id': np.random.randint(1, 20, n_products),
            'is_active': np.random.choice([True, False], n_products, p=[0.9, 0.1])
        })

        # Employees table
        self.employees = pd.DataFrame({
            'employee_id': range(1, n_employees + 1),
            'employee_name': [f"Employee {i}" for i in range(1, n_employees + 1)],
            'department': np.random.choice(['Sales', 'Marketing', 'Support', 'Operations'], n_employees),
            'hire_date': [datetime.now() - timedelta(days=np.random.randint(100, 2000)) for _ in range(n_employees)],
            'salary': np.random.randint(50000, 150000, n_employees),
            'manager_id': [np.random.randint(1, 5) if i > 5 else None for i in range(1, n_employees + 1)]
        })

        # Orders table
        self.orders = pd.DataFrame({
            'order_id': range(1, n_orders + 1),
            'customer_id': np.random.randint(1, n_customers + 1, n_orders),
            'employee_id': np.random.randint(1, n_employees + 1, n_orders),
            'order_date': [datetime.now() - timedelta(days=np.random.randint(0, 365)) for _ in range(n_orders)],
            'status': np.random.choice(['completed', 'pending', 'shipped', 'cancelled'], n_orders, p=[0.7, 0.1, 0.15, 0.05]),
            'total_amount': np.random.exponential(200, n_orders).round(2),
            'shipping_cost': np.random.uniform(5, 30, n_orders).round(2),
            'discount_amount': np.random.uniform(0, 50, n_orders).round(2)
        })

        # Order Items table
        n_items = n_orders * 3  # Average 3 items per order
        self.order_items = pd.DataFrame({
            'item_id': range(1, n_items + 1),
            'order_id': np.random.randint(1, n_orders + 1, n_items),
            'product_id': np.random.randint(1, n_products + 1, n_items),
            'quantity': np.random.randint(1, 10, n_items),
            'unit_price': np.random.uniform(10, 200, n_items).round(2),
            'discount_percent': np.random.choice([0, 5, 10, 15, 20], n_items, p=[0.5, 0.2, 0.15, 0.1, 0.05])
        })

        # Inventory table
        self.inventory = pd.DataFrame({
            'inventory_id': range(1, n_products + 1),
            'product_id': range(1, n_products + 1),
            'warehouse_id': np.random.randint(1, 5, n_products),
            'quantity_on_hand': np.random.randint(0, 500, n_products),
            'quantity_reserved': np.random.randint(0, 50, n_products),
            'last_restock_date': [datetime.now() - timedelta(days=np.random.randint(1, 60)) for _ in range(n_products)]
        })

        # Store table references
        self._tables = {
            'customers': self.customers,
            'products': self.products,
            'employees': self.employees,
            'orders': self.orders,
            'order_items': self.order_items,
            'inventory': self.inventory
        }

        # Schema definitions
        self._schemas = {
            'customers': [
                {'name': 'customer_id', 'type': 'INTEGER', 'primary_key': True},
                {'name': 'customer_name', 'type': 'VARCHAR(100)'},
                {'name': 'email', 'type': 'VARCHAR(255)'},
                {'name': 'segment', 'type': 'VARCHAR(50)'},
                {'name': 'region', 'type': 'VARCHAR(50)'},
                {'name': 'signup_date', 'type': 'DATE'},
                {'name': 'lifetime_value', 'type': 'DECIMAL(10,2)'},
                {'name': 'is_active', 'type': 'BOOLEAN'}
            ],
            'products': [
                {'name': 'product_id', 'type': 'INTEGER', 'primary_key': True},
                {'name': 'product_name', 'type': 'VARCHAR(200)'},
                {'name': 'category', 'type': 'VARCHAR(100)'},
                {'name': 'price', 'type': 'DECIMAL(10,2)'},
                {'name': 'cost', 'type': 'DECIMAL(10,2)'},
                {'name': 'stock_quantity', 'type': 'INTEGER'},
                {'name': 'reorder_point', 'type': 'INTEGER'},
                {'name': 'supplier_id', 'type': 'INTEGER', 'foreign_key': True},
                {'name': 'is_active', 'type': 'BOOLEAN'}
            ],
            'employees': [
                {'name': 'employee_id', 'type': 'INTEGER', 'primary_key': True},
                {'name': 'employee_name', 'type': 'VARCHAR(100)'},
                {'name': 'department', 'type': 'VARCHAR(50)'},
                {'name': 'hire_date', 'type': 'DATE'},
                {'name': 'salary', 'type': 'INTEGER'},
                {'name': 'manager_id', 'type': 'INTEGER', 'foreign_key': True}
            ],
            'orders': [
                {'name': 'order_id', 'type': 'INTEGER', 'primary_key': True},
                {'name': 'customer_id', 'type': 'INTEGER', 'foreign_key': True},
                {'name': 'employee_id', 'type': 'INTEGER', 'foreign_key': True},
                {'name': 'order_date', 'type': 'DATE'},
                {'name': 'status', 'type': 'VARCHAR(20)'},
                {'name': 'total_amount', 'type': 'DECIMAL(10,2)'},
                {'name': 'shipping_cost', 'type': 'DECIMAL(10,2)'},
                {'name': 'discount_amount', 'type': 'DECIMAL(10,2)'}
            ],
            'order_items': [
                {'name': 'item_id', 'type': 'INTEGER', 'primary_key': True},
                {'name': 'order_id', 'type': 'INTEGER', 'foreign_key': True},
                {'name': 'product_id', 'type': 'INTEGER', 'foreign_key': True},
                {'name': 'quantity', 'type': 'INTEGER'},
                {'name': 'unit_price', 'type': 'DECIMAL(10,2)'},
                {'name': 'discount_percent', 'type': 'INTEGER'}
            ],
            'inventory': [
                {'name': 'inventory_id', 'type': 'INTEGER', 'primary_key': True},
                {'name': 'product_id', 'type': 'INTEGER', 'foreign_key': True},
                {'name': 'warehouse_id', 'type': 'INTEGER'},
                {'name': 'quantity_on_hand', 'type': 'INTEGER'},
                {'name': 'quantity_reserved', 'type': 'INTEGER'},
                {'name': 'last_restock_date', 'type': 'DATE'}
            ]
        }

    def get_tables(self) -> list[str]:
        """Get list of table names."""
        return list(self._tables.keys())

    def get_table_schema(self, table_name: str) -> list[dict]:
        """Get schema for a specific table."""
        return self._schemas.get(table_name, [])

    def get_sample_data(self, table_name: str, limit: int = 10) -> pd.DataFrame:
        """Get sample data from a table."""
        table = self._tables.get(table_name)
        if table is not None:
            return table.head(limit)
        return pd.DataFrame()

    def execute_sql(self, sql: str) -> pd.DataFrame:
        """
        Execute SQL against the demo database.
        Uses pandas for simple query simulation.
        """
        # This is a simplified SQL executor for demo purposes
        # In production, this would connect to a real database

        sql_lower = sql.lower()

        try:
            # Determine the main table
            for table_name in self._tables.keys():
                if table_name in sql_lower:
                    main_table = table_name
                    break
            else:
                main_table = 'orders'

            df = self._tables[main_table].copy()

            # Apply basic filters if WHERE clause exists
            if 'where' in sql_lower:
                # Simple status filter
                if "'completed'" in sql_lower:
                    if 'status' in df.columns:
                        df = df[df['status'] == 'completed']

            # Apply LIMIT
            if 'limit' in sql_lower:
                import re
                limit_match = re.search(r'limit\s+(\d+)', sql_lower)
                if limit_match:
                    df = df.head(int(limit_match.group(1)))

            # Apply ORDER BY (simplified)
            if 'order by' in sql_lower:
                if 'desc' in sql_lower:
                    # Get the column before DESC
                    if 'total_amount' in sql_lower or 'revenue' in sql_lower:
                        if 'total_amount' in df.columns:
                            df = df.sort_values('total_amount', ascending=False)
                        elif 'lifetime_value' in df.columns:
                            df = df.sort_values('lifetime_value', ascending=False)

            return df.head(100)  # Safety limit

        except Exception as e:
            print(f"Query execution error: {e}")
            return pd.DataFrame()

    def get_full_schema_text(self) -> str:
        """Get full schema as text for LLM context."""
        schema_text = []
        for table_name, columns in self._schemas.items():
            cols = ", ".join([f"{c['name']} {c['type']}" for c in columns])
            schema_text.append(f"CREATE TABLE {table_name} ({cols});")
        return "\n".join(schema_text)
