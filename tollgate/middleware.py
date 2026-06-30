import os
import requests
from flask import request, jsonify, Response
from functools import wraps

class TollgateMiddleware:
    def __init__(self, app=None):
        self.app = app
        # Public Base Mainnet RPC endpoint to read the blockchain
        self.rpc_url = "https://mainnet.base.org"
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        @app.before_request
        def check_payment_status():
            # Skip payment checks for public/free routes
            if not getattr(app.view_functions.get(request.endpoint, {}), 'requires_payment', False):
                return

            # 1. Check if the user supplied a Transaction Hash
            tx_hash = request.headers.get("X-Transaction-Hash")
            if not tx_hash:
                return self._charge_payload()

            # 2. Verify the transaction directly on the Base Blockchain
            if not self._verify_on_chain(tx_hash):
                return jsonify({"error": "Invalid or unconfirmed transaction hash."}), 402

    def _verify_on_chain(self, tx_hash):
        """Queries the live Base Blockchain to verify the transaction status."""
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getTransactionReceipt",
            "params": [tx_hash],
            "id": 1
        }
        try:
            response = requests.post(self.rpc_url, json=payload, timeout=5).json()
            result = response.get("result")
            
            if result is None:
                return False # Transaction doesn't exist yet
                
            # '0x1' means the transaction was executed successfully on-chain
            status = result.get("status")
            return status == "0x1"
        except Exception:
            return False

    def _charge_payload(self):
        """The standard HTTP 402 Payment Required response layout."""
        merchant_wallet = os.getenv("MERCHANT_WALLET_ADDRESS", "0xMerchantMissing")
        requirements = {
            "type": "x402",
            "version": "2.0",
            "currency": "USDC",
            "network": "eip155:8453",  # Base Network chain ID
            "splits": [
                {"recipient": merchant_wallet, "weight": 99},
                {"recipient": "0x48b7783904ef29888d68072beb87fb500f1eba66", "weight": 1} # 1% Protocol Fee
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
