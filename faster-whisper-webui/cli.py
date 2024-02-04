import argparse
import os
import pathlib
from urllib.parse import urlparse
import warnings
import numpy as np

import torch
from app import VadOptions, WhisperTranscriber
from src.config import ApplicationConfig, VadInitialPromptMode
from src.download import download_url
from src.languages import get_language_names

from src.utils import optional_float, optional_int, str2bool
from src.whisper.whisperFactory import create_whisper_container

def cli():
    app_config = ApplicationConfig.create_default()
    whisper_models = app_config.get_model_names()

    # For the CLI, we fallback to saving the output to the current directory
    output_dir = app_config.output_dir if app_config.output_dir is not None else "."

    # Environment variable overrides
    default_whisper_implementation = os.environ.get("WHISPER_IMPLEMENTATION", app_config.whisper_implementation)

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("audio", nargs="+", type=str, \
                        help="audio file(s) to transcribe")
    parser.add_argument("--model", default=app_config.default_model_name, choices=whisper_models, \
                        help="name of the Whisper model to use") # medium
    parser.add_argument("--model_dir", type=str, default=app_config.model_dir, \
                        help="the path to save model files; uses ~/.cache/whisper by default")
    parser.add_argument("--device", default=app_config.device, \
                        help="device to use for PyTorch inference")
    parser.add_argument("--output_dir", "-o", type=str, default=output_dir, \
                        help="directory to save the outputs")
    parser.add_argument("--verbose", type=str2bool, default=app_config.verbose, \
                        help="whether to print out the progress and debug messages")
    parser.add_argument("--whisper_implementation", type=str, default=default_whisper_implementation, choices=["whisper", "faster-whisper"],\
                        help="the Whisper implementation to use")
                        
    parser.add_argument("--task", type=str, default=app_config.task, choices=["transcribe", "translate"], \
                        help="whether to perform X->X speech recognition ('transcribe') or X->English translation ('translate')")
    parser.add_argument("--language", type=str, default=app_config.language, choices=sorted(get_language_names()), \
                        help="language spoken in the audio, specify None to perform language detection")

    parser.add_argument("--vad", type=str, default=app_config.default_vad, choices=["none", "silero-vad", "silero-vad-skip-gaps", "silero-vad-expand-into-gaps", "periodic-vad"], \
                        help="The voice activity detection algorithm to use") # silero-vad
    parser.add_argument("--vad_initial_prompt_mode", type=str, default=app_config.vad_initial_prompt_mode, choices=["prepend_all_segments", "prepend_first_segment"], \
                        help="Whether or not to prepend the initial prompt to each VAD segment (prepend_all_segments), or just the first segment (prepend_first_segment)") # prepend_first_segment
    parser.add_argument("--vad_merge_window", type=optional_float, default=app_config.vad_merge_window, \
                        help="The window size (in seconds) to merge voice segments")
    parser.add_argument("--vad_max_merge_size", type=optional_float, default=app_config.vad_max_merge_size,\
                         help="The maximum size (in seconds) of a voice segment")
    parser.add_argument("--vad_padding", type=optional_float, default=app_config.vad_padding, \
                        help="The padding (in seconds) to add to each voice segment")
    parser.add_argument("--vad_prompt_window", type=optional_float, default=app_config.vad_prompt_window, \
                        help="The window size of the prompt to pass to Whisper")
    parser.add_argument("--vad_cpu_cores", type=int, default=app_config.vad_cpu_cores, \
                        help="The number of CPU cores to use for VAD pre-processing.") # 1
    parser.add_argument("--vad_parallel_devices", type=str, default=app_config.vad_parallel_devices, \
                        help="A commma delimited list of CUDA devices to use for parallel processing. If None, disable parallel processing.") # ""
    parser.add_argument("--auto_parallel", type=bool, default=app_config.auto_parallel, \
                        help="True to use all available GPUs and CPU cores for processing. Use vad_cpu_cores/vad_parallel_devices to specify the number of CPU cores/GPUs to use.") # False

    parser.add_argument("--temperature", type=float, default=app_config.temperature, \
                        help="temperature to use for sampling")
    parser.add_argument("--best_of", type=optional_int, default=app_config.best_of, \
                        help="number of candidates when sampling with non-zero temperature")
    parser.add_argument("--beam_size", type=optional_int, default=app_config.beam_size, \
                        help="number of beams in beam search, only applicable when temperature is zero")
    parser.add_argument("--patience", type=float, default=app_config.patience, \
                        help="optional patience value to use in beam decoding, as in https://arxiv.org/abs/2204.05424, the default (1.0) is equivalent to conventional beam search")
    parser.add_argument("--length_penalty", type=float, default=app_config.length_penalty, \
                        help="optional token length penalty coefficient (alpha) as in https://arxiv.org/abs/1609.08144, uses simple lengt normalization by default")

    parser.add_argument("--suppress_tokens", type=str, default=app_config.suppress_tokens, \
                        help="comma-separated list of token ids to suppress during sampling; '-1' will suppress most special characters except common punctuations")
    parser.add_argument("--initial_prompt", type=str, default=app_config.initial_prompt, \
                        help="optional text to provide as a prompt for the first window.")
    parser.add_argument("--condition_on_previous_text", type=str2bool, default=app_config.condition_on_previous_text, \
                        help="if True, provide the previous output of the model as a prompt for the next window; disabling may make the text inconsistent across windows, but the model becomes less prone to getting stuck in a failure loop")
    parser.add_argument("--fp16", type=str2bool, default=app_config.fp16, \
                        help="whether to perform inference in fp16; True by default")
    parser.add_argument("--compute_type", type=str, default=app_config.compute_type, choices=["default", "auto", "int8", "int8_float16", "int16", "float16", "float32"], \
                        help="the compute type to use for inference")

    parser.add_argument("--temperature_increment_on_fallback", type=optional_float, default=app_config.temperature_increment_on_fallback, \
                        help="temperature to increase when falling back when the decoding fails to meet either of the thresholds below")
    parser.add_argument("--compression_ratio_threshold", type=optional_float, default=app_config.compression_ratio_threshold, \
                        help="if the gzip compression ratio is higher than this value, treat the decoding as failed")
    parser.add_argument("--logprob_threshold", type=optional_float, default=app_config.logprob_threshold, \
                        help="if the average log probability is lower than this value, treat the decoding as failed")
    parser.add_argument("--no_speech_threshold", type=optional_float, default=app_config.no_speech_threshold, \
                        help="if the probability of the <|nospeech|> token is higher than this value AND the decoding has failed due to `logprob_threshold`, consider the segment as silence")

    args = parser.parse_args().__dict__
    model_name: str = args.pop("model")
    model_dir: str = args.pop("model_dir")
    output_dir: str = args.pop("output_dir")
    device: str = args.pop("device")
    os.makedirs(output_dir, exist_ok=True)

    whisper_implementation = args.pop("whisper_implementation")
    print(f"Using {whisper_implementation} for Whisper")

    if model_name.endswith(".en") and args["language"] not in {"en", "English"}:
        warnings.warn(f"{model_name} is an English-only model but receipted '{args['language']}'; using English instead.")
        args["language"] = "en"

    temperature = args.pop("temperature")
    temperature_increment_on_fallback = args.pop("temperature_increment_on_fallback")
    if temperature_increment_on_fallback is not None:
        temperature = tuple(np.arange(temperature, 1.0 + 1e-6, temperature_increment_on_fallback))
    else:
        temperature = [temperature]

    vad = args.pop("vad")
    vad_initial_prompt_mode = args.pop("vad_initial_prompt_mode")
    vad_merge_window = args.pop("vad_merge_window")
    vad_max_merge_size = args.pop("vad_max_merge_size")
    vad_padding = args.pop("vad_padding")
    vad_prompt_window = args.pop("vad_prompt_window")
    vad_cpu_cores = args.pop("vad_cpu_cores")
    auto_parallel = args.pop("auto_parallel")
    
    compute_type = args.pop("compute_type")

    transcriber = WhisperTranscriber(delete_uploaded_files=False, vad_cpu_cores=vad_cpu_cores, app_config=app_config)
    transcriber.set_parallel_devices(args.pop("vad_parallel_devices"))
    transcriber.set_auto_parallel(auto_parallel)

    model = create_whisper_container(whisper_implementation=whisper_implementation, model_name=model_name, 
                                     device=device, compute_type=compute_type, download_root=model_dir, models=app_config.models)

    if (transcriber._has_parallel_devices()):
        print("Using parallel devices:", transcriber.parallel_device_list)

    for audio_path in args.pop("audio"):
        sources = []

        # Detect URL and download the audio
        if (uri_validator(audio_path)):
            # Download from YouTube/URL directly
            for source_path in  download_url(audio_path, maxDuration=-1, destinationDirectory=output_dir, playlistItems=None):
                source_name = os.path.basename(source_path)
                sources.append({ "path": source_path, "name": source_name })
        else:
            sources.append({ "path": audio_path, "name": os.path.basename(audio_path) })

        for source in sources:
            source_path = source["path"]
            source_name = source["name"]

            vadOptions = VadOptions(vad, vad_merge_window, vad_max_merge_size, vad_padding, vad_prompt_window, 
                                    VadInitialPromptMode.from_string(vad_initial_prompt_mode))

            result = transcriber.transcribe_file(model, source_path, temperature=temperature, vadOptions=vadOptions, **args)
            
            transcriber.write_result(result, source_name, output_dir)

    transcriber.close()

def uri_validator(x):
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc])
    except:
        return False

if __name__ == '__main__':
    cli()