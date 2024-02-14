# 使用curl命令测试返回
# curl -X POST "http://127.0.0.1:8000/v1/chat/completions" \
# -H "Content-Type: application/json" \
# -d "{\"model\": \"chatglm3-6b\", \"messages\": [{\"role\": \"system\", \"content\": \"You are ChatGLM3, a large language model trained by Zhipu.AI. Follow the user's instructions carefully. Respond using markdown.\"}, {\"role\": \"user\", \"content\": \"你好，给我讲一个故事，大概100字\"}], \"stream\": false, \"max_tokens\": 100, \"temperature\": 0.8, \"top_p\": 0.8}"

# 使用Python代码测返回
import requests
import threading
import json
import utils
from zhipuai import ZhipuAI

file_lock = threading.Lock()

hps = utils.get_hparams_from_file("configs/config.json")
zhipu_key = hps.api_path.llm_api.zhipuai_key

def create_chat_completion(llm_model, messages,use_stream=False):
    '''

    :param llm_model: 你选择的大语言模型【推荐智谱api，当前支持智谱api和本地部署的chatglm3-6b模型】
    :param messages: [{"role":"","content":""},...]
    :param use_stream: 是否采用流式响应，默认关闭
    :return:
    '''
    if llm_model == "zhipu_api":
        response = zhipu_api(messages)
        result = response.replace(r"\n", "")
        return result
    elif llm_model == "chatglm3-6b":
        base_url = "http://127.0.0.1:8000"  # 本地部署的地址,或者使用你访问模型的API地址
        data = {
            "model": "chatglm3-6b", # 模型名称
            "messages": messages, # 会话历史
            "stream": use_stream, # 是否流式响应
            "max_tokens": 1011, # 最多生成字数
            "temperature": 0.8, # 温度
            "top_p": 0.8, # 采样概率
        }

        response = requests.post(f"{base_url}/v1/chat/completions", json=data, stream=use_stream)
        if response.status_code == 200:
            if use_stream:
                # 处理流式响应
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')[6:]
                        try:
                            response_json = json.loads(decoded_line)
                            content = response_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            print(content)
                        except:
                            print("Special Token:", decoded_line)
            else:
                # 处理非流式响应
                decoded_line = response.json()
                #print(decoded_line)
                content = decoded_line.get("choices", [{}])[0].get("message", "").get("content", "")
                #print(content)
                return content
        else:
            print("Error:", response.status_code)
            return None


def zhipu_api(messages):
    client = ZhipuAI(api_key=zhipu_key)  # 填写您自己的APIKey
    response = client.chat.completions.create(
        model="glm-3-turbo",  # 填写需要调用的模型名称
        messages=messages,
    )
    #print(response.choices[0].message.content)
    return response.choices[0].message.content


def send_file(file_path):
    client = ZhipuAI(api_key=zhipu_key)  # 请填写您自己的APIKey

    result = client.files.create(
        file=open(file_path, "rb"),
        purpose="fine-tune"
    )
    print(result.id)
    client.files.list()

def tool_database(content):
    client = ZhipuAI(api_key=zhipu_key) # 请填写您自己的APIKey
    response = client.chat.completions.create(
        model="glm-3-turbo",  # 填写需要调用的模型名称
        messages=[
            {"role": "user", "content": content},
        ],
        tools=[
                {
                    "type": "retrieval",
                    "retrieval": {
                        "knowledge_id": "1749745894347124736",
                        "prompt_template":"从文档\n\n{{knowledge}}\n\n中找问题\n\n{{content}}\n\n的答案，找到答案就仅使用文档语句回答，找不到答案就用自身知识回答并告诉用户该信息不是来自文档。\n不要复述问题，直接开始回答。"
                    }
                }
                ],
        stream=False,
    )
    result = response.choices[0].message.content
    #print(result)
    return content,result

