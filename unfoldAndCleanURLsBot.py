#!/usr/bin/python

import asyncio
from pprint import pprint
import re
import telebot
from telebot.async_telebot import AsyncTeleBot
from utils import *

bot = AsyncTeleBot(token=conf.bot1.api_token)


@bot.message_handler(
    func=lambda message: True,
    chat_types=['group', 'supergroup', 'channel'],
    content_types=telebot.util.content_type_media
)
async def unfoldAndCleanURLs(message):
    if not message.text:
        return
    http_url_regex_pattern = r"https?://[a-zA-Z0-9_.]+(:[0-9]{2,5})?([a-zA-Z0-9_.,/#!?&;=%:~*-]+)?"
    matches = re.finditer(http_url_regex_pattern, message.text, re.MULTILINE)
    extracted_urls = [match.group() for match in matches]
    print('extracted_urls:', extracted_urls)
    if not extracted_urls:
        return
    for orig_url in extracted_urls:
        print('orig_url:', orig_url)
        unescaped_url = unescape_url(orig_url)
        print('unescaped_url:', unescaped_url)
        target_url = get_target_url(unescaped_url)
        print('target_url:', target_url)
        clean_url = url_clean(target_url)
        print('clean_url:', clean_url)
        if clean_url != orig_url:
            await bot.reply_to(
                message, clean_url,
                disable_web_page_preview=False,
                disable_notification=True,
                allow_sending_without_reply=True
            )


asyncio.run(bot.infinity_polling())