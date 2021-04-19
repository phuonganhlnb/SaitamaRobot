import html

from telegram import ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler, Filters, run_async
from telegram.utils.helpers import mention_html

from SaitamaRobot import (
    DEV_USERS,
    LOGGER,
    OWNER_ID,
    DRAGONS,
    DEMONS,
    TIGERS,
    WOLVES,
    dispatcher,
)
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    connection_status,
    is_user_admin,
    is_user_ban_protected,
    is_user_in_chat,
    user_admin,
    user_can_ban,
    can_delete,
)
from SaitamaRobot.modules.helper_funcs.extraction import extract_user_and_text
from SaitamaRobot.modules.helper_funcs.string_handling import extract_time
from SaitamaRobot.modules.log_channel import gloggable, loggable


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def ban(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot = context.bot
    args = context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Mình nghi ngờ đó là một người dùng.")
        return log_message
    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "Không tìm thấy User":
            raise
        message.reply_text("Dường như không thể tìm thấy người này.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Oh yeah, tự ban chính mình à, ngốc quá!")
        return log_message

    if is_user_ban_protected(chat, user_id, member) and user not in DEV_USERS:
        if user_id == OWNER_ID:
            message.reply_text("Cố gắng đưa mình đi chống lại một thảm họa cấp độ Chúa hả?")
        elif user_id in DEV_USERS:
            message.reply_text("Mình không thể hành động chống lại chính chị chủ của mình được.")
        elif user_id in DRAGONS:
            message.reply_text(
                "Chiến đấu với con Rồng này ở đây sẽ khiến cuộc sống của dân thường gặp nguy hiểm.",
            )
        elif user_id in DEMONS:
            message.reply_text(
                "Mang lệnh từ hiệp hội Anh hùng để chống lại một thảm họa quỷ.",
            )
        elif user_id in TIGERS:
            message.reply_text(
                "Mang lệnh từ hiệp hội anh hùng để chống lại thảm họa Tiger.",
            )
        elif user_id in WOLVES:
            message.reply_text("Khả năng của loài sói khiến chúng miễn nhiễm với lệnh cấm!")
        else:
            message.reply_text("Người dùng này có quyền miễn trừ và không thể bị cấm.")
        return log_message
    if message.text.startswith("/s"):
        silent = True
        if not can_delete(chat, context.bot.id):
            return ""
    else:
        silent = False
    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#{'S' if silent else ''}BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        chat.kick_member(user_id)

        if silent:
            if message.reply_to_message:
                message.reply_to_message.delete()
            message.delete()
            return log

        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        reply = (
            f"<code>❕</code><b>Ban Event</b>\n"
            f"<code> </code><b>•  User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
        )
        if reason:
            reply += f"\n<code> </code><b>•  Reason:</b> \n{html.escape(reason)}"
        bot.sendMessage(chat.id, reply, parse_mode=ParseMode.HTML, quote=False)
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            if silent:
                return log
            message.reply_text("Banned!", quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "ERROR banning user %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Uhm...that didn't work...")

    return log_message


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def temp_ban(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("I doubt that's a user.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "Người dùng không được tìm thấy":
            raise
        message.reply_text("Mình dường như không thể tìm thấy người dùng này.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Mình sẽ không BAN chính mình đâu, Haizzzz")
        return log_message

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Mình không cảm thấy thích nó.")
        return log_message

    if not reason:
        message.reply_text("Bạn chưa chỉ định thời gian để cấm người dùng này!")
        return log_message

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    reason = split_reason[1] if len(split_reason) > 1 else ""
    bantime = extract_time(message, time_val)

    if not bantime:
        return log_message

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        "#TEMP BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}\n"
        f"<b>Time:</b> {time_val}"
    )
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            f"Banned! User {mention_html(member.user.id, html.escape(member.user.first_name))} "
            f"will be banned for {time_val}.",
            parse_mode=ParseMode.HTML,
        )
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text(
                f"Banned! User will be banned for {time_val}.", quote=False,
            )
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "ERROR banning user %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Hix, mình không thể cấm người dùng đó.")

    return log_message


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def punch(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Mình nghi ngờ đó là một người dùng.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "Không tìm thấy người dùng":
            raise

        message.reply_text("Mình dường như không thể tìm thấy người dùng này.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Yeahhh!! Mình sẽ không làm điều đó.")
        return log_message

    if is_user_ban_protected(chat, user_id):
        message.reply_text("Mình thực sự ước mình có thể đấm người dùng này ....")
        return log_message

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            f"Đã cho ăn đấm! {mention_html(member.user.id, html.escape(member.user.first_name))}.",
            parse_mode=ParseMode.HTML,
        )
        log = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#KICKED\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
        )
        if reason:
            log += f"\n<b>Lý do:</b> {reason}"

        return log

    else:
        message.reply_text("Hix, mình không thể đấm người dùng đó.")

    return log_message


