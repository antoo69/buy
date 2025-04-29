import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH") 
bot_token = os.getenv("BOT_TOKEN")
database_file = os.getenv("DATABASE_FILE", "menfess.db")
qr_pic = os.getenv("QRPIC", "qr.png")

# Payment configuration
DANA_NUMBER = os.getenv("DANA_NUMBER", "081234567890")
GOPAY_NUMBER = os.getenv("GOPAY_NUMBER", "081234567890") 
OVO_NUMBER = os.getenv("OVO_NUMBER", "081234567890")
