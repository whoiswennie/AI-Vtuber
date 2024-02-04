import threading
import utils
import requests
import os
project_root = os.path.dirname(os.path.abspath(__file__))
file_lock = threading.Lock()

def request_api(audio_path,AudioCount):
    # 服务端口和地址
    hps = utils.get_hparams_from_file("configs/config.json")
    url = hps.api_path.so_vits_svc.url
    tran = hps.api_path.so_vits_svc.tran
    spk = hps.api_path.so_vits_svc.spk
    wav_format = hps.api_path.so_vits_svc.wav_format
    # 请求参数
    data = {
        'audio_path': audio_path,
        'tran': tran,  # 你的音调值
        'spk': spk,  # 你的说话人信息
        'wav_format': wav_format  # 输出文件格式
    }
    # 发送请求
    response = requests.post(url, data=data)
    # 检查请求是否成功
    if response.status_code == 200:
        # 将响应保存为文件
        with file_lock:
            with open(os.path.join(project_root, f"song_output/{AudioCount}.wav"), 'wb') as f:
                f.write(response.content)
    else:
        print('请求失败，状态码:', response.status_code)
        print('响应内容:', response.text)

def Svc():
    # 服务端口和地址
    song_path = os.path.join(project_root, f"output/template_upload/wav_vocal.wav")
    hps = utils.get_hparams_from_file("configs/config.json")
    url = hps.api_path.so_vits_svc.url
    tran = hps.api_path.so_vits_svc.tran
    spk = hps.api_path.so_vits_svc.spk
    wav_format = hps.api_path.so_vits_svc.wav_format
    # 请求参数
    data = {
        'audio_path': song_path,
        'tran': tran,  # 你的音调值
        'spk': spk,  # 你的说话人信息
        'wav_format': wav_format  # 输出文件格式
    }
    # 发送请求
    response = requests.post(url, data=data)
    # 检查请求是否成功
    if response.status_code == 200:
        # 将响应保存为文件
        with file_lock:
            with open(os.path.join(project_root, f"output/template_upload/svc.wav"), 'wb') as f:
                f.write(response.content)
    else:
        print('请求失败，状态码:', response.status_code)
        print('响应内容:', response.text)
