import threading
import requests
import edge_tts
import wave
import subprocess
import os

import utils

project_root = os.path.dirname(os.path.abspath(__file__))
file_lock = threading.Lock()

def merge_audio_files(output_path, *input_paths):
    """
    :param output_path: 输出文件路径
    :param input_paths: 输入文件夹的所有音频片段
    """
    output_file = wave.open(output_path, 'wb')
    with wave.open(input_paths[0], 'rb') as input_file:
        output_file.setparams(input_file.getparams())
        output_file.writeframes(input_file.readframes(input_file.getnframes()))
    for input_path in input_paths[1:]:
        with file_lock:
            with wave.open(input_path, 'rb') as input_file:
                if input_file.getparams() != output_file.getparams():
                    raise ValueError("所有输入文件的参数必须相同")
                output_file.writeframes(input_file.readframes(input_file.getnframes()))
    output_file.close()


def bert_vits2_api(text, output_path):
    '''

    :param text: 需要合成的文本
    :param output_path: 合成音频的保存路径

    '''
    hps = utils.get_hparams_from_file("configs/config.json")
    flask_url = hps.api_path.bert_vits2.url
    params = {
        "speaker": hps.api_path.bert_vits2.speaker,
        "text": text,
        "sdp_ratio": hps.api_path.bert_vits2.sdp_ratio,
        "noise": hps.api_path.bert_vits2.noise,
        "noisew": hps.api_path.bert_vits2.noisew,
        "length": hps.api_path.bert_vits2.length,
        "language": hps.api_path.bert_vits2.language,
        "format": hps.api_path.bert_vits2.format,
    }
    response = requests.get(f"{flask_url}/", params=params)
    if response.status_code == 200:
        audio_data = response.content
        with file_lock:
            with open(output_path+"\output.wav", "wb") as audio_file:
                audio_file.write(audio_data)
        print("音频已下载到", output_path)
    else:
        print("请求失败，状态码：", response.status_code)
        print("响应内容：", response.text)

async def process_text_file(text, output_folder,AudioCount):
    '''
    将edge-tts合成的mp3文件转换成wav格式，方便so-vits-svc进行转换
    :param text: 需要edge-tts合成的文本
    :param output_folder:
    :param AudioCount: 记录正在合成第几个音频

    '''
    voice = "zh-CN-XiaoyiNeural"
    rate = "-4%"
    volume = "+0%"
    mp3_output_path = os.path.join(output_folder, f'{AudioCount}.mp3')
    wav_output_path = os.path.join(output_folder, f'{AudioCount}.wav')
    tts = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
    await tts.save(mp3_output_path)
    subprocess.run(['ffmpeg', '-y', '-i', mp3_output_path, wav_output_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def to_gpt_sovits_api(text,output_folder,AudioCount):
    hps = utils.get_hparams_from_file("configs/config.json")
    wav_output_path = os.path.join(output_folder, f'{AudioCount}.wav')
    url = hps.api_path.gpt_sovits.url
    params = {
        "refer_wav_path": hps.api_path.gpt_sovits.refer_wav_path,
        "prompt_text": hps.api_path.gpt_sovits.prompt_text,
        "prompt_language": hps.api_path.gpt_sovits.prompt_language,
        "text": text,
        "text_language": hps.api_path.gpt_sovits.text_language
    }
    response = requests.get(url, params)
    if response.status_code == 200:
        with open(wav_output_path, "wb") as f:
            f.write(response.content)
        print("INFO 响应成功")
