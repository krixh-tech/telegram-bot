import os
import json
import uuid
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# 1. CONFIGURATION
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))  
UPI_ID = "harshalx11@fam"

if not BOT_TOKEN:
    logging.error("BOT_TOKEN missing! Add it in Railway Variables.")
    exit(1)

# ==========================================
# 2. LOCAL JSON DATABASE SETUP
# ==========================================
DB_FILE = "database.json"

def load_db():
    # Agar file nahi hai, toh nayi banao
    if not os.path.exists(DB_FILE):
        return {
            "users": {},
            "orders": {},
            "products": {
                "flipkart": {"name": "FLIPKART 1k Coupon", "price": 100, "min_buy": 1, "stock": []},
                "shein4k": {"name": "SHEIN 4k Coupon", "price": 50, "min_buy": 2, "stock": []},
                "shein2k": {"name": "SHEIN 2k Coupon", "price": 30, "min_buy": 3, "stock": []},
                "gplay": {"name": "Google Play Redeem 1k", "price": 100, "min_buy": 1, "stock": []}
            }
        }
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # Agar file corrupt ho jaye toh fix karne ke liye
        return {"users": {}, "orders": {}, "products": {
                "flipkart": {"name": "FLIPKART 1k Coupon", "price": 100, "min_buy": 1, "stock": []},
                "shein4k": {"name": "SHEIN 4k Coupon", "price": 50, "min_buy": 2, "stock": []},
                "shein2k": {"name": "SHEIN 2k Coupon", "price": 30, "min_buy": 3, "stock": []},
                "gplay": {"name": "Google Play Redeem 1k", "price": 100, "min_buy": 1, "stock": []}
            }}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==========================================
# 3. BOT INITIALIZATION
# ==========================================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class CheckoutState(StatesGroup):
    waiting_for_screenshot = State()
    product_id = State()
    quantity = State()
    total_price = State()

# ==========================================
# 4. SHOP MENU & COMMANDS
# ==========================================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    # MAGIC FIX 1: Stuck commands ko clear karega
    await state.clear() 
    
    db = load_db()
    user_id = str(message.from_user.id)
    username = message.from_user.username or "User"
    
    # User ko DB mein save karo
    if user_id not in db["users"]:
        db["users"][user_id] = {"username": username}
        save_db(db)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 FLIPKART 1k Coupon - ₹100", callback_data="buy_flipkart")],
        [InlineKeyboardButton(text="👗 SHEIN 4k Coupon - ₹50 (Min 2)", callback_data="buy_shein4k")],
        [InlineKeyboardButton(text="👗 SHEIN 2k Coupon - ₹30 (Min 3)", callback_data="buy_shein2k")],
        [InlineKeyboardButton(text="🎮 Google Play 1k Code - ₹100", callback_data="buy_gplay")]
    ])
    
    await message.answer(f"Welcome to the Digital Store, @{username}!\nSelect a product to buy:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback_query: types.CallbackQuery, state: FSMContext):
    product_id = callback_query.data.split("_")[1]
    db = load_db()
    
    if product_id not in db["products"]:
        return await callback_query.answer("Invalid product.")

    prod = db["products"][product_id]
    total_price = prod["price"] * prod["min_buy"]
    
    await state.update_data(product_id=product_id, quantity=prod["min_buy"], total_price=total_price)
    await state.set_state(CheckoutState.waiting_for_screenshot)
    
    msg = (f"🛍 **{prod['name']}**\n\n"
           f"Minimum Buy: {prod['min_buy']}\n"
           f"Total Price: ₹{total_price}\n\n"
           f"💳 **Payment Instructions:**\n"
           f"1. Pay exactly ₹{total_price} to UPI: `{UPI_ID}`\n"
           f"2. Send the payment screenshot here in this chat.")
    
    await callback_query.message.answer(msg, parse_mode="Markdown")
    await callback_query.answer()

# ==========================================
# 5. HANDLE PAYMENT SCREENSHOTS
# ==========================================
@dp.message(CheckoutState.waiting_for_screenshot, F.photo)
async def handle_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.photo[-1].file_id
    order_id = str(uuid.uuid4())[:8]
    
    db = load_db()
    product_name = db["products"][data["product_id"]]["name"]
    username = message.from_user.username or "User"
    
    db["orders"][order_id] = {
        "user_id": message.from_user.id,
        "username": username,
        "product_id": data["product_id"],
        "product_name": product_name,
        "quantity": data["quantity"],
        "total_price": data["total_price"],
        "status": "PENDING"
    }
    save_db(db)
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{order_id}")],
        [InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{order_id}")]
    ])
    
    caption = (f"🚨 **NEW ORDER ALERT** 🚨\n\n"
               f"📝 Order ID: {order_id}\n"
               f"👤 User: @{username} ({message.from_user.id})\n"
               f"🛍 Product: {product_name}\n"
               f"📦 Qty: {data['quantity']}\n"
               f"💰 Amount: ₹{data['total_price']}")
               
    await bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=caption, reply_markup=admin_kb, parse_mode="Markdown")
    await message.answer("✅ Payment screenshot received! Please wait while an admin verifies your payment.")
    await state.clear()

