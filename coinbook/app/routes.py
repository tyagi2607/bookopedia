from flask import Blueprint, render_template
from app.services.coins import get_btc_data

main = Blueprint("main", __name__)

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

@main.route("/")
def home():
    data = get_btc_data()
    print("BTC DATA:", data)
    btc = BtcData(data) if data else None
    return render_template("index.html", btc=btc)