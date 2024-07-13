import json
import re
import requests
from func.chat import chat_api
import utils
from tqdm import tqdm

intention_recognition_list = [
    {
        "type":"function",
        "function": {
            "name": "chat",
            "description": "聊天",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "description": "聊天消息队列",
                        "type": "string"
                    }
                },
                "required": ["query"]
            },
        }
    },
    {
        "type":"function",
        "function": {
            "name": "get_information",
            "description": "获取信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "description": "需要查询的内容",
                        "type": "string"
                    }
                },
                "required": ["content"]
            },
        }
    }
]
common_information_retrieval_tools = [
    {
        "type": "function",
        "function": {
            "name": "query_search",
            "description": "联网搜索相关信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "description": "需要查询的关键词",
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

def intention_recognition(content):
    """
    用以判断用户的意图
    Args:
        content: 用户的问题

    Returns:

    """
    intention_recognition_prompt = """
    你是一个判断模型，没有回答问题的能力，只能用来理解用户的的意图，并且以Json格式输出你判断的结果，禁止回复多余的内容。
    你当前能够识别的意图类型只能包括[chat，sing，draw，search]
    chat:正常聊天（只要不属于其他的意图类型，那么都为chat意图）;
    sing:用户希望你进行唱歌;
    draw:用户希望你进行画画;
    search:用户需要你查询某些信息;
    你输出的Json格式应当为:
    {
        "intention_type":"你识别的意图类型"
    }
    """
    chat_messages = [
        {
            "role": "system",
            "content": intention_recognition_prompt
        },
        {
            "role": "user",
            "content": f"请你按照上述的角色设定来回答下面用户的问题:{content}"
        }
    ]
    response = chat_api.zhipu_api(messages=chat_messages)
    try:
        json_str = re.sub(r"```json\n", "", response).rstrip("`\n")
        response = json.loads(json_str)
    except json.decoder.JSONDecodeError:
        response = {"intention_type":"chat"}
    print("\033[33m当前识别的意图类型:\033[0m",response["intention_type"])
    return response

def problem_analysis (content):
    problem_analysis_prompt = f"""
    你需要理解并分析，如果需要解决用户的问题，你需要完成哪些任务，你拆解的子任务应当十分精炼。
    你应当将你的疑问以字符串的形式存储在一个列表中进行输出，你回复的内容只允许包含这个列表，禁止输出多余内容！！！
    用户的问题为:{content}。
    """
    chat_messages = [
        {
            "role": "user",
            "content": problem_analysis_prompt
        }
    ]
    response = chat_api.zhipu_api(messages=chat_messages)
    return response

def information_supplementation_judgment(information,query):
    information_supplementation_judgment = f"""
    你需要判断<>中的信息是否能够回答用户本次的问题，并且以Json格式输出，禁止回答多余的内容。
    **其中如果<>中说明了无法回答用户问题，或表达出否定、不确定、需要用户自己动手的意思，那么本次判断的结果为False（表示该信息不能回答用户本次的问题）。**
    你输出的Json应当包含一个键：judgment。
    judgment：本次判断的结果（你需要严格遵守**中的规定。），值为True或False（要求str类型,首字母大写）。
    你当前能够参考的信息：<{information}>。
    用户本次的问题：{query}。
    """
    chat_messages = [
        {
            "role": "user",
            "content": information_supplementation_judgment
        }
    ]
    response = chat_api.zhipu_api(messages=chat_messages)
    json_str = re.sub(r"```json\n", "", response).rstrip("`\n")
    response = json.loads(json_str)
    return response

def qa_judge(correct_answer,user_answer):
    from fuzzywuzzy import fuzz
    similarity = fuzz.ratio(correct_answer, user_answer)
    return similarity

def merge_dicts(dict1, dict2):
    import copy
    nodes1 = dict1['nodes']
    nodes2 = dict2['nodes']
    merged_nodes = copy.deepcopy(nodes1)
    name_to_index = {node['value']: node['id'] for node in merged_nodes}
    next_id = len(merged_nodes)
    for node in nodes2:
        if node['value'] not in name_to_index:
            new_node = copy.deepcopy(node)
            new_node['id'] = next_id
            merged_nodes.append(new_node)
            name_to_index[node['value']] = next_id
            next_id += 1
    for index, node in enumerate(merged_nodes):
        node['id'] = index
        name_to_index[node['value']] = index
    merged_properties = []
    for prop in dict1['properties']:
        new_prop = copy.deepcopy(prop)
        new_prop['node_start'] = name_to_index[nodes1[prop['node_start']]['value']]
        if 'node_end' in new_prop:
            new_prop['node_end'] = name_to_index[nodes1[prop['node_end']]['value']]
        merged_properties.append(new_prop)
    for prop in dict2['properties']:
        new_prop = copy.deepcopy(prop)
        new_prop['node_start'] = name_to_index[nodes2[prop['node_start']]['value']]
        if 'node_end' in new_prop:
            new_prop['node_end'] = name_to_index[nodes2[prop['node_end']]['value']]
        merged_properties.append(new_prop)
    merged_dict = {'nodes': merged_nodes, 'properties': merged_properties}
    return merged_dict

def information_extraction(content):
    information_extraction_prompt = """
    You are an AI expert specializing in knowledge graph creation with the goal of capturing relationships based on a given input or request.
    Based on the user input in various forms such as paragraph, email, text files, and more.
    Your task is to create a knowledge graph based on the input.
    Nodes must have a name parameter ,a value paramerter and id parameter. where the name is the category of the direct word or phrase from the input the value is a direct word or phrase from the input and id is used to represent the serial number of the node.
    Properties contain the relationships between generated nodes in nodes, such as the structure in the following example.
    Each element of properties should be a key value pair. Among them, node_start represents the head node, and its value should be the id value of a dictionary in the nodes group. 
    Node_end represents the node pointed to by the head node, and its value should also be the id value of a dictionary in the nodes group. 
    The relationship represents the relationship between node-start and node-end.
    The information you extract in JSON should be consistent with the language of the source text, but the keys should be consistent with the format I require.
    You need to strictly follow the example format provided below for output: {"nodes":[
            {"name":"该实体的类型(语言同源文本一致)","value":"你抽取的实体1","id":0},
            {"name":"该实体的类型(语言同源文本一致)","value":"你抽取的实体2","id":1},
            ...
        ],
    "properties":[
            {"node_start":0,"node_end":1,"relationship":"id0与id1之间的关系"},
            ...
        ]
    }
    Make sure the target and source of relationship match an existing node.
    """+f"你需要提取的内容：<{content}>"
    chat_messages = [
        {
            "role": "user",
            "content": information_extraction_prompt
        }
    ]
    response = chat_api.zhipu_api(messages=chat_messages)
    print("response:",response)
    try:
        pattern = r"json\n(.+?)\n```"
        json_str = re.findall(pattern, response, re.DOTALL)[0]
        json_data = json.loads(json_str)
        # print("json_data:", json_data)
        # print("json_data_type:", type(json_data))
        return "success",json_data
    except IndexError:
        json_data = json.loads(response)
        return "success", json_data
    except json.decoder.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        return "error",{"state_code":"JSONDecodeError","content":content}

def information_extraction_old(node_name,content):
    information_extraction_prompt = """
    你需要整理提取出<>中的信息，并以Json格式输出,其中键值对的值只能为字符串，不能包含别的数据类型，禁止回答除Json外多余的内容。
    请你自动的忽略和删除原文中的序号、特殊字符以及一些标记类文字,以免存入节点时发生错误.
    你整理后输出的Json的格式应该为：[{"name": "节点1的名称", "value":"节点1对应的值"},{"name": "节点2的名称", "value":"节点2对应的值"},...]。
    """+f"你需要提取的内容：<{content}>"
    chat_messages = [
        {
            "role": "user",
            "content": information_extraction_prompt
        }
    ]
    response = chat_api.zhipu_api(messages=chat_messages)
    try:
        json_str = re.sub(r"```json\n", "", response).rstrip("`\n")
        json_data = [json.loads(json_str)]
        json_data.insert(0, node_name)
        print("json_data:", json_data)
        print("json_data_type:", type(json_data))
        if_neo4j_json = utils.is_valid_json_format(json_data)
        if if_neo4j_json:
            return "success",json_data
        else:
            return "error",{"state_code":"Json格式不符合要求","data":json_data,"content":content}
    except json.decoder.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        return "error",{"state_code":"JSONDecodeError","content":content}

def information_to_neo4j(data):
    from func.Neo4j_Database import to_neo4j
    neo = to_neo4j.Neo4jHandler("configs/json/config.json")
    neo.connect_neo4j_database()
    id_to_name = {node['id']: node['name'] for node in data[1]['nodes']}
    id_to_value = {node['id']: node['value'] for node in data[1]['nodes']}
    formatted_nodes = [{'name': node['name'], "value": node['value']} for node in data[1]['nodes']]
    for node in tqdm(formatted_nodes, desc="创建节点中..."):
        neo.add_node(data[0],node)
    formatted_properties = [
        [{'name': id_to_name[prop['node_start']], "value": id_to_value[prop['node_start']]},
         {'name': id_to_name[prop['node_end']], "value": id_to_value[prop['node_end']]}, prop['relationship']]
        for prop in data[1]['properties']
    ]
    for node in tqdm(formatted_properties, desc="创建关系中..."):
        node1 = neo.search_node(data[0],node[0])[0]["node"]
        node2 = neo.search_node(data[0],node[1])[0]["node"]
        neo.set_relationship(node1,node2,data[0], {"name":node[2]})
    return True

def search_in_database(query):
    # 函数实现
    return "Database result for " + query

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
    response = chat_api.zhipu_api(messages=current_query_lst,tools=[
            {
                "type": "web_search",
                "web_search": {
                    "enable": True,
                    "search_result": True
                }
            }
        ],response_str=False)
    print(f"\033[31m[代理搜索汇总中：]\033[0m{response.choices[0].message.content}")
    return response.choices[0].message.content

# def parse_function_call(model_response,messages):
#     # 处理函数调用结果，根据模型返回参数，调用对应的函数。
#     # 调用函数返回结果后构造tool message，再次调用模型，将函数结果输入模型
#     # 模型会将函数调用结果以自然语言格式返回给用户。
#     if model_response.choices[0].message.tool_calls:
#         tool_call = model_response.choices[0].message.tool_calls[0]
#         args = tool_call.function.arguments
#         function_result = {}
#         if tool_call.function.name == "query_search":
#             function_result = query_search(**json.loads(args))
#         if tool_call.function.name == "get_current_weather_by_location":
#             function_result = get_current_weather_by_location(**json.loads(args))
#         messages.append({
#             "role": "tool",
#             "content": f"{json.dumps(function_result)}",
#             "tool_call_id":tool_call.id
#         })
#         response = chat_api.zhipu_api(messages,common_information_retrieval_tools,False)
#         print(response.choices[0].message.content)
#         messages.append(response.choices[0].message.model_dump())


def parse_function_call(model_response, messages, function_dict):
    # 处理函数调用结果，根据模型返回参数，调用对应的函数。
    # 调用函数返回结果后构造tool message，再次调用模型，将函数结果输入模型
    # 模型会将函数调用结果以自然语言格式返回给用户。
    if model_response.choices[0].message.tool_calls:
        tool_call = model_response.choices[0].message.tool_calls[0]
        function_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        # 如果函数名在function_dict中，则调用对应的函数
        if function_name in function_dict:
            function = function_dict[function_name]
            function_result = function(**args)
            messages.append({
                "role": "tool",
                "content": json.dumps(function_result),
                "tool_call_id": tool_call.id
            })
            response = chat_api.zhipu_api(messages,tools=common_information_retrieval_tools,response_str=False)
            messages.append(response.choices[0].message.model_dump())
            return response.choices[0].message.content

function_dict = {}
# 遍历 common_information_retrieval_tools 列表
for tool in common_information_retrieval_tools:
    # 获取函数名
    function_name = tool["function"]["name"]
    function_dict[function_name] = locals()[function_name]
#print("function_dict:", function_dict)

def search_in_tools(content,tools):
    memory_messages = []
    used_tools_dict = []
    filtered_tools = tools
    if_flag = False
    messages = [
        {
            "role": "user",
            "content": "你必须选择下面提供的一个工具，优先选择最有用的(若存在工具则必须选择一个)，若工具栏为空时，则输出字符串：None。"+content
        }
    ]
    data_search_in_neo4j = {"content": content}
    res = requests.post(f'http://localhost:9550/search_in_neo4j', json=data_search_in_neo4j)
    memory_messages.append(str(res.json()))

    while not if_flag:
        print("filtered_tools:",filtered_tools)
        print("function_dict:",function_dict)
        response = chat_api.zhipu_api(messages, tools=filtered_tools, response_str=False)
        if response.choices[0].message.tool_calls:
            print(response.choices[0].message.tool_calls)
            select_tool_name = response.choices[0].message.tool_calls[0].function.name
            used_tools_dict.append(response.choices[0].message.tool_calls[0].function.name)
            messages.append(response.choices[0].message.model_dump())
            response = parse_function_call(response, messages, function_dict)
            memory_messages.append(response)
            result = information_supplementation_judgment(memory_messages,content)
            print("result:",result)
            if result["judgment"] == "True":
                print(memory_messages)
                return memory_messages
            else:
                filtered_tools = [tool for tool in common_information_retrieval_tools if tool['function']['name'] != select_tool_name]
            function_dict.pop(select_tool_name)
        else:
            print(response.choices[0].message.tool_calls)
            print(memory_messages)
            return memory_messages
