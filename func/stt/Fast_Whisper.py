import os
from faster_whisper import WhisperModel

def format_time(seconds):
    # 将秒转换为分钟和秒
    minutes, seconds = divmod(seconds, 60)
    # 格式化时间戳为[分钟:秒.毫秒]的格式
    return "[%02d:%06.3f]" % (minutes, seconds)

def stt_from_txt(model_path, input_path, output_path,language=None):
    # 获取音频文件名（不包括后缀）
    audio_file_name = os.path.splitext(os.path.basename(input_path))[0]
    print("\033[31m"+audio_file_name+"\033[0m")
    # 拼接txt文件路径
    txt_file_path = os.path.join(output_path, f"{audio_file_name}.txt")
    os.makedirs(output_path, exist_ok=True)
    # 创建txt文件（如果不存在）
    if not os.path.exists(txt_file_path):
        with open(txt_file_path, 'w', encoding='utf-8'):
            pass  # 创建一个空文件
    text_list = []
    # 运行语音识别模型
    model = WhisperModel(model_size_or_path=model_path, device="cuda", local_files_only=True)
    segments, info = model.transcribe(input_path, beam_size=5, language=language, vad_filter=True,
                                      vad_parameters=dict(min_silence_duration_ms=1000))

    print("\033[32mDetected language '%s' with probability %f\033[0m" % (info.language, info.language_probability))
    # 将识别的内容写入txt文件
    with open(txt_file_path, 'a', encoding='utf-8') as txt_file:
        for segment in segments:
            formatted_time = format_time(segment.start)
            text_line = "%s %s\n" % (formatted_time, segment.text)
            text_list.append(text_line)
            txt_file.write(text_line)
            print("\033[33m"+text_line+"\033[0m")
    print(f"识别结果已保存在文件：{txt_file_path}")
    return text_list,txt_file_path

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