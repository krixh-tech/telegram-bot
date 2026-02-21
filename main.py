import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ==========================================
# 1. HARDCODED CONFIGURATION
# ==========================================
# Yahan apni actual details daalo
BOT_TOKEN = "8517481377:AAHJ4vF4SXOEuAOqyZkVudU-wiVwO9eJFNU" 
ADMIN_ID = 7510607171  # Apna Telegram ID integer format mein (bina quotes ke)
MONGO_URI = "mongodb+srv://xynif:<5%L2.rc@a2#FKXx>@cluster0.vfzuldi.mongodb.net/?appName=Cluster0"
UPI_ID = "harshalx11@fam"

# ==========================================
# 2. SETUP & DATABASE
# ==========================================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# MongoDB Connection
client = AsyncIOMotorClient(MONGO_URI)
db = client.digital_store
users_col = db.users
orders_col = db.orders
products_col = db.products

# States for handling screenshots
class CheckoutState(StatesGroup):
    waiting_for_screenshot = State()
    product_name = State()
    quantity = State()
    total_price = State()

# ==========================================
# 3. SHOP MENU & COMMANDS
# ==========================================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Save user to DB
    await users_col.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"username": message.from_user.username}},
        upsert=True
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 FLIPKART 1k Coupon - ₹100", callback_data="buy_flipkart")],
        [InlineKeyboardButton(text="👗 SHEIN 4k Coupon - ₹50 (Min 2)", callback_data="buy_shein4k")],
        [InlineKeyboardButton(text="👗 SHEIN 2k Coupon - ₹30 (Min 3)", callback_data="buy_shein2k")],
        [InlineKeyboardButton(text="🎮 Google Play 1k Code - ₹100", callback_data="buy_gplay")]
    ])
    
    await message.answer(f"Welcome to the Digital Store, @{message.from_user.username}!\nSelect a product to buy:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback_query: types.CallbackQuery, state: FSMContext):
    product_code = callback_query.data.split("_")[1]
    
    products = {
        "flipkart": {"name": "FLIPKART 1k Coupon", "price": 100, "min_buy": 1},
        "shein4k": {"name": "SHEIN 4k Coupon", "price": 50, "min_buy": 2},
        "shein2k": {"name": "SHEIN 2k Coupon", "price": 30, "min_buy": 3},
        "gplay": {"name": "Google Play Redeem 1k", "price": 100, "min_buy": 1},
    }
    
    if product_code not in products:
        return await callback_query.answer("Invalid product.")

    prod = products[product_code]
    total_price = prod["price"] * prod["min_buy"]
    
    # Save order details in memory state
    await state.update_data(
        product_name=prod["name"], 
        quantity=prod["min_buy"], 
        total_price=total_price
    )
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
# 4. HANDLE PAYMENT SCREENSHOTS
# ==========================================
@dp.message(CheckoutState.waiting_for_screenshot, F.photo)
async def handle_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.photo[-1].file_id
    
    # Save order to DB
    order_doc = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "product_name": data["product_name"],
        "quantity": data["quantity"],
        "total_price": data["total_price"],
        "status": "PENDING",
        "screenshot_id": file_id
    }
    result = await orders_col.insert_one(order_doc)
    order_id = str(result.inserted_id)
    
    # Forward to Admin
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{order_id}")],
        [InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{order_id}")]
    ])
    
    caption = (f"🚨 **NEW ORDER ALERT** 🚨\n\n"
               f"👤 User: @{message.from_user.username} ({message.from_user.id})\n"
               f"🛍 Product: {data['product_name']}\n"
               f"📦 Qty: {data['quantity']}\n"
               f"💰 Amount: ₹{data['total_price']}")
               
    await bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=caption, reply_markup=admin_kb, parse_mode="Markdown")
    
    await message.answer("✅ Payment screenshot received! Please wait while an admin verifies your payment.")
    await state.clear()

# ==========================================
# 5. ADMIN APPROVAL LOGIC
# ==========================================
@dp.callback_query(F.data.startswith("approve_"))
async def admin_approve(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        return await callback_query.answer("Not authorized.")
        
    order_id = callback_query.data.split("_")[1]
    from bson.objectid import ObjectId
    
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order or order["status"] != "PENDING":
        return await callback_query.answer("Order already processed.")

    # Fetch product stock
    product_db = await products_col.find_one({"name": order["product_name"]})
    
    if not product_db or len(product_db.get("stock", [])) < order["quantity"]:
        return await callback_query.message.answer(f"⚠️ Insufficient stock for {order['product_name']}. Please add stock first.")

    # Extract codes & update DB
    stock = product_db["stock"]
    codes_to_send = stock[:order["quantity"]]
    remaining_stock = stock[order["quantity"]:]
    
    await products_col.update_one({"name": order["product_name"]}, {"$set": {"stock": remaining_stock}})
    await orders_col.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "APPROVED"}})

    # Auto-deliver to user
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
    from bson.objectid import ObjectId
    
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    await orders_col.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "REJECTED"}})
    
    await bot.send_message(order["user_id"], f"❌ Your payment for {order['product_name']} was rejected.")
    await callback_query.message.edit_caption(caption=f"❌ **REJECTED**\nOrder: {order_id}")

# ==========================================
# 6. ADMIN COMMANDS
# ==========================================
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
    except Exception as e:
        await message.answer("❌ Failed to send. Maybe the user hasn't started the bot.")

# ==========================================
# 7. RUN BOT
# ==========================================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
