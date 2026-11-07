import csv
from pathlib import Path

import IP2Location
from pymongo import MongoClient, UpdateOne

BIN_PATH = Path("data/IP2LOCATION-LITE-DB5.BIN")
CSV_PATH = Path("data/ip_locations.csv")
FAILED = {"", "-", "INVALID IP ADDRESS", "IPV6 ADDRESS MISSING IN IPV4 BIN"}


def is_located(record):
    return (record.country_long or "") not in FAILED


def clean(value):
    return None if value in FAILED else value


def main():
    geo = IP2Location.IP2Location(str(BIN_PATH))
    database = MongoClient("mongodb://127.0.0.1:27017").countly
    locations = database.ip_locations
    locations.create_index("ip", unique=True, name="ip_1")

    print("Collecting distinct IPs. This reads all 41 million events.", flush=True)
    groups = database.summary.aggregate(
        [{"$group": {"_id": "$ip", "events": {"$sum": 1}}}],
        allowDiskUse=True,
    )

    total_events = 0
    located_events = 0
    unique_ips = 0
    batch = []
    printed_at = 0

    with CSV_PATH.open("w", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["ip", "country_name", "region_name", "city_name", "latitude", "longitude"],
        )
        writer.writeheader()

        for group in groups:
            ip = group["_id"] or ""
            events = group["events"]
            total_events += events
            unique_ips += 1

            if ip:
                record = geo.get_all(ip)
                located = is_located(record)
            else:
                record = None
                located = False

            if located:
                located_events += events
                row = {
                    "ip": ip,
                    "country_name": record.country_long,
                    "region_name": clean(record.region),
                    "city_name": clean(record.city),
                    "latitude": record.latitude,
                    "longitude": record.longitude,
                }
            else:
                row = {
                    "ip": ip,
                    "country_name": None,
                    "region_name": None,
                    "city_name": None,
                    "latitude": None,
                    "longitude": None,
                }

            writer.writerow(row)
            batch.append(UpdateOne({"ip": ip}, {"$set": row}, upsert=True))
            if len(batch) >= 2000:
                locations.bulk_write(batch, ordered=False)
                batch = []

            if unique_ips // 100000 != printed_at:
                printed_at = unique_ips // 100000
                print(f"processed {unique_ips:,} IPs", flush=True)

        if batch:
            locations.bulk_write(batch, ordered=False)

    coverage = located_events / total_events * 100
    print(f"unique IP: {unique_ips:,}", flush=True)
    print(f"ip_locations: {locations.count_documents({})}", flush=True)
    print(f"coverage: {coverage:.2f}%", flush=True)
    print(f"CSV: {CSV_PATH.resolve()}", flush=True)


if __name__ == "__main__":
    main()