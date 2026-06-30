import requests
import ast
from web3 import Web3

class TollgateClient:
    def __init__(self, base_url, rpc_url="https://mainnet.base.org"):
        self.base_url = base_url
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

    def pay_and_request(self, endpoint, private_key=None, token_address=None):
        """Hits an endpoint. If blocked by a 402, automatically executes the on-chain payout."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # 1. Make the initial dry-run request
        response = requests.get(url)
        
        if response.status_code != 402:
            return {"status": "success", "data": response.json() if response.status_code == 200 else response.text}

        # 2. Intercepted 402! Extract the financial requirements
        requirements_str = response.headers.get("X-402-Requirements")
        if not requirements_str or not private_key:
            return {"status": "payment_required_but_no_key", "error": "Private key missing or splits unreadable."}
            
        requirements = ast.literal_eval(requirements_str)
        splits = requirements.get("splits", [])
        
        print("\n\033[1;33m[Web3 Engine] 402 Intercepted. Preparing Live Blockchain Payout...\033[0m")
        
        # Derive account from private key safely
        account = self.w3.eth.account.from_key(private_key)
        sender_address = account.address
        
        # 3. Build and execute payments for each split recipient
        # Note: For production batch-splits, developers use a Splitter Smart Contract.
        # Here we automate the direct wallet execution tracking loop.
        last_tx_hash = None
        for split in splits:
            recipient = split["recipient"]
            weight = split["weight"]
            
            print(f" -> Authorizing payment to {recipient} ({weight}% weight status)")
            
            # Build standard transaction structure
            tx = {
                'nonce': self.w3.eth.get_transaction_count(sender_address),
                'to': self.w3.to_checksum_address(recipient),
                'value': self.w3.to_wei(0.0001 * (weight / 100), 'ether'), # Example split scaling
                'gas': 21000,
                'maxFeePerGas': self.w3.eth.gas_price,
                'maxPriorityFeePerGas': self.w3.to_wei(0.1, 'gwei'),
                'chainId': 8453 # Base Mainnet ID
            }
            
            # Cryptographically sign the data block locally
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            # Broadcast live to the Base Network
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            last_tx_hash = self.w3.to_hex(tx_hash)
            
        print(f"\033[1;32m[Web3 Engine] Payout Broadcasted! Tx Hash: {last_tx_hash}\033[0m")
        
        # 4. Automatically retry the original request, passing the real proof of payment
        print(" -> Retrying target endpoint with cryptographic proof header...")
        headers = {"X-Transaction-Hash": last_tx_hash}
        retry_response = requests.get(url, headers=headers)
        
        return {
            "status": "processed",
            "server_status_code": retry_response.status_code,
            "data": retry_response.json() if retry_response.status_code == 200 else retry_response.text
        }
