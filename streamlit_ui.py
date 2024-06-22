import subprocess
import webbrowser
import pandas as pd
import shutil
#from func.chroma_database import chroma_database
import streamlit as st
import os
import json
import utils
from zhipuai import ZhipuAI
import pyaudio
import wave

project_root = os.path.dirname(os.path.abspath(__file__))

# 定义全局变量
RECORDING = False

def delete_files_except_txt(folder_path):
    try:
        txt_folder_path = os.path.join("template", "txt")
        if not os.path.exists(txt_folder_path):
            os.makedirs(txt_folder_path)
        # 将txt文件转移到template/txt文件夹中
        for filename in os.listdir(folder_path):
            if filename.endswith(".txt"):
                file_path = os.path.join(folder_path, filename)
                shutil.move(file_path, txt_folder_path)
        # 删除folder_path文件夹
        shutil.rmtree(folder_path)
        # 创建一个新的folder_path文件夹
        os.makedirs(folder_path)
        # 将之前存在template/txt的txt文件再转移（不是复制）到新的folder_path的文件夹中
        for filename in os.listdir(txt_folder_path):
            file_path = os.path.join(txt_folder_path, filename)
            shutil.move(file_path, folder_path)
    except Exception as e:
        st.warning(f"处理文件时出错：{e}，请手动处理！")

def remove_wav_files(folder_path):
    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        # 检查文件扩展名是否为.wav
        if os.path.isfile(file_path) and filename.lower().endswith('.wav'):
            try:
                # 删除文件
                os.remove(file_path)
                print(f"删除文件: {file_path}")
            except Exception as e:
                print(f"删除文件 {file_path} 失败: {e}")

def start_recording():
    global RECORDING

    # 设置录音参数
    FORMAT = pyaudio.paInt16  # 设置采样格式
    CHANNELS = 1  # 设置声道数
    RATE = 44100  # 设置采样率
    CHUNK = 1024  # 设置缓冲区大小
    RECORD_SECONDS = 20  # 设置录音时长
    WAVE_OUTPUT_FILENAME = "template/output.wav"  # 设置输出文件名

    # 创建 PyAudio 实例
    p = pyaudio.PyAudio()

    # 打开音频流
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* 录音开始，请开始说话...")
    st.success("录音开始......")
    # 开始录音
    frames = []
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        if RECORDING:
            data = stream.read(CHUNK)
            frames.append(data)
        else:
            break

    print("* 录音结束")
    st.success("录音结束")
    # 停止录音并关闭音频流
    stream.stop_stream()
    stream.close()
    p.terminate()

    # 保存录音结果到 WAV 文件
    with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    print("* 录音已保存到 output.wav")

def set_emotion(score):
    global emotion_score,emotion_state
    emotion_score += score
    emotion_num = 2
    with open('configs/config.json', encoding="utf-8", mode='r') as f:
        data = json.load(f)
    data["ai_vtuber"]["emotion"] = emotion_score
    with open('configs/config.json', 'w', encoding='utf-8') as config_file:
        json.dump(data, config_file, indent=4, ensure_ascii=False)
    emotion_score = hps.ai_vtuber.emotion
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
    return emotion_state,emotion_num

def chat_tgw(model,messages):
    from chat_api import create_chat_completion
    return create_chat_completion(model, messages)

def llm_response(query):
    global role_name,role_sex,role_age
    keyword, score, result = study_for_memory.search_from_memory(query)
    if score == "None":
        score = 0
    emotion_state,emotion_num = set_emotion(score)
    role_json = {
        "角色名称": role_name,
        "角色性别": role_sex,
        "角色年龄": role_age,
        "角色当前情绪": f"你当前的心情值为{emotion_score}(范围为[0-100])，正处于{emotion_state}状态，此时角色的情绪表现为:{role_emotional_display[emotion_num]}",
        "你需要扮演的角色设定": role_prompt,
        "你之前的聊天记录:": memory.short_term_memory_window(query)
    }
    if keyword != "None":
        chat_messages = [
            {
                "role": "user",
                "content": f"用户本次的问题:{query}。下面的内容是从你的知识库中查询出来的，请你根据对后面补充的信息进行筛选来回答本次用户的问题，禁止回答多余的内容:{result}"
            }
        ]
        response = chat_tgw(role_language_model, chat_messages)
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
                "content": f"接下来你需要扮演我设定的角色,本段设定你自己知道即可，不要向别人说出来。{str(role_json)}你来使用扮演角色的语气和心情状态来回答下面的问题:{query}"
            }
        ]
        response = chat_tgw(role_language_model, chat_messages)
    return response

def query_search(query: str):
  current_query_lst = [{"role": "user", "content": query}]
  response = client.chat.completions.create(
    model="glm-3-turbo",  # 填写需要调用的模型名称
    messages=current_query_lst,
    tools=[
      {
        "type": "web_search",
        "web_search": {
          "enable": True
        }
      }
    ],
  )
  print(f"\033[31m[代理搜索汇总中：]\033[0m{response.choices[0].message.content}")
  return response.choices[0].message.content

