import asyncio
import datetime
import json
import os
import random
import time
import queue
import shutil
import subprocess
import threading

import requests

import make_song_n4j
import svc_api_request
import tts_module
import memory
import study_for_memory
import spleeter_to_svc
import plan_agency
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tool.search_for_song import search_in_wy, search_bilibili
from tool.send_to_web_captions_printer import send_to_web_captions_printer
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

danmu_count = 0

hps = utils.get_hparams_from_file('configs/config.json')
role_prompt = hps.ai_vtuber.setting
role_name = hps.ai_vtuber.name
role_sex = hps.ai_vtuber.sex
role_age = hps.ai_vtuber.age
emotion_score = hps.ai_vtuber.emotion
role_favorite_things = hps.ai_vtuber.favorite_things
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
AudioCount = hps.bilibili.AudioCount
AudioPlay = hps.bilibili.AudioPlay

sched1 = AsyncIOScheduler(timezone="Asia/Shanghai")

with open("configs/short_term_memory.json", "r", encoding="utf-8") as f:
    data = json.load(f)
data["short_term_memory"] = []
with open("configs/short_term_memory.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
# 文件夹初始化
if os.path.exists(os.path.join(project_root, "song_output")):
    shutil.rmtree(os.path.join(project_root, "song_output"))
if os.path.exists(os.path.join(project_root, "logs/danmu")):
    shutil.rmtree(os.path.join(project_root, "logs/danmu"))
output_dir = "logs/danmu"
os.makedirs(os.path.join(project_root, "logs/danmu"), exist_ok=True)



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
    elif content[0:3] == "#画画":
        with file_lock:
            with open('configs/config.json', encoding="utf-8", mode='r') as f:
                data = json.load(f)
            data["is_obs_play_ready"] = 0
        with file_lock:
            with open('configs/config.json', 'w', encoding='utf-8') as config_file:
                json.dump(data, config_file, indent=4, ensure_ascii=False)
        import draw_test
        draw_test.comfy_api(content[3:])
        with file_lock:
            with open('configs/config.json', encoding="utf-8", mode='r') as f:
                data = json.load(f)
            data["is_obs_play_ready"] = 1
            data["is_obs_ready"] = 1
        with file_lock:
            with open('configs/config.json', 'w', encoding='utf-8') as config_file:
                json.dump(data, config_file, indent=4, ensure_ascii=False)
        return 1

    elif content[0:3] == "#点歌":
        if content[3] == "0":
            song = search_in_wy(content[4:])
            if not song:
                print("很抱歉，网易爬虫似乎出现了些问题！！")
                return 0
            print("已成功点歌:"+song)
            web_captions_printer.put("已成功点歌:"+song)
            song_search_playList.queue.insert(0, song)
            song_lst.queue.insert(0, song)
        elif content[3] == "1":
            song = search_bilibili(content[4:])
            if not song:
                return 0
            song_search_playList.queue.insert(0, song)
            song_lst.queue.insert(0, song)
        return 1

    elif content[0:3] == "#翻唱":
        global find_wav_lst,is_song_cover_ready
        if not is_song_cover_ready:
            print("翻唱线程已被占用，请等待翻唱音频播放完毕后使用本功能！！！")
            return 1
        if len(content) != 3:
            spleeter_to_svc.sing_for_svc(f"{find_wav_lst[int(content[3:])]}")
            song_search_playList.queue.insert(0, "output")
            song_lst.queue.insert(0, "output")
        else:
            find_wav_lst = spleeter_to_svc.find_wav()
        return 1

    elif content[0:3] == "#唱歌":
        song_content = content[4:]
        song_database = make_song_n4j.neo4j_songdatabase("configs/config.json")
        songlist = song_database.search_song(song_content)
        songlist_str = ""
        for id, name in enumerate(songlist):
            content = f"序号{id}:{name}."
            songlist_str += content
        web_captions_printer.put("请选择所需的序号:\n"+songlist_str)
        return 1

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

    elif content[0:3] == "#命令":
        import re
        selected_indices_str = content[3:]
        # 使用正则表达式提取数字部分
        selected_indices = []
        # 匹配单独的数字或数字范围
        matches = re.finditer(r'(\d+)(?:-(\d+))?', selected_indices_str)
        for match in matches:
            start = int(match.group(1))
            end = int(match.group(2) or match.group(1))
            # 将范围内的数字添加到列表中
            selected_indices.extend(range(start, end + 1))
        # 遍历输入的序号，将对应元素存入队列
        current_songs = list(song_playList.queue)
        # 清空队列
        while not song_playList.empty():
            song_playList.get()
        if len(current_songs) != 0:
            for index in selected_indices:
                # 检查序号是否有效
                if 0 <= index < len(songlist):
                    current_songs.insert(0, songlist[index])
                else:
                    print(f"警告: 无效的序号 {index}")
            web_captions_printer.put("即将播放:\n" + ",".join([f"序号{index}:" + songlist[index] for index in selected_indices]))
        else:
            for index in selected_indices:
                # 检查序号是否有效
                if 0 <= index < len(songlist):
                    # 插入歌曲
                    current_songs.append(songlist[index])
                else:
                    print(f"警告: 无效的序号 {index}")
        # 将新的歌曲列表重新加入队列
        print("播放列表:",current_songs)
        for song in current_songs:
            song_playList.put(song)
            song_lst.put(song)
        web_captions_printer.put("即将播放:\n"+"\n".join([f"序号{index}:"+songlist[index] for index in selected_indices]))
        return 1
    else:
        return 0

# 获取b站直播间数据（当前该模块只能获取弹幕，获取的方式也比较原始，以后会支持更多的内容）
async def blivedm_api_get():
    global QuestionName,QuestionList,danmu_count
    danmu_file_path = f'logs/danmu/{danmu_count}.json'
    if os.path.exists(danmu_file_path):
        with open(danmu_file_path, 'r',encoding="utf-8") as file:
            danmu_data = json.load(file)
        user_name = danmu_data.get('user_name', '')
        content = danmu_data.get('content', '')
        os.remove(danmu_file_path)
        danmu_count += 1
        please = Classifiers(content)
        if please == 0:
            return 0
        elif please == 1:
            return 1

        if not QuestionList.full():
            content = content[3:]
            QuestionName.put(user_name)  # 将用户名放入队列
            QuestionList.put(content)  # 将弹幕消息放入队列
            time1 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            LogsList.put(f"[{time1}] [{user_name}]：{content}")
            print("\033[32mSystem>>\033[0m已将该条弹幕添加入问题队列")
        else:
            print("\033[32mSystem>>\033[0m队列已满，该条弹幕被丢弃")

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

def set_emotion(score):
    '''

    :param score: 本次需要变化的情绪分数
    :return: 变换后情绪值对应的情绪阶段
    '''
    global emotion_score,emotion_state
    emotion_score += score
    if 0 <= emotion_score < 20:
        emotion_state = "悲伤"
    elif 20 <= emotion_score < 40:
        emotion_state = "焦虑"
    elif 40 <= emotion_score < 60:
        emotion_state = "平静"
    elif 60 <= emotion_score < 80:
        emotion_state = "开心"
    elif 80 <= emotion_score <= 100:
        emotion_state = "激动"
    elif emotion_score < 0:
        emotion_score = 0
    elif emotion_score > 100:
        emotion_score = 100
    return emotion_state

def ai_response():
    """
    提取问题中是否存在会影响到主播情绪变化的关键词，获取该关键词的信息并计算变换后的情绪值。提供一个角色信息字典给llm参考并回复，将得到的回复内容进行临时存储并存入语音合成队列
    :return:
    """
    global is_ai_ready,emotion_state,emotion_score
    prompt = QuestionList.get()
    user_name = QuestionName.get()
    ques = LogsList.get()
    keyword,score,result = study_for_memory.search_from_memory(prompt)
    if score == "None":
        score = 0
    emotion_state = set_emotion(score)
    role_json = {
        "角色名称": role_name,
        "角色性别": role_sex,
        "角色年龄": role_age,
        "角色当前情绪": f"你当前的心情值为{emotion_score}(范围为[0-100])，正处于{emotion_state}状态",
        "你需要扮演的角色设定": role_prompt,
        "你之前的聊天记录:": memory.short_term_memory_window(prompt)
    }
    if keyword != "None":
        chat_messages = [
            {
                "role": "user",
                "content": f"用户本次的问题:{prompt}。下面的内容是从你的知识库中查询出来的，请你根据对后面补充的信息进行筛选来回答本次用户的问题，禁止回答多余的内容:{result}"
            }
        ]
        response = chat_tgw(role_language_model,chat_messages)
        chat_messages = [
            {
                "role": "user",
                "content": f"接下来你需要扮演我设定的角色,本段设定你自己知道即可，不要向别人说出来。{str(role_json)}你来使用扮演角色的语气和心情状态来复述下面的内容:{response}"
            }
        ]
        response = chat_tgw(role_language_model, chat_messages)
    else:
        chat_messages = [
            {
                "role": "user",
                "content": f"接下来你需要扮演我设定的角色,本段设定你自己知道即可，不要向别人说出来。{str(role_json)}你来使用扮演角色的语气和心情状态来回答下面的问题:{prompt}"
            }
        ]
        response = chat_tgw(role_language_model, chat_messages)
    answer = f"回复{user_name}：{response}"
    AnswerList.put(f"{prompt}" + "," + answer)
    current_question_count = QuestionList.qsize()
    print(f"\033[31m[AI-Vtuber]\033[0m{answer}")
    print(
        f"\033[32mSystem>>\033[0m[{user_name}]的回复已存入队列，当前剩余问题数:{current_question_count}"
    )
    time1 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with file_lock:
        with open("./logs/logs.txt", "a", encoding="utf-8") as f:
            f.write(
                f"{ques}\n[{time1}] {answer}\n========================================================\n"
            )
        with open("configs/short_term_memory.json","r",encoding="utf-8") as f:
            data = json.load(f)
        data["short_term_memory"].append({"role":"user","content":ques})
        data["short_term_memory"].append({"role":"assistant","content":answer+time1})
        with open("configs/short_term_memory.json","w",encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    is_ai_ready = 1

def chat_tgw(model,messages):
    '''

    :param model: 需要调用的llm
    :param messages: openai标准的消息会话
    :return: llm回复的内容，type:str
    '''
    from chat_api import create_chat_completion
    return create_chat_completion(model, messages)

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
    1.edge-tts -> so-vits-svc
    2.gpt-sovits
    3.bert-vits2
    :param text: 需要合成的文本

    '''
    # 创建输出文件夹
    output_folder = f"./song_output/tts"
    os.makedirs(output_folder, exist_ok=True)
    global AudioCount,is_tts_ready
    please = role_speech_model
    if please == "edge-tts":
        asyncio.run(tts_module.process_text_file(text, os.path.join(project_root, output_folder),AudioCount))
        # svc
        svc_api_request.request_api(os.path.join(project_root, f"song_output/tts/{AudioCount}.wav"),AudioCount)
        print("处理完成！")
        queue_contents = list(tts_playList.queue)
        if AudioCount not in queue_contents:
            tts_playList.put(AudioCount)
        is_tts_ready = 1
        AudioCount += 1
    elif please == "gpt-sovits":
        tts_module.to_gpt_sovits_api(text, os.path.join(project_root,"song_output"),AudioCount)
        queue_contents = list(tts_playList.queue)
        if AudioCount not in queue_contents:
            tts_playList.put(AudioCount)
        is_tts_ready = 1
        AudioCount += 1
    elif please == "bert-vits2":
        # 分割文本为多个片段
        segments = []
        max_segment_length = 100  # 每个片段的最大长度
        while len(text) > max_segment_length:
            # 查找最近的逗号或句号作为分割点
            split_index = max_segment_length
            for i in range(max_segment_length, 0, -1):
                if text[i] in [",", "。", "，"]:
                    split_index = i + 1
                    break
            segment = text[:split_index]
            segments.append(segment)
            text = text[split_index:]
        segments.append(text)  # 添加剩余的文本片段

        # 创建输出文件夹
        output_folder = r"./song_output"
        os.makedirs(output_folder, exist_ok=True)
        for i, segment in enumerate(segments):
            segment_folder = os.path.join(output_folder, f"segment_{i}")
            os.makedirs(segment_folder, exist_ok=True)
            tts_module.bert_vits2_api(segment, segment_folder)
            # 删除片段文件夹
            shutil.rmtree(segment_folder)

        print("处理完成！")
    web_captions_printer.put(text)

async def check_tts_play():
    """
    若已经播放完毕且播放列表中有数据 则创建一个播放tts音频的线程
    :return:
    """
    global is_tts_play_ready,is_song_play_ready,if_easy_ai_vtuber
    if not tts_playList.empty() and is_tts_play_ready and is_song_play_ready:
        is_tts_play_ready = 0
        wav_name = tts_playList.get()
        if not if_easy_ai_vtuber:
            tts_thread = threading.Thread(target=lambda: mpv_play(os.path.join(project_root, f"song_output/{wav_name}.wav")), daemon=True)
            tts_thread.start()
        else:
            easy_ai_vtuber_thread = threading.Thread(
                target=lambda: to_easy_ai_vtuber_api(
                    "speak",os.path.join(project_root, f"song_output/{wav_name}.wav")), daemon=False)
            easy_ai_vtuber_thread.start()


def mpv_play(path):
    """
    播放tts音频
    :param path: 音频路径
    :return:
    """
    duration = make_song_n4j.get_duration_ffmpeg(path)
    global is_tts_play_ready
    # end:播放多少秒结束  volume：音量，最大100，最小0
    subprocess.run(
        f'mpv.exe -vo null --volume=100 --start=0 --end={duration} "{path}" 1>nul',
        shell=False,
    )
    is_tts_play_ready = 1
    return

# 点歌线程
async def check_song_search():
    """
    若已经点歌播放完毕且点歌列表中有数据 则创建一个播放点歌歌曲的线程
    :return:
    """
    global is_song_play_ready,is_tts_play_ready,is_song_cover_ready,if_easy_ai_vtuber
    if not song_search_playList.empty() and is_song_play_ready and is_tts_play_ready:
        is_song_play_ready = 0
        song_name = song_search_playList.get()
        if song_name == "output":
            is_song_cover_ready = 0
        if not if_easy_ai_vtuber:
            tts_thread = threading.Thread(
                target=lambda: song_play(f"download/{song_name}.wav"), daemon=True)
            tts_thread.start()
        else:
            easy_ai_vtuber_thread = threading.Thread(
                target=lambda: to_easy_ai_vtuber_api(
                    "speak",os.path.join(project_root, f"download/{song_name}.wav")))
            easy_ai_vtuber_thread.start()

# 唱歌线程
async def check_song_play():
    """
    若音乐已经播放完毕且播放列表中有数据，且点歌线程和语音播放线程为空，则创建一个播放唱歌音频的线程
    :return:
    """
    global is_song_play_ready,is_tts_play_ready,is_song_cover_ready,if_easy_ai_vtuber
    if not song_playList.empty() and song_search_playList.empty() and is_song_play_ready and is_tts_play_ready :
        is_song_play_ready = 0
        if not if_easy_ai_vtuber:
            tts_thread = threading.Thread(
                target=lambda: song_play(os.path.join(hps.songdatabase.song_path, f'{song_playList.get()}.wav')))
            tts_thread.start()
        else:
            easy_ai_vtuber_thread = threading.Thread(
                target=lambda: to_easy_ai_vtuber_api("speak",os.path.join(hps.songdatabase.song_path, f'{song_playList.get()}.wav')))
            easy_ai_vtuber_thread.start()

def song_play(path):
    """
    播放歌曲
    :param path: 歌曲音频路径
    :return:
    """
    song_lst.get()
    duration = make_song_n4j.get_duration_ffmpeg(path)
    global is_song_play_ready,is_song_search_play_ready,is_song_cover_ready
    # end:播放多少秒结束  volume：音量，最大100，最小0
    subprocess.run(
        f'mpv.exe -vo null --volume=100 --start=0 --end={duration} "{path}" 1>nul',
        shell=False,
    )
    is_song_play_ready = 1
    is_song_cover_ready = 1
    return

def to_easy_ai_vtuber_api(type,path):
    global is_tts_play_ready,is_song_play_ready,is_song_cover_ready
    data = {
        "type": type,  # 说话动作
        "speech_path": path  # 语音音频路径
    }
    response = requests.post(easy_ai_vtuber_url, json=data)
    if response.status_code == 200:
        print("easy_ai_vtuber_api请求成功")
    is_tts_play_ready = 1
    is_song_play_ready = 1
    is_song_cover_ready = 1

async def check_web_captions_printer():
    '''
    投放字幕打印器
    :return:
    '''
    global is_web_captions_printer_ready
    if not web_captions_printer.empty() and is_web_captions_printer_ready:
        input_string = web_captions_printer.get()
        lines = input_string.splitlines()
        for line in lines:
            is_web_captions_printer_ready = 0
            send_to_web_captions_printer(line,web_captions_printer_port)
            time.sleep(3)
            is_web_captions_printer_ready = 1

async def data_monitor():
    global is_ai_ready,is_tts_ready,is_tts_play_ready,is_song_play_ready,is_song_cover_ready,is_obs_ready,is_obs_play_ready,is_web_captions_printer_ready,AudioPlay,AudioCount
    data = {
        "is_ai_ready": is_ai_ready,
        "is_tts_ready": is_tts_ready,
        "is_tts_play_ready": is_tts_play_ready,
        "is_song_play_ready": is_song_play_ready,
        "is_song_cover_ready": is_song_cover_ready,
        "is_obs_ready": is_obs_ready,
        "is_obs_play_ready": is_obs_play_ready,
        "is_web_captions_printer_ready": is_web_captions_printer_ready,
        "AudioPlay": AudioPlay,
        "AudioCount": AudioCount
    }

    response = requests.post('http://localhost:9550/api', json=data)



async def agent_to_do():
    """
    直播代理功能:当其余线程都为闲置时超过一定时间启动。
    自动聊天:会根据自己的角色设定和之前的聊天记忆发起对话
    自动唱歌:会根据自己的心情值和config中填写的喜欢的歌曲来选歌播放。
    :return:
    """
    global if_agent,is_ai_ready,is_tts_ready,is_tts_play_ready,is_song_play_ready,is_song_cover_ready,emotion_score
    if if_agent and is_tts_play_ready and is_song_play_ready and is_song_cover_ready and is_ai_ready and is_tts_ready:
        if_agent = 0
        random_agent = random.randint(0, 10)
        if random_agent <= 4:
            is_ai_ready = 0
            def call_agent_talk_main():
                global if_agent,is_ai_ready
                answer = plan_agency.agent_talk_main(role_prompt,role_name,role_sex,role_age,emotion_score,role_language_model)
                AnswerList.put(answer)
                print(f"\033[31m[AI-Vtuber]\033[0m{answer}")
                time1 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with file_lock:
                    with open("./logs/logs.txt", "a", encoding="utf-8") as f:
                        f.write(
                            f"[{time1}][agent-talk] {answer}\n========================================================\n"
                        )
                    with open("configs/short_term_memory.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["short_term_memory"].append({"role": "assistant", "content": answer + time1})
                    with open("configs/short_term_memory.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                if_agent,is_ai_ready = 1,1
                web_captions_printer.put(answer)
            tts_thread = threading.Thread(target=call_agent_talk_main)
            tts_thread.start()
        elif random_agent > 4:
            def call_agent_song_main(song_lst, song_playList):
                global if_agent
                role_favorite_songs = role_favorite_things["喜爱的音乐"]
                result,if_agent = plan_agency.agent_song_main(emotion_score,role_favorite_songs)
                song_lst.put(result)
                song_playList.put(result)
                web_captions_printer.put("即将播放:"+result)
            tts_thread = threading.Thread(target=call_agent_song_main, args=(song_lst, song_playList))
            tts_thread.start()

async def main():
    output_dir = "song_output"
    os.makedirs(output_dir, exist_ok=True)

    # 添加定时任务
    sched1.add_job(blivedm_api_get, "interval", seconds=1, id="blivedm_api_get", max_instances=1)
    sched1.add_job(check_tts, "interval", seconds=1, id="tts", max_instances=4)
    sched1.add_job(check_tts_play, "interval", seconds=1, id="tts_play", max_instances=1)
    sched1.add_job(check_song_play, "interval", seconds=1, id="song_play", max_instances=1)
    sched1.add_job(check_song_search, "interval", seconds=1, id="song_search", max_instances=1)
    sched1.add_job(check_web_captions_printer, "interval", seconds=1, id="web_captions_printer", max_instances=1)
    sched1.add_job(check_answer, "interval", seconds=1, id="llm_answer", max_instances=4)
    sched1.add_job(data_monitor, "interval", seconds=2, id="data_monitor", max_instances=1)
    sched1.add_job(agent_to_do, "interval", seconds=120, id="agent_to_do", max_instances=1)

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