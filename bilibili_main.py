import asyncio
import datetime
import json
import os
import queue
import shutil
import subprocess
import threading
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from flask_apscheduler import APScheduler
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import utils

# 配置文件初始化


project_root = os.path.dirname(os.path.abspath(__file__))


file_lock = threading.Lock()
QuestionList = queue.Queue(10)
QuestionName = queue.Queue(10)
AnswerList = queue.Queue()
tts_playList = queue.Queue()
song_lst = queue.Queue()
song_playList = queue.Queue()
song_search_playList = queue.Queue()
EmoteList = queue.Queue()
LogsList = queue.Queue()
web_captions_printer = queue.Queue()
find_wav_lst = []
history = []

if_check_blivedm_api_get = False

hps = utils.get_hparams_from_file('configs/json/config.json')
role_language_model = hps.ai_vtuber.language_model
role_speech_model = hps.ai_vtuber.speech_model
if_easy_ai_vtuber = hps.ai_vtuber.if_easy_ai_vtuber
if_agent = hps.ai_vtuber.if_agent
is_ai_ready = hps.bilibili.is_ai_ready
is_tts_ready = hps.bilibili.is_tts_ready
is_tts_play_ready = hps.bilibili.is_tts_play_ready
is_song_play_ready = hps.bilibili.is_song_play_ready
is_song_cover_ready = hps.bilibili.is_song_cover_ready
is_obs_ready = hps.bilibili.is_obs_ready
is_obs_play_ready = hps.bilibili.is_obs_play_ready
is_web_captions_printer_ready = hps.bilibili.is_web_captions_printer_ready
web_captions_printer_port = hps.api_path.web_captions_printer.port
easy_ai_vtuber_url = hps.api_path.easy_ai_vtuber.url
AudioCount = 0
AudioPlay = 0

sched1 = AsyncIOScheduler(timezone="Asia/Shanghai")
app = Flask(__name__)
CORS(app)

# 文件夹初始化
if os.path.exists(os.path.join(project_root, "song_output")):
    shutil.rmtree(os.path.join(project_root, "song_output"))
if os.path.exists(os.path.join(project_root, "logs/danmu")):
    shutil.rmtree(os.path.join(project_root, "logs/danmu"))
output_dir = "template/logs/danmu"
os.makedirs(os.path.join(project_root, "template/logs/danmu"), exist_ok=True)

@app.route('/AI_VTuber/DANMU_MSG',methods=['POST'])
def information_show():
    DANMU_response = request.json
    user_name = DANMU_response["audience_name"]
    content = DANMU_response["DANMU_MSG"]
    QuestionName.put(user_name)  # 将用户名放入队列
    QuestionList.put(content)  # 将弹幕消息放入队列
    time1 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LogsList.put(f"[{time1}] [{user_name}]：{content}")
    print(f"\033[35m[{time1}] [{user_name}]：{content}\033[0m")
    print("\033[32mSystem>>\033[0m已将该条弹幕添加入问题队列")
    return {"statue_code":200}

def Classifiers(content):
    """
    分类器:会根据弹幕的内容进行不同功能的使用
    #聊天:返回值为-1，表示为聊天任务
    #画画:返回值为1，表示为正常的功能调用，后面跟上提示词，对接sd-api
    #点歌:返回值为1，表示为正常的功能调用，拥有#点歌0+歌曲和#点歌1+bv号两种点歌方式
    #翻唱:返回值为1，表示为正常的功能调用，使用方式为先输入#翻唱获取翻唱列表，再输入#翻唱+序号来翻唱对应的歌
    #唱歌:返回值为1，表示为正常的功能调用，需要配合#命令来使用。#唱歌+你想搜索的音乐特征（为歌库.csv中储存的第一行标签，只要是你填写过的一般都可以。）
    #命令:返回值为1，表示为正常的功能调用，需要配合#唱歌来使用。用来选择#唱歌中搜索到的具体音乐。可以选择单选，也可以多选如:#序号0，1，3，4，7-16，18
    #复读:返回值为1，表示为正常的功能调用，复读后面的内容，一般用来测试语音模块。
    #播放列表:返回值为1，表示为正常的功能调用，可以打印之后将要播放的歌曲名称（包括点歌和唱歌两个功能的），不过不能显示正在播放的歌名。
    其余弹幕，返回值为0，会被过滤掉。
    :param content:
    :return:
    """
    global songlist,song_lst
    if content[0:3] == "#聊天":
        return -1

    elif content[0:3] == "#复读":
        AnswerList.put(content[3:])
        return 1

    elif content[0:5] == "#播放列表":
        current_songs = list(song_lst.queue)
        print("播放列表:",current_songs)
        with file_lock:
            with open('configs/config.json', encoding="utf-8", mode='r') as config_file:
                config_data = json.load(config_file)
            config_data["songlist"] = current_songs
        current_songs_str = ",".join(current_songs)
        web_captions_printer.put("播放列表:"+current_songs_str)
        with file_lock:
            with open('configs/config.json', 'w', encoding='utf-8') as config_file:
                json.dump(config_data, config_file, indent=4, ensure_ascii=False)
        return 1

# llm线程
async def check_answer():
    """
    如果AI没有在生成回复且队列中还有问题 则创建一个生成的线程
    :return:
    """
    global is_ai_ready
    if not QuestionList.empty() and is_ai_ready:
        is_ai_ready = 0
        answers_thread = threading.Thread(target=lambda: ai_response())
        answers_thread.start()

