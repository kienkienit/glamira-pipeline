import argparse
import logging
import subprocess

BUCKET = "gs://glamira-raw-data-asia-southeast1-513516"
LOCATION = "asia-southeast1"

LOADS = {
    "products": {
        "format": "PARQUET",
        "uri": f"{BUCKET}/products/products.parquet",
        "sample_uri": f"{BUCKET}/sample/products/products.parquet",
        "schema": None,
    },
    "ip_locations": {
        "format": "PARQUET",
        "uri": f"{BUCKET}/ip_locations/ip_locations.parquet",
        "sample_uri": f"{BUCKET}/sample/ip_locations/ip_locations.parquet",
        "schema": None,
    },
    "summary": {
        "format": "NEWLINE_DELIMITED_JSON",
        "uri": f"{BUCKET}/summary/parts/*.jsonl.gz",
        "sample_uri": f"{BUCKET}/sample/summary/*.jsonl.gz",
        "schema": "schemas/summary.json",
    },
}


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run(command):
    logging.info("command: %s", " ".join(command))
    subprocess.run(command, check=True)


def load_table(name, sample):
    job = LOADS[name]
    table = f"raw.{name}_sample" if sample else f"raw.{name}"
    uri = job["sample_uri"] if sample else job["uri"]
    command = [
        "bq",
        "load",
        f"--location={LOCATION}",
        "--replace",
        f"--source_format={job['format']}",
        table,
        uri,
    ]
    if job["schema"]:
        command.append(job["schema"])
    run(command)
    run(
        [
            "bq",
            "query",
            "--use_legacy_sql=false",
            f"--location={LOCATION}",
            f"SELECT COUNT(*) AS n FROM {table}",
        ]
    )
    logging.info("loaded %s", table)


def parse_args():
    parser = argparse.ArgumentParser(description="Load GCS files into BigQuery raw tables.")
    parser.add_argument(
        "--tables",
        nargs="+",
        choices=sorted(LOADS),
        default=["products", "ip_locations"],
        help="summary reads gs://.../summary/parts/ and needs those files uploaded first.",
    )
    parser.add_argument("--sample", action="store_true", help="Load the sample/ prefix into *_sample tables.")
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    failures = []
    for name in args.tables:
        try:
            load_table(name, args.sample)
        except Exception:
            logging.exception("failed: %s", name)
            failures.append(name)
    if failures:
        raise SystemExit(f"failed tables: {', '.join(failures)}")
    logging.info("load finished")
