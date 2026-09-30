FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends chromium chromium-driver ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
RUN useradd --uid 10001 --create-home scraper && mkdir /app/data && chown scraper:scraper /app/data
VOLUME /app/data
COPY --chown=scraper:scraper . .
USER scraper
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CHROME_BINARY=/usr/bin/chromium CHROMEDRIVER=/usr/bin/chromedriver CHROME_NO_SANDBOX=0
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000","--no-proxy-headers","--limit-concurrency","100","--timeout-keep-alive","5"]