@run_async
@bot_admin
@can_restrict
def punchme(update: Update, context: CallbackContext):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Mình ước là mình có thể ... nhưng bạn là quản trị viên mà @@.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("*Đấm bạn ra khỏi nhóm*")
    else:
        update.effective_message.reply_text("Huh? mình không thể :/")


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def unban(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Mình nghi ngờ đó là một người dùng.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "Không tìm thấy người dùng này":
            raise
        message.reply_text("Mình dường như không thể tìm thấy người dùng này.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Làm thế nào mình có thể tự bỏ cấm nếu như mình không có ở đây ...?")
        return log_message

    if is_user_in_chat(chat, user_id):
        message.reply_text("Không phải người này đã ở đây sao??")
        return log_message

    chat.unban_member(user_id)
    message.reply_text("Yep, người dùng này có thể tham gia!")

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )
    if reason:
        log += f"\n<b>Lý do:</b> {reason}"

    return log


@run_async
@connection_status
@bot_admin
@can_restrict
@gloggable
def selfunban(context: CallbackContext, update: Update) -> str:
    message = update.effective_message
    user = update.effective_user
    bot, args = context.bot, context.args
    if user.id not in DRAGONS or user.id not in TIGERS:
        return

    try:
        chat_id = int(args[0])
    except:
        message.reply_text("Vui lòng cung cấp một ID chat hợp lệ.")
        return

    chat = bot.getChat(chat_id)

    try:
        member = chat.get_member(user.id)
    except BadRequest as excp:
        if excp.message == "Không tìm thấy người dùng":
            message.reply_text("Mình dường như không thể tìm thấy người dùng này.")
            return
        else:
            raise

    if is_user_in_chat(chat, user.id):
        message.reply_text("Bạn vẫn chưa tham gia chat hả??")
        return

    chat.unban_member(user.id)
    message.reply_text("Yep, mình đã unban bạn.")

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )

    return log


__help__ = """
 • `/punchme`*:* đấm vào người dùng đã ra lệnh ^^
*Admins only:*
 • `/ban <userhandle>`*:* Ban một người dùng. (qua handle, hoặc reply)
 • `/sban <userhandle>`*:* Cấm âm thầm người dùng. Xóa lệnh, tin nhắn đã trả lời và không trả lời. (qua handle, hoặc reply)
 • `/tban <userhandle> x(m/h/d)`*:* ban một người dùng `x` thời gian. (qua handle, hoặc reply). `m` = `phút`, `h` = `giờ`, `d` = `ngày`.
 • `/unban <userhandle>`*:* unbans một người dùng. (qua handle, hoặc reply)
 • `/punch <userhandle>`*:* Đấm người dùng ra khỏi nhóm, (qua handle, hoặc reply)
"""

BAN_HANDLER = CommandHandler(["ban", "sban"], ban)
TEMPBAN_HANDLER = CommandHandler(["tban"], temp_ban)
PUNCH_HANDLER = CommandHandler("punch", punch)
UNBAN_HANDLER = CommandHandler("unban", unban)
ROAR_HANDLER = CommandHandler("roar", selfunban)
PUNCHME_HANDLER = DisableAbleCommandHandler("punchme", punchme, filters=Filters.group)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(PUNCH_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(ROAR_HANDLER)
dispatcher.add_handler(PUNCHME_HANDLER)

__mod_name__ = "Bans"
__handlers__ = [
    BAN_HANDLER,
    TEMPBAN_HANDLER,
    PUNCH_HANDLER,
    UNBAN_HANDLER,
    ROAR_HANDLER,
    PUNCHME_HANDLER,
]
