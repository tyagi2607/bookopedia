import requests

def get_btc_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": "bitcoin",
        "price_change_percentage": "7d"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        #data = response.json()[0]
        result = response.json()
        print("RAW API RESULT:", result)

        if not result or not isinstance(result, list):
            return None

        data = result[0]  # First (and only) coin in the result

        return {
            "price": data["current_price"],
            "market_cap": data["market_cap"],
            "volume": data["total_volume"],
            "change_24h": data["price_change_percentage_24h"],
            "change_7d": data["price_change_percentage_7d_in_currency"],
            "supply": data["circulating_supply"],
            "max_supply": data["max_supply"]
        }
    #except (requests.RequestException, IndexError, KeyError):
    #    return None
    except Exception as e:
        print("Error fetching BTC data:", e)
        return None
