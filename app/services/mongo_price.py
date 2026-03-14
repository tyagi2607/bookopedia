import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime, timedelta, date
import time

MONGO_URI = os.getenv('MONGO_URI')  # Set via environment variable — see .env.example
DB_NAME = 'bookopedia'
PRICE_HISTORY_COLLECTION = 'daily_prices'
BTC_METRICS_COLLECTION = 'crypto_metrics'
CRYPTO_METRICS_HISTORY_COLLECTION = 'crypto_metrics_history'
STOCK_SNAPSHOT_COLLECTION = 'stock_snapshots'

try:
    if not MONGO_URI:
        raise ValueError("MONGO_URI not set — running without MongoDB. Set env var to enable caching.")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
    # Lazy connection - don't ping on startup
    db = client[DB_NAME]
    collection = db[PRICE_HISTORY_COLLECTION]
    metrics_collection = db[BTC_METRICS_COLLECTION]
    stock_snapshot_collection = db[STOCK_SNAPSHOT_COLLECTION]
    crypto_metrics_history_collection = db[CRYPTO_METRICS_HISTORY_COLLECTION]
    # Create indexes for efficient queries (this will attempt connection)
    try:
        collection.create_index('ticker')
        collection.create_index('date')
        collection.create_index([('ticker', 1), ('date', 1)])
        crypto_metrics_history_collection.create_index('coin')
        crypto_metrics_history_collection.create_index('date')
        crypto_metrics_history_collection.create_index([('coin', 1), ('date', 1)])
        MONGO_AVAILABLE = True
        print("[Bookopedia] MongoDB Atlas connected successfully.")
    except Exception as e:
        MONGO_AVAILABLE = False
        print(f"[Bookopedia] MongoDB indexes failed: {e}. Continuing without MongoDB.")
except (ConnectionFailure, ServerSelectionTimeoutError, ValueError, Exception) as e:
    MONGO_AVAILABLE = False
    collection = None
    metrics_collection = None
    stock_snapshot_collection = None
    crypto_metrics_history_collection = None
    print(f"[Bookopedia] MongoDB not available ({e}). Using direct API mode.")


def save_price_history(ticker, prices):
    """Save daily prices to MongoDB. Handles multiple formats:
    - list of [timestamp_ms, price] pairs
    - dict of {date_str: {ohlcv}} (Alpha Vantage format)
    - list of dicts with 'date' and 'price' keys
    
    ticker: optional, defaults to 'BTC' for Bitcoin compatibility
    """
    # Handle being called with (prices) for Bitcoin - it's the old API
    if isinstance(ticker, (list, dict)) and prices is None:
        ticker = 'BTC'
        prices = ticker
        # Actually ticker was the first positional arg which was prices
        prices = ticker
    
    # If ticket doesn't look like a real ticker, it's probably prices
    if not isinstance(ticker, str) or len(ticker) > 10:
        ticker_safe = 'BTC'
        prices = ticker
        ticker = ticker_safe
    
    if not MONGO_AVAILABLE:
        return
    try:
        docs = []
        
        if isinstance(prices, dict):
            # Handle Alpha Vantage Time Series format: {"YYYY-MM-DD": {"4. close": "123.45", ...}}
            for date_str, ohlcv in prices.items():
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    close_price = float(ohlcv.get('4. close', ohlcv.get('close', 0)))
                    docs.append({
                        'ticker': ticker,
                        'date': date_obj,
                        'price': close_price
                    })
                except (ValueError, KeyError, TypeError):
                    continue
        else:
            # Handle list format
            for p in prices:
                try:
                    if isinstance(p, (list, tuple)) and len(p) >= 2:
                        # Check if first element is timestamp (number) or date string
                        if isinstance(p[0], (int, float)):
                            date_obj = datetime.fromtimestamp(p[0] / 1000)
                        elif isinstance(p[0], str):
                            date_obj = datetime.strptime(p[0], '%Y-%m-%d')
                        else:
                            continue
                        price = float(p[1])
                    elif isinstance(p, dict):
                        date_val = p.get('date')
                        if isinstance(date_val, str):
                            date_obj = datetime.strptime(date_val, '%Y-%m-%d')
                        else:
                            date_obj = date_val
                        price = float(p.get('price', p.get('close', 0)))
                    else:
                        continue
                    docs.append({
                        'ticker': ticker,
                        'date': date_obj,
                        'price': price
                    })
                except (ValueError, TypeError, AttributeError):
                    continue
        
        if docs:
            for doc in docs:
                collection.update_one(
                    {'ticker': ticker, 'date': doc['date']},
                    {'$set': doc},
                    upsert=True
                )
            date_range = f"{min(d['date'] for d in docs)} to {max(d['date'] for d in docs)}"
            print(f"[Bookopedia] Saved {len(docs)} daily prices for {ticker} to MongoDB ({date_range}).")
    except Exception as e:
        print(f"[Bookopedia] Failed to save price history: {e}")


