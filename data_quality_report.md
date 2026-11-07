# Data Quality Report — 10,000-row sample

Source: `data/sample_10k.jsonl`, a random draw from `countly.summary`.
This is a sample, not a conclusion for all 41 million rows.

## Summary

| Check | Result | Action needed |
| --- | --- | --- |
| Columns more than 50% null | 14 columns | Separate fields that do not belong to an event type from true nulls |
| Duplicate `_id` | 0 rows | None |
| Duplicate (`ip`, `time_stamp`) pair | 0 rows | None |
| Future dates | 0 rows | None |
| Empty `order_id` on `checkout` | 23 / 23 rows | Yes — the checkout step has no order id yet |
| IP shaped like `a.b.c.d` | 9998 / 10000 | Yes — 2 rows are IPv6 |
| Many currencies | €, £, $, CLP, kr, CAD $, RON, ZAR, ₫ | Yes — convert before comparing revenue |

## Key findings

- `_id` is the key of each event. The sample has no duplicate `_id`.
- `ip` is present on every sample row. 9,998 values are IPv4. 2 values are IPv6.
- `checkout.order_id` is present, but all 23 sample rows are empty strings. `checkout_success` is the event that carries a numeric order id.
- `price` is a string, written in more than one way (`324,00`, `1,097.00`, `54.222,00`). Negative prices cannot be checked until the number format is fixed.
- `currency` mixes symbols and currency codes.

## Risks for the full 41 million rows

- Rare event types, such as `checkout_success`, are too scarce in a 10,000-row sample to estimate their rate.
- `back_to_product_action` does not appear in this sample.
- Price and currency sit on the event for `add_to_cart_action`, and inside `cart_products` for orders. Those two places must be read separately.
