import asyncio
import logging
import telebot
from telebot.async_telebot import AsyncTeleBot
from journal_logger.journal_logger import JournalLogger
from tb_utils.extractYouTubeSubtitlesBotUtils import (
    BOT_NAME,
    get_conf,
)
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

conf = get_conf()
bot = AsyncTeleBot(token=conf.bot0.api_token)
logging.basicConfig(level=logging.DEBUG)
jl = JournalLogger(program_name=BOT_NAME)


def extract_video_id(url_or_id):
    # Take the 11 rightmost characters, which is the YouTube video ID
    return url_or_id[-11:]


@bot.message_handler(
    func=lambda message: (message.text is not None and message.text.split()[0].casefold() == f'@{BOT_NAME}'.casefold()) or (message.reply_to_message is not None and message.reply_to_message.text is not None),
    chat_types=['private', 'group', 'supergroup', 'channel'],
    content_types=telebot.util.content_type_media
)
async def extractYouTubeSubtitlesBot(message: telebot.types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action='typing', timeout=60)
    if message.reply_to_message is not None:
        message = message.reply_to_message
    message.text = message.text.replace(f'@{BOT_NAME} ', '', 1)
    language_code, video_url_or_id = message.text.split()
    video_id = extract_video_id(video_url_or_id)
    try:
        ytt_api = YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=conf.bot0.proxy_username,
                proxy_password=conf.bot0.proxy_password,
                filter_ip_locations=[language_code],
            )
        )
        # Fetch the transcript and convert to raw data (list of dictionaries)
        transcript = ytt_api.fetch(video_id, languages=[language_code]).to_raw_data()
        # Concatenate all text snippets
        full_text = " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        print(f"Error: {e}")


    await bot.reply_to(
        message, full_text,
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

