from typing import Any, Dict, List

import copy

def merge_timestamps(timestamps: List[Dict[str, Any]], merge_window: float = 5, max_merge_size: float = 30, padding_left: float = 1, padding_right: float = 1):
    result = []

    if len(timestamps) == 0:
        return result
    if max_merge_size is None:
        return timestamps

    if padding_left is None:
        padding_left = 0
    if padding_right is None:
        padding_right = 0

    processed_time = 0
    current_segment = None

    for i in range(len(timestamps)):
        next_segment = timestamps[i]

        delta = next_segment['start'] - processed_time

        # Note that segments can still be longer than the max merge size, they just won't be merged in that case
        if current_segment is None or (merge_window is not None and delta > merge_window) \
                 or next_segment['end'] - current_segment['start'] > max_merge_size:
            # Finish the current segment
            if current_segment is not None:
                # Add right padding
                finish_padding = min(padding_right, delta / 2) if delta < padding_left + padding_right else padding_right
                current_segment['end'] += finish_padding
                delta -= finish_padding

                result.append(current_segment)

            # Start a new segment
            current_segment = copy.deepcopy(next_segment)

            # Pad the segment
            current_segment['start'] = current_segment['start'] - min(padding_left, delta)
            processed_time = current_segment['end']

        else:
            # Merge the segment
            current_segment['end'] = next_segment['end']
            processed_time = current_segment['end']
        
    # Add the last segment
    if current_segment is not None:
        current_segment['end'] += padding_right
        result.append(current_segment)
    
    return result