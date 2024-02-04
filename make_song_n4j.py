import json
from fuzzywuzzy import process
import csv
import utils
import ffmpeg
from Neo4j_Songdatabase.songdatabase import reset,search_for_name


class neo4j_songdatabase(object):
    def __init__(self,song_csv_path):
        self.hps = utils.get_hparams_from_file(song_csv_path)
        self.url = self.hps.api_path.neo4j.url
        self.user = self.hps.api_path.neo4j.user
        self.password = self.hps.api_path.neo4j.password
        self.similarity_threshold = self.hps.songdatabase.similarity_threshold
        self.search_key = self.hps.songdatabase.search_key
        self.song_dict_path = self.hps.songdatabase.song_dict_path
        self.csv_file_path = self.hps.songdatabase.song_csv_path
        self.song_path = self.hps.songdatabase.song_path

    def find_node(self):
        # 用于存储数据的字典
        data_dict = {}
        # 读取CSV文件
        with open(self.csv_file_path, 'r', encoding='gbk') as csv_file:
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
        utils.write_json(data_dict,self.song_dict_path)
        return data_dict

    def find_matching_keywords_with_similarity(self,user_question,data_dict):
        # 存储匹配的结果
        matching_results = {}
        # 遍历字典中的每个键值对
        for key, values in data_dict.items():
            # 在用户问题中查找与当前键相关的关键词
            matching_keywords = [keyword for keyword in values if keyword in user_question]
            # 如果存在匹配的关键词，将结果存入字典
            if matching_keywords:
                matching_results[key] = matching_keywords
            # 如果当前键是歌名，使用相似度查询
            if key == self.search_key:
                # 在用户问题中查找与当前键相关的关键词
                matches = process.extract(user_question, values, limit=3)
                # 过滤相似度低于阈值的结果
                filtered_matches = [(name, score) for name, score in matches if score >= self.similarity_threshold]
                if filtered_matches:
                    matching_results[key] = filtered_matches
        # 打印匹配结果
        # print("Matching Results:", matching_results)
        return matching_results

    def reset(self,song_csv_path)-> bool:
        self.find_node()
        return reset(self.url,self.user,self.password,song_csv_path)

    def search_song(self,content)-> list:
        # 获取字典
        with open(self.song_dict_path, 'r', encoding='utf-8') as json_file:
            data_dict = json.load(json_file)

        # 寻找匹配的节点名称
        matching_results = self.find_matching_keywords_with_similarity(content,data_dict)
        print("匹配的结果：", matching_results)
        # 初始化一个空的集合，用于存储所有获取到的歌单内容
        final_songlist = set()
        # 先将歌名这个键的值存入final_songlist
        song_matches = matching_results.get("歌名", [])
        for name, _ in song_matches:
            if name.strip():
                final_songlist.add(name)
        # 循环遍历匹配到的节点
        for key, matches in matching_results.items():
            if key != self.search_key:
                # 遍历非歌名键值对匹配结果中的节点名称
                for value in matches:
                    # 对每个值进行search_for_name操作，得到一个存放歌名的列表
                    song_names = search_for_name(self.url,self.user,self.password,value)
                    # 将列表与final_songlist合并，确保不重复添加
                    final_songlist.update(song_names)
        # 将集合转换为列表
        final_songlist = list(final_songlist)
        for id, name in enumerate(final_songlist):
            print(f"序号{id}:", name)
        return final_songlist


def get_duration_ffmpeg(file_path):
    try:
        probe = ffmpeg.probe(file_path)
        stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
        duration = float(stream['duration'])
        return duration
    except ffmpeg._run.Error as e:
        print("该歌曲需要vip权限。")



if __name__ == '__main__':
    a = neo4j_songdatabase("configs/config.json")
    #a.reset("csv/歌库.csv")
    song = a.search_song("牛奶咖啡")
    print(song)



