import requests
import ast
from web3 import Web3

class TollgateClient:
    def __init__(self, base_url, rpc_url="https://mainnet.base.org"):
        self.base_url = base_url
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

    def pay_and_request(self, endpoint, private_key=None, token_address=None):
        """Hits an endpoint. If blocked by a 402, executes all on-chain split payouts and bundles proofs."""
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
        
        print("\n\033[1;33m[Web3 Engine] 402 Intercepted. Preparing Production-Grade Multi-Hash Payout...\033[0m")
        
        # Derive account from private key safely
        account = self.w3.eth.account.from_key(private_key)
        sender_address = account.address
        
        # List to collect every individual transaction hash
        collected_tx_hashes = []
        
        # 3. Build and execute native crypto payments for each distinct split recipient
        for split in splits:
            recipient = split["recipient"]
            weight = split["weight"]
            
            print(f" -> Authorizing split payment to {recipient} ({weight}% weight allocation)")
            
            # Fetch fresh nonce for each independent transaction block
            tx = {
                'nonce': self.w3.eth.get_transaction_count(sender_address),
                'to': self.w3.to_checksum_address(recipient),
                'value': self.w3.to_wei(0.0001 * (weight / 100), 'ether'),
                'gas': 21000,
                'maxFeePerGas': self.w3.eth.gas_price,
                'maxPriorityFeePerGas': self.w3.to_wei(0.1, 'gwei'),
                'chainId': 8453
            }
            
            # Cryptographically sign locally
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            # Broadcast live to the network
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Accumulate the hash signature
            collected_tx_hashes.append(self.w3.to_hex(tx_hash))
            
        # Bundle all proofs neatly together using commas
        bundled_hashes_str = ",".join(collected_tx_hashes)
        print(f"\033[1;32m[Web3 Engine] All Split Payments Broadcasted Successfully!\033[0m")
        print(f" -> Combined proof bundle: {bundled_hashes_str}")
        
        # 4. Retry original target endpoint with the complete multi-hash proof header
        print(" -> Transmitting multi-hash token bundle to gateway verification engine...")
        headers = {"X-Transaction-Hashes": bundled_hashes_str}
        retry_response = requests.get(url, headers=headers)
        
        return {
            "status": "processed",
            "server_status_code": retry_response.status_code,
            "data": retry_response.json() if retry_response.status_code == 200 else retry_response.text
        }
