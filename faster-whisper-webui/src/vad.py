from abc import ABC, abstractmethod
from collections import Counter, deque
import time

from typing import Any, Deque, Iterator, List, Dict

from pprint import pprint
from src.hooks.progressListener import ProgressListener
from src.hooks.subTaskProgressListener import SubTaskProgressListener
from src.hooks.whisperProgressHook import create_progress_listener_handle
from src.modelCache import GLOBAL_MODEL_CACHE, ModelCache

from src.segments import merge_timestamps
from src.whisper.abstractWhisperContainer import AbstractWhisperCallback

# Workaround for https://github.com/tensorflow/tensorflow/issues/48797
try:
    import tensorflow as tf
except ModuleNotFoundError:
    # Error handling
    pass

import torch

import ffmpeg
import numpy as np

from src.utils import format_timestamp
from enum import Enum

class NonSpeechStrategy(Enum):
    """
    Ignore non-speech frames segments.
    """
    SKIP = 1
    """
    Just treat non-speech segments as speech.
    """
    CREATE_SEGMENT = 2
    """
    Expand speech segments into subsequent non-speech segments.
    """
    EXPAND_SEGMENT = 3

# Defaults for Silero
SPEECH_TRESHOLD = 0.3

# Minimum size of segments to process
MIN_SEGMENT_DURATION = 1

# The maximum time for texts from old segments to be used in the next segment 
MAX_PROMPT_WINDOW = 0 # seconds (0 = disabled)
PROMPT_NO_SPEECH_PROB = 0.1 # Do not pass the text from segments with a no speech probability higher than this

VAD_MAX_PROCESSING_CHUNK = 60 * 60 # 60 minutes of audio

class TranscriptionConfig(ABC):
    def __init__(self, non_speech_strategy: NonSpeechStrategy = NonSpeechStrategy.SKIP, 
                       segment_padding_left: float = None, segment_padding_right = None, max_silent_period: float = None, 
                       max_merge_size: float = None, max_prompt_window: float = None, initial_segment_index = -1):
        self.non_speech_strategy = non_speech_strategy
        self.segment_padding_left = segment_padding_left
        self.segment_padding_right = segment_padding_right
        self.max_silent_period = max_silent_period
        self.max_merge_size = max_merge_size
        self.max_prompt_window = max_prompt_window
        self.initial_segment_index = initial_segment_index

class PeriodicTranscriptionConfig(TranscriptionConfig):
    def __init__(self, periodic_duration: float, non_speech_strategy: NonSpeechStrategy = NonSpeechStrategy.SKIP, 
                       segment_padding_left: float = None, segment_padding_right = None, max_silent_period: float = None, 
                       max_merge_size: float = None, max_prompt_window: float = None, initial_segment_index = -1):
        super().__init__(non_speech_strategy, segment_padding_left, segment_padding_right, max_silent_period, max_merge_size, max_prompt_window, initial_segment_index)
        self.periodic_duration = periodic_duration

