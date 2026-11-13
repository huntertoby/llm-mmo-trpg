"""大世界的存檔格式（Phase 5A-2；``docs/phases/Phase5計畫.md`` 2.5）。

| 資料 | 格式 |
|---|---|
| 世界快照 | ``trpg-world/4``（一個 JSON 物件，:class:`~trpg.world.state.WorldState`） |
| 角色 | ``trpg-char/15``（一角色一個 JSON 物件，:class:`~trpg.world.state.CharacterState`） |
| 世界動作日誌 | ``trpg-wlog/10``（JSON Lines：第一行 ``{"format": "trpg-wlog/10"}``，之後一行一筆
  :class:`~trpg.world.replay.WorldLogEntry`） |

JSON 一律排序鍵、UTF-8 不跳脫，同樣的狀態得到逐字相同的檔案。讀檔時 ``format`` 不認得就拒絕
（:class:`~trpg.world.errors.WorldSaveFormatError`）。寫檔走暫存檔＋原子改名（:func:`write_atomic`）。

**舊格式（Phase 6B-2）**：

- ``trpg-char/1`` 照讀，讀進來就是 ``trpg-char/2``（只多了選填欄位）。
- ``trpg-wlog/1`` 照讀，但那些紀錄是舊規則寫的（6B-2 起，有實地地圖的地點不能 ``travel``），
  **規則已變、不能重播**（同 ``LOG_FORMAT`` 遞增時的處理）。下一次寫回時標頭改成 ``trpg-wlog/2``，
  另記 ``stale_through``（最後一筆舊紀錄的序號）與 ``stale_zh``；重播只能從那之後開始
  （:attr:`WorldLog.stale_through`）。

**Phase 6C-1**：``trpg-char/2`` 照讀（只多了選填欄位 ``field_visit``、遭遇的 ``contact``），讀進來
就是 ``trpg-char/3``。``trpg-wlog/2`` 也是舊規則寫的（6C-1 起有實地地圖的地點不再擲遇敵，改成
看得見的敵人），處理同 ``trpg-wlog/1``：照讀、規則已變、不能重播，寫回時標頭改成 ``trpg-wlog/3``。

**Phase 6C-1b**：``trpg-world/1`` 照讀（只多了選填欄位 ``defeated_spawns``），讀進來就是
``trpg-world/2``。``trpg-wlog/3`` 也是舊規則寫的（6C-1b 起進圖寬限、每隊清空、``personal``、
``day_phase``），處理同上：照讀、規則已變、不能重播，寫回時標頭改成 ``trpg-wlog/4``。

**Phase 6C-2**：``trpg-char/3`` 照讀（只多了遭遇接觸的選填欄位 ``enemy_at``），讀進來就是
``trpg-char/4``。``trpg-wlog/4`` 也是舊規則寫的（6C-2 起碰到地圖上的敵人就地切 12×12 戰場，``fight``
的步驟是照模板地圖記的），處理同上：照讀、規則已變、不能重播，寫回時標頭改成 ``trpg-wlog/5``。
**Phase 6C-6**：同一版 ``trpg-char/4`` 也多了選填欄位 ``visited_locations``（和 6C-2
一起合進來，沒有另升版號）。去過的地點只是另外記下來，不改任何規則。

**Phase 6C-5**：``trpg-char/4`` 照讀（只多了選填欄位 ``field_event``、``sneaking``、
``object_uses``），讀進來就是 ``trpg-char/5``。``trpg-wlog/5`` 也是舊規則寫的（6C-5 起有實地地圖的
地點改成走到隱藏入口 3 格內才感知、事件放在地圖上碰到才開），處理同上：照讀、規則已變、不能重播，
寫回時標頭改成 ``trpg-wlog/6``。

**Phase 6C-R2**：``trpg-world/2`` 照讀（只多了 ``defeated_spawns`` 的選填欄位 ``wins``），讀進來就是
``trpg-world/3``。``trpg-wlog/6`` 也是舊規則寫的（6C-R2 起地圖上每隊的陣容改由世界種子＋(區域, 地點,
隊伍)＋重生世代衍生；6C-5b 起營火點的清空條件、新手固定戰照步驟消失、走路抵達格也感知；21.10 第 20
條起走過渡口算一步），處理同上：照讀、規則已變、不能重播，寫回時標頭改成 ``trpg-wlog/7``。

**Phase 6C-R3**：``trpg-wlog/7`` 的標頭另記 ``rules_key``（:func:`log_rules_key`：
``戰鬥紀錄版號|規則包雜湊|內容 digest``，比照 :func:`trpg.server.league.rules_key`）。讀檔的一方
（:class:`trpg.api.world.WorldStore`）拿它和目前的規則鍵比，不一樣（或沒記）就把 ``stale_through``
設成最後一筆，處理同上：規則已變、不能重播。之後內容或規則改了不必再手動升版號（版號只留給格式
變更）。日誌改成只 append：每個動作附加一行（:func:`append_log_line`）；標頭只在 ``stale_through``
或 ``rules_key`` 改變、格式升版時整份重寫（:func:`write_atomic`）。

**Phase 6D-R1**：規則鍵多一段 :data:`WORLD_RULES_VERSION`（``戰鬥紀錄版號|w世界規則版號|規則包雜湊|
內容 digest``）：內容 digest 只看資料，世界規則的**程式**改了（例如走路、遇敵、感知的判法）資料
不會變，所以改了這類程式要手動把它加一（``docs/開發PM交接.md`` 6.6）。讀檔時截掉寫到一半的最後
一行（沒有換行結尾）由 :func:`read_log`／:func:`log_lines` 統一處理，所有讀者共用
（:attr:`WorldLog.torn`）。

**Phase 6D-R2**：``trpg-char/5`` 照讀（只多了 ``field_visit`` 的選填欄位 ``generations``：進圖時
每隊的重生世代，這一趟的陣容固定用它），讀進來就是 ``trpg-char/6``。陣容種子的判法改了，
:data:`WORLD_RULES_VERSION` 升成 2（舊日誌標成規則已變、不能重播）。

**Phase 6L-2**：日誌每筆多一個選填欄位 ``generated``（這個動作用到的 LLM 生成內容與來源：閃現提議、
劇情技能的元素與文字、機遇的三選一；:mod:`trpg.world.generated`），格式升成 ``trpg-wlog/8``；
空的時候不寫（沒有生成內容的那一行和 ``/7`` 逐字相同）。``trpg-wlog/7`` **照讀**（標頭照常解析；
沒有 ``generated``＝全部用組合器、模板與內容版），寫回時標頭改成 ``/8``。重播只讀這些紀錄、不呼叫
LLM。角色格式升成 ``trpg-char/8``（``skill_regions``、``PendingOffer.region``；``/7`` 以前照讀）。
:data:`WORLD_RULES_VERSION` 升成 11（舊日誌標成規則已變、不能重播）。

**Phase 6T-1a**（交易共同前置＋郵寄，08 8.16、#136）：日誌每筆多兩個選填欄位 ``counterpart``、
``counterpart_actor``（同時改兩個角色的那一筆：寄信、拒收、取回過期的信；另一個角色與他的帳號），
格式升成 ``trpg-wlog/9``；空的時候不寫（只改一個角色的那一行和 ``/8`` 逐字相同）。``trpg-wlog/7``、
``/8`` **照讀**，寫回時標頭改成 ``/9``。角色格式升成 ``trpg-char/9``（``gear_origin``、``mailbox``；
``/8`` 以前照讀，舊裝備記成綁定）、世界格式升成 ``trpg-world/4``（``trades``、``weapon_mix``、
上線紀錄的 ``characters``；``/3`` 以前照讀）。:data:`WORLD_RULES_VERSION` 升成 18。

**Phase 6T-1b**：主手可換別大類、過期的信自動退回（日誌、角色、世界的格式都沒變）；
:data:`WORLD_RULES_VERSION` 升成 19。

**Phase 6R-1**（#138 狐族改成獸耳族）：角色格式升成 ``trpg-char/10``（``free_race_change_used``：
這一季用過免費換種族；``/9`` 以前照讀＝還沒用過）；新動作 ``change_race``（日誌格式不變，舊日誌沒有
這種紀錄）。:data:`WORLD_RULES_VERSION` 升成 20。

**Phase 6R-2**（#137 外觀選項）：角色格式升成 ``trpg-char/11``（主角紙娃娃的 ``custom``：玩家自己
選的外觀；``/10`` 以前照讀＝種族預設）；新動作 ``change_look``（日誌格式不變）。
:data:`WORLD_RULES_VERSION` 升成 21。

**Phase TR-1**（#134 開局在主城工坊靶場）：角色格式升成 ``trpg-char/12``（``opening``：未完成開局與
起始技能的種子；``/11`` 以前照讀＝已完成開局）；新動作 ``opening_confirm``（日誌格式不變；靶場的
沙盒試打不寫日誌）。:data:`WORLD_RULES_VERSION` 升成 22。

**Phase LF-1**（LLM 閃現的名稱與描述）：閃現提議紀錄（``generated`` 裡的 ``FlashGen.record``）多
選填欄位 ``texts``（LLM 的名稱與描述，依變化的鍵），格式升成 ``trpg-wlog/10``；空的時候不寫（沒有
文字的那一行和 ``/9`` 逐字相同）。``trpg-wlog/7``～``/9`` **照讀**，寫回時標頭改成 ``/10``。角色存檔
的變化歷程（``Variation``）多選填 ``name_zh``、``note_zh``，沒值時不輸出，``CHAR_FORMAT``
不變（待 PM 決定）。:data:`WORLD_RULES_VERSION` 不變：舊日誌沒有文字，重播結果逐字相同。

**Phase WP-1**（許願池）：新動作 ``wish``；``generated`` 多一種紀錄 ``WishGen``（LLM 對到的關鍵字與
完整技能三選一；願望文字在動作裡），日誌格式不變（同動作 union 多一種的前例，待 PM 決定）。角色格式
升 ``trpg-char/14``；:data:`WORLD_RULES_VERSION` 升成 28。

**Phase RG-2**（精英單挑）：新動作 ``duel_choice``，日誌格式不變（同上，動作 union 多一種）。
角色格式升 ``trpg-char/15``（``EncounterResult.duel``）；:data:`WORLD_RULES_VERSION` 升成 31。

**Phase RG-4**（塔盾詞條「護陣」#163）：掉落算在持盾弟子、熔殼甲兵頭上時掉到的塔盾必帶護陣
（:func:`trpg.world.loot.roll_loot` 的必帶詞條，資料在 ``world/loot.yaml``）。日誌、角色、世界格式都
沒變；掉落的程式改了，:data:`WORLD_RULES_VERSION` 升成 32。

**Phase RG-5**（#163 玩家大盾）：持盾弟子、熔殼甲兵掉的塔盾外觀一定是對應形制（雲紋碑盾、熔殼塔盾；
``world/loot.yaml`` 的 ``signature_affixes.form``），詞條改名「盾陣」；盾兵與盾陣的高度條件統一成
「攻擊者比被攻擊的人高 1 層以上無視」（戰鬥日誌 ``trpg-battle-log/124``）。日誌、角色、世界格式都
沒變；掉落與戰鬥結算的程式改了，:data:`WORLD_RULES_VERSION` 升成 33。
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ValidationError

from trpg.content.library import ContentLibrary
from trpg.engine.ruleset_hash import hash_ruleset
from trpg.engine.runner import LOG_FORMAT
from trpg.roguelite.save import ruleset_hash
from trpg.world.errors import WorldSaveFormatError
from trpg.world.replay import WorldLogEntry
from trpg.world.state import (
    CHAR_FORMAT,
    LEGACY_CHAR_FORMATS,
    LEGACY_WORLD_FORMATS,
    WORLD_FORMAT,
    CharacterState,
    WorldState,
)

__all__ = [
    "LEGACY_WLOG_FORMATS",
    "READABLE_WLOG_FORMATS",
    "STALE_LOG_ZH",
    "WLOG_FORMAT",
    "WORLD_RULES_VERSION",
    "WorldLog",
    "append_log_line",
    "content_digest",
    "dumps_char",
    "dumps_log",
    "dumps_log_entry",
    "dumps_log_header",
    "dumps_world",
    "loads_char",
    "loads_log",
    "loads_world",
    "log_lines",
    "log_rules_key",
    "read_log",
    "write_atomic",
]

WLOG_FORMAT: Final = "trpg-wlog/10"
READABLE_WLOG_FORMATS: Final = frozenset({"trpg-wlog/7", "trpg-wlog/8", "trpg-wlog/9"})
"""照讀、標頭照常解析的舊日誌格式（6L-2：``/7`` 只少了選填欄位 ``generated``；6T-1a：``/8`` 只少了
選填欄位 ``counterpart``、``counterpart_actor``；LF-1：``/9`` 只少了閃現提議紀錄的選填欄位
``texts``）。"""
LEGACY_WLOG_FORMATS: Final = frozenset(
    {"trpg-wlog/1", "trpg-wlog/2", "trpg-wlog/3", "trpg-wlog/4", "trpg-wlog/5", "trpg-wlog/6"}
)
"""照讀、但標成「規則已變、不能重播」的舊日誌格式。"""
STALE_LOG_ZH: Final = "規則已變、不能重播"
WORLD_RULES_VERSION: Final = 33
# 各版見下方說明（19＝6T-1b；20＝6R-1；21＝6R-2；22＝TR-1；23＝OB-1；24＝OB-2；25＝OB-3＋OB-4；
# 26＝DD-1；27＝OB-7；28＝WP-1；29＝RR-1；30＝RR-2c；31＝RG-2；32＝RG-4；33＝RG-5）
"""世界規則程式的版號（6D-R1）：改了世界規則的程式（``trpg.world`` 裡會讓同樣的日誌重播出不同結果
的改動）時手動加一；記在日誌的規則鍵裡（:func:`log_rules_key`），舊日誌就標成規則已變、不能重播。
只改內容資料不用加（內容 digest 會變）。

