import requests
import ast

class TollgateClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def request_premium_resource(self, endpoint, tx_hash=None):
        """Makes a request to a protected route, handling the 402 gateway layer."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {}
        
        # If the user has already paid and provided a transaction hash, attach it
        if tx_hash:
            headers["X-Transaction-Hash"] = tx_hash

        response = requests.get(url, headers=headers)

        if response.status_code == 402:
            requirements_str = response.headers.get("X-402-Requirements")
            if requirements_str:
                # Safely parse the payment rules string back into a Python dictionary
                requirements = ast.literal_eval(requirements_str)
                print("\n\033[1;33m[402 PAYMENT REQUIRED] Intercepted monetization requirements:\033[0m")
                print(f" -> Network: {requirements.get('network')}")
                print(f" -> Token Currency: {requirements.get('currency')}")
                print(" -> Required Payout Splits:")
                for split in requirements.get("splits", []):
                    print(f"    - Wallet: {split['recipient']} ({split['weight']}% cut)")
                
                return {
                    "status": "payment_required",
                    "requirements": requirements
                }
        
        return {
            "status": "success",
            "data": response.json() if response.status_code == 200 else response.text
        }
