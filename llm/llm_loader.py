import os
MODEL_PATH = os.getenv("WEALTHOS_MODEL_PATH", "./models/mistral-7b-instruct-v0.3.Q4_K_M.gguf")
N_GPU_LAYERS   = -1
N_CTX          = 4096
MAX_TOKENS     = 1024
TEMPERATURE    = 0.1
REPEAT_PENALTY = 1.1
TOP_P          = 0.9


def load_model(
    model_path: str = MODEL_PATH,
    n_gpu_layers: int = N_GPU_LAYERS,
    n_ctx: int = N_CTX
):
    try:
        from llama_cpp import Llama
        from pathlib import Path

        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}\n"
                "Download it first using the setup cell."
            )

        print(f"[LLMLoader] Loading Mistral 7B from {model_path}...")
        print(f"[LLMLoader] GPU layers: {n_gpu_layers} | Context: {n_ctx}")

        llm = Llama(
            model_path   = model_path,
            n_gpu_layers = n_gpu_layers,
            n_ctx        = n_ctx,
            n_batch      = 512,
            verbose      = False
        )

        print("[LLMLoader] Model loaded successfully.")
        return llm

    except Exception as e:
        print(f"[LLMLoader] ERROR loading model: {e}")
        raise


def format_prompt(system_prompt: str, user_message: str) -> str:
    return f"[INST] {system_prompt}\n\n{user_message} [/INST]"


def generate(
    llm,
    system_prompt: str,
    user_message: str,
    max_tokens: int = MAX_TOKENS,
    temperature: float = TEMPERATURE,
    repeat_penalty: float = REPEAT_PENALTY,
    top_p: float = TOP_P
) -> str:
    try:
        prompt = format_prompt(system_prompt, user_message)

        output = llm(
            prompt,
            max_tokens     = max_tokens,
            temperature    = temperature,
            repeat_penalty = repeat_penalty,
            top_p          = top_p,
            stop           = ["</s>", "[INST]", "[/INST]"]
        )

        response_text = output["choices"][0]["text"].strip()

        usage = output.get("usage", {})
        print(
            f"[LLMLoader] Tokens — "
            f"prompt: {usage.get('prompt_tokens', '?')} | "
            f"completion: {usage.get('completion_tokens', '?')}"
        )

        return response_text

    except Exception as e:
        print(f"[LLMLoader] ERROR during inference: {e}")
        return f"ERROR: {str(e)}"


def get_model_info(llm) -> dict:
    try:
        return {
            "model_path":   MODEL_PATH,
            "n_ctx":        N_CTX,
            "n_gpu_layers": N_GPU_LAYERS,
            "max_tokens":   MAX_TOKENS,
            "temperature":  TEMPERATURE,
            "status":       "loaded"
        }
    except Exception:
        return {"status": "error"}
