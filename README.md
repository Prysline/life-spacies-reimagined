# 生命空間 II｜非官方概念重建

這是受到 Christa Sommerer 與 Laurent Mignonneau 的互動藝術作品 **Life Spacies II（生命空間 II）** 啟發的個人研究／互動重建專案。

**本專案不是原作的原始碼、官方移植或逐項還原。** 原作完整的造型函式及演算法參數未公開；本專案自行實作可檢視的基因映射與 2D 人工生命模擬。

## 立即體驗（v2 介面；v3 第一階段資料層）

開啟 [index.html](index.html) 即可在桌面或手機瀏覽器離線使用；不需安裝相依套件或連線服務。

功能包括：

- 輸入文字產生生物，並預覽與逐字檢查 11 項基因性狀對應。
- 五種主要生物輪廓及不同的肢體、紋理、色彩等特徵。
- 字元作為食物：生物依其基因食性覓食、消耗能量、死亡、交配與突變。
- 完全空箱與三隻示範生物兩種起始模式、模擬速度、暫停、自動投餵。
- 點選個體查看基因、拖曳複製個體、點擊空白區投放字母。

已開始 v3 第一階段資料層：程式在單次實驗內保存所有出生個體（包含死亡者）的基因與表型、來源、雙親與子代、出生／進食／交配／死亡等結構化事件，並將每次進食移出全域生態紀錄。**完整生物清單、個體詳細檢視、事件 Tooltip、獨立清空飼料及新 RWD 版面仍未實作**，因此目前尚不能在介面中直接檢視上述檔案。完整重置會刪除本次實驗的個體及事件歷史；重新整理頁面也不會保留這些記憶體資料。

## 專案檔案

- `index.html`：**現行程式唯一正式來源**（保留原始 v2 HTML，尚未模組化）。
- `archive/life-spacies-v1.html`：先前 v1 的歷史快照，供比較；不要與現行版本同時維護功能。

往後如需模組化，應先建立來源檔與建置流程，並讓單一可執行 HTML 由正式來源產生；避免直接修改多份版本而造成漂移。

## 規格、文件與版本計畫

[Notion：生命空間 II｜原作研究、互動重建與版本規劃](https://app.notion.com/p/411b4185273f81b6bf45f656c9f3719c)

Notion 依主題區分研究、基因模型、版本現況、v3 需求、RWD 設計、測試與待確認事項。v3 第一階段的資料與實驗邊界請見 [Notion｜10 第一階段資料契約](https://app.notion.com/p/411b4185273f8184adcafdbd949950ef)。GitHub 管理程式碼及修改歷史。**不要把尚未實作的 v3 清單與詳細檢視功能視為已上線。**

## 網站建置與 GitHub Pages

網站公開部署使用 **GitHub Actions**，而不是從儲存庫根目錄直接發布：

1. 現有 `.github/workflows/baseline.yml` 在每次 PR／push 執行 Node.js 基準、產物驗證和 Chromium 回歸測試。
2. 當且僅當 `main` 的 push 測試成功，`.github/workflows/deploy.yml` 收到成功結果後，使用**相同提交 SHA**重新執行 `node scripts/build.mjs`。
3. 僅將 `dist/` 上傳為 Pages artifact 並部署到 `github-pages` 環境。PR 不會部署，測試失敗也不會部署。

目前 `scripts/build.mjs` 會將正式 `index.html` 原樣複製到 `dist/index.html`，並建立 `dist/.nojekyll`。之後拆成 JS／CSS 模組時，只需更新建置腳本，仍由 `dist/` 統一部署，並保留離線單檔 HTML 產出能力。**切勿直接修改 `dist/`；它是被 Git 忽略的建置產物。**

本機檢查：

```bash
node scripts/build.mjs
node --test tests/*.test.mjs
```

**首次啟用須由儲存庫管理者在** [Settings → Pages](https://github.com/Prysline/life-spacies-reimagined/settings/pages) **將 Build and deployment → Source 設成 `GitHub Actions`**。只有 workflow 存在，不能視為 Pages 已啟用。可在 [Actions](https://github.com/Prysline/life-spacies-reimagined/actions) 檢視部署作業；部署成功後預期網站為 `https://prysline.github.io/life-spacies-reimagined/`。以實際成功的 `github-pages` 部署紀錄為準。

## 測試與變更驗證

`main` 的 GitHub Actions 在每次推送與 Pull Request 時執行兩類檢查：

- `tests/baseline.test.mjs`：以 Node.js 檢查 HTML、嵌入式 JavaScript 語法與主要元件。
- `tests/browser_regression.py`：以 Playwright 驅動 Chromium，實際操作 v2 的基因預覽、五種外型、空箱及示範、生成、基因檢視、餵食、暫停、容量上限與響應式排版。
- `tests/browser_ecology.py`：以測試期間的可重現條件驅動**正式生態更新函式**，確認大小寫食性、進食補能、能量耗損、食物過期、兩種死亡原因、交配條件、交叉／突變／冷卻，以及實際滑鼠拖曳複製。測試只在記憶體中加入檢查介面，不修改 `index.html`。
- `tests/browser_records.py`：驗證 v3 第一階段個體檔案與事件儲存、出生來源、死亡後可追溯、進食事件分離、親子連結、拖曳複製與完整重置的語義。

本機執行（需 Python 及 Playwright Chromium）：

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m unittest discover -s tests -p 'browser_*.py' -v
node --test tests/baseline.test.mjs
```

如本機已安裝 Chromium，也可設定 `CHROMIUM_EXECUTABLE` 指向其執行檔。瀏覽器測試會載入正式 `index.html` 的完整文字並執行，**不會修改生產程式**。

**覆蓋範圍限制：** 生態測試使用可重現的人工初始狀態與固定時間步長，已檢查真實的進食、交配與死亡規則，但不等於驗證自然隨機環境中長時間的完整生態演化；觸控拖曳、跨瀏覽器及視覺回歸仍需補強。

## 技術與來源

此重建採用 HTML、CSS、Canvas 與原生 JavaScript。現有公式是自行設計的可追蹤映射，不等於原作 1999 年的完整 3D 網格變形演算法。

- [藝術家官方資料](https://interface.ufg.ac.at/christa-laurent/LifeSpaciesII.html)
- [Life Spacies II 技術論文](https://icat.vrsj.org/ICAT2003/papers/99215.pdf)
- [日本 ICC：Life Spacies 初代作品](https://www.ntticc.or.jp/en/archive/works/life-spacies/)

本儲存庫尚未指定軟體授權條款；公開可見不表示自動授予任意再利用授權。
