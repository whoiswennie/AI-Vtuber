# -*- coding: utf-8 -*-

from py2neo import Graph, Node, Relationship
from neo4j import GraphDatabase
import csv

class Neo4jHandler:
    def __init__(self, uri, user, password):
        self.py2neo_graph = Graph(uri, auth=(user, password))
        self.neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
        self.node_list = {}

    def connect_to_database(self):
        # 连接数据库，这里返回的是 neo4j 的连接
        return self.neo4j_driver

    def add_node_from_csv(self, label, csv_path):
        with open(csv_path, 'r', encoding='gbk') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                data_list = row[1].split('，')  # 使用中文逗号分割数据
                for data in data_list:
                    if data not in self.node_list.get(label, []):
                        self.node_list.setdefault(label, []).append(data)
                        self.create_node_py2neo(label, data)

    def create_node_py2neo(self, label, data):
        # 使用 py2neo 创建节点
        node = Node(label, name=data)
        self.py2neo_graph.create(node)

    def create_node_neo4j(self, label, data):
        # 使用 neo4j 创建节点
        with self.neo4j_driver.session() as session:
            session.run(f"CREATE (n:{label} {{name: $data}})", data=data)

    def delete_node_py2neo(self, name):
        # 使用 py2neo 删除节点
        node = self.py2neo_graph.nodes.match(name=name).first()
        if node:
            self.py2neo_graph.delete(node)

    def delete_node_neo4j(self, name):
        # 使用 neo4j 删除节点
        with self.neo4j_driver.session() as session:
            session.run("MATCH (n {name: $name}) DETACH DELETE n", name=name)

    def query_node_py2neo(self, node_name):
        # 使用 py2neo 查询节点
        node = self.py2neo_graph.nodes.match(name=node_name).first()
        if node:
            node_properties = dict(node)
            relationships = self.get_node_relationships_py2neo(node_name)
            return {"properties": node_properties, "relationships": relationships}
        else:
            return None

    def query_node_neo4j(self, node_name):
        # 使用 neo4j 查询节点
        with self.neo4j_driver.session() as session:
            result = session.run(
                "MATCH (n {name: $name}) RETURN n",
                name=node_name
            )

            records = list(result)
            if records:
                node_properties = records[0]["n"]._properties
                relationships = self.get_node_relationships_neo4j(node_name)
                return {"properties": node_properties, "relationships": relationships}
            else:
                return None

    def get_node_relationships_py2neo(self, node_name):
        # 使用 py2neo 获取节点关系
        node = self.py2neo_graph.nodes.match(name=node_name).first()
        if node:
            relationships = []
            for rel in self.py2neo_graph.relationships.match(nodes=(node,)):
                relationship_type = rel.type
                related_node = dict(rel.end_node)
                relationships.append({"relationship_type": relationship_type, "related_node": related_node})

            return relationships
        else:
            return []

    def get_node_relationships_neo4j(self, node_name):
        # 使用 neo4j 获取节点关系
        with self.neo4j_driver.session() as session:
            result = session.run(
                "MATCH (n {name: $name})-[r]-(m) RETURN r, m",
                name=node_name
            )

            relationships = []
            for record in result:
                relationship = record["r"].type
                related_node = record["m"]._properties
                relationships.append({"relationship_type": relationship, "related_node": related_node})

            return relationships

    def modify_node_py2neo(self, old_name, new_name=None, new_properties=None, modify_relationships=False):
        # 使用 py2neo 修改节点
        node = self.py2neo_graph.nodes.match(name=old_name).first()
        if node:
            if new_name:
                node['name'] = new_name
            if new_properties:
                for key, value in new_properties.items():
                    node[key] = value
            if modify_relationships:
                # 在这里添加修改节点关系的逻辑
                pass
            node.push()

    def modify_node_neo4j(self, old_name, new_name=None, new_properties=None, modify_relationships=False):
        # 使用 neo4j 修改节点
        with self.neo4j_driver.session() as session:
            node = session.run("MATCH (n {name: $name}) RETURN n", name=old_name).single()["n"]
            if node:
                if new_name:
                    session.run("MATCH (n {name: $old_name}) SET n.name = $new_name", old_name=old_name, new_name=new_name)
                if new_properties:
                    session.run("MATCH (n {name: $name}) SET n += $new_properties", name=old_name, new_properties=new_properties)
                if modify_relationships:
                    # 在这里添加修改节点关系的逻辑
                    pass

    def build_audio_library(self, csv_path):
        with open(csv_path, 'r', encoding='gbk') as file:
            csv_reader = csv.reader(file)
            header = next(csv_reader)  # 读取标签栏
            label_list = [label for label in header if label]  # 动态获取标签

            for row in csv_reader:
                for i, value in enumerate(row):
                    if i >= len(label_list):  # 避免索引越界
                        break
                    label = label_list[i]

                    # 处理有中文逗号的情况
                    if '，' in value:
                        data_list = value.split('，')
                        for data in data_list:
                            self.process_data(label, data, row, header)
                    else:
                        self.process_data(label, value, row, header)

    def process_data(self, label, data, row, header):
        if data:
            if data not in self.node_list.get(label, []):
                self.node_list.setdefault(label, []).append(data)
                node = Node(label, name=data)
                self.py2neo_graph.create(node)
            else:
                node = self.py2neo_graph.nodes.match(label, name=data).first()

            # 在这里处理其他标签的数据，建立关系等逻辑
            # 示例：建立歌名和其他标签之间的关系
            if label != "歌名" and row[header.index("歌名")]:  # 保证歌名不为空
                song_node = self.py2neo_graph.nodes.match("歌名", name=row[header.index("歌名")]).first()
                if song_node:
                    relationship = Relationship(song_node, label, node)
                    self.py2neo_graph.create(relationship)

    def query_node_and_neighbors(self, node_name):
        with self.neo4j_driver.session() as session:
            result = session.run(
                "MATCH (n {name: $name})-[r]-(m) RETURN n, r, m",
                name=node_name
            )

            data = {"node": {}, "neighbors": []}

            for record in result:
                # 处理查询到的节点
                node_properties = record["n"]._properties
                data["node"] = {"name": node_name, "properties": node_properties}

                # 处理查询到的关系和相邻节点
                relationship_type = record["r"].type
                related_node_properties = record["m"]._properties
                data["neighbors"].append(
                    {"relationship_type": relationship_type, "related_node": related_node_properties})

            return data

    def clear_database(self, clear_properties=False):
        # 清空数据库中所有信息（包括所有节点、关系）
        if clear_properties:
            # 使用 neo4j 清空所有属性键
            with self.neo4j_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
        else:
            # 使用 py2neo 清空数据库
            self.py2neo_graph.delete_all()


def search_for_name(uri,user,password,content):
    handler = Neo4jHandler(uri, user, password)
    #handler.add_node_from_csv("歌名", "csv/歌库.csv")
    # 示例：查询节点
    result = handler.get_node_relationships_neo4j(content)
    # 提取'name'的值并存入列表
    name_list = [item['related_node']['name'] for item in result]
    # 遍历打印列表中的值
    # for id,name in enumerate(name_list):
    #     print(f"序号{id}:",name)
    return name_list


def reset(uri,user,password,song_csv_path):
    handler = Neo4jHandler(uri, user, password)
    handler.clear_database(clear_properties=True)
    handler.build_audio_library(song_csv_path)
    #handler.add_nodes_and_relations_from_csv("csv/喜好.csv")
    return True

