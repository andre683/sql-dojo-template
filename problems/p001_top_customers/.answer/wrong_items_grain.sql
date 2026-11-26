-- Classic mistake: counting order_item rows instead of distinct orders.
-- Revenue is correct but order_count is inflated for multi-item orders.

SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name           AS full_name,
    SUM(oi.quantity * oi.unit_price_cents)        AS total_revenue_cents,
    COUNT(oi.order_item_id)                       AS order_count   -- should be COUNT(DISTINCT o.order_id)
FROM customers c
JOIN orders o       ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id    = oi.order_id
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY c.customer_id, c.first_name, c.last_name
ORDER BY total_revenue_cents DESC
LIMIT 5;