- 1（6D-R1）：起始版號。
- 2（6D-R2）：固定陣容——進圖時記下每隊的重生世代（``field_visit.generations``），這一趟的陣容
  種子用它，別的玩家打贏只影響下一趟。
- 3（6E-1／6E-3）：霧牆（出口 ``gate``）擋住山門出口；就地開打的開打距離。（6D-R2 與 6E-1／6E-3
  兩條分支各自從 1 加到 2，合併時取 3。）
- 4（6E-3b）：第三方起始區（離我方至少 2 格）；主角不擺在敵方帶頭的背後半邊。
- 5（6E-3c）：撤回背後半邊，改成主角不擺到敵方帶頭的另一側；第三方永遠至少隔 2 格。
- 6（6E-3d）：第三方擺在敵方那一側。
- 7（6F-1）：全滅回鎮時法力也回滿（原本照戰後）；新手鏈被動保底把新方向換成「還沒有的關鍵字」的
  被動時不再標成退回（三選一的 ``fallback`` 旗標會進角色狀態）。
- 8（6F-2）：#125 開局在主城——在主城、還沒到過新手區（``world/newcomer.yaml`` 的
  ``start_region``）小鎮的角色，傳送（``teleport``、``use_teleport_stone``）可以直接去那一區的小鎮
  （:func:`trpg.world.atlas.free_first_teleport`）；新角色改由 API 建在主城（``new_character`` 本身
  不變）。任務條件多一種狀態型的 ``flashed``（閃現過至少一招，#132：導師任務鏈「觀摩」新手時的
  閃現也算）。CHAR_FORMAT、wlog 格式不變（沒有新欄位）。
