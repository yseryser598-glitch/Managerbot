from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os, time

# Ia tokenul din variabila de mediu BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")

# ---- Config ----
STATE = {}  # chat_id -> user_id -> {'timestamps':[], 'warns':0}
BLOCKED_KEYWORDS = {'spam', 'free nitro', 'xxx', 'porn'}
FLOOD_MAX = 6
FLOOD_WINDOW = 10
TEMP_MUTE_MINUTES = 10
WELCOME_TEXT = "👋 Bun venit, {first}! Respectă regulile grupului. Tastează /rules pentru detalii."
DEFAULT_RULES = "1) Fără spam\n2) Respect\n3) Fără linkuri periculoase"
RULES = {}

# ---- Comenzi ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salut! Sunt botul tău de moderare 24/7 🚀")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "/rules – vezi regulile\n"
        "/setrules <text> – setează reguli (admin)\n"
        "/mute <reply> <min> – mute (admin)\n"
        "/unmute <reply> – scoate mute (admin)\n"
        "/warn <reply> [motiv] – avertisment (admin)"
    )
    await update.message.reply_text(text)

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(RULES.get(chat_id, DEFAULT_RULES))

async def setrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = [a.user.id for a in await context.bot.get_chat_administrators(update.effective_chat.id)]
    if update.effective_user.id not in admins:
        return await update.message.reply_text("Doar adminii pot seta reguli.")
    text = ' '.join(context.args)
    if not text:
        return await update.message.reply_text("Trebuie să scrii textul regulilor.")
    RULES[update.effective_chat.id] = text
    await update.message.reply_text("✅ Reguli setate.")

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        await update.message.reply_text(WELCOME_TEXT.format(first=user.first_name))

# ---- Moderare automată ----
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text_lower = msg.text.lower() if msg.text else ""

    # blocare cuvinte / linkuri
    if any(word in text_lower for word in BLOCKED_KEYWORDS) or ("http" in text_lower or "t.me/" in text_lower):
        try:
            await msg.delete()
        except:
            pass
        return

    # flood control
    user_state = STATE.setdefault(msg.chat_id, {}).setdefault(msg.from_user.id, {"timestamps": [], "warns": 0})
    now = time.time()
    user_state["timestamps"] = [t for t in user_state["timestamps"] if now - t <= FLOOD_WINDOW]
    user_state["timestamps"].append(now)

    if len(user_state["timestamps"]) > FLOOD_MAX:
        await msg.reply_text(f"⚠️ {msg.from_user.first_name}, ai trimis prea multe mesaje! Mut {TEMP_MUTE_MINUTES} min.")
        perms = ChatPermissions(can_send_messages=False)
        try:
            await context.bot.restrict_chat_member(
                msg.chat_id, msg.from_user.id, permissions=perms, until_date=now + TEMP_MUTE_MINUTES * 60
            )
        except:
            pass

# ---- Mute/Unmute ----
async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = [a.user.id for a in await context.bot.get_chat_administrators(update.effective_chat.id)]
    if update.effective_user.id not in admins:
        return await update.message.reply_text("Doar adminii pot folosi această comandă.")
    if not update.message.reply_to_message:
        return await update.message.reply_text("Trebuie să dai reply la cineva.")
    try:
        minutes = int(context.args[0])
    except:
        minutes = TEMP_MUTE_MINUTES
    perms = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(
        update.effective_chat.id, update.message.reply_to_message.from_user.id,
        permissions=perms, until_date=time.time() + minutes * 60
    )
    await update.message.reply_text(f"✅ {update.message.reply_to_message.from_user.first_name} a fost mutat {minutes} minute.")

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = [a.user.id for a in await context.bot.get_chat_administrators(update.effective_chat.id)]
    if update.effective_user.id not in admins:
        return await update.message.reply_text("Doar adminii pot folosi această comandă.")
    if not update.message.reply_to_message:
        return await update.message.reply_text("Trebuie să dai reply la cineva.")
    perms = ChatPermissions(can_send_messages=True)
    await context.bot.restrict_chat_member(update.effective_chat.id, update.message.reply_to_message.from_user.id, permissions=perms)
    await update.message.reply_text(f"✅ {update.message.reply_to_message.from_user.first_name} a fost demutat.")

# ---- Main ----
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("rules", rules_cmd))
    app.add_handler(CommandHandler("setrules", setrules_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))

    print("✅ Bot pornit...")
    app.run_polling()
