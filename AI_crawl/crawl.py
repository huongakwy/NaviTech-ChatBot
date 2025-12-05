#!/usr/bin/env python3
"""
Simple E-commerce Sitemap Crawler
Chỉ cần nhập URL → tự động crawl products từ sitemap
"""
import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from typing import List, Dict
import json
import pandas as pd
from bs4 import BeautifulSoup
import trafilatura
from datetime import datetime
import time
import os
from dotenv import load_dotenv

load_dotenv()


# ⚙️ Configuration - Set cứng mặc định
class Config:
    AI_PROVIDER = 'openai'           # openai, gemini, grok
    AI_EXTRACT_PRICES = False        # Disable AI extraction - Gemini free tier bị quota limit (2 req/min)
    RATE_LIMIT_DELAY = 0.01          # Nhỏ delay 10ms - tránh bị rate limit (từ 0 → 0.01)
    TIMEOUT = 2                       # Request timeout (giảm từ 3 -> 2s - bỏ trang chậm)
    MAX_RETRIES = 3                   # Retry khi fail (tăng từ 0 -> 3 để handle 429)
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
    PRICE_MIN_THRESHOLD = 0           # Giá tối thiểu hợp lệ
    PRICE_MAX_THRESHOLD = 1e15        # Giá tối đa hợp lệ
    DESCRIPTION_MAX_LENGTH = 300      # Cắt description sau N ký tự
    # Connection pooling - aggressive cho parallel requests
    POOL_CONNECTIONS = 50            # Tăng từ 20 -> 50
    POOL_MAXSIZE = 50                # Tăng từ 20 -> 50
    RETRIES_BACKOFF = 0.5            # Backoff 500ms (tăng từ 0 để handle 429)
    # Extract optimization - chỉ lấy data cần thiết
    EXTRACT_TRAFILATURA = False      # BỎ trafilatura - quá chậm, chỉ dùng JSON-LD + OG
    # Anti-blocking
    RANDOM_DELAY = (0.1, 0.5)        # Random delay 100-500ms giữa requests


class AIAgent:
    """AI Agent để nhận diện product sitemaps"""
    
    def __init__(self, provider=None):
        """provider: 'openai', 'gemini', hoặc 'grok'"""
        self.provider = provider or Config.AI_PROVIDER
        self.api_key = self._get_api_key()
        
        # Fallback: nếu API key empty, tìm provider khác
        if not self.api_key:
            self.provider, self.api_key = self._find_available_provider()
    
    def _find_available_provider(self):
        """Tìm provider đầu tiên có API key"""
        providers = ['openai', 'gemini', 'grok']
        for p in providers:
            if p == 'openai':
                key = os.getenv('OPENAI_API_KEY')
            elif p == 'gemini':
                key = os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY1') or os.getenv('GOOGLE_API_KEY')
            else:  # grok
                key = os.getenv('XAI_API_KEY')
            
            if key:
                return p, key
        
        return 'openai', None  # Fallback default (nếu không có API key nào)
    
    def _get_api_key(self):
        """Lấy API key từ environment"""
        if self.provider == 'openai':
            return os.getenv('OPENAI_API_KEY')
        elif self.provider == 'gemini':
            return os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY1') or os.getenv('GOOGLE_API_KEY')
        elif self.provider == 'grok':
            return os.getenv('XAI_API_KEY')
        return None
    
    def _get_gemini_keys(self):
        """Lấy danh sách các Gemini API keys để retry"""
        keys = []
        key1 = os.getenv('GEMINI_API_KEY')
        key2 = os.getenv('GEMINI_API_KEY1')
        key3 = os.getenv('GOOGLE_API_KEY')
        
        if key1:
            keys.append(key1)
        if key2 and key2 != key1:  # Avoid duplicate
            keys.append(key2)
        if key3 and key3 not in [key1, key2]:  # Avoid duplicate
            keys.append(key3)
        
        return keys
    
    def identify_product_sitemaps(self, sitemap_urls: List[str]) -> List[str]:
        """
        Dùng AI để nhận diện sitemap nào chứa products
        
        Args:
            sitemap_urls: Danh sách các sitemap URLs
        
        Returns:
            Danh sách các sitemap chứa products
        """
        if not self.api_key:
            print(f"⚠️  Không tìm thấy API key cho {self.provider}")
            print(f"   → Dùng heuristic fallback")
            return self._heuristic_identify(sitemap_urls)
        
        print(f"🤖 Dùng AI ({self.provider}) để nhận diện product sitemaps...")
        
        try:
            if self.provider == 'openai':
                return self._openai_identify(sitemap_urls)
            elif self.provider == 'gemini':
                return self._gemini_identify(sitemap_urls)
            elif self.provider == 'grok':
                return self._grok_identify(sitemap_urls)
        except Exception as e:
            print(f"⚠️  AI error: {e}")
            print(f"   → Dùng heuristic fallback")
            return self._heuristic_identify(sitemap_urls)
    
    def _heuristic_identify(self, sitemap_urls: List[str]) -> List[str]:
        """Heuristic fallback nếu không có AI"""
        product_keywords = [
            'product', 'item', 'goods', 'san-pham',
            '_products_', 'catalog'
        ]
        
        # Exclude patterns - các sitemap chắc chắn KHÔNG có products
        exclude_keywords = [
            'news', 'blog', 'page', 'landing',
            'collection.xml', 'collections.xml',  # Collection listing, không phải products
            'category', 'categories', 'tags'
        ]
        
        product_sitemaps = []
        for url in sitemap_urls:
            url_lower = url.lower()
            
            # Loại bỏ exclude patterns
            if any(x in url_lower for x in exclude_keywords):
                continue
            
            # Chấp nhận nếu có product keywords
            if any(x in url_lower for x in product_keywords):
                product_sitemaps.append(url)
        
        return product_sitemaps
    
    def _openai_identify(self, sitemap_urls: List[str]) -> List[str]:
        """Dùng OpenAI API"""
        import openai
        
        client = openai.OpenAI(api_key=self.api_key)
        
        prompt = f"""Bạn là chuyên gia phân tích e-commerce sitemaps.

Dưới đây là danh sách các sitemap URLs từ một trang web:

{json.dumps(sitemap_urls, indent=2)}

HÃY PHÂN TÍCH và CHỈ TRẢ VỀ các sitemap URLs có khả năng chứa PRODUCT PAGES (trang sản phẩm).

Các sitemap thường KHÔNG chứa products:
- news, blog, pages, landings, collections (collection listing)
- category, tags

Các sitemap thường chứa products:
- product, item, goods, catalog
- collection_products (products trong collection)

TRẢ VỀ JSON array với format:
{{
  "product_sitemaps": ["url1", "url2", ...],
  "reasoning": "giải thích ngắn gọn"
}}"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0
        )
        
        result = json.loads(response.choices[0].message.content)
        print(f"   AI reasoning: {result.get('reasoning', '')}")
        return result.get('product_sitemaps', [])
    
    def _gemini_identify(self, sitemap_urls: List[str]) -> List[str]:
        """Dùng Google Gemini API với retry bằng 2 keys"""
        import google.generativeai as genai
        
        gemini_keys = self._get_gemini_keys()
        
        prompt = f"""You are an e-commerce sitemap analyzer.

Here are sitemap URLs from a website:

{json.dumps(sitemap_urls, indent=2)}