- 9（6F-4）：#128 新手保護——新手任務鏈（``kind: starter``）的固定戰被敵人先看到時改成「沒有先手」
  （開打距離 3 格，:func:`trpg.world.field_enemies.newcomer_guarded`；同樣的走路日誌開出不同的
  戰場）；
  任務獎勵多 ``level_to``（補到剛好那一級的經驗，C2：同樣完成一步給的經驗不同）；三個只記畫面紀錄的
  動作（``hint_seen``、``hints_off``、``hints_reset``；戰鬥中、待選閃現或三選一時也能做）。
  角色格式升成 ``trpg-char/7``（提示紀錄 ``hints_seen``、``hints_off`` 與 ``level_seen``；``/6``
  以前照讀，舊角色的 ``level_seen`` 補成目前等級）。wlog 格式不變（6C-R3 起靠規則鍵標舊日誌）。
- 10（6F-4b）：#129 起始第 2 招改出組合器自動生成的利用者白板（``trpg.content.whiteboard_exploit``；
  :func:`trpg.roguelite.start.starting_skill` 的 ``prefer_uses``），白板檢查接受「條件傷害」帶第二個
  （利用的）關鍵字（:func:`trpg.skillgen.whiteboard_check.is_exploit`）——同樣的建角日誌給出不同的起始
  技能。新手三步只算打贏固定戰（``quests/cloud_ridge.yaml`` 的 ``group``）是內容，
  內容 digest 本來就會變；
  程式也改了，保守起見一起升版。一般的三選一（不指定 ``uses``）不抽生成的配方，結果不變。
