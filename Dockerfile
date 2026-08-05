FROM scratch
WORKDIR /app
COPY image-rootfs/ /
COPY . /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 WIGOS_NODE_DATA_DIR=/tmp/wigos-node/records
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 8888
CMD ["python", "-m", "uvicorn", "node.app:app", "--host", "0.0.0.0", "--port", "8888", "--root-path", ""]