class AbstractTranscription(ABC):
    def __init__(self, sampling_rate: int = 16000):
        self.sampling_rate = sampling_rate

    def get_audio_segment(self, str, start_time: str = None, duration: str = None):
        return load_audio(str, self.sampling_rate, start_time, duration)

    def is_transcribe_timestamps_fast(self):
        """
        Determine if get_transcribe_timestamps is fast enough to not need parallelization.
        """
        return False

    @abstractmethod
    def get_transcribe_timestamps(self, audio: str, config: TranscriptionConfig, start_time: float, end_time: float):
        """
        Get the start and end timestamps of the sections that should be transcribed by this VAD method.

        Parameters
        ----------
        audio: str
            The audio file.
        config: TranscriptionConfig
            The transcription configuration.

        Returns
        -------
        A list of start and end timestamps, in fractional seconds.
        """
        return 

    def get_merged_timestamps(self, timestamps: List[Dict[str, Any]], config: TranscriptionConfig, total_duration: float):
        """
        Get the start and end timestamps of the sections that should be transcribed by this VAD method,
        after merging the given segments using the specified configuration.

        Parameters
        ----------
        audio: str
            The audio file. 
        config: TranscriptionConfig
            The transcription configuration.

        Returns
        -------
        A list of start and end timestamps, in fractional seconds.
        """
        merged = merge_timestamps(timestamps, config.max_silent_period, config.max_merge_size, 
                                  config.segment_padding_left, config.segment_padding_right)

        if config.non_speech_strategy != NonSpeechStrategy.SKIP:
            # Expand segments to include the gaps between them
            if (config.non_speech_strategy == NonSpeechStrategy.CREATE_SEGMENT):
                # When we have a prompt window, we create speech segments betwen each segment if we exceed the merge size
                merged = self.fill_gaps(merged, total_duration=total_duration, max_expand_size=config.max_merge_size)
            elif config.non_speech_strategy == NonSpeechStrategy.EXPAND_SEGMENT: 
                # With no prompt window, it is better to just expand the segments (this effectively passes the prompt to the next segment)
                merged = self.expand_gaps(merged, total_duration=total_duration)
            else:
                raise Exception("Unknown non-speech strategy: " + str(config.non_speech_strategy))

            print("Transcribing non-speech:")
            pprint(merged)
        return merged

    def transcribe(self, audio: str, whisperCallable: AbstractWhisperCallback, config: TranscriptionConfig, 
                   progressListener: ProgressListener = None):
        """
        Transcribe the given audo file.

        Parameters
        ----------
        audio: str
            The audio file.
        whisperCallable: WhisperCallback
            A callback object to call to transcribe each segment.

        Returns
        -------
        A list of start and end timestamps, in fractional seconds.
        """

        try:
            max_audio_duration = self.get_audio_duration(audio, config)
            timestamp_segments = self.get_transcribe_timestamps(audio, config, 0, max_audio_duration)

            # Get speech timestamps from full audio file
            merged = self.get_merged_timestamps(timestamp_segments, config, max_audio_duration)

            # A deque of transcribed segments that is passed to the next segment as a prompt
            prompt_window = deque()

            print("Processing timestamps:")
            pprint(merged)

            result = {
                'text': "",
                'segments': [],
                'language': ""
            }
            languageCounter = Counter()
            detected_language = None

            segment_index = config.initial_segment_index

            # Calculate progress 
            progress_start_offset = merged[0]['start'] if len(merged) > 0 else 0
            progress_total_duration = sum([segment['end'] - segment['start'] for segment in merged])

            # For each time segment, run whisper
            for segment in merged:
                segment_index += 1
                segment_start = segment['start']
                segment_end = segment['end']
                segment_expand_amount = segment.get('expand_amount', 0)
                segment_gap = segment.get('gap', False)

                segment_duration = segment_end - segment_start

                if segment_duration < MIN_SEGMENT_DURATION:
                    continue

                # Audio to run on Whisper
                segment_audio = self.get_audio_segment(audio, start_time = str(segment_start), duration = str(segment_duration))
                # Previous segments to use as a prompt
                segment_prompt = ' '.join([segment['text'] for segment in prompt_window]) if len(prompt_window) > 0 else None
        
                # Detected language
                detected_language = languageCounter.most_common(1)[0][0] if len(languageCounter) > 0 else None

                print("Running whisper from ", format_timestamp(segment_start), " to ", format_timestamp(segment_end), ", duration: ", 
                    segment_duration, "expanded: ", segment_expand_amount, "prompt: ", segment_prompt, "language: ", detected_language)

                perf_start_time = time.perf_counter()

                scaled_progress_listener = SubTaskProgressListener(progressListener, base_task_total=progress_total_duration, 
                                                                   sub_task_start=segment_start - progress_start_offset, sub_task_total=segment_duration) 
                segment_result = whisperCallable.invoke(segment_audio, segment_index, segment_prompt, detected_language, progress_listener=scaled_progress_listener)

                perf_end_time = time.perf_counter()
                print("Whisper took {} seconds".format(perf_end_time - perf_start_time))

                adjusted_segments = self.adjust_timestamp(segment_result["segments"], adjust_seconds=segment_start, max_source_time=segment_duration)

                # Propagate expand amount to the segments
                if (segment_expand_amount > 0):
                    segment_without_expansion = segment_duration - segment_expand_amount

                    for adjusted_segment in adjusted_segments:
                        adjusted_segment_end = adjusted_segment['end']

                        # Add expand amount if the segment got expanded
                        if (adjusted_segment_end > segment_without_expansion):
                            adjusted_segment["expand_amount"] = adjusted_segment_end - segment_without_expansion

                # Append to output
                result['text'] += segment_result['text']
                result['segments'].extend(adjusted_segments)

                # Increment detected language
                if not segment_gap:
                    languageCounter[segment_result['language']] += 1

                # Update prompt window
                self.__update_prompt_window(prompt_window, adjusted_segments, segment_end, segment_gap, config)
                
            if detected_language is not None:
                result['language'] = detected_language
        finally:
            # Notify progress listener that we are done
            if progressListener is not None:
                progressListener.on_finished()
        return result
    
    def get_audio_duration(self, audio: str, config: TranscriptionConfig):
        return get_audio_duration(audio)

    def __update_prompt_window(self, prompt_window: Deque, adjusted_segments: List, segment_end: float, segment_gap: bool, config: TranscriptionConfig):
        if (config.max_prompt_window is not None and config.max_prompt_window > 0):
            # Add segments to the current prompt window (unless it is a speech gap)
            if not segment_gap:
                for segment in adjusted_segments:
                    if segment.get('no_speech_prob', 0) <= PROMPT_NO_SPEECH_PROB:
                        prompt_window.append(segment)

            while (len(prompt_window) > 0):
                first_end_time = prompt_window[0].get('end', 0)
                # Time expanded in the segments should be discounted from the prompt window
                first_expand_time = prompt_window[0].get('expand_amount', 0)

                if (first_end_time - first_expand_time < segment_end - config.max_prompt_window):
                    prompt_window.popleft()
                else:
                    break

    def include_gaps(self, segments: Iterator[dict], min_gap_length: float, total_duration: float):
        result = []
        last_end_time = 0

        for segment in segments:
            segment_start = float(segment['start'])
            segment_end = float(segment['end'])

            if (last_end_time != segment_start):
                delta = segment_start - last_end_time

                if (min_gap_length is None or delta >= min_gap_length):
                    result.append( { 'start': last_end_time, 'end': segment_start, 'gap': True } )
            
            last_end_time = segment_end
            result.append(segment)

        # Also include total duration if specified
        if (total_duration is not None and last_end_time < total_duration):
            delta = total_duration - segment_start

            if (min_gap_length is None or delta >= min_gap_length):
                result.append( { 'start': last_end_time, 'end': total_duration, 'gap': True } )

        return result

    # Expand the end time of each segment to the start of the next segment
    def expand_gaps(self, segments: List[Dict[str, Any]], total_duration: float):
        result = []

        if len(segments) == 0:
            return result

        # Add gap at the beginning if needed
        if (segments[0]['start'] > 0):
            result.append({ 'start': 0, 'end': segments[0]['start'], 'gap': True } )

        for i in range(len(segments) - 1):
            current_segment = segments[i]
            next_segment = segments[i + 1]

            delta = next_segment['start'] - current_segment['end']

            # Expand if the gap actually exists
            if (delta >= 0):
                current_segment = current_segment.copy()
                current_segment['expand_amount'] = delta
                current_segment['end'] = next_segment['start']
            
            result.append(current_segment)

        # Add last segment
        last_segment = segments[-1]
        result.append(last_segment)

        # Also include total duration if specified
        if (total_duration is not None):
            last_segment = result[-1]

            if (last_segment['end'] < total_duration):
                last_segment = last_segment.copy()
                last_segment['end'] = total_duration
                result[-1] = last_segment

        return result

    def fill_gaps(self, segments: List[Dict[str, Any]], total_duration: float, max_expand_size: float = None):
        result = []

        if len(segments) == 0:
            return result

        # Add gap at the beginning if needed
        if (segments[0]['start'] > 0):
            result.append({ 'start': 0, 'end': segments[0]['start'], 'gap': True } )

        for i in range(len(segments) - 1):
            expanded = False
            current_segment = segments[i]
            next_segment = segments[i + 1]

            delta = next_segment['start'] - current_segment['end']

            if (max_expand_size is not None and delta <= max_expand_size):
                # Just expand the current segment
                current_segment = current_segment.copy()
                current_segment['expand_amount'] = delta
                current_segment['end'] = next_segment['start']
                expanded = True

            result.append(current_segment)

            # Add a gap to the next segment if needed
            if (delta >= 0 and not expanded):
                result.append({ 'start': current_segment['end'], 'end': next_segment['start'], 'gap': True } )
            
        # Add last segment
        last_segment = segments[-1]
        result.append(last_segment)

        # Also include total duration if specified
        if (total_duration is not None):
            last_segment = result[-1]

            delta = total_duration - last_segment['end']

            if (delta > 0):
                if (max_expand_size is not None and delta <= max_expand_size):
                    # Expand the last segment
                    last_segment = last_segment.copy()
                    last_segment['expand_amount'] = delta
                    last_segment['end'] = total_duration
                    result[-1] = last_segment
                else:
                    result.append({ 'start': last_segment['end'], 'end': total_duration, 'gap': True } )

        return result

    def adjust_timestamp(self, segments: Iterator[dict], adjust_seconds: float, max_source_time: float = None):
        result = []

        for segment in segments:
            segment_start = float(segment['start'])
            segment_end = float(segment['end'])

            # Filter segments?
            if (max_source_time is not None):
                if (segment_start > max_source_time):
                    continue
                segment_end = min(max_source_time, segment_end)

                new_segment = segment.copy()

            # Add to start and end
            new_segment['start'] = segment_start + adjust_seconds
            new_segment['end'] = segment_end + adjust_seconds
            result.append(new_segment)
        return result

    def multiply_timestamps(self, timestamps: List[Dict[str, Any]], factor: float):
        result = []

        for entry in timestamps:
            start = entry['start']
            end = entry['end']

            result.append({
                'start': start * factor,
                'end': end * factor
            })
        return result


