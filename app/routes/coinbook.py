from flask import Blueprint, render_template, jsonify, request
import requests
import datetime
from app.services.coins import get_btc_data
from app.services.mongo_price import (
    save_price_history,
    get_latest_price_date,
    get_price_history,
    save_crypto_metrics_history,
    get_crypto_metrics_history,
    get_latest_crypto_metrics_date,
)

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
        'all': 1825
    }
    days = range_map.get(range_param, 30)
    if days == 'max' or days is None:
        days = 1825
    days = min(int(days), 1825)

    today = datetime.datetime.utcnow().date()
    start_date = None
    if isinstance(days, int):
        start_date = today - datetime.timedelta(days=days)

    latest_db_date = get_latest_price_date('BTC')
    history = get_price_history('BTC', start_date=start_date)

    stale_cutoff = today - datetime.timedelta(days=1)
    needs_api_fetch = not history or latest_db_date is None or latest_db_date < stale_cutoff

    if needs_api_fetch:
        url = f'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}'
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return jsonify({'error': f'CoinGecko API returned {resp.status_code}'}), 500
            data = resp.json()
            raw_prices = data.get('prices', [])
            if raw_prices:
                save_price_history('BTC', raw_prices)
                save_crypto_metrics_history('bitcoin', data)
            labels = [datetime.datetime.fromtimestamp(p[0] / 1000).strftime('%Y-%m-%d %H:%M') for p in raw_prices]
            prices = [p[1] for p in raw_prices]
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to fetch data: {str(e)}'}), 500
    else:
        try:
            labels = [h['date'].strftime('%Y-%m-%d %H:%M') if hasattr(h['date'], 'strftime') else str(h['date']) for h in history]
            prices = [float(h['price']) for h in history]
        except (KeyError, AttributeError, TypeError) as e:
            print(f"[Bookopedia] Error formatting history: {e}")
            return jsonify({'error': 'Failed to process price history'}), 500

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


@coinbook.route('/api/bitcoin/metrics')
def bitcoin_metrics():
    range_param = request.args.get('range', '5y')

    range_map = {
        'daily': 1,
        '7d': 7,
        '30d': 30,
        '6m': 180,
        '1y': 365,
        '5y': 1825,
        'all': 1825
    }
    days = range_map.get(range_param, 1825)
    if days == 'max' or days is None:
        days = 1825
    days = min(int(days), 1825)

    today = datetime.datetime.utcnow().date()
    start_date = today - datetime.timedelta(days=days)

    latest_db_date = get_latest_crypto_metrics_date('bitcoin')
    stale_cutoff = today - datetime.timedelta(days=1)
    needs_api_fetch = latest_db_date is None or latest_db_date < stale_cutoff

    if needs_api_fetch:
        url = f'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}'
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return jsonify({'error': f'CoinGecko API returned {resp.status_code}'}), 500
            data = resp.json()
            save_crypto_metrics_history('bitcoin', data)
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to fetch data: {str(e)}'}), 500

    rows = get_crypto_metrics_history('bitcoin', start_date=start_date)
    labels = [r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date']) for r in rows]
    market_caps = [r.get('market_cap') for r in rows]
    volumes = [r.get('volume') for r in rows]
    supplies = [r.get('supply') for r in rows]

    return jsonify({
        'labels': labels,
        'market_caps': market_caps,
        'volumes': volumes,
        'supplies': supplies,
    })
