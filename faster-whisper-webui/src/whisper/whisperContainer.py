# External programs
import abc
import os
import sys
from typing import List
from urllib.parse import urlparse
import torch
import urllib3
from src.hooks.progressListener import ProgressListener

import whisper
from whisper import Whisper

from src.config import ModelConfig, VadInitialPromptMode
from src.hooks.whisperProgressHook import create_progress_listener_handle

from src.modelCache import GLOBAL_MODEL_CACHE, ModelCache
from src.utils import download_file
from src.whisper.abstractWhisperContainer import AbstractWhisperCallback, AbstractWhisperContainer

class WhisperContainer(AbstractWhisperContainer):
    def __init__(self, model_name: str, device: str = None, compute_type: str = "float16",
                 download_root: str = None,
                 cache: ModelCache = None, models: List[ModelConfig] = []):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        super().__init__(model_name, device, compute_type, download_root, cache, models)
    
    def ensure_downloaded(self):
        """
        Ensure that the model is downloaded. This is useful if you want to ensure that the model is downloaded before
        passing the container to a subprocess.
        """
        # Warning: Using private API here
        try:
            root_dir = self.download_root
            model_config = self._get_model_config()

            if root_dir is None:
                root_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")

            if self.model_name in whisper._MODELS:
                whisper._download(whisper._MODELS[self.model_name], root_dir, False)
            else:
                # If the model is not in the official list, see if it needs to be downloaded
                model_config.download_url(root_dir)
            return True
        
        except Exception as e:
            # Given that the API is private, it could change at any time. We don't want to crash the program
            print("Error pre-downloading model: " + str(e))
            return False

    def _get_model_config(self) -> ModelConfig:
        """
        Get the model configuration for the model.
        """
        for model in self.models:
            if model.name == self.model_name:
                return model
        return None

    def _create_model(self):
        print("Loading whisper model " + self.model_name)
        model_config = self._get_model_config()

        # Note that the model will not be downloaded in the case of an official Whisper model
        model_path = self._get_model_path(model_config, self.download_root)

        return whisper.load_model(model_path, device=self.device, download_root=self.download_root)

    def create_callback(self, language: str = None, task: str = None, initial_prompt: str = None, 
                        initial_prompt_mode: VadInitialPromptMode = VadInitialPromptMode.PREPREND_FIRST_SEGMENT, 
                        **decodeOptions: dict) -> AbstractWhisperCallback:
        """
        Create a WhisperCallback object that can be used to transcript audio files.

        Parameters
        ----------
        language: str
            The target language of the transcription. If not specified, the language will be inferred from the audio content.
        task: str
            The task - either translate or transcribe.
        initial_prompt: str
            The initial prompt to use for the transcription.
        initial_prompt_mode: VadInitialPromptMode
            The mode to use for the initial prompt. If set to PREPEND_FIRST_SEGMENT, the initial prompt will be prepended to the first segment of audio.
            If set to PREPEND_ALL_SEGMENTS, the initial prompt will be prepended to all segments of audio.
        decodeOptions: dict
            Additional options to pass to the decoder. Must be pickleable.

        Returns
        -------
        A WhisperCallback object.
        """
        return WhisperCallback(self, language=language, task=task, initial_prompt=initial_prompt, initial_prompt_mode=initial_prompt_mode, **decodeOptions)

    def _get_model_path(self, model_config: ModelConfig, root_dir: str = None):
        from src.conversion.hf_converter import convert_hf_whisper
        """
        Download the model.

        Parameters
        ----------
        model_config: ModelConfig
            The model configuration.
        """
        # See if path is already set
        if model_config.path is not None:
            return model_config.path
        
        if root_dir is None:
            root_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")

        model_type = model_config.type.lower() if model_config.type is not None else "whisper"

        if model_type in ["huggingface", "hf"]:
            model_config.path = model_config.url
            destination_target = os.path.join(root_dir, model_config.name + ".pt")

            # Convert from HuggingFace format to Whisper format
            if os.path.exists(destination_target):
                print(f"File {destination_target} already exists, skipping conversion")
            else:
                print("Saving HuggingFace model in Whisper format to " + destination_target)
                convert_hf_whisper(model_config.url, destination_target)

            model_config.path = destination_target

        elif model_type in ["whisper", "w"]:
            model_config.path = model_config.url

            # See if URL is just a file
            if model_config.url in whisper._MODELS:
                # No need to download anything - Whisper will handle it
                model_config.path = model_config.url
            elif model_config.url.startswith("file://"):
                # Get file path
                model_config.path = urlparse(model_config.url).path
            # See if it is an URL
            elif model_config.url.startswith("http://") or model_config.url.startswith("https://"):
                # Extension (or file name)
                extension = os.path.splitext(model_config.url)[-1]
                download_target = os.path.join(root_dir, model_config.name + extension)

                if os.path.exists(download_target) and not os.path.isfile(download_target):
                    raise RuntimeError(f"{download_target} exists and is not a regular file")

                if not os.path.isfile(download_target):
                    download_file(model_config.url, download_target)
                else:
                    print(f"File {download_target} already exists, skipping download")

                model_config.path = download_target
            # Must be a local file
            else:
                model_config.path = model_config.url

        else:
            raise ValueError(f"Unknown model type {model_type}")

        return model_config.path

class WhisperCallback(AbstractWhisperCallback):
    def __init__(self, model_container: WhisperContainer, language: str = None, task: str = None, initial_prompt: str = None, 
                 initial_prompt_mode: VadInitialPromptMode=VadInitialPromptMode.PREPREND_FIRST_SEGMENT, **decodeOptions: dict):
        self.model_container = model_container
        self.language = language
        self.task = task
        self.initial_prompt = initial_prompt
        self.initial_prompt_mode = initial_prompt_mode
        self.decodeOptions = decodeOptions
        
    def invoke(self, audio, segment_index: int, prompt: str, detected_language: str, progress_listener: ProgressListener = None):
        """
        Peform the transcription of the given audio file or data.

        Parameters
        ----------
        audio: Union[str, np.ndarray, torch.Tensor]
            The audio file to transcribe, or the audio data as a numpy array or torch tensor.
        segment_index: int
            The target language of the transcription. If not specified, the language will be inferred from the audio content.
        task: str
            The task - either translate or transcribe.
        progress_listener: ProgressListener
            A callback to receive progress updates.
        """
        model = self.model_container.get_model()

        if progress_listener is not None:
            with create_progress_listener_handle(progress_listener):
                return self._transcribe(model, audio, segment_index, prompt, detected_language)
        else:
            return self._transcribe(model, audio, segment_index, prompt, detected_language)
    
    def _transcribe(self, model: Whisper, audio, segment_index: int, prompt: str, detected_language: str):
        decodeOptions = self.decodeOptions.copy()

        # Add fp16
        if self.model_container.compute_type in ["fp16", "float16"]:
            decodeOptions["fp16"] = True

        initial_prompt = self._get_initial_prompt(self.initial_prompt, self.initial_prompt_mode, prompt, segment_index)

        return model.transcribe(audio, \
            language=self.language if self.language else detected_language, task=self.task, \
            initial_prompt=initial_prompt, \
            **decodeOptions
        )