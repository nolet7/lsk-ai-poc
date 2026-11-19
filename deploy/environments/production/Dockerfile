FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home-dir /nonexistent app
COPY requirements-p28-13.txt /app/
COPY deploy/environments/production/requirements.txt /app/prod-requirements.txt
RUN python -m pip install --no-cache-dir -r requirements-p28-13.txt -r prod-requirements.txt
COPY phase28/ /app/phase28/
USER 10001:10001
EXPOSE 8081
CMD ["uvicorn", "phase28.production_app:from_environment", "--factory", "--host", "0.0.0.0", "--port", "8081", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", ""]
