import hmac
import json
import hashlib
import time
import base64
import requests
from requests.auth import AuthBase

# return map of necessary api keys
def get_keys():
    keys = {}
    with open("keys.json", "r", encoding="utf-8") as json_file:
        data = json.load(json_file)
        for d in data:
            keys[d] = data[d]
    return keys

keys = get_keys()
API_KEY = keys["key"]
API_SECRET = keys["secret"]
API_PASS = keys["pass"]

# setup the request sent to coinbase
class CoinbaseExchangeAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + (request.body or b'').decode()
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message.encode(), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode()

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
            })
        return request

# handle get requests
def get_data(endpoint):
    api_url = "https://api.pro.coinbase.com/"
    auth = CoinbaseExchangeAuth(API_KEY, API_SECRET, API_PASS)
    r = requests.get(api_url + endpoint, auth=auth)
    return r.json()

# get all account info with a balance: api.pro.coinbase.com/accounts
def get_all_accounts():
    data = get_data("accounts")
    accounts = []
    for key in data:
        bal = float(key["balance"])
        if(bal > 0):
            accounts.append(key["id"])
    return accounts

# get single account info: api.pro.coinbase.com/accounts/<account_id>
def get_account(account_id):
    data = get_data(f"accounts/{account_id}")
    print(data)
    print()

accounts = get_all_accounts()
for account in accounts:
    get_account(account)