# ==========================================
# 6. ADMIN APPROVAL LOGIC
# ==========================================
@dp.callback_query(F.data.startswith("approve_"))
async def admin_approve(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        return await callback_query.answer("Not authorized.")
        
    order_id = callback_query.data.split("_")[1]
    db = load_db()
    
    if order_id not in db["orders"] or db["orders"][order_id]["status"] != "PENDING":
        return await callback_query.answer("Order already processed or not found.")

    order = db["orders"][order_id]
    product_id = order["product_id"]
    product = db["products"][product_id]
    
    if len(product["stock"]) < order["quantity"]:
        return await callback_query.message.answer(f"⚠️ Insufficient stock for {product['name']}. Please add stock first using /addstock.")

    codes_to_send = product["stock"][:order["quantity"]]
    db["products"][product_id]["stock"] = product["stock"][order["quantity"]:]
    db["orders"][order_id]["status"] = "APPROVED"
    save_db(db)

    codes_text = "\n".join(codes_to_send)
    await bot.send_message(
        order["user_id"], 
        f"🎉 **Payment Approved!**\n\nHere are your codes for {order['product_name']}:\n\n`{codes_text}`", 
        parse_mode="Markdown"
    )
    await callback_query.message.edit_caption(caption=f"✅ **APPROVED & DELIVERED**\nOrder: {order_id}\nTo: {order['user_id']}")

@dp.callback_query(F.data.startswith("reject_"))
async def admin_reject(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        return await callback_query.answer("Not authorized.")
        
    order_id = callback_query.data.split("_")[1]
    db = load_db()
    
    if order_id in db["orders"]:
        db["orders"][order_id]["status"] = "REJECTED"
        save_db(db)
        await bot.send_message(db["orders"][order_id]["user_id"], f"❌ Your payment for {db['orders'][order_id]['product_name']} was rejected.")
    
    await callback_query.message.edit_caption(caption=f"❌ **REJECTED**\nOrder: {order_id}")

# ==========================================
# 7. ADMIN COMMANDS (/addstock & /sendproduct)
# ==========================================
@dp.message(Command("addstock"))
async def cmd_addstock(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    args = message.text.split(" ", 2)
    if len(args) < 3:
        return await message.answer("⚠️ Usage: `/addstock <product_id> <code1,code2,...>`\n\nValid IDs: `flipkart`, `shein4k`, `shein2k`, `gplay`", parse_mode="Markdown")
        
    product_id = args[1].lower()
    codes_to_add = [code.strip() for code in args[2].split(",")]
    
    db = load_db()
    if product_id not in db["products"]:
        return await message.answer("❌ Invalid product ID.")
        
    db["products"][product_id]["stock"].extend(codes_to_add)
    save_db(db)
    
    await message.answer(f"✅ Successfully added {len(codes_to_add)} codes to {db['products'][product_id]['name']}.\nTotal Stock: {len(db['products'][product_id]['stock'])}")

@dp.message(Command("sendproduct"))
async def cmd_sendproduct(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    args = message.text.split(" ", 2)
    if len(args) < 3:
        return await message.answer("⚠️ Usage: /sendproduct <user_id> <code>")
        
    target_user_id = int(args[1])
    code = args[2]
    
    try:
        await bot.send_message(target_user_id, f"🎁 **You have received a product from Admin!**\n\n`{code}`", parse_mode="Markdown")
        await message.answer(f"✅ Successfully sent to {target_user_id}")
    except Exception:
        await message.answer("❌ Failed to send. Maybe the user hasn't started the bot.")

# ==========================================
# 8. RUN BOT
# ==========================================
async def main():
    # MAGIC FIX 2: Yeh line Telegram ko batayegi ki purane latke hue messages delete karo aur fresh start karo
    await bot.delete_webhook(drop_pending_updates=True) 
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
