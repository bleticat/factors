FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

# Install dependencies first so this layer stays cached across builds unless
# pyproject.toml/uv.lock actually change.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY . .
RUN uv sync --locked

EXPOSE 8000

# docker-compose.yml overrides this with a migrate-then-serve command for
# local dev (with --reload); this CMD is the plain fallback if the image is
# run standalone.
CMD ["uv", "run", "uvicorn", "factors.entrypoints.server:app", "--host", "0.0.0.0", "--port", "8000"]