ANALYZE and RETURN only the sitemap URLs that likely contain PRODUCT PAGES.

Sitemaps that usually DON'T contain products:
- news, blog, pages, landings, collections (collection listing)
- category, tags

Sitemaps that usually contain products:
- product, item, goods, catalog
- collection_products (products in collection)

RETURN JSON format:
{{
  "product_sitemaps": ["url1", "url2", ...],
  "reasoning": "brief explanation"
}}"""
        
        last_error = None
        for key_idx, api_key in enumerate(gemini_keys, 1):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-pro')
                
                response = model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0
                    )
                )
                
                result = json.loads(response.text)
                print(f"   AI reasoning: {result.get('reasoning', '')}")
                return result.get('product_sitemaps', [])
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                
                # Check if it's a quota error
                if '429' in error_msg or 'quota' in error_msg.lower():
                    print(f"⚠️  AI error (key {key_idx}): {error_msg}")
                    if key_idx < len(gemini_keys):
                        print(f"   → Thử key #{key_idx + 1}...")
                    else:
                        print(f"   → Hết các keys, dùng heuristic fallback")
                else:
                    # Lỗi không phải quota
                    print(f"❌ Gemini API error (key {key_idx}): {error_msg}")
                    raise
        
        # Nếu hết tất cả keys, trả về empty list (sẽ dùng heuristic)
        print(f"⚠️  Tất cả Gemini keys đã hết quota. Dùng heuristic fallback.")
        return []
    
    def _grok_identify(self, sitemap_urls: List[str]) -> List[str]:
        """Dùng xAI Grok API"""
        
        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        prompt = f"""Analyze these sitemap URLs and identify which ones contain product pages:

{json.dumps(sitemap_urls, indent=2)}

Return JSON:
{{
  "product_sitemaps": ["url1", "url2"],
  "reasoning": "explanation"
}}"""
        
        data = {
            "model": "grok-beta",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = json.loads(response.json()['choices'][0]['message']['content'])
        print(f"   AI reasoning: {result.get('reasoning', '')}")
        return result.get('product_sitemaps', [])
    
    def extract_prices_with_ai(self, html: str, soup) -> dict:
        """
        Dùng AI để tự động phân tích HTML và trích xuất giá
        Detect pattern: <del>giá gốc</del> <ins>giá khuyến mãi</ins>
        """
        if not self.api_key:
            return {'price': 0, 'original_price': 0}
        
        try:
            # Extract price-related HTML snippets
            price_html = str(soup.find(['div', 'span', 'p'], class_=re.compile(r'price', re.I)))[:500]
            
            # Nếu không tìm được element có class 'price', dùng toàn bộ body
            if not price_html or len(price_html) < 20 or price_html == 'None':
                # Lấy body HTML (loại tags script/style)
                for script in soup(["script", "style"]):
                    script.decompose()
                price_html = str(soup.body)[:1000] if soup.body else str(soup)[:1000]
            
            if not price_html or len(price_html) < 20:
                return {'price': 0, 'original_price': 0}
            
            if self.provider == 'openai':
                import openai
                client = openai.OpenAI(api_key=self.api_key)
                
                prompt = f"""Phân tích HTML này và trích xuất giá sản phẩm:

HTML: {price_html}

Tìm kiếm:
1. Giá gốc (từ <del>, strikethrough, giá cũ)
2. Giá hiện tại (từ <ins>, giá mới, giá active)

Trả về JSON (chỉ số, không ký tự tiền tệ):
{{
  "original_price": 0,
  "current_price": 0
}}

Trả về CHỈ JSON, không giải thích."""
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=100
                )
                
                content = response.choices[0].message.content
                # Parse JSON từ markdown code block hoặc raw JSON
                if '```' in content:
                    # Extract JSON từ ```json ... ```
                    json_match = content.split('```json')[-1].split('```')[0].strip()
                else:
                    json_match = content.strip()
                
                result = json.loads(json_match)
                return {
                    'original_price': float(result.get('original_price', 0)),
                    'price': float(result.get('current_price', 0))
                }
            
            elif self.provider == 'gemini':
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                
                prompt = f"""Phân tích HTML này và trích xuất giá sản phẩm:

HTML: {price_html}

Tìm kiếm:
1. Giá gốc (từ <del>, strikethrough, giá cũ)
2. Giá hiện tại (từ <ins>, giá mới, giá active)

Trả về JSON (chỉ số, không ký tự tiền tệ):
{{
  "original_price": 0,
  "current_price": 0
}}

