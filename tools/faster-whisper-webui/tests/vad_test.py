import pprint
import unittest
import numpy as np
import sys

sys.path.append('../whisper-webui')

from src.vad import AbstractTranscription, TranscriptionConfig, VadSileroTranscription

class TestVad(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestVad, self).__init__(*args, **kwargs)
        self.transcribe_calls = []

    def test_transcript(self):
        mock = MockVadTranscription()

        self.transcribe_calls.clear()
        result = mock.transcribe("mock", lambda segment : self.transcribe_segments(segment))

        self.assertListEqual(self.transcribe_calls, [ 
            [30, 30],
            [100, 100]
        ])

        self.assertListEqual(result['segments'],
            [{'end': 50.0, 'start': 40.0, 'text': 'Hello world '},
            {'end': 120.0, 'start': 110.0, 'text': 'Hello world '}]
        )

    def transcribe_segments(self, segment):
        self.transcribe_calls.append(segment.tolist())

        # Dummy text
        return {
            'text': "Hello world ",
            'segments': [
                {
                    "start": 10.0,
                    "end": 20.0,
                    "text": "Hello world "
                }   
            ],
            'language': ""
        }

class MockVadTranscription(AbstractTranscription):
    def __init__(self):
        super().__init__()

    def get_audio_segment(self, str, start_time: str = None, duration: str = None):
        start_time_seconds = float(start_time.removesuffix("s"))
        duration_seconds = float(duration.removesuffix("s"))

        # For mocking, this just returns a simple numppy array
        return np.array([start_time_seconds, duration_seconds], dtype=np.float64)

    def get_transcribe_timestamps(self, audio: str, config: TranscriptionConfig, start_time: float, duration: float):
        result = []

        result.append( {  'start': 30, 'end': 60 } )
        result.append( {  'start': 100, 'end': 200 } )
        return result

if __name__ == '__main__':
    unittest.main()