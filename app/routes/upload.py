import os
import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException

ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
MAX_FILE_SIZE = 1 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PRODUCT_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "products")

router = APIRouter(tags=["Upload"])


@router.post("/upload-profile")
async def upload_profile(file: UploadFile = File(...)):
    filename = file.filename.lower()

    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG, GIF, WebP allowed"
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File exceeds 1MB limit"
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_location = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_location, "wb") as f:
        f.write(content)

    return {
        "message": "Upload successful",
        "filename": unique_filename
    }


@router.delete("/upload-profile")
async def delete_profile_image(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": "Profile image deleted"}
    raise HTTPException(status_code=404, detail="File not found")


@router.post("/upload-product-images")
async def upload_product_images(
    files: List[UploadFile] = File(...)
):
    if len(files) > 3:
        raise HTTPException(
            status_code=400,
            detail="Maximum 3 images only"
        )

    os.makedirs(PRODUCT_UPLOAD_DIR, exist_ok=True)
    uploaded_files = []

    for file in files:
        filename = file.filename.lower()

        if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail=f"{filename} is not allowed"
            )

        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"{filename} exceeds 1MB limit"
            )

        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(PRODUCT_UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        uploaded_files.append(unique_filename)

    return {
        "message": "Images uploaded successfully",
        "files": uploaded_files
    }


@router.delete("/upload-product-images/{filename}")
async def delete_product_image(filename: str):
    file_path = os.path.join(PRODUCT_UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": "Product image deleted"}
    raise HTTPException(status_code=404, detail="File not found")
