import itertools

import os
import queue
from py2neo import Graph, Node, Relationship
from neo4j import GraphDatabase
import csv
import json
import utils


class Neo4jHandler:
    def __init__(self,song_csv_path):
        self.hps = utils.get_hparams_from_file(song_csv_path)
        self.url = self.hps.api_path.neo4j.url
        self.user = self.hps.api_path.neo4j.user
        self.password = self.hps.api_path.neo4j.password
        self.system_url = self.url.replace("/neo4j", "/system")
        self.connect_neo4j_database()


    def connect_neo4j_database(self):
        self.py2neo_graph = Graph(self.url, auth=(self.user, self.password))
        self.neo4j_driver = GraphDatabase.driver(self.url, auth=(self.user, self.password))
        self.node_list = {}

    def find_shortest_path(self, node1, node2):
        start_node_id = node1.identity
        end_node_id = node2.identity
        print(start_node_id,end_node_id)
        if not start_node_id or not end_node_id:
            return None
        if start_node_id == end_node_id:
            return None
        query = f"""
        MATCH (start), (end),
              p = shortestPath((start)-[*]-(end))
        WHERE id(start) = {start_node_id} AND id(end) = {end_node_id}
        RETURN p,
               [r IN relationships(p) | [type(r), properties(r)]] AS relationships
        """
        with self.neo4j_driver.session() as session:
            result = session.run(query)
            path = result.data()
        if not path or not path[0]['p']:
            return None
        data_str = f"本次思考查询到了{int((len(path[0]['p'])-1)/2)}个节点，下面是节点的思考流程（从起点到终点）:"
        data_lst = queue.Queue()
        start_flag = True
        # 创建一个枚举迭代器
        for i in enumerate(path[0]["p"]):
            data_lst.put(i)
        while True:
            id, value = data_lst.get()
            if isinstance(value, dict) or start_flag:
                if start_flag:
                    start_flag = False
                    if data_lst.empty(): break
                    data_str += f"节点【{str(value)}】"
                else:
                    start_flag = True
                    data_str += f"查询到节点【{str(value)}】;"
                    temp_list = []
                    while not data_lst.empty():
                        temp_list.append(data_lst.get())
                    data_lst.put((id, value))
                    for item in temp_list:
                        data_lst.put(item)
            else:
                data_str += f"通过关系【{path[0]['relationships'][int(id / 2)]}】"
        #print(data_str)
        return data_str

    def get_all_node_names(self):
        if not self.py2neo_graph:
            raise Exception("Not connected to Neo4j database. Please call connect_neo4j_database first.")

        query = "MATCH (n) RETURN distinct labels(n)"
        results = self.py2neo_graph.run(query).data()
        node_labels = ["_".join(record['labels(n)']) for record in results]
        #print("node_labels:",node_labels)
        return node_labels

    def get_nodes_with_label(self, label, return_str = False):
        if not self.py2neo_graph:
            raise Exception("Not connected to Neo4j database. Please call connect_neo4j_database first.")

        # 执行Cypher查询来获取指定label的所有节点的属性
        query = f"""
        MATCH (n:{label})
        RETURN properties(n)
        """
        results = self.py2neo_graph.run(query).data()

        # 提取节点属性
        if not return_str:
            nodes_properties = [record['properties(n)'] for record in results]
            return nodes_properties
        else:
            result = []
            nodes_properties = [record['properties(n)'] for record in results]
            for n in nodes_properties:
                result.append(list(n.values())[0]+":"+list(n.values())[1])

            #print(result)
            return result

    # def add_node(self, tag, properties):
    #     """
    #     Adds a node with multiple properties to the graph.
    #
    #     Examples:
    #         add_node("Person", {"name": "John", "age": 30})
    #
    #     Args:
    #         tag (str): The label of the node.
    #         properties (dict): A dictionary of property names and values.
    #
    #     Returns:
    #         None
    #     """
    #     # Create a string with the format "key1: 'value1', key2: 'value2', ..."
    #     property_string = ", ".join([f"{key}: '{value}'" for key, value in list(properties.items())])
    #     query = f"CREATE (n:{tag} {{{property_string}}}) RETURN n"
    #     self.py2neo_graph.run(query)
    #     print("Node successfully added.")

    def add_node(self, tag, properties):
        """
        Adds a node with multiple properties to the graph if it doesn't already exist.

        Examples:
            add_node("Person", {"name": "John", "age": 30})

        Args:
            tag (str): The label of the node.
            properties (dict): A dictionary of property names and values.

        Returns:
            None
        """
        # 构建Cypher查询来检查节点是否已存在
        property_conditions = ", ".join([f"{key}: '{value}'" for key, value in properties.items()])
        query_check = f"MATCH (n:{tag} {{{property_conditions}}}) RETURN n LIMIT 1"

        # 执行查询检查节点是否存在
        existing_node = self.py2neo_graph.run(query_check).data()

        if existing_node:
            print("Node already exists.")
            node = [{'node': record['n']}for record in existing_node]
            return list(node)

        # 如果节点不存在，则创建节点
        property_string = ", ".join([f"{key}: '{value}'" for key, value in properties.items()])
        query_create = f"CREATE (n:{tag} {{{property_string}}}) RETURN n"
        self.py2neo_graph.run(query_create)
        #print("Node successfully added.")

    def set_relationship(self, node1, node2, relationship_type, properties=None):
        """
        Creates a relationship between two nodes.

        Args:
            node1 (Node): The first node.
            node2 (Node): The second node.
            relationship_type (str): The type of relationship.
            properties (dict, optional): A dictionary of property names and values for the relationship.

        Returns:
            Relationship: The created relationship object.
        """
        # Create a relationship object with the specified type and properties
        if properties:
            rel = Relationship(node1, relationship_type, node2, **properties)
        else:
            rel = Relationship(node1, relationship_type, node2)
        # Create the relationship in the graph
        self.py2neo_graph.create(rel)
        return rel

    def search_node(self, label, properties=None):
        """
        Searches for nodes in the graph based on the given label and optional properties,
        and returns each node with its relationship types.

        Args:
            label (str): The label of the nodes to search for.
            properties (dict, optional): A dictionary of property names and values to filter the nodes.

        Returns:
            list: A list of dictionaries with 'node' and 'relationship_types' keys.
        """
        query = f"MATCH (n:{label})"
        if properties:
            # 确保属性条件使用AND连接
            props = ' AND '.join([f"n.{k} = '{v}'" for k, v in properties.items()])
            query += f" WHERE {props}"
        query += """
        OPTIONAL MATCH (n)-[r]->()
        RETURN n, collect(distinct type(r)) as relationship_types
        """
        results = self.py2neo_graph.run(query).data()
        nodes_with_relationship_types = [{'node': record['n'], 'relationship_types': record['relationship_types']} for
                                         record in results]
        return nodes_with_relationship_types

    def find_related_nodes(self, start_node, relationship_type):
        """
        Finds all nodes related to a given start node by a specific relationship type.

        Args:
            start_node (Node): The starting node.
            relationship_type (str): The type of relationship to look for.

        Returns:
            list: A list of nodes related to the start node by the specified relationship type.
        """
        query = f"MATCH (n)-[:`{relationship_type}`]->(related_nodes) WHERE id(n) = {start_node.identity} RETURN related_nodes"
        results = self.py2neo_graph.run(query).data()
        related_nodes = [record['related_nodes'] for record in results]
        return related_nodes

    def delete_node(self, node):
        """
        Deletes a node from the graph.

        Args:
            node (Node): The node to be deleted.

        Returns:
            None
        """
        query = f"MATCH (n) WHERE id(n) = {node.identity} DELETE n"
        self.py2neo_graph.run(query)
        print("Node successfully deleted.")

    def delete_nodes_for_label(self, label):
        if not self.py2neo_graph:
            raise Exception("Not connected to Neo4j database. Please call connect_neo4j_database first.")

        # 执行Cypher查询来删除具有指定label的所有节点
        query = f"""
        MATCH (n:{label})
        DETACH DELETE n
        """
        self.py2neo_graph.run(query)

    def delete_database(self):
        query = "MATCH ()-[r]->() DELETE r"
        self.py2neo_graph.run(query)
        query = "MATCH (n) DETACH DELETE n"
        self.py2neo_graph.run(query)
        print("Database successfully cleared.")

    def clear_and_write_nodes_to_csv(self, label, csv_file_path):
        # 连接到Neo4j数据库
        self.connect_neo4j_database()

        # 查询所有指定标签的节点
        query = f"MATCH (n:{label}) RETURN n"
        nodes = self.py2neo_graph.run(query).data()

        # 检查CSV文件是否存在，如果不存在则创建
        if not os.path.exists(csv_file_path):
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                # 只使用节点标签作为字段名
                fieldnames = [label]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

        # 读取CSV文件，清空指定标签列的数据，并写入新数据
        with open(csv_file_path, 'r+', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

            # 检查CSV中是否存在该标签列，如果不存在则添加
            if label not in reader.fieldnames:
                reader.fieldnames.append(label)
                rows = [dict(row, **{label: ''}) for row in rows]

            # 如果节点数量大于行数，添加新行
            while len(rows) < len(nodes):
                rows.append({fn: '' for fn in reader.fieldnames})

            # 清空该列的数据
            for row in rows:
                row[label] = ''

            # 将节点数据写入该列
            for i, node in enumerate(nodes):
                rows[i][label] = str(node['n'])

            # 写入修改后的数据回CSV文件
            csvfile.seek(0)
            writer = csv.DictWriter(csvfile, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(rows)

def nodes_to_json(nodes):
    return json.loads(json.dumps(nodes, ensure_ascii=False))

def json_to_nodes(node_name,json_data,config_path="../configs/json/config.json"):
    a = Neo4jHandler(config_path)
    a.connect_neo4j_database()
    lst = []
    for i in json_data:
        result_lst = a.search_node(node_name,i["node"])
        lst += result_lst
    return lst

def print_shortest_path(path_result):
    if isinstance(path_result, str):
        print(path_result)
        return

    nodes = path_result["nodes"]
    relationships = path_result["relationships"]

    # 构建节点id到节点名称的映射
    node_id_to_name = {}
    for node in nodes:
        node_id_to_name[node["id"]] = f"{node['name']} ({node['value']})"

    # 打印起始节点
    start_node = nodes[0]
    print(f"Start: {start_node['name']} ({start_node['value']})")

    # 打印路径上的关系和经过的节点
    for relationship in relationships:
        relationship_type = relationship["type"]
        relationship_properties = relationship["properties"]
        start_node_id = relationship["start"]
        end_node_id = relationship["end"]

        start_node_name = node_id_to_name.get(start_node_id, f"Node {start_node_id}")
        end_node_name = node_id_to_name.get(end_node_id, f"Node {end_node_id}")

        print(f" --[{relationship_type}, {relationship_properties}]--> {end_node_name}")

    # 打印终点节点
    end_node = nodes[-1]
    print(f"End: {end_node['name']} ({end_node['value']})")


if __name__ == '__main__':
    a = Neo4jHandler("../../configs/json/config.json")
    a.connect_neo4j_database()
    # a.add_node("Person",{"age": 30, "city": "New York"})
    #node1 = a.search_node("夏宇闻")
    #a.clear_and_write_nodes_to_csv("原神","../../configs/csv/cognition.csv")
    #print(a.search_node("蕾米莉亚斯卡蕾特",{"name":"首次登场作品"}))
    #print(a.search_node("夏宇闻", {"性别": "男", "爱好": "男"}))
    # node2 = a.search_node("Person",{"name":"007"})[0]['node']
    #relationship = a.set_relationship(node2, node1, '朋友', properties={'since': 2024})
    # print(a.search_node("Person",{"name":"007"}))
    # print(a.find_related_nodes(node1,"朋友"))
    # a.delete_node(node1)
    s= "谁的称谓是“鸢尾花家系的艺者”"
    #print(utils.find_similar_keywords(a.get_nodes_with_label("流萤",False),s,35))
    node1 = a.search_node("歌库",{"name":"歌名","value":"花"})[0]["node"]
    node2 = a.search_node("歌库",{"name":"歌曲来源","value":"石見舞菜香"})[0]["node"]
    shortest_path_result = a.find_shortest_path(node1, node2)
    print(shortest_path_result)
    print(print_shortest_path(shortest_path_result))

