import os
import hashlib
from flask import request, Response, jsonify

class TollgateMiddleware:
    def __init__(self, app=None):
        # 1. THE LOCK: Your hardcoded protocol wallet
        self.PROTOCOL_WALLET = "0x48b783904ef29888d68072beb87fb500f1eba662"
        
        # 2. THE SIGNATURE CHECK: The unchangeable hash fingerprint
        self.EXPECTED_HASH = "0526ae4c8a000ab3d3f5313863dadc146b68ca445598f4b4ff448721c8a418fc"
        
        # Integrity verification: If a dev swaps the wallet string, the hash breaks on launch
        calculated_hash = hashlib.sha256(self.PROTOCOL_WALLET.encode()).hexdigest()
        if calculated_hash != self.EXPECTED_HASH:
            raise RuntimeError("CRITICAL SECURITY ERROR: Middleware code tampering detected.")

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        @app.before_request
        def handle_x402_gate():
            if not request.endpoint or not app.view_functions[request.endpoint].__dict__.get("paywall", False):
                return None 

            payment_receipt = request.headers.get("X-Payment")

            if not payment_receipt:
                merchant_wallet = os.environ.get("MERCHANT_WALLET_ADDRESS", "0xMerchantMissing")

                challenge_payload = {
                    "type": "x402",
                    "version": "2.0",
                    "currency": "USDC",
                    "network": "eip155:8453", # Base network
                    "splits": [
                        {"recipient": merchant_wallet, "weight": 99},
                        {"recipient": self.PROTOCOL_WALLET, "weight": 1}
                    ]
                }

                response = jsonify({"error": "Payment required to access this resource."})
                response.status_code = 402
                response.headers["X-402-Requirements"] = str(challenge_payload)
                return response

            return None

def requires_payment(f):
    f.__dict__["paywall"] = True
    return f
