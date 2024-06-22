import time
import pandas as pd
import requests
import streamlit as st
from func.agent import tools
import matplotlib.pyplot as plt
from streamlit_webrtc import webrtc_streamer
import subprocess
import utils
import json
import os
from tqdm import tqdm

project_root = os.path.dirname(os.path.abspath(__file__))[:-2]

def get_properties():
    # 文件路径
    file_path = "template/json/template.json"
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as file:
        node_properties = json.load(file)
    return node_properties


def save_properties_to_file(properties):
    file_path = "template/json/template.json"
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump({}, file)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(properties, file)

def create_form(data,key_path = []):
    for key, value in data.items():
        current_key_path = key_path + [key]
        if isinstance(value, str):
            if key == "default_model":
                from func.chat.chat_api import model_list
                data[key] = st.selectbox(key, model_list, index=0)
                continue
            user_input = st.text_input('.'.join(current_key_path), value=value,placeholder=value if value else "请输入字符串...")
            if user_input:
                data[key] = user_input
        elif isinstance(value, int):
            user_input = st.number_input('.'.join(current_key_path), value=value,placeholder=value if value else "请输入整数...", step=1,
                                         format="%d")
            if user_input is not None:
                data[key] = user_input
        elif isinstance(value, float):
            user_input = st.number_input('.'.join(current_key_path), value=value,
                                         placeholder=value if value else "请输入小数...")
            if user_input is not None:
                data[key] = user_input
        elif isinstance(value, bool):
            data[key] = st.checkbox('.'.join(current_key_path), value)
        elif isinstance(value, list):
            value = "每行一个列表项..." if not value else '\n'.join(map(str, value))
            placeholder = "每行一个列表项..." if not value else '\n'.join(map(str, value))
            list_items = st.text_area('.'.join(current_key_path), value=value,placeholder=placeholder)
            if list_items:
                data[key] = list_items.split('\n')
        elif isinstance(value, dict):
            # 对于字典，递归地创建表单
            create_form(value, current_key_path)
        else:
            st.write(f"Unsupported data type: {type(value)}")


def env_configuration(default_file_path="configs/json/config.json"):
    """
    管理和安装运行环境
    Returns:

    """
    t1,t2 = st.tabs(["虚拟环境管理","虚拟主播配置"])
    with t1:
        e_select = st.selectbox("创建或更新虚拟环境：", ["创建新虚拟环境", "选择已有虚拟环境"], index=1)
        if e_select == "选择已有虚拟环境":
            folder_path = os.path.join(project_root, "requirements")
            file_names = os.listdir(folder_path)
            file_name_list = [file_name for file_name in file_names]
            selected_requirement = st.selectbox("选择环境依赖配置文件：", file_name_list, index=0)
            mirror_source_list = [
                "https://pypi.tuna.tsinghua.edu.cn/simple/",
                "http://mirrors.aliyun.com/pypi/simple/",
                "https://pypi.mirrors.ustc.edu.cn/simple/",
                "http://pypi.hustunique.com/simple/",
                "https://mirror.sjtu.edu.cn/pypi/web/simple/",
                "http://pypi.douban.com/simple/"
            ]
            mirror_source = st.selectbox("选择镜像源：", mirror_source_list, index=0)
            folder_contents = os.listdir("runtime\miniconda3\envs")
            envs_name = [f for f in folder_contents if os.path.isdir(os.path.join("runtime\miniconda3\envs", f))]
            env_name = st.selectbox("选择虚拟环境：", envs_name, index=0)
            if st.button("安装依赖"):
                command = f"{project_root}\\runtime\\miniconda3\\envs\\{env_name}\\python.exe -m pip install -r {project_root}\\requirements\\{selected_requirement} -i {mirror_source}"
                subprocess.Popen(['start', 'cmd', '/k', command], shell=True)
                st.write(command)
            c = st.text_input("安装指定包:",placeholder="pip install ...")
            if st.button("安装依赖",key=1):
                command = f"{project_root}\\runtime\\miniconda3\\envs\\{env_name}\\python.exe -m {c} -i {mirror_source}"
                subprocess.Popen(['start', 'cmd', '/k', command], shell=True)
                st.write(command)
        elif e_select == "创建新虚拟环境":
            new_env_name = st.text_input("请输入待创建虚拟环境名称:")
            new_python_version = st.text_input("请输入待创建虚拟环境python版本:", placeholder="3.10")
            if st.button("新建虚拟环境"):
                command = f"{project_root}\\runtime\\miniconda3\\Scripts\\conda.exe create --name {new_env_name} python={new_python_version} -y"
                subprocess.Popen(['start', 'cmd', '/k', command], shell=True)
    with t2:
        s = st.selectbox("请选择需要进行的操作",["新建config","修改config"],index=1)
        if s == "新建config":
            default_file_path="configs/json/config.example.json"
        try:
            data = utils.load_json(default_file_path)
            st.write(project_root)
            select_key = st.selectbox("选择需要编辑的组", list(data.keys()), index=0)
            with st.form("config编辑"):
                st.write(select_key)
                create_form(data[select_key])
                if st.form_submit_button("保存"):
                    utils.write_json(data,"configs/json/config.json")
                    st.success("保存成功")
        except FileNotFoundError:
            st.error(f"默认文件 '{default_file_path}' 不存在。")
        except Exception as e:
            st.error(f"读取默认文件时出错: {e}")



