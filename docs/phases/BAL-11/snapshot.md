# BAL-11a：覆寫下的行為快照（`tests/skillgen/fixtures/refactor_3wr2.json`）

#### 覆寫 `fine_all`（三個舊階梯一起改細（修正 10‰、接續段 25‰、形態 25‰））

行為快照會變：完整技能 15／301、升階重配 15／301、閃現出題 9／129。

- complete：skill_attack_mastery、skill_form_bear、skill_form_cat、skill_form_demon、skill_form_dragon、skill_form_elemental、skill_form_giant、skill_form_roc、skill_form_shadow、skill_form_treant、skill_form_werewolf、skill_rune_resonance、skill_rune_sight、skill_searing_scar、skill_war_avatar
- retier：skill_attack_mastery、skill_form_bear、skill_form_cat、skill_form_demon、skill_form_dragon、skill_form_elemental、skill_form_giant、skill_form_roc、skill_form_shadow、skill_form_treant、skill_form_werewolf、skill_rune_resonance、skill_rune_sight、skill_searing_scar、skill_war_avatar
- flash：skill_attack_mastery@11@1、skill_attack_mastery@3@1、skill_attack_mastery@5@2、skill_form_demon@11@1、skill_form_demon@3@1、skill_form_demon@5@2、skill_shadow_whirl@11@1、skill_shadow_whirl@3@1、skill_shadow_whirl@5@2
- 完整技能預算分數有變 15 招：skill_attack_mastery 15.1200→12.0960、skill_form_bear 15.1250→15.4688、skill_form_cat 15.1250→15.4688、skill_form_demon 15.8125→15.4688、skill_form_dragon 15.8125→15.4688、skill_form_elemental 15.8125→15.4688、skill_form_giant 15.8125→15.4688、skill_form_roc 15.1250→15.4688、skill_form_shadow 15.8125→15.4688、skill_form_treant 15.8125→15.4688、skill_form_werewolf 15.1250→15.4688、skill_rune_resonance 14.7000→14.2800


#### 覆寫 `fine_flash`（三個舊階梯只在閃現改細（修正 10‰、接續段 25‰、形態 25‰））

行為快照會變：完整技能 0／301、升階重配 0／301、閃現出題 9／129。

- flash：skill_attack_mastery@11@1、skill_attack_mastery@3@1、skill_attack_mastery@5@2、skill_form_demon@11@1、skill_form_demon@3@1、skill_form_demon@5@2、skill_shadow_whirl@11@1、skill_shadow_whirl@3@1、skill_shadow_whirl@5@2


#### 覆寫 `floor_relax_20`（強度下限 ×0.98）

行為快照會變：完整技能 0／301、升階重配 0／301、閃現出題 22／129。

- flash：skill_covering_fire@11@1、skill_covering_fire@3@1、skill_covering_fire@5@2、skill_deep_freeze@3@1、skill_ember_brand@11@1、skill_ember_brand@3@1、skill_ember_brand@5@2、skill_fleet_foot@11@1、skill_fleet_foot@3@1、skill_fleet_foot@5@2、skill_frost_ledge_cleave@3@1、skill_ground_finish@11@1、skill_ground_finish@3@1、skill_hunters_strike@3@1、skill_hunters_strike@5@2、skill_point_blank_blast@11@1、skill_scorching_slash@11@1、skill_scorching_slash@3@1、skill_shoulder_strike@11@1、skill_stand_firm@11@1…


#### 覆寫 `cooldown_offset`（多一個旋鈕：冷卻 +1／+2 折抵）

行為快照會變：完整技能 0／301、升階重配 0／301、閃現出題 19／129。

- flash：skill_arc_follow_up@11@1、skill_clearing_breeze@11@1、skill_clearing_breeze@3@1、skill_clearing_breeze@5@2、skill_deep_freeze@11@1、skill_deep_freeze@3@1、skill_fire_bolt@11@1、skill_form_renewal@5@2、skill_frost_ledge_cleave@11@1、skill_hex_bolt@5@2、skill_mark_prey@11@1、skill_mark_prey@3@1、skill_mark_prey@5@2、skill_quake_wave@11@1、skill_quake_wave@3@1、skill_rallying_cry@11@1、skill_rallying_cry@3@1、skill_venom_detonation@11@1、skill_venom_detonation@3@1

