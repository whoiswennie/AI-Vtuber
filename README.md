# AI-VTUBER

<a href="//github.com/whoiswennie/AI-Vtuber/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/whoiswennie/AI-Vtuber?color=%09%2300BFFF&style=flat-square"></a>   <a href="//github.com/whoiswennie/AI-Vtuber/issues"><img alt="GitHub issues" src="https://img.shields.io/github/issues/whoiswennie/AI-Vtuber?color=Emerald%20green&style=flat-square"></a>   <a href="//github.com/whoiswennie/AI-Vtuber/network"><img alt="GitHub forks" src="https://img.shields.io/github/forks/whoiswennie/AI-Vtuber?color=%2300BFFF&style=flat-square"></a>   <a href="//www.python.org"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python"></a>


---
## 项目简介（推荐优先看）

**本项目旨在实现一个高自由度的可定制AI-VTuber。支持对接哔哩哔哩直播间，以智谱API作为语言基座模型，拥有意图识别、长短期记忆（直接记忆和联想记忆），支持搭建认知库、歌曲作品库，接入了当前热门的一些语音转换、语音合成、图像生成、数字人驱动项目，并提供了一个便于操作的客户端。**

本项目特色：

- 1.本项目对于本地显卡的要求并不高，能正常运行stable-diffusion的电脑基本都能安心食用本项目。
- 2.本项目占地面积可能会比较大（完整部署后大约20多g，还不算第三方项目），主要是因为虚拟环境体积比较大，日后会着手解决该问题。
- 3.本项目内置miniconda3管理虚拟环境，便于用户自行扩展第三方模块。
- 4.本项目提供了一个可视化的客户端（基于streamlit框架构建），支持：环境管理、虚拟主播定制、扩展项目自启动、一些实用的小工具、直播后端监听、图数据库编辑等操作。
- 5.本项目提供了对于so-vits-svc4.1项目的训练-推理一条龙服务。
- 6.本项目提供了一个后端API服务器，支持通过get/post请求获得本项目绝大多数服务。
- 7.本项目支持虚拟主播模板构建、多人设模板管理、实时切换虚拟主播模板等操作。
- 8.当前版本中，本项目对接的开源项目包括：so-vits-svc4.1（语音转换）、GPT-Sovits（语音合成）、UVR5（人声分离）、fast-whisper（语音识别）、stable-diffusion-webui（图像生成）、stable-diffusion-comfyui、easyaivtuber（数字人驱动）、rembg（背景扣除）
- 9.本项目提供的实用小工具包括：视频/音频爬虫、语音识别、人声分离、语音合成、语音转换、AI画画、图片去背景。
- 10.本项目通过构建角色提示词模板、基于知识图谱查询的认知/作品知识库、基于向量数据库的知识库查询构建AI虚拟主播人设（技术实现可以去看作者的语雀文档或者博客）。

---

## 附件

[文档教程(正在更新中)](https://www.yuque.com/alipayxxda4itl6o/xgcgm6)| [视频效果演示（这个是老版本的演示）](https://www.bilibili.com/video/BV1ur421p7CU)|[夸克网盘【提供整合包、预训练模型的下载】](https://pan.quark.cn/s/9f657bc7ab81)


## 使用须知
本项目提供release版以及整合包版。


---
## 当前版本功能介绍

- [x] **当前版本功能：**
  - [x] 对接哔哩哔哩开放平台
  - [x] 支持edge-tts+svc实现定制化的语音合成
  - [x] 支持gpt-sovits
  - [x] 支持智谱api
  - [x] 通过图数据库实现本地歌库多元化搜索
  - [x] 通过向量数据库和知识图谱搭建知识库
  - [x] 自动化的知识图谱制作工具
  - [x] 支持多模板AI虚拟主播定制
  - [x] 具有短期/长期记忆
  - [x] 支持情感聊天
  - [x] 支持对话、唱歌、本地/网络搜索、画画四种意图的任务
  - [x] 对接so-vits-svc并提供训练-推理的一条龙服务
  - [x] 对接sd（webui和comfyui）
  - [x] 对接EasyAiVtuber项目
  - [x] streamlit客户端设计（主要是管理和定制你的ai-vtuber的）

- [ ] **当前主要工作：**
  - [ ] 完善项目文档（在语雀更新【附件中文档教程】）
  - [ ] 录制相关使用教程（在b站更新）
  - [ ] 发布与本项目相关联的第三方项目整合包（【附件中夸克网盘】）

- [ ] **近期更新计划:  **
  - [ ] 支持更多的哔哩哔哩直播间弹幕互动
  - [ ] 字幕机
  - [ ] 支持通过与AI-VTuber的互动生成训练数据
  - [ ] 支持gpt-sovits情感控制
  - [ ] 对接diffsinger，实现一个完整的语音声库定制方案
  - [ ] 支持更多的llm接口方案
  - [ ] 支持更多的TTS接口方案
  - [ ] 高级一点的AI Agent 😏


## 如何启动本项目

**前置准备**

release版需要提前下载预训练模型并将其放置于
```pyth
runtime
├───miniconda3
└───pretrained_models
    ├───faster-whisper
    	└───large-v2
    		└───这里
    ├───gte-base-zh
    	└───这里
tools
├───uvr5
    └───uvr5_weights
        └───这里
```

**在本项目根目录中，存在以下两个bat脚本**

```pyth
运行 condaenv.bat  #本项目主环境搭建（整合包可以忽略这步）
运行 start.bat  #启动客户端
```

## 国内镜像源
```pyth
清华：https://pypi.tuna.tsinghua.edu.cn/simple/
阿里云：http://mirrors.aliyun.com/pypi/simple/
中国科技大学：https://pypi.mirrors.ustc.edu.cn/simple/
华中科技大学：http://pypi.hustunique.com/simple/
上海交通大学：https://mirror.sjtu.edu.cn/pypi/web/simple/
豆瓣：http://pypi.douban.com/simple/
```

## 本项目的数字人效果演示（对接EasyAIVTuber数字人项目实现：以流萤为例）

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


## 对接仓库

https://github.com/xfgryujk/blivedm

https://github.com/ycyy/faster-whisper-webui

https://github.com/svc-develop-team/so-vits-svc

https://github.com/RVC-Boss/GPT-SoVITS

https://github.com/Anjok07/ultimatevocalremovergui

https://github.com/Ksuriuri/EasyAIVtuber

https://github.com/fishaudio/Bert-VITS2