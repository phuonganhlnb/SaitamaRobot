import html
from typing import Optional, List
import re

from telegram import Message, Chat, Update, User, ChatPermissions

from SaitamaRobot import TIGERS, WOLVES, dispatcher
from SaitamaRobot.modules.helper_funcs.chat_status import (
    bot_admin,
    is_user_admin,
    user_admin,
    user_admin_no_reply,
)
from SaitamaRobot.modules.log_channel import loggable
from SaitamaRobot.modules.sql import antiflood_sql as sql
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    run_async,
)
from telegram.utils.helpers import mention_html
from SaitamaRobot.modules.helper_funcs.string_handling import extract_time
from SaitamaRobot.modules.connection import connected
from SaitamaRobot.modules.helper_funcs.alternate import send_message
from SaitamaRobot.modules.sql.approve_sql import is_approved

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(update, context) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    if not user:  # ignore channels
        return ""

    # ignore admins and whitelists
    if is_user_admin(chat, user.id) or user.id in WOLVES or user.id in TIGERS:
        sql.update_flood(chat.id, None)
        return ""
    # ignore approved users
    if is_approved(chat.id, user.id):
        sql.update_flood(chat.id, None)
        return
    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            chat.kick_member(user.id)
            execstrings = "Banned"
            tag = "BANNED"
        elif getmode == 2:
            chat.kick_member(user.id)
            chat.unban_member(user.id)
            execstrings = "Kicked"
            tag = "KICKED"
        elif getmode == 3:
            context.bot.restrict_chat_member(
                chat.id, user.id, permissions=ChatPermissions(can_send_messages=False),
            )
            execstrings = "Muted"
            tag = "MUTED"
        elif getmode == 4:
            bantime = extract_time(msg, getvalue)
            chat.kick_member(user.id, until_date=bantime)
            execstrings = "Banned for {}".format(getvalue)
            tag = "TBAN"
        elif getmode == 5:
            mutetime = extract_time(msg, getvalue)
            context.bot.restrict_chat_member(
                chat.id,
                user.id,
                until_date=mutetime,
                permissions=ChatPermissions(can_send_messages=False),
            )
            execstrings = "Muted for {}".format(getvalue)
            tag = "TMUTE"
        send_message(
            update.effective_message, "Beep Boop! Boop Beep!\n{}!".format(execstrings),
        )

        return (
            "<b>{}:</b>"
            "\n#{}"
            "\n<b>User:</b> {}"
            "\nFlooded the group.".format(
                tag,
                html.escape(chat.title),
                mention_html(user.id, html.escape(user.first_name)),
            )
        )

    except BadRequest:
        msg.reply_text(
            "Mình không thể hạn chế mọi người ở đây, hãy cho mình quyền trước! Cho đến lúc đó, mình sẽ tắt tính năng anti-flood",
        )
        sql.set_flood(chat.id, 0)
        return (
            "<b>{}:</b>"
            "\n#INFO"
            "\nKhông có đủ quyền hạn chế người dùng nên tính năng anti-flood sẽ tự động tắt".format(
                chat.title,
            )
        )