- 11（6L-2）：大世界接上三個 LLM 入口（閃現與重閃、劇情技能、機遇的完整技能三選一）。世界引擎改從
  生成內容的供應者（:mod:`trpg.world.generated`）拿提議，日誌每筆記下最後給出的版本；劇情技能可以
  換元素與文字（:func:`trpg.skillgen.story_theme.retheme`，骨架與預算不變）；學到的技能記取得地點的
  界域（``skill_regions``）。模型關閉時結果和 10 相同，但同一份新日誌在 10 的程式重播不出 LLM 版本，
  保守升版。
- 12（6F-4c）：大世界的候選改了——一般白板三選一也混進「利用玩家持有的關鍵字」的利用者白板、#130 的
  雙關鍵字橋接先試它（:mod:`trpg.skillgen.whiteboard_candidates`）；起始第 2 招的條件優先對上第 1 招
  實際造得出來的狀態或表面（:mod:`trpg.skillgen.exploit_match`）；技能的 ``pool_regions``
  （區域技能池，候選池依取得地點的區域過濾；九轉回天只在雲嶺）；手寫池補倒地 ↔ 撞擊、標記 ↔ 高處的
  技能。同一份日誌在 11 的程式給出不同的起始技能與三選一。梯田巡邏改陣容是內容，
  內容 digest 本來就會變。
- 13（6F-4d）：大世界的候選又改了——一般三選一混進利用者白板改照權重（``exploit`` 的
  ``offer_permille``、``bridge_permille``，:mod:`trpg.skillgen.whiteboard_candidates`）；起始第 2 招
  的條件只認第 1 招實際施加的狀態或表面（刪掉傷害元素的對應，:mod:`trpg.skillgen.exploit_match`）；
  起始第 1 招不挑「只利用、不製造」的招（:mod:`trpg.roguelite.start`）。同一份日誌在 12 的程式給出
  不同的起始技能與三選一。踢滾改名、梯田固定戰改陣容是內容，內容 digest 本來就會變。
