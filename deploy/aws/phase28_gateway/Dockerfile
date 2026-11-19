# P28-14: diagnostic, fail-closed deployment only; NOT a serving gateway.
FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY requirements-p28-13.txt /build/requirements.txt
RUN python -m pip install --no-cache-dir --prefix=/install -r /build/requirements.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    AI_LIVE_INFERENCE=false AI_LIVE_INFERENCE_ACK=false
WORKDIR /app
COPY --from=builder /install /usr/local
COPY phase28/ /app/phase28/
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "phase28.container_entry:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
