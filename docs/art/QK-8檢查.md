# QK-8 驗收（NPC 與人形敵人部件、#145 外觀資料）

美術 PM，2026-11-07。

- 報告：`docs/phases/PhaseQK-8報告.md`（origin/main `532a3903`）。依據：`docs/art/QK移植需求.md` 開頭第 2 版定案、第 8.5 節。
- 看法：`docs/art/shots/qk8/` 62 張並排＋實機，由唯讀審查 agent 原尺寸看過（扣掉規格和樣張不同、以規格為準的部分）。

**結論：退回，必修 1、小修 4。** 其餘四面分畫、新部件前後圖層、四指握法、赤膊內線與拳頭圈都對；QK-3 第 1 條補拍（長手套、臂環在西向拿盾手上）通過。

## 1. 必修

1. **疤面的刀沒畫出來**（`54_npc_scarface` 四方向兩手空空，地圖紙娃娃也一樣）：content 是 `main_hand: {kind: saber}`，`client/src/render/appearance.ts:92` 的 `KNOWN_KINDS.main_hand` 沒有 `saber`，被濾掉。清單與別名加 `saber`（或 content 改 `sword, form: curved`），並加測試「疤面有主手」。

## 2. 小修

1. 護法武僧畫成灰色拳套（`05_monk_sect_warrior_monk`）：照美術 PM 決定改空手拳頭；念珠顏色照樣張。
2. 長袍邊色只讀 `look.trim`、沒讀 `gear.body.trim`：霧鎖真人金邊、小蓮竹青邊變灰。改成 `look.trim ?? it?.trim ?? 預設`（樣張也會一起修）。
3. 頭目外光並排圖（`16`、`21`、`26`、`11`）整格被顏色鋪滿、上緣鋸齒：先在戰場實機確認頭目外光沿輪廓，再重拍這幾張。
4. 補拍：玩家戴頸飾（吊牌、符牌、骨符）四方向；霧鎖真人實機（霧渡鎮 NPC 或頭目戰）；確認 `qk8_battle_cliff_bandits_1600.jpg` 約 (1118,410)、`qk8_battle_sect_1600.jpg` 約 (1030,230) 兩個半透明灰白敵人是狀態效果（霧隱、隱匿、高處淡出）不是畫錯。

補完只看這幾張就結案。
