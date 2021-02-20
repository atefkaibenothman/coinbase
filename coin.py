import hmac
import json
import hashlib
import time
import datetime
import base64
import requests
from prettytable import PrettyTable
from requests.auth import AuthBase

# api key placeholder
API_KEY = ""
API_SECRET = ""
API_PASS = ""
# holds all active account ids
accounts = {}

# return map of necessary api keys
def get_keys():
    keys = {}
    with open("keys.json", "r", encoding="utf-8") as json_file:
        data = json.load(json_file)
        for d in data:
            keys[d] = data[d]
    return keys

# login
def login():
    keys = get_keys()
    global API_KEY
    global API_SECRET
    global API_PASS
    API_KEY = keys["key"]
    API_SECRET = keys["secret"]
    API_PASS = keys["pass"]
    get_all_accounts()
    print("logged in!")

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
    api_url = "https://api.pro.coinbase.com/" + endpoint
    auth = CoinbaseExchangeAuth(API_KEY, API_SECRET, API_PASS)
    r = requests.get(api_url, auth=auth)
    return r.json()

# get all account info with a balance: api.pro.coinbase.com/accounts
def get_all_accounts():
    global accounts
    data = get_data("accounts")
    for key in data:
        bal = float(key["balance"])
        if(bal > 0):
            accounts[key["currency"]] = key["id"]

# get single account info: api.pro.coinbase.com/accounts/<account_id>
def get_account(account_id):
    r = get_data(f"accounts/{account_id}")
    return r

# get balance for all accounts
def get_balance():
    table = PrettyTable()
    table.field_names = ["asset", "quantity"]
    for acc in accounts:
        data = get_account(accounts[acc])
        asset = data["currency"]
        bal = data["balance"]
        quantity = data["available"]
        table.add_row([asset, bal])
    print(table)

# get history for an account
def get_history(account_id):
    r = get_data(f"accounts/{account_id}/ledger")
    return r

# print history
def history():
    hist = []
    for acc in accounts:
        data = get_history(accounts[acc])
        for d in data:
            hist.append(d["details"])
    return hist

# get all orders
def get_all_orders():
    data = history()
    orders = []
    orders_set = set()
    for d in data:
        try:
            if (d["order_id"] not in orders_set):
                orders.append(d["order_id"])
            orders_set.add(d["order_id"])
        except:
            pass
    return orders

# get single order
def get_order(order_id):
    r = get_data(f"orders/{order_id}")
    return r

# print orders
def orders():
    table = PrettyTable()
    table.field_names = ["date", "type", "asset", "amount"]
    ordrs = get_all_orders()
    for order in ordrs:
        data = get_order(order)
        order_id = data["id"]
        side = data["side"]
        asset = data["product_id"]
        funds = data["funds"]
        date = data["done_at"]
        date = date.split("T")
        executed_val = data["executed_value"]
        table.add_row([date[0], side, asset, funds])
    print(table.get_string(sortby="date"))

# begin program
def run():
    r = True
    commands = ["login", "balance", "orders", "quit"]
    print("welcome to coinbase cli")
    print(f"available commands: {commands}")
    while (r):
        cmd = input("> ")
        if (cmd == "quit"):
            r = False
        if (cmd == "login"):
            login()
        if (cmd == "balance"):
            get_balance();
        if (cmd == "orders"):
            orders()

if __name__ == "__main__":
    run()

