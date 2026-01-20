from configparser import ConfigParser
from dot_dict.dot_dict import DotDict

BOT_NAME = 'extractYouTubeSubtitlesBot'

def get_conf():
    """A convenience function to parse a hardcoded conf file"""
    conf = ConfigParser()
    conf.read('config.toml')
    return DotDict(
        conf.__dict__['_sections']
    )

