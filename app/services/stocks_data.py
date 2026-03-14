import os
import time
import requests
from datetime import datetime, timedelta

ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"

_CACHE = {}


def _get_cached(key, ttl_seconds):
    cached = _CACHE.get(key)
    if not cached:
        return None
    if time.time() - cached["ts"] > ttl_seconds:
        return None
    return cached["data"]


def _set_cache(key, data):
    _CACHE[key] = {"ts": time.time(), "data": data}


def _alpha_vantage_get(params, cache_key, ttl_seconds=900):
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached

    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        return {"error": "Missing ALPHA_VANTAGE_KEY"}

    params = {**params, "apikey": api_key}
    try:
        resp = requests.get(ALPHA_VANTAGE_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return {"error": f"Alpha Vantage request failed: {exc}"}

    if "Note" in data:
        return {"error": data.get("Note")}
    if "Information" in data:
        return {"error": data.get("Information")}

    _set_cache(cache_key, data)
    return data


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _format_market_cap(value):
    if value is None:
        return "N/A"
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return str(value)


def get_company_overview(symbol):
    return _alpha_vantage_get(
        {"function": "OVERVIEW", "symbol": symbol},
        cache_key=f"overview:{symbol}",
        ttl_seconds=21600,
    )


def get_global_quote(symbol):
    return _alpha_vantage_get(
        {"function": "GLOBAL_QUOTE", "symbol": symbol},
        cache_key=f"quote:{symbol}",
        ttl_seconds=900,
    )


def get_cash_flow(symbol):
    return _alpha_vantage_get(
        {"function": "CASH_FLOW", "symbol": symbol},
        cache_key=f"cashflow:{symbol}",
        ttl_seconds=21600,
    )


def get_daily_series(symbol):
    return _alpha_vantage_get(
        {"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact"},
        cache_key=f"daily:{symbol}",
        ttl_seconds=21600,
    )


def _compute_fcf_ratio(market_cap, cash_flow_payload):
    if market_cap is None or not cash_flow_payload or "annualReports" not in cash_flow_payload:
        return None

    reports = cash_flow_payload.get("annualReports") or []
    if not reports:
        return None

    latest = reports[0]
    operating_cashflow = _to_float(latest.get("operatingCashflow"))
    capital_expenditures = _to_float(latest.get("capitalExpenditures"))

    if operating_cashflow is None or capital_expenditures is None:
        return None

    if capital_expenditures > 0:
        capital_expenditures = -capital_expenditures

    free_cash_flow = operating_cashflow + capital_expenditures
    if free_cash_flow <= 0:
        return None

    return market_cap / free_cash_flow


def build_company_snapshot(symbol, sector_override=None):
    """Fetch company data with smart MongoDB caching. Only API calls if snapshot is stale."""
    from app.services.mongo_price import get_cached_stock_snapshot, save_stock_snapshot
    
    # Check if we have a fresh cached snapshot (same day)
    cached = get_cached_stock_snapshot(symbol)
    if cached:
        updated_at = cached.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        if updated_at and updated_at.date() == datetime.now().date():
            print(f"[Bookopedia] Using cached snapshot for {symbol}")
            return cached, None
    
    # Cache is stale or missing — fetch from API
    print(f"[Bookopedia] Fetching fresh data for {symbol} from Alpha Vantage...")
    overview = get_company_overview(symbol)
    if "error" in overview:
        if cached:
            print(f"[Bookopedia] API failed for {symbol}, using stale cache")
            return cached, overview["error"]
        # No cache at all — return a skeleton row so the company still shows
        return {
            "name": symbol, "ticker": symbol,
            "sector": sector_override or "Energy", "country": "USA",
            "price": None, "market_cap": "N/A", "pe": None,
            "forward_pe": None, "price_to_book": None, "price_to_fcf": None,
            "ev_to_ebitda": None, "dividend_yield": None, "roe": None,
            "low_52": None, "high_52": None, "range_percent": None,
            "latest_trading_day": None, "_pending": True,
        }, overview["error"]

    quote = get_global_quote(symbol)
    if "error" in quote:
        if cached:
            return cached, quote["error"]
        return {
            "name": overview.get("Name") or symbol, "ticker": symbol,
            "sector": sector_override or overview.get("Sector") or "Energy",
            "country": overview.get("Country") or "USA",
            "price": None, "market_cap": _format_market_cap(_to_int(overview.get("MarketCapitalization"))),
            "pe": _to_float(overview.get("PERatio")),
            "forward_pe": _to_float(overview.get("ForwardPE")),
            "price_to_book": _to_float(overview.get("PriceToBookRatio")),
            "price_to_fcf": None,
            "ev_to_ebitda": _to_float(overview.get("EVToEBITDA")),
            "dividend_yield": _to_float(overview.get("DividendYield")),
            "roe": _to_float(overview.get("ReturnOnEquityTTM")),
            "low_52": _to_float(overview.get("52WeekLow")),
            "high_52": _to_float(overview.get("52WeekHigh")),
            "range_percent": None, "latest_trading_day": None, "_pending": True,
        }, quote["error"]

    # Fetch cash flow — non-blocking: if it fails, P/FCF just shows as N/A
    cashflow = get_cash_flow(symbol)
    cashflow_error = cashflow.get("error") if cashflow else None
    if cashflow_error:
        print(f"[Bookopedia] Cash flow unavailable for {symbol} ({cashflow_error}), P/FCF will be N/A")

    quote_data = quote.get("Global Quote", {})

    price = _to_float(quote_data.get("05. price"))
    latest_trading_day = quote_data.get("07. latest trading day")

    market_cap = _to_int(overview.get("MarketCapitalization"))
    pe_ratio = _to_float(overview.get("PERatio"))
    price_to_book = _to_float(overview.get("PriceToBookRatio"))
    low_52 = _to_float(overview.get("52WeekLow"))
    high_52 = _to_float(overview.get("52WeekHigh"))

    range_percent = None
    if price is not None and low_52 is not None and high_52 is not None and high_52 > low_52:
        range_percent = max(0.0, min(100.0, (price - low_52) / (high_52 - low_52) * 100))

    price_to_fcf = None if cashflow_error else _compute_fcf_ratio(market_cap, cashflow)

    dividend_yield = _to_float(overview.get("DividendYield"))
    ev_to_ebitda   = _to_float(overview.get("EVToEBITDA"))
    roe            = _to_float(overview.get("ReturnOnEquityTTM"))
    forward_pe     = _to_float(overview.get("ForwardPE"))

    snapshot = {
        "name": overview.get("Name") or symbol,
        "ticker": symbol,
        "sector": sector_override or overview.get("Sector") or "Energy",
        "country": overview.get("Country") or "USA",
        "price": price,
        "market_cap": _format_market_cap(market_cap),
        "pe": pe_ratio,
        "forward_pe": forward_pe,
        "price_to_book": price_to_book,
        "price_to_fcf": price_to_fcf,
        "ev_to_ebitda": ev_to_ebitda,
        "dividend_yield": dividend_yield,
        "roe": roe,
        "low_52": low_52,
        "high_52": high_52,
        "range_percent": range_percent,
        "latest_trading_day": latest_trading_day,
    }
    
    # Save to MongoDB
    save_stock_snapshot(symbol, snapshot)
    
    return snapshot, None


def build_energy_chart(range_param="30d", symbol="XLE"):
    """Fetch XLE chart data: first check MongoDB, only fetch API if missing today's data.
    If last date in MongoDB is older than today, fetches ALL missing dates from API.
    """
    from app.services.mongo_price import get_price_history, get_latest_price_date, save_price_history
    
    range_map = {
        "7d": 7,
        "30d": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365,
        "5y": 1825,
    }
    days = range_map.get(range_param, 30)
    start_date = datetime.now().date() - timedelta(days=days)
    today = datetime.now().date()

    # Check if we have data up to the most recent market day in MongoDB
    latest_db_date = get_latest_price_date(symbol)
    stale_cutoff = today - timedelta(days=3)
    needs_api_fetch = latest_db_date is None or latest_db_date < stale_cutoff
    
    if needs_api_fetch:
        if latest_db_date:
            print(f"[Bookopedia] Last price for {symbol} in MongoDB is {latest_db_date}. Today is {today}. Fetching from API...")
        else:
            print(f"[Bookopedia] No price data for {symbol} in MongoDB. Fetching from API...")
        
        try:
            series = get_daily_series(symbol)
            if "error" in series:
                # Try to use stale MongoDB data if API fails
                db_prices = get_price_history(symbol, start_date=start_date)
                if db_prices:
                    print(f"[Bookopedia] API failed for {symbol}, using stale cached data.")
                    labels = [p['date'].strftime('%Y-%m-%d') if hasattr(p['date'], 'strftime') else str(p['date']) for p in db_prices]
                    prices = [p['price'] for p in db_prices]
                    return {"labels": labels, "prices": prices}, None
                return None, series["error"]
            
            time_series = series.get("Time Series (Daily)") or {}
            if time_series:
                # This saves ALL dates returned by API (typically last 100 days)
                # So it fills in all gaps from last_db_date to today
                save_price_history(symbol, time_series)
                print(f"[Bookopedia] Backfilled {len(time_series)} trading days for {symbol}.")
        except Exception as e:
            print(f"[Bookopedia] Error fetching/saving {symbol} data: {e}")
            # Try to use stale MongoDB data if API fails
            db_prices = get_price_history(symbol, start_date=start_date)
            if db_prices:
                print(f"[Bookopedia] Using stale cached data after error.")
                labels = [p['date'].strftime('%Y-%m-%d') if hasattr(p['date'], 'strftime') else str(p['date']) for p in db_prices]
                prices = [p['price'] for p in db_prices]
                return {"labels": labels, "prices": prices}, None
            return None, f"Error fetching data: {str(e)}"
    
    # Always load from MongoDB (fresh if just updated, cached if not)
    db_prices = get_price_history(symbol, start_date=start_date)
    if not db_prices:
        return None, "No price data available"
    
    labels = []
    prices = []
    for p in db_prices:
        date_obj = p['date']
        # Handle both datetime and date objects
        if isinstance(date_obj, datetime):
            labels.append(date_obj.strftime('%Y-%m-%d'))
        else:
            labels.append(str(date_obj))
        prices.append(p['price'])
    
    return {"labels": labels, "prices": prices}, None


def build_sector_snapshot(symbol="XLE"):
    """Build sector snapshot with smart MongoDB caching."""
    from app.services.mongo_price import get_latest_price_date, get_price_history, save_price_history
    
    today = datetime.now().date()
    latest_db_date = get_latest_price_date(symbol)
    stale_cutoff = today - timedelta(days=3)
    needs_api_fetch = latest_db_date is None or latest_db_date < stale_cutoff
    
    if needs_api_fetch:
        print(f"[Bookopedia] Fetching sector snapshot data for {symbol}...")
        series = get_daily_series(symbol)
        if "error" not in series:
            time_series = series.get("Time Series (Daily)") or {}
            if time_series:
                save_price_history(symbol, time_series)
    
    # Get latest 2 days from MongoDB
    db_prices = get_price_history(symbol)
    if not db_prices or len(db_prices) < 2:
        return None, "Not enough data for sector snapshot"
    
    latest = db_prices[-1]
    prev = db_prices[-2]
    
    latest_close = latest.get('price')
    prev_close = prev.get('price')
    
    if latest_close is None or prev_close is None:
        return None, "Missing close prices"
    
    change_pct = ((latest_close - prev_close) / prev_close) * 100
    
    as_of = latest.get('date')
    if hasattr(as_of, 'strftime'):
        as_of = as_of.strftime('%Y-%m-%d')

    return {
        "label": f"Energy Sector ({symbol})",
        "value": f"${latest_close:,.2f}",
        "subtext": "Close",
        "trend_class": "green" if change_pct >= 0 else "red",
        "trend_text": f"{change_pct:+.2f}% 1d",
        "as_of": as_of,
    }, None


def build_oil_gas_table(tickers, sector_map=None, country_map=None):
    sector_map  = sector_map  or {}
    country_map = country_map or {}
    results = []
    errors = []
    as_of = None

    # All keys the template expects — ensures old cached docs don't crash Jinja
    DEFAULTS = {
        "name": None, "ticker": None, "sector": "Energy", "country": "USA",
        "price": None, "market_cap": "N/A", "pe": None, "forward_pe": None,
        "price_to_book": None, "price_to_fcf": None, "ev_to_ebitda": None,
        "dividend_yield": None, "roe": None,
        "low_52": None, "high_52": None, "range_percent": None,
        "latest_trading_day": None, "_pending": False,
    }

    for symbol in tickers:
        snapshot, err = build_company_snapshot(symbol, sector_override=sector_map.get(symbol))
        if err:
            errors.append(f"{symbol}: {err}")
        if snapshot is None:
            row = {**DEFAULTS, "name": symbol, "ticker": symbol,
                   "sector": sector_map.get(symbol, "Energy"),
                   "country": country_map.get(symbol, "USA"), "_pending": True}
        else:
            # Merge with defaults so any missing key from old cache is filled in
            row = {**DEFAULTS, **snapshot}
            if symbol in country_map:
                row["country"] = country_map[symbol]
        results.append(row)
        if not as_of and row.get("latest_trading_day"):
            as_of = row["latest_trading_day"]

    return results, errors, as_of
