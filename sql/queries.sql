-- 1. Total Revenue and Order Metrics by Category
SELECT 
    p.category,
    COUNT(o.order_id) AS total_orders_fulfilled,
    SUM(o.quantity) AS units_sold,
    ROUND(SUM(o.order_amount), 2) AS total_revenue_inr,
    ROUND(AVG(o.order_amount), 2) AS average_order_value
FROM orders o
JOIN products p ON o.product_id = p.product_id
WHERE o.order_status = 'completed'
GROUP BY p.category
ORDER BY total_revenue_inr DESC;

-- 2. Customer Demographics & Purchasing Patterns by City
SELECT 
    c.city,
    COUNT(DISTINCT c.customer_id) AS registered_customers,
    ROUND(AVG(c.age), 1) AS median_or_avg_age,
    COUNT(o.order_id) AS total_orders_placed
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.city
ORDER BY total_orders_placed DESC;

-- 3. Support Ticket Volume Distribution by Issue Type
SELECT 
    issue_type,
    COUNT(ticket_id) AS total_tickets_logged
FROM support_tickets
GROUP BY issue_type
ORDER BY total_tickets_logged DESC;

-- 4. High-Value Orders Analysis (Top 10 by Order Amount)
SELECT 
    order_id,
    customer_id,
    product_id,
    quantity,
    discount_pct,
    order_amount,
    order_ts
FROM orders
WHERE order_status = 'completed'
ORDER BY order_amount DESC
LIMIT 10;

-- 5. Delivery Performance Summary (Average Delivery Time in Minutes by Product Category)
SELECT 
    p.category,
    ROUND(AVG(o.delivery_minutes), 1) AS avg_delivery_time_mins,
    COUNT(o.order_id) AS completed_deliveries_count
FROM orders o
JOIN products p ON o.product_id = p.product_id
WHERE o.order_status = 'completed' AND o.delivery_minutes IS NOT NULL
GROUP BY p.category
ORDER BY avg_delivery_time_mins ASC;