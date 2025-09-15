FROM python:3.11-slim

# System deps for headless browsers
RUN apt-get update && apt-get install -y \
    curl ca-certificates xvfb fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock* requirements*.txt* /app/
# Pick one of these depending on your toolchain:
# RUN pip install -r requirements.txt
# or:
# RUN pip install uv && uv pip install --system --no-cache .

COPY . /app

# If using Playwright:
# RUN pip install playwright && playwright install --with-deps chromium

ENV PORT=8000
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]