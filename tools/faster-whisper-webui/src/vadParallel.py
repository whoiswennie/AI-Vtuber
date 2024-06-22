import multiprocessing
from queue import Empty
import threading
import time
from src.hooks.progressListener import ProgressListener
from src.vad import AbstractTranscription, TranscriptionConfig, get_audio_duration

from multiprocessing import Pool, Queue

from typing import Any, Dict, List, Union
import os

from src.whisper.abstractWhisperContainer import AbstractWhisperCallback

class _ProgressListenerToQueue(ProgressListener):
    def __init__(self, progress_queue: Queue):
        self.progress_queue = progress_queue
        self.progress_total = 0
        self.prev_progress = 0

    def on_progress(self, current: Union[int, float], total: Union[int, float]):
        delta = current - self.prev_progress
        self.prev_progress = current
        self.progress_total = total
        self.progress_queue.put(delta)

    def on_finished(self):
        if self.progress_total > self.prev_progress:
            delta = self.progress_total - self.prev_progress
            self.progress_queue.put(delta)
            self.prev_progress = self.progress_total

class ParallelContext:
    def __init__(self, num_processes: int = None, auto_cleanup_timeout_seconds: float = None):
        self.num_processes = num_processes
        self.auto_cleanup_timeout_seconds = auto_cleanup_timeout_seconds
        self.lock = threading.Lock()

        self.ref_count = 0
        self.pool = None
        self.cleanup_timer = None

    def get_pool(self):
        # Initialize pool lazily
        if (self.pool is None):
            context = multiprocessing.get_context('spawn')
            self.pool = context.Pool(self.num_processes)

        self.ref_count = self.ref_count + 1

        if (self.auto_cleanup_timeout_seconds is not None):
            self._stop_auto_cleanup()

        return self.pool

    def return_pool(self, pool):
        if (self.pool == pool and self.ref_count > 0):
            self.ref_count = self.ref_count - 1

            if (self.ref_count == 0):
                if (self.auto_cleanup_timeout_seconds is not None):
                    self._start_auto_cleanup()

    def _start_auto_cleanup(self):
        if (self.cleanup_timer is not None):
            self.cleanup_timer.cancel()
        self.cleanup_timer = threading.Timer(self.auto_cleanup_timeout_seconds, self._execute_cleanup)
        self.cleanup_timer.start()

        print("Started auto cleanup of pool in " + str(self.auto_cleanup_timeout_seconds) + " seconds")

    def _stop_auto_cleanup(self):
        if (self.cleanup_timer is not None):
            self.cleanup_timer.cancel()
            self.cleanup_timer = None

            print("Stopped auto cleanup of pool")

    def _execute_cleanup(self):
        print("Executing cleanup of pool")

        if (self.ref_count == 0):
            self.close()

    def close(self):
        self._stop_auto_cleanup()

        if (self.pool is not None):
            print("Closing pool of " + str(self.num_processes) + " processes")
            self.pool.close()
            self.pool.join()
        self.pool = None

class ParallelTranscriptionConfig(TranscriptionConfig):
    def __init__(self, device_id: str, override_timestamps, initial_segment_index, copy: TranscriptionConfig = None):
        super().__init__(copy.non_speech_strategy, copy.segment_padding_left, copy.segment_padding_right, copy.max_silent_period, copy.max_merge_size, copy.max_prompt_window, initial_segment_index)
        self.device_id = device_id
        self.override_timestamps = override_timestamps