- 14（6F-4e）：起始第 1 招優先挑實際施加該關鍵字狀態或表面的招
  （:func:`trpg.skillgen.exploit_match.applies_keyword`，:mod:`trpg.roguelite.start`；例：點燃池
  挑點燃、火焰彈、燃燒爆，不挑只有傷害的火球）；白板檢查接受 ``whiteboard.status_rider_keywords``
  （點燃、冰凍）的「傷害＋施加狀態或表面」（:mod:`trpg.skillgen.whiteboard_check`）。同一份日誌在
  13 的程式給出不同的起始技能與三選一（候選池多了新配方）。新配方本身是內容，內容 digest 本來
  就會變。
- 15（6F-4f）：起始第 1 招先在「照寫法就施加該關鍵字狀態或表面」的配方之間平均挑一個
  （``fork("recipe")``，:func:`trpg.skillgen.exploit_match.recipe_applies_keyword`、
  :func:`trpg.skillgen.whiteboard.starter_recipes`，:mod:`trpg.roguelite.start`），再擲種子；
  潮濕、倒地、標記各補 1 招施加型白板（激流、掀地、點名），火焰彈改名引火彈。同一份日誌在 14 的
  程式給出不同的起始技能。新配方與改名是內容，內容 digest 本來就會變。
- 16（6F-4g）：白板配方多了 ``min_cooldown``（主動白板照舊擲冷卻，再至少取到它，
  :func:`trpg.skillgen.whiteboard._active_cost`；掀地至少冷卻 2）——同一份日誌在 15 的程式給出
  不同冷卻的掀地。手寫池補倒地 ↔ 標記的「倒地追獵」（單手劍「標記＋倒地」的起始第 2 招、三選一的
  手寫補位都會抽到）。新技能是內容，內容 digest 本來就會變；程式也改了，保守升版。
- 17（6F-4h）：「倒地追獵」改成打擊骨架的「追印絆擊」（ID 沿用 ``skill_prone_mark_strike``）：
  對被標記的目標傷害較高（×1.8）＋擊倒，拿掉「只能對倒地的目標用」，冷卻 1 → 2。它現在也製造
  倒地，同一份日誌在 16 的規則下打出不同的結果（對沒倒地的目標也能用、會擊倒）。只改內容，
  內容 digest 本來就會變；規則行為改了，保守升版。
- 18（6T-1a）：交易共同前置與郵寄（:mod:`trpg.world.trade`；寄信、領信、拒收、取回過期的信，日誌的
  一筆可以同時改兩個角色）；每個動作之後補上裝備的來歷與綁定（穿上就綁定、獨特與首殺取得就綁定）；
  #135 主手掉落的武器大類（野外 50% 同大類、精英 75%，其餘依前一天全服在線角色的武器大類比例，
  :mod:`trpg.world.weapon_mix`；換日時算、存進世界狀態）。同一份日誌在 17 的程式掉出不同大類的主手。
- 19（6T-1b）：玩法 PM 對 6T-1a 的兩項決定。① 大世界的主手可以換成別大類的武器（換上後原大類的武器技
  開戰時不放進技能列，換回同大類就恢復；:func:`trpg.world.weapon_mix.usable_skills`）——18 的程式拒絕
  這種換裝。② 過期的信自動退回寄件人、照退件用 ``mail_claim`` 領（同時改兩人），
  拿掉 ``mail_reclaim``。
- 20（6R-1，#138）：狐族改成獸耳族。① 戰鬥引擎的種族技「獸躍」、被動「輕身」（大世界的戰鬥照新規則
  結算，同一份日誌開出的戰鬥結果不同）；② 聊天內容可以只對某些種族說（``TalkEntry.races``：霜音對
  獸耳族的專屬對話，:func:`trpg.world.affinity.talk_entries`）；③ 新動作 ``change_race``（這一季的
  免費換種族，:mod:`trpg.world.race_change`）。``fox`` 的判定加值改成攀爬跳躍是內容
  （``situation_rules.yaml``），內容 digest 本來就會變。
- 21（6R-2，#137）：新動作 ``change_look``（主城免費改外觀，:mod:`trpg.world.looks`）；
  ``change_race`` 換種族時，玩家選的外觀新種族沒有的改回預設（同一份日誌重播出的角色外觀不同）。
- 22（TR-1，#134）：開局在主城工坊靶場。新動作 ``opening_confirm``（確定出發：起始武器＋2 個關鍵字，
  :mod:`trpg.world.opening`）；未完成開局（``CharacterState.opening``）的角色只能做它與只記畫面紀錄
  的動作，完成後不能再送（21 的程式不認得這個動作，也不擋未完成開局的角色）。
- 23（OB-1，#150）：開局先玩再定。新動作 ``opening_class``（選大類：入門武器、入門招、4 點自動配）；
  ``opening_gate`` 分階段（``pick_class`` 白名單多了 ``change_look``、``starter`` 黑名單）；入門期
  升級時屬性點自動配掉（同樣的戰鬥日誌，角色屬性不同）。``CHAR_FORMAT`` 升 ``/13``，``trpg-wlog``
  不變（新動作只是 union 增項）。
