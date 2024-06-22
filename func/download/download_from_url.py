import os
import subprocess
from tempfile import mkdtemp
from typing import List
from yt_dlp import YoutubeDL
import yt_dlp

class FilenameCollectorPP(yt_dlp.postprocessor.PostProcessor):
    """
    用于收集下载的文件名的后处理器类
    """
    def __init__(self):
        super(FilenameCollectorPP, self).__init__(None)
        self.filenames = []

    def run(self, information):
        """
        执行后处理并收集文件名
        """
        self.filenames.append(information["filepath"])
        return [], information

class ExceededMaximumDuration(Exception):
    """
    视频时长超过允许的最大值时引发的异常类
    """
    def __init__(self, videoDuration, maxDuration, message):
        self.videoDuration = videoDuration
        self.maxDuration = maxDuration
        super().__init__(message)

def download_audio_from_url(url: str, maxDuration: int = None, destinationDirectory: str = None, playlistItems: str = "1") -> List[str]:
    """
    下载指定 URL 的音频文件

    Args:
        url: 音频文件的 URL
        maxDuration: 允许的最大时长（秒）
        destinationDirectory: 下载文件的目标目录
        playlistItems: 指定下载的播放列表项（默认为第一项）

    Returns:
        下载完成的音频文件名列表
    """
    try:
        return _perform_download(url, maxDuration=maxDuration, outputTemplate=None,
                                 destinationDirectory=destinationDirectory, playlistItems=playlistItems, is_audio=True)
    except yt_dlp.utils.DownloadError as e:
        # In case of an OS error, try again with a different output template
        if e.msg and e.msg.find("[Errno 36] File name too long") >= 0:
            return _perform_download(url, maxDuration=maxDuration, outputTemplate="%(title).10s %(id)s.%(ext)s",
                                     destinationDirectory=destinationDirectory, playlistItems=playlistItems, is_audio=True)
        pass

def download_video_from_url(url: str, maxDuration: int = None, destinationDirectory: str = None, playlistItems: str = "1", merge: bool = False) -> List[str]:
    """
    下载指定 URL 的视频文件

    Args:
        url: 视频文件的 URL
        maxDuration: 允许的最大时长（秒）
        destinationDirectory: 下载文件的目标目录
        playlistItems: 指定下载的播放列表项（默认为第一项）
        merge: 是否合并视频和音频文件（默认为 False）

    Returns:
        下载完成的视频文件名列表
    """
    try:
        return _perform_download(url, maxDuration=maxDuration, outputTemplate=None,
                                 destinationDirectory=destinationDirectory, playlistItems=playlistItems, is_audio=False, merge=merge)
    except yt_dlp.utils.DownloadError as e:
        # Handle errors
        pass

def _perform_download(url: str, maxDuration: int = None, outputTemplate: str = None, destinationDirectory: str = None, playlistItems: str = "1", is_audio: bool = False, merge: bool = False):
    # Create a temporary directory to store the downloaded files
    if destinationDirectory is None:
        destinationDirectory = mkdtemp()

    ydl_opts = {
        "format": "bestaudio/best" if is_audio else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        'paths': {
            'home': destinationDirectory
        }
    }
    if (playlistItems):
        ydl_opts['playlist_items'] = playlistItems

    # Specify audio format as WAV if downloading audio
    if is_audio:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }]

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
                raise ExceededMaximumDuration(videoDuration=total_duration, maxDuration=maxDuration, message="视频太长")

        ydl.add_post_processor(filename_collector)
        ydl.download([url])

    if len(filename_collector.filenames) <= 0:
        raise Exception("无法下载 " + url)

    result = []

    for filename in filename_collector.filenames:
        result.append(filename)
        print("下载完成 " + filename)

    if is_audio and merge:
        # Merge audio and video using ffmpeg
        for filename in result:
            audio_filename = filename.split(".")[0] + ".wav"  # Specify audio format as WAV
            output_filename = os.path.splitext(filename)[0] + "_merged.mp4"
            merge_command = ["ffmpeg", "-i", filename, "-i", audio_filename, "-c", "copy", output_filename]
            subprocess.run(merge_command, check=True)
            # Clean up audio file
            os.remove(audio_filename)
            # Update result list with merged filename
            result[result.index(filename)] = output_filename

    return result



if __name__ == '__main__':
    url = "https://www.bilibili.com/video/BV1Pm421u7x2"

    #下载音频（wav）
    downloaded_files = download_audio_from_url(
        url=url,  # 要下载的视频的URL
        destinationDirectory="../../template/downloads",  # 下载文件的保存目录
        playlistItems="1"  # 下载播放列表中的特定项目，"1" 表示第一个视频
    )
    #下载视频（mp4）
    # filenames = download_video_from_url(url=url, destinationDirectory="../../template/downloads")
    # print(filenames)