from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    BINANCE_API_KEY= os.getenv("BINANCE_API_KEY", "YOUR_API_KEY_HERE")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "YOUR_API_SECRET_HERE")
    TESTNET_URL= os.getenv("BINANCE_TESTNET_URL", "https://testnet.binance.vision")
    DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "ETHUSDT")


def load_config():
    return Config()
