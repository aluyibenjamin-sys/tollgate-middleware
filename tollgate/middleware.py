import os
import requests
from flask import request, jsonify
from functools import wraps

class TollgateMiddleware:
    def __init__(self, app=None):
        self.app = app
        self.rpc_url = "https://mainnet.base.org"
        self.protocol_wallet = "0x48b7783904ef29888d68072beb87fb500f1eba66".lower()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        @app.before_request
        def check_payment_status():
            if not getattr(app.view_functions.get(request.endpoint, {}), 'requires_payment', False):
                return

            tx_hash = request.headers.get("X-Transaction-Hash")
            if not tx_hash:
                return self._charge_payload()

            # Pass the designated merchant wallet into our fraud validator
            merchant_wallet = os.getenv("MERCHANT_WALLET_ADDRESS", "").lower()
            if not self._verify_on_chain(tx_hash, merchant_wallet):
                return jsonify({"error": "Fraud protection: Transaction unconfirmed or invalid destinations."}), 402

    def _verify_on_chain(self, tx_hash, merchant_wallet):
        """Scans the Base blockchain logs to verify real payments reached correct destinations."""
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getTransactionReceipt",
            "params": [tx_hash],
            "id": 1
        }
        try:
            response = requests.post(self.rpc_url, json=payload, timeout=5).json()
            result = response.get("result")
            
            if not result or result.get("status") != "0x1":
                return False  # Transaction failed or does not exist

            # Format wallets to 32-byte hex blocks to match native blockchain log topics
            merchant_topic = "0x" + merchant_wallet.replace("0x", "").zfill(64)
            protocol_topic = "0x" + self.protocol_wallet.replace("0x", "").zfill(64)

            paid_merchant = False
            paid_protocol = False

            # Scan through the transaction logs to find payment destinations
            for log in result.get("logs", []):
                topics = log.get("topics", [])
                if len(topics) >= 3:
                    recipient_topic = topics[2].lower()
                    if recipient_topic == merchant_topic:
                        paid_merchant = True
                    if recipient_topic == protocol_topic:
                        paid_protocol = True

            # The gate only unlocks if BOTH wallets actually received money in this transaction
            return paid_merchant and paid_protocol

        except Exception:
            return False

    def _charge_payload(self):
        merchant_wallet = os.getenv("MERCHANT_WALLET_ADDRESS", "0xMerchantMissing")
        requirements = {
            "type": "x402",
            "version": "2.0",
            "currency": "USDC",
            "network": "eip155:8453",
            "splits": [
                {"recipient": merchant_wallet, "weight": 99},
                {"recipient": self.protocol_wallet, "weight": 1}
            ]
        }
        response = jsonify({"error": "Payment required to access this resource."})
        response.status_code = 402
        response.headers["X-402-Requirements"] = str(requirements)
        return response

def requires_payment(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    decorated_function.requires_payment = True
    return decorated_function
