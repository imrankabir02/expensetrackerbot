from telegram import Update, InputFile, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from models import Expense, Session, Reminder, User, Category
from datetime import date, timedelta
from auth import is_authenticated, authenticate_user, logout_user, register_user
from auth_decorator import requires_auth
from io import StringIO, BytesIO
import matplotlib.pyplot as plt
import csv
from apscheduler.schedulers.background import BackgroundScheduler
from config import TOKEN

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text(
#         "👋 Welcome to *Expense Tracker Bot*!\n\n"
#         "💸 Track your spending.\n"
#         "✅ Type: `Spent 120 on groceries`\n"
#         "ℹ️ Type /help to see all commands.",
#         parse_mode="Markdown"
#     )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *Expense Tracker Bot*!\n\n"
        "💸 Track your expenses easily.\n"
        "🔐 Please register or login to start.\n\n"
        "Use `/help` to see all commands.",
        parse_mode="Markdown",
        reply_markup=main_menu()  # 🆕 Show buttons
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Expense Tracker Guide*\n\n"
        "🔐 *Auth:*\n"
        "`/register <pin>`\n"
        "`/login <pin>`\n"
        "`/logout`\n\n"
        "💸 *Add Expenses:*\n"
        "`Spent 120 on groceries`\n"
        "`Spent 50 on transport`\n\n"
        "📊 *Get Reports:*\n"
        "`/report today|week|month`\n\n"
        "📂 *Export Data:*\n"
        "`/export today|week|month|all`\n\n"
        "🔔 *Daily Reminder:*\n"
        "`/reminder on|off`\n\n"
        "🗑️ *Delete Expense:*\n"
        "`/delete` - Shows your last 5 expenses to delete.\n\n"
        "🗂️ *Manage Categories:*\n"
        "`/addcategory <name>`\n"
        "`/removecategory <name>`\n"
        "`/categories`",
        parse_mode="Markdown"
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    pin = context.args[0] if context.args else None
    if not pin:
        await update.message.reply_text("❗Usage: `/register 1234`", parse_mode="Markdown")
        return
    register_user(user_id, pin)
    
    keyboard = [[InlineKeyboardButton("Login", switch_inline_query_current_chat="/login ")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "✅ Registered! Now click the button to login.",
        reply_markup=reply_markup
    )

# async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = str(update.effective_user.id)
#     pin = context.args[0] if context.args else None
#     if not pin:
#         await update.message.reply_text("❗Usage: `/login 1234`", parse_mode="Markdown")
#         return
#     if authenticate_user(user_id, pin):
#         await update.message.reply_text("🔓 Login successful!")
#     else:
#         await update.message.reply_text("❌ Incorrect PIN.")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    pin = context.args[0] if context.args else None
    if not pin:
        await update.message.reply_text("❗Usage: `/login 1234`", parse_mode="Markdown")
        return
    if authenticate_user(user_id, pin):
        await update.message.reply_text("🔓 Login successful!", reply_markup=main_menu())  # 🆕 Show buttons
    else:
        await update.message.reply_text("❌ Incorrect PIN.")

# async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = str(update.effective_user.id)
#     logout_user(user_id)
#     await update.message.reply_text("🔒 Logged out.")

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    logout_user(user_id)
    await update.message.reply_text(
        "🔒 Logged out.",
        reply_markup=ReplyKeyboardRemove()  # 🆕 Remove buttons
    )

@requires_auth
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = str(update.effective_user.id)
    session = Session()

    try:
        # --- Button Handlers ---
        if text == "📊 Report":
            await update.message.reply_text("📊 Choose report range:", reply_markup=report_menu())
            return
        elif text == "📈 Chart":
            await update.message.reply_text("📈 Choose chart range:", reply_markup=chart_menu())
            return
        elif text == "📂 Export":
            await update.message.reply_text("📂 Choose export range:", reply_markup=export_menu())
            return
        elif text == "🔔 Reminder On":
            context.args = ["on"]
            await toggle_reminder(update, context)
            return
        elif text == "🔕 Reminder Off":
            context.args = ["off"]
            await toggle_reminder(update, context)
            return
        elif text == "🔐 Logout":
            await logout(update, context)
            return
        elif text == "💸 Add Expense":
            await add_expense_prompt(update, context)
            return
        elif text == "🗑️ Delete Expense":
            await delete_expense_prompt(update, context)
            return
        elif text == "⬅️ Back":
            await update.message.reply_text("🏠 Main menu:", reply_markup=main_menu())
            return
        elif text.startswith("Report "):
            period = text.split(" ")[1].lower()
            context.args = [period]
            await report(update, context)
            return
        elif text.startswith("Chart "):
            period = text.split(" ")[1].lower()
            context.args = [period]
            await chart(update, context)
            return
        elif text.startswith("Export "):
            period = text.split(" ")[1].lower()
            context.args = [period]
            await export_expenses(update, context)
            return

        # --- Expense Parsing ---
        if context.user_data.get('selected_category'):
            try:
                amount = float(text)
                category = context.user_data.pop('selected_category')
                
                expense = Expense(
                    user_id=user_id,
                    amount=amount,
                    category=category,
                    description=f"{category} {amount}"
                )
                session.add(expense)
                session.commit()
                await update.message.reply_text(f"✅ Saved: {amount:.2f} BDT on {category}")
            except ValueError:
                await update.message.reply_text("Please enter a valid amount.")
            finally:
                if 'selected_category' in context.user_data:
                    del context.user_data['selected_category']
            return

        text_lower = text.lower()
        parts = text_lower.split()
        amount = None
        category = None

        try:
            if "spent" in parts:
                idx = parts.index("spent")
                amount = float(parts[idx + 1])
                if "on" in parts:
                    on_idx = parts.index("on")
                    category = " ".join(parts[on_idx + 1:]) if len(parts) > on_idx + 1 else "misc"
                else:
                    category = "misc"
            elif len(parts) >= 2:
                try:
                    amount = float(parts[-1])
                    category = " ".join(parts[:-1])
                except ValueError:
                    amount = float(parts[0])
                    category = " ".join(parts[1:])
            
            if not category:
                category = "misc"

        except (ValueError, IndexError):
            await update.message.reply_text(
                "⚠️ Invalid format. Please use:\n`Spent 100 on food` or `food 100`",
                parse_mode="Markdown"
            )
            return

        if amount is not None and category is not None and category.strip() != "":
            expense = Expense(
                user_id=user_id,
                amount=amount,
                category=category.strip(),
                description=text
            )
            session.add(expense)
            session.commit()
            await update.message.reply_text(f"✅ Saved: {amount:.2f} BDT on {category.strip()}")
        else:
            await update.message.reply_text(
                "⚠️ Could not understand. Please use:\n`Spent 100 on food` or `food 100`",
                parse_mode="Markdown"
            )

    except Exception as e:
        print(f"[Error] handle_message: {e}")
        await update.message.reply_text("❌ An unexpected error occurred. Please try again.")
    finally:
        session.close()

@requires_auth
async def add_expense_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    session = Session()
    try:
        categories = session.query(Category).filter_by(user_id=user_id).all()
        if not categories:
            await update.message.reply_text("You have no categories. Add one with /addcategory or type an expense directly.")
            return

        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(cat.name, callback_data=f"category_{cat.name}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a category:", reply_markup=reply_markup)
    finally:
        session.close()

@requires_auth
async def delete_expense_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    session = Session()
    try:
        expenses = session.query(Expense).filter_by(user_id=user_id).order_by(Expense.date.desc()).limit(5).all()
        if not expenses:
            await update.message.reply_text("No recent expenses to delete.")
            return

        keyboard = []
        for exp in expenses:
            button_text = f"❌ {exp.date}: {exp.amount:.2f} - {exp.category}"
            callback_data = f"delete_{exp.id}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select an expense to delete:", reply_markup=reply_markup)
    finally:
        session.close()

@requires_auth
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("delete_"):
        expense_id = int(query.data.split("_")[1])
        session = Session()
        try:
            expense = session.query(Expense).filter_by(id=expense_id).first()
            if expense:
                session.delete(expense)
                session.commit()
                await query.edit_message_text(text=f"✅ Expense {expense_id} deleted.")
            else:
                await query.edit_message_text(text="❌ Expense not found.")
        except Exception as e:
            print(f"[Error] handle_callback_query: {e}")
            await query.edit_message_text(text="❌ Error deleting expense.")
        finally:
            session.close()
    elif query.data.startswith("category_"):
        category_name = query.data.split("_", 1)[1]
        context.user_data['selected_category'] = category_name
        await query.edit_message_text(text=f"How much did you spend on '{category_name}'?")

@requires_auth
async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    category_name = " ".join(context.args).strip()
    if not category_name:
        await update.message.reply_text("Usage: /addcategory <name>")
        return

    session = Session()
    try:
        exists = session.query(Category).filter_by(user_id=user_id, name=category_name).first()
        if exists:
            await update.message.reply_text(f"Category '{category_name}' already exists.")
            return
        
        new_category = Category(user_id=user_id, name=category_name)
        session.add(new_category)
        session.commit()
        await update.message.reply_text(f"✅ Category '{category_name}' added.")
    finally:
        session.close()

@requires_auth
async def remove_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    category_name = " ".join(context.args).strip()
    if not category_name:
        await update.message.reply_text("Usage: /removecategory <name>")
        return

    session = Session()
    try:
        category = session.query(Category).filter_by(user_id=user_id, name=category_name).first()
        if category:
            session.delete(category)
            session.commit()
            await update.message.reply_text(f"🗑️ Category '{category_name}' removed.")
        else:
            await update.message.reply_text(f"Category '{category_name}' not found.")
    finally:
        session.close()

@requires_auth
async def list_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    session = Session()
    try:
        categories = session.query(Category).filter_by(user_id=user_id).all()
        if not categories:
            await update.message.reply_text("You have no custom categories. Add one with /addcategory <name>.")
            return
        
        message = "Your categories:\n"
        for cat in categories:
            message += f"- {cat.name}\n"
        await update.message.reply_text(message)
    finally:
        session.close()
        
def get_date_range(period: str) -> tuple[date, str]:
    today = date.today()
    if period == "today":
        return today, "Today's"
    elif period == "month":
        return today.replace(day=1), "Monthly"
    elif period == "week":
        return today - timedelta(days=7), "Weekly"
    else: # Default to week
        return today - timedelta(days=7), "Weekly"

@requires_auth
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    session = Session()
    cmd = (context.args[0] if context.args else "week").lower()
    start_date, label = get_date_range(cmd)

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
    cmd = (context.args[0] if context.args else "all").lower()

    if cmd != "all":
        start_date, _ = get_date_range(cmd)
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
    cmd = (context.args[0] if context.args else "week").lower()
    start_date, label = get_date_range(cmd)

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


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            ["💸 Add Expense", "📊 Report"],
            ["📈 Chart", "📂 Export"],
            ["🗑️ Delete Expense", "🔔 Reminder On"],
            ["🔕 Reminder Off", "🔐 Logout"]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
def report_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            ["Report Today", "Report Week", "Report Month"],
            ["⬅️ Back"]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def chart_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            ["Chart Today", "Chart Week", "Chart Month"],
            ["⬅️ Back"]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def export_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            ["Export Today", "Export Week", "Export Month", "Export All"],
            ["⬅️ Back"]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    session = Session()
    session.query(User).update({User.session_active: False})
    session.commit()

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
    app.add_handler(CommandHandler("delete", delete_expense_prompt))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(CommandHandler("addcategory", add_category))
    app.add_handler(CommandHandler("removecategory", remove_category))
    app.add_handler(CommandHandler("categories", list_categories))

    print("🚀 Bot is running...")
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: app.create_task(send_daily_reminders(app)), 'cron', hour=21, minute=0)
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    main()
