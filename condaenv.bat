@echo off
chcp 65001
runtime\miniconda3\envs\ai-vtuber\python.exe  -m pip install -r requirements_ai_vtuber_simple.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
runtime\miniconda3\envs\ai-vtuber\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
cmd /k