- 24（OB-2，#150）：① 入門期（``opening.stage == "starter"``）完成新手任務（``kind: starter``）的
  步驟不再當場出三選一，改記進 ``opening.deferred_offers``；② ``opening_confirm`` 在入門期是正式選定
  （:mod:`trpg.world.opening_choice`；23 一律拒絕）；③ 開局還沒正式選定的角色整備後不存影子。同一份
  23 的日誌只要有入門期的角色，重播出的三選一與影子就不同。``CHAR_FORMAT`` 不變（欄位 OB-1 已加）。
- 25（OB-3＋OB-4，#150；兩段同一批上線，只加一次）。
  OB-4：入門期（``opening`` 還沒正式選定）的戰鬥閘與活動限制
  （:mod:`trpg.world.opening_limits`）：① 實地地圖上只留新手任務前兩步的固定戰，其他隊伍不出現、不
  接觸；② 節點移動的遇敵機率歸 0（擲骰照擲）；③ ``fight`` 只收那兩步固定戰的遭遇；④ 事件的戰鬥
  解法、機遇、``use: encounter`` 的情境物件擋下，入門期不出機遇保底、不記「遇過機遇」；⑤ 給招的任務
  步驟（三選一、劇情技能；新手任務前兩步除外）等正式選定才結算。同一份 24 的日誌只要有入門期的
  角色，重播出的遭遇與任務進度就不同；已完成開局的角色不變。``CHAR_FORMAT`` 不變。
  OB-3：① 延後的三選一改成選完一組才出下一組（24 是選定當下兩組一起出）；
  ② 新動作 ``opening_reselect``（4 級前的免費重選，:mod:`trpg.world.opening_reselect`）；③ 開局還沒
  結束的角色 4 級前不能閃現；④ 正式選定過的角色到 4 級時 ``opening`` 清成 ``None``（溶掉、傳承
  解鎖）；⑤ 略過配點教學之後換了地點會記一筆（``hints_seen``，再提示用）。``CHAR_FORMAT``、
  ``trpg-wlog`` 不變（沒有新的存檔欄位；新動作只是 union 增項，舊日誌沒有這種紀錄）。
- 26（DD-1，#153）：引擎的雙匕首單體武器技改打兩下（戰鬥紀錄 ``trpg-battle-log/116``）。世界的程式
  沒有改；世界日誌的規則鍵本來就含 ``LOG_FORMAT``，照開發 PM 的派工一併加一。同一份 25 的日誌只要
  有拿雙匕首施放單體武器技的戰鬥，重播結果就不同。``CHAR_FORMAT``、``trpg-wlog`` 不變。
- 27（OB-7，#154）：① 任務的 ``companion_after``：劇情夥伴等那一步完成才加入（阿岳在新手第 1 步打完
  才入隊，原本接任務就加入）；② ``hire`` 之後開局的護衛不在隊上時記劇情旗標 ``escort_parted``
  （隊伍面板的來歷只給開局帶來的那一位）。開局只帶賽倫是內容（``default_party``）。``CHAR_FORMAT``、
  ``trpg-wlog`` 不變。
- 28（WP-1，07 7.6、#88）：新動作 ``wish``（主城的許願池：扣任務幣、每週次數、完整技能三選一）；
  許願池的三選一都不拿時退還任務幣（``offer_pick`` 不帶 ``pick``）。``CHAR_FORMAT`` 升
  ``trpg-char/14``（``wish_week``、``PendingOffer.refund``）；
  ``trpg-wlog`` 不變（``generated`` 多一種
  紀錄 ``wish``，同動作 union 多一種的前例）。
- 29（RR-1，06 6.34.9「重推套不上的那一筆」）：升階重配時，閃過的技能照新階級套不上的那一筆記下
  升階前的定義（``FlashRecord.kept``），重推照它保留；以前整條重推失敗就重配存著的定義。套不上的
  那一筆在歷程中間時，升階後的數值與之後的閃現、重閃選項都會不同。``CHAR_FORMAT`` 不升（只多了
  選填、沒有時不輸出的欄位，舊存檔逐字不變）。
- 30（RR-2c，06 6.34.3「重閃也一樣」＋#160）：重閃多一道整招篩選（重閃後整招的預算分數不低於
  現在的卡），篩完一個都不剩的格子才改出較弱的候選（取代 RR-2 的判定）。日誌重播時重閃會重新出題
  （``make_offer``），舊日誌裡的重閃可能出不同的選項、``flash_pick`` 的索引對到別的變化，所以舊日誌
  標成規則已變。``CHAR_FORMAT`` 不升（``FlashOption.weaker`` 的意思改了，但 ``False`` 不輸出，
  存檔欄位沒變）。
