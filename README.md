# TensorRT-LLM-vs-vLLM
# TRT-LLM vs vLLM: RAG Inference Benchmark on Colab (DeepSeek-V3/R1-ready)

## TL;DR
- 同一套 Prompt 與並發設定，對比 TensorRT-LLM 與 vLLM 的端到端延遲（p50/p95）與吞吐（tokens/s）。
- 支援 batch=1/2/4/8、INT8/AWQ 量化（依模型與硬體支援而定）。
- 輕量品質評估（QA、Summarization）確保量化品質不崩。
- 可在 Colab 直接跑；若 TRT-LLM 本地安裝失敗，可配置遠端 TRT-LLM/Triton 端點，Colab 僅作壓測客戶端。

## 目錄
- `notebooks/01_colab_trtllm_vllm_bench.ipynb` — 一鍵 Notebook（環境、engine build、壓測、作圖、品質評估）
- `benchmarks/` — 產出的 CSV（latency、throughput、顯存、引擎大小）
- `plots/` — 產出的圖（Latency vs Concurrency、Tokens/s vs Batch、顯存）
- `app/` — 最小 OpenAI 相容 client + RAG 測試腳本（可獨立壓測）
- `configs/` — 模型與量化設定樣板（DeepSeek-V3/R1/Llama3/Qwen2）
- `README.md` — 本文件

## 快速開始（Colab）
1. 開啟 `notebooks/01_colab_trtllm_vllm_bench.ipynb`，Runtime 選 GPU（建議 T4/L4/A100）。
2. 執行「環境安裝」→「選擇模型與端點」→「建引擎或連線端點」→「啟動 vLLM baseline」→「跑壓測」。
3. 輸出 CSV 與圖會自動存進 `/content/benchmarks` 與 `/content/plots`，可直接上傳 GitHub。

## 模型與授權
- 預設示例用 `Llama-3-8B-Instruct` 或 `Qwen2-7B-Instruct` 作為可公開取得的 baseline。
- 若有權重存取，可在 `configs/deepseek_v3.yaml` 或 `configs/deepseek_r1.yaml` 中填入路徑，流程一致。

## 運行模式
- **Local TRT-LLM**：Colab 內安裝 TRT-LLM（若版本匹配），並 build engine + 服務端。
- **Remote TRT-LLM**：你在任一 GPU 主機以 `nvcr.io/nvidia/tensorrt-llm` 容器起服務；Notebook 設定 `TRTLLM_SERVER_URL` 直接壓測。

## 指標
- Latency p50/p95、端到端吞吐（tokens/s）、GPU Memory 峰值、Engine 大小。
- Quality：QA（EM/F1 粗略）、Summarization（ROUGE-L 或 cosine 相似度）。

## 產出
- 2～3 張關鍵圖：**Tokens/s vs Batch**、**p95 Latency vs Concurrency**、**顯存對比**。
- Nsight Systems 截圖（若使用本地 TRT-LLM 進行 profiling；Colab 可能受限）。
- 一頁結論：何種配置下 TRT-LLM 提升多少、量化對品質的影響。

## 常見問題
- 若 Colab 的 CUDA 與 TRT-LLM 不相容，改用 Remote 模式（最穩）。
- DeepSeek 模型較大，T4 可能 OOM；請選 7–8B 等級模型或縮短 `max_new_tokens`。
