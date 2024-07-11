import time

import base64
import json
import requests
import urllib.request
import urllib.parse
import utils
import uuid
import random
import websocket

mode_list = ["背景","立绘","其他"]
negative_prompt = "Easynagative,bad,worse,nsfw"
steps = 30
sampler_name = ["Euler a","DPM++ 2M SDE"]


def sd_webui_generate_image(prompt, image_name, mode, negative_prompt, steps, sampler_name, sd_model_checkpoint):
    global mode_list
    hps = utils.get_hparams_from_file("configs/json/config.json")
    url = hps.api_path.stable_diffusion.webui_url

    if mode == "背景":
        width = 960
        height = 540
        prompt2 = "(no_human)"

    elif mode == "立绘":
        width = 512
        height = 768
        prompt2 = "masterpiece,wallpaper,simple background,(upper_body),solo"

    else:
        width = 512
        height = 512
        prompt2 = ""

    payload = {
        "prompt": f"{prompt},{prompt2}",
        "negative_prompt": negative_prompt,
        "override_settings": {
            "sd_model_checkpoint": sd_model_checkpoint
        },
        "steps": steps,
        "sampler_name": sampler_name,
        "width": width,
        "height": height,
        "restore_faces": False,
        "enable_hr": True,
        "hr_upscaler": "R-ESRGAN 4x+ Anime6B",
        "hr_scale": 2,
        "hr_second_pass_steps": 15,
        "denoising_strength": 0.3,
    }

    try:
        response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
        if response.status_code == 200:
            r = response.json()
            for i, img_data in enumerate(r['images']):
                if ',' in img_data:
                    base64_data = img_data.split(",", 1)[1]
                else:
                    base64_data = img_data
                image_data = base64.b64decode(base64_data)
                final_image_name = f'{image_name}.png'
                with open(fr'template\img\{final_image_name}', 'wb') as f:
                    f.write(image_data)
                print(f'图片已保存为 {final_image_name}')
                return 200

        else:
            print("Failed to generate image:", response.text)
            return "Failed to generate image:"+response.text

    except:
        print("绘图失败！")
        return "绘图失败！"

def sd_comfyui_generate_image(prompt,api_json):
    url = '127.0.0.1:8188'
    client_id = str(
        uuid.uuid4())  # 生成一个唯一的客户端ID

    def queue_prompt(prompt):
        p = {"prompt": prompt, "client_id": client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request("http://{}/prompt".format(url), data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def get_history(prompt_id):
        with urllib.request.urlopen("http://{}/history/{}".format(url, prompt_id)) as response:
            return json.loads(response.read())

    def get_image(filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen("http://{}/view?{}".format(url, url_values)) as response:
            return response.read()

    def get_images(ws, prompt):
        prompt_id = queue_prompt(prompt)['prompt_id']
        print('prompt')
        print(prompt)
        print('prompt_id:{}'.format(prompt_id))
        output_images = {}
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        print('执行完成')
                        break
                    else:
                        continue
            max_attempts = 10  # 设置最大尝试次数
            attempts = 0

            while attempts < max_attempts:
                try:
                    history = get_history(prompt_id)[prompt_id]
                    break  # 如果成功，退出循环
                except KeyError:
                    attempts += 1
                    time.sleep(1)

            if attempts == max_attempts:
                print("尝试次数已达到上限，操作失败。")

            for o in history['outputs']:
                for node_id in history['outputs']:
                    node_output = history['outputs'][node_id]
                    # 图片分支
                    if 'images' in node_output:
                        images_output = []
                        for image in node_output['images']:
                            image_data = get_image(image['filename'], image['subfolder'], image['type'])
                            images_output.append(image_data)
                        output_images[node_id] = images_output
                    # 视频分支
                    if 'videos' in node_output:
                        videos_output = []
                        for video in node_output['videos']:
                            video_data = get_image(video['filename'], video['subfolder'], video['type'])
                            videos_output.append(video_data)
                        output_images[node_id] = videos_output
            print('获取图片完成')
            return output_images
    def parse_worflow(ws, prompt,api_json):
        api_json["6"]["inputs"]["text"] = prompt
        return get_images(ws, api_json)
    def generate_clip(prompt, seed, api_json, idx):
        print('seed:' + str(seed))
        ws = websocket.WebSocket()
        ws.connect("ws://{}/ws?clientId={}".format(url, client_id))
        images = parse_worflow(ws, prompt,api_json)
        images_name_list = []
        for node_id in images:
            for image_data in images[node_id]:
                from datetime import datetime
                # 获取当前时间，并格式化为 YYYYMMDDHHMMSS 的格式
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                # 使用格式化的时间戳在文件名中
                GIF_LOCATION = "template/img/{}_{}_{}.png".format(idx, seed, timestamp)
                images_name_list.append(GIF_LOCATION)
                with open(GIF_LOCATION, "wb") as binary_file:
                    # 写入二进制文件
                    binary_file.write(image_data)
                print("{} DONE!!!".format(GIF_LOCATION))
        return images_name_list

    seed = random.randint(0, 2**32 - 1)
    images_name_list = generate_clip(prompt, seed, api_json,0)
    return images_name_list



