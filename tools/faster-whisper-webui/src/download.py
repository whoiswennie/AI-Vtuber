from tempfile import mkdtemp
from typing import List
from yt_dlp import YoutubeDL

import yt_dlp
from yt_dlp.postprocessor import PostProcessor

class FilenameCollectorPP(PostProcessor):
    def __init__(self):
        super(FilenameCollectorPP, self).__init__(None)
        self.filenames = []

    def run(self, information):
        self.filenames.append(information["filepath"])
        return [], information

def download_url(url: str, maxDuration: int = None, destinationDirectory: str = None, playlistItems: str = "1") -> List[str]: 
    try:
        return _perform_download(url, maxDuration=maxDuration, outputTemplate=None, destinationDirectory=destinationDirectory, playlistItems=playlistItems)
    except yt_dlp.utils.DownloadError as e:
        # In case of an OS error, try again with a different output template
        if e.msg and e.msg.find("[Errno 36] File name too long") >= 0:
            return _perform_download(url, maxDuration=maxDuration, outputTemplate="%(title).10s %(id)s.%(ext)s")
        pass

def _perform_download(url: str, maxDuration: int = None, outputTemplate: str = None, destinationDirectory: str = None, playlistItems: str = "1"):
    # Create a temporary directory to store the downloaded files
    if destinationDirectory is None:
        destinationDirectory = mkdtemp()

    ydl_opts = {
        "format": "bestaudio/best",
        'paths': {
            'home': destinationDirectory
        }
    }
    if (playlistItems):
        ydl_opts['playlist_items'] = playlistItems

    # Add output template if specified
    if outputTemplate:
        ydl_opts['outtmpl'] = outputTemplate

    filename_collector = FilenameCollectorPP()

    with YoutubeDL(ydl_opts) as ydl:
        if maxDuration and maxDuration > 0:
            info = ydl.extract_info(url, download=False)
            entries = "entries" in info and info["entries"] or [info]

            total_duration = 0

            # Compute total duration
            for entry in entries:
                total_duration += float(entry["duration"])

            if total_duration >= maxDuration:
                raise ExceededMaximumDuration(videoDuration=total_duration, maxDuration=maxDuration, message="Video is too long")

        ydl.add_post_processor(filename_collector)
        ydl.download([url])

    if len(filename_collector.filenames) <= 0:
        raise Exception("Cannot download " + url)

    result = []

    for filename in filename_collector.filenames:
        result.append(filename)
        print("Downloaded " + filename)

    return result 

class ExceededMaximumDuration(Exception):
    def __init__(self, videoDuration, maxDuration, message):
        self.videoDuration = videoDuration
        self.maxDuration = maxDuration
        super().__init__(message)