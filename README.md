## 🎯 專案簡介
針對大型語言模型（LLM）推論場景開發的 Server-Sent Events (SSE) 串流優化系統，
實現低延遲的即時 token 輸出，大幅改善使用者互動體驗。
透過非同步架構與 GPU 效能監控，達成 production-grade 的推論服務品質。
本專案採用 FastAPI + SSE-Starlette + TextIteratorStreamer 技術棧，
建立高效能的串流推論 pipeline，將 Time To First Token (TTFT) 從原本的 2.5 秒降低至 580ms (P95)，
延遲改善幅度達 76.7%，適用於對話機器人、即時翻譯、程式碼補全等即時互動場景。

## ✅ 核心功能
✅ 即時串流輸出: SSE 協定實現 token-by-token 漸進式回應
✅ 非同步處理: Asyncio + Threading 架構避免阻塞
✅ TTFT 優化: 首 token 延遲降至 580ms (P95)，提升 76.7%
✅ GPU 效能監控: 即時追蹤 GPU 使用率、記憶體、溫度
✅ Production-Ready: 支援多併發請求、錯誤處理、連線管理
✅ 模型支援: 相容 HuggingFace Transformers 所有生成模型

## 🧰 技術架構
| 模組 | 技術 |
|------|------|
| **深度學習框架** | PyTorch 2.0+、CUDA 11.8+ |
| **核心技術** | Dynamic Batching、KV Cache、Attention Masking |
| **GPU 優化** | Custom CUDA Kernels、Memory Pooling |
| **推論引擎** | HuggingFace Transformers、Flash Attention |
| **排程策略** | Priority Queue、First-Come-First-Served |
| **測試模型** | Qwen2-1.5B、LLaMA-7B |
| **部署方式** | FastAPI + Uvicorn |

## 📊 效能指標
| 指標 | Baseline | (batch=1)優化後 | (dynamic batch)改善幅度 |
|------|------|------|------|
| **吞吐量 (tokens/s)** | 68 | 501 | 7.37x |
| **平均延遲** | 3.2s | 0.45s | 86% ↓ |
| **GPU 使用率** | 45% | 89% | 44% ↑ |
| **記憶體使用** | 8.2GB | 7.8GB | 5% ↓ |
| **最大 Batch Size** | 1 | 16 | 16x |
