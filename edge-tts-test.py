# -*- coding: utf-8 -*-
import edge_tts
import asyncio

voice = 'zh-CN-YunxiNeural'
output = 'demo.mp3'
rate = '-4%'
volume = '+0%'
async def my_function():
    tts = edge_tts.Communicate(text = "晚上好",voice = voice,rate = rate,volume=volume)
    await tts.save(output)
if __name__ == '__main__':
    asyncio.run(my_function())