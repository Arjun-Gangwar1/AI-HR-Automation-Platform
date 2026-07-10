FROM python:3.11-slim

WORKDIR /app

COPY src/ /app

RUN pip install --no-cache-dir \
  fastapi>=0.109.0 \
  uvicorn>=0.27.0 \
  pydantic>=2.6.0 \
  python-dotenv>=1.0.0 \
  requests>=2.31.0 \
  openai>=1.30.0 \
  "langchain>=0.3.0" \
  "langchain-openai>=0.2.0" \
  "langchain-core>=0.3.0" \
  "langgraph>=0.2.0" \
  click>=8.1.7

ENV PYTHONUNBUFFERED=1

CMD ["python", "__main__.py", "--host", "0.0.0.0", "--port", "5000"]
