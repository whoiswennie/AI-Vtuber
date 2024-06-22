# Run the app with no audio file restrictions
from app import create_ui
from src.config import ApplicationConfig

create_ui(ApplicationConfig.create_default(input_audio_max_duration=-1))