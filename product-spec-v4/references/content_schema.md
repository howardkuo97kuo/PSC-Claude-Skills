# content.json 格式

`build_spec.py` 只吃這個 JSON。格式、字體、顏色、頁首頁尾、簽核欄、目錄全部由母版與腳本處理，JSON 只放內容。

```json
{
  "cover": {
    "project_name": "Carter-Hoffmann PUC 10.1\"",
    "model_no": "90LM101C109A1-CH",
    "description": "Promate Midband 10.1\"\nHLUI-Lite HMI",
    "document_no": "",
    "version": "V01",
    "date": "2026/10/01",
    "approved_by": "Howard Kuo",
    "checked_by": "Marius Reyes",
    "prepared_by": "Charlie Wang"
  },
  "revisions": [
    ["01", "2026/10/01", "-", "First release, compiled from department design specifications"]
  ],
  "body": [ ...blocks... ]
}
```

- `description` 的 `\n` 會變成封面欄位內的第二行。
- `document_no` 留空字串 = 尚未取得（交付時要列在疑慮清單）。
- `total_pages` 不用填，腳本依實際頁數自動填入。
- `revisions` 最多 5 列（母版的列數）。
- `approved_by` / `checked_by` / `prepared_by`：簽核人姓名。簽名欄由腳本一律清空（親簽）。

## body 區塊

| type | 欄位 | 說明 |
|---|---|---|
| `h1` / `h2` / `h3` | `text` | 標題文字，**不含編號**。編號、書籤、目錄、換頁由腳本處理。h1 自動另起新頁（分節後第一個標題除外）。 |
| `p` | `text`, `style` | 內文。`style`: `body`（預設）、`lead`（與下一段同頁，用在「Main components:」這類引導句）。 |
| `note` | `text` | 灰色斜體註記，例：`Note:  The two USB 2.0 headers ...` |
| `bullets` | `items` | 項目符號清單。 |
| `image` | `path`, `caption`, `width_cm` 或 `height_cm` | 置中圖片＋自動編號圖說 `Figure n – caption`。只給一邊尺寸時依原比例；超過版面會自動縮小。 |
| `table` | `caption`, `header`, `rows`, `widths`, `align`, `group_first_col`, `band`, `row_height` | 見下方。 |
| `connector` | `ref`, `function`, `part`, `image`, `pins`, `note` | 一個接頭：標題列＋接頭圖（高 2.5 cm）＋ `Table n – <ref> : <function> - <part> Pin Assignment` ＋ pin 表（＋註記）。 |
| `section` | `orient` | `portrait` / `landscape`。之後的內容換到新的分節（新頁）。母版的 2.6 之後是橫向。 |

### table

```json
{"type": "table", "caption": "Display Characteristics",
 "header": ["Item", "Unit", "Specification", "Remark"],
 "widths": [2631, 1206, 4275, 1994],
 "align": ["L", "C", "L", "L"],
 "rows": [["Screen Diagonal", "inch", "10.1", ""]]}
```

- `widths`：相對比例即可，腳本會縮放到版面寬度。
- `align`：每欄 `L` 或 `C`（表頭一律置中）。
- 預設是斑馬紋（隔列淺藍底）。
- `group_first_col: true`：第一欄是分類欄（淺藍底、深藍粗體、上下合併）。同一分類的後續列第一欄填 `""`，就會與上方合併。此時不使用斑馬紋。
- `band: false`：關閉斑馬紋。
- `row_height`：最小列高（twip），缺陷表用 560。
- 儲存格可以是字串（`\n` 分段）或 `{"text": "...", "image": "path", "image_height_cm": 1.3}`（圖在上、文字在下，缺陷表用）。

### connector

```json
{"type": "connector", "ref": "J5 / J6", "function": "USB-A", "part": "614004135023",
 "image": "crops/img-013-020.png",
 "pins": [["1", "5V", "Supply 5 V"], ["2", "USB D-", "Data minus"]],
 "note": "Note:  The two USB 2.0 headers (J5 / J6) on the board can deliver a combined power rating of 3.5 A."}
```

- 每一根 pin 一列，不可用區間（"2-4"）合併。
- 圖片路徑可用相對路徑（相對於 content.json 所在資料夾）。
