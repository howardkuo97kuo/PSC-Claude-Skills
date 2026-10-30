---
name: product-spec-v4
description: 將硬體專案 O/M/E/T 四份 Design Specification 彙編成 Promate 正式 Product Specification .docx（以 Carter-Hoffmann PUC 成品為母版，格式完全沿用）。僅在使用者訊息中明確出現「/product-spec-v4」時觸發；提到 Product Spec、產品規格書但沒有這個字串時，一律不要觸發。
---

# Product Specification v4

把 OE（光學）、EE（板卡）、ME（機構）、TE（觸控）四份 Design Spec 彙編成一份**產品層級**的 Product Specification。

- 格式：`assets/master.docx`（Carter-Hoffmann PUC 10.1" V01 成品）就是模板。字體、標題、表格配色、頁首頁尾、封面、簽核欄、目錄樣式全部從母版複製，**不要手動排版，也不要用其他方式重建格式**。
- 內容規則：`references/mapping.md`（來源 → 章節對照、產品層級排除清單）。
- 固定句型與寫法：`references/phrases.md`（所有固定文字只填空、不改寫）。
- JSON 格式：`references/content_schema.md`。
- **可重現**：每份 Product Spec 都附一個「決定紀錄」zip（`content.json` ＋ `decisions.md` ＋ 圖片）。同樣的 RD 檔案配上同一份紀錄，重產結果完全相同；RD 檔案有變動時，只重新處理變動的部分。

## 流程總覽

```
0 檢查決定紀錄 → 1 讀取與比對 → 2 一次提問（等回覆）→ 3 內容清單確認（等回覆）
→ 4 產出與自動驗證 → 5 列出疑慮（等回覆）→ 6 交付（含決定紀錄）→ 7 通用規則回寫
```

每個「等回覆」都是停下來等使用者，不要在同一則回覆裡繼續往下做。使用者若說「直接做」或已預先回答，就跳過該次等待。

---

## 0. 檢查決定紀錄

使用者有附上之前的決定紀錄（`*_record.zip`）時：

```bash
python3 scripts/decision_record.py unpack <record.zip> <work>
python3 scripts/decision_record.py check <work>/content.json <OE> <ME> <EE> <TE>
```

- **全部 SAME**：RD 檔案與上次完全相同。直接用 `<work>/content.json` 進入步驟 4 重產，不再提問、不重新判斷。步驟 3 只需告訴使用者「來源與上次相同，將依紀錄重產」，使用者沒有要改的就繼續。
- **有 CHANGED / NEW / MISSING**：只對變動的檔案做步驟 1；比對新舊內容，找出受影響的欄位。**未受影響的欄位沿用紀錄中的值與文字，一個字都不改。** 步驟 2 只問變動帶來的問題，步驟 3 的內容清單只列有變動的欄位。若內容有變，Version 遞增並新增 Record of Revision 一列。
- 使用者說「跟上次一樣再做一次」但沒有附紀錄：先請使用者提供上次交付的 `*_record.zip`。沒有紀錄時，說明結果可能與上次不同，再照完整流程進行。

使用者提供的是上一版 Product Spec .docx（沒有紀錄）：用 `scripts/spec_to_json.py` 轉成 content.json 當作起點，其餘同上。

## 1. 讀取與比對

1. 讀 `references/mapping.md`、`references/phrases.md` 和 `references/content_schema.md`。
2. 執行：
   ```bash
   python3 scripts/extract_sources.py <work>/ext <OE> <ME> <EE> <TE>
   ```
   每份文件會得到 `text.txt`、頁面圖 `pages/`、內嵌圖 `images/`、`contact.jpg`；EE 另外有自動裁切的接頭圖 `crops/` 與 `crops_contact.jpg`。
   EE 兩種格式都支援：接頭圖與 pin 表在同一張圖（自動切出圖的部分），或接頭圖與 pin 表是分開的圖（保留接頭圖）。子板（AC/DC、Thermal…）的接頭圖也會出現在 crops，依步驟 2 的決定取用。
