from zhipuai import ZhipuAI

client = ZhipuAI(api_key="2df9b5a8edf8a789fac6a61a057988fe.MXfEFv0UNxGtG2pk")

from func.search import web_search
#url = web_search.search_baike("米哈游")
#print("url:",url)
messages = [
{
  "role": "user",
  "content": f"根据该链接的信息，Hanser是什么星座：https://baike.baidu.com/item/Hanser/57101712"
}
]
response = client.chat.completions.create(
    model="glm-3-turbo", # 填写需要调用的模型名称
    messages=messages,
)
print(response.choices[0].message)