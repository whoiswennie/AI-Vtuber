chcp 65001
@echo off

echo 初始化并启动WebUI……初次启动可能会花上较长时间
echo Initialize and start the WebUI... It may take a while for the first time launch.
echo WebUI运行过程中请勿关闭此窗口！
echo Please do not close this window while the WebUI is running!


..\..\runtime\miniconda3\envs\faster-whisper\python.exe setup.py
..\..\runtime\miniconda3\envs\faster-whisper\python.exe app.py --input_audio_max_duration -1 --auto_parallel True

pause