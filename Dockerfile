# syntax=docker/dockerfile:1

# Use a slim Python 3.11 base to match the locked dependency set.
FROM python:3.11-slim

# Keep Python output unbuffered and skip writing bytecode and pip caches into the image.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf-cache

WORKDIR /app

# Create an unprivileged user; the API never runs as root.
RUN useradd --create-home --uid 10001 appuser

# Install the locked dependencies. The CPU PyTorch index is consulted so pip
# selects the CPU build of torch instead of the much larger CUDA build.
COPY requirements.txt .
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt \
 && python -c "import torch, sys; sys.exit(0 if '+cpu' in torch.__version__ else 'expected CPU torch, got ' + torch.__version__)"

# Bake the embedding model into the image so containers start offline and deterministically.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the application source last so code changes do not invalidate the dependency layers.
COPY . .

# Prepare writable data directories; the document folder stays read-only at runtime.
RUN mkdir -p /app/data/chroma_db /app/data/outputs \
 && chown -R appuser:appuser /app/data

# Run the platform without network access to model hubs.
ENV HF_HUB_OFFLINE=1

USER appuser

EXPOSE 8000

# Liveness probe: the process must answer GET /health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

# Use a single worker: the embedding model and ChromaDB client are per process,
# and scaling is better done with replicas behind a load balancer.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
