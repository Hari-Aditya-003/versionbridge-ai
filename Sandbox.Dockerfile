FROM node:22-bookworm-slim AS node_runtime
RUN npm install --global --ignore-scripts --no-audit --no-fund typescript@5.9.3

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends g++ default-jdk-headless rustc golang-go postgresql \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pandas==2.2.3 numpy==2.2.6 pytest==8.3.5 pydantic==2.11.10 pydantic-settings==2.10.1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pytest_runner.py /opt/versionbridge/pytest_runner.py
COPY independent_tests.py independent_worker.py /opt/versionbridge/
COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node_runtime /usr/local/lib/node_modules/typescript /opt/versionbridge/typescript
