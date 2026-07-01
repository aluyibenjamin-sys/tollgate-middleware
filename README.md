# Tollgate Middleware (HTTP 402 Web3 Protocol)

A production-grade monetization layer for Flask APIs. Features automated split payments on the Base network and persistent SQLite anti-replay protection.

Optimized for autonomous AI agents requiring unattended programmatic payments.

---

## 🚀 Key Features

* **Dynamic 402 Interception:** Automatically halts incoming requests to protected routes, serving an execution breakdown.
* **Automated Cryptographic Signing:** Built-in client engine that processes split payments natively and bundles transaction proofs into request headers.
* **Persistent Anti-Replay Armor:** Backed by an embedded SQLite ledger (`tollgate_vault.db`) that logs used transaction hashes permanently to eliminate fraud.

---

## 🛠️ Quick Start Guide

### 1. Server-Side Guard Setup
You can enforce payment on any route and customize the required amount per request directly in the decorator.

```python
import os
from flask import Flask
from tollgate.middleware import TollgateMiddleware, requires_payment

app = Flask(__name__)
os.environ["MERCHANT_WALLET_ADDRESS"] = "0xYourMerchantWalletAddressHere"

TollgateMiddleware(app, db_path="tollgate_vault.db")

# To set a price, pass amount_usd to the decorator (e.g., 5 cents)
@app.route("/api/v1/premium-data")
@requires_payment(amount_usd=0.05) 
def premium_endpoint():
    return {"status": "unlocked", "payload": "Premium data."}

