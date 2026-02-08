import requests
import time


def get_btc_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": "bitcoin",
        "price_change_percentage": "7d"
    }

    # Retry up to 3 times with increasing delay
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=10)

            # Rate limited — wait and retry
            if response.status_code == 429:
                wait = 2 ** attempt
                print(f"[Coinbook] Rate limited by CoinGecko, retrying in {wait}s (attempt {attempt + 1}/3)")
                time.sleep(wait)
                continue

            response.raise_for_status()
            result = response.json()
            print("RAW API RESULT:", result)

            if not result or not isinstance(result, list):
                continue

            data = result[0]

            btc_data = {
                "price": data.get("current_price"),
                "market_cap": data.get("market_cap"),
                "volume": data.get("total_volume"),
                "change_24h": data.get("price_change_percentage_24h"),
                "change_7d": data.get("price_change_percentage_7d_in_currency"),
                "supply": data.get("circulating_supply"),
                "max_supply": data.get("max_supply")
            }

            # Cache to MongoDB on success
            try:
                from app.services.mongo_price import save_btc_metrics
                save_btc_metrics(btc_data)
            except Exception as e:
                print(f"[Coinbook] Could not cache metrics: {e}")

            return btc_data

        except requests.exceptions.Timeout:
            print(f"[Coinbook] API timeout (attempt {attempt + 1}/3)")
            time.sleep(1)
        except Exception as e:
            print(f"[Coinbook] Error fetching BTC data (attempt {attempt + 1}/3): {e}")
            time.sleep(1)

    # All retries failed — try MongoDB cache
    print("[Coinbook] All API attempts failed. Trying cached data...")
    try:
        from app.services.mongo_price import get_cached_btc_metrics
        cached = get_cached_btc_metrics()
        if cached:
            return cached
    except Exception as e:
        print(f"[Coinbook] Could not load cached metrics: {e}")

    return None
