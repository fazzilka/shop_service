-- 1) Сумма заказанных товаров по каждому клиенту (имя клиента, сумма)
-- Примечание: учитываем только заказы со статусом 'placed'; при необходимости уберите фильтр.
SELECT c.name AS client,
       SUM(oi.quantity * oi.price_per_unit) AS total_amount
FROM orders o
JOIN clients c ON c.id = o.client_id
JOIN order_items oi ON oi.order_id = o.id
WHERE o.status = 'placed'
GROUP BY c.id, c.name
ORDER BY total_amount DESC;

-- 2) Количество дочерних элементов 1-го уровня для категорий
SELECT p.id AS category_id,
       p.name,
       COUNT(c.id) AS direct_children
FROM categories p
LEFT JOIN categories c ON c.parent_id = p.id
GROUP BY p.id, p.name
ORDER BY p.id;

-- 3) View: Топ-5 самых покупаемых товаров за последний месяц
-- Здесь "последний месяц" трактуем как интервал в 30 дней от текущей даты.
-- Также выведем категорию 1-го уровня (root).
DROP VIEW IF EXISTS reporting.top5_products_last_month CASCADE;
CREATE SCHEMA IF NOT EXISTS reporting;

CREATE OR REPLACE VIEW reporting.top5_products_last_month AS
WITH RECURSIVE cat_tree AS (
    -- строим маппинг category_id -> root_id, root_name
    SELECT c.id, c.name, c.parent_id, c.id AS root_id, c.name AS root_name
    FROM categories c
    WHERE c.parent_id IS NULL
    UNION ALL
    SELECT ch.id, ch.name, ch.parent_id, ct.root_id, ct.root_name
    FROM categories ch
    JOIN cat_tree ct ON ch.parent_id = ct.id
),
last_month AS (
    SELECT oi.product_id, oi.quantity
    FROM order_items oi
    JOIN orders o ON o.id = oi.order_id
    WHERE o.created_at >= (CURRENT_DATE - INTERVAL '30 days')
)
SELECT p.name AS product,
       ct.root_name AS top_level_category,
       SUM(lm.quantity) AS total_quantity
FROM last_month lm
JOIN products p ON p.id = lm.product_id
LEFT JOIN cat_tree ct ON ct.id = p.category_id
GROUP BY p.name, ct.root_name
ORDER BY total_quantity DESC, product
LIMIT 5;

-- 4) Оптимизации: индексы (выполнить один раз)
-- CREATE INDEX CONCURRENTLY idx_orders_status_created ON orders(status, created_at);
-- CREATE INDEX CONCURRENTLY idx_order_items_order_product ON order_items(order_id, product_id);
-- CREATE INDEX CONCURRENTLY idx_categories_parent ON categories(parent_id);
-- CREATE INDEX CONCURRENTLY idx_products_category ON products(category_id);
-- При больших данных — материализовать маппинг категорий:
-- CREATE MATERIALIZED VIEW reporting.category_to_root AS
-- WITH RECURSIVE cat_tree AS (
--   SELECT c.id, c.name, c.parent_id, c.id AS root_id, c.name AS root_name
--   FROM categories c WHERE c.parent_id IS NULL
--   UNION ALL
--   SELECT ch.id, ch.name, ch.parent_id, ct.root_id, ct.root_name
--   FROM categories ch JOIN cat_tree ct ON ch.parent_id = ct.id
-- )
-- SELECT id AS category_id, root_id, root_name FROM cat_tree;
-- CREATE INDEX CONCURRENTLY ON reporting.category_to_root(category_id);
-- CREATE INDEX CONCURRENTLY ON reporting.category_to_root(root_id);
-- и переписать view на join к материализованному представлению.
