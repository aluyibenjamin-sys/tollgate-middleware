import os
import requests
from flask import request, jsonify
from functools import wraps

class TollgateMiddleware:
    def __init__(self, app=None):
        self.app = app
        self.rpc_url = "https://mainnet.base.org"
        self.protocol_wallet = "0x48b7783904ef29888d68072beb87fb500f1eba66".lower()
        # In-memory database to track used hashes and prevent replay fraud
        self.used_hashes = set()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        @app.before_request
        def check_payment_status():
            if not getattr(app.view_functions.get(request.endpoint, {}), 'requires_payment', False):
                return

            # Expecting a comma-separated string of hashes from the client
            tx_hashes_str = request.headers.get("X-Transaction-Hashes")
            if not tx_hashes_str:
                return self._charge_payload()

            tx_hashes = [h.strip() for h in tx_hashes_str.split(",") if h.strip()]
            merchant_wallet = os.getenv("MERCHANT_WALLET_ADDRESS", "").lower()

            if not self._verify_multi_payment(tx_hashes, merchant_wallet):
                return jsonify({"error": "Security Block: Invalid, duplicated, or unpaid transaction links."}), 402

    def _verify_multi_payment(self, tx_hashes, merchant_wallet):
        """Verifies all required split transactions are valid, unique, and unpaid."""
        paid_merchant = False
        paid_protocol = False

        for tx_hash in tx_hashes:
            # 1. Replay Attack Protection
            if tx_hash in self.used_hashes:
                print(f"[Security Warning] Replay attack detected for hash: {tx_hash}")
                return False

            # Fetch transaction details from Base Network
            payload = {"jsonrpc": "2.0", "method": "eth_getTransactionByHash", "params": [tx_hash], "id": 1}
            try:
                res = requests.post(self.rpc_url, json=payload, timeout=5).json()
                tx_data = res.get("result")
                if not tx_data:
                    return False

                recipient = tx_data.get("to", "").lower()
                
                # Check destinations
                if recipient == merchant_wallet:
                    paid_merchant = True
                    self.used_hashes.add(tx_hash) # Burn the hash so it can never be used again
                elif recipient == self.protocol_wallet:
                    paid_protocol = True
                    self.used_hashes.add(tx_hash)

            except Exception:
                return False

        return paid_merchant and paid_protocol

    def _charge_payload(self):
        merchant_wallet = os.getenv("MERCHANT_WALLET_ADDRESS", "0xMerchantMissing")
        requirements = {
            "type": "x402",
            "version": "2.0",
            "currency": "ETH",
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
