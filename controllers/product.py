from typing import Optional
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from models.product import ProductCreate, ProductUpdatePayload, ProductModel
from services.product import ProductService


router = APIRouter(
    prefix="/product",
    tags=["product"]
)


@router.post("", response_model=ProductModel)
async def create_product(payload: ProductCreate) -> ProductModel:
    """
    Create a new product
    """
    try:
        product = ProductService.create_product(payload)
        return product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}", response_model=ProductModel)
async def get_product(product_id: uuid.UUID) -> ProductModel:
    """
    Get a product by ID
    """
    product = ProductService.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductModel)
async def update_product(product_id: uuid.UUID, payload: ProductUpdatePayload) -> ProductModel:
    """
    Update a product
    """
    product = ProductService.update_product(product_id, payload)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}", response_model=bool)
async def delete_product(product_id: uuid.UUID) -> bool:
    """
    Delete a product
    """
    result = ProductService.delete_product(product_id)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return True

@router.get("", response_model=list[ProductModel])
async def list_all_products() -> list[ProductModel]:
    """
    List all products
    """
    products = ProductService.list_all_products()
    return products

@router.get("/some_infor/{product_id}", response_model=Optional[dict])
async def get_some_infor(product_id: uuid.UUID) -> Optional[dict]:
    """
    Get some information of a product by ID
    """
    product_info = ProductService.get_some_infor(product_id)
    if product_info is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_info


@router.post("/add_file_to_product/{product_id}", response_model=dict)
async def add_file_to_products(
    file: UploadFile = File(...),
    user_id: uuid.UUID = Form(...),
    website_name: str = Form("toi la gay"),
) -> dict:
    """
    Add products from CSV file
    Returns a dict with:
    - 'added_products': list of successfully added products
    - 'missing_info_products': list of products with missing required information
    """
    try:
        file_bytes = await file.read()
        result = ProductService.add_file_to_products(
            file_bytes, user_id, website_name, file.filename
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
