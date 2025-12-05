import psycopg2
from psycopg2.extras import RealDictCursor

def query_postgres(query: str, params: tuple = None):
    """
    Truy vấn PostgreSQL (SELECT, INSERT, UPDATE, DELETE).
    Tự động trả kết quả dạng list[dict] nếu có dữ liệu.
    """
    connection = None
    try:
        connection = psycopg2.connect(
            host="localhost",
            port="5431",
            database="chatbot",
            user="postgres",
            password="mypassword"
        )
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            
            # Nếu là SELECT → trả kết quả
            if query.strip().lower().startswith("select"):
                return cursor.fetchall()
            else:
                connection.commit()
                return {"status": "success"}

    except Exception as e:
        print("❌ Error executing query:", e)
        return {"status": "error", "message": str(e)}

    finally:
        if connection:
            connection.close()


# SELECT
rows = query_postgres("SELECT * FROM product WHERE url = %s", ("https://example.com/p1",))
print(rows)

# INSERT
# query_postgres("INSERT INTO users (id, name, email) VALUES (gen_random_uuid(), %s, %s)", ("A", "a@example.com"))