3. 讀每份的 `text.txt`；文字抽不出來的部分（EE pin 表是圖片、ME 圖面）看 `pages/` 頁面圖。EE pin 表逐張看圖抄寫，**每一根 pin 都要核對**。
4. 打開 `crops_contact.jpg` 確認每張接頭圖完整、沒裁到相鄰內容、數量等於 pin 表數量。
5. **判斷四份文件是否屬於同一個產品**：比對封面 Project Name / Model No.、處理器、尺寸、接頭。以下狀況一律在步驟 2 提出：
   - 型號或專案名稱不一致（例：EE 是通用板卡 Spec，專案名 / 型號不同）
   - 檔案屬性（`pdfinfo` 的 Title）殘留其他專案名稱
   - 封面 Total Pages 與實際頁數不符
6. **圖面能不能用**：
   - ME 是 .doc / .docx 且圖面為 WMF / EMF 向量圖時，這個環境無法正確轉圖（LibreOffice 會壓扁）。→ 在步驟 2 請使用者提供 **ME 的 PDF 版**（Word「另存 PDF」即可）。
   - 向量圖用 `scripts/crop_page.py` 從 PDF 頁面裁切（ME 圖面常是橫放在直式頁面上，用 `--rotate cw`）。腳本會自動偵測工程圖外框並裁到框線，不會帶到頁首標題與頁尾。裁完一定要看圖確認。
7. 依 `mapping.md` 在腦中整理每個欄位的值與出處，同時收集所有需要使用者決定的事項。

## 2. 一次提問（停下來等回覆）

所有問題放在**同一則訊息**，問完就停。

### 每一題的格式（固定）

```
**<題號>. <題目>**
- <來源文件與章節>：<Spec 原文 / 數值>
- <來源文件與章節>：<Spec 原文 / 數值>
**請回答：**<下列三種之一>
**不確定時：**<依下方預設規則，寫出會怎麼處理>
```

- **請回答**只能是三種，而且要寫得讓人一看就知道要做什麼：
  1. 「請提供 ___」（例：請提供三位簽核人姓名）
  2. 「請從上面的數值中指定一個（或填其他值）」
  3. 「請回答放或不放」
- 不用選擇題，不給建議答案；只列 Spec 原始資料，使用者不用回去翻文件。
- **不需要使用者決定的事項不放進提問**：已有明確規則可處理的（例：光學取整機那張表、名稱照 Connector List）、純粹告知的（例：Spec 內的錯字、版本日期不符、與產品無關的註記）→ 依規則處理，放到步驟 5 的疑慮清單。
- 題目依「必須提供 → 指定數值 → 放或不放」排序，同類放一起。

### 每次必問
- Approved By / Checked By / Prepared By：請提供姓名（只填姓名，簽名欄留白親簽）。
- OS / Firmware、Application：請提供。
- 產品實體照片（前 / 後）：請提供。
- 環境溫濕度（操作、儲存）：列出每份 Spec 的數值，請指定。
- EE 只列選項的配置（記憶體容量、標示 Optional 的介面）：列出選項，請指定實際配置。
- 步驟 1 發現需要使用者處理的事（例：ME 需要 PDF 版、上傳的檔案不是本專案）：請提供。

### 有才問
- Spec 中有、但 `mapping.md` 沒有對應位置的內容或新類別（例：新的規格項目、子板章節、多套缺陷標準、Sea 包裝）→ 附原文與出處，請回答放或不放（多套標準時請指定一套）。
- 同一項目在不同 Spec 數值不同、或同一 Spec 有多個候選值，**而且沒有明確規則可決定** → 全部列出，請指定一個。

### 使用者回答「不確定」或沒有回答時的預設規則

