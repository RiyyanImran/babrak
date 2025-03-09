import streamlit as st
import requests
import pandas as pd
import time
import csv
import hmac
import hashlib
import base64
import json
from datetime import datetime

def get_market_data():
    url = "https://api.btcturk.com/api/v2/ticker"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["data"]
    else:
        st.error("Failed to fetch market data")
        return []

def generate_signature(api_key, api_secret):
    timestamp = str(int(time.time() * 1000))
    message = f"{api_key}{timestamp}".encode('utf-8')
    signature = hmac.new(api_secret.encode('utf-8'), message, hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    return timestamp, signature_b64

def execute_trade(order_type, pair, amount, api_key, api_secret):
    url = "https://api.btcturk.com/api/v1/order"
    timestamp, signature = generate_signature(api_key, api_secret)
    payload = {
        "pairSymbol": pair,
        "orderType": order_type,
        "amount": amount
    }
    headers = {
        "X-PCK": api_key,
        "X-Stamp": timestamp,
        "X-Signature": signature,
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        st.success(f"{order_type} order placed for {pair} - Amount: {amount}")
        log_trade(pair, order_type, amount)
    else:
        st.error(f"Failed to execute trade: {response.text}")

def log_trade(pair, order_type, amount):
    with open("trade_history.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), pair, order_type, amount])

def monitor_and_trade(selected_coins, trade_amount, profit_target, api_key, api_secret):
    buy_prices = {}
    while True:
        data = get_market_data()
        if not data:
            continue
        for coin in data:
            if coin["pair"] in selected_coins:
                current_price = float(coin["last"])
                if coin["pair"] not in buy_prices:
                    buy_price = float(coin["average"]) * 0.95  # Simulated buy price
                    execute_trade("BUY", coin["pair"], trade_amount, api_key, api_secret)
                    buy_prices[coin["pair"]] = buy_price
                sell_price = buy_prices[coin["pair"]] * (1 + profit_target / 100)
                if current_price >= sell_price:
                    execute_trade("SELL", coin["pair"], trade_amount, api_key, api_secret)
                    del buy_prices[coin["pair"]]
        time.sleep(10)

def main():
    st.title("BTC Turk Trading Bot")
    
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
        st.session_state.api_secret = ""
    st.session_state.api_key = st.text_input("Enter API Key", type="password")
    st.session_state.api_secret = st.text_input("Enter API Secret", type="password")
    
    menu = ["Market Data", "Trade Recommendations", "Trade Execution", "Trade History", "Bot Control"]
    choice = st.sidebar.selectbox("Navigation", menu)
    
    if choice == "Market Data":
        data = get_market_data()
        if data:
            df = pd.DataFrame(data)
            df = df[["pair", "last", "high", "low", "volume", "average"]]
            st.dataframe(df)
    elif choice == "Trade Recommendations":
        available_coins = [coin["pair"] for coin in get_market_data()]
        selected_coins = st.multiselect("Select Coins for Automated Trading", available_coins, default=available_coins[:3])
        st.session_state.selected_coins = selected_coins
    elif choice == "Trade Execution":
        trade_amount = st.number_input("Trade Amount", min_value=0.001, step=0.001)
        profit_target = st.number_input("Profit Target (%)", min_value=1.0, step=0.1)
        if st.button("Start Automated Trading"):
            st.success("Automated Trading Started")
            monitor_and_trade(st.session_state.selected_coins, trade_amount, profit_target, st.session_state.api_key, st.session_state.api_secret)
    elif choice == "Trade History":
        try:
            df = pd.read_csv("trade_history.csv", names=["Timestamp", "Pair", "Order Type", "Amount"])
            st.dataframe(df)
        except FileNotFoundError:
            st.warning("No trade history available.")
    elif choice == "Bot Control":
        if st.button("Start Bot"):
            st.success("Trading Bot Started")
        if st.button("Stop Bot"):
            st.warning("Trading Bot Stopped")

if __name__ == "__main__":
    main()
