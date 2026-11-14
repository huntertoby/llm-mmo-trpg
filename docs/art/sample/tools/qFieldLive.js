// 自動產生，不要手改：現行戰場地形的畫法（client/src/render/terrainArt.ts drawTile、objectArt.ts drawObject、lethalMarks.ts、heightShapes.ts、heightMark.ts、
// minMark.ts、battle/elevation.ts、battle/glossary.ts HIGHLIGHT），用 vite 的 lib 模式打包成 IIFE，minify 關閉，掛到 window.QFieldLive。
// 只給 GB A5 熔心坑戰場樣張（giant-boss.html ?part=pit…）用，和實機同一份程式。重新產生：做法見 docs/art/GB巨型頭目-美術.md 3.8。
(function() {
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/material.ts
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/artPalette.ts
	var PAL = {
		stone: "#8e8a80",
		stoneGap: "#6c685f",
		grass: "#6b9a4b",
		grassLight: "#8dbb62",
		grassDark: "#4f7a35",
		dirt: "#9a7650",
		dirtLight: "#b48f66",
		dirtDark: "#76593a",
		wallTop: "#5d554e",
		wallLine: "#3d3732",
		wallFace: "#2e2925",
		chasm: "#0d0d14",
		chasmLip: "#3b3742",
		lava: "#e2531d",
		lavaCrust: "#7c2a14",
		lavaGlow: "#ffd04a",
		deep: "#1c4a7c",
		deepLight: "#4f86c0",
		water: "#3a86d8",
		ice: "#d4f0ff",
		oil: "#211a10",
		fire: "#ff6a1a",
		poison: "#74c23c",
		smoke: "#dcdfe6",
		holy: "#ffe58a",
		darkness: "#3b1f4f",
		wood: "#b77f3f",
		woodDark: "#6e4620",
		woodMid: "#8f5f2c",
		rock: "#a8a49a",
		rockDark: "#6c685f",
		cliff: "#5b4a3a",
		iceWall: "#9fe0ff",
		thorn: "#4f7a2a",
		bush: "#3f6e2a"
	};
	Object.fromEntries(Object.entries(MATERIAL).map(([id, c]) => [id, id === "silver" ? {
		c,
		shine: true
	} : { c }]));
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/color.ts
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
	function mix(a, b, t) {
		if (!HEX.test(a) || !HEX.test(b)) return a;
		const [r1, g1, b1] = hexRgb(a);
		const [r2, g2, b2] = hexRgb(b);
		const m = (x, y) => Math.round(x * (1 - t) + y * t);
		return `#${(m(r1, r2) << 16 | m(g1, g2) << 8 | m(b1, b2)).toString(16).padStart(6, "0")}`;
	}
	/** 把亮度乘上 `f`，回傳 CSS 顏色（`rgb(r,g,b)`，`f` 大於 1 變亮）。 */
	function shade(h, f) {
		const [r, g, b] = hexRgb(h);
		const c = (v) => Math.max(0, Math.min(255, Math.round(v)));
		return `rgb(${c(r * f)},${c(g * f)},${c(b * f)})`;
	}
	function rgba(h, a) {
		const [r, g, b] = hexRgb(h);
		return `rgba(${r},${g},${b},${a})`;
	}
	/** Pixi 的數字顏色 → `#rrggbb`。 */
	function numToHex(n) {
		return `#${(n & 16777215).toString(16).padStart(6, "0")}`;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/artDraw.ts
	var TAU = Math.PI * 2;
	function roundRect(ctx, x, y, w, h, r) {
		ctx.beginPath();
		ctx.roundRect(x, y, w, h, r);
	}
	function shadowEllipse(ctx, cx, cy, rx, ry) {
		ctx.fillStyle = "rgba(0,0,0,0.28)";
		ctx.beginPath();
		ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
		ctx.fill();
	}
	/** 危險記號（會爆的油桶，四區共用；docs/art/四區移植需求.md 第 1 節）：黃底黑框三角＋驚嘆號，中心在 (cx, cy)。 */
	function hazardMark(ctx, cx, cy, s = 7) {
		ctx.beginPath();
		ctx.moveTo(cx, cy - s);
		ctx.lineTo(cx + s, cy + s * .8);
		ctx.lineTo(cx - s, cy + s * .8);
		ctx.closePath();
		ctx.fillStyle = "#ffd23a";
		ctx.fill();
		ctx.lineWidth = 1.6;
		ctx.strokeStyle = "#1a1208";
		ctx.stroke();
		ctx.fillStyle = "#1a1208";
		ctx.fillRect(cx - 1, cy - s * .45, 2, s * .65);
		ctx.fillRect(cx - 1, cy + s * .32, 2, 2);
	}
	/** 發光線（裝飾光：裂縫熔岩光、晶能線）：`path` 只負責 moveTo／lineTo，畫完還原陰影設定。 */
	function glowLine(ctx, color, width, blur, path) {
		ctx.save();
		ctx.shadowColor = color;
		ctx.shadowBlur = blur;
		ctx.strokeStyle = color;
		ctx.lineWidth = width;
		ctx.lineCap = "round";
		ctx.beginPath();
		path();
		ctx.stroke();
		ctx.restore();
	}
	/** 實心小圓點。 */
	function dot(ctx, x, y, r, fill) {
		ctx.fillStyle = fill;
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU);
		ctx.fill();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/artRandom.ts
	function hash(x, y, salt) {
		let h = 2166136261 ^ salt;
		h = Math.imul(h ^ x + 374761393, 16777619);
		h = Math.imul(h ^ y + 668265263, 16777619);
		h ^= h >>> 13;
		h = Math.imul(h, 1274126177);
		return (h ^ h >>> 16) >>> 0;
	}
	/** 回傳 [0,1) 的確定性亂數產生器。 */
	function rng(x, y, salt) {
		return seeded(hash(x, y, salt));
	}
	/** 直接以整數種子起算的確定性亂數（mulberry32）。區域插畫（6F-ART1）用，與樣張 `docs/art/sample/regionArt.js` 的 `rng(seed)` 同一序列。 */
	function seeded(seed) {
		let a = seed | 0;
		return () => {
			a = a + 1831565813 | 0;
			let t = Math.imul(a ^ a >>> 15, 1 | a);
			t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
			return ((t ^ t >>> 14) >>> 0) / 4294967296;
		};
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/arcaneTerrain.ts
	var T$14 = 52;
	/** 魔導樞市色票（需求第 4 節）。 */
	var ARCANE = {
		plate: "#4a4238",
		coal: "#2a241e",
		brass: "#b08a4a",
		energy: "#4ae0d0",
		rune: "#e8a040",
		iron: "#5a5248",
		coolant: "#2a7a9a",
		outline: "#1c1712"
	};
	/** 晶能線的參數：2 寬、模糊 6；顏色用半透明的晶能青（比導電提示、技能特效暗）。 */
	var ARCANE_LINE = {
		width: 2,
		blur: 6,
		alpha: .55
	};
	/** 這一格鐵板有沒有晶能線（約 1/3 的格子，格子座標雜湊，固定）。 */
	function arcaneLineAt(x, y) {
		return hash(x, y, 401) % 3 === 0;
	}
	/** 鉚釘鐵板：四角黃銅鉚釘；約 1/3 的格子有一條轉折的晶能線。 */
	function arcaneStone(ctx, s) {
		const r = rng(s.x, s.y, 402);
		ctx.fillStyle = shade(ARCANE.plate, .94 + r() * .12);
		ctx.fillRect(0, 0, T$14, T$14);
		ctx.strokeStyle = ARCANE.coal;
		ctx.lineWidth = 2;
		ctx.strokeRect(1, 1, 50, 50);
		ctx.fillStyle = "rgba(255,255,255,0.08)";
		ctx.fillRect(3, 3, 46, 2);
		for (const [dx, dy] of [
			[5, 5],
			[47, 5],
			[5, 47],
			[47, 47]
		]) {
			dot(ctx, dx, dy, 2, ARCANE.brass);
			dot(ctx, dx - .6, dy - .6, .8, "rgba(255,255,255,0.5)");
		}
		if (arcaneLineAt(s.x, s.y)) {
			const horiz = r() < .5;
			glowLine(ctx, rgba(ARCANE.energy, ARCANE_LINE.alpha), ARCANE_LINE.width, ARCANE_LINE.blur, () => {
				if (horiz) {
					ctx.moveTo(0, T$14 / 2);
					ctx.lineTo(T$14 * .4, T$14 / 2);
					ctx.lineTo(T$14 * .5, T$14 * .38);
					ctx.lineTo(T$14, T$14 * .38);
				} else {
					ctx.moveTo(T$14 / 2, 0);
					ctx.lineTo(T$14 / 2, T$14 * .6);
					ctx.lineTo(T$14 * .62, T$14 * .7);
					ctx.lineTo(T$14 * .62, T$14);
				}
			});
		}
	}
	/** 鐵格柵下的苔草。 */
	function arcaneGrass(ctx, s) {
		const r = rng(s.x, s.y, 403);
		ctx.fillStyle = shade("#3e4a34", .95 + r() * .1);
		ctx.fillRect(0, 0, T$14, T$14);
		ctx.lineWidth = 1.5;
		ctx.lineCap = "round";
		const n = 6 + Math.floor(r() * 4);
		for (let i = 0; i < n; i++) {
			const x = 5 + r() * 42;
			const y = 8 + r() * 39;
			ctx.strokeStyle = r() < .55 ? "#7aa060" : "#4a6a3a";
			ctx.beginPath();
			ctx.moveTo(x, y);
			ctx.quadraticCurveTo(x - 1, y - 5, x - 4, y - 8);
			ctx.moveTo(x, y);
			ctx.quadraticCurveTo(x + 1, y - 5, x + 4, y - 9);
			ctx.stroke();
		}
		ctx.strokeStyle = ARCANE.coal;
		ctx.lineWidth = 2;
		ctx.beginPath();
		for (let k = 6; k < T$14; k += 10) {
			ctx.moveTo(k, 0);
			ctx.lineTo(k, T$14);
		}
		ctx.stroke();
		ctx.strokeRect(1, 1, 50, 50);
	}
	/** 煤渣地：黑點加少量黃銅屑。 */
	function arcaneDirt(ctx, s) {
		const r = rng(s.x, s.y, 404);
		ctx.fillStyle = shade("#3a3430", .94 + r() * .12);
		ctx.fillRect(0, 0, T$14, T$14);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.07)";
			ctx.beginPath();
			ctx.ellipse(r() * T$14, r() * T$14, 8 + r() * 10, 5 + r() * 7, r() * Math.PI * 2, 0, Math.PI * 2);
			ctx.fill();
		}
		for (let i = 0; i < 16; i++) {
			ctx.fillStyle = r() < .4 ? "rgba(176,138,74,0.4)" : "rgba(10,8,6,0.6)";
			ctx.fillRect(r() * T$14, r() * T$14, 1.8, 1.8);
		}
	}
	/** 鐵壁：分板、鉚釘；南鄰不是牆時畫深色立面，下段一條黃銅管線（比單位高）。 */
	function arcaneWall(ctx, s) {
		ctx.fillStyle = ARCANE.iron;
		ctx.fillRect(0, 0, T$14, T$14);
		ctx.fillStyle = "rgba(255,255,255,0.14)";
		ctx.fillRect(0, 0, T$14, 3);
		ctx.strokeStyle = "rgba(0,0,0,0.55)";
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		for (const k of [T$14 * .33, T$14 * .66]) {
			ctx.moveTo(k, 0);
			ctx.lineTo(k, T$14);
		}
		ctx.moveTo(0, T$14 / 2);
		ctx.lineTo(T$14, T$14 / 2);
		ctx.stroke();
		for (const y of [6, 32]) for (const k of [
			8,
			T$14 / 2,
			44
		]) dot(ctx, k, y, 1.8, ARCANE.brass);
		if (s.wallFace) {
			ctx.fillStyle = "#3a342c";
			ctx.fillRect(0, 40, T$14, 12);
			ctx.fillStyle = "rgba(0,0,0,0.3)";
			ctx.fillRect(0, 40, T$14, 2);
			ctx.fillStyle = ARCANE.brass;
			ctx.fillRect(0, 44, T$14, 5);
			ctx.fillStyle = "rgba(255,255,255,0.3)";
			ctx.fillRect(0, 44, T$14, 1.5);
		}
	}
	/** 崖緣：和其他地形相接的那一邊是鐵框，邊緣一條煤黑的崖線。 */
	function shaftLip(ctx, s) {
		ctx.fillStyle = ARCANE.iron;
		if (s.lip.n) ctx.fillRect(0, 0, T$14, 9);
		if (s.lip.s) ctx.fillRect(0, 47, T$14, 5);
		if (s.lip.w) ctx.fillRect(0, 0, 5, T$14);
		if (s.lip.e) ctx.fillRect(47, 0, 5, T$14);
		ctx.fillStyle = "rgba(0,0,0,0.5)";
		if (s.lip.n) ctx.fillRect(0, 9, T$14, 2);
		if (s.lip.n) for (const k of [
			6,
			T$14 / 2,
			46
		]) dot(ctx, k, 4.5, 1.5, ARCANE.brass);
	}
	/** 機械豎井：深色井底，兩條黃銅管線，幾個晶能光點；邊緣有崖線。 */
	function arcaneChasm(ctx, s) {
		const r = rng(s.x, s.y, 405);
		const g = ctx.createLinearGradient(0, 0, 0, T$14);
		g.addColorStop(0, "#14181a");
		g.addColorStop(1, "#06080a");
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$14, T$14);
		ctx.strokeStyle = rgba(ARCANE.brass, .55);
		ctx.lineWidth = 3;
		ctx.beginPath();
		for (const k of [12, 40]) {
			ctx.moveTo(k, 0);
			ctx.lineTo(k, T$14);
		}
		ctx.stroke();
		for (let i = 0; i < 3; i++) dot(ctx, 8 + r() * 36, 20 + r() * 28, 1.6, rgba(ARCANE.energy, .7));
		shaftLip(ctx, s);
	}
	/** 熔爐槽：岩漿（紅橘）外圍是鐵框，四角鉚釘。 */
	function arcaneLava(ctx, s) {
		const r = rng(s.x, s.y, 406);
		ctx.fillStyle = "#e0400a";
		ctx.fillRect(0, 0, T$14, T$14);
		for (let i = 0; i < 4; i++) {
			const cx = r() * T$14;
			const cy = r() * T$14;
			const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 18);
			gg.addColorStop(0, "#ffb030");
			gg.addColorStop(1, rgba("#ffb030", 0));
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$14, T$14);
		}
		ctx.strokeStyle = ARCANE.iron;
		ctx.lineWidth = 4;
		ctx.strokeRect(2, 2, 48, 48);
		for (const [dx, dy] of [
			[5, 5],
			[47, 5],
			[5, 47],
			[47, 47]
		]) dot(ctx, dx, dy, 1.6, "#d8b070");
	}
	/** 冷卻槽：冰藍液體 #2a7a9a，外圍黃銅邊（每格一個槽，靠黃銅邊和格子區分；致命）。 */
	function arcaneIceHole(ctx, s) {
		const r = rng(s.x, s.y, 407);
		ctx.fillStyle = ARCANE.plate;
		ctx.fillRect(0, 0, T$14, T$14);
		roundRect(ctx, 4, 4, 44, 44, 10);
		ctx.fillStyle = ARCANE.coolant;
		ctx.fill();
		ctx.lineWidth = 3;
		ctx.strokeStyle = ARCANE.brass;
		ctx.stroke();
		ctx.strokeStyle = "rgba(255,255,255,0.3)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		const wy = 16 + r() * 18;
		ctx.moveTo(12, wy);
		ctx.quadraticCurveTo(20, wy - 4, 28, wy);
		ctx.stroke();
	}
	/** 魔導樞市的地形畫法（地形 ID → 畫法）；需求第 4 節七種地形。 */
	var ARCANE_TERRAIN = {
		stone: arcaneStone,
		grass: arcaneGrass,
		dirt: arcaneDirt,
		wall: arcaneWall,
		chasm: arcaneChasm,
		lava: arcaneLava,
		ice_hole: arcaneIceHole
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/hazardTerrainArt.ts
	var T$13 = 52;
	/** 雲海的色票：底下的淡藍、雲團的白與陰影（照大世界圖的雲層）。 */
	var CLOUD_SEA = {
		deep: "#8fa9c8",
		shallow: "#c4d4e6",
		tint: [
			250,
			250,
			253
		],
		shade: [
			168,
			182,
			210
		]
	};
	/** 一團雲（`cloudPuff`）：左上偏亮、邊緣羽化到透明。 */
	function cloudPuff(ctx, x, y, r, a, tint, shadeC, sy) {
		ctx.save();
		ctx.translate(x, y);
		ctx.scale(1, sy);
		ctx.translate(-x, -y);
		const g = ctx.createRadialGradient(x - r * .25, y - r * .45, r * .1, x, y, r);
		const mid = tint.map((v, i) => Math.round(v * .6 + (shadeC[i] ?? 0) * .4)).join(",");
		g.addColorStop(0, `rgba(${tint.join(",")},${a})`);
		g.addColorStop(.55, `rgba(${mid},${a})`);
		g.addColorStop(.9, `rgba(${shadeC.join(",")},${a * .9})`);
		g.addColorStop(1, `rgba(${shadeC.join(",")},0)`);
		ctx.fillStyle = g;
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU);
		ctx.fill();
		ctx.restore();
	}
	/** 一格的雲團（格子座標雜湊；`ox`、`oy` 是這一格相對於畫布的位移，鄰格用 ±T）。 */
	function puffsOf(ctx, x, y, ox, oy, salt) {
		const r = rng(x, y, salt);
		const count = 5 + Math.floor(r() * 3);
		const items = [];
		for (let i = 0; i < count; i++) {
			const px = ox + i / count * T$13 + (r() - .5) * 14;
			const py = oy + 8 + r() * 36;
			const rad = 11 + r() * 9;
			items.push([
				px,
				py,
				rad,
				.62 + r() * .2
			]);
		}
		items.sort((p, q) => p[1] - q[1]);
		for (const [px, py, rad, a] of items) cloudPuff(ctx, px, py, rad, a, CLOUD_SEA.tint, CLOUD_SEA.shade, .7);
	}
	/** 哪些鄰格也是雲海（`lip` 為假＝同種地形）；斜鄰看兩邊都不是崖。 */
	function cloudNeighbors(s) {
		const n = !s.lip.n;
		const so = !s.lip.s;
		const w = !s.lip.w;
		const e = !s.lip.e;
		const out = [];
		if (n && w) out.push([-1, -1]);
		if (n) out.push([0, -1]);
		if (n && e) out.push([1, -1]);
		if (w) out.push([-1, 0]);
		if (e) out.push([1, 0]);
		if (so && w) out.push([-1, 1]);
		if (so) out.push([0, 1]);
		if (so && e) out.push([1, 1]);
		return out;
	}
	/** 雲海底圖（不含崖緣）：淡藍底 → 鄰格的雲團（接縫）→ 本格的雲團。 */
	function drawCloudSea(ctx, s, salt) {
		const r = rng(s.x, s.y, salt);
		const g = ctx.createLinearGradient(0, 0, 0, T$13);
		g.addColorStop(0, shade(CLOUD_SEA.deep, .96 + r() * .08));
		g.addColorStop(1, CLOUD_SEA.shallow);
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$13, T$13);
		for (let i = 0; i < 2; i++) {
			const cx = r() * T$13;
			const cy = r() * T$13;
			const rg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14 + r() * 8);
			rg.addColorStop(0, rgba("#6f8db4", .5));
			rg.addColorStop(1, rgba("#6f8db4", 0));
			ctx.fillStyle = rg;
			ctx.fillRect(0, 0, T$13, T$13);
		}
		for (const [dx, dy] of cloudNeighbors(s)) puffsOf(ctx, s.x + dx, s.y + dy, dx * T$13, dy * T$13, salt);
		puffsOf(ctx, s.x, s.y, 0, 0, salt);
	}
	/** 熔岩的色票（照荒原區域插畫的熔岩河）。 */
	var LAVA = {
		base: "#c2410c",
		bright: "#ff7a1a",
		hot: "#ffd36b",
		crust: "#2a1610",
		crustEdge: "#140a06"
	};
	/** 熔岩的岩殼塊：不規則的深色板塊、邊緣一圈更深的裂紋。 */
	function crustPlate(ctx, cx, cy, rad, r, fill, edge) {
		ctx.beginPath();
		const n = 7;
		for (let k = 0; k < n; k++) {
			const a = k / n * TAU;
			const rr = rad * (.7 + r() * .4);
			const px = cx + Math.cos(a) * rr;
			const py = cy + Math.sin(a) * rr * .75;
			if (k === 0) ctx.moveTo(px, py);
			else ctx.lineTo(px, py);
		}
		ctx.closePath();
		ctx.fillStyle = fill;
		ctx.fill();
		ctx.strokeStyle = edge;
		ctx.lineWidth = 1.2;
		ctx.lineJoin = "round";
		ctx.stroke();
	}
	/** 冷卻黑殼：靠岸（`lip`）那一邊一圈凹凸的黑殼，內側透一點熱光。 */
	function cooledRim(ctx, r, side) {
		const horizontal = side === "n" || side === "s";
		const depth = 5;
		ctx.fillStyle = LAVA.crust;
		ctx.beginPath();
		const steps = 7;
		for (let i = 0; i <= steps; i++) {
			const t = i / steps * T$13;
			const d = depth + r() * 3;
			const px = horizontal ? t : side === "w" ? d : T$13 - d;
			const py = horizontal ? side === "n" ? d : T$13 - d : t;
			if (i === 0) ctx.moveTo(horizontal ? 0 : side === "w" ? 0 : T$13, horizontal ? side === "n" ? 0 : T$13 : 0);
			ctx.lineTo(px, py);
		}
		ctx.lineTo(horizontal ? T$13 : side === "w" ? 0 : T$13, horizontal ? side === "n" ? 0 : T$13 : T$13);
		ctx.closePath();
		ctx.fill();
		ctx.strokeStyle = rgba(LAVA.hot, .35);
		ctx.lineWidth = 1;
		ctx.stroke();
	}
	/** 熔岩底圖：發光底 → 熱紋 → 岩殼塊 → 冷卻黑殼。`tone` 微調底色（荒原更暗紅）。 */
	function drawLavaBase(ctx, s, salt, tone = 1) {
		const r = rng(s.x, s.y, salt);
		ctx.fillStyle = shade(LAVA.base, tone * (.94 + r() * .12));
		ctx.fillRect(0, 0, T$13, T$13);
		const glows = 2 + Math.floor(r() * 2);
		for (let i = 0; i < glows; i++) {
			const cx = r() * T$13;
			const cy = r() * T$13;
			const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 16 + r() * 10);
			gg.addColorStop(0, rgba(LAVA.bright, .9));
			gg.addColorStop(1, rgba(LAVA.bright, 0));
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$13, T$13);
		}
		ctx.strokeStyle = rgba(LAVA.hot, .8);
		ctx.lineWidth = 1.6;
		ctx.lineCap = "round";
		for (let i = 0; i < 2; i++) {
			const x0 = r() * T$13;
			const y0 = 8 + i * 22 + r() * 10;
			ctx.beginPath();
			ctx.moveTo(x0 - 14, y0);
			ctx.bezierCurveTo(x0 - 6, y0 - 5, x0 + 2, y0 + 5, x0 + 12, y0 - 2);
			ctx.stroke();
		}
		const crusts = 2 + Math.floor(r() * 2);
		for (let i = 0; i < crusts; i++) crustPlate(ctx, 8 + r() * 36, 8 + r() * 36, 4 + r() * 4, r, rgba(LAVA.crust, .8), rgba(LAVA.crustEdge, .85));
		ctx.strokeStyle = rgba(LAVA.crustEdge, .7);
		ctx.lineWidth = 1.3;
		ctx.lineCap = "round";
		for (let i = 0; i < 2; i++) {
			let px = r() * T$13;
			let py = r() * T$13;
			ctx.beginPath();
			ctx.moveTo(px, py);
			for (let k = 0; k < 3; k++) {
				px += (r() - .5) * 16;
				py += (r() - .5) * 16;
				ctx.lineTo(px, py);
			}
			ctx.stroke();
		}
		if (s.lip.n) cooledRim(ctx, r, "n");
		if (s.lip.s) cooledRim(ctx, r, "s");
		if (s.lip.w) cooledRim(ctx, r, "w");
		if (s.lip.e) cooledRim(ctx, r, "e");
	}
	/** 羽化漸層的停點：（離內側的比例, 透明度倍率），近似 smoothstep，看不出漸層從哪裡開始。 */
	var FEATHER_STOPS = [
		[0, 1],
		[.3, .84],
		[.6, .4],
		[1, 0]
	];
	/**
	* 羽化的填色（6V-2b）：中間實心，岸那一側（`same` 為假）在 `f` 像素內由 `alpha` 淡到 0；兩個岸相接的角用 1/4 圓的放射漸層。
	* 各塊不重疊（不會有疊兩次變深的條紋）。
	*/
	function featherFill(ctx, same, f, color, alpha) {
		const x0 = same.w ? 0 : f;
		const y0 = same.n ? 0 : f;
		const x1 = same.e ? T$13 : T$13 - f;
		const y1 = same.s ? T$13 : T$13 - f;
		ctx.fillStyle = rgba(color, alpha);
		ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
		const stops = (g, inner) => {
			for (const [t, k] of FEATHER_STOPS) g.addColorStop(inner === 1 ? 1 - t : t, rgba(color, alpha * k));
		};
		const band = (gx0, gy0, gx1, gy1, rect) => {
			const g = ctx.createLinearGradient(gx0, gy0, gx1, gy1);
			stops(g, 1);
			ctx.fillStyle = g;
			ctx.fillRect(rect[0], rect[1], rect[2], rect[3]);
		};
		if (!same.n) band(0, 0, 0, f, [
			x0,
			0,
			x1 - x0,
			f
		]);
		if (!same.s) band(0, T$13, 0, T$13 - f, [
			x0,
			T$13 - f,
			x1 - x0,
			f
		]);
		if (!same.w) band(0, 0, f, 0, [
			0,
			y0,
			f,
			y1 - y0
		]);
		if (!same.e) band(T$13, 0, T$13 - f, 0, [
			T$13 - f,
			y0,
			f,
			y1 - y0
		]);
		const corner = (cx, cy, rx, ry) => {
			const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, f);
			stops(g, 0);
			ctx.fillStyle = g;
			ctx.fillRect(rx, ry, f, f);
		};
		if (!same.n && !same.w) corner(f, f, 0, 0);
		if (!same.n && !same.e) corner(T$13 - f, f, T$13 - f, 0);
		if (!same.s && !same.e) corner(T$13 - f, T$13 - f, T$13 - f, T$13 - f);
		if (!same.s && !same.w) corner(f, T$13 - f, 0, T$13 - f);
	}
	/** 濕痕的顏色：岸那一側的地面壓深一階（羽化，邊緣淡到透明）。 */
	var WET = "#141e28";
	/** 水面：填滿格子，岸邊（鄰格不是水）一圈羽化的濕痕、水由實心淡到透明（6V-2b），細反光線。`color` 是區域的水色。 */
	function drawWaterFill(ctx, s, color) {
		const r = rng(s.x, s.y, 21);
		const same = s.surfSame;
		featherFill(ctx, same, 4, WET, .26);
		featherFill(ctx, same, 12, color, .86);
		const x0 = same.w ? 0 : 4;
		const y0 = same.n ? 0 : 4;
		const x1 = same.e ? T$13 : 48;
		const y1 = same.s ? T$13 : 48;
		const cx = x0 + 6 + r() * Math.max(1, x1 - x0 - 12);
		const cy = y0 + 6 + r() * Math.max(1, y1 - y0 - 12);
		const g = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14 + r() * 6);
		g.addColorStop(0, rgba(mix(color, "#000000", .2), .45));
		g.addColorStop(1, rgba(mix(color, "#000000", .2), 0));
		ctx.fillStyle = g;
		ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
		ctx.strokeStyle = "rgba(235,248,255,0.55)";
		ctx.lineWidth = 1;
		ctx.lineCap = "round";
		for (let i = 0; i < 2; i++) {
			const wx = x0 + 6 + r() * Math.max(1, x1 - x0 - 24);
			const wy = y0 + 8 + r() * Math.max(1, y1 - y0 - 16);
			ctx.beginPath();
			ctx.moveTo(wx, wy);
			ctx.lineTo(wx + 9 + r() * 6, wy - 1);
			ctx.stroke();
		}
	}
	/** 深水的色票（6V-2b：灰渡口的灰河；比荒原水面 `#45627a` 深一階）。 */
	/** 深水的色票（6V-2b：灰渡口的灰河；比荒原水面 `#45627a` 深一階）。 */
	var DEEP_WATER = {
		/** 岸邊的濕泥（深淵格本身沒有地面，羽化的水邊底下要有東西）。 */
		bank: "#4a4541",
		base: "#34495c",
		dark: "#16212c",
		ripple: "rgba(176,200,222,0.2)"
	};
	/** 一格深水的暗斑與波紋（只看格子座標雜湊；`ox`、`oy` 是這一格相對於畫布的位移，鄰格用 ±T，畫面才接得起來）。 */
	function deepFeatures(ctx, x, y, ox, oy) {
		const r = rng(x, y, 232);
		const cx = ox + r() * T$13;
		const cy = oy + r() * T$13;
		const rad = 20 + r() * 10;
		const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, rad);
		g.addColorStop(0, rgba(DEEP_WATER.dark, .32));
		g.addColorStop(1, rgba(DEEP_WATER.dark, 0));
		ctx.fillStyle = g;
		ctx.fillRect(cx - rad, cy - rad, rad * 2, rad * 2);
		if (r() < .6) {
			const wx = ox + r() * T$13 - 10;
			const wy = oy + 10 + r() * 32;
			const len = 30 + r() * 14;
			ctx.strokeStyle = DEEP_WATER.ripple;
			ctx.lineWidth = 1.2;
			ctx.lineCap = "round";
			ctx.beginPath();
			ctx.moveTo(wx, wy);
			ctx.quadraticCurveTo(wx + len / 2, wy - 3 - r() * 2, wx + len, wy);
			ctx.stroke();
		}
	}
	/**
	* 深水（6V-2b，`look.chasm_style: deep_water`）：只換畫法，地形仍是 `chasm`（致命判定不動）。
	* 濕泥岸 → 羽化的深灰藍水 → 一層暗色 → 暗斑與很淡的大波紋（鄰格也是深水時連鄰格的一起畫，格與格接得起來；
	* 慢慢飄的大波紋在 `surfaceAnim.terrainShimmer`）。不畫裂谷的崖緣與底部紅光。`lip` 為真的那一側是岸。
	*/
	function drawDeepWater(ctx, s) {
		const same = {
			n: !s.lip.n,
			s: !s.lip.s,
			w: !s.lip.w,
			e: !s.lip.e
		};
		if (s.lip.n || s.lip.s || s.lip.w || s.lip.e) {
			ctx.fillStyle = DEEP_WATER.bank;
			ctx.fillRect(0, 0, T$13, T$13);
			featherFill(ctx, same, 3, WET, .4);
		}
		featherFill(ctx, same, 12, DEEP_WATER.base, .97);
		const x0 = same.w ? 0 : 12;
		const y0 = same.n ? 0 : 12;
		const x1 = same.e ? T$13 : 40;
		const y1 = same.s ? T$13 : 40;
		ctx.save();
		ctx.beginPath();
		ctx.rect(x0, y0, x1 - x0, y1 - y0);
		ctx.clip();
		ctx.fillStyle = rgba(DEEP_WATER.dark, .18);
		ctx.fillRect(0, 0, T$13, T$13);
		for (const [dx, dy] of cloudNeighbors(s)) deepFeatures(ctx, s.x + dx, s.y + dy, dx * T$13, dy * T$13);
		deepFeatures(ctx, s.x, s.y, 0, 0);
		ctx.restore();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/ashenTerrain.ts
	var T$12 = 52;
	/** 灰燼荒原色票（需求第 2 節）。 */
	var ASH = {
		scorch: "#4a3a30",
		char: "#2a1e18",
		lavaGlow: "#ff6a1a",
		ruin: "#6a5e54",
		ruinTop: "#7a6e64",
		ruinFace: "#5a4e44",
		dryGrass: "#8a7a48",
		blade: "#b8a060",
		bladeLight: "#c8b070",
		ash: "#5a5450",
		ember: "#ff7a2a",
		outline: "#1c1712"
	};
	/** 裝飾光（裂縫熔岩光、餘燼點）出現的比例上限：同一張圖最多約 1/3 的格子有（規格 43.0 第 3 條）。 */
	var ASH_GLOW_RATE = 1 / 3;
	/** 裂谷底部紅光的最大透明度（需求第 2 節：≤ 0.3）。 */
	var ASH_RIFT_GLOW_ALPHA = .28;
	/** 這一格有沒有裝飾光（格子座標雜湊，固定）。 */
	function ashGlowAt(x, y, salt) {
		return rng(x, y, salt)() < ASH_GLOW_RATE;
	}
	/** 焦土裂地：深褐地面、黑斑、細灰點；部分格子一道細熔岩光裂縫（先畫 3 寬黑縫，再疊 1.4 寬、模糊 5 的橘光）。 */
	function ashStone(ctx, s) {
		const r = rng(s.x, s.y, 201);
		ctx.fillStyle = shade(ASH.scorch, .9 + r() * .2);
		ctx.fillRect(0, 0, T$12, T$12);
		for (let i = 0; i < 5; i++) dot(ctx, r() * T$12, r() * T$12, 3 + r() * 5, "rgba(0,0,0,0.18)");
		for (let i = 0; i < 6; i++) dot(ctx, r() * T$12, r() * T$12, 1, "rgba(200,180,160,0.25)");
		if (ashGlowAt(s.x, s.y, 202)) {
			let px = r() * T$12;
			let py = 0;
			const pts = [[px, py]];
			for (let i = 0; i < 5; i++) {
				px += (r() - .5) * 16;
				py += T$12 / 5;
				pts.push([px, py]);
			}
			const trace = () => {
				pts.forEach(([a, b], i) => i === 0 ? ctx.moveTo(a, b) : ctx.lineTo(a, b));
			};
			ctx.strokeStyle = "#140c08";
			ctx.lineWidth = 3;
			ctx.lineCap = "round";
			ctx.beginPath();
			trace();
			ctx.stroke();
			glowLine(ctx, ASH.lavaGlow, 1.4, 5, trace);
		}
		ctx.strokeStyle = "rgba(0,0,0,0.25)";
		ctx.lineWidth = 1;
		ctx.strokeRect(.5, .5, 51, 51);
	}
	/** 枯黃草。 */
	function ashGrass(ctx, s) {
		const r = rng(s.x, s.y, 203);
		ctx.fillStyle = shade("#6e6040", .95 + r() * .1);
		ctx.fillRect(0, 0, T$12, T$12);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,240,200,0.05)" : "rgba(0,0,0,0.07)";
			ctx.beginPath();
			ctx.ellipse(r() * T$12, r() * T$12, 8 + r() * 10, 6 + r() * 8, r() * TAU, 0, TAU);
			ctx.fill();
		}
		ctx.lineWidth = 1.5;
		ctx.lineCap = "round";
		const n = 6 + Math.floor(r() * 4);
		for (let i = 0; i < n; i++) {
			const gx = 5 + r() * 42;
			const gy = 8 + r() * 39;
			ctx.strokeStyle = r() < .55 ? ASH.blade : "#5a4a2a";
			ctx.beginPath();
			ctx.moveTo(gx, gy);
			ctx.quadraticCurveTo(gx - 1, gy - 5, gx - 4, gy - 8);
			ctx.moveTo(gx, gy);
			ctx.quadraticCurveTo(gx + 1, gy - 5, gx + 4, gy - 9);
			ctx.stroke();
		}
	}
	/** 灰燼：灰色地面加深淺碎點。 */
	function ashDirt(ctx, s) {
		const r = rng(s.x, s.y, 204);
		ctx.fillStyle = shade(ASH.ash, .94 + r() * .12);
		ctx.fillRect(0, 0, T$12, T$12);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.07)";
			ctx.beginPath();
			ctx.ellipse(r() * T$12, r() * T$12, 8 + r() * 10, 5 + r() * 7, r() * TAU, 0, TAU);
			ctx.fill();
		}
		for (let i = 0; i < 14; i++) {
			ctx.fillStyle = r() < .4 ? "rgba(210,200,190,0.35)" : "rgba(30,24,20,0.55)";
			ctx.fillRect(r() * T$12, r() * T$12, 1.8, 1.8);
		}
	}
	/** 焦黑岩壁：深色岩面加岩縫，偶爾有餘燼亮點；南鄰不是牆時畫更深的立面（比單位高）。 */
	function ashWall(ctx, s) {
		const r = rng(s.x, s.y, 205);
		ctx.fillStyle = "#4a3e38";
		ctx.fillRect(0, 0, T$12, T$12);
		ctx.fillStyle = "rgba(255,255,255,0.1)";
		ctx.fillRect(0, 0, T$12, 3);
		ctx.strokeStyle = "rgba(0,0,0,0.6)";
		ctx.lineWidth = 1.5;
		for (let i = 0; i < 4; i++) {
			const x = r() * T$12;
			ctx.beginPath();
			ctx.moveTo(x, r() * T$12 * .3);
			ctx.lineTo(x + (r() - .5) * 10, T$12 * .55);
			ctx.lineTo(x + (r() - .5) * 12, T$12);
			ctx.stroke();
		}
		if (ashGlowAt(s.x, s.y, 206)) for (let i = 0; i < 3; i++) dot(ctx, 4 + r() * 44, T$12 * .25 + r() * T$12 * .6, 1.3, ASH.ember);
		if (s.wallFace) {
			ctx.fillStyle = "#2a221e";
			ctx.fillRect(0, 40, T$12, 12);
			ctx.fillStyle = "rgba(0,0,0,0.35)";
			ctx.fillRect(0, 40, T$12, 2);
			ctx.strokeStyle = "rgba(0,0,0,0.6)";
			ctx.lineWidth = 1.2;
			ctx.beginPath();
			for (let k = 8 + r() * 6; k < T$12; k += 13 + r() * 6) {
				ctx.moveTo(k, 42);
				ctx.lineTo(k + (r() - .5) * 4, T$12);
			}
			ctx.stroke();
		}
	}
	function cliffLip$1(ctx, r, p, n) {
		const [x0, y0, x1, y1] = p;
		ctx.fillStyle = "#3a302a";
		ctx.beginPath();
		ctx.moveTo(x0, y0);
		const steps = 6;
		for (let i = 0; i <= steps; i++) {
			const t = i / steps;
			const d = 3 + r() * 5;
			ctx.lineTo(x0 + (x1 - x0) * t + n[0] * d, y0 + (y1 - y0) * t + n[1] * d);
		}
		ctx.lineTo(x1, y1);
		ctx.closePath();
		ctx.fill();
		ctx.strokeStyle = "#140c08";
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.moveTo(x0 + n[0] * 5, y0 + n[1] * 5);
		ctx.lineTo(x1 + n[0] * 5, y1 + n[1] * 5);
		ctx.stroke();
	}
	/** 黑色裂谷：近黑的深谷，底部只有淡淡的紅光（透明度 ≤ 0.3，只在格子下半）；邊緣有崖線。 */
	function ashChasm(ctx, s) {
		const r = rng(s.x, s.y, 207);
		const g = ctx.createLinearGradient(0, 0, 0, T$12);
		g.addColorStop(0, "#0c0806");
		g.addColorStop(1, "#1a0a06");
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$12, T$12);
		const glow = ctx.createRadialGradient(T$12 / 2, T$12, 2, T$12 / 2, T$12, T$12 * .45);
		glow.addColorStop(0, rgba("#ff4a10", ASH_RIFT_GLOW_ALPHA));
		glow.addColorStop(1, rgba("#ff4a10", 0));
		ctx.fillStyle = glow;
		ctx.fillRect(0, T$12 / 2, T$12, T$12 / 2);
		if (s.lip.n) cliffLip$1(ctx, r, [
			0,
			0,
			T$12,
			0
		], [0, 1]);
		if (s.lip.s) cliffLip$1(ctx, r, [
			0,
			T$12,
			T$12,
			T$12
		], [0, -1]);
		if (s.lip.w) cliffLip$1(ctx, r, [
			0,
			0,
			0,
			T$12
		], [1, 0]);
		if (s.lip.e) cliffLip$1(ctx, r, [
			T$12,
			0,
			T$12,
			T$12
		], [-1, 0]);
		if (s.lip.n) {
			const gg = ctx.createLinearGradient(0, 0, 0, 14);
			gg.addColorStop(0, "rgba(58,48,42,0.85)");
			gg.addColorStop(1, "rgba(58,48,42,0)");
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$12, 14);
		}
	}
	/** 岩漿（本區主場；6V-2）：照熔岩河的畫法——橘紅發光、亮黃熱紋、黑色岩殼裂紋、靠岸一圈冷卻黑殼；荒原底色略暗。 */
	function ashLava(ctx, s) {
		drawLavaBase(ctx, s, 208, .92);
	}
	/** 灰水坑：暗灰的水，上面浮著灰膜；和地面相接的邊是焦土（深色水，致命）。 */
	function ashIceHole(ctx, s) {
		const r = rng(s.x, s.y, 209);
		ctx.fillStyle = "#2c3034";
		ctx.fillRect(0, 0, T$12, T$12);
		ctx.fillStyle = "rgba(150,140,130,0.35)";
		for (let i = 0; i < 4; i++) {
			ctx.beginPath();
			ctx.ellipse(10 + r() * 32, 10 + r() * 32, 5 + r() * 4, 2 + r() * 2, r(), 0, TAU);
			ctx.fill();
		}
		ctx.strokeStyle = "rgba(255,255,255,0.22)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		const wy = 14 + r() * 20;
		ctx.moveTo(12, wy);
		ctx.quadraticCurveTo(20, wy - 4, 28, wy);
		ctx.stroke();
		ctx.fillStyle = ASH.scorch;
		if (s.lip.n) ctx.fillRect(0, 0, T$12, 4);
		if (s.lip.w) ctx.fillRect(0, 0, 4, T$12);
		if (s.lip.e) ctx.fillRect(48, 0, 4, T$12);
		if (s.lip.s) ctx.fillRect(0, 48, T$12, 4);
	}
	/** 灰燼荒原的地形畫法（地形 ID → 畫法）；需求第 2 節「地形」七種。 */
	var ASHEN_TERRAIN = {
		stone: ashStone,
		grass: ashGrass,
		dirt: ashDirt,
		wall: ashWall,
		chasm: ashChasm,
		lava: ashLava,
		ice_hole: ashIceHole
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/cloudRidgeTerrain.ts
	var T$11 = 52;
	/** 雲嶺色票（需求第 2 節）。 */
	var CLOUD = {
		slate: "#7d8c84",
		ink: "#56645c",
		moss: "#5a8a3a",
		bamboo: "#6aa84a",
		bambooDark: "#4f8a3a",
		bambooNode: "#2f5a22",
		red: "#b8432f",
		redDark: "#8a2f20",
		tile: "#3c4a48",
		mist: "#e8e8e0",
		lamp: "#ffcf6a",
		outline: "#1c1712"
	};
	/** 青石板：2～4 塊一格，帶苔點。 */
	function cloudStone(ctx, s) {
		const r = rng(s.x, s.y, 101);
		ctx.fillStyle = CLOUD.ink;
		ctx.fillRect(0, 0, T$11, T$11);
		const blocks = r() < .5 ? [
			[
				0,
				0,
				.55,
				.5
			],
			[
				.55,
				0,
				.45,
				.5
			],
			[
				0,
				.5,
				1,
				.5
			]
		] : [
			[
				0,
				0,
				1,
				.45
			],
			[
				0,
				.45,
				.4,
				.55
			],
			[
				.4,
				.45,
				.6,
				.55
			]
		];
		for (const [bx, by, bw, bh] of blocks) {
			ctx.fillStyle = shade(CLOUD.slate, .92 + r() * .16);
			roundRect(ctx, bx * T$11 + 1.5, by * T$11 + 1.5, bw * T$11 - 3, bh * T$11 - 3, 3);
			ctx.fill();
			ctx.fillStyle = "rgba(255,255,255,0.12)";
			ctx.fillRect(bx * T$11 + 2, by * T$11 + 2, bw * T$11 - 4, 2);
		}
		if (r() < .45) {
			ctx.fillStyle = rgba(CLOUD.moss, .75);
			for (let i = 0; i < 4; i++) {
				ctx.beginPath();
				ctx.arc(r() * T$11, r() * T$11, 2 + r() * 3, 0, TAU);
				ctx.fill();
			}
		}
	}
	/** 偏青的草地：竹葉般細長的草葉。 */
	function cloudGrass(ctx, s) {
		const r = rng(s.x, s.y, 102);
		ctx.fillStyle = shade("#689a70", .96 + r() * .08);
		ctx.fillRect(0, 0, T$11, T$11);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(232,232,224,0.07)" : "rgba(0,0,0,0.05)";
			ctx.beginPath();
			ctx.ellipse(r() * T$11, r() * T$11, 8 + r() * 10, 6 + r() * 8, r() * TAU, 0, TAU);
			ctx.fill();
		}
		const n = 6 + Math.floor(r() * 4);
		ctx.lineWidth = 1.5;
		ctx.lineCap = "round";
		for (let i = 0; i < n; i++) {
			const gx = 5 + r() * 42;
			const gy = 8 + r() * 39;
			ctx.strokeStyle = r() < .55 ? "#9ccf86" : CLOUD.bambooDark;
			ctx.beginPath();
			ctx.moveTo(gx, gy);
			ctx.quadraticCurveTo(gx - 1, gy - 5, gx - 4, gy - 8);
			ctx.moveTo(gx, gy);
			ctx.quadraticCurveTo(gx + 1, gy - 5, gx + 4, gy - 9);
			ctx.stroke();
		}
	}
	/** 黃土小徑。 */
	function cloudDirt(ctx, s) {
		const r = rng(s.x, s.y, 103);
		ctx.fillStyle = shade("#a99560", .95 + r() * .1);
		ctx.fillRect(0, 0, T$11, T$11);
		const n = 5 + Math.floor(r() * 5);
		for (let i = 0; i < n; i++) {
			ctx.fillStyle = r() < .5 ? "#8a7748" : "#c4b27c";
			ctx.beginPath();
			ctx.ellipse(4 + r() * 44, 4 + r() * 44, 1.5 + r() * 2.5, 1.2 + r() * 1.8, r() * TAU, 0, TAU);
			ctx.fill();
		}
		ctx.strokeStyle = "rgba(110,90,50,0.35)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		const yy = T$11 * (.3 + r() * .4);
		ctx.moveTo(0, yy);
		ctx.bezierCurveTo(T$11 * .3, yy - 6, T$11 * .6, yy + 6, T$11, yy - 2);
		ctx.stroke();
	}
	/** 白牆黛瓦：頂上一排深色瓦，立面是白牆；比單位高（立面與瓦頂對比強）。 */
	function cloudWall(ctx, s) {
		const r = rng(s.x, s.y, 104);
		ctx.fillStyle = CLOUD.mist;
		ctx.fillRect(0, 0, T$11, T$11);
		ctx.strokeStyle = "rgba(86,100,92,0.28)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		for (let x = 13; x < T$11; x += 13) {
			ctx.moveTo(x + (r() - .5) * 2, 18);
			ctx.lineTo(x + (r() - .5) * 2, T$11);
		}
		ctx.stroke();
		ctx.fillStyle = "rgba(86,100,92,0.12)";
		ctx.fillRect(Math.floor(r() * 3) * 16 + 3, 24 + r() * 8, 12, 10);
		ctx.fillStyle = CLOUD.tile;
		ctx.fillRect(0, 0, T$11, 18);
		ctx.strokeStyle = "rgba(232,232,224,0.22)";
		ctx.lineWidth = 1.2;
		for (let row = 0; row < 2; row++) for (let x = row ? 4 : 0; x < 60; x += 8) {
			ctx.beginPath();
			ctx.arc(x, 4 + row * 7, 4, 0, Math.PI);
			ctx.stroke();
		}
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		ctx.fillRect(0, 18, T$11, 3);
		ctx.fillStyle = "#2a3534";
		ctx.fillRect(0, 16, T$11, 2);
		if (s.wallFace) {
			ctx.fillStyle = "#b9bab0";
			ctx.fillRect(0, 43, T$11, 9);
			ctx.fillStyle = "rgba(0,0,0,0.12)";
			ctx.fillRect(0, 43, T$11, 1.5);
		}
	}
	function cliffLip(ctx, r, p, n) {
		const [x0, y0, x1, y1] = p;
		ctx.beginPath();
		ctx.moveTo(x0, y0);
		const steps = 6;
		for (let i = 0; i <= steps; i++) {
			const t = i / steps;
			const d = 3 + r() * 5;
			ctx.lineTo(x0 + (x1 - x0) * t + n[0] * d, y0 + (y1 - y0) * t + n[1] * d);
		}
		ctx.lineTo(x1, y1);
		ctx.closePath();
		ctx.fill();
		ctx.strokeStyle = "#2c3833";
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.moveTo(x0 + n[0] * 5, y0 + n[1] * 5);
		ctx.lineTo(x1 + n[0] * 5, y1 + n[1] * 5);
		ctx.stroke();
	}
	/** 雲海山谷（6V-2）：白雲團鋪滿格子、邊緣羽化、底下透淡藍（`hazardTerrainArt.drawCloudSea`）；邊緣仍是青石崖線。 */
	function cloudChasm(ctx, s) {
		const r = rng(s.x, s.y, 105);
		drawCloudSea(ctx, s, 105);
		ctx.fillStyle = CLOUD.ink;
		if (s.lip.n) cliffLip(ctx, r, [
			0,
			0,
			T$11,
			0
		], [0, 1]);
		if (s.lip.s) cliffLip(ctx, r, [
			0,
			T$11,
			T$11,
			T$11
		], [0, -1]);
		if (s.lip.w) cliffLip(ctx, r, [
			0,
			0,
			0,
			T$11
		], [1, 0]);
		if (s.lip.e) cliffLip(ctx, r, [
			T$11,
			0,
			T$11,
			T$11
		], [-1, 0]);
		if (s.lip.n) {
			const gg = ctx.createLinearGradient(0, 0, 0, 14);
			gg.addColorStop(0, "rgba(60,72,66,0.8)");
			gg.addColorStop(1, "rgba(60,72,66,0)");
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$11, 14);
		}
	}
	/** 地熱泉：橘紅的泉水，冒白煙（保留紅色，致命）。 */
	function cloudLava(ctx, s) {
		const r = rng(s.x, s.y, 106);
		ctx.fillStyle = "#d9532a";
		ctx.fillRect(0, 0, T$11, T$11);
		const glow = ctx.createRadialGradient(T$11 / 2, T$11 / 2, 2, T$11 / 2, T$11 / 2, T$11 * .7);
		glow.addColorStop(0, "rgba(255,200,90,0.6)");
		glow.addColorStop(1, "rgba(255,200,90,0)");
		ctx.fillStyle = glow;
		ctx.fillRect(0, 0, T$11, T$11);
		ctx.strokeStyle = "rgba(255,230,160,0.55)";
		ctx.lineWidth = 1.3;
		for (let i = 0; i < 3; i++) {
			const wx = 5 + r() * 30;
			const wy = 12 + i * 14 + r() * 4;
			ctx.beginPath();
			ctx.moveTo(wx, wy);
			ctx.quadraticCurveTo(wx + 5, wy - 3, wx + 10, wy);
			ctx.quadraticCurveTo(wx + 15, wy + 3, wx + 20, wy);
			ctx.stroke();
		}
		for (let i = 0; i < 4; i++) {
			const px = 6 + r() * 40;
			const py = 6 + r() * 40;
			const rad = 7 + r() * 7;
			const sg = ctx.createRadialGradient(px, py, 0, px, py, rad);
			sg.addColorStop(0, "rgba(240,240,232,0.65)");
			sg.addColorStop(1, "rgba(240,240,232,0)");
			ctx.fillStyle = sg;
			ctx.beginPath();
			ctx.arc(px, py, rad, 0, TAU);
			ctx.fill();
		}
	}
	/** 寒潭：深青黑的水，邊緣一圈霜（致命）。 */
	function cloudIceHole(ctx, s) {
		const r = rng(s.x, s.y, 107);
		ctx.fillStyle = "#0e2a2e";
		ctx.fillRect(0, 0, T$11, T$11);
		ctx.strokeStyle = rgba("#4f8f8a", .6);
		ctx.lineWidth = 1.5;
		ctx.lineCap = "round";
		for (let i = 0; i < 3; i++) {
			const wx = 6 + r() * 32;
			const wy = 8 + r() * 36;
			ctx.beginPath();
			ctx.moveTo(wx, wy);
			ctx.quadraticCurveTo(wx + 4, wy - 3, wx + 8, wy);
			ctx.quadraticCurveTo(wx + 12, wy + 3, wx + 16, wy);
			ctx.stroke();
		}
		ctx.fillStyle = "rgba(214,236,232,0.55)";
		if (s.lip.n) ctx.fillRect(0, 0, T$11, 4);
		if (s.lip.w) ctx.fillRect(0, 0, 4, T$11);
		if (s.lip.e) ctx.fillRect(48, 0, 4, T$11);
		if (s.lip.s) ctx.fillRect(0, 48, T$11, 4);
	}
	/** `floor: plank_walk`：木棧道——橫向的木板，釘孔與木紋。 */
	function plankWalk(ctx, s) {
		const r = rng(s.x, s.y, 108);
		ctx.fillStyle = "#3e2e1c";
		ctx.fillRect(0, 0, T$11, T$11);
		const rows = 4;
		const h = T$11 / rows;
		for (let i = 0; i < rows; i++) {
			ctx.fillStyle = shade("#9a7848", .88 + r() * .2);
			ctx.fillRect(0, i * h + 1, T$11, 11);
			ctx.fillStyle = "rgba(255,240,200,0.14)";
			ctx.fillRect(0, i * h + 1, T$11, 1.5);
			ctx.strokeStyle = "rgba(70,48,24,0.4)";
			ctx.lineWidth = 1;
			ctx.beginPath();
			const gy = i * h + 3 + r() * 7;
			ctx.moveTo(0, gy);
			ctx.lineTo(T$11, gy + (r() - .5) * 2);
			ctx.stroke();
			ctx.fillStyle = "#3e2e1c";
			ctx.beginPath();
			ctx.arc(3.5, i * h + h / 2, 1.1, 0, TAU);
			ctx.arc(48.5, i * h + h / 2, 1.1, 0, TAU);
			ctx.fill();
		}
	}
	/** `floor: paddy`：泥田＋田埂（四周一圈較高的土埂，裡面是泥水與秧苗）。 */
	function paddy(ctx, s) {
		const r = rng(s.x, s.y, 109);
		ctx.fillStyle = "#a08a58";
		ctx.fillRect(0, 0, T$11, T$11);
		ctx.fillStyle = "rgba(255,255,255,0.12)";
		ctx.fillRect(0, 0, T$11, 2);
		ctx.fillRect(0, 0, 2, T$11);
		ctx.fillStyle = shade("#6e6040", .94 + r() * .12);
		roundRect(ctx, 5, 5, 42, 42, 4);
		ctx.fill();
		ctx.strokeStyle = "rgba(154,184,176,0.45)";
		ctx.lineWidth = 1.3;
		ctx.beginPath();
		for (let i = 0; i < 2; i++) {
			const wx = 9 + r() * 10;
			const wy = 12 + i * 18 + r() * 5;
			ctx.moveTo(wx, wy);
			ctx.quadraticCurveTo(wx + 6, wy - 3, wx + 13, wy);
		}
		ctx.stroke();
		ctx.strokeStyle = CLOUD.bamboo;
		ctx.lineWidth = 1.3;
		ctx.lineCap = "round";
		for (let row = 0; row < 2; row++) for (let col = 0; col < 3; col++) {
			const px = 11 + col * 15 + row % 2 * 4 + (r() - .5) * 2;
			const py = 18 + row * 17;
			ctx.beginPath();
			ctx.moveTo(px, py);
			ctx.lineTo(px - 3, py - 6);
			ctx.moveTo(px, py);
			ctx.lineTo(px, py - 7);
			ctx.moveTo(px, py);
			ctx.lineTo(px + 3, py - 6);
			ctx.stroke();
		}
	}
	/** `wall: canyon_rock`：灰褐色的山壁岩石（切面分明，頂面亮、底部立面暗）。 */
	function canyonRock(ctx, s) {
		const r = rng(s.x, s.y, 110);
		ctx.fillStyle = "#6f6558";
		ctx.fillRect(0, 0, T$11, T$11);
		const cols = [
			"#8a7e6e",
			"#7a6f60",
			"#9a8e7c",
			"#665c4f"
		];
		for (let i = 0; i < 5; i++) {
			const cx = r() * T$11;
			const cy = r() * T$11;
			const n = 5;
			ctx.beginPath();
			for (let k = 0; k < n; k++) {
				const a = k / n * TAU + r() * .6;
				const rad = 10 + r() * 9;
				const px = cx + Math.cos(a) * rad;
				const py = cy + Math.sin(a) * rad * .8;
				if (k === 0) ctx.moveTo(px, py);
				else ctx.lineTo(px, py);
			}
			ctx.closePath();
			ctx.fillStyle = cols[i % cols.length] ?? "#7a6f60";
			ctx.fill();
			ctx.strokeStyle = "rgba(38,32,26,0.55)";
			ctx.lineWidth = 1.2;
			ctx.stroke();
		}
		ctx.strokeStyle = "rgba(30,26,20,0.6)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		let px = T$11 * (.2 + r() * .6);
		let py = 0;
		ctx.moveTo(px, py);
		for (let i = 0; i < 4; i++) {
			px += (r() - .5) * 12;
			py += T$11 / 4;
			ctx.lineTo(px, py);
		}
		ctx.stroke();
		ctx.fillStyle = "rgba(255,255,255,0.08)";
		ctx.fillRect(0, 0, T$11, 3);
		if (s.wallFace) {
			ctx.fillStyle = "#3f372d";
			ctx.fillRect(0, 43, T$11, 9);
			ctx.fillStyle = "rgba(255,255,255,0.08)";
			ctx.fillRect(0, 43, T$11, 1.5);
		}
	}
	/** 雲嶺的地形畫法（地形 ID → 畫法）；需求第 3 節「地形」七種。 */
	var CLOUD_TERRAIN = {
		stone: cloudStone,
		grass: cloudGrass,
		dirt: cloudDirt,
		wall: cloudWall,
		chasm: cloudChasm,
		lava: cloudLava,
		ice_hole: cloudIceHole
	};
	/** `look` 覆寫的地形畫法：地板 `floor`（石、草、土都換）與牆 `wall`。 */
	var CLOUD_LOOK_TERRAIN = {
		"floor=plank_walk": {
			stone: plankWalk,
			grass: plankWalk,
			dirt: plankWalk
		},
		"floor=paddy": {
			stone: paddy,
			grass: paddy,
			dirt: paddy
		},
		"wall=canyon_rock": { wall: canyonRock }
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/crystalTerrain.ts
	var T$10 = 52;
	/** 晶冠色票（需求第 3 節）。 */
	var CRYSTAL = {
		slab: "#d8ccb0",
		gap: "#a89a7c",
		glint: "#8f7bff",
		banner: "#3a5ad0",
		gold: "#e8bb48",
		outline: "#1c1712"
	};
	/** 這一格石板有沒有金色菱形嵌線（約 1/7 的格子，格子座標雜湊，固定）。 */
	function crystalInlayAt(x, y) {
		return hash(x, y, 301) % 7 === 0;
	}
	/** 主城嵌線的線色：金飾色降低透明度（6Q-1）。 */
	var CAPITAL_INLAY_STROKE = "rgba(232,187,72,0.45)";
	/** 主城嵌線中心晶光點的顏色（同樣降低透明度）。 */
	var CAPITAL_INLAY_GLINT = "rgba(143,123,255,0.5)";
	/** 主城這一格石板有沒有金色嵌線（約 1/12 的格子，格子座標雜湊，固定）。 */
	function capitalInlayAt(x, y) {
		return hash(x, y, 301) % 12 === 0;
	}
	var CROWN_INLAY = {
		at: crystalInlayAt,
		stroke: CRYSTAL.gold,
		glint: CRYSTAL.glint
	};
	/** 主城的嵌線樣式（6Q-1）。 */
	var CAPITAL_INLAY = {
		at: capitalInlayAt,
		stroke: CAPITAL_INLAY_STROKE,
		glint: CAPITAL_INLAY_GLINT
	};
	/** 金色菱形嵌線（1.5 寬）＋中心一個晶光點。 */
	function inlay(ctx, s, style) {
		if (!style.at(s.x, s.y)) return;
		ctx.strokeStyle = style.stroke;
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		ctx.moveTo(T$10 / 2, 6);
		ctx.lineTo(46, T$10 / 2);
		ctx.lineTo(T$10 / 2, 46);
		ctx.lineTo(6, T$10 / 2);
		ctx.closePath();
		ctx.stroke();
		dot(ctx, T$10 / 2, T$10 / 2, 2.5, style.glint);
	}
	/** 深淵上的 4 個晶光碎點（避開北緣崖線）。 */
	function voidGlints(ctx, s) {
		const r = rng(s.x, s.y, 302);
		for (let i = 0; i < 4; i++) dot(ctx, 4 + r() * 44, 14 + r() * 34, 1.2, CRYSTAL.glint);
	}
	/** 白石城牆：頂面米白錯縫磚；南鄰不是牆時畫正面，頂面和正面之間一條金邊（比單位高）。 */
	function crystalWall(ctx, s) {
		ctx.fillStyle = "#e8dcc0";
		ctx.fillRect(0, 0, T$10, T$10);
		ctx.fillStyle = "rgba(255,255,255,0.2)";
		ctx.fillRect(0, 0, T$10, 3);
		ctx.strokeStyle = "rgba(90,74,50,0.5)";
		ctx.lineWidth = 1.5;
		const rows = 4;
		const rh = T$10 / rows;
		ctx.beginPath();
		for (let i = 1; i < rows; i++) {
			ctx.moveTo(0, i * rh);
			ctx.lineTo(T$10, i * rh);
		}
		for (let i = 0; i < rows; i++) for (let bx = i % 2 === 0 ? T$10 / 4 : T$10 / 2; bx < T$10; bx += T$10 / 2) {
			ctx.moveTo(bx, i * rh);
			ctx.lineTo(bx, (i + 1) * rh);
		}
		ctx.stroke();
		if (s.wallFace) {
			ctx.fillStyle = "#b8aa8a";
			ctx.fillRect(0, 42, T$10, 10);
			ctx.strokeStyle = "rgba(90,74,50,0.6)";
			ctx.lineWidth = 1.2;
			ctx.beginPath();
			for (let bx = 9; bx < T$10; bx += 13) {
				ctx.moveTo(bx, 42);
				ctx.lineTo(bx, T$10);
			}
			ctx.stroke();
			ctx.fillStyle = CRYSTAL.gold;
			ctx.fillRect(0, 40, T$10, 2);
		}
	}
	/** 晶冠的地形畫法表：`base` 是預設畫法（由 terrainArt 傳入），石板與深淵在預設上疊點綴。 */
	function crystalTerrain(base, inlayStyle = CROWN_INLAY) {
		return {
			stone: (ctx, s) => {
				base.stone(ctx, s);
				inlay(ctx, s, inlayStyle);
			},
			wall: crystalWall,
			chasm: (ctx, s) => {
				base.chasm(ctx, s);
				voidGlints(ctx, s);
			}
		};
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/frostTerrain.ts
	var T$9 = 52;
	/** 霜潮海境色票（需求第 5 節）。 */
	var FROST = {
		sand: "#d8c89a",
		wetSand: "#b8a478",
		sea: "#3f8ac8",
		floe: "#cdeeff",
		reef: "#6a7a80",
		coral: "#e8807a",
		/** 牆與物件的深色外框（2px）。 */
		outline: "#18222a"
	};
	function speckle(ctx, r, base, fleck, fleck2, n) {
		ctx.fillStyle = shade(base, .94 + r() * .12);
		ctx.fillRect(0, 0, T$9, T$9);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.07)";
			ctx.beginPath();
			ctx.ellipse(r() * T$9, r() * T$9, 8 + r() * 10, 5 + r() * 7, r() * TAU, 0, TAU);
			ctx.fill();
		}
		for (let i = 0; i < n; i++) {
			ctx.fillStyle = fleck2 !== null && r() < .4 ? fleck2 : fleck;
			ctx.fillRect(r() * T$9, r() * T$9, 1.8, 1.8);
		}
	}
	/** 沙岸：沙色加深淺沙粒。 */
	function frostStone(ctx, s) {
		speckle(ctx, rng(s.x, s.y, 501), FROST.sand, "rgba(122,106,72,0.5)", "rgba(255,255,255,0.5)", 12);
	}
	/** 海草灘：彎曲的海草。 */
	function frostGrass(ctx, s) {
		const r = rng(s.x, s.y, 502);
		ctx.fillStyle = shade("#8a9a6a", .95 + r() * .1);
		ctx.fillRect(0, 0, T$9, T$9);
		ctx.lineWidth = 1.5;
		ctx.lineCap = "round";
		const n = 6 + Math.floor(r() * 4);
		for (let i = 0; i < n; i++) {
			const x = 5 + r() * 42;
			const y = 12 + r() * 35;
			ctx.strokeStyle = r() < .55 ? "#4a8a6a" : "#2e6a50";
			ctx.beginPath();
			ctx.moveTo(x, y);
			ctx.bezierCurveTo(x - 3, y - 3, x + 3, y - 6, x, y - 9);
			ctx.stroke();
		}
	}
	/** 濕沙：深一點的沙，加兩道淺色波紋。 */
	function frostDirt(ctx, s) {
		const r = rng(s.x, s.y, 503);
		speckle(ctx, r, FROST.wetSand, "rgba(90,74,48,0.5)", null, 8);
		ctx.strokeStyle = "rgba(255,255,255,0.3)";
		ctx.lineWidth = 1;
		for (let i = 0; i < 2; i++) {
			const y = 14 + i * 20 + r() * 4;
			ctx.beginPath();
			ctx.moveTo(6, y);
			ctx.quadraticCurveTo(T$9 / 2, y - 4, 46, y);
			ctx.stroke();
		}
	}
	/** 冰崖：頂面冰白、裂紋；南鄰不是牆時畫冰藍立面，頂緣垂著冰柱（比單位高）。和其他地形相接的邊畫 2px 深色外框。 */
	function frostWall(ctx, s) {
		const r = rng(s.x, s.y, 504);
		ctx.fillStyle = "#e8f6ff";
		ctx.fillRect(0, 0, T$9, T$9);
		ctx.fillStyle = "rgba(138,184,216,0.35)";
		for (let i = 0; i < 3; i++) {
			ctx.beginPath();
			ctx.ellipse(r() * T$9, r() * T$9, 6 + r() * 8, 3 + r() * 4, r() * TAU, 0, TAU);
			ctx.fill();
		}
		ctx.strokeStyle = "rgba(40,80,110,0.4)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		for (let i = 0; i < 2; i++) {
			const x = 6 + r() * 40;
			ctx.moveTo(x, 4 + r() * 10);
			ctx.lineTo(x + (r() - .5) * 12, T$9 * .6);
		}
		ctx.stroke();
		if (s.wallFace) {
			const faceY = 38;
			ctx.fillStyle = "#8ab8d8";
			ctx.fillRect(0, faceY, T$9, 14);
			ctx.strokeStyle = "rgba(255,255,255,0.55)";
			ctx.lineWidth = 1.2;
			ctx.beginPath();
			for (let i = 0; i < 3; i++) {
				const x = 6 + r() * 40;
				ctx.moveTo(x, 40);
				ctx.lineTo(x - 3, T$9);
			}
			ctx.stroke();
			ctx.fillStyle = "rgba(255,255,255,0.75)";
			for (let k = 4; k < 50; k += 9) {
				ctx.beginPath();
				ctx.moveTo(k, faceY);
				ctx.lineTo(k + 4, faceY);
				ctx.lineTo(k + 2, 43 + r() * 4);
				ctx.fill();
			}
			ctx.fillStyle = FROST.outline;
			ctx.fillRect(0, 37, T$9, 1.5);
		}
		ctx.strokeStyle = FROST.outline;
		ctx.lineWidth = 2;
		ctx.beginPath();
		if (s.lip.n) {
			ctx.moveTo(0, 1);
			ctx.lineTo(T$9, 1);
		}
		if (s.lip.s || s.wallFace) {
			ctx.moveTo(0, 51);
			ctx.lineTo(T$9, 51);
		}
		if (s.lip.w) {
			ctx.moveTo(1, 0);
			ctx.lineTo(1, T$9);
		}
		if (s.lip.e) {
			ctx.moveTo(51, 0);
			ctx.lineTo(51, T$9);
		}
		ctx.stroke();
	}
	/** 深海溝：深藍漸層、兩道淡波紋；和其他地形相接的邊是沙色崖線（北緣加深的崖影）。 */
	function frostChasm(ctx, s) {
		const r = rng(s.x, s.y, 505);
		const g = ctx.createLinearGradient(0, 0, 0, T$9);
		g.addColorStop(0, "#123a6a");
		g.addColorStop(1, "#061a34");
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$9, T$9);
		ctx.strokeStyle = "rgba(160,210,255,0.18)";
		ctx.lineWidth = 1.2;
		for (let i = 0; i < 2; i++) {
			const y = 22 + i * 16 + r() * 4;
			ctx.beginPath();
			ctx.moveTo(8, y);
			ctx.quadraticCurveTo(T$9 / 2, y - 4, 44, y);
			ctx.stroke();
		}
		ctx.fillStyle = "#c8b88a";
		if (s.lip.n) ctx.fillRect(0, 0, T$9, 9);
		if (s.lip.s) ctx.fillRect(0, 48, T$9, 4);
		if (s.lip.w) ctx.fillRect(0, 0, 4, T$9);
		if (s.lip.e) ctx.fillRect(48, 0, 4, T$9);
		ctx.fillStyle = "rgba(0,0,0,0.5)";
		if (s.lip.n) ctx.fillRect(0, 9, T$9, 2);
	}
	/** 海底熱泉（少見）：紅橘岩漿上面多兩團白蒸氣。 */
	function frostLava(ctx, s) {
		const r = rng(s.x, s.y, 506);
		ctx.fillStyle = "#d04010";
		ctx.fillRect(0, 0, T$9, T$9);
		for (let i = 0; i < 4; i++) {
			const cx = r() * T$9;
			const cy = r() * T$9;
			const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 18);
			gg.addColorStop(0, "#ffb030");
			gg.addColorStop(1, rgba("#ffb030", 0));
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$9, T$9);
		}
		for (let i = 0; i < 2; i++) {
			const cx = 10 + r() * 32;
			const cy = 10 + r() * 20;
			const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14);
			gg.addColorStop(0, "rgba(240,240,235,0.45)");
			gg.addColorStop(1, "rgba(240,240,235,0)");
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$9, T$9);
		}
	}
	/** 冰窟（主場）：深藍水；和其他地形相接的邊是冰白外框加淺藍內緣（深色水，致命）。 */
	function frostIceHole(ctx, s) {
		const r = rng(s.x, s.y, 507);
		ctx.fillStyle = "#1e3a5a";
		ctx.fillRect(0, 0, T$9, T$9);
		ctx.strokeStyle = "rgba(255,255,255,0.3)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		const wy = 16 + r() * 18;
		ctx.moveTo(12, wy);
		ctx.quadraticCurveTo(20, wy - 4, 28, wy);
		ctx.stroke();
		const edge = (fill, d, w) => {
			ctx.fillStyle = fill;
			if (s.lip.n) ctx.fillRect(0, d, T$9, w);
			if (s.lip.s) ctx.fillRect(0, T$9 - d - w, T$9, w);
			if (s.lip.w) ctx.fillRect(d, 0, w, T$9);
			if (s.lip.e) ctx.fillRect(T$9 - d - w, 0, w, T$9);
		};
		edge("#9ad0f0", 4, 3);
		edge("#e8f6ff", 0, 4);
	}
	/** 霜潮海境的地形畫法（地形 ID → 畫法）；需求第 5 節七種地形。 */
	var FROST_TERRAIN = {
		stone: frostStone,
		grass: frostGrass,
		dirt: frostDirt,
		wall: frostWall,
		chasm: frostChasm,
		lava: frostLava,
		ice_hole: frostIceHole
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/regionArt.ts
	/** 依 `look` 覆寫 → 區域查畫法；都沒有回傳 undefined（呼叫端退回預設）。覆寫優先於區域。 */
	function pickThemed(theme, id, regions, looks) {
		if (theme.look !== "") for (const pair of theme.look.split(",")) {
			const hit = own(own(looks, pair), id);
			if (hit !== void 0) return hit;
		}
		return theme.region === "" ? void 0 : own(own(regions, theme.region), id);
	}
	/** 取 `look` 正規化字串裡某個鍵的值（沒有為 undefined）；供表面這類「微調顏色而非換整個畫法」的覆寫使用。 */
	function lookValue(look, key) {
		for (const pair of look.split(",")) {
			const i = pair.indexOf("=");
			if (i > 0 && pair.slice(0, i) === key) return pair.slice(i + 1);
		}
	}
	/** 水底色微調（`look.water_tint` → 水面底色）；值不認得 → undefined（用預設的水色）。 */
	var WATER_TINT = { green: "#4f9a62" };
	/** 水底色：依 `look.water_tint` 查表；沒有或不認得 → undefined。 */
	function waterTintOf(look) {
		const v = lookValue(look, "water_tint");
		return v !== void 0 && Object.hasOwn(WATER_TINT, v) ? WATER_TINT[v] : void 0;
	}
	/** 各區的水色（6V-2；Fable 審查第 2 節 A）：雲嶺清藍、荒原深灰藍、主城晶藍；沒列的區域用預設水色。 */
	var WATER_BY_REGION = {
		cloud_ridge: "#3f93d6",
		ashen_waste: "#45627a",
		capital: "#4aa6e4"
	};
	/** 這張圖的水色：`look.water_tint` 優先（雨中梯田的綠），再依區域，都沒有 → `fallback`。 */
	function waterColorOf(theme, fallback) {
		const tint = waterTintOf(theme.look);
		if (tint !== void 0) return tint;
		return own(WATER_BY_REGION, theme.region) ?? fallback;
	}
	/** 只讀自己的屬性（"constructor" 之類的鍵不當成畫法）。 */
	function own(table, key) {
		return table !== void 0 && Object.hasOwn(table, key) ? table[key] : void 0;
	}
	var MIN_INSET = 1.5;
	var INSET_SPAN = 3;
	/** 凸角半徑 10～14 單位。 */
	var RADIUS_MIN = 10;
	var RADIUS_SPAN = 4;
	/** 一條邊的起伏控制點數（段數）與取樣數。 */
	var KNOTS = 4;
	var SIDE_STEPS = 12;
	var CORNER_STEPS = 6;
	/** 邊的方向（N、E、S、W）各自的雜湊鹽。 */
	var SIDE_SALT = [
		301,
		302,
		303,
		304
	];
	var KNOT_SALT = 320;
	var RADIUS_SALT = 340;
	var ALL_CORNERS = {
		nw: true,
		ne: true,
		se: true,
		sw: true
	};
	/** 邊與角的索引：邊 0＝N、1＝E、2＝S、3＝W；角 k 在邊 k−1 與邊 k 之間（0＝西北、1＝東北、2＝東南、3＝西南）。 */
	var CORNER_OFFSET = [
		[0, 0],
		[1, 0],
		[1, 1],
		[0, 1]
	];
	var insetOf = (h) => MIN_INSET + h % 1e3 / 1e3 * INSET_SPAN;
	/** 邊 `side` 在角 `corner` 那個頂點的內縮量：只看頂點的全域座標與邊的方向，相鄰格共用。 */
	function vertexInset(x, y, corner, side) {
		const [dx, dy] = CORNER_OFFSET[corner];
		return insetOf(hash(x + dx, y + dy, SIDE_SALT[side]));
	}
	/** 邊 k 的內縮量曲線：t＝0 在角 k、t＝1 在角 k＋1；兩端只看頂點，中間看格子。餘弦內插，值域不超出控制點。 */
	function sideProfile(x, y, side) {
		const knots = [vertexInset(x, y, side, side)];
		for (let i = 1; i < KNOTS; i++) knots.push(insetOf(hash(x, y, KNOT_SALT + side * 8 + i)));
		knots.push(vertexInset(x, y, (side + 1) % 4, side));
		return (t) => {
			const s = Math.min(3, Math.max(0, Math.floor(t * KNOTS)));
			const u = Math.min(1, Math.max(0, t * KNOTS - s));
			const w = (1 - Math.cos(u * Math.PI)) / 2;
			return knots[s] * (1 - w) + knots[s + 1] * w;
		};
	}
	function cornerRadius(x, y, corner) {
		const [dx, dy] = CORNER_OFFSET[corner];
		return RADIUS_MIN + hash(x + dx, y + dy, RADIUS_SALT) % 1e3 / 1e3 * RADIUS_SPAN;
	}
	/** 以西北角為準的座標轉到角 k（順時針轉 k 次 90°）。 */
	function rot(p, k, T) {
		let [px, py] = p;
		for (let i = 0; i < k; i++) [px, py] = [T - py, px];
		return [px, py];
	}
	function quad(a, c, b, steps) {
		const out = [];
		for (let i = 0; i <= steps; i++) {
			const t = i / steps;
			const u = 1 - t;
			out.push([u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1]]);
		}
		return out;
	}
	var convexAt = (c, k) => c.exposed[(k + 3) % 4] && c.exposed[k];
	/** 角 k 的點（以西北角為準算，再轉過去）。 */
	function cornerPoints(c, k) {
		const prev = (k + 3) % 4;
		const pp = c.profile[prev];
		const cp = c.profile[k];
		const T = c.T;
		let local;
		if (pp && cp) {
			const R = c.radius[k];
			const a = pp(1 - R / T);
			const b = cp(R / T);
			local = quad([a, R], [a, b], [R, b], CORNER_STEPS).map((p) => ({
				p,
				edge: true
			}));
		} else if (cp) local = [{
			p: [0, cp(0)],
			edge: true
		}];
		else if (pp) local = [{
			p: [pp(1), 0],
			edge: false
		}];
		else if (c.diag[k]) local = [{
			p: [0, 0],
			edge: false
		}];
		else {
			const ih = vertexInset(c.x, c.y, k, k);
			const iv = vertexInset(c.x, c.y, k, prev);
			const pts = quad([0, ih], [iv, ih], [iv, 0], CORNER_STEPS);
			local = pts.map((p, i) => ({
				p,
				edge: i < pts.length - 1
			}));
		}
		return local.map(({ p, edge }) => {
			const [px, py] = rot(p, k, T);
			return {
				x: px,
				y: py,
				edge
			};
		});
	}
	/** 邊 k 中間的取樣點（不含兩端，兩端由角給）。 */
	function sidePoints(c, k) {
		const prof = c.profile[k];
		if (!prof) return [];
		const T = c.T;
		const t0 = convexAt(c, k) ? c.radius[k] / T : 0;
		const t1 = convexAt(c, (k + 1) % 4) ? 1 - c.radius[(k + 1) % 4] / T : 1;
		const out = [];
		for (let i = 1; i < SIDE_STEPS; i++) {
			const t = t0 + (t1 - t0) * i / SIDE_STEPS;
			const [px, py] = rot([t * T, prof(t)], k, T);
			out.push({
				x: px,
				y: py,
				edge: true
			});
		}
		return out;
	}
	/**
	* 一格地表的形狀。`same`：四鄰是不是同種地表；`diag`：四個斜鄰是不是同種（只影響兩邊都是接縫的角）。
	* `x`、`y` 是格子座標（雜湊用），`T` 是格子邊長（預設 52 單位）。
	*/
	function blobShape(x, y, same, diag = ALL_CORNERS, T = 52) {
		const exposed = [
			!same.n,
			!same.e,
			!same.s,
			!same.w
		];
		const d = [
			diag.nw,
			diag.ne,
			diag.se,
			diag.sw
		];
		const c = {
			x,
			y,
			T,
			exposed,
			diag: d,
			profile: exposed.map((e, k) => e ? sideProfile(x, y, k) : null),
			radius: [
				0,
				1,
				2,
				3
			].map((k) => cornerRadius(x, y, k))
		};
		const points = [];
		for (let k = 0; k < 4; k++) points.push(...cornerPoints(c, k), ...sidePoints(c, k));
		return {
			points,
			full: exposed.every((e) => !e) && d.every(Boolean)
		};
	}
	/** 把形狀加進目前的路徑（呼叫端自己 `beginPath`／`fill`／`clip`）。 */
	function blobPath(ctx, shape) {
		const pts = shape.points;
		if (pts.length === 0) return;
		ctx.moveTo(pts[0].x, pts[0].y);
		for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
		ctx.closePath();
	}
	/** 外緣的折線（只含露在外面的段，接縫不畫）；每條是一串連續的點。 */
	function blobEdges(shape) {
		const pts = shape.points;
		const n = pts.length;
		const start = pts.findIndex((p, i) => !p.edge && pts[(i + 1) % n].edge);
		if (start < 0) return pts.some((p) => p.edge) ? [[...pts, pts[0]].map(({ x, y }) => ({
			x,
			y
		}))] : [];
		const runs = [];
		let run = [];
		for (let j = 1; j <= n; j++) {
			const i = (start + j) % n;
			const p = pts[i];
			if (run.length === 0) run.push({
				x: p.x,
				y: p.y
			});
			if (p.edge) {
				const q = pts[(i + 1) % n];
				run.push({
					x: q.x,
					y: q.y
				});
			} else {
				if (run.length > 1) runs.push(run);
				run = [];
			}
		}
		if (run.length > 1) runs.push(run);
		return runs;
	}
	/** 只描露在外面的外緣（筆觸樣式由呼叫端先設好）。 */
	function strokeBlobEdges(ctx, shape) {
		const runs = blobEdges(shape);
		if (runs.length === 0) return;
		ctx.beginPath();
		for (const run of runs) {
			ctx.moveTo(run[0].x, run[0].y);
			for (let i = 1; i < run.length; i++) ctx.lineTo(run[i].x, run[i].y);
		}
		ctx.stroke();
	}
	var T$8 = 52;
	function drawStone(ctx, s) {
		const r = rng(s.x, s.y, 1);
		ctx.fillStyle = PAL.stoneGap;
		ctx.fillRect(0, 0, T$8, T$8);
		const slabs = [];
		const splitV = r() < .5;
		const cut = .35 + r() * .3;
		if (splitV) slabs.push([
			0,
			0,
			T$8 * cut,
			T$8
		], [
			T$8 * cut,
			0,
			T$8 * (1 - cut),
			T$8
		]);
		else slabs.push([
			0,
			0,
			T$8,
			T$8 * cut
		], [
			0,
			T$8 * cut,
			T$8,
			T$8 * (1 - cut)
		]);
		if (r() < .6) {
			const [sx, sy, sw, sh] = slabs.pop();
			const c2 = .4 + r() * .2;
			if (splitV) slabs.push([
				sx,
				sy,
				sw,
				sh * c2
			], [
				sx,
				sy + sh * c2,
				sw,
				sh * (1 - c2)
			]);
			else slabs.push([
				sx,
				sy,
				sw * c2,
				sh
			], [
				sx + sw * c2,
				sy,
				sw * (1 - c2),
				sh
			]);
		}
		for (const [sx, sy, sw, sh] of slabs) {
			ctx.fillStyle = shade(PAL.stone, .94 + r() * .12);
			roundRect(ctx, sx + 1.5, sy + 1.5, sw - 3, sh - 3, 3);
			ctx.fill();
			ctx.fillStyle = "rgba(255,255,255,0.10)";
			ctx.fillRect(sx + 3, sy + 2, sw - 6, 2);
		}
		if (r() < .35) {
			ctx.strokeStyle = "rgba(60,56,50,0.55)";
			ctx.lineWidth = 1;
			ctx.beginPath();
			let px = T$8 * (.2 + r() * .6);
			let py = T$8 * (.2 + r() * .2);
			ctx.moveTo(px, py);
			for (let i = 0; i < 3; i++) {
				px += (r() - .5) * 12;
				py += 5 + r() * 6;
				ctx.lineTo(px, py);
			}
			ctx.stroke();
		}
	}
	function drawGrass(ctx, s) {
		const r = rng(s.x, s.y, 2);
		ctx.fillStyle = shade(PAL.grass, .96 + r() * .08);
		ctx.fillRect(0, 0, T$8, T$8);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)";
			ctx.beginPath();
			ctx.ellipse(r() * T$8, r() * T$8, 8 + r() * 10, 6 + r() * 8, r() * TAU, 0, TAU);
			ctx.fill();
		}
		const n = 6 + Math.floor(r() * 4);
		ctx.lineWidth = 1.6;
		ctx.lineCap = "round";
		for (let i = 0; i < n; i++) {
			const gx = 5 + r() * 42;
			const gy = 7 + r() * 40;
			ctx.strokeStyle = r() < .6 ? PAL.grassLight : PAL.grassDark;
			ctx.beginPath();
			ctx.moveTo(gx - 3, gy - 4);
			ctx.lineTo(gx, gy);
			ctx.lineTo(gx + 3, gy - 5);
			ctx.moveTo(gx, gy);
			ctx.lineTo(gx, gy - 6);
			ctx.stroke();
		}
		if (r() < .3) {
			ctx.fillStyle = r() < .5 ? "#f3e27a" : "#f0f0f0";
			ctx.beginPath();
			ctx.arc(6 + r() * 40, 6 + r() * 40, 2, 0, TAU);
			ctx.fill();
		}
	}
	function drawDirt(ctx, s) {
		const r = rng(s.x, s.y, 3);
		ctx.fillStyle = shade(PAL.dirt, .95 + r() * .1);
		ctx.fillRect(0, 0, T$8, T$8);
		const n = 5 + Math.floor(r() * 5);
		for (let i = 0; i < n; i++) {
			ctx.fillStyle = r() < .5 ? PAL.dirtDark : PAL.dirtLight;
			ctx.beginPath();
			ctx.ellipse(4 + r() * 44, 4 + r() * 44, 1.5 + r() * 2.5, 1.2 + r() * 1.8, r() * TAU, 0, TAU);
			ctx.fill();
		}
		ctx.strokeStyle = "rgba(90,66,40,0.35)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		const yy = T$8 * (.3 + r() * .4);
		ctx.moveTo(0, yy);
		ctx.bezierCurveTo(T$8 * .3, yy - 6, T$8 * .6, yy + 6, T$8, yy - 2);
		ctx.stroke();
	}
	function drawWall(ctx, s) {
		ctx.fillStyle = PAL.wallTop;
		ctx.fillRect(0, 0, T$8, T$8);
		const r = rng(s.x, s.y, 4);
		ctx.strokeStyle = PAL.wallLine;
		ctx.lineWidth = 2;
		const rows = 4;
		const rh = T$8 / rows;
		for (let i = 0; i < rows; i++) {
			ctx.beginPath();
			ctx.moveTo(0, i * rh);
			ctx.lineTo(T$8, i * rh);
			ctx.stroke();
			const off = i % 2 === 0 ? 0 : T$8 / 4;
			for (let bx = off; bx < T$8; bx += T$8 / 2) {
				ctx.beginPath();
				ctx.moveTo(bx, i * rh);
				ctx.lineTo(bx, (i + 1) * rh);
				ctx.stroke();
			}
		}
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = `rgba(255,255,255,${.04 + r() * .05})`;
			ctx.fillRect(Math.floor(r() * 2) * (T$8 / 2) + 2, Math.floor(r() * rows) * rh + 2, T$8 / 2 - 4, 9);
		}
		if (s.wallFace) {
			ctx.fillStyle = PAL.wallFace;
			ctx.fillRect(0, 43, T$8, 9);
			ctx.fillStyle = "rgba(255,255,255,0.08)";
			ctx.fillRect(0, 43, T$8, 1.5);
		}
	}
	function jag(ctx, r, p, n) {
		const [x0, y0, x1, y1] = p;
		ctx.beginPath();
		ctx.moveTo(x0, y0);
		const steps = 6;
		for (let i = 0; i <= steps; i++) {
			const t = i / steps;
			const d = 3 + r() * 5;
			ctx.lineTo(x0 + (x1 - x0) * t + n[0] * d, y0 + (y1 - y0) * t + n[1] * d);
		}
		ctx.lineTo(x1, y1);
		ctx.closePath();
		ctx.fill();
	}
	/** 雲海／深淵（6V-2）：白雲團鋪滿格子、邊緣羽化、底下透淡藍（`hazardTerrainArt.drawCloudSea`）；崖緣照舊。 */
	function drawChasm(ctx, s) {
		const r = rng(s.x, s.y, 5);
		drawCloudSea(ctx, s, 5);
		ctx.fillStyle = PAL.chasmLip;
		if (s.lip.n) {
			jag(ctx, r, [
				0,
				0,
				T$8,
				0
			], [0, 1]);
			const gg = ctx.createLinearGradient(0, 0, 0, 16);
			gg.addColorStop(0, "rgba(70,64,80,0.9)");
			gg.addColorStop(1, "rgba(70,64,80,0)");
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$8, 16);
			ctx.fillStyle = PAL.chasmLip;
		}
		if (s.lip.s) jag(ctx, r, [
			0,
			T$8,
			T$8,
			T$8
		], [0, -1]);
		if (s.lip.w) jag(ctx, r, [
			0,
			0,
			0,
			T$8
		], [1, 0]);
		if (s.lip.e) jag(ctx, r, [
			T$8,
			0,
			T$8,
			T$8
		], [-1, 0]);
	}
	/** 熔岩（6V-2）：橘紅發光、黑色岩殼裂紋、靠岸一圈冷卻黑殼（`hazardTerrainArt.drawLavaBase`）；岩殼慢速漂移在 surfaceAnim。 */
	function drawLava(ctx, s) {
		drawLavaBase(ctx, s, 6);
	}
	function drawIceHole(ctx, s) {
		const r = rng(s.x, s.y, 7);
		ctx.fillStyle = PAL.deep;
		ctx.fillRect(0, 0, T$8, T$8);
		ctx.strokeStyle = rgba(PAL.deepLight, .6);
		ctx.lineWidth = 1.5;
		ctx.lineCap = "round";
		for (let i = 0; i < 3; i++) {
			const wx = 6 + r() * 32;
			const wy = 8 + r() * 36;
			ctx.beginPath();
			ctx.moveTo(wx, wy);
			ctx.quadraticCurveTo(wx + 4, wy - 3, wx + 8, wy);
			ctx.quadraticCurveTo(wx + 12, wy + 3, wx + 16, wy);
			ctx.stroke();
		}
		ctx.fillStyle = "rgba(220,240,255,0.55)";
		if (s.lip.n) ctx.fillRect(0, 0, T$8, 4);
		if (s.lip.w) ctx.fillRect(0, 0, 4, T$8);
		if (s.lip.e) ctx.fillRect(48, 0, 4, T$8);
		if (s.lip.s) ctx.fillRect(0, 48, T$8, 4);
	}
	/** 有專屬畫法的地形。 */
	var TERRAIN_DRAW = {
		stone: drawStone,
		grass: drawGrass,
		dirt: drawDirt,
		wall: drawWall,
		chasm: drawChasm,
		lava: drawLava,
		ice_hole: drawIceHole
	};
	/** 各區的地形畫法（區域 ID → 地形 ID → 畫法）；預設區不在表內。雲嶺（3-37b）、灰燼荒原與晶冠點綴（5A-ART6）、魔導樞市與霜潮海境（5A-ART7）已加入。 */
	var REGION_TERRAIN_DRAW = {
		cloud_ridge: CLOUD_TERRAIN,
		ashen_waste: ASHEN_TERRAIN,
		crystal_crown: crystalTerrain({
			stone: drawStone,
			chasm: drawChasm
		}),
		arcane_hub: ARCANE_TERRAIN,
		frost_tide: FROST_TERRAIN,
		capital: { stone: crystalTerrain({
			stone: drawStone,
			chasm: drawChasm
		}, CAPITAL_INLAY).stone }
	};
	/** `look` 覆寫的地形畫法（`"wall=canyon_rock"` → 地形 ID → 畫法）。 */
	var LOOK_TERRAIN_DRAW = {
		...CLOUD_LOOK_TERRAIN,
		"chasm_style=deep_water": { chasm: drawDeepWater }
	};
	/** 頂面亮度（3-19 定案第 4 條）：每高一階疊一層暖白。 */
	function heightLight(ctx, h) {
		if (h <= 0) return;
		ctx.fillStyle = `rgba(255,246,220,${.1 * h})`;
		ctx.fillRect(0, 0, T$8, T$8);
	}
	/** 冰：反光斜線＋細裂紋。 */
	function iceTexture(ctx, _s, r) {
		const ox = (r() - .5) * 10;
		const oy = (r() - .5) * 8;
		ctx.strokeStyle = "rgba(255,255,255,0.9)";
		ctx.lineWidth = 2;
		ctx.lineCap = "round";
		ctx.beginPath();
		ctx.moveTo(14 + ox, 20 + oy);
		ctx.lineTo(24 + ox, 12 + oy);
		ctx.moveTo(20 + ox, 26 + oy);
		ctx.lineTo(34 + ox, 14 + oy);
		ctx.stroke();
		ctx.strokeStyle = "rgba(90,138,168,0.6)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		const cx = T$8 * (.45 + r() * .2);
		const cy = T$8 * (.5 + r() * .2);
		ctx.moveTo(cx, cy);
		ctx.lineTo(cx + 8, cy + 10);
		ctx.lineTo(cx + 14, cy + 6);
		ctx.moveTo(cx + 8, cy + 10);
		ctx.lineTo(cx + 4 + r() * 6, cy + 16);
		ctx.stroke();
	}
	/** 油：虹彩亮斑＋一抹白色油光。 */
	function oilTexture(ctx, _s, r) {
		const cx = T$8 * (.3 + r() * .3);
		const cy = T$8 * (.3 + r() * .3);
		const g = ctx.createLinearGradient(cx - 12, cy - 6, cx + 12, cy + 6);
		g.addColorStop(0, "rgba(160,90,220,0.4)");
		g.addColorStop(.5, "rgba(80,200,160,0.32)");
		g.addColorStop(1, "rgba(230,200,80,0.3)");
		ctx.fillStyle = g;
		ctx.beginPath();
		ctx.ellipse(cx, cy, 11, 4.5, -.4 + (r() - .5) * .6, 0, TAU);
		ctx.fill();
		ctx.fillStyle = "rgba(255,255,255,0.25)";
		ctx.beginPath();
		ctx.ellipse(cx + 11, cy + 11, 6, 2.5, -.4, 0, TAU);
		ctx.fill();
	}
	/** 火的焦痕（6V-3）：黑底不規則的燒焦斑＋外圈煙燻暈＋幾點灰燼；全部照格子座標雜湊。 */
	function scorchMarks(ctx, r) {
		const n = 2 + Math.floor(r() * 2);
		for (let i = 0; i < n; i++) {
			const cx = T$8 * (.22 + r() * .56);
			const cy = T$8 * (.45 + r() * .4);
			const rx = 8 + r() * 8;
			const ry = rx * (.45 + r() * .2);
			const soot = ctx.createRadialGradient(cx, cy, 1, cx, cy, rx * 1.5);
			soot.addColorStop(0, "rgba(18,10,6,0.55)");
			soot.addColorStop(1, "rgba(18,10,6,0)");
			ctx.fillStyle = soot;
			ctx.fillRect(cx - rx * 1.5, cy - rx * 1.5, rx * 3, rx * 3);
			ctx.fillStyle = "rgba(20,12,8,0.82)";
			ctx.beginPath();
			for (let k = 0; k < 8; k++) {
				const a = k / 8 * TAU;
				const j = .7 + r() * .45;
				const px = cx + Math.cos(a) * rx * j;
				const py = cy + Math.sin(a) * ry * j;
				if (k === 0) ctx.moveTo(px, py);
				else ctx.lineTo(px, py);
			}
			ctx.closePath();
			ctx.fill();
		}
		ctx.fillStyle = "rgba(255,150,70,0.75)";
		for (let i = 0; i < 4; i++) {
			ctx.beginPath();
			ctx.arc(6 + r() * 40, T$8 * .55 + r() * T$8 * .38, .9 + r() * .8, 0, TAU);
			ctx.fill();
		}
	}
	/** 一簇火苗（6V-3）：底部圓、往上收成彎曲的尖（`lean` ＝ 尖端往側邊偏，-1～1），旁邊兩條小火舌；三層色（暗紅橘、橘、黃芯）。 */
	function fireTongue(ctx, x, y, h, lean) {
		const w = h * .42;
		const tip = (k) => [x + lean * w * .9 * k, y - h * k];
		const layer = (k, color) => {
			const [tx, ty] = tip(k);
			const ww = w * k;
			ctx.fillStyle = color;
			ctx.beginPath();
			ctx.moveTo(x - ww, y - h * .18 * k);
			ctx.bezierCurveTo(x - ww * 1.05, y - h * .55 * k, tx - ww * .15 - lean * ww * .2, ty + h * .32 * k, tx, ty);
			ctx.bezierCurveTo(tx + ww * .25, ty + h * .3 * k, x + ww * 1.1, y - h * .45 * k, x + ww, y - h * .18 * k);
			ctx.quadraticCurveTo(x + ww * .75, y + h * .06, x, y + h * .06);
			ctx.quadraticCurveTo(x - ww * .75, y + h * .06, x - ww, y - h * .18 * k);
			ctx.closePath();
			ctx.fill();
		};
		for (const s of [-1, 1]) {
			const bx = x + s * w * .75;
			const by = y - h * .12;
			ctx.fillStyle = "rgba(226,72,24,0.9)";
			ctx.beginPath();
			ctx.moveTo(bx - w * .3, by);
			ctx.quadraticCurveTo(bx - w * .2 + s * w * .1, by - h * .3, bx + s * w * .45 + lean * w * .3, by - h * .5);
			ctx.quadraticCurveTo(bx + s * w * .05, by - h * .2, bx + w * .3, by);
			ctx.closePath();
			ctx.fill();
		}
		layer(1, "rgba(214,58,20,0.95)");
		layer(.72, "#ff8a1e");
		layer(.42, "#ffe07a");
	}
	/** 火（6V-3）：黑底焦痕、暖光暈、2～3 簇彎曲的火苗（不畫成三角錐）。火光閃動另由 `surfaceShimmer` 做（減少動態時靜止）。 */
	function fireTexture(ctx, _s, r) {
		scorchMarks(ctx, r);
		const glow = ctx.createRadialGradient(T$8 / 2, T$8 * .62, 2, T$8 / 2, T$8 * .62, T$8 * .55);
		glow.addColorStop(0, "rgba(255,190,70,0.6)");
		glow.addColorStop(1, "rgba(255,90,20,0)");
		ctx.fillStyle = glow;
		ctx.fillRect(0, 0, T$8, T$8);
		const n = 2 + Math.floor(r() * 2);
		for (let i = 0; i < n; i++) fireTongue(ctx, T$8 * ((i + .5) / n) + (r() - .5) * 6, 45 - r() * 9, 13 + r() * 7, (r() - .5) * 1.2);
	}
	function poisonTexture(ctx, _s, r) {
		ctx.strokeStyle = "rgba(220,255,180,0.8)";
		ctx.fillStyle = "rgba(160,230,100,0.6)";
		ctx.lineWidth = 1;
		for (let i = 0; i < 4; i++) {
			ctx.beginPath();
			ctx.arc(8 + r() * 36, 8 + r() * 36, 2 + r() * 3, 0, TAU);
			ctx.fill();
			ctx.stroke();
		}
	}
	/** 煙霧：幾個較大的雲團（裁在形狀內）。 */
	function smokeTexture(ctx, _s, r) {
		const n = 4 + Math.floor(r() * 3);
		for (let i = 0; i < n; i++) {
			ctx.fillStyle = i % 3 === 2 ? "rgba(150,155,170,0.22)" : "rgba(235,238,245,0.38)";
			ctx.beginPath();
			ctx.arc(4 + r() * 44, 4 + r() * 44, 9 + r() * 7, 0, TAU);
			ctx.fill();
		}
	}
	function holyTexture(ctx, _s, r) {
		const g = ctx.createRadialGradient(T$8 / 2, T$8 / 2, 2, T$8 / 2, T$8 / 2, T$8 * .55);
		g.addColorStop(0, "rgba(255,255,240,0.55)");
		g.addColorStop(1, "rgba(255,255,240,0)");
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$8, T$8);
		ctx.strokeStyle = "rgba(255,255,255,0.9)";
		ctx.lineWidth = 1.5;
		ctx.lineCap = "round";
		for (let i = 0; i < 3; i++) {
			const cx = 10 + r() * 32;
			const cy = 10 + r() * 32;
			const k = 3 + r() * 3;
			ctx.beginPath();
			ctx.moveTo(cx - k, cy);
			ctx.lineTo(cx + k, cy);
			ctx.moveTo(cx, cy - k);
			ctx.lineTo(cx, cy + k);
			ctx.stroke();
		}
	}
	/** 黑暗：深紫徑向暈染（中心較深，不用橢圓斑塊避免和油混淆）＋2–3 道捲曲煙絲。 */
	function darknessTexture(ctx, _s, r) {
		const g = ctx.createRadialGradient(T$8 / 2, T$8 / 2, 2, T$8 / 2, T$8 / 2, T$8 * .62);
		g.addColorStop(0, rgba(PAL.darkness, .6));
		g.addColorStop(1, rgba(PAL.darkness, 0));
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$8, T$8);
		ctx.strokeStyle = "rgba(190,130,240,0.5)";
		ctx.lineWidth = 1.4;
		ctx.lineCap = "round";
		const wisps = 2 + Math.floor(r() * 2);
		for (let i = 0; i < wisps; i++) {
			const x0 = 8 + r() * 36;
			const y0 = 46 - r() * 10;
			ctx.beginPath();
			ctx.moveTo(x0, y0);
			ctx.bezierCurveTo(x0 + 10, y0 - 10, x0 - 12, y0 - 18, x0 + 4, y0 - 26 - r() * 8);
			ctx.bezierCurveTo(x0 + 10, y0 - 30, x0 + 12, y0 - 24, x0 + 6, y0 - 22);
			ctx.stroke();
		}
	}
	var SURFACE_STYLE = {
		water: {
			fill: (s) => rgba(waterColorOf(s, PAL.water), .86),
			edge: {
				color: "rgba(220,240,255,0.55)",
				width: 1.2
			}
		},
		ice: {
			fill: () => rgba(PAL.ice, .88),
			texture: iceTexture,
			edge: {
				color: "#ffffff",
				width: 2.2
			}
		},
		oil: {
			fill: () => rgba(PAL.oil, .88),
			texture: oilTexture,
			edge: {
				color: "rgba(200,170,90,0.85)",
				width: 2
			}
		},
		fire: {
			fill: () => "rgba(70,26,10,0.7)",
			texture: fireTexture,
			edge: {
				color: "rgba(255,120,40,0.9)",
				width: 2,
				glow: "#ff8a2a"
			}
		},
		poison: {
			fill: () => rgba(PAL.poison, .7),
			texture: poisonTexture,
			edge: {
				color: "rgba(190,240,140,0.85)",
				width: 1.6
			}
		},
		smoke: {
			fill: () => rgba(PAL.smoke, .35),
			texture: smokeTexture,
			edge: {
				color: "rgba(235,238,245,0.6)",
				width: 1.4
			}
		},
		holy: {
			fill: () => rgba(PAL.holy, .5),
			texture: holyTexture,
			edge: {
				color: "rgba(255,245,200,0.9)",
				width: 1.6
			}
		},
		darkness: {
			fill: () => rgba(PAL.darkness, .55),
			texture: darknessTexture,
			edge: {
				color: "rgba(150,90,200,0.75)",
				width: 1.6
			}
		}
	};
	/** 未知表面：灰色併塊、沒有紋理。 */
	var UNKNOWN_SURFACE = {
		fill: () => rgba("#9a9aa8", .5),
		edge: {
			color: "rgba(210,210,220,0.6)",
			width: 1.4
		}
	};
	/** 這一格表面的形狀（四鄰、斜鄰的同種旗標 → 併塊）。 */
	function surfaceShape(s) {
		return blobShape(s.x, s.y, s.surfSame, s.surfDiag ?? ALL_CORNERS, T$8);
	}
	function drawSurface(ctx, s) {
		if (s.surface === "water") {
			drawWaterFill(ctx, s, waterColorOf(s, PAL.water));
			return;
		}
		const r = rng(s.x, s.y, 20);
		const style = SURFACE_STYLE[s.surface] ?? UNKNOWN_SURFACE;
		const shape = surfaceShape(s);
		ctx.save();
		ctx.beginPath();
		blobPath(ctx, shape);
		ctx.fillStyle = style.fill(s);
		ctx.fill();
		if (style.texture !== void 0) {
			ctx.clip();
			style.texture(ctx, s, r);
		}
		ctx.restore();
		ctx.save();
		ctx.strokeStyle = style.edge.color;
		ctx.lineWidth = style.edge.width;
		ctx.lineJoin = "round";
		ctx.lineCap = "round";
		if (style.edge.glow !== void 0) {
			ctx.shadowColor = style.edge.glow;
			ctx.shadowBlur = 6;
		}
		strokeBlobEdges(ctx, shape);
		ctx.restore();
	}
	/** 畫一個格子（座標以 ART_T 為單位；呼叫端負責縮放與裁切）。 */
	function drawTile(ctx, s) {
		(pickThemed(s, s.terrain, REGION_TERRAIN_DRAW, LOOK_TERRAIN_DRAW) ?? TERRAIN_DRAW[s.terrain] ?? drawStone)(ctx, s);
		if (s.tint !== null) {
			ctx.fillStyle = rgba(numToHex(s.tint), .3);
			ctx.fillRect(0, 0, T$8, T$8);
		}
		if (!s.blocked) heightLight(ctx, s.height);
		if (s.surface !== "none") drawSurface(ctx, s);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/palette.ts
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/battle/glossary.ts
	/** 表面的顏色取自 `render/palette.ts`（單一來源），這裡只決定疊色比例。 */
	var ground = (id, alpha) => ({
		color: parseInt((SURFACE_GROUND_COLOR[id] ?? "#888888").slice(1), 16),
		alpha
	});
	ground("oil", .6), ground("water", .55), ground("fire", .7), ground("ice", .7), ground("poison", .6), ground("holy", .6), ground("darkness", .65), ground("smoke", .6);
	var HIGHLIGHT = {
		move: 8381439,
		attack: 16728128,
		preview: 16751150,
		direction: 16769357,
		active: 16769357,
		hero: 16777215,
		trap: 16765503,
		/** 被揭露的敵方陷阱（Phase 3C-6a）。 */
		trap_revealed: 16734810,
		/** 源泉格（Phase 3C-6a）。 */
		well: 12160255,
		/** 撤離的出口格（Phase 3-22）。 */
		exit: 6217866,
		/** 守點格（Phase 3-22）。 */
		point: 16762941,
		burning: 16734720,
		flammable: 14721088,
		deadly: 16724016,
		trigger: 16732120,
		route: 16769357,
		pierced: 5232895,
		behind: 16755021,
		crush: 12597547,
		rubble: 11569760,
		picked: 5232895,
		landing: 8257405,
		dash: 16747586,
		leap: 8246271,
		swap: 14191871,
		vault: 11758591,
		banish: 12160255,
		banish_lethal: 16724016,
		summon: 6220500,
		/** 持續區域（Phase 3D-5）：有害（傷害、減益）與有益的底色。 */
		zone_harmful: 16738877,
		zone_helpful: 16766282,
		/** 不影響我方的持續區域（3-37b）：虛線外框＋淡底色。 */
		zone_neutral: 11581636,
		/** 定時炸彈（Phase 3D-8b）：預覽的爆炸範圍與倒數；倒地的友方（可復活）與復活的位置。 */
		bomb: 16738842,
		downed: 16726832,
		revive: 8257405,
		/** 複合技能（Phase 3F-3b）：動作段的範圍（紫色）。 */
		followup: 13073919
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/fieldFx.ts
	var T$7 = 52;
	/** 物件受損的裂痕（可破壞物件共用）：級距 1 一道細裂、級距 2 三道粗裂。`box` 是格子內的比例範圍。 */
	function cracks(ctx, stage, gx, gy, color = "#1a1a1a", box = [
		.25,
		.2,
		.75,
		.75
	]) {
		if (stage === 0) return;
		const heavy = stage === 2;
		const r = rng(gx, gy, 11);
		const [x0, y0, x1, y1] = [
			box[0] * T$7,
			box[1] * T$7,
			box[2] * T$7,
			box[3] * T$7
		];
		ctx.save();
		ctx.strokeStyle = color;
		ctx.lineCap = "round";
		ctx.lineWidth = heavy ? 2 : 1.3;
		const lines = heavy ? 3 : 1;
		for (let k = 0; k < lines; k++) {
			let px = x0 + r() * (x1 - x0);
			let py = y0 + r() * (y1 - y0) * .3;
			ctx.beginPath();
			ctx.moveTo(px, py);
			for (let s = 0; s < 4; s++) {
				px += (r() - .5) * 10;
				py += 4 + r() * 5;
				ctx.lineTo(Math.min(x1, Math.max(x0, px)), Math.min(y1, py));
			}
			ctx.stroke();
		}
		ctx.restore();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/lowWallArt.ts
	var T$6 = 52;
	/** 矮牆（美術 PM docs/archive/art/矮牆.md）：暖色石塊——頂面亮、正面錯縫磚、2px 深色外框（相連的一側不畫）、較深的投影。 */
	var LOW_WALL = {
		top: "#d8c7a2",
		topEdge: "#f2e6c8",
		face: "#86704f",
		mortar: "#4c3d2a",
		outline: "#241c13"
	};
	function drawLowWall(ctx, s, pal = LOW_WALL) {
		const x0 = s.joinL ? 0 : 4;
		const x1 = s.joinR ? T$6 : 48;
		const capY = T$6 * .3;
		const capH = T$6 * .16;
		const faceH = T$6 * .26;
		const faceY = 23.92;
		const w = x1 - x0;
		ctx.fillStyle = "rgba(0,0,0,0.42)";
		ctx.fillRect(x0 + 4, 37.44, w, 7);
		ctx.fillStyle = pal.face;
		ctx.fillRect(x0, faceY, w, faceH);
		ctx.strokeStyle = pal.mortar;
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		const rowH = faceH / 2;
		ctx.moveTo(x0, 30.68);
		ctx.lineTo(x1, 30.68);
		for (let r = 0; r < 2; r++) for (let bx = r ? 8 : 17; bx < x1 - 1; bx += 17) {
			if (bx <= x0 + 1) continue;
			ctx.moveTo(bx, faceY + r * rowH);
			ctx.lineTo(bx, faceY + (r + 1) * rowH);
		}
		ctx.stroke();
		ctx.fillStyle = pal.top;
		ctx.fillRect(x0, capY, w, capH);
		ctx.fillStyle = pal.topEdge;
		ctx.fillRect(x0, capY, w, 2);
		ctx.strokeStyle = "rgba(76,61,42,0.6)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		for (let bx = 13; bx < x1 - 1; bx += 26) {
			if (bx <= x0 + 1) continue;
			ctx.moveTo(bx, capY);
			ctx.lineTo(bx, 23.92);
		}
		ctx.stroke();
		ctx.strokeStyle = pal.outline;
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.moveTo(x0, capY);
		ctx.lineTo(x1, capY);
		ctx.moveTo(x0, 37.44);
		ctx.lineTo(x1, 37.44);
		if (!s.joinL) {
			ctx.moveTo(x0, capY);
			ctx.lineTo(x0, 37.44);
		}
		if (!s.joinR) {
			ctx.moveTo(x1, capY);
			ctx.lineTo(x1, 37.44);
		}
		ctx.stroke();
		ctx.strokeStyle = "rgba(36,28,19,0.7)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		ctx.moveTo(x0, faceY);
		ctx.lineTo(x1, faceY);
		ctx.stroke();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/arcaneObjects.ts
	var T$5 = 52;
	var OUT$3 = ARCANE.outline;
	function box$2(ctx, x, y, w, h, fill, lw = 2, r = 2) {
		roundRect(ctx, x, y, w, h, r);
		ctx.fillStyle = fill;
		ctx.fill();
		ctx.lineWidth = lw;
		ctx.strokeStyle = OUT$3;
		ctx.stroke();
	}
	/** 木殼貨箱：黃銅包角，中間有符文橘點（半掩護、可燃）。 */
	function cargoCrate(ctx) {
		shadowEllipse(ctx, 29, 33, T$5 * .34, T$5 * .28);
		const s = T$5 * .62;
		const o = 19.759999999999998 / 2;
		box$2(ctx, o, o, s, s, "#8a6a44", 2, 3);
		ctx.strokeStyle = "rgba(40,26,12,0.55)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		for (let k = 1; k < 4; k++) {
			ctx.moveTo(11.879999999999999, o + s * k / 4);
			ctx.lineTo(40.120000000000005, o + s * k / 4);
		}
		ctx.stroke();
		for (const [cx, cy] of [
			[o, o],
			[35.120000000000005, o],
			[o, 35.120000000000005],
			[35.120000000000005, 35.120000000000005]
		]) box$2(ctx, cx, cy, 7, 7, "#c89a52", 1.2, 1);
		dot(ctx, T$5 / 2, T$5 / 2, 3, ARCANE.rune);
	}
	/** 沙包矮牆的色盤（共用矮牆外框規則）。 */
	var ARCANE_LOW_WALL = {
		top: "#a08a60",
		topEdge: "#c8b080",
		face: "#7a6a4a",
		mortar: "#4a3e2a",
		outline: "#1e1810"
	};
	/** 沙包矮牆＋鐵欄杆：欄杆是 1.2 寬的細線，最高只到矮牆頂上 5 單位（半掩護，不能看起來變高）。 */
	function sandbagWall(ctx, s) {
		drawLowWall(ctx, s, ARCANE_LOW_WALL);
		const x0 = s.joinL ? 0 : 4;
		const x1 = s.joinR ? T$5 : 48;
		const capY = T$5 * .3;
		const railY = 10.6;
		ctx.strokeStyle = rgba(ARCANE.coal, .85);
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		ctx.moveTo(x0 + (s.joinL ? 0 : 2), railY);
		ctx.lineTo(x1 - (s.joinR ? 0 : 2), railY);
		for (let k = 8; k < 49; k += 12) {
			if (k < x0 + 2 || k > x1 - 2) continue;
			ctx.moveTo(k, railY);
			ctx.lineTo(k, capY);
		}
		ctx.stroke();
	}
	/** 黃銅管柱：豎管、三道環箍、壓力表、一小段晶能光（擋視線，畫到格頂）。 */
	function brassPipe(ctx) {
		const c = T$5 / 2;
		ctx.fillStyle = "rgba(0,0,0,0.3)";
		ctx.beginPath();
		ctx.moveTo(20, 46);
		ctx.lineTo(32, 46);
		ctx.lineTo(48, 52);
		ctx.lineTo(34, 52);
		ctx.fill();
		box$2(ctx, 15, 40, 22, 8, ARCANE.plate);
		box$2(ctx, 19, 3, 14, 38, ARCANE.brass, 2, 3);
		ctx.fillStyle = "rgba(255,255,255,0.3)";
		ctx.fillRect(21, 5, 2, 34);
		ctx.fillStyle = "rgba(0,0,0,0.25)";
		ctx.fillRect(28, 5, 4, 34);
		for (const y of [
			8,
			24,
			36
		]) box$2(ctx, 17, y, 18, 4, "#7a5e30", 1.2, 1);
		ctx.beginPath();
		ctx.arc(c, 17, 4.5, 0, TAU);
		ctx.fillStyle = "#f2ead8";
		ctx.fill();
		ctx.lineWidth = 1.5;
		ctx.strokeStyle = OUT$3;
		ctx.stroke();
		ctx.beginPath();
		ctx.moveTo(c, 17);
		ctx.lineTo(28.5, 14.5);
		ctx.strokeStyle = "#c03020";
		ctx.lineWidth = 1.2;
		ctx.stroke();
		glowLine(ctx, rgba(ARCANE.energy, .7), 1.5, 5, () => {
			ctx.moveTo(c, 29);
			ctx.lineTo(c, 34);
		});
	}
	/** 晶能罐：黃銅罐身，中間一條發光的晶能窗；貼四區共用的危險記號（會爆）。 */
	function energyCanister(ctx) {
		shadowEllipse(ctx, 29, 34, T$5 * .3, T$5 * .24);
		const cx = T$5 / 2;
		const bot = 42;
		const w = 16;
		ctx.beginPath();
		ctx.moveTo(10, 14);
		ctx.lineTo(10, bot);
		ctx.ellipse(cx, bot, w, 5, 0, Math.PI, 0, true);
		ctx.lineTo(42, 14);
		ctx.closePath();
		ctx.fillStyle = "#9a7a40";
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$3;
		ctx.stroke();
		ctx.fillStyle = "rgba(0,0,0,0.22)";
		ctx.fillRect(32.4, 14, w * .55, 30);
		ctx.strokeStyle = "#5a4424";
		ctx.lineWidth = 2.5;
		for (const y of [21, 35]) {
			ctx.beginPath();
			ctx.moveTo(10, y);
			ctx.quadraticCurveTo(cx, y + 4, 42, y);
			ctx.stroke();
		}
		ctx.beginPath();
		ctx.ellipse(cx, 14, w, 5, 0, 0, TAU);
		ctx.fillStyle = "#c89a52";
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$3;
		ctx.stroke();
		ctx.save();
		ctx.shadowColor = ARCANE.energy;
		ctx.shadowBlur = 6;
		ctx.fillStyle = rgba(ARCANE.energy, .8);
		ctx.fillRect(32, 24, 5, 16);
		ctx.restore();
		hazardMark(ctx, 23, 34, 6.5);
	}
	/** 倒下的木樑：木頭上一排黃銅鉚釘（半掩護、可燃）。 */
	function rivetBeam(ctx) {
		shadowEllipse(ctx, 28, 35, T$5 * .42, T$5 * .14);
		const y = T$5 / 2 - 4;
		box$2(ctx, 6, y, 40, 13, "#7a5a38", 2, 3);
		ctx.strokeStyle = "rgba(0,0,0,0.35)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		ctx.moveTo(10, 26);
		ctx.lineTo(36, 26);
		ctx.moveTo(10, 32);
		ctx.lineTo(40, 32);
		ctx.stroke();
		roundRect(ctx, 40, y, 6, 13, 1);
		ctx.fillStyle = "#b8905a";
		ctx.fill();
		ctx.lineWidth = 1.5;
		ctx.strokeStyle = OUT$3;
		ctx.stroke();
		for (const x of [
			14,
			24,
			34
		]) dot(ctx, x, 28.5, 1.8, "#c89a52");
	}
	/** 蒸氣苔：苔草、底下一段黃銅管、上面飄著白蒸氣（隱蔽、可燃）。 */
	function steamMoss(ctx, s) {
		const r = rng(s.x, s.y, 411);
		shadowEllipse(ctx, 28, T$5 * .74, T$5 * .36, T$5 * .12);
		box$2(ctx, 2, T$5 * .66, 48, 6, ARCANE.brass, 1.5, 2);
		ctx.lineCap = "round";
		ctx.lineWidth = 2.6;
		for (let i = 0; i < 16; i++) {
			const x = 10 + r() * 32;
			const y = T$5 * .68;
			const h = 14 + r() * 16;
			ctx.strokeStyle = i % 3 === 0 ? "#4a6a3a" : "#7aa060";
			ctx.beginPath();
			ctx.moveTo(x, y);
			ctx.quadraticCurveTo(x + (r() - .5) * 4, y - h * .6, x + (r() - .5) * 12, y - h);
			ctx.stroke();
		}
		for (let i = 0; i < 3; i++) {
			const gx = 14 + i * 12;
			const gg = ctx.createRadialGradient(gx, 14, 1, gx, 14, 10);
			gg.addColorStop(0, "rgba(235,240,240,0.5)");
			gg.addColorStop(1, "rgba(235,240,240,0)");
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$5, T$5);
		}
	}
	/** 鋼樑橋：兩側鐵樑（黃銅鉚釘），中間鋪木板（木板可燃、可破）。沿南北方向畫，東西向時轉 90°。 */
	function steelBridge(ctx, s) {
		ctx.save();
		if (!s.vertical) {
			ctx.translate(T$5, 0);
			ctx.rotate(Math.PI / 2);
		}
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		ctx.fillRect(9, 0, 40, T$5);
		for (let y = 1; y < T$5; y += 8) box$2(ctx, 8, y, 36, 6.5, shade("#9a7448", .9 + y * 7 % 10 / 50), 1.4, 1);
		ctx.fillStyle = ARCANE.plate;
		ctx.fillRect(4, 0, 5, T$5);
		ctx.fillRect(43, 0, 5, T$5);
		ctx.strokeStyle = OUT$3;
		ctx.lineWidth = 1.2;
		ctx.strokeRect(4, 0, 5, T$5);
		ctx.strokeRect(43, 0, 5, T$5);
		for (let y = 4; y < T$5; y += 12) {
			dot(ctx, 6.5, y, 1.4, "#d8b070");
			dot(ctx, 45.5, y, 1.4, "#d8b070");
		}
		ctx.restore();
	}
	/** 木製吊臂：木柱、橫臂、吊鉤（擋視線，畫到格頂；可燃、可推倒）。 */
	function woodCrane(ctx) {
		const c = T$5 / 2;
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		ctx.beginPath();
		ctx.ellipse(29, 46, 12, 4, 0, 0, TAU);
		ctx.fill();
		box$2(ctx, 23, 6, 6, 40, "#8a6a44", 2, 1);
		box$2(ctx, 20, 3, 28, 5, "#8a6a44", 2, 1);
		ctx.strokeStyle = ARCANE.coal;
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		ctx.moveTo(44, 8);
		ctx.lineTo(44, 24);
		ctx.stroke();
		box$2(ctx, 41, 24, 6, 5, ARCANE.brass, 1.2, 1);
		ctx.strokeStyle = ARCANE.brass;
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		ctx.moveTo(c, 18);
		ctx.lineTo(36, 8);
		ctx.stroke();
		for (const y of [16, 30]) box$2(ctx, 21, y, 10, 3, ARCANE.brass, 1, 1);
	}
	/** 冷卻槽上的格柵板：黃銅框的鐵格柵；受損時格條彎曲，最後缺兩根露出冷卻液（薄冰自己畫裂痕）。 */
	function coolantGrate(ctx, s) {
		const stage = s.hpStage;
		ctx.fillStyle = ARCANE.coolant;
		ctx.fillRect(0, 0, T$5, T$5);
		ctx.globalAlpha = .92;
		roundRect(ctx, 5, 5, 42, 42, 6);
		ctx.fillStyle = rgba(ARCANE.plate, stage === 2 ? .55 : .75);
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = ARCANE.brass;
		ctx.stroke();
		ctx.globalAlpha = 1;
		ctx.strokeStyle = ARCANE.brass;
		ctx.lineWidth = 2;
		ctx.beginPath();
		let bar = 0;
		for (let k = 12; k < 46; k += 8, bar++) {
			if (stage === 2 && (bar === 2 || bar === 3)) continue;
			const bend = stage >= 1 && bar === 1 ? 4 : 0;
			ctx.moveTo(k, 7);
			ctx.quadraticCurveTo(k + bend, T$5 / 2, k, 45);
		}
		ctx.stroke();
	}
	/** 魔導樞市的物件畫法（物件 ID → 畫法）；需求第 4 節九種物件。 */
	var ARCANE_OBJECTS = {
		crate: cargoCrate,
		low_wall: sandbagWall,
		stone_pillar: brassPipe,
		oil_barrel: energyCanister,
		fallen_log: rivetBeam,
		grass: steamMoss,
		wooden_bridge: steelBridge,
		dead_tree: woodCrane,
		thin_ice: coolantGrate
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/ashenObjects.ts
	var T$4 = 52;
	var OUT$2 = ASH.outline;
	function box$1(ctx, x, y, w, h, fill, lw = 2, r = 2) {
		roundRect(ctx, x, y, w, h, r);
		ctx.fillStyle = fill;
		ctx.fill();
		ctx.lineWidth = lw;
		ctx.strokeStyle = OUT$2;
		ctx.stroke();
	}
	/** 破木箱：一角破洞，鐵包角（半掩護、可燃）。 */
	function brokenCrate(ctx) {
		shadowEllipse(ctx, 29, 33, T$4 * .34, T$4 * .28);
		const s = T$4 * .62;
		const o = 19.759999999999998 / 2;
		box$1(ctx, o, o, s, s, "#7a5a38", 2, 3);
		ctx.strokeStyle = "rgba(40,24,12,0.6)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		for (let k = 1; k < 4; k++) {
			ctx.moveTo(11.879999999999999, o + s * k / 4);
			ctx.lineTo(40.120000000000005, o + s * k / 4);
		}
		ctx.stroke();
		for (const [cx, cy] of [
			[o, o],
			[35.120000000000005, o],
			[o, 35.120000000000005],
			[35.120000000000005, 35.120000000000005]
		]) box$1(ctx, cx, cy, 7, 7, ASH.ash, 1.2, 1);
		ctx.fillStyle = "#1a120c";
		ctx.beginPath();
		ctx.moveTo(27.612000000000002, 10.879999999999999);
		ctx.lineTo(35.672, 19.552);
		ctx.lineTo(41.120000000000005, 16.328);
		ctx.lineTo(41.120000000000005, 10.879999999999999);
		ctx.closePath();
		ctx.fill();
	}
	/** 殘牆：灰褐石的矮牆（共用矮牆外框規則），頂端有一角崩缺。 */
	var ASH_LOW_WALL = {
		top: ASH.ruinTop,
		topEdge: "#9a8e84",
		face: ASH.ruinFace,
		mortar: "#2e2620",
		outline: "#1a1410"
	};
	function ruinedWall(ctx, s) {
		drawLowWall(ctx, s, ASH_LOW_WALL);
		if (!s.joinR || rng(s.x, s.y, 211)() < 1 / 3) {
			const x1 = s.joinR ? 46 : 48;
			ctx.fillStyle = "#1a1410";
			ctx.beginPath();
			ctx.moveTo(x1 - 14, 14.6);
			ctx.lineTo(x1 - 8, 21.6);
			ctx.lineTo(x1 + 1, 17.6);
			ctx.lineTo(x1 + 1, 14.6);
			ctx.closePath();
			ctx.fill();
		}
	}
	/** 斷柱：頂端斷口參差、有裂紋（擋視線，畫到格頂）。 */
	function brokenPillar(ctx) {
		const c = T$4 / 2;
		ctx.fillStyle = "rgba(0,0,0,0.3)";
		ctx.beginPath();
		ctx.moveTo(20, 46);
		ctx.lineTo(32, 46);
		ctx.lineTo(48, 52);
		ctx.lineTo(34, 52);
		ctx.fill();
		box$1(ctx, 15, 40, 22, 8, ASH.ruinFace);
		ctx.beginPath();
		ctx.moveTo(19, 41);
		ctx.lineTo(19, 10);
		ctx.lineTo(23, 6);
		ctx.lineTo(c, 11);
		ctx.lineTo(29, 3);
		ctx.lineTo(33, 9);
		ctx.lineTo(33, 41);
		ctx.closePath();
		ctx.fillStyle = ASH.ruinTop;
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$2;
		ctx.stroke();
		ctx.fillStyle = "rgba(0,0,0,0.28)";
		ctx.fillRect(28, 10, 4, 30);
		ctx.strokeStyle = "rgba(0,0,0,0.45)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		for (const y of [18, 28]) {
			ctx.moveTo(20, y);
			ctx.lineTo(32, y + 2);
		}
		ctx.stroke();
		for (const [dx, dy] of [[-4, 24], [2, 34]]) dot(ctx, c + dx, dy, 1.6, "#1a120c");
	}
	/** 鐵油桶（鏽）：灰鐵桶身、鏽斑，桶身貼四區共用的危險記號（會爆）。 */
	function rustyBarrel(ctx) {
		shadowEllipse(ctx, 29, 34, T$4 * .3, T$4 * .24);
		const cx = T$4 / 2;
		const bot = 42;
		const w = 16;
		ctx.beginPath();
		ctx.moveTo(10, 14);
		ctx.lineTo(10, bot);
		ctx.ellipse(cx, bot, w, 5, 0, Math.PI, 0, true);
		ctx.lineTo(42, 14);
		ctx.closePath();
		ctx.fillStyle = "#5a5e60";
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$2;
		ctx.stroke();
		ctx.fillStyle = "rgba(0,0,0,0.22)";
		ctx.fillRect(32.4, 14, w * .55, 30);
		ctx.strokeStyle = "#3a3c3e";
		ctx.lineWidth = 2.5;
		for (const y of [21, 35]) {
			ctx.beginPath();
			ctx.moveTo(10, y);
			ctx.quadraticCurveTo(cx, y + 4, 42, y);
			ctx.stroke();
		}
		ctx.beginPath();
		ctx.ellipse(cx, 14, w, 5, 0, 0, TAU);
		ctx.fillStyle = "#6a6e70";
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$2;
		ctx.stroke();
		for (const [dx, dy, rad] of [
			[
				-8,
				22,
				4
			],
			[
				6,
				32,
				3
			],
			[
				-3,
				38,
				2.5
			]
		]) dot(ctx, cx + dx, dy, rad, "#9a4a20");
		hazardMark(ctx, 23, 34, 6.5);
	}
	/** 焦黑倒木：中段炭化，上面有餘燼點（半掩護、可燃）。 */
	function charredLog(ctx, s) {
		shadowEllipse(ctx, 28, 35, T$4 * .42, T$4 * .14);
		box$1(ctx, 6, T$4 / 2 - 4, 40, 13, "#4a3628", 2, 6);
		ctx.strokeStyle = "rgba(0,0,0,0.5)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		ctx.moveTo(10, 27);
		ctx.lineTo(36, 26);
		ctx.moveTo(14, 31);
		ctx.lineTo(40, 31);
		ctx.stroke();
		ctx.beginPath();
		ctx.ellipse(44, 28.5, 4, 6.5, 0, 0, TAU);
		ctx.fillStyle = "#8a6a48";
		ctx.fill();
		ctx.lineWidth = 1.5;
		ctx.strokeStyle = OUT$2;
		ctx.stroke();
		ctx.fillStyle = "#1a120c";
		ctx.fillRect(16, 23, 10, 11);
		ctx.fillRect(30, 23, 5, 11);
		if (ashGlowAt(s.x, s.y, 212)) for (const x of [20, 32]) dot(ctx, x, 28, 1.2, ASH.ember);
	}
	/** 枯草堆（隱蔽、可燃）：一叢較高的乾黃草葉。 */
	function dryTuft(ctx, s) {
		const r = rng(s.x, s.y, 213);
		shadowEllipse(ctx, 28, T$4 * .74, T$4 * .36, T$4 * .12);
		ctx.lineCap = "round";
		ctx.lineWidth = 2.6;
		for (let i = 0; i < 16; i++) {
			const x = 10 + r() * 32;
			const y = T$4 * .72;
			const h = 14 + r() * 16;
			ctx.strokeStyle = i % 3 === 0 ? "#7a6438" : ASH.bladeLight;
			ctx.beginPath();
			ctx.moveTo(x, y);
			ctx.quadraticCurveTo(x + (r() - .5) * 4, y - h * .6, x + (r() - .5) * 12, y - h);
			ctx.stroke();
		}
	}
	/** 焦木渡橋：橋板兩端焦黑，兩側有橋樁；橋下是下面的地形（通常是岩漿）。沿南北方向畫，東西向時轉 90°。 */
	function charredBridge(ctx, s) {
		ctx.save();
		if (!s.vertical) {
			ctx.translate(T$4, 0);
			ctx.rotate(Math.PI / 2);
		}
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		ctx.fillRect(9, 0, 40, T$4);
		for (let y = 1; y < T$4; y += 8) {
			box$1(ctx, 8, y, 36, 6.5, shade("#7a5a38", .9 + y * 7 % 10 / 50), 1.4, 1);
			ctx.fillStyle = "#1e140c";
			ctx.fillRect(8, y, 5, 6.5);
			ctx.fillRect(37, y, 7, 6.5);
		}
		for (const y of [0, 44]) {
			box$1(ctx, 3, y, 6, 8, "#3a2a1e", 1.4, 1);
			box$1(ctx, 43, y, 6, 8, "#3a2a1e", 1.4, 1);
		}
		ctx.restore();
	}
	/** 枯樹（本區主場）：焦黑分枝，有餘燼點（擋視線，畫到格頂；可燃、可推倒）。 */
	function charredTree(ctx, s) {
		const c = T$4 / 2;
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		ctx.beginPath();
		ctx.ellipse(29, 46, 12, 4, 0, 0, TAU);
		ctx.fill();
		const br = [
			[
				c,
				46,
				c,
				22,
				7
			],
			[
				c,
				30,
				14,
				16,
				4
			],
			[
				c,
				26,
				38,
				12,
				4
			],
			[
				38,
				12,
				44,
				4,
				2.5
			],
			[
				14,
				16,
				10,
				6,
				2.5
			],
			[
				30,
				22,
				28,
				3,
				3
			]
		];
		ctx.lineCap = "round";
		for (const [color, extra] of [[OUT$2, 3], ["#3a2a20", 0]]) {
			ctx.strokeStyle = color;
			for (const [ax, ay, bx, by, w] of br) {
				ctx.lineWidth = w + extra;
				ctx.beginPath();
				ctx.moveTo(ax, ay);
				ctx.lineTo(bx, by);
				ctx.stroke();
			}
		}
		if (ashGlowAt(s.x, s.y, 214)) for (const [x, y] of [
			[25, 34],
			[35, 15],
			[16, 19]
		]) dot(ctx, x, y, 1.4, ASH.ember);
	}
	/** 灰水上的浮板：木板拼成，架在灰水坑上；受損時木縫變大，最後缺一塊露出灰水（薄冰自己畫裂痕）。 */
	function floatPlanks(ctx, s) {
		const stage = s.hpStage;
		const r = rng(s.x, s.y, 215);
		ctx.fillStyle = "#2c3034";
		ctx.fillRect(0, 0, T$4, T$4);
		ctx.globalAlpha = stage === 2 ? .8 : .95;
		roundRect(ctx, 5, 5, 42, 42, 6);
		ctx.fillStyle = "#8a6a48";
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = "#3a2a1e";
		ctx.stroke();
		ctx.globalAlpha = 1;
		ctx.strokeStyle = rgba("#000000", stage === 0 ? .35 : .55);
		ctx.lineWidth = stage === 0 ? 1.2 : 2;
		ctx.beginPath();
		for (let y = 14; y < 44; y += 9) {
			ctx.moveTo(7, y);
			ctx.lineTo(45, y + (stage === 0 ? 0 : (r() - .5) * 3));
		}
		ctx.stroke();
		if (stage >= 1) {
			ctx.strokeStyle = "#2a1c10";
			ctx.lineWidth = 1.3;
			ctx.beginPath();
			const px = 14 + r() * 20;
			ctx.moveTo(px, 15);
			ctx.lineTo(px + 4, 22);
			ctx.lineTo(px + 1, 30);
			ctx.stroke();
		}
		if (stage === 2) {
			ctx.fillStyle = "#1e2226";
			ctx.fillRect(9, 24, 34, 8);
		}
	}
	/** 灰燼荒原的物件畫法（物件 ID → 畫法）；需求第 2 節「物件」九種。 */
	var ASHEN_OBJECTS = {
		crate: brokenCrate,
		low_wall: ruinedWall,
		stone_pillar: brokenPillar,
		oil_barrel: rustyBarrel,
		fallen_log: charredLog,
		grass: dryTuft,
		wooden_bridge: charredBridge,
		dead_tree: charredTree,
		thin_ice: floatPlanks
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/cloudRidgeObjects.ts
	var T$3 = 52;
	var BAMBOO_TAN = "#b9a05a";
	/** 竹籠貨箱：竹篾編成的方籠（半掩護，矮；斜紋編織＋竹框＋蓋）。 */
	function bambooCrate(ctx) {
		shadowEllipse(ctx, 29, 31, T$3 * .34, T$3 * .3);
		const s = T$3 * .62;
		const o = 19.759999999999998 / 2;
		roundRect(ctx, o, o, s, s, 3);
		ctx.fillStyle = BAMBOO_TAN;
		ctx.fill();
		ctx.save();
		ctx.beginPath();
		ctx.rect(10.879999999999999, 10.879999999999999, 30.240000000000002, 30.240000000000002);
		ctx.clip();
		ctx.strokeStyle = "rgba(92,70,28,0.55)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		for (let k = -32.24; k < s * 2; k += 5) {
			ctx.moveTo(o + k, o);
			ctx.lineTo(o + k + s, 42.120000000000005);
			ctx.moveTo(o + k + s, o);
			ctx.lineTo(o + k, 42.120000000000005);
		}
		ctx.stroke();
		ctx.restore();
		roundRect(ctx, o, o, s, s, 3);
		ctx.lineWidth = 2.5;
		ctx.strokeStyle = "#5c4620";
		ctx.stroke();
		ctx.strokeStyle = CLOUD.bambooDark;
		ctx.lineWidth = 3;
		ctx.beginPath();
		ctx.moveTo(11.879999999999999, 26);
		ctx.lineTo(40.120000000000005, 26);
		ctx.stroke();
		ctx.fillStyle = "rgba(255,255,255,0.2)";
		ctx.fillRect(11.879999999999999, 11.879999999999999, 28.240000000000002, 3);
	}
	/** 白牆矮垣（黛瓦壓頂）：沿用矮牆的外框規則（相連的一側不畫外框），換白牆與黛瓦。 */
	var CLOUD_LOW_WALL = {
		top: CLOUD.tile,
		topEdge: "#6a7a76",
		face: CLOUD.mist,
		mortar: "#a9aca2",
		outline: "#1f2a28"
	};
	/** 朱紅樑柱：高大的紅柱，頂有斗拱與黛瓦，腳下石礎（擋視線）。 */
	function redPillar(ctx) {
		ctx.fillStyle = "rgba(0,0,0,0.3)";
		ctx.beginPath();
		ctx.moveTo(20, 46);
		ctx.lineTo(32, 46);
		ctx.lineTo(48, 52);
		ctx.lineTo(34, 52);
		ctx.fill();
		roundRect(ctx, 15, 40, 22, 8, 2);
		ctx.fillStyle = CLOUD.slate;
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = CLOUD.outline;
		ctx.stroke();
		roundRect(ctx, 20, 9, 12, 32, 2);
		ctx.fillStyle = CLOUD.red;
		ctx.fill();
		ctx.stroke();
		ctx.fillStyle = CLOUD.redDark;
		ctx.fillRect(27, 10, 4, 30);
		ctx.fillStyle = "rgba(255,255,255,0.22)";
		ctx.fillRect(22, 11, 2, 28);
		roundRect(ctx, 14, 6, 24, 6, 1);
		ctx.fillStyle = CLOUD.redDark;
		ctx.fill();
		ctx.stroke();
		ctx.beginPath();
		ctx.moveTo(8, 8);
		ctx.lineTo(16, 1);
		ctx.lineTo(36, 1);
		ctx.lineTo(44, 8);
		ctx.lineTo(36, 6);
		ctx.lineTo(16, 6);
		ctx.closePath();
		ctx.fillStyle = CLOUD.tile;
		ctx.fill();
		ctx.stroke();
	}
	/** 酒罈：圓肚陶罈，紅布封口綁繩；罈身貼危險記號（會爆）。 */
	function wineJar(ctx) {
		shadowEllipse(ctx, 29, 31, T$3 * .3, T$3 * .28);
		const c = T$3 / 2;
		const r = T$3 * .29;
		ctx.fillStyle = "#4a2a1c";
		ctx.beginPath();
		ctx.ellipse(c, 31, r, r * .92, 0, 0, TAU);
		ctx.fill();
		ctx.fillStyle = "#9a6a44";
		ctx.beginPath();
		ctx.ellipse(c, 27, r, r * .92, 0, 0, TAU);
		ctx.fill();
		ctx.strokeStyle = CLOUD.outline;
		ctx.lineWidth = 2;
		ctx.stroke();
		ctx.fillStyle = "rgba(255,255,255,0.2)";
		ctx.beginPath();
		ctx.ellipse(20, 20, 4, 2.4, -.6, 0, TAU);
		ctx.fill();
		roundRect(ctx, 19, 9.920000000000002, 14, 9, 3);
		ctx.fillStyle = CLOUD.red;
		ctx.fill();
		ctx.stroke();
		ctx.strokeStyle = "#e0c890";
		ctx.lineWidth = 1.6;
		ctx.beginPath();
		ctx.moveTo(19, 15.920000000000002);
		ctx.lineTo(33, 15.920000000000002);
		ctx.stroke();
		ctx.save();
		ctx.beginPath();
		ctx.arc(c, 30, r * .45, 0, TAU);
		ctx.clip();
		ctx.fillStyle = "#f2b33d";
		ctx.fillRect(10.920000000000002, 10.920000000000002, r * 2, 38.16);
		ctx.fillStyle = "#1a120a";
		ctx.beginPath();
		ctx.moveTo(c, 24.5);
		ctx.bezierCurveTo(31, 30.5, 30, 35, c, 35);
		ctx.bezierCurveTo(22, 35, 21, 30.5, c, 24.5);
		ctx.fill();
		ctx.restore();
	}
	/** 倒竹：一捆倒下的竹子（半掩護，矮、可燃），斜放，竹節與斷口。 */
	function fallenBamboo(ctx) {
		ctx.save();
		ctx.translate(T$3 / 2, T$3 / 2);
		ctx.rotate(-.5);
		ctx.fillStyle = "rgba(0,0,0,0.28)";
		roundRect(ctx, -17.8, -2, T$3 * .8, 20, 7);
		ctx.fill();
		for (let i = 0; i < 3; i++) {
			const y = -9 + i * 6.5;
			ctx.fillStyle = i === 1 ? CLOUD.bambooDark : CLOUD.bamboo;
			roundRect(ctx, -20.8, y, T$3 * .8, 7, 3.5);
			ctx.fill();
			ctx.lineWidth = 1.4;
			ctx.strokeStyle = CLOUD.outline;
			ctx.stroke();
			ctx.fillStyle = CLOUD.bambooNode;
			for (let k = -52 * .28; k < T$3 * .36; k += 11) ctx.fillRect(k, y + .5, 1.8, 6);
			ctx.fillStyle = "#d8dca0";
			ctx.beginPath();
			ctx.ellipse(T$3 * .4, y + 3.5, 1.8, 3.2, 0, 0, TAU);
			ctx.fill();
		}
		ctx.restore();
	}
	/** 矮竹叢（隱蔽、可燃）：一叢短短的竹桿與葉。 */
	function bambooBush(ctx, s) {
		const r = rng(s.x, s.y, 112);
		shadowEllipse(ctx, 28, T$3 * .78, T$3 * .36, T$3 * .12);
		const stalks = 5;
		for (let i = 0; i < stalks; i++) {
			const bx = T$3 * (.2 + .6 * i / 4) + (r() - .5) * 3;
			const base = T$3 * (.76 + i % 2 * .04);
			const top = base - (18 + r() * 8);
			ctx.fillStyle = i % 2 ? CLOUD.bambooDark : CLOUD.bamboo;
			ctx.fillRect(bx - 2, top, 4, base - top);
			ctx.strokeStyle = CLOUD.outline;
			ctx.lineWidth = 1.2;
			ctx.strokeRect(bx - 2, top, 4, base - top);
			ctx.fillStyle = CLOUD.bambooNode;
			for (let k = top + 7; k < base - 2; k += 8) ctx.fillRect(bx - 2.5, k, 5, 1.6);
			ctx.fillStyle = "#7cc05a";
			ctx.beginPath();
			ctx.ellipse(bx + 5, top + 3 + r() * 4, 6, 2.2, -.5, 0, TAU);
			ctx.ellipse(bx - 5, top + 6 + r() * 4, 6, 2.2, .5, 0, TAU);
			ctx.fill();
		}
	}
	/** 竹木吊橋：兩側繩索與繩樁，竹木橋板；橋下是雲海（下面的地形）。 */
	function suspensionBridge(ctx, s) {
		ctx.save();
		if (s.vertical) {
			ctx.translate(T$3, 0);
			ctx.rotate(Math.PI / 2);
		}
		const r = rng(s.x, s.y, 113);
		ctx.fillStyle = "#6a4a28";
		ctx.fillRect(0, 9, T$3, 34);
		for (let px = 0; px < T$3; px += T$3 / 6) {
			ctx.fillStyle = `rgba(${200 + Math.floor(r() * 30)},${160 + Math.floor(r() * 30)},90,1)`;
			ctx.fillRect(px + 1, 10, T$3 / 6 - 2, 32);
			ctx.fillStyle = "rgba(255,240,200,0.18)";
			ctx.fillRect(px + 1, 10, T$3 / 6 - 2, 2);
		}
		ctx.strokeStyle = "#3a2814";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		for (let px = 0; px <= T$3; px += T$3 / 6) {
			ctx.moveTo(px, 10);
			ctx.lineTo(px, 42);
		}
		ctx.stroke();
		for (const ry of [6, 46]) {
			ctx.strokeStyle = CLOUD.outline;
			ctx.lineWidth = 3.4;
			ctx.beginPath();
			ctx.moveTo(0, ry);
			ctx.quadraticCurveTo(T$3 / 2, ry + (ry < T$3 / 2 ? 2 : -2), T$3, ry);
			ctx.stroke();
			ctx.strokeStyle = "#c8a870";
			ctx.lineWidth = 1.8;
			ctx.stroke();
			ctx.fillStyle = "#5a3c1e";
			for (const px of [2, 50]) ctx.fillRect(px - 1.5, ry - 3, 3, 6);
		}
		ctx.restore();
	}
	/** 老松：深綠針葉成層，彎曲的樹幹（擋視線、高、可燃、可推倒）。 */
	function oldPine(ctx, s) {
		const r = rng(s.x, s.y, 114);
		shadowEllipse(ctx, 30, T$3 * .84, T$3 * .34, T$3 * .1);
		ctx.strokeStyle = CLOUD.outline;
		ctx.lineCap = "round";
		ctx.lineWidth = 7;
		ctx.beginPath();
		ctx.moveTo(24, 47);
		ctx.quadraticCurveTo(30, 34, 24, 22);
		ctx.quadraticCurveTo(22, 14, 28, 8);
		ctx.stroke();
		ctx.strokeStyle = "#5a4030";
		ctx.lineWidth = 4;
		ctx.stroke();
		for (const [cx, cy, rx, ry] of [
			[
				18,
				34,
				17,
				6
			],
			[
				34,
				26,
				15,
				6
			],
			[
				20,
				19,
				14,
				5.5
			],
			[
				32,
				12,
				12,
				5
			],
			[
				26,
				6,
				9,
				4
			]
		]) {
			ctx.fillStyle = "#274a34";
			ctx.beginPath();
			ctx.ellipse(cx + 1, cy + 2, rx, ry, 0, 0, TAU);
			ctx.fill();
			ctx.fillStyle = r() < .5 ? "#2f5a3a" : "#356642";
			ctx.beginPath();
			ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
			ctx.fill();
			ctx.strokeStyle = CLOUD.outline;
			ctx.lineWidth = 1.5;
			ctx.stroke();
			ctx.fillStyle = "rgba(190,230,170,0.22)";
			ctx.beginPath();
			ctx.ellipse(cx - rx * .25, cy - ry * .35, rx * .5, ry * .3, 0, 0, TAU);
			ctx.fill();
		}
	}
	/** 寒潭薄冰：架在寒潭上的冰板，裂痕隨耐久增加（級距 0／1／2），最後露出黑水。 */
	function pondIce(ctx, s) {
		const stage = s.hpStage;
		ctx.fillStyle = "#0e2a2e";
		ctx.fillRect(0, 0, T$3, T$3);
		const r = rng(s.x, s.y, 115);
		ctx.beginPath();
		ctx.roundRect(3, 3, 46, 46, 8);
		ctx.fillStyle = rgba("#cfe8e4", stage === 2 ? .62 : .86);
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = "#eef8f4";
		ctx.stroke();
		ctx.fillStyle = rgba("#0e2a2e", .25);
		ctx.beginPath();
		ctx.ellipse(T$3 / 2, T$3 / 2, T$3 * .26, T$3 * .2, .3, 0, TAU);
		ctx.fill();
		const rays = stage === 0 ? 2 : stage === 1 ? 4 : 7;
		ctx.strokeStyle = stage === 2 ? "#0e2a2e" : "#5a8a88";
		ctx.lineWidth = stage === 2 ? 2 : 1.3;
		ctx.beginPath();
		for (let i = 0; i < rays; i++) {
			const ang = i / rays * TAU + r();
			let px = T$3 / 2;
			let py = T$3 / 2;
			ctx.moveTo(px, py);
			for (let k = 0; k < 3; k++) {
				px += Math.cos(ang + (r() - .5) * .8) * 7;
				py += Math.sin(ang + (r() - .5) * .8) * 7;
				ctx.lineTo(px, py);
			}
		}
		ctx.stroke();
		if (stage === 2) {
			ctx.fillStyle = "#07191c";
			ctx.beginPath();
			ctx.moveTo(T$3 * .44, T$3 * .42);
			ctx.lineTo(T$3 * .58, T$3 * .44);
			ctx.lineTo(T$3 * .56, T$3 * .58);
			ctx.lineTo(T$3 * .42, T$3 * .55);
			ctx.fill();
		}
	}
	/** 雲嶺的物件畫法（物件 ID → 畫法）；需求第 3 節「物件」九種。 */
	var CLOUD_OBJECTS = {
		crate: bambooCrate,
		low_wall: (ctx, s) => drawLowWall(ctx, s, CLOUD_LOW_WALL),
		stone_pillar: redPillar,
		oil_barrel: wineJar,
		fallen_log: fallenBamboo,
		grass: bambooBush,
		wooden_bridge: suspensionBridge,
		dead_tree: oldPine,
		thin_ice: pondIce
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/crystalObjects.ts
	var T$2 = 52;
	var OUT$1 = CRYSTAL.outline;
	/** 晶柱外光的透明度（模糊 10；比頭目外光淡）。 */
	var CRYSTAL_PILLAR_GLOW_ALPHA = .5;
	/** 晶柱：藍紫水晶柱，淡淡的外光（模糊 10）、金色底座（擋視線）。 */
	function crystalPillar(ctx) {
		const c = T$2 / 2;
		ctx.fillStyle = "rgba(0,0,0,0.3)";
		ctx.beginPath();
		ctx.moveTo(20, 46);
		ctx.lineTo(32, 46);
		ctx.lineTo(48, 52);
		ctx.lineTo(34, 52);
		ctx.fill();
		roundRect(ctx, 15, 40, 22, 8, 2);
		ctx.fillStyle = CRYSTAL.slab;
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$1;
		ctx.stroke();
		ctx.save();
		ctx.shadowColor = rgba(CRYSTAL.glint, CRYSTAL_PILLAR_GLOW_ALPHA);
		ctx.shadowBlur = 10;
		ctx.beginPath();
		ctx.moveTo(18, 41);
		ctx.lineTo(17, 14);
		ctx.lineTo(c, 2);
		ctx.lineTo(35, 14);
		ctx.lineTo(34, 41);
		ctx.closePath();
		ctx.fillStyle = "#a898ff";
		ctx.fill();
		ctx.restore();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$1;
		ctx.stroke();
		ctx.fillStyle = "rgba(255,255,255,0.35)";
		ctx.beginPath();
		ctx.moveTo(21, 38);
		ctx.lineTo(20, 15);
		ctx.lineTo(c, 6);
		ctx.lineTo(25, 38);
		ctx.fill();
		ctx.fillStyle = "rgba(0,0,0,0.18)";
		ctx.beginPath();
		ctx.moveTo(28, 38);
		ctx.lineTo(27, 6);
		ctx.lineTo(34, 15);
		ctx.lineTo(33, 38);
		ctx.fill();
		roundRect(ctx, 15, 38, 22, 4, 1);
		ctx.fillStyle = CRYSTAL.gold;
		ctx.fill();
		ctx.lineWidth = 1.5;
		ctx.strokeStyle = OUT$1;
		ctx.stroke();
	}
	/** 晶冠的物件畫法（物件 ID → 畫法）；需求第 3 節只有晶柱。 */
	var CRYSTAL_OBJECTS = { stone_pillar: crystalPillar };
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/frostObjects.ts
	var T$1 = 52;
	var OUT = FROST.outline;
	var LW = 2;
	function box(ctx, x, y, w, h, fill, r = 2) {
		roundRect(ctx, x, y, w, h, r);
		ctx.fillStyle = fill;
		ctx.fill();
		ctx.lineWidth = LW;
		ctx.strokeStyle = OUT;
		ctx.stroke();
	}
	/** 漁貨箱：箱面畫一條魚的線稿（半掩護、可燃）。 */
	function fishCrate(ctx) {
		shadowEllipse(ctx, 29, 33, T$1 * .34, T$1 * .28);
		const s = T$1 * .62;
		const o = 19.759999999999998 / 2;
		box(ctx, o, o, s, s, "#9a8460", 3);
		ctx.strokeStyle = "rgba(40,30,16,0.5)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		for (const k of [1, 3]) {
			ctx.moveTo(11.879999999999999, o + s * k / 4);
			ctx.lineTo(40.120000000000005, o + s * k / 4);
		}
		ctx.stroke();
		ctx.strokeStyle = "#f2ead8";
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		ctx.ellipse(T$1 / 2 - 2, T$1 / 2, 7, 3.5, 0, 0, TAU);
		ctx.moveTo(31, T$1 / 2);
		ctx.lineTo(36, T$1 / 2 - 4);
		ctx.lineTo(36, 30);
		ctx.closePath();
		ctx.stroke();
	}
	/** 防波石堤的色盤（灰藍石；共用矮牆外框規則，外框 2px）。 */
	var FROST_LOW_WALL = {
		top: "#8a989c",
		topEdge: "#b8c6ca",
		face: "#5a6a70",
		mortar: "#34404a",
		outline: OUT
	};
	/** 防波石堤：灰藍石的矮牆，正面一排浪花白點（畫在正面內，不比矮牆頂高）。 */
	function breakwater(ctx, s) {
		drawLowWall(ctx, s, FROST_LOW_WALL);
		const x0 = s.joinL ? 0 : 4;
		const x1 = s.joinR ? T$1 : 48;
		const y = 33.44;
		ctx.fillStyle = "rgba(255,255,255,0.75)";
		for (let k = 6; k < 49; k += 9) {
			if (k < x0 + 3 || k > x1 - 3) continue;
			ctx.beginPath();
			ctx.arc(k, y, 2, 0, TAU);
			ctx.fill();
		}
	}
	/** 珊瑚礁柱：不規則的岩柱，長著珊瑚枝（擋視線，畫到格頂）。 */
	function coralPillar(ctx) {
		const c = T$1 / 2;
		ctx.fillStyle = "rgba(0,0,0,0.3)";
		ctx.beginPath();
		ctx.moveTo(20, 46);
		ctx.lineTo(32, 46);
		ctx.lineTo(48, 52);
		ctx.lineTo(34, 52);
		ctx.fill();
		box(ctx, 15, 40, 22, 8, "#5a6a70");
		ctx.beginPath();
		ctx.moveTo(17, 41);
		ctx.quadraticCurveTo(15, 22, 20, 6);
		ctx.quadraticCurveTo(c, 1, 32, 6);
		ctx.quadraticCurveTo(37, 22, 35, 41);
		ctx.closePath();
		ctx.fillStyle = FROST.reef;
		ctx.fill();
		ctx.lineWidth = LW;
		ctx.strokeStyle = OUT;
		ctx.stroke();
		ctx.fillStyle = "rgba(0,0,0,0.22)";
		ctx.fillRect(29, 12, 5, 28);
		const branches = () => {
			ctx.beginPath();
			ctx.moveTo(22, 20);
			ctx.lineTo(16, 14);
			ctx.moveTo(19, 17);
			ctx.lineTo(19, 11);
			ctx.moveTo(29, 30);
			ctx.lineTo(36, 25);
			ctx.stroke();
		};
		ctx.lineCap = "round";
		ctx.strokeStyle = OUT;
		ctx.lineWidth = 2.5 + LW;
		branches();
		ctx.strokeStyle = FROST.coral;
		ctx.lineWidth = 2.5;
		branches();
		for (const [dx, dy] of [
			[-3, 34],
			[1, 14],
			[4, 22]
		]) dot(ctx, c + dx, dy, 1.2, "rgba(255,255,255,0.4)");
	}
	/** 鯨油桶：深色木桶，藍灰色鐵箍；貼四區共用的危險記號（會爆）。 */
	function whaleOilBarrel(ctx) {
		shadowEllipse(ctx, 29, 34, T$1 * .3, T$1 * .24);
		const cx = T$1 / 2;
		const bot = 42;
		const w = 16;
		ctx.beginPath();
		ctx.moveTo(10, 14);
		ctx.lineTo(10, bot);
		ctx.ellipse(cx, bot, w, 5, 0, Math.PI, 0, true);
		ctx.lineTo(42, 14);
		ctx.closePath();
		ctx.fillStyle = "#6a5a40";
		ctx.fill();
		ctx.lineWidth = LW;
		ctx.strokeStyle = OUT;
		ctx.stroke();
		ctx.fillStyle = "rgba(0,0,0,0.22)";
		ctx.fillRect(32.4, 14, w * .55, 30);
		ctx.strokeStyle = "#2a3a4a";
		ctx.lineWidth = 2.5;
		for (const y of [21, 35]) {
			ctx.beginPath();
			ctx.moveTo(10, y);
			ctx.quadraticCurveTo(cx, y + 4, 42, y);
			ctx.stroke();
		}
		ctx.beginPath();
		ctx.ellipse(cx, 14, w, 5, 0, 0, TAU);
		ctx.fillStyle = "#8a7650";
		ctx.fill();
		ctx.lineWidth = LW;
		ctx.strokeStyle = OUT;
		ctx.stroke();
		hazardMark(ctx, 23, 34, 6.5);
	}
	/** 漂流木：灰白色木頭（半掩護、可燃）。 */
	function driftwood(ctx) {
		shadowEllipse(ctx, 28, 35, T$1 * .42, T$1 * .14);
		box(ctx, 6, T$1 / 2 - 4, 40, 13, "#a8a090", 6);
		ctx.strokeStyle = "rgba(60,56,48,0.5)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		ctx.moveTo(10, 27);
		ctx.lineTo(36, 26);
		ctx.moveTo(14, 31);
		ctx.lineTo(40, 31);
		ctx.stroke();
		ctx.fillStyle = "rgba(255,255,255,0.25)";
		ctx.fillRect(8, 24, 32, 2);
		ctx.beginPath();
		ctx.ellipse(44, 28.5, 4, 6.5, 0, 0, TAU);
		ctx.fillStyle = "#d8d0c0";
		ctx.fill();
		ctx.lineWidth = LW;
		ctx.strokeStyle = OUT;
		ctx.stroke();
	}
	/** 海草叢（隱蔽、可燃）：一叢彎曲的高海草；每片草葉先描 2px 深色外框。 */
	function kelpTuft(ctx, s) {
		const r = rng(s.x, s.y, 511);
		shadowEllipse(ctx, 28, T$1 * .74, T$1 * .36, T$1 * .12);
		const blades = [];
		for (let i = 0; i < 14; i++) {
			const x = 10 + r() * 32;
			const h = 14 + r() * 16;
			blades.push([
				x,
				h,
				(r() - .5) * 6,
				i % 3 === 0 ? "#1e5a44" : "#3a8a6a"
			]);
		}
		const y = T$1 * .72;
		ctx.lineCap = "round";
		for (const pass of [0, 1]) for (const [x, h, tip, color] of blades) {
			ctx.strokeStyle = pass === 0 ? OUT : color;
			ctx.lineWidth = pass === 0 ? 2.6 + LW : 2.6;
			ctx.beginPath();
			ctx.moveTo(x, y);
			ctx.bezierCurveTo(x - 5, y - h * .3, x + 5, y - h * .6, x + tip, y - h);
			ctx.stroke();
		}
	}
	/** 碼頭棧道：兩側有樁、繩索，中間木板（可燃、可破）。沿南北方向畫，東西向時轉 90°。 */
	function pier(ctx, s) {
		ctx.save();
		if (!s.vertical) {
			ctx.translate(T$1, 0);
			ctx.rotate(Math.PI / 2);
		}
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		ctx.fillRect(9, 0, 40, T$1);
		for (let y = 1; y < T$1; y += 8) box(ctx, 8, y, 36, 6.5, shade("#9a8460", .9 + y * 7 % 10 / 50), 1);
		ctx.strokeStyle = "#c8b48a";
		ctx.lineWidth = 1.6;
		ctx.beginPath();
		for (const x of [5, 47]) {
			ctx.moveTo(x, 0);
			ctx.lineTo(x, T$1);
		}
		ctx.stroke();
		for (const y of [0, 44]) {
			box(ctx, 3, y, 6, 8, "#5a4a36", 1);
			box(ctx, 43, y, 6, 8, "#5a4a36", 1);
		}
		ctx.restore();
	}
	/** 斷桅：桅杆、橫桁、破帆（擋視線，畫到格頂；可燃、可推倒）。 */
	function brokenMast(ctx) {
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		ctx.beginPath();
		ctx.ellipse(29, 46, 12, 4, 0, 0, TAU);
		ctx.fill();
		box(ctx, 23, 4, 6, 42, "#7a6448", 1);
		ctx.beginPath();
		ctx.moveTo(23, 4);
		ctx.lineTo(25, 1);
		ctx.lineTo(27, 4);
		ctx.lineTo(29, 0);
		ctx.lineWidth = LW;
		ctx.strokeStyle = OUT;
		ctx.stroke();
		box(ctx, 10, 13, 32, 4, "#7a6448", 1);
		ctx.beginPath();
		ctx.moveTo(12, 17);
		ctx.lineTo(38, 17);
		ctx.lineTo(34, 30);
		ctx.lineTo(28, 26);
		ctx.lineTo(22, 33);
		ctx.lineTo(14, 28);
		ctx.closePath();
		ctx.fillStyle = "#e8e0cc";
		ctx.fill();
		ctx.lineWidth = LW;
		ctx.strokeStyle = OUT;
		ctx.stroke();
		ctx.strokeStyle = "rgba(60,50,40,0.6)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		ctx.moveTo(10, 15);
		ctx.lineTo(20, 44);
		ctx.stroke();
	}
	/** 霜潮海境的物件畫法（物件 ID → 畫法）；需求第 5 節九種物件中的八種（`thin_ice` 同預設，不在表內）。 */
	var FROST_OBJECTS = {
		crate: fishCrate,
		low_wall: breakwater,
		stone_pillar: coralPillar,
		oil_barrel: whaleOilBarrel,
		fallen_log: driftwood,
		grass: kelpTuft,
		wooden_bridge: pier,
		dead_tree: brokenMast
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/objectArt.ts
	var T = 52;
	function crate(ctx) {
		shadowEllipse(ctx, T / 2 + 3, T / 2 + 5, T * .34, T * .3);
		const s = T * .62;
		const o = (T - s) / 2;
		roundRect(ctx, o, o, s, s, 3);
		ctx.fillStyle = PAL.wood;
		ctx.fill();
		ctx.lineWidth = 2.5;
		ctx.strokeStyle = PAL.woodDark;
		ctx.stroke();
		ctx.strokeStyle = PAL.woodMid;
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		for (let i = 1; i < 3; i++) {
			ctx.moveTo(o + 2, o + s * i / 3);
			ctx.lineTo(o + s - 2, o + s * i / 3);
		}
		ctx.stroke();
		ctx.strokeStyle = PAL.woodDark;
		ctx.lineWidth = 3;
		ctx.beginPath();
		ctx.moveTo(o + 3, o + 3);
		ctx.lineTo(o + s - 3, o + s - 3);
		ctx.stroke();
		ctx.fillStyle = "rgba(255,255,255,0.18)";
		ctx.fillRect(o + 2, o + 2, s - 4, 3);
	}
	function oilBarrel(ctx) {
		shadowEllipse(ctx, T / 2 + 3, T / 2 + 5, T * .3, T * .28);
		const c = T / 2;
		const r = T * .29;
		ctx.fillStyle = "#4a2a12";
		roundRect(ctx, c - r, c - r + 4, r * 2, r * 2, r);
		ctx.fill();
		ctx.fillStyle = "#8a5228";
		ctx.beginPath();
		ctx.arc(c, c, r, 0, TAU);
		ctx.fill();
		ctx.strokeStyle = "rgba(60,32,12,0.55)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		for (let k = -2; k <= 2; k++) {
			const half = Math.sqrt(r * r - (k * r * .36) ** 2);
			ctx.moveTo(c + k * r * .36, c - half + 1);
			ctx.lineTo(c + k * r * .36, c + half - 1);
		}
		ctx.stroke();
		ctx.lineWidth = 3;
		ctx.strokeStyle = "#9aa0a8";
		ctx.beginPath();
		ctx.arc(c, c, r - 1.5, 0, TAU);
		ctx.stroke();
		ctx.save();
		ctx.beginPath();
		ctx.arc(c, c, r * .5, 0, TAU);
		ctx.clip();
		ctx.fillStyle = "#f2b33d";
		ctx.fillRect(c - r, c - r, r * 2, r * 2);
		ctx.fillStyle = "#1a120a";
		ctx.beginPath();
		ctx.moveTo(c, c - 5.5);
		ctx.bezierCurveTo(c + 5, c + .5, c + 4, c + 5, c, c + 5);
		ctx.bezierCurveTo(c - 4, c + 5, c - 5, c + .5, c, c - 5.5);
		ctx.fill();
		ctx.restore();
	}
	function stonePillar(ctx) {
		const c = T / 2;
		const r = T * .3;
		const oct = (cx, cy, rad) => {
			ctx.beginPath();
			for (let k = 0; k < 8; k++) {
				const a = k / 8 * TAU + Math.PI / 8;
				ctx.lineTo(cx + Math.cos(a) * rad, cy + Math.sin(a) * rad);
			}
			ctx.closePath();
		};
		ctx.fillStyle = "rgba(0,0,0,0.3)";
		ctx.beginPath();
		ctx.moveTo(c - r * .7, c + r * .7);
		ctx.lineTo(c + r * .7, c - r * .7);
		ctx.lineTo(c + r * .7 + 12, c - r * .7 + 12);
		ctx.lineTo(c - r * .7 + 12, c + r * .7 + 12);
		ctx.fill();
		oct(c + 12, c + 12, r);
		ctx.fill();
		ctx.fillStyle = PAL.rockDark;
		oct(c, c + 5, r);
		ctx.fill();
		ctx.fillRect(c - r * .92, c, r * 1.84, 5);
		ctx.fillStyle = PAL.rock;
		oct(c, c, r);
		ctx.fill();
		ctx.fillStyle = "#bdb9af";
		oct(c, c, r * .62);
		ctx.fill();
		ctx.strokeStyle = "rgba(80,76,70,0.7)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		ctx.moveTo(c - 3, c - r + 2);
		ctx.lineTo(c + 1, c - 5);
		ctx.lineTo(c - 2, c + 2);
		ctx.stroke();
	}
	function lowWall(ctx, s) {
		drawLowWall(ctx, s);
	}
	function woodenBridge(ctx, s) {
		ctx.save();
		if (s.vertical) {
			ctx.translate(T, 0);
			ctx.rotate(Math.PI / 2);
		}
		ctx.fillStyle = "#7a5028";
		ctx.fillRect(0, 7, T, T - 14);
		ctx.strokeStyle = "#4b2f15";
		ctx.lineWidth = 1.5;
		for (let px = 0; px <= T; px += T / 6) {
			ctx.beginPath();
			ctx.moveTo(px, 8);
			ctx.lineTo(px, T - 8);
			ctx.stroke();
		}
		const r = rng(s.x, s.y, 30);
		for (let px = 0; px < T; px += T / 6) {
			ctx.fillStyle = `rgba(255,220,170,${.05 + r() * .12})`;
			ctx.fillRect(px + 1, 8, T / 6 - 2, T - 16);
		}
		ctx.fillStyle = "#4b2f15";
		ctx.fillRect(0, 4, T, 4);
		ctx.fillRect(0, T - 8, T, 4);
		ctx.restore();
	}
	function fallenLog(ctx) {
		ctx.save();
		ctx.translate(T / 2, T / 2);
		ctx.rotate(-.5);
		ctx.fillStyle = "rgba(0,0,0,0.28)";
		roundRect(ctx, -T * .4 + 3, -1, T * .8, 15, 7);
		ctx.fill();
		ctx.fillStyle = "#7a5130";
		roundRect(ctx, -T * .4, -8, T * .8, 16, 8);
		ctx.fill();
		ctx.strokeStyle = "#4e3119";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		ctx.moveTo(-T * .3, -3);
		ctx.lineTo(T * .1, -3);
		ctx.moveTo(-T * .2, 3);
		ctx.lineTo(T * .2, 3);
		ctx.stroke();
		ctx.fillStyle = "#d1a86e";
		ctx.beginPath();
		ctx.ellipse(T * .36, 0, 5, 8, 0, 0, TAU);
		ctx.fill();
		ctx.strokeStyle = "#8a6038";
		ctx.beginPath();
		ctx.ellipse(T * .36, 0, 2.5, 4.5, 0, 0, TAU);
		ctx.stroke();
		ctx.restore();
	}
	function earthWall(ctx) {
		shadowEllipse(ctx, T / 2 + 3, T / 2 + 6, T * .42, T * .3);
		roundRect(ctx, 5, 9, T - 10, T - 16, 10);
		ctx.fillStyle = "#8a6a45";
		ctx.fill();
		ctx.fillStyle = "#a7845a";
		roundRect(ctx, 8, 9, T - 16, T * .35, 8);
		ctx.fill();
		ctx.strokeStyle = "#5e4529";
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		ctx.moveTo(9, T * .58);
		ctx.lineTo(T - 9, T * .55);
		ctx.moveTo(10, T * .7);
		ctx.lineTo(T - 12, T * .72);
		ctx.stroke();
	}
	function deadTree(ctx) {
		shadowEllipse(ctx, T / 2 + 4, T / 2 + 5, T * .36, T * .3);
		ctx.strokeStyle = "#4a3624";
		ctx.lineCap = "round";
		const branch = (x, y, a, len, w, depth) => {
			const x2 = x + Math.cos(a) * len;
			const y2 = y + Math.sin(a) * len;
			ctx.lineWidth = w;
			ctx.beginPath();
			ctx.moveTo(x, y);
			ctx.lineTo(x2, y2);
			ctx.stroke();
			if (depth > 0) {
				branch(x2, y2, a - .5, len * .6, w * .6, depth - 1);
				branch(x2, y2, a + .6, len * .55, w * .6, depth - 1);
			}
		};
		for (let k = 0; k < 5; k++) branch(T / 2, T / 2, k / 5 * TAU + .3, T * .2, 4, 1);
		ctx.fillStyle = "#5c4430";
		ctx.beginPath();
		ctx.arc(T / 2, T / 2, 6, 0, TAU);
		ctx.fill();
	}
	var lastTurn = (s) => s.turnsLeft !== null && s.turnsLeft <= 1;
	function softShadow(ctx, cx, cy, rx, ry, a = .32) {
		ctx.fillStyle = `rgba(0,0,0,${a})`;
		ctx.beginPath();
		ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
		ctx.fill();
	}
	/** 冰牆：半透明的冰晶塊（有高度、擋視線）；最後一回合開始融化（滴水、變透明、頂部變圓）。 */
	function iceWall(ctx, s) {
		const melting = lastTurn(s);
		softShadow(ctx, T / 2 + 3, T * .82, T * .38, T * .12, .35);
		const a = melting ? .62 : .85;
		const top = melting ? T * .14 : T * .04;
		const base = T * .84;
		const l = T * .12;
		const rr = T * .88;
		const pts = melting ? [
			[l, base],
			[l, top + 16],
			[l + 8, top + 6],
			[T * .42, top + 2],
			[T * .6, top + 8],
			[rr - 6, top + 10],
			[rr, top + 20],
			[rr, base]
		] : [
			[l, base],
			[l, top + 14],
			[l + 6, top + 4],
			[T * .34, top + 12],
			[T * .5, top],
			[T * .66, top + 10],
			[rr - 5, top + 6],
			[rr, top + 16],
			[rr, base]
		];
		ctx.save();
		ctx.beginPath();
		pts.forEach(([px, py], i) => i ? ctx.lineTo(px, py) : ctx.moveTo(px, py));
		ctx.closePath();
		const g = ctx.createLinearGradient(l, top, rr, base);
		g.addColorStop(0, rgba("#e8fbff", a));
		g.addColorStop(.5, rgba("#8fd8f0", a));
		g.addColorStop(1, rgba("#3f9cc8", a));
		ctx.fillStyle = g;
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = "#163a52";
		ctx.stroke();
		ctx.clip();
		ctx.strokeStyle = rgba("#ffffff", .75);
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.moveTo(l + 7, base - 6);
		ctx.lineTo(l + 13, top + 14);
		ctx.moveTo(T * .5, base - 4);
		ctx.lineTo(T * .47, top + 8);
		ctx.stroke();
		ctx.strokeStyle = rgba("#1d5f86", .5);
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		ctx.moveTo(T * .34, top + 12);
		ctx.lineTo(T * .36, base);
		ctx.moveTo(T * .66, top + 10);
		ctx.lineTo(T * .64, base);
		ctx.stroke();
		ctx.restore();
		if (melting) {
			ctx.fillStyle = rgba("#4aa3ff", .55);
			ctx.beginPath();
			ctx.ellipse(T / 2, base + 2, T * .42, 4, 0, 0, TAU);
			ctx.fill();
			ctx.fillStyle = "#bfefff";
			for (const [dx, dy] of [
				[.2, .62],
				[.55, .7],
				[.8, .58]
			]) {
				ctx.beginPath();
				ctx.ellipse(dx * T, dy * T, 1.6, 2.6, 0, 0, TAU);
				ctx.fill();
			}
		}
	}
	/** 荊棘叢：一團交纏的藤蔓＋尖刺＋小紅花；最後一回合枯萎（褐色、刺變少、沒有花）。 */
	function thornWall(ctx, s) {
		const dry = lastTurn(s);
		const r = rng(s.x, s.y, 3);
		softShadow(ctx, T / 2 + 2, T * .74, T * .4, T * .14);
		const vine = dry ? "#7a5a30" : "#3f6a26";
		const vineHi = dry ? "#a07a44" : "#6aa040";
		ctx.fillStyle = dry ? "#3a2a16" : "#1e3412";
		ctx.beginPath();
		ctx.ellipse(T / 2, T * .56, T * .42, T * .24, 0, 0, TAU);
		ctx.fill();
		ctx.lineCap = "round";
		for (let i = 0; i < 7; i++) {
			const sx = 6 + r() * (T - 12);
			const sy = T * .72;
			const ex = 6 + r() * (T - 12);
			const ey = T * .3 + r() * 8;
			ctx.strokeStyle = i % 2 ? vine : vineHi;
			ctx.lineWidth = 3;
			ctx.beginPath();
			ctx.moveTo(sx, sy);
			ctx.quadraticCurveTo(r() * T, T * (.2 + r() * .3), ex, ey);
			ctx.stroke();
			const n = dry ? 1 : 3;
			for (let k = 0; k < n; k++) {
				const tt = .25 + k * .25;
				const px = sx + (ex - sx) * tt;
				const py = sy + (ey - sy) * tt;
				ctx.fillStyle = dry ? "#d8c8a0" : "#f2ecd0";
				ctx.beginPath();
				ctx.moveTo(px - 2, py);
				ctx.lineTo(px, py - 6);
				ctx.lineTo(px + 2, py);
				ctx.fill();
			}
		}
		if (!dry) {
			ctx.fillStyle = "#c84a6a";
			for (let i = 0; i < 2; i++) {
				ctx.beginPath();
				ctx.arc(12 + r() * (T - 24), T * .38 + r() * 10, 2.4, 0, TAU);
				ctx.fill();
			}
		}
	}
	/** 倒塌物：大小石塊堆成的一堆（深色外框＋頂面亮色），一看就是「擋路、可躲」。 */
	function rubble(ctx, s) {
		const r = rng(s.x, s.y, 5);
		softShadow(ctx, T / 2 + 3, T * .74, T * .42, T * .15, .4);
		for (const [rx, ry, size] of [
			[
				.3,
				.62,
				11
			],
			[
				.62,
				.64,
				12
			],
			[
				.46,
				.46,
				12
			],
			[
				.76,
				.5,
				8
			],
			[
				.2,
				.46,
				8
			],
			[
				.5,
				.7,
				7
			]
		]) {
			const cx = rx * T;
			const cy = ry * T;
			const n = 5 + Math.floor(r() * 2);
			const pts = [];
			for (let i = 0; i < n; i++) {
				const ang = i / n * TAU + r() * .5;
				const rad = size * (.75 + r() * .3);
				pts.push([cx + Math.cos(ang) * rad, cy + Math.sin(ang) * rad * .8]);
			}
			ctx.beginPath();
			pts.forEach(([px, py], i) => i ? ctx.lineTo(px, py) : ctx.moveTo(px, py));
			ctx.closePath();
			ctx.fillStyle = "#8d8376";
			ctx.fill();
			ctx.lineWidth = 2;
			ctx.strokeStyle = "#2a241d";
			ctx.stroke();
			ctx.fillStyle = "#b9ae9c";
			ctx.beginPath();
			ctx.ellipse(cx - size * .15, cy - size * .3, size * .5, size * .28, -.3, 0, TAU);
			ctx.fill();
		}
		ctx.fillStyle = "#6e665b";
		for (let i = 0; i < 6; i++) ctx.fillRect(6 + r() * (T - 12), T * .72 + r() * 8, 2.5, 2);
	}
	/** 薄冰：架在冰窟上的冰板；裂痕隨 HP 增加（級距 0／1／2 → 2／4／7 道），最後露出底下的黑水。 */
	function thinIce(ctx, s) {
		const stage = s.hpStage;
		ctx.fillStyle = "#0e2a44";
		ctx.fillRect(0, 0, T, T);
		const r = rng(s.x, s.y, 9);
		ctx.beginPath();
		ctx.roundRect(3, 3, T - 6, T - 6, 8);
		ctx.fillStyle = rgba("#cdeeff", stage === 2 ? .62 : .85);
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = "#e8fbff";
		ctx.stroke();
		ctx.fillStyle = rgba("#0e2a44", .25);
		ctx.beginPath();
		ctx.ellipse(T / 2, T / 2, T * .26, T * .2, .3, 0, TAU);
		ctx.fill();
		const rays = stage === 0 ? 2 : stage === 1 ? 4 : 7;
		ctx.strokeStyle = stage === 2 ? "#0e2a44" : "#4a7a9a";
		ctx.lineWidth = stage === 2 ? 2 : 1.3;
		ctx.beginPath();
		for (let i = 0; i < rays; i++) {
			const ang = i / rays * TAU + r();
			let px = T / 2;
			let py = T / 2;
			ctx.moveTo(px, py);
			for (let k = 0; k < 3; k++) {
				px += Math.cos(ang + (r() - .5) * .8) * 7;
				py += Math.sin(ang + (r() - .5) * .8) * 7;
				ctx.lineTo(px, py);
			}
		}
		ctx.stroke();
		if (stage === 2) {
			ctx.fillStyle = "#081a2c";
			ctx.beginPath();
			ctx.moveTo(T * .44, T * .42);
			ctx.lineTo(T * .58, T * .44);
			ctx.lineTo(T * .56, T * .58);
			ctx.lineTo(T * .42, T * .55);
			ctx.fill();
		}
	}
	function grassFloor(ctx, s) {
		const r = rng(s.x, s.y, 43);
		shadowEllipse(ctx, T / 2 + 2, T * .78, T * .36, T * .12);
		const clumps = 3 + Math.floor(r() * 2);
		for (let i = 0; i < clumps; i++) {
			const bx = T * (.22 + .56 * i / (clumps - 1)) + (r() - .5) * 4;
			const by = T * (.74 + i % 2 * .04);
			const blades = 6 + Math.floor(r() * 3);
			for (let b = 0; b < blades; b++) {
				const lean = (b / (blades - 1) * 2 - 1) * 9 + (r() - .5) * 3;
				const h = 20 + r() * 8 - Math.abs(lean) * .5;
				ctx.fillStyle = b % 3 === 0 ? PAL.grassLight : PAL.bush;
				ctx.beginPath();
				ctx.moveTo(bx + (b - blades / 2) * 1.1 - 1.6, by);
				ctx.quadraticCurveTo(bx + lean * .5, by - h * .6, bx + lean, by - h);
				ctx.quadraticCurveTo(bx + lean * .5 + 2, by - h * .5, bx + (b - blades / 2) * 1.1 + 1.6, by);
				ctx.closePath();
				ctx.fill();
			}
		}
	}
	var OBJECT_DRAW = {
		crate,
		oil_barrel: oilBarrel,
		stone_pillar: stonePillar,
		low_wall: lowWall,
		wooden_bridge: woodenBridge,
		fallen_log: fallenLog,
		earth_wall: earthWall,
		dead_tree: deadTree,
		ice_wall: iceWall,
		thorn_wall: thornWall,
		rubble,
		thin_ice: thinIce,
		grass: grassFloor
	};
	/** 各區的物件畫法（區域 ID → 物件 ID → 畫法）；預設區不在表內。雲嶺（3-37b）、灰燼荒原與晶冠點綴（5A-ART6）、魔導樞市與霜潮海境（5A-ART7）已加入。 */
	var REGION_OBJECT_DRAW = {
		cloud_ridge: CLOUD_OBJECTS,
		ashen_waste: ASHEN_OBJECTS,
		crystal_crown: CRYSTAL_OBJECTS,
		arcane_hub: ARCANE_OBJECTS,
		frost_tide: FROST_OBJECTS
	};
	/** `look` 覆寫的物件畫法（`"鍵=值"` → 物件 ID → 畫法）；目前沒有。 */
	var LOOK_OBJECT_DRAW = {};
	/** 沒有畫法的新物件：灰色六角形（不會出錯；字由繪圖端疊上）。 */
	function drawGenericObject(ctx) {
		ctx.fillStyle = "#888";
		ctx.beginPath();
		for (let k = 0; k < 6; k++) {
			const a = k / 6 * TAU;
			ctx.lineTo(T / 2 + Math.cos(a) * 16, T / 2 + Math.sin(a) * 16);
		}
		ctx.closePath();
		ctx.fill();
	}
	/** 受損裂痕的顏色與範圍（比例）；沒列的物件用預設。薄冰自己畫裂痕（依級距），不套通用裂痕。 */
	var CRACKS = {
		ice_wall: {
			color: "#123048",
			box: [
				.2,
				.15,
				.8,
				.8
			]
		},
		thorn_wall: { color: "#140c06" },
		rubble: { color: "#1a1612" }
	};
	function drawObject(ctx, s) {
		(pickThemed(s, s.kind, REGION_OBJECT_DRAW, LOOK_OBJECT_DRAW) ?? OBJECT_DRAW[s.kind] ?? drawGenericObject)(ctx, s);
		if (s.hpStage > 0 && s.kind !== "thin_ice") {
			const style = CRACKS[s.kind];
			cracks(ctx, s.hpStage, s.x, s.y, style?.color, style?.box);
		}
	}
	var LETHAL_CORNER_WIDTH = 1.5;
	/** 角標的透明度；滑過、預覽、選目標時整格淡紅的透明度（同現在的危險區色）。 */
	var LETHAL_CORNER_ALPHA = .85;
	/** 四角角標的折線（格子像素；`t` 是格子邊長）。 */
	function lethalCornerPaths(t, size = 6, inset = 2) {
		const a = inset;
		const b = t - inset;
		return [
			[
				a,
				a + size,
				a,
				a,
				a + size,
				a
			],
			[
				b - size,
				a,
				b,
				a,
				b,
				a + size
			],
			[
				b,
				b - size,
				b,
				b,
				b - size,
				b
			],
			[
				a + size,
				b,
				a,
				b,
				a,
				b - size
			]
		];
	}
	/** 共用每個角的另外 3 格（橫、直、斜）的位移；順序同 `lethalCornerPaths`。 */
	var CORNER_NEIGHBORS = [
		[
			[-1, 0],
			[0, -1],
			[-1, -1]
		],
		[
			[1, 0],
			[0, -1],
			[1, -1]
		],
		[
			[1, 0],
			[0, 1],
			[1, 1]
		],
		[
			[-1, 0],
			[0, 1],
			[-1, 1]
		]
	];
	/**
	* 6V-2b（`docs/archive/art/6V-2檢查.md` 2.1）：角標只描致命區的外輪廓。一個角只在共用它的 3 格裡有「非致命格」時才畫；
	* 3 格都是致命就不畫（大片區內部沒有角標，不會拼成紅十字網格）。地圖外不是格子，不算非致命格。
	* `nonDeadly(x, y)` 回傳這一格在地圖內且不是致命格。
	*/
	function lethalCornerMask(nonDeadly, x, y) {
		const m = CORNER_NEIGHBORS.map((ns) => ns.some(([dx, dy]) => nonDeadly(x + dx, y + dy)));
		return [
			m[0] === true,
			m[1] === true,
			m[2] === true,
			m[3] === true
		];
	}
	/** 高 h（可為補間中的小數）的格子往上抬多少模型像素；負值視為 0。 */
	function tileLift(h) {
		return Math.max(0, h) * 6;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/heightShapes.ts
	/** 崖面漸層的上下色（第 5 節第 2 條）、崖頂亮唇、外側暗線。 */
	var CLIFF_TOP = 7033398;
	var CLIFF_BOTTOM = 4864036;
	var RIM = {
		color: 16775383,
		alpha: .8
	};
	var EDGE = {
		color: 1643018,
		alpha: .85
	};
	/** 兩個 0xRRGGBB 顏色的線性插值。 */
	function mixColor(a, b, t) {
		const k = Math.max(0, Math.min(1, t));
		const ch = (shift) => Math.round((a >> shift & 255) * (1 - k) + (b >> shift & 255) * k);
		return ch(16) << 16 | ch(8) << 8 | ch(0);
	}
	/** 崖面上每一階的 1px 暗線位置（相對崖頂；高 `lift` 像素的崖面每 RAISE 一條，不含頂與底）。 */
	function strataLines(lift) {
		const out = [];
		for (let y = 6; y < lift - .5; y += 6) out.push(y);
		return out;
	}
	//#endregion
	//#region entry.ts
	window.QFieldLive = {
		drawTile,
		drawObject,
		ART_T: 52,
		lethalCornerPaths,
		lethalCornerMask,
		LETHAL_CORNER_WIDTH,
		LETHAL_CORNER_ALPHA,
		CLIFF_TOP,
		CLIFF_BOTTOM,
		RIM,
		EDGE,
		mixColor,
		strataLines,
		HEIGHT_MARK_BG: {
			x: 3,
			y: 3,
			w: 19,
			h: 13,
			r: 4
		},
		HEIGHT_MARK_TRI: [
			6,
			13,
			9.5,
			6,
			13,
			13
		],
		HEIGHT_MARK_NUM: {
			x: 14,
			y: 4
		},
		MIN_HEIGHT_BADGE_FONT_PX: 10,
		RAISE: 6,
		tileLift,
		HIGHLIGHT
	};
	//#endregion
})();