| 項目 | 預設處理 | 疑慮清單 |
|---|---|---|
| 環境溫濕度 | 各份 Spec 中範圍最窄的（溫度與濕度分別取） | 列出 |
| Project Name | 光學規格封面的 Project Name | 列出 |
| Model No. | 整機型號（光學 / 機構規格共同的 90 開頭型號） | 列出 |
| 封面 Description | 第一行 `Promate {型態} {size}"`，型態依機構圖面判斷；第二行用光學規格封面 Description（去掉廠牌名稱） | 列出 |
| 記憶體 / Optional 介面 | 照 Spec 原文寫出全部選項 | 列出，標明待確認 |
| 多個候選值 | 取整機層級的數值；同層級時取版本較新的文件 | 列出 |
| 放或不放（新內容） | 不放 | 列出 |
| 簽核人、OS、Application | 留空 | 列出，標明待補 |
| 產品照片 | 不放 Figure 1 / 2，第 1 章只有文字 | 列出，標明待補 |

**不要問：** Document No.（留空，交付時說明尚未填寫）、格式相關問題、已在 `mapping.md` 有明確規則的取捨。

## 3. 內容清單確認（停下來等回覆）

收到回答後，產出 .docx **之前**，先給使用者一份內容清單：

- 依章節列出每個欄位的值與出處（文件 + 章節），例：`Contrast Ratio | 800 / 1000 / - | 光學規格 2-2（整機）`。
- 接頭部分不用逐 pin 列出，列「接頭清單＋每個接頭的 pin 數＋做過的修改」（合併、改名、改寫的描述）即可。
- 標出：採用使用者回答的項目、依排除清單刪除的內容（一行帶過）、留空的欄位。
- 用表格呈現，方便掃讀。

使用者確認或修改後才進入步驟 4。

## 4. 產出與自動驗證

1. 把確認後的內容寫成 `<work>/content.json`（格式見 `content_schema.md`；圖片用相對路徑放在 `<work>/` 底下），並記錄來源檔案指紋：
   ```bash
   python3 scripts/decision_record.py stamp <work>/content.json <OE> <ME> <EE> <TE>
   ```
   同時寫 `<work>/decisions.md`（格式見 `references/decisions_example.md`）：來源文件表、使用者回答（每題附 Spec 上的原始資料）、非使用者回答但影響內容的判斷（合併、改名、取捨、句型無法套用時的新寫法）、未完成事項。
2. 產出：
   ```bash
   python3 scripts/build_spec.py <work>/content.json <work>/<檔名>.docx
   ```
   腳本會自動：套母版、重建目錄（超連結＋書籤）、轉 PDF 找出每個標題所在頁、回填目錄頁碼與封面 Total Pages，直到頁碼穩定。
3. 驗證：
   ```bash
   python3 scripts/verify_spec.py <work>/<檔名>.docx --render <work>/render
   ```
   - **FAIL 必須修正後重跑**（目錄連結、頁碼、圖表編號、接頭缺表、出現部門名稱）。
   - **WARN / INFO 逐條判斷**，屬實的列入步驟 5 的疑慮。
4. 看 `render/contact.jpg` 全部頁面，再打開封面、目錄、每個 h1 / h2 起始頁、所有圖片頁的單頁圖，確認：版面沒有大片空白、圖沒被裁切或變形、表格沒有跨頁斷在表頭、橫向頁正確。
5. 自己再讀一次全文，檢查：
   - 固定文字是否完全照 `phrases.md` 的句型，數值與單位是否照第 4 節寫法
   - 2.1 總覽與各章節數值是否一致
   - 同一數值在不同章節的寫法是否一致（單位、空格、× 符號、大小寫）
   - 英文是否通順、有無直接照抄 Spec 的中式英文或錯字
   - 有無殘留的零件 / 模組層級內容
   - 圖說與圖片內容是否相符

