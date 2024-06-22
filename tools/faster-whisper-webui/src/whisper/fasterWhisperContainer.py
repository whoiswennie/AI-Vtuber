import os
from typing import List, Union

from faster_whisper import WhisperModel, download_model
from src.config import ModelConfig, VadInitialPromptMode
from src.hooks.progressListener import ProgressListener
from src.languages import get_language_from_name
from src.modelCache import ModelCache
from src.whisper.abstractWhisperContainer import AbstractWhisperCallback, AbstractWhisperContainer
from src.utils import format_timestamp

class FasterWhisperContainer(AbstractWhisperContainer):
    def __init__(self, model_name: str, device: str = None, compute_type: str = "float16",
                       download_root: str = None,
                       cache: ModelCache = None, models: List[ModelConfig] = []):
        super().__init__(model_name, device, compute_type, download_root, cache, models)
    
    def ensure_downloaded(self):
        """
        Ensure that the model is downloaded. This is useful if you want to ensure that the model is downloaded before
        passing the container to a subprocess.
        """
        model_config = self._get_model_config()
        
        if os.path.isdir(model_config.url):
            model_config.path = model_config.url
        else:
            model_config.path = download_model(model_config.url, output_dir=self.download_root)

    def _get_model_config(self) -> ModelConfig:
        """
        Get the model configuration for the model.
        """
        for model in self.models:
            if model.name == self.model_name:
                return model
        return None

    def _create_model(self):
        print("Loading faster whisper model " + self.model_name + " for device " + str(self.device))
        model_config = self._get_model_config()
        
        if model_config.type == "whisper" and model_config.url not in ["tiny", "base", "small", "medium", "large", "large-v2"]:
            raise Exception("FasterWhisperContainer does not yet support Whisper models. Use ct2-transformers-converter to convert the model to a faster-whisper model.")

        device = self.device

        if (device is None):
            device = "auto"
        # model_path = FASTER_WHISPER_MODELS_PATH[model_config.url]
        model_path = os.path.join(os.path.join("models", "faster-whisper"),model_config.url)
        # model = WhisperModel(model_config.url, device=device, compute_type=self.compute_type)
        model = WhisperModel(model_size_or_path=model_path, device=device, compute_type=self.compute_type)
        return model

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
        return FasterWhisperCallback(self, language=language, task=task, initial_prompt=initial_prompt, initial_prompt_mode=initial_prompt_mode, **decodeOptions)

class FasterWhisperCallback(AbstractWhisperCallback):
    def __init__(self, model_container: FasterWhisperContainer, language: str = None, task: str = None, 
                 initial_prompt: str = None, initial_prompt_mode: VadInitialPromptMode=VadInitialPromptMode.PREPREND_FIRST_SEGMENT, 
                 **decodeOptions: dict):
        self.model_container = model_container
        self.language = language
        self.task = task
        self.initial_prompt = initial_prompt
        self.initial_prompt_mode = initial_prompt_mode
        self.decodeOptions = decodeOptions

        self._printed_warning = False
        
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
        model: WhisperModel = self.model_container.get_model()
        language_code = self._lookup_language_code(self.language) if self.language else None

        # Copy decode options and remove options that are not supported by faster-whisper
        decodeOptions = self.decodeOptions.copy()
        verbose = decodeOptions.pop("verbose", None)

        logprob_threshold = decodeOptions.pop("logprob_threshold", None)

        patience = decodeOptions.pop("patience", None)
        length_penalty = decodeOptions.pop("length_penalty", None)
        suppress_tokens = decodeOptions.pop("suppress_tokens", None)

        if (decodeOptions.pop("fp16", None) is not None):
            if not self._printed_warning:
                print("WARNING: fp16 option is ignored by faster-whisper - use compute_type instead.")
            self._printed_warning = True

        # Fix up decode options
        if (logprob_threshold is not None):
            decodeOptions["log_prob_threshold"] = logprob_threshold

        decodeOptions["patience"] = float(patience) if patience is not None else 1.0
        decodeOptions["length_penalty"] = float(length_penalty) if length_penalty is not None else 1.0

        # See if supress_tokens is a string - if so, convert it to a list of ints
        decodeOptions["suppress_tokens"] = self._split_suppress_tokens(suppress_tokens)

        initial_prompt = self._get_initial_prompt(self.initial_prompt, self.initial_prompt_mode, prompt, segment_index)

        segments_generator, info = model.transcribe(audio, \
            language=language_code if language_code else detected_language, task=self.task, \
            initial_prompt=initial_prompt, \
            **decodeOptions
        )

        segments = []

        for segment in segments_generator:
            segments.append(segment)

            if progress_listener is not None:
                progress_listener.on_progress(segment.end, info.duration)
            if verbose:
                print("[{}->{}] {}".format(format_timestamp(segment.start, True), format_timestamp(segment.end, True),
                                          segment.text))

        text = " ".join([segment.text for segment in segments])

        # Convert the segments to a format that is easier to serialize
        whisper_segments = [{
            "text": segment.text,
            "start": segment.start,
            "end": segment.end,

            # Extra fields added by faster-whisper
            "words": [{
                "start": word.start,
                "end": word.end,
                "word": word.word,
                "probability": word.probability
            } for word in (segment.words if segment.words is not None else []) ]
        } for segment in segments]

        result = {
            "segments": whisper_segments,
            "text": text,
            "language": info.language if info else None,

            # Extra fields added by faster-whisper
            "language_probability": info.language_probability if info else None,
            "duration": info.duration if info else None
        }

        if progress_listener is not None:
            progress_listener.on_finished()
        return result

    def _split_suppress_tokens(self, suppress_tokens: Union[str, List[int]]):
        if (suppress_tokens is None):
            return None
        if (isinstance(suppress_tokens, list)):
            return suppress_tokens

        return [int(token) for token in suppress_tokens.split(",")]

    def _lookup_language_code(self, language: str):
        language = get_language_from_name(language)

        if language is None:
            raise ValueError("Invalid language: " + language)
        
        return language.code
