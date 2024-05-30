import asyncio
import logging
import os
import re
import sys
import telebot
from telebot.async_telebot import AsyncTeleBot
from utils import (
    dl_worker,
    DotDict,
    get_conf,
    get_destination_url,
    JournalLogger,
    reply_with_text_only,
    reply_with_video,
    url_clean,
)
sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '../url_tools'
        )
    )
)
from url_unescape import url_unescape

conf = get_conf()
bot = AsyncTeleBot(token=conf.bot1.api_token)
logging.basicConfig(level=logging.DEBUG)
jl = JournalLogger(program_name='unfoldAndCleanURLsBot')
HTTP_URL_REGEX_PATTERN = r"https?://[a-zA-Z0-9_.]+(:[0-9]{2,5})?\S*"
patterns_to_ignore = ['youtu.be']
PATTERNS_FROM_WHICH_TO_DOWNLOAD_MEDIA = ['tiktok.com', 'instagram.com/tv', 'instagram.com/reel', 'youtube.com/shorts', 'twitter.com', 'v.redd.it']


@bot.message_handler(
    func=lambda message: message.text is not None and message.text.split()[0].casefold() == '@unfoldAndCleanURLsbot'.casefold() and message.reply_to_message is not None and message.reply_to_message.text is not None,
    chat_types=['private', 'group', 'supergroup', 'channel'],
    content_types=telebot.util.content_type_media
)
async def unfoldAndCleanURLs(message: telebot.types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action='typing', timeout=60)
    message = message.reply_to_message
    jl.print(f"original message text: {message.text!r}")
    matches = re.finditer(HTTP_URL_REGEX_PATTERN, message.text, re.MULTILINE)
    extracted_urls = [match.group() for match in matches]
    if not extracted_urls:
        jl.print(f"no URLs in this message, but maybe we can at least unescape it and send back")
        unescaped_text = url_unescape(message.text)
        jl.print(f"unescaped message text: {unescaped_text!r}")
        if unescaped_text == message.text:
            jl.print(f"unescaped text is identical to the original text: skip it")
        else:
            await reply_with_text_only(message, unescaped_text, message.text, jl, bot)
        return
    jl.print(f'extracted_urls: {extracted_urls!r}')
    for i, orig_url in enumerate(extracted_urls, start=1):
        jl.print(f'orig_url {i}: {orig_url!r}')
        if any([pattern in orig_url for pattern in patterns_to_ignore]):
            jl.print(f'orig_url was found among patterns to ignore: skip it')
            continue
        target_url = (await get_destination_url(orig_url, jl)).strip('\n')
        jl.print(f'target_url: {target_url!r}')
        unescaped_url = url_unescape(target_url)
        jl.print(f'unescaped_url: {unescaped_url!r}')
        clean_url = (await url_clean(unescaped_url, jl)).strip('\n')
        jl.print(f'clean_url: {clean_url!r}')
        if any([pattern in orig_url for pattern in PATTERNS_FROM_WHICH_TO_DOWNLOAD_MEDIA]):
            payload = await dl_worker(clean_url, jl)
            if payload is not None:
                payload = DotDict(payload)
                payload.clean_url = clean_url
                await reply_with_video(message, payload, jl, bot)
                os.remove(payload.abs_path_to_media)
                jl.print(f"downloaded media file {payload.abs_path_to_media!r} has been removed")
                del payload
                continue
        if clean_url == orig_url:
            jl.print(f"clean_url is identical to orig_url: skip it")
        else:
            await reply_with_text_only(message, clean_url, orig_url, jl, bot)


#
# Main thread
#
try:
    asyncio.run(
        bot.infinity_polling(
            skip_pending=True,
            logger_level=logging.DEBUG
        )
    )
except KeyboardInterrupt:
    jl.print("process interrupted by user")
