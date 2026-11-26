"""German TTS with Kartoffel-Orpheus (natural, GGUF Q8) on the GPU. Run with .venv-tts python.
Usage: tts_kartoffel.py <narration.json> <outdir> --voice Lea [--only n1,n2] [--temp 0.6] [--suffix _x] [--seed 7]
Female voices: Sophie, Marie, Mia, Maria, Sophia, Lina, Lea
Male voices:   Jakob, Anton, Julian, Jan, Alexander, Emil, Ben, Elias, Felix, Jonas, Noah, Maximilian
--voice accepts a comma list (model is loaded once).
Writes <outdir>/<key><suffix>.wav (24 kHz). Word timings: align_tts.py afterwards.
"""
import argparse, json, os, re
import numpy as np, torch, soundfile as sf
from gguf import GGUFReader, dequantize
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer, LlamaConfig, LlamaForCausalLM
from snac import SNAC

REPO, FILE = "cstr/kartoffel-orpheus-3b-german-natural-GGUF", "kartoffel-orpheus-de-natural-q8_0.gguf"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv-tts", "kartoffel_bf16.pt")

def unpermute(w, n_head):  # undo llama.cpp's rotary q/k permutation
    return w.reshape(n_head, w.shape[0] // n_head // 2, 2, *w.shape[1:]).swapaxes(1, 2).reshape(w.shape)

def load_model(permuted):
    cfg = LlamaConfig(vocab_size=156940, hidden_size=3072, intermediate_size=8192, num_hidden_layers=28,
                      num_attention_heads=24, num_key_value_heads=8, head_dim=128, rms_norm_eps=1e-5,
                      rope_theta=500000.0, max_position_embeddings=131072, tie_word_embeddings=True,
                      rope_scaling={"rope_type": "llama3", "factor": 32.0, "low_freq_factor": 1.0,
                                    "high_freq_factor": 4.0, "original_max_position_embeddings": 8192})
    if os.path.exists(CACHE) and not permuted:
        sd = torch.load(CACHE)
    else:
        r = GGUFReader(hf_hub_download(REPO, FILE))
        names = {"attn_q": "self_attn.q_proj", "attn_k": "self_attn.k_proj", "attn_v": "self_attn.v_proj",
                 "attn_output": "self_attn.o_proj", "ffn_gate": "mlp.gate_proj", "ffn_up": "mlp.up_proj",
                 "ffn_down": "mlp.down_proj", "attn_norm": "input_layernorm", "ffn_norm": "post_attention_layernorm"}
        sd = {}
        for t in r.tensors:
            w = dequantize(t.data, t.tensor_type).reshape([int(x) for x in reversed(t.shape)]).astype(np.float32)
            n = t.name.removeprefix("talker.").removesuffix(".weight")
            if n == "token_embd": key = "model.embed_tokens.weight"
            elif n == "output_norm": key = "model.norm.weight"
            elif n == "output": key = "lm_head.weight"
            else:
                _, i, part = n.split(".", 2)
                key = f"model.layers.{i}.{names[part]}.weight"
                if permuted and part == "attn_q": w = unpermute(w, 24)
                if permuted and part == "attn_k": w = unpermute(w, 8)
            sd[key] = torch.from_numpy(w).to(torch.bfloat16)
        if not permuted:
            torch.save(sd, CACHE)
    if "lm_head.weight" in sd:
        cfg.tie_word_embeddings = False
    m = LlamaForCausalLM(cfg).to(torch.bfloat16)
    print("load:", m.load_state_dict(sd, strict=False))
    return m.cuda().eval()

def codes_to_audio(snac, toks):
    codes = [t - 128266 for t in toks if t >= 128266]
    codes = codes[: len(codes) // 7 * 7]
    l1, l2, l3 = [], [], []
    for i in range(0, len(codes), 7):
        c = codes[i:i + 7]
        l1.append(c[0]); l2 += [c[1] - 4096, c[4] - 4 * 4096]
        l3 += [c[2] - 2 * 4096, c[3] - 3 * 4096, c[5] - 5 * 4096, c[6] - 6 * 4096]
    layers = [torch.tensor(x, device="cuda").clamp(0, 4095).unsqueeze(0) for x in (l1, l2, l3)]
    with torch.inference_mode():
        return snac.decode(layers).squeeze().float().cpu().numpy()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("narration"); ap.add_argument("outdir"); ap.add_argument("--voice", default="Lea")
    ap.add_argument("--only"); ap.add_argument("--temp", type=float, default=0.6)
    ap.add_argument("--suffix", default=""); ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--permuted", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    tok = AutoTokenizer.from_pretrained("unsloth/Llama-3.2-3B-Instruct")
    model = load_model(a.permuted)
    snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").cuda().eval()
    texts = json.load(open(a.narration, encoding="utf-8-sig"))
    voices = a.voice.split(",")  # several voices -> files get suffix _<Voice>
    jobs = [(k, v) for v in voices for k in (a.only.split(",") if a.only else texts)]
    for k, voice in jobs:
        suffix = a.suffix + (f"_{voice}" if len(voices) > 1 else "")
        torch.manual_seed(a.seed)
        parts, cur = [], ""  # chunks of whole sentences, <= ~220 chars
        for s in [s for s in re.split(r"(?<=[.!?])\s+", texts[k].strip()) if s]:
            if cur and len(cur) + len(s) > 220:
                parts.append(cur); cur = s
            else:
                cur = f"{cur} {s}".strip()
        parts.append(cur)
        audio = []
        for p in parts:
            ids = [128259] + tok(f"{voice}: {p}").input_ids + [128009, 128260, 128261, 128257]
            x = torch.tensor([ids], device="cuda")
            with torch.inference_mode():
                out = model.generate(x, attention_mask=torch.ones_like(x), max_new_tokens=2400,
                                     do_sample=True, temperature=a.temp, top_p=0.95, repetition_penalty=1.1,
                                     eos_token_id=[128258, 128257], pad_token_id=128263)
            audio += [codes_to_audio(snac, out[0, len(ids):].tolist()), np.zeros(int(24000 * 0.15), np.float32)]
        path = os.path.join(a.outdir, f"{k}{suffix}.wav")
        sf.write(path, np.concatenate(audio[:-1]), 24000)
        print(k, path)

if __name__ == "__main__":
    main()