class ParallelTranscription(AbstractTranscription):
    # Silero VAD typically takes about 3 seconds per minute, so there's no need to split the chunks 
    # into smaller segments than 2 minute (min 6 seconds per CPU core)
    MIN_CPU_CHUNK_SIZE_SECONDS = 2 * 60

    def __init__(self, sampling_rate: int = 16000):
        super().__init__(sampling_rate=sampling_rate)

    def transcribe_parallel(self, transcription: AbstractTranscription, audio: str, whisperCallable: AbstractWhisperCallback, config: TranscriptionConfig, 
                            cpu_device_count: int, gpu_devices: List[str], cpu_parallel_context: ParallelContext = None, gpu_parallel_context: ParallelContext = None, 
                            progress_listener: ProgressListener = None):
        total_duration = get_audio_duration(audio)

        # First, get the timestamps for the original audio
        if (cpu_device_count > 1 and not transcription.is_transcribe_timestamps_fast()):
            merged = self._get_merged_timestamps_parallel(transcription, audio, config, total_duration, cpu_device_count, cpu_parallel_context)
        else:
            timestamp_segments = transcription.get_transcribe_timestamps(audio, config, 0, total_duration)
            merged = transcription.get_merged_timestamps(timestamp_segments, config, total_duration)

        # We must make sure the whisper model is downloaded
        if (len(gpu_devices) > 1):
            whisperCallable.model_container.ensure_downloaded()

        # Split into a list for each device
        # TODO: Split by time instead of by number of chunks
        merged_split = list(self._split(merged, len(gpu_devices)))

        # Parameters that will be passed to the transcribe function
        parameters = []
        segment_index = config.initial_segment_index

        processing_manager = multiprocessing.Manager()
        progress_queue = processing_manager.Queue()

        for i in range(len(gpu_devices)):
            # Note that device_segment_list can be empty. But we will still create a process for it,
            # as otherwise we run the risk of assigning the same device to multiple processes.
            device_segment_list = list(merged_split[i]) if i < len(merged_split) else []
            device_id = gpu_devices[i]

            print("Device " + str(device_id) + " (index " + str(i) + ") has " + str(len(device_segment_list)) + " segments")

            # Create a new config with the given device ID
            device_config = ParallelTranscriptionConfig(device_id, device_segment_list, segment_index, config)
            segment_index += len(device_segment_list)

            progress_listener_to_queue = _ProgressListenerToQueue(progress_queue)
            parameters.append([audio, whisperCallable, device_config, progress_listener_to_queue]);

        merged = {
            'text': '',
            'segments': [],
            'language': None
        }

        created_context = False

        perf_start_gpu = time.perf_counter()

        # Spawn a separate process for each device
        try:
            if (gpu_parallel_context is None):
                gpu_parallel_context = ParallelContext(len(gpu_devices))
                created_context = True

            # Get a pool of processes
            pool = gpu_parallel_context.get_pool()

            # Run the transcription in parallel
            results_async = pool.starmap_async(self.transcribe, parameters)
            total_progress = 0

            while not results_async.ready():
                try:
                    delta = progress_queue.get(timeout=5)  # Set a timeout of 5 seconds
                except Empty:
                    continue
                
                total_progress += delta
                if progress_listener is not None:
                    progress_listener.on_progress(total_progress, total_duration)

            results = results_async.get()

            # Call the finished callback
            if progress_listener is not None:
                progress_listener.on_finished()

            for result in results:
                # Merge the results
                if (result['text'] is not None):
                    merged['text'] += result['text']
                if (result['segments'] is not None):
                    merged['segments'].extend(result['segments'])
                if (result['language'] is not None):
                    merged['language'] = result['language']

        finally:
            # Return the pool to the context
            if (gpu_parallel_context is not None):
                gpu_parallel_context.return_pool(pool)
            # Always close the context if we created it
            if (created_context):
                gpu_parallel_context.close()

        perf_end_gpu = time.perf_counter()
        print("Parallel transcription took " + str(perf_end_gpu - perf_start_gpu) + " seconds")

        return merged

    def _get_merged_timestamps_parallel(self, transcription: AbstractTranscription, audio: str, config: TranscriptionConfig, total_duration: float, 
                                       cpu_device_count: int, cpu_parallel_context: ParallelContext = None):
        parameters = []

        chunk_size = max(total_duration / cpu_device_count, self.MIN_CPU_CHUNK_SIZE_SECONDS)
        chunk_start = 0
        cpu_device_id = 0

        perf_start_time = time.perf_counter()

        # Create chunks that will be processed on the CPU
        while (chunk_start < total_duration):
            chunk_end = min(chunk_start + chunk_size, total_duration)

            if (chunk_end - chunk_start < 1):
                # No need to process chunks that are less than 1 second
                break

            print("Parallel VAD: Executing chunk from " + str(chunk_start) + " to " + 
                    str(chunk_end) + " on CPU device " + str(cpu_device_id))
            parameters.append([audio, config, chunk_start, chunk_end]);

            cpu_device_id += 1
            chunk_start = chunk_end

        created_context = False

        # Spawn a separate process for each device
        try:
            if (cpu_parallel_context is None):
                cpu_parallel_context = ParallelContext(cpu_device_count)
                created_context = True

            # Get a pool of processes
            pool = cpu_parallel_context.get_pool()

            # Run the transcription in parallel. Note that transcription must be picklable.
            results = pool.starmap(transcription.get_transcribe_timestamps, parameters)

            timestamps = []

            # Flatten the results
            for result in results:
                timestamps.extend(result)

            merged = transcription.get_merged_timestamps(timestamps, config, total_duration)

            perf_end_time = time.perf_counter()
            print("Parallel VAD processing took {} seconds".format(perf_end_time - perf_start_time))
            return merged

        finally:
            # Return the pool to the context
            if (cpu_parallel_context is not None):
                cpu_parallel_context.return_pool(pool)
            # Always close the context if we created it
            if (created_context):
                cpu_parallel_context.close()

    def get_transcribe_timestamps(self, audio: str, config: ParallelTranscriptionConfig, start_time: float, duration: float):
        return []

    def get_merged_timestamps(self,  timestamps: List[Dict[str, Any]], config: ParallelTranscriptionConfig, total_duration: float):
        # Override timestamps that will be processed
        if (config.override_timestamps is not None):
            print("(get_merged_timestamps) Using override timestamps of size " + str(len(config.override_timestamps)))
            return config.override_timestamps
        return super().get_merged_timestamps(timestamps, config, total_duration)

    def transcribe(self, audio: str, whisperCallable: AbstractWhisperCallback, config: ParallelTranscriptionConfig, 
                   progressListener: ProgressListener = None):
        # Override device ID the first time
        if (os.environ.get("INITIALIZED", None) is None):
            os.environ["INITIALIZED"] = "1"

            # Note that this may be None if the user didn't specify a device. In that case, Whisper will
            # just use the default GPU device.
            if (config.device_id is not None):
                print("Using device " + config.device_id)
                os.environ["CUDA_VISIBLE_DEVICES"] = config.device_id
        
        return super().transcribe(audio, whisperCallable, config, progressListener)

    def _split(self, a, n):
        """Split a list into n approximately equal parts."""
        k, m = divmod(len(a), n)
        return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

