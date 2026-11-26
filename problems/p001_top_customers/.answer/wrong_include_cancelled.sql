-- Classic mistake: forgetting to exclude cancelled and refunded orders.
-- The trap customer (Victor Trap) has $10 000 in cancelled orders,
-- which pushes them into the top 5 here but not in the correct answer.

SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name           AS full_name,
    SUM(oi.quantity * oi.unit_price_cents)        AS total_revenue_cents,
    COUNT(DISTINCT o.order_id)                    AS order_count
FROM customers c
JOIN orders o       ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id    = oi.order_id
GROUP BY c.customer_id, c.first_name, c.last_name
ORDER BY total_revenue_cents DESC
LIMIT 5;
