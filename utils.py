# -*- coding: utf-8 -*-
import time

import ffmpeg
import json
import os
import re
import shutil
import socket
from urllib.parse import urlparse
from fuzzywuzzy import process


def get_duration_ffmpeg(file_path):
  """
  获取音频的时长
  :param file_path:
  :return:
  """
  try:
    probe = ffmpeg.probe(file_path)
    stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
    duration = float(stream['duration'])
    return duration
  except ffmpeg._run.Error as e:
    print(f"出现异常，{e}")

class HParams():
  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      if type(v) == dict:
        v = HParams(**v)
      self[k] = v

  def keys(self):
    return self.__dict__.keys()

  def items(self):
    return self.__dict__.items()

  def values(self):
    return self.__dict__.values()

  def __len__(self):
    return len(self.__dict__)

  def __getitem__(self, key):
    return getattr(self, key)

  def __setitem__(self, key, value):
    return setattr(self, key, value)

  def __contains__(self, key):
    return key in self.__dict__

  def __repr__(self):
    return self.__dict__.__repr__()

  def get(self,index):
    return self.__dict__.get(index)

def get_hparams_from_file(dict_path):
  with open(dict_path, "r", encoding="utf-8") as f:
    data = f.read()
  config = json.loads(data)
  hparams =HParams(**config)
  return hparams

def get_hparams_from_dict(dict):
  hparams = HParams(**dict)
  return hparams

def load_json(path):
  with open(path, 'r', encoding='utf-8') as json_file:
    data_dict = json.load(json_file)
  return data_dict

def write_json(data_dict,path):
  with open(path, 'w', encoding='utf-8') as json_file:
    json.dump(data_dict, json_file, ensure_ascii=False, indent=4)

def update_progress(current_time, total_duration, progress):
  print(f"A: {current_time} / {total_duration} ({progress}%)", end='\r')


def check_port(host, port):
  # 创建一个套接字对象
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    # 尝试连接到指定的主机和端口
    s.connect((host, port))
    # 如果连接成功，说明端口已被占用
    # print(f"Port {port} on {host} is already in use")
    return True
  except socket.error as e:
    # 如果连接失败，说明端口未被占用
    # print(f"Port {port} on {host} is not in use")
    return False
  finally:
    # 关闭套接字连接
    s.close()

def extract_port_and_url(url):
  parsed_url = urlparse(url)
  if parsed_url.scheme == 'http' or parsed_url.scheme == 'https':
    netloc = parsed_url.netloc.split(':')[0]
    return netloc, parsed_url.port
  elif parsed_url.scheme == 'bolt':
    netloc = parsed_url.netloc.split(':')[0]
    return netloc, int(parsed_url.netloc.split(':')[-1])
  else:
    return None, None

def empty_directory(directory_path):
  # 遍历文件夹内所有的文件与子文件夹名称
  for filename in os.listdir(directory_path):
    file_path = os.path.join(directory_path, filename)
    try:
      if os.path.isfile(file_path) or os.path.islink(file_path):
        os.unlink(file_path)  # 删除文件或链接
      elif os.path.isdir(file_path):
        shutil.rmtree(file_path)  # 删除文件夹
    except Exception as e:
      print(f"删除 {file_path} 时出现错误。原因： {e}")

def timer(func):
  def wrapper(*args, **kwargs):
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    print(f"\033[31m{func.__name__} 运行时间：{end_time - start_time} 秒\033[0m")
    return result

  return wrapper

def find_similar_keywords(keyword_list, string,score=50):
  # 使用fuzzywuzzy的extractBests方法来找到最相似的匹配
  node_index = {}
  result = []
  for n in keyword_list:
    s = list(n.values())[0] + ":" + list(n.values())[1]
    result.append(s)
    node_index[s] = n
  matches = process.extractBests(string, result, score_cutoff=score)
  # 提取匹配结果和它们的相似度分数
  similar_keywords = [(match[0], match[1]) for match in matches]
  r_lst = []
  for i in similar_keywords:
    print(i[0])
    r_lst.append((node_index[i[0]],i[1]))
  return r_lst

def replace_special_characters(filename):
  special_chars = {
    '/': '_',
    '\\': '_',
    ':': '-',
    '?': '',
    '？': '',
    '*': '',
    '"': '',
    ' ': '_',
    "'": "_",
    '<': '',
    '>': '',
    '|': '',
    '.': '',
    '。': '',
    '，': '',
    '·': '',
    ',': '',
    '[': '',
    ']': '',
    '{': '',
    '}': '',
    '+': '',
    '=': '',
    '&': '',
    '%': '',
    '#': '',
    '@': '',
    '!': '',
    '^': '',
    '(': '_',  # 将'('替换为下划线
    ')': '_',  # 将')'替换为下划线
    '-': '_',
    '（': '_',
    '）': '_',
    '、': ',',  # 将'、'替换为逗号
    '0': '零',
    '1': '一',
    '2': '二',
    '3': '三',
    '4': '四',
    '5': '五',
    '6': '六',
    '7': '七',
    '8': '八',
    '9': '九',
    # 添加其他特殊字符...
  }

  # 使用正则表达式进行替换
  try:
    for char, replacement in special_chars.items():
      filename = re.sub(re.escape(char), replacement, filename)
  except TypeError as e:
    print(e)

  return filename

