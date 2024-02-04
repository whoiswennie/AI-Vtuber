---
title: Faster Whisper Webui
emoji: 🚀
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 3.23.0
app_file: app.py
pinned: false
license: apache-2.0
---
[**English**](README.md) | [**中文文档**](README_zh_CN.md)

请查看配置参考，网址为： https://huggingface.co/docs/hub/spaces-config-reference

本项目复制自 [aadnk/whisper-webui](https://gitlab.com/aadnk/whisper-webui), 为了个人使用我在此基础上进行了修改。

# 本地运行

要在本地运行此程序，首先需要安装Python 3.9+和Git。然后安装Pytorch 10.1+和所有其他依赖项：
```
pip install -r requirements.txt
```
项目模型为本地加载，需要在项目路径下创建`models`目录，然后按照如下格式放置模型文件
```
├─faster-whisper
│  ├─base
│  ├─large
│  ├─large-v2
│  ├─medium
│  ├─small
│  └─tiny
└─silero-vad
    ├─examples
    │  ├─cpp
    │  ├─microphone_and_webRTC_integration
    │  └─pyaudio-streaming
    ├─files
    └─__pycache__
```
### 模型下载地址

[faster-whisper](https://huggingface.co/guillaumekln)

[silero-vad](https://github.com/snakers4/silero-vad)

您可以在Windows 10/11上找到安装详细说明： [here (PDF)](docs/windows/install_win10_win11.pdf).

最后，启用并行CPU/GPU，运行应用程序的完整版本（无音频长度限制）：
```
python app.py --input_audio_max_duration -1 --server_name 127.0.0.1 --auto_parallel True
```

您还可以运行CLI界面，它类似于Whisper自己的CLI，但还支持以下额外的参数：
```
python cli.py \
[--vad {none,silero-vad,silero-vad-skip-gaps,silero-vad-expand-into-gaps,periodic-vad}] \
[--vad_merge_window VAD_MERGE_WINDOW] \
[--vad_max_merge_size VAD_MAX_MERGE_SIZE] \
[--vad_padding VAD_PADDING] \
[--vad_prompt_window VAD_PROMPT_WINDOW]
[--vad_cpu_cores NUMBER_OF_CORES]
[--vad_parallel_devices COMMA_DELIMITED_DEVICES]
[--auto_parallel BOOLEAN]
```
此外，您还可以使用URL作为输入，而不仅仅是文件路径。
```
python cli.py --model large --vad silero-vad --language Japanese "https://www.youtube.com/watch?v=4cICErqqRSM"
```

您可以使用配置文件`config.json5`而不是向`app.py`或`cli.py`提供参数。请参阅该文件以获取更多信息。
如果您想使用不同的配置文件，则可以使用`WHISPER_WEBUI_CONFIG`环境变量来指定另一个文件的路径。
### 多个文件


您可以通过“上传文件”选项或作为YouTube上的播放列表上传多个文件。
然后，每个音频文件将依次进行处理，并将生成的SRT/VTT/Transcript放在“下载”部分中。
当处理多个文件时，UI还将生成一个“All_Output”zip文件，其中包含所有文本输出文件。

### 一键启动
针对新手用户，可以在`Releases`页面下载免安装程序。点击`webui-start.bat`启动程序，然后在浏览器输入对应地址访问即可(仅包含`small` 模型，其他模型自行下载)。