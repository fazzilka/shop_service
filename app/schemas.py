from pydantic import BaseModel, Field, PositiveInt, conint, NonNegativeInt
from typing import Optional
from decimal import Decimal
from enum import Enum

class AddItemRequest(BaseModel):
    product_id: PositiveInt
    quantity: conint(strict=True, gt=0) = Field(..., description="how many units to add")

class OrderItemOut(BaseModel):
    order_id: int
    product_id: int
    quantity: int
    price_per_unit: Decimal
    line_total: Decimal

class ErrorResponse(BaseModel):
    detail: str
