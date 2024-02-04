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

def create_chat_completion(model, messages,zhipu_api_use,use_stream=False):
    if zhipu_api_use:
        response = zhipu_api(messages[0]["content"])
        result = response.replace(r"\n", "")
        return result
    else:
        base_url = "http://127.0.0.1:8000"  # 本地部署的地址,或者使用你访问模型的API地址
        data = {
            "model": model, # 模型名称
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


def zhipu_api(content):
    client = ZhipuAI(api_key=zhipu_key)  # 填写您自己的APIKey
    response = client.chat.completions.create(
        model="glm-3-turbo",  # 填写需要调用的模型名称
        messages=[
            {"role": "user", "content": content}
        ],
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

