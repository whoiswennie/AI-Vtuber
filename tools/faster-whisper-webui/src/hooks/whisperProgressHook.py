import sys
import threading
from typing import List, Union
import tqdm

from src.hooks.progressListener import ProgressListener

class ProgressListenerHandle:
    def __init__(self, listener: ProgressListener):
        self.listener = listener
    
    def __enter__(self):
        register_thread_local_progress_listener(self.listener)

    def __exit__(self, exc_type, exc_val, exc_tb):
        unregister_thread_local_progress_listener(self.listener)
        
        if exc_type is None:
            self.listener.on_finished()

class _CustomProgressBar(tqdm.tqdm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current = self.n  # Set the initial value

    def update(self, n):
        super().update(n)
        # Because the progress bar might be disabled, we need to manually update the progress
        self._current += n

        # Inform listeners
        listeners = _get_thread_local_listeners()

        for listener in listeners:
            listener.on_progress(self._current, self.total)

_thread_local = threading.local()

def _get_thread_local_listeners():
    if not hasattr(_thread_local, 'listeners'):
        _thread_local.listeners = []
    return _thread_local.listeners

_hooked = False

def init_progress_hook():
    global _hooked

    if _hooked:
        return

    # Inject into tqdm.tqdm of Whisper, so we can see progress
    import whisper.transcribe 
    transcribe_module = sys.modules['whisper.transcribe']
    transcribe_module.tqdm.tqdm = _CustomProgressBar
    _hooked = True

def register_thread_local_progress_listener(progress_listener: ProgressListener):
    # This is a workaround for the fact that the progress bar is not exposed in the API
    init_progress_hook()

    listeners = _get_thread_local_listeners()
    listeners.append(progress_listener)

def unregister_thread_local_progress_listener(progress_listener: ProgressListener):
    listeners = _get_thread_local_listeners()
    
    if progress_listener in listeners:
        listeners.remove(progress_listener)

def create_progress_listener_handle(progress_listener: ProgressListener):
    return ProgressListenerHandle(progress_listener)

# Example usage
if __name__ == '__main__':
    class PrintingProgressListener:
        def on_progress(self, current: Union[int, float], total: Union[int, float]):
            print(f"Progress: {current}/{total}")

        def on_finished(self):
            print("Finished")

    import whisper
    model = whisper.load_model("medium")

    with create_progress_listener_handle(PrintingProgressListener()) as listener:
        # Set verbose to None to disable the progress bar, as we are using our own
        result = model.transcribe("J:\\Dev\\OpenAI\\whisper\\tests\\Noriko\\out.mka", language="Japanese", fp16=False, verbose=None)
        print(result)

    print("Done")