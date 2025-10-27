from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from .db import get_session, engine
from .models import Base, Product, Order, OrderItem, OrderStatus
from .schemas import AddItemRequest, OrderItemOut

app = FastAPI(title="Shop Service", version="1.0.0")

@app.on_event("startup")
async def on_startup():
    # create tables if they don't exist (for demo/dev only; in prod use Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/orders/{order_id}/items", response_model=OrderItemOut, status_code=201)
async def add_item_to_order(order_id: int, payload: AddItemRequest, session: AsyncSession = Depends(get_session)):
    # open one transaction
    async with session.begin():
        # 1) Ensure order exists and is mutable
        order = await session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OrderNotFound")
        if order.status != OrderStatus.draft:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OrderNotEditable")

        # 2) Lock product row to avoid races
        result = await session.execute(
            select(Product).where(Product.id == payload.product_id).with_for_update()
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ProductNotFound")

        # 3) Find existing order item, if any
        result = await session.execute(
            select(OrderItem).where(OrderItem.order_id == order_id, OrderItem.product_id == payload.product_id).with_for_update()
        )
        oi = result.scalar_one_or_none()

        # Only the delta is taken from stock
        delta_qty = payload.quantity

        # 4) Check stock
        if product.stock < delta_qty:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="NotEnoughStock")

        # 5) Apply changes
        product.stock -= delta_qty

        if oi:
            oi.quantity += delta_qty
            price_per_unit = oi.price_per_unit  # keep snapshot price
        else:
            price_per_unit = product.price
            oi = OrderItem(order_id=order_id, product_id=product.id, quantity=delta_qty, price_per_unit=price_per_unit)
            session.add(oi)

        # Session will flush at commit
    # refresh out of transaction scope
    await session.refresh(oi)
    line_total = Decimal(oi.quantity) * Decimal(oi.price_per_unit)
    return OrderItemOut(
        order_id=oi.order_id,
        product_id=oi.product_id,
        quantity=oi.quantity,
        price_per_unit=Decimal(oi.price_per_unit),
        line_total=line_total
    )

# --- Dev helpers (optional seeding) ---
@app.post("/seed")
async def seed(session: AsyncSession = Depends(get_session)):
    async with session.begin():
        # create minimal data if empty
        ccount = (await session.execute(select(func.count()).select_from(Product))).scalar()
        from sqlalchemy import func
        if ccount and ccount > 0:
            return {"seeded": False}
        from .models import Category, Client, Order, Product
        root = Category(name="Electronics")
        phones = Category(name="Phones", parent=root)
        session.add_all([root, phones])
        session.flush()
        p = Product(name="Phone X", price=999.00, stock=10, category_id=phones.id)
        session.add(p)
        client = Client(name="ООО Ромашка", address="Москва, ул. Пушкина, 1")
        session.add(client)
        session.flush()
        order = Order(client_id=client.id, status=OrderStatus.draft)
        session.add(order)
    return {"seeded": True}
    
