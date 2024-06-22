import time

import utils
from func.agent.agent_to_study import tools

Debug = True
def tool_search_in_neo4j(content,database):
    start_time = time.time()
    print(f"\033[35m[正在查询关联数据(当前知识库{database})]\033[0m")
    related_keywords = []
    from func.Neo4j_Database import to_neo4j
    neo = to_neo4j.Neo4jHandler("configs/json/config.json")
    neo.connect_neo4j_database()
    related_keywords += utils.find_similar_keywords(neo.get_nodes_with_label(database,False),content,40)
    if not related_keywords:
        related_keywords += utils.find_similar_keywords(neo.get_nodes_with_label(database, False), content,30)
        related_keywords = sorted(related_keywords, key=lambda x: x[1], reverse=True)[:1]
    else:
        related_keywords = sorted(related_keywords, key=lambda x: x[1], reverse=True)[:]
    #new_related_keywords = {"初始节点":related_keywords,"关联节点":[]}
    new_related_keywords = {"初始节点":[],"关联节点":[]}
    new_related_keywords["初始节点"] += [f"提取到的关键词为【{n[0]['value']}】,类别为【{n[0]['name']}】与记忆库匹配度为:{n[1]}。" for n in related_keywords]
    related_keywords_pairs = [(related_keywords[i], related_keywords[j]) for i in range(len(related_keywords)) for j in range(i + 1, len(related_keywords))]
    swapped_pairs = [(b, a) for a, b in related_keywords_pairs]
    # 将交换后的组合添加到原始的pairs列表中
    related_keywords_pairs.extend(swapped_pairs)
    for node in related_keywords:
        node = neo.search_node(database,node[0])
        print(node)
        if node[0]["relationship_types"]:
            related_nodes = neo.find_related_nodes(node[0]["node"],node[0]["relationship_types"][0])
            #new_related_keywords["关联节点"] += [{"name": node["name"], "value": node["value"]} for node in related_nodes]
            new_related_keywords["关联节点"] += [f"通过关键词{node[0]['node']['value']}查询到的{n['name']}是{n['value']}。" for n in related_nodes]
    k_lst = new_related_keywords
    k_lst["思考路径"] = []
    for i in related_keywords_pairs:
        node1 = neo.search_node(database,i[0][0])[0]["node"]
        node2 = neo.search_node(database,i[1][0])[0]["node"]
        node_path = neo.find_shortest_path(node1,node2)
        if node_path:
            k_lst["思考路径"].append(node_path)
    if Debug:
        print("\033[33m查询到的初始节点:\033[0m", related_keywords)
        print("\033[33m查询到的关联节点:\033[0m", new_related_keywords["关联节点"])
    if Debug:
        print("\033[33mAI筛查的片段:\033[0m", k_lst)
    print("\033[36m[关联数据查询完毕]\033[0m")
    end_time = time.time()
    print(f"\033[31m运行时间：{end_time - start_time} 秒\033[0m")
    return k_lst

tool_search_in_neo4j("Akie秋绘和warma","歌库")