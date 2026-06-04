from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from models.rating_model import RatingModel
from models.product_model import ProductModel
from utils.deps import get_current_user

router = APIRouter(tags=["10. Ratings"])


class RateRequest(BaseModel):
    rating: int


@router.post("/products/{product_id}/rate")
async def rate_product(
    product_id: str,
    body: RateRequest,
    current_user=Depends(get_current_user),
):
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    product = await ProductModel.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    user_id = current_user.get("sub") or current_user.get("user_id") or current_user.get("email")

    if not await RatingModel.can_user_rate(user_id, product_id):
        raise HTTPException(
            status_code=403,
            detail="You can only rate products you have purchased and received",
        )

    await RatingModel.add_or_update(product_id, user_id, body.rating)

    avg, count = await RatingModel.get_product_ratings(product_id)
    return {"avgRating": avg, "numRatings": count}


@router.get("/products/{product_id}/can-rate")
async def can_rate_product(
    product_id: str,
    current_user=Depends(get_current_user),
):
    user_id = current_user.get("sub") or current_user.get("user_id") or current_user.get("email")
    can = await RatingModel.can_user_rate(user_id, product_id)
    return {"can_rate": can}


@router.get("/products/{product_id}/rating")
async def get_product_rating(product_id: str):
    avg, count = await RatingModel.get_product_ratings(product_id)
    return {"avgRating": avg, "numRatings": count}


@router.get("/products/{product_id}/user-rating")
async def get_user_rating(
    product_id: str,
    current_user=Depends(get_current_user),
):
    user_id = current_user.get("sub") or current_user.get("user_id") or current_user.get("email")
    rating = await RatingModel.get_user_rating(product_id, user_id)
    if rating:
        return {"rating": rating["rating"]}
    return {"rating": 0}


@router.get("/user/reviews")
async def get_my_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
):
    user_id = current_user.get("sub") or current_user.get("user_id") or current_user.get("email")
    return await RatingModel.get_user_reviews(user_id, page, limit)


@router.get("/user/rateable-products")
async def get_rateable_products(
    current_user=Depends(get_current_user),
):
    user_id = current_user.get("sub") or current_user.get("user_id") or current_user.get("email")
    return {"products": await RatingModel.get_rateable_products(user_id)}
