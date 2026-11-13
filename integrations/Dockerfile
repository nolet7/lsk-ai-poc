FROM python:3.12-slim
WORKDIR /srv
RUN pip install --no-cache-dir "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "httpx>=0.27,<1" "boto3>=1.35,<2" "langgraph>=1,<2"
COPY integrations ./integrations
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8090
CMD ["uvicorn","integrations.gateway:app","--host","0.0.0.0","--port","8090"]
