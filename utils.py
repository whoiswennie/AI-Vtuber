# -*- coding: utf-8 -*-

import json
import socket

import torch
import numpy as np
from tqdm import tqdm

def make_padding(width, cropsize, offset):
  left = offset
  roi_size = cropsize - left * 2
  if roi_size == 0:
    roi_size = cropsize
  right = roi_size - (width % roi_size) + left

  return left, right, roi_size


def inference(X_spec, device, model, aggressiveness, data):
  '''
  data ： dic configs
  '''

  def _execute(X_mag_pad, roi_size, n_window, device, model, aggressiveness):
    model.eval()

    with torch.no_grad():
      preds = []

      iterations = [n_window]

      total_iterations = sum(iterations)
      for i in tqdm(range(n_window)):
        start = i * roi_size
        X_mag_window = X_mag_pad[None, :, :, start:start + data['window_size']]
        X_mag_window = torch.from_numpy(X_mag_window).to(device)

        pred = model.predict(X_mag_window, aggressiveness)

        pred = pred.detach().cpu().numpy()
        preds.append(pred[0])

      pred = np.concatenate(preds, axis=2)
    return pred

  def preprocess(X_spec):
    X_mag = np.abs(X_spec)
    X_phase = np.angle(X_spec)

    return X_mag, X_phase

  X_mag, X_phase = preprocess(X_spec)

  coef = X_mag.max()
  X_mag_pre = X_mag / coef

  n_frame = X_mag_pre.shape[2]
  pad_l, pad_r, roi_size = make_padding(n_frame,
                                        data['window_size'], model.offset)
  n_window = int(np.ceil(n_frame / roi_size))

  X_mag_pad = np.pad(
    X_mag_pre, ((0, 0), (0, 0), (pad_l, pad_r)), mode='constant')

  pred = _execute(X_mag_pad, roi_size, n_window,
                  device, model, aggressiveness)
  pred = pred[:, :, :n_frame]

  if data['tta']:
    pad_l += roi_size // 2
    pad_r += roi_size // 2
    n_window += 1

    X_mag_pad = np.pad(
      X_mag_pre, ((0, 0), (0, 0), (pad_l, pad_r)), mode='constant')

    pred_tta = _execute(X_mag_pad, roi_size, n_window,
                        device, model, aggressiveness)
    pred_tta = pred_tta[:, :, roi_size // 2:]
    pred_tta = pred_tta[:, :, :n_frame]

    return (pred + pred_tta) * 0.5 * coef, X_mag, np.exp(1.j * X_phase)
  else:
    return pred * coef, X_mag, np.exp(1.j * X_phase)


def _get_name_params(model_path, model_hash):
  ModelName = model_path
  if model_hash == '47939caf0cfe52a0e81442b85b971dfd':
    model_params_auto = str('lib_v5/modelparams/4band_44100.json')
    param_name_auto = str('4band_44100')
  if model_hash == '4e4ecb9764c50a8c414fee6e10395bbe':
    model_params_auto = str('lib_v5/modelparams/4band_v2.json')
    param_name_auto = str('4band_v2')
  if model_hash == 'e60a1e84803ce4efc0a6551206cc4b71':
    model_params_auto = str('lib_v5/modelparams/4band_44100.json')
    param_name_auto = str('4band_44100')
  if model_hash == 'a82f14e75892e55e994376edbf0c8435':
    model_params_auto = str('lib_v5/modelparams/4band_44100.json')
    param_name_auto = str('4band_44100')
  if model_hash == '6dd9eaa6f0420af9f1d403aaafa4cc06':
    model_params_auto = str('lib_v5/modelparams/4band_v2_sn.json')
    param_name_auto = str('4band_v2_sn')
  if model_hash == '5c7bbca45a187e81abbbd351606164e5':
    model_params_auto = str('lib_v5/modelparams/3band_44100_msb2.json')
    param_name_auto = str('3band_44100_msb2')
  if model_hash == 'd6b2cb685a058a091e5e7098192d3233':
    model_params_auto = str('lib_v5/modelparams/3band_44100_msb2.json')
    param_name_auto = str('3band_44100_msb2')
  if model_hash == 'c1b9f38170a7c90e96f027992eb7c62b':
    model_params_auto = str('lib_v5/modelparams/4band_44100.json')
    param_name_auto = str('4band_44100')
  if model_hash == 'c3448ec923fa0edf3d03a19e633faa53':
    model_params_auto = str('lib_v5/modelparams/4band_44100.json')
    param_name_auto = str('4band_44100')
  if model_hash == '68aa2c8093d0080704b200d140f59e54':
    model_params_auto = str('lib_v5/modelparams/3band_44100.json')
    param_name_auto = str('3band_44100.json')
  if model_hash == 'fdc83be5b798e4bd29fe00fe6600e147':
    model_params_auto = str('lib_v5/modelparams/3band_44100_mid.json')
    param_name_auto = str('3band_44100_mid.json')
  if model_hash == '2ce34bc92fd57f55db16b7a4def3d745':
    model_params_auto = str('lib_v5/modelparams/3band_44100_mid.json')
    param_name_auto = str('3band_44100_mid.json')
  if model_hash == '52fdca89576f06cf4340b74a4730ee5f':
    model_params_auto = str('lib_v5/modelparams/4band_44100.json')
    param_name_auto = str('4band_44100.json')
  if model_hash == '41191165b05d38fc77f072fa9e8e8a30':
    model_params_auto = str('lib_v5/modelparams/4band_44100.json')
    param_name_auto = str('4band_44100.json')
  if model_hash == '89e83b511ad474592689e562d5b1f80e':
    model_params_auto = str('lib_v5/modelparams/2band_32000.json')
    param_name_auto = str('2band_32000.json')
  if model_hash == '0b954da81d453b716b114d6d7c95177f':
    model_params_auto = str('lib_v5/modelparams/2band_32000.json')
    param_name_auto = str('2band_32000.json')

  # v4 Models
  if model_hash == '6a00461c51c2920fd68937d4609ed6c8':
    model_params_auto = str('lib_v5/modelparams/1band_sr16000_hl512.json')
    param_name_auto = str('1band_sr16000_hl512')
  if model_hash == '0ab504864d20f1bd378fe9c81ef37140':
    model_params_auto = str('lib_v5/modelparams/1band_sr32000_hl512.json')
    param_name_auto = str('1band_sr32000_hl512')
  if model_hash == '7dd21065bf91c10f7fccb57d7d83b07f':
    model_params_auto = str('lib_v5/modelparams/1band_sr32000_hl512.json')
    param_name_auto = str('1band_sr32000_hl512')
  if model_hash == '80ab74d65e515caa3622728d2de07d23':
    model_params_auto = str('lib_v5/modelparams/1band_sr32000_hl512.json')
    param_name_auto = str('1band_sr32000_hl512')
  if model_hash == 'edc115e7fc523245062200c00caa847f':
    model_params_auto = str('lib_v5/modelparams/1band_sr33075_hl384.json')
    param_name_auto = str('1band_sr33075_hl384')
  if model_hash == '28063e9f6ab5b341c5f6d3c67f2045b7':
    model_params_auto = str('lib_v5/modelparams/1band_sr33075_hl384.json')
    param_name_auto = str('1band_sr33075_hl384')
  if model_hash == 'b58090534c52cbc3e9b5104bad666ef2':
    model_params_auto = str('lib_v5/modelparams/1band_sr44100_hl512.json')
    param_name_auto = str('1band_sr44100_hl512')
  if model_hash == '0cdab9947f1b0928705f518f3c78ea8f':
    model_params_auto = str('lib_v5/modelparams/1band_sr44100_hl512.json')
    param_name_auto = str('1band_sr44100_hl512')
  if model_hash == 'ae702fed0238afb5346db8356fe25f13':
    model_params_auto = str('lib_v5/modelparams/1band_sr44100_hl1024.json')
    param_name_auto = str('1band_sr44100_hl1024')
    # User Models

  # 1 Band
  if '1band_sr16000_hl512' in ModelName:
    model_params_auto = str('lib_v5/modelparams/1band_sr16000_hl512.json')
    param_name_auto = str('1band_sr16000_hl512')
  if '1band_sr32000_hl512' in ModelName:
    model_params_auto = str('lib_v5/modelparams/1band_sr32000_hl512.json')
    param_name_auto = str('1band_sr32000_hl512')
  if '1band_sr33075_hl384' in ModelName:
    model_params_auto = str('lib_v5/modelparams/1band_sr33075_hl384.json')
    param_name_auto = str('1band_sr33075_hl384')
  if '1band_sr44100_hl256' in ModelName:
    model_params_auto = str('lib_v5/modelparams/1band_sr44100_hl256.json')
    param_name_auto = str('1band_sr44100_hl256')
  if '1band_sr44100_hl512' in ModelName:
    model_params_auto = str('lib_v5/modelparams/1band_sr44100_hl512.json')
    param_name_auto = str('1band_sr44100_hl512')
  if '1band_sr44100_hl1024' in ModelName:
    model_params_auto = str('lib_v5/modelparams/1band_sr44100_hl1024.json')
    param_name_auto = str('1band_sr44100_hl1024')

  # 2 Band
  if '2band_44100_lofi' in ModelName:
    model_params_auto = str('lib_v5/modelparams/2band_44100_lofi.json')
    param_name_auto = str('2band_44100_lofi')
  if '2band_32000' in ModelName:
    model_params_auto = str('lib_v5/modelparams/2band_32000.json')
    param_name_auto = str('2band_32000')
  if '2band_48000' in ModelName:
    model_params_auto = str('lib_v5/modelparams/2band_48000.json')
    param_name_auto = str('2band_48000')

  # 3 Band
  if '3band_44100' in ModelName:
    model_params_auto = str('lib_v5/modelparams/3band_44100.json')
    param_name_auto = str('3band_44100')
  if '3band_44100_mid' in ModelName:
    model_params_auto = str('lib_v5/modelparams/3band_44100_mid.json')
    param_name_auto = str('3band_44100_mid')
  if '3band_44100_msb2' in ModelName:
    model_params_auto = str('lib_v5/modelparams/3band_44100_msb2.json')
    param_name_auto = str('3band_44100_msb2')

  # 4 Band
  if '4band_44100' in ModelName:
    model_params_auto = str('lib_v5/modelparams/4band_44100.json')
    param_name_auto = str('4band_44100')
  if '4band_44100_mid' in ModelName:
    model_params_auto = str('lib_v5/modelparams/4band_44100_mid.json')
    param_name_auto = str('4band_44100_mid')
  if '4band_44100_msb' in ModelName:
    model_params_auto = str('lib_v5/modelparams/4band_44100_msb.json')
    param_name_auto = str('4band_44100_msb')
  if '4band_44100_msb2' in ModelName:
    model_params_auto = str('lib_v5/modelparams/4band_44100_msb2.json')
    param_name_auto = str('4band_44100_msb2')
  if '4band_44100_reverse' in ModelName:
    model_params_auto = str('lib_v5/modelparams/4band_44100_reverse.json')
    param_name_auto = str('4band_44100_reverse')
  if '4band_44100_sw' in ModelName:
    model_params_auto = str('lib_v5/modelparams/4band_44100_sw.json')
    param_name_auto = str('4band_44100_sw')
  if '4band_v2' in ModelName:
    model_params_auto = str('lib_v5/modelparams/4band_v2.json')
    param_name_auto = str('4band_v2')
  if '4band_v2_sn' in ModelName:
    model_params_auto = str('lib_v5/modelparams/4band_v2_sn.json')
    param_name_auto = str('4band_v2_sn')
  if 'tmodelparam' in ModelName:
    model_params_auto = str('lib_v5/modelparams/tmodelparam.json')
    param_name_auto = str('User Model Param Set')
  return param_name_auto, model_params_auto

class HParams():
  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      if type(v) == dict:
        v = HParams(**v)
      self[k] = v

  def keys(self):
    return self.__dict__.keys()

  def items(self):
    return self.__dict__.items()

  def values(self):
    return self.__dict__.values()

  def __len__(self):
    return len(self.__dict__)

  def __getitem__(self, key):
    return getattr(self, key)

  def __setitem__(self, key, value):
    return setattr(self, key, value)

  def __contains__(self, key):
    return key in self.__dict__

  def __repr__(self):
    return self.__dict__.__repr__()

  def get(self,index):
    return self.__dict__.get(index)

def get_hparams_from_file(config_path):
  with open(config_path, "r", encoding="utf-8") as f:
    data = f.read()
  config = json.loads(data)
  hparams =HParams(**config)
  return hparams

def write_json(data_dict,path):
  with open(path, 'w', encoding='utf-8') as json_file:
    json.dump(data_dict, json_file, ensure_ascii=False, indent=4)

def update_progress(current_time, total_duration, progress):
  print(f"A: {current_time} / {total_duration} ({progress}%)", end='\r')

def to_jsonl(sys_prompt):
    # 读取原始JSON文件并转换为JSON Lines格式
    with open('dataset/answers.json', 'r', encoding='utf-8') as f:
      # 遍历文件的每一行
      with open('dataset/converted_data.jsonl', 'w', encoding='utf-8') as out_file:
        for line in f:
          # 解析JSON对象
          data = json.loads(line)
          print(data)
          # 提取问题和完成部分
          prompt = data["prompt"].split("问题：")[1].strip()
          print(prompt)
          completion = data["completion"]  # 将completion视为字符串
          # 将数据转换为新的格式并写入到JSON Lines文件中
          messages = [{"role": "system", "content": sys_prompt},{"role": "user", "content": prompt}, {"role": "assistant", "content": completion}]
          out_file.write(json.dumps({"messages": messages}, ensure_ascii=False) + '\n')


def check_port(host, port):
  # 创建一个套接字对象
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    # 尝试连接到指定的主机和端口
    s.connect((host, port))
    # 如果连接成功，说明端口已被占用
    # print(f"Port {port} on {host} is already in use")
    return True
  except socket.error as e:
    # 如果连接失败，说明端口未被占用
    # print(f"Port {port} on {host} is not in use")
    return False
  finally:
    # 关闭套接字连接
    s.close()

#to_jsonl("我想让你成为我的知识点整理员,你需要按照我的要求把内容存入字典中。你的目标是帮助我整理最佳的知识点信息,这些知识点将为你提供信息参考。你将遵循以下过程：1.首先，你会问我知识点是关于什么的。我会告诉你，但我们需要通过不断的重复来改进它，通过则进行下一步。2.根据我的输入，你会创建三个部分（这三个部分必须存放在一个格式化json的字典结构中）：a)修订整理后的知识点(你整合汇总后的信息，你不要随意删除之前已经提取的信息，应该清晰、精确、易于理解，应当包含之前提取的所有有关信息块)b)建议(你提出建议，哪些细节应该包含在整理的知识点中，以使其更完善)c)问题(你提出相关问题，询问我需要哪些额外信息来补充进你整理的信息)3.你整理的知识点数据应该采用我发出请求的形式，由你执行。4.我们将继续这个迭代过程我会提供更多的信息。你会更新“修订后的，你整理的信息'’部分的请求，直到它完整为止。")
