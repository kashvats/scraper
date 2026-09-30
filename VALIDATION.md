# Validation — visual picker update

Passed:
- Five Python tests: nested traversal/pagination/deduplication; page limits/cancellation; URL/column validation; CSV/XLSX exports and request boundaries; picker API validation and expired sessions.
- DOM tests: exact selection of the second repeated price, similar product links, enclosing-element selection, absolute image/link URLs.
- UI logic tests in JSDOM: selection-to-column mapping with a custom name and image attribute, duplicate-column prevention, switching to a nested-link rule.
- Python compilation and JavaScript syntax checks.

Not verified end-to-end here:
- Live browser launch, screenshots, remote mouse interaction, and rendered UI. The development environment blocks Chromium's socket operation (`Operation not permitted`). DOM/UI tests use JSDOM and controlled data, not a real browser.
- Docker build/run and third-party website scraping.

Local acceptance:
1. Run `docker compose up --build`; open http://localhost:8000.
2. Click Load sample catalog. The website should appear in the app's browser view.
3. Select Next, choose Next-page link, and save it.
4. Select View product 1, choose Follow similar links, preview (two matching links), then Save links & open one.
5. Click the heading, enter Product Name, and Add column. Click the price, enter Price, and Add column.
6. Run with Playwright. Expect six visited pages, four product rows, and the column names you chose in CSV/XLSX.
7. Repeat the scrape with Selenium using the same mapped columns.
8. Test scroll, Browse mode, Back, custom column names, image attributes, and Close site view on a permitted real website.
