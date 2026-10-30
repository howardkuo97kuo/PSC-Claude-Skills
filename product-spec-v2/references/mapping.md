# 來源 → Product Spec 對照表

依據：Carter-Hoffmann PUC 10.1"（90LM101C109A1-CH）V01 成品與其四份 Design Spec。
新專案的 Spec 段落名稱可能略有不同，依「內容」對應，不要只看標題。

原則：
- **整份文件只放產品（整機）層級的資訊。** 模組 / 零件層級的內容一律不放（見最下方排除清單）。
- 所有固定文字、數值與單位寫法依 `phrases.md`。
- 文件只有：封面、Record of Revision、Contents、1. General Description、2. Product Specification、3. Package。**不放 Appendix / Source Documents、Material List、Software 獨立章節。**

---

## 封面

| 欄位 | 來源 | 規則 |
|---|---|---|
| Project Name | OE / ME / TE 封面的 Project Name | 三份不一致時列入提問 |
| Model No. | 同上 Model No.（完整型號，不加說明文字） | EE 是通用板卡時型號會不同，不採用 EE 的 |
| Description | 兩行：`Promate {型態} {size}"` / `{產品線} HMI`（`phrases.md` 第 5 節）。OE / TE 封面若已寫好（例：`Promate Midband 10.1" HLUI-Lite HMI - Optical Design Spec`），去掉部門字尾直接用；沒有產品線名稱時步驟 2 請使用者提供 | 母版為 `Promate Midband 10.1"` / `HLUI-Lite HMI` |
| Document No. | 不從 Spec 取 | **留空**，交付時列為「尚未填寫」，不用提問 |
| Version | 新文件 V01；改版則遞增 | |
| Date | 產出當天 | |
| Approved / Checked / Prepared By | 不從 Spec 取 | **每次提問**，只填姓名。簽名欄一律留白（親簽），不放簽名圖 |

Record of Revision 第一版內容：`01 / <date> / - / First release, compiled from department design specifications`

---

## 1. General Description

- 產品描述一段、`Main components:`、元件條列：**依 `phrases.md` 第 1 節的句型填空**，不要自由改寫。
- 欄位值取自四份 Spec（尺寸、解析度、觸控結構與介面、處理器與介面、機構件）。`{application}` Spec 沒寫時依 phrases.md 規則，並在內容清單標出。
- Figure 1 / 2：**產品實體照片（前 / 後）— 一律向使用者索取**，Spec 內沒有。

## 2. Product Specification

### 2.1 System Overview — `Table – System Key Features Overview`
表頭 `Category | Key Features`，widths `[3017, 7089]`。

| Category | 來源 |
|---|---|
| Display Solution | OE：`TDM, <size>", <H × V>` |
| Touch Solution | TE General Information 的 Driver IC |
| Processor / MCU | EE Hardware Features |
| Memory | EE Hardware Features（**實際配置要問**，EE 常列多個選項） |
| I/Os | EE Hardware Features 彙整 |
| Power Supply | EE Input Power Voltage |
| OS / Firmware | **一律提問** |
| Application | **一律提問** |
| Operating Temp. & Humidity | 各份 Spec 的數值**全部列出來提問**（例：OE、TE 為 -20~70°C，EE 為 0~70°C） |
| Storage Temp. & Humidity | 同上 |
| Product Dimension | ME Outline Drawing 外形尺寸（W × H × D） |

### 2.2 Display & Optical Characteristics
**2.2.1 Display Characteristics**（OE 2-1）— 表頭 `Item | Unit | Specification | Remark`，widths `[2631, 1206, 4275, 1994]`，align `L C L L`。
- 取：Screen Diagonal、Outline、Active Area、Pixels、Pixel Pitch、Pixel Arrangement、Display Mode、Support Color。
- `Surface Treatment` 與 `Hardness` 合併為一列 `Cover Glass Hardness`。
- 不取：Weight（模組重量）。
- 尺寸寫法統一 `254.9 (W) × 167.9 (H)`；`1920 × R.G.B. × 1200` 改為 `1920 × 1200`。

