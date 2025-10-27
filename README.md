# Shop Service (PostgreSQL + FastAPI + SQLAlchemy)

## Что внутри
- **PostgreSQL схема** (`sql/schema.sql`) и индексы.
- **SQL-запросы по ТЗ** (`sql/queries.sql`) + представление `reporting.top5_products_last_month`.
- **FastAPI сервис** с методом `POST /orders/{order_id}/items` для добавления товара в заказ с проверкой остатков (п.3 ТЗ).
- Асинхронный SQLAlchemy 2.0 + драйвер `asyncpg`.
- `docker-compose.yml` для быстрого запуска PostgreSQL.

## Быстрый старт
1. Поднять PostgreSQL (через Docker):
   ```bash
   docker compose up -d db
   ```

2. Установить зависимости и переменные окружения:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   # отредактируйте DATABASE_URL при необходимости
   ```

3. Создать таблицы в БД:
   ```bash
   python create_tables.py
   ```

4. Запустить API:
   ```bash
   uvicorn app.main:app --reload
   ```

## Проверка метода добавления товара
- Создайте данные (клиента, категории, товар, заказ) — можно через любой клиент к БД (psql/DBeaver) или временные ручки `/seed` из `main.py`.
- Вызов:
  ```bash
  curl -X POST "http://127.0.0.1:8000/orders/1/items" -H "Content-Type: application/json" -d '{"product_id": 1, "quantity": 2}'
  ```
- Если товара не хватает на складе — получите `400` с сообщением `NotEnoughStock`.

## Структура
```
app/
  db.py
  models.py
  schemas.py
  main.py
sql/
  schema.sql
  queries.sql
.env.example
requirements.txt
docker-compose.yml
create_tables.py
```

## Примечания по проектированию
- Дерево категорий — **adjacency list** (`categories.parent_id`) с рекурсивными CTE в запросах.
- Заказы: строки заказа (`order_items`) содержат `price_per_unit` как **снимок цены** на момент добавления.
- Проверка остатков: транзакция + `SELECT ... FOR UPDATE` по товару, чтобы корректно работать при конкуренции.
- Оптимизации: индексы на `categories.parent_id`, `products.category_id`, `orders(client_id, created_at)`, `order_items(order_id, product_id)`,
  материализуемое представление для маппинга категорий к корню при росте данных и т.д. См. `sql/queries.sql`!
