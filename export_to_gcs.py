import argparse
import gzip
import json
import logging
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pymongo import MongoClient

MONGO_URI = "mongodb://127.0.0.1:27017"
BUCKET = "gs://glamira-raw-data-asia-southeast1-513516"
PART_BYTES = 2_000_000_000
BATCH_SIZE = 5000

PRODUCT_FIELDS = [
    "product_id",
    "product_name",
    "category",
    "price",
    "description",
    "image_url",
    "source_url",
    "crawled_at",
    "status_code",
]
PRODUCT_SCHEMA = pa.schema(
    [
        ("product_id", pa.string()),
        ("product_name", pa.string()),
        ("category", pa.string()),
        ("price", pa.string()),
        ("description", pa.string()),
        ("image_url", pa.string()),
        ("source_url", pa.string()),
        ("crawled_at", pa.string()),
        ("status_code", pa.int64()),
    ]
)
IP_FIELDS = [
    "ip",
    "country_name",
    "region_name",
    "city_name",
    "latitude",
    "longitude",
]
IP_SCHEMA = pa.schema([(field, pa.string()) for field in IP_FIELDS])


def setup_logging():
    Path("data").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("data/pipeline.log"),
        ],
    )


def run(command):
    logging.info("command: %s", " ".join(command))
    subprocess.run(command, check=True)


def gcs_uri(*parts):
    return "/".join([BUCKET, *parts])


def upload_file(local_path, uri):
    logging.info("upload %s (%s bytes)", local_path, local_path.stat().st_size)
    run(["gcloud", "storage", "cp", str(local_path), uri])
    logging.info("uploaded %s", uri)


def connect():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    logging.info("connected to %s", MONGO_URI)
    return client


def export_parquet(database, collection, fields, schema, destination, limit):
    projection = {field: 1 for field in fields}
    projection["_id"] = 0
    cursor = database[collection].find({}, projection).batch_size(BATCH_SIZE)
    if limit is not None:
        cursor = cursor.limit(limit)

    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    total = 0
    batch = []

    def write_batch():
        nonlocal writer, total
        rows = [{field: doc.get(field) for field in fields} for doc in batch]
        table = pa.Table.from_pylist(rows, schema=schema)
        if writer is None:
            writer = pq.ParquetWriter(destination, schema)
        writer.write_table(table)
        total += len(rows)
        if total % 500000 == 0:
            logging.info("%s exported %s rows", collection, total)

    for doc in cursor:
        batch.append(doc)
        if len(batch) == BATCH_SIZE:
            write_batch()
            batch = []
    if batch:
        write_batch()
    if writer is None:
        logging.info("%s has no rows", collection)
        return None
    writer.close()
    logging.info("%s done %s rows %s bytes", collection, total, destination.stat().st_size)
    return destination


def export_summary(database, destination, limit):
    destination.mkdir(parents=True, exist_ok=True)
    for old_part in destination.glob("summary-*.jsonl.gz"):
        old_part.unlink()

    cursor = database.summary.find({}).batch_size(2000)
    if limit is not None:
        cursor = cursor.limit(limit)

    part = 0
    total = 0
    path = destination / f"summary-{part:02d}.jsonl.gz"
    outfile = gzip.open(path, "wt")
    try:
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            outfile.write(json.dumps(doc, default=str))
            outfile.write("\n")
            total += 1
            if total % 500000 == 0:
                outfile.flush()
                logging.info("summary exported %s rows %s bytes", total, path.stat().st_size)
                if path.stat().st_size >= PART_BYTES:
                    outfile.close()
                    part += 1
                    path = destination / f"summary-{part:02d}.jsonl.gz"
                    outfile = gzip.open(path, "wt")
    finally:
        outfile.close()

    if path.exists() and path.stat().st_size == 0:
        path.unlink()

    parts = sorted(destination.glob("summary-*.jsonl.gz"))
    logging.info("summary done %s rows %s files", total, len(parts))
    for item in parts:
        logging.info("%s %s bytes", item.name, item.stat().st_size)
    return parts


def upload_existing_summary_parts():
    parts = sorted(Path("data/summary_parts").glob("summary-*.jsonl.gz"))
    if not parts:
        raise FileNotFoundError("data/summary_parts has no summary-*.jsonl.gz files")
    for part in parts:
        if part.stat().st_size >= 4294967296:
            raise RuntimeError(f"{part} is still at least 4 GB")
        upload_file(part, gcs_uri("summary", "parts", part.name))
    logging.info("uploaded %s existing summary parts", len(parts))


def export_to_gcs(limit=None, collections=None, upload=True):
    selected = collections or ["summary", "ip_locations", "products"]
    local_root = Path("data/sample_export") if limit is not None else Path("data")
    prefix = ["sample"] if limit is not None else []
    client = connect()
    database = client.countly
    failures = []

    jobs = []
    if "products" in selected:
        jobs.append(
            (
                "products",
                lambda: export_parquet(
                    database,
                    "products",
                    PRODUCT_FIELDS,
                    PRODUCT_SCHEMA,
                    local_root / "products" / "products.parquet",
                    limit,
                ),
                lambda path: path and upload_file(path, gcs_uri(*prefix, "products", "products.parquet")),
            )
        )
    if "ip_locations" in selected:
        jobs.append(
            (
                "ip_locations",
                lambda: export_parquet(
                    database,
                    "ip_locations",
                    IP_FIELDS,
                    IP_SCHEMA,
                    local_root / "ip_locations" / "ip_locations.parquet",
                    limit,
                ),
                lambda path: path
                and upload_file(path, gcs_uri(*prefix, "ip_locations", "ip_locations.parquet")),
            )
        )
    if "summary" in selected:
        jobs.append(
            (
                "summary",
                lambda: export_summary(database, local_root / "summary", limit),
                lambda paths: [
                    upload_file(
                        path,
                        gcs_uri("sample", "summary", path.name)
                        if prefix
                        else gcs_uri("summary", "parts", path.name),
                    )
                    for path in paths
                ],
            )
        )

    for name, export, send in jobs:
        try:
            paths = export()
            if upload:
                send(paths)
        except Exception:
            logging.exception("failed: %s", name)
            failures.append(name)

    client.close()
    if failures:
        raise SystemExit(f"failed collections: {', '.join(failures)}")
    logging.info("export finished")


def parse_args():
    parser = argparse.ArgumentParser(description="Export MongoDB collections to Cloud Storage.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--limit", type=int, help="Export this many rows from each collection.")
    mode.add_argument("--full", action="store_true", help="Export every row. Reads 41 million events.")
    mode.add_argument(
        "--upload-existing-summary",
        action="store_true",
        help="Upload data/summary_parts. Does not read MongoDB.",
    )
    parser.add_argument(
        "--collections",
        nargs="+",
        choices=["summary", "ip_locations", "products"],
        default=["summary", "ip_locations", "products"],
    )
    parser.add_argument("--no-upload", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    try:
        if args.upload_existing_summary:
            upload_existing_summary_parts()
        else:
            export_to_gcs(
                limit=None if args.full else args.limit,
                collections=args.collections,
                upload=not args.no_upload,
            )
    except Exception:
        logging.exception("export stopped")
        raise SystemExit(1)
