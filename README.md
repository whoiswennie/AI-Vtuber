# AI-VTUBER

<a href="//github.com/whoiswennie/AI-Vtuber/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/whoiswennie/AI-Vtuber?color=%09%2300BFFF&style=flat-square"></a>   <a href="//github.com/whoiswennie/AI-Vtuber/issues"><img alt="GitHub issues" src="https://img.shields.io/github/issues/whoiswennie/AI-Vtuber?color=Emerald%20green&style=flat-square"></a>   <a href="//github.com/whoiswennie/AI-Vtuber/network"><img alt="GitHub forks" src="https://img.shields.io/github/forks/whoiswennie/AI-Vtuber?color=%2300BFFF&style=flat-square"></a>   <a href="//www.python.org"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python"></a>


---
## 项目简介

本项目旨在实现一个高自由度的可定制AI-VTuber。支持对接哔哩哔哩直播间，以智谱API作为语言基座模型，拥有意图识别、长短期记忆（直接记忆和联想记忆），支持搭建认知库、歌曲作品库，接入了当前热门的一些语音转换、语音合成、图像生成、数字人驱动项目。提供了一个便于操作的客户端。

---

## 附件

[文档教程(正在更新中)](https://www.yuque.com/alipayxxda4itl6o/xgcgm6)| [视频效果演示（这个是老版本的演示）](https://www.bilibili.com/video/BV1ur421p7CU)


## VTuber数字人效果演示（对接EasyAIVTuber数字人项目实现：以流萤为例）

[流萤：睡眠状态]

https://github.com/whoiswennie/AI-Vtuber/assets/104626642/4422cde1-e6c2-4c7c-8562-f5f1d2ab5c8c

<video width="640" height="360" controls>
  <source src="assets/ly_sleep.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

[流萤：说话状态]

https://github.com/whoiswennie/AI-Vtuber/assets/104626642/6bb1bfda-c1e4-4a16-812d-f155f3c7619c

<video width="640" height="360" controls>
  <source src="assets/ly_talk.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

[流萤：点歌状态]

https://github.com/whoiswennie/AI-Vtuber/assets/104626642/8e5db4d6-f71c-4a94-a474-e5bd5f31f251

<video width="640" height="360" controls>
  <source src="assets/ly_search.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

[流萤：唱歌状态]

https://github.com/whoiswennie/AI-Vtuber/assets/104626642/db5347d6-95f7-4836-95fd-00040e9826c4

<video width="640" height="360" controls>
  <source src="assets/ly_sing.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

---

## 使用须知
请注意：由于当前仓库缺失一些大容量的重要文件，导致当前分支的源码暂时无法复现，本分支在与主分支合并后会提供完成的源码仓库和整合包，请耐心等待。

---
## 当前版本功能介绍
**【正在施工中】**


---

## 当前版本代办清单
- [ ] **当前版本功能：**
  - [x] 对接哔哩哔哩开放平台
  - [x] 支持edge-tts+svc实现定制化的语音合成
  - [x] 支持bert-vits2
  - [x] 支持gpt-sovits
  - [x] 支持智谱api和已开源的chatglm3模型
  - [x] 可以通过弹幕指令跟AI-Vtuber进行互动
  - [x] 通过图数据库实现本地歌库多元化搜索
  - [x] 通过向量数据库和关键词词表搭建长期记忆知识库
  - [x] 支持简单的情感聊天
  - [x] 支持直播代理功能（让你的ai主播闲不下来）
  - [x] 支持直播时在线翻唱（实验性功能，后续会调整）
  - [x] 支持bv号点歌和网易云点歌（非会员）
  - [x] 构建类memgpt式的记忆滑动窗口做短期记忆搜索
  - [ ] 对接sd（webui和comfyui）
  - [x] 对接ikaros-521的字幕打印器项目
  - [x] 对接EasyAiVtuber项目
  - [ ] 支持通过按键映射来调整live2d动作
  - [x] 支持视频学习（本质上是听音频）和文本学习
  - [x] 简单的代理学习（通过智谱的搜索插件来比较偷懒的制作知识库，人类可以随时干预）
  - [x] streamlit客户端设计（主要是管理和定制你的ai-vtuber的）

- [ ] **当前主要工作：**

  - [x] 制作测试版本整合包（内置了流萤人设）
  - [ ] 完善项目文档
  - [ ] 录制相关使用教程
  - [ ] 完善streamlit客户端
  - [ ] 发布第一版正式整合包

- [ ] **未来更新计划:**
  - [ ] 支持更多的哔哩哔哩直播间弹幕互动
  - [ ] 支持gpt-sovits情感控制
  - [ ] 对接diffsinger，实现一个完整的语音声库定制方案
  - [ ] 支持更多的llm接口方案
  - [ ] 支持更多的TTS接口方案
  - [ ] 利用comfyui工作流搞点事 😏


## 创建虚拟环境

```pyth
conda create --name ai-vtuber python=3.10
```

## 配置环境

```pyth
# 先执行
pip install -r requirements.txt
# 国内源通常会下载cpu版的torch，手动卸载
pip uninstall torch
# 下载cuda版本的torch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### streamlit页面版客户端
```pyth
start.bat  #启动客户端
```

##### 国内镜像源
```pyth
清华：https://pypi.tuna.tsinghua.edu.cn/simple/
阿里云：http://mirrors.aliyun.com/pypi/simple/
中国科技大学：https://pypi.mirrors.ustc.edu.cn/simple/
华中科技大学：http://pypi.hustunique.com/simple/
上海交通大学：https://mirror.sjtu.edu.cn/pypi/web/simple/
豆瓣：http://pypi.douban.com/simple/
```

## 对接仓库

https://github.com/xfgryujk/blivedm

https://github.com/ycyy/faster-whisper-webui

https://github.com/svc-develop-team/so-vits-svc

https://github.com/RVC-Boss/GPT-SoVITS

https://github.com/Anjok07/ultimatevocalremovergui

https://github.com/Ksuriuri/EasyAIVtuber

https://github.com/fishaudio/Bert-VITS2