from typing import Optional
import uuid
from models.product import ProductCreate, ProductUpdatePayload, ProductModel
from repositories.product import ProductRepository


class ProductService:
    @staticmethod
    def create_product(payload: ProductCreate) -> ProductModel:
        return ProductRepository.create(payload)

    @staticmethod
    def get_product(product_id: uuid.UUID) -> Optional[ProductModel]:
        return ProductRepository.get_one(product_id)

    @staticmethod
    def update_product(product_id: uuid.UUID, data: ProductUpdatePayload) -> Optional[ProductModel]:
        return ProductRepository.update(product_id, data)

    @staticmethod
    def delete_product(product_id: uuid.UUID) -> bool:
        return ProductRepository.delete(product_id)
    @staticmethod
    def list_all_products() -> list[ProductModel]:
        return ProductRepository.list_all()
    
    @staticmethod
    def get_some_infor(product_id: uuid.UUID) -> Optional[dict]:
        return ProductRepository.get_some_infor(product_id)
    
    @staticmethod
    def add_file_to_products(
        file: bytes, user_id: uuid.UUID, website_name: str, file_name: str | None = None
    ) -> dict:
        return ProductRepository.add_file_to_products(file, user_id, website_name, file_name)