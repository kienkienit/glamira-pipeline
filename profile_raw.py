import json
import logging
import subprocess

LOCATION = "asia-southeast1"
TABLES = ["products", "ip_locations", "summary"]
SUMMARY_DISTINCT = ["_id", "collection", "ip", "product_id", "store_id", "device_id"]


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def query(sql):
    logging.info("query started")
    completed = subprocess.run(
        [
            "bq",
            "query",
            "--use_legacy_sql=false",
            f"--location={LOCATION}",
            "--format=prettyjson",
            sql,
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        logging.error(completed.stderr.rstrip())
        raise RuntimeError("BigQuery query failed")
    return json.loads(completed.stdout)


def quote(field_path):
    return ".".join(f"`{part}`" for part in field_path.split("."))


def alias(name, suffix):
    text = f"{name}_{suffix}"
    if text[0] == "_":
        return f"`{text}`"
    return text


def column_list():
    rows = query(
        """
        SELECT table_name, field_path, data_type
        FROM raw.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS
        WHERE table_name IN ('products', 'ip_locations', 'summary')
        ORDER BY table_name, field_path
        """
    )
    print("\n=== Columns ===")
    current = None
    for row in rows:
        if row["table_name"] != current:
            current = row["table_name"]
            print(f"\n{current}")
        print(f"  {row['field_path']}: {row['data_type']}")
    return rows


def profile_table(table, fields):
    top_level = [field for field in fields if "." not in field["field_path"]]
    expressions = ["COUNT(*) AS row_count"]
    for field in top_level:
        name = field["field_path"]
        column = quote(name)
        if field["data_type"].startswith("ARRAY"):
            expressions.append(f"COUNTIF(ARRAY_LENGTH({column}) = 0) AS {alias(name, 'empty')}")
        else:
            expressions.append(f"COUNTIF({column} IS NULL) AS {alias(name, 'null')}")
    if table == "summary":
        expressions.append("MIN(time_stamp) AS time_stamp_min")
        expressions.append("MAX(time_stamp) AS time_stamp_max")
        for name in SUMMARY_DISTINCT:
            expressions.append(f"APPROX_COUNT_DISTINCT({quote(name)}) AS {alias(name, 'distinct')}")
    elif table == "products":
        expressions.append("APPROX_COUNT_DISTINCT(product_id) AS product_id_distinct")
        expressions.append("APPROX_COUNT_DISTINCT(category) AS category_distinct")
    elif table == "ip_locations":
        expressions.append("APPROX_COUNT_DISTINCT(ip) AS ip_distinct")
        expressions.append("APPROX_COUNT_DISTINCT(country_name) AS country_distinct")

    rows = query(f"SELECT {', '.join(expressions)} FROM raw.{table}")
    print(f"\n=== {table} ===")
    for key, value in rows[0].items():
        print(f"  {key}: {value}")


def relationships():
    rows = query(
        """
        SELECT
          COUNTIF(
            s.ip IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM raw.ip_locations i WHERE i.ip = s.ip)
          ) AS ip_missing_from_locations,
          COUNTIF(
            s.product_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM raw.products p WHERE p.product_id = s.product_id)
          ) AS product_id_missing_from_products
        FROM raw.summary AS s
        """
    )
    print("\n=== Relationships ===")
    for key, value in rows[0].items():
        print(f"  {key}: {value}")


def main():
    fields = column_list()
    by_table = {table: [] for table in TABLES}
    for field in fields:
        by_table[field["table_name"]].append(field)
    for table in TABLES:
        profile_table(table, by_table[table])
    relationships()
    logging.info("profile finished")


if __name__ == "__main__":
    setup_logging()
    try:
        main()
    except Exception:
        logging.exception("profile stopped")
        raise SystemExit(1)
