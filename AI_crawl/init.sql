-- Create products table in public schema
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    website_id INTEGER DEFAULT 0,
    website_name VARCHAR(255),
    url VARCHAR(1000) NOT NULL UNIQUE,
    title VARCHAR(500),
    price FLOAT DEFAULT 0,
    original_price FLOAT DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'VND',
    sku VARCHAR(255),
    brand VARCHAR(255),
    category VARCHAR(255),
    description TEXT,
    availability VARCHAR(100),
    images TEXT,  -- JSON string, not array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alter existing column if it's array type
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'images' AND data_type = 'ARRAY'
    ) THEN
        ALTER TABLE products ALTER COLUMN images TYPE TEXT;
    END IF;
END $$;-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_products_url ON products(url);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_website_id ON products(website_id);
CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
