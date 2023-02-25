import asyncio
import logging
import os
import re
import sys
import telebot
from telebot.async_telebot import AsyncTeleBot
from utils import *
sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '../url_tools'
        )
    )
)
from url_unescape import url_unescape

bot = AsyncTeleBot(token=conf.bot1.api_token)
logging.basicConfig(level=logging.DEBUG)
jl = JournalLogger(program_name='unfoldAndCleanURLsBot')
http_url_regex_pattern = r"https?://[a-zA-Z0-9_.]+(:[0-9]{2,5})?\S*"
patterns_to_ignore = ['youtu.be']
patterns_from_which_to_download_media = ['tiktok.com', 'instagram.com/tv', 'instagram.com/reel', 'youtube.com/shorts', 'twitter.com', 'v.redd.it']


@bot.message_handler(
    func=lambda message: True,
    chat_types=['private', 'group', 'supergroup', 'channel'],
    content_types=telebot.util.content_type_media
)
async def unfoldAndCleanURLs(message):
    if not message.text:
        return
    await bot.send_chat_action(chat_id=message.chat.id, action='typing', timeout=60)
    matches = re.finditer(http_url_regex_pattern, message.text, re.MULTILINE)
    extracted_urls = [match.group() for match in matches]
    if not extracted_urls:
        jl.print(f"no URLs in this message: unescape message text and return")
        jl.print(f"original message text: {message.text!r}")
        unescaped_text = url_unescape(message.text)
        jl.print(f"unescaped message text: {unescaped_text!r}")
        await reply_with_text_only(message, unescaped_text, message.text, jl, bot)
        return
    jl.print(f'extracted_urls: {extracted_urls!r}')
    for orig_url in extracted_urls:
        jl.print(f'orig_url: {orig_url!r}')
        if any([pattern in orig_url for pattern in patterns_to_ignore]):
            jl.print(f'skip this URL as orig_url was found among patterns to ignore')
            continue
        reply_with_media = False
        ret = DotDict({'abs_path_to_media': '', 'clean_url': '', 'dl_info': ''})
        if any([pattern in orig_url for pattern in patterns_from_which_to_download_media]):
            reply_with_media = True
            payload = await dl_worker(orig_url, jl)
            if payload is None:
                reply_with_media = False
            else:
                ret.update(payload)
                ret = DotDict(ret)
                jl.print(f"stored ret.abs_path_to_media = {ret.abs_path_to_media!r}")
                jl.print(f"stored ret.clean_url = {ret.clean_url!r}")
                jl.print(f"stored ret.dl_info = {'{...}'}")
                await reply_with_video(message, ret, jl, bot)
                os.remove(ret.abs_path_to_media)
                jl.print(f"downloaded media file {ret.abs_path_to_media!r} has been removed")
                del ret
                continue
        target_url = (await get_destination_url(orig_url, jl)).strip('\n')
        jl.print(f'target_url: {target_url!r}')
        unescaped_url = url_unescape(target_url)
        jl.print(f'unescaped_url: {unescaped_url!r}')
        clean_url = (await url_clean(unescaped_url, jl)).strip('\n')
        jl.print(f'clean_url: {clean_url!r}')
        ret.clean_url = clean_url
        jl.print(f"stored ret.clean_url = {ret.clean_url!r}")
        if not reply_with_media:
            await reply_with_text_only(message, clean_url, orig_url, jl, bot)
            continue


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
except KeyboardInterrupt as e:
    jl.print("process interrupted by user")
