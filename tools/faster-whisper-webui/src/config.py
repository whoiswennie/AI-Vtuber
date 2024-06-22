from enum import Enum
import urllib

import os
from typing import List
from urllib.parse import urlparse
import json5
import torch

from tqdm import tqdm

class ModelConfig:
    def __init__(self, name: str, url: str, path: str = None, type: str = "whisper"):
        """
        Initialize a model configuration.

        name: Name of the model
        url: URL to download the model from
        path: Path to the model file. If not set, the model will be downloaded from the URL.
        type: Type of model. Can be whisper or huggingface.
        """
        self.name = name
        self.url = url
        self.path = path
        self.type = type

class VadInitialPromptMode(Enum):
    PREPEND_ALL_SEGMENTS = 1
    PREPREND_FIRST_SEGMENT = 2

    @staticmethod
    def from_string(s: str):
        normalized = s.lower() if s is not None else None

        if normalized == "prepend_all_segments":
            return VadInitialPromptMode.PREPEND_ALL_SEGMENTS
        elif normalized == "prepend_first_segment":
            return VadInitialPromptMode.PREPREND_FIRST_SEGMENT
        else:
            raise ValueError(f"Invalid value for VadInitialPromptMode: {s}")

class ApplicationConfig:
    def __init__(self, models: List[ModelConfig] = [], input_audio_max_duration: int = 600, 
                 share: bool = False, server_name: str = None, server_port: int = 7860, 
                 queue_concurrency_count: int = 1, delete_uploaded_files: bool = True,
                 whisper_implementation: str = "whisper",
                 default_model_name: str = "medium", default_vad: str = "silero-vad", 
                 vad_parallel_devices: str = "", vad_cpu_cores: int = 1, vad_process_timeout: int = 1800, 
                 auto_parallel: bool = False, output_dir: str = None,
                 model_dir: str = None, device: str = None, 
                 verbose: bool = True, task: str = "transcribe", language: str = None,
                 vad_initial_prompt_mode: str = "prepend_first_segment ", 
                 vad_merge_window: float = 5, vad_max_merge_size: float = 30,
                 vad_padding: float = 1, vad_prompt_window: float = 3,
                 temperature: float = 0, best_of: int = 5, beam_size: int = 5,
                 patience: float = None, length_penalty: float = None,
                 suppress_tokens: str = "-1", initial_prompt: str = None,
                 condition_on_previous_text: bool = True, fp16: bool = True,
                 compute_type: str = "float16", 
                 temperature_increment_on_fallback: float = 0.2, compression_ratio_threshold: float = 2.4,
                 logprob_threshold: float = -1.0, no_speech_threshold: float = 0.6):
        
        self.models = models
        
        # WebUI settings
        self.input_audio_max_duration = input_audio_max_duration
        self.share = share
        self.server_name = server_name
        self.server_port = server_port
        self.queue_concurrency_count = queue_concurrency_count
        self.delete_uploaded_files = delete_uploaded_files

        self.whisper_implementation = whisper_implementation
        self.default_model_name = default_model_name
        self.default_vad = default_vad
        self.vad_parallel_devices = vad_parallel_devices
        self.vad_cpu_cores = vad_cpu_cores
        self.vad_process_timeout = vad_process_timeout
        self.auto_parallel = auto_parallel
        self.output_dir = output_dir

        self.model_dir = model_dir
        self.device = device
        self.verbose = verbose
        self.task = task
        self.language = language
        self.vad_initial_prompt_mode = vad_initial_prompt_mode
        self.vad_merge_window = vad_merge_window
        self.vad_max_merge_size = vad_max_merge_size
        self.vad_padding = vad_padding
        self.vad_prompt_window = vad_prompt_window
        self.temperature = temperature
        self.best_of = best_of
        self.beam_size = beam_size
        self.patience = patience
        self.length_penalty = length_penalty
        self.suppress_tokens = suppress_tokens
        self.initial_prompt = initial_prompt
        self.condition_on_previous_text = condition_on_previous_text
        self.fp16 = fp16
        self.compute_type = compute_type
        self.temperature_increment_on_fallback = temperature_increment_on_fallback
        self.compression_ratio_threshold = compression_ratio_threshold
        self.logprob_threshold = logprob_threshold
        self.no_speech_threshold = no_speech_threshold
        
    def get_model_names(self):
        return [ x.name for x in self.models ]

    def update(self, **new_values):
        result = ApplicationConfig(**self.__dict__)

        for key, value in new_values.items():
            setattr(result, key, value)
        return result

    @staticmethod
    def create_default(**kwargs):
        app_config = ApplicationConfig.parse_file(os.environ.get("WHISPER_WEBUI_CONFIG", "config.json5"))

        # Update with kwargs
        if len(kwargs) > 0:
            app_config = app_config.update(**kwargs)
        return app_config

    @staticmethod
    def parse_file(config_path: str):
        import json5

        with open(config_path, "r") as f:
            # Load using json5
            data = json5.load(f)
            data_models = data.pop("models", [])

            models = [ ModelConfig(**x) for x in data_models ]

            return ApplicationConfig(models, **data)
