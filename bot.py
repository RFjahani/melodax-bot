import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# بارگذاری توکن از متغیر محیطی (برای Railway)
BOT_TOKEN = os.environ["BOT_TOKEN"]

# فقط ادمین می‌تونه سفارش اضافه کنه
ADMIN_USER_ID = 62435607

ORDERS_FILE = "orders.json"
awaiting_bulk = {}  # وضعیت هر ادمین که منتظر ثبت دسته‌ای باشه

# خواندن کد رهگیری
def get_tracking_code(order_id: str) -> str:
    try:
        with open(ORDERS_FILE, "r") as f:
            orders = json.load(f)
        result = orders.get(order_id)
        if result is None:
            return "⏳ سفارش شما هنوز ارسال نشده."
        return f"📦 کد رهگیری شما:\n`{result}`"
    except:
        return "📁 هنوز هیچ سفارشی ثبت نشده."

# افزودن سفارش
def add_order(order_id: str, code: str) -> bool:
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, "r") as f:
                orders = json.load(f)
        else:
            orders = {}
        orders[order_id] = code
        with open(ORDERS_FILE, "w") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

# منوی شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📦 استعلام سفارش", callback_data="check")],
    ]
    if update.effective_user.id == ADMIN_USER_ID:
        keyboard.append([InlineKeyboardButton("➕ افزودن سفارش", callback_data="add")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("لطفاً یک گزینه را انتخاب کنید:", reply_markup=reply_markup)

# مدیریت دکمه‌ها
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "check":
        await query.message.reply_text("✅ لطفاً شماره سفارش خود را وارد کنید:")
    elif query.data == "add":
        if user_id == ADMIN_USER_ID:
            awaiting_bulk[user_id] = True
            await query.message.reply_text("✍️ لطفاً سفارش‌ها را به صورت جفت‌جفت وارد کنید:\nمثال:\n1234\nکد1\n1235\nکد2")
        else:
            await query.message.reply_text("⛔ فقط ادمین می‌تواند سفارش ثبت کند.")

# دریافت پیام‌های متنی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.message.from_user.id

    # اگر ادمین تایپ کرده: add
    if text.lower() == "add" and user_id == ADMIN_USER_ID:
        awaiting_bulk[user_id] = True
        await update.message.reply_text("✍️ لطفاً سفارش‌ها را به صورت جفت‌جفت وارد کنید:\nمثال:\n1234\nکد1\n1235\nکد2")
        return

    # اگر در حالت ثبت چندتایی باشه
    if awaiting_bulk.get(user_id):
        lines = text.splitlines()
        if len(lines) % 2 != 0:
            await update.message.reply_text("❗ هر سفارش باید با یک کد رهگیری همراه باشد (تعداد خطوط باید زوج باشد).")
            return

        count = 0
        for i in range(0, len(lines), 2):
            order_id = lines[i].strip()
            code = lines[i + 1].strip()
            if order_id and code:
                if add_order(order_id, code):
                    count += 1
        awaiting_bulk.pop(user_id)
        await update.message.reply_text(f"✅ {count} سفارش ثبت شد.")
        return

    # اگر عدد بود: بررسی سفارش
    if text.isdigit():
        tracking = get_tracking_code(text)
        await update.message.reply_text(tracking, parse_mode="Markdown")

        # اگر ادمین نبود → اطلاع بده
        if user_id != ADMIN_USER_ID and tracking.startswith("📦"):
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"📬 استعلام جدید:\nشماره سفارش: {text}\n{tracking}",
                parse_mode="Markdown"
            )
        return

    # پیام نامعتبر
    await update.message.reply_text(
        "❗ درخواست شما معتبر نیست.\n"
        "اگر کد رهگیری دارید فقط شماره سفارش را به انگلیسی وارد کنید (مثلاً: 12345).\n"
        "در غیر این صورت با پشتیبانی ملوداکس تماس بگیرید: 03132752221"
    )

# اجرای ربات
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 ربات ملوداکس با منو و قابلیت کامل اجرا شد...")
    app.run_polling()
