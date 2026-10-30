# 固定句型與寫法

目的：不同次、不同專案產出的文字一致。**只替換 `{ }` 欄位，不要改寫句子其他部分。**
句型不適用（例：沒有觸控、沒有板卡）時，依「變化」欄刪掉對應片段；仍不適用時，寫一句新的並在疑慮清單中說明，經使用者同意後補進本表。

## 1. General Description

**產品描述（第一段）**
```
The module is a {size}-inch {application} {form_factor} touch HMI display, integrating a TFT LCD module {bonding} a capacitive touch panel, an embedded single-board computer, and a mechanical {me_assembly} into a single ready-to-mount unit.
```
| 欄位 | 來源 / 寫法 |
|---|---|
| `{size}` | OE Screen Diagonal，例 `10.1` |
| `{application}` | 產品應用。Spec 沒寫時，Middleby 旗下客戶用 `commercial food-service`；其他客戶列在內容清單請使用者確認 |
| `{form_factor}` | 依機構圖面：中框 `midband`、開放式 `open-frame`、有安裝耳 / 法蘭與鎖附孔 `panel-mount`。英文中框一律用 `midband`（Mid-band） |
| `{bonding}` | 依光學規格的貼合方式：Optical bonding → `optically bonded to`；Tape bond / Tape bonding / Air bonding → `tape-bonded to` |
| `{me_assembly}` | 依機構爆炸圖零件表：只有機殼 `chassis assembly`；機殼＋背蓋 `chassis and back cover assembly` |

變化：沒有觸控 → 刪 `touch`、`optically bonded to a capacitive touch panel` 改為 `TFT LCD module`；沒有板卡 → 刪 `an embedded single-board computer,`；沒有機構件 → 刪 `and a mechanical chassis assembly`。

**引導句**：`Main components:`（`p`，style `lead`）

**2.1 Touch Solution**：TE 有 Driver IC 時寫 Driver IC（例 `Microchip maXTouch Series`）；沒有時寫 `PCAP, {structure}, {interface}`（例 `PCAP, Glass-Glass, I2C`）。

**元件條列**（依序，沒有的部門就不列）
```
{size}" TFT LCD Module (LCM), {H} × {V} resolution, {bonding_short} the touch panel
{size}" Projected Capacitive Touch Panel (PCT), {structure} structure, {interface} interface
Embedded system board ({processor} processor), supporting {interfaces}
Mechanical chassis, {form_factor}, {me_parts}
```
- `{bonding_short}`：`optically bonded to` / `tape-bonded to`（同 `{bonding}`）。
- **不寫廠牌**（Yeebo、Orient、Innolux…）：Spec 中的面板 / 觸控廠牌名稱一律不出現在 Product Spec。
- `{structure}` 小寫，例 `glass-glass`；`{interface}` 例 `I2C`。
- `{interfaces}`：EE Introduction 列出的介面，順序 `LCD/touch, Ethernet, RS232/RS485, CAN bus, USB and audio`（沒有的刪掉，最後兩項用 `and`）。
- `{me_parts}`：機構爆炸圖零件表中除了面板、PCB、螺絲、膠帶以外的結構件，用小寫、逗號分隔，例 `EMI cover`、`back cover, EMI cover, sealing gasket`。

## 2. Product Specification

| 位置 | 句型 |
|---|---|
| 2.3.2 引導句 | `The embedded board provides the following connectors. The connector list and pin definitions are summarized below.` |
| 接頭標題 | `{Ref} : {Function} - {Part No.}`（例 `J17 : QSPI - 640456-8`；多個接頭 `J5 / J6 : USB-A - 614004135023`；左右聲道 `J4 (R) / J4-1 (L) : Speaker - ...`） |
| 接頭電流註記 | `Note:  The two USB 2.0 headers ({refs}) on the board can deliver a combined power rating of {current} A.`（`Note:` 後兩個空格） |
| 其他接頭註記 | `Note:  {EE 註記改寫為完整英文句}` |
| 2.3.4 | `PCB dimension: {W} mm × {H} mm.` |
| 2.4 Power-up | `Power-Up / Reset Requirements: the device must be held in RESET (active low) while the digital and analog power supplies ({supplies}) are powering up. The supplies must reach their nominal values before the RESET signal is de-asserted (goes high).` |
| 2.5 檢驗環境 | `Visual inspection is conducted under a light source of {lux} lux, positioned above and between the glass and the inspector. The inspector observes the glass at a viewing distance of {distance}, with an inspection time of {time} per piece, within a viewing angle of {angle} with respect to the normal direction of the glass surface.` |
| 2.7 鎖附扭力 | `Recommended torque: M3 screws, {m3} kgf-cm; M4 screws, {m4} kgf-cm.`（只有一種螺絲就只寫一種） |
| 3 包裝（Spec 沒有的欄位連同前後文字整段省略，例：沒有重量就不寫 Max weight） | `Carton size: {L} × {W} × {H} mm. Max capacity: {n} modules/carton. Max weight: {kg} kg/carton ± {tol}. Pallet: Promate standard pallet, {L} × {W} × {H} mm (pallet weight {pkg} kg ± {ptol} kg). {c} cartons/pallet = {pcs} pcs.` |

## 3. 表格內固定用語

**缺陷判定**（同一項目多條，用 `; ` 連接，小寫開頭）
```
D≤0.15 mm: unlimited; 0.15 mm<D≤0.4 mm: accept 3 pcs (interval of 10 mm); D>0.4 mm: reject
```
缺陷名稱：`Dot / Bubble / BM Dot`、`Line Particle`、`Lens Breakage`、`Printing Sawtooth`、`Cover Glass Crack`、`BM Pin Hole`（Title Case，`CG` 寫成 `Cover Glass`）。

**Pin Description 常用詞**（Spec 原文大寫或縮寫時統一成下列寫法）
| Spec 原文 | 寫成 |
|---|---|
| GROUND / GND | `Ground` |
| Supply 5V / 5V | `Supply 5 V` |
| Data minus (D-) / Data Plus (D+) | `Data minus` / `Data plus` |
| LVDS0 DATA / LVDS0 CLK | `LVDS0 data` / `LVDS0 clock` |
| NC | `NC` |
| CHASSIS GND | `Chassis ground` |

## 4. 數值與單位寫法

| 類型 | 寫法 | 例 |
|---|---|---|
| 尺寸 | `{W} (W) × {H} (H)`；三維加 `× {D} (D) mm` | `254.9 (W) × 167.9 (H)` |
| 解析度 | `{H} × {V}`（去掉 R.G.B.） | `1920 × 1200` |
| 溫度範圍 | `{min}°C ~ {max}°C` | `0°C ~ 70°C` |
| 濕度 | `{min} ~ {max}% RH (Non-condensing)` | `20 ~ 90% RH (Non-condensing)` |
| 電壓 | 數字與單位間空格 | `24 VDC ± 10%`、`3.3 V` |
| 數量 | `× {n}`（× 前後空格） | `RS485 × 2` |
| 乘號 | 一律 `×`，不用 `x` / `*` | |
| 比較符號 | `≤ ≥ < >`，不用 `≦ ≧` | |
| 空值 | `-` | |

## 5. 封面與改版

| 欄位 | 寫法 |
|---|---|
| Description | 兩行：`Promate {Form} {size}"` / `{Product line} HMI`（例 `Promate Midband 10.1"` / `HLUI-Lite HMI`） |
| 第一版 Revision Content | `First release, compiled from department design specifications` |
| 改版 Revision Content | `Updated {章節}: {一句話說明}`，多項用 `; ` |
