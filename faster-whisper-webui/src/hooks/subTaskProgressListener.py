from src.hooks.progressListener import ProgressListener

from typing import Union

class SubTaskProgressListener(ProgressListener):
    """
    A sub task listener that reports the progress of a sub task to a base task listener
    Parameters
    ----------
    base_task_listener : ProgressListener
        The base progress listener to accumulate overall progress in.
    base_task_total : float
        The maximum total progress that will be reported to the base progress listener.
    sub_task_start : float
        The starting progress of a sub task, in respect to the base progress listener.
    sub_task_total : float
        The total amount of progress a sub task will report to the base progress listener.
    """
    def __init__(
        self,
        base_task_listener: ProgressListener,
        base_task_total: float,
        sub_task_start: float,
        sub_task_total: float,
    ):
        self.base_task_listener = base_task_listener
        self.base_task_total = base_task_total
        self.sub_task_start = sub_task_start
        self.sub_task_total = sub_task_total

    def on_progress(self, current: Union[int, float], total: Union[int, float]):
        sub_task_progress_frac = current / total
        sub_task_progress = self.sub_task_start + self.sub_task_total * sub_task_progress_frac
        self.base_task_listener.on_progress(sub_task_progress, self.base_task_total)

    def on_finished(self):
        self.base_task_listener.on_progress(self.sub_task_start + self.sub_task_total, self.base_task_total)