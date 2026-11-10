# Copyright (c) 2025 strad-dev131
# Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
# Part of the cloudymusic project. All rights reserved where applicable.

from pytdbot import Client, types

from cloudymusic import __version__
from cloudymusic.core import (
    config,
    Filter,
    SupportButton,
)
from cloudymusic.core.buttons import add_me_markup, HelpMenu, BackHelpMenu

startText = """
ʜᴇʏ {};

◎ ᴛʜɪꜱ ɪꜱ {}!
➻ ᴀ ꜰᴀꜱᴛ & ᴘᴏᴡᴇʀꜰᴜʟ ᴛᴇʟᴇɢʀᴀᴍ ᴍᴜꜱɪᴄ ᴘʟᴀʏᴇʀ ʙᴏᴛ ᴡɪᴛʜ ꜱᴏᴍᴇ ᴀᴡᴇꜱᴏᴍᴇ ꜰᴇᴀᴛᴜʀᴇꜱ.

ꜱᴜᴘᴘᴏʀᴛᴇᴅ ᴘʟᴀᴛꜰᴏʀᴍꜱ: ʏᴏᴜᴛᴜʙᴇ, ꜱᴘᴏᴛɪꜰʏ, ᴊɪᴏꜱᴀᴀᴠɴ, ᴀᴘᴘʟᴇ ᴍᴜꜱɪᴄ ᴀɴᴅ ꜱᴏᴜɴᴅᴄʟᴏᴜᴅ.

---
◎ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴍʏ ᴍᴏᴅᴜʟᴇꜱ ᴀɴᴅ ᴄᴏᴍᴍᴀɴᴅꜱ.
"""

def extract_user_id(msg_obj) -> int:
    """Helper to safely extract user ID as int from pytdbot message/callback."""
    raw = (
        getattr(msg_obj, "sender_id", None) 
        or getattr(msg_obj, "sender_user_id", None) 
        or getattr(msg_obj, "from_id", 0)
    )
    if isinstance(raw, dict):
        raw = raw.get("user_id") or raw.get("id", 0)
    
    # Check if sender is a user message object or has an id attribute
    if hasattr(raw, "id"):
        raw = raw.id
    elif hasattr(raw, "user_id"):
        raw = raw.user_id

    try:
        return int(raw) if raw else 0
    except (ValueError, TypeError):
        return 0


@Client.on_message(filters=Filter.command(["start", "help"]))
async def start_cmd(c: Client, message: types.Message):
    chat_id = message.chat_id
    bot_name = c.me.first_name
    
    sender_id = extract_user_id(message)
    user = await c.getUser(sender_id) if sender_id else None
    user_name = user.first_name if user else "User"
    mention = f"<a href='tg://user?id={sender_id}'>{user_name}</a>"

    # Safe username extraction for pytdbot
    bot_username = None
    try:
        if hasattr(c.me, "usernames") and c.me.usernames:
            bot_username = c.me.usernames.editable_username
        elif hasattr(c.me, "username"):
            bot_username = c.me.username
    except Exception:
        bot_username = None

    if chat_id < 0:  # Group
        welcome_text = (
            f"🎵 <b>ʜᴇʟʟᴏ {mention}!</b>\n\n"
            f"<b>{bot_name}</b> ɪꜱ ɴᴏᴡ ᴀᴄᴛɪᴠᴇ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ.\n"
            "ʜᴇʀᴇ’ꜱ ᴡʜᴀᴛ ɪ ᴄᴀɴ ᴅᴏ:\n"
            "• ʜɪɢʜ-ǫᴜᴀʟɪᴛʏ ᴍᴜꜱɪᴄ ꜱᴛʀᴇᴀᴍɪɴɢ\n"
            "• ꜱᴜᴘᴘᴏʀᴛꜱ ʏᴏᴜᴛᴜʙᴇ, ꜱᴘᴏᴛɪꜰʏ, ᴀɴᴅ ᴍᴏʀᴇ\n"
            "• ᴘᴏᴡᴇʀꜰᴜʟ ᴄᴏɴᴛʀᴏʟꜱ ꜰᴏʀ ꜱᴇᴀᴍʟᴇꜱꜱ ᴘʟᴀʏʙᴀᴄᴋ\n\n"
            f"💬 <a href='{config.SUPPORT_GROUP}'>ɴᴇᴇᴅ ʜᴇʟᴘ? ᴊᴏɪɴ ᴏᴜʀ ꜱᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ</a>"
        )
        reply = await message.reply_text(
            text=welcome_text,
            disable_web_page_preview=True,
            reply_markup=SupportButton,
        )

    else:  # Private chat
        reply = await message.reply_photo(
            photo=config.START_IMG,
            caption=startText.format(user_name, bot_name),
            reply_markup=add_me_markup(bot_username),
        )

    if isinstance(reply, types.Error):
        c.logger.warning(reply.message)


