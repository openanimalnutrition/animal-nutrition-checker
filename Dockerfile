# The GUI and MCP server (plan, "Server and hosting"). The core needs only the standard
# library; the server needs Python 3.10+ for the MCP SDK, so it runs here, not on the host.
# Base image pinned by digest; packages installed only from the hashed lock.
FROM python:3.12-slim@sha256:cb33f7f771ecec2ef1225cf39b159591a040391bd73e4c01f00fdfc4c47611d2 AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY server/requirements.lock server/requirements.lock
RUN pip install --require-hashes --no-deps -r server/requirements.lock
COPY oan oan
COPY data data
COPY docs/result.schema.json docs/result.schema.json
COPY server server
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin oan
USER 10001
EXPOSE 8790
CMD ["python", "-I", "-B", "-m", "uvicorn", "--app-dir", "/app/server", "app:app", \
     "--host", "0.0.0.0", "--port", "8790", "--no-access-log", "--no-server-header", \
     "--limit-concurrency", "16", "--timeout-keep-alive", "5"]

# The contract tests (plan, "Verification"): the same image plus the tests.
FROM runtime AS test
COPY tests/contract tests/contract
CMD ["python", "-I", "-B", "tests/contract/test_server.py"]
