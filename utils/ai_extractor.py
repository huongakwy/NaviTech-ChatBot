#!/usr/bin/env python3
"""
AI Extractor - Use Gemini AI to extract product data from unstructured content
"""

import json
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


class AIProductExtractor:
    """Extract product data using Gemini AI"""
    
    # Product schema matching database
    PRODUCT_SCHEMA = {
        "url": "string (required) - Link URL của sản phẩm",
        "title": "string (required) - Tên sản phẩm",
        "price": "float - Giá bán hiện tại",
        "original_price": "float - Giá gốc (nếu có giảm giá)",
        "currency": "string - Đơn vị tiền tệ (VND, USD, etc.)",
        "sku": "string - Mã SKU/mã sản phẩm",
        "brand": "string - Thương hiệu",
        "category": "string - Danh mục sản phẩm",
        "description": "string - Mô tả chi tiết sản phẩm",
        "availability": "string - Tình trạng (Còn hàng, Hết hàng, etc.)",
        "images": "array of strings - Danh sách link ảnh sản phẩm"
    }
    
    @staticmethod
    def extract_from_text(text_content: str, gemini_api_key: str = None) -> List[Dict]:
        """
        Extract product data from unstructured text using Gemini AI
        
        Args:
            text_content: Raw text content
            gemini_api_key: Gemini API key (optional, will use from env)
        
        Returns:
            List of product dictionaries matching database schema
        """
        try:
            import google.generativeai as genai
            
            # Get API key
            api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment")
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Create prompt with schema
            prompt = f"""
You are a data extraction AI. Extract product information from the following text and return ONLY a valid JSON array.

**IMPORTANT RULES:**
1. Return ONLY valid JSON - no markdown, no explanations, no code blocks
2. Each product must be a JSON object in an array
3. Match the schema exactly
4. If a field is not found, use null or empty string/array
5. url and title are REQUIRED - skip products without these

**Database Schema:**
{json.dumps(AIProductExtractor.PRODUCT_SCHEMA, indent=2, ensure_ascii=False)}

**Text to extract from:**
{text_content[:10000]}

Return ONLY the JSON array, nothing else:
"""
            
            # Call Gemini API
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean response (remove markdown code blocks if present)
            if response_text.startswith('```'):
                # Remove ```json and ``` markers
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:].strip()
            
            # Parse JSON
            try:
                products = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parse error: {e}")
                print(f"Response preview: {response_text[:500]}")
                raise ValueError(f"AI returned invalid JSON: {str(e)}")
            
            # Validate and normalize products
            if not isinstance(products, list):
                products = [products]
            
            normalized_products = []
            for product in products:
                # Ensure required fields
                if not product.get('url') or not product.get('title'):
                    continue
                
                normalized = {
                    'url': str(product.get('url', '')),
                    'title': str(product.get('title', '')),
                    'price': float(product.get('price') or 0),
                    'original_price': float(product.get('original_price') or 0),
                    'currency': product.get('currency', 'VND'),
                    'sku': product.get('sku', ''),
                    'brand': product.get('brand', ''),
                    'category': product.get('category', ''),
                    'description': product.get('description', ''),
                    'availability': product.get('availability', ''),
                    'images': product.get('images', []) if isinstance(product.get('images'), list) else []
                }
                normalized_products.append(normalized)
            
            return normalized_products
            
        except ImportError:
            raise ValueError("google-generativeai not installed. Run: pip install google-generativeai")
        except Exception as e:
            raise ValueError(f"AI extraction error: {str(e)}")
    
    @staticmethod
    def extract_from_file(file_path: str, gemini_api_key: str = None) -> List[Dict]:
        """
        Extract product data from file using AI
        
        Supports: TXT, PDF (text), Word (text), and any file with readable content
        """
        try:
            # Read file content
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            elif ext == '.pdf':
                try:
                    import pdfplumber
                    all_text = []
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                all_text.append(text)
                    content = '\n\n'.join(all_text)
                except ImportError:
                    raise ValueError("pdfplumber not installed. Run: pip install pdfplumber")
            
            elif ext == '.docx':
                try:
                    from docx import Document
                    doc = Document(file_path)
                    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
                    content = '\n\n'.join(paragraphs)
                except ImportError:
                    raise ValueError("python-docx not installed. Run: pip install python-docx")
            
            else:
                raise ValueError(f"Unsupported file type for AI extraction: {ext}")
            
            # Extract using AI
            return AIProductExtractor.extract_from_text(content, gemini_api_key)
            
        except Exception as e:
            raise ValueError(f"File extraction error: {str(e)}")


if __name__ == '__main__':
    # Test extractor
    test_text = """
    Sản phẩm 1: iPhone 15 Pro Max 256GB
    Giá: 29,990,000 VNĐ
    Giá gốc: 34,990,000 VNĐ
    Thương hiệu: Apple
    Link: https://example.com/iphone-15-pro-max
    Mô tả: Điện thoại cao cấp với chip A17 Pro
    
    Sản phẩm 2: Samsung Galaxy S24 Ultra
    Giá: 27,990,000 VNĐ
    Thương hiệu: Samsung
    Link: https://example.com/galaxy-s24-ultra
    """
    
    try:
        products = AIProductExtractor.extract_from_text(test_text)
        print(f"✅ Extracted {len(products)} products")
        print(json.dumps(products, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Error: {e}")
