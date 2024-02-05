# AI-VTUBER

## 使用须知

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