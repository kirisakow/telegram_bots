BOT_NAME = 'extractYouTubeSubtitlesBot'

def extract_video_id(url_or_id):
    """Take the 11 rightmost characters, which is the YouTube video ID"""
    return url_or_id[-11:]
