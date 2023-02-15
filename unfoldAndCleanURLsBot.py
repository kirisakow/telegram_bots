import asyncio
import logging
import re
import telebot
from telebot.async_telebot import AsyncTeleBot
from utils import *

bot = AsyncTeleBot(token=conf.bot1.api_token)
logging.basicConfig(level=logging.DEBUG)
jl = JournalLogger(program_name='unfoldAndCleanURLsBot')


@bot.message_handler(
    func=lambda message: True,
    chat_types=['private', 'group', 'supergroup', 'channel'],
    content_types=telebot.util.content_type_media
)
async def unfoldAndCleanURLs(message):
    if not message.text:
        return
    http_url_regex_pattern = r"https?://[a-zA-Z0-9_.]+(:[0-9]{2,5})?([a-zA-Z0-9_.,/#!?&;=%:~*-]+)?"
    matches = re.finditer(http_url_regex_pattern, message.text, re.MULTILINE)
    extracted_urls = [match.group() for match in matches]
    if not extracted_urls:
        return
    jl.print(f'extracted_urls: {extracted_urls!r}')
    for orig_url in extracted_urls:
        jl.print(f'orig_url: {orig_url!r}')
        target_url = get_destination_url(orig_url).strip('\n')
        jl.print(f'target_url: {target_url!r}')
        unescaped_url = await unescape_url(target_url)
        jl.print(f'unescaped_url: {unescaped_url!r}')
        if not re.match(http_url_regex_pattern, unescaped_url):
            return
        clean_url = url_clean(unescaped_url).strip('\n')
        jl.print(f'clean_url: {clean_url!r}')
        if clean_url != orig_url:
            await bot.reply_to(
                message, clean_url,
                disable_web_page_preview=False,
                disable_notification=True,
                allow_sending_without_reply=True
            )


@bot.message_handler(
    commands=['unescape'],
    func=lambda message: True,
    chat_types=['private', 'group', 'supergroup', 'channel'],
    content_types=telebot.util.content_type_media
)
async def unescape(message):
    if message.reply_to_message:
        text = message.reply_to_message.text
        jl.print(f'orig message.reply_to_message.text: {text!r}')
    else:
        text = message.text
        if not text:
            return
        jl.print(f'orig message.text: {text!r}')
    unescaped_text = await unescape_url(text)
    jl.print(f'unescaped message.text: {unescaped_text!r}')
    await bot.reply_to(
        message, unescaped_text,
        disable_web_page_preview=False,
        disable_notification=True,
        allow_sending_without_reply=True
    )


@bot.message_handler(
    commands=['unfold_url', 'resolve_url', 'deref_url'],
    func=lambda message: True,
    chat_types=['private', 'group', 'supergroup', 'channel'],
    content_types=telebot.util.content_type_media
)
async def unfold_url(message):
    if not message.text:
        return
    http_url_regex_pattern = r"https?://[a-zA-Z0-9_.]+(:[0-9]{2,5})?([a-zA-Z0-9_.,/#!?&;=%:~*-]+)?"
    matches = re.finditer(http_url_regex_pattern, message.text, re.MULTILINE)
    extracted_urls = [match.group() for match in matches]
    jl.print(f'extracted_urls: {extracted_urls!r}')
    if not extracted_urls:
        return
    for orig_url in extracted_urls:
        jl.print(f'orig_url: {orig_url!r}')
        target_url = get_destination_url(orig_url)
        jl.print(f'target_url: {target_url!r}')
        await bot.reply_to(
            message, target_url,
            disable_web_page_preview=False,
            disable_notification=True,
            allow_sending_without_reply=True
        )


@bot.message_handler(
    commands=['clean_url'],
    func=lambda message: True,
    chat_types=['private', 'group', 'supergroup', 'channel'],
    content_types=telebot.util.content_type_media
)
async def clean_url(message):
    if not message.text:
        return
    http_url_regex_pattern = r"https?://[a-zA-Z0-9_.]+(:[0-9]{2,5})?([a-zA-Z0-9_.,/#!?&;=%:~*-]+)?"
    matches = re.finditer(http_url_regex_pattern, message.text, re.MULTILINE)
    extracted_urls = [match.group() for match in matches]
    jl.print(f'extracted_urls: {extracted_urls!r}')
    if not extracted_urls:
        return
    for orig_url in extracted_urls:
        jl.print(f'orig_url: {orig_url!r}')
        clean_url = url_clean(orig_url)
        jl.print(f'clean_url: {clean_url!r}')
        await bot.reply_to(
            message, clean_url,
            disable_web_page_preview=False,
            disable_notification=True,
            allow_sending_without_reply=True
        )

try:
    asyncio.run(
        bot.infinity_polling(
            timeout=10,
            skip_pending=True,
            logger_level=logging.DEBUG
        )
    )
except KeyboardInterrupt as e:
    print('process interrupted by user')