**2.2.2 Optical Characteristics**（OE 2-2）— 表頭 `Item | Unit | Min. | Typ. | Max.`，widths `[3700, 1200, 1735, 1735, 1736]`，align `L C C C C`。
- OE 有 TDM 與整機兩張表：**一律用整機（90-level）那張**，不提問。兩張數值不同時，在疑慮清單列出差異。
- OE 某欄位沒有值（例：Typ. 空白）→ 填 `-`，不自行補值。
- OE 欄位內容明顯錯置（例：Pixel Arrangement 寫成解析度）→ 不放該列，列入疑慮。
- 刪除 ★ 等 DV 標記。Viewing Angle 寫成 `Viewing Angle – Horizontal (Right/Left), CR≥10`，Min/Typ 以 `80 / 80` 形式。

### 2.3 Embedded Board Specification
**2.3.1 Hardware Features**（EE 3.2）— 表頭 `Category | Item | Specification`，widths `[2959, 2346, 4801]`，`group_first_col: true`。
- Memory 只寫實際配置（與 2.1 一致）。
- **不放** Operation Environment 三列（已移到 2.1）。

**2.3.2 Pin Assignment**
- 引導句：`The embedded board provides the following connectors. The connector list and pin definitions are summarized below.`
- Figure：Connector Location Diagram（EE 3.3 的接頭位置圖）。
- `Table – Connector List`（EE 3.5）：表頭 `No. | Ref. | Function | Equivalent Connector`，widths `[767, 1535, 2959, 4845]`，align `C L L L`。Function 改為一般大小寫（`POWER IN` → `Power In`，`USBA` → `USB-A`）。
- 接頭名稱與功能**一律照 Connector List**；Pin Assignment 標題與清單不一致時照清單，不提問，列入疑慮。
- 每個接頭一個 `connector` 區塊（EE 3.6）：
  - 圖：`extract_sources.py` 自動裁切的接頭圖（`crops/`），裁完用 `crops_contact.jpg` 檢查。
  - 同一張 EE 表涵蓋多個接頭時合併成一個區塊：`J4 (R) / J4-1 (L)`、`J5 / J6`、`J8 / J9`。
  - 每一根 pin 獨立一列，Pin Name 照 EE 原文，Description 改為一般大小寫的英文（`GROUND` → `Ground`）。
  - EE 圖下方的 (※) 註記 → `note`，寫成 `Note:  ...`，並把適用的接頭寫進句子。
  - **名稱與內容不符時要修正並列入疑慮**（例：EE 的 J24 叫「PCT」，但 pin 是 Push Button → 改為 `PB`）。

**2.3.3 Function Block** — EE 3.1 的 Function Block 圖。
**2.3.4 Connector & PCB Schematic** — 一行 `PCB dimension: <W> mm × <H> mm.`（來自 EE 尺寸）＋ PCB Top / Bottom Placement 兩張圖（EE 3.7）。不放 EE 3.4 PCB Dimension 圖。

### 2.4 CTP Touch Panel Specification（TE）
- `Touch Panel General Information`：表頭 `Item | Contents`，widths `[3288, 6818]`。
  - 固定放：Sensor Structure、Surface Hardness、Ball-Falling Test、Resolution、Screen Size、Interface Type、Driver IC、Connector (Wafer Part)、Connector (Mating Housing Part)——TE 有哪些就放哪些，沒有的不補。
  - **不放**：溫度兩項（零件層級）。
  - TE 有上述以外的項目（例：Touch Count Max、I2C Slave Address、Origin of Coordinate）→ 步驟 2 列出，請使用者回答放或不放；放的話接在固定項目後面。
  - 項目名稱統一成 Title Case（`Ball-falling Test` → `Ball-Falling Test`），數值格式依 `phrases.md`（`1024*600 Dots` → `1024 × 600 Dots`）。
