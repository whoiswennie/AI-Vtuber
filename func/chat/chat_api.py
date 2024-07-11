import requests
import threading
import json
import utils
import time
model_list = ["glm-4-0520","glm-4","glm-4-air","glm-4-airx","glm-4-flash","glm-3-turbo"]

file_lock = threading.Lock()

hps = utils.get_hparams_from_file("configs/json/config.json")
default_glm_model = hps.ai_vtuber.default_model
zhipu_key = hps.api_path.llm_api.zhipuai_key
qwen_key = hps.api_path.llm_api.qwen_key
formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print(f"[{formatted_time}]INFO 正在加载语言基座模型服务，当前选用模型为:{default_glm_model}")
def create_chat_completion(llm_model, messages, use_stream=False,response_str = True):
    '''

    :param llm_model: 你选择的大语言模型【推荐智谱api，当前支持智谱api和本地部署的chatglm3-6b模型】
    :param messages: [{"role":"","content":""},...]
    :param use_stream: 是否采用流式响应，默认关闭
    :return:
    '''
    if llm_model == "zhipu_api":
        response = zhipu_api(messages,response_str=response_str)
        if response_str == True:
            response = response.replace(r"\n", "")
        return response
    elif llm_model == "":
        response = qwen_api(messages)
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


def zhipu_api(messages,tools=None,response_str=True,model=default_glm_model):
    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key=zhipu_key)  # 填写您自己的APIKey
    response = client.chat.completions.create(
        model=model,  # 填写需要调用的模型名称
        messages=messages,
        tools=tools,
    )
    #print(response.choices[0].message.content)
    if response_str:
        return response.choices[0].message.content
    else:
        return response


def qwen_api(messages,tools=None,response_str=True,model="qwen-long"):
    from openai import OpenAI
    client = OpenAI(
        api_key=qwen_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 填写DashScope服务endpoint
    )
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=False
    )
    if response_str:
        return response.choices[0].message.content
    else:
        return response