Trả về CHỈ JSON, không giải thích."""
                
                model = genai.GenerativeModel('gemini-2.5-pro')
                response = model.generate_content(prompt)
                
                content = response.text
                # Parse JSON từ markdown code block hoặc raw JSON
                if '```' in content:
                    # Extract JSON từ ```json ... ```
                    json_match = content.split('```json')[-1].split('```')[0].strip()
                else:
                    json_match = content.strip()
                
                result = json.loads(json_match)
                return {
                    'original_price': float(result.get('original_price', 0)),
                    'price': float(result.get('current_price', 0))
                }
        except Exception as e:
            # Debug: log error
            import traceback
            print(f"⚠️  AI extract_prices error: {e}")
            print(f"   Traceback: {traceback.format_exc()[:200]}")
        
        return {'price': 0, 'original_price': 0}


class SimpleSitemapCrawler:
    """Crawler đơn giản từ sitemap"""
    
    def __init__(self, base_url: str, ai_provider='openai'):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.headers = {
            'User-Agent': Config.USER_AGENT
        }
        self.ai_agent = AIAgent(provider=ai_provider)
        
        # ⚡ Connection pooling + reuse - tối ưu cho parallel requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=Config.MAX_RETRIES,
            backoff_factor=Config.RETRIES_BACKOFF,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        # HTTPAdapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=Config.POOL_CONNECTIONS,
            pool_maxsize=Config.POOL_MAXSIZE
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def inspect_sitemap(self):
        """Debug function: xem cấu trúc sitemap"""
        print(f"\n🔍 INSPECT SITEMAP: {self.base_url}\n")
        
        sitemap_url = self.base_url + '/sitemap.xml'
        content = self.fetch_sitemap(sitemap_url)
        
        if not content:
            print("❌ Không tìm thấy sitemap.xml")
            return
        
        try:
            root = ET.fromstring(content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            if root.tag.endswith('sitemapindex'):
                print("📂 Đây là SITEMAP INDEX\n")
                sitemaps = root.findall('.//sm:sitemap', ns)
                if not sitemaps:
                    sitemaps = root.findall('.//sitemap')
                
                print(f"Tìm thấy {len(sitemaps)} sub-sitemaps:\n")
                for i, sitemap in enumerate(sitemaps, 1):
                    loc = sitemap.find('sm:loc', ns)
                    if loc is None:
                        loc = sitemap.find('loc')
                    lastmod = sitemap.find('sm:lastmod', ns)
                    if lastmod is None:
                        lastmod = sitemap.find('lastmod')
                    
                    if loc is not None and loc.text:
                        url = loc.text.strip()
                        mod = lastmod.text if lastmod is not None and lastmod.text else 'N/A'
                        print(f"  {i}. {url}")
                        print(f"     Last modified: {mod}")
            
            elif root.tag.endswith('urlset'):
                print("📄 Đây là URLSET (sitemap trực tiếp)\n")
                urls = root.findall('.//sm:url', ns)
                if not urls:
                    urls = root.findall('.//url')
                print(f"Có {len(urls)} URLs\n")
                
                # Show sample
                for i, url_elem in enumerate(urls[:5], 1):
                    loc = url_elem.find('sm:loc', ns) or url_elem.find('loc')
                    if loc is not None and loc.text:
                        print(f"  {i}. {loc.text}")
        
        except Exception as e:
            print(f"❌ Lỗi parse: {e}")
    
    def fetch_sitemap(self, url: str) -> str:
        """Tải sitemap - fallback: curl khi requests fail"""
        # Try a sequence of Accept headers to handle picky servers
        accept_values = [
            None,
            'application/xml, text/xml, */*',
            'text/xml, application/xml, */*',
            'application/rss+xml, application/xml, text/xml, */*',
            'text/plain, */*; q=0.1'
        ]

        last_error = None
        for accept in accept_values:
            try:
                headers = dict(self.headers)
                if accept:
                    headers['Accept'] = accept
                resp = self.session.get(url, headers=headers, timeout=Config.TIMEOUT)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                last_error = e
                # If it's 415 specifically, try next Accept header; otherwise continue retry logic
                err_str = str(e)
                # small backoff before next try
                time.sleep(0.1)

        # As a last resort, try curl fallback (bypass some WAFs/behavior)
        try:
            import subprocess
            curl_cmd = [
                'curl', '-s', '-L', '-A', Config.USER_AGENT,
                '-H', 'Accept: application/xml, text/xml, */*', url
            ]
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except Exception:
            pass

        print(f"  ❌ Không tải được {url}: {str(last_error)[:120]}")
        return ""
    
    def get_sitemap_urls(self) -> List[str]:
        """Tìm và lấy tất cả URLs từ sitemap"""
        
        # Các vị trí sitemap phổ biến
        sitemap_paths = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemap-index.xml',
            '/product-sitemap.xml',
            '/products-sitemap.xml',
        ]
        
        all_urls = []
        
        for path in sitemap_paths:
            sitemap_url = self.base_url + path
            
            content = self.fetch_sitemap(sitemap_url)
            if not content:
                continue
            
            # Parse XML
            try:
                # Try lxml first (more forgiving), fallback to ElementTree
                try:
                    from lxml import etree as lxml_etree
                    parser = lxml_etree.XMLParser(recover=True)
                    root = lxml_etree.fromstring(content.encode('utf-8'), parser=parser)
                except (ImportError, Exception):
                    root = ET.fromstring(content)
                ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                
                # Kiểm tra xem đây là sitemap index hay urlset
                if root.tag.endswith('sitemapindex'):
                    # Lấy các sub-sitemap
                    sitemaps_found = root.findall('.//sm:sitemap', ns)
                    if not sitemaps_found:
                        sitemaps_found = root.findall('.//sitemap')
                    
                    # Lấy tất cả sitemap URLs
                    all_sitemap_urls = []
                    for sitemap in sitemaps_found:
                        loc = sitemap.find('sm:loc', ns)
                        if loc is None:
                            loc = sitemap.find('loc')
                        if loc is not None and loc.text:
                            all_sitemap_urls.append(loc.text.strip())
                    
                    # Dùng AI để identify product sitemaps
                    product_sitemap_urls = self.ai_agent.identify_product_sitemaps(all_sitemap_urls)
                    
                    # Crawl các product sitemaps (recursive)
                    for sub_url in product_sitemap_urls:
                        sub_urls = self._crawl_sitemap_recursive(sub_url)
                        all_urls.extend(sub_urls)
                
                elif root.tag.endswith('urlset'):
                    urls = self._parse_urlset(content)
                    all_urls.extend(urls)
                    print(f"  └─ {len(urls)} URLs")
                
                if all_urls:
                    break  # Đã tìm thấy sitemap, không cần tìm tiếp
                    
            except Exception as e:
                error_msg = str(e)[:120]
                if 'mismatched tag' in error_msg:
                    print(f"  ⚠️ Lỗi parse XML: mismatched tag (cắt ngắn/malformed)")
                else:
                    print(f"  ⚠️ Lỗi parse XML: {error_msg}")
                continue
        
        return all_urls
    
    def _crawl_sitemap_recursive(self, sitemap_url: str, depth: int = 0, max_depth: int = 3) -> List[str]:
        """Crawl sitemap recursively để xử lý sitemap index trong sitemap"""
        if depth > max_depth:
            return []
        
        urls = []
        content = self.fetch_sitemap(sitemap_url)
        if not content:
            return []
        
        try:
            # Try lxml first (more forgiving), fallback to ElementTree
            try:
                from lxml import etree as lxml_etree
                parser = lxml_etree.XMLParser(recover=True)
                root = lxml_etree.fromstring(content.encode('utf-8'), parser=parser)
            except (ImportError, Exception):
                root = ET.fromstring(content)
            
            # Nếu là sitemapindex -> crawl tiếp vào các sitemap con
            if root.tag.endswith('sitemapindex'):
                ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                indent = "  " * (depth + 1)
                
                for sitemap_elem in root.findall('.//sm:sitemap', ns) or root.findall('.//sitemap'):
                    loc = sitemap_elem.find('sm:loc', ns) or sitemap_elem.find('loc')
                    if loc is not None and loc.text:
                        sub_url = loc.text.strip()
                        print(f"{indent}└─ Sub-sitemap: {sub_url}")
                        sub_urls = self._crawl_sitemap_recursive(sub_url, depth + 1, max_depth)
                        urls.extend(sub_urls)
                        if sub_urls:
                            print(f"{indent}   ✓ {len(sub_urls)} URLs")
            
            # Nếu là urlset -> parse URLs
            elif root.tag.endswith('urlset'):
                urls = self._parse_urlset(content)
        
        except Exception as e:
            error_msg = str(e)[:100]
            if depth == 0:
                if 'mismatched tag' in error_msg:
                    print(f"  ⚠️ XML mismatched tag (có thể bị cắt ngắn hoặc malformed)")
                else:
                    print(f"  ⚠️ Lỗi parse recursive: {error_msg}")
        
        return urls
    
    def _parse_urlset(self, content: str) -> List[str]:
        """Parse urlset XML - xử lý cả có và không có namespace"""
        urls = []
        try:
            # Try lxml first (more forgiving with malformed XML), fallback to ElementTree
            try:
                from lxml import etree as lxml_etree
                parser = lxml_etree.XMLParser(recover=True)  # recover=True: forgiving parser
                root = lxml_etree.fromstring(content.encode('utf-8'), parser=parser)
            except (ImportError, Exception):
                # Fallback to standard ElementTree
                root = ET.fromstring(content)
            
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Thử tìm với namespace trước
            url_elements = root.findall('.//sm:url', ns)
            if not url_elements:
                # Nếu không có, tìm không namespace
                try:
                    url_elements = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
                except:
                    pass
            if not url_elements:
                # Cuối cùng thử không có namespace gì cả
                url_elements = root.findall('.//url')
            
            for url_elem in url_elements:
                # Thử nhiều cách tìm <loc>
                loc = url_elem.find('sm:loc', ns)
                if loc is None:
                    try:
                        loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    except:
                        pass
                if loc is None:
                    loc = url_elem.find('loc')
                
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())
        except Exception as e:
            # Log detailed error info for debugging
            error_msg = str(e)[:100]
            if 'mismatched tag' in error_msg:
                # Try to detect truncated XML
                if not content.rstrip().endswith('>'):
                    print(f"    ⚠️ XML có thể bị cắt ngắn (không kết thúc bằng >)")
                else:
                    print(f"    ⚠️ XML có mismatched tags: {error_msg}")
            else:
                print(f"    ⚠️ Parse error: {error_msg}")
        return urls
    
    def is_product_url(self, url: str) -> bool:
        """Heuristic đơn giản để phát hiện product URL"""
        
        # Loại trừ các URL không phải product
        exclude_patterns = [
            '/category', '/danh-muc', '/collection',
            '/blog', '/tin-tuc', '/news',
            '/search', '/cart', '/checkout', '/account',
            '/page', '/about', '/contact', '/help',
        ]
        
        if any(pattern in url.lower() for pattern in exclude_patterns):
            return False
        
        # Product patterns
        product_patterns = [
            r'/san-pham/',
            r'/product/',
            r'/p/',
            r'-p\d+',           # tiki style
            r'/\d+\.html',      # số.html
            r'-i\d+',           # shopee/lazada style
        ]
        
        if any(re.search(pattern, url, re.I) for pattern in product_patterns):
            return True
        
        # Nếu URL có số ID dài (>= 5 digits), có thể là product
        if re.search(r'\d{5,}', url):
            return True
        
        return False
    
    def _extract_description_from_html(self, soup, url: str) -> str:
        """
        Parse HTML để tìm description section - hỗ trợ cấu trúc HTML đa dạng
        Tìm "Mô tả", "Description", "Chi tiết", v.v. và extract text đầy đủ
        Priority: HTML patterns → Full page text parsing → JSON-LD
        """
        description = ""
        
        # Pattern 1: Các pattern tìm heading (Tiếng Việt + Tiếng Anh)
        heading_patterns = [
            r'mô\s+tả', r'description', r'chi\s+tiết\s+sản\s+phẩm',
            r'thông\s+tin\s+chi\s+tiết', r'sản\s+phẩm\s+chi\s+tiết',
            r'product\s+details', r'about\s+product', r'thông\s+tin\s+sản\s+phẩm'
        ]
        
        # Pattern 2: Các selector class/id phổ biến chứa description
        selectors_to_try = [
            # WooCommerce specific (popular e-commerce platform) - HIGHEST PRIORITY
            {'tag': 'div', 'attrs': {'class': re.compile(r'woocommerce-tabs-panel.*description|tab-panel.*description', re.I)}},
            # Class-based (most specific first)
            {'tag': 'div', 'attrs': {'class': re.compile(r'(description|mota|chi-tiet|detail|content|entry-content)', re.I)}},
            {'tag': 'div', 'attrs': {'id': re.compile(r'(description|mota|detail|content|main)', re.I)}},
            # itemprop
            {'tag': 'div', 'attrs': {'itemprop': 'description'}},
            # Data attributes (common in modern e-com)
            {'tag': 'div', 'attrs': {'data-section': re.compile(r'(description|detail)', re.I)}},
            # Fallback: section tag
            {'tag': 'section', 'attrs': {'class': re.compile(r'(description|detail|content)', re.I)}},
        ]
        
        # PRIORITY 2.5 (MOVED UP): Thử CSS selectors TRƯỚC heading patterns
        # Vì một số site như WooCommerce đã đóng gói description đẹp trong div với class cụ thể
        for selector in selectors_to_try:
            # Handle both 'attrs' dict format and direct parameters
            if 'attrs' in selector:
                tag = selector.get('tag', 'div')
                attrs = selector['attrs']
                # Convert attrs to keyword arguments
                elem = soup.find(tag, **attrs)
            else:
                elem = soup.find(**selector)
            
            if elem:
                text = elem.get_text(separator=' ', strip=True)
                # Need meaningful content (at least 200 chars for good description)
                if len(text) > 200:
                    description = text
                    break
                # If selector found but short (< 200), still use if nothing better found later
                elif len(text) > 100:
                    description = text
                    # Don't break - keep looking for longer content
        
        
        # PRIORITY 1: Thử tìm từ heading pattern (nếu chưa tìm được qua selector)
        # Tìm heading text với patterns như "Mô tả", "Description", etc.
        if not description or len(description) < 200:
            for heading in soup.find_all(['h2', 'h3', 'h4', 'h5', 'span', 'strong', 'b', 'div']):
                heading_text = heading.get_text(strip=True)
                
                # Skip nếu heading quá dài (likely navigation menu, không phải heading thực)
                if len(heading_text) > 500:
                    continue
                
                if any(re.search(pattern, heading_text, re.I) for pattern in heading_patterns):
                    # Strategy 1: Tìm parent container có thể chứa toàn bộ description
                    # Một số page (ví dụ MYPC) ghép text description vào cùng container với heading
                    container = heading.find_parent(['div', 'section', 'article', 'main']) or heading
                    content_parts = []
                    
                    # Thêm text từ heading element nếu nó dài hơn heading pattern
                    full_heading_text = heading.get_text(separator=' ', strip=True)
                    if len(full_heading_text) > 100:  # Có thể heading element chứa cả description
                        # Extract từ heading nhưng bỏ phần heading pattern
                        clean_text = re.sub(r'^(mô\s+tả|description|chi\s+tiết|thông\s+tin)[\s\-:]*', '', full_heading_text, flags=re.I, count=1)
                        if len(clean_text.strip()) > 50:
                            content_parts.append(clean_text)
                    
                    # Tìm siblings
                    current = heading.find_next_sibling()
                    max_siblings = 30
                    skip_count = 0
                    
                    while current and len(content_parts) < 20 and max_siblings > 0:
                        max_siblings -= 1
                        
                        # Skip certain elements
                        if current.name in ['table', 'form', 'script', 'style', 'noscript']:
                            current = current.find_next_sibling()
                            continue
                        
                        # Stop conditions
                        if current.name and current.name.startswith('h'):  # Gặp heading khác = stop
                            break
                        if current.name == 'div' and current.get('class'):
                            class_str = ' '.join(current.get('class', [])).lower()
                            # Skip div containers cho specs, pricing, related
                            if any(x in class_str for x in ['spec', 'price', 'related', 'sidebar', 'nav', 'footer', 'breadcrumb']):
                                current = current.find_next_sibling()
                                continue
                        
                        # Extract text
                        if current.name in ['p', 'div', 'h2', 'h3', 'h4', 'h5', 'blockquote', 'ul', 'ol', 'li']:
                            text = current.get_text(separator=' ', strip=True)
                            # Filter out short text, pure numbers, navigation
                            if (len(text.strip()) > 20 and 
                                not re.match(r'^[0-9\.\,\-\+\s]+$', text) and
                                not any(nav in text.lower() for nav in ['đăng nhập', 'đăng ký', 'giỏ hàng', 'tìm kiếm'])):
                                content_parts.append(text)
                                skip_count = 0  # Reset skip counter
                        else:
                            skip_count += 1
                            if skip_count > 5:  # Too many non-content siblings = stop
                                break
                        
                        current = current.find_next_sibling()
                    
                    if content_parts:  # Removed requirement for >= 2 parts
                        description = ' '.join(content_parts)
                        break
                    
                    # Strategy 2: Nếu Strategy 1 không work, tìm từ parent container với recursive
                    if not description or len(description) < 100:
                        container = heading.find_parent(['div', 'section', 'article']) or heading
                        content_parts = []
                        
                        for elem in container.find_all(['p', 'h2', 'h3', 'h4', 'blockquote', 'ul', 'ol', 'li'], recursive=True):
                            if elem != heading and elem not in heading.find_parents():
                                # Skip heading tags và tables
                                if elem.name and elem.name.startswith('h'):
                                    continue
                                if elem.name == 'table':
                                    continue
                                
                                text = elem.get_text(separator=' ', strip=True)
                                if (len(text.strip()) > 20 and 
                                    not re.match(r'^[0-9\.\,\-\+\s]+$', text)):
                                    content_parts.append(text)
                                
                                if len(content_parts) >= 20:
                                    break
                        
                        if content_parts:
                            description = ' '.join(content_parts[:20])
        

        # PRIORITY 2: Nếu chưa tìm được từ heading, parse TOÀN BỘ page text
        # Loại bỏ script, style, nav, footer, sidebar
        if not description or len(description) < 100:
            # Clone soup để không modify original
            soup_copy = BeautifulSoup(str(soup), 'html.parser')
            
            # Remove script, style, nav, footer, sidebar, etc.
            for tag in soup_copy(['script', 'style', 'meta', 'link', 'noscript', 'svg', 'path']):
                tag.decompose()
            
            # Remove common non-content elements
            try:
                for div in list(soup_copy.find_all('div')):  # Convert to list to avoid iterator issues
                    if not div or not div.name:  # Skip if decomposed
                        continue
                    class_str = ' '.join(div.get('class', [])).lower() if div.get('class') else ''
                    id_str = div.get('id', '').lower() if div.get('id') else ''
                    
                    # Skip navigation, footer, sidebar, breadcrumb, etc.
                    if any(x in (class_str + id_str) for x in ['nav', 'footer', 'sidebar', 'breadcrumb', 'menu', 'header', 'search', 'cart', 'comment', 'social', 'category', 'widget']):
                        div.decompose()
            except:
                pass  # If decomposition fails, continue
            
            # Extract all paragraphs and text
            content_parts = []
            for elem in soup_copy.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'li', 'blockquote', 'article', 'main']):
                text = elem.get_text(separator=' ', strip=True)
                
                # Skip category/navigation lists
                if any(nav in text.lower()[:100] for nav in ['danh mục', 'categories', 'sản phẩm', 'linh kiện', 'laptop –', 'giảm giá', 'khuyến mãi']):
                    if len(text) < 500:  # Only skip if short (category list)
                        continue
                
                # Filter
                if (len(text.strip()) > 20 and 
                    not re.match(r'^[0-9\.\,\-\+\s]+$', text) and
                    not any(nav in text.lower() for nav in ['đăng nhập', 'đăng ký', 'giỏ hàng', 'tìm kiếm', 'search', 'login', 'cart'])):
                    content_parts.append(text)
            
            # Lấy tối đa 50 đoạn text
            if content_parts:
                # Sắp xếp theo độ dài (ưu tiên những đoạn dài - likely content)
                content_parts = sorted(content_parts, key=len, reverse=True)[:50]
                description = ' '.join(content_parts)
        
        # PRIORITY 3: Fallback sang JSON-LD schema nếu HTML không đủ
        if not description or len(description) < 100:
            if hasattr(self, '_last_json_ld_desc') and self._last_json_ld_desc:
                description = self._last_json_ld_desc
        
        # Clean text
        if description:
            # Remove extra whitespace
            description = re.sub(r'\s+', ' ', description)
            # Remove breadcrumbs
            description = re.sub(r'Trang chủ\s*[/>].*?:\s*', '', description, flags=re.I)
            # Remove common noise
            description = re.sub(r'(Chia sẻ|Share|Like|Đánh giá|Review|Gửi bình luận|Liên hệ|Contact).*?$', '', description, flags=re.I)
            # Remove HTML entities if any
            description = description.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&amp;', '&')
            # Clean up - trim to 5000 chars (để lấy full mô tả chi tiết)
            # Note: For embedding, may need to chunk text if > 8191 tokens
            description = description.strip()[:5000]
        
        return description
    
    def _extract_category_from_html(self, soup, url: str) -> str:
        """
        Parse HTML để tìm category/breadcrumb - hỗ trợ nhiều cấu trúc khác nhau
        Tìm từ breadcrumb, schema.org, URL, hoặc HTML structure
        """
        category = ""
        
        # 1. Thử từ JSON-LD schema (category thường có trong Product schema)
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for json_ld in json_ld_scripts:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'Product':
                            data = item
                            break
                
                if isinstance(data, dict):
                    # Tìm category từ schema
                    if 'category' in data:
                        category = data['category']
                        if isinstance(category, dict):
                            category = category.get('name', '')
                        break
                    # Hoặc từ breadcrumb
                    if 'breadcrumb' in data:
                        breadcrumb = data['breadcrumb']
                        if isinstance(breadcrumb, dict):
                            items = breadcrumb.get('itemListElement', [])
                            if items and len(items) > 1:
                                # Lấy category từ second-to-last breadcrumb item
                                category = items[-2].get('name', '')
                        break
            except:
                pass
        
        if category:
            return category.strip()
        
        # 2. Thử từ breadcrumb HTML structure
        breadcrumb_selectors = [
            {'tag': 'nav', 'attrs': {'class': re.compile(r'breadcrumb', re.I)}},
            {'tag': 'div', 'attrs': {'class': re.compile(r'breadcrumb', re.I)}},
            {'tag': 'ol', 'attrs': {'class': re.compile(r'breadcrumb', re.I)}},
            {'tag': 'ul', 'attrs': {'class': re.compile(r'breadcrumb', re.I)}},
        ]
        
        for selector in breadcrumb_selectors:
            breadcrumb = soup.find(**selector)
            if breadcrumb:
                # Tìm tất cả links hoặc items trong breadcrumb
                items = breadcrumb.find_all(['a', 'li', 'span'])
                if items and len(items) >= 2:
                    # Thường category là item gần cuối (trước product name)
                    for item in reversed(items[:-1]):
                        text = item.get_text(strip=True)
                        # Bỏ "Home", "Trang chủ", numbers, etc.
                        if text and len(text) > 2 and not re.match(r'^\d+$', text):
                            if text.lower() not in ['home', 'trang chủ', 'all', 'shop']:
                                category = text
                                break
                if category:
                    break
        
        if category:
            return category.strip()
        
        # 3. Thử từ URL path
        # Pattern: /category/subcategory/product-name
        from urllib.parse import urlparse
        path = urlparse(url).path
        path_parts = [p for p in path.split('/') if p and p not in ['product', 'products']]
        
        if path_parts:
            # Lấy part gần cuối (trước product slug)
            # Thường có pattern: domain/category/subcategory/product-name
            if len(path_parts) >= 2:
                # Lấy second-to-last part
                category_slug = path_parts[-2]
                # Convert slug to readable format
                category = category_slug.replace('-', ' ').title()
            elif len(path_parts) == 1:
                category = path_parts[0].replace('-', ' ').title()
        
        # 4. Thử từ structured data attributes
        if not category:
            category_elem = soup.find(attrs={'itemtype': re.compile(r'Product|Thing', re.I)})
            if category_elem:
                category_meta = category_elem.find(attrs={'itemprop': 'category'})
                if category_meta:
                    category = category_meta.get_text(strip=True)
        
        # 5. Thử từ meta tags
        if not category:
            cat_meta = soup.find('meta', attrs={'name': re.compile(r'category|product-category', re.I)})
            if cat_meta:
                category = cat_meta.get('content', '').strip()
        
        # Clean category
        if category:
            # Remove extra whitespace
            category = re.sub(r'\s+', ' ', category)
            # Remove special chars
            category = category.replace('|', ' ').replace('>', ' ').strip()
            # Take first category if multiple separated by comma
            if ',' in category:
                category = category.split(',')[0].strip()
        
        return category.strip() if category else ""
    
    def _extract_original_price_from_html(self, soup, current_price: float) -> float:
        """
        Parse HTML để tìm giá gốc/giá khuyến mãi
        Khi JSON-LD không có priceBefore, tìm từ:
        - Strikethrough text (<del>, <s>, <strike>)
        - Old price badges
        - Discount percentage (tính ngược từ discount %)
        """
        original_price = 0
        
        if current_price <= 0:
            return 0
        
        # STRATEGY 1: Tìm strikethrough price (<del>, <s>, <strike>)
        for tag in soup.find_all(['del', 's', 'strike']):
            text = tag.get_text(strip=True)
            # Extract numbers
            numbers = re.findall(r'\d+(?:[.,]\d{3})*(?:[.,]\d{2})?', text.replace('.', '').replace(',', ''))
            if numbers:
                try:
                    price = float(numbers[-1])  # Lấy số cuối (likely price)
                    if price > current_price and price < 1e15:  # Giá gốc > giá hiện tại
                        original_price = price
                        break
                except:
                    pass
        
        # STRATEGY 2: Tìm "Old price" / "Original price" text nearby current price
        if not original_price:
            # Find price elements
            price_patterns = [
                {'class': re.compile(r'(price|giá|gia|cost)', re.I)},
                {'itemprop': 'price'},
                {'data-price': True}
            ]
            
            for pattern in price_patterns:
                price_elem = soup.find(attrs=pattern)
                if not price_elem:
                    continue
                
                # Look at siblings and nearby elements
                container = price_elem.find_parent(['div', 'section', 'article']) or price_elem
                
                for elem in container.find_all(['span', 'div', 'p']):
                    text = elem.get_text(strip=True)
                    
                    # Check if contains "old", "gốc", "gốc", "original"
                    if any(keyword in text.lower() for keyword in ['old price', 'original price', 'giá gốc', 'giá cũ', 'giá khuyến mãi trước']):
                        numbers = re.findall(r'\d+(?:[.,]\d{3})*(?:[.,]\d{2})?', text.replace('.', '').replace(',', ''))
                        if numbers:
                            try:
                                price = float(numbers[-1])
                                if price > current_price and price < 1e15:
                                    original_price = price
                                    break
                            except:
                                pass
        
        # STRATEGY 3: Tìm discount percentage và tính ngược giá gốc
        if not original_price:
            # Tìm text như "-20%", "Giảm 30%", etc.
            discount_text = soup.get_text()
            
            # Extract discount percentage
            discount_matches = re.findall(r'-(\d+)%|(?:giảm|sale|discount)\s*(\d+)\s*%', discount_text, re.I)
            
            if discount_matches:
                for match in discount_matches:
                    discount_pct = int(match[0] or match[1])
                    
                    # Tính giá gốc từ công thức: current_price = original_price * (1 - discount_pct/100)
                    # => original_price = current_price / (1 - discount_pct/100)
                    if discount_pct > 0 and discount_pct < 99:
                        calc_original = current_price / (1 - discount_pct / 100)
                        
                        # Sanity check: giá gốc hợp lý (không quá 10x giá hiện tại)
                        if calc_original > current_price and calc_original < current_price * 10:
                            original_price = calc_original
                            break
        
        # STRATEGY 4: Tìm trong price lists (multiple prices shown)
        if not original_price:
            # Tìm tất cả numbers giống kiểu giá trong page
            price_numbers = re.findall(r'\d+(?:[.,]\d{3})*(?:[.,]\d{2})?', soup.get_text())
            
            # Convert to floats
            prices = []
            for num_str in price_numbers:
                try:
                    price = float(num_str.replace('.', '').replace(',', ''))
                    if price > current_price * 0.5 and price < 1e15:  # Filter reasonable range
                        prices.append(price)
                except:
                    pass
            
            # Take largest price as likely original
            if prices:
                max_price = max(prices)
                if max_price > current_price and max_price < current_price * 5:
                    original_price = max_price
        
        return original_price
    
    def _extract_price_from_element(self, elem, elem_type="div/span"):
        """
        Helper method: Extract price từ HTML element
        Support multiple e-commerce formats:
        - "249,000đ" → 249000 (VND with currency)
        - "25.990.000₫" → 25990000 (European format)
        - "$19.99" → 19.99 (USD)
        - "€15,50" → 15.50 (Euro)
        
        Returns: float (price) hoặc None
        """
        if not elem:
            return None
        
        price_text = elem.get_text(strip=True)
        if not price_text:
            return None
        
        # Pattern 1: Try to extract price BEFORE currency symbol
        # Matches: "249,000đ", "$19.99", "€15,50", "₫25.990.000"
        match = re.search(r'(\d+(?:[.,]\d{3})*)\s*[đ$€₫¥]', price_text)
        if match:
            price_str = match.group(1).replace('.', '').replace(',', '')
            try:
                return float(price_str)
            except:
                pass
        
        # Pattern 2: Fallback - remove everything after currency symbol
        # Remove currency symbols and everything after them, then extract numbers
        price_text_clean = re.sub(r'[đ$€₫¥].*', '', price_text)
        numbers = re.findall(r'\d+', price_text_clean.replace('.', '').replace(',', ''))
        if numbers:
            try:
                return float(''.join(numbers))
            except:
                pass
        
        return None
    
    def extract_product(self, url: str) -> Dict:
        """Crawl và extract thông tin từ 1 product page - TỔNG QUÁT cho mọi site"""
        
        product = {
            'url': url,
            'title': '',
            'price': 0,
            'original_price': 0,
            'currency': 'VND',
            'sku': '',
            'brand': '',
            'category': '',
            'images': [],
            'description': '',
            'availability': ''
        }
        
        try:
            # Random delay để tránh pattern detection
            import random
            if Config.RANDOM_DELAY:
                delay = random.uniform(*Config.RANDOM_DELAY)
                time.sleep(delay)
            elif Config.RATE_LIMIT_DELAY > 0:
                time.sleep(Config.RATE_LIMIT_DELAY)
            
            try:
                resp = self.session.get(url, headers=self.headers, timeout=Config.TIMEOUT)
                resp.raise_for_status()
                html = resp.text
            except Exception as e:
                # Fallback to curl khi requests fail
                if '429' in str(e):
                    import subprocess
                    try:
                        result = subprocess.run(
                            ['curl', '-s', '-L', '-A', Config.USER_AGENT, url],
                            capture_output=True,
                            text=True,
                            timeout=Config.TIMEOUT
                        )
                        if result.returncode == 0 and result.stdout:
                            html = result.stdout
                        else:
                            raise e
                    except:
                        raise e
                else:
                    raise e
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. Extract JSON-LD Schema.org (chuẩn e-commerce toàn cầu)
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for json_ld in json_ld_scripts:
                try:
                    data = json.loads(json_ld.string)
                    
                    # Xử lý nếu là @graph structure
                    if isinstance(data, dict) and '@graph' in data:
                        for item in data['@graph']:
                            if isinstance(item, dict) and item.get('@type') == 'Product':
                                data = item
                                break
                    
                    # Xử lý nếu là array
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'Product':
                                data = item
                                break
                    
                    # Chỉ process nếu là Product schema
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        product['title'] = data.get('name', '')
                        product['sku'] = data.get('sku', '')
                        product['description'] = data.get('description', '')
                        # Save để dùng trong helper function
                        if product['description']:
                            self._last_json_ld_desc = product['description']
                        
                        # Brand
                        brand = data.get('brand', {})
                        if isinstance(brand, dict):
                            product['brand'] = brand.get('name', '')
                        elif isinstance(brand, str):
                            product['brand'] = brand
                        
                        # Category từ schema nếu có
                        if 'category' in data:
                            cat = data.get('category', '')
                            if isinstance(cat, dict):
                                product['category'] = cat.get('name', '')
                            else:
                                product['category'] = cat
                        
                        # Images
                        images = data.get('image', [])
                        image_urls = []
                        if isinstance(images, str):
                            image_urls = [images]
                        elif isinstance(images, list):
                            for img in images:
                                if isinstance(img, dict) and 'url' in img:
                                    # Extract URL từ ImageObject
                                    image_urls.append(img['url'])
                                elif isinstance(img, str):
                                    image_urls.append(img)
                        product['images'] = image_urls[:5]  # Lấy max 5 ảnh
                        
                        # Price từ offers
                        offers = data.get('offers', {})
                        if isinstance(offers, list) and offers:
                            offers = offers[0]
                        
                        if isinstance(offers, dict):
                            # Extract price
                            price_str = str(offers.get('price', '')).replace(',', '').replace('.', '')
                            if price_str:
                                try:
                                    product['price'] = float(price_str)
                                except:
                                    pass
                            
                            # Extract original price (để detect khuyến mãi)
                            if 'priceBefore' in offers:
                                orig_price_str = str(offers.get('priceBefore', '')).replace(',', '').replace('.', '')
                                if orig_price_str:
                                    try:
                                        product['original_price'] = float(orig_price_str)
                                    except:
                                        pass
                            elif offers.get('sameAs'):
                                # Một số site dùng sameAs cho original price
                                pass
                            
                            product['currency'] = offers.get('priceCurrency', 'VND')
                            
                            # Availability - convert URL sang text dễ đọc
                            avail = offers.get('availability', '')
                            if 'InStock' in avail:
                                product['availability'] = 'Còn hàng'
                            elif 'OutOfStock' in avail:
                                product['availability'] = 'Hết hàng'
                            elif 'PreOrder' in avail:
                                product['availability'] = 'Đặt trước'
                            else:
                                product['availability'] = avail
                        
                        break  # Đã tìm thấy Product schema
                except:
                    continue
            
            # 2. Fallback: Extract từ meta tags
            if not product['title']:
                og_title = soup.find('meta', property='og:title')
                if og_title:
                    product['title'] = og_title.get('content', '')
            
            # Fallback cho SKU - thử extract từ URL hoặc HTML
            if not product['sku']:
                # Pattern 1: SKU trong URL (ví dụ: --s250711016)
                sku_match = re.search(r'--s(\d+)', url)
                if sku_match:
                    product['sku'] = sku_match.group(1)
                else:
                    # Pattern 2: SKU trong HTML
                    sku_patterns = [
                        soup.find('span', {'itemprop': 'sku'}),
                        soup.find(string=re.compile(r'SKU[:|\s]', re.I)),
                        soup.find(attrs={'data-sku': True})
                    ]
                    for elem in sku_patterns:
                        if elem:
                            if hasattr(elem, 'get_text'):
                                sku_text = elem.get_text(strip=True)
                            elif hasattr(elem, 'strip'):
                                sku_text = elem.strip()
                            else:
                                sku_text = str(elem)
                            # Extract SKU number
                            sku_num = re.search(r'[\d]+', sku_text)
                            if sku_num:
                                product['sku'] = sku_num.group(0)
                                break
            
            # Fallback cho Brand - thử extract từ title hoặc HTML
            if not product['brand']:
                # Pattern 1: Brand có thể ở đầu title
                brand_patterns = [
                    soup.find('span', {'itemprop': 'brand'}),
                    soup.find('a', {'class': re.compile(r'brand', re.I)}),
                    soup.find('div', {'class': re.compile(r'brand', re.I)})
                ]
                for elem in brand_patterns:
                    if elem:
                        brand_text = elem.get_text(strip=True)
                        if brand_text and len(brand_text) < 50:
                            product['brand'] = brand_text
                            break
                
                # Pattern 2: Extract từ đầu title (thường brand đứng đầu)
                if not product['brand'] and product['title']:
                    # Lấy từ đầu tiên trong title (thường là brand)
                    first_word = product['title'].split()[0] if product['title'].split() else ''
                    # Chỉ lấy nếu là chữ in hoa hoặc CamelCase (điển hình của brand)
                    if first_word and (first_word.isupper() or (first_word[0].isupper() and any(c.isupper() for c in first_word[1:]))):
                        product['brand'] = first_word
                else:
                    title_tag = soup.find('title')
                    if title_tag:
                        product['title'] = title_tag.get_text(strip=True)
            
            if product['price'] == 0:
                # Tìm price meta tag
                price_meta = soup.find('meta', property='product:price:amount')
                if price_meta:
                    try:
                        product['price'] = float(price_meta.get('content', '0'))
                    except:
                        pass
            
            if not product['images']:
                og_image = soup.find('meta', property='og:image')
                if og_image:
                    product['images'] = [og_image.get('content', '')]
            
            # 3. Fallback cuối: Tìm price trong HTML (common patterns)
            if product['price'] == 0:
                price_patterns = [
                    {'class': 'price-detail'},  # Rabity.vn specific
                    {'class': re.compile(r'(price|giá|gia)', re.I)},
                    {'itemprop': 'price'},
                    {'data-price': True}
                ]
                
                for pattern in price_patterns:
                    price_elem = soup.find(attrs=pattern)
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        # Extract số trước "đ" hoặc "$" (VD: "249,000đ0đ-50%" → 249000, "25.990.000₫" → 25990000)
                        # First, extract price before currency symbols
                        match = re.search(r'(\d+(?:[.,]\d{3})*)\s*[đ$€₫]', price_text)
                        if match:
                            price_str = match.group(1).replace('.', '').replace(',', '')
                            try:
                                product['price'] = float(price_str)
                                break
                            except:
                                pass
                        else:
                            # Fallback: extract all numbers, remove those after currency
                            price_text_clean = re.sub(r'[đ$€₫].*', '', price_text)
                            numbers = re.findall(r'\d+', price_text_clean.replace('.', '').replace(',', ''))
                            if numbers:
                                try:
                                    product['price'] = float(''.join(numbers))
                                    break
                                except:
                                    pass
            
            # 3.5 Detect strikethrough/discount patterns - WooCommerce + other e-commerce
            # Cách phổ biến: <del>giá gốc</del> <ins>giá mới</ins> hoặc <s>giá gốc</s> <price>giá mới</price>
            # Luôn chạy để tìm original_price, ngay cả khi đã có price
            if True:  # Luôn detect để tìm original_price
                try:
                    # Pattern 1: <del> + <ins>
                    del_tags = soup.find_all('del')
                    ins_tags = soup.find_all('ins')
                    
                    if del_tags and ins_tags:
                        # Tìm original_price từ <del> nếu chưa có
                        if product['original_price'] == 0:
                            for del_tag in del_tags[:3]:
                                price_text = del_tag.get_text(strip=True)
                                if re.search(r'\d{3,}', price_text):
                                    numbers = re.findall(r'\d+', price_text)
                                    if numbers:
                                        try:
                                            potential_orig = float(''.join(numbers))
                                            if 100000 < potential_orig < 1e10:
                                                product['original_price'] = potential_orig
                                                break
                                        except:
                                            pass
                        
                        # Tìm current price từ <ins> nếu chưa có
                        if product['price'] == 0:
                            for ins_tag in ins_tags[:3]:
                                price_text = ins_tag.get_text(strip=True)
                                if re.search(r'\d{3,}', price_text):
                                    numbers = re.findall(r'\d+', price_text)
                                    if numbers:
                                        try:
                                            potential_price = float(''.join(numbers))
                                            if 100000 < potential_price < 1e10:
                                                product['price'] = potential_price
                                                break
                                        except:
                                            pass
                    
                    # Pattern 2: <s> (strikethrough) = original price
                    if product['original_price'] == 0:
                        s_tags = soup.find_all('s')
                        for s_tag in s_tags[:3]:
                            price_text = s_tag.get_text(strip=True)
                            if re.search(r'\d{3,}', price_text):
                                numbers = re.findall(r'\d+', price_text)
                                if numbers:
                                    try:
                                        potential_orig = float(''.join(numbers))
                                        if 100000 < potential_orig < 1e10:
                                            product['original_price'] = potential_orig
                                            break
                                    except:
                                        pass
                except:
                    pass
            
            # 3.5.5 AGGRESSIVE HTML PRICE EXTRACTION - For websites like Rabity
            # Tìm tất cả numbers có 5+ digits trong page (likely prices)
            if product['price'] == 0:
                try:
                    # Extract tất cả text từ page
                    page_text = soup.get_text()
                    # Find all numbers with 5+ digits (likely prices)
                    all_numbers = re.findall(r'\d{5,}', page_text.replace(',', '').replace('.', ''))
                    
                    if all_numbers:
                        # Convert to floats và filter by reasonable price range
                        potential_prices = []
                        for num_str in all_numbers:
                            try:
                                num = float(num_str)
                                if 50000 < num < 1e10:  # Reasonable price range (50k - 10 billion VND)
                                    potential_prices.append(num)
                            except:
                                pass
                        
                        if potential_prices:
                            # Thường giá đầu tiên hay thấy là giá hiện tại
                            product['price'] = min(potential_prices)
                except:
                    pass
            
            # 3.6 AI Fallback - dùng AI để phân tích pattern <del>/<ins> nếu chưa có original_price
            # Chạy để tìm original_price ngay cả khi đã có price (có thể không phải giá gốc)
            if Config.AI_EXTRACT_PRICES and self.ai_agent and product['original_price'] == 0:
                try:
                    ai_prices = self.ai_agent.extract_prices_with_ai(html, soup)
                    # Nếu AI tìm được original_price, hãy dùng nó
                    if ai_prices['original_price'] > 0:
                        product['original_price'] = ai_prices['original_price']
                    # Nếu chưa có price nhưng AI tìm được, dùng giá từ AI
                    elif ai_prices['price'] > 0 and product['price'] == 0:
                        product['price'] = ai_prices['price']
                except Exception as e:
                    pass  # Silent fail
            
            # 3.7 HTML Fallback - Parse HTML để tìm giá gốc nếu JSON-LD không có
            # Tương tự description extraction - dùng strikethrough, discount badge, etc.
            if product['original_price'] == 0 and product['price'] > 0:
                html_original_price = self._extract_original_price_from_html(soup, product['price'])
                if html_original_price > 0:
                    product['original_price'] = html_original_price
            
            # 4. Extract description chi tiết từ HTML
            # Always try to get full description from page - override JSON-LD short snippet
            extracted_desc = self._extract_description_from_html(soup, url)
            if extracted_desc and len(extracted_desc) > len(product.get('description', '')):
                product['description'] = extracted_desc
            
            # 5. Extract category từ HTML (breadcrumb, schema, URL, etc.)
            if not product['category']:
                extracted_cat = self._extract_category_from_html(soup, url)
                if extracted_cat:
                    product['category'] = extracted_cat
            
            # Final cleanup
            if product['description']:
                desc = product['description']
                desc = re.sub(r'Trang chủ\s*/[^:]+:\s*', '', desc, flags=re.I)
                # Removed overly aggressive regex that was truncating descriptions
                product['description'] = desc.strip()
        
        except Exception as e:
            print(f"    ⚠️ Lỗi: {str(e)[:50]}")
        
        return product
    
    def crawl(self, max_products: int = 10000):
        """Main crawl function - tối ưu hóa cho tốc độ"""
        
        # Lấy URLs từ sitemap
        all_urls = self.get_sitemap_urls()
        
        if not all_urls:
            return []
        
        product_urls = all_urls
        
        if not product_urls:
            return []
        
        # Crawl products - không print chi tiết
        products = []
        for i, url in enumerate(product_urls[:max_products], 1):
            product = self.extract_product(url)
            products.append(product)
        
        return products
        print(f"  Có images: {sum(1 for p in products if p['images'])}")
        
        print("\n" + "="*70)
        print("✅ HOÀN THÀNH!")
        print("="*70)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Cách dùng: python3 crawl.py <URL> [số_sản_phẩm] [--ai=openai|gemini|grok]")
        print("           python3 crawl.py <URL> --inspect  (xem cấu trúc sitemap)")
        print("\nVí dụ:")
        print("  python3 crawl.py https://phongvu.vn")
        print("  python3 crawl.py https://phongvu.vn --ai=gemini")
        print("  python3 crawl.py https://phongvu.vn 50 --ai=openai")
        print("  python3 crawl.py https://phongvu.vn --inspect")
        print("\nAI Providers:")
        print("  openai  → Cần OPENAI_API_KEY")
        print("  gemini  → Cần GEMINI_API_KEY hoặc GOOGLE_API_KEY")
        print("  grok    → Cần XAI_API_KEY")
        print("\nNếu không có API key, sẽ dùng heuristic fallback")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Parse arguments
    ai_provider = 'openai'
    max_products = 10000  # Mặc định crawl hết tất cả sản phẩm
    inspect_mode = False
    
    for arg in sys.argv[2:]:
        if arg == '--inspect':
            inspect_mode = True
        elif arg.startswith('--ai='):
            ai_provider = arg.split('=')[1]
        elif arg.isdigit():
            max_products = int(arg)
    
    crawler = SimpleSitemapCrawler(url, ai_provider=ai_provider)
    
    if inspect_mode:
        crawler.inspect_sitemap()
    else:
        crawler.crawl(max_products)
