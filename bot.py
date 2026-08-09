
import os
import json
from collections import defaultdict
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

BOT_LINK = "https://t.me/+XJgDsUzOkaxiOGI0"
OTP_GROUP = "https://t.me/+Xo8NjhC8flFmM2M8"

ADMINS = {7255612018, 8694189919, 8111267812}

DATA_FILE = "stock.json"

SERVICE, COUNTRY, FILE = range(3)

pending_delete = {}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def admin_only(update: Update):
    user_id = update.effective_user.id
    return user_id in ADMINS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔵 Check Stock", callback_data="stock")],
        [InlineKeyboardButton("🔴 OTP", url=BOT_LINK)],
        [InlineKeyboardButton("🟢 OTP Group", url=OTP_GROUP)],
    ]
    text = (
        "👋 Welcome to *OTP Bot*\n\n"
        "Use the buttons below."
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data:
        await update.message.reply_text("📦 No stock available.")
        return

    lines = ["📦 *Available Stock*"]
    for service, countries in data.items():
        for country, numbers in countries.items():
            lines.append(f"🔵 {service} — 🇳🇬 {country}: *{len(numbers)}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def stock_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    if not data:
        await query.message.reply_text("📦 No stock available.")
        return

    lines = ["📦 *Available Stock*"]
    for service, countries in data.items():
        for country, numbers in countries.items():
            lines.append(f"🔵 {service} — 🇳🇬 {country}: *{len(numbers)}*")

    await query.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update):
        return ConversationHandler.END
    await update.message.reply_text("📝 Send the service name")
    return SERVICE

async def add_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["service"] = update.message.text.strip()
    await update.message.reply_text("🌍 Send the country")
    return COUNTRY

async def add_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["country"] = update.message.text.strip()
    await update.message.reply_text("📄 Now send the .txt file containing the numbers")
    return FILE

async def add_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".txt"):
        await update.message.reply_text("❌ Please send a .txt file")
        return FILE

    file = await document.get_file()
    path = "temp.txt"
    await file.download_to_drive(path)

    with open(path, "r", encoding="utf-8") as f:
        numbers = [line.strip() for line in f if line.strip()]

    service = context.user_data["service"]
    country = context.user_data["country"]

    data = load_data()
    data.setdefault(service, {})
    data[service].setdefault(country, [])
    data[service][country].extend(numbers)
    save_data(data)

    keyboard = [
        [
            InlineKeyboardButton("🔴 OTP", url=BOT_LINK),
            InlineKeyboardButton("🟢 OTP Group", url=OTP_GROUP),
        ]
    ]

    text = (
        f"✅ *Upload completed*\n\n"
        f"📦 Service: *{service}*\n"
        f"🌍 Country: *{country}*\n"
        f"🔢 Numbers: *{len(numbers)}*"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return ConversationHandler.END

async def delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update):
        return

    data = load_data()
    if not data:
        await update.message.reply_text("📦 No stock available.")
        return

    keyboard = []
    for service, countries in data.items():
        for country, numbers in countries.items():
            key = f"{service}|{country}"
            pending_delete[key] = len(numbers)
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ {service} • {country} ({len(numbers)})",
                    callback_data=f"del:{key}"
                )
            ])

    await update.message.reply_text(
        "⚠️ Select stock to delete",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key = query.data.replace("del:", "")
    service, country = key.split("|", 1)
    count = pending_delete.get(key, 0)

    keyboard = [
        [
            InlineKeyboardButton("🟢 Yes, Delete", callback_data=f"confirm:{key}"),
            InlineKeyboardButton("🔴 Cancel", callback_data="cancel")
        ]
    ]

    text = (
        f"⚠️ *Delete this stock?*\n\n"
        f"📦 Service: *{service}*\n"
        f"🌍 Country: *{country}*\n"
        f"🔢 Numbers: *{count}*"
    )

    await query.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key = query.data.replace("confirm:", "")
    service, country = key.split("|", 1)

    data = load_data()
    count = len(data.get(service, {}).get(country, []))

    if service in data and country in data[service]:
        del data[service][country]
        if not data[service]:
            del data[service]
        save_data(data)

    text = (
        f"🗑️ *Stock deleted successfully*\n\n"
        f"📦 Service: *{service}*\n"
        f"🌍 Country: *{country}*\n"
        f"🔢 Numbers: *{count}*\n\n"
        f"✅ *{service} - {country} - {count} numbers deleted successfully.*"
    )

    await query.message.reply_text(text, parse_mode="Markdown")

async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("❌ Cancelled")

async def get_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n/get Service Country\nExample:\n/get WhatsApp Nigeria"
        )
        return

    service = context.args[0]
    country = " ".join(context.args[1:])

    data = load_data()
    numbers = data.get(service, {}).get(country, [])

    if len(numbers) < 3:
        await update.message.reply_text("❌ Not enough stock.")
        return

    send_numbers = numbers[:3]
    data[service][country] = numbers[3:]
    save_data(data)

    keyboard = [
        [InlineKeyboardButton("🟢 OTP Group", url=OTP_GROUP)]
    ]

    text = (
        f"📦 *{service} • {country}*\n\n"
        + "\n".join(send_numbers)
        + f"\n\n📦 Stock left: *{len(data[service][country])}*"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).build()

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_service)],
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_country)],
            FILE: [MessageHandler(filters.Document.ALL, add_file)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stock", stock_command))
    app.add_handler(CommandHandler("delete", delete_start))
    app.add_handler(CommandHandler("get", get_numbers))
    app.add_handler(add_conv)

    app.add_handler(CallbackQueryHandler(stock_button, pattern="^stock$"))
    app.add_handler(CallbackQueryHandler(delete_select, pattern="^del:"))
    app.add_handler(CallbackQueryHandler(delete_confirm, pattern="^confirm:"))
    app.add_handler(CallbackQueryHandler(cancel_callback, pattern="^cancel$"))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
