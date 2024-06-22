from func.chat import chat_api
import json
import utils
from zhipuai import ZhipuAI


hps = utils.get_hparams_from_file("configs/json/config.json")
api_key = hps.api_path.llm_api.zhipuai_key

client = ZhipuAI(api_key=api_key)
messages = []
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_search",
            "description": "搜索或查询某个问题的答案",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "description": "用户的问题",
                        "type": "string"
                    }
                },
                "required": ["query"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_weather_by_location",
            "description": "查询某城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "description": "城市名",
                        "type": "string"
                    }
                },
                "required": ["city_name"]
            },
        }
    },
]

# 根据地区获取当前天气
def get_current_weather_by_location(city_name: str):
    print("天气函数被调用了")
    if not isinstance(city_name, str):
        raise TypeError("City name must be a string")

    key_selection = {
        "current_condition": ["temp_C", "FeelsLikeC", "humidity", "weatherDesc", "observation_time"],
    }
    import requests
    try:
        resp = requests.get(f"https://wttr.in/{city_name}?format=j1")
        resp.raise_for_status()
        resp = resp.json()
        ret = {k: {_v: resp[k][0][_v] for _v in v} for k, v in key_selection.items()}
    except:
        import traceback
        ret = "Error encountered while fetching weather data!\n" + traceback.format_exc()

    return str(ret)

def query_search(query:str):
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


def parse_function_call(model_response,messages):
    # 处理函数调用结果，根据模型返回参数，调用对应的函数。
    # 调用函数返回结果后构造tool message，再次调用模型，将函数结果输入模型
    # 模型会将函数调用结果以自然语言格式返回给用户。
    if model_response.choices[0].message.tool_calls:
        tool_call = model_response.choices[0].message.tool_calls[0]
        args = tool_call.function.arguments
        function_result = {}
        if tool_call.function.name == "query_search":
            function_result = query_search(**json.loads(args))
        elif tool_call.function.name == "get_current_weather_by_location":
            function_result = get_current_weather_by_location(**json.loads(args))
        messages.append({
            "role": "tool",
            "content": f"{json.dumps(function_result)}",
            "tool_call_id":tool_call.id
        })
        response = client.chat.completions.create(
            model="glm-3-turbo",  # 填写需要调用的模型名称
            messages=messages,
            tools=tools,
        )
        print("最终回答:",response.choices[0].message.content)
        messages.append({"role": "assistant", "content": response.choices[0].message.content})

def agent_to_study(query:str):
    split_parts = query.split(":", 1)
    extracted_part = split_parts[1]
    agent_prompt = "我想让你成为我的知识点整理员,你需要按照我的要求把内容存入字典中。你的目标是帮助我整理最佳的知识点信息,这些知识点将为你提供信息参考。你将遵循以下过程：1.首先，你会问我知识点是关于什么的。我会告诉你，但我们需要通过不断的重复来完善它，通过则进行下一步。2.根据我的输入，你会创建三个部分：a)修订整理后的知识点(你整合汇总后的信息，你不要随意删除之前已经提取的信息，应该清晰、精确、易于理解，拥有严谨的输出格式并给出标签，应当包含之前提取的所有有关信息块)b)问答对(你需要将a中整理的已有信息转换成问答对)c)问题(你提出相关问题，询问我需要哪些额外信息来补充进a中你整理的信息)3.我们将继续这个迭代过程我会提供更多的信息。你会更新“修订后的，你整理的信息'’部分的请求，直到它完整为止。"
    messages = [
        {"role": "user", "content": agent_prompt},
        {"role": "user", "content": query}
    ]
    messages.append({"role": "user", "content": extracted_part})
    while True:
        print("messages:",messages[-1]["content"])
        query = chat_api.zhipu_api("请你提取出下段文本中用户的问题:" + messages[-1]["content"])
        print("当前问题:", query)
        result = query_search(query)
        messages.append({"role": "user", "content": result})
        chat_messages = [
            {"role": "user", "content": agent_prompt+"我提供的信息如下:"+messages[-1]["content"]+messages[-2]["content"]}
        ]
        result = chat_api.zhipu_api(chat_messages[0]["content"])
        messages.append({"role": "user", "content": result})
        print(f"\033[31m[代理学习汇总：]\033[0m{result}")
        please = input("按s保存，按q退出，按g人为提供问题：")
        if please == "s":
            with open(f"chroma_database/text/{extracted_part}.txt","w",encoding="utf-8") as f:
                f.write(result)
            please = input("输入0退出,按其余任意键退出：")
            if please == "0":
                break
        elif please == "q":
            break
        elif please == "g":
            knowledge = chat_api.zhipu_api("请你提取出下段文本中已经整理好的知识点，不可随意删减，格式要保持一致，删除和忽略里面的问题:" + messages[-1]["content"])
            messages[-1]["content"] = knowledge+input("请你提供学习方向:")



def main(messages):
    print("main_messages:",messages)
    current_query_lst = [messages[-1]]
    print("query:",current_query_lst[-1]["content"])
    response = client.chat.completions.create(
        model="glm-3-turbo",  # 填写需要调用的模型名称
        messages=current_query_lst,
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "query_search"}},
    )
    print(response.choices[0].message)
    messages.append({"role": "assistant", "content": response.choices[0].message.content})
    parse_function_call(response, messages)

if __name__ == '__main__':
    content = input("请输入:")
    chat_messages = [
        {"role": "user", "content": content}
    ]
    main(chat_messages)

