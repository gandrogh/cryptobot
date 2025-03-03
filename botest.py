import ccxt
import time
import logging
import pandas as pd

# Configuration API KuCoin
exchange = ccxt.kucoin({
    'apiKey': '************',
    'secret': '************************',
    'password': '*******************',
    'enableRateLimit': True,
})
exchange.load_markets()

# Configuration du logging
logging.basicConfig(filename='trading_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

def get_market_price(exchange, symbol):
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

def get_min_trade_limits(exchange, symbol):
    market = exchange.markets[symbol]
    return market['limits']['amount']['min'], market['limits']['cost']['min']

def get_balance(exchange, currency):
    balance = exchange.fetch_balance()
    return balance['total'].get(currency, 0)

def cancel_order_if_unfilled(exchange, order_id, symbol, timeout=60):
    """ Annule l'ordre d'achat s'il n'est pas exécuté après timeout secondes """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            order = exchange.fetch_order(order_id, symbol)
            if order['status'] == 'closed':
                logging.info(f"✅ Ordre {order_id} exécuté.")
                return True
        except Exception as e:
            logging.warning(f"⚠ Erreur lors de la vérification de l'ordre {order_id} : {str(e)}")
        time.sleep(5)

    try:
        exchange.cancel_order(order_id, symbol)
        logging.info(f"❌ Ordre {order_id} annulé après {timeout}s d'inactivité.")
    except Exception as e:
        logging.error(f"⚠ Erreur lors de l'annulation de l'ordre {order_id} : {str(e)}")
    
    return False

def monitor_orders(exchange, sl_order_id, tp_order_id, symbol):
    """ Surveille les ordres SL et TP et annule l'autre dès qu'un est exécuté """
    while True:
        try:
            sl_order = exchange.fetch_order(sl_order_id, symbol)
            tp_order = exchange.fetch_order(tp_order_id, symbol)
            
            if sl_order['status'] == 'closed':
                logging.info(f"🔴 Stop-Loss exécuté, annulation du Take-Profit ({tp_order_id})")
                exchange.cancel_order(tp_order_id, symbol)
                break

            if tp_order['status'] == 'closed':
                logging.info(f"🟢 Take-Profit exécuté, annulation du Stop-Loss ({sl_order_id})")
                exchange.cancel_order(sl_order_id, symbol)
                break
            
        except Exception as e:
            logging.warning(f"⚠ Erreur lors de la surveillance des ordres : {str(e)}")

        time.sleep(5)  # Vérification toutes les 5 secondes

def update_trailing_stop(exchange, symbol, buy_price, sl_order_id, current_price, trailing_stop_percent=0.5):
    """ Mets à jour le Stop-Loss en fonction du trailing stop et de l'évolution du marché """
    stop_loss_price = buy_price * (1 - trailing_stop_percent / 100)
    
    if current_price > buy_price * (1 + trailing_stop_percent / 100):
        stop_loss_price = current_price * (1 - trailing_stop_percent / 100)
        logging.info(f"🔄 Mise à jour du Stop-Loss à {stop_loss_price} USDT")
        
        try:
            # Mise à jour du Stop-Loss LIMIT
            exchange.cancel_order(sl_order_id, symbol)
            sl_order = exchange.create_order(symbol, "limit", "sell", amount, stop_loss_price)
            logging.info(f"🟢 Nouveau Stop-Loss placé à {stop_loss_price} USDT")
            return sl_order['id']
        except Exception as e:
            logging.error(f"⚠ Erreur lors de la mise à jour du Stop-Loss : {str(e)}")
            return sl_order_id  # Si l'erreur survient, retourner l'ID actuel du SL pour éviter un crash
    return sl_order_id

def fetch_candles(exchange, symbol, timeframe='5m', limit=50):
    candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df


    
def calculate_indicators(df):
    # Calcul de l'EMA
    df['EMA'] = df['close'].ewm(span=14, adjust=False).mean()

    # Calcul du RSI
    delta = df['close'].diff()  # Différence des prix de clôture
    gain = delta.where(delta > 0, 0)  # Gagner uniquement quand delta est positif
    loss = -delta.where(delta < 0, 0)  # Perdre uniquement quand delta est négatif

    avg_gain = gain.rolling(window=14).mean()  # Moyenne des gains sur 14 périodes
    avg_loss = loss.rolling(window=14).mean()  # Moyenne des pertes sur 14 périodes

    # Calcul du RSI
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    return df


def place_limit_buy_with_sl_tp(exchange, symbol, capital, risk_percent=0.5, sl_percent=0.2, tp_percent=0.5, trailing_stop_percent=0.5):
    market_price = get_market_price(exchange, symbol)
    if not market_price:
        logging.error("❌ Impossible de récupérer le prix du marché.")
        return
    
    min_amount, min_cost = get_min_trade_limits(exchange, symbol)
    investment_amount = (capital * risk_percent) / 100
    amount = investment_amount / market_price
    
    if amount < min_amount:
        amount = min_amount
    if (amount * market_price) < min_cost:
        amount = min_cost / market_price
    
    buy_price = round(market_price * 0.999, 5)
    stop_loss_price = round(buy_price * (1 - sl_percent / 100), 5)
    take_profit_price = round(buy_price * (1 + tp_percent / 100), 5)
    
    balance = get_balance(exchange, 'USDT')
    if balance < (amount * buy_price):
        logging.error("❌ Solde insuffisant pour passer l'ordre.")
        return
    
    # 📊 Récupération des données des chandeliers et calcul des indicateurs
    df = fetch_candles(exchange, symbol)
    df = calculate_indicators(df)
    
    # 🔴 Stratégie avec indicateurs
    rsi = df['RSI'].iloc[-1]
    ema = df['EMA'].iloc[-1]
    current_price = df['close'].iloc[-1]

    # Stratégie RSI et EMA
    if rsi > 70:
        logging.info("⚠ RSI trop élevé, éviter d'acheter en surachat.")
        return

    if rsi < 30 and current_price > ema:  # Signal d'achat : RSI < 30 et prix supérieur à EMA
        try:
            # 📌 Placement de l'ordre d'achat
            buy_order = exchange.create_order(symbol, "limit", "buy", amount, buy_price)
            if buy_order:
                order_id = buy_order['id']
                logging.info(f"✅ Ordre d'achat {order_id} placé à {buy_price} USDT.")

                # 📌 Annulation automatique si non exécuté après 60s
                if not cancel_order_if_unfilled(exchange, order_id, symbol):
                    return  # Ne place pas les ordres SL et TP si l'achat n'a pas été exécuté

                # 📌 Placement du Stop-Loss Limit
                sl_order = exchange.create_order(symbol, "limit", "sell", amount, stop_loss_price)
                sl_order_id = sl_order['id']
                logging.info(f"🔴 Stop-Loss placé à {stop_loss_price} USDT")
                
                # 📌 Placement du Take-Profit Limit
                tp_order = exchange.create_order(symbol, "limit", "sell", amount, take_profit_price)
                tp_order_id = tp_order['id']
                logging.info(f"🟢 Take-Profit placé à {take_profit_price} USDT")
                
                # 📌 Lancer la surveillance des ordres pour annulation automatique
                monitor_orders(exchange, sl_order_id, tp_order_id, symbol)
                
                # 📌 Trailing Stop : Suivi du prix et mise à jour du Stop
                while True:
                    current_price = get_market_price(exchange, symbol)
                    sl_order_id = update_trailing_stop(exchange, symbol, buy_price, sl_order_id, current_price, trailing_stop_percent)
                    time.sleep(2)  # Mise à jour toutes les 2 secondes pour ne pas dépasser la limite API

        except Exception as e:
            logging.error(f"❌ Erreur lors du placement des ordres : {str(e)}")
    else:
        logging.info(f"⚠ Pas de signal d'achat, conditions non remplies (RSI : {rsi}, EMA : {ema})")

ticker = "BTC/USDT"
capital = 30
while True:
    try:
        place_limit_buy_with_sl_tp(exchange, ticker, capital)
    except Exception as e:
        logging.error(f"❌ Erreur dans l'exécution du bot : {str(e)}")
    
    time.sleep(5)  # Attente de 5 secondes avant de réexécuter
