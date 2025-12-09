import asyncio
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import torch
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TextIteratorStreamer,
)

# ============================================================
# Config
# ============================================================

MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"  # 你也可以換成其他 HF 模型
DEVICE = "cuda"
DTYPE = torch.float16
MAX_NEW_TOKENS = 128
TEMPERATURE = 0.7
TOP_P = 0.95

app = FastAPI(title="PoC#1 - SSE Streaming Inference Server")

print(f"🚀 Loading model: {MODEL_ID} (device={DEVICE})")

model_ready = False
tokenizer = None
model = None

# 專門給 tokenizer 用的 ThreadPool → tokenizer parallelization
tokenizer_executor = ThreadPoolExecutor(max_workers=4)


# ============================================================
# Model Loading & Warmup
# ============================================================

warmup_metrics = {
    "warmup_tokenization_ms": None,
    "warmup_generate_ms": None,
    "warmup_total_ms": None,
}


def _load_model():
    global tokenizer, model, model_ready, warmup_metrics

    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        use_fast=True,
        trust_remote_code=True,
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    t_tok_end = time.time()

    model_ = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=DTYPE,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    ).eval()

    t_model_end = time.time()

    # Warmup: small generate 一次，初始化 CUDA context / graph 等
    print("🔥 Warming up model...")
    with torch.no_grad():
        inputs = tokenizer("Hello", return_tensors="pt").to(DEVICE)
        _ = model_.generate(
            **inputs,
            max_new_tokens=2,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )
    torch.cuda.synchronize()
    t_warm_end = time.time()

    tokenizer_time_ms = (t_tok_end - t0) * 1000
    load_time_ms = (t_model_end - t_tok_end) * 1000
    warm_time_ms = (t_warm_end - t_model_end) * 1000

    warmup_metrics["warmup_tokenization_ms"] = round(tokenizer_time_ms, 2)
    warmup_metrics["warmup_generate_ms"] = round(warm_time_ms, 2)
    warmup_metrics["warmup_total_ms"] = round((t_warm_end - t0) * 1000, 2)

    print(
        f"✅ Model loaded. "
        f"Tokenizer: {tokenizer_time_ms:.1f}ms, "
        f"Load: {load_time_ms:.1f}ms, "
        f"Warmup: {warm_time_ms:.1f}ms, "
        f"Total: {warmup_metrics['warmup_total_ms']:.1f}ms"
    )

    return model_


try:
    model = _load_model()
    model_ready = True
except Exception as e:
    print(f"❌ Model loading failed: {e}")
    import traceback

    traceback.print_exc()
    model_ready = False


# ============================================================
# Request Models
# ============================================================

class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = MAX_NEW_TOKENS
    temperature: float = TEMPERATURE
    top_p: float = TOP_P


# ============================================================
# Helper: Async Tokenization (Tokenizer Parallelization)
# ============================================================

def _tokenize_sync(prompt: str):
    """同步 tokenizer 呼叫；會被包在 thread pool 裡平行化執行。"""
    return tokenizer(prompt, return_tensors="pt")


async def tokenize_async(prompt: str):
    """
    非同步 tokenization：
    - 利用 ThreadPoolExecutor 將 CPU-bound 的 tokenizer 丟到背景執行緒
    - 多個請求同時進來時，tokenizer 可以平行化 → tokenizer parallelization
    """
    loop = asyncio.get_running_loop()
    t0 = time.time()
    inputs = await loop.run_in_executor(
        tokenizer_executor,
        _tokenize_sync,
        prompt,
    )
    t1 = time.time()
    inputs = inputs.to(DEVICE)
    return inputs, t0, t1  # 回傳 tokenization 的時間點


# ============================================================
# Helper: Background Generate
# ============================================================

def _run_generate_background(inputs, streamer, req: GenerateRequest):
    """
    背景 Thread 執行 model.generate：
    - Prefill + Decode 全部在這裡跑
    - streamer 會在 decode 過程逐 token push 給前端 event loop
    """
    try:
        if not model_ready:
            return

        with torch.no_grad():
            model.generate(
                **inputs,
                max_new_tokens=req.max_new_tokens,
                temperature=req.temperature,
                top_p=req.top_p,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                streamer=streamer,
                use_cache=True,
            )

        torch.cuda.synchronize()
    except Exception as e:
        print(f"❌ Generation failed: {e}")


# ============================================================
# Non-Streaming Endpoint (Baseline)
# ============================================================

