from func.stt.Fast_Whisper import stt_from_txt
import requests
#stt_from_txt(model_path="runtime/pretrained_models/faster-whisper/large-v2",input_path=r"C:\Users\32873\Desktop\【幻】我会等.mp4",output_path="template/stt")

data = {"input_path":r"C:\Users\32873\Desktop\【幻】你的声音.mp4"}
res = requests.post(f'http://localhost:9550/tool/faster_whisper', json=data)
print(res.json()["text"])

# import requests
#
# # Flask应用程序的URL
# URL = 'http://localhost:9550/upload_audio'
#
# # 要上传的文件的路径
# file_path = r"C:\Users\32873\Desktop\【幻】怪物 (Monster).mp4"
#
# # 指定文件和文件名
# files = {'audio_file': ('【幻】怪物 (Monster).mp4', open(file_path, 'rb'))}
#
# # 发送POST请求
# response = requests.post(URL, files=files)
#
# # 打印响应内容
# print(response.status_code)
# print(response.json())

# url="https://www.bilibili.com/video/BV11i421k74Z"
# from func.download.download_from_url import download_audio_from_url,download_video_from_url
# downloaded_files = download_audio_from_url(
#     url=url,  # 要下载的视频的URL
#     destinationDirectory="template/downloads",  # 下载文件的保存目录
#     playlistItems="1"  # 下载播放列表中的特定项目，"1" 表示第一个视频
# )
#filenames = download_video_from_url(url=url,destinationDirectory="template/downloads")