- `Touch Panel Electrical Characteristics`：**只放** `Power Supply Input Voltage` 與 `I/O Signal Voltage` 兩列，其他列（ripple、VIH/VIL、電流…）一律不放、不提問。表頭 `Item | Symbol | Min. | Typ. | Max. | Unit`，widths `[3288, 1535, 1315, 1315, 1315, 1338]`，align `L C C C C C`。TE 註記（※）不放。
- `CTP Interface Description`：**固定兩欄** `Interface No. | Name`，widths `[3288, 6818]`，align `C L`。TE 有更多欄（I/O、Description）也只取這兩欄，不提問。
- Power-Up / Reset：`phrases.md` 句型＋時序圖（TE 有圖才放）。

### 2.5 Touch Panel Defects & Acceptance（TE）
- 檢驗環境一段：TE 有才放（`phrases.md` 句型）；沒有就不放，也不自行補。
- `Defects and Acceptance Standards`：表頭 `Defect Item | Inspection Criteria`，widths `[2600, 7506]`，align `C L`，`band: false`，`row_height: 560`。
  - 缺陷項目依 TE 原表，名稱 Title Case；同一項目的多條判定合併成一格（`phrases.md` 第 3 節寫法），`Accept` / `Reject` 寫成小寫 `accept` / `reject`。
  - TE 有示意圖才放圖（`crop_page.py --box` 裁切）。
  - TE 有多套標準（例：Industrial / Non-industrial）→ 步驟 2 請使用者指定一套。
  - TE 表下方的通用註記（例：兩缺陷間距 ≥ 10 mm）→ 放成表格下方的 `note`。

### `section` → landscape

### 2.6 Mechanical Outline Drawing — ME 1（`Product Outline Drawing`）
### 2.7 Product Explode Drawing — ME 2 ＋ 圖下一行 `Recommended torque: M3 screws, 4 ± 0.3 kgf-cm; M4 screws, 6 ± 0.5 kgf-cm.`（ME 3）

## 3. Package (Air / Sea)
- 標題依 ME 實際有的包裝方式：只有空運 `Package (Air)`；只有海運 `Package (Sea)`；兩種都有用 `Package`，底下兩個 h2：`Package (Air)`、`Package (Sea)`。
- 每種包裝：一段文字（`phrases.md` 第 2 節包裝句型，從 ME 包裝圖的 NOTE 讀出 Carton size、Max capacity、Max weight、Pallet 尺寸與重量、cartons/pallet = pcs）＋包裝圖，圖說 `Package (Air)` / `Package (Sea)`。

---

## 排除清單（產品層級規則）

以下內容即使 Spec 有，也**不放**：

| 來源 | 內容 | 原因 |
|---|---|---|
| OE | Absolute Ratings of Environment（TDM 絕對值） | 模組層級 |
| OE | Reliability test criteria | 模組層級 |
| OE | Material list、SAP DOC、MOQ、TDM Drawing 編號 | 內部採購 / 零件資訊 |
| OE | Weight（TDM） | 模組層級 |
| TE | Operating / Storage Temperature | 零件層級 |
| TE | VIH / VIL / VOH / VOL | 零件層級電氣特性 |
| TE | External Dimensions、Mechanical Drawing | 零件層級 |
| TE | Reliability Test、Precautions | 零件層級 |
| EE | Operation Environment（移到 2.1，不在 2.3.1 重複） | |
| EE | PCB Dimension 圖、Summary / Document Control / Revision History | |
| 全部 | 各部門的封面、核准人、版本紀錄 | |

全文（含註記）**不可出現** OE / EE / ME / TE、Design Spec、來源檔名。

## Spec 中出現本表沒有的內容時

新的章節、新的規格類別（例如 Audio 規格、EMC、IP 等級、Sea 包裝、第二種 OS 配置）→ **在一次提問中列出**，附上 Spec 原文與出處，問使用者是否要加入本次 Product Spec。不要自行決定放或不放。
