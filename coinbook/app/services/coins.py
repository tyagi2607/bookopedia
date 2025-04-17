import requests

def get_btc_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": "bitcoin"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()[0]
        return {
            "price": data["current_price"],
            "market_cap": data["market_cap"],
            "volume": data["total_volume"],
            "change_24h": data["price_change_percentage_24h"],
            "change_7d": data["price_change_percentage_7d_in_currency"],
            "supply": data["circulating_supply"],
            "max_supply": data["max_supply"]
        }
    except (requests.RequestException, IndexError, KeyError):
        return None
