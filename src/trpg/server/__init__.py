"""伺服器的領域服務（Phase 5D-R2：從 ``trpg.api`` 移出）。

- ``accounts``／``account_config``：帳號存檔與設定（API、Bot、開發腳本共用）。
- ``first_kills``：全服首殺紀錄；``announce``：Discord 公告的資料與文字；``notes``：地點留言與足跡。
- ``season_policy``：每個存檔欄位的季末重置分類（數值類／紀念類，09 9.7、#91）。
- 依賴方向：可以匯入 ``trpg.world``、``trpg.content``、``trpg.roguelite``、``trpg.shared``；
  不得匯入 ``trpg.api``、``trpg.cli``、``trpg.bot``。``trpg.api`` 與 ``trpg.bot`` 匯入本套件；
  ``trpg.engine``、``trpg.world`` 等下層不得匯入本套件
  （import-linter 與 ``tests/test_architecture.py``）。
"""
