# -*- coding: utf-8 -*-

import utils
from func.Neo4j_Database import to_neo4j
from collections import Counter


class Node:
    def __init__(self, category, name, value):
        self.category = category
        self.name = name
        self.value = value

    def __eq__(self, other):
        return self.name == other.name and self.value == other.value

    def __hash__(self):
        return hash((self.name, self.value))

    def __repr__(self):
        return f"Node({self.category}, {self.name}, {self.value})"

def find_common_nodes(lists):
    if not lists:
        return []

    # Count occurrences of each node
    node_counter = Counter()
    for node_list in lists:
        node_set = set(node_list)  # Convert list to set to avoid counting duplicates in the same list
        node_counter.update(node_set)

    # Find nodes that appear in all lists
    common_nodes = [node for node, count in node_counter.items() if count == len(lists)]

    return common_nodes

def remove_duplicates(lst):
    # 创建一个新列表来存储结果
    result = []
    # 遍历原始列表
    for i, item_i in enumerate(lst):
        # 假设当前元素的value没有出现在其他元素的value中
        found = False
        # 再次遍历列表，检查其他元素的value
        for j, item_j in enumerate(lst):
            # 跳过当前元素
            if i == j:
                continue
            # 检查当前元素的value是否出现在其他元素的value中
            if item_i['value'] in item_j['value']:
                found = True
                break
        # 如果当前元素的value没有出现在其他元素的value中，将其添加到结果列表
        if not found:
            result.append(item_i)
    return result
def similar(a, b):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()
def extract_from_dict(input_str, data_dict, similarity_threshold=0.4):
    result = []
    for key, values in data_dict.items():
        for value in values:
            if not value:
                continue
            if key.lower() == '歌名':
                # 如果key是歌名，则使用模糊搜索
                if similar(value, input_str) >= similarity_threshold:
                    result.append({"name": key, "value": value})
            else:
                # 其他key则使用原始的精确匹配
                if value in input_str:
                    result.append({"name": key, "value": value})
    #print(result)
    filtered_list = remove_duplicates(result)
    return filtered_list

def get_song_information_dicts(content,song_dict_path = "../../data/json/song_dict.json"):
    song_dict = utils.load_json(song_dict_path)
    return extract_from_dict(content,song_dict)

def search_song_from_neo4j(content,config_path = "../../configs/json/config.json",song_dict_path = "../../data/json/song_dict.json"):
    song_information_list = get_song_information_dicts(content,song_dict_path)
    print("\033[32m查询到的歌名列表:\033[0m",song_information_list)
    neo = to_neo4j.Neo4jHandler(config_path)
    search_lst = []
    songlist = []
    songinformationlist = []
    for item in song_information_list:
        if item["name"] == "歌名":
            node = neo.search_node("歌库", item)[0]["node"]
            find_node = neo.find_related_nodes(node,"歌曲关系")
            search_lst.append([node])
            songinformationlist.append({"歌名":item["value"],"歌曲信息":[{find_node[i]["name"]: find_node[i]["value"]} for i in range(len(find_node))]})
            songlist.append(item["value"])
        else:
            node = neo.search_node("歌库",item)[0]["node"]
            search_lst.append(neo.find_related_nodes(node,"歌曲关系"))
            common_nodes = find_common_nodes(search_lst)
            for song in common_nodes:
                songlist.append(song["value"])
    #print(songinformationlist)
    return songinformationlist,songlist

if __name__ == '__main__':
    search_song_from_neo4j("我想听我不曾忘记")

