import ccxt
import yfinance as yf
import pandas as pd

print('CCXT version:', ccxt.__version__)  # requires CCXT version > 1.20.31
exchange = ccxt.kucoin({
    'apiKey': '67be022945e41a0001668f7e ',
    'secret': 'ca6f8519-8b50-4236-ab2f-108a23203f5b',
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # ←-------------- quotes and 'future'
    },
})
#exchange.set_sandbox_mode(True)  # enable sandbox mode PAS D'URL SANDBOX

exchange.load_markets()

# exchange.verbose = True  # uncomment this line if it doesn't work

# 🔹 PARAMÈTRES 🔹
SYMBOL = "BTC/USDT"  # Crypto tradée
EXCHANGE_NAME = "kucoin"  # Exchange (Binance, KuCoin...)
EMA_SHORT = 9
EMA_LONG = 21

# 🔹 Récupérer les données 🔹
def get_data(symbol="BTC-USD"):
    df = yf.download(symbol, period="7d", interval="1h")  # Dernière semaine en 1h
    df["EMA_SHORT"] = df["Close"].ewm(span=EMA_SHORT, adjust=False).mean()
    df["EMA_LONG"] = df["Close"].ewm(span=EMA_LONG, adjust=False).mean()
    return df

# 🔹 Détecter un Signal 🔹
def detect_signal(df):
    if df["EMA_SHORT"].iloc[-1] > df["EMA_LONG"].iloc[-1]:  
        return "BUY"
    elif df["EMA_SHORT"].iloc[-1] < df["EMA_LONG"].iloc[-1]:  
        return "SELL"
    return "HOLD"

# 🔹 Passer un Ordre 🔹
def execute_trade(signal):
    if signal == "BUY":
        print("📈 Achat détecté - Exécution de l’ordre d’achat")
        exchange.create_market_buy_order(SYMBOL, 0.001)  # Désactiver en test !
    elif signal == "SELL":
        print("📉 Vente détectée - Exécution de l’ordre de vente")
        exchange.create_market_sell_order(SYMBOL, 0.001) # Désactiver en test !

# 🔹 Exécuter le bot 🔹
df = get_data()
signal = detect_signal(df)
execute_trade(signal)
print(f"Signal détecté : {signal}")
