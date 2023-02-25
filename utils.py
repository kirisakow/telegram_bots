from configparser import ConfigParser
from cysystemd import journal
import httpx
import inspect
import json
import logging
import re
import subprocess
import sys
import telebot
import urllib.parse
import yt_dlp


def this_func_name():
    return inspect.stack()[1].function


def caller_func_name():
    return inspect.stack()[2].function


class JournalLogger(logging.Logger):
    """An object that enables logging to `journalctl`"""

    def __init__(self, program_name=None):
        super().__init__(program_name)
        self.program_name = program_name

    def print(self, *args, **kwargs):
        if (caller := caller_func_name()) is str:
            print(f"{self.program_name}: {caller}: {str(*args)}", **kwargs, file=journal)
        else:
            print(f"{self.program_name}: {str(*args)}", **kwargs, file=journal)


async def unescape_url_async(url: str) -> str:
    resp = httpx.get(
        f'https://crac.ovh/unescape_url/{urllib.parse.quote(url)}'
    )
    if resp.status_code != httpx.codes.OK:
        status_code_and_name = f"{resp.status_code} {httpx.codes(resp.status_code).name}"
        return status_code_and_name.replace('_', ' ')
    unescaped_url = resp.text.strip('"')
    return unescaped_url


async def get_destination_url(url: str, jl: JournalLogger) -> str:
    """Follow the URL through redirects, if any, and return the destination URL"""
    proc_url_deref = subprocess.Popen(
        ['bash', '-c', '. ../url_tools/bash_functions.sh ; url_deref'],
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
        ['url_clean'],
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


class DotDict(dict):
    """A dictionary that's recursively navigable with dots, not brackets.

Usage examples:

d = {'key1': 'value1',
     'key2': 'value2',
     'key3': {'key3a': 'value3a'},
     'key4': {'key4a': [{'key4aa': 'value4aa',
                         'key4ab': 'value4ab',
                         'key4ac': 'value4ac'}],
              'key4b': 'value4b'}}

dd = DotDict(d)
print(dd.key4.key4a[0].key4aa)  # value4aa
dd.key4.key4a[0].key4aa = 'newval'
print(dd.key4.key4a[0].key4aa)  # newval

print(dd.key4.key4a[0].key4aaa) # AttributeError: attribute .key4aaa not found
DotDict({}) # AttributeError: DotDict must be instantiated with a non-empty dictionary.
DotDict()   # AttributeError: DotDict must be instantiated with a non-empty dictionary.

Source: https://stackoverflow.com/questions/22161876/python-getattr-and-setattr-with-self-dict/75561249#75561249
"""

    def __init__(self, data: dict = None):
        # super().__init__()
        if data is None or not isinstance(data, dict):
            raise AttributeError(f"{type(self).__name__} must be instantiated with a dictionary, not a {type(data).__name__}.")
        for key, value in data.items():
            if isinstance(value, list):
                self[key] = [DotDict(item) for item in value]
            elif isinstance(value, dict):
                self[key] = DotDict(value)
            else:
                self[key] = value

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"attribute .{key} not found")


def get_conf():
    """A convenience function to parse a hardcoded conf file"""
    conf = ConfigParser()
    conf.read('config.toml')
    return DotDict(
        vars(conf)['_sections']
    )


conf = get_conf()


async def reply_with_text_only(message: telebot.types.Message,
                               transformed_text: str,
                               original_text: str,
                               jl: JournalLogger,
                               bot: telebot.async_telebot.AsyncTeleBot) -> None:
    if transformed_text == original_text:
        jl.print(
            f"do not send reply: transformed text ({transformed_text!r}) is identical to the original text ({original_text!r})")
        return
    await bot.reply_to(
        message, transformed_text,
        disable_web_page_preview=False,
        disable_notification=True,
        allow_sending_without_reply=True
    )


async def reply_with_video(message: telebot.types.Message,
                            ret: dict | DotDict,
                            jl: JournalLogger,
                            bot: telebot.async_telebot.AsyncTeleBot) -> None:
    with open(file=ret.abs_path_to_media, mode='rb') as videofile_bytes:
        await bot.send_chat_action(chat_id=message.chat.id, action='upload_video', timeout=60)
        await bot.send_video(
            reply_to_message_id=message.message_id,
            chat_id=message.chat.id,
            video=videofile_bytes,
            thumb=ret.dl_info.thumbnail,
            caption='\n'.join([
                ret.clean_url,
                build_caption(ret.dl_info)
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
            return '\n'.join([dl_info[fn] for fn in field_names])
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
            clean_url = dl_info.webpage_url
            return {'abs_path_to_media': abs_path_to_media,
                    'clean_url': dl_info.webpage_url,
                    'dl_info': dl_info}
        except Exception as e:
            jl.print(e)
    except Exception as e:
        jl.print("download process has not finished properly")
        jl.print(e)
        return None
    return None
