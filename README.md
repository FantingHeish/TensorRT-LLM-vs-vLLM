SSE Streaming 實作與 TTFT 對比
🎯 主要目的
驗證「Streaming 回傳（SSE Server-Sent Events）」相比傳統 Non-Streaming API 的響應速度差異， 並建立可量測 TTFT（Time To First Token） 與 總延遲（Latency） 的標準化測試框架。

🧰 技術內容
模組	說明
FastAPI + SSE-Starlette	實作伺服器端 SSE 串流端點 /generate_stream。
Transformers + TextIteratorStreamer	實際使用 Hugging Face 模型（如 Qwen2-0.5B-Instruct）進行 token 生成。
Threading + Streamer	以背景 thread 執行生成，同時逐 token 傳出。
TTFT 量測	從「接收請求」到「第一段文字送出」為止。
Latency 量測	從「接收請求」到「整段生成完成」。
⚖️ 對比實驗
模式	特徵	量測項目
Non-Streaming	一次性返回整段文字	TTFT（首段出現時間）與 Latency
Streaming	每次生成一段就推送給客戶端（SSE）	TTFT 與 Latency
📊 產出結果
* 以 P50 / P95 / P99 方式呈現 TTFT 分佈。
* 產生對比圖：poc1_ttft_comparison.png
* 結果檔：poc1_streaming_results.csv
* 圖表顯示 Streaming 在 TTFT 明顯快（即更早開始輸出文字）。

✅ 結論摘要
Streaming 架構可顯著降低用戶「第一段回應出現時間（TTFT）」， 即使總延遲（Latency）相近，體感上仍提升互動即時性。