@Client.on_updateNewCallbackQuery(filters=Filter.regex(r"help_\w+"))
async def callback_query_help(c: Client, message: types.UpdateNewCallbackQuery) -> None:
    data = message.payload.data.decode()

    bot_username = None
    try:
        if hasattr(c.me, "usernames") and c.me.usernames:
            bot_username = c.me.usernames.editable_username
        elif hasattr(c.me, "username"):
            bot_username = c.me.username
    except Exception:
        bot_username = None

    sender_id = extract_user_id(message)

    if data == "help_all":
        user = await c.getUser(sender_id) if sender_id else None
        user_name = user.first_name if user else "User"
        await message.answer("📚 ᴏᴘᴇɴɪɴɢ ʜᴇʟᴘ ᴍᴇɴᴜ...")
        welcome_text = (
            f"👋 <b>ʜᴇʟʟᴏ {user_name}!</b>\n\n"
            f"ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ <b>{c.me.first_name}</b> — ʏᴏᴜʀ ᴜʟᴛɪᴍᴀᴛᴇ ᴍᴜꜱɪᴄ ʙᴏᴛ.\n"
            f"<code>ᴠᴇʀꜱɪᴏɴ: ᴠ{__version__}</code>\n\n"
            "💡 <b>ᴡʜᴀᴛ ᴍᴀᴋᴇꜱ ᴍᴇ ꜱᴘᴇᴄɪᴀʟ?</b>\n"
            "• ʏᴏᴜᴛᴜʙᴇ, ꜱᴘᴏᴛɪꜰʏ, ᴀᴘᴘʟᴇ ᴍᴜꜱɪᴄ, ꜱᴏᴜɴᴅᴄʟᴏᴜᴅ ꜱᴜᴘᴘᴏʀᴛ\n"
            "• ᴀᴅᴠᴀɴᴄᴇᴅ ǫᴜᴇᴜᴇ ᴀɴᴅ ᴘʟᴀʏʙᴀᴄᴋ ᴄᴏɴᴛʀᴏʟꜱ\n"
            "• ᴘʀɪᴠᴀᴛᴇ ᴀɴᴅ ɢʀᴏᴜᴘ ᴜꜱᴀɢᴇ\n\n"
            "🔍 <i>ꜱᴇʟᴇᴄᴛ ᴀ ʜᴇʟᴘ ᴄᴀᴛᴇɢᴏʀʏ ʙᴇʟᴏᴡ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.</i>"
        )
        edit = await message.edit_message_caption(welcome_text, reply_markup=HelpMenu)
        if isinstance(edit, types.Error):
            c.logger.error(f"ꜰᴀɪʟᴇᴅ ᴛᴏ ᴇᴅɪᴛ ᴍᴇꜱꜱᴀɢᴇ: {edit}")
        return

    if data == "help_back":
        await message.answer("ʜᴏᴍᴇ ..")
        user = await c.getUser(sender_id) if sender_id else None
        user_name = user.first_name if user else "User"
        await message.edit_message_caption(
            caption=startText.format(user_name, c.me.first_name),
            reply_markup=add_me_markup(bot_username),
        )
        return

    help_categories = {
        "help_user": {
            "title": "🎧 ᴜꜱᴇʀ ᴄᴏᴍᴍᴀɴᴅꜱ",
            "content": (
                "<b>▶️ ᴘʟᴀʏʙᴀᴄᴋ:</b>\n"
                "• <code>/play [ꜱᴏɴɢ]</code> — ᴘʟᴀʏ ᴀᴜᴅɪᴏ ɪɴ ᴠᴄ\n"
                "• <code>/vplay [ᴠɪᴅᴇᴏ]</code> — ᴘʟᴀʏ ᴠɪᴅᴇᴏ ɪɴ ᴠᴄ\n"
                "<b>🛠 ᴜᴛɪʟɪᴛɪᴇꜱ:</b>\n"
                "• <code>/start</code> — ɪɴᴛʀᴏ ᴍᴇꜱꜱᴀɢᴇ\n"
                "• <code>/privacy</code> — ᴘʀɪᴠᴀᴄʏ ᴘᴏʟɪᴄʏ\n"
                "• <code>/queue</code> — ᴠɪᴇᴡ ᴛʀᴀᴄᴋ ǫᴜᴇᴜᴇ\n"
            ),
            "markup": BackHelpMenu,
        },
        "help_admin": {
            "title": "⚙️ ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅꜱ",
            "content": (
                "<b>🎛 ᴘʟᴀʏʙᴀᴄᴋ ᴄᴏɴᴛʀᴏʟꜱ:</b>\n"
                "• <code>/skip</code> — ꜱᴋɪᴘ ᴄᴜʀʀᴇɴᴛ ᴛʀᴀᴄᴋ\n"
                "• <code>/pause</code> — ᴘᴀᴜꜱᴇ ᴘʟᴀʏʙᴀᴄᴋ\n"
                "• <code>/resume</code> — ʀᴇꜱᴜᴍᴇ ᴘʟᴀʏʙᴀᴄᴋ\n"
                "• <code>/seek [ꜱᴇᴄ]</code> — ᴊᴜᴍᴘ ᴛᴏ ᴀ ᴘᴏꜱɪᴛɪᴏɴ\n"
                "• <code>/volume [1-200]</code> — ꜱᴇᴛ ᴘʟᴀʏʙᴀᴄᴋ ᴠᴏʟᴜᴍᴇ\n\n"
                "<b>📋 ǫᴜᴇᴜᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ:</b>\n"
                "• <code>/remove [x]</code> — ʀᴇᴍᴏᴠᴇ ᴛʀᴀᴄᴋ ɴᴜᴍʙᴇʀ x\n"
                "• <code>/clear</code> — ᴄʟᴇᴀʀ ᴛʜᴇ ᴇɴᴛɪʀᴇ ǫᴜᴇᴜᴇ\n"
                "• <code>/loop [0-10]</code> — ʀᴇᴘᴇᴀᴛ ǫᴜᴇᴜᴇ x ᴛɪᴍᴇꜱ\n\n"
                "<b>👑 ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ:</b>\n"
                "• <code>/auth [ʀᴇᴘʟʏ]</code> — ɢʀᴀɴᴛ ᴀᴘᴘʀᴏᴠᴀʟ ᴛᴏ ᴜꜱᴇ ᴄᴏᴍᴍᴀɴᴅꜱ \n"
                "• <code>/unauth [ʀᴇᴘʟʏ]</code> — ʀᴇᴠᴏᴋᴇ ᴀᴜᴛʜᴏʀɪᴢᴀᴛɪᴏɴ\n"
                "• <code>/authlist</code> — ᴠɪᴇᴡ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜꜱᴇʀꜱ\n\n"
            ),
            "markup": BackHelpMenu,
        },
        "help_owner": {
            "title": "🔐 ᴏᴡɴᴇʀ ᴄᴏᴍᴍᴀɴᴅꜱ",
            "content": (
                "<b>⚙️ ꜱᴇᴛᴛɪɴɢꜱ:</b>\n"
                "• <code>/buttons</code> — ᴛᴏɢɢʟᴇ ᴄᴏɴᴛʀᴏʟ ʙᴜᴛᴛᴏɴꜱ\n"
                "• <code>/thumb</code> — ᴛᴏɢɢʟᴇ ᴛʜᴜᴍʙɴᴀɪʟ ᴍᴏᴅᴇ"
            ),
            "markup": BackHelpMenu,
        },
        "help_devs": {
            "title": "🛠 ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏᴏʟꜱ",
            "content": (
                "<b>📊 ꜱʏꜱᴛᴇᴍ ᴛᴏᴏʟꜱ:</b>\n"
                "• <code>/stats</code> — ꜱʜᴏᴡ ᴜꜱᴀɢᴇ ꜱᴛᴀᴛꜱ\n"
                "• <code>/logger</code> — ᴛᴏɢɢʟᴇ ʟᴏɢ ᴍᴏᴅᴇ\n"
                "• <code>/broadcast</code> — ꜱᴇɴᴅ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴀʟʟ\n\n"
                "<b>🧹 ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ:</b>\n"
                "• <code>/activevc</code> — ꜱʜᴏᴡ ᴀᴄᴛɪᴠᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛꜱ\n"
                "• <code>/clearallassistants</code> — ʀᴇᴍᴏᴠᴇ ᴀʟʟ ᴀꜱꜱɪꜱᴛᴀɴᴛꜱ ᴅᴀᴛᴀ ꜰʀᴏᴍ ᴅʙ\n"
                "• <code>/autoend</code> — ᴇɴᴀʙʟᴇ ᴀᴜᴛᴏ-ʟᴇᴀᴠᴇ ᴡʜᴇɴ ᴠᴄ ɪꜱ ᴇᴍᴘᴛʏ"
            ),
            "markup": BackHelpMenu,
        },
    }

    if category := help_categories.get(data):
        await message.answer(f"📖 {category['title']}")
        formatted_text = (
            f"<b>{category['title']}</b>\n\n"
            f"{category['content']}\n\n"
            "🔙 <i>ᴜꜱᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ ᴛᴏ ɢᴏ ʙᴀᴄᴋ.</i>"
        )
        edit = await message.edit_message_caption(formatted_text, reply_markup=category["markup"])
        if isinstance(edit, types.Error):
            c.logger.error(f"ꜰᴀɪʟᴇᴅ ᴛᴏ ᴇᴅɪᴛ ᴍᴇꜱꜱᴀɢᴇ: {edit}")
        return

    await message.answer("⚠️ ᴜɴᴋɴᴏᴡɴ ᴄᴏᴍᴍᴀɴᴅ ᴄᴀᴛᴇɢᴏʀʏ.")