檔名：`PSC_<Customer>-<Project>_Product-Spec_V<NN>_<YYYYMMDD>.docx`（例：`PSC_Carter-Hoffmann-PUC_Product-Spec_V01_20261001.docx`）。修改後重產時，在工作資料夾用新檔名（`_r2`、`_r3`），不要覆寫已交付的檔案。

## 5. 列出疑慮（傳檔前，停下來等回覆）

產出後、**傳檔之前**，用一則訊息列出所有疑慮，然後停下來等使用者回覆：

- 不用選擇題。每條寫：問題是什麼、在哪一節、各來源怎麼寫、我目前怎麼處理、建議怎麼改。
- 分類列出：數值衝突、前後不一致、語句不通順（附原句與改寫）、有疑慮的資料、未填欄位（Document No.）、我做的假設。
- 沒有疑慮時也要明說「沒有發現衝突或疑慮」，並問是否直接交付。

使用者回覆後：修改 → 重跑步驟 4 的產出與驗證 → 進入步驟 6。使用者回「直接傳」→ 照建議改完後交付。

## 6. 交付

1. 打包決定紀錄（使用最終版的 content.json 與 decisions.md）：
   ```bash
   python3 scripts/decision_record.py pack <work>/content.json <work>/decisions.md <work>/<docx 檔名去副檔名>_record.zip
   ```
2. 用 SendUserFile 一次傳 .docx 與 `_record.zip`（display: attach）。
3. 一兩句說明：總頁數、Document No. 尚未填寫、其他仍待確認的事項（若有），並提醒「請把 record.zip 和 Product Spec 放在一起，之後重產或改版時一起提供」。不要重述內容。

## 修改時的固定規則

- **章節結構調整**（搬動小節、合併、拆分、改層級）：動手前先問清楚使用者要的最終層級結構，不要自己猜一個結構就開始搬。
- **使用者貼上的範例表格只參考格式**：內容數字一律回到 Spec 原文取得對應的數字，不可照抄範例裡的數字。
- 以上兩點在步驟 2～5 的任何階段都適用。

## 7. 通用規則回寫

使用者在任何步驟提出修正時，判斷是否為**通用規則**（下一個專案也適用，例：某類內容一律不放、某欄位寫法、某種圖的處理方式）：

- **專案特有**的修正：只改這次的內容，不動 skill。
- **通用規則**：先問使用者「這條要不要寫入 skill」，同意後才修改 `SKILL.md` / `references/mapping.md` / 腳本，並提供更新後的 skill 檔案給使用者安裝。
- 修改腳本後，用 `scripts/spec_to_json.py assets/master.docx <dir>` 轉出母版內容，再用 `build_spec.py` 重建、`verify_spec.py` 驗證，確認母版仍能完整重現（0 FAIL）。

---

## 腳本一覽

| 腳本 | 用途 |
|---|---|
| `extract_sources.py` | 四份 Spec → 文字、頁面圖、內嵌圖、EE 接頭圖自動裁切 |
| `crop_page.py` | 從 PDF 頁面裁切向量圖（ME 圖面、TE 缺陷示意圖），可旋轉 |
| `build_spec.py` | content.json ＋ 母版 → .docx，自動目錄與頁碼 |
| `verify_spec.py` | 交付前檢查（目錄、頁碼、編號、接頭、用詞、層級、與母版格式一致性），可輸出頁面圖 |
| `spec_to_json.py` | 既有 Product Spec .docx → content.json（改版時從上一版開始；也用於回歸測試） |
| `decision_record.py` | 決定紀錄：`stamp` 記錄來源指紋、`check` 比對新舊 RD 檔案、`pack` / `unpack` 打包與還原 |

## 改版（已有上一版 Product Spec）

使用者提供上一版 Product Spec 時：先 `spec_to_json.py` 轉成 content.json，比對新的 Design Spec 找出差異，步驟 2 只問差異與新增項目，步驟 3 的內容清單只列有變動的欄位。Version 遞增，Record of Revision 新增一列（Page Affected 填有變動的章節頁碼，Content 簡述變更）。
