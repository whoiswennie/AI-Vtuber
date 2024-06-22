from pathlib import Path
from openai import OpenAI

client = OpenAI(
    api_key="sk-6ce39892c46a4c0ebe34bb736c03a7e3",  # 替换成真实DashScope的API_KEY
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 填写DashScope服务endpoint
)

# data.pdf 是一个示例文件
file = client.files.create(file=Path("template/txt/liuying.txt"), purpose="file-extract")

# 首次对话会等待文档解析完成，首次rt可能较长
completion = client.chat.completions.create(
    model="qwen-long",
    messages=[
        {
            'role': 'system',
            'content': 'You are a helpful assistant.'
        },
        {
            'role': 'user',
            'content': '你好'
        }
    ],
    stream=False
)
print(completion.choices[0].message.content)
print(completion)