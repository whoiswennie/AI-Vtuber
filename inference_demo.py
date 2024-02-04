import os,torch
import librosa
import argparse
import importlib
import  numpy as np
import hashlib , math
import soundfile as sf
from tqdm import  tqdm
from lib_v5 import spec_utils
from utils import _get_name_params,inference
from lib_v5.model_param_init import ModelParameters

project_root = os.path.dirname(os.path.abspath(__file__))

class  _audio_pre_():
    def __init__(self, model_path = '/home/nr/uvr5/models/Main_Models/2_HP-UVR.pth',
                                device='cpu',**keys):
        self.model_path = model_path
        self.device = device
        self.data = {
            # Processing Options
            'postprocess': True,
            'tta': True,
            # Constants
            'window_size': 512,
            'agg': 10,
            'high_end_process': 'mirroring',
        }
        nn_arch_sizes = [
            31191, # default
            33966, 123821, 123812, 537238 # custom
        ]
        self.nn_architecture = list('{}KB'.format(s) for s in nn_arch_sizes)
        # model_path = '/home/nr/uvr5/models/Main_Models/5_HP-Karaoke-UVR.pth'
        # model_path = '/home/nr/uvr5/models/Main_Models/4_HP-Vocal-UVR.pth'
        #### 保留 people 
        model_size = math.ceil(os.stat(model_path ).st_size / 1024)
        nn_architecture = '{}KB'.format(min(nn_arch_sizes, key=lambda x:abs(x-model_size)))
        nets = importlib.import_module('lib_v5.nets' + f'_{nn_architecture}'.replace('_{}KB'.format(nn_arch_sizes[0]), ''), package=None)
        model_hash = hashlib.md5(open(model_path,'rb').read()).hexdigest()
        print(model_hash)
        ########   gggg 
        param_name ,model_params_d = _get_name_params(model_path , model_hash)
        mp = ModelParameters(model_params_d)
        model = nets.CascadedASPPNet(mp.param['bins'] * 2)
        cpk = torch.load( model_path , map_location='cpu')  
        model.load_state_dict(cpk)
        model.eval()
        model = model.to(device)

        self.mp = mp
        self.model = model
        # self. = 
    def _path_audio_(self, music_file ,save_path):
        '''
        music_file  path
        save_path save_path
        '''
        os.makedirs(save_path , exist_ok=True)
        X_wave, y_wave, X_spec_s, y_spec_s = {}, {}, {}, {}
        bands_n = len(self.mp.param['band'])
        for d in range(bands_n, 0, -1): 
            bp = self.mp.param['band'][d]
            if d == bands_n: # high-end band
                X_wave[d], _ = librosa.core.load(
                    music_file, bp['sr'], False, dtype=np.float32, res_type=bp['res_type'])
                if X_wave[d].ndim == 1:
                    X_wave[d] = np.asfortranarray([X_wave[d], X_wave[d]])
            else: # lower bands
                X_wave[d] = librosa.core.resample(X_wave[d+1], self.mp.param['band'][d+1]['sr'], bp['sr'], res_type=bp['res_type'])
            # Stft of wave source
            X_spec_s[d] = spec_utils.wave_to_spectrogram_mt(X_wave[d], bp['hl'], bp['n_fft'], 
                                                                                                                    self.mp.param['mid_side'], 
                                                                                                                self.mp.param['mid_side_b2'], 
                                                                                                                self.mp.param['reverse'])

            if d == bands_n and self.data['high_end_process'] != 'none':
                input_high_end_h = (bp['n_fft']//2 - bp['crop_stop']) + ( self.mp.param['pre_filter_stop'] - self.mp.param['pre_filter_start'])
                input_high_end = X_spec_s[d][:, bp['n_fft']//2-input_high_end_h:bp['n_fft']//2, :]

        X_spec_m = spec_utils.combine_spectrograms(X_spec_s, self.mp)
        aggresive_set = float(self.data['agg']/100)
        aggressiveness = {'value': aggresive_set, 
                        'split_bin': self.mp.param['band'][1]['crop_stop']}
        with torch.no_grad():
            pred, X_mag, X_phase = inference(X_spec_m,
                    self.device,
                    self.model, aggressiveness,self.data)
        # Postprocess
        if self.data['postprocess']:
            pred_inv = np.clip(X_mag - pred, 0, np.inf)
            pred = spec_utils.mask_silence(pred, pred_inv)
        y_spec_m = pred * X_phase
        v_spec_m = X_spec_m - y_spec_m

        if self.data['high_end_process'].startswith('mirroring'):        
            input_high_end_ = spec_utils.mirroring(self.data['high_end_process'], 
                                                                                                y_spec_m, input_high_end, self.mp)
            wav_instrument = spec_utils.cmb_spectrogram_to_wave(y_spec_m, self.mp,
                                                                                                 input_high_end_h, input_high_end_)    
        else:
            wav_instrument = spec_utils.cmb_spectrogram_to_wave(y_spec_m, self.mp)
        print ('wav_instrument is ok')                     
        if self.data['high_end_process'].startswith('mirroring'):        
            input_high_end_ = spec_utils.mirroring(self.data['high_end_process'], 
                                                                                                v_spec_m, input_high_end, self.mp)
            wav_vocals = spec_utils.cmb_spectrogram_to_wave(v_spec_m, self.mp,
                                                                                                 input_high_end_h, input_high_end_)    
        else:        
            wav_vocals = spec_utils.cmb_spectrogram_to_wave(v_spec_m, self.mp)
        print ('wav_vocals is ok')                     
        in_path = os.path.join(save_path , 'wav_instrument.wav')
        vo_path = os.path.join(save_path , 'wav_vocal.wav')

        # 写入乐器声音
        sf.write(in_path, wav_instrument[:, 0], self.mp.param['sr'])

        # 写入人声音
        sf.write(vo_path, wav_vocals[:, 0], self.mp.param['sr'])
        print ('{} is ok '.format(music_file) )

        return wav_instrument , wav_vocals


def vocal_separation(audio_path,save_path,model_path='./models/Main_Models/2_HP-UVR.pth'):
    device = 'cuda'
    pre_fun = _audio_pre_(
        device=device,
        model_path=model_path,
    )
    in_data, vo_data = pre_fun._path_audio_(audio_path, save_path)

if __name__ == '__main__':
    device = 'cuda'
    pre_fun = _audio_pre_(
        device=device,
        model_path = './models/Main_Models/2_HP-UVR.pth',
                        )
    audio_path = './dengziqi/句号.m4a'
    save_path = './dengziqi/pre_datas'
    in_data , vo_data = pre_fun._path_audio_(audio_path , save_path)
    # # 创建解析器对象
    # parser = argparse.ArgumentParser(description='Process audio separation parameters')
    #
    # # 添加命令行参数
    # parser.add_argument('-ap', '--audio_path', type=str, help='Path to the audio file')
    # parser.add_argument('-sp', '--save_path', type=str, help='Path to save the separated audio file')
    # parser.add_argument('-mp', '--model_path', type=str, default='./models/Main_Models/2_HP-UVR.pth',
    #                     help='Path to the model file')
    #
    # # 解析命令行参数
    # args = parser.parse_args()
    #
    # # 获取解析后的参数值
    # audio_path = args.audio_path
    # save_path = args.save_path
    # model_path = args.model_path
    # vocal_separation(audio_path,save_path,model_path)





















