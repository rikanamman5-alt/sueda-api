from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from bson.objectid import ObjectId
from database.collections import product_images_collection

router = APIRouter(tags=["Images"])


@router.get("/images/{image_id}")
async def get_image(image_id: str):
    doc = None
    try:
        doc = await product_images_collection.find_one({"_id": ObjectId(image_id)})
    except Exception:
        pass
    if not doc:
        doc = await product_images_collection.find_one({"_id": image_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Image not found")
    data = doc.get("data")
    content_type = doc.get("content_type", "image/jpeg")
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
