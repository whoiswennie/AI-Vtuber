import asyncio
import datetime
import json
import os
import queue
import shutil
import subprocess
import threading
import make_song_n4j
import svc_api_request
import tts_module
import spleeter_to_svc
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bilibili_api import live, sync, Credential
from tool.search_for_song import search_in_wy, search_bilibili
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
hps = utils.get_hparams_from_file('configs/config.json')
is_ai_ready = hps.bilibili.is_ai_ready
is_tts_ready = hps.bilibili.is_tts_ready
is_tts_play_ready = hps.bilibili.is_tts_play_ready
is_song_play_ready = hps.bilibili.is_song_play_ready
is_song_cover_ready = hps.bilibili.is_song_cover_ready
is_obs_ready = hps.bilibili.is_obs_ready
is_obs_play_ready = hps.bilibili.is_obs_play_ready
is_web_captions_printer_ready = hps.bilibili.is_web_captions_printer_ready
web_captions_printer_port = hps.api_path.web_captions_printer.port
AudioCount = hps.bilibili.AudioCount
AudioPlay = hps.bilibili.AudioPlay


# 文件夹初始化
if os.path.exists(os.path.join(project_root, "song_output")):
    shutil.rmtree(os.path.join(project_root, "song_output"))

cred = Credential(
    sessdata = hps.bilibili.sessdata,
    buvid3 = hps.bilibili.buvid3,
    dedeuserid = hps.bilibili.dedeuserid
)
room_id = hps.bilibili.room_id
room = live.LiveDanmaku(room_id, credential=cred)  # 连接弹幕服务器
sched1 = AsyncIOScheduler(timezone="Asia/Shanghai")

def Classifiers(content):
    global songlist,song_lst
    if content[0:3] == "[幻]":
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
            song_search_playList.queue.insert(0, song)
            song_lst.queue.insert(0, song)
        elif content[3] == "1":
            song = search_bilibili(content[4:])
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
        find_wav_lst = spleeter_to_svc.find_wav()
        return 1

    elif content[0:3] == "#唱歌":
        song_content = content[4:]
        song_database = make_song_n4j.neo4j_songdatabase("configs/config.json")
        songlist = song_database.search_song(song_content)
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
        with file_lock:
            with open('configs/config.json', 'w', encoding='utf-8') as config_file:
                json.dump(config_data, config_file, indent=4, ensure_ascii=False)

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
        #send_to_web_captions_printer("即将播放:\n"+",".join([f"序号{index}:"+songlist[index] for index in selected_indices]))
        return 1
    else:
        return 0

@room.on("INTERACT_WORD")  # 用户进入直播间
async def in_liveroom(event):
    user_name = event["data"]["data"]["uname"]  # 获取用户昵称
    time1 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{time1}:粉丝\033[36m[{user_name}]\033[0m进入了直播间")
    #web_captions_printer.put(f"欢迎{user_name}来到幻的直播间")
    # 直接放到语音合成处理
    AnswerList.put(f"欢迎{user_name}来到幻的直播间")


@room.on("DANMU_MSG")  # 弹幕消息事件回调函数
async def input_msg(event):
    """
    处理弹幕消息
    """
    global QuestionList
    global QuestionName
    global LogsList
    content = event["data"]["info"][1]  # 获取弹幕内容
    user_name = event["data"]["info"][2][1]  # 获取用户昵称
    print(f"\033[36m[{user_name}]\033[0m:{content}")  # 打印弹幕信息
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

# tts线程
def check_tts():
    """
    如果语音已经放完且队列中还有回复 则创建一个生成并播放TTS的线程
    :return:
    """
    global is_tts_ready,AudioCount
    if not AnswerList.empty() and is_tts_ready:
        text = AnswerList.get()
        is_tts_ready = 0
        tts_thread = threading.Thread(target=lambda: tts_main(text))
        tts_thread.start()

def tts_main(text):
    # 创建输出文件夹
    output_folder = f"./song_output/edge-tts"
    os.makedirs(output_folder, exist_ok=True)
    global AudioCount,is_tts_ready
    # please = int(input("1.bert-vits   2.edge-tts"))
    please = 2
    if please == 2:
        asyncio.run(tts_module.process_text_file(text, os.path.join(project_root, output_folder),AudioCount))
        # svc
        svc_api_request.request_api(os.path.join(project_root, f"song_output/edge-tts/{AudioCount}.wav"),AudioCount)
        print("处理完成！")
        queue_contents = list(tts_playList.queue)
        if AudioCount not in queue_contents:
            tts_playList.put(AudioCount)
        is_tts_ready = 1
        AudioCount += 1

    else:
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
def check_tts_play():
    """
    若已经播放完毕且播放列表中有数据 则创建一个播放音频的线程
    :return:
    """
    global is_tts_play_ready,is_song_play_ready
    if not tts_playList.empty() and is_tts_play_ready and is_song_play_ready:
        is_tts_play_ready = 0
        tts_thread = threading.Thread(target=lambda: mpv_play(os.path.join(project_root, f"song_output/{tts_playList.get()}.wav")))
        tts_thread.start()

def mpv_play(path):
    duration = make_song_n4j.get_duration_ffmpeg(path)
    global is_tts_play_ready
    # end：播放多少秒结束  volume：音量，最大100，最小0
    subprocess.run(
        f'mpv.exe -vo null --volume=100 --start=0 --end={duration} "{path}" 1>nul',
        shell=False,
    )
    is_tts_play_ready = 1
    return

# 点歌线程
def check_song_search():
    global is_song_play_ready,is_tts_play_ready,is_song_cover_ready
    if not song_search_playList.empty() and is_song_play_ready and is_tts_play_ready:
        is_song_play_ready = 0
        song_name = song_search_playList.get()
        if song_name == "output":
            is_song_cover_ready = 0
        else:
            is_song_cover_ready = 1
        tts_thread = threading.Thread(
            target=lambda: song_play(f"download/{song_name}.wav"))
        tts_thread.start()

# 唱歌线程
def check_song_play():
    global is_song_play_ready,is_tts_play_ready
    if not song_playList.empty() and song_search_playList.empty() and is_song_play_ready and is_tts_play_ready :
        is_song_play_ready = 0
        tts_thread = threading.Thread(
            target=lambda: song_play(os.path.join(hps.songdatabase.song_path, f'{song_playList.get()}.wav')))
        tts_thread.start()

def song_play(path):
    song_lst.get()
    duration = make_song_n4j.get_duration_ffmpeg(path)
    global is_song_play_ready,is_song_search_play_ready
    # end：播放多少秒结束  volume：音量，最大100，最小0
    subprocess.run(
        f'mpv.exe -vo null --volume=100 --start=0 --end={duration} "{path}" 1>nul',
        shell=False,
    )
    is_song_play_ready = 1
    return

def main():
    output_dir = "song_output"
    os.makedirs(output_dir, exist_ok=True)
    # tts语音转换
    sched1.add_job(check_tts, "interval", seconds=1, id=f"tts", max_instances=4)
    # tts播放
    sched1.add_job(check_tts_play, "interval", seconds=1, id=f"tts_play", max_instances=4)
    # song播放
    sched1.add_job(check_song_play, "interval", seconds=1, id=f"song_play", max_instances=4)
    # 网易点歌
    sched1.add_job(check_song_search, "interval", seconds=1, id=f"song_search", max_instances=4)
    # 启动调度器
    sched1.start()
    # 开始监听弹幕流
    sync(room.connect())

if __name__ == '__main__':
    main()