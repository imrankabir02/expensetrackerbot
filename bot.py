from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from models import Expense, Session, Reminder
from datetime import date, timedelta
from auth import is_authenticated, authenticate_user, logout_user, register_user
from auth_decorator import requires_auth
from io import StringIO, BytesIO
import matplotlib.pyplot as plt
import csv
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = "8298302907:AAEh16HAggOwbVlVN59KuJ5C3tCBQoMSDyU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *Expense Tracker Bot*!\n\n"
        "💸 Track your spending.\n"
        "✅ Type: `Spent 120 on groceries`\n"
        "ℹ️ Type /help to see all commands.",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Expense Tracker Guide*\n\n"
        "💸 *Add Expenses:*\n"
        "`Spent 120 on groceries`\n"
        "`Spent 50 on transport`\n\n"
        "📊 *Get Reports:*\n"
        "`/report today|week|month`\n\n"
        "📂 *Export Data:*\n"
        "`/export today|week|month|all`\n\n"
        "🔔 *Daily Reminder:*\n"
        "`/reminder on|off`\n\n"
        "🔐 *Auth:*\n"
        "`/register <pin>`\n"
        "`/login <pin>`\n"
        "`/logout`",
        parse_mode="Markdown"
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    pin = context.args[0] if context.args else None
    if not pin:
        await update.message.reply_text("❗Usage: `/register 1234`", parse_mode="Markdown")
        return
    register_user(user_id, pin)
    await update.message.reply_text("✅ Registered! Now login: `/login 1234`", parse_mode="Markdown")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    pin = context.args[0] if context.args else None
    if not pin:
        await update.message.reply_text("❗Usage: `/login 1234`", parse_mode="Markdown")
        return
    if authenticate_user(user_id, pin):
        await update.message.reply_text("🔓 Login successful!")
    else:
        await update.message.reply_text("❌ Incorrect PIN.")

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    logout_user(user_id)
    await update.message.reply_text("🔒 Logged out.")

@requires_auth
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.effective_user.id)

    try:
        parts = text.lower().split()
        if "spent" in parts:
            idx = parts.index("spent")
            amount = float(parts[idx + 1])
            category = parts[idx + 3] if len(parts) > idx + 3 else "misc"

            session = Session()
            expense = Expense(
                user_id=user_id,
                amount=amount,
                category=category,
                description=text
            )
            session.add(expense)
            session.commit()
            await update.message.reply_text(f"✅ Saved: {amount} BDT on {category}")
        else:
            await update.message.reply_text("⚠️ Use: `Spent 100 on food`", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Invalid format. Try: `Spent 100 on food`", parse_mode="Markdown")

@requires_auth
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    session = Session()
    today = date.today()
    cmd = (context.args[0] if context.args else "week").lower()

    if cmd == "today":
        start_date, label = today, "Today's"
    elif cmd == "month":
        start_date, label = today.replace(day=1), "Monthly"
    else:
        start_date, label = today - timedelta(days=7), "Weekly"

    expenses = session.query(Expense).filter(Expense.user_id == user_id, Expense.date >= start_date).all()
    if not expenses:
        await update.message.reply_text(f"😶 No {label.lower()} expenses found.")
        return

    summary = {}
    total = 0
    for e in expenses:
        summary[e.category] = summary.get(e.category, 0) + e.amount
        total += e.amount

    message = f"📊 *{label} Report:*\n"
    for cat, amt in summary.items():
        message += f"- {cat.capitalize()}: {amt:.2f} BDT\n"
    message += f"\n*Total*: {total:.2f} BDT"
    await update.message.reply_text(message, parse_mode="Markdown")

@requires_auth
async def export_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    session = Session()
    today = date.today()
    cmd = (context.args[0] if context.args else "all").lower()

    if cmd == "today":
        start_date = today
    elif cmd == "week":
        start_date = today - timedelta(days=7)
    elif cmd == "month":
        start_date = today.replace(day=1)
    else:
        start_date = None

    if start_date:
        expenses = session.query(Expense).filter(Expense.user_id == user_id, Expense.date >= start_date).all()
    else:
        expenses = session.query(Expense).filter(Expense.user_id == user_id).all()

    if not expenses:
        await update.message.reply_text("📂 No expenses to export.")
        return

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Amount", "Category", "Description"])
    for e in expenses:
        writer.writerow([e.date, e.amount, e.category, e.description])
    output.seek(0)

    await update.message.reply_document(
        document=output.getvalue().encode(),
        filename=f"expenses_{cmd}.csv",
        caption=f"🧾 Your {cmd} expense report"
    )

@requires_auth
async def chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    session = Session()
    today = date.today()
    cmd = (context.args[0] if context.args else "week").lower()

    if cmd == "today":
        start_date, label = today, "Today's"
    elif cmd == "month":
        start_date, label = today.replace(day=1), "Monthly"
    else:
        start_date, label = today - timedelta(days=7), "Weekly"

    expenses = session.query(Expense).filter(Expense.user_id == user_id, Expense.date >= start_date).all()
    if not expenses:
        await update.message.reply_text(f"😶 No {label.lower()} expenses found.")
        return

    summary = {}
    for e in expenses:
        summary[e.category] = summary.get(e.category, 0) + e.amount

    fig, ax = plt.subplots()
    ax.pie(summary.values(), labels=summary.keys(), autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    plt.title(f"{label} Expense Chart")

    buffer = BytesIO()
    plt.savefig(buffer, format="PNG")
    buffer.seek(0)
    plt.close()

    await update.message.reply_photo(photo=InputFile(buffer, filename="chart.png"))

@requires_auth
async def toggle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    session = Session()
    cmd = (context.args[0] if context.args else "").lower()

    reminder = session.query(Reminder).filter_by(user_id=user_id).first() or Reminder(user_id=user_id)
    if cmd == "on":
        reminder.is_enabled = True
        msg = "✅ Daily reminder enabled."
    elif cmd == "off":
        reminder.is_enabled = False
        msg = "🔕 Daily reminder disabled."
    else:
        msg = "Usage: `/reminder on` or `/reminder off`"

    session.merge(reminder)
    session.commit()
    await update.message.reply_text(msg, parse_mode="Markdown")

async def send_daily_reminders(app):
    session = Session()
    users = session.query(Reminder).filter_by(is_enabled=True).all()
    for r in users:
        try:
            await app.bot.send_message(chat_id=r.user_id, text="📝 Don’t forget to log your expenses today!")
        except Exception as e:
            print(f"Failed to message {r.user_id}: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("logout", logout))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("export", export_expenses))
    app.add_handler(CommandHandler("chart", chart))
    app.add_handler(CommandHandler("reminder", toggle_reminder))

    print("🚀 Bot is running...")
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: app.create_task(send_daily_reminders(app)), 'cron', hour=21, minute=0)
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    main()