def get_price_history(ticker='BTC', start_date=None, end_date=None):
    """Get daily prices from MongoDB. Defaults to BTC for Bitcoin compatibility."""
    if not MONGO_AVAILABLE:
        return []
    try:
        query = {'ticker': ticker}
        if start_date:
            # Convert date to datetime if needed for MongoDB
            if isinstance(start_date, date) and not isinstance(start_date, datetime):
                start_dt = datetime.combine(start_date, datetime.min.time())
            else:
                start_dt = start_date
            query['date'] = {'$gte': start_dt}
        if end_date:
            # Convert date to datetime if needed for MongoDB
            if isinstance(end_date, date) and not isinstance(end_date, datetime):
                end_dt = datetime.combine(end_date, datetime.max.time())
            else:
                end_dt = end_date
            query['date'] = query.get('date', {})
            query['date']['$lte'] = end_dt
        results = list(collection.find(query).sort('date', 1))
        return results
    except Exception as e:
        print(f"[Bookopedia] Failed to read price history: {e}")
        return []


def get_latest_price_date(ticker):
    """Get the most recent date we have price data for a ticker."""
    if not MONGO_AVAILABLE:
        return None
    try:
        result = collection.find_one({'ticker': ticker}, sort=[('date', -1)])
        if result:
            date_val = result['date']
            # Extract date part if it's a datetime
            if isinstance(date_val, datetime):
                return date_val.date()
            elif isinstance(date_val, date):
                return date_val
            return date_val
        return None
    except Exception as e:
        print(f"[Bookopedia] Failed to get latest date for {ticker}: {e}")
        return None


# ---- BTC Metrics Cache ----

def save_crypto_metrics(coin, data):
    """Save crypto metrics snapshot to MongoDB for caching."""
    if not MONGO_AVAILABLE or not data:
        return
    try:
        doc = {
            'coin': coin,
            'updated_at': datetime.utcnow(),
            **data
        }
        metrics_collection.update_one(
            {'coin': coin},
            {'$set': doc},
            upsert=True
        )
        print(f"[Bookopedia] {coin} metrics cached to MongoDB.")
    except Exception as e:
        print(f"[Bookopedia] Failed to cache {coin} metrics: {e}")


def get_cached_crypto_metrics(coin):
    """Get cached crypto metrics from MongoDB. Returns None if unavailable."""
    if not MONGO_AVAILABLE:
        return None
    try:
        doc = metrics_collection.find_one({'coin': coin})
        if doc:
            doc.pop('_id', None)
            doc.pop('coin', None)
            print(f"[Bookopedia] Serving cached {coin} metrics (updated: {doc.get('updated_at', 'unknown')})")
            return doc
        return None
    except Exception as e:
        print(f"[Bookopedia] Failed to read cached {coin} metrics: {e}")
        return None


