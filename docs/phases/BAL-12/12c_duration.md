## 2. 升階持續回合上限 10（B-3W-4）

點數固定的狀態／表面白板配方 13 個 × 種子 1～4，在最低階級組出後逐階升階重配（`retier`）。
- 比例＝預算比例（驗證窗 0.70～1.00）；目標＝最低階組出時的比例（3W-9b 重配維持比例）。
- 實用比例＝比例 × min(持續, 6) ÷ 持續：一般遭遇 4～6 輪，超過的回合帳面算點數、戰鬥裡用不到。
- A 加強度＝升階改加強度不加回合：持續停在 6、每回合強度 ×（持續 ÷ 6），帳面比例不變，實用比例回到帳面。
- B 層數＝施加狀態加層數參數：層數 ⌈持續 ÷ 6⌉、持續 ⌈持續 ÷ 層數⌉（點數 × 層數），列帳面比例。
- 完整 ‰＝3 階這招做成完整技能（+120‰）實際加了多少（持續上限 10 擋住時加不上去）。

| 配方 | 種類 | 狀態／表面 | 階 | 形狀 | 持續 | 比例 | 目標 | 實用比例 | A 加強度（持續、強度） | B 層數（層×持續→比例） | 完整 ‰ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 餘燼（ember_touch） | passive | burning | 1 | self | 3 | 0.80 | 0.80 | 0.80 | - | - | - |
| 餘燼（ember_touch） | passive | burning | 2 | self | 4 | 0.83 | 0.80 | 0.83 | - | - | - |
| 餘燼（ember_touch） | passive | burning | 3 | self | 5 | 0.81 | 0.80 | 0.81 | - | - | 0／4 |
| 凝冰（frost_patch） | active | ice | 1 | cross | 6 | 0.79 | 0.79 | 0.79 | - | - | - |
| 凝冰（frost_patch） | active | ice | 2 | square3 | 7 | 0.77 | 0.79 | 0.66 | 6、×1.17 | 2×4→0.86／2×4→0.87／2×4→0.88／2×4→0.91 | - |
| 凝冰（frost_patch） | active | ice | 3 | square3 | 9 | 0.78 | 0.79 | 0.52 | 6、×1.50 | 2×5→0.85／2×5→0.86／2×5→0.89 | 17／23／64／7 |
| 點燃（kindle） | active | burning | 1 | cross | 4～5 | 0.86 | 0.86 | 0.86 | - | - | - |
| 點燃（kindle） | active | burning | 2 | cross | 5～6 | 0.81 | 0.86 | 0.81 | - | - | - |
| 點燃（kindle） | active | burning | 3 | cross | 6～8 | 0.83 | 0.86 | 0.67 | -／6、×1.33 | -／2×4→0.83／2×4→0.87／2×4→0.88 | 14／17／27／7 |
| 追蹤印記（mark_retort） | reaction | marked | 1 | single | 4 | 0.87 | 0.87 | 0.87 | - | - | - |
| 追蹤印記（mark_retort） | reaction | marked | 2 | single | 5 | 0.85 | 0.87 | 0.85 | - | - | - |
| 追蹤印記（mark_retort） | reaction | marked | 3 | single | 6 | 0.79 | 0.87 | 0.79 | - | - | 2／55 |
| 烙印（mark_target） | active | marked | 1 | cross／single | 4～5 | 0.83 | 0.83 | 0.83 | - | - | - |
| 烙印（mark_target） | active | marked | 2 | cross／single | 5～6 | 0.78 | 0.83 | 0.78 | - | - | - |
| 烙印（mark_target） | active | marked | 3 | cross／single | 6～8 | 0.79 | 0.83 | 0.64 | -／6、×1.33 | -／2×4→0.77／2×4→0.81 | 23／24／33／80 |
| 追蹤印痕（mark_touch） | passive | marked | 2 | self | 3 | 0.83 | 0.83 | 0.83 | - | - | - |
| 追蹤印痕（mark_touch） | passive | marked | 3 | self | 4 | 0.86 | 0.83 | 0.86 | - | - | 0／4／9 |
| 振奮（rally） | active | empowered | 1 | self | 3 | 0.79 | 0.79 | 0.79 | - | - | - |
| 振奮（rally） | active | empowered | 2 | self | 4 | 0.82 | 0.79 | 0.82 | - | - | - |
| 振奮（rally） | active | empowered | 3 | self | 5 | 0.80 | 0.79 | 0.80 | - | - | 14／61／9 |
| 先機標記（scout_mark） | passive | marked | 1 | self | 3 | 0.85 | 0.85 | 0.85 | - | - | - |
| 先機標記（scout_mark） | passive | marked | 2 | self | 4 | 0.88 | 0.85 | 0.88 | - | - | - |
| 先機標記（scout_mark） | passive | marked | 3 | self | 5 | 0.87 | 0.85 | 0.87 | - | - | 0／4 |
| 毒沼（toxic_pool） | active | poison | 1 | cross | 6 | 0.79 | 0.79 | 0.79 | - | - | - |
| 毒沼（toxic_pool） | active | poison | 2 | square3 | 7 | 0.77 | 0.79 | 0.66 | 6、×1.17 | 2×4→0.86／2×4→0.87／2×4→0.88／2×4→0.91 | - |
| 毒沼（toxic_pool） | active | poison | 3 | square3 | 9 | 0.78 | 0.79 | 0.52 | 6、×1.50 | 2×5→0.85／2×5→0.86／2×5→0.89 | 17／23／64／7 |
| 隱身脫離（veil_retort） | reaction | concealed | 1 | self | 5 | 0.81 | 0.81 | 0.81 | - | - | - |
| 隱身脫離（veil_retort） | reaction | concealed | 2 | self | 6 | 0.75 | 0.81 | 0.75 | - | - | - |
| 隱身脫離（veil_retort） | reaction | concealed | 3 | self | 8 | 0.78 | 0.81 | 0.59 | 6、×1.33 | 2×4→0.78／2×4→0.79 | 47／52 |
| 淬毒（venom） | active | poison | 1 | cross | 6 | 0.79 | 0.79 | 0.79 | - | - | - |
| 淬毒（venom） | active | poison | 2 | cross | 8 | 0.82 | 0.79 | 0.62 | 6、×1.33 | 2×4→0.79／2×4→0.83／2×4→0.84 | - |
| 淬毒（venom） | active | poison | 3 | cross | 10 | 0.80 | 0.79 | 0.48 | 6、×1.67 | 2×5→0.77／2×5→0.81／2×5→0.82 | 17／2／7 |
| 毒刺迎擊（venom_retort） | reaction | poison | 1 | single | 6 | 0.81 | 0.81 | 0.81 | - | - | - |
| 毒刺迎擊（venom_retort） | reaction | poison | 2 | single | 8 | 0.84 | 0.81 | 0.63 | 6、×1.33 | 2×4→0.80／2×4→0.84／2×4→0.87 | - |
| 毒刺迎擊（venom_retort） | reaction | poison | 3 | single | 10 | 0.82 | 0.81 | 0.49 | 6、×1.67 | 2×5→0.79／2×5→0.82／2×5→0.85 | 0／4／47／52 |
| 毒牙（venom_touch） | passive | poison | 1 | self | 5 | 0.89 | 0.89 | 0.89 | - | - | - |
| 毒牙（venom_touch） | passive | poison | 2 | self | 6 | 0.83 | 0.89 | 0.83 | - | - | - |
| 毒牙（venom_touch） | passive | poison | 3 | self | 8 | 0.87 | 0.89 | 0.65 | 6、×1.33 | 2×4→0.86／2×4→0.87 | 0／4 |

- 持續到頂（10）的（非控制）8 列，其中帳面比例低於目標 0 列；持續 > 6（帳面有、戰鬥用不到）46／152 列。
- 3 階完整技能加不到 +120‰ 的 52／52 個：ember_touch 0～4、frost_patch 7～64、kindle 7～27、mark_retort 2～55、mark_target 23～80、mark_touch 0～9、rally 9～61、scout_mark 0～4、toxic_pool 7～64、veil_retort 47～52、venom 2～17、venom_retort 0～52、venom_touch 0～4。

