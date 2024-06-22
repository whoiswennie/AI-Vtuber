import csv
import utils
from func.Neo4j_Database import to_neo4j
from tqdm import tqdm


def check_dict_in_dict(dict_a, dict_b):
    key_name = dict_a['name']
    value = dict_a['value']

    # 检查键名是否存在于字典b中
    if key_name in dict_b:
        # 如果字典b中的值是列表，检查value是否在列表中
        if isinstance(dict_b[key_name], list):
            return value in dict_b[key_name]
        # 如果字典b中的值是单个值，直接比较
        else:
            return dict_b[key_name] == value
    return False

def make_song_dict(csv_file_path,song_dict_path):
    # 用于存储数据的字典
    data_dict = {}
    # 读取CSV文件
    with open(csv_file_path, 'r', encoding='gbk') as csv_file:
        csv_reader = csv.reader(csv_file)
        # 读取标签行
        labels = next(csv_reader)
        # 初始化字典
        for label in labels:
            data_dict[label] = []
        # 读取数据行
        for row in csv_reader:
            for label, value in zip(labels, row):
                # 检查值中是否包含逗号
                if '，' in value:
                    # 如果包含中文逗号，拆分数据
                    sub_values = [sub_value.strip() for sub_value in value.split('，')]
                    # 遍历拆分后的数据
                    for sub_value in sub_values:
                        # 检查是否已经存储过该值
                        if sub_value not in data_dict[label]:
                            data_dict[label].append(sub_value)
                elif ',' in value:
                    # 如果包含英文逗号，拆分数据
                    sub_values = [sub_value.strip() for sub_value in value.split(',')]
                    # 遍历拆分后的数据
                    for sub_value in sub_values:
                        # 检查是否已经存储过该值
                        if sub_value not in data_dict[label]:
                            data_dict[label].append(sub_value)
                else:
                    # 检查是否已经存储过该值
                    if value not in data_dict[label]:
                        data_dict[label].append(value)
    utils.write_json(data_dict,song_dict_path)
    return data_dict

def parse_csv_to_dict_list(file_path):
    dict_list = []
    with open(file_path, 'r', encoding='gbk') as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            song_info = {}
            for key, value in row.items():
                if value:  # 如果值不为空
                    # 检查是否有中文逗号分隔的多个元素
                    if '，' in value:
                        song_info[key] = value.split('，')
                    else:
                        song_info[key] = value
                else:
                    song_info[key] = []
            dict_list.append(song_info)
    return dict_list

def song_dict_to_neo4j(song_dict_path = "../../data/json/song_dict.json",song_csv_path = "../../configs/csv/歌库.csv",config_path = "../../configs/json/config.json"):
    song_dicts = utils.load_json(song_dict_path)
    song_nodes_no_name = []
    song_nodes_with_name = []
    neo = to_neo4j.Neo4jHandler(config_path)
    song_tags = list(song_dicts.keys())[1:]
    # 添加所有节点
    for tag in song_tags:
        tag_lists = song_dicts[tag]
        for item in tag_lists:
            if item == "":
                continue
            neo.add_node("歌库",{"name":tag,"value":item})
            if tag == "歌名":
                song_nodes_with_name.append({"name":tag,"value":item})
            else:
                song_nodes_no_name.append({"name":tag,"value":item})
    #print(song_nodes_no_name)
    # 添加关系
    dict_list = parse_csv_to_dict_list(song_csv_path)
    # 创建一个进度条，长度为 dict_list * song_nodes_no_name 的长度
    progress_bar = tqdm(total=len(dict_list) * len(song_nodes_no_name), desc='正在为节点设置关系')
    for song_d in dict_list:
        for song_node in song_nodes_no_name:
            is_present = check_dict_in_dict(song_node, song_d)
            if is_present:
                node1 = neo.search_node("歌库", song_node)
                node2 = neo.search_node("歌库", {"name": "歌名", "value": song_d["歌名"]})
                # 赋予（歌曲信息节点）->歌名节点的关系
                neo.set_relationship(node1[0]["node"], node2[0]["node"], "歌曲关系", {"name": "歌名"})
                neo.set_relationship(node2[0]["node"], node1[0]["node"], "歌曲关系", {"name": song_node["name"]})
            progress_bar.update(1)
    progress_bar.close()



if __name__ == '__main__':
    #make_song_dict("../../configs/csv/歌库.csv","../../data/json/song_dict.json")
    song_dict_to_neo4j()