class VadSileroTranscription(AbstractTranscription):
    def __init__(self, sampling_rate: int = 16000, cache: ModelCache = None):
        super().__init__(sampling_rate=sampling_rate)
        self.model = None
        self.cache = cache
        self._initialize_model()

    def _initialize_model(self):
        if (self.cache is not None):
            model_key = "VadSileroTranscription"
            self.model, self.get_speech_timestamps = self.cache.get(model_key, self._create_model)
            print("Loaded Silerio model from cache.")
        else:
            self.model, self.get_speech_timestamps = self._create_model()
            print("Created Silerio model")

    def _create_model(self):
        
        # model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
        model, utils = torch.hub.load(repo_or_dir='models/silero-vad', model='silero_vad',source="local")
        
        # Silero does not benefit from multi-threading
        torch.set_num_threads(1) # JIT
        (get_speech_timestamps, _, _, _, _) = utils

        return model, get_speech_timestamps

    def get_transcribe_timestamps(self, audio: str, config: TranscriptionConfig, start_time: float, end_time: float):
        result = []

        print("Getting timestamps from audio file: {}, start: {}, duration: {}".format(audio, start_time, end_time))
        perf_start_time = time.perf_counter()

        # Divide procesisng of audio into chunks
        chunk_start = start_time

        while (chunk_start < end_time):
            chunk_duration = min(end_time - chunk_start, VAD_MAX_PROCESSING_CHUNK)

            print("Processing VAD in chunk from {} to {}".format(format_timestamp(chunk_start), format_timestamp(chunk_start + chunk_duration)))
            wav = self.get_audio_segment(audio, str(chunk_start), str(chunk_duration))

            sample_timestamps = self.get_speech_timestamps(wav, self.model, sampling_rate=self.sampling_rate, threshold=SPEECH_TRESHOLD)
            seconds_timestamps = self.multiply_timestamps(sample_timestamps, factor=1 / self.sampling_rate) 
            adjusted = self.adjust_timestamp(seconds_timestamps, adjust_seconds=chunk_start, max_source_time=chunk_start + chunk_duration)

            #pprint(adjusted)

            result.extend(adjusted)
            chunk_start += chunk_duration

        perf_end_time = time.perf_counter()
        print("VAD processing took {} seconds".format(perf_end_time - perf_start_time))

        return result

    def __getstate__(self):
        # We only need the sampling rate
        return { 'sampling_rate': self.sampling_rate }

    def __setstate__(self, state):
        self.sampling_rate = state['sampling_rate']
        self.model = None
        # Use the global cache
        self.cache = GLOBAL_MODEL_CACHE
        self._initialize_model()

