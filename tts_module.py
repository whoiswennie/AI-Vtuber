import threading
import requests
import edge_tts
import wave
import subprocess
import os
project_root = os.path.dirname(os.path.abspath(__file__))
file_lock = threading.Lock()

def merge_audio_files(output_path, *input_paths):
    # 打开输出文件
    output_file = wave.open(output_path, 'wb')

    # 打开第一个输入文件并获取参数
    with wave.open(input_paths[0], 'rb') as input_file:
        output_file.setparams(input_file.getparams())

        # 写入第一个输入文件的数据
        output_file.writeframes(input_file.readframes(input_file.getnframes()))

    # 逐个打开其他输入文件并写入输出文件
    for input_path in input_paths[1:]:
        with file_lock:
            with wave.open(input_path, 'rb') as input_file:
                # 确保输入文件参数与输出文件参数相同
                if input_file.getparams() != output_file.getparams():
                    raise ValueError("所有输入文件的参数必须相同")

                # 追加输入文件的数据
                output_file.writeframes(input_file.readframes(input_file.getnframes()))

    # 关闭输出文件
    output_file.close()


def bert_vits2_api(text, output_path):
    # 设置Flask应用的URL
    flask_url = "http://127.0.0.1:5000"  # 请替换为你的Flask应用的URL
    # 提供的参数，根据你的需求进行设置
    params = {
        "speaker": "huan",
        "text": text,
        "sdp_ratio": 0.2,
        "noise": 0.5,
        "noisew": 0.6,
        "length": 1.2,
        "language": "ZH",
        "format": "wav",
    }

    # 发送GET请求到Flask应用
    response = requests.get(f"{flask_url}/", params=params)

    if response.status_code == 200:
        # 从响应中获取音频数据并保存到文件
        audio_data = response.content
        with file_lock:
            with open(output_path+"\output.wav", "wb") as audio_file:
                audio_file.write(audio_data)
        print("音频已下载到", output_path)
    else:
        print("请求失败，状态码：", response.status_code)
        print("响应内容：", response.text)

async def process_text_file(text, output_folder,AudioCount):
    voice = "zh-CN-XiaoyiNeural"
    rate = "-4%"
    volume = "+0%"
    mp3_output_path = os.path.join(output_folder, f'{AudioCount}.mp3')
    wav_output_path = os.path.join(output_folder, f'{AudioCount}.wav')

    # 使用edge-tts生成MP3文件
    tts = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
    await tts.save(mp3_output_path)

    # 使用FFmpeg转换为WAV文件
    subprocess.run(['ffmpeg', '-y', '-i', mp3_output_path, wav_output_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def to_gpt_sovits_api(text,output_folder,AudioCount):
    wav_output_path = os.path.join(output_folder, f'{AudioCount}.wav')
    #url = "http://127.0.0.1:8080"
    url = "http://127.0.0.1:9880"
    params = {
        "refer_wav_path": r"C:\Users\32873\Desktop\ai\tts\GPT-SoVITS-TTS\output\sanyueqi-撒娇.wav",
        "text": text,
        "text_language": "zh"
    }
    # 发送 GET 请求
    response = requests.get(url, params)
    # 检查响应状态码
    if response.status_code == 200:
        # 将音频流写入临时文件
        with open(wav_output_path, "wb") as f:
            f.write(response.content)
        print("INFO 响应成功")
