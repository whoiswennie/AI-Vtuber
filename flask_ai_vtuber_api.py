import time
import threading
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import json
import os
import re
import subprocess
import requests
from datetime import datetime
from flask import Flask, request, send_file, jsonify, send_from_directory, render_template
from func.OBS.obs import ObsWebSocket
from func.chroma_database import chroma_database
from werkzeug.utils import secure_filename
from flask_cors import CORS
from func.chat import chat_api
from func.tts import svc_api_request
from func.tts import tts_module
from func.t2img import sd_api
from func.download.download_from_url import download_audio_from_url,download_video_from_url
from func.stt import Fast_Whisper
from func.agent import tools
import utils
import queue
import logging

# 过滤定时器的计划任务提示
logger = logging.getLogger('apscheduler')
logger.setLevel(logging.ERROR)
class IgnoreMaxInstancesFilter(logging.Filter):
    def filter(self, record):
        return "maximum number of running instances reached" not in record.getMessage()
logger.addFilter(IgnoreMaxInstancesFilter())


#__init__
##
formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

Debug = True
ALLOWED_EXTENSIONS = {'txt','mp3','mp4','wav', 'ogg', 'flac'}
hps = utils.get_hparams_from_file("configs/json/config.json")

song_path_list = queue.Queue() #存放待播放音频的队列
song_play_list = []
images_name_list = []
ReplyTextList = queue.Queue()
ReplyTextList_new = queue.Queue()
if_mpv_play = True
if_obs_play = True
if_easy_ai_vtuber = hps.ai_vtuber.if_easy_ai_vtuber
self_search = True

project_root = os.path.dirname(os.path.abspath(__file__))
songdatabase_root = hps.songdatabase.song_path
live_broadcast_data_monitor = {}
pre_live_broadcast_data_monitor = {}
role_prompt = None
role_setting = None
role_name = None
role_sex = None
role_age = None
role_emotional_display = []
role_tts_emotion = None
role_language_model = hps.ai_vtuber.language_model
for d in [i["name"] for i in hps.ai_vtuber.knowledge_database]:
    database_to_neo = [k["name"] for k in hps.ai_vtuber.knowledge_database if k["plan"] == 0 and k["name"]==d]
    database_to_chr = [k["name"] for k in hps.ai_vtuber.knowledge_database if k["plan"] == 1 and k["name"]==d]
knowledge_databases = "auto"
role_edge_tts_voice =None
role_speech_model = hps.ai_vtuber.speech_model
role_sd_comfyui_api_json = utils.load_json(hps.ai_vtuber.sd_comfyui_api_json)
obs_host = hps.api_path.obs.host
obs_port = hps.api_path.obs.port
obs_password = hps.api_path.obs.password
emotion_score = 50
MemoryList = utils.CircularBuffer(10)
DANMU_MSGS = queue.Queue(10)
faster_whisper_model = hps.api_path.fast_whisper.model_path


app = Flask(__name__)
CORS(app)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return send_from_directory('', 'chatUI.html')


@app.route('/tryChat', methods=['GET', 'POST'])
def tryChat():
    Chatword = ReplyTextList.get()
    return Chatword


