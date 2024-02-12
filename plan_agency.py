import random
import utils
import threading
import time
import make_song_n4j
from chat_api import create_chat_completion

class Timer(threading.Thread):
    def __init__(self, seconds):
        super().__init__()
        self.seconds = seconds
        self.elapsed_time = 0
        self.time_up = False

    def run(self):
        start_time = time.time()
        while self.elapsed_time < self.seconds:
            time.sleep(1)  # 休眠1秒钟
            self.elapsed_time = time.time() - start_time
        self.time_up = True

def start_timer(seconds):
    timer = Timer(seconds)
    timer.start()
    return timer


def agent_to_sing(emotion_score):
    hps_emotional_factors = utils.get_hparams_from_file("configs/emotional_influencing_factors.json")
    print(
        f"\033[32mSystem>>\033[0m[agent执行中]，当前选择的任务:\033[31m[唱歌任务]\033[0m"
    )
    if emotion_score >= 0 and emotion_score < 20:
        emotion_score_state = 0
    elif emotion_score >= 20 and emotion_score < 40:
        emotion_score_state = 1
    elif emotion_score >= 40 and emotion_score < 60:
        emotion_score_state = 2
    elif emotion_score >= 60 and emotion_score < 80:
        emotion_score_state = 3
    elif emotion_score >= 80 and emotion_score <= 100:
        emotion_score_state = 4
    elif emotion_score < 0:
        emotion_score_state = 0
    else:
        emotion_score_state = 4
    prefer_emotional_lst = hps_emotional_factors[str(emotion_score_state)]
    random_num = random.randint(0, len(prefer_emotional_lst)-1)
    a = make_song_n4j.neo4j_songdatabase("configs/config.json")
    random_song_lst = a.search_song(prefer_emotional_lst[random_num])
    random_song_num = random.randint(0, len(random_song_lst)-1)
    random_song_name = random_song_lst[random_song_num]
    print(f"当前情绪值为{emotion_score}，主播想唱一首关于\033[31m{prefer_emotional_lst[random_num]}\033[0m的歌，选择的歌曲名字为:",random_song_name)
    return random_song_name

def agent_song_main(emotion_score):
    seconds_to_count = 5  # 设置计时器计数的秒数
    timer = start_timer(seconds_to_count)
    while not timer.time_up:
        time.sleep(1)
    return agent_to_sing(emotion_score),1

def set_emotion(emotion_score,score):
    global emotion_state
    emotion_score += score
    if emotion_score >= 0 and emotion_score < 20:
        emotion_state = "悲伤"
    elif emotion_score >= 20 and emotion_score < 40:
        emotion_state = "焦虑"
    elif emotion_score >= 40 and emotion_score < 60:
        emotion_state = "平静"
    elif emotion_score >= 60 and emotion_score < 80:
        emotion_state = "开心"
    elif emotion_score >= 80 and emotion_score <= 100:
        emotion_state = "激动"
    elif emotion_score < 0:
        emotion_score = 0
    elif emotion_score > 100:
        emotion_score = 100
    return emotion_state

def agent_talk_main(role_prompt,role_name,role_sex,role_age,emotion_score,role_language_model):
    seconds_to_count = 5  # 设置计时器计数的秒数
    timer = start_timer(seconds_to_count)
    while not timer.time_up:
        time.sleep(1)
    hps_mem = utils.get_hparams_from_file("configs/short_term_memory.json")
    role_mem = hps_mem.short_term_memory
    if len(role_mem) > 10:
        role_mem = role_mem[-10:]
    print(
        f"\033[32mSystem>>\033[0m[agent执行中]，当前选择的任务:\033[31m[聊天任务]\033[0m"
    )
    emotion_state = set_emotion(emotion_score,0)
    role_json = {
        "角色名称": role_name,
        "角色性别": role_sex,
        "角色年龄": role_age,
        "角色当前情绪": f"你当前的心情值为{emotion_score}(范围为[0-100])，正处于{emotion_state}状态",
        "你需要扮演的角色设定": role_prompt,
        "你之前的聊天记录:": role_mem
    }
    chat_messages = [
        {
            "role": "user",
            "content": f"接下来你需要扮演我设定的角色,本段设定你自己知道即可，不要向别人说出来。{str(role_json)},你要根据扮演角色的语气、设定、心情状态和聊天记忆来主动发起对话来跟直播间的观众们互动，注意说的内容不要与之前聊天记录中的内容重复。"
        }
    ]
    response = create_chat_completion(role_language_model, chat_messages)
    return response


# 使用示例
if __name__ == "__main__":
    seconds_to_count = 2  # 设置计时器计数的秒数
    timer = start_timer(seconds_to_count)
    while not timer.time_up:
        print(f"Elapsed time: {timer.elapsed_time:.1f} seconds")
        time.sleep(1)
    print("Time's up!")
    agent_to_sing(85)
