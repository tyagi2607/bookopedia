# Bookopedia

**Where we visualize freely available data to reveal patterns.**

Bookopedia is an open data encyclopedia — a collection of interactive dashboards and visualizations built from publicly available data. Our mission is to democratize data, making complex information accessible, visual, and understandable for everyone.

---

## Sections

### Section I: Coinbook
Cryptocurrency metrics, charts, and analysis.
- **Chapter 1: Bitcoin** — Live price, market cap, volume, supply, and interactive price history chart.

### Section II: Industry Stock Analysis
Sector-level stock data and trends.
- **Oil & Gas** — *(Coming soon)* Stock performance, crude oil correlation, sector ETF analysis.

---

## Tech Stack
- **Frontend:** HTML5, CSS3, Jinja2 Templates, Chart.js
- **Backend:** Python, Flask 3.1.0
- **Database:** MongoDB (caching & price history)
- **APIs:** CoinGecko (cryptocurrency data)
- **Deployment:** Render.com

## Project Structure
```
bookopedia/
  run.py                    # App entry point
  requirements.txt
  app/
    __init__.py             # Flask app factory
    routes/
      main.py               # Home page
      coinbook.py            # Coinbook section (Bitcoin, etc.)
      stocks.py              # Stock analysis section
    services/
      coins.py               # BTC data fetching + caching
      mongo_price.py          # MongoDB integration
    static/
      style.css              # Book/encyclopedia theme
    templates/
      base.html              # Shared layout with sidebar
      home.html              # Landing page
      coinbook/
        bitcoin.html         # Bitcoin dashboard
      stocks/
        oil_gas.html         # Oil & Gas placeholder
```

## Running Locally
```bash
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python run.py
```

## License
Open source. Data sourced from freely available public APIs.
