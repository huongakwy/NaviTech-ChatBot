# Dùng Python 3.12 slim
FROM python:3.12-slim

# Copy requirements trước để tối ưu layer cache
COPY requirements.txt .

# Cài dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Cài uvicorn nếu chưa có trong requirements.txt
RUN pip install --no-cache-dir uvicorn[standard]

# Copy toàn bộ code (bao gồm app.py) vào container
COPY . .

# Khai báo biến môi trường (có thể override từ .env hoặc docker-compose)
ARG FASTAPI_PORT=8000
ENV FASTAPI_PORT=${FASTAPI_PORT}

# Expose port runtime
EXPOSE ${FASTAPI_PORT}

# Chạy FastAPI với port lấy từ biến môi trường
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $FASTAPI_PORT"]
