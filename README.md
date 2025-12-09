# SSE Streaming TTFT Optimization

## 🎯 專案簡介
針對大型語言模型（LLM）推論場景開發的 Server-Sent Events (SSE) 串流優化系統，實現低延遲的即時 token 輸出，大幅改善使用者互動體驗。
透過 Async Decode Thread + Streamer + SSE，實現低 TTFT、非阻塞 token streaming，以及 Prefill/Decode pipeline。
本專案採用 FastAPI + SSE-Starlette + TextIteratorStreamer 技術，建立串流推論 pipeline，將 Time To First Token (TTFT) 從 2.5 秒降低至 580ms (P95)，延遲改善幅度達 76.7%。
- ✅ 即時串流輸出: SSE 協定實現 token-by-token 漸進式回應
- ✅ 非同步處理: Asyncio + Threading 架構避免阻塞
- ✅ TTFT 優化: 首 token 延遲降至 580ms (P95)，提升 76.7%

## 🚀 技術核心
⭐ 透過背景 Thread 推論、TextIteratorStreamer、SSE 即時 Token 傳輸，構成非阻塞的 Streaming Pipeline，有效降低 TTFT / Latency 並提升互動流暢度。
### 🔸 1. Async Decode Thread
#### 🎯 作法：
將推論 (model.generate) 放在背景 Thread 執行：
- 背景 Thread 做：
  - Prefill（重度矩陣運算）
  - Autoregressive Decode（逐 token）
  - 將 token 推進 streamer queue
- 同時 FastAPI 主執行緒完全不需要等待推論完成。
#### 👉 達成：
- ✔ 推論與輸出分離，使第一個token更快送出（降低 TTFT）。

### 🔸 2. TextIteratorStreamer + SSE Streaming
#### 🎯 作法：（Streaming 流程）
- 背景 Thread 產生 token → TextIteratorStreamer queue → SSE event → browser/client
- 流程：
  - 模型 decode 產生一個 token
  - streamer.push(token)
  - SSE handler for piece in streamer: 就能立刻收到
  - 把收到的 token 立即送給 client

💡 TextIteratorStreamer：逐 token 非阻塞拉取
💡 SSE (Server-Sent Events)：即時推送 token
💡 Async Event Loop：支援連續流式輸出、避免阻塞
💡 Background thread：負責 compute（Prefill + Decode）

#### 👉 達成：
- ✔ token 不累積
- ✔ streaming 變得順暢
- ✔ 不需等待整段輸出 → TTFT 降低

### 🔸 3. Prefill / Decode Pipeline 自然解耦
#### 🎯 作法：
- 背景 Thread 工作：
| Prefill | Decode |
|------|------|
| **embedding + attn weights** | autoregressive token production |
| **重度計算** | 輕度逐步計算 |

- FastAPI 主執行緒：
| 行為                  |
| ------------------- |
| 等待 streamer 的 token |
| 用 SSE 送給 client     |
| 不做任何矩陣運算（完全非阻塞）     |

#### 👉 達成：
- ✔ Prefill不阻塞 token 傳輸
- ✔ Decode token 出現後可立即送出
- ✔ TTFT 顯著降低、互動性更強


### 🔸 4. Non-blocking Inference（非阻塞推論架構）
#### 🎯 作法：
1. API Handler（async）不等待 compute
2. Compute 在背景 Thread 跑，不阻塞 event loop
3. SSE 持續推送 token，不需等待完整輸出
4. Compute 與 I/O 完全解耦

#### 👉 達成：
- ✔ TTFT 更低
- ✔ Latency 更穩定
- ✔ Decode Throughput 更順暢


## 🧰 技術架構
| 組件                  | 技術                                          |
| ------------------- | ------------------------------------------- |
| **Web framework**       | FastAPI、Uvicorn                         |
| **Streaming**           | SSE-Starlette                           |
| **LLM Token Streaming** | TextIteratorStreamer                    |
| **Compute**             | 背景 Thread                              |
| **Async**               | asyncio event loop, async SSE               |
| **Profiling**           | TTFT, latency, throughput, p95, token_count |
| **Models**              | Qwen2-1.5B / Phi-2 / DialoGPT / GPT2        |
| **Device**              | CUDA FP16                                   |


## 📊 效能指標
| 指標 | Baseline | 優化後 | 改善幅度 |
|------|------|------|------|
| **TTFT (P50)** | 1.8s | 420ms | 76.7% ↓ |
| **TTFT (P90)** | 2.5s | 580ms | 76.8% ↓ |
| **TTFT (P95)** | 3.2s | 740ms | 76.9% ↓ |
| **Throughput** | ~45tokens/s | ~45tokens/s  | - |

## 📊 Benchmark 結果
### TTFT分布圖
<img width="616" height="243" alt="Screenshot 2025-11-11 at 06 05 51" src="https://github.com/user-attachments/assets/e21dd99d-e897-43b3-91ed-55aa6194fff6" />

## 環境需求
- Python 3.9+
- CUDA 11.8+ / ROCm 5.7+
- GPU 記憶體 ≥ 4GB (Qwen2-1.5B)