# A very simple VAD that just marks every N seconds as speech
class VadPeriodicTranscription(AbstractTranscription):
    def __init__(self, sampling_rate: int = 16000):
        super().__init__(sampling_rate=sampling_rate)

    def is_transcribe_timestamps_fast(self):
        # This is a very fast VAD - no need to parallelize it
        return True

    def get_transcribe_timestamps(self, audio: str, config: PeriodicTranscriptionConfig, start_time: float, end_time: float):
        result = []

        # Generate a timestamp every N seconds
        start_timestamp = start_time

        while (start_timestamp < end_time):
            end_timestamp = min(start_timestamp + config.periodic_duration, end_time)
            segment_duration = end_timestamp - start_timestamp

            # Minimum duration is 1 second
            if (segment_duration >= 1):
                result.append( {  'start': start_timestamp, 'end': end_timestamp } )

            start_timestamp = end_timestamp

        return result

def get_audio_duration(file: str):
    return float(ffmpeg.probe(file)["format"]["duration"])

def load_audio(file: str, sample_rate: int = 16000, 
               start_time: str = None, duration: str = None):
    """
    Open an audio file and read as mono waveform, resampling as necessary

    Parameters
    ----------
    file: str
        The audio file to open

    sr: int
        The sample rate to resample the audio if necessary

    start_time: str
        The start time, using the standard FFMPEG time duration syntax, or None to disable.
    
    duration: str
        The duration, using the standard FFMPEG time duration syntax, or None to disable.

    Returns
    -------
    A NumPy array containing the audio waveform, in float32 dtype.
    """
    try:
        inputArgs = {'threads': 0}

        if (start_time is not None):
            inputArgs['ss'] = start_time
        if (duration is not None):
            inputArgs['t'] = duration

        # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
        # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
        out, _ = (
            ffmpeg.input(file, **inputArgs)
            .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sample_rate)
            .run(cmd="ffmpeg", capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}")

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0