def main_page(hps,role_hps):
    st.set_page_config(
        page_title='AI-Vtuber',
        layout="wide",
        page_icon='assets/icon/ComfyUI_00011_.png',
        initial_sidebar_state="expanded",
        menu_items={
            'Get help': "http://www.worldline-fantasy.top",
            'Report a bug': "https://space.bilibili.com/287906485?spm_id_from=333.1007.0.0",
            'About': "http://www.worldline-fantasy.top"
        }
    )
    with st.sidebar:
        st.sidebar.image("assets/icon/image.gif", caption='放着好看！', use_column_width=True)
        st.title('AI-VTuber')
        st.markdown('项目作者:这就是天幻呀')
        st.markdown("[博客官网](http://www.worldline-fantasy.top)")
        st.markdown("[GitHub项目主页](https://github.com/whoiswennie/AI-Vtuber)")
        st.markdown("[哔哩哔哩主页](https://space.bilibili.com/287906485)")
        st.markdown('---')
        page = st.sidebar.radio("页面导航", ["配置环境","AI-VTuber","个性定制"])
    if page == "配置环境":
        env_configuration()
    elif page == "AI-VTuber":
        with st.expander("一键启动脚本管理"):
            bats_path = None
            bat_select = st.selectbox("选择项目的一键启动脚本：", ["选择待启动的服务","配置一键启动脚本"], index=0)
            if bat_select == "配置一键启动脚本":
                bat_select_2 = st.selectbox("新增（修改）或删除脚本:", ["新增（修改）脚本","删除脚本"], index=0)
                with open("configs/json/bat_start.json", 'r', encoding='utf-8') as file:
                    data = json.load(file)
                if bat_select_2 == "新增（修改）脚本":
                    bat_names = [item['bat_name'] for item in data if "bat_name" in item]
                    bat_name_select = st.selectbox("选择项目的一键启动脚本：", bat_names, index=0)
                    if bat_name_select:
                        st.write([item["bat_path"] for item in data if item["bat_name"] == bat_name_select][0])
                    bat_name = st.text_input("请输入一键启动脚本的项目名称:")
                    bat_path = st.text_input("请输入bat脚本的绝对路径:", placeholder="例如:D:/so-vits-svc/api.bat")
                    bat_dict = {"bat_name":bat_name,"bat_path":bat_path}
                    if st.button("保存"):
                        if bat_name in bat_names:
                            for item in data:
                                if item["bat_name"] == bat_name and bat_path != None:item["bat_path"] = bat_path
                            with open("configs/json/bat_start.json", 'w', encoding='utf-8') as file:
                                json.dump(data,file, ensure_ascii=False, indent=4)
                        else:
                            data.append(bat_dict)
                            with open("configs/json/bat_start.json", 'w', encoding='utf-8') as file:
                                json.dump(data,file, ensure_ascii=False, indent=4)
                        st.success("保存成功")
                elif bat_select_2 == "删除脚本":
                    d_bat_name = st.multiselect(
                        "选择你需要删除的脚本:",
                        [item for item in data ]
                    )
                    if st.button("删除"):
                        data = [item for item in data + d_bat_name if item not in data or item not in d_bat_name]
                        with open("configs/json/bat_start.json", 'w', encoding='utf-8') as file:
                            json.dump(data, file, ensure_ascii=False, indent=4)
                        st.success("删除成功")
            elif bat_select == "选择待启动的服务":
                with open("configs/json/bat_start.json", 'r', encoding='utf-8') as file:
                    data = json.load(file)
                bat_names = [item['bat_name'] for item in data if "bat_name" in item]
                bats_start = st.multiselect(
                    "选择你需要开启的服务:",
                    bat_names
                )
                bats_path = [item["bat_path"] for item in data if item["bat_name"] in bats_start]
            st.markdown("---")
            col0, col1, col2, col3, col4 = st.columns(5)
            with col0:
                if st.button("一键启动bat"):
                    if bats_path is not None:
                        for p in bats_path:
                            print(p)
                            try:
                                command = f'cd /d "{os.path.dirname(p)}" && start "" "{p}"'
                                subprocess.Popen(command, shell=True)
                                st.success(f"成功启动脚本: {p}")
                            except FileNotFoundError:
                                st.error(f"脚本未找到: {p}")
                            except subprocess.CalledProcessError as e:
                                st.error(f"脚本执行出错: {p}，错误代码: {e.returncode}")
                            except Exception as e:
                                st.error(f"启动脚本时发生未知错误: {p}，错误信息: {str(e)}")
                    else:
                        st.warning("没有可用的BAT脚本路径。")
            with col1:
                if st.button("开启直播"):
                    ACCESS_KEY_ID = hps.bilibili.blivedm.ACCESS_KEY_ID
                    ACCESS_KEY_SECRET = hps.bilibili.blivedm.ACCESS_KEY_SECRET
                    APP_ID = hps.bilibili.blivedm.APP_ID
                    ROOM_OWNER_AUTH_CODE = hps.bilibili.blivedm.ROOM_OWNER_AUTH_CODE
                    command_1 = f'{project_root}\\runtime\\miniconda3\\envs\\ai-vtuber\\python.exe blivedm_api.py -AKI {ACCESS_KEY_ID} -AKS {ACCESS_KEY_SECRET} -AI {APP_ID} -ROAC {ROOM_OWNER_AUTH_CODE}'
                    command_2 = f'{project_root}\\runtime\\miniconda3\\envs\\ai-vtuber\\python.exe bilibili_main.py'
                    subprocess.Popen(['start', 'cmd', '/k', command_1], shell=True)
                    subprocess.Popen(['start', 'cmd', '/k', command_2], shell=True)
                    st.success("直播已开始")
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
                if st.button("启动flask服务端"):
                    st.success("flask服务端启动成功")
                    command = f'{project_root}\\runtime\\miniconda3\\envs\\ai-vtuber\\python.exe flask_ai_vtuber_api.py'
                    subprocess.Popen(['start', 'cmd', '/k', command], shell=True)
            with col4:
                if st.button("判断所有端口是否启动"):
                    import socket
                    urls = [
                        {"flask服务端": "http://0.0.0.0:9550"},
                        {"so_vits_svc_api": hps.api_path.so_vits_svc.url},
                        {"bert_vits2_api": hps.api_path.bert_vits2.url},
                        {"gpt_sovits_api": hps.api_path.gpt_sovits.url},
                        {"easy_ai_vtuber_api": hps.api_path.easy_ai_vtuber.url},
                        {"neo4j_api": hps.api_path.neo4j.url}
                    ]

                    def is_port_in_use(host, port):
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
                        host, port = utils.extract_port_and_url(api_url)
                        if is_port_in_use(host, port):
                            st.success(f"{api_name} 端口 {port} 已启动")
                        else:
                            st.error(f"{api_name} 端口 {port} 未启动")
        with st.expander("测试AI-VTuber"):
            selected_options = st.multiselect(
                "选择你需要开启的模块:",
                ["语音", "数字人驱动"]
            )
            s_m_1 = False
            s_m_2 = False
            easyaivtuber_img = None
            tts_plan = [0,1]
            action_type = "speak"
            st.write("当前已开启的模块:")
            for select_module in selected_options:
                st.success(select_module)
                if "语音" == select_module:
                    s_m_1 = True
                    tts_plan = st.selectbox("请选择语音合成方案:", ["1.edge-tts+svc", "2.GPT-SoVITS"], index=1)
                elif "数字人驱动" == select_module:
                    s_m_2 = True
            if s_m_2:
                action_type = st.radio(
                    "请选择一个选项:",
                    ["speak", "rhythm", "sing"]
                )
                st.write("您选择的选项:", action_type)
                webrtc_streamer(
                    key="video_streamer",
                    media_stream_constraints={
                        "video": {
                            "width": 1920,  # 设置视频宽度
                            "height": 1080,  # 设置视频高度
                            "frameRate": 60,  # 设置帧率
                            "aspectRatio": 1.777777778,  # 设置宽高比（16:9）
                            "deviceId": None  # 设置摄像头设备ID，None表示自动选择
                        },
                        "audio": False
                    }
                )
            role_keys_hps = utils.get_hparams_from_file("configs/json/role_setting.json").keys()
            role = st.selectbox("请你选择聊天的角色模板:",list(role_keys_hps),index=0)
            if s_m_2:
                easyaivtuber_img_dir_path = role_hps.get(role).easyaivtuber_dir_path
                if easyaivtuber_img_dir_path:
                    png_files = [f for f in os.listdir(easyaivtuber_img_dir_path) if f.endswith('.png')]
                    easyaivtuber_img = st.selectbox("请选择主播的形象图",png_files,index=0)
            knowledge_database = hps.ai_vtuber.knowledge_database
            select_databases = st.multiselect("请你选择参考知识库", knowledge_database)
            if st.button("选择该角色的模板"):
                data_role = {"role_key":role,"tts_plan":int(tts_plan[0]),"easyaivtuber_img":easyaivtuber_img,"knowledge_databases":[database_dict["name"] for database_dict in select_databases]}
                res = requests.post('http://localhost:9550/switch_role', json=data_role)
                if res.status_code == 200:st.success("角色模板切换成功")
            st.write("---")
            st.write("本次对话")
            if_memory = st.checkbox("是否启动AI-VTuber记忆")
            if not if_memory:if_memory = False
            user_input = st.text_input("输入您的消息:", "")
            if 'memory_list' not in st.session_state:
                st.session_state.memory_list = [{"query":"","answer":""}]
            if st.button("发送"):
                with st.spinner('任务运行中...'):
                    status_placeholder = st.empty()
                    data_agent_to_do = {"content": user_input,"memory":if_memory}
                    res = requests.post(f'http://localhost:9550/agent_to_do', json=data_agent_to_do).json()
                    st.write("参考信息:", res["refer_information"])
                    st.session_state.memory_list.append({"query":user_input,"answer":res["content"]})
                    stream_bar = st.progress(0)
                    placeholder = st.empty()
                    # 模拟流式输出
                    status_placeholder.text("正在流式输出！")
                    for i in range(len(res["content"])):
                        # 更新容器中的文本
                        placeholder.text_area("AI-Vtuber:", value=res["content"][:i + 1], key=i)
                        stream_bar.progress((i+1)/len(res["content"]))
                        time.sleep(0.01)
                    if res["songlist"]:
                        st.write("当前播放列表:",res["songlist"])
                    if s_m_1:
                        data_tts = {"tts_plan": int(tts_plan[0]), "text": res["content"], "AudioCount": 1}
                        response = requests.post('http://localhost:9550/tts', json=data_tts).json()
                        status_placeholder.text("已发送语音合成指令！")
                        data_tts_play = {"wav_path": response["path"]}
                        if s_m_2:
                            data_action = {"type": action_type, "speech_path": data_tts_play["wav_path"]}
                            response = requests.post("http://127.0.0.1:7888/alive", json=data_action)
                            status_placeholder.text("已发送数字人动作参数！")
                            if response.status_code == 200:
                                st.success("INFO:easy_ai_vtuber_api请求成功")
                        else:
                            requests.post('http://localhost:9550/mpv_play', json=data_tts_play)
            memory_list_choose = st.sidebar.selectbox("选择聊天记录:", st.session_state.memory_list,index=0)
            if memory_list_choose:
                st.write("---")
                st.write("历史回复")
                placeholder_user = st.empty()
                placeholder_vtuber = st.empty()
                for i in range(len(memory_list_choose["query"])):
                    placeholder_user.text_area("user:", value=memory_list_choose["query"][:i + 1], key=f"user_{i}")
                    time.sleep(0.001)
                for j in range(len(memory_list_choose["answer"])):
                    placeholder_vtuber.text_area("AI-Vtuber:", value=memory_list_choose["answer"][:j + 1], key=f"AI-Vtuber_{j}")
                    time.sleep(0.001)
        with st.expander("实用小工具"):
            t1,t2,t3,t4 = st.tabs(["下载","语音识别","人声分离","语音合成"])
            with t1:
                if "download_files" not in st.session_state:
                    st.session_state.download_files = None
                c1,c2,c3 =st.columns(3)
                d_url,d_index,d_format = None,1,"wav"
                with c1:
                    d_url = st.text_input("请输入网址链接：")
                with c2:
                    d_index = st.text_input("请输入下载序号：")
                with c3:
                    d_format = st.selectbox("文件类型",["wav","mp4"],index=0)
                if st.button("开始下载") or st.session_state.download_files:
                    if d_url:
                        download_data = {"url":d_url,"index":d_index,"format":d_format}
                        st.write("本次请求:",download_data)
                        download_list = requests.post('http://localhost:9550/tool/download_from_url', json=download_data).json()
                        st.session_state.download_files = download_list
                        if download_list:
                            if d_format == "wav":
                                select_audio = st.selectbox("选中的音频",download_list,index=0)
                                st.audio(select_audio)
                                if st.button("删除该音频"):
                                    if os.path.exists(select_audio):
                                        os.remove(select_audio)
                                        st.session_state.download_files = None
                                        st.success(f"文件 {select_audio} 已被删除。")
                                    else:
                                        st.warning(f"文件 {select_audio} 不存在。")
                            elif d_format == "mp4":
                                select_video = st.selectbox("选中的视频",download_list,index=0)
                                st.video(select_video)
                                if st.button("删除该视频"):
                                    if os.path.exists(select_video):
                                        os.remove(select_video)
                                        st.session_state.download_files = None
                                        st.success(f"文件 {select_video} 已被删除。")
                                    else:
                                        st.warning(f"文件 {select_video} 不存在。")
                if st.button("打开缓存文件夹"):
                    subprocess.run(['explorer', os.path.abspath(os.path.join(project_root, "template/downloads"))])
            with t2:
                audio_file = st.file_uploader("Upload an audio file", type=["wav", "mp3", "flac"])
                if audio_file is not None:
                    st.audio(audio_file.read(), format=audio_file.type)
                    language = st.selectbox("语言",["自动","zh","en","ja"],index=0)
                    if language == "自动":language =None
                    file_path = os.path.join("template/uploads", audio_file.name)
                    with open(file_path, "wb") as f:
                        f.write(audio_file.getbuffer())
                    if st.button("语音识别"):
                        with st.spinner("语音识别中，请耐心等待......"):
                            data = {"input_path": file_path,"language":language}
                            res = requests.post(f'http://localhost:9550/tool/faster_whisper', json=data)
                            st.write(res.json()["text"])
            with t3:
                device = st.selectbox("运行设备:",["cuda","cpu"])
                is_half_precision = st.selectbox("半精度计算:",[True,False])
                port = st.number_input("运行端口:",value=9660)
                if_share = st.selectbox("是否启动一个在线的端口:",[True,False],index=1)
                if st.button("打开uvr5的webui"):
                    command = f"{project_root}\\runtime\\miniconda3\\envs\\uvr5\\python.exe tools/uvr5/webui.py {device} {is_half_precision} {port} {if_share}"
                    subprocess.Popen(['start', 'cmd', '/k', command], shell=True)

            with t4:
                tts_plan = st.selectbox("请选择语音合成方案:", ["1.edge-tts+svc", "2.GPT-SoVITS"], index=1,key="tts")
                text = st.text_input("请输入需要合成的文本:")
                if st.button("语音合成",key=f"tts_{1}"):
                    data_tts = {"tts_plan": int(tts_plan[0]), "text": text, "AudioCount": 1}
                    response = requests.post('http://localhost:9550/tts', json=data_tts).json()
                    st.audio(response["path"], format='audio/wav')

    elif page == "个性定制":
        choose = st.selectbox("请选择个性定制方向:", ["认知定制", "功能定制"], index=0)
        if choose == "认知定制":
            y_please = st.selectbox("请选择:", ["人设定制","neo4j数据库操作台(需要启动neo4j数据库)"], index=0)
            st.write("---")
            if y_please == "人设定制":
                t1,t2,t3 = st.tabs(["config配置文件", "知识库管理","txt转neo4j"])
                with t1:
                    col_1,col_2 = st.columns(2)
                    role_keys_hps = role_hps.keys()
                    if_del = col_1.selectbox("是否需要删除角色模板:", [True,False], index=1)
                    if if_del:
                        role_del = col_2.selectbox("请你选择待删除的角色模板:", list(role_keys_hps), index=0)
                        if role_del == "默认模板":
                            st.error("禁止删除默认模板")
                        else:
                            if st.button("删除角色模板") and role_del != "默认模板":
                                role_mod = utils.load_json("configs/json/role_setting.json")
                                del role_mod[role_del]
                                utils.write_json(role_mod, "configs/json/role_setting.json")
                                st.success("角色模板删除成功")
                    edge_tts_voice, so_vits_svc_model, so_vits_svc_config, gpt_sovits_model = "", "", "", ""
                    from func.tts import tts_voices
                    col1, col2, col3, col4 = st.columns(4)
                    name_input = col1.text_input("姓名",placeholder="默认模板")
                    if not name_input:name_input="默认模板"
                    if role_hps.get(name_input) == None:
                        role_json = utils.get_hparams_from_dict(role_hps.get("默认模板"))
                    else:
                        role_json = utils.get_hparams_from_dict(role_hps.get(name_input))
                    sex_input = col2.text_input("性别",placeholder=role_json.sex)
                    age_input = col3.text_input("年龄",placeholder=role_json.age)
                    emotion_input = col4.text_input("情绪值",placeholder=role_json.emotion)
                    setting_input = st.text_input("角色设定",placeholder=role_json.setting)
                    emo_col1, emo_col2, emo_col3, emo_col4, emo_col5 = st.columns(5)
                    emotional_display_prompt_list = role_json.emotional_display
                    emotional_display_prompt_list[0] = emo_col1.text_input("0.悲伤",placeholder=role_json.emotional_display[0])
                    emotional_display_prompt_list[1] = emo_col2.text_input("1.焦虑",placeholder=role_json.emotional_display[1])
                    emotional_display_prompt_list[2] = emo_col3.text_input("2.平静",placeholder=role_json.emotional_display[2])
                    emotional_display_prompt_list[3] = emo_col4.text_input("3.开心",placeholder=role_json.emotional_display[3])
                    emotional_display_prompt_list[4] = emo_col5.text_input("4.激动",placeholder=role_json.emotional_display[4])
                    tts_plan = st.selectbox("请选择语音合成方案",["plan_1:edge-tts+svc","plan_2:gpt-sovits"],index=0)[0:6]
                    if tts_plan == "plan_1":
                        col5, col6 = st.columns(2)
                        edge_tts_voice = role_json.tts.plan_1.edge_tts
                        if edge_tts_voice in tts_voices.SUPPORTED_LANGUAGES:
                            default_index = tts_voices.SUPPORTED_LANGUAGES.index(edge_tts_voice)
                        else:
                            default_index = 0
                        edge_tts_voice = col5.selectbox("请选择edge-tts音色:", tts_voices.SUPPORTED_LANGUAGES, index=default_index)
                        text = col6.text_input("请输入音色测试语句:","")
                        if st.button("edge-tts音色测试"):
                            tts_voices.to_edge_tts(text,edge_tts_voice,"template/tts/demo.mp3")
                            st.audio("template/tts/demo.mp3", format='audio/mp3')
                        col7, col8 = st.columns(2)
                        so_vits_svc_model = col7.text_input("输入so-vits-svc模型绝对路径",placeholder=role_json.tts.plan_1.so_vits_svc)
                        so_vits_svc_config = col8.text_input("输入so-vits-svc配置文件绝对路径",placeholder=role_json.tts.plan_1.so_vits_svc_config)
                    elif tts_plan == "plan_2":
                        gpt_sovits_model = st.text_input("输入gpt-sovits模型绝对路径",placeholder=role_json.tts.plan_2.gpt_sovits)
                    easyaivtuber_img_dir_path = role_json.easyaivtuber_dir_path
                    easyaivtuber_img_path = st.text_input("请输入easyaivtuber数字人形象路径(.png)",placeholder=easyaivtuber_img_dir_path)
                    if not sex_input:sex_input=role_json.sex
                    if not age_input:age_input=role_json.age
                    if not emotion_input:emotion_input=role_json.emotion
                    if not setting_input:setting_input=role_json.setting
                    if not edge_tts_voice:edge_tts_voice=role_json.tts.plan_1.edge_tts
                    if not so_vits_svc_model:so_vits_svc_model=role_json.tts.plan_1.so_vits_svc
                    if not so_vits_svc_config:so_vits_svc_config=role_json.tts.plan_1.so_vits_svc_config
                    if not gpt_sovits_model:gpt_sovits_model=role_json.tts.plan_2.gpt_sovits
                    if not easyaivtuber_img_path:easyaivtuber_img_path=role_json.easyaivtuber_dir_path
                    st.write("---")
                    if st.button("保存角色配置"):
                        st.write(name_input)
                        if name_input != "默认模板":
                            role_hps = utils.load_json("configs/json/role_setting.json")
                            role_hps.get("默认模板")["name"] = name_input
                            role_hps.get("默认模板")["setting"] = setting_input
                            role_hps.get("默认模板")["sex"] = sex_input
                            role_hps.get("默认模板")["age"] = age_input
                            role_hps.get("默认模板")["emotional_display"] = emotional_display_prompt_list
                            role_hps.get("默认模板")["emotion"] = emotion_input
                            role_hps.get("默认模板")["tts"]["plan_1"]["edge_tts"] = edge_tts_voice
                            role_hps.get("默认模板")["tts"]["plan_1"]["so_vits_svc"] = so_vits_svc_model
                            role_hps.get("默认模板")["tts"]["plan_1"]["so_vits_svc_config"] = so_vits_svc_config
                            role_hps.get("默认模板")["tts"]["plan_2"]["gpt_sovits"] = gpt_sovits_model
                            role_hps.get("默认模板")["easyaivtuber_dir_path"] = easyaivtuber_img_path
                            role_dict = utils.load_json("configs/json/role_setting.json")
                            role_dict[name_input] = role_hps.get("默认模板")
                            utils.write_json(role_dict,"configs/json/role_setting.json")
                            st.success("人设模型已更新")
                        else:
                            st.error("禁止修改默认模板")
                with t2:
                    knowledge_databases = hps.ai_vtuber.knowledge_database
                    select_database = st.selectbox("请选择知识库:",knowledge_databases,index=0)
                    if select_database == "歌库":
                        if st.button("更新歌库（需要启动neo4j服务）"):
                            with st.spinner('任务运行中...'):
                                from func.Neo4j_Database import make_song_n4j
                                from func.Neo4j_Database import to_neo4j
                                neo = to_neo4j.Neo4jHandler("configs/json/config.json")
                                neo.connect_neo4j_database()
                                neo.delete_nodes_for_label("歌库")
                                st.success("删除成功")
                                make_song_n4j.song_dict_to_neo4j(song_dict_path = "data/json/song_dict.json",song_csv_path = "configs/csv/歌库.csv",config_path = "configs/json/config.json")
                        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
                        if uploaded_file is not None:
                            data = pd.read_csv(uploaded_file, encoding="gbk")
                            edited_data = st.data_editor(data)
                            if st.button("Save Edited CSV"):
                                edited_csv = edited_data.to_csv(index=False)
                                st.download_button(
                                    label="Download Edited CSV",
                                    data=edited_csv,
                                    file_name="edited_data.csv",
                                    mime="text/csv"
                                )
                        else:
                            st.write("Please upload a CSV file.")
                    else:
                        st.title(f"当前知识库:{list(select_database.keys())[0]}")
                        introduction = st.text_input("添加当前知识库的介绍:")
                        d_col1, d_col_2 = st.columns(2)
                        if d_col1.button("保存配置"):
                            config_data = utils.load_json("configs/json/config.json")
                            config_data["ai_vtuber"]["knowledge_database"] = [
                                {k: introduction if k == f'{list(select_database.keys())[0]}' else v for k, v in d.items()}
                                for d in config_data["ai_vtuber"]["knowledge_database"]
                            ]
                            utils.write_json(config_data, "configs/json/config.json")
                            st.success("知识库已更新")
                with t3:
                    uploaded_file = st.file_uploader("上传TXT文件", type="txt")
                    if uploaded_file is not None:
                        if os.path.exists(os.path.join("template/txt", uploaded_file.name)):
                            with open(os.path.join("template/txt", uploaded_file.name), "wb") as f:
                                f.write(uploaded_file.getbuffer())
                        file_content = uploaded_file.read().decode("utf-8")
                        d_select = st.selectbox("请选择知识库制作方案:",["知识图谱","向量数据库"],index=0)
                        if d_select == "知识图谱":
                            s_select = st.selectbox("请选择切片方式",["按字数切分","按qa行分割"])
                            if s_select == "按字数切分":
                                segment_number = st.slider('选择一个数字:', 0, 1000, value = 100)
                                segments = utils.split_text_by_length(file_content, segment_number)
                            elif s_select == "按qa行分割":
                                segments = utils.read_qa_from_txt(os.path.join("template/txt", uploaded_file.name))
                                segments = [segment['question']+segment['answer'] for segment in segments]
                            st.write("切片:", segments)
                            information_extraction = []
                            node_name_col1,introduction_col2 = st.columns(2)
                            node_name = node_name_col1.text_input("请输入本次学习的标签:",key="node_name")
                            introduction = introduction_col2.text_input("添加当前知识库的介绍:",key="introduction")
                            if st.button("开始信息抽取"):
                                if not introduction:introduction = ""
                                t_ = 0  # 成功计数器
                                e_ = 0  # 错误计数器
                                total_segments = len(segments)
                                progress = st.progress(0)
                                for i, segment in enumerate(segments, 1):
                                    flag,res = tools.information_extraction(segment)
                                    res = [res]
                                    res.insert(0, node_name)
                                    if flag == "success":
                                        tools.information_to_neo4j(res)
                                        t_ += 1
                                    else:
                                        e_ += 1
                                        information_extraction.append(segment)
                                        st.write(res)
                                    progress.progress(i / total_segments)
                                config_data = utils.load_json("configs/json/config.json")
                                config_data["ai_vtuber"]["knowledge_database"].append({"name":f"{node_name}", "introduction":introduction,"plan":0})
                                utils.write_json(config_data, "configs/json/config.json")
                                error_log_json_string = json.dumps(information_extraction)
                                with open('template/json/error_log.json', 'w', encoding='utf-8') as f:
                                    f.write(error_log_json_string)
                                with open('template/txt/error_log.txt', 'a', encoding='utf-8') as f:
                                    if s_select == "按qa行分割":
                                        for qa in information_extraction:
                                            f.write(qa)
                                    else:
                                        for qa in information_extraction:
                                            f.write(qa)
                                st.write(f"成功处理了 {t_} 个段，{e_} 个段处理出错。")
                        elif d_select == "向量数据库":
                            segment_number = st.slider('选择一个数字:', 0, 1000, value=100)
                            segments = utils.split_text_by_length(file_content, segment_number)
                            st.write("切片:", segments)
                            node_name_col1, introduction_col2 = st.columns(2)
                            node_name = node_name_col1.text_input("请输入本次学习的标签:", key="node_name")
                            introduction = introduction_col2.text_input("添加当前知识库的介绍:", key="introduction")
                            if st.button("生成向量数据库"):
                                data_dict = {"uploaded_file_name":uploaded_file.name,"node_name":node_name,"segment_number":segment_number,"introduction":introduction}
                                response = requests.post('http://localhost:9550/tts', json=data_dict).json()
                                if response.status_code == 200:
                                    st.success("存储完毕")
                                else:
                                    st.error("出现异常")

                    else:
                        st.text("请上传一个TXT文件")
                    expander_del = st.expander("删除指定节点标签组")
                    expander_del.header("删除指定节点标签组")
                    label_name = expander_del.text_input("请输入需要删除的节点标签组:")
                    if expander_del.button("删除该节点标签组"):
                        from func.Neo4j_Database import to_neo4j
                        neo = to_neo4j.Neo4jHandler("configs/json/config.json")
                        neo.connect_neo4j_database()
                        neo.delete_nodes_for_label(label_name)
                        config_data = utils.load_json("configs/json/config.json")
                        config_data["ai_vtuber"]["knowledge_database"] = [d for d in config_data["ai_vtuber"]["knowledge_database"] if label_name not in d]
                        utils.write_json(config_data, "configs/json/config.json")
                        st.success("删除成功")
                    with st.expander("测试"):
                        uploaded_file = st.file_uploader("上传测试TXT文件", type="txt")
                        if uploaded_file is not None:
                            question_numbers = []
                            similarities_used = []
                            similarities_unused = []
                            if os.path.exists(os.path.join("template/txt", uploaded_file.name)):
                                with open(os.path.join("template/txt", uploaded_file.name), "wb") as f:
                                    f.write(uploaded_file.getbuffer())
                            segments = utils.read_qa_from_txt(os.path.join("template/txt", uploaded_file.name))
                            if st.button("开始测试"):
                                save_json = []
                                progress_bar = st.progress(0)
                                with tqdm(total=len(segments), desc="正在测试中", unit="问题", ascii=False, ncols=80) as pbar:
                                    for index, segment in enumerate(segments):
                                        query = segment["question"]
                                        answer = segment["answer"]
                                        data_search_in_neo4j = {"content": query}
                                        res = requests.post('http://localhost:9550/search_in_neo4j',
                                                            json=data_search_in_neo4j)
                                        data_chat = {"query": query, "reference_text": str(res.json())}
                                        bot_response = requests.post('http://localhost:9550/chat', json=data_chat).text
                                        similarity_used = tools.qa_judge(answer, bot_response)
                                        similarities_used.append(similarity_used)

                                        data_chat_without_reference = {"query": query}
                                        bot_response_without_reference = requests.post('http://localhost:9550/chat',
                                                                                       json=data_chat_without_reference).text
                                        similarity_unused = tools.qa_judge(answer, bot_response_without_reference)
                                        similarities_unused.append(similarity_unused)

                                        question_numbers.append(index)
                                        save_dict = {"问题": query, "正确答案": answer, "回答(used)": bot_response,
                                                     "相似度(used)": similarity_used,
                                                     "回答(unused)": bot_response_without_reference,
                                                     "相似度(unused)": similarity_unused}
                                        save_json.append(save_dict)
                                        pbar.update(1)
                                        progress = (index + 1) / len(segments)
                                        progress_bar.progress(progress)
                                save_json_string = json.dumps(save_json)
                                with open('template/json/save_log.json', 'w', encoding='utf-8') as f:
                                    f.write(save_json_string)
                                plt.figure(figsize=(10, 5))
                                plt.plot(question_numbers, similarities_used, 'go-',
                                         label='With Reference')  # 绿色点表示similarity_used
                                plt.plot(question_numbers, similarities_unused, 'ro-',
                                         label='Without Reference')  # 红色点表示similarity_unused
                                plt.title('Answer Similarity')
                                plt.xlabel('Question Number')
                                plt.ylabel('Similarity')
                                plt.legend()
                                plt.grid(True)
                                st.pyplot(plt)
                                plt.savefig("template/imgs/chart.png")
                        if st.button("展示测试日志"):
                            st.image("template/imgs/chart.png")
                            with open('template/json/save_log.json', 'r', encoding='utf-8') as f:
                                save_log = json.load(f)
                            count = sum(1 for item in save_log if abs(item["相似度(used)"] - item["相似度(unused)"]) <= 5 or item["相似度(used)"] >= item["相似度(unused)"])
                            st.write(f"相似度(used)更优或差距在5分以内的比例为: {(count/len(save_log))*100}%")
                            st.write(save_log)

            elif y_please == "neo4j数据库操作台(需要启动neo4j数据库)":
                p = st.text_input("【用户认证】请输入以下内容:", placeholder="清空图数据库")
                neo4j_url = hps.api_path.neo4j.url
                url, port = utils.extract_port_and_url(neo4j_url)
                if st.button("清空图数据库（请先关闭neo4j服务）"):
                    if not utils.check_port(url, port) and (p=="清空图数据库"):
                        import shutil
                        try:
                            shutil.rmtree("tools/neo4j-chs-community-4.2.2-windows/data/databases/neo4j")
                            shutil.rmtree("tools/neo4j-chs-community-4.2.2-windows/data/transactions/neo4j")
                            print(f"Folder 'tools/neo4j-chs-community-4.2.2-windows/data/databases/neo4j' has been deleted.")
                        except FileNotFoundError:
                            print(f"Folder 'tools/neo4j-chs-community-4.2.2-windows/data/transactions/neo4j' does not exist.")
                        except Exception as e:
                            print(f"An error occurred while deleting : {e}")
                        st.success("图数据库已清空")
                    else:
                        st.error("请先关闭neo4j服务")
                if utils.check_port(url, port):
                    from func.Neo4j_Database import to_neo4j
                    neo_db = to_neo4j.Neo4jHandler("configs/json/config.json")
                    neo_db.connect_neo4j_database()
                    if st.button('打开Neo4j浏览器'):
                        st.write(f'[打开Neo4j浏览器](http://localhost:7474/browser/)')
                    please = st.selectbox("请选择功能:",["增添节点","设置关系","查询节点","查询关联节点","修改节点","删除节点"],index=0)
                    if please == "增添节点":
                        input_node_name = st.text_input("输入节点名称:","")
                        input_node_properties_name = st.text_input("输入节点属性名称:")
                        input_node_properties_value = st.text_input("输入节点属性值:")
                        node_properties = get_properties()
                        if st.button("添加属性"):
                            if input_node_properties_name and input_node_properties_value:
                                node_properties[input_node_properties_name] = input_node_properties_value
                                save_properties_to_file(node_properties)
                                st.success("属性添加成功！")
                            else:
                                st.error("请输入属性名称和值。")

                        selected_properties = st.multiselect("选择要操作的属性:", list(node_properties.keys()),
                                                             default=list(node_properties.keys()))
                        if st.button("删除属性"):
                            for property_name in selected_properties:
                                del node_properties[property_name]
                            save_properties_to_file(node_properties)
                            st.success("属性删除成功！")
                        st.write("当前属性：", get_properties())
                        if st.button("添加节点"):
                            node_properties = get_properties()
                            neo_db.add_node(input_node_name,node_properties)
                            st.success("节点创建完毕")
                    elif please == "设置关系":
                        node1_name = st.text_input("输入节点1名称:","")
                        node1_list = neo_db.search_node(node1_name) if node1_name else []
                        node2_name = st.text_input("输入节点2名称:","")
                        node2_list = neo_db.search_node(node2_name) if node2_name else []
                        nodes1 = st.selectbox("请选择节点1:", json.loads(json.dumps(node1_list)), index=0)
                        nodes2 = st.selectbox("请选择节点2:", json.loads(json.dumps(node2_list)), index=0)
                        relationship_name = st.text_input("输入关系名称:","")
                        relationship_properties = st.text_input("输入关系属性","")
                        if not relationship_properties: relationship_properties = "{}"
                        if st.button("创建关系（节点1-->节点2）"):
                            nodes1 = neo_db.search_node(node1_name,nodes1["node"])
                            nodes2 = neo_db.search_node(node2_name,nodes2["node"])
                            neo_db.set_relationship(nodes1[0]["node"], nodes2[0]["node"], relationship_name, properties=json.loads(relationship_properties))
                            st.success("关系创建完毕")
                    elif please == "查询节点":
                        query_type = st.selectbox("请选择查询方式:",["按名称选择","按名称、属性查询"],index=0)
                        input_node_name = st.text_input("输入节点名称:", "")
                        if query_type == "按名称选择":
                            nodes = neo_db.search_node(input_node_name) if input_node_name else None
                            nodes_list = to_neo4j.nodes_to_json(nodes) if nodes else []
                            select_node = st.selectbox("请选择节点",nodes_list,index=0)
                            if st.button("查询"):
                                print(select_node)
                                query_node = to_neo4j.json_to_nodes(input_node_name,[select_node],config_path="configs/json/config.json")
                                st.write(query_node)
                        elif query_type == "按名称、属性查询":
                            input_node_properties_name = st.text_input("输入节点属性名称:")
                            input_node_properties_value = st.text_input("输入节点属性值:")
                            node_properties = get_properties()
                            if st.button("添加属性"):
                                if input_node_properties_name and input_node_properties_value:
                                    node_properties[input_node_properties_name] = input_node_properties_value
                                    save_properties_to_file(node_properties)

                                    st.success("属性添加成功！")
                                else:
                                    st.error("请输入属性名称和值。")
                            selected_properties = st.multiselect("选择要操作的属性:", list(node_properties.keys()),
                                                                 default=list(node_properties.keys()))
                            if st.button("删除属性"):
                                for property_name in selected_properties:
                                    del node_properties[property_name]
                                save_properties_to_file(node_properties)
                                st.success("属性删除成功！")
                            if st.button("查询"):
                                result = neo_db.search_node(input_node_name, node_properties)
                                st.write(result)

                    elif please == "查询关联节点":
                        input_node_name = st.text_input("输入节点名称:", "")
                        input_node_relationship_type = st.text_input("输入关系类型:", "")
                        nodes = neo_db.search_node(input_node_name) if input_node_name else None
                        nodes_list = to_neo4j.nodes_to_json(nodes) if nodes else []
                        select_node = st.selectbox("请选择节点", nodes_list, index=0)
                        if st.button("查询关联节点"):
                            query_node = to_neo4j.json_to_nodes(input_node_name, [select_node],
                                                                config_path="configs/json/config.json")
                            result = neo_db.find_related_nodes(query_node[0]["node"], input_node_relationship_type)
                            st.write(result)


                    elif please == "删除节点":
                        node_name = st.text_input("输入待删除的节点名称:", "")
                        node_list = neo_db.search_node(node_name) if node_name else []
                        del_node = st.selectbox("请选择待删除的节点:", json.loads(json.dumps(node_list)), index=0)
                        if st.button("删除节点"):
                            del_node = neo_db.search_node(node_name, del_node["node"])
                            st.write(del_node[0])
                            neo_db.delete_node(del_node[0]["node"])
                            st.success("节点删除成功")
            else:
                input_keyword = st.text_input("输入关键词名称:", "")
                st.write(input_keyword)

def main():
    hps = utils.get_hparams_from_file("configs/json/config.json")
    role_hps = utils.get_hparams_from_file("configs/json/role_setting.json")
    main_page(hps,role_hps)

if __name__ == '__main__':
    main()