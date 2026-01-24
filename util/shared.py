import configparser
from dot_dict.dot_dict import DotDict


def get_conf(bot_name: str):
    """A convenience function to parse a hardcoded conf file"""
    conf = configparser.ConfigParser()
    conf.read('config.toml')
    return DotDict(
        conf.__dict__['_sections'][bot_name]
    )
