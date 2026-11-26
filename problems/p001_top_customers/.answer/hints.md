# Hints for p001

## Level 1 — nudge

You need revenue from orders, but not all orders should count.
Check the `status` column in the `orders` table — what values are there?

## Level 2 — approach

You need three tables: `customers`, `orders`, and `order_items`.
The revenue lives in `order_items` (quantity × unit_price_cents).
Filter out orders where `status IN ('cancelled', 'refunded')` before aggregating.

## Level 3 — skeleton

```sql
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name  AS full_name,
    SUM(___)                             AS total_revenue_cents,
    COUNT(DISTINCT ___)                  AS order_count
FROM customers c
JOIN orders o      ON ___
JOIN order_items oi ON ___
WHERE o.status NOT IN (___)
GROUP BY ___
ORDER BY total_revenue_cents DESC
LIMIT 5;
```
