# -*- coding: utf-8 -*-
import os
import csv
from func.chroma_database import chroma_database
from fuzzywuzzy import process
import tool.search_for_song
import tool.Fast_Whisper


class KeywordAssociationManager:
    def __init__(self, csv_file_path):
        self.keyword_dict = {}
        self.emotion_dict = {}
        self.current_keyword = None
        self.csv_file_path = csv_file_path
        self.load_csv()

    def add_keyword(self, new_keyword):
        """
        添加新的关键词到CSV文件中
        :param new_keyword: 要添加的关键词
        """
        if new_keyword not in self.keyword_dict:
            # 如果关键词不存在，则创建新的一行
            self.keyword_dict[new_keyword] = []
            self.save_csv()
            self.get_association(new_keyword)
            self.add_association("None")
        else:
            print(f"关键词 '{new_keyword}' 已经存在于CSV文件中。")

    def load_csv(self):
        with open(self.csv_file_path, 'r', encoding='gbk') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                keyword = row['keyword']
                association_str = row['association']
                association = association_str.split('，')  # 使用中文逗号分隔字符串
                emotion = row['emotion']
                self.keyword_dict[keyword] = association
                self.emotion_dict[keyword] = emotion

    def update_emotion(self, keyword, new_emotion):
        """
        更新关键词对应的情绪标签
        :param keyword: 要更新情绪标签的关键词
        :param new_emotion: 新的情绪标签
        """
        if keyword in self.keyword_dict:
            self.emotion_dict[keyword] = new_emotion
            self.save_csv()  # 及时更新CSV文件
            print(f"关键词 '{keyword}' 的情绪标签已更新为 '{new_emotion}'。")
        else:
            print(f"关键词 '{keyword}' 不存在于CSV文件中。")

    def add_association(self, new_association):
        if self.current_keyword is not None:
            if self.current_keyword in self.keyword_dict:
                self.keyword_dict[self.current_keyword].append(new_association)
            else:
                # 如果关键词不存在，则创建新的一行
                self.keyword_dict[self.current_keyword] = [new_association]
            self.save_csv()  # 及时更新CSV文件

    def save_csv(self):
        with open(self.csv_file_path, 'w', encoding='gbk', newline='') as file:
            fieldnames = ['keyword', 'association', 'emotion']
            csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
            csv_writer.writeheader()
            for keyword, association in self.keyword_dict.items():
                csv_writer.writerow({'keyword': keyword, 'association': '，'.join(association),'emotion': self.emotion_dict.get(keyword, "")})


    def get_association(self, keyword):
        if keyword in self.keyword_dict:
            self.current_keyword = keyword
            return self.keyword_dict[keyword]
        else:
            return []

    def delete_association(self, association_to_delete):
        if self.current_keyword is not None:
            if self.current_keyword in self.keyword_dict:
                if association_to_delete in self.keyword_dict[self.current_keyword]:
                    self.keyword_dict[self.current_keyword].remove(association_to_delete)
                    self.save_csv()

    def update_association(self, old_association, new_association):
        if self.current_keyword is not None:
            if self.current_keyword in self.keyword_dict:
                if old_association in self.keyword_dict[self.current_keyword]:
                    index = self.keyword_dict[self.current_keyword].index(old_association)
                    self.keyword_dict[self.current_keyword][index] = new_association
                    self.save_csv()

    def search_keyword_fuzzy(self, search_query, threshold=60):
        """
        使用模糊搜索查找关键词
        :param search_query: 要搜索的字符串
        :param threshold: 模糊匹配的阈值，默认为80
        :return: 匹配的关键词列表
        """
        matches = process.extractBests(search_query, self.keyword_dict.keys(), score_cutoff=threshold)
        if not matches:
            return []

        matched_keywords = [match[0] for match in matches]
        return matched_keywords

    def delect_emotion(self,keyword):
        score = self.emotion_dict[keyword]
        return score

def find_most_similar(query, target_list, threshold=8):
    """
    利用模糊搜索查找与给定字符串最相似的列表元素
    :param query: 要搜索的字符串
    :param target_list: 目标列表
    :param threshold: 模糊匹配的阈值，默认为80
    :return: 最相似的列表元素，以及相似度分数
    """
    print(query,target_list)
    best_match, score = process.extractOne(query, target_list, score_cutoff=threshold)

    if best_match is not None:
        return best_match, score
    else:
        return "None", 0

def study_from_bilibili(bv:str,keyword:str,emotion:int):
    bv_title = tool.search_for_song.search_bilibili(bv)
    manager = KeywordAssociationManager('csv/keyword_dict.csv')
    manager.add_keyword(keyword)
    manager.update_emotion(keyword, emotion)
    manager.get_association(keyword)
    tool.Fast_Whisper.stt(model_path="faster-whisper-webui/Models/faster-whisper/large-v2",input_path=os.path.join(project_root,f"download/{bv_title}.wav"),output_path=os.path.join(project_root,f"chroma_database/database/{keyword}"))
    manager.add_association(bv_title)
    chroma_database.make_db(text_path=os.path.join(project_root, f"chroma_database/database/{keyword}/{bv_title}.txt"), persist_directory=os.path.join(project_root, f"chroma_database/database/{keyword}"), chunk_size=100)

def study_from_txt(keyword:str,emotion:int,txt_name:str):
    manager = KeywordAssociationManager('csv/keyword_dict.csv')
    manager.add_keyword(keyword)
    manager.update_emotion(keyword,emotion)
    manager.get_association(keyword)
    manager.add_association(txt_name)
    chroma_database.make_db(text_path=os.path.join(project_root, f"chroma_database/text/{txt_name}.txt"),
                            persist_directory=os.path.join(project_root, f"chroma_database/database/{keyword}"),
                            chunk_size=100)

def detect_for_keyword(content):
    manager = KeywordAssociationManager('csv/keyword_dict.csv')
    matched_keywords = manager.search_keyword_fuzzy(content)
    if matched_keywords:
        print(f"模糊匹配到的关键词：{matched_keywords}")
        for keyword in matched_keywords:
            associations = manager.get_association(keyword)
            print(f'{keyword} 对应的关联内容：{associations}')
            most_similar_text, similarity_score = find_most_similar(content,associations)
            if most_similar_text:
                print(f"最相似的内容：{most_similar_text}")
                print(f"相似度分数：{similarity_score}")
                score = int(manager.delect_emotion(keyword))
                return keyword,score
            else:
                print(f"未找到与 '{content}' 相似度超过阈值的元素。")
                return "None","None"
    else:
        print("此次对话为正常对话，不含关键词！")
        return "None","None"

def search_from_memory(content):
    keyword,score = detect_for_keyword(content)
    result = chroma_database.search_in_db(f"chroma_database/database/{keyword}", content, k_lin=2)
    if result:
        return keyword,score,result
    else:
        return "None","None","None"

if __name__ == '__main__':
    project_root = os.path.dirname(os.path.abspath(__file__))
    please = input("1.视频学习 2.文本学习")
    keyword = input("请设定本次学习内容的关键词:")
    output_dir = f"chroma_database/database/{keyword}"
    os.makedirs(output_dir, exist_ok=True)
    if please == "1":
        bv = input("请输入需要学习的b站视频bv号:")
        study_from_bilibili(bv=bv,keyword=keyword)
    elif please == "2":
        txt_name = input("请输入文本名称:")
        study_from_txt(keyword,txt_name)
    # print(search_from_memory("三次元桂乃芬是什么梗"))

