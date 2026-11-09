import os
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
import joblib

def run_part_b():
    print("Running Part B Customer Segmentation & Lapse Model...")
    os.makedirs("outputs", exist_ok=True)
    
    if not os.path.exists("data/raw/orders.csv") or not os.path.exists("data/raw/customers.csv"):
        raise FileNotFoundError("Run generate_data.py first!")

    orders = pd.read_csv("data/raw/orders.csv")
    customers = pd.read_csv("data/raw/customers.csv")

    # RFM Feature Engineering
    max_date = pd.to_datetime(orders["order_ts"]).max()
    rfm = orders.groupby("customer_id").agg(
        recency=("order_ts", lambda x: (max_date - pd.to_datetime(x).max()).days),
        frequency=("order_id", "count"),
        monetary=("order_amount", "sum")
    ).reset_index()

    # K-Means Segmentation (K=4)
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    rfm["cluster"] = kmeans.fit_predict(rfm[["recency", "frequency", "monetary"]])
    
    cluster_names = {0: "Active Regulars", 1: "High-Value Loyalists", 2: "At-Risk Lapsed", 3: "New Explorers"}
    rfm["segment_name"] = rfm["cluster"].map(cluster_names)
    rfm["is_premium"] = rfm["monetary"] > rfm["monetary"].quantile(0.75)

    segments_out = rfm[["customer_id", "segment_name", "is_premium", "recency", "frequency", "monetary"]]
    segments_out.to_csv("outputs/customer_segments.csv", index=False)

    # Random Forest Lapse Prediction Model
    rfm["is_lapsed"] = (rfm["recency"] > 60).astype(int)
    X = rfm[["recency", "frequency", "monetary"]]
    y = rfm["is_lapsed"]

    model = RandomForestClassifier(random_state=42)
    model.fit(X, y)
    joblib.dump(model, "outputs/lapse_model.joblib")

    rfm["lapse_prob"] = model.predict_proba(X)[:, 1]
    retention_list = rfm.sort_values("lapse_prob", ascending=False).head(100)
    retention_list.to_csv("outputs/retention_list.csv", index=False)

    print("Part B outputs successfully generated in outputs/")

if __name__ == "__main__":
    run_part_b()