@app.route('/upload_txt', methods=['POST'])
def upload_file():
    """
    # 打开文件
    with open(file_path, 'rb') as file:
        # 发送POST请求上传文件
        response = requests.post(upload_url, files={'file': file})
    Returns:

    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join('template/txt', filename)
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        file.save(save_path)
        return jsonify({'message': 'File uploaded successfully', 'filename': filename}), 200

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    """
        处理音频文件上传的函数。

        该函数接收一个POST请求，并从请求中提取音频文件。如果请求中没有文件部分，或者文件名为空，函数将返回一个错误响应。

        请求的JSON格式应包含一个名为"audio_file"的文件对象。文件对象的名称应包含有效的音频文件扩展名，例如"mp3"、"wav"、"ogg"或"flac"甚至可以mp4。

        如果上传的文件是允许的音频文件类型，文件将被保存在"template/uploads"目录下，并返回一个成功响应，包括文件的存储相对路径。

        请求JSON示例:
        {
            "audio_file": <file object>
        }

        响应JSON示例(成功):
        {
            "message": "File uploaded successfully",
            "file_path": "template/uploads/example.mp3"
        }

        响应JSON示例(错误):
        {
            "error": "No audio_file part"
        }
        或者
        {
            "error": "No selected file"
        }
        或者
        {
            "error": "File type not allowed"
        }

        Returns:
            一个包含状态信息和文件名的JSON响应。
        """
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio_file part'}), 400
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join('template/uploads', filename)
        if not os.path.exists('template/uploads'):
            os.makedirs('template/uploads')
        file.save(save_path)
        return jsonify({'message': 'File uploaded successfully', 'file_path': save_path}), 200
    else:
        return jsonify({'error': 'File type not allowed'}), 400


@app.route('/show',methods=['POST'])
def information_show():
    json_show = {
        "角色名":role_name,
        "情绪值":emotion_score,
        "记忆":list(MemoryList),
        "知识库":knowledge_databases,
        "待播放图片":images_name_list,
        "待播放音频":song_play_list
    }
    return json_show

@app.route('/switch_role',methods=['POST'])
def role_init():
    global role_prompt, role_setting, role_name, role_sex, role_age, role_emotional_display, emotion_score, role_edge_tts_voice, role_tts_emotion,knowledge_databases, database_to_neo, database_to_chr
    data = request.json
    role_key = data["role_key"]
    tts_plan = data["tts_plan"]
    if tts_plan == 2:
        role_tts_emotion = data["role_tts_emotion"]
    easyaivtuber_img = data.get("easyaivtuber_img","")
    knowledge_databases = data.get("knowledge_databases","")
    for d in [i["name"] for i in hps.ai_vtuber.knowledge_database]:
        database_to_neo = [k["name"] for k in hps.ai_vtuber.knowledge_database if k["plan"] == 0 and k["name"] == d]
        database_to_chr = [k["name"] for k in hps.ai_vtuber.knowledge_database if k["plan"] == 1 and k["name"] == d]
    if not knowledge_databases:knowledge_databases = "auto"
    role_hps = utils.get_hparams_from_file("configs/json/role_setting.json")
    role_json = role_hps.get(role_key)
    role_json_hps = utils.get_hparams_from_dict(role_json)
    role_prompt = hps.ai_vtuber.prompt
    role_setting = role_json_hps.setting
    role_name = role_json_hps.name
    role_sex = role_json_hps.sex
    role_age = role_json_hps.age
    role_emotional_display = role_json_hps.emotional_display
    emotion_score = role_json_hps.emotion
    if tts_plan == 1:
        role_edge_tts_voice = role_json_hps.tts.plan_1.edge_tts
        role_so_vits_svc = role_json_hps.tts.plan_1.so_vits_svc
        role_so_vits_svc_config = role_json_hps.tts.plan_1.so_vits_svc_config
        data_sovits = {
            "model_name": role_so_vits_svc,
            "config_name": role_so_vits_svc_config
        }
        res = requests.post('http://127.0.0.1:1145/update_model', data=data_sovits)
        if res.status_code == 200:
            print(f"\033[31m[so-vits-svc模型已切换]\033[0m")
    if easyaivtuber_img:
        data = {"type": "change_img","img": "data/images/"+easyaivtuber_img}
        res = requests.post('http://127.0.0.1:7888/alive', json=data)
        if res.status_code == 200:
            print(f"\033[31m[easyaivtuber模型已切换为{easyaivtuber_img}]\033[0m")
    print(f"\033[31m[角色模板已切换]\033[33m当前模板为{role_key}\033[0m")
    MemoryList.clear()
    print(f"\033[31m[角色模板已切换]\033[33m模型记忆已清空\033[0m")
    print(f"\033[31m[参考知识库已更新]\033[33m当前知识库:\033[32m{knowledge_databases}\033[0m")
    return {"status_code": 200}

def set_emotion(score):
    global role_name,emotion_score,emotion_state
    emotion_score += score
    emotion_num = 2
    if emotion_score >= 0 and emotion_score < 20:
        emotion_state = "悲伤"
        emotion_num = 0
    elif emotion_score >= 20 and emotion_score < 40:
        emotion_state = "焦虑"
        emotion_num = 1
    elif emotion_score >= 40 and emotion_score < 60:
        emotion_state = "平静"
        emotion_num = 2
    elif emotion_score >= 60 and emotion_score < 80:
        emotion_state = "开心"
        emotion_num = 3
    elif emotion_score >= 80 and emotion_score <= 100:
        emotion_state = "激动"
        emotion_num = 4
    elif emotion_score < 0:
        emotion_score = 0
    elif emotion_score > 100:
        emotion_score = 100
    with open('configs/json/role_setting.json', encoding="utf-8", mode='r') as f:
        data = json.load(f)
    data[role_name]["emotion"] = emotion_score
    with open('configs/json/role_setting.json', 'w', encoding='utf-8') as config_file:
        json.dump(data, config_file, indent=4, ensure_ascii=False)
    return emotion_state,emotion_num

@app.route('/chat',methods=['POST'])
def vtuber_chat():
    """
    {
        "query":
        "reference_text":
    }
    :return:
    """
    global role_prompt, role_setting, role_name, role_sex, role_age, role_emotional_display, emotion_score,knowledge_databases
    from func.chat.chat_api import create_chat_completion
    start_time = time.time()
    data = request.json
    query = data["query"]
    if data.get("if_sing",False):
        reference_text = "这是从你的作品库中获取的你即将演唱歌曲信息，请你参考其回复用户的问题:"+str(data.get("reference_text", ""))
    else:
        reference_text = data.get("reference_text", "")
    try:
        add_emo_score = reference_text.get("neo4j",{}).get("情绪值",0)
    except:
        add_emo_score = 0
    emotion_state,emotion_num = set_emotion(add_emo_score)
    web_search = data.get("web_search", "")
    if_memory = data.get("memory", False)
    if Debug:
        print("\033[33m--------------------------------------------------------------------------\033[0m")
        print("\033[32m是否启动记忆:\033[0m",if_memory)
        print("\033[32m当前已启用数据库:\033[0m",knowledge_databases)
        print("\033[32m当前时间:\033[0m",datetime.now().strftime('【%Y/%m/%d】%H:%M:%S'))
        print("\033[33m--------------------------------------------------------------------------\033[0m")
    if if_memory:
        VTuber_memory = MemoryList
    else:
        VTuber_memory = ""
    role_json = {
        "角色名称": role_name,
        "角色性别": role_sex,
        "角色年龄": role_age,
        "你需要扮演的角色设定": role_setting,
        "你当前的情绪状态为": emotion_state,
        "你当前情绪下的表现或语气应该为": role_emotional_display[emotion_num]
    }
    if Debug:
        print("\033[36m··········································································\033[0m")
        print(f"\033[34m本地知识库:\033[0m{reference_text}")
        print(f"\033[34m网络搜索:\033[0m{web_search}")
    chat_messages = [
        {
            "role":"system",
            "content":f"你之前的短期记忆为:{VTuber_memory},本条表示你与用户的历史聊天记录。当前时间为{datetime.now().strftime('%Y年%m月%d日 %H时%M分%S秒')}"
        },
        {
            "role":"assistant",
            "content":f"【这是你通过回忆的方式获取到的信息:<{reference_text}>,neo4j和chroma是从你长期记忆中查到的与当前用户问题有关的内容,一般作为当前问题的答案。】"
        },
        {
            "role": "assistant",
            "content": f"【这是你调用网络搜索工具后获取的相关信息:<{web_search}>,本条<>中表示通过网络搜索获取的信息。】"
        },
        {
            "role": "user",
            "content": f"当上面的【】中存在参考信息时，表示你已经通过某些手段获取到了答案，请你组织这些内容来回答下面用户的问题。用户问题为:{query}"
        }
    ]
    think_response = create_chat_completion(role_language_model, chat_messages)
    if Debug:
        print(f"\033[34m思考结果:\033[0m{think_response}")
    role_messages = [
        {
            "role": "system",
            "content": f"{role_prompt}，你当前扮演的角色的资料如下:{str(role_json)}。"
        },
        {
            "role": "assistant",
            "content": f"这是你经历思考后得到的结果:{think_response},请你根据你当前扮演的角色设定将该内容转换成该角色的语气。"
        },
        {
            "role": "user",
            "content": f"用户的问题为:{query}。请牢记你当前的身份是{role_name},禁止随意将自己的身份更换。"
        }
    ]
    response = create_chat_completion(role_language_model, role_messages)
    message = [{"role":"user","content":query},{"role":"assistant","content":response}]
    MemoryList.append(message)
    ReplyTextList.put(response)
    if Debug:
        print("\033[36m··········································································\033[0m")
        print("\033[35m==========================================================================\033[0m")
        print(f"\033[33m用户问题:\033[0m{query}")
        print(f"\033[33mAI-VTuber:\033[0m{response}")
        print("\033[35m==========================================================================\033[0m")
    print("当前短期记忆长度:",len(VTuber_memory))
    end_time = time.time()
    print(f"\033[31m思考运行时间：{end_time - start_time} 秒\033[0m")
    return response

@app.route('/auto_select_knowledge_databse',methods=["POST"])
def auto_select_knowledge_databse():
    content = request.json["content"]
    template_prompt = f"""
    你是一个判断工具，用来判断该选择哪些知识库来解决<>中用户的问题，要求将选择的知识库以列表的格式输出，禁止回复多余的内容。
    你当前拥有的知识库包括(其中的键为知识库名称，对应的值为该知识库的介绍)：<{hps.ai_vtuber.knowledge_database}>;
    当前用户的问题：<{content}>;
    你输出的格式严格为：["知识库1","知识库2",...]，如果不存在合适的知识库是，你应该输出[]。
    """
    chat_messages = [
        {
            "role": "user",
            "content": template_prompt
        }
    ]
    response = chat_api.zhipu_api(messages=chat_messages)
    json_str = re.sub(r"```json\n", "", response).rstrip("`\n")
    try:
        result = json.loads(json_str)
        print(f"\033[035m当前自动选取的知识库为:{result}\033[0m")
        return result
    except json.decoder.JSONDecodeError as e:
        print(f"JSONDecodeError: {e};result:{response}")
        return []

@app.route('/agent_to_do',methods=["POST"])
def agent_to_do():
    """
    POST:{"content":,"memory":(True/False)}
    Returns:

    """
    songlist = []
    d1,d2 = {},{}
    global song_path_list,self_search,knowledge_databases,database_to_neo,database_to_chr
    content = request.json["content"]
    memory = request.json["memory"]
    intention_recognition_result = tools.intention_recognition(content)
    data_auto_select_knowledge_databse = {"content": content}
    if knowledge_databases == "auto":
        knowledge_databases = requests.post(f'http://localhost:9550/auto_select_knowledge_databse', json=data_auto_select_knowledge_databse).json()
    if intention_recognition_result["intention_type"] == "chat":
        if knowledge_databases:
            for item in knowledge_databases:
                if item in database_to_chr:
                    data_search = {"content": content,"database":item}
                    d1 = requests.post(f'http://localhost:9550/search_in_chroma', json=data_search).json()
                else:
                    data_search = {"content": content,"database":item}
                    d2 = requests.post(f'http://localhost:9550/search_in_neo4j', json=data_search).json()
        else:
            data_search = {"content": content, "database": []}
            d2 = requests.post(f'http://localhost:9550/search_in_neo4j', json=data_search).json()
        data_chat = {"query": content, "reference_text": {"neo4j":d2,"chroma":d1}, "memory": memory}
        bot_response = requests.post('http://localhost:9550/chat', json=data_chat).text
        return {"content":bot_response,"refer_information":{"neo4j":d2,"chroma":d1},"songlist":songlist}
    elif intention_recognition_result["intention_type"] == "sing":
        data_sing = {"content": content}
        res = requests.post('http://localhost:9550/search_song_from_neo4j', json=data_sing).json()
        data_chat = {"query": content, "reference_text": res, "memory": memory,"if_sing":True}
        bot_response = requests.post('http://localhost:9550/chat', json=data_chat).text
        for song_path in res["songlist"]:
            song_path_dict = {"wav_path": os.path.join(res["songdatabase_root"], song_path + ".wav")}
            song_path_list.put(song_path_dict)
            songlist = list(song_path_list.queue)
        return {"content":bot_response,"refer_information":[],"songlist":songlist}
    elif intention_recognition_result["intention_type"] == "search":
        if knowledge_databases:
            for item in knowledge_databases:
                if item in database_to_chr:
                    data_search = {"content": content, "database": item}
                    d1 = requests.post(f'http://localhost:9550/search_in_chroma', json=data_search).json()
                else:
                    data_search = {"content": content, "database": item}
                    d2 = requests.post(f'http://localhost:9550/search_in_neo4j', json=data_search).json()
        else:
            data_search = {"content": content, "database": []}
            d2 = requests.post(f'http://localhost:9550/search_in_neo4j', json=data_search).json()
        if_information_supplementation_judgment = tools.information_supplementation_judgment(str({"neo4j":d2,"chroma":d1}),content)
        if if_information_supplementation_judgment["judgment"] == "True":
            data_chat = {"query": content, "reference_text": {"neo4j":d2,"chroma":d1}, "memory": memory}
            bot_response = requests.post('http://localhost:9550/chat', json=data_chat).text
            return {"content": bot_response, "refer_information": {"neo4j":d2,"chroma":d1},
                    "songlist": songlist}
        else:
            web_result = tools.query_search(content)
            refer_information = [{"本地知识库:": {"neo4j":d2,"chroma":d1}}, {"网络搜索:": web_result}]
            data_chat = {"query": content, "reference_text":{"neo4j":d2,"chroma":d1}, "memory": memory,"web_search":web_result}
            bot_response = requests.post('http://localhost:9550/chat', json=data_chat).text
            return {"content": bot_response, "refer_information": refer_information,
                    "songlist": songlist}
    elif intention_recognition_result["intention_type"] == "draw":
        if knowledge_databases:
            for item in knowledge_databases:
                if item in database_to_chr:
                    data_search = {"content": content,"database":item}
                    d1 = requests.post(f'http://localhost:9550/search_in_chroma', json=data_search).json()
                else:
                    data_search = {"content": content,"database":item}
                    d2 = requests.post(f'http://localhost:9550/search_in_neo4j', json=data_search).json()
        else:
            data_search = {"content": content, "database": []}
            d2 = requests.post(f'http://localhost:9550/search_in_neo4j', json=data_search).json()
        data_chat = {"query": "你正在为观众画一份画，观众的要求是:"+content, "reference_text": {"neo4j":d2,"chroma":d1}, "memory": memory}
        bot_response = requests.post('http://localhost:9550/chat', json=data_chat).text
        global images_name_list
        payload = json.dumps({
            "model": "model",
            "messages": [
                {
                    "role": "system",
                    "content": "你需要理解用户的要求并将其拆解成相应的能够用于图像生成的英文prompt，其应该由简短的英文单词或英语短句组成，输出格式样例:a girl,pink hair,black shoes,long hair,young,lovely。请注意，人名与实际内容无关无需翻译出来，只输出英文单词，不要输出多余的内容，禁止输入出英文以外的语言！"
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
        })
        headers = {
            'Accept': 'application/json',
            'Authorization': '',
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }
        prompt = json.loads(requests.request("POST", "http://localhost:9550/llm_chat", headers=headers, data=payload).text)['choices'][0]['message']['content']
        images_name_list += sd_api.sd_comfyui_generate_image(prompt, role_sd_comfyui_api_json)
        return {"content": bot_response, "refer_information": {"neo4j": d2, "chroma": d1},
                "save_img": images_name_list[-1]}

@app.route('/llm_chat',methods=["POST"])
def llm_chat():
    req_llm_chat = request.json
    messages = req_llm_chat["messages"]
    from func.chat.chat_api import create_chat_completion
    response = create_chat_completion(role_language_model, messages,response_str=False).json()
    print(response)
    return response

@app.route('/tts',methods=["POST"])
def vtuber_tts():
    """
    {"tts_plan":,"text":,"AudioCount":}
    :return:
    """
    req_tts = request.json
    tts_plan = req_tts["tts_plan"]
    text = req_tts["text"]
    global role_name
    if tts_plan == 1:
        AudioCount = request.json["AudioCount"]
        edge_tts_output_folder = os.path.join(project_root, f"./template/tts")
        os.makedirs(edge_tts_output_folder, exist_ok=True)
        asyncio.run(tts_module.process_text_file(role_edge_tts_voice,text, edge_tts_output_folder, AudioCount))
        svc_path = svc_api_request.request_api(project_root,os.path.join(edge_tts_output_folder, f"{AudioCount}.wav"), AudioCount)
        return {"status_code":200,"text":text,"path":svc_path,"AudioCount":AudioCount}
    elif tts_plan == 2:
        AudioCount = request.json["AudioCount"]
        gpt_sovits_output_folder = os.path.join(project_root, f"./template/tts")
        os.makedirs(gpt_sovits_output_folder, exist_ok=True)
        tts_module.to_gpt_sovits_api(role_name,text,gpt_sovits_output_folder,AudioCount,role_tts_emotion)
        return {"status_code": 200, "text": text, "path": os.path.join(gpt_sovits_output_folder,f"{AudioCount}.wav"), "AudioCount": AudioCount}

@app.route('/mpv_play',methods=["POST"])
def wav_play():
    """
    {"wav_path":}
    :return:
    """
    wav_path = request.json["wav_path"]
    duration = utils.get_duration_ffmpeg(wav_path)
    # end:播放多少秒结束  volume：音量，最大100，最小0
    subprocess.run(
        f'mpv.exe -vo null --volume=100 --start=0 --end={duration} "{wav_path}" 1>nul',
        shell=False,
    )
    return {"status_code": 200}

@app.route('/get_songlist',methods=["POST"])
def get_songlist():
    return song_play_list

@app.route('/clear_songlist',methods=["POST"])
def clear_songlist():
    global song_play_list,song_path_list
    song_play_list = []
    while not song_path_list.empty():
        song_path_list.get()
    return {"status_code": 200}

@app.route('/search_song_from_neo4j',methods=["POST"])
def vtuber_sing():
    """
    {"content"}
    :return:
    """
    global song_play_list
    from func.Neo4j_Database import songdatabase
    content = request.json["content"]
    song_information_list,songlist = songdatabase.search_song_from_neo4j(content,"configs/json/config.json","data/json/song_dict.json")
    song_play_list += songlist
    return {"songlist":songlist,"songdatabase_root":songdatabase_root,"song_information_list":song_information_list}

@app.route('/send_audio',methods=["POST"])
def download_audio():
    """
    {"wav_path":}
    :return:
    """
    audio_file_path = request.json["wav_path"]
    return send_file(audio_file_path, as_attachment=True)

@app.route('/draw',methods=["POST"])
def vtuber_draw():
    global images_name_list
    sd_prompt = request.json["sd_prompt"]
    images_name_list += sd_api.sd_comfyui_generate_image(sd_prompt, utils.load_json(role_sd_comfyui_api_json))
    return images_name_list

@app.route('/action',methods=["POST"])
def vtuber_action():
    """
    {"type":,"speech_path":,"music_path":,"voice_path":,"mouth_offset":}
    :return:
    """
    req = request.json
    type = req["type"]
    if type == "speak":
        data = {
            "type": type,  # 说话动作
            "speech_path": req["speech_path"]  # 语音音频路径
        }
    elif type == "rhythm":
        data = {
            "type": type,  # 节奏摇动作
            "music_path": req["music_path"]  # 歌曲音频路径
        }
    elif type == "sing":
        data = {
            "type": "sing",
            "music_path": req["music_path"],  # 修改为原曲路径
            "voice_path": req["voice_path"],  # 修改为人声音频路径
            "mouth_offset": 0.0
        }
    else:
        data = {}
    response = requests.post("http://127.0.0.1:7888/alive", json=data)
    if response.status_code == 200:
        print("\033[31measy_ai_vtuber_api请求成功\033[0m")
    return

@app.route('/tool/faster_whisper',methods=["POST"])
def tool_faster_whisper():
    """
    {"input_path":}
    Returns:

    """
    req = request.json
    input_path = req["input_path"]
    language = req.get("language",None)
    text_list,txt_file_path = Fast_Whisper.stt_from_txt(model_path=faster_whisper_model,input_path=input_path,output_path="template/stt",language=language)
    return {"text":text_list,"txt_file_path":txt_file_path}

@app.route('/tool/download_from_url',methods=["POST"])
def tool_download_from_url():
    """
    {"url":,"index":,"format":(mp4/wav)}
    Returns:

    """
    req = request.json
    url = req["url"]
    index = req["index"]
    format = req["format"]
    print(url,index,format)
    if format == "mp4":
        downloaded_files = download_video_from_url(
            url=url,  # 要下载的视频的URL
            destinationDirectory="template/downloads",  # 下载文件的保存目录
            playlistItems=index  # 下载播放列表中的特定项目，"1" 表示第一个视频
        )
        return downloaded_files
    elif format == "wav":
        downloaded_files = download_audio_from_url(
            url=url,
            destinationDirectory="template/downloads",
            playlistItems=index
        )
        return downloaded_files
    else:
        return "Format error"

@app.route('/tool/information_to_chroma',methods=["POST"])
def tool_information_to_chroma():
    req = request.json
    uploaded_file_name = req["uploaded_file_name"]
    node_name = req["node_name"]
    segment_number = req["segment_number"]
    introduction = req.get("introduction","")
    chroma_database.make_db(f"template/txt/{uploaded_file_name}", f"data/chroma_database/database/{node_name}",
                            chunk_size=segment_number)
    config_data = utils.load_json("configs/json/config.json")
    config_data["ai_vtuber"]["knowledge_database"].append(
        {"name": f"{node_name}", "introduction": introduction, "plan": 1})
    utils.write_json(config_data, "configs/json/config.json")
    return {"status_code": 200}

@app.route('/search_in_chroma',methods=["POST"])
def tool_search_in_chroma():
    start_time = time.time()
    print("\033[35m[正在查询向量数据库]\033[0m")
    req = request.json
    content = req["content"]
    database = req["database"]
    from func.chroma_database import chroma_database
    k_lst = []
    k_lst.append(chroma_database.search_in_db(f"data/chroma_database/database/{database}",content,k_lin=2))
    if Debug:
        print("\033[33mAI筛查的向量数据库片段:\033[0m", k_lst)
    print("\033[36m[向量数据库查询完毕]\033[0m")
    end_time = time.time()
    print(f"\033[31m运行时间：{end_time - start_time} 秒\033[0m")
    return k_lst

@app.route('/search_in_neo4j',methods=["POST"])
def tool_search_in_neo4j():
    start_time = time.time()
    req = request.json
    content = req["content"]
    database = req["database"]
    print(f"\033[35m[正在查询关联数据(当前知识库{database})]\033[0m")
    related_keywords = []
    from func.Neo4j_Database import to_neo4j
    neo = to_neo4j.Neo4jHandler("configs/json/config.json")
    neo.connect_neo4j_database()
    new_related_keywords = {"认知知识库": [], "外置知识库初始节点": [], "外置知识库关联节点": [], "情绪值":0}
    if database:
        # ==================================================================================================================
        # AI-VTuber的外置知识库查询
        related_keywords += utils.find_similar_keywords(neo.get_nodes_with_label(database, False), content, 40)
        if not related_keywords:
            related_keywords += utils.find_similar_keywords(neo.get_nodes_with_label(database, False), content, 30)
            related_keywords = sorted(related_keywords, key=lambda x: x[1], reverse=True)[:1]
        else:
            related_keywords = sorted(related_keywords, key=lambda x: x[1], reverse=True)[:]
        new_related_keywords["外置知识库初始节点"] += [f"提取到的关键词为【{n[0]['value']}】,类别为【{n[0]['name']}】与记忆库匹配度为:{n[1]}。" for n in
                                              related_keywords]
        related_keywords_pairs = [(related_keywords[i], related_keywords[j]) for i in range(len(related_keywords)) for j
                                  in
                                  range(i + 1, len(related_keywords))]
        swapped_pairs = [(b, a) for a, b in related_keywords_pairs]
        related_keywords_pairs.extend(swapped_pairs)
        for node in related_keywords:
            node = neo.search_node(database, node[0])
            if node[0]["relationship_types"]:
                related_nodes = neo.find_related_nodes(node[0]["node"], node[0]["relationship_types"][0])
                new_related_keywords["外置知识库关联节点"] += [f"通过关键词{node[0]['node']['value']}查询到的{n['name']}是{n['value']}。"
                                                      for n
                                                      in related_nodes if n['name'] != "情绪值"]
    # ==================================================================================================================
    # AI-VTuber的认知关联知识库查询
    related_database = []
    related_keywords_cog = []
    related_keywords_cog += utils.find_similar_keywords(neo.get_nodes_with_label("认知", False), content, 40)
    new_related_keywords["认知知识库"] += [f"提取到的关键词为【{n[0]['value']}】,类别为【{n[0]['name']}】与记忆库匹配度为:{n[1]}。" for n in
                                      related_keywords_cog]
    try:
        for node in related_keywords_cog:
            node = neo.search_node("认知", node[0])
            if node[0]["relationship_types"]:
                related_nodes = neo.find_related_nodes(node[0]["node"], node[0]["relationship_types"][0])
                for n in related_nodes:
                    if n['name'] == "关联":
                        related_database.append(n['value'])
                new_related_keywords["外置知识库关联节点"] += [f"通过关键词{node[0]['node']['value']}查询到的{n['name']}是{n['value']}。"
                                                      for n
                                                      in related_nodes if n['name'] != "关联" and n['name'] != "情绪值"]
                # ==================================================================================================================
                # 认知识库情绪值计算
                for n in related_nodes:
                    if n['name'] == "情绪值":
                        new_related_keywords["情绪值"] += int(n['value'])
    # ==================================================================================================================
    except:
        pass
    if database:
        for d in related_database:
            d = json.loads(d)
            if d["plan"] == 0 and d["name"] != database:
                database = d["name"]
                related_keywords_cog += utils.find_similar_keywords(neo.get_nodes_with_label(database, False), content,
                                                                    40)
        while related_keywords_cog:
            node = neo.search_node(database, related_keywords_cog.pop()[0])
            try:
                if node[0]["relationship_types"]:
                    related_nodes = neo.find_related_nodes(node[0]["node"], node[0]["relationship_types"][0])
                    new_related_keywords["外置知识库关联节点"] += [
                        f"通过关键词{node[0]['node']['value']}查询到的{n['name']}是{n['value']}。"
                        for
                        n in
                        related_nodes if n['name'] != "关联" and n['name'] != "情绪值"]
            except:
                pass
    k_lst = new_related_keywords
    if database:
        k_lst["思考路径"] = []
        for i in related_keywords_pairs:
            node1 = neo.search_node(database, i[0][0])[0]["node"]
            node2 = neo.search_node(database, i[1][0])[0]["node"]
            node_path = neo.find_shortest_path(node1, node2)
            if node_path:
                k_lst["思考路径"].append(node_path)
    # ==================================================================================================================
    if Debug:
        print("\033[33m查询到的初始节点:\033[0m", related_keywords)
        if database:
            print("\033[33m查询到的认知知识库节点:\033[0m", k_lst["认知知识库"])
        print("\033[33m查询到的关联节点:\033[0m", new_related_keywords["外置知识库关联节点"])
    if Debug:
        print("\033[33mAI筛查的内容:\033[0m", k_lst)
    print("\033[36m[关联数据查询完毕]\033[0m")
    end_time = time.time()
    print(f"\033[31m运行时间：{end_time - start_time} 秒\033[0m")
    return k_lst

def song_play():
    global if_mpv_play,song_play_list,if_easy_ai_vtuber
    wav_path = song_path_list.get()
    try:
        if if_easy_ai_vtuber:
            action_dict = {"type": "rhythm", "music_path": wav_path}
            res = requests.post('http://localhost:9550/action',
                                json=action_dict).json()
        else:
            res = requests.post('http://localhost:9550/mpv_play',
                          json=wav_path).json()
    except:
        res = requests.post('http://localhost:9550/mpv_play',
                            json=wav_path).json()
    song_name = os.path.splitext(os.path.basename(wav_path["wav_path"]))[0]
    if res["status_code"] == 200:
        if_mpv_play = True
    try:
        if song_name in song_play_list:
            song_play_list.remove(song_name)
    except:
        pass

def check_song_play():
    global song_path_list,if_mpv_play
    if not song_path_list.empty() and if_mpv_play:
        if_mpv_play = False
        thread = threading.Thread(target=song_play())
        thread.start()
        thread.join()

def send_to_obs():
    try:
        global if_obs_play,images_name_list
        obs = ObsWebSocket(host=obs_host, port=obs_port, password=obs_password)
        obs.connect()
        obs.show_image("to_obs", os.path.join(project_root,images_name_list.pop(0)))
        obs.disconnect()
    except Exception as e:
        print("\033[31m出现异常:\033[0m",e)

def check_obs_play():
    global images_name_list,if_obs_play
    if len(images_name_list)>1 and if_obs_play:
        if_obs_play = False
        thread = threading.Thread(target=send_to_obs())
        thread.start()
        thread.join()

def app_server():
    app.run(debug=False, host='0.0.0.0', port=9550, threaded=True)

async def run_flask():
    sched1 = AsyncIOScheduler(timezone="Asia/Shanghai")
    app_thread = threading.Thread(target=app_server)
    app_thread.start()
    # 添加定时任务
    sched1.add_job(check_song_play, "interval", seconds=1, id="check_song_play", max_instances=1)
    sched1.add_job(check_obs_play, "interval", seconds=1, id="check_obs_play", max_instances=1)
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


if __name__ == "__main__":
    asyncio.run(run_flask())