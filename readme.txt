conda create --name ai-vtuber python=3.10
pip install fuzzywuzzy==0.18.0
pip install pandas
pip install py2neo
pip install neo4j
pip install ffmpeg-python
pip install bilibili-api-python
pip install edge_tts
pip install spleeter -i https://pypi.tuna.tsinghua.edu.cn/simple
https://github.com/deezer/spleeter/releases/download/v1.4.0/2stems.tar.gz
pip install pydub

#stt教程：https://zhuanlan.zhihu.com/p/664892334
pip install faster-whisper
https://huggingface.co/guillaumekln/faster-whisper-large-v2
https://huggingface.co/Systran/faster-whisper-large-v3
git clone https://github.com/ycyy/faster-whisper-webui.git
cd faster-whisper-webui
pip3 install -r requirements.txt
pip3 install -r requirements-fasterWhisper.txt
pip uninstall torch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
python cli.py --model large-v2 --vad silero-vad --language Japanese --output_dir d:/whisper_model d:/Downloads/test.mp4
python cli.py --whisper_implementation faster-whisper --model large-v2 --vad silero-vad --language Chinese --output_dir C:/Users/32873/Desktop/ai/AI-Vtuber/AI-Vtuber_huan/output C:/Users/32873/Desktop/ai/AI-Vtuber/AI-Vtuber_huan/download/棉花糖-这就是天幻呀.wav
# 中文字幕
python cli.py --whisper_implementation faster-whisper --model large-v2 --vad silero-vad --language Chinese --output_dir d:/whisper_model d:/Downloads/test.mp4

pip install zhipuai
pip install langchain
pip install langchain_community
pip install sentence_transformers
pip install chromadb


#AttributeError: module 'click.utils' has no attribute '_expand_args'
pip install -U click

pip install streamlit
pip install pyaudio

# about uvr5
librosa==0.9.2
numba==0.56.4
python spleeter_to_svc.py -ap "download/我不曾忘记-花玲.wav" -sp "output/template_load" -mp "pretrained_models/uvr5/models/Main_Models/2_HP-UVR.pth"