#send_file("dataset/converted_data.jsonl")
# content,result = tool_database("任务是干什么？")
# print("最终回复:",zhipu_api(f"本次用户的问题是：{content}，请你参考下面你的知识库来筛选有效信息来回答本次用户的问题：{result}"))
if __name__ == '__main__':
    import re
    import os
    import subprocess
    import shutil
    import datetime
    import chroma_database


    def set_emotion(score):
        global emotion_state
        with open('configs/config.json', encoding="utf-8", mode='r') as f:
            data = json.load(f)
        emotion_score = data["ai_vtuber"]["emotion"]
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
    hps = utils.get_hparams_from_file("configs/prompt.json")
    emotion_score = 82
    template_role_play = hps.template_role_play
    summary_message = hps.summary_message
    emotion_state = set_emotion(0)
    role_json = {
        "角色名称":"幻",
        "角色性别":"女",
        "角色年龄": 17,
        "角色当前情绪":f"{emotion_state}，因为你刚刚获得了哔哩哔哩2024年的百大up主。",
        "你需要扮演的角色设定":"你是一个生活在虚拟世界的少女名字叫幻，其他人喜欢叫你幻酱，你的职业是一个擅长唱歌的虚拟主播，你的性格活泼，是一个有礼貌，并且热情开朗的人类女孩。现在正在跟观众互动，当观众有问题时，你需要结合有用的信息来回复观众们的问题。"
    }
    #messages = [{"role": "system", "content": template_role_play+str(role_json)}]
    client = ZhipuAI(api_key=zhipu_key)  # 填写您自己的APIKey
    if os.path.exists("chroma_database/database/logs"):
        shutil.rmtree("chroma_database/database/logs")
    while 1:
        content = input("user:")
        memory = chroma_database.search_in_db("chroma_database/database/logs",content,k_lin=3)
        #messages.append({"role": "user", "content": {"你之前的历史聊天记录:":memory, "用户本次的问题:":content}})
        import study_for_memory
        keyword, score, result = study_for_memory.search_from_memory(content)
        if score == "None":
            score = 0
        emotion_state = set_emotion(score)
        messages = [
            {"role": "system", "content": template_role_play + str(role_json) + "你之前的聊天记录:"+memory},
            {"role": "user", "content": "你可以结合目前已有的信息来回答下面字典中用户的问题，你回复的格式是一个标准的字符串:"+str({f"用户本次问题涉及到的你可能认识的关键词{keyword}的信息":result,"用户本次的问题:": content})},
        ]
        response = client.chat.completions.create(
            model="glm-3-turbo",  # 填写需要调用的模型名称
            messages=messages,
        )
        #messages.append({"role": "assistant", "content": response.choices[0].message.content})
        print("huan:",response.choices[0].message.content)
        print(messages)
        time1 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ques = f"观众：{content}"
        answer = f"幻：{response.choices[0].message.content}"
        pattern = r'(.*?)【.*?】'  # 匹配并保留【】外的内容
        matches = re.findall(pattern, response.choices[0].message.content)
        # 打印提取到的内容
        result = ""
        for match in matches:
            result += match
        # 定义请求参数
        url = "http://127.0.0.1:8080"
        params = {
            "refer_wav_path": r"C:\Users\32873\Desktop\ai\tts\GPT-SoVITS-TTS\output\sanyueqi-撒娇.wav",
            "text": result,
            "text_language": "zh"
        }
        # 发送 GET 请求
        response = requests.get(url, params)
        # 检查响应状态码
        if response.status_code == 200:
            # 将音频流写入临时文件
            with open("temp.wav", "wb") as f:
                f.write(response.content)
            import make_song_n4j
            duration = make_song_n4j.get_duration_ffmpeg("temp.wav")
            subprocess.run(
                f'mpv.exe -vo null --volume=100 --start=0 --end={duration} "{"temp.wav"}" 1>nul',
                shell=False,
            )
            print("INFO 响应成功")
        with file_lock:
            with open("./logs/logs.txt", "a", encoding="utf-8") as f:  # 将问答写入logs
                f.write(
                    f"[{time1}]{ques}\n[{time1}] {answer}\n\n"
                )
        chroma_database.make_db("./logs/logs.txt","chroma_database/database/logs",chunk_size=200)

