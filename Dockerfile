FROM python:3.12-slim-bookworm
# System deps for Playwright's Chromium and Selenium's chromedriver
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium-driver ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libxkbcommon0 libpango-1.0-0 \
    libcairo2 libasound2 libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
# Install Playwright's own Chromium to a fixed path accessible by the scraper user
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
RUN playwright install chromium
RUN useradd --uid 10001 --create-home scraper && mkdir /app/data && chown scraper:scraper /app/data
VOLUME /app/data
COPY --chown=scraper:scraper . .
USER scraper
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    CHROMEDRIVER=/usr/bin/chromedriver \
    CHROME_NO_SANDBOX=1
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000","--no-proxy-headers","--limit-concurrency","100","--timeout-keep-alive","5"]
