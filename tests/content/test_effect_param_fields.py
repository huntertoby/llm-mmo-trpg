"""Phase 3E-1 #7：``EffectSpec.param_values`` 的欄位清單從 ``model_fields`` 推導。"""

from __future__ import annotations

from trpg.content.skills import EFFECT_NON_PARAM_FIELDS, EFFECT_PARAM_FIELDS, EffectSpec


def test_every_effect_field_is_a_parameter_or_explicitly_excluded() -> None:
    fields = set(EffectSpec.model_fields)
    assert fields >= EFFECT_NON_PARAM_FIELDS  # 排除清單裡沒有已經不存在的欄位
    assert set(EFFECT_PARAM_FIELDS) | EFFECT_NON_PARAM_FIELDS == fields
    assert not set(EFFECT_PARAM_FIELDS) & EFFECT_NON_PARAM_FIELDS
    assert list(EFFECT_PARAM_FIELDS) == sorted(EFFECT_PARAM_FIELDS)


def test_param_values_returns_only_filled_parameters() -> None:
    spec = EffectSpec.model_validate(
        {"type": "damage", "dice": "2d6", "element": "fire", "affects": "enemies"}
    )
    values = spec.param_values()
    assert set(values) == {"dice", "element"}
    assert not set(values) & EFFECT_NON_PARAM_FIELDS
