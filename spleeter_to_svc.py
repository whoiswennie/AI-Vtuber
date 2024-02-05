import argparse
import glob
import svc_api_request
import os
from pydub import AudioSegment

import utils


def sing_for_svc(song_name):
    hps = utils.get_hparams_from_file("configs/config.json")
    selected_model = hps.api_path.uvr5.model
    # 构建完整的命令
    # command = f"python -m spleeter separate -p spleeter:2stems -o output template/{song_name}.wav" 已废弃
    command = rf'python spleeter_to_svc.py -ap "download/{song_name}.wav" -sp "output/template_upload" -mp "pretrained_models/uvr5/models/Main_Models/{selected_model}"'
    # 执行命令
    os.system(command)
    svc_api_request.Svc()
    # 读取人声和伴奏音频文件
    vocal_file = f"output/template_upload/svc.wav"
    instrumental_file = f"output/template_upload/wav_instrument.wav"
    # 加载人声和伴奏音频
    vocal = AudioSegment.from_file(vocal_file)
    instrumental = AudioSegment.from_file(instrumental_file)
    # 确保两个音频文件具有相同的采样率和通道数
    vocal = vocal.set_frame_rate(instrumental.frame_rate)
    vocal = vocal.set_channels(instrumental.channels)
    # 将人声和伴奏音频混合在一起
    merged_audio = vocal.overlay(instrumental)
    # 保存合并后的音频文件
    output_file = f"download/output.wav"
    merged_audio.export(output_file, format="wav")
    return output_file

def to_uvr5(audio_path,save_path,model_path):
    import inference_demo as uvr5
    uvr5.vocal_separation(audio_path,save_path,model_path)

def vocal_svc():
    svc_api_request.Svc()
    # 读取人声和伴奏音频文件
    vocal_file = f"output/template_upload/svc.wav"
    instrumental_file = f"output/template_upload/wav_instrument.wav"

    # 加载人声和伴奏音频
    vocal = AudioSegment.from_file(vocal_file)
    instrumental = AudioSegment.from_file(instrumental_file)

    # 确保两个音频文件具有相同的采样率和通道数
    vocal = vocal.set_frame_rate(instrumental.frame_rate)
    vocal = vocal.set_channels(instrumental.channels)

    # 将人声和伴奏音频混合在一起
    merged_audio = vocal.overlay(instrumental)

    # 保存合并后的音频文件
    output_file = f"output/template_upload/output.wav"
    merged_audio.export(output_file, format="wav")
    return output_file

def find_wav(folder_path="download"):
    # 使用 glob 模块匹配文件夹内的所有 WAV 文件
    wav_files = glob.glob(f"{folder_path}/*.wav")
    song_list = []
    # 打印所有匹配到的 WAV 文件路径
    for id,file in enumerate(wav_files):
        file_name = os.path.splitext(os.path.basename(file))[0]
        print(f"序号{id}:",file_name)
        song_list.append(file_name)
    return song_list


if __name__ == '__main__':
    # 创建解析器对象
    parser = argparse.ArgumentParser(description='Process audio separation parameters')

    # 添加命令行参数
    parser.add_argument('-ap', '--audio_path', type=str, help='Path to the audio file')
    parser.add_argument('-sp', '--save_path', type=str, help='Path to save the separated audio file')
    parser.add_argument('-mp', '--model_path', type=str, default='./models/Main_Models/2_HP-UVR.pth',
                        help='Path to the model file')

    # 解析命令行参数
    args = parser.parse_args()

    # 获取解析后的参数值
    audio_path = args.audio_path
    save_path = args.save_path
    model_path = args.model_path
    #sing_for_svc("我不曾忘记-花玲")
    #to_uvr5("download/我不曾忘记-花玲.wav","output/template_upload","pretrained_models/uvr5/models/Main_Models/2_HP-UVR.pth")
    to_uvr5(audio_path,save_path,model_path)
    #find_wav()