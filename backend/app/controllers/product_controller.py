from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from bson.objectid import ObjectId
from models.product_model import ProductModel
from schemas.product_schema import ProductCreate, ProductUpdate
from utils.deps import require_role
from database.collections import users_collection

router = APIRouter(tags=["2. Products"])


@router.post("/products")
async def create_product(
    data: ProductCreate,
    seller=Depends(require_role(["seller"]))
):
    product = data.model_dump()
    product["seller_id"] = seller["user_id"]
    product["created_at"] = datetime.utcnow()
    result = await ProductModel.create(product)
    return {"product_id": str(result.inserted_id)}


@router.get("/products")
async def list_products(
    search: str = Query(None, description="Search by name or description"),
    category: str = Query(None, description="Filter by category"),
    min_price: float = Query(None, description="Minimum price"),
    max_price: float = Query(None, description="Maximum price"),
    sort_by: str = Query("created_at", pattern="^(price|name|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    order = 1 if sort_order == "asc" else -1
    result = await ProductModel.search(
        search=search,
        category=category,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        sort_order=order,
        page=page,
        limit=limit,
    )
    products = result.get("products", [])
    for p in products:
        seller_id = p.get("seller_id")
        if seller_id:
            seller = None
            try:
                seller = await users_collection.find_one({"_id": ObjectId(seller_id)})
            except Exception:
                pass
            if not seller:
                seller = await users_collection.find_one({"_id": seller_id})
            if seller:
                p["shop_name"] = (
                    seller.get("shop_name") or
                    seller.get("store_name") or
                    seller.get("name", "")
                )
    return result


@router.get("/products/{product_id}")
async def get_product(product_id: str):
    product = await ProductModel.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    data: ProductUpdate,
    seller=Depends(require_role(["seller"]))
):
    product = await ProductModel.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if str(product["seller_id"]) != seller["user_id"]:
        raise HTTPException(status_code=403, detail="Not your product")

    result = await ProductModel.update(product_id, data.model_dump(exclude_none=True))
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product updated"}


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    seller=Depends(require_role(["seller"]))
):
    product = await ProductModel.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if str(product["seller_id"]) != seller["user_id"]:
        raise HTTPException(status_code=403, detail="Not your product")

    result = await ProductModel.delete(product_id)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}



