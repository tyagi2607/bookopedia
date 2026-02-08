from flask import Blueprint, render_template, jsonify, request
import requests
import datetime
from app.services.coins import get_btc_data
from app.services.mongo_price import save_price_history, get_price_history

coinbook = Blueprint("coinbook", __name__, url_prefix="/coinbook")


# Helper class to enable dot notation in Jinja
class BtcData:
    def __init__(self, data):
        self.price = data.get("price")
        self.market_cap = data.get("market_cap")
        self.volume = data.get("volume")
        self.change_24h = data.get("change_24h")
        self.change_7d = data.get("change_7d")
        self.supply = data.get("supply")
        self.max_supply = data.get("max_supply")


@coinbook.route("/bitcoin")
def bitcoin():
    data = get_btc_data()
    print("BTC DATA:", data)
    btc = BtcData(data) if data else None
    return render_template("coinbook/bitcoin.html", btc=btc, active_page="bitcoin")


@coinbook.route('/api/bitcoin/history')
def bitcoin_history():
    range_param = request.args.get('range', '30d')
    chart_type = request.args.get('type', 'line')

    range_map = {
        'daily': 1,
        '7d': 7,
        '30d': 30,
        '6m': 180,
        '1y': 365,
        '5y': 1825,
        'all': 'max'
    }
    days = range_map.get(range_param, 30)

    history = get_price_history()

    if not history:
        url = f'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}'
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return jsonify({'error': f'CoinGecko API returned {resp.status_code}'}), 500
            data = resp.json()
            raw_prices = data.get('prices', [])
            save_price_history(raw_prices)
            labels = [datetime.datetime.fromtimestamp(p[0] / 1000).strftime('%Y-%m-%d %H:%M') for p in raw_prices]
            prices = [p[1] for p in raw_prices]
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to fetch data: {str(e)}'}), 500
    else:
        labels = [datetime.datetime.fromtimestamp(h['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M') for h in history]
        prices = [h['price'] for h in history]

    chart_data = {
        'labels': labels,
        'prices': prices
    }

    if chart_type == 'candlestick':
        chart_data['candles'] = [
            {'t': labels[i], 'o': prices[i], 'h': prices[i], 'l': prices[i], 'c': prices[i]}
            for i in range(len(prices))
        ]

    return jsonify(chart_data)