def clear_messages(messages):
    messages["input_text"] = ""
    messages["query"] = ""
    messages["web_search"] = ""
    messages["agent_study"] = ""
    save_json(messages)

@st.cache_data
def get_song_dict():
    a = make_song_n4j.neo4j_songdatabase("configs/config.json")
    with open("configs/song_dict.json", 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data,a


def get_session_state():
    with open("configs/messages.json", 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

# 保存 JSON 文件
def save_json(data,filename="configs/messages.json"):
    """

    :param data:
    :param filename:
    :return:
    {"input_text": "","query": "","web_search": "","agent_study": ""}
    """

    old_messages = get_session_state()
    non_empty_keys = [key for key, value in data.items() if value is not None and value != '']
    print("messages:",data)
    print("old_messages:",old_messages)
    print("non_empty_keys:",non_empty_keys)
    for key in non_empty_keys:
        if key in data:
            replacement_value = data[key]
            old_messages[key] = replacement_value
    print("new_message:",old_messages)
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(old_messages, file, ensure_ascii=False, indent=4)

def save_agent_txt(text,filename):
    with open(f"chroma_database/text/{filename}.txt", "w", encoding="utf-8") as f:
        f.write(text)

def main():
    st.set_page_config(
        page_title='AI-Vtuber',
        layout="wide",
        page_icon='icon/ComfyUI_00011_.png',
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': "https://space.bilibili.com/287906485?spm_id_from=333.1007.0.0",
            'Report a bug': "https://space.bilibili.com/287906485?spm_id_from=333.1007.0.0",
            'About': "作者还懒得写......"
        }
    )
    st.markdown(
        """
        <style>
        body {
            background-color: rgba(135, 206, 235, 0.2); /* 使用rgba设置透明度 */
            color: white;
        }
        .stApp {
            background-color: rgba(135, 206, 235, 0.2); /* 使用rgba设置透明度 */
        }
        .sidebar .sidebar-content {
            background-color: rgba(192, 192, 192, 0.2); /* 使用rgba设置透明度 */
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    with st.sidebar:
        st.sidebar.image("icon/image.gif", caption='放着好看！', use_column_width=True)
        st.title('AI-Vtuber')
        st.markdown('项目作者:这就是天幻呀')
        st.markdown('---')
        page = st.sidebar.radio("页面导航", ["直播管理","AI-Vtuber","歌库","认知学习"])
    if page == "直播管理":
        st.title("直播管理")
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("开启直播"):
                subprocess.Popen(["cmd", "/c", "start", "python", "blivedm_api.py"], shell=True)
                subprocess.Popen(["cmd", "/c", "start", "python", "bilibili_main.py"], shell=True)
                # 构建iframe标签的HTML代码，并将BV号插入到URL中
                webbrowser.open(f"https://live.bilibili.com/{room_id}")
        with col2:
            if st.button("终止mpv播放器"):
                import psutil
                import signal
                # 查找包含 "mpv" 的进程列表
                for proc in psutil.process_iter(['pid', 'name']):
                    if 'mpv' in proc.name():
                        mpv_pid = proc.pid
                        # 终止找到的 mpv 进程
                        proc.send_signal(signal.SIGTERM)
        with col3:
            if st.button("启动flask监听"):
                st.success("flask监听端口启动成功")
                subprocess.Popen(['cmd', '/k', 'python', 'flask_ai_vtuber_api.py'], creationflags=subprocess.CREATE_NEW_CONSOLE)
        with col4:
            if st.button("判断所有端口是否启动"):
                import socket
                from urllib.parse import urlparse
                def extract_port_and_url(url):
                    parsed_url = urlparse(url)
                    if parsed_url.scheme == 'http' or parsed_url.scheme == 'https':
                        netloc = parsed_url.netloc.split(':')[0]
                        return netloc, parsed_url.port
                    elif parsed_url.scheme == 'bolt':
                        netloc = parsed_url.netloc.split(':')[0]
                        return netloc, int(parsed_url.netloc.split(':')[-1])
                    else:
                        return None, None
                urls = [
                    {"live_broadcast_data_monitor_api":"http://0.0.0.0:9550"},
                    {"so_vits_svc_api":hps.api_path.so_vits_svc.url},
                    {"bert_vits2_api":hps.api_path.bert_vits2.url},
                    {"gpt_sovits_api":hps.api_path.gpt_sovits.url},
                    {"easy_ai_vtuber_api":hps.api_path.easy_ai_vtuber.url},
                    {"neo4j_api":hps.api_path.neo4j.url}
                ]
                def is_port_in_use(host,port):
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        try:
                            s.bind((host, port))
                        except OSError:
                            return True
                        else:
                            return False
                for url in urls:
                    api_name = next(iter(url.keys()), None)
                    api_url = next(iter(url.values()), None)
                    host,port = extract_port_and_url(api_url)
                    if is_port_in_use(host,port):
                        st.success(f"{api_name} 端口 {port} 已启动")
                    else:
                        st.error(f"{api_name} 端口 {port} 未启动")

        select_live = st.selectbox("功能选择",["默认","live2d监控"],index=0)
        if select_live == "live2d监控":
            import socket as skt
            try:
                # 检查端口是否已被占用
                sock = skt.socket(skt.AF_INET, skt.SOCK_STREAM)
                result = sock.connect_ex(("localhost", 8765))
                if result == 0:
                    st.error("端口 8765 已被占用，请确保没有其他程序在使用该端口。")
                else:
                    st.success("端口 8765 可用，正在进行live2d监控...")
                    st.write("正在启动 WebSocket 服务器...")
                    process = subprocess.Popen(["python", "websocket_server.py"], stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE)
                    # 显示服务器启动日志
                    st.write("WebSocket 服务器启动日志：")
                    for line in process.stdout:
                        st.write(line.decode().strip())

                    for line in process.stderr:
                        st.error(line.decode('utf-8', 'ignore').strip())
            except Exception as e:
                st.error(f"发生错误：{e}")
            finally:
                pass

    elif page == "AI-Vtuber":
        markdown_text = """
        <div style="text-align:center;">
          <h1 style="color:red; text-shadow: 2px 2px 4px #FF00FF;">欢迎使用 <span style="color:blue;">A</span><span style="color:green;">I</span>-<span style="color:orange;">V</span><span style="color:purple;">t</span><span style="color:yellow;">u</span><span style="color:pink;">b</span><span style="color:brown;">e</span><span style="color:grey;">r</span>！</h1>
          <p style="font-size:24px; color:orange; text-decoration:underline;">本项目正在重构中……</p>
        </div>
        """

        st.markdown(markdown_text, unsafe_allow_html=True)
        st.markdown('---')
        choice = st.selectbox("功能选择:", ["爬虫", "画画", "聊天", "翻唱", "ai-agent"], index=0)
        # 根据选择的功能显示不同的信息
        if choice == "爬虫":
            selected_option = st.selectbox('请选择一个选项：', ['网易云', '哔哩哔哩视频', '哔哩哔哩音频'])
            if selected_option == "网易云":
                query = st.text_input("请输入您想听的歌:")
                if query:
                    progress_bar = st.progress(0)
                    st.text("正在下载音频，请耐心等待...")
                    song_name = tool.search_for_song.search_in_wy(query)
                    progress_bar.progress(100)
                    st.text("音频名称:"+song_name)
                    st.audio(os.path.join(project_root,f"download/{song_name}.wav"))
                    st.text("如果音频时长为0，则表示该音频是VIP歌曲，无法播放")
            elif selected_option == "哔哩哔哩音频":
                query = st.text_input("请输入bv号:")
                if query:
                    progress_bar = st.progress(0)
                    st.text("正在下载音频，请耐心等待...")
                    song_name =tool.search_for_song.search_bilibili(query)
                    progress_bar.progress(100)
                    st.text("音频名称:" + song_name)
                    st.audio(os.path.join(project_root,f"download/{song_name}.wav"))
            elif selected_option == "哔哩哔哩视频":
                query = st.text_input("请输入bv号:")
                if query:
                    progress_bar = st.progress(0)
                    st.text("正在下载视频，请耐心等待...")
                    video_name =tool.search_for_song.search_bilibili_mp4(query)
                    progress_bar.progress(100)
                    st.text("视频名称:"+video_name)
                    st.video(os.path.join(project_root,"download/merged_video.mp4"))
                    st.text("视频源地址:")
                    # 构建iframe标签的HTML代码，并将BV号插入到URL中
                    iframe_html = f"""
                    <iframe id="bilibiliFrame" src="https://www.bilibili.com/video/{query}" width="1000" height="600" style="border:none;"></iframe>
                    """

                    # 在Streamlit应用程序中嵌入B站视频的iframe
                    st.write(iframe_html, unsafe_allow_html=True)
        elif choice == "聊天":
            audio_text = None
            # 创建录音按钮
            global RECORDING
            button1 = st.button("开始录音")
            button2 = st.button("停止录音")
            if button2:
                RECORDING = False
                st.success("录音结束")
                st.text("正在进行语音识别中......")
                audio_text = tool.Fast_Whisper.stt_for_llm("./faster-whisper-webui/Models/faster-whisper/large-v2",
                                      input_path="template/output.wav")
                st.text("语音识别完毕！")
            elif button1:
                RECORDING = True
                st.text("正在进行录音中......")
                start_recording()
            if audio_text:
                # 创建输入框
                user_input = st.text_area("请输入信息：", value=audio_text,height=100)
            else:
                user_input = st.text_area("请输入信息：", height=100)

            # 创建提交按钮
            if st.button("提交"):
                response = llm_response(user_input)
            else:
                response = ""
            st.write("状态栏")
            n_hps = utils.get_hparams_from_file("configs/config.json")
            e_score = n_hps.ai_vtuber.emotion
            col1, col2, col3, col4 = st.columns(4)
            # 在每列中显示文本
            with col1:
                st.text("姓名: " + vtuber_name)
            with col2:
                st.text("性别: " + vtuber_sex)
            with col3:
                st.text("当前情绪值: " + f"{e_score}")
            with col4:
                st.text("当前情绪状态:" + set_emotion(0)[0])
            st.text("角色设定:" + vtuber_setting)
            # 创建输出框
            st.write("回复信息：")
            st.text_area("",value=response, height=400)
            tts_response = tts_module.to_gpt_sovits_api(response, os.path.join(project_root, "output"), "tts")
            if tts_response:
                st.audio("output/tts.wav", format="audio/wav")
                st.success("gpt-sovits合成成功")
            else:
                st.error("语音合成服务未启动")

        elif choice == "翻唱":
            # 添加一个按钮来删除临时音频文件
            if st.button("删除当前音频文件和临时翻唱文件"):
                if os.path.exists('template/template_upload.wav'):
                    os.remove('template/template_upload.wav')
                remove_wav_files("output/template_upload")
                st.success("临时音频文件已成功删除！")
            # 检查是否存在 template_upload.wav 文件
            if os.path.exists('template/template_upload.wav'):
                st.text("之前上传的翻唱推理原版音频:")
                # 如果存在，则加载它
                st.audio('template/template_upload.wav', format='audio/wav')
            else:
                # 如果不存在，则创建一个文件上传组件
                uploaded_file = st.file_uploader("上传需要翻唱的音频文件", type=['wav'])
                # 加载音频文件
                if uploaded_file:
                    # 保存上传的音频文件到 template 文件夹中
                    with open('template/template_upload.wav', 'wb') as f:
                        f.write(uploaded_file.read())
                    # 提示用户上传成功
                    st.success("音频文件上传成功！")
                    # 加载并播放保存的音频文件
                    st.audio('template/template_upload.wav', format='audio/wav')
            folder_path = os.path.join(project_root,"pretrained_models/uvr5/models/Main_Models")
            file_names = os.listdir(folder_path)
            file_name_list = [file_name for file_name in file_names]
            selected_model = st.selectbox("请选择人声分离模型：", file_name_list, index=len(file_name_list)-1)
            if st.button("开始分离"):
                # 定义命令行指令
                command = rf'python spleeter_to_svc.py -ap "template/template_upload.wav" -sp "output/template_upload" -mp "pretrained_models/uvr5/models/Main_Models/{selected_model}"'

                # 运行命令行指令
                try:
                    st.text("正在人声分离中,请耐心等待...")
                    subprocess.run(command, shell=True, check=True)
                    print("命令执行成功")
                    if st.button("人声伴奏互换"):
                        os.rename('output/template_upload/wav_vocal.wav', "output/template_upload/temp.wav")
                        os.rename('output/template_upload/wav_instrument.wav', 'output/template_upload/wav_vocal.wav')
                        os.rename("output/template_upload/temp.wav", 'output/template_upload/wav_instrument.wav')
                        st.success("人声伴奏已互换")
                    st.text("分离的人声")
                    st.audio('output/template_upload/wav_vocal.wav', format='audio/wav')
                    st.text("分离的伴奏")
                    st.audio('output/template_upload/wav_instrument.wav', format='audio/wav')
                    if st.button("开始翻唱"):
                        st.text("正在翻唱中，请耐心等待......")
                        spleeter_to_svc.vocal_svc()
                        st.text("翻唱的人声")
                        st.audio('output/template_upload/svc.wav', format='audio/wav')
                        st.text("合并的音频")
                        st.audio('output/template_upload/output.wav', format='audio/wav')
                except subprocess.CalledProcessError as e:
                    print("命令执行失败:", e)
            else:
                if os.path.exists('output/template_upload/wav_vocal.wav'):
                    if st.button("人声伴奏互换"):
                        os.rename('output/template_upload/wav_vocal.wav', "output/template_upload/temp.wav")
                        os.rename('output/template_upload/wav_instrument.wav', 'output/template_upload/wav_vocal.wav')
                        os.rename("output/template_upload/temp.wav", 'output/template_upload/wav_instrument.wav')
                        st.success("人声伴奏已互换")
                    st.text("分离的人声")
                    st.audio('output/template_upload/wav_vocal.wav', format='audio/wav')
                    st.text("分离的伴奏")
                    st.audio('output/template_upload/wav_instrument.wav', format='audio/wav')
                    if os.path.exists('output/template_upload/output.wav'):
                        st.text("翻唱的人声")
                        st.audio('output/template_upload/svc.wav', format='audio/wav')
                        st.text("合并的音频")
                        st.audio('output/template_upload/output.wav', format='audio/wav')
                    if st.button("开始翻唱"):
                        st.text("正在翻唱中，请耐心等待......")
                        spleeter_to_svc.vocal_svc()
                        st.text("翻唱的人声")
                        st.audio('output/template_upload/svc.wav', format='audio/wav')
                        st.text("合并的音频")
                        st.audio('output/template_upload/output.wav', format='audio/wav')
        elif choice == "ai-agent":
            ai_vtuber = hps.ai_vtuber
            modified_t = st.text_area("ai_agent信息表:",value=ai_vtuber)
            st.text(modified_t)

    elif page == "歌库":
        st.title("歌库")
        if not os.path.exists("configs/song_dict.json"):
            a = make_song_n4j.neo4j_songdatabase("configs/config.json")
            a.reset("csv/歌库.csv")
        song_data_dict, a = get_song_dict()
        if st.button("更新图数据库:"):
            a.reset("csv/歌库.csv")
            st.success("图数据库更新成功！")
        selected_option = st.selectbox('请选择一个选项：', ['歌名', '歌曲语言','演唱人数','歌曲来源', '风格', '标签'])

        # 检查是否存在选定的歌曲
        if 'selected_song' not in st.session_state:
            st.session_state.selected_song = None

        if selected_option == "歌名":
            song_button = song_data_dict["歌名"]
        elif selected_option == "歌曲语言":
            song_button = song_data_dict["歌曲语言"]
        elif selected_option == "演唱人数":
            song_button = song_data_dict["演唱人数"]
        elif selected_option == "歌曲来源":
            song_button = song_data_dict["歌曲来源"]
        elif selected_option == "风格":
            song_button = song_data_dict["风格"]
        elif selected_option == "标签":
            song_button = song_data_dict["标签"]
        else:
            song_button = song_data_dict["歌名"]

        # 检查选定的歌曲是否在列表中
        if st.session_state.selected_song is not None and st.session_state.selected_song not in song_button:
            st.session_state.selected_song = None

        # 加载存储在messages.json中的歌名列表
        with open('configs/messages.json', 'r',encoding="utf-8") as f:
            messages_data = json.load(f)
            song_list = messages_data.get('song_list', [])

        # 如果歌名列表不为空，则将其作为搜索按钮的默认结果
        if song_list:
            selected_song = st.selectbox('请选择一个选项：', song_button, index=song_button.index(
                st.session_state.selected_song) if st.session_state.selected_song else 0, key='song_select')
        else:
            selected_song = st.selectbox('请选择一个选项：', song_button, index=0, key='song_select')

        if st.button('搜索'):
            st.text(f'正在搜索：{selected_song}')
            search_results = a.search_song(selected_song)
            if search_results:
                song_list = [song for song in search_results]
                messages_data["song_list"] = song_list
                # 保存歌名列表到JSON文件
                with open('configs/messages.json', 'w',encoding="utf-8") as f:
                    json.dump(messages_data, f)
                selected_song_result = st.selectbox('请选择要播放的歌曲：', song_list)
                if selected_song_result:
                    song_file = None
                    for song in search_results:
                        if song == selected_song_result:
                            song_file = os.path.join(song_path, song + ".wav")
                            break
                    if song_file is not None:
                        st.audio(song_file, format='audio/wav')
                    else:
                        st.text('未找到选择的歌曲路径')

                # 保存选定的歌曲
                st.session_state.selected_song = selected_song_result
        else:
            # 检查是否存在选定的歌曲，若存在则显示之前选定的歌曲
            if song_list:
                song_name_list = [song for song in song_list]
                selected_song_result = st.selectbox('请选择要播放的歌曲：', song_name_list)
                if selected_song_result:
                    song_file = None
                    for song in song_list:
                        if song == selected_song_result:
                            song_file = os.path.join(song_path, song + ".wav")
                            break
                    if song_file is not None:
                        st.audio(song_file, format='audio/wav')
                    else:
                        st.text('未找到选择的歌曲路径')

        # 清空歌名列表按钮
        if st.button('清空歌名列表'):
            song_list = []
            messages_data["song_list"] = song_list
            # 保存清空后的歌名列表到JSON文件
            with open('configs/messages.json', 'w') as f:
                json.dump(messages_data, f)

    elif page == "认知学习":
        y_select = st.selectbox('请选择一个选项：', ['知识库', '代理学习'])
        if y_select == "知识库":
            y1_select = st.selectbox('请选择一个选项：', ['视频学习', '文本学习', '知识库管理'])
            if y1_select == "视频学习":
                # 添加一个按钮来删除临时音频文件
                if st.button("删除当前上传的视频文件:"):
                    if os.path.exists('template/template_upload.mp4'):
                        os.remove('template/template_upload.mp4')
                    st.success("临时视频文件已成功删除！")
                st.text("请选择你要学习的视频:")
                uploaded_file = st.file_uploader("上传视频或音频文件", type=['mp4','wav'])
                if uploaded_file:
                    # 保存上传的视频文件到 template 文件夹中
                    with open('template/template_upload.mp4', 'wb') as f:
                        f.write(uploaded_file.read())
                    # 提示用户上传成功
                    st.success("视频文件上传成功！")
                    # 加载并播放保存的音频文件
                    st.video('template/template_upload.mp4', format='video/mp4')
                if os.path.exists('template/template_upload.mp4'):
                    st.text("之前上传的视频:")
                    st.video('template/template_upload.mp4', format='video/mp4')
                if st.button("开始提取视频信息"):
                    video_text = tool.Fast_Whisper.stt_for_llm("faster-whisper-webui/Models/faster-whisper/large-v2",input_path="template/template_upload.mp4")
                    with open('chroma_database/text/template_upload.txt', 'w',encoding="utf-8") as f:
                        f.write(video_text)
                if os.path.exists('chroma_database/text/template_upload.txt'):
                    with open('chroma_database/text/template_upload.txt', 'r',encoding="utf-8") as f:
                        video_text = f.read()
                    modified_text = st.text_area("视频转换的文本:",video_text)
                    if modified_text != video_text:
                        with open('chroma_database/text/template_upload.txt', 'w', encoding="utf-8") as f:
                            f.write(modified_text)
                    k = st.text_input("请输入本次的学习的关键词:")
                    txt_name = st.text_input("请输入本次的学习的标题:")
                    text_emotion = st.slider("情绪影响因子:", min_value=-5, max_value=5, step=1, value=0)
                    if st.button("进行向量化存储"):
                        output_dir = f"chroma_database/database/{k}"
                        os.makedirs(output_dir, exist_ok=True)
                        manager = study_for_memory.KeywordAssociationManager('csv/keyword_dict.csv')
                        manager.add_keyword(k)
                        manager.update_emotion(k, text_emotion)
                        manager.get_association(k)
                        manager.add_association(txt_name)
                        chroma_database.make_db("chroma_database/text/template_upload.txt", f"chroma_database/database/{k}", chunk_size=100)
                        with open(os.path.join(output_dir,f"{txt_name}.txt"),"w",encoding="utf-8") as f:
                            f.write(modified_text)
                        st.success("新知识储存完毕！")


            elif y1_select == "文本学习":
                uploaded_file = st.file_uploader("上传一个文本文件 (.txt)", type="txt")
                if uploaded_file:
                    content = uploaded_file.read().decode("utf-8")
                    st.success("文件上传成功")
                    st.code(content)
                    with open('chroma_database/text/template_upload.txt', 'w', encoding="utf-8") as f:
                        f.write(content)
                    k = st.text_input("请输入本次的学习的关键词:")
                    txt_name = st.text_input("请输入本次的学习的标题:")
                    text_emotion = st.slider("情绪影响因子:", min_value=-5, max_value=5, step=1, value=0)
                    if st.button("进行向量化存储"):
                        output_dir = f"chroma_database/database/{k}"
                        os.makedirs(output_dir, exist_ok=True)
                        manager = study_for_memory.KeywordAssociationManager('csv/keyword_dict.csv')
                        manager.add_keyword(k)
                        manager.update_emotion(k, text_emotion)
                        manager.get_association(k)
                        manager.add_association(txt_name)
                        chroma_database.make_db("chroma_database/text/template_upload.txt", f"chroma_database/database/{k}", chunk_size=100)
                        with open(os.path.join(output_dir,f"{txt_name}.txt"),"w",encoding="utf-8") as f:
                            f.write(content)
                        st.success("新知识储存完毕！")

            elif y1_select == "知识库管理":
                select_option = st.selectbox(
                    "选择需要管理的内容",
                    ("关键词词表","代理模式情绪影响因子")
                )
                if select_option == '关键词词表':
                    # 读取CSV文件
                    df = pd.read_csv("csv/keyword_dict.csv", encoding="gbk")
                    # 创建侧边栏选项
                    display_option = st.sidebar.selectbox(
                        '选择展示方式',
                        ('关键词', '情绪值')
                    )
                    # 选择展示方式为关键词
                    if display_option == '关键词':
                        keyword = st.sidebar.selectbox('选择关键词', df['keyword'])
                        selected_row = df[df['keyword'] == keyword]
                        # 展示关键词的详情信息
                        st.write(selected_row)
                        # 展示关键词对应的 association 标签下的数据
                        associations = selected_row['association'].iloc[0].split('，')
                        for association in associations:
                            st.write(association)
                        # 选择具体的 association 数据
                        selected_association = st.selectbox('选择 association 数据', associations)
                        selected_row_association = selected_row[
                            selected_row['association'].str.contains(selected_association)]
                        # 获取文件路径
                        file_path = f"chroma_database/database/{keyword}/{selected_association}.txt"
                        if os.path.exists(file_path):
                            # 读取并展示文件内容
                            with open(file_path, 'r', encoding='utf-8') as file:
                                file_content = file.read()
                            t1 = st.text_area(f"{selected_association}",value=file_content,height=500)
                            if file_content != t1:
                                with open(file_path, 'w', encoding='utf-8') as file:
                                    file.write(t1)
                                st.success("更新成功")
                            folder_path = f"chroma_database/database/{keyword}"
                            new_associtation_name = st.text_input(label="是否更改此条association的命名:")
                            if new_associtation_name:
                                manager = study_for_memory.KeywordAssociationManager("csv/keyword_dict.csv")
                                manager.get_association(keyword)
                                manager.delete_association(association_to_delete=selected_association)
                                manager.add_association(new_association=new_associtation_name)
                                file_path = os.path.join(folder_path, selected_association + ".txt")
                                new_file_path = os.path.join(folder_path, new_associtation_name + ".txt")
                                if os.path.exists(file_path):
                                    os.rename(file_path, new_file_path)
                                st.success("词表已更新！")
                            if st.button("删除此条association"):
                                manager = study_for_memory.KeywordAssociationManager("csv/keyword_dict.csv")
                                manager.get_association(keyword)
                                manager.delete_association(association_to_delete=selected_association)
                                file_path = os.path.join(folder_path, selected_association+".txt")
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                st.success("词表已删除！")
                            if st.button("更新向量数据库"):
                                if folder_path:
                                    delete_files_except_txt(folder_path)
                                    for filename in os.listdir(folder_path):
                                        if filename.endswith(".txt"):
                                            file_path = os.path.join(folder_path, filename)
                                            chroma_database.make_db(file_path, folder_path, chunk_size=100)
                                            st.success("向量库更新成功！")
                                else:
                                    st.warning("请输入文件夹路径！")
                        else:
                            st.text_area("提示:",value=f"文件 '{file_path}' 不存在")
                    # 选择展示方式为情绪值
                    elif display_option == '情绪值':
                        emotion = st.sidebar.selectbox('选择情绪值', df['emotion'].unique())
                        selected_rows = df[df['emotion'] == emotion]
                        # 展示情绪值对应的数据
                        st.write(selected_rows)
                    # 在侧边栏中添加按钮，用于按需显示更多信息
                    if st.sidebar.button('显示更多信息'):
                        st.write(df)
                elif select_option == "代理模式情绪影响因子":
                    st.write("---")
                    song_dict_data, _ = get_song_dict()
                    # 初始化 session_state 字典，用于保存用户选择的值
                    if 'selected_values' not in st.session_state:
                        st.session_state.selected_values = {"0": [], "1": [], "2": [], "3": [], "4": []}
                    json_file = "configs/emotional_influencing_factors.json"
                    # 如果JSON文件存在，且不为空，读取内容并解析为字典
                    if os.path.exists(json_file) and os.path.getsize(json_file) > 0:
                        with open(json_file, "r", encoding="utf-8") as f:
                            st.session_state.selected_values = json.load(f)
                    # 单选框选择情绪
                    emotion = st.radio("选择情绪：", options=["all","0", "1", "2", "3", "4"])
                    # 下拉框选择字典中的键
                    selected_key = st.selectbox("选择字典中的键：", options=list(song_dict_data.keys()))
                    # 根据情绪和已选择的值，更新可供选择的值列表
                    if emotion != "all":
                        # 获取之前情绪已选择的值
                        previous_selected_values = []
                        for i in range(int(emotion)):
                            previous_selected_values.extend(st.session_state.selected_values[str(i)])
                        # 获取当前情绪未选择的值
                        remaining_values = [value for value in song_dict_data[selected_key] if
                                            value not in previous_selected_values]
                        # 获取当前情绪已选择的值，但需要去除不在 remaining_values 中的值
                        current_selected_values = [value for value in st.session_state.selected_values[emotion] if
                                                   value in remaining_values]
                        # 更新选择框的选项
                        selected_values = st.multiselect("选择值：", options=remaining_values,
                                                         default=current_selected_values)
                    else:
                        # 如果是情绪为all，则直接显示所有值供选择
                        selected_values = st.multiselect("选择值：", options=song_dict_data[selected_key])
                        return
                    # 显示已选择的值，并提供删除选项
                    st.write("已保存的选项：")
                    saved_options = st.multiselect("选择要删除的选项：", options=st.session_state.selected_values[emotion],
                                                   default=[])
                    if st.button("删除"):
                        st.session_state.selected_values[emotion] = [value for value in
                                                                     st.session_state.selected_values[emotion] if
                                                                     value not in saved_options]
                        with open(json_file, "w", encoding="utf-8") as f:
                            json.dump(st.session_state.selected_values, f, indent=4)
                    # 保存按钮
                    if st.button("保存"):
                        # 更新字典中对应键的值
                        st.session_state.selected_values[emotion] += selected_values
                        # 去除重复元素
                        st.session_state.selected_values[emotion] = list(set(st.session_state.selected_values[emotion]))
                        # 写回到JSON文件，并格式化为可读性更好的形式
                        with open(json_file, "w", encoding="utf-8") as f:
                            json.dump(st.session_state.selected_values, f, indent=4)

        elif y_select == "代理学习":
            # 添加一个标题
            st.title("代理学习")
            # 新增文本框用于手动输入文本
            input_text = st.text_input("请输入本次学习方向:")
            # 从会话状态获取或创建按钮点击状态和输出文本
            messages = get_session_state()
            print(messages)
            button_states = st.session_state.setdefault('button_states', {'问题提取': False, '网络搜索': False, '代理学习': False,'清空会话':False})
            agent_prompt = "我想让你成为我的知识点整理员,你需要按照我的要求把内容存入字典中。你的目标是帮助我整理最佳的知识点信息,这些知识点将为你提供信息参考。你将遵循以下过程：1.首先，你会问我知识点是关于什么的。我会告诉你，但我们需要通过不断的重复来完善它，通过则进行下一步。2.根据我的输入，你会创建三个部分：a)修订整理后的知识点(你整合汇总后的信息，你不要随意删除之前已经提取的信息，应该清晰、精确、易于理解，拥有严谨的输出格式并给出标签，应当包含之前提取的所有有关信息块)b)问答对(你需要将a中整理的已有信息转换成问答对)c)问题(你提出相关问题，询问我需要哪些额外信息来补充进a中你整理的信息)3.我们将继续这个迭代过程我会提供更多的信息。你会更新“修订后的，你整理的信息'’部分的请求，直到它完整为止。"
            chat_messages = [
                {"role": "user", "content": agent_prompt + "我提供的新信息如下:" + (messages["web_search"] if messages["web_search"] else "") + "这是你之前已经整理的信息,请你将前面提供的新内容补充到你后面整理的信息中:" + (messages["agent_study"] if messages["agent_study"] else "")}
            ]
            # 检查按钮点击状态
            button1_clicked = st.button('问题提取')
            button2_clicked = st.button('网络搜索')
            button3_clicked = st.button('代理学习')
            button4_clicked = st.button('清空会话')

            # 如果按钮被点击，更新按钮状态和输出文本
            if button1_clicked:
                button_states['问题提取'] = True
                messages['query'] = chat_api.zhipu_api("请你提取出下段文本中用户的问题:" + (messages["agent_study"] if messages["agent_study"] else ""))
                save_json(messages)
            elif button2_clicked:
                button_states['网络搜索'] = True
                if input_text:
                    messages['web_search'] = query_search(input_text)
                else:
                    messages['web_search'] = query_search(messages['query'])
                save_json(messages)
            elif button3_clicked:
                button_states['代理学习'] = True
                messages['agent_study'] = chat_api.zhipu_api(chat_messages)
                save_json(messages)
            elif button4_clicked:
                button_states['清空会话'] = True
                clear_messages(messages)
            # 在文本框中显示结果
            messages1 = st.empty()
            messages2 = st.empty()
            messages3 = st.empty()
            modified_query = messages1.text_area('问题提取:', value=messages['query'], height=300)
            modified_web_search = messages2.text_area('网络搜索:', value=messages['web_search'], height=300)
            modified_agent_study = messages3.text_area('代理学习:', value=messages['agent_study'], height=300)
            # 判断用户是否修改了文本内容
            if modified_query != messages['query']:
                messages['query'] = modified_query
                save_json(messages)

            if modified_web_search != messages['web_search']:
                messages['web_search'] = modified_web_search
                save_json(messages)

            if modified_agent_study != messages['agent_study']:
                messages['agent_study'] = modified_agent_study
                save_json(messages)
            # 显示手动输入的文本
            messages["input_text"] = input_text
            filename = st.text_input("请输入需要保存的文件名称:")
            if filename:
                save_agent_txt(messages['agent_study'],filename)
                st.text(filename+"保存完毕！")

if __name__ == '__main__':
    # 初始化
    hps = utils.get_hparams_from_file("configs/json/config.json")
    api_key = hps.api_path.llm_api.zhipuai_key
    song_path = hps.songdatabase.song_path
    room_id = hps.bilibili.blivedm.room_id
    client = ZhipuAI(api_key=api_key)
    role_prompt = hps.ai_vtuber.setting
    role_name = hps.ai_vtuber.name
    role_sex = hps.ai_vtuber.sex
    role_age = hps.ai_vtuber.age
    role_emotional_display = hps.ai_vtuber.emotional_display
    role_language_model = hps.ai_vtuber.language_model
    role_speech_model = hps.ai_vtuber.speech_model
    vtuber_name = hps.ai_vtuber.name
    vtuber_sex = hps.ai_vtuber.sex
    vtuber_setting = hps.ai_vtuber.setting
    emotion_score = hps.ai_vtuber.emotion
    main()