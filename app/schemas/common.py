import math

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, size: int) -> "Page[T]":
        pages = math.ceil(total / size) if total else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)
