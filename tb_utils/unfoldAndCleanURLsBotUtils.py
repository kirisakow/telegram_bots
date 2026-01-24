import json
import re
import subprocess
import telebot
from dot_dict.dot_dict import DotDict
from journal_logger.journal_logger import JournalLogger
from url_unescape import url_unescape
from telebot.async_telebot import AsyncTeleBot


BOT_NAME = 'unfoldAndCleanURLsBot'
HTTP_URL_REGEX_PATTERN = r"https?://[a-zA-Z0-9-_.]+(:[0-9]{2,5})?\S*"
PATTERNS_TO_IGNORE = ['youtu.be']
PATTERNS_FROM_WHICH_TO_DOWNLOAD_MEDIA = [
    'tiktok.com',
    'instagram.com/tv',
    'instagram.com/reel',
    'youtube.com/shorts',
    'twitter.com',
    'v.redd.it'
]


def extract_urls(msg_txt: str) -> list:
    matches = re.finditer(HTTP_URL_REGEX_PATTERN, msg_txt, re.MULTILINE)
    extracted_urls = [match.group() for match in matches]
    return extracted_urls


async def get_destination_url(url: str, jl: JournalLogger) -> str:
    """Follow the URL through redirects, if any, and return the destination URL"""
    proc_url_deref = subprocess.Popen(
        ['/usr/bin/bash', '-c', '. ../url_tools/bash_functions.sh ; url_deref'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    proc_url_deref.stdin.write(url.encode())
    proc_url_deref.stdin.flush()
    output_as_bytes, err_as_bytes = proc_url_deref.communicate()
    if err_as_bytes and not output_as_bytes:
        jl.print(err_as_bytes)
        return url
    return output_as_bytes.decode()


async def url_clean(url: str, jl: JournalLogger) -> str:
    """Clean a URL of any junk query parameters. Rules:
    https://github.com/kirisakow/url_tools/blob/main/url_clean/url_cleaner/unwanted_query_params.txt"""
    proc_url_clean = subprocess.Popen(
        ['../url_tools/url_clean/url_clean'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    proc_url_clean.stdin.write(url.encode())
    proc_url_clean.stdin.flush()
    output_as_bytes, err_as_bytes = proc_url_clean.communicate()
    if err_as_bytes and not output_as_bytes:
        jl.print(err_as_bytes)
        return url
    return output_as_bytes.decode()


async def reply_with_video(message: telebot.types.Message,
                           payload: dict | DotDict,
                           jl: JournalLogger,
                           bot: AsyncTeleBot) -> None:
    with open(file=payload.abs_path_to_media, mode='rb') as videofile_bytes:
        await bot.send_chat_action(chat_id=message.chat.id,
                                   action='upload_video', timeout=60)
        await bot.send_video(
            reply_to_message_id=message.message_id,
            chat_id=message.chat.id,
            video=videofile_bytes,
            thumb=payload.dl_info.thumbnail,
            caption='\n'.join([
                payload.clean_url,
                build_caption(payload.dl_info)
            ]),
            disable_notification=True,
            allow_sending_without_reply=True
        )


def build_caption(dl_info: DotDict | dict) -> str:
    fields_by_extractor = {
        'instagram': ['title', 'description', 'uploader', 'channel'],
        'tiktok': ['title', 'description', 'uploader', 'uploader_id'],
        'twitter': ['description', 'uploader', 'uploader_id'],
        'youtube': ['title', 'description', 'uploader', 'channel'],
        'reddit': ['fulltitle'],
        'generic': [],
    }
    for extractor_name, field_names in fields_by_extractor.items():
        if extractor_name in dl_info.extractor.lower():
            return '\n'.join([dl_info[fld_nm] for fld_nm in field_names])
    return ''


async def dl_worker(url: str, jl: JournalLogger):
    ydl = yt_dlp.YoutubeDL({
        'format': 'bestvideo*+bestaudio/best',
        'outtmpl': '%(webpage_url_domain)s.%(webpage_url_basename)s.%(ext)s',
        'fixup': 'never'})
    try:
        jl.print("start downloading media file")
        dl_info = ydl.extract_info(url)
        jl.print("media file has been downloaded")
        jl.print(json.dumps(ydl.sanitize_info(
            dl_info), indent=2, ensure_ascii=False))
        dl_info = DotDict(dl_info)
        try:
            abs_path_to_media = dl_info.requested_downloads[-1].filepath
            return {'abs_path_to_media': abs_path_to_media,
                    'dl_info': dl_info}
        except Exception as e:
            jl.print(e)
    except Exception as e:
        jl.print("download process has not finished properly")
        jl.print(e)
        return None
    return None


async def old_unfoldAndCleanURLs(message: telebot.types.Message,
                                 jl: JournalLogger,
                                 bot: AsyncTeleBot):
    await bot.send_chat_action(chat_id=message.chat.id, action='typing', timeout=60)
    message = message.reply_to_message
    jl.print(f"original message text: {message.text!r}")
    matches = re.finditer(HTTP_URL_REGEX_PATTERN, message.text, re.MULTILINE)
    extracted_urls = [match.group() for match in matches]
    if not extracted_urls:
        jl.print("no URLs in this message, but maybe we can at least unescape it and send back")
        unescaped_text = url_unescape(message.text)
        jl.print("unescaped message text: {unescaped_text!r}")
        if unescaped_text == message.text:
            jl.print("unescaped text is identical to the original text: skip it")
        else:
            await bot.reply_to(
                message, unescaped_text,
                disable_web_page_preview=False,
                disable_notification=True,
                allow_sending_without_reply=True
            )
        return
    jl.print(f'extracted_urls: {extracted_urls!r}')
    for i, orig_url in enumerate(extracted_urls, start=1):
        jl.print(f'orig_url {i}: {orig_url!r}')
        if any([pattern in orig_url for pattern in PATTERNS_TO_IGNORE]):
            jl.print('orig_url was found among patterns to ignore: skip it')
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
            jl.print("clean_url is identical to orig_url: skip it")
        else:
            await bot.reply_to(
                message, clean_url,
                disable_web_page_preview=False,
                disable_notification=True,
                allow_sending_without_reply=True
            )
