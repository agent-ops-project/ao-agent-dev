# Backend Python Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY src/ /app/src/
COPY pyproject.toml /app/
RUN pip install --upgrade pip && pip install -e . \
	&& pip install fastapi uvicorn[standard] python-dotenv requests
# Expose auth FastAPI port (5958) and the develop server port (5959)
EXPOSE 5958
EXPOSE 5959
# Run both the auth FastAPI (uvicorn) and the existing main_server
CMD ["sh", "-c", "uvicorn src.server.auth_app:app --host 0.0.0.0 --port 5958 & python -m src.server.main_server"]
