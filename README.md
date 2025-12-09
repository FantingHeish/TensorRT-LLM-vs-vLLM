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
- Background Thread
  - 執行 Prefill（重計算）
  - Autoregressive Decode（逐 token）
- FastAPI 主執行緒
  - 不做 compute
  - 專責讀取 Streamer、推送 token
#### 👉 達成：
- ✔ 推論與輸出分離，使第一個token更快送出（降低 TTFT）。

### 🔸 2. Streaming Pipeline：token 一生成就送到 client
#### 🎯 作法：（Streaming 流程）
1. 背景 Thread 執行 model.generate()
2. 每生成一個 token → push 到 TextIteratorStreamer queue
3. FastAPI SSE handler 逐 token 傳輸：
💡 TextIteratorStreamer：逐 token 非阻塞拉取
💡 SSE (Server-Sent Events)：即時推送 token
💡 Async Event Loop：支援連續流式輸出、避免阻塞

#### 👉 達成：
- ✔ Streamer 一旦收到 token，即刻送給 client —— 無需等待整段完成。

### 🔸 3. Prefill / Decode Pipeline 的自然解耦
#### 🎯 作法：
架構會自動形成兩條 pipeline 如下：
| 執行緒 | 工作內容 |
|------|------|
| **背景 Thread** | Prefill → Decode → push token 到 Streamer |
| **主執行緒（FastAPI）** | 從 Streamer 拉 token → SSE 傳給前端 |

#### 👉 達成：
- ✔ Prefill（重度計算）不阻塞 token 傳輸
- ✔ Decode token 出現後可立即送出
- ✔ TTFT 顯著降低、互動性更強

### 🔸 4. Non-blocking Inference（非阻塞推論架構）
#### 🎯 作法：
1. API Handler（async）不等待 compute
2. Compute 在背景 Thread 跑，不阻塞 event loop
3. SSE 持續推送 token，不需等待完整輸出
4. Compute 與 I/O 完全解耦

#### 👉 達成：
✔ TTFT 更低
✔ Latency 更穩定
✔ Decode Throughput 更順暢


## 🧰 技術架構
| 模組 | 技術 |
|------|------|
| **Web 框架** | FastAPI、SSE-Starlette |
| **串流機制** | TextIteratorStreamer、Server-Sent Events |
| **非同步處理** | Asyncio、Threading |
| **模型推論** | HuggingFace Transformers、PyTorch |
| **測試模型** | Qwen2-1.5B-Instruct |
| **部署方式** | Uvicorn ASGI Server |

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

