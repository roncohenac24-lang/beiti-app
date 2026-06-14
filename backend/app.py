"""
beiti - Flask Application Entry Point
"""

import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

from routes.webhook  import webhook_bp
from routes.shopping import shopping_bp
from routes.bills    import bills_bp

app = Flask(__name__)

app.register_blueprint(webhook_bp,  url_prefix="/webhook")
app.register_blueprint(shopping_bp, url_prefix="/shopping")
app.register_blueprint(bills_bp,    url_prefix="/bills")


@app.route("/health")
def health():
    return {"status": "ok", "service": "beiti", "channel": "telegram"}


if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
