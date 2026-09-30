import os
from pathlib import Path

ROOT = Path(__file__).parent
DATA = Path(os.getenv('HARVEST_DATA', str(ROOT / 'data')))
DB = DATA / 'harvest.sqlite3'
PUBLIC_ORIGIN = os.getenv('PUBLIC_ORIGIN', 'http://localhost:8000').rstrip('/')
PRODUCTION = os.getenv('HARVEST_ENV', 'development') == 'production'
COOKIE_SECURE = PRODUCTION or PUBLIC_ORIGIN.startswith('https://')
PROXY = os.getenv('BROWSER_PROXY', '')
DEMO_URL = os.getenv('DEMO_URL', 'http://demo.harvest.test/catalog.html')
MAX_JOB_SECONDS = int(os.getenv('MAX_JOB_SECONDS', '1800'))
SESSION_SECONDS = 8 * 60 * 60
RETENTION_DAYS = int(os.getenv('RETENTION_DAYS', '30'))

def validate():
    if not 1 <= RETENTION_DAYS <= 3650 or not 60 <= MAX_JOB_SECONDS <= 86400:
        raise RuntimeError('RETENTION_DAYS must be 1–3650 and MAX_JOB_SECONDS 60–86400.')
    if PRODUCTION:
        if not PUBLIC_ORIGIN.startswith('https://'):
            raise RuntimeError('Production requires PUBLIC_ORIGIN=https://your-host')
        if not PROXY:
            raise RuntimeError('Production requires BROWSER_PROXY')
        if os.getenv('CHROME_NO_SANDBOX') == '1':
            raise RuntimeError('Production refuses CHROME_NO_SANDBOX=1')
