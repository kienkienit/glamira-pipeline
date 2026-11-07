# Data Dictionary - Glamira Analytics

Database: `countly` on local MongoDB at `127.0.0.1:27017`.

The source is Countly events from 1 April 2020 through 4 June 2020. The collections below were built in Phase 2. Types describe the stored values, not the sample table in the course notes. The notes use `event_id` and `order_amount`. Those fields are not in the data.

## Collection: summary

41,432,473 raw events. Each document is one event. An event does not carry every field below. A field appears only on the event types that use it.

Indexes: `time_stamp_-1`, `device_id_1`.

### Fields on most events

| Field | Type | Nullable | Description | Example |
| --- | --- | --- | --- | --- |
| `_id` | OBJECTID | No | Event key | `5eb3e92466936336ee913e5e` |
| `collection` | STRING | No | Event type | `view_product_detail` |
| `time_stamp` | INTEGER | No | Event time, Unix seconds, UTC | `1588848933` |
| `local_time` | STRING | Yes | Local time as text | `2020-05-07 5:55:24` |
| `ip` | STRING | Yes | Session IP address | `171.253.137.149` |
| `store_id` | STRING | Yes | Glamira store id | `54` |
| `device_id` | STRING | Yes | Device id | `1ce40e16-770c-4e42-b4d3-0b2bd1426d75` |
| `user_id_db` | STRING | Yes | Logged-in user id. Often an empty string | `""` |
| `email_address` | STRING | Yes | Email. Often an empty string | `""` |
| `api_version` | STRING | Yes | Countly API version | `1.0` |
| `resolution` | STRING | Yes | Screen resolution | `412x892` |
| `user_agent` | STRING | Yes | Browser string | `Mozilla/5.0 ...` |
| `current_url` | STRING | Yes | URL being viewed | `https://www.glamira.vn/...html` |
| `referrer_url` | STRING | Yes | Previous URL | `https://www.glamira.vn/...` |
| `show_recommendation` | STRING | Yes | Recommendation flag, stored as text | `true` |

### Fields on some event types

| Field | Type | Event types | Description |
| --- | --- | --- | --- |
| `product_id` | STRING | Product view, option selection, add to cart, view-all recommendations | Product id as text |
| `option` | ARRAY | Product view, option selection, listing pages | Selected options. Each item has `option_label`, `option_id`, `value_label`, `value_id` |
| `viewing_product_id` | STRING | Recommendations on a product page | Product being viewed when the recommendation appeared |
| `recommendation_product_id` | STRING | Recommendation click | Product clicked inside the recommendation block |
| `recommendation_clicked_position` | STRING | Recommendation click | Position of the clicked product |
| `recommendation_product_position` | STRING | Recommendation click | Position of the product in the recommendation list |
| `cat_id` | STRING | Listing pages | Category id of the listing page |
| `collect_id` | STRING | Listing pages | Collection id of the listing page |
| `key_search` | STRING | `search_box_action` | Search text |
| `price` | STRING | `add_to_cart_action` | Price at add-to-cart time. A string, with more than one number format |
| `currency` | STRING | `add_to_cart_action` | Currency symbol or code |
| `is_paypal` | STRING | `add_to_cart_action` | PayPal flag |
| `utm_source` | STRING or BOOLEAN | `view_product_detail` | UTM source. Some documents store `false` |
| `utm_medium` | STRING or BOOLEAN | `view_product_detail` | UTM medium. Some documents store `false` |
| `recommendation` | BOOLEAN | `view_product_detail` | Whether the event came from a recommendation block |
| `order_id` | STRING or INTEGER | `checkout`, `checkout_success` | Order id. In the 10,000-row sample every `checkout` value is an empty string. `checkout_success` stores a number |
| `cart_products` | ARRAY | `view_shopping_cart`, `checkout`, `checkout_success` | Products in the cart or the order |

Each `cart_products` item:

| Field | Type | Description | Example |
| --- | --- | --- | --- |
| `product_id` | INTEGER | Product id. A number here, unlike the string `product_id` on product-view events | `90273` |
| `amount` | INTEGER | Quantity | `1` |
| `price` | STRING | Unit price as text | `189.00` |
| `currency` | STRING | Currency for this line | `£` |
| `option` | ARRAY | Selected options, same shape as `option` on a product-view event | `alloy`, `diamond` |

The 10,000-row sample contains 26 event types: `view_listing_page`, `view_product_detail`, `select_product_option`, `select_product_option_quality`, `view_static_page`, `view_landing_page`, `product_detail_recommendation_visible`, `view_home_page`, `listing_page_recommendation_visible`, `product_detail_recommendation_noticed`, `landing_page_recommendation_visible`, `view_shopping_cart`, `search_box_action`, `product_detail_recommendation_clicked`, `add_to_cart_action`, `view_my_account`, `checkout`, `landing_page_recommendation_noticed`, `listing_page_recommendation_noticed`, `view_all_recommend`, `landing_page_recommendation_clicked`, `checkout_success`, `product_view_all_recommend_clicked`, `view_sorting_relevance`, `listing_page_recommendation_clicked`, `sorting_relevance_click_action`.

