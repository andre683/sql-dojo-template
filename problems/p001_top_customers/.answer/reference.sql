SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name           AS full_name,
    SUM(oi.quantity * oi.unit_price_cents)        AS total_revenue_cents,
    COUNT(DISTINCT o.order_id)                    AS order_count
FROM customers c
JOIN orders o      ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id   = oi.order_id
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY c.customer_id, c.first_name, c.last_name
ORDER BY total_revenue_cents DESC
LIMIT 5;
