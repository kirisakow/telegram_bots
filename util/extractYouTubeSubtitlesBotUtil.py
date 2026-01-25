from typing import Union
from urllib.parse import urlparse, parse_qs
import re

BOT_NAME = 'extractYouTubeSubtitlesBot'


def extract_video_id(url_or_id: str) -> Union[str, None]:
    """Extract video ID from various YouTube URL formats."""
    id = None
    if len(url_or_id) == 11 and re.match(r'^[A-Za-z0-9_-]+$', url_or_id):
        id = url_or_id
    else:
        if re.search(r'^https?://', url_or_id) is None:
            url_or_id = f'https://{url_or_id}'
        parsed = urlparse(url_or_id)
        if parsed.hostname.endswith('youtu.be'):
            path = parsed.path.lstrip('/')
            id = path if len(path) == 11 else id
        elif parsed.hostname.endswith('youtube.com'):
            v_value = parse_qs(parsed.query).get('v', [None])[0]
            id = v_value if v_value and len(v_value) == 11 else id
    return id
