"""Discord Bot 核心（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29）。

- 只靠 :class:`~trpg.bot.gateway.DiscordGateway` 介面跟 Discord 溝通；測試用
  :class:`~trpg.bot.fake.FakeDiscordGateway`，不連網。真實 adapter 是
  :mod:`trpg.bot.discord_adapter`（5E-2b；discord.py 只在這裡匯入）。
- 帳號一律經 ``trpg.api`` 的服務層（:class:`trpg.api.accounts.AccountStore`）；不直接匯入
  ``trpg.world``、``trpg.engine`` 等（import-linter 契約）。
"""