`back_to_product_action` is not in that sample.

## Collection: ip_locations

3,239,628 distinct IPs, looked up in IP2Location LITE DB5. One document per IP. Unique index: `ip_1`.

CSV copy: `data/ip_locations.csv` (not committed).

| Field | Type | Nullable | Description | Example |
| --- | --- | --- | --- | --- |
| `ip` | STRING | No | IP address | `1.1.1.1` |
| `country_name` | STRING | Yes | Country name | `Australia` |
| `region_name` | STRING | Yes | Region, state, or province | `Queensland` |
| `city_name` | STRING | Yes | City name | `Brisbane` |
| `latitude` | STRING | Yes | Latitude returned by DB5, stored as text | `-27.467541` |
| `longitude` | STRING | Yes | Longitude returned by DB5, stored as text | `153.028091` |

3,236,823 IPs have `region_name`. 2,805 IPs do not.

## Collection: product_urls

12,411,699 `(product_id, url)` pairs taken from events that carry a product URL. 19,417 distinct `product_id` values. Unique index: `product_id_1_url_1`.

One product has many URLs because of query strings (`alloy`, `diamond`) and because the same product appears on many domains.

| Field | Type | Nullable | Description | Example |
| --- | --- | --- | --- | --- |
| `product_id` | STRING | No | Product id | `91062` |
| `url` | STRING | No | URL seen on the event | `https://www.glamira.vn/nhan-glamira-alfrida-0.1-crt.html?...` |

## Collection: products

18,655 products, one document per `product_id`. Unique index: `product_id_1`.

CSV copy: `data/products.csv` (not committed).

The crawl stores one page per id. It tries `www.glamira.com`, `www.glamira.co.uk`, `www.glamira.com.ph`, then `www.glamira.vn`. A page with a product name is saved. When the page has no category, `category` is null. Homepage labels (`Home`, `Trang chủ`, `Pagina Iniziale`, and the other labels in `crawl_products.py`) are not stored in `category`.

| Field | Type | Nullable | Description | Example |
| --- | --- | --- | --- | --- |
| `product_id` | STRING | No | Product id | `90527` |
| `product_name` | STRING | No | Name on the page | `Men's Wedding Ring Immortal Love` |
| `category` | STRING | Yes | Category from the breadcrumb. Null when the page has no category | `Men’s Wedding Rings` |
| `price` | STRING | Yes | Price from the meta tag, without a currency | `4768` |
| `description` | STRING | Yes | Open Graph description. May still contain HTML entities | `Buy White Silver Men&#039;s Wedding Ring...` |
| `image_url` | STRING | Yes | Open Graph image | `https://cdn-media.glamira.com/...` |
| `source_url` | STRING | No | URL that was crawled | `https://www.glamira.ae/men-s-ring-immortal-love.html?...` |
| `crawled_at` | STRING | No | Crawl time, ISO 8601 UTC | `2026-11-04T11:36:58.514778+00:00` |
| `status_code` | INTEGER | No | HTTP status of the saved page | `200` |

13,989 products have a category. 4,666 products have `category` null.

## Collection: product_catalog_misses

762 `product_id` values that were tried on all four domains and had no product page. Unique index: `product_id_1`.

18,655 saved products plus these 762 ids equal the 19,417 ids in `product_urls`.

| Field | Type | Nullable | Description | Example |
| --- | --- | --- | --- | --- |
| `product_id` | STRING | No | Id with no product page | `100111` |
| `reason` | STRING | Yes | Why it was skipped. Most values are `not_found`. 16 older documents do not have this field | `not_found` |
| `checked_at` | STRING | No | Check time, ISO 8601 UTC | `2026-11-05T13:59:41.026421+00:00` |

## Known data quality issues

- Many `summary` columns are more than 50% empty because the field belongs to one event type, not because the value was lost.
- The 10,000-row sample has no duplicate `_id` and no duplicate (`ip`, `time_stamp`) pair.
- The sample has no future dates.
- In the sample, `checkout.order_id` is an empty string on all 23 rows. `checkout_success` is the event with an order id.
- `price` is a string with several formats (`324,00`, `1,097.00`, `54.222,00`). It cannot be parsed as a number until comma and dot rules are fixed.
- `currency` mixes symbols and codes: €, £, $, CLP, kr, CAD $, RON, ZAR, ₫. Revenue cannot be compared across countries until it is converted.
- The `add_to_cart_action` price is the `price` field. The order price is inside `cart_products`. Read those separately.
- `product_id` on an event is a string. `product_id` inside `cart_products` is a number.
- The 10,000-row sample has 9,998 IPv4 addresses and 2 IPv6 addresses. DB5 can look up IPv4 only, so IPv6 addresses have no location.
- 2,805 IPs have no `region_name`.
- 4,666 products have a name and a null `category`.
- 762 product ids have no page on `.com`, `.co.uk`, `.com.ph`, or `.vn`.
- `products.price` has no currency. `products.description` can still contain HTML entities.
