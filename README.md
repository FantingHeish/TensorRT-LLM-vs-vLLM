# SSE Streaming TTFT Optimization

## 🎯 專案簡介
針對大型語言模型（LLM）推論場景開發的 Server-Sent Events (SSE) 串流優化系統，
實現低延遲的即時 token 輸出，大幅改善使用者互動體驗。
透過非同步架構與 GPU 效能監控，達成 production-grade 的推論服務品質。
本專案採用 FastAPI + SSE-Starlette + TextIteratorStreamer 技術棧，
建立高效能的串流推論 pipeline，將 Time To First Token (TTFT) 從原本的 2.5 秒降低至 580ms (P95)，
延遲改善幅度達 76.7%，適用於對話機器人、即時翻譯、程式碼補全等即時互動場景。

## ✅ 核心功能
- ✅ 即時串流輸出: SSE 協定實現 token-by-token 漸進式回應
- ✅ 非同步處理: Asyncio + Threading 架構避免阻塞
- ✅ TTFT 優化: 首 token 延遲降至 580ms (P95)，提升 76.7%
- ✅ Production-Ready: 支援多併發請求、錯誤處理、連線管理
- ✅ 模型支援: 相容 HuggingFace Transformers 所有生成模型

## 🧰 技術架構
| 模組 | 技術 |
|------|------|
| **Web 框架** | FastAPI、SSE-Starlette |
| **串流機制** | TextIteratorStreamer、Server-Sent Events |
| **非同步處理** | Asyncio、Threading |
| **模型推論** | HuggingFace Transformers、PyTorch |
| **效能監控** | psutil |
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
### 測試環境
- GPU: NVIDIA RTX 3090 (24GB)
- CPU: AMD Ryzen 9 5950X
- Model: Qwen2-1.5B-Instruct
- Batch Size: 1

### TTFT分布圖
<img width="616" height="243" alt="Screenshot 2025-11-11 at 06 05 51" src="https://github.com/user-attachments/assets/e21dd99d-e897-43b3-91ed-55aa6194fff6" />

### 延遲改善分析
| 優化項目 | Baseline | 
|------|------|
| **模型預載入** | -800ms |
| **Async Thread** | -600ms |
| **KV Cache 預分配** | -350ms |
| **SSE 協定優化** | -170ms |

## 環境需求
- Python 3.9+
- CUDA 11.8+ / ROCm 5.7+
- GPU 記憶體 ≥ 4GB (Qwen2-1.5B)

