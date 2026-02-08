from flask import Flask


def create_app():
    app = Flask(__name__)

    from app.routes.main import main
    from app.routes.coinbook import coinbook
    from app.routes.stocks import stocks

    app.register_blueprint(main)
    app.register_blueprint(coinbook)
    app.register_blueprint(stocks)

    return app
