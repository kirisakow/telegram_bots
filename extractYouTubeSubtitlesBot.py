from journal_logger.journal_logger import JournalLogger
from util.extractYouTubeSubtitlesBotUtil import BOT_NAME, extract_video_id
from util.shared import get_conf

from telebot.async_telebot import AsyncTeleBot
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
import asyncio
import logging
import os
import telebot
import tempfile

conf = get_conf(BOT_NAME)
bot = AsyncTeleBot(token=conf.api_token)
logging.basicConfig(level=logging.DEBUG)
jl = JournalLogger(program_name=BOT_NAME)


@bot.message_handler(
    func=lambda message: message.text.startswith(f'@{BOT_NAME}'),
    chat_types=['private', 'group', 'supergroup', 'channel'],
    content_types=telebot.util.content_type_media
)
async def extractYouTubeSubtitlesBot(message: telebot.types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action='typing', timeout=60)
    if message.reply_to_message is not None:
        message = message.reply_to_message
    message.text = message.text.replace(f'@{BOT_NAME} ', '', 1)
    language_code, video_url_or_id = sorted(message.text.split(), key=len)
    video_id = extract_video_id(video_url_or_id)
    try:
        ytt_api = YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=conf.proxy_username,
                proxy_password=conf.proxy_password,
                filter_ip_locations=[language_code],
            )
        )
        # Fetch the transcript and convert to raw data (list of dictionaries)
        transcript = ytt_api.fetch(video_id, languages=[language_code]).to_raw_data()
        # Concatenate all text snippets
        full_text = " ".join([entry['text'] for entry in transcript])
        tmp_path = tempfile.mktemp(suffix='.txt')
        open(tmp_path, 'w').write(full_text)
        with open(tmp_path, 'rb') as f:
            await bot.send_document(
                    message.chat.id,
                    f,
                    caption=f'transcript (lang: {language_code})',
                    reply_to_message_id=message.id)
        os.unlink(tmp_path)
    except Exception as e:
        print(f"Error: {e}")
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

