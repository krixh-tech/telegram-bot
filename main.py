import telebot
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = 7510607171   # ⚠ Yaha apna Telegram ID daalna

users = set()
orders = []

products = {
    "p1": {"name": "Shein 4K Coupon", "price": "50"},
    "p2": {"name": "Shein 2K Coupon", "price": "30"},
    "p3": {"name": "Flipkart Gift Card 1K", "price": "100"},
    "p4": {"name": "Google Play Code 1K", "price": "100"}
}


# START
@bot.message_handler(commands=['start'])
def start(msg):
    users.add(msg.from_user.id)
    bot.send_message(msg.chat.id, "Bot Working ✅")


# ADMIN PANEL
@bot.message_handler(commands=['admin'])
def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, "Not Admin ❌")
        return

    text = "🔥 Admin Panel\n\n"
    text += "/orders → View Orders\n"
    text += "/broadcast → Broadcast Message"

    bot.send_message(msg.chat.id, text)


# ORDERS VIEW
@bot.message_handler(commands=['orders'])
def show_orders(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    if not orders:
        bot.send_message(msg.chat.id, "No Orders")
        return

    text = "📦 Orders\n\n"
    for o in orders:
        text += f"User: {o['user']}\nProduct: {o['product']}\nStatus: {o['status']}\n\n"

    bot.send_message(msg.chat.id, text)


# BROADCAST
@bot.message_handler(commands=['broadcast'])
def bc(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    bot.send_message(msg.chat.id, "Send message to broadcast")
    bot.register_next_step_handler(msg, bc_send)


def bc_send(msg):
    for u in users:
        try:
            bot.send_message(u, msg.text)
        except:
            pass


print("BOT RUNNING 🔥")
bot.infinity_polling()
