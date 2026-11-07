# Scope Confirmation — Glamira Project 05

## Question 1: Is IP location required?

- Dashboard needs "Revenue by country/region": YES
- IP location available in the raw data: NO. The stored field is `ip`. There is no `country` or `city`
- Decision: BUILD
- Reason: A geographic dashboard needs country and city names. The 10,000-row sample has `ip` on every event, including `checkout_success`. Lookups use IP2Location. The two IPv6 rows in the sample have to be handled separately.

## Question 2: Is product crawling required?

- Dashboard needs product category and name: YES
- Product info available in the raw events: NO. `view_product_detail` has `product_id` and `current_url`, not `product_name` or `category`
- Decision: BUILD
- Reason: The product dashboard needs a name and a category. Pages are crawled from `product_id` and URL pairs. The course estimate is about 8 hours, with a 100-product test before the full crawl.

## Question 3: How much data should be loaded?

- Full 41M rows: needs a VM and MongoDB
- Sample of 100K rows: could go straight to BigQuery
- Decision: FULL
- Reason: The 10,000-row sample has only 4 `checkout_success` events and no `back_to_product_action`. Revenue by country and by category needs the full period from 1 April 2020 through 4 June 2020.

## GO / NO-GO decision

- [x] GO: Proceed to Phase 1 infrastructure
- Confirmed scope: IP=YES, Products=YES, Full data=YES
