from pathlib import Path

import pandas as pd

sample_path = Path(__file__).resolve().parent / "data" / "sample_10k.jsonl"
df = pd.read_json(sample_path, lines=True)

print("=== 1. Shape (rows, columns) ===")
print(df.shape)

print("\n=== 2. Column dtypes ===")
print(df.dtypes)

print("\n=== 3. First five rows ===")
preview_columns = ["collection", "local_time", "store_id", "product_id", "order_id"]
print(df[preview_columns].head(5))

print("\n=== 4. Rows by event type ===")
counts = df["collection"].value_counts(dropna=False)
print(f"Event types: {len(counts)}")
print(counts)

print("\n=== 5. Time range ===")
timestamps = pd.to_numeric(df["time_stamp"], errors="coerce")
print("min:", pd.to_datetime(timestamps.min(), unit="s", utc=True))
print("max:", pd.to_datetime(timestamps.max(), unit="s", utc=True))

print("\n=== 6. Distinct IP addresses ===")
print(df["ip"].nunique(dropna=True))

print("\n=== 7. Null rate by event type ===")
for event_type, subset in df.groupby("collection"):
    print(f"\n{event_type} ({len(subset)} rows)")
    for column in ["product_id", "order_id", "ip"]:
        if column not in subset.columns:
            print(f"  {column}: column missing")
            continue
        null_percent = subset[column].isna().mean() * 100
        print(f"  {column}: {null_percent:.1f}% null")