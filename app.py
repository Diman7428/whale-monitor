import streamlit as st
import requests
import pandas as pd
import time
import telebot
from datetime import datetime
import threading

# !!! Обязательно вставьте ваши данные между кавычками !!!
ETHERSCAN_API_KEY = '5YSHJAXPZ3SBQXYGU2D7FWU7SRWIRQSPP8'
TELEGRAM_BOT_TOKEN = '8602846394:AAHGycjHrlQAbd4QqVk-KvWMclpm5AQD7rM'
CHANNEL_ID = '@Crypto_alert_my' # Юзернейм вашего созданного канала
REFERRAL_LINK = 'ВАША_РЕФЕРАЛЬНАЯ_ССЫЛКА'

ETH_THRESHOLD = 500
STABLE_THRESHOLD = 1000000

USDT_CONTRACT = "0xdac17f958d2ee523a2206206994597c13d831ec7"
USDC_CONTRACT = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
API_URL = "https://etherscan.io"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

if "global_history" not in st.get_nav_to_all_sections_by_name if hasattr(st, "get_nav_to_all_sections_by_name") else globals():
    @st.cache_resource
    def get_shared_history(): return []
    SHARED_HISTORY = get_shared_history()
else:
    SHARED_HISTORY = []

def get_latest_block():
    try:
        res = requests.get(API_URL, params={"module": "proxy", "action": "eth_blockNumber", "apikey": ETHERSCAN_API_KEY}, timeout=10).json()
        return int(res["result"], 16)
    except: return None

def save_and_notify(asset, value, from_addr, to_addr, tx_hash):
    now = datetime.now().strftime("%H:%M:%S")
    SHARED_HISTORY.append({"Время": now, "Актив": asset, "Сумма": f"{value:,.2f}", "Откуда": f"{from_addr[:6]}...", "Куда": f"{to_addr[:6]}..."})
    if len(SHARED_HISTORY) > 50: SHARED_HISTORY.pop(0)

    emoji = "🟢" if asset in ["USDT", "USDC"] else "🔷"
    formatted = f"${value:,.2f}" if asset in ["USDT", "USDC"] else f"{value:.2f} ETH"
    msg = f"🚨 **ОБНАРУЖЕН КИТ ({asset})!** 🚨\n\n{emoji} **Сумма:** `{formatted}`\n➡️ **Откуда:** `{from_addr[:10]}...`\n⬅️ **Куда:** `{to_addr[:10]}...`\n\n🔗 [Смотреть на Etherscan](https://etherscan.io{tx_hash})\n\n📈 *Торгуй по сигналам:* [Регистрация на бирже]({REFERRAL_LINK})"
    try: bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown", disable_web_page_preview=True)
    except: pass

def check_blockchain():
    last_block = get_latest_block()
    if not last_block: return
    while True:
        try:
            current_block = get_latest_block()
            if current_block and current_block > last_block:
                res = requests.get(API_URL, params={"module": "account", "action": "tokentx", "startblock": last_block + 1, "endblock": 99999999, "page": 1, "offset": 30, "sort": "desc", "apikey": ETHERSCAN_API_KEY}, timeout=10).json()
                if res.get("status") == "1":
                    for tx in res.get("result", []):
                        contract = tx.get("contractAddress", "").lower()
                        value = int(tx.get("value", 0)) / (10 ** int(tx.get("tokenDecimal", 18)))
                        if contract in [USDT_CONTRACT.lower(), USDC_CONTRACT.lower()] and value >= STABLE_THRESHOLD:
                            save_and_notify("USDT" if contract == USDT_CONTRACT.lower() else "USDC", value, tx['from'], tx['to'], tx['hash'])
                for b in range(last_block + 1, current_block + 1):
                    eth_res = requests.get(API_URL, params={"module": "proxy", "action": "eth_getBlockByNumber", "tag": hex(b), "boolean": "true", "apikey": ETHERSCAN_API_KEY}, timeout=10).json()
                    for tx in eth_res.get("result", {}).get("transactions", []):
                        val_eth = int(tx.get("value", "0x0"), 16) / 10**18
                        if val_eth >= ETH_THRESHOLD: save_and_notify("ETH", val_eth, tx['from'], tx['to'], tx['hash'])
                last_block = current_block
            time.sleep(25)
        except: time.sleep(15)

if "blockchain_thread" not in st.get_nav_to_all_sections_by_name if hasattr(st, "get_nav_to_all_sections_by_name") else globals():
    @st.cache_resource
    def start_background_monitor():
        threading.Thread(target=check_blockchain, daemon=True).start()
        return True
    start_background_monitor()

st.set_page_config(page_title="Whale Monitor", page_icon="📊", layout="wide")
st.title("📊 Мониторинг Крупных Транзакций")
if SHARED_HISTORY:
    st.dataframe(pd.DataFrame(SHARED_HISTORY).iloc[::-1], use_container_width=True)
else:
    st.info("Ожидание транзакций китов из блокчейна сети Ethereum...")
if st.button("🔄 Обновить"): st.rerun()
