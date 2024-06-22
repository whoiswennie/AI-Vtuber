import requests
from bs4 import BeautifulSoup
import json

def search_baike(keyword):
    # 百度百科的搜索 URL
    search_url = 'https://baike.baidu.com/search?word=' + keyword
    # 发送 GET 请求
    response = requests.get(search_url)

    # 检查响应状态码
    if response.status_code != 200:
        return None

    # 解析 HTML 内容
    soup = BeautifulSoup(response.text, 'html.parser')

    # 查找第一个搜索结果的链接
    first_result = soup.find(class_='search-result-item')
    if first_result:
        # 获取链接
        link = first_result.find('a')['href']
        # 构建完整的词条 URL
        item_url = 'https://baike.baidu.com' + link
        return item_url
    else:
        return None

import urllib.request
import urllib.parse
from lxml import etree

def query(content):
    # 请求地址
    url = 'https://baike.baidu.com/item/' + content
    # 请求头部
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
    }
    # 利用请求地址和请求头部构造请求对象
    req = requests.get(url,headers).text
    # 创建 BeautifulSoup 对象
    soup = BeautifulSoup(req, 'html.parser')

    # 使用 CSS 选择器定位 <script> 标签
    script_tags = soup.find_all('script')

    # 遍历 <script> 标签并提取它们的文本内容
    script_contents = []
    for script in script_tags:
        script_contents.append(script.get_text())

    print(script_tags)
    return json.loads(script_contents[1][18:])

if __name__ == '__main__':
    while (True):
        content = input('查询词语：')
        result = query(content)
        print("查询结果：%s" % result)