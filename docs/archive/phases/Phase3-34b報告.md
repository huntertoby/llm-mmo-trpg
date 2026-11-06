# Phase 3-34b 報告：隨機組合器種子 966 做不出合格技能

## 現象

`TRPG_FULL=1 pytest -m ""` 跑 `test_one_thousand_seeds_are_all_valid_and_spread_out` 與
`test_one_thousand_skills_pass_everything_and_the_summary_is_reproducible`（兩者標 slow，平常不跑）失敗：
種子 966「50 次重抽都做不出合格技能（階級 5、rare、control、weapon）」。

## 原因

1. 50 次嘗試全部是 `Retry`：38 次是強度調整（`tune`）到不了預算窗（比例遠低於 0.75，常見 0.05–0.2），
   12 次是 `delayed_damage` 只能用在法術技。
2. 控場骨架的核心原語有一批「沒有旋鈕」的效果（`raise_terrain`、`lower_terrain`、`dispel`、`create_obstacle`、
   `steal_buff`、`reveal`、`create_surface`），附帶效果只有占比 ≤ 40% 的傷害。階級 5 的預算很大，
   這類核心怎麼調都到不了 0.75，單次成功率只有約一成（階級 5／rare／control／weapon 掃 60 個種子，
   平均約 10 次才成功），50 次全滅的機率約 0.5%，一千個種子中就會碰到。
3. 這是長期存在的低成功率，不是新邏輯錯誤：種子 966 的亂數串流剛好被 3-33e1 改動。

## 開始壞的 commit

`1bd8b7a`（feat: add 6 summons, fill infusion keywords to 10, rework war totem (3-33e1)），以
`git bisect`（good = `172027d`）找出。該 commit 新增狀態與關鍵字資料，改變了組合器抽選池，使種子 966
的重抽串流落到全部失敗。

另外 `test_skill_fuzz` 的 slow 測試還有一個舊的過期斷言：要求「所有啟用的骨架都抽得到」，但
`consume_status`（3C-3b）與 `summon`（3D-4a）是 `_HAND_WRITTEN_ONLY`，隨機組合器本來就不產生，
所以這個測試在第一個問題修好後仍會失敗。

## 修法

- `src/trpg/skillgen/random_composer.py`：`MAX_ATTEMPTS` 由 50 提高到 100；原本用
  `MAX_ATTEMPTS // 2` 決定「前半重抽帶變奏」，改為獨立常數 `VARIANT_ATTEMPTS = 25`，
  所以已成功的種子（含帶變奏的）產物完全不變，只有原本會失敗的種子會用到第 51 次之後的重抽。
- `tests/sim/test_skill_fuzz.py`：骨架覆蓋斷言排除手寫專用骨架（`consume_status`、`summon`），
  其餘門檻（`max(counts) <= 400`、種子數、可重現）不變。
- 沒有改任何測試門檻、跳過種子或刪測試。快照不受影響。

## 後續建議（待 PM 決定）

根本改善是讓「沒有旋鈕的控場核心」在高階時搭配有旋鈕的附帶效果或從核心池剔除，以降低浪費的重抽。
這會改變多數控場種子的產物與快照，所以本次未做。

## 驗證

`TRPG_FULL=1 uv run pytest -q -m "" -n 4 tests/skillgen/test_random_composer.py tests/sim/test_skill_fuzz.py`：57 passed。
