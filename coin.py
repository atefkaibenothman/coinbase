#!/usr/bin/env python3
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
    print("logged in")

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
    auth = CoinbaseExchangeAuth(API_KEY,API_SECRET,API_PASS)        
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

# get a list of available currency pairs for trading: api.pro.coinbase.com/products
def get_all_products():
    r = get_data("products")
    prds = set()
    ticker = {}
    for i in r:
        if (i["base_currency"] in accounts and i["id"] not in prds and "USD" in i["id"]):
            ticker[i["base_currency"]] = [i["id"]]
            prds.add(i["id"])
    return ticker

# get single product info: api.coinbase.com/products/<product_id>
def get_product(product_id):
    r = get_data(f"products/{product_id}/stats")
    return r;

# get balance for all accounts
def get_balance():
    products = get_all_products() 
    for prod in products:
        t = get_product(products[prod][0])
        products[prod].append(t["last"])
    
    table = PrettyTable()
    table.field_names = ["asset", "quantity", "balance"]
    total = 0
    for acc in accounts:
        data = get_account(accounts[acc])
        asset = data["currency"]
        quantity = data["available"]
        try:
            balance = float(products[acc][1]) * float(quantity)
        except KeyError:
            balance = 0
        total += balance
        table.add_row([asset, quantity, balance])
    table.add_row(["total", "-", total])
    print(table.get_string(sortby="balance", reversesort=True))

# get history for an account
def get_history(account_id):
    r = get_data(f"accounts/{account_id}/ledger")
    return r

# get transfer information: api.coinbase.com/transfers/<transfer_id>
def get_transfer(transfer_id):
    r = get_data(f"transfers/{transfer_id}")
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
    total = 0
    for order in ordrs:
        data = get_order(order)
        order_id = data["id"]
        side = data["side"]
        asset = data["product_id"]
        funds = data["funds"]
        date = data["done_at"]
        date = date.split("T")
        executed_val = data["executed_value"]
        total += float(executed_val)
        table.add_row([date[0], side, asset, executed_val])
    total += 199.0045910997000000 + 199.0045910997000000 + 99.0045910997000000 + 49.74480
    table.add_row(["2021-01-12", "buy", "ETH-USD", 199.0045910997000000])
    table.add_row(["2021-01-21", "buy", "ETH-USD", 199.0045910997000000])
    table.add_row(["2021-02-05", "buy", "ETH-USD", 99.0045910997000000])
    table.add_row(["2021-02-08", "buy", "BTC-USD", 49.7448000000000000])
    table.add_row(["total", "", "", total])
    print(table.get_string(sortby="date"))

# get account details
def account():
    table = PrettyTable()
    table.field_names = ["name", "id"]
    for acc in accounts:
        table.add_row([acc, accounts[acc]])
    print(table)

# create summary of all stats
def summary():
    ordrs = get_all_orders()
    products = {} 
    for order in ordrs:
        data = get_order(order)
        executed_val = float(data["executed_value"])
        pid = data["product_id"].split("-")[0]
        if (pid not in products):
            products[pid] = [executed_val]
        else:
            products[pid].append(executed_val)
        products[pid] = [sum(products[pid])]

    for acc in accounts:
        if (acc not in products):
            products[acc] = [0]

    for acc in accounts:
        data = get_account(accounts[acc])
        quantity = data["available"]
        products[acc].append(quantity)

    try:
        del products["USD"]
    except KeyError:
        pass

    ticker = get_all_products() 
    for prod in ticker:
        t = get_product(ticker[prod][0])
        ticker[prod].append(t["last"])

    products["ETH"][0] += 491.03
    products["BTC"][0] += 49.50

    table = PrettyTable()
    table.field_names = ["asset", "total deposit", "balance", "increase", "profit", "quantity", "price"]
    dep = 0
    bal = 0
    prof = 0
    for product in products:
        products[product].append(ticker[product][1])
        asset = product
        total_deposit = float(products[product][0])
        dep += total_deposit
        quantity = float(products[product][1])
        price = float(products[product][2])
        balance = price * quantity
        bal += balance
        try:
            increase = ((balance - total_deposit) / total_deposit)
        except ZeroDivisionError:
            increase = 100
        increase = "{:.2%}".format(increase)
        profit = balance - total_deposit
        prof += profit
        total_deposit = "{:.2f}".format(total_deposit)
        balance = "{:.2f}".format(balance)
        # profit = "{:.2f}".format(profit)
        profit = str(round(profit, 2))
        table.add_row([asset, total_deposit, balance, increase, profit, quantity, price])
    total_increase = ((bal - dep)/dep)
    total_increase = "{:.2%}".format(total_increase)
    bal = "{0:.2f}".format(bal)
    dep = "{0:.2f}".format(dep)
    prof = str(round(prof, 2))
    R = "\033[1;31;40m" #RED
    G = "\033[0;32;40m" # GREEN
    LG = "\033[1;32;40m" # LIGHT GREEN
    Y = "\033[1;33;40m" # Yellow
    B = "\033[1;34;40m" # Blue
    N = "\033[0m" # Reset
    table.add_row([Y+"TOTAL"+N, R+dep+N, LG+bal+N, LG+total_increase+N, LG+prof+N, "-", "-"])
    table.align = "r"
    print(table)

        
# begin program
def run():
    r = True
    commands = ["login", "balance", "orders", "quit", "account", "summary"]
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
        if (cmd == "account"):
            account()
        if (cmd == "summary"):
            summary()

if __name__ == "__main__":
    run()
