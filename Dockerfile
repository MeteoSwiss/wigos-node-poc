FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OSCAR_NODE_DATA_DIR=/tmp/oscar-node/records

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY node ./node
COPY README.md ./README.md

RUN mkdir -p /tmp/oscar-node/records \
    && chmod -R a+rX /app \
    && chmod -R a+rwX /tmp/oscar-node

EXPOSE 8888

CMD ["sh", "-c", "python -m uvicorn node.app:app --host 0.0.0.0 --port ${PORT:-8888} --root-path \"${RENKU_BASE_URL_PATH:-}\""]