- 31（RG-2，#162，09 9.6.6）：精英單挑——遇敵時陣容排最前的精英帶 ``duel: true`` 就提出一對一
  （``EncounterResult.duel``），新動作 ``duel_choice``；接受時開戰只有主角對精英本人（組場改變），
  獎勵照整個陣容（掉材料的成員改成整個敵方陣容）。另外戰鬥紀錄 ``trpg-battle-log/121``（敵方陷阱的
  可疑痕跡；第一季沒有會放陷阱的敵人，世界戰鬥的結果不變）。``CHAR_FORMAT`` 升 ``trpg-char/15``
  （``EncounterResult.duel``，``None`` 不輸出）；``trpg-wlog`` 不變（動作 union 多一種的前例）。

沒有升版的規則改動（保守判斷：目前的內容觸發不到，同一份日誌重播結果不變）：

- 6P-2 查地點圖改走 ``location_map``（含主城）：``contact_battlefield`` 在主城就地開打時拿得到
  主城地點（只影響戰場名字），但主城是安全區、不可有 ``spawns``
  （:func:`~trpg.content.fields.field_map_report` 的檢查），碰不到地圖上的敵人；跨區出口指向
  主城現在能走，但目前沒有任何出口通往主城（主城只能傳送抵達）。內容加了這兩種情況之一時要升版。
