FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends chromium chromium-driver && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m scraper && mkdir -p /app/data && chown -R scraper:scraper /app
USER scraper
ENV CHROME_BINARY=/usr/bin/chromium CHROMEDRIVER=/usr/bin/chromedriver CHROME_NO_SANDBOX=1
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