@run_async
@user_admin_no_reply
@bot_admin
def flood_button(update: Update, context: CallbackContext):
    bot = context.bot
    query = update.callback_query
    user = update.effective_user
    match = re.match(r"unmute_flooder\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat = update.effective_chat.id
        try:
            bot.restrict_chat_member(
                chat,
                int(user_id),
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            update.effective_message.edit_text(
                f"Unmuted by {mention_html(user.id, html.escape(user.first_name))}.",
                parse_mode="HTML",
            )
        except:
            pass


@run_async
@user_admin
@loggable
def set_flood(update, context) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = context.args

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "Lệnh này được sử dụng trong nhóm không phải trong PM",
            )
            return ""
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if len(args) >= 1:
        val = args[0].lower()
        if val in ["off", "no", "0"]:
            sql.set_flood(chat_id, 0)
            if conn:
                text = message.reply_text(
                    "Antiflood đã bị vô hiệu hóa trong {}.".format(chat_name),
                )
            else:
                text = message.reply_text("Antiflood đã bị vô hiệu hóa.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat_id, 0)
                if conn:
                    text = message.reply_text(
                        "Antiflood đã bị vô hiệu hóa trong {}.".format(chat_name),
                    )
                else:
                    text = message.reply_text("Antiflood đã bị vô hiệu hóa.")
                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nĐã vô hiệu hóa antiflood.".format(
                        html.escape(chat_name),
                        mention_html(user.id, html.escape(user.first_name)),
                    )
                )

            elif amount <= 3:
                send_message(
                    update.effective_message,
                    "Antiflood phải là 0 (bị vô hiệu hóa) hoặc số lớn hơn 3!",
                )
                return ""

            else:
                sql.set_flood(chat_id, amount)
                if conn:
                    text = message.reply_text(
                        "Antiflood đã được đặt thành {} trong trò chuyện: {}".format(
                            amount, chat_name,
                        ),
                    )
                else:
                    text = message.reply_text(
                        "Đã cập nhật thành công giới hạn Antiflood thành {}!".format(amount),
                    )
                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nĐặt antiflood thành <code>{}</code>.".format(
                        html.escape(chat_name),
                        mention_html(user.id, html.escape(user.first_name)),
                        amount,
                    )
                )

        else:
            message.reply_text("Đối số không hợp lệ, vui lòng sử dụng một số, 'off' or 'no'")
    else:
        message.reply_text(
            (
                "Sử dụng `/setflood number` để kích hoạt anti-flood.\nHoặc sử dụng `/setflood off` để vô hiệu hóa antiflood!."
            ),
            parse_mode="markdown",
        )
    return ""


