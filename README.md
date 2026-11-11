# 生命空間 II｜非官方概念重建

這是受到 Christa Sommerer 與 Laurent Mignonneau 的互動藝術作品 **Life Spacies II（生命空間 II）** 啟發的個人研究／互動重建專案。

**本專案不是原作的原始碼、官方移植或逐項還原。** 原作完整的造型函式及演算法參數未公開；本專案自行實作可檢視的基因映射與 2D 人工生命模擬。

## 立即體驗（v3 功能整合與響應式版面重構中）

開啟 [index.html](index.html) 即可在桌面或手機瀏覽器離線使用；不需安裝相依套件或連線服務。

功能包括：

- 輸入文字產生生物，並預覽與逐字檢查 11 項基因性狀對應。
- 五種主要生物輪廓及不同的肢體、紋理、色彩等特徵。
- 字元作為食物：生物依其基因食性覓食、消耗能量、死亡、交配與突變。
- 完全空箱與三隻示範生物兩種起始模式、模擬速度、暫停、自動投餵。
- 點選個體查看基因、拖曳複製個體、點擊空白區投放字母。

已開始 v3 第一階段資料層：程式在單次實驗內保存所有出生個體（包含死亡者）的基因與表型、來源、雙親與子代、出生／進食／交配／死亡等結構化事件，並將每次進食移出全域生態紀錄。**目前已加入完整生物名冊與共用四頁籤個體詳情**：存活／死亡／全部篩選、編號與基因搜尋、排序、狀態、出生基因與逐字映射、生命紀錄及親緣跳轉。**全域最近九筆生態紀錄已可透過個體編號開啟同一詳情面板，桌面滑鼠／鍵盤可預覽基因，手機點按可查看摘要再進入詳情**。**全域生態紀錄現在也能展開完整重大事件歷史**，可依出生／交配／死亡篩選，從最新事件起每頁瀏覽 25 筆，舊事件的個體編號仍可開啟基因摘要與詳情。完整歷史直接讀取同一份 `lifeEvents`；每次進食只保留在個體生命紀錄，一般投餵與操作提示仍僅顯示於最近訊息。**已新增「清空所有飼料（保留生物）」按鈕**：只移除養殖箱內字母，保留生物、出生計數、模擬時間、個體檔案與生命事件，且不改變自動投餵開關；若自動投餵仍開啟，稍後可能再次產生食物。**此功能與環境控制中的「立即完全清空養殖箱」不同**。**個體狀態頁已加入共用繪圖的放大外觀預覽與目前行為顯示**：活體依原有覓食／交配選擇規則顯示追逐目標、自由游動、拖曳或暫停；死亡個體依出生基因靜態重建外觀並標示死亡，並非死亡瞬間截圖。**第三階段第一批版面已實作**：桌面左工具／中養殖箱／右名冊，平板保留養殖箱優先，手機優先顯示養殖箱、即時狀態與工具快速入口，名冊可返回養殖箱。**第三階段 3B 第一批已完成手機工具與基因觀察室按需展開**：手機初始收合基因生成、餵食、環境控制與完整基因研究；快速入口會自動展開指定工具。選擇個體時手機使用接近全螢幕的共用詳情面板，具有返回名冊、返回養殖箱與 Esc 關閉；桌面版維持原有三欄和固定詳情。**3B 第二批已加入桌面右欄的可收合個體詳情**：選取個體時展開詳情，同時縮短但保留可捲動名冊；關閉詳情返回名冊，不遮蓋中央養殖箱。**平板名冊也可收合**，收合後養殖箱取得較大寬度；從全域事件開啟生物時會自動重新展開名冊及詳情。實體觸控手勢、大量生物／長歷史驗收仍待後續階段。完整重置會刪除本次實驗的個體及事件歷史；重新整理頁面也不會保留這些記憶體資料。

## 專案檔案

- `index.html`：**現行程式唯一正式來源**（保留原始 v2 HTML，尚未模組化）。
- `archive/life-spacies-v1.html`：先前 v1 的歷史快照，供比較；不要與現行版本同時維護功能。

往後如需模組化，應先建立來源檔與建置流程，並讓單一可執行 HTML 由正式來源產生；避免直接修改多份版本而造成漂移。

## 規格、文件與版本計畫

[Notion：生命空間 II｜原作研究、互動重建與版本規劃](https://app.notion.com/p/411b4185273f81b6bf45f656c9f3719c)

Notion 依主題區分研究、基因模型、版本現況、v3 需求、RWD 設計、測試與待確認事項。v3 第一階段的資料與實驗邊界請見 [Notion｜10 第一階段資料契約](https://app.notion.com/p/411b4185273f8184adcafdbd949950ef)。GitHub 管理程式碼及修改歷史。**v3 第二階段主要功能與第三階段 3A 主要版面已完成；3B 的手機工具／個體詳情，以及桌面右欄詳情、平板名冊收合已實作。3C 觸控與長清單驗收、跨頁保存仍屬後續工作。**

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
- `tests/browser_archive.py`：驗證名冊篩選搜尋、死亡個體基因詳情、四頁籤、雙親／子代連結、養殖箱選取同步、分批個體生命紀錄與小螢幕橫向溢出。
- `tests/browser_loglinks.py`：驗證全域最近事件的出生／交配／死亡編號連結、死亡後可開啟詳情、桌面滑鼠與鍵盤基因摘要、觸控摘要與進入詳情、重置及未知 ID 的安全顯示。
- `tests/browser_global_history.py`：驗證完整重大事件歷史的分頁、出生／交配／死亡篩選、舊事件個體連結、進食與一般操作排除、重置及窄螢幕版面。
- `tests/browser_clear_food.py`：驗證獨立清空飼料後生物／出生／時間／死亡檔案／事件不變、自動投餵開關不變、可自然再投餵，以及與完全重置的差異和手機排版。
- `tests/browser_status_preview.py`：驗證狀態頁活體放大外觀、共用 Canvas 畫法、當前食物／交配目標、暫停與拖曳、死亡個體靜態基因外觀、檢視不修改生態資料及手機寬度。
- `tests/browser_rwd_shell.py`：驗證桌面三欄、平板與手機實際順序、320～1440px 無橫向溢出、手機快速入口與返回、即時數字同步、個體四頁籤、鍵盤導航，以及縮放後生物與基因不變。
- `tests/browser_rwd_disclosures.py`：驗證手機工具預設收合／快速展開、基因觀察室 Canvas 重新計算、個體詳情近全螢幕／四頁籤、返回名冊或養殖箱、Escape 關閉、重置及斷點切換保留資料。
- `tests/browser_rwd_drawers.py`：驗證桌面右欄詳情收合／焦點返回、平板名冊收合增加養殖箱寬度、事件自動開啟詳情、跨斷點保留資料與重置。

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