@app.post("/generate")
async def generate_non_streaming(req: GenerateRequest):
    """
    Baseline：一次性回傳整段文字（不使用 SSE）。
    但內部仍用 TextIteratorStreamer 來量 token timing，拿到：
    - tokenization_ms
    - prefill_ms
    - decode_ms
    - ttft_ms
    - latency_ms
    - decode_tokens_per_s
    """
    if not model_ready:
        return JSONResponse({"error": "Model not ready"}, status_code=503)

    try:
        rid = str(uuid.uuid4())
        t_req_start = time.time()

        # 1) Async tokenization（平行化）
        inputs, t_tok_start, t_tok_end = await tokenize_async(req.prompt)
        tokenization_ms = (t_tok_end - t_tok_start) * 1000

        # 2) streamer & background thread
        streamer = TextIteratorStreamer(
            tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
            timeout=120.0,
        )

        t_gen_start = time.time()
        th = threading.Thread(
            target=_run_generate_background,
            args=(inputs, streamer, req),
            daemon=True,
        )
        th.start()

        # 3) Collect tokens，同時量 prefill / decode
        first_piece_time = None
        pieces = []
        piece_count = 0

        for piece in streamer:
            if piece and piece.strip():
                now = time.time()
                if first_piece_time is None:
                    first_piece_time = now
                piece_count += 1
                pieces.append(piece)

        th.join(timeout=120.0)
        t_end = time.time()

        # 4) Metrics
        if first_piece_time is None:
            # 沒有任何 token，避免錯誤
            first_piece_time = t_end

        ttft_ms = (first_piece_time - t_req_start) * 1000
        latency_ms = (t_end - t_req_start) * 1000
        prefill_ms = max(first_piece_time - t_tok_end, 0) * 1000
        decode_ms = max(t_end - first_piece_time, 0) * 1000

        if decode_ms > 0:
            decode_tok_per_s = piece_count / (decode_ms / 1000)
        else:
            decode_tok_per_s = 0.0

        full_text = "".join(pieces)

        metrics = {
            "rid": rid,
            "mode": "non_streaming",
            "ttft_ms": round(ttft_ms, 2),
            "latency_ms": round(latency_ms, 2),
            "tokenization_ms": round(tokenization_ms, 2),
            "prefill_ms": round(prefill_ms, 2),
            "decode_ms": round(decode_ms, 2),
            "decode_tokens": piece_count,
            "decode_tok_per_s": round(decode_tok_per_s, 2),
        }

        return JSONResponse(
            {
                "metrics": metrics,
                "text": full_text,
            }
        )

    except Exception as e:
        print(f"❌ Non-Streaming error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ============================================================
# Streaming Endpoint (SSE + Async Decode Thread)
# ============================================================

@app.post("/generate_stream")
async def generate_streaming(req: GenerateRequest):
    """
    Streaming 版本：
    - Async handler + 背景 Thread 跑 generate()
    - SSE 逐 token 推送
    - 真實 TTFT（第一個 token）+ prefill/decode 拆開
    """
    if not model_ready:
        return EventSourceResponse(
            content={"error": "Model not ready"},
            status_code=503,
        )

    try:
        rid = str(uuid.uuid4())
        t_req_start = time.time()

        # 1) Async tokenization（平行化）
        inputs, t_tok_start, t_tok_end = await tokenize_async(req.prompt)
        tokenization_ms = (t_tok_end - t_tok_start) * 1000

        # 2) streamer & background thread
        streamer = TextIteratorStreamer(
            tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
            timeout=120.0,
        )

        th = threading.Thread(
            target=_run_generate_background,
            args=(inputs, streamer, req),
            daemon=True,
        )
        th.start()

        async def event_generator():
            nonlocal rid, t_req_start, tokenization_ms

            first_piece_time = None
            piece_count = 0

            # 先送一個 start event
            yield {
                "event": "start",
                "data": json.dumps(
                    {
                        "rid": rid,
                        "status": "generating",
                    }
                ),
            }

            # 3) 逐 piece 讀取 streamer → SSE 推送
            for piece in streamer:
                if piece and piece.strip():
                    now = time.time()
                    if first_piece_time is None:
                        first_piece_time = now

                    piece_count += 1

                    yield {
                        "event": "token",
                        "data": json.dumps(
                            {
                                "text": piece,
                                "token_id": piece_count,
                            }
                        ),
                    }
                    # 讓 event loop 有機會處理其他 I/O
                    await asyncio.sleep(0)

            th.join(timeout=120.0)
            t_end = time.time()

            # 4) Metrics
            if first_piece_time is None:
                first_piece_time = t_end

            ttft_ms = (first_piece_time - t_req_start) * 1000
            latency_ms = (t_end - t_req_start) * 1000
            prefill_ms = max(first_piece_time - t_tok_end, 0) * 1000
            decode_ms = max(t_end - first_piece_time, 0) * 1000

            if decode_ms > 0:
                decode_tok_per_s = piece_count / (decode_ms / 1000)
            else:
                decode_tok_per_s = 0.0

            metrics_data = {
                "rid": rid,
                "mode": "streaming",
                "ttft_ms": round(ttft_ms, 2),
                "latency_ms": round(latency_ms, 2),
                "tokenization_ms": round(tokenization_ms, 2),
                "prefill_ms": round(prefill_ms, 2),
                "decode_ms": round(decode_ms, 2),
                "decode_tokens": piece_count,
                "decode_tok_per_s": round(decode_tok_per_s, 2),
            }

            print(
                f"✅ Streaming completed "
                f"(TTFT={metrics_data['ttft_ms']}ms, "
                f"Latency={metrics_data['latency_ms']}ms, "
                f"Tok={piece_count}, "
                f"DecodeTok/s={metrics_data['decode_tok_per_s']})"
            )

            # 傳回 metrics event
            yield {
                "event": "metrics",
                "data": json.dumps(metrics_data),
            }
            yield {
                "event": "done",
                "data": "{}",
            }

        return EventSourceResponse(event_generator())

    except Exception as e:
        print(f"❌ Streaming error: {e}")
        return EventSourceResponse(
            content={"error": str(e)},
            status_code=500,
        )


# ============================================================
# Health & Warmup Metrics
# ============================================================

@app.get("/health")
async def health():
    status = "ready" if model_ready else "loading"
    return {
        "status": status,
        "model": MODEL_ID,
        "device": DEVICE,
        "warmup": warmup_metrics,
    }
