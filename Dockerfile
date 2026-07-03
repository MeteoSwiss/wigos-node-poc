FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OSCAR_NODE_DATA_DIR=/app/data/records

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY node ./node
COPY README.md ./README.md
RUN mkdir -p /app/data/records

EXPOSE 8000
CMD ["uvicorn", "node.app:app", "--host", "0.0.0.0", "--port", "8000"]
