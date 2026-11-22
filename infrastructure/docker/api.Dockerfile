# Pinned base images and toolchain. No floating tags.
FROM ghcr.io/astral-sh/uv:0.10.7 AS uv
FROM python:3.12.12-slim

COPY --from=uv /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY migrations ./migrations
COPY agent-profiles ./agent-profiles
RUN uv sync --frozen --no-dev

EXPOSE 8100
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=2)"]

CMD ["/app/.venv/bin/karta-api"]
