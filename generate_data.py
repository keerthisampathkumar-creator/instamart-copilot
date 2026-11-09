import os
import random
import numpy as np
import pandas as pd

def build_mock_datasets(random_seed=42):
    random.seed(random_seed)
    np.random.seed(random_seed)

    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/clean", exist_ok=True)
    os.makedirs("data/policies", exist_ok=True)

    metro_locations = ["Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Pune"]
    gender_categories = ["male", "female", "other", "unknown", ""]
    
    customer_records = []
    for idx in range(1, 1201):
        c_id = f"C{idx:04d}"
        age_val = random.choice([random.randint(18, 70)] * 20 + [random.randint(5, 95), None])
        loc = random.choice(metro_locations)
        g_val = random.choice(gender_categories) if random.random() > 0.1 else ""
        reg_date = pd.Timestamp("2023-01-01") + pd.to_timedelta(random.randint(0, 365), unit="D")
        
        customer_records.append({
            "customer_id": c_id,
            "age": age_val,
            "city": loc,
            "gender": g_val,
            "join_date": reg_date.strftime("%Y-%m-%d")
        })
    customer_dataframe = pd.DataFrame(customer_records)
    customer_dataframe.loc[customer_dataframe.sample(n=30, random_state=random_seed).index, "gender"] = ""
    customer_dataframe.loc[customer_dataframe.sample(n=61, random_state=random_seed+1).index, "age"] = np.nan
    customer_dataframe.to_csv("data/raw/customers.csv", index=False)

    product_departments = ["Grocery", "Dairy", "Snacks", "Personal Care", "Electronics"]
    catalog_items = []
    for idx in range(1, 41):
        p_id = f"P{idx:03d}"
        dept = random.choice(product_departments)
        cost = round(random.uniform(20.0, 1500.0), 2)
        catalog_items.append({
            "product_id": p_id,
            "product_name": f"{dept} Item {idx}",
            "category": dept,
            "price_inr": cost
        })
    product_dataframe = pd.DataFrame(catalog_items)
    product_dataframe.to_csv("data/raw/products.csv", index=False)

    transaction_orders = []
    order_states = ["completed", "cancelled", "pending"]
    for idx in range(1, 13001):
        o_id = f"O{idx:06d}"
        c_id = f"C{random.randint(1, 1200):04d}"
        p_id = f"P{random.randint(1, 40):03d}"
        prod_row = product_dataframe[product_dataframe["product_id"] == p_id].iloc[0]
        quantity_val = random.choice([1, 2, 3, 4, 5])
        disc_pct = random.choice([0, 5, 10, 15, 20])
        
        raw_amt = round(prod_row["price_inr"] * quantity_val * (1 - disc_pct/100), 2)
        if random.random() < 0.01:
            raw_amt = "INVALID"
        elif random.random() < 0.01:
            raw_amt = -100.0

        state_val = random.choices(order_states, weights=[0.8, 0.1, 0.1], k=1)[0]
        deliv_time = random.randint(10, 45) if state_val == "completed" else (None if state_val == "pending" else random.choice([-5, None]))
        
        order_timestamp = pd.Timestamp("2023-06-01") + pd.to_timedelta(random.randint(0, 180), unit="D") + pd.to_timedelta(random.randint(0, 86400), unit="s")

        transaction_orders.append({
            "order_id": o_id,
            "customer_id": c_id,
            "product_id": p_id,
            "quantity": quantity_val,
            "discount_pct": disc_pct,
            "order_amount": raw_amt,
            "order_status": state_val,
            "delivery_minutes": deliv_time,
            "order_ts": order_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    order_dataframe = pd.DataFrame(transaction_orders)
    dup_rows = order_dataframe.sample(n=120, random_state=random_seed)
    order_dataframe = pd.concat([order_dataframe, dup_rows], ignore_index=True)
    order_dataframe.to_csv("data/raw/orders.csv", index=False)

    support_logs = []
    issue_categories = ["missing_item", "delayed_delivery", "damaged_item", "wrong_item"]
    for idx in range(1, 165):
        t_id = f"T{idx:04d}"
        o_id = f"O{random.randint(1, 12000):06d}"
        issue_val = random.choice(issue_categories)
        msg_text = f"My order {o_id} had a {issue_val} problem. Contact me at user{idx}@example.com or phone 98765{idx:04d}."
        support_logs.append({
            "ticket_id": t_id,
            "order_id": o_id,
            "issue_type": issue_val,
            "raw_text": msg_text
        })
    ticket_dataframe = pd.DataFrame(support_logs)
    ticket_dataframe.to_csv("data/raw/support_tickets.csv", index=False)

    print(f"generated: customers={len(customer_dataframe)} products={len(product_dataframe)} orders_raw={len(order_dataframe)} tickets={len(ticket_dataframe)}")

if __name__ == "__main__":
    build_mock_datasets()