@run_async
def flood(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message

    conn = connected(context.bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "Lệnh này được sử dụng trong nhóm không dùng trong PM",
            )
            return
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        if conn:
            text = msg.reply_text(
                "Mình không thực thi bất kỳ biện pháp antiflood nào ở {}!".format(chat_name),
            )
        else:
            text = msg.reply_text("Tôi không thực thi bất kỳ antiflood nào ở đây!")
    else:
        if conn:
            text = msg.reply_text(
                "Mình hiện đang giới hạn thành viên sau {} tin nhắn liên tiếp trong {}.".format(
                    limit, chat_name,
                ),
            )
        else:
            text = msg.reply_text(
                "Mình hiện đang giới hạn thành viên sau {} tin nhắn liên tiếp.".format(
                    limit,
                ),
            )


@run_async
@user_admin
def set_flood_mode(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "Lệnh này được sử dụng trong nhóm không dùng trong PM",
            )
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() == "ban":
            settypeflood = "ban"
            sql.set_flood_strength(chat_id, 1, "0")
        elif args[0].lower() == "kick":
            settypeflood = "kick"
            sql.set_flood_strength(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            settypeflood = "mute"
            sql.set_flood_strength(chat_id, 3, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                teks = """Có vẻ như bạn đã cố gắng đặt giá trị thời gian cho antiflood nhưng bạn không chỉ định thời gian; Thủ, `/setfloodmode tban <Giá trị thời gian>`.
Ví dụ về giá trị thời gian: 4m = 4 phút, 3h = 3 giờ, 6d = 6 ngày, 5w = 5 tuần."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "tban for {}".format(args[1])
            sql.set_flood_strength(chat_id, 4, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                teks = (
                    update.effective_message,
                    """Có vẻ như bạn đã cố gắng đặt giá trị thời gian cho antiflood nhưng bạn không chỉ định thời gian; Try, `/setfloodmode tmute <Giá trị thời gian>`.
Ví dụ về giá trị thời gian: 4m = 4 phút, 3h = 3 giờ, 6d = 6 ngày, 5w = 5 tuần.""",
                )
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "tmute for {}".format(args[1])
            sql.set_flood_strength(chat_id, 5, str(args[1]))
        else:
            send_message(
                update.effective_message, "Mình chỉ hiểu ban/kick/mute/tban/tmute thôi!",
            )
            return
        if conn:
            text = msg.reply_text(
                "Vượt quá giới hạn antiflood liên tiếp sẽ dẫn đến{} trong {}!".format(
                    settypeflood, chat_name,
                ),
            )
        else:
            text = msg.reply_text(
                "Vượt quá giới hạn antiflood liên tiếp sẽ dẫn đến {}!".format(
                    settypeflood,
                ),
            )
        return (
            "<b>{}:</b>\n"
            "<b>Admin:</b> {}\n"
            "Đã thay đổi chế độ antiflood. Người dùng sẽ {}.".format(
                settypeflood,
                html.escape(chat.title),
                mention_html(user.id, html.escape(user.first_name)),
            )
        )
    else:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            settypeflood = "ban"
        elif getmode == 2:
            settypeflood = "kick"
        elif getmode == 3:
            settypeflood = "mute"
        elif getmode == 4:
            settypeflood = "tban for {}".format(getvalue)
        elif getmode == 5:
            settypeflood = "tmute for {}".format(getvalue)
        if conn:
            text = msg.reply_text(
                "Gửi nhiều tin nhắn hơn giới hạn antiflood sẽ dẫn đến{} trong {}.".format(
                    settypeflood, chat_name,
                ),
            )
        else:
            text = msg.reply_text(
                "Gửi nhiều tin nhắn hơn giới hạn antiflood sẽ dẫn đến {}.".format(
                    settypeflood,
                ),
            )
    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "Không thực thi để kiểm soát flood."
    else:
        return "Antiflood đã được đặt thành`{}`.".format(limit)


__help__ = """
Antiflood cho phép bạn thực hiện hành động đối với những người dùng gửi hơn x tin nhắn liên tiếp. Vượt số lượng đã định sắn sẽ dẫn đến việc hạn chế người dùng đó.
Điều này sẽ tắt tiếng người dùng nếu họ gửi hơn 10 tin nhắn liên tiếp, các bot sẽ bị bỏ qua.
 • `/flood`*:* Nhận cài đặt kiểm soát flood hiện tại
• *Admins only:*
 • `/setflood <int/'no'/'off'>`*:* bật hoặc tắt kiểm soát flood
 *Ví dụ:* `/setflood 10`
 • `/setfloodmode <ban/kick/mute/tban/tmute> <Giá trị>`*:* Hành động cần thực hiện khi người dùng đã vượt quá giới hạn flood. ban/kick/mute/tmute/tban
• *Ghi chú:*
 • Giá trị phải được điền cho tban và tmute!!
 Nó có thể là:
 `5m` = 5 phút
 `6h` = 6 giờ
 `3d` = 3 ngày
 `1w` = 1 tuần
 """

__mod_name__ = "Anti-Flood"

FLOOD_BAN_HANDLER = MessageHandler(
    Filters.all & ~Filters.status_update & Filters.group, check_flood,
)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, filters=Filters.group)
SET_FLOOD_MODE_HANDLER = CommandHandler(
    "setfloodmode", set_flood_mode, pass_args=True,
)  # , filters=Filters.group)
FLOOD_QUERY_HANDLER = CallbackQueryHandler(flood_button, pattern=r"unmute_flooder")
FLOOD_HANDLER = CommandHandler("flood", flood, filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(FLOOD_QUERY_HANDLER)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(SET_FLOOD_MODE_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)

__handlers__ = [
    (FLOOD_BAN_HANDLER, FLOOD_GROUP),
    SET_FLOOD_HANDLER,
    FLOOD_HANDLER,
    SET_FLOOD_MODE_HANDLER,
]
