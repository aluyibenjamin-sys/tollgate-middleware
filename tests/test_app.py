from flask import Flask, jsonify
from tollgate.middleware import TollgateMiddleware, requires_payment

app = Flask(__name__)

# Initialize your middleware onto the web application
tg = TollgateMiddleware(app)

@app.route("/api/free-content")
def public_data():
    return jsonify({"status": "free", "msg": "Welcome! This endpoint is free for anyone."})

@app.route("/api/premium-ai-intel")
@requires_payment
def premium_data():
    return jsonify({"status": "success", "data": "Here is the top-secret AI training data."})

if __name__ == "__main__":
    app.run(port=5000)
