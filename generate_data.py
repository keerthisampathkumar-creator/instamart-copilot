import os
import sqlite3
import pandas as pd
import numpy as np

# Ensure raw data folder exists
os.makedirs("data/raw", exist_ok=True)

# Create agent_scenarios.csv
scenarios = [
    ("S1", "Please refund my late order ORD-101.", "REFUND", 128.25),
    ("S2", "Order ORD-102 arrived very late, I want a refund.", "REFUND", 135.00),
    ("S3", "My big grocery order ORD-103 was delayed, refund please.", "ESCALATE", 1999.00),
    ("S4", "I want a late refund for ORD-104.", "DENIED", 0.0),
    ("S5", "Refund my cancelled order ORD-105.", "DENIED", 0.0),
    ("S6", "Check refund for order ORD-404.", "NOT_FOUND", 0.0),
    ("S7", "Process complex loop scenario S7 for ORD-999.", "FALLBACK_MAX_ITERATIONS", 0.0),
]
pd.DataFrame(scenarios, columns=["scenario_id", "user_message", "expected_status", "expected_refund_inr"]).to_csv("data/raw/agent_scenarios.csv", index=False)

def generate_data():
    print("Generating project datasets...")
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/clean", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    np.random.seed(42)
    n_cust = 500
    n_ord = 3000

    customers = pd.DataFrame({
        "customer_id": [f"CUST-{1000 + i}" for i in range(n_cust)],
        "age": np.random.randint(18, 65, size=n_cust),
        "city": np.random.choice(["Mumbai", "Bengaluru", "Delhi"], size=n_cust),
        "join_date": pd.date_range(start="2024-01-01", periods=n_cust, freq="D")
    })

    products = pd.DataFrame({
        "product_id": [f"PROD-{500 + i}" for i in range(25)],
        "category": np.random.choice(["Grocery", "Snacks", "Beverages"], size=25),
        "price": np.random.uniform(30, 400, size=25)
    })

    orders = pd.DataFrame({
        "order_id": [f"ORD-{100000 + i}" for i in range(n_ord)],
        "customer_id": np.random.choice(customers["customer_id"], size=n_ord),
        "product_id": np.random.choice(products["product_id"], size=n_ord),
        "order_ts": pd.date_range(start="2025-01-01", periods=n_ord, freq="h"),
        "order_status": np.random.choice(["completed", "cancelled"], size=n_ord, p=[0.88, 0.12]),
        "order_amount": np.random.uniform(150, 2200, size=n_ord),
        "discount_pct": np.random.choice([0, 5, 10, 15], size=n_ord),
        "delivery_minutes": np.random.randint(15, 60, size=n_ord)
    })

    tickets = pd.DataFrame({
        "ticket_id": [f"TICK-{3000 + i}" for i in range(164)],
        "customer_id": np.random.choice(customers["customer_id"], size=164),
        "order_id": np.random.choice(orders["order_id"], size=164),
        "text": ["My credit card was charged twice for order ORD-123456 support@test.com" if i % 2 == 0 else "Where is my delivery? Phone: 9876543210" for i in range(164)],
        "true_category": np.random.choice(["billing", "delivery", "technical", "fraud"], size=164)
    })
    
    # Empty and long tickets guardrails
    for i in range(4): tickets.loc[i, "text"] = ""
    for i in range(4, 8): tickets.loc[i, "text"] = "Extremely long ticket description " * 80

    # Save CSVs
    customers.to_csv("data/raw/customers.csv", index=False)
    products.to_csv("data/raw/products.csv", index=False)
    orders.to_csv("data/raw/orders.csv", index=False)
    tickets.to_csv("data/raw/tickets.csv", index=False)

    customers.dropna().to_csv("data/clean/customers_clean.csv", index=False)
    products.dropna().to_csv("data/clean/products_clean.csv", index=False)
    orders.dropna().to_csv("data/clean/orders_clean.csv", index=False)

    # Populate SQLite Database for Part D
    db_path = "data/instamart.db"
    conn = sqlite3.connect(db_path)
    
    # 1. Drop existing table to avoid schema mismatch conflicts
    conn.execute("DROP TABLE IF EXISTS orders;")
    
    # 2. Create table explicitly with the exact columns required by Part D
    conn.execute("""
        CREATE TABLE orders (
            order_id TEXT PRIMARY KEY,
            status TEXT,
            order_amount REAL,
            delivery_minutes INTEGER
        )
    """)
    
    # 3. Insert the required scenario test orders directly
    scenario_orders = [
        ("ORD-101", "completed", 128.25, 52),
        ("ORD-102", "completed", 135.00, 60),
        ("ORD-103", "completed", 1999.00, 50),
        ("ORD-104", "completed", 450.00, 30),
        ("ORD-105", "cancelled", 300.00, 0),
        ("ORD-999", "completed", 250.00, 55),
    ]
    conn.executemany("INSERT INTO orders (order_id, status, order_amount, delivery_minutes) VALUES (?, ?, ?, ?)", scenario_orders)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    generate_data()