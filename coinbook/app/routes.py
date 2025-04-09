from flask import Blueprint, render_template
from app.services.coins import get_btc_price

main = Blueprint("main", __name__)

@main.route("/")
def home():
    btc = get_btc_data()
    return render_template("index.html", btc=btc)

