# 生命空間 II｜非官方概念重建

這是受到 Christa Sommerer 與 Laurent Mignonneau 的互動藝術作品 **Life Spacies II（生命空間 II）** 啟發的個人研究／互動重建專案。

**本專案不是原作的原始碼、官方移植或逐項還原。** 原作完整的造型函式及演算法參數未公開；本專案自行實作可檢視的基因映射與 2D 人工生命模擬。

## 立即體驗（目前 v2）

開啟 [index.html](index.html) 即可在桌面或手機瀏覽器離線使用；不需安裝相依套件或連線服務。

功能包括：

- 輸入文字產生生物，並預覽與逐字檢查 11 項基因性狀對應。
- 五種主要生物輪廓及不同的肢體、紋理、色彩等特徵。
- 字元作為食物：生物依其基因食性覓食、消耗能量、死亡、交配與突變。
- 完全空箱與三隻示範生物兩種起始模式、模擬速度、暫停、自動投餵。
- 點選個體查看基因、拖曳複製個體、點擊空白區投放字母。

v2 已知限制：沒有完整生物清單與死亡檔案、沒有個體生命紀錄、進食訊息混在全域事件、沒有獨立清空飼料；這些屬於 v3 待辦，**尚未實作**。

## 專案檔案

- `index.html`：**現行程式唯一正式來源**（保留原始 v2 HTML，尚未模組化）。
- `archive/life-spacies-v1.html`：先前 v1 的歷史快照，供比較；不要與現行版本同時維護功能。

往後如需模組化，應先建立來源檔與建置流程，並讓單一可執行 HTML 由正式來源產生；避免直接修改多份版本而造成漂移。

## 規格、文件與版本計畫

[Notion：生命空間 II｜原作研究、互動重建與版本規劃](https://app.notion.com/p/411b4185273f81b6bf45f656c9f3719c)

Notion 依主題區分研究、基因模型、v1／v2 現況、v3 需求、RWD 設計、測試與待確認事項。GitHub 管理程式碼及修改歷史。**不要將 v3 的規劃頁視為已上線功能。**

## 測試與變更驗證

`main` 的 GitHub Actions 在每次推送與 Pull Request 時執行兩類檢查：

- `tests/baseline.test.mjs`：以 Node.js 檢查 HTML、嵌入式 JavaScript 語法與主要元件。
- `tests/browser_regression.py`：以 Playwright 驅動 Chromium，實際操作 v2 的基因預覽、五種外型、空箱及示範、生成、基因檢視、餵食、暫停、容量上限與響應式排版。

本機執行（需 Python 及 Playwright Chromium）：

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m unittest discover -s tests -p 'browser_*.py' -v
node --test tests/baseline.test.mjs
```

如本機已安裝 Chromium，也可設定 `CHROMIUM_EXECUTABLE` 指向其執行檔。瀏覽器測試會載入正式 `index.html` 的完整文字並執行，**不會修改生產程式**。

**覆蓋範圍限制：** 目前並未以決定性測試驗證長時間覓食／繁殖／死亡的完整事件鏈，也未驗證所有觸控拖曳手勢。v3 動工前應持續補強這些高風險行為。

## 技術與來源

此重建採用 HTML、CSS、Canvas 與原生 JavaScript。現有公式是自行設計的可追蹤映射，不等於原作 1999 年的完整 3D 網格變形演算法。

- [藝術家官方資料](https://interface.ufg.ac.at/christa-laurent/LifeSpaciesII.html)
- [Life Spacies II 技術論文](https://icat.vrsj.org/ICAT2003/papers/99215.pdf)
- [日本 ICC：Life Spacies 初代作品](https://www.ntticc.or.jp/en/archive/works/life-spacies/)

本儲存庫尚未指定軟體授權條款；公開可見不表示自動授予任意再利用授權。