def ai_response():
    """
    提取问题中是否存在会影响到主播情绪变化的关键词，获取该关键词的信息并计算变换后的情绪值。提供一个角色信息字典给llm参考并回复，将得到的回复内容进行临时存储并存入语音合成队列
    :return:
    """
    global is_ai_ready,emotion_state,emotion_score
    user_input = QuestionList.get()
    user_name = QuestionName.get()
    ques = LogsList.get()
    data_agent_to_do = {"content": user_input, "memory": True}
    res = requests.post(f'http://localhost:9550/agent_to_do', json=data_agent_to_do).json()
    bot_response = res.get("content")
    answer = f"回复{user_name}：{bot_response}"
    AnswerList.put(f"{user_input}" + "," + answer)
    current_question_count = QuestionList.qsize()
    print(f"\033[31m[AI-Vtuber]\033[0m{answer}")
    print(
        f"\033[32mSystem>>\033[0m[{user_name}]的回复已存入队列，当前剩余问题数:{current_question_count}"
    )
    time1 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with file_lock:
        with open("template/logs/logs.txt", "a", encoding="utf-8") as f:
            f.write(
                f"{ques}\n[{time1}] {answer}\n========================================================\n"
            )
    is_ai_ready = 1

# tts线程
async def check_tts():
    """
    如果语音已经放完且队列中还有回复 则创建一个合成TTS的线程
    :return:
    """
    global is_tts_ready,AudioCount
    if not AnswerList.empty() and is_tts_ready:
        text = AnswerList.get()
        is_tts_ready = 0
        tts_thread = threading.Thread(target=lambda: tts_main(text))
        tts_thread.start()

def tts_main(text):
    '''
    当前支持
    1.edge-tts+svc -> so-vits-svc
    2.gpt-sovits
    3.bert-vits2
    :param text: 需要合成的文本

    '''
    # 创建输出文件夹
    global AudioCount,is_tts_ready
    tts_plan = 1
    if role_speech_model == "edge-tts+svc":
        tts_plan = 1
    elif role_speech_model == "gpt-sovits":
        tts_plan = 2
    elif role_speech_model == "bert-vits2":
        tts_plan = 3
    data_tts = {"tts_plan": tts_plan, "text": text, "AudioCount": AudioCount}
    tts_path = requests.post('http://localhost:9550/tts', json=data_tts).json()["path"]
    tts_playList.put(tts_path)
    is_tts_ready = 1
    web_captions_printer.put(text)
    AudioCount += 1

async def check_tts_play():
    """
    若已经播放完毕且播放列表中有数据 则创建一个播放tts音频的线程
    :return:
    """
    global is_tts_play_ready,is_song_play_ready,if_easy_ai_vtuber
    if not tts_playList.empty() and is_tts_play_ready and is_song_play_ready:
        is_tts_play_ready = 0
        wav_path = tts_playList.get()
        if not if_easy_ai_vtuber:
            tts_thread = threading.Thread(target=lambda: mpv_play(wav_path) , daemon=True)
            tts_thread.start()
        else:
            easy_ai_vtuber_thread = threading.Thread(
                target=lambda: to_easy_ai_vtuber_api(
                    "speak",wav_path), daemon=False)
            easy_ai_vtuber_thread.start()


def mpv_play(path):
    """
    播放tts音频
    :param path: 音频路径
    :return:
    """
    duration = utils.get_duration_ffmpeg(path)
    global is_tts_play_ready
    # end:播放多少秒结束  volume：音量，最大100，最小0
    subprocess.run(
        f'mpv.exe -vo null --volume=100 --start=0 --end={duration} "{path}" 1>nul',
        shell=False,
    )
    is_tts_play_ready = 1
    return

def to_easy_ai_vtuber_api(type,path):
    global is_tts_play_ready,is_song_play_ready,is_song_cover_ready
    data = {}
    if type == "speak":
        data = {
            "type": type,  # 说话动作
            "speech_path": path  # 语音音频路径
        }
    elif type == "rhythm":
        data = {
            "type": type,  # 节奏摇动作
            "music_path": path  # 歌曲音频路径
        }
    elif type == "sing":
        data = {
            "type": "sing",
            "music_path": path,  # 修改为原曲路径
            "voice_path": path,  # 修改为人声音频路径
            "mouth_offset": 0.0
        }
    response = requests.post(easy_ai_vtuber_url, json=data)
    if response.status_code == 200:
        print("\033[31measy_ai_vtuber_api请求成功\033[0m")
    is_tts_play_ready = 1
    is_song_play_ready = 1
    is_song_cover_ready = 1

def app_server():
    app.run(host="0.0.0.0", port=9551)

async def main():
    app_thread = threading.Thread(target=app_server)
    app_thread.start()
    # 添加定时任务
    sched1.add_job(check_answer, "interval", seconds=1, id="llm_answer", max_instances=1)
    sched1.add_job(check_tts, "interval", seconds=1, id="tts", max_instances=4)
    sched1.add_job(check_tts_play, "interval", seconds=1, id="tts_play", max_instances=1)

    # 启动调度器
    sched1.start()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        # 关闭调度器
        sched1.shutdown()


if __name__ == '__main__':
    asyncio.run(main())