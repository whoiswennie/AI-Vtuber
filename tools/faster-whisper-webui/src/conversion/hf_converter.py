# https://github.com/bayartsogt-ya/whisper-multiple-hf-datasets

from copy import deepcopy
import torch

WHISPER_MAPPING = {
    "layers": "blocks",
    "fc1": "mlp.0",
    "fc2": "mlp.2",
    "final_layer_norm": "mlp_ln",
    "layers": "blocks",
    ".self_attn.q_proj": ".attn.query",
    ".self_attn.k_proj": ".attn.key",
    ".self_attn.v_proj": ".attn.value",
    ".self_attn_layer_norm": ".attn_ln",
    ".self_attn.out_proj": ".attn.out",
    ".encoder_attn.q_proj": ".cross_attn.query",
    ".encoder_attn.k_proj": ".cross_attn.key",
    ".encoder_attn.v_proj": ".cross_attn.value",
    ".encoder_attn_layer_norm": ".cross_attn_ln",
    ".encoder_attn.out_proj": ".cross_attn.out",
    "decoder.layer_norm.": "decoder.ln.",
    "encoder.layer_norm.": "encoder.ln_post.",
    "embed_tokens": "token_embedding",
    "encoder.embed_positions.weight": "encoder.positional_embedding",
    "decoder.embed_positions.weight": "decoder.positional_embedding",
    "layer_norm": "ln_post",
}


def rename_keys(s_dict):
    keys = list(s_dict.keys())
    for key in keys:
        new_key = key
        for k, v in WHISPER_MAPPING.items():
            if k in key:
                new_key = new_key.replace(k, v)

        print(f"{key} -> {new_key}")

        s_dict[new_key] = s_dict.pop(key)
    return s_dict


def convert_hf_whisper(hf_model_name_or_path: str, whisper_state_path: str):
    from transformers import WhisperForConditionalGeneration
    transformer_model = WhisperForConditionalGeneration.from_pretrained(hf_model_name_or_path)
    config = transformer_model.config

    # first build dims
    dims = {
        'n_mels': config.num_mel_bins,
        'n_vocab': config.vocab_size,
        'n_audio_ctx': config.max_source_positions,
        'n_audio_state': config.d_model,
        'n_audio_head': config.encoder_attention_heads,
        'n_audio_layer': config.encoder_layers,
        'n_text_ctx': config.max_target_positions,
        'n_text_state': config.d_model,
        'n_text_head': config.decoder_attention_heads,
        'n_text_layer': config.decoder_layers
    }

    state_dict = deepcopy(transformer_model.model.state_dict())
    state_dict = rename_keys(state_dict)

    torch.save({"dims": dims, "model_state_dict": state_dict}, whisper_state_path)