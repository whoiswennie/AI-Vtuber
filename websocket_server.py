import asyncio
import json
import websockets
import webview

# 与 JavaScript 进行通信的 WebSocket 服务器
async def websocket_server(websocket, path):
    # 获取音频和视频设备信息
    device_info = await websocket.recv()

    # 打印可用的音频和视频设备信息
    print("音频输入源:")
    for device in device_info['audioInput']:
        print(device['label'])

    print("音频输出目的地:")
    for device in device_info['audioOutput']:
        print(device['label'])

    print("视频输入源:")
    for device in device_info['videoInput']:
        print(device['label'])

    # 发送设备信息给客户端
    await websocket.send(json.dumps(device_info))

# 创建一个简单的 webview 应用程序
def main():
    # 启动 WebSocket 服务器
    start_server = websockets.serve(websocket_server, "localhost", 8765)
    asyncio.get_event_loop().run_until_complete(start_server)

    # 创建一个简单的 webview 窗口，并在加载完成时执行 connect_and_send_device_info 函数
    webview.create_window("ai-vtuber", "https://webrtc.github.io/samples/src/content/devices/input-output/")

    # 启动应用程序
    webview.start()

if __name__ == "__main__":
    main()
