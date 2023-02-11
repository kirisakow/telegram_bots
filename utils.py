from configparser import ConfigParser
import httpx
import re
import subprocess
import types


def unquote_str_if_quoted(possibly_quoted_string: str) -> str:
    """Unquote a possibly quoted string, like a JSON response"""
    return re.sub(r'^"(.*)"$', "\\1", possibly_quoted_string, 1)


async def unescape_url(url: str) -> str:
    resp = httpx.get(
        f'https://crac.ovh/unescape_url?url={url}'
    )
    if resp.status_code != httpx.codes.OK:
        status_code_and_name = f"{resp.status_code} {httpx.codes(resp.status_code).name}"
        return status_code_and_name.replace('_', ' ')
    unescaped_url = unquote_str_if_quoted(resp.text)
    return unescaped_url


def get_destination_url(url: str) -> str:
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
        print(err_as_bytes)
    return output_as_bytes.decode()


def url_clean(url: str) -> str:
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
        print(err_as_bytes)
    return output_as_bytes.decode()


class DotDict(dict):
    """A dictionary that's navigable with dots, not brackets: `my_dict.key1.value`.

Source: https://stackoverflow.com/questions/22161876/python-getattr-and-setattr-with-self-dict/74224889#74224889
"""

    def __init__(self, d: dict = None):
        super().__init__()
        if d in (None, {}):
            raise ValueError(
                "DotDict cannot be instantiated with an empty dictionary")
        for key, value in d.items():
            self[key] = DotDict(value) if type(value) is dict else value

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(key)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def get_conf():
    """A convenience function to parse a hardcoded conf file"""
    conf = ConfigParser()
    conf.read('config.toml')
    return DotDict(
        vars(conf)['_sections']
    )


conf = get_conf()
