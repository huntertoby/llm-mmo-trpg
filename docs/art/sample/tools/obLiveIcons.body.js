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
	/** 「會替物品與形態上色」的元素色：物理與不認得的元素回傳 `undefined`（不套元素色）；水套水色。 */
	function elementTintColors(el) {
		if (el == null || el === "physical") return void 0;
		if (el === "water") return {
			primary: WATER_COLOR,
			bright: "#d8f0ff"
		};
		return ELEMENT_COLORS[el];
	}
	ELEMENT_COLORS["fire"].primary, ELEMENT_COLORS["lightning"].primary, ELEMENT_COLORS["ice"].primary;
	ELEMENT_COLORS["fire"].primary;
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
	/** 表面的顏色取自 `render/palette.ts`（單一來源），這裡只決定疊色比例。 */
	var ground = (id, alpha) => ({
		color: parseInt((SURFACE_GROUND_COLOR[id] ?? "#888888").slice(1), 16),
		alpha
	});
	ground("oil", .6), ground("water", .55), ground("fire", .7), ground("ice", .7), ground("poison", .6), ground("holy", .6), ground("darkness", .65), ground("smoke", .6);
	//#endregion
	//#region client/src/render/color.ts
	var HEX = /^#[0-9a-f]{6}$/i;
	/** `#rrggbb` → [r, g, b]（0–255）。 */
	function hexRgb(h) {
		const n = parseInt(h.slice(1), 16);
		return [
			n >> 16 & 255,
			n >> 8 & 255,
			n & 255
		];
	}
	/** 兩色混合（`t` ＝ b 的比例）；任一個不是 `#rrggbb` 時原樣回傳 `a`。 */
	function mix$1(a, b, t) {
		if (!HEX.test(a) || !HEX.test(b)) return a;
		const [r1, g1, b1] = hexRgb(a);
		const [r2, g2, b2] = hexRgb(b);
		const m = (x, y) => Math.round(x * (1 - t) + y * t);
		return `#${(m(r1, r2) << 16 | m(g1, g2) << 8 | m(b1, b2)).toString(16).padStart(6, "0")}`;
	}
	/** 與黑色混合（暗 t）。 */
	var darken = (c, t) => mix$1(c, "#000000", t);
	//#endregion
	//#region client/src/render/artDraw.ts
	var TAU$2 = Math.PI * 2;
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
	var INK$1 = "#2b1e16";
	/** 部件名稱 → 32 位元種子（FNV-1a）。 */
	function seedOf(s) {
		let h = 2166136261;
		for (const ch of s) h = Math.imul(h ^ (ch.codePointAt(0) ?? 0), 16777619);
		return h >>> 0;
	}
	/** 線性同餘亂數（回傳 [0, 1)）；同一個種子永遠產生同一串數字。 */
	function lcg(seed) {
		let s = seed >>> 0;
		return () => {
			s = Math.imul(s, 1664525) + 1013904223 >>> 0;
			return s / 4294967296;
		};
	}
	/** 橢圓取點（n 個點）。 */
	function ellPts(cx, cy, rx, ry, n = 18) {
		return Array.from({ length: n }, (_, i) => [cx + Math.cos(i / n * TAU$2) * rx, cy + Math.sin(i / n * TAU$2) * ry]);
	}
	/** 每個點隨機抖動 ±amt/2。 */
	function wobble(pts, r, amt) {
		return pts.map(([x, y]) => [x + (r() - .5) * amt, y + (r() - .5) * amt]);
	}
	var mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
	/** 用中點二次曲線把折線圓滑化（closed ＝ 封閉形狀）。 */
	function smooth(ctx, pts, closed = true) {
		ctx.beginPath();
		const n = pts.length;
		const first = pts[0];
		const last = pts[n - 1];
		if (first === void 0 || last === void 0) return;
		if (!closed) {
			ctx.moveTo(first[0], first[1]);
			for (let i = 1; i < n - 1; i++) {
				const p = pts[i];
				const m = mid(p, pts[i + 1]);
				ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]);
			}
			ctx.lineTo(last[0], last[1]);
			return;
		}
		const m0 = mid(last, first);
		ctx.moveTo(m0[0], m0[1]);
		for (let i = 0; i < n; i++) {
			const p = pts[i];
			const m = mid(p, pts[(i + 1) % n]);
			ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]);
		}
		ctx.closePath();
	}
	function outline(ctx, pts, sharp) {
		if (sharp !== true) {
			smooth(ctx, pts);
			return;
		}
		ctx.beginPath();
		pts.forEach(([x, y], i) => i > 0 ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
		ctx.closePath();
	}
	/**
	* 暗面方向跟著畫布走（Phase 3T-4：原本是模組變數，畫出來的樣子取決於「上一個畫的是誰」）。
	* 沒有指定的畫布一律 1；要改方向請用 `withShadeDir`，它在結束時還原，所以呼叫順序不影響結果。
	* 貼圖快取鍵已含朝向（暗面方向由朝向決定），不需另外加。
	*/
	var shadeDirs = /* @__PURE__ */ new WeakMap();
	/** 在 `fn` 執行期間把 `ctx` 的暗面方向設成 `dir`，結束時還原（含例外）。 */
	function withShadeDir(ctx, dir, fn) {
		const before = shadeDirs.get(ctx);
		shadeDirs.set(ctx, dir);
		try {
			return fn();
		} finally {
			if (before === void 0) shadeDirs.delete(ctx);
			else shadeDirs.set(ctx, before);
		}
	}
	var iconModes = /* @__PURE__ */ new WeakMap();
	/** 在 `fn` 執行期間把 `ctx` 設成小圖示模式，結束時還原（含例外）。 */
	function withIconMode(ctx, mode, fn) {
		const before = iconModes.get(ctx);
		iconModes.set(ctx, mode);
		try {
			return fn();
		} finally {
			if (before === void 0) iconModes.delete(ctx);
			else iconModes.set(ctx, before);
		}
	}
	/** 目前是不是在畫小圖示。 */
	var inIconMode = (ctx) => iconModes.has(ctx);
	var lineMul = (ctx) => iconModes.get(ctx)?.lineScale ?? 1;
	/**
	* 小圖示裡把「頭」（斧刃、錘頭、鐮刃、杖頭）以 (ax, ay)（頭與柄交接處）為中心放大 `headScale` 倍，柄不變；
	* 放大後墨線寬度除回去，線不會跟著變粗。不是小圖示時照原樣畫。
	*/
	function iconHead(ctx, ax, ay, fn) {
		const mode = iconModes.get(ctx);
		if (mode === void 0 || mode.headScale === 1) {
			fn();
			return;
		}
		const h = mode.headScale;
		ctx.save();
		ctx.translate(ax, ay);
		ctx.scale(h, h);
		ctx.translate(-ax, -ay);
		try {
			withIconMode(ctx, {
				...mode,
				lineScale: mode.lineScale / h
			}, fn);
		} finally {
			ctx.restore();
		}
	}
	function hatch(ctx, pts, sharp) {
		const dir = shadeDirs.get(ctx) ?? 1;
		let x0 = Infinity;
		let x1 = -Infinity;
		let y0 = Infinity;
		let y1 = -Infinity;
		for (const [x, y] of pts) {
			x0 = Math.min(x0, x);
			x1 = Math.max(x1, x);
			y0 = Math.min(y0, y);
			y1 = Math.max(y1, y);
		}
		const w = x1 - x0;
		const h = y1 - y0;
		if (w <= 3 || h <= 3) return;
		ctx.save();
		outline(ctx, pts, sharp);
		ctx.clip();
		const a = dir > 0 ? x0 + w * .6 : x0 - h;
		const b = dir > 0 ? x1 + h : x0 + w * .4;
		ctx.strokeStyle = "rgba(43,30,22,0.42)";
		ctx.lineWidth = .35 * lineMul(ctx);
		ctx.beginPath();
		for (let x = a; x < b; x += 1.3) {
			ctx.moveTo(x, y0);
			ctx.lineTo(x - h * .9, y1);
		}
		ctx.stroke();
		ctx.restore();
	}
	/** 畫一個部件：水彩填色＋暗面排線＋兩次抖動墨線。`key` 決定抖動（同一部件在不同方向用不同 key）。 */
	function ink(ctx, key, pts, color, opt = {}) {
		const r = lcg(seedOf(key));
		ctx.save();
		ctx.translate(.45, .35);
		outline(ctx, wobble(pts, r, .7), opt.sharp);
		ctx.globalAlpha = opt.alpha ?? .94;
		ctx.fillStyle = color;
		ctx.fill();
		ctx.globalAlpha = .35;
		ctx.strokeStyle = "rgba(0,0,0,0.55)";
		ctx.lineWidth = .9 * lineMul(ctx);
		ctx.stroke();
		ctx.restore();
		if (opt.shade !== false) hatch(ctx, pts, opt.sharp);
		if (opt.line === false) return;
		const w = opt.w ?? .85;
		ctx.strokeStyle = INK$1;
		ctx.lineJoin = "round";
		ctx.lineCap = "round";
		ctx.lineWidth = w * lineMul(ctx);
		outline(ctx, wobble(pts, r, .5), opt.sharp);
		ctx.stroke();
		ctx.lineWidth = w * .45 * lineMul(ctx);
		outline(ctx, wobble(pts, r, .85), opt.sharp);
		ctx.stroke();
	}
	/** 開放的抖動線（腰帶、縫線、嘴、骨架線）。 */
	function stroke(ctx, key, pts, w = .7, color = INK$1) {
		const r = lcg(seedOf(key));
		ctx.strokeStyle = color;
		ctx.lineWidth = w * lineMul(ctx);
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		smooth(ctx, wobble(pts, r, .35), false);
		ctx.stroke();
	}
	/** 小橢圓點（眼睛、手上的點）。 */
	function dot(ctx, x, y, rx, ry, c) {
		ctx.fillStyle = c;
		ctx.beginPath();
		ctx.ellipse(x, y, rx, ry, 0, 0, TAU$2);
		ctx.fill();
	}
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
	var TAU$1 = Math.PI * 2;
	var INK = GEAR_INK;
	/** 魔導劍源晶槽的預設顏色（無元素；有元素時紙娃娃畫法換成元素色，見 `paperdoll.ts`）。 */
	var ARCANE_GLOW$1 = "#9a86ff";
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
	function line(ctx, c, w, pts) {
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
		if (P.shine) line(ctx, "rgba(255,255,255,0.95)", 1.4, pts);
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
				ctx.shadowColor = ARCANE_GLOW$1;
				ctx.shadowBlur = 5;
				line(ctx, ARCANE_GLOW$1, 2.4, [[0, 5], [0, -22]]);
				ctx.restore();
			} else if (r.form !== "curved") line(ctx, P.d, 1.2, [[0, 6], [0, -20]]);
			shine(ctx, P, [[-1.5, 4], [-1.5, -18]]);
			if (r.form === "arcane") {
				shape(ctx, "#b08a4a", () => {
					for (let i = 0; i < 12; i += 1) {
						const a = i / 12 * TAU$1;
						const k = i % 2 === 0 ? 7.5 : 5.6;
						ctx.lineTo(Math.cos(a) * k, 10 + Math.sin(a) * k * .6);
					}
					ctx.closePath();
				}, 1.5);
				ctx.fillStyle = ARCANE_GLOW$1;
				ctx.beginPath();
				ctx.arc(0, 10, 2, 0, TAU$1);
				ctx.fill();
			} else guard(ctx, P, 8, r.form === "broad" ? 22 : 18);
			grip(ctx, P, 12, 10);
			shape(ctx, P.guard, () => ctx.arc(0, 24, 2.5, 0, TAU$1), 1.2);
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
			line(ctx, P.d, 1.2, [[0, 3], [0, -25]]);
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
					const a = i / 8 * TAU$1;
					shape(ctx, P.d, () => {
						ctx.moveTo(Math.cos(a) * 7, -20 + Math.sin(a) * 7);
						ctx.lineTo(Math.cos(a + .25) * 12, -20 + Math.sin(a + .25) * 12);
						ctx.lineTo(Math.cos(a + .5) * 7, -20 + Math.sin(a + .5) * 7);
					}, 1);
				}
				shape(ctx, P.a, () => ctx.arc(0, -20, 8, 0, TAU$1));
			} else if (r.form === "warhammer") {
				shape(ctx, P.a, () => ctx.roundRect(-11, -26, 22, 12, 2));
				line(ctx, P.d, 1.5, [[-11, -20], [11, -20]]);
			} else {
				line(ctx, INK, 3.5, [
					[0, -14],
					[6, -20],
					[4, -26]
				]);
				line(ctx, P.d, 2, [
					[0, -14],
					[6, -20],
					[4, -26]
				]);
				for (let i = 0; i < 8; i++) {
					const a = i / 8 * TAU$1;
					shape(ctx, P.d, () => {
						ctx.moveTo(4 + Math.cos(a) * 5, -31 + Math.sin(a) * 5);
						ctx.lineTo(4 + Math.cos(a + .3) * 9, -31 + Math.sin(a + .3) * 9);
						ctx.lineTo(4 + Math.cos(a + .6) * 5, -31 + Math.sin(a + .6) * 5);
					}, 1);
				}
				shape(ctx, P.a, () => ctx.arc(4, -31, 6, 0, TAU$1));
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
		line(ctx, "#e6e0d0", 1, [[r.form === "recurve" ? 4 : 0, -L], [r.form === "recurve" ? 4 : 0, L]]);
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
				ctx.arc(0, -20, 8, 0, TAU$1);
				ctx.lineWidth = 5;
				ctx.strokeStyle = INK;
				ctx.stroke();
				ctx.lineWidth = 3;
				ctx.strokeStyle = r.material === "wood" ? "#e8bb48" : P.a;
				ctx.stroke();
				gem(ctx, 0, -20, 4.5, orb);
			} else {
				shape(ctx, orb, () => ctx.arc(0, -20, r.form === "wand" ? 5 : 7, 0, TAU$1));
				ctx.fillStyle = "rgba(255,255,255,0.6)";
				ctx.beginPath();
				ctx.arc(-2, -22, 2, 0, TAU$1);
				ctx.fill();
			}
			if (r.form === "long") {
				line(ctx, INK, 3, [[-5, -14], [5, -14]]);
				line(ctx, r.material === "wood" ? "#6a4420" : P.d, 1.6, [[-5, -14], [5, -14]]);
			}
		});
		return [[40, 22], [28, 38]];
	};
	D.round_shield = (ctx, r, P) => {
		shape(ctx, P.a, () => ctx.arc(32, 33, 22, 0, TAU$1), 2.5);
		if (r.form === "wood") for (const x of [
			-11,
			0,
			11
		]) line(ctx, P.d, 1.5, [[32 + x, 13 + Math.abs(x) / 3], [32 + x, 53 - Math.abs(x) / 3]]);
		else {
			ctx.beginPath();
			ctx.arc(32, 33, 19, 0, TAU$1);
			ctx.lineWidth = 4;
			ctx.strokeStyle = "#8d969f";
			ctx.stroke();
			for (let i = 0; i < 8; i++) {
				const a = i / 8 * TAU$1;
				shape(ctx, "#c3ccd6", () => ctx.arc(32 + Math.cos(a) * 19, 33 + Math.sin(a) * 19, 1.6, 0, TAU$1), .8);
			}
		}
		shape(ctx, r.form === "wood" ? "#8d969f" : P.d, () => ctx.arc(32, 33, 6, 0, TAU$1), 1.5);
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
		line(ctx, P.d, 3, [[32, 13], [32, r.form === "kite" ? 52 : 54]]);
		line(ctx, P.d, 3, [[19, 27], [45, 27]]);
		if (r.form === "tower") for (const y of [12, 54]) for (const x of [19, 45]) shape(ctx, P.d, () => ctx.arc(x, y, 1.6, 0, TAU$1), .8);
		shine(ctx, P, [[18, 16], [18, 26]]);
		return [[23, 20], [41, 40]];
	};
	D.tome = (ctx, r, P) => {
		if (r.form === "book") {
			shape(ctx, "#efe6cf", () => ctx.roundRect(17, 14, 32, 40, 3), 1.5);
			shape(ctx, P.a, () => ctx.roundRect(14, 12, 32, 40, 3), 2.5);
			line(ctx, P.d, 3, [[19, 12], [19, 52]]);
			gem(ctx, 32, 32, 6, P.accent);
			for (const y of [16, 48]) line(ctx, "#e8bb48", 2, [[38, y], [44, y]]);
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
			shape(ctx, c, () => ctx.arc(32, 30, 15, 0, TAU$1), 2.5);
		} else {
			ctx.beginPath();
			ctx.ellipse(32, 32, 24, 7, -.3, 0, TAU$1);
			ctx.lineWidth = 4;
			ctx.strokeStyle = INK;
			ctx.stroke();
			ctx.lineWidth = 2;
			ctx.strokeStyle = "#e8bb48";
			ctx.stroke();
			shape(ctx, c, () => ctx.arc(32, 31, 12, 0, TAU$1), 2.5);
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
		ctx.arc(26, 24, 4, 0, TAU$1);
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
		line(ctx, P.d, 2, [[32, 17], [32, hem]]);
		line(ctx, "#e8bb48", 2.5, [[17, hem - 2], [47, hem - 2]]);
		shape(ctx, P.d, () => ctx.roundRect(20, 32, 24, 4, 1), 1.2);
		return [[25, 42], [39, 24]];
	};
	D.leather = (ctx, r, P) => {
		torso(ctx, P, r.form === "hunter", 52);
		line(ctx, P.d, 1.5, [[32, 16], [32, 52]]);
		for (const y of [
			24,
			31,
			38
		]) line(ctx, "#2a1c10", 1.5, [[29, y], [35, y]]);
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
			ctx.arc(x, y, 1.4, 0, TAU$1);
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
			shape(ctx, P.a, () => ctx.ellipse(16, 20, 9, 7, -.4, 0, TAU$1), 2);
			shape(ctx, P.a, () => ctx.ellipse(48, 20, 9, 7, .4, 0, TAU$1), 2);
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
		line(ctx, P.d, 1.5, [[32, 20], [32, 40]]);
		line(ctx, P.d, 1.5, [[22, 26], [42, 26]]);
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
		line(ctx, P.d, 2, [[32, 16], [32, 56]]);
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
		]) shape(ctx, "#e8bb48", () => ctx.arc(35, y, 1.6, 0, TAU$1), .8);
		return [[25, 34], [40, 46]];
	};
	D.ring = (ctx, r, P) => {
		ctx.beginPath();
		ctx.ellipse(32, 38, 15, 13, 0, 0, TAU$1);
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
			shape(ctx, P.a, () => ctx.arc(32, 40, 12, 0, TAU$1), 2);
			gem(ctx, 32, 40, 6, P.accent);
		} else {
			shape(ctx, P.a, () => ctx.roundRect(22, 28, 20, 26, 3), 2);
			line(ctx, P.d, 1.5, [[26, 36], [38, 36]]);
			line(ctx, P.d, 1.5, [[26, 42], [36, 42]]);
			shape(ctx, INK, () => ctx.arc(32, 32, 1.6, 0, TAU$1), .5);
		}
		return [[46, 44], [18, 44]];
	};
	D.charm = (ctx, r, P) => {
		if (r.form === "tablet") {
			shape(ctx, P.a, () => ctx.roundRect(20, 12, 24, 40, 4), 2.5);
			line(ctx, P.d, 2, [[32, 18], [32, 46]]);
			line(ctx, P.d, 2, [[26, 24], [38, 24]]);
			line(ctx, P.d, 2, [[27, 34], [37, 40]]);
			line(ctx, "#b83a3a", 2.5, [[32, 52], [30, 60]]);
			line(ctx, "#b83a3a", 2.5, [[32, 52], [35, 60]]);
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
			]) line(ctx, "#8a8070", 1.5, [[28, y], [36, y]]);
			line(ctx, P.a, 3, [[26, 50], [38, 50]]);
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
		shape(ctx, SKIN_HINT, () => ctx.ellipse(32, 34, 11, 13, 0, 0, TAU$1), 1.5);
		if (r.form === "cowl") shape(ctx, P.d, () => {
			ctx.moveTo(8, 50);
			ctx.quadraticCurveTo(32, 60, 56, 50);
			ctx.lineTo(58, 58);
			ctx.lineTo(6, 58);
			ctx.closePath();
		}, 2);
		else line(ctx, P.d, 2, [[14, 48], [50, 48]]);
		return [[46, 22], [18, 26]];
	};
	D.hat = (ctx, r, P) => {
		if (r.form === "wizard") {
			shape(ctx, P.d, () => ctx.ellipse(32, 46, 26, 7, 0, 0, TAU$1), 2.5);
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
			shape(ctx, P.d, () => ctx.ellipse(32, 44, 28, 9, 0, 0, TAU$1), 2.5);
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
			]) shape(ctx, P.d, () => ctx.arc(x, y, 1.6, 0, TAU$1), .6);
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
			for (let x = 13; x < 52; x += 5) line(ctx, "#b8b09a", 1, [[x, 41], [x + 1.5, 46]]);
		} else {
			shape(ctx, P.d, () => ctx.roundRect(10, 38, 44, 7, 2), 2);
			line(ctx, P.d, 1.4, [[32, 15], [32, 38]]);
			for (const y of [
				20,
				27,
				34
			]) line(ctx, "#2a1c10", 1, [[30, y], [34, y]]);
		}
		return [[46, 24], [18, 24]];
	};
	D.helmet = (ctx, r, P) => {
		if (r.form === "greathelm") {
			shape(ctx, P.a, () => ctx.roundRect(14, 12, 36, 42, 7), 2.5);
			shape(ctx, INK, () => ctx.roundRect(18, 28, 28, 4, 1), .5);
			line(ctx, P.d, 2, [[32, 32], [32, 50]]);
			for (const y of [38, 43]) for (const x of [24, 40]) shape(ctx, INK, () => ctx.arc(x, y, 1, 0, TAU$1), 0);
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
		line(ctx, P.d, 1.5, [[21, 44], [44, 44]]);
		return [[40, 30], [26, 38]];
	};
	D.leather_gloves = (ctx, r, P) => {
		glove(ctx, P, false, r.form === "long");
		line(ctx, P.d, 1.2, [[26, 30], [38, 30]]);
		if (r.form === "short") shape(ctx, P.d, () => ctx.roundRect(19, 44, 26, 7, 2), 1.8);
		for (const x of [
			24,
			32,
			40
		]) shape(ctx, "#c8a040", () => ctx.arc(x, 48, 1.3, 0, TAU$1), .6);
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
			]) line(ctx, P.d, 1.5, [[21, y], [45, y - 1]]);
			shape(ctx, P.a, () => ctx.ellipse(32, 46, 14, 5, 0, 0, TAU$1), 1.8);
		} else {
			ctx.save();
			ctx.beginPath();
			ctx.rect(20, 26, 26, 30);
			ctx.clip();
			ctx.strokeStyle = P.d;
			ctx.lineWidth = 1;
			for (let y = 27; y < 56; y += 3) for (let x = 20 + y / 3 % 2 * 1.5; x < 46; x += 3) {
				ctx.beginPath();
				ctx.arc(x, y, 1.2, 0, TAU$1);
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
				ctx.ellipse(32, y, 18, 7, 0, 0, TAU$1);
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
			line(ctx, "#2a1c10", 1, [[24, 14], [22, 52]]);
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
			for (let y = 18; y < 44; y += 6) line(ctx, P.d, 1.5, [[22, y], [38, y + 3]]);
		}
		line(ctx, P.d, 1.5, [[22, 40], [38, 40]]);
		return [[46, 30], [28, 46]];
	};
	D.boots = (ctx, r, P) => {
		boot(ctx, P, r.form === "tall" ? 8 : 24, false);
		shape(ctx, P.d, () => ctx.roundRect(20, (r.form === "tall" ? 8 : 24) - 2, 20, 5, 1.5), 1.5);
		for (const y of [32, 38]) shape(ctx, "#c8a040", () => ctx.arc(36, y, 1.2, 0, TAU$1), .5);
		return [[46, 30], [28, 46]];
	};
	D.iron_boots = (ctx, r, P) => {
		boot(ctx, P, 20, r.form === "sabaton");
		for (const y of [28, 36]) line(ctx, P.d, 1.6, [[21, y], [38, y]]);
		shine(ctx, P, [[24, 24], [24, 44]]);
		return [[48, 30], [28, 46]];
	};
	D.greaves = (ctx, r, P) => {
		boot(ctx, P, 6, false);
		shape(ctx, P.d, () => ctx.roundRect(20, 18, 20, 3, 1), 1.2);
		if (r.form === "knee") shape(ctx, P.a, () => ctx.ellipse(30, 10, 11, 7, 0, 0, TAU$1), 2);
		shine(ctx, P, [[24, 12], [24, 44]]);
		return [[48, 28], [28, 46]];
	};
	var baseRing = D.ring;
	D.ring = (ctx, r, P) => {
		if (r.form !== "signet") return baseRing(ctx, r, P);
		ctx.beginPath();
		ctx.ellipse(32, 40, 15, 12, 0, 0, TAU$1);
		ctx.lineWidth = 8;
		ctx.strokeStyle = INK;
		ctx.stroke();
		ctx.lineWidth = 5;
		ctx.strokeStyle = P.a;
		ctx.stroke();
		shape(ctx, P.a, () => ctx.roundRect(21, 14, 22, 16, 3), 2.2);
		shape(ctx, P.d, () => ctx.roundRect(24, 17, 16, 10, 2), 1.2);
		line(ctx, P.a, 1.6, [
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
				shape(ctx, "#8fe3ff", () => ctx.arc(8, -11.5, 1.6, 0, TAU$1), .8);
				line(ctx, INK, 1.8, [[18, -2], [14, 8]]);
				line(ctx, INK, 1.8, [[18, -2], [22, 8]]);
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
				for (const x of [-1.5, 2.5]) line(ctx, INK, 1, [[x, -8], [x, -2]]);
				shape(ctx, WOOD$2, () => {
					ctx.moveTo(-6, -4);
					ctx.lineTo(-2, -2);
					ctx.lineTo(-6, 10);
					ctx.lineTo(-11, 8);
					ctx.closePath();
				});
				line(ctx, INK, 1.6, [
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
		line(ctx, "#e6e0d0", 1, [
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
		line(ctx, "#a06a36", 1.6, [[0, -17], [0, 3]]);
		if (r.form === "heavy") {
			shape(ctx, P.d, () => ctx.arc(0, 14, 4.5, 0, TAU$1), 1.5);
			line(ctx, INK, 1.6, [[0, 14], [7, 18]]);
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
			]) shape(ctx, P.d, () => ctx.arc(14, y + 1.5, 1.8, 0, TAU$1), 1);
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
				ctx.ellipse(x, y, 2.6, 1.8, i * .4, 0, TAU$1);
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
	function pair(base) {
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
	D.dual_dagger = pair(D.dagger);
	D.dual_pistol = pair(D.pistol);
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
			shape(ctx, r.keywords.length ? P.accent : "#7dffb0", () => ctx.arc(0, -30, 3, 0, TAU$1), 1.2);
		});
		return [[42, 18], [28, 38]];
	};
	//#endregion
	//#region client/src/render/dollGear.ts
	/** 標準 `kind` → 紙娃娃部件（只列名稱不同的；其餘同名）。 */
	var HEAD_PART = {
		hat: (f) => f === "wide" ? "wide_hat" : "wizard_hat",
		circlet: (f) => f === "crown" ? "crown" : "bandana",
		helmet: (f) => f === "horned" ? "horned_helm" : f === "greathelm" ? "greathelm" : "helmet"
	};
	var PART_OF = {
		cloth_gloves: "gloves",
		leather_gloves: "gloves",
		round_shield: "shield_round",
		kite_shield: "shield_kite",
		dual_dagger: "dagger",
		dual_pistol: "pistol"
	};
	var PAIRED_KINDS = new Set(gearKinds().filter((k) => k.paired).map((k) => k.id));
	function partOf(kind, form) {
		const head = HEAD_PART[kind];
		return head !== void 0 ? head(form) : PART_OF[kind] ?? kind;
	}
	/** 成對武器造型（雙匕首、雙手槍）→ 單把武器的部件 kind（紙娃娃主手、副手各畫一把）；不是成對造型回傳 `null`。 */
	function pairedPart(kind) {
		return PAIRED_KINDS.has(kind) ? partOf(kind, "") : null;
	}
	//#endregion
	//#region client/src/render/appearance.ts
	/** 元素 → 色（`palette.ts` 的元素主色，與技能特效同一份）；物理與不認得的元素回傳 `undefined`（不套元素色）。 */
	function elementTint(element) {
		return elementTintColors(element)?.primary;
	}
	//#endregion
	//#region client/src/render/inkWeaponFrame.ts
	/** 槍弩（現有座標朝 +x）。 */
	var GUN_KINDS = [
		"pistol",
		"shotgun",
		"longgun",
		"crossbow"
	];
	/** inkWeapons 的傾斜表：[正面／背面往外斜, 側面往前傾]（弧度）；槍弩是朝上抬的角度。 */
	var LEAN$1 = {
		greatsword: [.18, .8],
		hammer: [.2, .5],
		spear: [.12, .4],
		scythe: [.12, .3],
		fist: [.1, 1.2],
		whip: [0, 0],
		pistol: [.35, .05],
		shotgun: [.35, .05],
		longgun: [.35, .05],
		crossbow: [.35, .05]
	};
	/** 側面劍、匕首、拂塵往前上斜（inkGear、inkSect 的 SIDE_TILT）。 */
	var SIDE_TILT = .75;
	/**
	* 預設握法：現有畫法在「平移到手、鏡像」之後的旋轉角度；`null` ＝ 現有畫法不旋轉（法杖、弓、符紙、傀儡線、法球、書）。
	* 數值和運算式照搬原本各檔案的寫法，浮點結果完全相同（快照鎖住）。
	*/
	function restLean(ctx, it, o) {
		switch (it.kind) {
			case "sword":
				if (it.form === "arcane") return inIconMode(ctx) ? 0 : o.side ? .75 : 0;
				return o.side ? SIDE_TILT : 0;
			case "dagger": return o.side ? SIDE_TILT : o.back !== true ? -.5 : 0;
			case "axe": return (o.side ? SIDE_TILT : 0) * .8;
			case "staff":
				if (it.form === "scepter" || it.form === "totem") return inIconMode(ctx) ? 0 : o.side ? .4 : 0;
				return null;
			case "whisk": return o.side ? SIDE_TILT : null;
			case "bow":
			case "talisman":
			case "puppet_cross":
			case "orb":
			case "tome": return null;
		}
		if (inIconMode(ctx)) return 0;
		const [front, side] = LEAN$1[it.kind] ?? [0, 0];
		const gun = GUN_KINDS.includes(it.kind);
		if (!o.side) return gun ? -front : front;
		return gun ? -side + (o.far ? .2 : 0) : side;
	}
	/** 彎刀、彎匕的刀尖往外彎的量（同 inkGear 的 drawBlade）。 */
	function bladeBow(it, o) {
		const outward = !o.side && o.back !== true ? -1 : 1;
		return it.form === "curved" ? 3 * outward : it.form === "kris" ? 3 : 0;
	}
	var PISTOL_LEN = {
		derringer: 6.5,
		revolver: 10.5
	};
	var LONGGUN_LEN = {
		sniper: 25,
		hunting: 24
	};
	function meleeTip(it, o) {
		switch (it.kind) {
			case "sword": return it.form === "arcane" ? [0, -21] : [bladeBow(it, o), -21];
			case "dagger": return [bladeBow(it, o), -10];
			case "greatsword": return it.form === "zhanma" ? [2.8, -28] : [0, -28];
			case "axe": return [0, -24];
			case "hammer": return it.form === "mace" ? [0, -30] : it.form === "flail" ? [3, -34.4] : [0, -35];
			case "spear": return it.form === "trident" ? [0, -52] : [0, -50];
			case "scythe": return [0, -35];
			case "fist": return it.form === "knuckle" ? [0, -5.7] : it.form === "claw" ? [0, -11] : [0, -13];
			case "whip": return it.form === "bladed" ? [20, 9.6] : [16, 9];
			case "whisk": return [0, -22];
			default: return;
		}
	}
	function rangedTip(it, o) {
		switch (it.kind) {
			case "staff":
				if (it.form === "totem") return [0, -46];
				if (it.form === "scepter") return [0, -34];
				return it.form === "wand" ? [0, -30.4 * .75] : [0, -30.4];
			case "bow": return o.side ? [6, 0] : [-6, 0];
			case "crossbow": return it.form === "heavy" ? [18.6, -4.8] : [17.6, -4.8];
			case "pistol": return [PISTOL_LEN[it.form ?? ""] ?? 9, -2.8];
			case "shotgun": return it.form === "blunderbuss" ? [17.4, -3] : [20, -3.2];
			case "longgun": return [LONGGUN_LEN[it.form ?? ""] ?? 22, -3];
			case "talisman": return [.4, -11.2];
			case "puppet_cross": return [0, 11];
			case "orb": return [o.side ? 3.4 : 0, it.form === "floating" ? -9.4 : -5.6];
			default: return;
		}
	}
	/** 作用端在現有座標（握把＝原點、平移到手並鏡像之後、旋轉之前）；不是武器（盾、書）回傳 `undefined`。 */
	function weaponTip(it, o) {
		return meleeTip(it, o) ?? rangedTip(it, o);
	}
	/**
	* 刃點（6M-3，6M-2 驗收第 2 點）：斧、戟、鐮的刃在柄的側邊，揮砍弧光與受擊點從刃的中心畫（技能特效批用）。
	* 座標和 `weaponTip` 相同（現有座標，握把＝原點）；取刃口的中點，落在畫出來的輪廓上。
	* 斧：主刃刃口 (9.4,-20.6)；戟：斧刃刃口中點 (8.5,-42.4)；鐮：內彎刃口的中段 (11,-28)。
	*/
	var EDGE = {
		axe: [9.4, -20.6],
		halberd: [8.5, -42.4],
		scythe: [11, -28]
	};
	/** 有側刃的武器（斧、戟、鐮）的刃點；其他武器回傳 `undefined`（揮砍弧光與受擊點照作用端）。 */
	function weaponEdge(it) {
		if (it.kind === "axe") return EDGE["axe"];
		if (it.kind === "spear" && it.form === "halberd") return EDGE["halberd"];
		if (it.kind === "scythe") return EDGE["scythe"];
	}
	function weaponFrame(it, o) {
		const tip = weaponTip(it, o);
		if (tip === void 0) return void 0;
		return {
			tip,
			base: -Math.PI / 2 - Math.atan2(tip[1], tip[0]),
			len: Math.hypot(tip[0], tip[1])
		};
	}
	/**
	* 轉到握法：沒給 `wpn`（或不是側面）＝ 照現有傾斜（指令和 6M-1 相同）；給了 `wpn` ＝ 統一座標下轉 `wpn`。
	* 呼叫端已平移到手、做好鏡像；之後接著畫現有輪廓。有 `probe` 時回報手與作用端（在 `extraScale` 之前算好作用端）。
	*/
	function orientWeapon(ctx, it, o, lean) {
		const f = o.wpn !== void 0 && o.side ? weaponFrame(it, o) : void 0;
		if (f !== void 0) ctx.rotate(o.wpn + f.base);
		else if (lean !== null) ctx.rotate(lean);
		if (o.probe !== void 0) probeWeapon(ctx, it, o, o.probe);
	}
	function probeWeapon(ctx, it, o, probe) {
		const tip = weaponTip(it, o);
		if (tip === void 0) return;
		const m = ctx.getTransform();
		const at = (p) => [m.a * p[0] + m.c * p[1] + m.e, m.b * p[0] + m.d * p[1] + m.f];
		const edge = weaponEdge(it);
		probe(at([0, 0]), at(tip), edge === void 0 ? void 0 : at(edge));
	}
	//#endregion
	//#region client/src/render/inkSect.ts
	/** 劍穗（sword／dagger 的 `tassel`，劍陣弟子）：在護手下方垂一條；呼叫端已移到手的位置並轉好角度。 */
	function drawTassel(ctx, it, key) {
		if (it.tassel === void 0) return;
		const pts = [
			[0, .6],
			[.8, 4],
			[.2, 7]
		];
		stroke(ctx, `${key}-tassel`, pts, 1.6, INK$1);
		stroke(ctx, `${key}-tassel2`, pts, 1, it.tassel);
	}
	/** 這一層畫得出來的手持物（魔導劍、權杖、圖騰杖仍走現行畫法）。 */
	function isInkWeapon(it) {
		switch (it.kind) {
			case "sword": return it.form !== "arcane";
			case "staff": return it.form !== "scepter" && it.form !== "totem";
			case "dagger":
			case "axe":
			case "bow":
			case "shield_round": return true;
			default: return false;
		}
	}
	/** 金屬部分的顏色：指定顏色或材質色；沒有材質、木材或不認得 → 鋼色（元素仍混色）。 */
	function metalOf(it, colors) {
		return colors(it.color === void 0 && (it.material === void 0 || it.material === "wood") ? {
			...it,
			material: "steel"
		} : it)[0];
	}
	function drawBlade(ctx, it, key, metal, outward = 1) {
		const L = it.kind === "sword" ? 21 : 10;
		const half = it.kind === "sword" && it.form === "broad" ? 1.7 : 1;
		const bow = it.form === "curved" ? 3 * outward : it.form === "kris" ? 3 : 0;
		const bx = (y) => bow * (y / L) ** 2;
		ink(ctx, `${key}-blade`, [
			[-1.1 * half, -2],
			[-1 * half + bx(L - 1.6), -L + 1.6],
			[bx(L), -L],
			[1 * half + bx(L - 1.6), -L + 1.6],
			[1.1 * half, -2]
		], metal, {
			shade: false,
			w: .7
		});
		if (it.kind === "dagger" && inIconMode(ctx)) {
			ink(ctx, `${key}-grip`, [
				[-.9, -2],
				[.9, -2],
				[.9, 4.6],
				[-.9, 4.6]
			], "#3a2a1c", {
				shade: false,
				w: .5
			});
			ink(ctx, `${key}-guard`, [
				[-2.2, -2.9],
				[2.2, -2.9],
				[2.2, -2],
				[-2.2, -2]
			], it.hilt ?? MAT.gold, {
				shade: false,
				w: .5
			});
			return;
		}
		ink(ctx, `${key}-guard`, [
			[-3.4, -3.2],
			[3.4, -3.2],
			[3.4, -1.6],
			[-3.4, -1.6]
		], it.hilt ?? MAT.gold, {
			shade: false,
			w: .6
		});
		drawTassel(ctx, it, key);
	}
	function drawAxe(ctx, key, metal, wood) {
		ink(ctx, `${key}-haft`, [
			[-.8, 9],
			[.8, 9],
			[.8, -24],
			[-.8, -24]
		], wood, {
			shade: false,
			w: .6
		});
		iconHead(ctx, 0, -20, () => {
			ink(ctx, `${key}-head`, [
				[.6, -23],
				[7.6, -27],
				[9.4, -20.6],
				[7.6, -14],
				[.6, -18]
			], metal, { w: .8 });
			ink(ctx, `${key}-head2`, [
				[-.6, -22.4],
				[-4.6, -24.4],
				[-5.2, -20.4],
				[-4.6, -16.6],
				[-.6, -18.6]
			], metal, { w: .7 });
		});
	}
	/** 杖頭光暈：用同心半透明圓疊出柔邊（不用漸層，確定性、好測）。 */
	function drawStaff(ctx, it, key, wood) {
		ink(ctx, `${key}-pole`, [
			[-.8, 22],
			[.8, 22],
			[.9, -27],
			[-.9, -27]
		], wood, {
			shade: false,
			w: .6
		});
		const glow = elementTint(it.element) ?? it.glow ?? "#8fe3ff";
		iconHead(ctx, 0, -27, () => {
			ctx.save();
			ctx.fillStyle = glow;
			for (const [r, a] of [
				[8, .14],
				[6.2, .2],
				[4.4, .28]
			]) {
				ctx.globalAlpha = a;
				ctx.beginPath();
				ctx.arc(0, -30, r, 0, TAU$2);
				ctx.fill();
			}
			ctx.restore();
			ink(ctx, `${key}-claw`, [
				[-3, -27],
				[-2.6, -33.4],
				[0, -29],
				[2.6, -33.4],
				[3, -27]
			], wood, {
				shade: false,
				w: .6
			});
			ink(ctx, `${key}-orb`, ellPts(0, -30.4, 2.4, 2.4, 10), glow, {
				shade: false,
				w: .6
			});
		});
	}
	/** 弓：弓弦在 +x、弓身往 -x 彎（箭的方向 -x）。`pull`（6M-2）＝ 弓弦中點往 +x 拉開的距離；> 0.5 時搭上一支箭。 */
	function drawBow(ctx, key, wood, pull, metal) {
		stroke(ctx, `${key}-string`, pull > 0 ? [
			[2, -15],
			[2 + pull, 0],
			[2, 14]
		] : [[2, -15], [2, 14]], .35, "#e8e0d0");
		ink(ctx, `${key}-limb`, [
			[1.6, -15],
			[-2.4, -9],
			[-3.6, 0],
			[-2.4, 8],
			[1.6, 14],
			[.4, 14.4],
			[-4.4, 8],
			[-5.8, 0],
			[-4.4, -9],
			[.4, -15.4]
		], wood, {
			shade: false,
			w: .6
		});
		if (pull > .5) {
			stroke(ctx, `${key}-arrow`, [[2 + pull, 0], [-9, 0]], .9, "#c8a070");
			ink(ctx, `${key}-arrowhead`, [
				[-8.6, 1.2],
				[-11, 0],
				[-8.6, -1.2]
			], metal, {
				shade: false,
				w: .4,
				sharp: true
			});
		}
	}
	/**
	* 畫 C 畫風的手持物。(x, y) ＝ 手的位置，`key` ＝ 抖動種子前綴（main／off／main-s／off-s／main-b／off-b）。
	* 正面、背面豎起；側面劍、匕首往前上斜 0.75 rad、斧 0.6 rad，法杖、弓直立。不是這一層畫得出來的 kind 回傳 false。
	*/
	function drawInkWeapon(ctx, it, key, x, y, o, colors) {
		if (!isInkWeapon(it) || it.kind === "shield_round") return false;
		const shade = o.far ? .25 : 0;
		const metal = darken(metalOf(it, colors), shade);
		const wood = darken(MAT.wood, shade);
		ctx.save();
		ctx.translate(x, y);
		if (o.mirror !== (it.kind === "axe" && !o.side)) ctx.scale(-1, 1);
		orientWeapon(ctx, it, o, restLean(ctx, it, o));
		switch (it.kind) {
			case "sword":
			case "dagger":
				drawBlade(ctx, it, key, metal, !o.side && o.back !== true ? -1 : 1);
				break;
			case "axe":
				drawAxe(ctx, key, metal, wood);
				break;
			case "staff":
				if (it.form === "wand") ctx.scale(.75, .75);
				drawStaff(ctx, it, key, wood);
				break;
			default:
				if (o.side) ctx.scale(-1, 1);
				drawBow(ctx, key, it.color ?? wood, o.pull ?? 0, metal);
		}
		ctx.restore();
		return true;
	}
	//#endregion
	//#region client/src/render/inkWeapons.ts
	var GOLD$2 = MAT.gold;
	var WOOD$1 = MAT.wood;
	var WOOD_DARK = "#6a4420";
	var STOCK = "#7a5232";
	var GRIP = "#3a2a1c";
	/** 魔導劍預設劍身色（冷灰，比一般鋼劍暗一點，讓光槽更明顯）。 */
	var ARCANE_BLADE = "#8a93a8";
	/** 魔導劍的源晶槽顏色：有元素換元素色，否則藍紫（供測試與圖示共用）。 */
	var arcaneGlow = (element) => elementTint(element) ?? "#9a86ff";
	var BRASS = "#b08a4a";
	var rect = (x0, y0, x1, y1) => [
		[x0, y0],
		[x1, y0],
		[x1, y1],
		[x0, y1]
	];
	/** 木柄：y0（下端）到 y1（上端，較小）。 */
	function haft(ctx, k, y0, y1, c, w = .9) {
		ink(ctx, `${k}-haft`, rect(-w, y1, w, y0), c, {
			shade: false,
			w: .6
		});
	}
	function drawGreatsword(ctx, it, k, c) {
		const pts = it.form === "zhanma" ? [
			[-2.4, -3.6],
			[-2.4, -26],
			[2.8, -28],
			[2.8, -3.6]
		] : [
			[-2.4, -3.6],
			[-2.2, -25],
			[0, -28],
			[2.2, -25],
			[2.4, -3.6]
		];
		ink(ctx, `${k}-blade`, pts, c.metal, {
			shade: false,
			w: .8
		});
		stroke(ctx, `${k}-fuller`, [[0, -7], [0, -23]], .4, c.dark);
		if (it.form === "serrated") {
			const teeth = [];
			for (let i = 0; i < 6; i += 1) teeth.push([2.3, -8 - i * 3.2], [4.2, -9.4 - i * 3.2]);
			stroke(ctx, `${k}-teeth`, teeth, .5, c.metal);
		}
		ink(ctx, `${k}-guard`, rect(-5.4, -4.8, 5.4, -3.2), c.gold, {
			shade: false,
			w: .6
		});
		ink(ctx, `${k}-grip`, rect(-1, -3.2, 1, 5), c.grip, {
			shade: false,
			w: .5
		});
		ink(ctx, `${k}-pommel`, ellPts(0, 6, 1.6, 1.6, 8), c.gold, {
			shade: false,
			w: .5
		});
	}
	function drawHammer(ctx, it, k, c) {
		if (it.form === "mace") {
			haft(ctx, k, 4, -22, c.wood);
			iconHead(ctx, 0, -22, () => {
				ink(ctx, `${k}-ball`, ellPts(0, -25, 5, 5, 12), c.metal, { w: .8 });
				stroke(ctx, `${k}-flange`, [[-5, -25], [5, -25]], .5, c.dark);
			});
			return;
		}
		if (it.form === "flail") {
			haft(ctx, k, 4, -18, c.wood);
			iconHead(ctx, 0, -18, () => {
				stroke(ctx, `${k}-chain`, [
					[0, -18],
					[3.8, -22],
					[3.2, -26]
				], .9, c.dark);
				ink(ctx, `${k}-ball`, ellPts(3, -30, 4.4, 4.4, 12), c.metal, { w: .8 });
			});
			return;
		}
		haft(ctx, k, 4, -27, c.wood, 1);
		iconHead(ctx, 0, -26, () => {
			ink(ctx, `${k}-head`, rect(-7.6, -35, 7.6, -26), c.metal, {
				w: .9,
				sharp: inIconMode(ctx)
			});
			stroke(ctx, `${k}-band`, [[-7.6, -30.5], [7.6, -30.5]], .5, c.dark);
		});
	}
	function drawSpear(ctx, it, k, c) {
		haft(ctx, k, 8, -36, c.wood, 1);
		if (it.form === "trident") {
			for (const sx of [
				-3.6,
				0,
				3.6
			]) ink(ctx, `${k}-prong${sx}`, [
				[sx, sx === 0 ? -52 : -49],
				[sx + 1.4, -38],
				[sx - 1.4, -38]
			], c.metal, {
				shade: false,
				w: .6
			});
			ink(ctx, `${k}-cross`, rect(-4.4, -39, 4.4, -37.2), c.metal, {
				shade: false,
				w: .6
			});
			return;
		}
		iconHead(ctx, 0, -36, () => {
			const sp = it.form === "halberd" || !inIconMode(ctx) ? 1 : 4 / 3;
			const hp = (x, y) => [x * sp, -36 + (y + 36) * sp];
			ink(ctx, `${k}-head`, [
				hp(0, -50),
				hp(3.6, -43),
				hp(0, -36),
				hp(-3.6, -43)
			], c.metal, { w: .8 });
			if (it.form === "halberd") ink(ctx, `${k}-axe`, [
				[1.4, -45],
				[8.6, -46.4],
				[8.4, -38.4],
				[1.4, -39.6]
			], c.metal, { w: .8 });
		});
	}
	/** 小圖示的拳套（3T-4d）：正面指虎——壓扁的鋼色方塊、上緣 4 個相連半圓指節（高約方塊 35%）、橫向長條握孔，直立。 */
	function drawFistIcon(ctx, k, c) {
		ink(ctx, `${k}-block`, rect(-5.6, -1.5, 5.6, 3.5), c.metal, {
			w: .9,
			sharp: true
		});
		for (const x of [
			-4.2,
			-1.4,
			1.4,
			4.2
		]) {
			const arc = [];
			for (let i = 0; i <= 8; i++) {
				const t = Math.PI * i / 8;
				arc.push([x + 1.4 * Math.cos(t), -1.5 - 1.75 * Math.sin(t)]);
			}
			ink(ctx, `${k}-knuckle${x}`, arc, c.metal, { w: .7 });
		}
		ink(ctx, `${k}-hole`, rect(-3.4, .5, 3.4, 2.1), c.dark, {
			shade: false,
			w: .6,
			sharp: true
		});
	}
	function drawFist(ctx, it, k, c) {
		if (inIconMode(ctx)) {
			drawFistIcon(ctx, k, c);
			return;
		}
		ink(ctx, `${k}-block`, rect(-3.4, -4, 3.4, 3), c.metal, { w: .8 });
		if (it.form === "knuckle") {
			for (const x of [
				-2.2,
				0,
				2.2
			]) ink(ctx, `${k}-stud${x}`, ellPts(x, -4.6, 1.1, 1.1, 8), c.dark, {
				shade: false,
				w: .4
			});
			return;
		}
		const blades = it.form === "claw" ? [
			-2.2,
			0,
			2.2
		] : [0];
		for (const x of blades) ink(ctx, `${k}-blade${x}`, [
			[x - 1.3, -4],
			[x, it.form === "claw" ? -11 : -13],
			[x + 1.3, -4]
		], c.metal, {
			shade: false,
			w: .6
		});
	}
	function drawScythe(ctx, _it, k, c) {
		haft(ctx, k, 8, -34, c.wood);
		iconHead(ctx, 0, -32, () => ink(ctx, `${k}-blade`, [
			[0, -35],
			[7, -38],
			[15, -33],
			[18.4, -22],
			[11, -28],
			[0, -29]
		], c.metal, { w: .8 }));
	}
	function drawWhip(ctx, it, k, c) {
		ink(ctx, `${k}-handle`, rect(-1.1, -5, 1.1, 5), c.grip, {
			shade: false,
			w: .5
		});
		const lash = [
			[0, -5],
			[6, -9],
			[9, -5],
			[8, 1],
			[11, 6],
			[16, 9]
		];
		const chain = it.form === "chain";
		stroke(ctx, `${k}-lash`, lash, chain ? 1.3 : 1, chain ? c.dark : c.wood);
		if (chain) for (let i = 1; i < lash.length; i += 1) dot(ctx, lash[i][0], lash[i][1], .9, .9, c.metal);
		if (it.form === "bladed") ink(ctx, `${k}-tip`, [
			[15, 7],
			[20, 9.6],
			[15, 11.4]
		], c.metal, {
			shade: false,
			w: .5
		});
	}
	function drawArcaneSword(ctx, it, k, c) {
		const glow = arcaneGlow(it.element);
		ink(ctx, `${k}-blade`, [
			[-1.5, -2],
			[-1.3, -19.2],
			[0, -21],
			[1.3, -19.2],
			[1.5, -2]
		], c.metal, {
			shade: false,
			w: .7
		});
		ink(ctx, `${k}-groove`, rect(-.6, -18.6, .6, -5), glow, {
			shade: false,
			line: false,
			w: .4
		});
		for (const y of [
			-6.5,
			-10.5,
			-14.5
		]) dot(ctx, 0, y, 1, .45, "#e8e2ff");
		ink(ctx, `${k}-gear`, ellPts(0, -3.2, 4.6, 2.5, 12), BRASS, {
			shade: false,
			w: .6
		});
		ink(ctx, `${k}-crystal`, ellPts(0, -3.2, 1.4, 1.4, 8), glow, {
			shade: false,
			w: .4
		});
		ink(ctx, `${k}-grip`, rect(-.9, -1.6, .9, 4.6), c.grip, {
			shade: false,
			w: .5
		});
	}
	function drawScepter(ctx, it, k, c) {
		const gem = elementTint(it.element) ?? c.metal;
		ink(ctx, `${k}-shaft`, rect(-1.3, -30, 1.3, 8), WOOD_DARK, {
			shade: false,
			w: .6
		});
		iconHead(ctx, 0, -29, () => {
			const ring = ellPts(0, -34, 6, 6, 16);
			stroke(ctx, `${k}-ring`, [...ring, ring[0]], 1.5, c.gold);
			ink(ctx, `${k}-gem`, ellPts(0, -34, 3, 3, 10), gem, {
				shade: false,
				w: .6
			});
			dot(ctx, -1, -35, .8, .8, "#ffffff");
		});
	}
	/** 杖頭光暈（Phase 5A-ART5，`GearItem.glow`）：同心半透明圓疊出柔邊，同 inkGear 的 `drawStaff`。 */
	function staffHalo(ctx, glow, y) {
		ctx.save();
		ctx.fillStyle = glow;
		for (const [r, a] of [
			[8, .14],
			[6.2, .2],
			[4.4, .28]
		]) {
			ctx.globalAlpha = a;
			ctx.beginPath();
			ctx.arc(0, y, r, 0, Math.PI * 2);
			ctx.fill();
		}
		ctx.restore();
	}
	function drawTotem(ctx, it, k) {
		ink(ctx, `${k}-pole`, rect(-1.9, -42, 1.9, 8), "#8f5f2c", {
			shade: false,
			w: .6
		});
		for (const [y, col] of [[-39, "#b83a3a"], [-27, "#3a8a8a"]]) {
			ink(ctx, `${k}-face${y}`, rect(-5.2, y, 5.2, y + 9), "#b77f3f", { w: .7 });
			stroke(ctx, `${k}-brow${y}`, [[-3.4, y + 2], [3.4, y + 2]], 1.2, col);
			stroke(ctx, `${k}-mouth${y}`, [[-2.4, y + 6], [2.4, y + 6]], .9, "#1d1a22");
		}
		for (const s of [-1, 1]) ink(ctx, `${k}-feather${s}`, [
			[s * 5, -37],
			[s * 10.5, -43],
			[s * 11, -33],
			[s * 5, -31]
		], "#e6e6e0", { w: .6 });
		if (it.glow !== void 0) staffHalo(ctx, it.glow, -46);
		ink(ctx, `${k}-orb`, ellPts(0, -46, 3.4, 3.4, 10), it.glow ?? "#7dffb0", {
			shade: false,
			w: .6
		});
		dot(ctx, -1, -47, .9, .9, "#ffffff");
	}
	function drawPistol(ctx, it, k, c) {
		const L = it.form === "derringer" ? 6.5 : it.form === "revolver" ? 10.5 : 9;
		const grip = inIconMode(ctx) ? [
			[-1.4, -1.4],
			[2.2, -1.4],
			[-1.4, 5.4],
			[-5, 5.4]
		] : [
			[-1.8, -1.4],
			[1.8, -1.4],
			[1.2, 5.8],
			[-2, 5.8]
		];
		ink(ctx, `${k}-grip`, grip, it.form === "flintlock" ? STOCK : GRIP, {
			shade: false,
			w: .6,
			sharp: inIconMode(ctx)
		});
		ink(ctx, `${k}-barrel`, rect(-1.4, -4.4, L, -1.2), c.metal, {
			w: .7,
			sharp: inIconMode(ctx)
		});
		if (it.form === "derringer") ink(ctx, `${k}-barrel2`, rect(-1.4, -1.2, L, 1.2), c.dark, {
			shade: false,
			w: .6
		});
		if (it.form === "revolver") ink(ctx, `${k}-cyl`, ellPts(1.6, -2.8, 3, 3.2, 10), c.dark, {
			shade: false,
			w: .6
		});
		if (it.form === "flintlock") ink(ctx, `${k}-cock`, [
			[-.6, -4.4],
			[-2.4, -8],
			[.4, -8.4],
			[1.8, -4.4]
		], c.dark, {
			shade: false,
			w: .5
		});
	}
	function drawShotgun(ctx, it, k, c) {
		const icon = inIconMode(ctx);
		const L = it.form === "blunderbuss" ? 15 : icon ? 16.5 : 20;
		const stock = icon ? [
			[-5.4, -4.4],
			[0, -5.4],
			[0, 0],
			[-3.9, 2.2]
		] : [
			[-9, -5],
			[0, -4.6],
			[0, 0],
			[-6.4, 1.8],
			[-9, -1]
		];
		ink(ctx, `${k}-stock`, stock, STOCK, {
			shade: false,
			w: .7,
			sharp: icon
		});
		ink(ctx, `${k}-grip`, [
			[-1.6, -1],
			[1.2, -1],
			[.8, 4.6],
			[-1.8, 4.6]
		], GRIP, {
			shade: false,
			w: .5
		});
		if (icon && it.form !== "blunderbuss") {
			ink(ctx, `${k}-barrel`, rect(0, -5.4, L, -2.7), c.metal, {
				w: .8,
				sharp: true
			});
			ink(ctx, `${k}-barrel-low`, rect(0, -2.7, L, 0), c.metal, {
				w: .8,
				sharp: true
			});
		} else ink(ctx, `${k}-barrel`, rect(0, -5.2, L, -1.2), c.metal, { w: .8 });
		if (it.form === "double" && !icon) ink(ctx, `${k}-barrel2`, rect(0, -1.2, L, 1.8), c.dark, {
			shade: false,
			w: .6
		});
		if (it.form === "pump") ink(ctx, `${k}-slide`, rect(6, -1.2, 13, 1.6), STOCK, {
			shade: false,
			w: .6
		});
		if (it.form === "blunderbuss") ink(ctx, `${k}-flare`, [
			[L - 6, -5.2],
			[L + 2.4, -9],
			[L + 2.4, 3],
			[L - 6, -.8]
		], c.metal, { w: .8 });
	}
	function drawLongGun(ctx, it, k, c) {
		const sniper = it.form === "sniper";
		const L = sniper ? 25 : it.form === "hunting" ? 24 : 22;
		ink(ctx, `${k}-stock`, [
			[-10.5, -5],
			[0, -4.6],
			[0, 0],
			[-7.4, 2],
			[-10.5, -1]
		], sniper ? c.dark : STOCK, {
			shade: false,
			w: .7
		});
		ink(ctx, `${k}-grip`, [
			[-1.6, -1],
			[1.2, -1],
			[.8, 4.6],
			[-1.8, 4.6]
		], GRIP, {
			shade: false,
			w: .5
		});
		ink(ctx, `${k}-barrel`, rect(0, -4.6, L, -1.4), c.metal, { w: .8 });
		if (it.form === "hunting") ink(ctx, `${k}-fore`, rect(L * .3, -1.4, L, 1), STOCK, {
			shade: false,
			w: .6
		});
		if (it.form === "flintlock") {
			ink(ctx, `${k}-cock`, [
				[-.4, -4.6],
				[-2.6, -8.4],
				[.4, -9],
				[2, -4.6]
			], c.dark, {
				shade: false,
				w: .5
			});
			ink(ctx, `${k}-band`, rect(L * .45, -4.8, L * .45 + 1.8, -1.2), c.gold, {
				shade: false,
				w: .4
			});
		}
		if (sniper) {
			ink(ctx, `${k}-scope`, rect(5, -9, 16, -5.4), "#2a2d33", { w: .7 });
			dot(ctx, 16, -7.2, .9, 1.4, "#8fe3ff");
			stroke(ctx, `${k}-bipod`, [[20, -1.4], [18.4, 4.6]], .7);
			stroke(ctx, `${k}-bipod2`, [[20, -1.4], [22.4, 4.6]], .7);
		}
	}
	function drawCrossbow(ctx, it, k, c) {
		const heavy = it.form === "heavy";
		const span = heavy ? 11.6 : 9.6;
		const tip = heavy ? 15 : 14;
		ink(ctx, `${k}-stock`, rect(-3.4, -4.4, tip + 1, -1.4), STOCK, {
			shade: false,
			w: .7
		});
		ink(ctx, `${k}-grip`, [
			[-1.4, -1.4],
			[1.4, -1.4],
			[1, 4.4],
			[-1.6, 4.4]
		], GRIP, {
			shade: false,
			w: .5
		});
		if (it.form === "repeater") ink(ctx, `${k}-mag`, rect(1.6, -9.4, 9.6, -4.4), GRIP, { w: .7 });
		stroke(ctx, `${k}-string`, [
			[tip, -2.9 - span],
			[tip - 8, -2.9],
			[tip, -2.9 + span]
		], .4, "#e8e0d0");
		stroke(ctx, `${k}-arm`, [
			[tip - 1, -2.9 - span],
			[tip + 3, -2.9],
			[tip - 1, -2.9 + span]
		], heavy ? 1.8 : 1.3, c.metal);
		ink(ctx, `${k}-bolt`, rect(tip - 12, -5.2, tip + 1, -4.4), c.wood, {
			shade: false,
			w: .4
		});
		ink(ctx, `${k}-bolt-tip`, [
			[tip + 1, -5.7],
			[tip + 3.6, -4.8],
			[tip + 1, -3.9]
		], c.metal, {
			shade: false,
			w: .4
		});
		if (heavy) {
			const r = ellPts(tip + 3, -2.9, 2.4, 3.2, 10);
			stroke(ctx, `${k}-stirrup`, [...r, r[0]], .8, GRIP);
		}
	}
	var SHAPES = {
		greatsword: drawGreatsword,
		hammer: drawHammer,
		spear: drawSpear,
		fist: drawFist,
		scythe: drawScythe,
		whip: drawWhip,
		pistol: drawPistol,
		shotgun: drawShotgun,
		longgun: drawLongGun,
		crossbow: drawCrossbow
	};
	/** 這一層畫得出來的手持物：魔導劍、權杖、圖騰杖，以及上面那些武器 kind。 */
	function isInkWeaponMore(it) {
		if (it.kind === "sword") return it.form === "arcane";
		if (it.kind === "staff") return it.form === "scepter" || it.form === "totem";
		return SHAPES[it.kind] !== void 0;
	}
	function shapeOf(it) {
		if (it.kind === "sword") return drawArcaneSword;
		if (it.kind === "staff") return it.form === "totem" ? drawTotem : drawScepter;
		return SHAPES[it.kind];
	}
	/**
	* 畫其餘武器。(x, y) ＝ 手的位置；`key` ＝ 抖動種子前綴。外側（正面主手＝畫面左、副手鏡像＝畫面右、背面相反）與側面前方都是 +x。
	* 回傳 false ＝ 不是這一層的武器。
	*/
	function drawInkWeaponMore(ctx, it, key, x, y, o, colors) {
		if (!isInkWeaponMore(it)) return false;
		const shade = o.far ? .25 : 0;
		const c = {
			metal: darken(it.kind === "sword" && it.color === void 0 ? ARCANE_BLADE : metalOf(it, colors), shade),
			dark: darken(colors(it)[1], shade),
			wood: darken(WOOD$1, shade),
			grip: darken(GRIP, shade),
			gold: darken(GOLD$2, shade)
		};
		ctx.save();
		ctx.translate(x, y);
		if (!o.side && !o.mirror) ctx.scale(-1, 1);
		if (o.side && it.kind === "staff" && it.form === "totem") ctx.translate(2, 0);
		orientWeapon(ctx, it, o, restLean(ctx, it, o));
		shapeOf(it)(ctx, it, key, c);
		ctx.restore();
		return true;
	}
	/**
	* 單獨畫一件主手武器（小圖示用）：原點在手的位置，不是側面；和小人手持的同一套 C 畫法。
	* 以「副手鏡像」的方向畫，外側朝 +x 的武器（斧、槍弩、魔導劍…）槍口與刃朝右。畫不出來的 kind 回傳 false。
	*/
	function drawInkWeaponAlone(ctx, it, colors) {
		const o = {
			mirror: true,
			side: false,
			far: false,
			back: true
		};
		return drawInkWeapon(ctx, it, "icon", 0, 0, o, colors) || drawInkWeaponMore(ctx, it, "icon", 0, 0, o, colors);
	}
	MAT.gold;
	MAT.gold;
	MAT.wood;
	Object.freeze({});
	//#endregion
	//#region client/src/render/itemColors.ts
	function darker(c, f = .68) {
		return mix$1(c, "#000000", 1 - f);
	}
	/** 一件裝備的 [主色, 暗色]：指定顏色或材質色（不認得 → 布料色），有元素時混入元素色 45%。 */
	function itemColors(item) {
		const base = MATERIAL[item.material ?? "cloth"] ?? MATERIAL.cloth;
		let [main, dark] = item.color !== void 0 ? [item.color, darker(item.color)] : [base[0], base[1]];
		const tint = elementTint(item.element);
		if (tint !== void 0) {
			main = mix$1(main, tint, .45);
			dark = mix$1(dark, tint, .3);
		}
		return [main, dark];
	}
	function fill(ctx, c, path) {
		ctx.beginPath();
		ctx.fillStyle = c;
		path();
		ctx.fill();
	}
	/** 兩色混合（樣張 mix；只認 #rrggbb）。 */
	function mix(a, b, t) {
		const p = (h) => [
			1,
			3,
			5
		].map((i) => parseInt(h.slice(i, i + 2), 16));
		const A = p(a);
		const B = p(b);
		return "#" + A.map((v, i) => Math.round(v + ((B[i] ?? 0) - v) * t).toString(16).padStart(2, "0")).join("");
	}
	({
		A: {
			a: .7,
			dx: 0,
			tilt: 0,
			robe: 0,
			hold: 0,
			sw: 0,
			swa: 0
		},
		E: {
			a: .325,
			dx: 0,
			tilt: 0,
			robe: 0,
			hold: 0,
			sw: 1,
			swa: 0,
			bk: -1,
			shf: true,
			po: 0,
			shA: .2,
			ea: .09,
			edge: {
				mode: "inner",
				w: .9,
				k: .45,
				fist: {
					mode: "ring",
					w: .9,
					k: .45
				}
			},
			sideOne: true
		}
	}).E;
	//#endregion
	//#region client/src/render/qNpcHeld.ts
	/** 四指：橫過握柄的一條（和手同色）＋一條指縫。 */
	function heldFingers(c, it) {
		const k = it?.skin ?? "#f1c9a5";
		fill(c, k, () => c.roundRect(-2.3, -1.1, 4.6, 2.2, 1));
		c.strokeStyle = mix(k, "#000000", .3);
		c.lineWidth = .35;
		c.beginPath();
		c.moveTo(-1.6, .05);
		c.lineTo(1.6, .05);
		c.stroke();
	}
	var QW_HELD = {
		whisk: {
			len: 7,
			hold: {
				side: .3,
				front: 0
			},
			draw: (c, it) => {
				fill(c, "#8a5a2a", () => c.roundRect(-.65, -6.6, 1.3, 9.4, .6));
				fill(c, "#e8bb48", () => c.roundRect(-.9, -7.2, 1.8, 1.2, .5));
				fill(c, it?.color ?? "#f2f0ea", () => {
					c.moveTo(-.9, -7);
					c.quadraticCurveTo(-5.6, -7.6, -6.4, 1.6);
					c.quadraticCurveTo(-4.6, 3.2, -3.2, .6);
					c.quadraticCurveTo(-2.4, -4.4, .9, -6.6);
					c.closePath();
				});
				heldFingers(c, it);
			}
		},
		talisman: {
			len: 9,
			hold: {
				side: .25,
				front: .15
			},
			draw: (c, it) => {
				fill(c, it?.color ?? "#f2d860", () => c.roundRect(-1.5, -9.4, 3, 8.4, .3));
				c.strokeStyle = "#c0392b";
				c.lineWidth = .45;
				c.lineCap = "round";
				c.beginPath();
				c.moveTo(0, -8.6);
				c.lineTo(-.7, -7.2);
				c.lineTo(.7, -5.8);
				c.lineTo(-.5, -4.4);
				c.lineTo(.3, -3.2);
				c.stroke();
				heldFingers(c, it);
			}
		},
		puppet_strings: {
			len: 4,
			hold: {
				side: 0,
				front: 0
			},
			draw: (c, it) => {
				fill(c, "#8a6a48", () => c.roundRect(-4.4, -.6, 8.8, 1.3, .5));
				fill(c, "#8a6a48", () => c.roundRect(-.65, -3.6, 1.3, 7.6, .5));
				heldFingers(c, it);
			}
		}
	};
	var BOW_R = 8.5;
	var BOW_EY = BOW_R - Math.cos(1.2) * BOW_R;
	({ ...QW_HELD });
	//#endregion
	//#region client/src/render/qAnimFB.ts
	var arm = (who, L, x = {}) => ({
		t: "arm",
		who,
		L,
		...x
	});
	var wpn = (L, a, x = {}) => ({
		t: "w",
		L,
		a,
		...x
	});
	var wrapOp = (L, a, on = "m") => ({
		t: "wrap",
		L,
		a,
		on
	});
	var IDLE_F = {
		m: {
			h: [-11.85, -10.06],
			st: true
		},
		o: {
			h: [11.85, -10.06],
			st: true
		}
	};
	var IDLE_B = {
		m: {
			h: [11.85, -10.06],
			st: true
		},
		o: {
			h: [-11.85, -10.06],
			st: true
		}
	};
	var PI = Math.PI;
	/** 背面前傾（0 預備 … 4 命中 … 6 回正）。 */
	var LEAN = [
		0,
		.05,
		.08,
		.1,
		.12,
		.05,
		0
	];
	var lean = (fr) => fr.map((f, i) => ({
		...f,
		lean: LEAN[i] ?? 0
	}));
	({ ...IDLE_F }), arm("o", "over"), arm("m", "over"), wpn("over", -.12, { wrap: true }), arm("o", "over"), arm("m", "over"), wpn("over", -.05, { wrap: true }), wpn("under", .8), arm("o", "over"), arm("m", "over"), arm("o", "over"), arm("m", "over"), wpn("top", -.25, {
		s: .55,
		wd: 1.1,
		wrap: true
	}), arm("o", "over"), arm("m", "top"), wpn("top", PI - .4, {
		s: .75,
		wd: 1.15,
		wrap: true
	}), arm("o", "over"), arm("m", "top"), wpn("top", 2.25, {
		s: .95,
		wd: 1.05,
		wrap: true
	}), IDLE_F.o, arm("o", "over"), arm("m", "over"), wpn("over", -.5, { wrap: true }), lean([
		{
			...IDLE_B,
			ops: [
				wpn("under", .12),
				arm("o", "over"),
				arm("m", "over"),
				wpn("over", .12, { clip: "hand" })
			]
		},
		{
			m: {
				h: [13, -21.5],
				out: 1
			},
			o: {
				h: [-12, -13],
				st: true
			},
			bob: -.4,
			ops: [
				arm("o", "over"),
				arm("m", "over"),
				wpn("over", .05)
			]
		},
		{
			m: {
				h: [12, -29.5],
				out: 1
			},
			o: {
				h: [-11.5, -15],
				st: true
			},
			bob: -.6,
			ops: [
				arm("o", "over"),
				arm("m", "over"),
				wpn("top", -.8)
			]
		},
		{
			m: {
				h: [10.5, -28],
				out: 1
			},
			o: {
				h: [-12, -14],
				st: true
			},
			bob: -.3,
			ops: [
				arm("o", "over"),
				wpn("over", .1, { s: .6 }),
				arm("m", "over"),
				wpn("over", .1, {
					s: .6,
					clip: "hand"
				})
			]
		},
		{
			m: {
				h: [3, -15],
				out: 1
			},
			o: {
				h: [-12.5, -16],
				st: true
			},
			ops: [
				wpn("under", -2.2, { s: .8 }),
				arm("m", "over", { clip: "out" }),
				arm("o", "over")
			]
		},
		{
			m: {
				h: [.5, -14.5],
				out: 1
			},
			o: {
				h: [-12, -15],
				st: true
			},
			ops: [
				wpn("under", -2.55, { s: .85 }),
				arm("m", "over", { clip: "out" }),
				arm("o", "over")
			]
		},
		{
			m: {
				h: [11, -12],
				st: true
			},
			o: IDLE_B.o,
			ops: [
				wpn("under", .4),
				arm("o", "over"),
				arm("m", "over"),
				wpn("over", .4, { clip: "hand" })
			]
		}
	]);
	var SPF = (Lf, hl, hw) => [
		arm("o", "over"),
		arm("m", "over"),
		{
			t: "spear",
			L: "over",
			Lf,
			Lb: 4,
			hl,
			hw,
			w0: 1.5,
			w1: 2.1 + hw * .06
		},
		wrapOp("over", "spA", "m"),
		wrapOp("over", "spA", "o")
	];
	var SPB = (Lf, Lb, d) => {
		const dd = d === void 0 ? {} : { d };
		return [
			arm("o", "under"),
			{
				t: "spear",
				L: "under",
				Lf,
				Lb,
				hl: 3,
				hw: 3.4,
				w0: 2.4,
				w1: 1.3,
				...dd
			},
			arm("m", "over"),
			{
				t: "spear",
				L: "over",
				Lf,
				Lb,
				hl: 3,
				hw: 3.4,
				w0: 2.4,
				w1: 1.3,
				hand: true,
				...dd
			}
		];
	};
	SPF(14, 5, 6.5), SPF(11, 4.5, 6), SPF(10, 4.3, 5.8), SPF(18, 6.2, 8.4), SPF(20, 7, 9.6), SPF(18.5, 6.6, 9), SPF(14, 5, 6.5), lean([
		{
			m: {
				h: [9.3, -12.5],
				out: 1
			},
			o: {
				h: [2, -16.5],
				out: -1
			},
			ops: SPB(11, 9)
		},
		{
			m: {
				h: [10.2, -10.5],
				out: 1
			},
			o: {
				h: [.5, -16.5],
				out: -1
			},
			bob: -.3,
			ops: SPB(11, 10)
		},
		{
			m: {
				h: [10.4, -10],
				out: 1
			},
			o: {
				h: [.2, -16.2],
				out: -1
			},
			bob: -.5,
			ops: SPB(11, 10.5)
		},
		{
			m: {
				h: [8.6, -15],
				out: 1
			},
			o: {
				h: [0, -19],
				out: -1
			},
			liftL: 1.5,
			ops: SPB(22, 8, [-.33, -.94])
		},
		{
			m: {
				h: [8, -16],
				out: 1
			},
			o: {
				h: [-.5, -19.5],
				out: -1
			},
			liftL: 1,
			ops: SPB(25, 7.5, [-.34, -.94])
		},
		{
			m: {
				h: [8.3, -15.5],
				out: 1
			},
			o: {
				h: [0, -19.2],
				out: -1
			},
			ops: SPB(24, 7.8, [-.34, -.94])
		},
		{
			m: {
				h: [9.3, -12.5],
				out: 1
			},
			o: {
				h: [2, -16.5],
				out: -1
			},
			ops: SPB(11, 9)
		}
	]);
	var BK = BOW_EY + 9;
	var F_FULL = [10 / BK, 9.5 / BK];
	var F_FULL_B = [-13.3 / BK, -5 / BK];
	var bow = (L, U, pull, nock = true, F, torso = false) => ({
		t: "bow",
		L,
		U,
		pull,
		nock,
		...F === void 0 ? {} : { F },
		...torso ? { torso } : {}
	});
	var BF = (U, pull, nock = true, F) => [
		arm("o", "top"),
		bow("top", U, pull, nock, F),
		arm("m", "top")
	];
	var BB = (U, pull, nock, F, clipM = false) => [
		bow("under", U, pull, nock, F),
		arm("o", "over"),
		arm("m", "over", clipM ? { clip: "out" } : {})
	];
	var BOW = {
		front: [
			{
				m: {
					h: [0, -15],
					out: -1
				},
				o: {
					h: [5, -11.5],
					st: true
				},
				ops: BF([-.3, .95], 2)
			},
			{
				m: {
					h: [-1, -19],
					out: -1
				},
				o: {
					h: [5.5, -16.5],
					st: true
				},
				bob: -.2,
				ops: BF([-.4, .92], 3)
			},
			{
				m: {
					h: [-3.5, -22],
					out: -1
				},
				o: {
					h: [5, -15.5],
					st: true
				},
				bob: -.3,
				ops: BF([-.45, .89], 6)
			},
			{
				m: {
					h: [-5.5, -24],
					out: -1
				},
				o: {
					h: [4.5, -14.5],
					st: true
				},
				bob: -.3,
				ops: BF([-.5, .87], 9)
			},
			{
				m: {
					h: [-8, -25.5],
					out: -1
				},
				o: {
					h: [4.5, -14.5],
					st: true
				},
				bob: -.2,
				ops: BF([-.5, .87], 0, false, F_FULL)
			},
			{
				m: {
					h: [-7, -21],
					out: -1
				},
				o: {
					h: [4.5, -14],
					st: true
				},
				ops: BF([-.5, .87], 0, false, F_FULL)
			},
			{
				m: IDLE_F.m,
				o: {
					h: [5, -12],
					st: true
				},
				ops: [
					arm("o", "top"),
					bow("top", [-.3, .95], 0, false, [.62, .42]),
					arm("m", "over")
				]
			}
		],
		back: lean([
			{
				m: {
					h: [1, -14],
					out: 1
				},
				o: {
					h: [-4, -12],
					st: true
				},
				ops: [
					bow("under", [.3, .95], 1.5, true, void 0, true),
					arm("o", "over", { clip: "out" }),
					arm("m", "over", { clip: "out" })
				]
			},
			{
				m: {
					h: [3, -21.5],
					out: 1
				},
				o: {
					h: [-5.5, -24],
					st: true
				},
				bob: -.2,
				ops: BB([.5, .87], 3, false, void 0, true)
			},
			{
				m: {
					h: [5, -23.5],
					out: 1
				},
				o: {
					h: [-6.8, -28],
					st: true
				},
				bob: -.3,
				ops: BB([.6, .8], 6, false)
			},
			{
				m: {
					h: [6, -24.5],
					out: 1
				},
				o: {
					h: [-7.3, -29.5],
					st: true
				},
				bob: -.3,
				ops: BB([.7, .71], 9, false)
			},
			{
				m: {
					h: [11, -24.5],
					out: 1
				},
				o: {
					h: [-7.3, -29.5],
					st: true
				},
				bob: -.2,
				ops: BB([.7, .71], 0, false, F_FULL_B)
			},
			{
				m: {
					h: [10, -21],
					out: 1
				},
				o: {
					h: [-7, -28.5],
					st: true
				},
				ops: BB([.7, .71], 0, false, F_FULL_B)
			},
			{
				m: {
					h: [1, -14],
					out: 1
				},
				o: {
					h: [-4, -12],
					st: true
				},
				ops: [
					bow("under", [.3, .95], 0, false, [-.5, -.4], true),
					arm("o", "over", { clip: "out" }),
					arm("m", "over", { clip: "out" })
				]
			}
		])
	};
	var STF = (a, mg = 0) => [
		arm("o", "over"),
		arm("m", "over"),
		wpn("over", a, {
			mg,
			wrap: true
		})
	];
	var STB = (a, mg = 0) => [
		wpn("under", a, { mg }),
		arm("o", "over"),
		arm("m", "over")
	];
	var sfs = (L, d, Lf, Lb, sc, w0, w1) => ({
		t: "staffFS",
		L,
		d,
		Lf,
		Lb,
		sc,
		w0,
		w1
	});
	var STAFF = {
		front: [
			{
				...IDLE_F,
				ops: STF(0, -1.9)
			},
			{
				m: {
					h: [-12.5, -21],
					out: -1
				},
				o: {
					h: [11.5, -15],
					st: true
				},
				glow: .4,
				bob: -.3,
				ops: STF(.05)
			},
			{
				m: {
					h: [-11.5, -27],
					out: -1
				},
				o: {
					h: [11, -17],
					st: true
				},
				glow: 1,
				bob: -.5,
				ops: STF(.12)
			},
			{
				m: {
					h: [-7, -17],
					st: true
				},
				o: {
					h: [11.5, -15],
					st: true
				},
				glow: 1,
				ops: [
					arm("o", "over"),
					arm("m", "over"),
					sfs("top", [.35, .94], 12, 4, 1.45, 2.4, 3),
					wrapOp("top", PI - .36)
				]
			},
			{
				m: {
					h: [-7, -17.5],
					st: true
				},
				o: {
					h: [11.5, -15],
					st: true
				},
				glow: .6,
				ops: [
					arm("o", "over"),
					arm("m", "over"),
					sfs("top", [.33, .94], 11, 4, 1.35, 2.4, 2.9),
					wrapOp("top", PI - .34)
				]
			},
			{
				m: {
					h: [-10.5, -15],
					st: true
				},
				o: {
					h: [11.8, -12],
					st: true
				},
				glow: .3,
				ops: STF(0, -1)
			},
			{
				...IDLE_F,
				ops: STF(0, -1.9)
			}
		],
		back: lean([
			{
				...IDLE_B,
				ops: STB(0, -1.9)
			},
			{
				m: {
					h: [12.5, -21],
					out: 1
				},
				o: {
					h: [-11.5, -15],
					st: true
				},
				glow: .4,
				bob: -.3,
				ops: STB(-.05)
			},
			{
				m: {
					h: [11.5, -27],
					out: 1
				},
				o: {
					h: [-11, -17],
					st: true
				},
				glow: 1,
				bob: -.5,
				ops: STB(-.12)
			},
			{
				m: {
					h: [9.5, -25],
					out: 1
				},
				o: {
					h: [-11.5, -15],
					st: true
				},
				glow: 1,
				ops: [
					sfs("under", [-.3, -.95], 15, 3, .8, 2.2, 1.6),
					arm("o", "over"),
					arm("m", "over")
				]
			},
			{
				m: {
					h: [9.5, -25.5],
					out: 1
				},
				o: {
					h: [-11.5, -15],
					st: true
				},
				glow: .6,
				ops: [
					sfs("under", [-.28, -.96], 14, 3, .8, 2.2, 1.6),
					arm("o", "over"),
					arm("m", "over")
				]
			},
			{
				m: {
					h: [11, -15],
					st: true
				},
				o: {
					h: [-11.8, -12],
					st: true
				},
				glow: .3,
				ops: STB(0, -1)
			},
			{
				...IDLE_B,
				ops: STB(0, -1.9)
			}
		])
	};
	var GD_F = {
		m: {
			h: [-4, -16.5],
			out: "down"
		},
		o: {
			h: [4.5, -16],
			out: "down"
		}
	};
	var GD_B = {
		m: {
			h: [2.5, -15],
			out: 1
		},
		o: {
			h: [-3, -14.5],
			out: -1
		}
	};
	var oOut = arm("o", "over", { clip: "out" });
	({ ...GD_F }), arm("o", "over"), arm("m", "over"), GD_F.o, arm("m", "over"), arm("o", "over"), GD_F.o, arm("m", "over"), arm("o", "over"), arm("o", "over"), arm("m", "top", { big: 1.4 }), arm("o", "over"), arm("m", "top", { big: 2 }), arm("o", "over"), arm("m", "top", { big: 1.75 }), { ...GD_F }, arm("o", "over"), arm("m", "over"), lean([
		{
			...GD_B,
			ops: [oOut, arm("m", "over", { clip: "out" })]
		},
		{
			m: {
				h: [9.8, -12],
				out: 1
			},
			o: GD_B.o,
			bob: -.2,
			ops: [oOut, arm("m", "over", { big: 1.1 })]
		},
		{
			m: {
				h: [9, -17],
				out: 1
			},
			o: GD_B.o,
			bob: -.3,
			ops: [oOut, arm("m", "over")]
		},
		{
			m: {
				h: [9.3, -27],
				st: true
			},
			o: {
				h: [-3, -14.5],
				out: -1
			},
			ops: [oOut, arm("m", "over")]
		},
		{
			m: {
				h: [8.9, -29],
				st: true
			},
			o: {
				h: [-3, -14.5],
				out: -1
			},
			liftL: 1,
			ops: [oOut, arm("m", "over")]
		},
		{
			m: {
				h: [9, -28.5],
				st: true
			},
			o: {
				h: [-3, -14.5],
				out: -1
			},
			ops: [oOut, arm("m", "over")]
		},
		{
			...GD_B,
			ops: [oOut, arm("m", "over", { clip: "out" })]
		}
	]);
	/** 火器在持弓手上的方向與縮短：正面指向鏡頭（往下、縮短），背面指向遠處（往上，被身體擋住只露槍口）。 */
	var GUN_A = {
		front: PI - .55,
		back: -.45
	};
	/** QK-5c（美術 PM QK-5 檢查第 4 節第 2 題）：正面（朝南）火器整把放大 1.3 倍（長 0.55×1.3、寬 ×1.3），讓槍身看得出來。 */
	var GUN_FRONT_ZOOM = 1.3;
	var GUN_S = {
		front: .55 * GUN_FRONT_ZOOM,
		back: .8
	};
	var GUN_W = {
		front: GUN_FRONT_ZOOM,
		back: 1
	};
	/** 弓那組換成火器：拉弦的手、弓弦拿掉；第 2～3 格持平（同第 1 格舉起的手），命中、收招、回位照放箭格。 */
	function gunOf(view) {
		const src = BOW[view];
		const L = view === "front" ? "top" : "under";
		const ops = (i) => {
			const g = wpn(L, GUN_A[view], {
				on: "o",
				s: i === 0 || i === 6 ? GUN_S[view] * .8 : GUN_S[view],
				wd: GUN_W[view]
			});
			return view === "front" ? [
				arm("o", "top"),
				g,
				arm("m", i === 6 ? "over" : "top")
			] : [
				g,
				arm("o", "over", { clip: "out" }),
				arm("m", "over", { clip: "out" })
			];
		};
		return src.map((f, i) => {
			const hold = i === 2 || i === 3 ? src[1] : f;
			return {
				...f,
				m: hold.m,
				o: hold.o,
				ops: ops(i)
			};
		});
	}
	gunOf("front"), gunOf("back");
	/** 法杖那組換成手上的武器：杖頭往前（staffFS）那兩格改畫主手武器（同方向、縮短 0.55），其他格照法杖（武器用 w 畫）。 */
	function castOf(view) {
		return STAFF[view].map((f) => ({
			...f,
			ops: f.ops.map((o) => o.t === "staffFS" ? wpn(o.L, Math.atan2(o.d[0], -o.d[1]), { s: .55 }) : o)
		}));
	}
	castOf("front"), castOf("back");
	//#endregion
	//#region client/src/render/weaponIcon.ts
	/** 量外框用的暫時畫布：虛擬大小與解析度倍率（武器最長約 60 個虛擬單位，頭放大後更長）。 */
	var WORK = 160;
	var WORK_RES = 3;
	/** 外框離圖示邊緣的留白（兩側各 10％ → 外框的長邊佔圖示 80％）。 */
	var PAD = .1;
	/** 28px 圖示上的墨線寬（CSS 像素；其他尺寸等比）。墨線的基本寬 0.85 個虛擬單位。 */
	var LINE_PX = 1.2;
	var BASE_LINE = .85;
	/** 頭部放大倍率（斧、錘、錘矛、鐮刀、杖頭）。 */
	var HEAD_SCALE = 1.5;
	/** 內部解析度倍率（canvas 實際像素 ＝ 邊長 × 2）。 */
	var DPR = 2;
	/** 槍弩的槍口朝 +x（畫的時候往右），要逆時針轉 45° 才朝右上；其餘（刃、柄、杖）朝上，順時針轉 45°。 */
	var MUZZLE_RIGHT = /* @__PURE__ */ new Set([
		"pistol",
		"shotgun",
		"longgun",
		"crossbow"
	]);
	/** 斜放的角度（弧度）：手槍不斜放（側面 L 形）、拳套正面直立（指虎，3T-4c）；其餘槍弩 -45°（槍口朝右上），其餘 +45°（刃、柄朝右上）。 */
	var iconAngle = (kind) => kind === "pistol" || kind === "fist" ? 0 : MUZZLE_RIGHT.has(kind) ? -Math.PI / 4 : Math.PI / 4;
	function drawIcon(ctx, item, mode) {
		ctx.rotate(iconAngle(item.kind));
		withShadeDir(ctx, 1, () => withIconMode(ctx, mode, () => drawInkWeaponAlone(ctx, item, itemColors)));
	}
	/** 在暫時畫布上畫一次量出外框（只量，不顯示）。 */
	function measure(item) {
		const canvas = document.createElement("canvas");
		canvas.width = 480;
		canvas.height = 480;
		const ctx = canvas.getContext("2d", { willReadFrequently: true });
		if (ctx === null) return null;
		ctx.scale(WORK_RES, WORK_RES);
		ctx.translate(WORK / 2, WORK / 2);
		drawIcon(ctx, item, {
			lineScale: 1,
			headScale: HEAD_SCALE
		});
		const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
		let x0 = canvas.width;
		let y0 = canvas.height;
		let x1 = -1;
		let y1 = -1;
		for (let y = 0; y < canvas.height; y += 1) for (let x = 0; x < canvas.width; x += 1) {
			if ((data[(y * canvas.width + x) * 4 + 3] ?? 0) < 8) continue;
			if (x < x0) x0 = x;
			if (x > x1) x1 = x;
			if (y < y0) y0 = y;
			if (y > y1) y1 = y;
		}
		if (x1 < 0) return null;
		return {
			cx: (x0 + x1 + 1) / 2 / WORK_RES - WORK / 2,
			cy: (y0 + y1 + 1) / 2 / WORK_RES - WORK / 2,
			side: Math.max(x1 - x0 + 1, y1 - y0 + 1) / WORK_RES
		};
	}
	var cache = /* @__PURE__ */ new Map();
	/** 同上，直接給裝備造型（開發用一覽頁不經過後端的武器對照表）。 */
	function weaponItemIconCanvas(item, px = 28) {
		if (typeof document === "undefined") return null;
		const key = `${px}|${item.kind}|${item.material ?? ""}|${item.element ?? ""}|${item.form ?? ""}`;
		const hit = cache.get(key);
		if (hit !== void 0) return hit;
		const box = measure(item);
		if (box === null) return null;
		const size = px * DPR;
		const canvas = document.createElement("canvas");
		canvas.width = size;
		canvas.height = size;
		const ctx = canvas.getContext("2d");
		if (ctx === null) return null;
		const k = size * (1 - 2 * PAD) / box.side;
		const lineScale = LINE_PX * (px / 28) * DPR / (k * BASE_LINE);
		ctx.translate(size / 2, size / 2);
		ctx.scale(k, k);
		ctx.translate(-box.cx, -box.cy);
		drawIcon(ctx, item, {
			lineScale,
			headScale: HEAD_SCALE
		});
		cache.set(key, canvas);
		return canvas;
	}
	//#endregion
	//#region C:/Users/tobby/AppData/Local/Temp/claude/ef4681d56bbe6415/f83e7b9c-9c17-448b-a847-8d7dc0627b4d/scratchpad/ob-samples-v2/live/entry.ts
	window.OBLive = { weaponIcon(look, px = 20) {
		return weaponItemIconCanvas({
			kind: pairedPart(look.kind) ?? look.kind,
			material: look.material,
			...look.element ? { element: look.element } : {},
			...look.form ? { form: look.form } : {}
		}, px);
	} };
	//#endregion
})();
