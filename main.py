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
    if not os.path.exists(DB_FILE):
        return {
            "users": {},
            "orders": {},
            "products": {
                "flipkart": {"name": "FLIPKART 1k Coupon", "price": 100, "min_buy": 1, "stock": []},
                "shein4k": {"name": "SHEIN 4k Coupon", "price": 50, "min_buy": 2, "stock": []},
                "shein2k": {"name": "SHEIN 2k Coupon", "price": 30, "min_buy": 3, "stock": []},
                "gplay": {"name": "Google Play Redeem 1k", "price": 100, "min_buy": 1, "stock": []},
                "sheinbot": {"name": "Auto Shein Order Bot", "price": 150, "min_buy": 1, "stock": []} 
            }
        }
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "orders": {}, "products": {
                "flipkart": {"name": "FLIPKART 1k Coupon", "price": 100, "min_buy": 1, "stock": []},
                "shein4k": {"name": "SHEIN 4k Coupon", "price": 50, "min_buy": 2, "stock": []},
                "shein2k": {"name": "SHEIN 2k Coupon", "price": 30, "min_buy": 3, "stock": []},
                "gplay": {"name": "Google Play Redeem 1k", "price": 100, "min_buy": 1, "stock": []},
                "sheinbot": {"name": "Auto Shein Order Bot", "price": 150, "min_buy": 1, "stock": []} 
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
    await state.clear() 
    db = load_db()
    user_id = str(message.from_user.id)
    username = message.from_user.username or "User"
    
    if user_id not in db["users"]:
        db["users"][user_id] = {"username": username}
        save_db(db)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 FLIPKART 1k Coupon - ₹100", callback_data="buy_flipkart")],
        [InlineKeyboardButton(text="👗 SHEIN 4k Coupon - ₹50 (Min 2)", callback_data="buy_shein4k")],
        [InlineKeyboardButton(text="👗 SHEIN 2k Coupon - ₹30 (Min 3)", callback_data="buy_shein2k")],
        [InlineKeyboardButton(text="🎮 Google Play 1k Code - ₹100", callback_data="buy_gplay")],
        [InlineKeyboardButton(text="🤖 Auto Shein Order Bot - ₹150", callback_data="buy_sheinbot")] 
    ])
    
    await message.answer(f"Welcome to the Digital Store, @{username}!\nSelect a product to buy:\n\n(Type /myorders to check your purchase history)", reply_markup=keyboard)

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
# 5. USER COMMAND: /myorders
# ==========================================
@dp.message(Command("myorders"))
async def cmd_myorders(message: types.Message):
    db = load_db()
    user_id = message.from_user.id
    
    # User ke saare orders nikalna
    user_orders = []
    for order_id, order_data in db["orders"].items():
        if order_data["user_id"] == user_id:
            user_orders.append((order_id, order_data))
            
    if not user_orders:
        return await message.answer("🤷‍♂️ You haven't placed any orders yet. Type /start to browse the shop!")
        
    # Sirf aakhiri 10 orders dikhayenge taaki message bohot bada na ho jaye
    user_orders = list(reversed(user_orders))[:10]
    
    msg_lines = ["📜 **Your Recent Orders:**\n"]
    for oid, order in user_orders:
        # Status ke hisaab se emoji
        emoji = "⏳" if order["status"] == "PENDING" else "✅" if order["status"] == "APPROVED" else "❌"
        
        msg_lines.append(
            f"🆔 `{oid}`\n"
            f"🛍 {order['product_name']} (x{order['quantity']})\n"
            f"💰 ₹{order['total_price']} | Status: {emoji} {order['status']}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
    await message.answer("\n".join(msg_lines), parse_mode="Markdown")

# ==========================================
# 6. HANDLE PAYMENT SCREENSHOTS
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
    await message.answer("✅ Payment screenshot received! Please wait while an admin verifies your payment. Type /myorders to track status.")
    await state.clear()

# ==========================================
# 7. ADMIN APPROVAL LOGIC
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
# 8. ADMIN COMMANDS (/stats, /addstock, /sendproduct)
# ==========================================
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    db = load_db()
    total_users = len(db.get("users", {}))
    
    approved_orders = [o for o in db["orders"].values() if o["status"] == "APPROVED"]
    pending_orders = [o for o in db["orders"].values() if o["status"] == "PENDING"]
    
    total_revenue = sum(o["total_price"] for o in approved_orders)
    
    stock_info = "\n".join([f"📦 {p['name']}: {len(p['stock'])} left" for p in db["products"].values()])
    
    stats_msg = (
        f"📊 **ADMIN DASHBOARD** 📊\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🛒 Total Orders: {len(db['orders'])}\n"
        f"⏳ Pending Approvals: {len(pending_orders)}\n"
        f"💰 Total Revenue: ₹{total_revenue}\n\n"
        f"**Current Stock:**\n{stock_info}"
    )
    await message.answer(stats_msg, parse_mode="Markdown")

@dp.message(Command("addstock"))
async def cmd_addstock(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    args = message.text.split(" ", 2)
    if len(args) < 3:
        return await message.answer("⚠️ Usage: `/addstock <product_id> <code1,code2,...>`\n\nValid IDs: `flipkart`, `shein4k`, `shein2k`, `gplay`, `sheinbot`", parse_mode="Markdown")
        
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
# 9. RUN BOT
# ==========================================
async def main():
    await bot.delete_webhook(drop_pending_updates=True) 
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
