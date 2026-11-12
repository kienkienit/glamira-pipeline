import json
import logging
from pathlib import Path

from google.cloud import bigquery

PROJECT = "glamira-analytics-513516"
DATASET = "raw"
LOCATION = "asia-southeast1"
SCHEMA_PATH = Path(__file__).parent / "schemas" / "summary.json"


def load_summary_schema():
    fields = json.loads(SCHEMA_PATH.read_text())
    return [bigquery.SchemaField.from_api_repr(field) for field in fields]


SUMMARY_SCHEMA = load_summary_schema()


def route_for(name):
    if name.startswith("sample/"):
        return None
    if name.startswith("products/") and name.endswith(".parquet"):
        return {"table": "products", "format": bigquery.SourceFormat.PARQUET, "disposition": "WRITE_TRUNCATE"}
    if name.startswith("ip_locations/") and name.endswith(".parquet"):
        return {"table": "ip_locations", "format": bigquery.SourceFormat.PARQUET, "disposition": "WRITE_TRUNCATE"}
    if name.startswith("summary/parts/") and name.endswith(".jsonl.gz"):
        return {
            "table": "summary",
            "format": bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            "disposition": "WRITE_APPEND",
            "schema": SUMMARY_SCHEMA,
        }
    return None


def trigger_bigquery_load(event, context):
    bucket = event["bucket"]
    name = event["name"]
    uri = f"gs://{bucket}/{name}"
    logging.info("new file %s event %s", uri, getattr(context, "event_id", None))

    route = route_for(name)
    if route is None:
        logging.info("ignored %s", uri)
        return

    job_config = bigquery.LoadJobConfig(
        source_format=route["format"],
        write_disposition=route["disposition"],
    )
    if "schema" in route:
        job_config.schema = route["schema"]

    table = f"{PROJECT}.{DATASET}.{route['table']}"
    client = bigquery.Client(project=PROJECT, location=LOCATION)
    job = client.load_table_from_uri(uri, table, job_config=job_config)
    logging.info("started job %s for %s into %s", job.job_id, uri, table)
