from pathlib import Path
import re

import pandas as pd

sample_path = Path(__file__).resolve().parent / "data" / "sample_10k.jsonl"
df = pd.read_json(sample_path, lines=True)

print("=== 1. Columns more than 50% null ===")
null_rate = df.isna().mean().sort_values(ascending=False)
flagged = null_rate[null_rate > 0.5]
print(flagged.map(lambda rate: f"{rate:.1%}").to_string())

print("\n=== 2. Duplicate _id rows ===")
print("Duplicate _id count:", int(df["_id"].duplicated().sum()))

print("\n=== 3. Duplicate (ip, time_stamp) pairs ===")
print("Duplicate pair count:", int(df.duplicated(subset=["ip", "time_stamp"]).sum()))

print("\n=== 4. Future dates ===")
timestamps = pd.to_datetime(df["time_stamp"], unit="s", utc=True)
print("Rows with time_stamp in the future:", int((timestamps > pd.Timestamp.now(tz="UTC")).sum()))

print("\n=== 5. Values in currency ===")
print(df["currency"].value_counts(dropna=False).to_string())

print("\n=== 6. IP addresses shaped like a.b.c.d ===")
ip_text = df["ip"].astype(str)
pattern = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
valid_ip = ip_text.map(lambda value: bool(pattern.match(value)))
print(f"IPv4-shaped addresses: {int(valid_ip.sum())} / {len(df)}")

print("\n=== 7. Empty order_id on checkout ===")
checkout = df[df["collection"] == "checkout"]
empty_order_id = checkout["order_id"].fillna("").astype(str).str.strip().eq("")
print(f"checkout: {int(empty_order_id.sum())} / {len(checkout)} empty order_id")