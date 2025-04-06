from flask import Blueprint, render_template
from app.services.coins import get_btc_price

main = Blueprint("main", __name__)

@main.route("/")
def home():
    btc_price = get_btc_price()
    return render_template("index.html", price=btc_price)

