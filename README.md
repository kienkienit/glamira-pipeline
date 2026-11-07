# Glamira analytics pipeline

Local pipeline for the Glamira Countly dump: explore the raw events, geolocate IP addresses, and crawl product pages. MongoDB database: `countly` at `127.0.0.1:27017`.

`data/` is not in git. It holds the IP2Location BIN file, the 10k sample, CSV exports, and the crawl log.

## Phase 0 — Investigation

| File | Result |
| --- | --- |
| `data_exploration.py` | Profile of `data/sample_10k.jsonl` |
| `data_quality_assessment.py` | Nulls, duplicates, future dates, currency, IP shape, empty checkout order ids |
| `data_quality_report.md` | Findings from the 10,000-row sample |
| `scope_confirmation.md` | GO. IP location, product crawl, and the full 41,432,473 events |

## Phase 1 — Infrastructure

GCP project, Cloud Storage bucket, and a MongoDB VM were used to load the BSON dump. The working copy for later steps is the local MongoDB database. There is no loader script in this repo; the restore was run with `mongorestore` on the VM.

## Phase 2 — Enrichment

| File | Result |
| --- | --- |
| `enrich_ip_locations.py` | `ip_locations`: 3,239,628 IPs, including `region_name` |
| `extract_product_urls.py` | `product_urls`: 12,411,699 pairs and 19,417 product ids |
| `crawl_products.py` | `products`: 18,655 rows. 4,666 have a null category. 762 ids were not found |
| `data_dictionary.md` | Fields for `summary`, `ip_locations`, `product_urls`, `products`, and `product_catalog_misses` |

Product crawl order is `www.glamira.com`, `www.glamira.co.uk`, `www.glamira.com.ph`, then `www.glamira.vn`. A homepage breadcrumb is not stored as a category.

## Setup

```bash
uv sync
```

Place `IP2LOCATION-LITE-DB5.BIN` at `data/IP2LOCATION-LITE-DB5.BIN` before running the IP job. Place `data/sample_10k.jsonl` before the Phase 0 scripts.

```bash
uv run python data_exploration.py
uv run python data_quality_assessment.py
uv run python enrich_ip_locations.py
uv run python extract_product_urls.py
uv run python crawl_products.py
```
