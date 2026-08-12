import asyncio
import os
import re

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import Channel
from telethon.tl.functions.channels import EditTitleRequest
from telethon.tl.functions.messages import EditChatTitleRequest

import db

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

bot = TelegramClient("master_bot", API_ID, API_HASH)

LOGIN_PATTERN = re.compile(r"^\.login\s+(\$?[\d,]+(?:\.\d+)?\$?)$", re.IGNORECASE)

DEAL_MSG = "Deal Logged Successfully!!"

TOS = (
    "**TOS:** My only responsibility is to hold funds. "
    "I am not responsible for changes in crypto value or sending fees. "
    "The MM fee (2%, at least $5 min fee) is non-refundable. "
    "If not provided upfront, it will be taken before sending to the seller/refund. "
    "I am not responsible for accounts/products pulled or revoked during or after the deal. "
    "I have the right to compensate either party if timewasting is occurring."
)


def is_admin(user_id):
    return user_id in ADMIN_IDS


def has_access(user_id):
    return is_admin(user_id) or db.is_authorized(user_id)


@bot.on(events.NewMessage(pattern=r"^/help\b"))
async def cmd_help(event):
    if not is_admin(event.sender_id):
        return
    await event.respond(
        "Admin commands:\n"
        "/giveaccess <user_id> [label] - grant a user access\n"
        "/revoke <user_id> - remove a user's access\n"
        "/access - list authorized users\n\n"
        "Authorized user commands (in private chat):\n"
        "/settos <text> - set your custom TOS\n"
        "/setmsg <text> - set your custom deal message\n"
        "/view - see your current settings\n"
        "/reset - clear your custom settings (back to defaults)\n\n"
        "Authorized users can send .login <amount> in a group "
        "to rename it to 'mm chat <amount>' and log the deal."
    )


@bot.on(events.NewMessage(pattern=r"^/giveaccess\b"))
async def cmd_giveaccess(event):
    if not is_admin(event.sender_id):
        return

    parts = event.raw_text.strip().split()
    if len(parts) < 2 or not parts[1].lstrip("+").isdigit():
        await event.respond("Usage: /giveaccess <user_id> [label]")
        return

    user_id = int(parts[1].lstrip("+"))
    label = parts[2] if len(parts) > 2 else ""
    db.add_user(user_id, label)
    await event.respond(f"Access granted to {user_id}.")


@bot.on(events.NewMessage(pattern=r"^/revoke\b"))
async def cmd_revoke(event):
    if not is_admin(event.sender_id):
        return

    parts = event.raw_text.strip().split()
    if len(parts) < 2 or not parts[1].lstrip("+").isdigit():
        await event.respond("Usage: /revoke <user_id>")
        return

    user_id = int(parts[1].lstrip("+"))
    db.remove_user(user_id)
    await event.respond(f"Access revoked from {user_id}.")


@bot.on(events.NewMessage(pattern=r"^/access\b"))
async def cmd_access(event):
    if not is_admin(event.sender_id):
        return

    users = db.list_users()
    if not users:
        await event.respond("No users have access yet.")
        return

    lines = [f"{u['user_id']} | {u['label']}" for u in users]
    await event.respond("Authorized users:\n" + "\n".join(lines))


@bot.on(events.NewMessage(pattern=r"^/settos\b"))
async def cmd_settos(event):
    if not has_access(event.sender_id):
        return
    if not event.is_private:
        await event.respond("Use this in a private chat with the bot.")
        return

    parts = event.raw_text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await event.respond("Usage: /settos <your custom TOS text>")
        return

    text = parts[1].strip()
    db.ensure_user(event.sender_id)
    db.set_tos(event.sender_id, text)
    await event.respond("Your custom TOS is saved. It will be used when you trigger .login.")


@bot.on(events.NewMessage(pattern=r"^/setmsg\b"))
async def cmd_setmsg(event):
    if not has_access(event.sender_id):
        return
    if not event.is_private:
        await event.respond("Use this in a private chat with the bot.")
        return

    parts = event.raw_text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await event.respond("Usage: /setmsg <your custom deal message>")
        return

    text = parts[1].strip()
    db.ensure_user(event.sender_id)
    db.set_msg(event.sender_id, text)
    await event.respond("Your custom deal message is saved. It will be used when you trigger .login.")


@bot.on(events.NewMessage(pattern=r"^/view\b"))
async def cmd_view(event):
    if not has_access(event.sender_id):
        return
    if not event.is_private:
        await event.respond("Use this in a private chat with the bot.")
        return

    user = db.get_user(event.sender_id)
    msg = user["msg"] if user and user["msg"] else DEAL_MSG
    tos = user["tos"] if user and user["tos"] else TOS
    await event.respond(
        f"Your deal message:\n{msg}\n\nYour TOS:\n{tos}\n\n"
        "Defaults are used where you have not customized."
    )


@bot.on(events.NewMessage(pattern=r"^/reset\b"))
async def cmd_reset(event):
    if not has_access(event.sender_id):
        return
    if not event.is_private:
        await event.respond("Use this in a private chat with the bot.")
        return

    db.set_tos(event.sender_id, "")
    db.set_msg(event.sender_id, "")
    await event.respond("Your custom TOS and deal message are cleared. Defaults will be used.")


@bot.on(events.NewMessage)
async def on_login(event):
    if not event.is_group:
        return
    if not has_access(event.sender_id):
        return

    match = LOGIN_PATTERN.match(event.raw_text.strip())
    if not match:
        return

    title = f"mm chat {match.group(1)}"

    try:
        chat = await event.get_chat()
        if isinstance(chat, Channel):
            await bot(EditTitleRequest(chat_id=chat.id, title=title))
        else:
            await bot(EditChatTitleRequest(chat_id=chat.id, title=title))
    except Exception as e:
        await event.respond(f"Failed to rename group: {e}")
        return

    user = db.get_user(event.sender_id)
    msg = user["msg"] if user and user["msg"] else DEAL_MSG
    tos = user["tos"] if user and user["tos"] else TOS

    await event.respond(msg)
    await event.respond(tos)


async def main():
    db.init_db()
    await bot.start(bot_token=BOT_TOKEN)
    print("Ogu system bot is running...")
    try:
        await bot.run_until_disconnected()
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
