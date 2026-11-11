// 自動產生，不要手改：現行技能圖示、部件小圓片、骨架徽章的畫法（client/src/render/skillIcon.ts、skillParts.ts、skillGlyphs.ts、statusIcon.ts 與 battle/glossary.ts，用 vite 的 lib 模式打包成 IIFE，pixi.js 設成 external）。
// 只給 Q 版小圖示第 4 批樣張（q-icons-parts.html）的「現行」那一欄用，和實機同一份程式。用法：QPartsLive.setGlossary(名詞表) 之後呼叫 skillIconCanvas、drawChip、effectPart、tileCanvas…
// 重新產生的做法見 docs/art/Q版小圖示-第4批徽章與部件.md 第 8 節最後一項。
(function() {
	//#region client/src/render/palette.ts
	var ELEMENT_COLORS = {
		physical: {
			name: "物理",
			primary: "#f2f2f2",
			secondary: "#b8bcc8",
			accent: "#e8ebf0",
			dark: "#2c313b",
			light: "#7d8798",
			bright: "#ffffff",
			mark: "#e05050"
		},
		fire: {
			name: "火",
			primary: "#ff6a1a",
			secondary: "#ffd23f",
			accent: "#ffb23a",
			dark: "#4a1104",
			light: "#e8541a",
			bright: "#ffd04a"
		},
		ice: {
			name: "冰",
			primary: "#8fe3ff",
			secondary: "#ffffff",
			accent: "#d8f6ff",
			dark: "#0b2f4e",
			light: "#3fa6d8",
			bright: "#e8fbff"
		},
		lightning: {
			name: "雷",
			primary: "#fff36b",
			secondary: "#8fd0ff",
			accent: "#fff36b",
			dark: "#1d1d4a",
			light: "#5a5ac8",
			bright: "#fff7c0"
		},
		poison: {
			name: "毒",
			primary: "#7ddc3a",
			secondary: "#3f8f2a",
			accent: "#b6f06a",
			dark: "#12320c",
			light: "#4f9a28",
			bright: "#d6f59a"
		},
		wind: {
			name: "風",
			primary: "#c8ffe8",
			secondary: "#7fe0c0",
			accent: "#dcfff1",
			dark: "#0b3f3a",
			light: "#3fb59a",
			bright: "#effff8"
		},
		earth: {
			name: "大地",
			primary: "#b0814a",
			secondary: "#6e5236",
			accent: "#f0c890",
			dark: "#2e1d0e",
			light: "#9a6a36",
			bright: "#e6c89a"
		},
		holy: {
			name: "聖光",
			primary: "#fff2b0",
			secondary: "#ffd75e",
			accent: "#fff6c8",
			dark: "#5a3a06",
			light: "#e7b23a",
			bright: "#fffbe0"
		},
		shadow: {
			name: "暗影",
			primary: "#9a6ad8",
			secondary: "#2a1840",
			accent: "#d2b0ff",
			dark: "#10071e",
			light: "#5a3590",
			bright: "#c8a8f0"
		}
	};
	/** 水不是元素（只是表面與「濕」關鍵字）；保留一個水色，若之後內容加入水元素可直接放進 `ELEMENT_COLORS`。 */
	var WATER_COLOR = "#4aa8ff";
	/** 沒有元素、不認得的元素。 */
	var NEUTRAL_COLOR = "#d8d8e0";
	/** 元素的代表色（狀態圖樣、腳邊粒子、陷阱與區域）；水＝水色，不認得 → 中性色。 */
	function elementColor(el) {
		if (el == null) return NEUTRAL_COLOR;
		if (el === "water") return WATER_COLOR;
		const c = ELEMENT_COLORS[el];
		return c === void 0 ? NEUTRAL_COLOR : c.mark ?? c.primary;
	}
	ELEMENT_COLORS["fire"].primary, ELEMENT_COLORS["lightning"].primary, ELEMENT_COLORS["ice"].primary;
	/** 技能圖示上「表面」小圖樣的顏色（畫在深色底上，偏亮）；火取元素色。 */
	var SURFACE_ICON_COLOR = {
		fire: ELEMENT_COLORS["fire"].primary,
		ice: "#cdeeff",
		oil: "#5a4a30",
		water: "#4a9af0",
		holy: "#ffe58a",
		darkness: "#8a5ad0",
		smoke: "#c0c0c8",
		poison: "#86d84a"
	};
	/** 戰場上表面蓋在地形上的顏色（半透明疊色，偏暗）；火取元素色。 */
	var SURFACE_GROUND_COLOR = {
		oil: "#2b2416",
		water: "#3a7bd5",
		fire: ELEMENT_COLORS["fire"].primary,
		ice: "#c8ecff",
		poison: "#7bc043",
		holy: "#fff1a8",
		darkness: "#3b1f4f",
		smoke: "#b8b8c0"
	};
	//#endregion
	//#region client/src/battle/glossary.ts
	var index = /* @__PURE__ */ new Map();
	/** 載入（或在測試中設定）名詞對照表。 */
	function setGlossary(g) {
		index.clear();
		for (const c of [
			"terrain",
			"surfaces",
			"objects",
			"statuses",
			"stacks",
			"reactions",
			"elements",
			"attributes",
			"effects",
			"conditions",
			"triggers",
			"actions",
			"objectives"
		]) index.set(c, new Map((g[c] ?? []).map((e) => [e.id, e])));
		weaponLooks.clear();
		for (const w of g.weapon_looks ?? []) weaponLooks.set(w.id, w);
	}
	/** 武器預設外觀（`/api/glossary` 的 `weapon_looks`；`weapons.yaml` 的 `look`）。 */
	var weaponLooks = /* @__PURE__ */ new Map();
	function glossaryEntry(category, id) {
		return index.get(category)?.get(id);
	}
	/** 中文名；對照表沒有時顯示 ID。 */
	function glossaryName(category, id) {
		return glossaryEntry(category, id)?.name_zh ?? id;
	}
	var statusName = (id) => glossaryName("statuses", id);
	/** 狀態圖示與身上特效用的欄位（`/api/glossary` 的 `status_look`）；沒有資料時為 `undefined`。 */
	var statusLook = (id) => glossaryEntry("statuses", id)?.status_look ?? void 0;
	var surfaceName = (id) => glossaryName("surfaces", id);
	var effectName = (id) => glossaryName("effects", id);
	var conditionName = (id) => glossaryName("conditions", id);
	var triggerName = (id) => glossaryName("triggers", id);
	/** 效果原語、條件、觸發的玩家說明（內容檔的 `player_description`／`description_zh`）；沒有時為空字串。 */
	var glossaryDescription = (category, id) => glossaryEntry(category, id)?.description_zh ?? "";
	/** 表面的顏色取自 `render/palette.ts`（單一來源），這裡只決定疊色比例。 */
	var ground$1 = (id, alpha) => ({
		color: parseInt((SURFACE_GROUND_COLOR[id] ?? "#888888").slice(1), 16),
		alpha
	});
	ground$1("oil", .6), ground$1("water", .55), ground$1("fire", .7), ground$1("ice", .7), ground$1("poison", .6), ground$1("holy", .6), ground$1("darkness", .65), ground$1("smoke", .6);
	Object.freeze({});
	//#endregion
	//#region client/src/render/material.ts
	/** 材質 → [主色, 暗色]；不認得的材質用布料色。 */
	var MATERIAL = {
		cloth: ["#8a8f99", "#5d6168"],
		leather: ["#8a5a32", "#5e3b1f"],
		iron: ["#7a828b", "#474c52"],
		steel: ["#a9b6c6", "#6d7a8a"],
		gold: ["#e8bb48", "#9c7420"],
		wood: ["#a06a36", "#6a4420"],
		bone: ["#e9e3cf", "#a8a08a"],
		copper: ["#b06a3c", "#6e3e20"],
		silver: ["#e8edf2", "#a8b0ba"],
		crystal: ["#b8a8ff", "#7a68c8"]
	};
	//#endregion
	//#region client/src/render/inkStyle.ts
	/**
	* 墨線畫風共用的材質色（Phase 3T-4）。金、木取自 `appearance.MATERIAL`（同一份）；
	* 鋼、鐵是墨線畫風專用的較亮金屬色（美術 PM 定案，與 `MATERIAL` 的 steel／iron 不同，改了會動所有小人的盔甲與劍）。
	*/
	var MAT = {
		steel: "#c3ccd6",
		iron: "#8d969f",
		gold: MATERIAL["gold"][0],
		wood: MATERIAL["wood"][0]
	};
	//#endregion
	//#region client/src/render/attackVariants.ts
	var PI = Math.PI;
	/** 由上往下（6N-5 以前唯一的弧光）。 */
	var ARC_DOWN = {
		kind: "arc",
		from: -.45 * PI,
		sweep: .9 * PI
	};
	var ARC_UP = {
		kind: "arc",
		from: .45 * PI,
		sweep: -.9 * PI
	};
	var ARC_ACROSS = {
		kind: "arc",
		from: .95 * PI,
		sweep: -.9 * PI,
		squash: .42
	};
	var ARC_RING = {
		kind: "ring",
		from: .5 * PI,
		sweep: -2 * PI,
		squash: .5
	};
	var line$2 = (angle) => ({
		kind: "line",
		angle
	});
	var REST$1 = {
		arm: 0,
		wpn: .75
	};
	var fx$2 = (kind, where, from = 0, to = 1) => ({
		kind,
		where,
		from,
		to
	});
	var STANCE = {
		hipN: .45,
		hipF: -.3
	};
	var LO = {
		arm: .9,
		wpn: -3.3,
		lean: -.1,
		hipN: .25,
		hipF: -.2,
		bob: 1.5
	};
	var SIDE = {
		arm: -1.2,
		wpn: -.4,
		lean: -.12,
		hipN: .2
	};
	var THRUST_BACK = {
		arm: .4,
		elbow: -1.2,
		wpn: 2.4,
		lean: -.08,
		hipN: .2
	};
	var HOP_IN = {
		arm: -2.7,
		wpn: 1.6,
		lean: -.05,
		kneeN: .7,
		kneeF: .7,
		bob: 2.5
	};
	var DRAW_IN = {
		arm: .6,
		elbow: -.9,
		wpn: -2.2,
		lean: .1,
		kneeN: .5,
		kneeF: .3,
		bob: 1.5
	};
	var TWIST = {
		arm: -1,
		wpn: -.4,
		lean: -.2,
		hipN: -.2,
		hipF: .3
	};
	var RUNE_UP = {
		arm: -2.9,
		wpn: 2.9,
		lean: -.06,
		bob: -.6
	};
	var CLEAVE_IN = {
		arm: -2.9,
		elbow: -.2,
		wpn: 2.4,
		armF: -2.6,
		lean: -.18,
		hipN: .3,
		hipF: -.25,
		bob: -.5
	};
	var HEAVY_SIDE = {
		arm: -1,
		wpn: -.5,
		armF: -1,
		lean: -.2,
		hipN: -.1,
		hipF: .25
	};
	var WHIRL_IN = {
		arm: -.2,
		wpn: -1.8,
		armF: -.2,
		lean: -.15,
		kneeN: .4,
		bob: 1
	};
	var STAB_IN = {
		arm: .4,
		elbow: -1.3,
		wpn: 2.4,
		armF: .3,
		elbowF: -1.3,
		lean: -.08
	};
	var PAIR_TWIST = {
		arm: -.9,
		wpn: -.5,
		armF: -.6,
		lean: -.2,
		hipN: -.2,
		hipF: .3
	};
	var BACKHAND_IN = {
		arm: -2.6,
		elbow: -.4,
		wpn: 6,
		armF: -1.2,
		lean: -.1
	};
	var LOW_IN = {
		arm: .6,
		wpn: 1.3,
		lean: .05,
		kneeN: .6,
		kneeF: .5,
		bob: 2
	};
	var SPEAR_SIDE = {
		arm: -1.3,
		wpn: -.3,
		lean: -.15,
		hipN: .2
	};
	var LEAP_IN = {
		arm: -2.2,
		wpn: 3,
		lean: -.05,
		kneeN: .8,
		kneeF: .8,
		bob: 2.5
	};
	var SCY_LIFT_IN = {
		arm: .6,
		wpn: -2.8,
		lean: -.1,
		kneeN: .4,
		bob: 1.2
	};
	var WHIP_UP_IN = {
		arm: .5,
		wpn: -2.4,
		lean: -.1,
		kneeN: .3,
		bob: 1
	};
	var WHIP_IN = {
		arm: -2.6,
		wpn: .4,
		lean: -.15
	};
	var WRAP_IN = {
		arm: -2,
		wpn: -.6,
		lean: -.1
	};
	var wind = (ms, to, extra = {}) => ({
		ms,
		anchor: "tip",
		keys: [[0, REST$1], [1, to]],
		...extra
	});
	var HOOK_IN = {
		arm: .1,
		elbow: -1.9,
		lean: -.15,
		hipN: -.15,
		hipF: .25
	};
	var UPPER_IN = {
		arm: .7,
		elbow: -1.5,
		lean: .08,
		kneeN: .5,
		kneeF: .4,
		bob: 2.2
	};
	var KNEE_IN = {
		arm: -.7,
		elbow: -1.5,
		armF: -.7,
		elbowF: -1.5,
		lean: -.05
	};
	var KICK_IN = {
		arm: -.6,
		elbow: -1.4,
		armF: .3,
		lean: -.25,
		hipN: -.2,
		hipF: .3
	};
	var AIM$1 = {
		arm: -1.3,
		wpn: 2.87,
		lean: -.05
	};
	/** 半蹲射：膝蓋彎、身體往下沉。 */
	var BOW_CROUCH = {
		kneeN: .9,
		kneeF: .7,
		hipN: .45,
		hipF: .1,
		bob: 4,
		lean: .06
	};
	/** 側身射：上半身往後仰、轉開。 */
	var BOW_SIDE = {
		lean: -.14,
		hipN: -.25,
		hipF: .35,
		arm: .05
	};
	/** 拋射：弓往上抬約 45 度（武器絕對角度 ≈ π/4）。 */
	var BOW_LOB = {
		arm: -.6,
		wpn: -.2,
		lean: -.15
	};
	/** 腰射：手放低、手肘彎，槍身仍水平（arm＋elbow＋wpn 不變）。 */
	var GUN_HIP = {
		arm: .8,
		elbow: -.85,
		wpn: .05,
		lean: .05
	};
	/** 單膝射：前腳跪下。 */
	var GUN_KNEEL = {
		kneeN: 1.6,
		hipN: 1,
		kneeF: .4,
		bob: 5,
		lean: .05
	};
	/** 姿勢逐欄相加（遠程變體 ＝ 原本的瞄準、放箭姿勢 ＋ 一組差值，後座的形狀跟著原本的）。 */
	function plus$1(p, d) {
		const out = { ...p };
		for (const [k, v] of Object.entries(d)) out[k] = (p[k] ?? 0) + v;
		return out;
	}
	/**
	* 遠程變體的蓄力＋出招：照起手對照表的弓（aim／release）或弩、火槍（aim_gun／fire）的關鍵點，每個姿勢加上 `delta`
	* （開頭的站好不加），後座那一格（0.15）再加 `kick`。長度、`hitAt`、特效（火槍的槍口火光）都和原本的一樣。
	*/
	function rangedPair(name, base, delta, kick) {
		const a = plus$1(AIM$1, delta);
		const windup = base === "bow" ? {
			ms: 360,
			anchor: "tip",
			keys: [
				[0, REST$1],
				[.6, a],
				[1, {
					...a,
					pull: 6
				}]
			]
		} : {
			ms: 340,
			anchor: "tip",
			keys: [
				[0, REST$1],
				[.7, a],
				[1, a]
			]
		};
		const strike = base === "bow" ? {
			ms: 300,
			anchor: "tip",
			hitAt: .15,
			keys: [
				[0, {
					...a,
					pull: 6
				}],
				[.15, plus$1(plus$1({
					arm: -1.45,
					wpn: 2.77,
					lean: -.08,
					pull: 0
				}, delta), kick)],
				[1, {
					...a,
					pull: 0
				}]
			]
		} : {
			ms: 260,
			anchor: "tip",
			hitAt: .15,
			keys: [
				[0, a],
				[.15, plus$1(plus$1({
					arm: -1.6,
					wpn: 2.77,
					lean: -.12
				}, delta), kick)],
				[1, a]
			],
			fx: [fx$2("muzzle", "anchor", .1, .45)]
		};
		return {
			[`${name}_in`]: windup,
			[name]: strike
		};
	}
	wind(260, LO), { ...STANCE }, { ...STANCE }, wind(260, SIDE), { ...STANCE }, { ...STANCE }, wind(260, THRUST_BACK), wind(260, HOP_IN), wind(260, DRAW_IN), wind(260, TWIST), { ...STANCE }, { ...STANCE }, wind(280, SIDE, { fx: [fx$2("glow", "anchor", .3, 1)] }), wind(280, THRUST_BACK, { fx: [fx$2("glow", "anchor", .3, 1)] }), wind(280, RUNE_UP, { fx: [fx$2("glow", "anchor", .2, 1), fx$2("sigil", "anchor", .45, 1)] }), { ...STANCE }, { ...STANCE }, wind(260, CLEAVE_IN), wind(260, HEAVY_SIDE), { ...STANCE }, { ...STANCE }, wind(260, WHIRL_IN), { ...STANCE }, { ...STANCE }, wind(260, STAB_IN), { ...STANCE }, { ...STANCE }, wind(260, PAIR_TWIST), { ...STANCE }, { ...STANCE }, wind(260, BACKHAND_IN), { ...STANCE }, { ...STANCE }, wind(220, LOW_IN), wind(220, SPEAR_SIDE), { ...STANCE }, { ...STANCE }, wind(220, LEAP_IN), wind(260, SIDE), wind(260, SCY_LIFT_IN), wind(260, TWIST), { ...STANCE }, { ...STANCE }, wind(240, WHIP_UP_IN), wind(240, WHIP_IN), wind(240, WRAP_IN), wind(200, HOOK_IN, { anchor: "hand" }), { ...STANCE }, { ...STANCE }, wind(200, UPPER_IN, { anchor: "hand" }), wind(200, KNEE_IN, { anchor: "chest" }), wind(200, KICK_IN, { anchor: "feet" }), {
		...rangedPair("bow_crouch", "bow", BOW_CROUCH, {}),
		...rangedPair("bow_side", "bow", BOW_SIDE, { lean: -.03 }),
		...rangedPair("bow_lob", "bow", BOW_LOB, { arm: -.05 }),
		...rangedPair("gun_hip", "gun", GUN_HIP, { elbow: -.15 }),
		...rangedPair("gun_kneel", "gun", GUN_KNEEL, { lean: -.04 })
	};
	var v = (id, zh, windup, strike, swing, arc) => ({
		id,
		zh,
		windup,
		strike,
		swing,
		arc
	});
	/**
	* 變體表（方案 2.10 第 5 點的例子）。每列第一個 ＝ 6N-6 以前的普攻（起手對照表的近身那一欄），弧光照舊由上往下或照揮的方向。
	*/
	var MELEE_VARIANTS = {
		sword: [
			v("sword_down", "由上往下", "windup", "slash", "down", ARC_DOWN),
			v("sword_up", "由下往上", "windup_lo", "slash_lo", "up", ARC_UP),
			v("sword_across", "橫掃", "windup_side", "slash_side", "across", ARC_ACROSS),
			v("sword_thrust", "突刺", "sword_thrust_in", "sword_thrust", "thrust", line$2(0)),
			v("sword_hop", "小跳斬", "hop_in", "hop_slash", "down", {
				kind: "arc",
				from: -.55 * PI,
				sweep: .8 * PI
			})
		],
		saber: [
			v("saber_down", "由上往下", "windup", "slash", "down", ARC_DOWN),
			v("saber_up", "由下往上", "windup_lo", "slash_lo", "up", ARC_UP),
			v("saber_across", "橫掃", "windup_side", "slash_side", "across", ARC_ACROSS),
			v("saber_draw", "拔刀斬", "draw_in", "draw_slash", "up", {
				kind: "arc",
				from: .6 * PI,
				sweep: -.75 * PI
			}),
			v("saber_spin", "迴身斬", "spin_in", "spin_slash", "spin", ARC_RING)
		],
		arcane: [
			v("arcane_down", "由上往下", "arcane_windup", "slash", "down", ARC_DOWN),
			v("arcane_across", "橫掃", "arcane_side_in", "slash_side", "across", ARC_ACROSS),
			v("arcane_thrust", "突刺", "arcane_thrust_in", "sword_thrust", "thrust", line$2(0)),
			v("arcane_rune", "符文一亮再斬", "rune_in", "rune_slash", "down", {
				kind: "arc",
				from: -.5 * PI,
				sweep: .75 * PI
			})
		],
		heavy: [
			v("heavy_cleave", "劈", "cleave_in", "cleave", "down", {
				kind: "arc",
				from: -.55 * PI,
				sweep: .85 * PI
			}),
			v("heavy_across", "橫掃", "heavy_side_in", "heavy_sweep", "across", ARC_ACROSS),
			v("heavy_whirl", "掄一圈", "whirl_in", "whirl", "spin", {
				kind: "ring",
				from: PI,
				sweep: 2 * PI,
				squash: 1
			})
		],
		pair: [
			v("pair_cross", "交叉斬", "x_windup", "twin_slash", "down", {
				kind: "cross",
				angle: .3 * PI,
				angle2: .7 * PI
			}),
			v("pair_stab", "連刺", "pair_stab_in", "pair_stab", "thrust", line$2(0)),
			v("pair_spin", "迴旋", "pair_spin_in", "pair_spin", "spin", ARC_RING),
			v("pair_backhand", "反手刺", "backhand_in", "backhand_stab", "down", line$2(.4 * PI))
		],
		spear: [
			v("spear_thrust", "直刺", "thrust_in", "thrust", "thrust", line$2(0)),
			v("spear_low", "下段刺", "low_thrust_in", "low_thrust", "thrust", line$2(.15 * PI)),
			v("spear_across", "橫掃", "spear_side_in", "spear_sweep", "across", ARC_ACROSS),
			v("spear_leap", "跳刺", "leap_thrust_in", "leap_thrust", "thrust", line$2(.3 * PI))
		],
		scythe: [
			v("scythe_across", "橫掃", "scythe_side_in", "sweep", "across", ARC_ACROSS),
			v("scythe_lift", "上挑", "scythe_lift_in", "scythe_lift", "up", ARC_UP),
			v("scythe_spin", "迴旋", "scythe_spin_in", "scythe_spin", "spin", ARC_RING)
		],
		whip: [
			v("whip_up", "上甩", "whip_up_in", "whip_up", "up", ARC_UP),
			v("whip_side", "側甩", "whip_side_in", "whip_lash", "across", ARC_ACROSS),
			v("whip_wrap", "纏繞拉扯", "whip_wrap_in", "whip_wrap", "spin", ARC_RING)
		]
	};
	/** 6N-7 的列（每列第一個 ＝ 6N-7 以前的普攻：拳套空手照近身那一欄，弓、弩、火槍照遠程那一欄）。 */
	var MORE_VARIANTS = {
		fist: [
			v("fist_jab", "直拳", "fist_in", "punch", "thrust", line$2(0)),
			v("fist_hook", "勾拳", "hook_in", "hook", "across", ARC_ACROSS),
			v("fist_upper", "上勾拳", "upper_in", "uppercut", "up", ARC_UP),
			v("fist_knee", "膝撞", "knee_in", "knee_strike", "up", line$2(-.3 * PI)),
			v("fist_kick", "迴旋踢", "kick_in", "spin_kick", "spin", ARC_RING)
		],
		bow: [
			v("bow_stand", "站射", "aim", "release", "shoot", null),
			v("bow_crouch", "半蹲射", "bow_crouch_in", "bow_crouch", "shoot", null),
			v("bow_side", "側身射", "bow_side_in", "bow_side", "shoot", null),
			v("bow_lob", "拋射", "bow_lob_in", "bow_lob", "shoot", null)
		],
		crossbow: [
			v("crossbow_shoulder", "抵肩射", "aim_gun", "fire", "shoot", null),
			v("crossbow_hip", "腰射", "gun_hip_in", "gun_hip", "shoot", null),
			v("crossbow_kneel", "單膝射", "gun_kneel_in", "gun_kneel", "shoot", null)
		],
		gun: [
			v("gun_shoulder", "抵肩射", "aim_gun", "fire", "shoot", null),
			v("gun_hip", "腰射", "gun_hip_in", "gun_hip", "shoot", null),
			v("gun_kneel", "單膝射", "gun_kneel_in", "gun_kneel", "shoot", null)
		]
	};
	({
		...MELEE_VARIANTS,
		...MORE_VARIANTS
	});
	Object.freeze({
		hipN: .35,
		kneeN: .55,
		hipF: .1,
		kneeF: .3,
		arm: -1.9,
		elbow: -.3,
		armF: -1.5,
		liftL: 1.5,
		armL: -1.2,
		armR: -1.2
	});
	Object.freeze({
		hipN: .45,
		kneeN: .15,
		hipF: -.35,
		kneeF: .35,
		arm: -1.1,
		armF: -.9,
		elbow: -.2,
		liftL: 1.2,
		armL: -1.4,
		armR: -1.4
	});
	//#endregion
	//#region client/src/render/artPalette.ts
	/** 圖示描邊色。 */
	var GEAR_INK = "#16181d";
	Object.fromEntries(Object.entries(MATERIAL).map(([id, c]) => [id, id === "silver" ? {
		c,
		shine: true
	} : { c }]));
	var gearAppearance_default = {
		styles: ["common"],
		materials: [
			"iron",
			"steel",
			"copper",
			"silver",
			"gold",
			"wood",
			"leather",
			"cloth",
			"bone",
			"crystal"
		],
		dyes: [
			"red",
			"blue",
			"green",
			"purple",
			"black",
			"white",
			"brown",
			"gold"
		],
		dyeMaterials: ["cloth", "leather"],
		rarities: [
			"common",
			"uncommon",
			"rare",
			"epic",
			"legendary"
		],
		maxKeywords: 2,
		keywords: [
			"ignite",
			"wet",
			"charged",
			"frozen",
			"prone",
			"collision",
			"marked",
			"high_ground",
			"concealed",
			"summon",
			"poisoned",
			"form"
		],
		elementKeywords: [
			"ignite",
			"wet",
			"charged",
			"frozen"
		],
		kinds: [
			{
				"id": "sword",
				"slotType": "weapon",
				"zh": "劍",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "straight",
						"zh": "直劍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "curved",
						"zh": "彎刀",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "broad",
						"zh": "闊劍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "arcane",
						"zh": "魔導劍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "greatsword",
				"slotType": "weapon",
				"zh": "巨劍",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "twohand",
						"zh": "雙手劍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "zhanma",
						"zh": "斬馬刀",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "serrated",
						"zh": "鋸齒巨劍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "dagger",
				"slotType": "weapon",
				"zh": "匕首",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "short",
						"zh": "短刀",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "stiletto",
						"zh": "三稜刺",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "kris",
						"zh": "彎匕",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "axe",
				"slotType": "weapon",
				"zh": "斧",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "hand",
						"zh": "手斧",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "battle",
						"zh": "戰斧",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "double",
						"zh": "雙刃斧",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "hammer",
				"slotType": "weapon",
				"zh": "錘",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "mace",
						"zh": "釘頭錘",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "warhammer",
						"zh": "戰錘",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "flail",
						"zh": "連枷",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "spear",
				"slotType": "weapon",
				"zh": "矛",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"wood"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "spear",
						"zh": "長矛",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"wood"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "halberd",
						"zh": "戟",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"wood"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "trident",
						"zh": "三叉戟",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"wood"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "bow",
				"slotType": "weapon",
				"zh": "弓",
				"paired": false,
				"materials": [
					"wood",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "wood",
				"forms": [
					{
						"id": "short",
						"zh": "短弓",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "long",
						"zh": "長弓",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "recurve",
						"zh": "反曲弓",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					}
				]
			},
			{
				"id": "crossbow",
				"slotType": "weapon",
				"zh": "弩",
				"paired": false,
				"materials": [
					"wood",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "wood",
				"forms": [
					{
						"id": "light",
						"zh": "輕弩",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "heavy",
						"zh": "重弩",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "repeater",
						"zh": "連弩",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					}
				]
			},
			{
				"id": "longgun",
				"slotType": "weapon",
				"zh": "火槍",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [
					{
						"id": "flintlock",
						"zh": "燧發火槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "hunting",
						"zh": "獵槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "sniper",
						"zh": "狙擊火槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					}
				]
			},
			{
				"id": "shotgun",
				"slotType": "weapon",
				"zh": "霰彈槍",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "blunderbuss",
						"zh": "喇叭槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "double",
						"zh": "雙管",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "pump",
						"zh": "泵動",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "pistol",
				"slotType": "weapon",
				"zh": "手槍",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [
					{
						"id": "flintlock",
						"zh": "燧發手槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "revolver",
						"zh": "左輪",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "derringer",
						"zh": "短銃",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					}
				]
			},
			{
				"id": "dual_pistol",
				"slotType": "weapon",
				"zh": "雙手槍",
				"paired": true,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [
					{
						"id": "flintlock",
						"zh": "燧發手槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "revolver",
						"zh": "左輪",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "derringer",
						"zh": "短銃",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					}
				]
			},
			{
				"id": "fist",
				"slotType": "weapon",
				"zh": "拳套",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"leather"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "katar",
						"zh": "拳刃",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"leather"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "knuckle",
						"zh": "鐵拳",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"leather"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "claw",
						"zh": "爪",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"leather"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "scythe",
				"slotType": "weapon",
				"zh": "鐮刀",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "long",
						"zh": "長柄鐮",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "crescent",
						"zh": "彎月鐮",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "hook",
						"zh": "鉤鐮",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "whip",
				"slotType": "weapon",
				"zh": "鞭",
				"paired": false,
				"materials": [
					"leather",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone"
				],
				"defaultMaterial": "leather",
				"forms": [
					{
						"id": "leather",
						"zh": "皮鞭",
						"materials": [
							"leather",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "leather"
					},
					{
						"id": "chain",
						"zh": "鏈鞭",
						"materials": [
							"leather",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "leather"
					},
					{
						"id": "bladed",
						"zh": "蛇骨鞭",
						"materials": [
							"leather",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "leather"
					}
				]
			},
			{
				"id": "dual_dagger",
				"slotType": "weapon",
				"zh": "雙匕首",
				"paired": true,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "short",
						"zh": "短刀",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "stiletto",
						"zh": "三稜刺",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "kris",
						"zh": "彎匕",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "staff",
				"slotType": "weapon",
				"zh": "杖",
				"paired": false,
				"materials": [
					"wood",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "wood",
				"forms": [
					{
						"id": "long",
						"zh": "長杖",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "scepter",
						"zh": "權杖",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "wand",
						"zh": "短杖",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "totem",
						"zh": "圖騰杖",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "wood"
					}
				]
			},
			{
				"id": "round_shield",
				"slotType": "offhand",
				"zh": "圓盾",
				"paired": false,
				"materials": [
					"wood",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "wood",
				"forms": [{
					"id": "wood",
					"zh": "木圓盾",
					"materials": [
						"wood",
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "wood"
				}, {
					"id": "banded",
					"zh": "包鐵圓盾",
					"materials": [
						"wood",
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "wood"
				}]
			},
			{
				"id": "kite_shield",
				"slotType": "offhand",
				"zh": "鳶盾",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [{
					"id": "kite",
					"zh": "鳶盾",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}, {
					"id": "tower",
					"zh": "塔盾",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}]
			},
			{
				"id": "tome",
				"slotType": "offhand",
				"zh": "法書",
				"paired": false,
				"materials": ["leather", "cloth"],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "book",
					"zh": "典籍",
					"materials": ["leather", "cloth"],
					"defaultMaterial": "leather"
				}, {
					"id": "scroll",
					"zh": "卷軸匣",
					"materials": ["leather", "cloth"],
					"defaultMaterial": "leather"
				}]
			},
			{
				"id": "orb",
				"slotType": "offhand",
				"zh": "法器珠",
				"paired": false,
				"materials": ["crystal", "bone"],
				"defaultMaterial": "crystal",
				"forms": [{
					"id": "ball",
					"zh": "水晶球",
					"materials": ["crystal", "bone"],
					"defaultMaterial": "crystal"
				}, {
					"id": "floating",
					"zh": "浮空寶珠",
					"materials": ["crystal", "bone"],
					"defaultMaterial": "crystal"
				}]
			},
			{
				"id": "robe",
				"slotType": "body",
				"zh": "布袍",
				"paired": false,
				"materials": ["cloth"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "long",
					"zh": "長袍",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}, {
					"id": "short",
					"zh": "短袍",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "leather",
				"slotType": "body",
				"zh": "皮甲",
				"paired": false,
				"materials": ["leather"],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "vest",
					"zh": "皮背心",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}, {
					"id": "hunter",
					"zh": "獵裝",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}]
			},
			{
				"id": "mail",
				"slotType": "body",
				"zh": "鎖甲",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [{
					"id": "chain",
					"zh": "鎖子甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}, {
					"id": "scale",
					"zh": "鱗甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}]
			},
			{
				"id": "plate",
				"slotType": "body",
				"zh": "板甲",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [{
					"id": "half",
					"zh": "半身板甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}, {
					"id": "full",
					"zh": "全身板甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}]
			},
			{
				"id": "coat",
				"slotType": "body",
				"zh": "外套",
				"paired": false,
				"materials": ["cloth", "leather"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "travel",
					"zh": "旅行外套",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}, {
					"id": "cape",
					"zh": "披風外套",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "hood",
				"slotType": "head",
				"zh": "兜帽",
				"paired": false,
				"materials": ["cloth", "leather"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "cloth",
					"zh": "布兜帽",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}, {
					"id": "cowl",
					"zh": "斗篷帽",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "hat",
				"slotType": "head",
				"zh": "帽子",
				"paired": false,
				"materials": ["cloth", "leather"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "wizard",
					"zh": "法師帽",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}, {
					"id": "wide",
					"zh": "寬簷帽",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "circlet",
				"slotType": "head",
				"zh": "頭巾／頭冠",
				"paired": false,
				"materials": [
					"cloth",
					"leather",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "bandana",
					"zh": "頭巾",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}, {
					"id": "crown",
					"zh": "頭冠",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold",
						"bone",
						"crystal"
					],
					"defaultMaterial": "gold"
				}]
			},
			{
				"id": "cap",
				"slotType": "head",
				"zh": "皮帽",
				"paired": false,
				"materials": ["leather", "cloth"],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "leather",
					"zh": "皮帽",
					"materials": ["leather", "cloth"],
					"defaultMaterial": "leather"
				}, {
					"id": "fur",
					"zh": "毛帽",
					"materials": ["leather", "cloth"],
					"defaultMaterial": "leather"
				}]
			},
			{
				"id": "helmet",
				"slotType": "head",
				"zh": "頭盔",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "iron",
						"zh": "鐵盔",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "horned",
						"zh": "角盔",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "greathelm",
						"zh": "全罩盔",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "cloth_gloves",
				"slotType": "hands",
				"zh": "布手套",
				"paired": false,
				"materials": ["cloth"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "plain",
					"zh": "素手套",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}, {
					"id": "fingerless",
					"zh": "露指手套",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "leather_gloves",
				"slotType": "hands",
				"zh": "皮手套",
				"paired": false,
				"materials": ["leather"],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "short",
					"zh": "短皮手套",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}, {
					"id": "long",
					"zh": "長皮手套",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}]
			},
			{
				"id": "gauntlets",
				"slotType": "hands",
				"zh": "護手",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [{
					"id": "plate",
					"zh": "板金護手",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}, {
					"id": "mail",
					"zh": "鎖鏈護手",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}]
			},
			{
				"id": "bracers",
				"slotType": "hands",
				"zh": "臂甲",
				"paired": false,
				"materials": [
					"leather",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "leather",
					"zh": "皮臂甲",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}, {
					"id": "ring",
					"zh": "臂環",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "copper"
				}]
			},
			{
				"id": "shoes",
				"slotType": "feet",
				"zh": "布鞋",
				"paired": false,
				"materials": ["cloth"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "slipper",
					"zh": "布鞋",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}, {
					"id": "wrapped",
					"zh": "綁腿鞋",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "boots",
				"slotType": "feet",
				"zh": "皮靴",
				"paired": false,
				"materials": ["leather"],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "short",
					"zh": "短靴",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}, {
					"id": "tall",
					"zh": "長靴",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}]
			},
			{
				"id": "iron_boots",
				"slotType": "feet",
				"zh": "鐵靴",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [{
					"id": "plain",
					"zh": "鐵靴",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}, {
					"id": "sabaton",
					"zh": "尖頭鐵靴",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}]
			},
			{
				"id": "greaves",
				"slotType": "feet",
				"zh": "脛甲",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [{
					"id": "plain",
					"zh": "脛甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}, {
					"id": "knee",
					"zh": "護膝脛甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}]
			},
			{
				"id": "ring",
				"slotType": "ring",
				"zh": "戒指",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "gold",
				"forms": [
					{
						"id": "plain",
						"zh": "素戒",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "gold"
					},
					{
						"id": "gem",
						"zh": "寶石戒",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "gold"
					},
					{
						"id": "signet",
						"zh": "印戒",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "gold"
					}
				]
			},
			{
				"id": "pendant",
				"slotType": "neck",
				"zh": "墜飾",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "gold",
				"forms": [{
					"id": "pendant",
					"zh": "項鍊墜",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold",
						"bone",
						"crystal"
					],
					"defaultMaterial": "gold"
				}, {
					"id": "tag",
					"zh": "吊牌",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold",
						"bone",
						"crystal"
					],
					"defaultMaterial": "gold"
				}]
			},
			{
				"id": "charm",
				"slotType": "neck",
				"zh": "護符",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal",
					"leather",
					"cloth"
				],
				"defaultMaterial": "gold",
				"forms": [{
					"id": "tablet",
					"zh": "符牌",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold",
						"bone",
						"crystal",
						"leather",
						"cloth"
					],
					"defaultMaterial": "gold"
				}, {
					"id": "bone",
					"zh": "骨符",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold",
						"bone",
						"crystal",
						"leather",
						"cloth"
					],
					"defaultMaterial": "gold"
				}]
			}
		]
	};
	//#endregion
	//#region client/src/render/gearIcon.ts
	var TAU$4 = Math.PI * 2;
	var INK = GEAR_INK;
	/** 魔導劍源晶槽的預設顏色（無元素；有元素時紙娃娃畫法換成元素色，見 `paperdoll.ts`）。 */
	var ARCANE_GLOW = "#9a86ff";
	Object.fromEntries(gearAppearance_default.kinds.map((k) => [k.id, k]));
	gearAppearance_default.maxKeywords;
	/** 造型清單（供預覽頁與測試用）。 */
	function gearKinds() {
		return gearAppearance_default.kinds;
	}
	function shape(ctx, fillC, path, lw = 2) {
		ctx.beginPath();
		path();
		ctx.fillStyle = fillC;
		ctx.fill();
		ctx.lineWidth = lw;
		ctx.strokeStyle = INK;
		ctx.stroke();
	}
	function line$1(ctx, c, w, pts) {
		const [first, ...rest] = pts;
		if (first === void 0) return;
		ctx.beginPath();
		ctx.moveTo(first[0], first[1]);
		for (const p of rest) ctx.lineTo(p[0], p[1]);
		ctx.strokeStyle = c;
		ctx.lineWidth = w;
		ctx.stroke();
	}
	function diag(ctx, fn) {
		ctx.save();
		ctx.translate(32, 33);
		ctx.rotate(Math.PI / 4);
		fn();
		ctx.restore();
	}
	function grip(ctx, P, y0, len) {
		shape(ctx, P.handle, () => ctx.roundRect(-2.5, y0, 5, len, 1.5), 1.5);
		ctx.strokeStyle = "rgba(0,0,0,0.35)";
		ctx.lineWidth = 1;
		for (let y = y0 + 2.5; y < y0 + len - 1; y += 3) {
			ctx.beginPath();
			ctx.moveTo(-2.5, y);
			ctx.lineTo(2.5, y + 1.2);
			ctx.stroke();
		}
	}
	function guard(ctx, P, y, w) {
		shape(ctx, P.guard, () => ctx.roundRect(-w / 2, y, w, 4, 2), 1.5);
	}
	function shine(ctx, P, pts) {
		if (P.shine) line$1(ctx, "rgba(255,255,255,0.95)", 1.4, pts);
	}
	function gem(ctx, x, y, r, c) {
		shape(ctx, c, () => {
			ctx.moveTo(x, y - r);
			ctx.lineTo(x + r, y);
			ctx.lineTo(x, y + r);
			ctx.lineTo(x - r, y);
			ctx.closePath();
		}, 1.5);
		ctx.fillStyle = "rgba(255,255,255,0.55)";
		ctx.beginPath();
		ctx.moveTo(x, y - r);
		ctx.lineTo(x + r * .5, y - r * .2);
		ctx.lineTo(x, y);
		ctx.closePath();
		ctx.fill();
	}
	var D = {};
	D.sword = (ctx, r, P) => {
		diag(ctx, () => {
			const blade = {
				straight: () => {
					ctx.moveTo(-3.5, 8);
					ctx.lineTo(-3.5, -22);
					ctx.lineTo(0, -28);
					ctx.lineTo(3.5, -22);
					ctx.lineTo(3.5, 8);
					ctx.closePath();
				},
				curved: () => {
					ctx.moveTo(-3, 8);
					ctx.quadraticCurveTo(-6, -12, 6, -28);
					ctx.quadraticCurveTo(4, -10, 4, 8);
					ctx.closePath();
				},
				broad: () => {
					ctx.moveTo(-6, 8);
					ctx.lineTo(-6, -18);
					ctx.lineTo(0, -28);
					ctx.lineTo(6, -18);
					ctx.lineTo(6, 8);
					ctx.closePath();
				},
				arcane: () => {
					ctx.moveTo(-3.5, 8);
					ctx.lineTo(-3.5, -22);
					ctx.lineTo(0, -28);
					ctx.lineTo(3.5, -22);
					ctx.lineTo(3.5, 8);
					ctx.closePath();
				}
			}[r.form];
			shape(ctx, P.a, blade ?? (() => void 0));
			if (r.form === "arcane") {
				ctx.save();
				ctx.shadowColor = ARCANE_GLOW;
				ctx.shadowBlur = 5;
				line$1(ctx, ARCANE_GLOW, 2.4, [[0, 5], [0, -22]]);
				ctx.restore();
			} else if (r.form !== "curved") line$1(ctx, P.d, 1.2, [[0, 6], [0, -20]]);
			shine(ctx, P, [[-1.5, 4], [-1.5, -18]]);
			if (r.form === "arcane") {
				shape(ctx, "#b08a4a", () => {
					for (let i = 0; i < 12; i += 1) {
						const a = i / 12 * TAU$4;
						const k = i % 2 === 0 ? 7.5 : 5.6;
						ctx.lineTo(Math.cos(a) * k, 10 + Math.sin(a) * k * .6);
					}
					ctx.closePath();
				}, 1.5);
				ctx.fillStyle = ARCANE_GLOW;
				ctx.beginPath();
				ctx.arc(0, 10, 2, 0, TAU$4);
				ctx.fill();
			} else guard(ctx, P, 8, r.form === "broad" ? 22 : 18);
			grip(ctx, P, 12, 10);
			shape(ctx, P.guard, () => ctx.arc(0, 24, 2.5, 0, TAU$4), 1.2);
		});
		return [[36, 26], [28, 36]];
	};
	D.greatsword = (ctx, r, P) => {
		diag(ctx, () => {
			if (r.form === "twohand") shape(ctx, P.a, () => {
				ctx.moveTo(-4.5, 5);
				ctx.lineTo(-4.5, -27);
				ctx.lineTo(0, -32);
				ctx.lineTo(4.5, -27);
				ctx.lineTo(4.5, 5);
				ctx.closePath();
			});
			else if (r.form === "zhanma") shape(ctx, P.a, () => {
				ctx.moveTo(-4, 5);
				ctx.lineTo(-4, -26);
				ctx.quadraticCurveTo(-1, -33, 7, -31);
				ctx.lineTo(6, 5);
				ctx.closePath();
			});
			else shape(ctx, P.a, () => {
				ctx.moveTo(-5, 5);
				ctx.lineTo(-5, -26);
				ctx.lineTo(0, -32);
				ctx.lineTo(5, -26);
				for (let y = -22; y < 5; y += 5) {
					ctx.lineTo(8, y);
					ctx.lineTo(5, y + 2.5);
				}
				ctx.lineTo(5, 5);
				ctx.closePath();
			});
			line$1(ctx, P.d, 1.2, [[0, 3], [0, -25]]);
			shine(ctx, P, [[-2, 2], [-2, -24]]);
			guard(ctx, P, 5, 20);
			grip(ctx, P, 9, 16);
		});
		return [[38, 22], [30, 32]];
	};
	D.dagger = (ctx, r, P) => {
		diag(ctx, () => {
			if (r.form === "short") shape(ctx, P.a, () => {
				ctx.moveTo(-3.5, 6);
				ctx.lineTo(-3.5, -10);
				ctx.lineTo(0, -16);
				ctx.lineTo(3.5, -10);
				ctx.lineTo(3.5, 6);
				ctx.closePath();
			});
			else if (r.form === "stiletto") shape(ctx, P.a, () => {
				ctx.moveTo(-2.5, 6);
				ctx.lineTo(0, -20);
				ctx.lineTo(2.5, 6);
				ctx.closePath();
			});
			else shape(ctx, P.a, () => {
				ctx.moveTo(-3, 6);
				ctx.quadraticCurveTo(-5, -4, 0, -8);
				ctx.quadraticCurveTo(5, -12, 2, -18);
				ctx.quadraticCurveTo(9, -10, 3, -3);
				ctx.lineTo(3, 6);
				ctx.closePath();
			});
			shine(ctx, P, [[-1, 4], [-1, -10]]);
			guard(ctx, P, 6, 14);
			grip(ctx, P, 10, 9);
		});
		return [[33, 30], [27, 34]];
	};
	D.axe = (ctx, r, P) => {
		diag(ctx, () => {
			shape(ctx, P.handle, () => ctx.roundRect(-2.5, -24, 5, 46, 2), 1.5);
			const head = (s) => () => {
				ctx.moveTo(2, -22);
				ctx.quadraticCurveTo(14 * s, -28, 16 * s, -14);
				ctx.quadraticCurveTo(12 * s, -12, 2, -10);
				ctx.closePath();
			};
			if (r.form === "hand") {
				ctx.save();
				ctx.scale(.8, .8);
				shape(ctx, P.a, head(1));
				ctx.restore();
			} else if (r.form === "battle") shape(ctx, P.a, () => {
				ctx.moveTo(2, -26);
				ctx.quadraticCurveTo(20, -32, 20, -12);
				ctx.quadraticCurveTo(14, -6, 2, -8);
				ctx.closePath();
			});
			else {
				shape(ctx, P.a, head(1));
				ctx.save();
				ctx.scale(-1, 1);
				shape(ctx, P.a, head(1));
				ctx.restore();
			}
			shine(ctx, P, [[8, -22], [13, -16]]);
		});
		return [[40, 20], [24, 40]];
	};
	D.hammer = (ctx, r, P) => {
		diag(ctx, () => {
			shape(ctx, P.handle, () => ctx.roundRect(-2.5, -14, 5, 36, 2), 1.5);
			if (r.form === "mace") {
				for (let i = 0; i < 8; i++) {
					const a = i / 8 * TAU$4;
					shape(ctx, P.d, () => {
						ctx.moveTo(Math.cos(a) * 7, -20 + Math.sin(a) * 7);
						ctx.lineTo(Math.cos(a + .25) * 12, -20 + Math.sin(a + .25) * 12);
						ctx.lineTo(Math.cos(a + .5) * 7, -20 + Math.sin(a + .5) * 7);
					}, 1);
				}
				shape(ctx, P.a, () => ctx.arc(0, -20, 8, 0, TAU$4));
			} else if (r.form === "warhammer") {
				shape(ctx, P.a, () => ctx.roundRect(-11, -26, 22, 12, 2));
				line$1(ctx, P.d, 1.5, [[-11, -20], [11, -20]]);
			} else {
				line$1(ctx, INK, 3.5, [
					[0, -14],
					[6, -20],
					[4, -26]
				]);
				line$1(ctx, P.d, 2, [
					[0, -14],
					[6, -20],
					[4, -26]
				]);
				for (let i = 0; i < 8; i++) {
					const a = i / 8 * TAU$4;
					shape(ctx, P.d, () => {
						ctx.moveTo(4 + Math.cos(a) * 5, -31 + Math.sin(a) * 5);
						ctx.lineTo(4 + Math.cos(a + .3) * 9, -31 + Math.sin(a + .3) * 9);
						ctx.lineTo(4 + Math.cos(a + .6) * 5, -31 + Math.sin(a + .6) * 5);
					}, 1);
				}
				shape(ctx, P.a, () => ctx.arc(4, -31, 6, 0, TAU$4));
			}
			shine(ctx, P, [[-4, -24], [-1, -24]]);
		});
		return [[40, 18], [28, 38]];
	};
	D.spear = (ctx, r, P) => {
		diag(ctx, () => {
			shape(ctx, P.handle, () => ctx.roundRect(-2, -18, 4, 46, 2), 1.5);
			if (r.form === "spear") shape(ctx, P.a, () => {
				ctx.moveTo(0, -32);
				ctx.quadraticCurveTo(6, -22, 0, -16);
				ctx.quadraticCurveTo(-6, -22, 0, -32);
			});
			else if (r.form === "halberd") {
				shape(ctx, P.a, () => {
					ctx.moveTo(0, -33);
					ctx.lineTo(3, -18);
					ctx.lineTo(-3, -18);
					ctx.closePath();
				});
				shape(ctx, P.a, () => {
					ctx.moveTo(2, -26);
					ctx.quadraticCurveTo(14, -28, 13, -16);
					ctx.lineTo(2, -18);
					ctx.closePath();
				});
			} else {
				shape(ctx, P.a, () => ctx.roundRect(-8, -20, 16, 3, 1), 1.5);
				for (const x of [
					-7,
					0,
					7
				]) shape(ctx, P.a, () => {
					ctx.moveTo(x, -32);
					ctx.lineTo(x + 2, -20);
					ctx.lineTo(x - 2, -20);
					ctx.closePath();
				}, 1.5);
			}
			shine(ctx, P, [[-1, -28], [-1, -20]]);
		});
		return [[42, 18], [26, 40]];
	};
	D.bow = (ctx, r, P) => {
		const L = r.form === "long" ? 26 : 20;
		ctx.save();
		ctx.translate(30, 32);
		ctx.beginPath();
		if (r.form === "recurve") {
			ctx.moveTo(4, -L);
			ctx.quadraticCurveTo(-2, -L + 4, 8, -L / 2);
			ctx.quadraticCurveTo(16, 0, 8, L / 2);
			ctx.quadraticCurveTo(-2, L - 4, 4, L);
		} else {
			ctx.moveTo(0, -L);
			ctx.quadraticCurveTo(18, 0, 0, L);
		}
		ctx.lineWidth = 6;
		ctx.strokeStyle = INK;
		ctx.stroke();
		ctx.lineWidth = 3.5;
		ctx.strokeStyle = P.a;
		ctx.stroke();
		line$1(ctx, "#e6e0d0", 1, [[r.form === "recurve" ? 4 : 0, -L], [r.form === "recurve" ? 4 : 0, L]]);
		shape(ctx, P.handle, () => ctx.roundRect(r.form === "recurve" ? 9 : 6, -4, 5, 8, 1), 1.2);
		ctx.restore();
		return [[38, 20], [38, 44]];
	};
	D.staff = (ctx, r, P) => {
		const orb = r.keywords.length ? P.accent : r.material === "crystal" ? P.a : "#9ad0ff";
		diag(ctx, () => {
			const len = r.form === "wand" ? 26 : 40;
			shape(ctx, r.material === "wood" ? P.a : P.d, () => ctx.roundRect(-2.5, -14, 5, len, 2), 1.5);
			if (r.form === "scepter") {
				ctx.beginPath();
				ctx.arc(0, -20, 8, 0, TAU$4);
				ctx.lineWidth = 5;
				ctx.strokeStyle = INK;
				ctx.stroke();
				ctx.lineWidth = 3;
				ctx.strokeStyle = r.material === "wood" ? "#e8bb48" : P.a;
				ctx.stroke();
				gem(ctx, 0, -20, 4.5, orb);
			} else {
				shape(ctx, orb, () => ctx.arc(0, -20, r.form === "wand" ? 5 : 7, 0, TAU$4));
				ctx.fillStyle = "rgba(255,255,255,0.6)";
				ctx.beginPath();
				ctx.arc(-2, -22, 2, 0, TAU$4);
				ctx.fill();
			}
			if (r.form === "long") {
				line$1(ctx, INK, 3, [[-5, -14], [5, -14]]);
				line$1(ctx, r.material === "wood" ? "#6a4420" : P.d, 1.6, [[-5, -14], [5, -14]]);
			}
		});
		return [[40, 22], [28, 38]];
	};
	D.round_shield = (ctx, r, P) => {
		shape(ctx, P.a, () => ctx.arc(32, 33, 22, 0, TAU$4), 2.5);
		if (r.form === "wood") for (const x of [
			-11,
			0,
			11
		]) line$1(ctx, P.d, 1.5, [[32 + x, 13 + Math.abs(x) / 3], [32 + x, 53 - Math.abs(x) / 3]]);
		else {
			ctx.beginPath();
			ctx.arc(32, 33, 19, 0, TAU$4);
			ctx.lineWidth = 4;
			ctx.strokeStyle = "#8d969f";
			ctx.stroke();
			for (let i = 0; i < 8; i++) {
				const a = i / 8 * TAU$4;
				shape(ctx, "#c3ccd6", () => ctx.arc(32 + Math.cos(a) * 19, 33 + Math.sin(a) * 19, 1.6, 0, TAU$4), .8);
			}
		}
		shape(ctx, r.form === "wood" ? "#8d969f" : P.d, () => ctx.arc(32, 33, 6, 0, TAU$4), 1.5);
		shine(ctx, P, [[20, 22], [26, 16]]);
		return [[22, 26], [42, 42]];
	};
	D.kite_shield = (ctx, r, P) => {
		if (r.form === "kite") shape(ctx, P.a, () => {
			ctx.moveTo(14, 12);
			ctx.lineTo(50, 12);
			ctx.lineTo(50, 30);
			ctx.quadraticCurveTo(48, 48, 32, 57);
			ctx.quadraticCurveTo(16, 48, 14, 30);
			ctx.closePath();
		}, 2.5);
		else shape(ctx, P.a, () => ctx.roundRect(15, 8, 34, 50, 4), 2.5);
		line$1(ctx, P.d, 3, [[32, 13], [32, r.form === "kite" ? 52 : 54]]);
		line$1(ctx, P.d, 3, [[19, 27], [45, 27]]);
		if (r.form === "tower") for (const y of [12, 54]) for (const x of [19, 45]) shape(ctx, P.d, () => ctx.arc(x, y, 1.6, 0, TAU$4), .8);
		shine(ctx, P, [[18, 16], [18, 26]]);
		return [[23, 20], [41, 40]];
	};
	D.tome = (ctx, r, P) => {
		if (r.form === "book") {
			shape(ctx, "#efe6cf", () => ctx.roundRect(17, 14, 32, 40, 3), 1.5);
			shape(ctx, P.a, () => ctx.roundRect(14, 12, 32, 40, 3), 2.5);
			line$1(ctx, P.d, 3, [[19, 12], [19, 52]]);
			gem(ctx, 32, 32, 6, P.accent);
			for (const y of [16, 48]) line$1(ctx, "#e8bb48", 2, [[38, y], [44, y]]);
		} else {
			shape(ctx, P.a, () => ctx.roundRect(22, 10, 20, 44, 6), 2.5);
			for (const y of [16, 48]) shape(ctx, "#e8bb48", () => ctx.roundRect(20, y - 2, 24, 4, 1.5), 1.2);
			shape(ctx, "#efe6cf", () => {
				ctx.moveTo(42, 26);
				ctx.lineTo(54, 30);
				ctx.lineTo(54, 40);
				ctx.lineTo(42, 36);
				ctx.closePath();
			}, 1.5);
			gem(ctx, 32, 32, 4, P.accent);
		}
		return [[24, 22], [40, 44]];
	};
	D.orb = (ctx, r, P) => {
		const c = P.a;
		if (r.form === "ball") {
			shape(ctx, "#7a5a3a", () => {
				ctx.moveTo(20, 54);
				ctx.lineTo(44, 54);
				ctx.lineTo(38, 44);
				ctx.lineTo(26, 44);
				ctx.closePath();
			}, 2);
			shape(ctx, c, () => ctx.arc(32, 30, 15, 0, TAU$4), 2.5);
		} else {
			ctx.beginPath();
			ctx.ellipse(32, 32, 24, 7, -.3, 0, TAU$4);
			ctx.lineWidth = 4;
			ctx.strokeStyle = INK;
			ctx.stroke();
			ctx.lineWidth = 2;
			ctx.strokeStyle = "#e8bb48";
			ctx.stroke();
			shape(ctx, c, () => ctx.arc(32, 31, 12, 0, TAU$4), 2.5);
			ctx.beginPath();
			ctx.ellipse(32, 32, 24, 7, -.3, 0, Math.PI);
			ctx.lineWidth = 4;
			ctx.strokeStyle = INK;
			ctx.stroke();
			ctx.lineWidth = 2;
			ctx.strokeStyle = "#e8bb48";
			ctx.stroke();
		}
		ctx.fillStyle = "rgba(255,255,255,0.6)";
		ctx.beginPath();
		ctx.arc(26, 24, 4, 0, TAU$4);
		ctx.fill();
		return [[32, 30], [40, 36]];
	};
	function torso(ctx, P, sleeves, hem) {
		shape(ctx, P.a, () => {
			ctx.moveTo(22, 12);
			ctx.quadraticCurveTo(32, 18, 42, 12);
			if (sleeves) {
				ctx.lineTo(54, 20);
				ctx.lineTo(50, 32);
				ctx.lineTo(44, 28);
			} else ctx.lineTo(46, 18);
			ctx.lineTo(45, hem);
			ctx.lineTo(19, hem);
			if (sleeves) {
				ctx.lineTo(20, 28);
				ctx.lineTo(14, 32);
				ctx.lineTo(10, 20);
			} else ctx.lineTo(18, 18);
			ctx.closePath();
		}, 2.5);
	}
	D.robe = (ctx, r, P) => {
		const hem = r.form === "long" ? 58 : 46;
		shape(ctx, P.a, () => {
			ctx.moveTo(22, 12);
			ctx.quadraticCurveTo(32, 18, 42, 12);
			ctx.lineTo(54, 22);
			ctx.lineTo(48, 30);
			ctx.lineTo(44, 26);
			ctx.lineTo(48, hem);
			ctx.lineTo(16, hem);
			ctx.lineTo(20, 26);
			ctx.lineTo(16, 30);
			ctx.lineTo(10, 22);
			ctx.closePath();
		}, 2.5);
		line$1(ctx, P.d, 2, [[32, 17], [32, hem]]);
		line$1(ctx, "#e8bb48", 2.5, [[17, hem - 2], [47, hem - 2]]);
		shape(ctx, P.d, () => ctx.roundRect(20, 32, 24, 4, 1), 1.2);
		return [[25, 42], [39, 24]];
	};
	D.leather = (ctx, r, P) => {
		torso(ctx, P, r.form === "hunter", 52);
		line$1(ctx, P.d, 1.5, [[32, 16], [32, 52]]);
		for (const y of [
			24,
			31,
			38
		]) line$1(ctx, "#2a1c10", 1.5, [[29, y], [35, y]]);
		shape(ctx, "#3a2a1a", () => ctx.roundRect(19, 42, 26, 5, 1), 1.2);
		shape(ctx, "#c8a040", () => ctx.roundRect(30, 42, 5, 5, 1), 1);
		return [[24, 30], [40, 30]];
	};
	D.mail = (ctx, r, P) => {
		torso(ctx, P, true, 54);
		ctx.save();
		ctx.beginPath();
		ctx.rect(19, 14, 26, 40);
		ctx.clip();
		ctx.strokeStyle = P.d;
		ctx.lineWidth = 1;
		if (r.form === "chain") for (let y = 16; y < 54; y += 3.5) for (let x = 19 + y / 3.5 % 2 * 1.75; x < 46; x += 3.5) {
			ctx.beginPath();
			ctx.arc(x, y, 1.4, 0, TAU$4);
			ctx.stroke();
		}
		else for (let y = 16; y < 56; y += 5) for (let x = 19 + y / 5 % 2 * 3; x < 47; x += 6) {
			ctx.beginPath();
			ctx.arc(x, y, 3, 0, Math.PI);
			ctx.stroke();
		}
		ctx.restore();
		shine(ctx, P, [[22, 18], [22, 30]]);
		return [[25, 30], [39, 44]];
	};
	D.plate = (ctx, r, P) => {
		if (r.form === "full") {
			shape(ctx, P.a, () => ctx.ellipse(16, 20, 9, 7, -.4, 0, TAU$4), 2);
			shape(ctx, P.a, () => ctx.ellipse(48, 20, 9, 7, .4, 0, TAU$4), 2);
		}
		shape(ctx, P.a, () => {
			ctx.moveTo(20, 14);
			ctx.quadraticCurveTo(32, 20, 44, 14);
			ctx.lineTo(46, 34);
			ctx.quadraticCurveTo(32, 46, 18, 34);
			ctx.closePath();
		}, 2.5);
		if (r.form === "full") for (const y of [
			42,
			48,
			54
		]) shape(ctx, P.a, () => ctx.roundRect(21, y - 6 + (y - 42) * 0, 22, 6, 2), 1.5);
		line$1(ctx, P.d, 1.5, [[32, 20], [32, 40]]);
		line$1(ctx, P.d, 1.5, [[22, 26], [42, 26]]);
		shine(ctx, P, [[24, 18], [25, 32]]);
		return [[26, 32], [38, 22]];
	};
	D.coat = (ctx, r, P) => {
		if (r.form === "cape") shape(ctx, P.d, () => {
			ctx.moveTo(18, 14);
			ctx.lineTo(46, 14);
			ctx.lineTo(54, 58);
			ctx.lineTo(10, 58);
			ctx.closePath();
		}, 2);
		torso(ctx, P, true, 56);
		line$1(ctx, P.d, 2, [[32, 16], [32, 56]]);
		shape(ctx, P.d, () => {
			ctx.moveTo(24, 12);
			ctx.lineTo(32, 22);
			ctx.lineTo(40, 12);
			ctx.lineTo(36, 10);
			ctx.lineTo(32, 16);
			ctx.lineTo(28, 10);
			ctx.closePath();
		}, 1.5);
		for (const y of [
			28,
			36,
			44
		]) shape(ctx, "#e8bb48", () => ctx.arc(35, y, 1.6, 0, TAU$4), .8);
		return [[25, 34], [40, 46]];
	};
	D.ring = (ctx, r, P) => {
		ctx.beginPath();
		ctx.ellipse(32, 38, 15, 13, 0, 0, TAU$4);
		ctx.lineWidth = 8;
		ctx.strokeStyle = INK;
		ctx.stroke();
		ctx.lineWidth = 5;
		ctx.strokeStyle = P.a;
		ctx.stroke();
		shine(ctx, P, [[20, 34], [23, 28]]);
		if (r.form === "gem") {
			shape(ctx, P.a, () => ctx.roundRect(25, 18, 14, 9, 2), 1.5);
			gem(ctx, 32, 18, 7, P.accent);
		}
		return [[46, 44], [18, 46]];
	};
	D.pendant = (ctx, r, P) => {
		ctx.beginPath();
		ctx.arc(32, 14, 18, .15 * Math.PI, .85 * Math.PI, true);
		ctx.strokeStyle = "#9c7420";
		ctx.lineWidth = 1.8;
		ctx.setLineDash([2, 1.5]);
		ctx.stroke();
		ctx.setLineDash([]);
		if (r.form === "pendant") {
			shape(ctx, P.a, () => ctx.arc(32, 40, 12, 0, TAU$4), 2);
			gem(ctx, 32, 40, 6, P.accent);
		} else {
			shape(ctx, P.a, () => ctx.roundRect(22, 28, 20, 26, 3), 2);
			line$1(ctx, P.d, 1.5, [[26, 36], [38, 36]]);
			line$1(ctx, P.d, 1.5, [[26, 42], [36, 42]]);
			shape(ctx, INK, () => ctx.arc(32, 32, 1.6, 0, TAU$4), .5);
		}
		return [[46, 44], [18, 44]];
	};
	D.charm = (ctx, r, P) => {
		if (r.form === "tablet") {
			shape(ctx, P.a, () => ctx.roundRect(20, 12, 24, 40, 4), 2.5);
			line$1(ctx, P.d, 2, [[32, 18], [32, 46]]);
			line$1(ctx, P.d, 2, [[26, 24], [38, 24]]);
			line$1(ctx, P.d, 2, [[27, 34], [37, 40]]);
			line$1(ctx, "#b83a3a", 2.5, [[32, 52], [30, 60]]);
			line$1(ctx, "#b83a3a", 2.5, [[32, 52], [35, 60]]);
		} else {
			shape(ctx, "#e9e3cf", () => {
				ctx.moveTo(32, 10);
				ctx.quadraticCurveTo(44, 24, 36, 50);
				ctx.lineTo(28, 50);
				ctx.quadraticCurveTo(20, 24, 32, 10);
			}, 2.5);
			for (const y of [
				24,
				32,
				40
			]) line$1(ctx, "#8a8070", 1.5, [[28, y], [36, y]]);
			line$1(ctx, P.a, 3, [[26, 50], [38, 50]]);
		}
		return [[46, 30], [18, 40]];
	};
	var SKIN_HINT = "#3a3f4a";
	D.hood = (ctx, r, P) => {
		shape(ctx, P.a, () => {
			ctx.moveTo(12, 52);
			ctx.quadraticCurveTo(10, 14, 32, 10);
			ctx.quadraticCurveTo(54, 14, 52, 52);
			ctx.closePath();
		}, 2.5);
		shape(ctx, SKIN_HINT, () => ctx.ellipse(32, 34, 11, 13, 0, 0, TAU$4), 1.5);
		if (r.form === "cowl") shape(ctx, P.d, () => {
			ctx.moveTo(8, 50);
			ctx.quadraticCurveTo(32, 60, 56, 50);
			ctx.lineTo(58, 58);
			ctx.lineTo(6, 58);
			ctx.closePath();
		}, 2);
		else line$1(ctx, P.d, 2, [[14, 48], [50, 48]]);
		return [[46, 22], [18, 26]];
	};
	D.hat = (ctx, r, P) => {
		if (r.form === "wizard") {
			shape(ctx, P.d, () => ctx.ellipse(32, 46, 26, 7, 0, 0, TAU$4), 2.5);
			shape(ctx, P.a, () => {
				ctx.moveTo(18, 46);
				ctx.quadraticCurveTo(26, 26, 30, 8);
				ctx.quadraticCurveTo(38, 6, 44, 14);
				ctx.quadraticCurveTo(38, 14, 36, 20);
				ctx.lineTo(46, 46);
				ctx.closePath();
			}, 2.5);
			shape(ctx, "#e8bb48", () => ctx.roundRect(19, 39, 26, 4, 1), 1.2);
		} else {
			shape(ctx, P.d, () => ctx.ellipse(32, 44, 28, 9, 0, 0, TAU$4), 2.5);
			shape(ctx, P.a, () => {
				ctx.moveTo(18, 44);
				ctx.lineTo(19, 24);
				ctx.quadraticCurveTo(32, 16, 45, 24);
				ctx.lineTo(46, 44);
				ctx.closePath();
			}, 2.5);
			shape(ctx, P.d, () => ctx.roundRect(18, 36, 28, 5, 1), 1.2);
			shape(ctx, "#e6e6e0", () => {
				ctx.moveTo(42, 36);
				ctx.quadraticCurveTo(52, 22, 48, 14);
				ctx.quadraticCurveTo(46, 26, 40, 34);
				ctx.closePath();
			}, 1.2);
		}
		return [[48, 22], [16, 30]];
	};
	D.circlet = (ctx, r, P) => {
		if (r.form === "bandana") {
			shape(ctx, P.a, () => {
				ctx.moveTo(10, 40);
				ctx.quadraticCurveTo(12, 14, 32, 14);
				ctx.quadraticCurveTo(52, 14, 54, 40);
				ctx.quadraticCurveTo(32, 32, 10, 40);
			}, 2.5);
			shape(ctx, P.d, () => {
				ctx.moveTo(48, 36);
				ctx.lineTo(58, 48);
				ctx.lineTo(52, 52);
				ctx.lineTo(46, 40);
				ctx.closePath();
			}, 1.8);
			for (const [x, y] of [
				[22, 24],
				[32, 21],
				[42, 24]
			]) shape(ctx, P.d, () => ctx.arc(x, y, 1.6, 0, TAU$4), .6);
		} else {
			shape(ctx, P.a, () => {
				ctx.moveTo(12, 44);
				ctx.lineTo(12, 22);
				ctx.lineTo(20, 32);
				ctx.lineTo(26, 16);
				ctx.lineTo(32, 30);
				ctx.lineTo(38, 16);
				ctx.lineTo(44, 32);
				ctx.lineTo(52, 22);
				ctx.lineTo(52, 44);
				ctx.closePath();
			}, 2.5);
			shape(ctx, P.d, () => ctx.roundRect(12, 38, 40, 6, 1.5), 1.5);
			gem(ctx, 32, 36, 5, P.accent);
			shine(ctx, P, [[15, 26], [15, 36]]);
		}
		return [[48, 18], [16, 18]];
	};
	D.cap = (ctx, r, P) => {
		shape(ctx, P.a, () => {
			ctx.moveTo(12, 42);
			ctx.quadraticCurveTo(12, 14, 32, 14);
			ctx.quadraticCurveTo(52, 14, 52, 42);
			ctx.closePath();
		}, 2.5);
		if (r.form === "fur") {
			shape(ctx, "#e9e3cf", () => ctx.roundRect(9, 38, 46, 11, 5), 2);
			for (let x = 13; x < 52; x += 5) line$1(ctx, "#b8b09a", 1, [[x, 41], [x + 1.5, 46]]);
		} else {
			shape(ctx, P.d, () => ctx.roundRect(10, 38, 44, 7, 2), 2);
			line$1(ctx, P.d, 1.4, [[32, 15], [32, 38]]);
			for (const y of [
				20,
				27,
				34
			]) line$1(ctx, "#2a1c10", 1, [[30, y], [34, y]]);
		}
		return [[46, 24], [18, 24]];
	};
	D.helmet = (ctx, r, P) => {
		if (r.form === "greathelm") {
			shape(ctx, P.a, () => ctx.roundRect(14, 12, 36, 42, 7), 2.5);
			shape(ctx, INK, () => ctx.roundRect(18, 28, 28, 4, 1), .5);
			line$1(ctx, P.d, 2, [[32, 32], [32, 50]]);
			for (const y of [38, 43]) for (const x of [24, 40]) shape(ctx, INK, () => ctx.arc(x, y, 1, 0, TAU$4), 0);
		} else {
			shape(ctx, P.a, () => {
				ctx.moveTo(12, 44);
				ctx.lineTo(12, 32);
				ctx.quadraticCurveTo(12, 12, 32, 12);
				ctx.quadraticCurveTo(52, 12, 52, 32);
				ctx.lineTo(52, 44);
				ctx.closePath();
			}, 2.5);
			shape(ctx, P.d, () => ctx.roundRect(10, 38, 44, 7, 2), 2);
			shape(ctx, P.d, () => ctx.roundRect(29.5, 38, 5, 14, 1.5), 1.5);
			if (r.form === "horned") for (const s of [-1, 1]) shape(ctx, "#efe6cc", () => {
				ctx.moveTo(32 + s * 16, 26);
				ctx.quadraticCurveTo(32 + s * 30, 22, 32 + s * 28, 6);
				ctx.quadraticCurveTo(32 + s * 24, 18, 32 + s * 14, 20);
				ctx.closePath();
			}, 2);
		}
		shine(ctx, P, [[19, 22], [24, 17]]);
		return [[46, 22], [18, 28]];
	};
	function glove(ctx, P, fingerless, cuff) {
		if (cuff) shape(ctx, P.d, () => ctx.roundRect(17, 44, 30, 14, 3), 2);
		shape(ctx, P.a, () => {
			ctx.moveTo(20, 50);
			ctx.lineTo(20, 34);
			ctx.lineTo(16, 26);
			ctx.quadraticCurveTo(14, 21, 19, 22);
			ctx.lineTo(23, 28);
			if (fingerless) {
				ctx.lineTo(23, 20);
				ctx.lineTo(29, 20);
				ctx.lineTo(30, 18);
				ctx.lineTo(36, 18);
				ctx.lineTo(37, 20);
				ctx.lineTo(42, 20);
				ctx.lineTo(43, 24);
				ctx.lineTo(47, 24);
			} else {
				ctx.lineTo(23, 12);
				ctx.quadraticCurveTo(26, 8, 29, 12);
				ctx.lineTo(29, 24);
				ctx.lineTo(30, 9);
				ctx.quadraticCurveTo(33, 5, 36, 9);
				ctx.lineTo(35, 24);
				ctx.lineTo(37, 11);
				ctx.quadraticCurveTo(40, 8, 42, 12);
				ctx.lineTo(41, 26);
				ctx.lineTo(43, 17);
				ctx.quadraticCurveTo(46, 15, 47, 19);
			}
			ctx.lineTo(45, 38);
			ctx.lineTo(44, 50);
			ctx.closePath();
		}, 2.5);
		if (fingerless) for (const [x, y] of [
			[26, 14],
			[33, 12],
			[39.5, 14],
			[45, 19]
		]) shape(ctx, "#f0c8a0", () => ctx.roundRect(x - 2.5, y, 5, 7, 2.5), 1.5);
	}
	D.cloth_gloves = (ctx, r, P) => {
		glove(ctx, P, r.form === "fingerless", false);
		line$1(ctx, P.d, 1.5, [[21, 44], [44, 44]]);
		return [[40, 30], [26, 38]];
	};
	D.leather_gloves = (ctx, r, P) => {
		glove(ctx, P, false, r.form === "long");
		line$1(ctx, P.d, 1.2, [[26, 30], [38, 30]]);
		if (r.form === "short") shape(ctx, P.d, () => ctx.roundRect(19, 44, 26, 7, 2), 1.8);
		for (const x of [
			24,
			32,
			40
		]) shape(ctx, "#c8a040", () => ctx.arc(x, 48, 1.3, 0, TAU$4), .6);
		return [[40, 22], [26, 38]];
	};
	D.gauntlets = (ctx, r, P) => {
		shape(ctx, P.d, () => ctx.roundRect(16, 42, 32, 16, 3), 2);
		glove(ctx, P, false, false);
		if (r.form === "plate") {
			for (const y of [
				28,
				34,
				40
			]) line$1(ctx, P.d, 1.5, [[21, y], [45, y - 1]]);
			shape(ctx, P.a, () => ctx.ellipse(32, 46, 14, 5, 0, 0, TAU$4), 1.8);
		} else {
			ctx.save();
			ctx.beginPath();
			ctx.rect(20, 26, 26, 30);
			ctx.clip();
			ctx.strokeStyle = P.d;
			ctx.lineWidth = 1;
			for (let y = 27; y < 56; y += 3) for (let x = 20 + y / 3 % 2 * 1.5; x < 46; x += 3) {
				ctx.beginPath();
				ctx.arc(x, y, 1.2, 0, TAU$4);
				ctx.stroke();
			}
			ctx.restore();
		}
		shine(ctx, P, [[23, 30], [23, 40]]);
		return [[42, 18], [24, 50]];
	};
	D.bracers = (ctx, r, P) => {
		if (r.form === "ring") {
			for (const y of [22, 40]) {
				ctx.beginPath();
				ctx.ellipse(32, y, 18, 7, 0, 0, TAU$4);
				ctx.lineWidth = 9;
				ctx.strokeStyle = INK;
				ctx.stroke();
				ctx.lineWidth = 6;
				ctx.strokeStyle = P.a;
				ctx.stroke();
			}
			shine(ctx, P, [[18, 20], [24, 16]]);
			gem(ctx, 32, 47, 3.5, P.accent);
		} else {
			shape(ctx, P.a, () => {
				ctx.moveTo(18, 12);
				ctx.lineTo(46, 12);
				ctx.lineTo(44, 54);
				ctx.lineTo(20, 54);
				ctx.closePath();
			}, 2.5);
			for (const y of [
				20,
				32,
				44
			]) {
				shape(ctx, P.d, () => ctx.roundRect(18, y - 2, 28, 4, 1), 1.2);
				shape(ctx, "#c8a040", () => ctx.roundRect(30, y - 2.5, 4, 5, 1), .8);
			}
			line$1(ctx, "#2a1c10", 1, [[24, 14], [22, 52]]);
		}
		return [[48, 30], [16, 30]];
	};
	function boot(ctx, P, top, toe) {
		shape(ctx, P.a, () => {
			ctx.moveTo(22, top);
			ctx.lineTo(38, top);
			ctx.lineTo(38, 42);
			ctx.quadraticCurveTo(52, 42, 54, 50);
			ctx.lineTo(54, 54);
			ctx.lineTo(20, 54);
			ctx.lineTo(20, 46);
			ctx.closePath();
		}, 2.5);
		shape(ctx, P.d, () => ctx.roundRect(18, 52, 38, 5, 2), 2);
		if (toe) shape(ctx, P.d, () => {
			ctx.moveTo(42, 44);
			ctx.quadraticCurveTo(54, 44, 58, 52);
			ctx.lineTo(44, 52);
			ctx.closePath();
		}, 1.8);
	}
	D.shoes = (ctx, r, P) => {
		boot(ctx, P, 36, false);
		if (r.form === "wrapped") {
			boot(ctx, P, 14, false);
			for (let y = 18; y < 44; y += 6) line$1(ctx, P.d, 1.5, [[22, y], [38, y + 3]]);
		}
		line$1(ctx, P.d, 1.5, [[22, 40], [38, 40]]);
		return [[46, 30], [28, 46]];
	};
	D.boots = (ctx, r, P) => {
		boot(ctx, P, r.form === "tall" ? 8 : 24, false);
		shape(ctx, P.d, () => ctx.roundRect(20, (r.form === "tall" ? 8 : 24) - 2, 20, 5, 1.5), 1.5);
		for (const y of [32, 38]) shape(ctx, "#c8a040", () => ctx.arc(36, y, 1.2, 0, TAU$4), .5);
		return [[46, 30], [28, 46]];
	};
	D.iron_boots = (ctx, r, P) => {
		boot(ctx, P, 20, r.form === "sabaton");
		for (const y of [28, 36]) line$1(ctx, P.d, 1.6, [[21, y], [38, y]]);
		shine(ctx, P, [[24, 24], [24, 44]]);
		return [[48, 30], [28, 46]];
	};
	D.greaves = (ctx, r, P) => {
		boot(ctx, P, 6, false);
		shape(ctx, P.d, () => ctx.roundRect(20, 18, 20, 3, 1), 1.2);
		if (r.form === "knee") shape(ctx, P.a, () => ctx.ellipse(30, 10, 11, 7, 0, 0, TAU$4), 2);
		shine(ctx, P, [[24, 12], [24, 44]]);
		return [[48, 28], [28, 46]];
	};
	var baseRing = D.ring;
	D.ring = (ctx, r, P) => {
		if (r.form !== "signet") return baseRing(ctx, r, P);
		ctx.beginPath();
		ctx.ellipse(32, 40, 15, 12, 0, 0, TAU$4);
		ctx.lineWidth = 8;
		ctx.strokeStyle = INK;
		ctx.stroke();
		ctx.lineWidth = 5;
		ctx.strokeStyle = P.a;
		ctx.stroke();
		shape(ctx, P.a, () => ctx.roundRect(21, 14, 22, 16, 3), 2.2);
		shape(ctx, P.d, () => ctx.roundRect(24, 17, 16, 10, 2), 1.2);
		line$1(ctx, P.a, 1.6, [
			[28, 25],
			[32, 19],
			[36, 25]
		]);
		shine(ctx, P, [[20, 36], [23, 30]]);
		return [[50, 44], [14, 44]];
	};
	var WOOD$2 = "#7a5232";
	var WOOD_D = "#4e321c";
	/** 以槍身方向（往右上 −0.42 rad）畫；回傳槍口位置（64 格座標）。 */
	function gunFrame(ctx, fn, muzzle) {
		ctx.save();
		ctx.translate(32, 34);
		ctx.rotate(-.42);
		fn();
		ctx.restore();
		const a = -.42;
		return [32 + Math.cos(a) * muzzle[0] - Math.sin(a) * muzzle[1], 34 + Math.sin(a) * muzzle[0] + Math.cos(a) * muzzle[1]];
	}
	function flintHammer(ctx, x, y) {
		shape(ctx, "#454c58", () => {
			ctx.moveTo(x, y);
			ctx.lineTo(x - 2, y - 6);
			ctx.lineTo(x + 2, y - 7);
			ctx.lineTo(x + 3, y);
			ctx.closePath();
		}, 1.2);
	}
	D.longgun = (ctx, r, P) => {
		const m = gunFrame(ctx, () => {
			if (r.form === "flintlock") {
				shape(ctx, WOOD$2, () => {
					ctx.moveTo(-28, -2);
					ctx.lineTo(-14, -6);
					ctx.lineTo(16, -6);
					ctx.lineTo(16, -2);
					ctx.lineTo(-12, 0);
					ctx.lineTo(-28, 6);
					ctx.closePath();
				});
				shape(ctx, P.a, () => ctx.roundRect(-12, -9, 40, 3.5, 1.2), 1.5);
				for (const x of [-2, 10]) shape(ctx, P.d, () => ctx.roundRect(x, -9.5, 2.5, 7, .8), 1);
				flintHammer(ctx, -10, -6);
			} else if (r.form === "hunting") {
				shape(ctx, WOOD$2, () => {
					ctx.moveTo(-28, -3);
					ctx.lineTo(-12, -6);
					ctx.lineTo(-10, 2);
					ctx.lineTo(-28, 6);
					ctx.closePath();
				});
				shape(ctx, P.a, () => ctx.roundRect(-12, -7, 18, 7, 1.5));
				shape(ctx, P.d, () => ctx.roundRect(6, -6, 22, 3.5, 1), 1.5);
				shape(ctx, WOOD$2, () => ctx.roundRect(6, -2.5, 14, 3.5, 1.2), 1.2);
				shape(ctx, P.d, () => {
					ctx.moveTo(-6, 0);
					ctx.lineTo(-1, 0);
					ctx.lineTo(-3, 8);
					ctx.lineTo(-8, 8);
					ctx.closePath();
				});
			} else {
				shape(ctx, P.d, () => {
					ctx.moveTo(-28, -4);
					ctx.lineTo(-12, -6);
					ctx.lineTo(-10, 2);
					ctx.lineTo(-22, 2);
					ctx.lineTo(-28, 6);
					ctx.closePath();
				});
				shape(ctx, P.a, () => ctx.roundRect(-12, -7, 20, 7, 1.5));
				shape(ctx, P.d, () => ctx.roundRect(8, -5.5, 22, 3, 1), 1.5);
				shape(ctx, "#2a2d33", () => ctx.roundRect(-8, -14, 16, 5, 2), 1.5);
				shape(ctx, "#8fe3ff", () => ctx.arc(8, -11.5, 1.6, 0, TAU$4), .8);
				line$1(ctx, INK, 1.8, [[18, -2], [14, 8]]);
				line$1(ctx, INK, 1.8, [[18, -2], [22, 8]]);
			}
			shine(ctx, P, [[-10, -8], [8, -8]]);
		}, [r.form === "flintlock" ? 28 : 30, -6]);
		return [[m[0] - 2, m[1] - 4], [24, 44]];
	};
	D.pistol = (ctx, r, P) => {
		const m = gunFrame(ctx, () => {
			ctx.scale(1.4, 1.4);
			if (r.form === "flintlock") {
				shape(ctx, WOOD$2, () => {
					ctx.moveTo(-6, -6);
					ctx.lineTo(4, -6);
					ctx.lineTo(4, -2);
					ctx.quadraticCurveTo(-4, 0, -10, 10);
					ctx.lineTo(-15, 8);
					ctx.quadraticCurveTo(-10, 0, -6, -6);
				});
				shape(ctx, P.a, () => ctx.roundRect(-2, -8.5, 20, 3.5, 1.2), 1.5);
				flintHammer(ctx, -4, -6);
			} else if (r.form === "revolver") {
				shape(ctx, P.a, () => ctx.roundRect(-2, -8, 20, 4, 1.2), 1.5);
				shape(ctx, P.d, () => ctx.roundRect(-4, -9, 9, 8, 2.5), 1.5);
				for (const x of [-1.5, 2.5]) line$1(ctx, INK, 1, [[x, -8], [x, -2]]);
				shape(ctx, WOOD$2, () => {
					ctx.moveTo(-6, -4);
					ctx.lineTo(-2, -2);
					ctx.lineTo(-6, 10);
					ctx.lineTo(-11, 8);
					ctx.closePath();
				});
				line$1(ctx, INK, 1.6, [
					[-1, -1],
					[2, 2],
					[-1, 3]
				]);
			} else {
				shape(ctx, P.a, () => ctx.roundRect(-4, -9, 14, 3.5, 1), 1.5);
				shape(ctx, P.a, () => ctx.roundRect(-4, -5.5, 14, 3.5, 1), 1.5);
				shape(ctx, "#e8bb48", () => ctx.roundRect(-6, -9, 4, 7, 1), 1.2);
				shape(ctx, WOOD$2, () => {
					ctx.moveTo(-6, -2);
					ctx.lineTo(-2, -2);
					ctx.lineTo(-4, 6);
					ctx.lineTo(-8, 5);
					ctx.closePath();
				});
			}
			shine(ctx, P, [[0, -7.5], [14, -7.5]]);
		}, [24, -9]);
		return [[m[0], m[1] - 4], [24, 44]];
	};
	D.shotgun = (ctx, r, P) => {
		const m = gunFrame(ctx, () => {
			shape(ctx, WOOD$2, () => {
				ctx.moveTo(-28, -3);
				ctx.lineTo(-12, -7);
				ctx.lineTo(-10, 2);
				ctx.lineTo(-28, 7);
				ctx.closePath();
			});
			if (r.form === "blunderbuss") {
				shape(ctx, P.a, () => {
					ctx.moveTo(-12, -8);
					ctx.lineTo(16, -7);
					ctx.lineTo(26, -12);
					ctx.lineTo(26, 2);
					ctx.lineTo(16, -2);
					ctx.lineTo(-12, -1);
					ctx.closePath();
				});
				flintHammer(ctx, -10, -7);
			} else if (r.form === "double") {
				shape(ctx, P.a, () => ctx.roundRect(-12, -8, 10, 9, 2));
				shape(ctx, P.d, () => ctx.roundRect(-2, -8, 28, 4, 1), 1.5);
				shape(ctx, P.d, () => ctx.roundRect(-2, -4, 28, 4, 1), 1.5);
				shape(ctx, WOOD$2, () => ctx.roundRect(0, 0, 10, 3.5, 1.2), 1.2);
			} else {
				shape(ctx, P.a, () => ctx.roundRect(-12, -8, 14, 9, 2));
				shape(ctx, P.d, () => ctx.roundRect(2, -8, 24, 4, 1), 1.5);
				shape(ctx, P.d, () => ctx.roundRect(2, -4, 24, 4, 1), 1.5);
				shape(ctx, WOOD$2, () => ctx.roundRect(6, 0, 12, 4, 1.5), 1.5);
			}
			shape(ctx, P.d, () => {
				ctx.moveTo(-6, 0);
				ctx.lineTo(-1, 0);
				ctx.lineTo(-3, 8);
				ctx.lineTo(-8, 8);
				ctx.closePath();
			});
			shine(ctx, P, [[-10, -6], [0, -6]]);
		}, [26, -5]);
		return [[m[0] - 2, m[1] - 4], [24, 44]];
	};
	D.crossbow = (ctx, r, P) => {
		ctx.save();
		ctx.translate(32, 34);
		ctx.rotate(-Math.PI / 4);
		const wide = r.form === "heavy" ? 24 : 19;
		shape(ctx, r.material === "wood" ? WOOD$2 : P.d, () => ctx.roundRect(-3, -14, 6, 32, 2), 1.8);
		ctx.beginPath();
		ctx.moveTo(-wide, -4);
		ctx.quadraticCurveTo(0, -18, wide, -4);
		ctx.lineWidth = r.form === "heavy" ? 7 : 5.5;
		ctx.strokeStyle = INK;
		ctx.stroke();
		ctx.lineWidth = r.form === "heavy" ? 4.5 : 3.2;
		ctx.strokeStyle = P.a;
		ctx.stroke();
		line$1(ctx, "#e6e0d0", 1, [
			[-wide + 1, -4],
			[0, 4],
			[wide - 1, -4]
		]);
		shape(ctx, "#c3ccd6", () => {
			ctx.moveTo(0, -22);
			ctx.lineTo(1.8, -17);
			ctx.lineTo(-1.8, -17);
			ctx.closePath();
		}, 1);
		line$1(ctx, "#a06a36", 1.6, [[0, -17], [0, 3]]);
		if (r.form === "heavy") {
			shape(ctx, P.d, () => ctx.arc(0, 14, 4.5, 0, TAU$4), 1.5);
			line$1(ctx, INK, 1.6, [[0, 14], [7, 18]]);
		}
		if (r.form === "repeater") shape(ctx, WOOD_D, () => ctx.roundRect(-5, -12, 10, 12, 1.5), 1.5);
		shape(ctx, P.handle, () => ctx.roundRect(-2.5, 6, 5, 9, 1.5), 1.2);
		ctx.restore();
		return [[40, 18], [24, 40]];
	};
	D.fist = (ctx, r, P) => {
		ctx.save();
		ctx.translate(30, 36);
		ctx.rotate(-.6);
		shape(ctx, "#8a5a32", () => ctx.roundRect(-14, -6, 12, 12, 3), 1.8);
		shape(ctx, "#f0c8a0", () => ctx.roundRect(-3, -8, 13, 16, 5), 1.8);
		if (r.form === "katar") {
			shape(ctx, P.a, () => {
				ctx.moveTo(8, -4);
				ctx.lineTo(28, 0);
				ctx.lineTo(8, 4);
				ctx.closePath();
			});
			shape(ctx, P.d, () => ctx.roundRect(4, -9, 4, 18, 1), 1.5);
		} else if (r.form === "knuckle") {
			shape(ctx, P.a, () => ctx.roundRect(7, -9, 6, 18, 2.5));
			for (const y of [
				-6,
				-1.5,
				3
			]) shape(ctx, P.d, () => ctx.arc(14, y + 1.5, 1.8, 0, TAU$4), 1);
		} else for (const y of [
			-6,
			0,
			6
		]) shape(ctx, P.a, () => {
			ctx.moveTo(8, y - 1.6);
			ctx.quadraticCurveTo(22, y - 4, 27, y + 2);
			ctx.quadraticCurveTo(20, y, 8, y + 1.6);
			ctx.closePath();
		}, 1.5);
		ctx.restore();
		return [[44, 18], [18, 46]];
	};
	D.scythe = (ctx, r, P) => {
		diag(ctx, () => {
			const len = r.form === "hook" ? 30 : 46;
			shape(ctx, P.handle, () => ctx.roundRect(-2.2, -24, 4.4, len, 2), 1.5);
			if (r.form === "long") shape(ctx, P.a, () => {
				ctx.moveTo(1, -24);
				ctx.quadraticCurveTo(-18, -30, -26, -12);
				ctx.quadraticCurveTo(-16, -22, 1, -19);
				ctx.closePath();
			});
			else if (r.form === "crescent") {
				shape(ctx, P.a, () => {
					ctx.moveTo(1, -24);
					ctx.quadraticCurveTo(-18, -30, -24, -14);
					ctx.quadraticCurveTo(-14, -22, 1, -19);
					ctx.closePath();
				});
				shape(ctx, P.a, () => {
					ctx.moveTo(-1, -24);
					ctx.quadraticCurveTo(14, -30, 18, -18);
					ctx.quadraticCurveTo(10, -23, -1, -20);
					ctx.closePath();
				});
			} else shape(ctx, P.a, () => {
				ctx.moveTo(1, -24);
				ctx.quadraticCurveTo(-12, -28, -14, -16);
				ctx.quadraticCurveTo(-10, -12, -7, -15);
				ctx.quadraticCurveTo(-8, -21, 1, -19);
				ctx.closePath();
			});
			shine(ctx, P, [[-6, -25], [-14, -22]]);
		});
		return [[22, 18], [40, 40]];
	};
	D.whip = (ctx, r, P) => {
		shape(ctx, P.handle, () => {
			ctx.save();
			ctx.translate(16, 48);
			ctx.rotate(-.7);
			ctx.roundRect(-2.5, -10, 5, 14, 2);
			ctx.restore();
		}, 1.5);
		const pts = [];
		for (let i = 0; i <= 24; i++) {
			const t = i / 24;
			pts.push([20 + t * 34 - Math.sin(t * Math.PI) * 6, 42 - t * 30 + Math.sin(t * Math.PI * 2.2) * 9 * t]);
		}
		if (r.form === "chain") pts.forEach(([x, y], i) => {
			if (i % 2 === 0) {
				ctx.beginPath();
				ctx.ellipse(x, y, 2.6, 1.8, i * .4, 0, TAU$4);
				ctx.lineWidth = 2.8;
				ctx.strokeStyle = INK;
				ctx.stroke();
				ctx.lineWidth = 1.6;
				ctx.strokeStyle = P.a;
				ctx.stroke();
			}
		});
		else {
			ctx.beginPath();
			pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
			ctx.lineCap = "round";
			ctx.lineWidth = 5;
			ctx.strokeStyle = INK;
			ctx.stroke();
			ctx.lineWidth = 3;
			ctx.strokeStyle = r.form === "bladed" ? P.d : P.a;
			ctx.stroke();
			ctx.lineCap = "butt";
			if (r.form === "bladed") pts.forEach(([x, y], i) => {
				if (i % 3 === 1) shape(ctx, P.a, () => {
					ctx.moveTo(x - 3, y + 1);
					ctx.lineTo(x, y - 4);
					ctx.lineTo(x + 3, y + 1);
					ctx.closePath();
				}, 1);
			});
		}
		return [[44, 16], [30, 34]];
	};
	/** 成對武器：畫兩把（左邊一把縮小、右邊鏡像）。 */
	function pair$1(base) {
		return (ctx, r, P) => {
			ctx.save();
			ctx.translate(32, 33);
			ctx.scale(.78, .78);
			ctx.translate(-36, -33);
			const s = base(ctx, r, P);
			ctx.restore();
			ctx.save();
			ctx.translate(32, 33);
			ctx.scale(-.78, .78);
			ctx.translate(-36, -31);
			base(ctx, r, P);
			ctx.restore();
			return [[32 + (s[0][0] - 36) * .78, 33 + (s[0][1] - 33) * .78], [32 - (s[0][0] - 36) * .78, 33 + (s[0][1] - 31) * .78]];
		};
	}
	D.dual_dagger = pair$1(D.dagger);
	D.dual_pistol = pair$1(D.pistol);
	var baseStaff = D.staff;
	D.staff = (ctx, r, P) => {
		if (r.form !== "totem") return baseStaff(ctx, r, P);
		diag(ctx, () => {
			shape(ctx, P.a, () => ctx.roundRect(-3, -12, 6, 38, 2), 1.5);
			for (const [y, c] of [[-26, "#b83a3a"], [-17, "#3a8a8a"]]) {
				shape(ctx, P.a, () => ctx.roundRect(-6, y, 12, 9, 2.5), 1.5);
				shape(ctx, c, () => ctx.rect(-4, y + 2, 8, 2), .8);
				shape(ctx, INK, () => ctx.rect(-3, y + 5.5, 6, 1.5), 0);
			}
			for (const s of [-1, 1]) shape(ctx, "#e6e6e0", () => {
				ctx.moveTo(s * 6, -24);
				ctx.quadraticCurveTo(s * 16, -30, s * 14, -20);
				ctx.quadraticCurveTo(s * 10, -21, s * 6, -21);
				ctx.closePath();
			}, 1.2);
			shape(ctx, r.keywords.length ? P.accent : "#7dffb0", () => ctx.arc(0, -30, 3, 0, TAU$4), 1.2);
		});
		return [[42, 18], [28, 38]];
	};
	new Set(gearKinds().filter((k) => k.paired).map((k) => k.id));
	MAT.gold;
	MAT.gold;
	MAT.wood;
	MAT.gold;
	MAT.wood;
	var POINT = {
		arm: -1.45,
		wpn: 3.02,
		lean: -.04
	};
	var AIM = {
		arm: -1.3,
		wpn: 2.87,
		lean: -.05
	};
	({ ...POINT }), { ...POINT }, { ...POINT }, { ...POINT }, { ...POINT }, { ...AIM }, { ...AIM }, { ...AIM }, { ...POINT };
	Object.freeze({
		kneeN: 1.4,
		kneeF: 1.2,
		hipN: .7,
		hipF: .5,
		bob: 7,
		lean: .25,
		arm: .3,
		armF: .35
	});
	//#endregion
	//#region client/src/battle/vfxPalette.ts
	function vfx(primary, secondary, particle, particles = 10, extra = {}) {
		return {
			primary,
			secondary,
			particle,
			particles,
			jagged: false,
			column: false,
			...extra
		};
	}
	/** `#rrggbb` → 0xrrggbb。 */
	function hexToNumber(hex) {
		return parseInt(hex.slice(1), 16);
	}
	function fromColors(id, particle, particles, extra = {}) {
		const c = ELEMENT_COLORS[id];
		if (c === void 0) throw new Error(`ELEMENT_COLORS 缺少 ${id}`);
		return vfx(hexToNumber(c.primary), hexToNumber(c.secondary), particle, particles, extra);
	}
	fromColors("physical", "spark", 8), fromColors("fire", "ember", 12), fromColors("ice", "shard", 10), fromColors("lightning", "bolt", 7, { jagged: true }), fromColors("poison", "bubble", 9), fromColors("wind", "gust", 7), fromColors("earth", "rock", 9), fromColors("holy", "pillar", 9, { column: true }), fromColors("shadow", "smoke", 9), vfx(hexToNumber(WATER_COLOR), 14217471, "splash", 10);
	vfx(8188570, 15138793, "sparkle", 9);
	vfx(12101887, 16777215, "sparkle", 9);
	//#endregion
	//#region client/src/battle/vfx.ts
	/**
	* 技能卡 `shape` 文字的開頭（形狀的中文名，`skill_shapes.yaml` 的 `name_zh`）→ 形狀 id。
	* **只當最後的退回**：技能卡有 `icon`（Phase 3-17）時一律讀 `icon.segments[n].shape_id`；
	* 沒有 `icon` 的舊資料才用卡片的中文一句話（例如「錐形（大小 2）」「單體（射程 6）・穿透」）對照。
	*/
	var SHAPE_NAMES = {
		自身: "self",
		單體: "single",
		直線: "line",
		錐形: "cone",
		十字: "cross",
		方陣: "square3",
		環形: "ring",
		指定格: "ground_tile",
		連鎖: "chain",
		範圍光環: "allies_in_radius",
		物件與落點: "object_then_tile",
		單位與落點: "unit_then_tile",
		兩個單位: "unit_pair"
	};
	//#endregion
	//#region client/src/render/labels.ts
	/** 畫布文字的字型清單；須與 `styles/base.css` 的 `body` font-family 同步。 */
	var FONT = "'Noto Sans TC', 'Microsoft JhengHei', system-ui, sans-serif";
	//#endregion
	//#region client/src/render/statusIcon.ts
	var TAU$3 = Math.PI * 2;
	/** 圖樣色：控制類依 control_group。 */
	var CTRL_COLOR = {
		hard: "#ffd84a",
		movement: "#6ac8ff",
		mental: "#c890ff"
	};
	var POL_COLOR = {
		buff: "#7dffb0",
		debuff: "#ff8a8a",
		neutral: "#e8d8a8"
	};
	/** 少數保留自己顏色的狀態（原本的辨識度；圖樣查表的一部分）。 */
	var OWN_COLOR = {
		time_bomb: "#ffb03a",
		shielded: "#8ac8ff",
		guarded: "#8ac8ff",
		stoneskin: "#c8a060",
		defending: "#8ac8ff",
		entangled: "#6ac8ff",
		regenerating: "#7dffb0",
		undying: "#ff8a9a",
		soul_link: "#c8a0ff",
		revealed: "#ffd04a",
		marked: "#ff6a4a",
		overwatch: "#ffd04a",
		infused_fire: "#ff6a1a",
		infused_holy: "#ffe9a0"
	};
	var isPolarity = (p) => p === "buff" || p === "debuff" || p === "neutral";
	/** 狀態的極性：沒有資料或不認得 → neutral。 */
	function polarityOf(id) {
		const p = id == null ? void 0 : statusLook(id)?.polarity;
		return isPolarity(p) ? p : "neutral";
	}
	/** 圖樣顏色：`control_group` → 持續傷害元素 → 專屬色 → `polarity`。 */
	function glyphColor(id) {
		const look = id == null ? void 0 : statusLook(id);
		const ctrl = look?.control_group;
		if (ctrl != null) {
			const c = CTRL_COLOR[ctrl];
			if (c !== void 0) return c;
		}
		if (look?.dot_element != null) return elementColor(look.dot_element);
		return (id == null ? void 0 : OWN_COLOR[id]) ?? POL_COLOR[polarityOf(id)];
	}
	function line(c, pts) {
		c.beginPath();
		pts.forEach(([px, py], i) => i > 0 ? c.lineTo(px, py) : c.moveTo(px, py));
		c.stroke();
	}
	function circle(c, x, y, r, fill = false) {
		c.beginPath();
		c.arc(x, y, r, 0, TAU$3);
		if (fill) c.fill();
		else c.stroke();
	}
	function shield(c) {
		c.beginPath();
		c.moveTo(0, -9);
		c.lineTo(8, -6);
		c.quadraticCurveTo(8, 5, 0, 10);
		c.quadraticCurveTo(-8, 5, -8, -6);
		c.closePath();
		c.stroke();
	}
	function arrow$1(c, x, y, up) {
		const s = up ? -1 : 1;
		line(c, [[x, y - 5 * s], [x, y + 5 * s]]);
		line(c, [
			[x - 4, y - 1 * s],
			[x, y - 5 * s],
			[x + 4, y - 1 * s]
		]);
	}
	function eye$1(c, open) {
		c.beginPath();
		c.moveTo(-10, 0);
		c.quadraticCurveTo(0, -9, 10, 0);
		c.quadraticCurveTo(0, 9, -10, 0);
		c.stroke();
		if (open) circle(c, 0, 0, 3.5, true);
	}
	function star$1(c, x, y, r) {
		c.beginPath();
		for (let i = 0; i < 10; i++) {
			const rad = i % 2 === 1 ? r * .45 : r;
			const a = i / 10 * TAU$3 - Math.PI / 2;
			c.lineTo(x + Math.cos(a) * rad, y + Math.sin(a) * rad);
		}
		c.closePath();
		c.fill();
	}
	function flame(c, x, y, h) {
		c.beginPath();
		c.moveTo(x, y - h);
		c.quadraticCurveTo(x + h * .6, y - h * .2, x + h * .35, y + h * .3);
		c.quadraticCurveTo(x, y + h * .5, x - h * .35, y + h * .3);
		c.quadraticCurveTo(x - h * .6, y - h * .2, x, y - h);
		c.fill();
	}
	function drop$1(c, x, y, s) {
		c.beginPath();
		c.moveTo(x, y - s);
		c.quadraticCurveTo(x + s * .8, y + s * .2, x, y + s * .7);
		c.quadraticCurveTo(x - s * .8, y + s * .2, x, y - s);
		c.fill();
	}
	function sword(c) {
		line(c, [[-6, 7], [6, -7]]);
		line(c, [[-7, 2], [-2, 7]]);
	}
	var STANCE_ELEMENTS = [
		"physical",
		"fire",
		"ice",
		"lightning",
		"poison",
		"wind",
		"earth",
		"holy",
		"shadow"
	];
	var STANCE_LEVELS = 5;
	function elementMark(c, element) {
		switch (element) {
			case "fire":
				c.beginPath();
				c.arc(7, -5, 3, 0, TAU$3);
				c.fill();
				break;
			case "ice":
				line(c, [[4, -5], [10, -5]]);
				line(c, [[7, -8], [7, -2]]);
				break;
			case "lightning":
				line(c, [
					[5, -9],
					[8, -5],
					[5, -4],
					[8, 0]
				]);
				break;
			case "poison":
				c.beginPath();
				c.arc(7, -4, 2.5, 0, TAU$3);
				c.stroke();
				break;
			case "wind":
				line(c, [[3, -7], [10, -7]]);
				line(c, [[4, -3], [9, -3]]);
				break;
			case "earth":
				c.strokeRect(4, -9, 6, 6);
				break;
			case "holy":
				line(c, [[7, -9], [7, -1]]);
				line(c, [[3, -5], [11, -5]]);
				break;
			case "shadow":
				c.beginPath();
				c.arc(7, -5, 3.5, Math.PI * .5, Math.PI * 1.5);
				c.stroke();
		}
	}
	function elementStanceGlyphs() {
		const out = {};
		for (const element of STANCE_ELEMENTS) for (let level = 1; level <= STANCE_LEVELS; level++) out[`stance_${element}_${level}`] = (c) => {
			line(c, [[-8, 5], [4, -7]]);
			line(c, [[-9, 0], [-4, 5]]);
			elementMark(c, element);
			for (let i = 0; i < level; i++) {
				c.beginPath();
				c.arc(-8 + i * 4, 10, 1.2, 0, TAU$3);
				c.fill();
			}
		};
		return out;
	}
	/** 一個狀態一個圖樣（圖樣查表；不認得的狀態畫名稱第一個字）。 */
	var GLYPH = {
		...elementStanceGlyphs(),
		defending: (c) => shield(c),
		guarded: (c) => {
			shield(c);
			arrow$1(c, 0, .5, false);
		},
		stoneskin: (c) => {
			shield(c);
			line(c, [
				[-3, -4],
				[0, -1],
				[-2, 2],
				[1, 5]
			]);
			line(c, [[0, -1], [4, 0]]);
		},
		shielded_thorns: (c) => {
			shield(c);
			line(c, [
				[-3, 2],
				[0, -3],
				[3, 2]
			]);
		},
		shielded_mending: (c) => {
			shield(c);
			line(c, [[0, -4], [0, 4]]);
			line(c, [[-4, 0], [4, 0]]);
		},
		shielded_wet: (c) => {
			shield(c);
			c.beginPath();
			c.arc(0, 1, 2.5, 0, TAU$3);
			c.stroke();
		},
		shielded_marking: (c) => {
			shield(c);
			c.beginPath();
			c.arc(0, 0, 3, 0, TAU$3);
			c.fill();
		},
		shielded_charged: (c) => {
			shield(c);
			line(c, [
				[1, -4],
				[-2, 0],
				[2, 0],
				[-1, 4]
			]);
		},
		shielded: (c) => {
			circle(c, 0, 0, 9);
			c.globalAlpha *= .35;
			c.fill();
			c.globalAlpha /= .35;
			c.beginPath();
			c.arc(0, 0, 5, Math.PI * 1.1, Math.PI * 1.55);
			c.strokeStyle = "#ffffff";
			c.stroke();
		},
		prone: (c) => {
			circle(c, -6, 3, 3, true);
			line(c, [[-2, 4], [9, 4]]);
			line(c, [[-10, 8], [10, 8]]);
		},
		burning: (c) => flame(c, 0, 1, 10),
		poison: (c) => {
			drop$1(c, 0, 0, 10);
			c.fillStyle = "#1a2a10";
			c.beginPath();
			c.arc(-2, 2, 2, 0, TAU$3);
			c.arc(3, -1, 1.4, 0, TAU$3);
			c.fill();
		},
		bleed: (c) => {
			drop$1(c, -3, -1, 7);
			drop$1(c, 5, 3, 5);
		},
		concealed: (c) => {
			c.globalAlpha *= .55;
			circle(c, 0, -4, 4, true);
			c.beginPath();
			c.moveTo(-8, 9);
			c.quadraticCurveTo(0, -2, 8, 9);
			c.fill();
			c.globalAlpha /= .55;
			line(c, [[-9, 9], [9, -9]]);
		},
		revealed: (c) => {
			eye$1(c, true);
			line(c, [[-9, -9], [-5, -6]]);
			line(c, [[9, -9], [5, -6]]);
			line(c, [[0, -10], [0, -7]]);
		},
		overwatch: (c) => {
			circle(c, 0, 0, 7);
			line(c, [[0, -10], [0, -4]]);
			line(c, [[0, 4], [0, 10]]);
			line(c, [[-10, 0], [-4, 0]]);
			line(c, [[4, 0], [10, 0]]);
			circle(c, 0, 0, 1.8, true);
		},
		marked: (c) => {
			line(c, [[-7, -7], [7, 7]]);
			line(c, [[7, -7], [-7, 7]]);
			circle(c, 0, 0, 9);
		},
		time_bomb: (c) => {
			circle(c, -1, 2, 7, true);
			line(c, [[3, -4], [7, -9]]);
			c.fillStyle = "#fff";
			star$1(c, 8, -9, 3);
		},
		charging: (c) => {
			circle(c, 0, 0, 8);
			circle(c, 0, 0, 3.5, true);
		},
		shard_burst: (c) => {
			star$1(c, -4, -4, 4);
			star$1(c, 5, -2, 3);
			drop$1(c, 0, 5, 5);
		},
		sword_formation: (c) => {
			for (const x of [
				-6,
				0,
				6
			]) {
				line(c, [[x, -9], [x, 6]]);
				line(c, [[x - 2.5, 3], [x + 2.5, 3]]);
			}
		},
		array_ward: (c) => {
			circle(c, 0, 0, 8.5);
			circle(c, 0, 0, 3, true);
		},
		oath_bonus_easy: (c) => {
			star$1(c, 0, -2, 6);
			circle(c, 0, 8, 1.5, true);
		},
		oath_bonus_medium: (c) => {
			star$1(c, 0, -2, 6);
			circle(c, -3, 8, 1.5, true);
			circle(c, 3, 8, 1.5, true);
		},
		oath_bonus_hard: (c) => {
			star$1(c, 0, -2, 6);
			for (const x of [
				-5,
				0,
				5
			]) circle(c, x, 8, 1.5, true);
		},
		oath_broken: (c) => {
			star$1(c, 0, 0, 6);
			line(c, [[-8, 8], [8, -8]]);
		},
		summit_array_ward: (c) => {
			circle(c, 0, 0, 8.5);
			circle(c, 0, 0, 5);
			circle(c, 0, 0, 2, true);
		},
		mist_return: (c) => {
			circle(c, 0, 2, 7.5);
			drop$1(c, 0, -2, 5);
		},
		league_truce: (c) => {
			circle(c, 0, 0, 8.5);
			line(c, [[-3, -4.5], [-3, 4.5]]);
			line(c, [[3, -4.5], [3, 4.5]]);
		},
		rift_resonance: (c) => {
			circle(c, 0, 0, 8.5);
			line(c, [
				[0, -6],
				[4, 0],
				[0, 6],
				[-4, 0],
				[0, -6]
			]);
		},
		rift_channel: (c) => {
			line(c, [
				[0, -5],
				[3.5, 0],
				[0, 5],
				[-3.5, 0],
				[0, -5]
			]);
			line(c, [[0, -6.5], [0, -9.5]]);
			line(c, [[-5, 4], [-8, 6.5]]);
			line(c, [[5, 4], [8, 6.5]]);
		},
		crystal_surge: (c) => {
			line(c, [
				[0, -8],
				[5, -1],
				[0, 6],
				[-5, -1],
				[0, -8]
			]);
			circle(c, 0, 9, 1.5, true);
		},
		crystal_surge_2: (c) => {
			line(c, [
				[0, -8],
				[5, -1],
				[0, 6],
				[-5, -1],
				[0, -8]
			]);
			circle(c, -3, 9, 1.5, true);
			circle(c, 3, 9, 1.5, true);
		},
		rift_collapse: (c) => {
			line(c, [
				[-1, -8],
				[-6, 0],
				[-1, 8]
			]);
			line(c, [
				[1, -8],
				[6, 0],
				[1, 8]
			]);
			line(c, [
				[0, -6],
				[2, -1],
				[-2, 2],
				[0, 6]
			]);
		},
		molten_burst: (c) => {
			star$1(c, -5, -4, 3.5);
			star$1(c, 5, -4, 3.5);
			flame(c, 0, 4, 7);
		},
		heart_ember_burst: (c) => {
			line(c, [
				[-8, -2],
				[-5, -7],
				[0, -8.5],
				[5, -7],
				[8, -2]
			]);
			star$1(c, 0, -3, 3);
			flame(c, 0, 4, 7);
		},
		frost_ember_burst: (c) => {
			star$1(c, -5, -5, 3.5);
			star$1(c, 5, -5, 3.5);
			for (let i = 0; i < 3; i++) {
				const a = i / 3 * Math.PI;
				line(c, [[Math.cos(a) * -5, 4 + Math.sin(a) * -5], [Math.cos(a) * 5, 4 + Math.sin(a) * 5]]);
			}
		},
		molten_shell: (c) => {
			circle(c, 0, 0, 8.5);
			flame(c, 0, 2, 7);
		},
		hard_shell: (c) => {
			line(c, [
				[-8, 4],
				[-5, -4],
				[0, -7],
				[5, -4],
				[8, 4]
			]);
			line(c, [
				[-5, 6],
				[-3, 0],
				[0, -2],
				[3, 0],
				[5, 6]
			]);
		},
		heart_link: (c) => {
			circle(c, -5, 0, 4);
			circle(c, 5, 0, 4);
			line(c, [[-1, 0], [1, 0]]);
		},
		slow: (c) => {
			circle(c, 0, 0, 8.5);
			line(c, [[0, 0], [0, -6]]);
			line(c, [[0, 0], [4, 3]]);
		},
		root: (c) => {
			line(c, [[0, -9], [0, 4]]);
			line(c, [[0, 4], [-7, 9]]);
			line(c, [[0, 4], [7, 9]]);
			line(c, [[0, 1], [-5, -3]]);
		},
		stun: (c) => {
			star$1(c, -5, -3, 5);
			star$1(c, 5, -3, 5);
			star$1(c, 0, 5, 5);
		},
		frozen: (c) => {
			for (let i = 0; i < 3; i++) {
				const a = i / 3 * Math.PI;
				line(c, [[Math.cos(a) * -10, Math.sin(a) * -10], [Math.cos(a) * 10, Math.sin(a) * 10]]);
			}
			circle(c, 0, 0, 2.5, true);
		},
		weaken: (c) => {
			sword(c);
			arrow$1(c, 6, 3, false);
		},
		empowered: (c) => {
			line(c, [
				[-8, 0],
				[0, -8],
				[8, 0]
			]);
			line(c, [
				[-8, 8],
				[0, 0],
				[8, 8]
			]);
		},
		commanding: (c) => {
			line(c, [[-9, 9], [-1, -1]]);
			circle(c, -3, -5, 2.4, true);
			circle(c, 3, 5, 3.5);
			arrow$1(c, 8, -3, true);
		},
		infused_fire: (c) => {
			sword(c);
			circle(c, 7, -7, 2.8, true);
			circle(c, -7, 7, 1.6, true);
		},
		infused_holy: (c) => {
			sword(c);
			line(c, [[7, -10], [7, -4]]);
			line(c, [[4, -7], [10, -7]]);
		},
		race_adapt: (c) => {
			line(c, [[-9, 0], [7, 0]]);
			line(c, [
				[2, -6],
				[8, 0],
				[2, 6]
			]);
			line(c, [[-9, -6], [-4, -6]]);
			line(c, [[-9, 6], [-4, 6]]);
		},
		race_stonewall: (c) => {
			shield(c);
			line(c, [[-6, 8], [6, 8]]);
			line(c, [[-3, 5], [3, 5]]);
		},
		rallied: (c) => {
			line(c, [[-6, 10], [-6, -9]]);
			c.beginPath();
			c.moveTo(-6, -9);
			c.lineTo(8, -5);
			c.lineTo(-6, -1);
			c.closePath();
			c.fill();
		},
		vulnerable: (c) => {
			shield(c);
			line(c, [
				[-2, -8],
				[2, -2],
				[-2, 2],
				[2, 9]
			]);
		},
		entangled: (c) => {
			c.beginPath();
			c.moveTo(-9, -6);
			c.bezierCurveTo(-2, -12, 6, -2, -1, 0);
			c.bezierCurveTo(-8, 2, 0, 8, 9, 2);
			c.stroke();
			arrow$1(c, -5, 5, false);
		},
		armor_broken: (c) => {
			c.beginPath();
			c.moveTo(-8, -6);
			c.lineTo(0, -9);
			c.lineTo(8, -6);
			c.lineTo(8, 1);
			c.lineTo(0, 9);
			c.lineTo(-8, 1);
			c.closePath();
			c.stroke();
			arrow$1(c, 0, 0, false);
		},
		hasted: (c) => {
			line(c, [
				[-8, -7],
				[-1, 0],
				[-8, 7]
			]);
			line(c, [
				[1, -7],
				[8, 0],
				[1, 7]
			]);
		},
		regenerating: (c) => {
			c.fillRect(-2.5, -9, 5, 18);
			c.fillRect(-9, -2.5, 18, 5);
		},
		undying: (c) => {
			c.beginPath();
			c.moveTo(0, 9);
			c.bezierCurveTo(-12, 0, -6, -10, 0, -4);
			c.bezierCurveTo(6, -10, 12, 0, 0, 9);
			c.fill();
			c.fillStyle = "#000";
			c.fillRect(-1, -4, 2, 9);
			c.fillRect(-3.5, -1.5, 7, 2);
		},
		soul_link: (c) => {
			circle(c, -4, 0, 5.5);
			circle(c, 4, 0, 5.5);
		},
		taunted: (c) => {
			circle(c, 0, 0, 9);
			circle(c, 0, 0, 4.5);
			circle(c, 0, 0, 1.5, true);
		},
		feared: (c) => {
			c.font = `bold 17px ${FONT}`;
			c.textAlign = "center";
			c.textBaseline = "middle";
			c.fillText("!", 0, 1);
			line(c, [[-8, -6], [-5, -3]]);
			line(c, [[8, -6], [5, -3]]);
		},
		overdrawn: (c) => {
			c.beginPath();
			c.roundRect(-8, -6, 14, 12, 2);
			c.stroke();
			line(c, [
				[6, -2],
				[9, -2],
				[9, 2],
				[6, 2]
			]);
			arrow$1(c, -1, 0, false);
		},
		silenced: (c) => {
			c.beginPath();
			c.roundRect(-9, -7, 18, 12, 4);
			c.stroke();
			c.beginPath();
			c.moveTo(-3, 5);
			c.lineTo(-6, 10);
			c.lineTo(2, 5);
			c.stroke();
			line(c, [[-10, 9], [10, -9]]);
		},
		blinded: (c) => {
			eye$1(c, false);
			line(c, [[-9, 7], [9, -7]]);
		},
		stance_fury: (c) => {
			for (const dx of [
				-5,
				0,
				5
			]) line(c, [[dx - 3, 8], [dx + 3, -8]]);
		},
		stance_bulwark: (c) => {
			c.fillRect(-8, -2, 16, 10);
			for (const dx of [
				-8,
				-2,
				4
			]) c.fillRect(dx, -7, 4, 5);
		},
		stance_guard: (c) => {
			c.beginPath();
			c.moveTo(-8, -8);
			c.lineTo(8, -8);
			c.lineTo(8, 1);
			c.lineTo(0, 10);
			c.lineTo(-8, 1);
			c.closePath();
			c.stroke();
		},
		stance_bastion: (c) => {
			c.strokeRect(-9, -8, 18, 16);
			line(c, [[-9, -2], [9, -2]]);
			line(c, [[-9, 4], [9, 4]]);
			line(c, [[0, -8], [0, -2]]);
		},
		stance_ironwall: (c) => {
			c.strokeRect(-9, -7, 18, 14);
			line(c, [[-9, 0], [9, 0]]);
			line(c, [[-3, -7], [-3, 0]]);
			line(c, [[3, 0], [3, 7]]);
		},
		stance_flame: (c) => {
			line(c, [[-7, 8], [7, -8]]);
			line(c, [[-9, 3], [-3, 9]]);
			c.beginPath();
			c.arc(7, 6, 3, 0, TAU$3);
			c.fill();
		},
		stance_blaze: (c) => {
			c.beginPath();
			c.moveTo(0, -10);
			c.quadraticCurveTo(9, -1, 6, 6);
			c.quadraticCurveTo(0, 12, -6, 6);
			c.quadraticCurveTo(-8, 0, -2, -4);
			c.quadraticCurveTo(-1, -7, 0, -10);
			c.closePath();
			c.stroke();
		},
		stance_frost: (c) => {
			line(c, [[-7, 8], [7, -8]]);
			line(c, [[3, 4], [9, 4]]);
			line(c, [[6, 1], [6, 7]]);
		},
		stance_glacier: (c) => {
			for (const [x, y] of [
				[0, 9],
				[8, 4.5],
				[8, -4.5]
			]) line(c, [[-x, -y], [x, y]]);
		}
	};
	/** 在以 (0,0) 為中心、半徑約 10 的範圍畫狀態圖樣（顏色與線寬由呼叫端設）；不認得的狀態畫名稱第一個字。 */
	function drawGlyph(c, id) {
		const known = id == null ? void 0 : GLYPH[id];
		if (known !== void 0) {
			known(c);
			return;
		}
		const name = id == null || id === "" ? "?" : statusName(id);
		c.font = `bold 13px ${FONT}`;
		c.textAlign = "center";
		c.textBaseline = "middle";
		c.fillText([...name][0] ?? "?", 0, 1);
	}
	//#endregion
	//#region client/src/render/skillGlyphs.ts
	var TAU$2 = Math.PI * 2;
	/** 元素 → 圖示配色；顏色與特效共用 `render/palette.ts` 的 `ELEMENT_COLORS`（唯一來源）。 */
	var ELEMENT_ICON = Object.fromEntries(Object.entries(ELEMENT_COLORS).map(([id, c]) => [id, {
		name: c.name,
		accent: c.accent,
		dark: c.dark,
		light: c.light
	}]));
	var DEFAULT_ELEMENT_ICON = {
		name: "（無）",
		accent: "#e8e0ff",
		dark: "#221c44",
		light: "#6a5ad0"
	};
	/** 工坊還沒選元素時的中性色。 */
	var NEUTRAL_ELEMENT_ICON = {
		name: "（未選）",
		accent: "#c8ccd4",
		dark: "#23262d",
		light: "#4a4f5a"
	};
	/** 元素代碼 → 配色；`undefined` ＝ 還沒選（中性），其他不認得 ＝ 預設。 */
	function elementPalette(el) {
		if (el === void 0) return NEUTRAL_ELEMENT_ICON;
		if (el === null) return DEFAULT_ELEMENT_ICON;
		return ELEMENT_ICON[el] ?? DEFAULT_ELEMENT_ICON;
	}
	var RARITY_COLOR = {
		common: "#9aa0a6",
		rare: "#4da3ff",
		epic: "#b06cff",
		legendary: "#ffbf3a"
	};
	var rarityColor = (rarity) => RARITY_COLOR[rarity] ?? "#6a6f7a";
	var SKELETON_NAME = {
		strike: "打擊",
		area: "範圍",
		control: "控制",
		aura: "增益",
		summon: "召喚",
		trap: "陷阱",
		displace: "位移",
		consume_status: "引爆狀態",
		builder_finisher: "累積終結",
		stance: "姿態",
		reaction: "反應",
		modifier: "改造",
		passive: "被動",
		combo: "連段",
		rune: "刻印",
		sacrifice: "獻祭"
	};
	function starPath(ctx, cx, cy, n, ro, ri, rot = -Math.PI / 2) {
		ctx.beginPath();
		for (let i = 0; i < n * 2; i++) {
			const r = i % 2 === 0 ? ro : ri;
			const a = rot + i / (n * 2) * TAU$2;
			ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
		}
		ctx.closePath();
	}
	function figure(ctx, cx, cy, k, color) {
		ctx.fillStyle = color;
		ctx.beginPath();
		ctx.arc(cx, cy - 9 * k, 6 * k, 0, TAU$2);
		ctx.fill();
		ctx.beginPath();
		ctx.moveTo(cx - 11 * k, cy + 12 * k);
		ctx.quadraticCurveTo(cx - 11 * k, cy - 2 * k, cx, cy - 1 * k);
		ctx.quadraticCurveTo(cx + 11 * k, cy - 2 * k, cx + 11 * k, cy + 12 * k);
		ctx.closePath();
		ctx.fill();
	}
	/** 先畫深色描邊再畫本體，縮小時仍清楚。 */
	function outlined(ctx, path, color, width = 5) {
		ctx.save();
		ctx.strokeStyle = "rgba(0,0,0,0.55)";
		ctx.lineWidth = width;
		ctx.lineJoin = "round";
		path();
		ctx.stroke();
		ctx.restore();
		ctx.fillStyle = color;
		path();
		ctx.fill();
	}
	function elementGlyph(ctx, el, cx, cy, k, color) {
		ctx.save();
		ctx.translate(cx, cy);
		ctx.scale(k, k);
		ctx.fillStyle = color;
		ctx.strokeStyle = color;
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		switch (el) {
			case "fire":
				ctx.beginPath();
				ctx.moveTo(0, -10);
				ctx.bezierCurveTo(7, -3, 8, 3, 0, 9);
				ctx.bezierCurveTo(-8, 3, -6, -2, -2, -4);
				ctx.bezierCurveTo(-2, -1, 0, 0, 0, -10);
				ctx.fill();
				break;
			case "ice":
				iceGlyph(ctx);
				break;
			case "lightning":
				ctx.beginPath();
				ctx.moveTo(3, -11);
				ctx.lineTo(-6, 1);
				ctx.lineTo(0, 1);
				ctx.lineTo(-3, 11);
				ctx.lineTo(7, -2);
				ctx.lineTo(1, -2);
				ctx.lineTo(5, -11);
				ctx.closePath();
				ctx.fill();
				break;
			case "poison":
				ctx.beginPath();
				ctx.moveTo(0, -10);
				ctx.bezierCurveTo(8, -1, 8, 8, 0, 8);
				ctx.bezierCurveTo(-8, 8, -8, -1, 0, -10);
				ctx.fill();
				ctx.fillStyle = "rgba(0,0,0,0.35)";
				ctx.beginPath();
				ctx.arc(-2, 2, 2.2, 0, TAU$2);
				ctx.arc(2.5, 4.5, 1.4, 0, TAU$2);
				ctx.fill();
				break;
			case "wind":
				ctx.lineWidth = 2.6;
				ctx.beginPath();
				ctx.moveTo(-10, -4);
				ctx.lineTo(4, -4);
				ctx.arc(4, -7.5, 3.5, Math.PI / 2, -Math.PI * .9, true);
				ctx.moveTo(-10, 2);
				ctx.lineTo(7, 2);
				ctx.arc(7, 6, 4, -Math.PI / 2, Math.PI * .9);
				ctx.moveTo(-7, 8);
				ctx.lineTo(-1, 8);
				ctx.stroke();
				break;
			case "earth":
				ctx.beginPath();
				ctx.moveTo(-11, 8);
				ctx.lineTo(-4, -6);
				ctx.lineTo(0, 0);
				ctx.lineTo(4, -9);
				ctx.lineTo(11, 8);
				ctx.closePath();
				ctx.fill();
				break;
			case "holy":
				starPath(ctx, 0, 0, 4, 11, 3.2);
				ctx.fill();
				starPath(ctx, 0, 0, 4, 6, 2, -Math.PI / 4);
				ctx.fill();
				break;
			case "shadow":
				ctx.beginPath();
				ctx.arc(0, 0, 9, 0, TAU$2);
				ctx.arc(4, -3, 7.5, 0, TAU$2, true);
				ctx.fill("evenodd");
				break;
			case "physical":
				starPath(ctx, 0, 0, 4, 10, 2.6, 0);
				ctx.fill();
				break;
			default:
				ctx.beginPath();
				for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos(i / 6 * TAU$2) * 8, Math.sin(i / 6 * TAU$2) * 8);
				ctx.closePath();
				ctx.fill();
				ctx.fillStyle = "rgba(255,255,255,0.6)";
				ctx.fillRect(-2, -5, 3, 10);
		}
		ctx.restore();
	}
	function iceGlyph(ctx) {
		ctx.lineWidth = 2.4;
		ctx.beginPath();
		for (let i = 0; i < 3; i++) {
			const a = i / 3 * Math.PI + Math.PI / 2;
			ctx.moveTo(Math.cos(a) * 9, Math.sin(a) * 9);
			ctx.lineTo(-Math.cos(a) * 9, -Math.sin(a) * 9);
		}
		for (let i = 0; i < 6; i++) {
			const a = i / 6 * TAU$2 + Math.PI / 2;
			const bx = Math.cos(a) * 5.5;
			const by = Math.sin(a) * 5.5;
			ctx.moveTo(bx, by);
			ctx.lineTo(bx + Math.cos(a + .8) * 3.5, by + Math.sin(a + .8) * 3.5);
			ctx.moveTo(bx, by);
			ctx.lineTo(bx + Math.cos(a - .8) * 3.5, by + Math.sin(a - .8) * 3.5);
		}
		ctx.stroke();
	}
	function elementTexture(ctx, el, p) {
		ctx.save();
		ctx.globalAlpha = .18;
		ctx.strokeStyle = p.accent;
		ctx.fillStyle = p.accent;
		ctx.lineWidth = 2;
		switch (el) {
			case "fire":
				for (let i = 0; i < 5; i++) elementGlyph(ctx, "fire", 10 + i * 20, 96, 1.3 + i % 2 * .5, p.accent);
				break;
			case "ice":
				ctx.beginPath();
				ctx.moveTo(0, 30);
				ctx.lineTo(30, 0);
				ctx.moveTo(60, 100);
				ctx.lineTo(100, 55);
				ctx.moveTo(0, 70);
				ctx.lineTo(45, 100);
				ctx.moveTo(70, 0);
				ctx.lineTo(100, 25);
				ctx.stroke();
				break;
			case "lightning":
				ctx.beginPath();
				ctx.moveTo(0, 20);
				ctx.lineTo(20, 32);
				ctx.lineTo(12, 40);
				ctx.lineTo(36, 54);
				ctx.moveTo(100, 60);
				ctx.lineTo(82, 70);
				ctx.lineTo(90, 78);
				ctx.lineTo(66, 96);
				ctx.stroke();
				break;
			case "poison":
				for (const [x, y, r] of [
					[
						14,
						30,
						6
					],
					[
						86,
						40,
						8
					],
					[
						28,
						88,
						5
					],
					[
						74,
						86,
						4
					],
					[
						60,
						12,
						3
					]
				]) {
					ctx.beginPath();
					ctx.arc(x, y, r, 0, TAU$2);
					ctx.stroke();
				}
				break;
			case "wind":
				for (let i = 0; i < 3; i++) {
					ctx.beginPath();
					ctx.arc(50, 50, 22 + i * 14, -.4 + i, 1.4 + i);
					ctx.stroke();
				}
				break;
			case "earth":
				ctx.beginPath();
				ctx.moveTo(0, 78);
				ctx.lineTo(30, 72);
				ctx.lineTo(60, 80);
				ctx.lineTo(100, 70);
				ctx.moveTo(0, 90);
				ctx.lineTo(40, 86);
				ctx.lineTo(100, 92);
				ctx.stroke();
				break;
			case "holy":
				holyRays(ctx);
				break;
			case "shadow":
				ctx.globalAlpha = .25;
				ctx.fillStyle = "#000";
				for (const [x, y, r] of [
					[
						10,
						90,
						26
					],
					[
						90,
						10,
						22
					],
					[
						95,
						85,
						16
					]
				]) {
					ctx.beginPath();
					ctx.arc(x, y, r, 0, TAU$2);
					ctx.fill();
				}
				break;
			case "physical":
				ctx.beginPath();
				for (let i = -100; i < 100; i += 9) {
					ctx.moveTo(i, 100);
					ctx.lineTo(i + 100, 0);
				}
				ctx.globalAlpha = .07;
				ctx.stroke();
		}
		ctx.restore();
	}
	function holyRays(ctx) {
		for (let i = 0; i < 12; i++) {
			const a = i / 12 * TAU$2;
			ctx.beginPath();
			ctx.moveTo(50, 50);
			ctx.lineTo(50 + Math.cos(a - .08) * 80, 50 + Math.sin(a - .08) * 80);
			ctx.lineTo(50 + Math.cos(a + .08) * 80, 50 + Math.sin(a + .08) * 80);
			ctx.fill();
		}
	}
	/** 畫元素底色（漸層＋淡紋理）；`el` 為 `undefined`（還沒選）時只有中性漸層。 */
	function paintBackground(ctx, el) {
		const p = elementPalette(el);
		const bg = ctx.createRadialGradient(38, 30, 4, 50, 50, 78);
		bg.addColorStop(0, p.light);
		bg.addColorStop(1, p.dark);
		ctx.fillStyle = bg;
		ctx.fillRect(0, 0, 100, 100);
		if (el !== void 0) elementTexture(ctx, el ?? "default", p);
	}
	function projectile(ctx, el, p) {
		const x0 = 22;
		const y0 = 78;
		const x1 = 64;
		const y1 = 36;
		const g = ctx.createLinearGradient(x0, y0, x1, y1);
		g.addColorStop(0, "rgba(255,255,255,0)");
		g.addColorStop(1, p.accent);
		ctx.fillStyle = g;
		ctx.beginPath();
		ctx.moveTo(x0, y0);
		ctx.lineTo(58, 30);
		ctx.lineTo(70, 42);
		ctx.closePath();
		ctx.fill();
		ctx.fillStyle = p.accent;
		ctx.globalAlpha = .5;
		ctx.beginPath();
		ctx.arc(x1, y1, 17, 0, TAU$2);
		ctx.fill();
		ctx.globalAlpha = 1;
		ctx.save();
		ctx.translate(x1, y1);
		ctx.rotate(Math.PI / 4);
		ctx.translate(-64, -36);
		elementGlyph(ctx, el, x1, y1, 1.55, "#ffffff");
		ctx.restore();
	}
	function slash(ctx, el, p) {
		const crescent = (dx, dy) => {
			ctx.beginPath();
			ctx.moveTo(24 + dx, 24 + dy);
			ctx.quadraticCurveTo(90 + dx, 12 + dy, 78 + dx, 80 + dy);
			ctx.quadraticCurveTo(70 + dx, 34 + dy, 24 + dx, 24 + dy);
			ctx.closePath();
		};
		crescent(3, 3);
		ctx.fillStyle = "rgba(0,0,0,0.4)";
		ctx.fill();
		crescent(0, 0);
		const g = ctx.createLinearGradient(24, 24, 80, 80);
		g.addColorStop(0, p.accent);
		g.addColorStop(.5, "#ffffff");
		g.addColorStop(1, p.accent);
		ctx.fillStyle = g;
		ctx.fill();
		elementGlyph(ctx, el, 40, 62, 1.3, p.accent);
	}
	function buffTarget(ctx, el, p) {
		ctx.fillStyle = p.accent;
		ctx.globalAlpha = .35;
		ctx.beginPath();
		ctx.ellipse(46, 78, 24, 8, 0, 0, TAU$2);
		ctx.fill();
		ctx.globalAlpha = 1;
		figure(ctx, 46, 64, 1.25, "#ffffff");
		ctx.strokeStyle = p.accent;
		ctx.lineWidth = 4.5;
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		for (const y of [36, 48]) {
			ctx.beginPath();
			ctx.moveTo(64, y + 8);
			ctx.lineTo(72, y);
			ctx.lineTo(80, y + 8);
			ctx.stroke();
		}
		elementGlyph(ctx, el, 46, 30, .9, p.accent);
	}
	function beam(ctx, el, p) {
		ctx.save();
		ctx.translate(50, 50);
		ctx.rotate(-Math.PI / 4);
		ctx.fillStyle = p.accent;
		ctx.globalAlpha = .45;
		ctx.fillRect(-42, -12, 84, 24);
		ctx.globalAlpha = 1;
		ctx.fillStyle = "#ffffff";
		ctx.fillRect(-42, -5, 84, 10);
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		for (let i = -1; i <= 1; i++) ctx.fillRect(i * 24 - 5, -5, 10, 10);
		ctx.restore();
		elementGlyph(ctx, el, 74, 26, 1, p.accent);
	}
	function fan(ctx, el, p) {
		const ox = 22;
		const oy = 78;
		const a = -Math.PI / 4;
		ctx.save();
		ctx.beginPath();
		ctx.moveTo(ox, oy);
		ctx.arc(ox, oy, 66, a - .55, a + .55);
		ctx.closePath();
		const g = ctx.createRadialGradient(ox, oy, 4, ox, oy, 66);
		g.addColorStop(0, "#ffffff");
		g.addColorStop(1, p.accent);
		ctx.fillStyle = g;
		ctx.globalAlpha = .9;
		ctx.fill();
		ctx.globalAlpha = 1;
		ctx.strokeStyle = "rgba(0,0,0,0.3)";
		ctx.lineWidth = 2;
		for (const rr of [30, 48]) {
			ctx.beginPath();
			ctx.arc(ox, oy, rr, a - .55, a + .55);
			ctx.stroke();
		}
		ctx.restore();
		elementGlyph(ctx, el, 60, 42, 1.3, "rgba(0,0,0,0.45)");
	}
	var GRID = {
		square3: [
			1,
			1,
			1,
			1,
			1,
			1,
			1,
			1,
			1
		],
		cross: [
			0,
			1,
			0,
			1,
			1,
			1,
			0,
			1,
			0
		],
		ring: [
			1,
			1,
			1,
			1,
			0,
			1,
			1,
			1,
			1
		]
	};
	/** 5F-ART1（`docs/archive/art/大十字圖示.md`）：臂長 ≥ 2 的十字畫 5×5（亮中心列與中心行 9 格）。 */
	var BIG_CROSS = Array.from({ length: 25 }, (_, i) => i % 5 === 2 || Math.floor(i / 5) === 2 ? 1 : 0);
	/** 臂長：不是 ≥ 1 的整數（缺欄位、0、負數、非整數）一律當 1。 */
	function normalizeArm(arm) {
		return typeof arm === "number" && Number.isInteger(arm) && arm >= 1 ? arm : 1;
	}
	/** 形狀格子的版面：`n`×`n` 格、每格 `cs`、間距 `gap`、亮格表（3×3 與 5×5 的總寬都是 63）。 */
	function gridLayout(shape, arm) {
		if (shape === "cross" && normalizeArm(arm) >= 2) return {
			n: 5,
			cs: 11,
			gap: 2,
			cells: BIG_CROSS
		};
		return {
			n: 3,
			cs: 19,
			gap: 3,
			cells: GRID[shape] ?? GRID["square3"] ?? []
		};
	}
	function grid(ctx, el, p, shape, arm) {
		const { n, cs, gap, cells } = gridLayout(shape, arm);
		const big = n === 5;
		const o = 50 - (cs * n + gap * (n - 1)) / 2;
		for (let i = 0; i < n * n; i++) {
			const x = o + i % n * (cs + gap);
			const y = o + Math.floor(i / n) * (cs + gap);
			ctx.beginPath();
			ctx.roundRect(x, y, cs, cs, big ? 2 : 3);
			if (cells[i] === 1) {
				ctx.fillStyle = p.accent;
				ctx.globalAlpha = .85;
				ctx.fill();
				ctx.globalAlpha = 1;
			} else {
				ctx.strokeStyle = "rgba(255,255,255,0.45)";
				ctx.lineWidth = 1.5;
				ctx.stroke();
			}
		}
		if (shape === "ring") figure(ctx, 50, 52, .62, "#ffffff");
		else {
			const k = big ? .7 : 1;
			outlined(ctx, () => starPath(ctx, 50, 50, 8 * k, 17 * k, 8), "#ffffff", 4);
			elementGlyph(ctx, el, 50, 50, .9 * k, p.dark);
		}
	}
	function chain(ctx, el, p) {
		const pts = [
			[22, 72],
			[48, 30],
			[78, 62]
		];
		ctx.strokeStyle = "#ffffff";
		ctx.lineWidth = 3;
		ctx.lineJoin = "round";
		ctx.beginPath();
		for (let i = 0; i < pts.length - 1; i++) {
			const [ax, ay] = pts[i];
			const [bx, by] = pts[i + 1];
			ctx.moveTo(ax, ay);
			for (let k = 1; k < 5; k++) {
				const t = k / 5;
				const nx = -(by - ay);
				const ny = bx - ax;
				const len = Math.hypot(nx, ny);
				const off = (k % 2 === 1 ? 5 : -5) / len;
				ctx.lineTo(ax + (bx - ax) * t + nx * off, ay + (by - ay) * t + ny * off);
			}
			ctx.lineTo(bx, by);
		}
		ctx.stroke();
		for (const [x, y] of pts) {
			ctx.fillStyle = p.accent;
			ctx.beginPath();
			ctx.arc(x, y, 9, 0, TAU$2);
			ctx.fill();
			ctx.strokeStyle = "rgba(0,0,0,0.4)";
			ctx.lineWidth = 2;
			ctx.stroke();
		}
		elementGlyph(ctx, el, 48, 30, .6, p.dark);
	}
	function groundMarker(ctx, p) {
		ctx.save();
		for (const [rx, a] of [
			[30, .35],
			[22, .6],
			[13, .9]
		]) {
			ctx.strokeStyle = p.accent;
			ctx.globalAlpha = a;
			ctx.lineWidth = 3;
			ctx.beginPath();
			ctx.ellipse(50, 70, rx, rx * .4, 0, 0, TAU$2);
			ctx.stroke();
		}
		ctx.restore();
	}
	function trapJaws(ctx, el, p) {
		for (const [base, tip, color] of [[
			50,
			62,
			"#ffffff"
		], [
			76,
			64,
			"#d8dce4"
		]]) {
			ctx.fillStyle = color;
			ctx.beginPath();
			ctx.moveTo(26, base);
			for (let i = 0; i < 6; i++) {
				ctx.lineTo(26 + i * 8 + 4, tip);
				ctx.lineTo(26 + (i + 1) * 8, base);
			}
			ctx.lineTo(74, base + (base < tip ? -4 : 4));
			ctx.lineTo(26, base + (base < tip ? -4 : 4));
			ctx.closePath();
			ctx.fill();
		}
		elementGlyph(ctx, el, 50, 28, 1, p.accent);
	}
	function ground(ctx, el, p, skeleton) {
		groundMarker(ctx, p);
		if (skeleton === "summon") {
			ctx.save();
			ctx.beginPath();
			ctx.rect(0, 0, 100, 70);
			ctx.clip();
			figure(ctx, 50, 54, 1.25, "#ffffff");
			ctx.restore();
			elementGlyph(ctx, el, 50, 42, .7, p.dark);
		} else if (skeleton === "trap") trapJaws(ctx, el, p);
		else {
			ctx.fillStyle = p.accent;
			ctx.beginPath();
			ctx.moveTo(50, 60);
			ctx.lineTo(40, 46);
			ctx.lineTo(60, 46);
			ctx.closePath();
			ctx.fill();
			elementGlyph(ctx, el, 50, 32, 1.4, "#ffffff");
		}
	}
	function selfAura(ctx, p, skeleton) {
		for (const [r, a] of [
			[36, .25],
			[28, .45],
			[20, .7]
		]) {
			ctx.strokeStyle = p.accent;
			ctx.globalAlpha = a;
			ctx.lineWidth = 4;
			ctx.beginPath();
			ctx.arc(50, 52, r, 0, TAU$2);
			ctx.stroke();
		}
		ctx.globalAlpha = 1;
		figure(ctx, 50, 56, 1, "#ffffff");
		if (skeleton === "stance") outlined(ctx, () => {
			ctx.beginPath();
			ctx.moveTo(50, 40);
			ctx.lineTo(62, 45);
			ctx.lineTo(60, 60);
			ctx.lineTo(50, 68);
			ctx.lineTo(40, 60);
			ctx.lineTo(38, 45);
			ctx.closePath();
		}, p.accent, 4);
	}
	function alliesRadius(ctx, el, p) {
		ctx.strokeStyle = p.accent;
		ctx.lineWidth = 4;
		ctx.beginPath();
		ctx.arc(50, 72, 38, Math.PI, 0);
		ctx.stroke();
		ctx.globalAlpha = .2;
		ctx.fillStyle = p.accent;
		ctx.fill();
		ctx.globalAlpha = 1;
		figure(ctx, 28, 66, .7, "rgba(255,255,255,0.75)");
		figure(ctx, 72, 66, .7, "rgba(255,255,255,0.75)");
		figure(ctx, 50, 60, 1, "#ffffff");
		elementGlyph(ctx, el, 50, 30, .9, p.accent);
	}
	function hurl(ctx, el, p) {
		ctx.strokeStyle = p.accent;
		ctx.setLineDash([5, 4]);
		ctx.lineWidth = 3;
		ctx.beginPath();
		ctx.moveTo(24, 76);
		ctx.quadraticCurveTo(50, 8, 76, 70);
		ctx.stroke();
		ctx.setLineDash([]);
		ctx.fillStyle = "#c8894a";
		ctx.fillRect(40, 22, 20, 20);
		ctx.strokeStyle = "#5a3412";
		ctx.lineWidth = 2;
		ctx.strokeRect(40, 22, 20, 20);
		elementGlyph(ctx, el, 76, 70, 1, "#ffffff");
	}
	function pair(ctx, p) {
		figure(ctx, 30, 58, .85, "#ffffff");
		figure(ctx, 70, 58, .85, p.accent);
		ctx.strokeStyle = "#ffffff";
		ctx.lineWidth = 3;
		ctx.beginPath();
		ctx.moveTo(36, 30);
		ctx.quadraticCurveTo(50, 20, 64, 30);
		ctx.moveTo(64, 30);
		ctx.lineTo(57, 27);
		ctx.moveTo(64, 30);
		ctx.lineTo(60, 23);
		ctx.stroke();
	}
	/** 單體技能的遠近：有射程看射程；射程是武器（`null`）時看武器需求。 */
	function isRanged(range, weaponReq) {
		if (typeof range === "number") return range >= 2;
		return weaponReq === "ranged";
	}
	/** 畫形狀主圖；形狀不認得（含 `single` 以外的未知值）退回自身光環。 */
	function drawMotif(ctx, spec, el, p) {
		const shape = spec.shape_id;
		if (shape === "single" && spec.skeleton === "aura") buffTarget(ctx, el, p);
		else if (shape === "single") (spec.ranged ? projectile : slash)(ctx, el, p);
		else if (shape === "line") beam(ctx, el, p);
		else if (shape === "cone") fan(ctx, el, p);
		else if (shape !== null && GRID[shape] !== void 0) grid(ctx, el, p, shape, normalizeArm(spec.arm));
		else if (shape === "chain") chain(ctx, el, p);
		else if (shape === "ground_tile") ground(ctx, el, p, spec.skeleton);
		else if (shape === "allies_in_radius") alliesRadius(ctx, el, p);
		else if (shape === "object_then_tile") hurl(ctx, el, p);
		else if (shape === "unit_pair" || shape === "unit_then_tile") pair(ctx, p);
		else selfAura(ctx, p, spec.skeleton);
	}
	function skeletonGlyph(ctx, sk, cx, cy) {
		ctx.save();
		ctx.translate(cx, cy);
		ctx.strokeStyle = "#ffffff";
		ctx.fillStyle = "#ffffff";
		ctx.lineWidth = 2.2;
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		const line = (...pts) => {
			ctx.beginPath();
			for (let i = 0; i < pts.length; i += 2) {
				const x = pts[i];
				const y = pts[i + 1];
				if (i === 0) ctx.moveTo(x, y);
				else ctx.lineTo(x, y);
			}
			ctx.stroke();
		};
		switch (sk) {
			case "strike":
				ctx.beginPath();
				ctx.moveTo(-6, 6);
				ctx.lineTo(6, -6);
				ctx.moveTo(-6, 1);
				ctx.lineTo(-1, 6);
				ctx.stroke();
				break;
			case "area":
				starPath(ctx, 0, 0, 6, 7.5, 3.5);
				ctx.fill();
				break;
			case "control":
				ctx.beginPath();
				ctx.arc(0, -2, 4, Math.PI, 0);
				ctx.stroke();
				ctx.fillRect(-5.5, -1.5, 11, 8);
				break;
			case "aura":
				ctx.beginPath();
				ctx.moveTo(-5, 1);
				ctx.lineTo(0, -4);
				ctx.lineTo(5, 1);
				ctx.moveTo(-5, 6);
				ctx.lineTo(0, 1);
				ctx.lineTo(5, 6);
				ctx.stroke();
				break;
			case "summon":
				ctx.beginPath();
				ctx.moveTo(0, -6);
				ctx.lineTo(0, 6);
				ctx.moveTo(-6, 0);
				ctx.lineTo(6, 0);
				ctx.stroke();
				break;
			case "trap":
				line(-7, -1, -4, 4, -1, -1, 2, 4, 5, -1, 7, 3);
				break;
			case "displace":
				ctx.beginPath();
				ctx.moveTo(-7, 0);
				ctx.lineTo(7, 0);
				ctx.moveTo(3, -4);
				ctx.lineTo(7, 0);
				ctx.lineTo(3, 4);
				ctx.moveTo(-3, -4);
				ctx.lineTo(-7, 0);
				ctx.lineTo(-3, 4);
				ctx.stroke();
				break;
			case "rune":
				ctx.beginPath();
				ctx.moveTo(0, -7);
				ctx.lineTo(7, 0);
				ctx.lineTo(0, 7);
				ctx.lineTo(-7, 0);
				ctx.closePath();
				ctx.stroke();
				ctx.beginPath();
				ctx.moveTo(0, -2.6);
				ctx.lineTo(2.6, 0);
				ctx.lineTo(0, 2.6);
				ctx.lineTo(-2.6, 0);
				ctx.closePath();
				ctx.fill();
				break;
			case "consume_status":
				starPath(ctx, 0, 0, 5, 7, 3);
				ctx.stroke();
				ctx.beginPath();
				ctx.arc(0, 0, 1.8, 0, TAU$2);
				ctx.fill();
				break;
			case "builder_finisher":
				for (let i = 0; i < 3; i++) ctx.fillRect(-6 + i * 4.5, 4 - i * 4, 3, 3 + i * 4);
				break;
			case "stance":
				ctx.beginPath();
				ctx.moveTo(0, -7);
				ctx.lineTo(6, -4);
				ctx.lineTo(5, 3);
				ctx.lineTo(0, 7);
				ctx.lineTo(-5, 3);
				ctx.lineTo(-6, -4);
				ctx.closePath();
				ctx.stroke();
				break;
			case "reaction":
				ctx.beginPath();
				ctx.arc(0, 0, 5.5, -2.6, 1.4);
				ctx.stroke();
				line(-6, -6, -5, -1, -1, -3.5);
				break;
			default:
				ctx.beginPath();
				ctx.arc(0, 0, 5, 0, TAU$2);
				ctx.stroke();
		}
		ctx.restore();
	}
	/** 外框路徑（100×100 座標）：主動＝圓角方、反應＝盾形、被動＝圓、姿態＝六角、修正＝齒輪。 */
	function framePath(ctx, kind, inset = 0) {
		const i = inset;
		ctx.beginPath();
		switch (kind) {
			case "reaction":
				ctx.moveTo(8 + i, 6 + i);
				ctx.lineTo(92 - i, 6 + i);
				ctx.lineTo(92 - i, 50);
				ctx.quadraticCurveTo(92 - i, 82 - i, 50, 96 - i * 1.4);
				ctx.quadraticCurveTo(8 + i, 82 - i, 8 + i, 50);
				ctx.closePath();
				break;
			case "passive":
				ctx.arc(50, 50, 46 - i, 0, TAU$2);
				break;
			case "stance":
				for (let k = 0; k < 6; k++) {
					const a = k / 6 * TAU$2;
					ctx.lineTo(50 + Math.cos(a) * (48 - i), 50 + Math.sin(a) * (48 - i));
				}
				ctx.closePath();
				break;
			case "modifier":
				for (let k = 0; k < 48; k++) {
					const a = k / 48 * TAU$2;
					const r = (k % 4 < 2 ? 48 : 43) - i;
					ctx.lineTo(50 + Math.cos(a) * r, 50 + Math.sin(a) * r);
				}
				ctx.closePath();
				break;
			default: ctx.roundRect(4 + i, 4 + i, 92 - i * 2, 92 - i * 2, 14);
		}
	}
	//#endregion
	//#region client/src/render/skillParts.ts
	var TAU$1 = Math.PI * 2;
	/** 部件的浮動說明：分類字，有玩家說明時接在後面（效果原語、條件、觸發）。 */
	function partTip(part) {
		return part.description === void 0 ? part.note : `${part.note}：${part.description}`;
	}
	function described(description) {
		return description === "" ? {} : { description };
	}
	function arrow(ctx, x0, y0, x1, y1, head = 4) {
		const a = Math.atan2(y1 - y0, x1 - x0);
		ctx.beginPath();
		ctx.moveTo(x0, y0);
		ctx.lineTo(x1, y1);
		ctx.stroke();
		ctx.beginPath();
		ctx.moveTo(x1 + Math.cos(a), y1 + Math.sin(a));
		ctx.lineTo(x1 - Math.cos(a - .6) * head, y1 - Math.sin(a - .6) * head);
		ctx.lineTo(x1 - Math.cos(a + .6) * head, y1 - Math.sin(a + .6) * head);
		ctx.closePath();
		ctx.fill();
	}
	function dot(ctx, x, y, r) {
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU$1);
		ctx.fill();
	}
	function ring(ctx, x, y, r) {
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU$1);
		ctx.stroke();
	}
	/** 符文：菱形外框，裡面一個小菱形（`filled` 時填滿）。 */
	function runeMark(ctx, x, y, k = 1, filled = false) {
		const r = 8 * k;
		ctx.beginPath();
		ctx.moveTo(x, y - r);
		ctx.lineTo(x + r, y);
		ctx.lineTo(x, y + r);
		ctx.lineTo(x - r, y);
		ctx.closePath();
		ctx.stroke();
		const s = 3.6 * k;
		ctx.beginPath();
		ctx.moveTo(x, y - s);
		ctx.lineTo(x + s, y);
		ctx.lineTo(x, y + s);
		ctx.lineTo(x - s, y);
		ctx.closePath();
		if (filled) ctx.fill();
		else ctx.stroke();
	}
	function person(ctx, x, y, k = 1) {
		dot(ctx, x, y - 5 * k, 2.6 * k);
		ctx.beginPath();
		ctx.moveTo(x - 4.5 * k, y + 5 * k);
		ctx.quadraticCurveTo(x - 4.5 * k, y - 1.5 * k, x, y - 1.5 * k);
		ctx.quadraticCurveTo(x + 4.5 * k, y - 1.5 * k, x + 4.5 * k, y + 5 * k);
		ctx.closePath();
		ctx.fill();
	}
	function shieldPath(ctx, k = 1) {
		ctx.beginPath();
		ctx.moveTo(0, -9 * k);
		ctx.lineTo(7.5 * k, -6 * k);
		ctx.lineTo(7 * k, 2 * k);
		ctx.lineTo(0, 9 * k);
		ctx.lineTo(-7 * k, 2 * k);
		ctx.lineTo(-7.5 * k, -6 * k);
		ctx.closePath();
	}
	function heart(ctx, k = 1) {
		ctx.beginPath();
		ctx.moveTo(0, 8 * k);
		ctx.bezierCurveTo(-11 * k, 0, -6 * k, -10 * k, 0, -4 * k);
		ctx.bezierCurveTo(6 * k, -10 * k, 11 * k, 0, 0, 8 * k);
		ctx.closePath();
	}
	function drop(ctx, x, y, k = 1) {
		ctx.beginPath();
		ctx.moveTo(x, y - 8 * k);
		ctx.bezierCurveTo(x + 6.5 * k, y, x + 5.5 * k, y + 6 * k, x, y + 6 * k);
		ctx.bezierCurveTo(x - 5.5 * k, y + 6 * k, x - 6.5 * k, y, x, y - 8 * k);
		ctx.fill();
	}
	function hourglass(ctx) {
		ctx.beginPath();
		ctx.moveTo(-6, -8);
		ctx.lineTo(6, -8);
		ctx.lineTo(0, 0);
		ctx.lineTo(6, 8);
		ctx.lineTo(-6, 8);
		ctx.lineTo(0, 0);
		ctx.closePath();
		ctx.fill();
	}
	function text(ctx, s, size = 11) {
		ctx.font = `700 ${size}px ${FONT}`;
		ctx.textAlign = "center";
		ctx.textBaseline = "middle";
		ctx.fillText(s, 0, .5);
	}
	function eye(ctx, slashed) {
		ctx.beginPath();
		ctx.moveTo(-9, 0);
		ctx.quadraticCurveTo(0, -9, 9, 0);
		ctx.quadraticCurveTo(0, 9, -9, 0);
		ctx.stroke();
		dot(ctx, 0, 0, 2.6);
		if (slashed) {
			ctx.beginPath();
			ctx.moveTo(-8, 7);
			ctx.lineTo(8, -7);
			ctx.stroke();
		}
	}
	function footprints(ctx) {
		for (const [x, y, r] of [[
			-4,
			4,
			-.3
		], [
			3,
			-3,
			.3
		]]) {
			ctx.save();
			ctx.translate(x, y);
			ctx.rotate(r);
			ctx.beginPath();
			ctx.ellipse(0, 0, 2.6, 4, 0, 0, TAU$1);
			ctx.fill();
			dot(ctx, 0, -5.5, 1.3);
			ctx.restore();
		}
	}
	function chevrons(ctx, dir) {
		for (const o of [-4, 2]) {
			ctx.beginPath();
			if (dir === "right") {
				ctx.moveTo(o - 2, -6);
				ctx.lineTo(o + 4, 0);
				ctx.lineTo(o - 2, 6);
			} else {
				ctx.moveTo(-6, -o + 2);
				ctx.lineTo(0, -o - 4);
				ctx.lineTo(6, -o + 2);
			}
			ctx.stroke();
		}
	}
	function dice(ctx) {
		ctx.beginPath();
		ctx.roundRect(-7.5, -7.5, 15, 15, 3);
		ctx.stroke();
		for (const [x, y] of [
			[-3.5, -3.5],
			[3.5, 3.5],
			[0, 0],
			[3.5, -3.5],
			[-3.5, 3.5]
		]) dot(ctx, x, y, 1.4);
	}
	function card(ctx, x, y) {
		ctx.beginPath();
		ctx.roundRect(x - 4.5, y - 6.5, 9, 13, 1.5);
		ctx.fill();
	}
	function star(ctx, n, ro, ri) {
		starPath(ctx, 0, 0, n, ro, ri);
		ctx.fill();
	}
	function plus(ctx, x, y) {
		ctx.fillRect(x - 1, y - 3.5, 2, 7);
		ctx.fillRect(x - 3.5, y - 1, 7, 2);
	}
	function ghost(ctx, alpha, draw) {
		const before = ctx.globalAlpha;
		ctx.globalAlpha = before * alpha;
		draw();
		ctx.globalAlpha = before;
	}
	/** 圖樣表（id → [預設色, 畫法]）；顏色以 `statusColor` 為準，這裡的色只給少數不經 `statusColor` 的舊用法。 */
	var STATUS = Object.fromEntries(Object.entries(GLYPH).map(([id, draw]) => [id, ["#d8d8e0", draw]]));
	var UNKNOWN_COLOR = "#d8d8e0";
	/** 狀態圖樣（技能部件、組裝列用；不認得的狀態畫名稱第一個字）。 */
	function statusGlyph(ctx, id) {
		drawGlyph(ctx, id);
	}
	/** 狀態的圖樣顏色：`control_group` → 持續傷害元素 → 專屬色 → `polarity`（見 `statusIcon.glyphColor`）。 */
	function statusColor(id) {
		if (id == null || id === "") return UNKNOWN_COLOR;
		return glyphColor(id);
	}
	var surfaceColor = (id) => id == null ? "#c8c8c8" : SURFACE_ICON_COLOR[id] ?? "#c8c8c8";
	function surfaceGlyph(ctx, id) {
		ctx.save();
		ctx.fillStyle = surfaceColor(id);
		drop(ctx, 0, -2, .9);
		ctx.globalAlpha = .85;
		ctx.beginPath();
		ctx.ellipse(0, 7, 9, 2.6, 0, 0, TAU$1);
		ctx.fill();
		ctx.restore();
	}
	var stackDots = (c) => {
		for (let i = 0; i < 3; i++) dot(c, -6 + i * 6, 3, 2.4);
	};
	var EFFECT = {
		damage: ["#ffffff", (c) => star(c, 8, 9.5, 4)],
		heal: ["#7cf29a", (c) => {
			c.fillRect(-2.5, -8, 5, 16);
			c.fillRect(-8, -2.5, 16, 5);
		}],
		shield: ["#8fd0ff", (c) => {
			shieldPath(c);
			c.fill();
		}],
		cleanse: ["#bfffe8", (c) => star(c, 4, 9, 2.4)],
		push: ["#ffffff", (c) => {
			dot(c, -6, 0, 3.4);
			arrow(c, -1, 0, 9, 0, 4.5);
		}],
		pull: ["#ffffff", (c) => {
			dot(c, -7, 0, 3.4);
			arrow(c, 9, 0, -1, 0, 4.5);
		}],
		knock_prone: ["#e0c49a", (c) => STATUS["prone"][1](c)],
		shockwave: ["#e0c49a", (c) => {
			STATUS["prone"][1](c);
			c.beginPath();
			c.moveTo(-10, 11);
			c.lineTo(-6, 9);
			c.lineTo(-2, 11);
			c.lineTo(2, 9);
			c.lineTo(6, 11);
			c.lineTo(10, 9);
			c.stroke();
		}],
		teleport: ["#d8b8ff", (c) => {
			c.setLineDash([2.5, 2]);
			ring(c, -3, 2, 6);
			c.setLineDash([]);
			dot(c, 5, -4, 3.2);
		}],
		dash: ["#ffffff", (c) => {
			c.beginPath();
			c.moveTo(-9, -4);
			c.lineTo(-1, -4);
			c.moveTo(-9, 4);
			c.lineTo(-1, 4);
			c.stroke();
			arrow(c, -3, 0, 9, 0, 4.5);
		}],
		charge_through: ["#ffffff", (c) => {
			c.fillRect(-1.5, -9, 3, 18);
			arrow(c, -9, 0, 9, 0, 4.5);
		}],
		shadowstep: ["#c8a0ff", (c) => {
			c.beginPath();
			c.arc(-2, 0, 7, .6, TAU$1 - .6);
			c.stroke();
			arrow(c, 0, 0, 9, 0, 4);
		}],
		leap: ["#ffffff", (c) => {
			c.beginPath();
			c.moveTo(-9, 6);
			c.quadraticCurveTo(0, -14, 7, 4);
			c.stroke();
			arrow(c, 5, 0, 8, 6, 4);
		}],
		swap: ["#ffffff", (c) => {
			arrow(c, -8, -3, 8, -3, 3.5);
			arrow(c, 8, 3, -8, 3, 3.5);
		}],
		apply_status: ["#ffffff", (c) => ring(c, 0, 0, 7)],
		create_surface: ["#ffffff", (c) => surfaceGlyph(c, null)],
		blow_surface: ["#cfe8ff", (c) => {
			surfaceGlyph(c, null);
			arrow(c, -9, -7, 8, -7, 3.5);
		}],
		enter_form: ["#c9a0ff", (c) => {
			person(c, -6, 0, .8);
			arrow(c, -1, 0, 6, 0, 3);
			dot(c, 8, 0, 2);
		}],
		leave_form: ["#c9a0ff", (c) => {
			dot(c, -8, 0, 2);
			arrow(c, 1, 0, -6, 0, 3);
			person(c, 6, 0, .8);
		}],
		clear_surface: ["#cfe8ff", (c) => {
			surfaceGlyph(c, null);
			c.beginPath();
			c.moveTo(-8, 8);
			c.lineTo(8, -8);
			c.stroke();
		}],
		destroy_object: ["#e0c49a", (c) => {
			c.strokeRect(-7, -7, 14, 14);
			c.beginPath();
			c.moveTo(-2, -7);
			c.lineTo(1, -1);
			c.lineTo(-2, 3);
			c.lineTo(1, 7);
			c.stroke();
		}],
		create_obstacle: ["#d8c0a0", (c) => {
			for (let r = 0; r < 3; r++) for (let i = 0; i < 2; i++) c.fillRect(-8 + i * 8 + r % 2 * 4 - (r % 2 === 1 && i === 1 ? 4 : 0), -7 + r * 5, 7, 4);
		}],
		raise_terrain: ["#e0c49a", (c) => {
			c.fillRect(-8, 2, 16, 6);
			arrow(c, 0, 1, 0, -9, 4);
		}],
		lower_terrain: ["#e0c49a", (c) => {
			c.fillRect(-8, 2, 16, 6);
			arrow(c, 0, -9, 0, 0, 4);
		}],
		intercept: ["#8fd0ff", (c) => {
			person(c, -3, 1, 1.1);
			c.save();
			c.translate(5, 0);
			shieldPath(c, .6);
			c.fill();
			c.restore();
		}],
		add_stack: ["#ffd04a", (c) => {
			stackDots(c);
			c.fillRect(-1, -9, 2, 7);
			c.fillRect(-3.5, -6.5, 7, 2);
		}],
		consume_stack: ["#ffd04a", (c) => {
			stackDots(c);
			c.fillRect(-3.5, -6.5, 7, 2);
		}],
		consume_status: ["#ffb03a", (c) => {
			star(c, 6, 9, 4.5);
			c.save();
			c.fillStyle = "#1a1420";
			dot(c, 0, 0, 2.6);
			c.restore();
		}],
		place_trap: ["#e0e0e0", (c) => {
			for (const [b, t] of [[-2, -8], [2, 8]]) {
				c.beginPath();
				c.moveTo(-8, b);
				for (let i = 0; i < 4; i++) {
					c.lineTo(-8 + i * 4 + 2, t * .6 + b * .4);
					c.lineTo(-8 + (i + 1) * 4, b);
				}
				c.closePath();
				c.fill();
			}
		}],
		grant_ap: ["#ffe14d", (c) => {
			ring(c, -2, 0, 6.5);
			text(c, "+", 12);
		}],
		reset_cooldown: ["#a8e0ff", (c) => {
			c.beginPath();
			c.arc(0, 0, 7.5, -1.2, 4.2);
			c.stroke();
			arrow(c, -6.5, -4, -3.5, -8, 3.5);
		}],
		cheat_death: ["#ff7a7a", (c) => {
			heart(c);
			c.fill();
		}],
		redirect_damage: ["#ffffff", (c) => {
			c.beginPath();
			c.moveTo(-8, 7);
			c.lineTo(0, -1);
			c.stroke();
			arrow(c, 0, -1, 8, 7, 4);
		}],
		copy_skill: ["#d8c8ff", (c) => {
			ghost(c, .6, () => card(c, -3, -2));
			card(c, 3, 2);
		}],
		extra_reaction: ["#8fd0ff", (c) => {
			shieldPath(c, .9);
			c.stroke();
			elementGlyph(c, "lightning", 0, 0, .55, c.fillStyle);
		}],
		hurl_object: ["#e0b080", (c) => {
			c.fillRect(-9, 1, 7, 7);
			c.beginPath();
			c.moveTo(-5, 0);
			c.quadraticCurveTo(0, -12, 7, 2);
			c.stroke();
			arrow(c, 5, -2, 8, 4, 3.5);
		}],
		topple: ["#c8c0b0", (c) => {
			c.save();
			c.rotate(.6);
			c.fillRect(-2.5, -9, 5, 16);
			c.restore();
			c.fillRect(-9, 7, 18, 2);
		}],
		restore_resource: ["#c89cff", (c) => {
			c.beginPath();
			c.moveTo(-2, -8);
			c.lineTo(4, -2);
			c.lineTo(-2, 4);
			c.lineTo(-8, -2);
			c.closePath();
			c.fill();
			c.fillRect(4, 2, 2, 7);
			c.fillRect(1.5, 4.5, 7, 2);
		}],
		steal_buff: ["#c8a0ff", (c) => {
			c.beginPath();
			c.moveTo(-8, 6);
			c.lineTo(-8, -2);
			c.quadraticCurveTo(-8, -8, -2, -8);
			c.lineTo(6, -8);
			c.stroke();
			chevrons(c, "up");
		}],
		dispel: ["#d8d0ff", (c) => {
			c.beginPath();
			c.moveTo(-7, -7);
			c.lineTo(7, 7);
			c.moveTo(7, -7);
			c.lineTo(-7, 7);
			c.stroke();
		}],
		reveal: ["#ffffff", (c) => eye(c, false)],
		revive: ["#ffd75e", (c) => {
			heart(c);
			c.fill();
			c.save();
			c.fillStyle = "#1a1420";
			c.fillRect(-1.2, -4, 2.4, 8);
			c.fillRect(-4, -1.2, 8, 2.4);
			c.restore();
		}],
		delayed_damage: ["#ffb03a", (c) => {
			c.save();
			c.scale(.75, .75);
			c.translate(-4, 0);
			hourglass(c);
			c.restore();
			c.save();
			c.translate(5, -3);
			star(c, 6, 5, 2.4);
			c.restore();
		}],
		summon: ["#8ff0e2", (c) => {
			person(c, -2, 1, 1.25);
			plus(c, 6, -5);
		}],
		zone: ["#ffd04a", (c) => {
			c.setLineDash([3, 2]);
			ring(c, 0, 0, 8);
			c.setLineDash([]);
			dot(c, 0, 0, 2.5);
		}],
		rule_change: ["#ffd75e", (c) => {
			c.beginPath();
			c.roundRect(-7, -8, 14, 16, 2);
			c.stroke();
			c.fillRect(-4, -4, 8, 1.6);
			c.fillRect(-4, 0, 8, 1.6);
			c.fillRect(-4, 4, 5, 1.6);
		}],
		gamble: ["#ffffff", dice],
		grant_skill: ["#d8c8ff", (c) => {
			card(c, -2, 1);
			plus(c, 6, -5);
		}],
		sacrifice_summon: ["#ff9f6b", (c) => {
			person(c, 0, 1, .9);
			arrow(c, 0, -6, 0, -10.5, 3);
			arrow(c, -6, 0, -10.5, 0, 3);
			arrow(c, 6, 0, 10.5, 0, 3);
		}],
		inscribe: ["#ffe08a", (c) => runeMark(c, 0, 0, 1.1, true)],
		detonate_runes: ["#ffb36b", (c) => {
			runeMark(c, 0, 0, .6, true);
			arrow(c, 0, -5, 0, -10, 3);
			arrow(c, 0, 5, 0, 10, 3);
			arrow(c, -5, 0, -10, 0, 3);
			arrow(c, 5, 0, 10, 0, 3);
		}]
	};
	EFFECT["teleport_target"] = EFFECT["swap"];
	EFFECT["swap_any"] = EFFECT["swap"];
	/** 效果原語 → 部件（附加狀態與產生表面用各自的圖示）。 */
	function effectPart(e) {
		if (e.type === "apply_status" && e.status != null && e.status !== "") {
			const id = e.status;
			return {
				cat: "effect",
				key: `status:${id}`,
				color: statusColor(id),
				draw: (c) => statusGlyph(c, id),
				label: statusName(id),
				note: "附加狀態"
			};
		}
		if (e.type === "create_surface" && e.surface != null && e.surface !== "") {
			const id = e.surface;
			return {
				cat: "effect",
				key: `surface:${id}`,
				color: surfaceColor(id),
				draw: (c) => surfaceGlyph(c, id),
				label: `${surfaceName(id)}表面`,
				note: "產生表面"
			};
		}
		const g = EFFECT[e.type];
		return {
			cat: "effect",
			key: e.type,
			color: g?.[0] ?? UNKNOWN_COLOR,
			draw: g?.[1] ?? ((c) => text(c, "?", 13)),
			label: effectName(e.type),
			note: "效果原語",
			...described(glossaryDescription("effects", e.type))
		};
	}
	function halfHeart(c, k) {
		heart(c, k);
		c.stroke();
		c.save();
		c.beginPath();
		c.rect(-10, 1, 20, 10);
		c.clip();
		heart(c, k);
		c.fill();
		c.restore();
	}
	var COND = {
		height_advantage: (c) => {
			c.beginPath();
			c.moveTo(-9, 8);
			c.lineTo(0, -4);
			c.lineTo(9, 8);
			c.closePath();
			c.fill();
			dot(c, 0, -7.5, 2.6);
		},
		target_hp_below: (c) => halfHeart(c, 1),
		self_hp_below: (c) => {
			halfHeart(c, .85);
			person(c, 7, -5, .5);
		},
		target_has_status: (c) => {
			ring(c, -2, 1, 6);
			text(c, "?", 9);
		},
		target_on_surface: (c) => {
			drop(c, -2, 0, .75);
			c.save();
			c.translate(6, -5);
			text(c, "?", 9);
			c.restore();
		},
		from_behind: (c) => {
			person(c, 3, 0, 1.1);
			arrow(c, -9, 0, -3, 0, 3.5);
		},
		flanked: (c) => {
			dot(c, 0, 0, 3);
			arrow(c, -9, 0, -4.5, 0, 3.5);
			arrow(c, 9, 0, 4.5, 0, 3.5);
		},
		target_isolated: (c) => {
			c.setLineDash([2.5, 2]);
			ring(c, 0, 0, 8);
			c.setLineDash([]);
			dot(c, 0, 0, 3);
		},
		moved_this_turn: footprints,
		first_round: (c) => text(c, "1", 14),
		cast_tag_this_turn: (c) => {
			card(c, -3, 0);
			arrow(c, 1, 0, 9, 0, 3.5);
		},
		self_concealed: (c) => STATUS["concealed"][1](c),
		on_own_rune: (c) => {
			runeMark(c, -2, 1, .95, true);
			c.save();
			c.translate(6.5, -5.5);
			text(c, "?", 8);
			c.restore();
		},
		adjacent_ally: (c) => {
			person(c, -4, 1, .85);
			person(c, 4, 1, .85);
		},
		target_collided: (c) => {
			person(c, -3, 1, .9);
			c.fillRect(4, -8, 3, 16);
			arrow(c, -9, -7, -4, -7, 3);
		},
		wielding_weapon: (c) => {
			c.fillRect(-1.5, -9, 3, 12);
			c.fillRect(-5, 3, 10, 2.5);
			c.fillRect(-1.5, 5.5, 3, 4);
		},
		in_form: (c) => {
			c.lineWidth = 2;
			c.lineCap = "round";
			c.beginPath();
			for (let i = -1; i <= 1; i++) {
				c.moveTo(i * 5 - 2, -8);
				c.lineTo(i * 5 + 2, 8);
			}
			c.stroke();
		}
	};
	var CONDITION_COLOR = "#ffe9a8";
	/** 條件 → 部件；`target_has_status` 帶狀態時畫該狀態圖示加問號。 */
	function conditionPart(id, status) {
		if (id == null || id === "") return null;
		let draw = COND[id] ?? ((c) => text(c, "?", 13));
		if (id === "target_has_status" && status != null && status !== "") draw = (c) => {
			c.save();
			c.scale(.85, .85);
			statusGlyph(c, status);
			c.restore();
			c.save();
			c.translate(6.5, 5.5);
			text(c, "?", 8);
			c.restore();
		};
		return {
			cat: "condition",
			key: id === "target_has_status" && status != null && status !== "" ? `${id}:${status}` : id,
			color: CONDITION_COLOR,
			draw,
			label: conditionName(id),
			note: "條件",
			...described(glossaryDescription("conditions", id))
		};
	}
	var COST_LABEL = {
		source: "源力",
		gamble: "賭注",
		self: "自身代價（失手自傷等）",
		stacks: "消耗層數",
		once: "每場一次",
		delay: "延遲"
	};
	var COST_ART = {
		source: ["#c89cff", (x) => {
			x.beginPath();
			x.moveTo(0, -9);
			x.lineTo(7, 0);
			x.lineTo(0, 9);
			x.lineTo(-7, 0);
			x.closePath();
			x.fill();
		}],
		gamble: ["#ffffff", dice],
		self: ["#ff6a6a", (x) => {
			heart(x);
			x.fill();
			x.save();
			x.strokeStyle = "#1a1420";
			x.lineWidth = 1.6;
			x.beginPath();
			x.moveTo(-1, -4);
			x.lineTo(2, 0);
			x.lineTo(-1, 3);
			x.stroke();
			x.restore();
		}],
		stacks: ["#ffd04a", EFFECT["consume_stack"][1]],
		once: ["#ffd75e", (x) => {
			ring(x, 0, 0, 8.5);
			text(x, "1", 11);
		}],
		delay: ["#a8e0ff", hourglass]
	};
	/** 帶數值時的名稱（Phase 3-18a）：源力 2、消耗層數 3、每場一次、延遲 1 回合。 */
	function costLabel(id, value) {
		const base = COST_LABEL[id] ?? id;
		if (value === void 0) return base;
		if (id === "delay") return `${base} ${value} 回合`;
		if (id === "once") return value === 1 ? base : `每場 ${value} 次`;
		return `${base} ${value}`;
	}
	/** 特殊代價 → 部件（`value` 是代價的數值，沒有就不寫）；不認得的代價畫「?」。 */
	function costPart(id, value) {
		const art = COST_ART[id];
		return {
			cat: "cost",
			key: id,
			color: art?.[0] ?? "#d8d8e0",
			draw: art?.[1] ?? ((x) => text(x, "?", 13)),
			label: costLabel(id, value),
			note: "特殊代價"
		};
	}
	var TRIG = {
		on_hit: EFFECT["damage"][1],
		on_kill: (c) => {
			dot(c, 0, -2, 7);
			c.fillRect(-4, 2, 8, 6);
			c.save();
			c.fillStyle = "#1a1420";
			dot(c, -2.8, -2, 2);
			dot(c, 2.8, -2, 2);
			c.restore();
		},
		on_crit: (c) => star(c, 4, 10, 2.6),
		on_natural_20: (c) => {
			c.beginPath();
			for (let i = 0; i < 6; i++) c.lineTo(Math.cos(i / 6 * TAU$1 - Math.PI / 2) * 9.5, Math.sin(i / 6 * TAU$1 - Math.PI / 2) * 9.5);
			c.closePath();
			c.stroke();
			text(c, "20", 8);
		},
		on_move: footprints,
		on_damaged: STATUS["vulnerable"][1],
		on_status_applied: (c) => {
			ring(c, 0, 0, 8);
			dot(c, 0, 0, 3);
		},
		on_cast_tag: (c) => card(c, 0, 0),
		on_collision: (c) => {
			arrow(c, -9, 0, -2, 0, 3.5);
			arrow(c, 9, 0, 2, 0, 3.5);
		},
		on_turn_start: (c) => {
			c.beginPath();
			c.arc(0, 4, 7, Math.PI, 0);
			c.fill();
			c.fillRect(-10, 4, 20, 1.8);
			arrow(c, 0, -2, 0, -9, 3);
		},
		on_turn_end: (c) => {
			c.beginPath();
			c.arc(0, 4, 7, Math.PI, 0);
			c.fill();
			c.fillRect(-10, 4, 20, 1.8);
			arrow(c, 0, -10, 0, -3, 3);
		},
		on_enter_surface: (c) => drop(c, 0, 0, .9),
		on_summon_downed: (c) => {
			ring(c, 0, -2, 6);
			dot(c, 0, -2, 2.4);
			arrow(c, 0, 5, 0, 10, 3);
		},
		every_n_hits: (c) => {
			for (let i = 0; i < 3; i++) dot(c, -6 + i * 6, 0, 2.6);
		},
		enemy_enters_adjacent: (c) => {
			ring(c, 2, 0, 6);
			arrow(c, -10, 0, -3, 0, 3.5);
		},
		enemy_leaves_adjacent: (c) => {
			ring(c, -2, 0, 6);
			arrow(c, 2, 0, 10, 0, 3.5);
		},
		hit_by_spell: (c) => {
			shieldPath(c);
			c.stroke();
			c.save();
			c.scale(.5, .5);
			star(c, 5, 9, 4);
			c.restore();
		},
		hit_by_attack: (c) => {
			shieldPath(c);
			c.stroke();
			c.beginPath();
			c.moveTo(-9, -9);
			c.lineTo(-2, -2);
			c.stroke();
		},
		hit_by_melee: (c) => {
			shieldPath(c);
			c.stroke();
			c.beginPath();
			c.moveTo(-9, -9);
			c.lineTo(-2, -2);
			c.moveTo(-9, -4);
			c.lineTo(-5, -8);
			c.stroke();
		},
		ally_targeted: (c) => {
			person(c, 0, 1, 1.1);
			ghost(c, .9, () => STATUS["marked"][1](c));
		},
		ally_downed: STATUS["prone"][1],
		ally_hit_adjacent: (c) => {
			person(c, -4, 1, .9);
			c.save();
			c.translate(5, -3);
			star(c, 6, 5, 2.2);
			c.restore();
		}
	};
	function triggerPart(id, isReaction) {
		if (id == null || id === "") return null;
		return {
			cat: "trigger",
			key: id,
			color: "#ffffff",
			draw: TRIG[id] ?? ((c) => text(c, "?", 13)),
			label: triggerName(id),
			note: isReaction ? "反應時機" : "觸發時機",
			...described(glossaryDescription("triggers", id))
		};
	}
	var LINK = {
		after_action: ["接著做", (c) => arrow(c, -7, 0, 7, 0, 5)],
		on_hit: ["命中才觸發", (c) => {
			c.beginPath();
			c.moveTo(-7, 0);
			c.lineTo(-2, 5);
			c.lineTo(7, -6);
			c.stroke();
		}],
		on_kill: ["擊殺才觸發", TRIG["on_kill"]],
		delayed: ["延遲觸發", hourglass],
		after_move: ["移動後觸發", (c) => {
			c.save();
			c.scale(.85, .85);
			footprints(c);
			c.restore();
		}],
		after_gather: ["聚集後觸發", (c) => {
			arrow(c, -9, 0, -3, 0, 3);
			arrow(c, 9, 0, 3, 0, 3);
		}]
	};
	/** 接續記號；不認得的種類當成「接著做」。 */
	function linkPart(when) {
		const id = when ?? "after_action";
		const l = LINK[id] ?? LINK["after_action"];
		return {
			cat: "link",
			key: id,
			color: "#ffffff",
			draw: l[1],
			label: l[0],
			note: "接續"
		};
	}
	var TAG_TARGET = {
		push: "push",
		heal: "heal",
		control: "apply_status",
		ranged: "dash",
		shout: "damage",
		area: "damage"
	};
	var TAG_NAMES = {
		push: "推擊",
		heal: "治療",
		control: "控制",
		ranged: "遠程",
		shout: "吼叫",
		area: "範圍"
	};
	/** 召喚物數值類修正的小標記字（3-24b1、3-33f1）；沒列出的（HP）畫「＋」。 */
	var SUMMON_MARK = {
		summon_attack_dice: "骰",
		summon_limit_delta: "數",
		summon_duration_delta: "時",
		summon_damage_permille: "攻"
	};
	var rangedGlyph = (c) => {
		c.beginPath();
		c.arc(-4, 0, 9, -1.1, 1.1);
		c.stroke();
		arrow(c, -6, 0, 9, 0, 3.5);
	};
	/** `applies_to`（只含有填的欄位）→ 被改造對象的部件。 */
	function modifierTargetPart(applies) {
		const a = applies ?? {};
		let draw = EFFECT["damage"][1];
		let label = "所有技能";
		const actions = Array.isArray(a["actions"]) ? a["actions"] : [];
		const tags = Array.isArray(a["skill_tags"]) ? a["skill_tags"].map(String) : [];
		const swordGlyph = (c) => {
			c.beginPath();
			c.moveTo(-7, 7);
			c.lineTo(7, -7);
			c.moveTo(-7, 2);
			c.lineTo(-2, 7);
			c.stroke();
		};
		if (a["all_skills"] === true) draw = (c) => {
			ghost(c, .6, () => card(c, -3, -2));
			card(c, 3, 2);
		};
		else if (a["all_attacks"] === true || actions.includes("attack")) {
			draw = swordGlyph;
			label = a["all_attacks"] === true ? "所有攻擊" : "普通攻擊";
		} else if (tags.length > 0) {
			const t = tags[0];
			draw = t === "ranged" ? rangedGlyph : (EFFECT[TAG_TARGET[t] ?? "damage"] ?? EFFECT["damage"])[1];
			label = `${tags.map((x) => TAG_NAMES[x] ?? x).join("／")}技能`;
		} else if (actions.length > 0) {
			draw = swordGlyph;
			label = actions.map(String).join("／");
		}
		return {
			cat: "target",
			key: "target",
			color: "#ffffff",
			draw,
			label,
			note: "被改造的對象"
		};
	}
	var ELEMENT_FALLBACK = "#ffffff";
	/** `on_hit_effects` 的一項（原始效果或後端給的 `type[:status]`）→ `type[:status]`。 */
	function effectId(raw) {
		if (typeof raw === "string") return raw;
		const e = typeof raw === "object" && raw !== null ? raw : {};
		const type = typeof e["type"] === "string" ? e["type"] : "?";
		return typeof e["status"] === "string" && e["status"] !== "" ? `${type}:${e["status"]}` : type;
	}
	function effectLikeOf(id) {
		const [type = "?", status] = id.split(":");
		return status === void 0 ? { type } : {
			type,
			status
		};
	}
	/** 修正的改變內容（一個鍵一個部件）。 */
	function modifierChangePart(key, value, partIds = []) {
		let draw;
		let label;
		let color = "#ffe14d";
		const num = typeof value === "number" ? value : 0;
		const signed = num > 0 ? `+${num}` : `${num}`;
		switch (key) {
			case "add_element": {
				const el = String(value);
				color = ELEMENT_ICON[el]?.accent ?? ELEMENT_FALLBACK;
				draw = (c) => {
					elementGlyph(c, el, -1, 1, .75, color);
					c.save();
					c.fillStyle = "#ffffff";
					plus(c, 6, -6);
					c.restore();
				};
				label = `加上${ELEMENT_ICON[el]?.name ?? el}元素`;
				break;
			}
			case "damage_permille":
				draw = (c) => {
					c.save();
					c.translate(-2, 2);
					c.scale(.7, .7);
					star(c, 8, 9.5, 4);
					c.restore();
					arrow(c, 6, 6, 6, -8, 3.5);
				};
				label = `傷害 ${num > 0 ? "+" : ""}${num / 10}%`;
				break;
			case "hit_bonus":
				draw = (c) => {
					ring(c, 0, 0, 7);
					dot(c, 0, 0, 2.2);
					plus(c, 7, -7);
				};
				label = `命中 ${signed}`;
				break;
			case "cooldown_delta":
				draw = (c) => {
					ring(c, -2, 1, 7);
					c.beginPath();
					c.moveTo(-2, -3);
					c.lineTo(-2, 1);
					c.lineTo(1, 3);
					c.stroke();
					c.fillRect(4, -9, 6, 2);
				};
				label = `冷卻 ${signed}`;
				break;
			case "area_delta":
				draw = (c) => {
					arrow(c, -2, -2, -9, -9, 3.5);
					arrow(c, 2, 2, 9, 9, 3.5);
					c.strokeRect(-4, -4, 8, 8);
				};
				label = `範圍 ${signed}`;
				break;
			case "push_distance_delta":
				draw = EFFECT["push"][1];
				label = `推距 ${signed}`;
				break;
			case "ap_delta":
				draw = (c) => {
					ring(c, -2, 0, 6.5);
					c.fillRect(4, -9, 6, 2);
				};
				label = `AP ${signed}`;
				break;
			case "range_delta":
				draw = rangedGlyph;
				label = `射程 ${signed}`;
				break;
			case "add_tags": {
				const tags = partIds.length > 0 ? partIds : Array.isArray(value) ? value.map(String) : [];
				const first = tags[0] ?? "";
				const base = first === "ranged" ? rangedGlyph : (EFFECT[TAG_TARGET[first] ?? ""] ?? EFFECT["damage"])[1];
				draw = (c) => {
					c.save();
					c.scale(.85, .85);
					base(c);
					c.restore();
					plus(c, 6.5, -6.5);
				};
				label = tags.length === 0 ? "加上標籤" : `加上標籤：${tags.map((t) => TAG_NAMES[t] ?? t).join("／")}`;
				break;
			}
			case "on_hit_effects": {
				const ids = partIds.length > 0 ? partIds : Array.isArray(value) ? value.map((v) => effectId(v)) : [];
				const first = ids[0];
				const part = first === void 0 ? null : effectPart(effectLikeOf(first));
				draw = (c) => {
					if (part !== null) {
						c.save();
						c.scale(.85, .85);
						part.draw(c);
						c.restore();
					}
					c.save();
					c.translate(6.5, -6.5);
					text(c, "命", 7);
					c.restore();
				};
				label = ids.length === 0 ? "命中後效果" : `命中後：${ids.map((i) => effectPart(effectLikeOf(i)).label).join("／")}`;
				break;
			}
			case "shape_to":
				draw = (c) => {
					c.beginPath();
					c.moveTo(-9, 6);
					c.lineTo(9, -6);
					c.stroke();
				};
				label = `形狀改為 ${String(value)}`;
				break;
			case "allow_self_target":
				draw = (c) => {
					person(c, 0, 1, 1.2);
					ring(c, 0, 0, 9.5);
				};
				label = "可以對自己用";
				break;
			case "grant_pierce":
				draw = (c) => {
					c.fillRect(-1.5, -9, 3, 18);
					arrow(c, -9, 0, 9, 0, 4);
				};
				label = "穿透";
				break;
			case "heal_permille":
			case "summon_hp_permille":
			case "summon_limit_delta":
			case "summon_duration_delta":
			case "summon_damage_permille":
			case "summon_attack_dice": {
				const base = EFFECT[key === "heal_permille" ? "heal" : "summon"][1];
				draw = (c) => {
					c.save();
					c.scale(.85, .85);
					base(c);
					c.restore();
					const mark = SUMMON_MARK[key];
					if (mark !== void 0) {
						c.save();
						c.translate(6.5, -6.5);
						text(c, mark, 7);
						c.restore();
					} else plus(c, 6.5, -6.5);
				};
				if (key === "heal_permille") label = `治療量 ${num > 0 ? "+" : ""}${num / 10}%`;
				else if (key === "summon_hp_permille") label = `召喚物 HP +${num / 10}%`;
				else if (key === "summon_limit_delta") label = `召喚物上限 ${signed}`;
				else if (key === "summon_duration_delta") label = `召喚物持續 ${signed} 輪`;
				else if (key === "summon_damage_permille") label = `召喚物傷害 +${num / 10}%`;
				else label = `召喚物攻擊 +${num} 骰`;
				break;
			}
			default:
				draw = (c) => text(c, "?", 13);
				label = key;
		}
		return {
			cat: "change",
			key,
			color,
			draw,
			label,
			note: "改變的內容"
		};
	}
	/** 在 (x, y) 畫一個部件小圓片：深色底＋外圈＋圖示。 */
	function drawChip(ctx, part, x, y, r, opts = {}) {
		ctx.save();
		ctx.translate(x, y);
		ctx.fillStyle = opts.bg ?? "rgba(10,12,18,0.85)";
		ctx.beginPath();
		ctx.arc(0, 0, r, 0, TAU$1);
		ctx.fill();
		if (opts.ring !== false) {
			ctx.strokeStyle = opts.ring ?? "rgba(255,255,255,0.35)";
			ctx.lineWidth = Math.max(1, r * .12);
			ctx.stroke();
		}
		const k = r * .78 / 10;
		ctx.scale(k, k);
		ctx.fillStyle = part.color;
		ctx.strokeStyle = part.color;
		ctx.lineWidth = 2.2;
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		part.draw(ctx);
		ctx.restore();
	}
	/** 有專屬圖示的部件代碼（其他走預設圖；測試用來對照 `content/` 檢查有沒有漏）。 */
	var KNOWN_PARTS = {
		effects: Object.keys(EFFECT),
		statuses: Object.keys(STATUS),
		surfaces: Object.keys(SURFACE_ICON_COLOR),
		conditions: Object.keys(COND),
		triggers: Object.keys(TRIG),
		links: Object.keys(LINK),
		costs: Object.keys(COST_ART)
	};
	//#endregion
	//#region client/src/render/skillIcon.ts
	var TAU = Math.PI * 2;
	/** 形狀 id → 中文名（由 `vfx.ts` 的名稱表反查，只放一處）。 */
	var SHAPE_NAME_ZH = Object.fromEntries(Object.entries(SHAPE_NAMES).map(([zh, id]) => [id, zh]));
	/** 資料 → 部件清單；`icon` 缺欄位或有不認得的值時也不丟例外。 */
	function partsOf(icon) {
		const kind = icon.kind || "active";
		const first = icon.elements[0];
		const el = first !== void 0 ? first : icon.partial ? void 0 : null;
		const segs = icon.segments.map((s, i) => ({
			motif: {
				shape_id: s.shape_id,
				skeleton: s.skeleton,
				ranged: isRanged(s.range, icon.weapon_req),
				arm: normalizeArm(s.arm)
			},
			el: i === 0 ? el : s.elements?.[0] ?? el,
			effects: s.effects.map(effectPart)
		}));
		if (segs.length === 0) segs.push({
			motif: {
				shape_id: null,
				skeleton: null,
				ranged: false,
				arm: 1
			},
			el,
			effects: []
		});
		const mod = icon.modifier === null || icon.modifier === void 0 ? null : {
			target: modifierTargetPart(icon.modifier.applies_to),
			changes: icon.modifier.changes.map((c) => modifierChangePart(c.key, c.value, c.part_ids ?? []))
		};
		let effects = [];
		const seen = /* @__PURE__ */ new Set();
		for (const s of segs) for (const e of s.effects) if (!seen.has(e.key)) {
			seen.add(e.key);
			effects.push(e);
		}
		if (mod !== null) effects = mod.changes;
		const coreIdx = effects.findIndex((e) => e.key !== "damage");
		const core = effects.length === 0 ? null : effects[coreIdx === -1 ? 0 : coreIdx] ?? null;
		if (core !== null) effects = [core, ...effects.filter((e) => e !== core)];
		const isReaction = kind === "reaction";
		return {
			kind,
			rarity: icon.rarity,
			el,
			el2: icon.elements[1],
			segs,
			link: icon.link == null ? null : linkPart(icon.link),
			trigger: kind === "reaction" || kind === "passive" ? triggerPart(icon.trigger, isReaction) : null,
			mod,
			condition: icon.condition == null ? null : conditionPart(icon.condition.id, icon.condition.status),
			costs: icon.costs.map((c) => costPart(c, icon.cost_values?.[c])),
			effects: effects.slice(0, 4),
			core
		};
	}
	function bigGlyph(ctx, part, cx, cy, k) {
		ctx.save();
		ctx.translate(cx, cy);
		ctx.scale(k, k);
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		ctx.save();
		ctx.translate(.8, 1);
		ctx.fillStyle = "rgba(0,0,0,0.45)";
		ctx.strokeStyle = "rgba(0,0,0,0.45)";
		ctx.lineWidth = 2.4;
		part.draw(ctx);
		ctx.restore();
		ctx.fillStyle = "#ffffff";
		ctx.strokeStyle = "#ffffff";
		ctx.lineWidth = 2.2;
		part.draw(ctx);
		ctx.restore();
	}
	function segMotif(ctx, seg, cx, cy, k) {
		if (seg.motif.shape_id === null) {
			ctx.save();
			ctx.setLineDash([6, 5]);
			ctx.strokeStyle = "rgba(255,255,255,0.45)";
			ctx.lineWidth = 3;
			ctx.beginPath();
			ctx.arc(cx, cy, 22 * k, 0, TAU);
			ctx.stroke();
			ctx.restore();
			return;
		}
		ctx.save();
		ctx.translate(cx, cy);
		ctx.scale(k, k);
		ctx.translate(-50, -50);
		drawMotif(ctx, seg.motif, seg.el === void 0 ? "default" : seg.el ?? "default", elementPalette(seg.el));
		ctx.restore();
	}
	function clipTriangle(ctx, pts) {
		ctx.beginPath();
		pts.forEach(([x, y], i) => i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y));
		ctx.closePath();
		ctx.clip();
	}
	function compositeArt(ctx, parts, small) {
		const [a, b] = parts.segs;
		ctx.save();
		clipTriangle(ctx, [
			[0, 0],
			[100, 0],
			[0, 100]
		]);
		segMotif(ctx, a, 30, 30, .52);
		ctx.restore();
		ctx.save();
		clipTriangle(ctx, [
			[100, 0],
			[100, 100],
			[0, 100]
		]);
		if (b.el !== a.el) paintBackground(ctx, b.el);
		else {
			ctx.fillStyle = "rgba(0,0,0,0.22)";
			ctx.fillRect(0, 0, 100, 100);
		}
		segMotif(ctx, b, 68, small ? 68 : 62, .52);
		ctx.restore();
		ctx.strokeStyle = "rgba(0,0,0,0.6)";
		ctx.lineWidth = 5;
		ctx.beginPath();
		ctx.moveTo(104, -4);
		ctx.lineTo(-4, 104);
		ctx.stroke();
		ctx.strokeStyle = "#ffffff";
		ctx.lineWidth = 2.2;
		ctx.stroke();
		if (parts.link !== null) drawChip(ctx, parts.link, 50, 50, small ? 13 : 10.5, { ring: "#ffffff" });
	}
	function mainArt(ctx, parts, small) {
		const ky = small ? 50 : 44;
		const k = small ? 1 : .8;
		const first = parts.segs[0];
		if (parts.mod !== null) bigGlyph(ctx, parts.mod.target, 50, ky, small ? 3 : 2.4);
		else if (parts.trigger !== null) bigGlyph(ctx, parts.trigger, 50, ky, small ? 3 : 2.4);
		else if (parts.segs.length > 1) compositeArt(ctx, parts, small);
		else segMotif(ctx, first, 50, ky + (small ? 0 : 2), k);
	}
	function elementChip(ctx, el, x, y, r) {
		ctx.fillStyle = "rgba(8,10,16,0.8)";
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU);
		ctx.fill();
		elementGlyph(ctx, el ?? "default", x, y, r / 12 * .8, elementPalette(el).accent);
	}
	function skeletonBadge(ctx, skeleton, rarity) {
		ctx.fillStyle = "rgba(8,10,16,0.88)";
		ctx.beginPath();
		ctx.arc(86, 86, 11, 0, TAU);
		ctx.fill();
		ctx.strokeStyle = rarity;
		ctx.lineWidth = 2;
		ctx.stroke();
		ctx.save();
		ctx.translate(86, 86);
		ctx.scale(.85, .85);
		skeletonGlyph(ctx, skeleton, 0, 0);
		ctx.restore();
	}
	function effectRow(ctx, parts) {
		const list = parts.effects;
		if (list.length === 0) return;
		const left = parts.condition !== null ? 26 : 5;
		const right = 75;
		const rc = 11.5;
		let ro = 8.5;
		const gap = 1.5;
		let total = rc * 2 + (list.length - 1) * (ro * 2 + gap);
		if (total > right - left) {
			ro = Math.max(4.5, ((right - left - rc * 2) / (list.length - 1) - gap) / 2);
			total = rc * 2 + (list.length - 1) * (ro * 2 + gap);
		}
		let x = (left + right) / 2 - total / 2;
		list.forEach((p, i) => {
			const r = i === 0 ? rc : ro;
			drawChip(ctx, p, x + r, 85 + (i === 0 ? 0 : 2), r, { ring: i === 0 ? p.color : "rgba(255,255,255,0.3)" });
			x += r * 2 + gap;
		});
	}
	function frame(ctx, parts, rarity) {
		framePath(ctx, parts.kind, 1);
		ctx.lineWidth = parts.rarity === "legendary" ? 5 : 3.5;
		ctx.strokeStyle = rarity;
		ctx.stroke();
		if (parts.rarity === "legendary" || parts.rarity === "epic") {
			framePath(ctx, parts.kind, 6);
			ctx.lineWidth = 1;
			ctx.globalAlpha = .6;
			ctx.stroke();
			ctx.globalAlpha = 1;
		}
	}
	/**
	* 在 `ctx` 上畫一個組裝式圖示。`ctx` 已經縮放成 100×100 的座標（見 `skillIconCanvas`）；
	* `small` 為真時只畫元素、形狀、核心效果與外框。
	*/
	function paintSkillIcon(ctx, icon, small) {
		const parts = partsOf(icon);
		const rarity = rarityColor(parts.rarity);
		ctx.save();
		framePath(ctx, parts.kind);
		ctx.clip();
		paintBackground(ctx, parts.el);
		if (parts.el2 !== void 0) {
			ctx.save();
			ctx.globalAlpha = .55;
			ctx.fillStyle = elementPalette(parts.el2).light;
			ctx.beginPath();
			ctx.moveTo(62, 0);
			ctx.lineTo(80, 0);
			ctx.lineTo(0, 80);
			ctx.lineTo(0, 62);
			ctx.closePath();
			ctx.fill();
			ctx.restore();
		}
		mainArt(ctx, parts, small);
		ctx.restore();
		frame(ctx, parts, rarity);
		if (small) {
			if (parts.core !== null) drawChip(ctx, parts.core, 79, 79, 18, { ring: rarity });
			return;
		}
		if (parts.el !== void 0) elementChip(ctx, parts.el, 15, 15, 11);
		const [c1, c2] = parts.costs;
		if (c1 !== void 0) drawChip(ctx, c1, 85, 15, 11, { ring: c1.color });
		if (c2 !== void 0) drawChip(ctx, c2, 85, 36, 8, { ring: c2.color });
		if (parts.condition !== null) drawChip(ctx, parts.condition, 14, 86, 11, { ring: "#ffe9a8" });
		const skeleton = parts.segs[0]?.motif.skeleton ?? null;
		if (skeleton !== null) skeletonBadge(ctx, skeleton, rarity);
		effectRow(ctx, parts);
	}
	/** 穩定序列化（鍵排序），同一組合永遠得到同一個字串。 */
	function stableStringify(value) {
		if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
		if (typeof value === "object" && value !== null) return `{${Object.entries(value).filter(([, v]) => v !== void 0).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`).join(",")}}`;
		return JSON.stringify(value) ?? "null";
	}
	/** 圖示的快取鍵：`icon` 的穩定序列化 ＋ 尺寸 ＋ 大小圖（同組合共用一張貼圖，不是每個技能一張）。 */
	function iconCacheKey(icon, size, small = size <= 40) {
		return `${size}|${small ? "s" : "l"}|${stableStringify(icon)}`;
	}
	var DPR = 2;
	var CACHE_LIMIT = 300;
	var cache = /* @__PURE__ */ new Map();
	/** 取得（或畫出並快取）一張圖示的離屏 canvas，邊長 `size` px（內部解析度 ×2）；`small` 預設依邊長決定。 */
	function skillIconCanvas(icon, size, small = size <= 40) {
		const key = iconCacheKey(icon, size, small);
		const hit = cache.get(key);
		if (hit !== void 0) return hit;
		const canvas = document.createElement("canvas");
		canvas.width = size * DPR;
		canvas.height = size * DPR;
		const ctx = canvas.getContext("2d");
		if (ctx !== null) {
			ctx.scale(size * DPR / 100, size * DPR / 100);
			paintSkillIcon(ctx, icon, small);
		}
		if (cache.size >= CACHE_LIMIT) {
			const oldest = cache.keys().next().value;
			if (oldest !== void 0) cache.delete(oldest);
		}
		cache.set(key, canvas);
		return canvas;
	}
	var FAINT_RING = "rgba(255,255,255,0.3)";
	var CORE_RING = "#ffffff";
	function chipTile(cat, part, ring) {
		return {
			cat,
			label: part.label,
			tip: partTip(part),
			id: `${cat}|${part.key}|${part.label}|${ring}`,
			draw: (ctx) => drawChip(ctx, part, 50, 50, 42, { ring })
		};
	}
	function skeletonTile(skeleton, second) {
		return {
			cat: second ? "骨架（第二段）" : "骨架",
			label: SKELETON_NAME[skeleton] ?? skeleton,
			tip: "技能的骨架：決定這一段怎麼出手",
			id: `skeleton|${skeleton}`,
			draw: (ctx) => {
				ctx.fillStyle = "#14161c";
				ctx.beginPath();
				ctx.arc(50, 50, 40, 0, TAU);
				ctx.fill();
				ctx.save();
				ctx.translate(50, 50);
				ctx.scale(3, 3);
				skeletonGlyph(ctx, skeleton, 0, 0);
				ctx.restore();
			}
		};
	}
	function shapeTile(seg) {
		if (seg.motif.shape_id === null) return null;
		const shape = seg.motif.shape_id;
		const arm = normalizeArm(seg.motif.arm);
		return {
			cat: "形狀",
			label: SHAPE_NAME_ZH[shape] ?? shape,
			tip: shape === "cross" && arm >= 2 ? `技能的作用範圍，臂長 ${arm}` : "技能的作用範圍",
			id: `shape|${shape}|${String(seg.el)}|${seg.motif.skeleton ?? ""}|${seg.motif.ranged ? 1 : 0}|${arm}`,
			draw: (ctx) => {
				paintBackground(ctx, seg.el);
				segMotif(ctx, seg, 50, 50, .95);
			}
		};
	}
	/** 一段的部件：骨架 ＋ 形狀 ＋ 效果（核心效果白外圈）。元素、類型、稀有度不是部件，已由圖示本身表達。 */
	function segmentTiles(seg, index, core) {
		const out = [];
		if (seg.motif.skeleton !== null) out.push(skeletonTile(seg.motif.skeleton, index > 0));
		const shape = shapeTile(seg);
		if (shape !== null) out.push(shape);
		const unique = seg.effects.filter((x, i, a) => a.findIndex((y) => y.key === x.key) === i);
		for (const e of unique) {
			const isCore = e.key === core?.key;
			out.push(chipTile(isCore ? "效果（核心）" : "效果", e, isCore ? CORE_RING : FAINT_RING));
		}
		return out;
	}
	function assemblyFormula(icon) {
		const parts = partsOf(icon);
		const rows = [];
		const links = [];
		if (parts.mod !== null) rows.push([chipTile("改造對象", parts.mod.target, CORE_RING), ...parts.mod.changes.map((c) => chipTile("改變內容", c, FAINT_RING))]);
		else {
			const [a, b] = parts.segs;
			const first = segmentTiles(a, 0, parts.core);
			rows.push(parts.trigger === null ? first : [chipTile("觸發", parts.trigger, CORE_RING), ...first]);
			if (parts.link !== null && b !== void 0) {
				links.push(chipTile("接續", parts.link, CORE_RING));
				rows.push(segmentTiles(b, 1, parts.core));
			}
		}
		const extras = [];
		if (parts.condition !== null) extras.push(chipTile("條件", parts.condition, "#ffe9a8"));
		for (const c of parts.costs) if (!(c.key === "delay" && parts.link?.key === "delayed")) extras.push(chipTile("代價", c, c.color));
		return {
			rows,
			links,
			extras
		};
	}
	/** 狀態的部件小圖（說明取名詞對照表的描述）。 */
	function statusTile(id) {
		const entry = glossaryEntry("statuses", id);
		const tip = [entry?.description_zh ?? "", ...entry?.rules_zh ?? []].filter((x) => x !== "").join(" ");
		return {
			cat: "狀態",
			label: statusName(id),
			tip: tip === "" ? "狀態" : tip,
			id: `status|${id}`,
			draw: (ctx) => drawChip(ctx, {
				cat: "effect",
				key: `status:${id}`,
				color: statusColor(id),
				draw: (c) => statusGlyph(c, id),
				label: id,
				note: ""
			}, 50, 50, 42, { ring: FAINT_RING })
		};
	}
	/** 表面的部件小圖（說明取名詞對照表的描述與規則）。 */
	function surfaceTile(id) {
		const entry = glossaryEntry("surfaces", id);
		const tip = [entry?.description_zh ?? "", ...entry?.rules_zh ?? []].filter((x) => x !== "").join(" ");
		return {
			cat: "表面",
			label: surfaceName(id),
			tip: tip === "" ? "地面上的表面" : tip,
			id: `surface|${id}`,
			draw: (ctx) => drawChip(ctx, {
				cat: "effect",
				key: `surface:${id}`,
				color: surfaceColor(id),
				draw: (c) => surfaceGlyph(c, id),
				label: id,
				note: ""
			}, 50, 50, 42, { ring: FAINT_RING })
		};
	}
	/** 組裝列方塊的快取鍵（同一個部件共用一張小圖）。 */
	var tileKey = (t, px) => `${px}|${t.id}`;
	var tileCache = /* @__PURE__ */ new Map();
	/** 一塊組裝列方塊的離屏 canvas（`px` 邊長，內部解析度 ×2；同一個部件共用）。 */
	function tileCanvas(tile, px = 44) {
		const key = tileKey(tile, px);
		const hit = tileCache.get(key);
		if (hit !== void 0) return hit;
		const canvas = document.createElement("canvas");
		canvas.width = px * DPR;
		canvas.height = px * DPR;
		const ctx = canvas.getContext("2d");
		if (ctx !== null) {
			ctx.scale(px * DPR / 100, px * DPR / 100);
			ctx.beginPath();
			ctx.arc(50, 50, 49, 0, TAU);
			ctx.clip();
			tile.draw(ctx);
		}
		if (tileCache.size >= CACHE_LIMIT) {
			const oldest = tileCache.keys().next().value;
			if (oldest !== void 0) tileCache.delete(oldest);
		}
		tileCache.set(key, canvas);
		return canvas;
	}
	var OPTION_ID = (field, value) => `option|${field}|${value}`;
	var PART_CAT_NAME = {
		effect: "效果",
		condition: "條件",
		cost: "代價",
		trigger: "觸發",
		link: "接續",
		target: "改造對象",
		change: "改變內容"
	};
	function partTile(field, value, part) {
		return {
			cat: PART_CAT_NAME[part.cat] ?? part.cat,
			label: part.label,
			tip: partTip(part),
			id: OPTION_ID(field, value),
			draw: (ctx) => drawChip(ctx, part, 50, 50, 46, { ring: "rgba(255,255,255,0.3)" })
		};
	}
	/**
	* 工坊某個欄位的某個選項的小圖（與技能圖示共用同一套部件）；沒有圖示的欄位回傳 `null`。
	* 欄位：`skeleton`、`shape`、`condition`、`event`（觸發／反應時機）、效果列表的 `type`、
	* 效果參數的 `status`、`surface`、`element`。
	*/
	function optionTile(field, value) {
		if (typeof value !== "string" || value === "") return null;
		switch (field.split(".").pop() ?? field) {
			case "skeleton": return skeletonTile(value, false);
			case "shape": {
				const motif = {
					motif: {
						shape_id: value,
						skeleton: null,
						ranged: true
					},
					el: null,
					effects: []
				};
				return {
					cat: "形狀",
					label: SHAPE_NAME_ZH[value] ?? value,
					tip: "技能的作用範圍",
					id: OPTION_ID(field, value),
					draw: (ctx) => {
						paintBackground(ctx, null);
						segMotif(ctx, motif, 50, 50, .95);
					}
				};
			}
			case "condition":
			case "condition_type": {
				const part = conditionPart(value);
				return part === null ? null : partTile(field, value, part);
			}
			case "event": {
				const part = triggerPart(value, false);
				return part === null ? null : partTile(field, value, part);
			}
			case "effects": return partTile(field, value, effectPart({ type: value }));
			case "status": return statusTile(value);
			case "surface": return surfaceTile(value);
			case "element": return {
				cat: "元素",
				label: elementPalette(value).name,
				tip: "技能的元素",
				id: OPTION_ID(field, value),
				draw: (ctx) => {
					paintBackground(ctx, value);
					elementGlyph(ctx, value, 50, 50, 2.6, "#ffffff");
				}
			};
			default: return null;
		}
	}
	//#endregion
	//#region entry.ts
	window.QPartsLive = {
		paintSkillIcon,
		skillIconCanvas,
		partsOf,
		assemblyFormula,
		tileCanvas,
		optionTile,
		statusTile,
		surfaceTile,
		SMALL_ICON_MAX: 40,
		drawChip,
		effectPart,
		conditionPart,
		costPart,
		triggerPart,
		linkPart,
		modifierTargetPart,
		modifierChangePart,
		KNOWN_PARTS,
		statusColor,
		statusGlyph,
		surfaceColor,
		surfaceGlyph,
		skeletonGlyph,
		SKELETON_NAME,
		framePath,
		rarityColor,
		elementPalette,
		elementGlyph,
		paintBackground,
		setGlossary,
		glossaryName
	};
	//#endregion
})();
