import requests

def get_btc_price():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise error if request fails
        data = response.json()
        return data["bitcoin"]["usd"]
    except (requests.RequestException, KeyError):
        return None
