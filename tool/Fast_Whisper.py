import os

from faster_whisper import WhisperModel


def stt(model_path, input_path, output_path):
    # 获取音频文件名（不包括后缀）
    audio_file_name = os.path.splitext(os.path.basename(input_path))[0]
    print(audio_file_name)
    # 拼接txt文件路径
    txt_file_path = os.path.join(output_path, f"{audio_file_name}.txt")
    print(txt_file_path)
    os.makedirs(output_path, exist_ok=True)
    # 创建txt文件（如果不存在）
    if not os.path.exists(txt_file_path):
        with open(txt_file_path, 'w', encoding='utf-8'):
            pass  # 创建一个空文件

    # 运行语音识别模型
    model = WhisperModel(model_size_or_path=model_path, device="cuda", local_files_only=True)
    segments, info = model.transcribe(input_path, beam_size=5, language="zh", vad_filter=True,
                                      vad_parameters=dict(min_silence_duration_ms=1000))

    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    # 将识别的内容写入txt文件
    with open(txt_file_path, 'a', encoding='utf-8') as txt_file:
        for segment in segments:
            txt_file.write("[%.2fs -> %.2fs] %s\n" % (segment.start, segment.end, segment.text))

    print(f"识别结果已保存在文件：{txt_file_path}")

def stt_for_llm(model_path, input_path):
    # 获取音频文件名（不包括后缀）
    audio_file_name = os.path.splitext(os.path.basename(input_path))[0]
    print(audio_file_name)
    # 运行语音识别模型
    model = WhisperModel(model_size_or_path=model_path, device="cuda", local_files_only=True)
    segments, info = model.transcribe(input_path, beam_size=5, language="zh", vad_filter=True,
                                      vad_parameters=dict(min_silence_duration_ms=1000))
    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
    result = ""
    # 将识别的内容写入txt文件
    for segment in segments:
        result += (segment.text+",")
    print(result)
    return result

def v3_test():
    model = WhisperModel("../faster-whisper-webui/Models/faster-whisper/large-v3")

    segments, info = model.transcribe(r"C:\Users\32873\Desktop\ai\AI-Vtuber\AI-Vtuber_huan\download\我不曾忘记-花玲.wav")
    for segment in segments:
        print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

if __name__ == '__main__':
    #stt(model_path="../faster-whisper-webui/Models/faster-whisper/large-v2",input_path=r"C:\Users\32873\Desktop\ai\AI-Vtuber\AI-Vtuber_huan\download\1001夜-KBShinya.wav",output_path="./")
    stt_for_llm(model_path="../faster-whisper-webui/Models/faster-whisper/large-v2",input_path=r"C:\Users\32873\Desktop\ai\AI-Vtuber\AI-Vtuber_huan\download\1001夜-KBShinya.wav")
    #v3_test()