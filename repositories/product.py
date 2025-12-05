from typing import Optional
import uuid
import csv
import io
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session 

from db import Session
from models.product import Product, ProductCreate, ProductUpdatePayload, ProductModel


class ProductRepository:
    @staticmethod
    def _parse_float(value: str) -> Optional[float]:
        """Safely parse a string to float, returning None if invalid"""
        if not value or not value.strip():
            return None
        try:
            return float(value.strip())
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def create(payload: ProductCreate) -> ProductModel:
        product = Product(**payload.model_dump())
        with Session() as session:
            session.add(product)
            session.commit()
            session.refresh(product)
            return ProductModel.model_validate(product)

    @staticmethod
    def get_one(product_id: uuid.UUID) -> Optional[ProductModel]:
        with Session() as session:
            query = select(Product).where(Product.id == product_id)
            result = session.execute(query).scalar_one_or_none()
            if result is None:
                return None
            return ProductModel.model_validate(result)

    @staticmethod
    def update(product_id: uuid.UUID, data: ProductUpdatePayload) -> Optional[ProductModel]:
        with Session() as session:
            # Convert Pydantic model to dict and remove None values
            update_data = data.model_dump(exclude_unset=True)
            if not update_data:
                return None

            # Update the product
            query = update(Product).where(Product.id == product_id).values(**update_data)
            result = session.execute(query)
            session.commit()

            if result.rowcount == 0:
                return None

            # Get the updated product
            product = session.get(Product, product_id)
            return ProductModel.model_validate(product)

    @staticmethod
    def delete(product_id: uuid.UUID) -> bool:
        with Session() as session:
            query = delete(Product).where(Product.id == product_id)
            result = session.execute(query)
            session.commit()
            return result.rowcount > 0
        
    @staticmethod
    def list_all() -> list[ProductModel]:
        with Session() as session:
            query = select(Product)
            results = session.execute(query).scalars().all()
            return [ProductModel.model_validate(product) for product in results]
        
    @staticmethod
    def get_some_infor(product_id: uuid.UUID) -> Optional[dict]:
        with Session() as session:
            query = select(Product).where(Product.id == product_id)
            result = session.execute(query).scalar_one_or_none()
            if result is None:
                return None
            return {
                "title": result.title,
                "price": str(result.price),
                "brand": result.brand
            }
            

    @staticmethod
    def add_file_to_products(file: bytes, user_id: uuid.UUID, website_name: str) -> dict:
        """
        Parse CSV file and create products in database.
        Returns a dict with:
        - 'added_products': list of successfully added products
        - 'missing_info_products': list of products with missing required information
        """
        added_products = []
        missing_info_products = []
        
        # Parse CSV file from bytes
        try:
            file_content = file.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(file_content))
        except Exception as e:
            raise ValueError(f"Error parsing CSV file: {str(e)}")
        
        # Required fields to check for missing information
        required_fields = ['title', 'price', 'original_price', 'currency', 'brand', 'description', 'availability']
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because row 1 is header
            try:
                # Extract data from CSV row
                # Map CSV columns to ProductCreate fields
                # Handle website_id parsing
                website_id_value = row.get('website_id', '').strip() if row.get('website_id') else ''
                try:
                    website_id = int(website_id_value) if website_id_value else 0
                except (ValueError, TypeError):
                    website_id = 0
                
                product_data = {
                    'website_name': website_name,
                    'website_id': website_id,
                    'url': row.get('url', '').strip() if row.get('url') else '',
                    'title': row.get('title', '').strip() if row.get('title') else None,
                    'price': ProductRepository._parse_float(row.get('price', '')),
                    'original_price': ProductRepository._parse_float(row.get('original_price', '')),
                    'currency': row.get('currency', '').strip() if row.get('currency') else None,
                    'sku': row.get('sku', '').strip() if row.get('sku') else None,
                    'brand': row.get('brand', '').strip() if row.get('brand') else None,
                    'category': row.get('category', '').strip() if row.get('category') else None,
                    'description': row.get('description', '').strip() if row.get('description') else None,
                    'availability': row.get('availability', '').strip() if row.get('availability') else None,
                    'images': [img.strip() for img in row.get('images', '').split(',')] if row.get('images') and row.get('images').strip() else None,
                    'user_id': user_id,
                }
                
                # Check for missing information
                missing_fields = []
                for field in required_fields:
                    value = product_data.get(field)
                    if value is None or (isinstance(value, str) and not value.strip()):
                        missing_fields.append(field)
                
                # Validate required fields for database
                if not product_data['url'] or not product_data['website_name']:
                    missing_info_products.append({
                        'row_number': row_num,
                        'data': product_data,
                        'missing_fields': missing_fields + (['url'] if not product_data['url'] else []) + (['website_name'] if not product_data['website_name'] else [])
                    })
                    continue
                
                # Create product using ProductCreate model
                product_create = ProductCreate(**product_data)
                
                # Try to create product in database
                try:
                    created_product = ProductRepository.create(product_create)
                    product_dict = created_product.model_dump()
                    
                    # If there are missing fields, add to missing_info_products
                    if missing_fields:
                        missing_info_products.append({
                            'row_number': row_num,
                            'product_id': str(product_dict['id']),
                            'data': product_dict,
                            'missing_fields': missing_fields
                        })
                    else:
                        added_products.append(product_dict)
                        
                except Exception as e:
                    # If creation fails, add to missing_info_products
                    missing_info_products.append({
                        'row_number': row_num,
                        'data': product_data,
                        'missing_fields': missing_fields,
                        'error': str(e)
                    })
                    
            except Exception as e:
                # Handle errors in parsing individual rows
                missing_info_products.append({
                    'row_number': row_num,
                    'data': row,
                    'missing_fields': required_fields,
                    'error': f"Error processing row: {str(e)}"
                })
        
        return {
            'added_products': added_products,
            'missing_info_products': missing_info_products
        }