def save_crypto_metrics_history(coin, market_chart_payload):
    """Save crypto metrics history (price, market cap, volume, supply) to MongoDB."""
    if not MONGO_AVAILABLE or not market_chart_payload:
        return
    try:
        prices = market_chart_payload.get('prices') or []
        market_caps = market_chart_payload.get('market_caps') or []
        volumes = market_chart_payload.get('total_volumes') or []

        if not prices:
            return

        points = min(len(prices), len(market_caps), len(volumes))
        docs = {}

        for i in range(points):
            try:
                ts = prices[i][0]
                price = float(prices[i][1])
                market_cap = float(market_caps[i][1]) if market_caps[i] else None
                volume = float(volumes[i][1]) if volumes[i] else None
                supply = (market_cap / price) if market_cap and price else None

                date_obj = datetime.fromtimestamp(ts / 1000)
                date_key = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)

                docs[date_key] = {
                    'coin': coin,
                    'date': date_key,
                    'price': price,
                    'market_cap': market_cap,
                    'volume': volume,
                    'supply': supply,
                }
            except (TypeError, ValueError, IndexError):
                continue

        for doc in docs.values():
            crypto_metrics_history_collection.update_one(
                {'coin': coin, 'date': doc['date']},
                {'$set': doc},
                upsert=True
            )

        print(f"[Bookopedia] Saved {len(docs)} crypto metrics rows for {coin}.")
    except Exception as e:
        print(f"[Bookopedia] Failed to save {coin} metrics history: {e}")


def get_crypto_metrics_history(coin, start_date=None, end_date=None):
    """Get crypto metrics history from MongoDB."""
    if not MONGO_AVAILABLE:
        return []
    try:
        query = {'coin': coin}
        if start_date:
            if isinstance(start_date, date) and not isinstance(start_date, datetime):
                start_dt = datetime.combine(start_date, datetime.min.time())
            else:
                start_dt = start_date
            query['date'] = {'$gte': start_dt}
        if end_date:
            if isinstance(end_date, date) and not isinstance(end_date, datetime):
                end_dt = datetime.combine(end_date, datetime.max.time())
            else:
                end_dt = end_date
            query['date'] = query.get('date', {})
            query['date']['$lte'] = end_dt
        return list(crypto_metrics_history_collection.find(query).sort('date', 1))
    except Exception as e:
        print(f"[Bookopedia] Failed to read {coin} metrics history: {e}")
        return []


def get_latest_crypto_metrics_date(coin):
    """Get the most recent metrics date for a coin."""
    if not MONGO_AVAILABLE:
        return None
    try:
        result = crypto_metrics_history_collection.find_one({'coin': coin}, sort=[('date', -1)])
        if result:
            date_val = result['date']
            if isinstance(date_val, datetime):
                return date_val.date()
            if isinstance(date_val, date):
                return date_val
            return date_val
        return None
    except Exception as e:
        print(f"[Bookopedia] Failed to get latest metrics date for {coin}: {e}")
        return None


def save_stock_snapshot(ticker, snapshot_data):
    """Save one company snapshot to MongoDB."""
    if not MONGO_AVAILABLE or not snapshot_data:
        return
    try:
        doc = {
            'ticker': ticker,
            'updated_at': datetime.utcnow(),
            **snapshot_data
        }
        stock_snapshot_collection.update_one(
            {'ticker': ticker},
            {'$set': doc},
            upsert=True
        )
    except Exception as e:
        print(f"[Bookopedia] Failed to save stock snapshot for {ticker}: {e}")


def get_cached_stock_snapshot(ticker):
    """Get cached stock snapshot from MongoDB."""
    if not MONGO_AVAILABLE:
        return None
    try:
        doc = stock_snapshot_collection.find_one({'ticker': ticker})
        if doc:
            doc.pop('_id', None)
            return doc
        return None
    except Exception as e:
        print(f"[Bookopedia] Failed to read stock snapshot for {ticker}: {e}")
        return None
