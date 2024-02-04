import sys
import unittest

sys.path.append('../whisper-webui')

from src.segments import merge_timestamps

class TestSegments(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestSegments, self).__init__(*args, **kwargs)
        
    def test_merge_segments(self):
        segments = [
            {'start': 10.0, 'end': 20.0},
            {'start': 22.0, 'end': 27.0},
            {'start': 31.0, 'end': 35.0},
            {'start': 45.0, 'end': 60.0},
            {'start': 61.0, 'end': 65.0},
            {'start': 68.0, 'end': 98.0},
            {'start': 100.0, 'end': 102.0},
            {'start': 110.0, 'end': 112.0}
        ]

        result = merge_timestamps(segments, merge_window=5, max_merge_size=30, padding_left=1, padding_right=1)

        self.assertListEqual(result, [
            {'start': 9.0, 'end': 36.0},
            {'start': 44.0, 'end': 66.0},
            {'start': 67.0, 'end': 99.0},
            {'start': 99.0, 'end': 103.0},
            {'start': 109.0, 'end': 113.0}
        ])

    def test_overlap_next(self):
        segments = [
            {'start': 5.0, 'end': 39.182},
            {'start': 39.986, 'end': 40.814}
        ]

        result = merge_timestamps(segments, merge_window=5, max_merge_size=30, padding_left=1, padding_right=1)

        self.assertListEqual(result, [
            {'start': 4.0, 'end': 39.584},
            {'start': 39.584, 'end': 41.814}
        ])

if __name__ == '__main__':
    unittest.main()