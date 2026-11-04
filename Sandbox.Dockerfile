FROM python:3.12-slim
RUN pip install --no-cache-dir pandas==2.2.3 numpy==2.2.6 pytest==8.3.5 pydantic==2.11.10 pydantic-settings==2.10.1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
