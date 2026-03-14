from flask import Blueprint, render_template, jsonify, request

from app.services.stocks_data import (
    build_energy_chart,
    build_oil_gas_table,
    build_sector_snapshot,
)

stocks = Blueprint("stocks", __name__, url_prefix="/stocks")


@stocks.route("/oil-gas")
def oil_gas():
    # USA majors + E&P + Oilfield Services; top 2 Canadian oil sands (NYSE-listed)
    tickers = [
        # USA Integrated
        "XOM", "CVX", "COP", "OXY",
        # USA E&P
        "EOG", "DVN", "MRO",
        # USA Refining
        "VLO", "PSX",
        # Oilfield Services
        "SLB", "HAL",
        # Canada
        "SU", "CNQ",
    ]
    sector_map = {
        "XOM": "Integrated",  "CVX": "Integrated",
        "COP": "E&P",         "OXY": "E&P",
        "EOG": "E&P",         "DVN": "E&P",         "MRO": "E&P",
        "VLO": "Refining",    "PSX": "Refining",
        "SLB": "Oilfield Svcs", "HAL": "Oilfield Svcs",
        "SU":  "CA Integrated", "CNQ": "CA E&P",
    }
    country_map = {
        "SU": "CA", "CNQ": "CA",
    }

    companies, errors, as_of = build_oil_gas_table(tickers, sector_map=sector_map, country_map=country_map)
    sector_metric, sector_error = build_sector_snapshot(symbol="XLE")

    # Only include sector metrics if we got data (no errors)
    sector_metrics = [sector_metric] if sector_metric and not sector_error else []

    return render_template(
        "stocks/oil_gas.html",
        active_page="oil_gas",
        sector_metrics=sector_metrics,
        companies=companies,
        as_of=as_of,
    )


@stocks.route("/api/energy/history")
def energy_history():
    import traceback
    try:
        range_param = request.args.get("range", "30d")
        chart_data, error = build_energy_chart(range_param=range_param, symbol="XLE")
        if error:
            print(f"[Bookopedia] Chart error: {error}")
            return jsonify({"error": error}), 500
        return jsonify(chart_data)
    except Exception as e:
        print(f"[Bookopedia] Unhandled exception in energy_history: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
