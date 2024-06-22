import json
from zhipuai import ZhipuAI
client = ZhipuAI(api_key="2df9b5a8edf8a789fac6a61a057988fe.MXfEFv0UNxGtG2pk")
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
        if tool_call.function.name == "get_current_weather_by_location":
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
        print(response.choices[0].message)
        messages.append(response.choices[0].message.model_dump())

messages.append({"role": "user", "content": "帮我查询上海的天气"})
response = client.chat.completions.create(
    model="glm-3-turbo",  # 填写需要调用的模型名称
    messages=messages,
    tools=tools,
)
print(response.choices[0].message)
messages.append(response.choices[0].message.model_dump())
print("response:",response,"messages:",messages)
parse_function_call(response, messages)