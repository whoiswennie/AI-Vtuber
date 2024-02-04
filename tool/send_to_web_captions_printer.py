# -*- coding: utf-8 -*-

# 请求web字幕打印机
import json
import threading
import time

import requests
file_lock = threading.Lock()


def send_to_web_captions_printer(content,api_ip_port = "http://127.0.0.1:5500"):
    """请求web字幕打印机

    Args:
        api_ip_port (str): api请求地址
        data (dict): 包含用户名,弹幕内容

    Returns:
        bool: True/False
    """
    # 记录数据库):
    try:
        response = requests.get(url=api_ip_port + f'/send_message?content={content}')
        response.raise_for_status()  # 检查响应的状态码

        result = response.content
        ret = json.loads(result)


        if ret['code'] == 200:
            return True
        else:
            return False
    except Exception as e:
        print('web字幕打印机请求失败！请确认配置是否正确或者服务端是否运行！')
        return False

#print(send_to_web_captions_printer("耿治南芝,南方小土豆,是只貢獻哈爾濱的南方朋友,身穿淺色羽絨服,頭戴可愛帽子是他們的特徵,因為北方的平均身高比南方高,所以被調侃為南方小土豆,他們將澡堂、澡室、冰雪大世界全部貢獻"))