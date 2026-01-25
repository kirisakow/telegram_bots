from journal_logger.journal_logger import JournalLogger
from url_unescape import url_unescape
from util.unfoldAndCleanURLsBotUtil import (
    BOT_NAME,
    PATTERNS_TO_IGNORE,
    extract_urls,
    get_destination_url,
    url_clean,
)
from util.shared import get_conf

from telebot.async_telebot import AsyncTeleBot
import asyncio
import logging
import telebot

conf = get_conf(BOT_NAME)
bot = AsyncTeleBot(token=conf.api_token)
logging.basicConfig(level=logging.DEBUG)
jl = JournalLogger(program_name=BOT_NAME)


@bot.message_handler(
    func=lambda message: message.text.startswith(f'@{BOT_NAME}'),
    chat_types=['private', 'group', 'supergroup', 'channel'],
    content_types=telebot.util.content_type_media
)
async def unfoldAndCleanURLs(message: telebot.types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action='typing', timeout=60)
    if message.reply_to_message is not None:
        message = message.reply_to_message
    message.text = message.text.replace(f'@{BOT_NAME} ', '', 1)
    jl.print(f"original message text: {message.text!r}")
    unescaped_text = url_unescape(message.text)
    jl.print(f"unescaped message text: {unescaped_text!r}")
    extracted_urls = extract_urls(message.text)
    if not extracted_urls:
        jl.print("no URLs in this message, but maybe we can at least unescape it and send back")
        if unescaped_text == message.text:
            jl.print("however, unescaped text is identical to the original text: nothing to return")
            return
        await bot.reply_to(
            message, unescaped_text,
            disable_web_page_preview=False,
            disable_notification=True,
            allow_sending_without_reply=True
        )
        return
    msg_txt_clean_copy = message.text
    jl.print(f'extracted_urls: {extracted_urls!r}')
    for i, orig_url in enumerate(extracted_urls, start=1):
        jl.print(f'orig_url {i}: {orig_url!r}')
        if any([pattern in orig_url for pattern in PATTERNS_TO_IGNORE]):
            jl.print(f'orig_url {i} was found among patterns to ignore: skip it')
            continue
        target_url = (await get_destination_url(orig_url, jl)).strip('\n')
        jl.print(f'target_url: {target_url!r}')
        unescaped_url = url_unescape(target_url)
        jl.print(f'unescaped_url: {unescaped_url!r}')
        clean_url = (await url_clean(unescaped_url, jl)).strip('\n')
        jl.print(f'clean_url: {clean_url!r}')
        if clean_url == orig_url:
            jl.print("clean_url is identical to orig_url: skip it")
            continue
        msg_txt_clean_copy = msg_txt_clean_copy.replace(orig_url, clean_url, 1)
    await bot.reply_to(
        message, msg_txt_clean_copy,
        disable_web_page_preview=False,
        disable_notification=True,
        allow_sending_without_reply=True
    )
    return


#
# Main thread
#
try:
    print("""To monitor the logs, use command "journalctl -f" """)
    asyncio.run(
        bot.infinity_polling(
            skip_pending=True,
            logger_level=logging.DEBUG
        )
    )
except KeyboardInterrupt:
    asyncio.run(bot.close_session())
    jl.print("Process interrupted by user")
    print("Process interrupted by user")
