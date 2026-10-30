# Decision Record — Carter-Hoffmann PUC 10.1" (90LM101C109A1-CH) Product Spec V01

產出日期：2026/10/13　｜　skill：product-spec-v4

## 來源文件
| 部門 | 檔名 | 版本 / 日期 | 備註 |
|---|---|---|---|
| OE | 90LM101C109A1-CH_Design_Specification_OE_V0.1.pdf | 0.1 / 2026/08/14 | |
| ME | Middleby_CarterHoffmann__Design_SpecificationME-v0_260817.doc | 0.1 / 2026/08/13 | 圖面為 WMF，改用使用者提供的圖 |
| TE | Carter-Hoffmann_10.1_Design_Spec_v2026_08_21_002.pdf | 0.1 / 2026/08/21 | PDF 屬性 Title 殘留「Wunder-Bar AutoSaucer」；封面寫 9 頁，實際 10 頁 |
| EE | PSC_COOK-Lite_EE-Board-Design-Specification_V03_20260722.pdf | V0.3 / 2026/07/22 | 通用板卡 Spec（COOK-Lite / 99EMCOOKLITA0），使用者確認為本專案板卡 |

## 使用者回答（步驟 2）
| 項目 | Spec 上的資料 | 使用者決定 |
|---|---|---|
| Approved / Checked / Prepared By | 無 | Howard Kuo / Marius Reyes / Charlie Wang（簽名欄留白，親簽） |
| OS / Firmware | 無 | Android 9 |
| Application | 無 | Blue Sparq + Vantron BlueSphere |
| 產品照片 | 無 | 使用者提供前 / 後兩張 |
| 記憶體配置 | EE 3.2：eMMC 16/32/64/128 GB；LPDDR4 1/2/4 GB | eMMC 16 GB、LPDDR4 2 GB |
| 操作溫度 | OE 2-3：-20~70°C；TE 1：-20~70°C；EE 3.2：0~70°C | 0°C ~ 70°C |
| 操作濕度 | OE 2-3：20~90% RH；EE 3.2：5~90% RH | 20 ~ 90% RH (Non-condensing) |
| 儲存溫度 | OE 2-3：-30~80°C；TE 1：-30~80°C；EE 3.2：-20~70°C | -20°C ~ 70°C |
| 儲存濕度 | OE 2-3：20~90% RH | 20 ~ 90% RH (Non-condensing) |

## 判斷與處理（非使用者回答，但影響內容）
| 章節 | 處理 | 依據 |
|---|---|---|
| 2.2.2 | OE TDM 與整機兩張光學表數值相同，只放一張 | mapping.md |
| 2.3.2 | J24 在 EE 名稱為「PCT」，pin 內容為 Push Button → 改為「PB」 | EE p21 pin 表 |
| 2.3.2 | J4/J4-1、J5/J6、J8/J9 依 EE 原表合併為一個區塊 | EE p13、p14 |
| 2.1 | Product Dimension 258.50 × 171.50 × 30.80 mm 沿用 V01 成品（ME 外形圖） | V01 成品 |
| 3 | 包裝數據取自 ME 包裝圖 NOTE | ME p7 |

## 未完成
- Document No.：尚未取得
