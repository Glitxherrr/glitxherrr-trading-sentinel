import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

print("Environment Loaded SUCCESSFULLY.")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

DEFAULT_EXCHANGE = os.getenv("DEFAULT_EXCHANGE", "binance").strip()
DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "BTC/USDT").strip()
DEFAULT_TIMEFRAME = os.getenv("DEFAULT_TIMEFRAME", "15m").strip()

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY is missing. Add it in the .env file.")
