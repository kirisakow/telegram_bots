from configparser import ConfigParser
from cysystemd import journal
import httpx
import inspect
import logging
import re
import subprocess
import sys
import types
import urllib.parse

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
        if not data or data is None or not isinstance(data, dict):
            raise AttributeError(f"{type(self).__name__} must be instantiated with a non-empty dictionary.")
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
