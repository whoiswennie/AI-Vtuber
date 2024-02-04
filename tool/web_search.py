import requests
from bs4 import BeautifulSoup



def search_wikipedia(query):
    # 提供一个合法的用户代理字符串
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    }

    # 发送请求
    url = f'https://zh.wikipedia.org/w/api.php?action=query&format=json&titles={query}&prop=extracts&exintro=1'

    try:
        response = requests.get(url, headers=headers)

        # 处理响应
        data = response.json()
        page_id = next(iter(data['query']['pages']))

        if page_id == '-1':
            return "未找到相关内容。"

        # 获取页面的正文链接
        page_link = f'https://zh.wikipedia.org/wiki/{query}'

        # 发送请求获取页面内容
        page_response = requests.get(page_link, headers=headers)

        # 使用BeautifulSoup解析页面内容
        soup = BeautifulSoup(page_response.content, 'html.parser')

        # 提取页面正文
        content_div = soup.find(id='mw-content-text')
        text = ''.join([p.get_text() for p in content_div.find_all('p')])

        # 移除一些特殊字符或乱码
        valid_text = ''.join(char for char in text if char.isprintable())

        return valid_text

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def search_baidu(keyword):
    url = f"https://baike.baidu.com/item/{keyword}"
    # 发送GET请求获取页面内容
    response = requests.get(url)
    print("本次查询的关键词:",keyword)
    # 检查请求是否成功
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # 找到包含正文内容的标签
        #content_tag = soup.find('div', {'class' : 'lemmaSummary_fNAax J-summary'})
        #content_tag = soup.find('div', {'class' : 'J-lemma-content'})
        #content_tag = soup.find('div', {'class' : 'text_xgHHZ'})
        #print(content_tag)
        # 找到包含文本内容的标签
        text_spans = soup.find_all('span', class_='text_xgHHZ')
        # 提取文本内容并组合在一起
        text = ''.join(span.get_text() for span in text_spans)
        print("搜索结果:",text)
        return text
    else:
        print("请求失败:", response.status_code)
        return None

def search_from_web(keyword):
    result = search_baidu(keyword)
    if not result:
        result = search_wikipedia(keyword)
    return result

if __name__ == '__main__':
    print("结果:",search_wikipedia("洛天依"))
    print(search_baidu("洛天依"))



