from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "flask", "time": datetime.now(timezone.utc).isoformat()})


@app.post("/notifications/order")
def order_notification():
    payload = request.get_json(silent=True) or {}
    return jsonify({"accepted": True, "message": "Order notification queued", "order_number": payload.get("order_number")}), 202


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
