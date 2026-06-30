import os
import sqlite3
import requests
from flask import request, jsonify
from functools import wraps

class TollgateMiddleware:
    def __init__(self, app=None, db_path="tollgate_vault.db"):
        self.app = app
        self.rpc_url = "https://mainnet.base.org"
        self.protocol_wallet = "0x48b7783904ef29888d68072beb87fb500f1eba66".lower()
        self.db_path = db_path
        
        # Initialize the persistent database storage immediately
        self._init_db()
        
        if app is not None:
            self.init_app(app)

    def _init_db(self):
        """Creates a permanent, thread-safe database table to track spent hashes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spent_hashes (
                    tx_hash TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def init_app(self, app):
        @app.before_request
        def check_payment_status():
            if not getattr(app.view_functions.get(request.endpoint, {}), 'requires_payment', False):
                return

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

        # Open a distinct connection for this request thread to ensure safety
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for tx_hash in tx_hashes:
                # 1. Replay Attack Protection: Check disk database
                cursor.execute("SELECT 1 FROM spent_hashes WHERE tx_hash = ?", (tx_hash,))
                if cursor.fetchone():
                    print(f"[Security Warning] Replay attack blocked on disk for hash: {tx_hash}")
                    return False

                # 2. On-Chain Verification
                payload = {"jsonrpc": "2.0", "method": "eth_getTransactionByHash", "params": [tx_hash], "id": 1}
                try:
                    res = requests.post(self.rpc_url, json=payload, timeout=5).json()
                    tx_data = res.get("result")
                    if not tx_data:
                        return False

                    recipient = tx_data.get("to", "").lower()
                    
                    if recipient == merchant_wallet:
                        paid_merchant = True
                        # Commit the hash to disk immediately so it can never be re-used
                        cursor.execute("INSERT INTO spent_hashes (tx_hash) VALUES (?)", (tx_hash,))
                    elif recipient == self.protocol_wallet:
                        paid_protocol = True
                        cursor.execute("INSERT INTO spent_hashes (tx_hash) VALUES (?)", (tx_hash,))

                except Exception:
                    return False
            
            conn.commit()

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