def is_valid_json_format(data):
  try:
    # 检查data是否是一个列表
    if not isinstance(data, list) or len(data) <= 1:
      return False

    # 检查列表的第一个元素是否是字符串（节点名称）
    if not isinstance(data[0], str):
      return False

    # 检查列表的第二个元素是否是一个列表
    if not isinstance(data[1], list):
      return False

    # 遍历列表中的每个字典，检查它们是否都有'name'键
    for item in data[1]:
      if not isinstance(item, dict) or 'name' not in item:
        return False

    # 如果所有检查都通过，则返回True
    return True
  except json.JSONDecodeError:
    # 如果解析过程中出现错误，返回False
    return False

def split_text_by_length(content, length):
  # 存储切分后的段落
  segments = []
  # 使用正则表达式查找合适的切分点
  pattern = re.compile(r'(?<=[，。,.])')

  while len(content) > length:
    # 查找最近的逗号或句号
    end = content[:length].rfind('，') if content[:length].rfind('，') != -1 else content[:length].rfind('。')
    if end == -1:  # 如果在指定字数内找不到逗号或句号
      end = length
    else:
      end += 1  # 包含标点符号
    segment = content[:end].strip()
    segments.append(segment)
    content = content[end:].strip()

  # 添加剩余的内容
  if content:
    segments.append(content)

  return segments

def read_qa_from_txt(file_path):
  # 存储问答对的列表
  qa_list = []
  with open(file_path, 'r', encoding='utf-8') as file:
    lines = file.readlines()
  if len(lines) % 2 != 0:
    raise ValueError("文件中的行数不是偶数，无法正确匹配问题和答案。")
  # 遍历文件内容，将奇数行作为问题，偶数行作为答案
  for i in range(0, len(lines), 2):
    question = lines[i].strip()
    answer = lines[i + 1].strip()
    qa_dict = {'question': question, 'answer': answer}
    qa_list.append(qa_dict)

  return qa_list

class CircularBuffer:
  """
  环形缓冲区类，用于存储和 管理 固定容量 的元素集合。

  Attributes:
      capacity (int): 缓冲区 的最大容量。
      buffer (list): 存储元素 的列表。
      size (int): 缓冲区 当前存储的元素数量。

  Methods:
      __init__(self, capacity): 构造函数，初始化环形缓冲区。
      append(self, item): 向缓冲区添加一个新元素。
      __getitem__(self, index): 通过索引访问缓冲区中的元素。
      __len__(self): 返回缓冲区的当前大小。
      __str__(self): 返回缓冲区的字符串表示。
  """

  def __init__(self, capacity):
    """
    构造函数，用于创建CircularBuffer类的实例。

    Parameters:
        capacity (int): 缓冲区的最大容量。
    """
    self.capacity = capacity
    self.buffer = []
    self.size = 0

  def append(self, item):
    """
    向环形缓冲区添加一个新元素。

    如果缓冲区已满，则先移除头部元素，再添加新元素到尾部；
    如果缓冲区未满，则直接添加新元素到尾部，并更新缓冲区大小。

    Parameters:
        item: 要添加到缓冲区的新元素。
    """
    if self.size >= self.capacity:
      self.buffer.pop(0)
    else:
      self.size += 1
    self.buffer.append(item)

  def __getitem__(self, index):
    """
    通过索引访问环形缓冲区中的元素。

    Parameters:
        index (int): 要访问的元素的索引。

    Returns:
        缓冲区中指定索引处的元素。
    """
    return self.buffer[index]

  def __len__(self):
    """
    返回环形缓冲区的当前大小。

    Returns:
        int: 缓冲区中包含的元素数量。
    """
    return self.size

  def __str__(self):
    """
    返回环形缓冲区的字符串表示。

    Returns:
        str: 缓冲区内容的字符串表示。
    """
    return str(self.buffer)

  def clear(self):
    """
    清空环形缓冲区，移除所有元素。
    """
    self.buffer = []
    self.size = 0


#to_jsonl("我想让你成为我的知识点整理员,你需要按照我的要求把内容存入字典中。你的目标是帮助我整理最佳的知识点信息,这些知识点将为你提供信息参考。你将遵循以下过程：1.首先，你会问我知识点是关于什么的。我会告诉你，但我们需要通过不断的重复来改进它，通过则进行下一步。2.根据我的输入，你会创建三个部分（这三个部分必须存放在一个格式化json的字典结构中）：a)修订整理后的知识点(你整合汇总后的信息，你不要随意删除之前已经提取的信息，应该清晰、精确、易于理解，应当包含之前提取的所有有关信息块)b)建议(你提出建议，哪些细节应该包含在整理的知识点中，以使其更完善)c)问题(你提出相关问题，询问我需要哪些额外信息来补充进你整理的信息)3.你整理的知识点数据应该采用我发出请求的形式，由你执行。4.我们将继续这个迭代过程我会提供更多的信息。你会更新“修订后的，你整理的信息'’部分的请求，直到它完整为止。")
#print((get_hparams_from_file("configs/json/role_setting.json").get("幻")).get("prompt"))