- 6P-2 ``walk`` 的格數上限改由規則 ``field.walk_max_steps`` 決定：規則值仍是 30，與原本的程式
  上限相同，只有超過時的錯誤訊息不同（被拒絕的動作不改狀態）。改規則值會改內容 digest。"""


@dataclass(frozen=True)
class WorldLog:
    """讀進來的世界動作日誌。"""

    entries: tuple[WorldLogEntry, ...]
    stale_through: int | None = None
    """這個序號（含）以前的紀錄是舊規則寫的：規則已變、不能重播。``None``＝全部能重播。"""
    rules_key: str | None = None
    """標頭記的規則鍵（6C-R3，:func:`log_rules_key`）；``None``＝沒記（6C-R3 以前寫的、舊格式）。"""
    header: str = field(default="", compare=False)
    """標頭那一行的原文（判斷要不要重寫標頭用）。"""
    torn: bool = field(default=False, compare=False)
    """最後一行沒有換行結尾（append 寫到一半中斷），已略過那一行（6D-R1）。"""

    @property
    def stale_zh(self) -> str | None:
        return None if self.stale_through is None else STALE_LOG_ZH


def _dumps(model: BaseModel, *, indent: int | None) -> str:
    separators = None if indent is not None else (",", ":")
    return json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        indent=indent,
        separators=separators,
    )


def _parse_object(text: str, expected: str, legacy: frozenset[str] = frozenset()) -> dict[str, Any]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise WorldSaveFormatError(f"不是合法的 JSON：{exc}") from exc
    if not isinstance(raw, dict):
        raise WorldSaveFormatError("存檔必須是 JSON 物件")
    found = raw.get("format")
    if found != expected and found not in legacy:
        raise WorldSaveFormatError(f"不認得的存檔格式：{found!r}（需要 {expected}）")
    return raw


def _validate[M: BaseModel](model: type[M], raw: object) -> M:
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise WorldSaveFormatError(f"{model.__name__} 的內容不合法：{exc}") from exc


def dumps_world(world: WorldState) -> str:
    return _dumps(world, indent=2) + "\n"


def loads_world(text: str) -> WorldState:
    return _validate(WorldState, _parse_object(text, WORLD_FORMAT, LEGACY_WORLD_FORMATS))


def dumps_char(char: CharacterState) -> str:
    return _dumps(char, indent=2) + "\n"


def loads_char(text: str) -> CharacterState:
    return _validate(CharacterState, _parse_object(text, CHAR_FORMAT, LEGACY_CHAR_FORMATS))


def dumps_log_entry(entry: WorldLogEntry) -> str:
    """日誌的一行（不含換行）。``generated`` 空的時候不寫（6L-2：和 ``trpg-wlog/7`` 的行
    逐字相同）；``counterpart``、``counterpart_actor`` 是 ``None`` 時也不寫（6T-1a：和 ``/8``
    相同）。"""
    data = entry.model_dump(mode="json")
    if not data.get("generated"):
        data.pop("generated", None)
    for key in ("counterpart", "counterpart_actor"):
        if data.get(key) is None:
            data.pop(key, None)
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def dumps_log_header(*, stale_through: int | None = None, rules_key: str | None = None) -> str:
    """日誌的標頭（一行，不含換行）。鍵的順序固定：``format``、``rules_key``、``stale_through``、
    ``stale_zh``。"""
    header: dict[str, object] = {"format": WLOG_FORMAT}
    if rules_key is not None:
        header["rules_key"] = rules_key
    if stale_through is not None:
        header |= {"stale_through": stale_through, "stale_zh": STALE_LOG_ZH}
    return json.dumps(header, ensure_ascii=False)


def dumps_log(
    entries: Iterable[WorldLogEntry],
    *,
    stale_through: int | None = None,
    rules_key: str | None = None,
) -> str:
    """整份日誌（標頭＋每筆一行，結尾換行）。``stale_through`` 有值時，標頭記下舊規則的紀錄
    到哪一筆；``rules_key`` 有值時記下寫入時的規則鍵（6C-R3）。"""
    header = dumps_log_header(stale_through=stale_through, rules_key=rules_key)
    lines = [header, *(dumps_log_entry(e) for e in entries)]
    return "\n".join(lines) + "\n"


def append_log_line(path: Path, entry: WorldLogEntry) -> None:
    """在已存在、以換行結尾的日誌檔尾端附加一筆（6C-R3）；結果和 :func:`dumps_log` 整份重寫的
    內容逐字相同。"""
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(dumps_log_entry(entry) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def content_digest(library: ContentLibrary) -> str:
    """內容的確定性 digest（6C-R3）：全部內容檔（:func:`~trpg.roguelite.save.ruleset_hash`，依相對
    路徑排序、排序鍵 JSON）再加上內容庫裡的實地地圖（依地圖 ID）與大世界規則（測試用
    ``dataclasses.replace`` 換掉、沒進 ``files`` 的也算到）。不用內建 ``hash()``。"""
    maps = library.field_maps
    fields = [[k, maps[k].model_dump(mode="json")] for k in sorted(maps)]
    rules = None if library.world_rules is None else library.world_rules.model_dump(mode="json")
    text = json.dumps(
        [ruleset_hash(library), fields, rules],
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def log_rules_key(library: ContentLibrary) -> str:
    """世界日誌的規則鍵（6C-R3）：``戰鬥紀錄版號|w世界規則版號|規則包雜湊|內容 digest``（比照
    :func:`trpg.server.league.rules_key`；世界規則版號 :data:`WORLD_RULES_VERSION` 是 6D-R1 加的）。
    和日誌標頭記的不同＝規則或內容改了，舊紀錄不能重播。"""
    ruleset = hash_ruleset(library.ruleset)
    return f"{LOG_FORMAT}|w{WORLD_RULES_VERSION}|{ruleset}|{content_digest(library)[:16]}"


def _log_header(line: str) -> tuple[int | None, str | None]:
    """讀標頭，回傳 ``(stale_through, rules_key)``（舊格式的 ``stale_through``＝``-1``，表示
    「全部」，由 :func:`read_log` 換成最後一筆的序號）。"""
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as exc:
        raise WorldSaveFormatError(f"不是合法的 JSON：{exc}") from exc
    if isinstance(raw, dict) and raw.get("format") in LEGACY_WLOG_FORMATS:
        return -1, None
    header = _parse_object(line, WLOG_FORMAT, READABLE_WLOG_FORMATS)
    key = header.get("rules_key")
    if key is not None and not isinstance(key, str):
        raise WorldSaveFormatError(f"日誌標頭的 rules_key 不合法：{key!r}")
    stale = header.get("stale_through")
    if stale is None:
        return None, key
    if not isinstance(stale, int) or isinstance(stale, bool) or stale < 0:
        raise WorldSaveFormatError(f"日誌標頭的 stale_through 不合法：{stale!r}")
    return stale, key


def log_lines(text: str) -> tuple[list[str], bool]:
    """日誌的完整行（略過空行）與「最後一行有沒有被丟掉」（6D-R1）：最後一行沒有換行結尾＝append
    寫到一半中斷（那個動作的角色存檔也還沒寫），丟掉那一行。所有讀日誌的地方都經過這裡。"""
    torn = bool(text) and not text.endswith("\n")
    if torn:
        text = text[: text.rfind("\n") + 1]
    return [line for line in text.splitlines() if line.strip()], torn


def read_log(text: str) -> WorldLog:
    """讀整份日誌（含舊格式；見模組說明）。寫到一半的最後一行略過（:func:`log_lines`）；連標頭都
    沒寫完＝空的日誌（``torn`` 為真）。"""
    lines, torn = log_lines(text)
    if not lines:
        if torn:
            return WorldLog(entries=(), torn=True)
        raise WorldSaveFormatError("日誌是空的（缺少標頭）")
    stale, key = _log_header(lines[0])
    entries = _log_entries(lines)
    if stale == -1:
        stale = entries[-1].seq if entries else None
    return WorldLog(entries=entries, stale_through=stale, rules_key=key, header=lines[0], torn=torn)


def loads_log(text: str) -> tuple[WorldLogEntry, ...]:
    """整份日誌的紀錄（含舊格式的；要知道能不能重播用 :func:`read_log`）。"""
    return read_log(text).entries


def _log_entries(lines: list[str]) -> tuple[WorldLogEntry, ...]:
    entries: list[WorldLogEntry] = []
    for number, line in enumerate(lines[1:], start=2):
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorldSaveFormatError(f"日誌第 {number} 行不是合法的 JSON：{exc}") from exc
        entries.append(_validate(WorldLogEntry, raw))
    return tuple(entries)


def write_atomic(path: Path, text: str) -> None:
    """寫入 ``path``：先寫同資料夾的暫存檔再原子改名（中斷時舊檔不會壞掉）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
