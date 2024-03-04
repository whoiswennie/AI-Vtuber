from flask import Flask, request

live_broadcast_data_monitor = {}
pre_live_broadcast_data_monitor = {}

app = Flask(__name__)

@app.route('/api', methods=['POST'])
def api():
    global live_broadcast_data_monitor,pre_live_broadcast_data_monitor
    live_broadcast_data_monitor = request.json
    if pre_live_broadcast_data_monitor != live_broadcast_data_monitor:
        pre_live_broadcast_data_monitor = live_broadcast_data_monitor
        for key, value in pre_live_broadcast_data_monitor.items():
            if key == "is_ai_ready":
                status = 'llm模型正在合成中' if value == 0 else 'llm模型闲置中'
            elif key == "is_tts_ready":
                status = 'tts模型正在合成中' if value == 0 else 'tts模型闲置中'
            elif key == "is_tts_play_ready":
                status = 'tts播放器正在播放音频' if value == 0 else 'tts播放器闲置中'
            elif key == "is_song_play_ready" or key == "is_song_cover_ready":
                status = '歌曲播放器正在播放歌曲(唱歌功能)' if value == 0 else '歌曲播放器闲置中'
            elif key == "is_obs_ready":
                status = '存在可用虚拟摄像机' if value == 0 else '不存在可用虚拟摄像机'
            elif key == "is_obs_play_ready":
                status = '虚拟摄像机正在切换图片' if value == 0 else '虚拟摄像机闲置中'
            elif key == "is_web_captions_printer_ready":
                status = '字幕打印机投屏中' if value == 0 else '字幕打印器已就绪'
            else:
                status = value

            print(status)
    return live_broadcast_data_monitor

def run_flask():
    app.run(debug=False, host='0.0.0.0', port=9550, threaded=True)

if __name__ == "__main__":
    run_flask()