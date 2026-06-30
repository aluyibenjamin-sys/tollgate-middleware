import sys
from unittest.mock import MagicMock
from flask import Flask

# Import your newly upgraded modules
from tollgate.middleware import TollgateMiddleware, requires_payment
from tollgate.client import TollgateClient

print("\033[1;34m=== Setting Up Safe Local Web3 Simulation ===\033[0m")

# 1. Initialize a localized Flask app instance
app = Flask(__name__)
middleware = TollgateMiddleware(app)

@app.route("/premium")
@requires_payment
def premium_route():
    return {"status": "unlocked", "secret_content": "Bitcoin whitepaper copy #42"}

# 2. Instantiate the client pointing to our local simulation environment
client = TollgateClient(base_url="http://127.0.0.1:5000")

# 3. Securely mock out the actual blockchain network calls so no real money is used
client.w3 = MagicMock()
client.w3.eth.get_transaction_count.return_code = 0
client.w3.eth.gas_price = 1000000000
client.w3.to_wei.return_value = 100000
client.w3.to_hex.return_value = "0xSimulatedSuccessfulTxHashString123456789"
client.w3.eth.account.from_key = MagicMock()
client.w3.eth.account.sign_transaction = MagicMock()
client.w3.eth.send_raw_transaction = MagicMock()

# Mock out the server side network check to trust our simulation hash
middleware._verify_on_chain = MagicMock(return_value=True)

# 4. Run the complete Web3 automated execution test loop inside a Flask test context
with app.test_client() as flask_server:
    # Overwrite the client's internal request mechanism to hit our local mock server
    import requests
    original_get = requests.get
    
    def mock_get(url, headers=None):
        endpoint = url.replace("http://127.0.0.1:5000", "")
        # Map the request directly to the Flask test engine
        flask_res = flask_server.get(endpoint, headers=headers)
        
        # Build a standard response object compatible with TollgateClient
        mock_response = MagicMock()
        mock_response.status_code = flask_res.status_code
        mock_response.headers = flask_res.headers
        mock_response.json = lambda: flask_res.get_json()
        mock_response.text = flask_res.get_data(as_text=True)
        return mock_response

    requests.get = mock_get

    print("\033[1;35mExecuting client request with an active Private Key...\033[0m")
    # Using a standard dummy testing private key string (completely fake)
    dummy_key = "0x" + "a" * 64 
    
    # Run the live engine call!
    result = client.pay_and_request("/premium", private_key=dummy_key)
    
    print("\n\033[1;32m=== FINAL SIMULATION RESPONSE ===\033[0m")
    print(result)

    # Restore native network behavior
    requests.get = original_get
