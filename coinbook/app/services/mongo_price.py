import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = 'coinbook'
COLLECTION = 'btc_price_history'

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    # Test connection
    client.admin.command('ping')
    db = client[DB_NAME]
    collection = db[COLLECTION]
    MONGO_AVAILABLE = True
    print("[Coinbook] MongoDB connected successfully.")
except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
    MONGO_AVAILABLE = False
    collection = None
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
