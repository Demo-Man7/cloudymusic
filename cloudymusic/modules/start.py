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
◎ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʜᴇʟᴘ ʙᴜᴛᴛ𝐨𝐧 ᴛᴏ ɢᴇᴛ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ 𝐀𝐛𝐨𝐮𝐭 ᴍʏ ᴍᴏᴅᴜʟᴇꜱ 𝐀ɴᴅ ᴄᴏᴍᴍᴀɴᴅꜱ.
"""

@Client.on_message(filters=Filter.command(["start", "help"]))
async def start_cmd(c: Client, message: types.Message):
    chat_id = message.chat_id
    bot_name = c.me.first_name
    
    # Safe user name & mention handling
    user = await c.getUser(message.sender_user_id)
    user_name = user.first_name if user else "User"
    mention = f"<a href='tg://user?id={message.sender_user_id}'>{user_name}</a>"

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
            f"🎵 <b>Hello {mention}!</b>\n\n"
            f"<b>{bot_name}</b> is now active in this group.\n"
            "Here’s what I can do:\n"
            "• High-quality music streaming\n"
            "• Supports YouTube, Spotify, and more\n"
            "• Powerful controls for seamless playback\n\n"
            f"💬 <a href='{config.SUPPORT_GROUP}'>Need help? Join our Support Chat</a>"
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

    # Safe username extraction for callbacks
    bot_username = None
    try:
        if hasattr(c.me, "usernames") and c.me.usernames:
            bot_username = c.me.usernames.editable_username
        elif hasattr(c.me, "username"):
            bot_username = c.me.username
    except Exception:
        bot_username = None

    if data == "help_all":
        user = await c.getUser(message.sender_user_id)
        user_name = user.first_name if user else "User"
        await message.answer("📚 Opening Help Menu...")
        welcome_text = (
            f"👋 <b>Hello {user_name}!</b>\n\n"
            f"Welcome to <b>{c.me.first_name}</b> — your ultimate music bot.\n"
            f"<code>Version: v{__version__}</code>\n\n"
            "💡 <b>What makes me special?</b>\n"
            "• YouTube, Spotify, Apple Music, SoundCloud support\n"
            "• Advanced queue and playback controls\n"
            "• Private and group usage\n\n"
            "🔍 <i>Select a help category below to continue.</i>"
        )
        edit = await message.edit_message_caption(welcome_text, reply_markup=HelpMenu)
        if isinstance(edit, types.Error):
            c.logger.error(f"Failed to edit message: {edit}")
        return

    if data == "help_back":
        await message.answer("HOME ..")
        user = await c.getUser(message.sender_user_id)
        user_name = user.first_name if user else "User"
        await message.edit_message_caption(
            caption=startText.format(user_name, c.me.first_name),
            reply_markup=add_me_markup(bot_username),
        )
        return

    help_categories = {
        "help_user": {
            "title": "🎧 User Commands",
            "content": (
                "<b>▶️ Playback:</b>\n"
                "• <code>/play [song]</code> — Play audio in VC\n"
                "• <code>/vplay [video]</code> — Play video in VC\n"
                "<b>🛠 Utilities:</b>\n"
                "• <code>/start</code> — Intro message\n"
                "• <code>/privacy</code> — Privacy policy\n"
                "• <code>/queue</code> — View track queue\n"
            ),
            "markup": BackHelpMenu,
        },
        "help_admin": {
            "title": "⚙️ Admin Commands",
            "content": (
                "<b>🎛 Playback Controls:</b>\n"
                "• <code>/skip</code> — Skip current track\n"
                "• <code>/pause</code> — Pause playback\n"
                "• <code>/resume</code> — Resume playback\n"
                "• <code>/seek [sec]</code> — Jump to a position\n"
                "• <code>/volume [1-200]</code> — Set playback volume\n\n"
                "<b>📋 Queue Management:</b>\n"
                "• <code>/remove [x]</code> — Remove track number x\n"
                "• <code>/clear</code> — Clear the entire queue\n"
                "• <code>/loop [0-10]</code> — Repeat queue x times\n\n"
                "<b>👑 Permissions:</b>\n"
                "• <code>/auth [reply]</code> — Grant approval to use commands \n"
                "• <code>/unauth [reply]</code> — Revoke authorization\n"
                "• <code>/authlist</code> — View authorized users\n\n"
            ),
            "markup": BackHelpMenu,
        },
        "help_owner": {
            "title": "🔐 Owner Commands",
            "content": (
                "<b>⚙️ Settings:</b>\n"
                "• <code>/buttons</code> — Toggle control buttons\n"
                "• <code>/thumb</code> — Toggle thumbnail mode"
            ),
            "markup": BackHelpMenu,
        },
        "help_devs": {
            "title": "🛠 Developer Tools",
            "content": (
                "<b>📊 System Tools:</b>\n"
                "• <code>/stats</code> — Show usage stats\n"
                "• <code>/logger</code> — Toggle log mode\n"
                "• <code>/broadcast</code> — Send a message to all\n\n"
                "<b>🧹 Maintenance:</b>\n"
                "• <code>/activevc</code> — Show active voice chats\n"
                "• <code>/clearallassistants</code> — Remove all assistants data from DB\n"
                "• <code>/autoend</code> — Enable auto-leave when VC is empty"
            ),
            "markup": BackHelpMenu,
        },
    }

    if category := help_categories.get(data):
        await message.answer(f"📖 {category['title']}")
        formatted_text = (
            f"<b>{category['title']}</b>\n\n"
            f"{category['content']}\n\n"
            "🔙 <i>Use the buttons below to go back.</i>"
        )
        edit = await message.edit_message_caption(formatted_text, reply_markup=category["markup"])
        if isinstance(edit, types.Error):
            c.logger.error(f"Failed to edit message: {edit}")
        return

    await message.answer("⚠️ Unknown command category.")
