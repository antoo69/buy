from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client, filters
import qrcode
import io
from PIL import Image
from config import *

# Database setup for coins and payments
def setup_coin_database():
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_coins (
            user_id INTEGER PRIMARY KEY,
            coins INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Coin prices and payment details
COIN_PACKAGES = {
    "basic": {"coins": 5, "price": 5000},
    "medium": {"coins": 25, "price": 20000}, 
    "premium": {"coins": 50, "price": 35000}
}

PAYMENT_METHODS = {
    "dana": "081234567890",
    "gopay": "081234567890",
    "ovo": "081234567890",
    "barcode": ".png"
}

COST_PER_MESSAGE = 1  # Cost in coins to send one message

# Helper functions
def get_user_coins(user_id):
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM user_coins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def add_coins(user_id, amount):
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_coins (user_id, coins) 
        VALUES (?, ?) 
        ON CONFLICT(user_id) 
        DO UPDATE SET coins = coins + ?
    """, (user_id, amount, amount))
    conn.commit()
    conn.close()

def deduct_coins(user_id, amount):
    if get_user_coins(user_id) >= amount:
        conn = sqlite3.connect(database_file)
        cursor = conn.cursor()
        cursor.execute("UPDATE user_coins SET coins = coins - ? WHERE user_id = ?", 
                      (amount, user_id))
        conn.commit()
        conn.close()
        return True
    return False

def generate_qr(payment_data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(payment_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# Command handlers
@app.on_message(filters.command("coins"))
async def check_coins(client, message):
    user_id = message.from_user.id
    coins = get_user_coins(user_id)
    await message.reply(f"💰 Your current balance: {coins} coins")

@app.on_message(filters.command("buy"))
async def buy_coins(client, message):
    keyboard = []
    for package, details in COIN_PACKAGES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{package.title()} - {details['coins']} coins (Rp {details['price']:,})",
                callback_data=f"buy_{package}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply(
        "🪙 Select a coin package to purchase:",
        reply_markup=reply_markup
    )

@app.on_callback_query(filters.regex(r"^buy_(.+)"))
async def process_coin_purchase(client, callback_query):
    package = callback_query.matches[0].group(1)
    if package in COIN_PACKAGES:
        package_details = COIN_PACKAGES[package]
        
        keyboard = []
        for method, number in PAYMENT_METHODS.items():
            keyboard.append([
                InlineKeyboardButton(
                    method.upper(),
                    callback_data=f"pay_{package}_{method}"
                )
            ])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await callback_query.message.reply(
            f"💳 Select payment method for {package_details['coins']} coins "
            f"(Rp {package_details['price']:,}):",
            reply_markup=reply_markup
        )

@app.on_callback_query(filters.regex(r"^pay_(.+)_(.+)"))
async def show_payment_details(client, callback_query):
    package, method = callback_query.matches[0].groups()
    package_details = COIN_PACKAGES[package]
    payment_number = PAYMENT_METHODS[method]
    
    # Generate QR code
    qr_data = f"{method.upper()}: {payment_number}\nAmount: Rp {package_details['price']:,}"
    qr_image = generate_qr(qr_data)
    
    keyboard = [[
        InlineKeyboardButton(
            "✅ I have paid",
            callback_data=f"confirm_{package}"
        )
    ]]
    
    await callback_query.message.reply_photo(
        qr_image,
        caption=f"📱 {method.upper()} Payment Details:\n"
                f"Number: {payment_number}\n"
                f"Amount: Rp {package_details['price']:,}\n\n"
                f"Please send the exact amount and click 'I have paid' after payment.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_callback_query(filters.regex(r"^confirm_(.+)"))
async def confirm_payment(client, callback_query):
    package = callback_query.matches[0].group(1)
    user_id = callback_query.from_user.id
    
    if package in COIN_PACKAGES:
        coins = COIN_PACKAGES[package]["coins"]
        add_coins(user_id, coins)
        await callback_query.message.reply(
            f"✅ Payment confirmed!\n"
            f"Added {coins} coins to your balance.\n"
            f"Current balance: {get_user_coins(user_id)} coins"
        )

# Modified message handler to check for coins
@app.on_message(filters.private & ~filters.command(["start", "coins", "buy"]))
async def handle_message(client, message):
    user_id = message.from_user.id
    
    if not deduct_coins(user_id, COST_PER_MESSAGE):
        await message.reply(
            "❌ Insufficient coins! You need 1 coin to send a message.\n"
            "Use /buy to purchase coins or /coins to check your balance."
        )
        return
    
    # Continue with regular message processing...
    # (Your existing message handling code goes here)

setup_coin_database()

