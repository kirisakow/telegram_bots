from configparser import ConfigParser
import httpx
import subprocess
import types


async def unescape_url(url: str) -> str | None:
    response_obj = httpx.get(
        f'https://crac.ovh/unescape_url/{url}'
    )
    unescaped_url = response_obj.text
    return unescaped_url


def get_target_url(url: str) -> str:
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


# Source: https://stackoverflow.com/questions/22161876/python-getattr-and-setattr-with-self-dict/74224889#74224889
class DotDict(dict):
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
    conf = ConfigParser()
    conf.read('config.toml')
    # return conf
    return DotDict(
        vars(conf)['_sections']
    )


conf = get_conf()
