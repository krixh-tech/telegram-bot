import telebot
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = 7510607171
UPI_ID = "harshalx11@fam"

users = set()
orders = []

products = {
    "p1": {"name": "Shein 4K Coupon", "price": 50},
    "p2": {"name": "Shein 2K Coupon", "price": 30},
    "p3": {"name": "Flipkart Gift Card 1K", "price": 100},
    "p4": {"name": "Google Play Code 1K", "price": 100}
}

# START
@bot.message_handler(commands=['start'])
def start(msg):
    users.add(msg.from_user.id)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🛒 Shop", callback_data="shop"))
    kb.add(InlineKeyboardButton("📦 My Orders", callback_data="orders"))

    bot.send_message(msg.chat.id, "Welcome To Premium Coupon Shop 🛍", reply_markup=kb)

# SHOP
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    if call.data == "shop":
        kb = InlineKeyboardMarkup()

        for pid in products:
            p = products[pid]
            kb.add(InlineKeyboardButton(f"{p['name']} ₹{p['price']}", callback_data=f"buy_{pid}"))

        bot.edit_message_text("Select Product:", call.message.chat.id, call.message.message_id, reply_markup=kb)

    if call.data.startswith("buy_"):
        pid = call.data.split("_")[1]
        product = products[pid]

        order = {
            "user": call.from_user.id,
            "product": product["name"],
            "price": product["price"],
            "status": "pending"
        }

        orders.append(order)

        text = f"""
💰 Payment Details

UPI: {UPI_ID}
Amount: ₹{product['price']}

Send Payment Screenshot Here
"""

        bot.send_message(call.message.chat.id, text)

# SCREENSHOT RECEIVE
@bot.message_handler(content_types=['photo'])
def screenshot(msg):

    caption = f"""
📸 Payment Screenshot

User: {msg.from_user.id}
"""

    bot.forward_message(ADMIN_ID, msg.chat.id, msg.message_id)
    bot.send_message(msg.chat.id, "✅ Screenshot Sent To Admin")

# ADMIN PANEL
@bot.message_handler(commands=['admin'])
def admin(msg):

    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, "Not Admin ❌")
        return

    text = f"""
🔥 ADMIN PANEL

👥 Users: {len(users)}
📦 Orders: {len(orders)}

Commands:
/orders
/broadcast TEXT
/sendcoupon USERID CODE
"""

    bot.send_message(msg.chat.id, text)

# VIEW ORDERS
@bot.message_handler(commands=['orders'])
def view_orders(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    text = "📦 Orders List\n\n"

    for o in orders:
        text += f"""
User: {o['user']}
Product: {o['product']}
Status: {o['status']}
---------
"""

    bot.send_message(msg.chat.id, text)

# BROADCAST
@bot.message_handler(commands=['broadcast'])
def broadcast(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    text = msg.text.replace("/broadcast ", "")

    for u in users:
        try:
            bot.send_message(u, text)
        except:
            pass

    bot.send_message(msg.chat.id, "✅ Broadcast Done")

# SEND COUPON
@bot.message_handler(commands=['sendcoupon'])
def send_coupon(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    try:
        parts = msg.text.split()
        user_id = int(parts[1])
        code = parts[2]

        bot.send_message(user_id, f"🎁 Your Coupon Code:\n{code}")
        bot.send_message(msg.chat.id, "✅ Coupon Sent")

    except:
        bot.send_message(msg.chat.id, "Usage:\n/sendcoupon USERID CODE")

print("BOT RUNNING")
bot.infinity_polling()
