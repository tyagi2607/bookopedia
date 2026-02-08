from flask import Blueprint, render_template

stocks = Blueprint("stocks", __name__, url_prefix="/stocks")


@stocks.route("/oil-gas")
def oil_gas():
    return render_template("stocks/oil_gas.html", active_page="oil_gas")
