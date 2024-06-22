import requests
import os

url = "http://localhost:9550/"
port_data = {
    "show":"",
    "switch_role":{"role_key":"","tts_plan":1,"easyaivtuber_img":""},
    "chat":{"query": "你好"},
    "tts":{"tts_plan": 1, "text": "", "AudioCount": 1},
    "mpv_play":"mpv_play",
    "action":{"type": "", "speech_path": "template/tts/1.wav"},
    "tool/information_to_neo4j":{"text":""},
    "search_in_neo4j":{"content":"流萤身份是什么"},
    "search_song_from_neo4j":{"content":"我想听代表作，仙气一点的"}
}

def post_to_api(port,data):
    res = requests.post(f'http://localhost:9550/{port}', json=data)
    print(res.json())
    return res

if __name__ == '__main__':
    res = post_to_api("search_song_from_neo4j",port_data["search_song_from_neo4j"]).json()
    post_to_api("mpv_play", {"wav_path":os.path.join(res["songdatabase_root"],res["songlist"][0]+".wav")})