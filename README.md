# AI-VTUBER



[![Build Status](https://www.travis-ci.org/{whoiswennie}/{AI-Vtuber}.svg?branch=master)](https://www.travis-ci.org/{whoiswennie}/{AI-Vtuber})

[文档教程](https://www.yuque.com/alipayxxda4itl6o/xgcgm6)


## 使用须知

---
## 当前版本介绍（因为很多功能正在调整中，暂时就写一个简略的说明，等该版本稳定后会提供详细的教学视频和文档）
#### --1.支持与哔哩哔哩直播间对接
#### -----支持弹幕聊天、唱歌【此功能对接创作者自制的歌库图数据库，支持用歌名、原唱、歌曲语言、风格、自定义的标签等来点歌，播放队列可以无限添加（最新一次的点歌会插队播放）】、点歌【支持哔哩哔哩和网易云非会员歌曲点歌，会优先于唱歌队列播放】、翻唱【支持对之前点歌的音频进行实时翻唱（对接你的so-vits-svc4.1）】
#### --2.支持定制化
#### -----支持歌库定制【将你做好的翻唱信息按要求填写在歌库.csv中，启动streamlit_agent.py可以将其录入你的图数据库中】、支持角色性格和认知定制【在streamlit页面端中可以给你的虚拟主播塑造性格和基础认知，大致原理就是通过向量数据库来进行长期记忆存储，其中每一个认知实体都会在索引表中建立目录，之后在聊天时会根据用户的问题去合适的目录索引对应的向量数据，ai会根据涉及到的关键词产生情绪的变动，情绪会最终反馈在说话的语气里】

---

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

#### 更多详细教程请运行
```pyth
streamlit run streamlit_agent.py
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

## 预训练模型和其余配置文件
夸克网盘链接:https://pan.quark.cn/s/a039b9c03692

#### 建立图数据库
环境：jdk-15
图数据库版本:neo4j-4.2

#### 虚拟声卡
voicemeeter

#### 预训练模型存放路径

【faster-whisper】

###### AI-Vtuber/faster-whisper-webui/Models/faster-whisper/large-v2（v3暂时有bug）
###### AI-Vtuber/faster-whisper-webui/Models/silero-vad

【gte-base-zh】

###### AI-Vtuber/pretrained_models/gte-base-zh
【uvr5】

###### AI-Vtuber/pretrained_models/uvr5/models