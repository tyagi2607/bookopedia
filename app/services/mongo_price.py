import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = 'coinbook'
PRICE_HISTORY_COLLECTION = 'btc_price_history'
BTC_METRICS_COLLECTION = 'btc_metrics'

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    # Test connection
    client.admin.command('ping')
    db = client[DB_NAME]
    collection = db[PRICE_HISTORY_COLLECTION]
    metrics_collection = db[BTC_METRICS_COLLECTION]
    MONGO_AVAILABLE = True
    print("[Coinbook] MongoDB connected successfully.")
except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
    MONGO_AVAILABLE = False
    collection = None
    metrics_collection = None
    print(f"[Coinbook] MongoDB not available ({e}). Using direct API mode.")


def save_price_history(prices):
    """Save prices to MongoDB. Silently skips if MongoDB is unavailable."""
    if not MONGO_AVAILABLE:
        return
    try:
        docs = [
            {
                'timestamp': int(p[0]),
                'date': datetime.fromtimestamp(p[0]/1000),
                'price': p[1]
            } for p in prices
        ]
        for doc in docs:
            collection.update_one({'timestamp': doc['timestamp']}, {'$set': doc}, upsert=True)
    except Exception as e:
        print(f"[Coinbook] Failed to save to MongoDB: {e}")


def get_price_history(start_ts=None, end_ts=None):
    """Get prices from MongoDB. Returns empty list if unavailable."""
    if not MONGO_AVAILABLE:
        return []
    try:
        query = {}
        if start_ts:
            query['timestamp'] = {'$gte': start_ts}
        if end_ts:
            query['timestamp'] = query.get('timestamp', {})
            query['timestamp']['$lte'] = end_ts
        return list(collection.find(query).sort('timestamp', 1))
    except Exception as e:
        print(f"[Coinbook] Failed to read from MongoDB: {e}")
        return []


# ---- BTC Metrics Cache ----

def save_btc_metrics(data):
    """Save BTC metrics snapshot to MongoDB for caching."""
    if not MONGO_AVAILABLE or not data:
        return
    try:
        doc = {
            'coin': 'bitcoin',
            'updated_at': datetime.utcnow(),
            **data
        }
        metrics_collection.update_one(
            {'coin': 'bitcoin'},
            {'$set': doc},
            upsert=True
        )
        print("[Coinbook] BTC metrics cached to MongoDB.")
    except Exception as e:
        print(f"[Coinbook] Failed to cache BTC metrics: {e}")


def get_cached_btc_metrics():
    """Get cached BTC metrics from MongoDB. Returns None if unavailable."""
    if not MONGO_AVAILABLE:
        return None
    try:
        doc = metrics_collection.find_one({'coin': 'bitcoin'})
        if doc:
            # Remove MongoDB internal fields
            doc.pop('_id', None)
            doc.pop('coin', None)
            print(f"[Coinbook] Serving cached BTC metrics (last updated: {doc.get('updated_at', 'unknown')})")
            return doc
        return None
    except Exception as e:
        print(f"[Coinbook] Failed to read cached BTC metrics: {e}")
        return None
