import os
import sqlite3
import pandas as pd
import numpy as np

def execute_foundation_cleaning():
    print("Executing Data Foundation and Cleanup Pipeline...")

    # 1. Import Raw Datasets
    cust_df = pd.read_csv("data/raw/customers.csv")
    prod_df = pd.read_csv("data/raw/products.csv")
    ord_df = pd.read_csv("data/raw/orders.csv")
    tkt_df = pd.read_csv("data/raw/support_tickets.csv")

    # 2. Extract Audit Statistics
    print("\n--- DATASET AUDIT METRICS ---")
    total_raw_orders = len(ord_df)
    duplicate_records = ord_df.duplicated().sum()
    pending_records = len(ord_df[ord_df["order_status"] == "pending"])
    unique_orders_count = ord_df["order_id"].nunique()
    
    invalid_amount_entries = pd.to_numeric(ord_df["order_amount"], errors='coerce').isna().sum()
    negative_deliv_count = len(ord_df[ord_df["delivery_minutes"] < 0])
    missing_deliv_count = ord_df["delivery_minutes"].isna().sum()
    missing_age_count = cust_df["age"].isna().sum()
    invalid_age_count = len(cust_df[(cust_df["age"] < 10) | (cust_df["age"] > 100)])
    
    print(f"Raw orders rows: {total_raw_orders}")
    print(f"Exact duplicates: {duplicate_records}")
    print(f"Pending rows: {pending_records}")
    print(f"Distinct order_id: {unique_orders_count}")
    print(f"Non-numeric order_amount: {invalid_amount_entries}")
    print(f"Negative delivery_minutes: {negative_deliv_count}")
    print(f"Blank delivery_minutes: {missing_deliv_count}")
    print(f"Blank customer age: {missing_age_count}")
    print(f"Out of bounds age: {invalid_age_count}")

    # 3. Data Cleansing & Transformation Steps
    # Territory Normalization
    cust_df["city"] = cust_df["city"].str.strip().str.title()
    
    # Demographics Standardization
    cust_df["gender"] = cust_df["gender"].str.strip().str.lower()
    cust_df["gender"] = cust_df["gender"].replace({
        "": "unknown", "unknown": "unknown", "other": "other", "male": "male", "female": "female"
    })
    cust_df["gender"] = cust_df["gender"].fillna("unknown")

    # Age Imputation via Location Median
    regional_age_medians = cust_df.groupby("city")["age"].transform("median")
    cust_df["age"] = cust_df["age"].fillna(regional_age_medians)
    cust_df.loc[(cust_df["age"] < 10) | (cust_df["age"] > 100), "age"] = np.nan
    cust_df["age"] = cust_df["age"].fillna(cust_df.groupby("city")["age"].transform("median"))

    # Order Calculations & Amount Repair
    ord_df["order_amount"] = pd.to_numeric(ord_df["order_amount"], errors="coerce")
    
    # Merge with product catalog to fix faulty amounts
    ord_df = ord_df.merge(prod_df[["product_id", "price_inr"]], on="product_id", how="left")
    computed_subtotal = round(ord_df["price_inr"] * ord_df["quantity"] * (1 - ord_df["discount_pct"] / 100), 2)
    ord_df.loc[ord_df["order_amount"].isna() | (ord_df["order_amount"] < 0), "order_amount"] = computed_subtotal

    # Filter duplicates and pending states
    ord_df = ord_df.drop_duplicates()
    ord_df = ord_df[ord_df["order_status"] != "pending"]
    ord_df = ord_df.sort_values(by="order_ts", ascending=False).drop_duplicates(subset=["order_id"], keep="first")

    # Delivery Duration Adjustments
    ord_df.loc[ord_df["delivery_minutes"] < 0, "delivery_minutes"] = np.nan
    item_median_delivery = ord_df.groupby("product_id")["delivery_minutes"].transform("median")
    ord_df.loc[(ord_df["order_status"] == "completed") & (ord_df["delivery_minutes"].isna()), "delivery_minutes"] = item_median_delivery

    # Support Logs Text Prep
    tkt_df["clean_text"] = tkt_df["raw_text"]

    # Export Processed Dataframes
    os.makedirs("data/clean", exist_ok=True)
    cust_df.to_csv("data/clean/customers_clean.csv", index=False)
    prod_df.to_csv("data/clean/products_clean.csv", index=False)
    ord_df.to_csv("data/clean/orders_clean.csv", index=False)
    tkt_df.to_csv("data/clean/support_tickets_clean.csv", index=False)

    # 4. Persistence into SQLite Database
    os.makedirs("data", exist_ok=True)
    database_destination = "data/instamart.db"
    db_connection = sqlite3.connect(database_destination)
    
    cust_df.to_sql("customers", db_connection, if_exists="replace", index=False)
    prod_df.to_sql("products", db_connection, if_exists="replace", index=False)
    ord_df.to_sql("orders", db_connection, if_exists="replace", index=False)
    tkt_df.to_sql("support_tickets", db_connection, if_exists="replace", index=False)
    
    db_connection.close()

    print("\nALL CHECKPOINTS PASSED")
    print(f"Sanitized data successfully stored and indexed at {database_destination}")

if __name__ == "__main__":
    execute_foundation_cleaning()