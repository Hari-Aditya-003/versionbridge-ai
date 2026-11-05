SELECT c.id, COUNT(*) AS paid_orders, COALESCE(SUM(o.cents), 0) AS total_cents
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.id AND o.status = 'paid'
GROUP BY c.id
ORDER BY c.id
