// 自動產生：遊戲目前的畫法（client/src/render 的 terrainArt、objectArt、skillIcon 打包成 IIFE，main 5be3c27），只給樣張的「現況」欄比對用。
(function() {
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-5ea9fb/client/src/render/artPalette.ts
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
		fire: "#ff7a1a",
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
	function hexRgb(h) {
		const n = parseInt(h.slice(1), 16);
		return [
			n >> 16 & 255,
			n >> 8 & 255,
			n & 255
		];
	}
	/** 把亮度乘上 `f`，回傳 CSS 顏色。 */
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-5ea9fb/client/src/render/artDraw.ts
	var TAU$3 = Math.PI * 2;
	function roundRect(ctx, x, y, w, h, r) {
		ctx.beginPath();
		ctx.roundRect(x, y, w, h, r);
	}
	function flame(ctx, x, y, h) {
		const w = h * .55;
		ctx.fillStyle = "#ff8a1e";
		ctx.beginPath();
		ctx.moveTo(x, y - h);
		ctx.bezierCurveTo(x + w, y - h * .4, x + w, y, x, y);
		ctx.bezierCurveTo(x - w, y, x - w, y - h * .4, x, y - h);
		ctx.fill();
		ctx.fillStyle = "#ffe07a";
		ctx.beginPath();
		ctx.moveTo(x, y - h * .55);
		ctx.bezierCurveTo(x + w * .5, y - h * .2, x + w * .45, y, x, y);
		ctx.bezierCurveTo(x - w * .45, y, x - w * .5, y - h * .2, x, y - h * .55);
		ctx.fill();
	}
	function shadowEllipse(ctx, cx, cy, rx, ry) {
		ctx.fillStyle = "rgba(0,0,0,0.28)";
		ctx.beginPath();
		ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU$3);
		ctx.fill();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-5ea9fb/client/src/render/artRandom.ts
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
		let a = hash(x, y, salt);
		return () => {
			a = a + 1831565813 | 0;
			let t = Math.imul(a ^ a >>> 15, 1 | a);
			t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
			return ((t ^ t >>> 14) >>> 0) / 4294967296;
		};
	}
	var T$1 = 52;
	function drawStone(ctx, s) {
		const r = rng(s.x, s.y, 1);
		ctx.fillStyle = PAL.stoneGap;
		ctx.fillRect(0, 0, T$1, T$1);
		const slabs = [];
		const splitV = r() < .5;
		const cut = .35 + r() * .3;
		if (splitV) slabs.push([
			0,
			0,
			T$1 * cut,
			T$1
		], [
			T$1 * cut,
			0,
			T$1 * (1 - cut),
			T$1
		]);
		else slabs.push([
			0,
			0,
			T$1,
			T$1 * cut
		], [
			0,
			T$1 * cut,
			T$1,
			T$1 * (1 - cut)
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
			let px = T$1 * (.2 + r() * .6);
			let py = T$1 * (.2 + r() * .2);
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
		ctx.fillRect(0, 0, T$1, T$1);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)";
			ctx.beginPath();
			ctx.ellipse(r() * T$1, r() * T$1, 8 + r() * 10, 6 + r() * 8, r() * TAU$3, 0, TAU$3);
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
			ctx.arc(6 + r() * 40, 6 + r() * 40, 2, 0, TAU$3);
			ctx.fill();
		}
	}
	function drawDirt(ctx, s) {
		const r = rng(s.x, s.y, 3);
		ctx.fillStyle = shade(PAL.dirt, .95 + r() * .1);
		ctx.fillRect(0, 0, T$1, T$1);
		const n = 5 + Math.floor(r() * 5);
		for (let i = 0; i < n; i++) {
			ctx.fillStyle = r() < .5 ? PAL.dirtDark : PAL.dirtLight;
			ctx.beginPath();
			ctx.ellipse(4 + r() * 44, 4 + r() * 44, 1.5 + r() * 2.5, 1.2 + r() * 1.8, r() * TAU$3, 0, TAU$3);
			ctx.fill();
		}
		ctx.strokeStyle = "rgba(90,66,40,0.35)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		const yy = T$1 * (.3 + r() * .4);
		ctx.moveTo(0, yy);
		ctx.bezierCurveTo(T$1 * .3, yy - 6, T$1 * .6, yy + 6, T$1, yy - 2);
		ctx.stroke();
	}
	function drawWall(ctx, s) {
		ctx.fillStyle = PAL.wallTop;
		ctx.fillRect(0, 0, T$1, T$1);
		const r = rng(s.x, s.y, 4);
		ctx.strokeStyle = PAL.wallLine;
		ctx.lineWidth = 2;
		const rows = 4;
		const rh = T$1 / rows;
		for (let i = 0; i < rows; i++) {
			ctx.beginPath();
			ctx.moveTo(0, i * rh);
			ctx.lineTo(T$1, i * rh);
			ctx.stroke();
			const off = i % 2 === 0 ? 0 : T$1 / 4;
			for (let bx = off; bx < T$1; bx += T$1 / 2) {
				ctx.beginPath();
				ctx.moveTo(bx, i * rh);
				ctx.lineTo(bx, (i + 1) * rh);
				ctx.stroke();
			}
		}
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = `rgba(255,255,255,${.04 + r() * .05})`;
			ctx.fillRect(Math.floor(r() * 2) * (T$1 / 2) + 2, Math.floor(r() * rows) * rh + 2, T$1 / 2 - 4, 9);
		}
		if (s.wallFace) {
			ctx.fillStyle = PAL.wallFace;
			ctx.fillRect(0, 43, T$1, 9);
			ctx.fillStyle = "rgba(255,255,255,0.08)";
			ctx.fillRect(0, 43, T$1, 1.5);
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
	function drawChasm(ctx, s) {
		const r = rng(s.x, s.y, 5);
		const g = ctx.createLinearGradient(0, 0, 0, T$1);
		g.addColorStop(0, "#05050a");
		g.addColorStop(1, PAL.chasm);
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$1, T$1);
		for (let i = 0; i < 4; i++) {
			ctx.fillStyle = `rgba(140,130,200,${.15 + r() * .2})`;
			ctx.fillRect(r() * T$1, r() * T$1, 1.5, 1.5);
		}
		ctx.fillStyle = PAL.chasmLip;
		if (s.lip.n) {
			jag(ctx, r, [
				0,
				0,
				T$1,
				0
			], [0, 1]);
			const gg = ctx.createLinearGradient(0, 0, 0, 16);
			gg.addColorStop(0, "rgba(70,64,80,0.9)");
			gg.addColorStop(1, "rgba(70,64,80,0)");
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$1, 16);
			ctx.fillStyle = PAL.chasmLip;
		}
		if (s.lip.s) jag(ctx, r, [
			0,
			T$1,
			T$1,
			T$1
		], [0, -1]);
		if (s.lip.w) jag(ctx, r, [
			0,
			0,
			0,
			T$1
		], [1, 0]);
		if (s.lip.e) jag(ctx, r, [
			T$1,
			0,
			T$1,
			T$1
		], [-1, 0]);
	}
	function drawLava(ctx, s) {
		const r = rng(s.x, s.y, 6);
		ctx.fillStyle = PAL.lava;
		ctx.fillRect(0, 0, T$1, T$1);
		const glow = ctx.createRadialGradient(T$1 / 2, T$1 / 2, 2, T$1 / 2, T$1 / 2, T$1 * .7);
		glow.addColorStop(0, "rgba(255,210,80,0.55)");
		glow.addColorStop(1, "rgba(255,210,80,0)");
		ctx.fillStyle = glow;
		ctx.fillRect(0, 0, T$1, T$1);
		const n = 4 + Math.floor(r() * 3);
		for (let i = 0; i < n; i++) {
			const cx = r() * T$1;
			const cy = r() * T$1;
			const rad = 5 + r() * 7;
			ctx.fillStyle = PAL.lavaCrust;
			ctx.beginPath();
			for (let k = 0; k < 7; k++) {
				const a = k / 7 * TAU$3;
				const rr = rad * (.7 + r() * .4);
				const px = cx + Math.cos(a) * rr;
				const py = cy + Math.sin(a) * rr;
				if (k === 0) ctx.moveTo(px, py);
				else ctx.lineTo(px, py);
			}
			ctx.closePath();
			ctx.fill();
			ctx.strokeStyle = "rgba(255,208,74,0.5)";
			ctx.lineWidth = 1;
			ctx.stroke();
		}
	}
	function drawIceHole(ctx, s) {
		const r = rng(s.x, s.y, 7);
		ctx.fillStyle = PAL.deep;
		ctx.fillRect(0, 0, T$1, T$1);
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
		if (s.lip.n) ctx.fillRect(0, 0, T$1, 4);
		if (s.lip.w) ctx.fillRect(0, 0, 4, T$1);
		if (s.lip.e) ctx.fillRect(48, 0, 4, T$1);
		if (s.lip.s) ctx.fillRect(0, 48, T$1, 4);
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
	/** 頂面亮度（3-19 定案第 4 條）：每高一階疊一層暖白。 */
	function heightLight(ctx, h) {
		if (h <= 0) return;
		ctx.fillStyle = `rgba(255,246,220,${.1 * h})`;
		ctx.fillRect(0, 0, T$1, T$1);
	}
	function surfaceBlob(ctx, s, color, alpha) {
		const inset = 4;
		const l = s.surfSame.w ? 0 : inset;
		const t = s.surfSame.n ? 0 : inset;
		const rr = s.surfSame.e ? 0 : inset;
		const b = s.surfSame.s ? 0 : inset;
		ctx.fillStyle = rgba(color, alpha);
		ctx.beginPath();
		ctx.roundRect(l, t, T$1 - l - rr, T$1 - t - b, [
			l && t ? 12 : 0,
			rr && t ? 12 : 0,
			rr && b ? 12 : 0,
			l && b ? 12 : 0
		]);
		ctx.fill();
	}
	var SURFACE_DRAW = {
		water(ctx, s, r) {
			surfaceBlob(ctx, s, PAL.water, .78);
			ctx.strokeStyle = "rgba(220,240,255,0.7)";
			ctx.lineWidth = 1.5;
			for (let i = 0; i < 2; i++) {
				const wx = 8 + r() * 26;
				const wy = 12 + r() * 30;
				ctx.beginPath();
				ctx.moveTo(wx, wy);
				ctx.quadraticCurveTo(wx + 5, wy - 4, wx + 10, wy);
				ctx.stroke();
			}
		},
		ice(ctx, s, r) {
			surfaceBlob(ctx, s, PAL.ice, .85);
			ctx.strokeStyle = "rgba(120,180,220,0.7)";
			ctx.lineWidth = 1;
			ctx.beginPath();
			const cx = T$1 * (.3 + r() * .4);
			const cy = T$1 * (.3 + r() * .4);
			for (let i = 0; i < 4; i++) {
				const a = r() * TAU$3;
				ctx.moveTo(cx, cy);
				ctx.lineTo(cx + Math.cos(a) * 18, cy + Math.sin(a) * 18);
			}
			ctx.stroke();
			ctx.strokeStyle = "rgba(255,255,255,0.9)";
			ctx.lineWidth = 3;
			ctx.beginPath();
			ctx.moveTo(10, 36);
			ctx.lineTo(18, 28);
			ctx.stroke();
		},
		oil(ctx, s, r) {
			surfaceBlob(ctx, s, PAL.oil, .85);
			const g = ctx.createLinearGradient(10, 10, 40, 30);
			g.addColorStop(0, "rgba(160,90,220,0.35)");
			g.addColorStop(.5, "rgba(80,200,160,0.30)");
			g.addColorStop(1, "rgba(230,200,80,0.25)");
			ctx.fillStyle = g;
			ctx.beginPath();
			ctx.ellipse(T$1 * (.35 + r() * .3), T$1 * (.35 + r() * .3), 12, 6, r() * TAU$3, 0, TAU$3);
			ctx.fill();
		},
		fire(ctx, s, r) {
			surfaceBlob(ctx, s, "#7a2a10", .6);
			const glow = ctx.createRadialGradient(T$1 / 2, T$1 * .6, 2, T$1 / 2, T$1 * .6, T$1 * .6);
			glow.addColorStop(0, "rgba(255,200,60,0.8)");
			glow.addColorStop(1, "rgba(255,90,20,0)");
			ctx.fillStyle = glow;
			ctx.fillRect(0, 0, T$1, T$1);
			for (let i = 0; i < 3; i++) flame(ctx, 10 + i * 15 + r() * 6, 44 - r() * 8, 9 + r() * 5);
		},
		poison(ctx, s, r) {
			surfaceBlob(ctx, s, PAL.poison, .7);
			ctx.strokeStyle = "rgba(220,255,180,0.8)";
			ctx.fillStyle = "rgba(160,230,100,0.6)";
			ctx.lineWidth = 1;
			for (let i = 0; i < 4; i++) {
				ctx.beginPath();
				ctx.arc(8 + r() * 36, 8 + r() * 36, 2 + r() * 3, 0, TAU$3);
				ctx.fill();
				ctx.stroke();
			}
		},
		smoke(ctx, s, r) {
			surfaceBlob(ctx, s, PAL.smoke, .35);
			const n = 4 + Math.floor(r() * 3);
			for (let i = 0; i < n; i++) {
				ctx.fillStyle = i % 3 === 2 ? "rgba(150,155,170,0.22)" : "rgba(235,238,245,0.38)";
				ctx.beginPath();
				ctx.arc(4 + r() * 44, 4 + r() * 44, 9 + r() * 7, 0, TAU$3);
				ctx.fill();
			}
		},
		holy(ctx, s, r) {
			surfaceBlob(ctx, s, PAL.holy, .5);
			const g = ctx.createRadialGradient(T$1 / 2, T$1 / 2, 2, T$1 / 2, T$1 / 2, T$1 * .55);
			g.addColorStop(0, "rgba(255,255,240,0.55)");
			g.addColorStop(1, "rgba(255,255,240,0)");
			ctx.fillStyle = g;
			ctx.fillRect(0, 0, T$1, T$1);
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
		},
		darkness(ctx, _s, r) {
			const g = ctx.createRadialGradient(T$1 / 2, T$1 / 2, 2, T$1 / 2, T$1 / 2, T$1 * .62);
			g.addColorStop(0, rgba(PAL.darkness, .85));
			g.addColorStop(1, rgba(PAL.darkness, .12));
			ctx.fillStyle = g;
			ctx.fillRect(0, 0, T$1, T$1);
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
	};
	function drawSurface(ctx, s) {
		const r = rng(s.x, s.y, 20);
		const draw = SURFACE_DRAW[s.surface];
		if (draw !== void 0) draw(ctx, s, r);
		else surfaceBlob(ctx, s, "#9a9aa8", .5);
	}
	/** 畫一個格子（座標以 ART_T 為單位；呼叫端負責縮放與裁切）。 */
	function drawTile(ctx, s) {
		(TERRAIN_DRAW[s.terrain] ?? drawStone)(ctx, s);
		if (s.tint !== null) {
			ctx.fillStyle = rgba(numToHex(s.tint), .3);
			ctx.fillRect(0, 0, T$1, T$1);
		}
		if (!s.blocked) heightLight(ctx, s.height);
		if (s.surface !== "none") drawSurface(ctx, s);
		ctx.strokeStyle = "rgba(0,0,0,0.14)";
		ctx.lineWidth = 1;
		ctx.strokeRect(.5, .5, 51, 51);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-5ea9fb/client/src/render/objectArt.ts
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
		ctx.arc(c, c, r, 0, TAU$3);
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
		ctx.arc(c, c, r - 1.5, 0, TAU$3);
		ctx.stroke();
		ctx.save();
		ctx.beginPath();
		ctx.arc(c, c, r * .5, 0, TAU$3);
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
				const a = k / 8 * TAU$3 + Math.PI / 8;
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
	/** 矮牆（美術 PM docs/art/矮牆.md）：暖色石塊——頂面亮、正面錯縫磚、2px 深色外框（相連的一側不畫）、較深的投影。 */
	var LOW_WALL = {
		top: "#d8c7a2",
		topEdge: "#f2e6c8",
		face: "#86704f",
		mortar: "#4c3d2a",
		outline: "#241c13"
	};
	function lowWall(ctx, s) {
		const x0 = s.joinL ? 0 : 4;
		const x1 = s.joinR ? T : T - 4;
		const capY = T * .3;
		const capH = T * .16;
		const faceH = T * .26;
		const faceY = capY + capH;
		const w = x1 - x0;
		ctx.fillStyle = "rgba(0,0,0,0.42)";
		ctx.fillRect(x0 + 4, faceY + faceH, w, 7);
		ctx.fillStyle = LOW_WALL.face;
		ctx.fillRect(x0, faceY, w, faceH);
		ctx.strokeStyle = LOW_WALL.mortar;
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		const rowH = faceH / 2;
		ctx.moveTo(x0, faceY + rowH);
		ctx.lineTo(x1, faceY + rowH);
		for (let r = 0; r < 2; r++) for (let bx = r ? 8 : 17; bx < x1 - 1; bx += 17) {
			if (bx <= x0 + 1) continue;
			ctx.moveTo(bx, faceY + r * rowH);
			ctx.lineTo(bx, faceY + (r + 1) * rowH);
		}
		ctx.stroke();
		ctx.fillStyle = LOW_WALL.top;
		ctx.fillRect(x0, capY, w, capH);
		ctx.fillStyle = LOW_WALL.topEdge;
		ctx.fillRect(x0, capY, w, 2);
		ctx.strokeStyle = "rgba(76,61,42,0.6)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		for (let bx = 13; bx < x1 - 1; bx += 26) {
			if (bx <= x0 + 1) continue;
			ctx.moveTo(bx, capY);
			ctx.lineTo(bx, capY + capH);
		}
		ctx.stroke();
		ctx.strokeStyle = LOW_WALL.outline;
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.moveTo(x0, capY);
		ctx.lineTo(x1, capY);
		ctx.moveTo(x0, faceY + faceH);
		ctx.lineTo(x1, faceY + faceH);
		if (!s.joinL) {
			ctx.moveTo(x0, capY);
			ctx.lineTo(x0, faceY + faceH);
		}
		if (!s.joinR) {
			ctx.moveTo(x1, capY);
			ctx.lineTo(x1, faceY + faceH);
		}
		ctx.stroke();
		ctx.strokeStyle = "rgba(36,28,19,0.7)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		ctx.moveTo(x0, faceY);
		ctx.lineTo(x1, faceY);
		ctx.stroke();
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
		ctx.ellipse(T * .36, 0, 5, 8, 0, 0, TAU$3);
		ctx.fill();
		ctx.strokeStyle = "#8a6038";
		ctx.beginPath();
		ctx.ellipse(T * .36, 0, 2.5, 4.5, 0, 0, TAU$3);
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
		for (let k = 0; k < 5; k++) branch(T / 2, T / 2, k / 5 * TAU$3 + .3, T * .2, 4, 1);
		ctx.fillStyle = "#5c4430";
		ctx.beginPath();
		ctx.arc(T / 2, T / 2, 6, 0, TAU$3);
		ctx.fill();
	}
	function iceWall(ctx) {
		shadowEllipse(ctx, T / 2 + 3, T / 2 + 6, T * .38, T * .28);
		roundRect(ctx, 6, 8, T - 12, T - 16, 7);
		ctx.fillStyle = rgba(PAL.iceWall, .78);
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = "#5fa8d3";
		ctx.stroke();
		ctx.fillStyle = "rgba(255,255,255,0.45)";
		roundRect(ctx, 9, 10, T - 18, T * .28, 5);
		ctx.fill();
		ctx.strokeStyle = "rgba(255,255,255,0.85)";
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.moveTo(14, T - 16);
		ctx.lineTo(22, T - 26);
		ctx.moveTo(T - 20, T - 14);
		ctx.lineTo(T - 15, T - 22);
		ctx.stroke();
	}
	function thornWall(ctx, s) {
		const r = rng(s.x, s.y, 40);
		shadowEllipse(ctx, T / 2 + 3, T / 2 + 6, T * .4, T * .28);
		ctx.fillStyle = "#33521c";
		ctx.beginPath();
		ctx.ellipse(T / 2, T / 2 + 2, T * .38, T * .3, 0, 0, TAU$3);
		ctx.fill();
		ctx.lineCap = "round";
		ctx.lineWidth = 3;
		ctx.strokeStyle = PAL.thorn;
		for (let i = 0; i < 4; i++) {
			const y = 12 + i * 9 + r() * 3;
			ctx.beginPath();
			ctx.moveTo(6, y);
			ctx.bezierCurveTo(T * .3, y - 8, T * .6, y + 8, T - 6, y);
			ctx.stroke();
		}
		ctx.fillStyle = "#d8d2a8";
		for (let i = 0; i < 9; i++) {
			const px = 8 + r() * (T - 16);
			const py = 10 + r() * (T - 20);
			ctx.beginPath();
			ctx.moveTo(px, py - 4);
			ctx.lineTo(px + 2.5, py + 2);
			ctx.lineTo(px - 2.5, py + 2);
			ctx.closePath();
			ctx.fill();
		}
	}
	function rubble(ctx, s) {
		const r = rng(s.x, s.y, 41);
		const n = 3 + Math.floor(r() * 3);
		for (let i = 0; i < n; i++) {
			const a0 = i / n * TAU$3 + r() * .8;
			const dist = i === 0 ? 0 : 9 + r() * 5;
			const cx = T / 2 + Math.cos(a0) * dist;
			const cy = T / 2 + 2 + Math.sin(a0) * dist * .8;
			const rad = 8 + r() * 4;
			shadowEllipse(ctx, cx + 2, cy + rad * .6, rad * 1.05, rad * .55);
			ctx.fillStyle = i % 2 === 0 ? PAL.rock : PAL.rockDark;
			ctx.beginPath();
			for (let k = 0; k < 7; k++) {
				const a = k / 7 * TAU$3;
				const rr = rad * (.78 + r() * .3);
				ctx.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr * .85);
			}
			ctx.closePath();
			ctx.fill();
			ctx.fillStyle = "rgba(255,255,255,0.28)";
			ctx.beginPath();
			ctx.ellipse(cx - rad * .25, cy - rad * .3, rad * .45, rad * .25, -.4, 0, TAU$3);
			ctx.fill();
			ctx.fillStyle = "rgba(0,0,0,0.18)";
			ctx.fillRect(cx - rad * .2, cy + rad * .25, rad * .8, 1.5);
		}
	}
	function thinIce(ctx, s) {
		const r = rng(s.x, s.y, 42);
		ctx.beginPath();
		const pts = 11;
		for (let k = 0; k < pts; k++) {
			const a = k / pts * TAU$3;
			const rad = T * (.4 + r() * .08);
			ctx.lineTo(T / 2 + Math.cos(a) * rad, T / 2 + Math.sin(a) * rad);
		}
		ctx.closePath();
		ctx.fillStyle = "rgba(205,238,255,0.55)";
		ctx.fill();
		ctx.lineWidth = 1.5;
		ctx.strokeStyle = "rgba(255,255,255,0.8)";
		ctx.stroke();
		ctx.strokeStyle = "rgba(90,150,200,0.75)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		const cx = T * (.35 + r() * .3);
		const cy = T * (.35 + r() * .3);
		for (let i = 0; i < 6; i++) {
			const a = i / 6 * TAU$3 + r() * .5;
			const len = 12 + r() * 10;
			const mx = cx + Math.cos(a) * len * .5;
			const my = cy + Math.sin(a) * len * .5;
			ctx.moveTo(cx, cy);
			ctx.lineTo(mx, my);
			ctx.lineTo(mx + Math.cos(a + .6) * len * .5, my + Math.sin(a + .6) * len * .5);
		}
		ctx.stroke();
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
	/** 沒有畫法的新物件：灰色六角形（不會出錯；字由繪圖端疊上）。 */
	function drawGenericObject(ctx) {
		ctx.fillStyle = "#888";
		ctx.beginPath();
		for (let k = 0; k < 6; k++) {
			const a = k / 6 * TAU$3;
			ctx.lineTo(T / 2 + Math.cos(a) * 16, T / 2 + Math.sin(a) * 16);
		}
		ctx.closePath();
		ctx.fill();
	}
	/** 可燃物右上角的小火苗。 */
	function flammableMark(ctx) {
		ctx.save();
		ctx.translate(T - 9, 12);
		ctx.fillStyle = "rgba(20,12,6,0.65)";
		ctx.beginPath();
		ctx.arc(0, -2, 6.5, 0, TAU$3);
		ctx.fill();
		flame(ctx, 0, 3, 9);
		ctx.restore();
	}
	function drawObject(ctx, s) {
		(OBJECT_DRAW[s.kind] ?? drawGenericObject)(ctx, s);
		if (s.flammable && s.kind !== "wooden_bridge") flammableMark(ctx);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-5ea9fb/client/src/battle/glossary.ts
	var index = /* @__PURE__ */ new Map();
	function glossaryEntry(category, id) {
		return index.get(category)?.get(id);
	}
	/** 中文名；對照表沒有時顯示 ID。 */
	function glossaryName(category, id) {
		return glossaryEntry(category, id)?.name_zh ?? id;
	}
	var statusName = (id) => glossaryName("statuses", id);
	var surfaceName = (id) => glossaryName("surfaces", id);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-5ea9fb/client/src/battle/vfxPalette.ts
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
	var ELEMENT_COLORS = {
		physical: {
			name: "物理",
			primary: "#f2f2f2",
			secondary: "#b8bcc8",
			accent: "#e8ebf0",
			dark: "#2c313b",
			light: "#7d8798"
		},
		fire: {
			name: "火",
			primary: "#ff6a1a",
			secondary: "#ffd23f",
			accent: "#ffb23a",
			dark: "#4a1104",
			light: "#e8541a"
		},
		ice: {
			name: "冰",
			primary: "#8fe3ff",
			secondary: "#ffffff",
			accent: "#d8f6ff",
			dark: "#0b2f4e",
			light: "#3fa6d8"
		},
		lightning: {
			name: "雷",
			primary: "#fff36b",
			secondary: "#8fd0ff",
			accent: "#fff36b",
			dark: "#1d1d4a",
			light: "#5a5ac8"
		},
		poison: {
			name: "毒",
			primary: "#7ddc3a",
			secondary: "#3f8f2a",
			accent: "#b6f06a",
			dark: "#12320c",
			light: "#4f9a28"
		},
		wind: {
			name: "風",
			primary: "#c8ffe8",
			secondary: "#7fe0c0",
			accent: "#dcfff1",
			dark: "#0b3f3a",
			light: "#3fb59a"
		},
		earth: {
			name: "大地",
			primary: "#b0814a",
			secondary: "#6e5236",
			accent: "#f0c890",
			dark: "#2e1d0e",
			light: "#9a6a36"
		},
		holy: {
			name: "聖光",
			primary: "#fff2b0",
			secondary: "#ffd75e",
			accent: "#fff6c8",
			dark: "#5a3a06",
			light: "#e7b23a"
		},
		shadow: {
			name: "暗影",
			primary: "#9a6ad8",
			secondary: "#2a1840",
			accent: "#d2b0ff",
			dark: "#10071e",
			light: "#5a3590"
		}
	};
	/** `#rrggbb` → 0xrrggbb。 */
	function hexToNumber(hex) {
		return parseInt(hex.slice(1), 16);
	}
	function fromColors(id, particle, particles, extra = {}) {
		const c = ELEMENT_COLORS[id];
		if (c === void 0) throw new Error(`ELEMENT_COLORS 缺少 ${id}`);
		return vfx(hexToNumber(c.primary), hexToNumber(c.secondary), particle, particles, extra);
	}
	fromColors("physical", "spark", 8), fromColors("fire", "ember", 12), fromColors("ice", "shard", 10), fromColors("lightning", "bolt", 7, { jagged: true }), fromColors("poison", "bubble", 9), fromColors("wind", "gust", 7), fromColors("earth", "rock", 9), fromColors("holy", "pillar", 9, { column: true }), fromColors("shadow", "smoke", 9), vfx(4892927, 14217471, "splash", 10);
	vfx(8188570, 15138793, "sparkle", 9);
	vfx(12101887, 16777215, "sparkle", 9);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-5ea9fb/client/src/battle/vfx.ts
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-5ea9fb/client/src/render/skillGlyphs.ts
	var TAU$2 = Math.PI * 2;
	Object.fromEntries(Object.entries(ELEMENT_COLORS).map(([id, c]) => [id, {
		name: c.name,
		accent: c.accent,
		dark: c.dark,
		light: c.light
	}]));
	function starPath(ctx, cx, cy, n, ro, ri, rot = -Math.PI / 2) {
		ctx.beginPath();
		for (let i = 0; i < n * 2; i++) {
			const r = i % 2 === 0 ? ro : ri;
			const a = rot + i / (n * 2) * TAU$2;
			ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
		}
		ctx.closePath();
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
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-5ea9fb/client/src/render/skillParts.ts
	var TAU$1 = Math.PI * 2;
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
		ctx.font = `800 ${size}px "Noto Sans TC","Microsoft JhengHei",sans-serif`;
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
	var bleedGlyph = (c) => {
		drop(c, -3, -1, .75);
		drop(c, 4, 3, .6);
	};
	var STATUS = {
		burning: ["#ff8a2a", (c) => elementGlyph(c, "fire", 0, 0, .95, c.fillStyle)],
		frozen: ["#9fe6ff", (c) => elementGlyph(c, "ice", 0, 0, .95, c.fillStyle)],
		poison: ["#8fdc4a", (c) => elementGlyph(c, "poison", 0, 0, .95, c.fillStyle)],
		bleed: ["#ff5a5a", bleedGlyph],
		root: ["#b8d07a", (c) => {
			c.beginPath();
			c.moveTo(0, -8);
			c.lineTo(0, 4);
			c.moveTo(0, 4);
			c.lineTo(-6, 8);
			c.moveTo(0, 4);
			c.lineTo(6, 8);
			c.moveTo(0, 0);
			c.lineTo(-5, 3);
			c.stroke();
		}],
		slow: ["#a8b4ff", (c) => {
			ring(c, 0, 0, 8);
			c.beginPath();
			c.moveTo(0, -5);
			c.lineTo(0, 0);
			c.lineTo(3.5, 3);
			c.stroke();
		}],
		stun: ["#ffe14d", (c) => {
			for (const [x, y] of [
				[-5, -3],
				[5, -3],
				[0, 5]
			]) {
				c.save();
				c.translate(x, y);
				star(c, 5, 4, 1.7);
				c.restore();
			}
		}],
		prone: ["#e0c49a", (c) => {
			dot(c, -7, 2, 2.6);
			c.fillRect(-4, 0, 12, 4.5);
		}],
		blinded: ["#c8c8d8", (c) => eye(c, true)],
		vulnerable: ["#ff6a6a", (c) => {
			shieldPath(c);
			c.stroke();
			c.beginPath();
			c.moveTo(-2, -8);
			c.lineTo(2, -2);
			c.lineTo(-2, 2);
			c.lineTo(1, 8);
			c.stroke();
		}],
		armor_broken: ["#d8a060", (c) => {
			shieldPath(c);
			c.stroke();
			arrow(c, 0, -5, 0, 6, 3.2);
		}],
		weaken: ["#e09a9a", (c) => {
			c.beginPath();
			c.moveTo(-6, -7);
			c.lineTo(4, 3);
			c.stroke();
			arrow(c, 6, -6, 6, 6, 3.5);
		}],
		feared: ["#c890ff", (c) => text(c, "!", 15)],
		taunted: ["#ff7a4a", (c) => {
			ring(c, 0, 0, 7.5);
			ring(c, 0, 0, 3.5);
			dot(c, 0, 0, 1.4);
		}],
		silenced: ["#d0a0ff", (c) => {
			c.beginPath();
			c.roundRect(-8, -7, 16, 11, 4);
			c.moveTo(-3, 4);
			c.lineTo(-5, 8);
			c.lineTo(1, 4);
			c.stroke();
			c.beginPath();
			c.moveTo(-4, -4);
			c.lineTo(4, 2);
			c.moveTo(4, -4);
			c.lineTo(-4, 2);
			c.stroke();
		}],
		marked: ["#ff5a5a", (c) => {
			ring(c, 0, 0, 7);
			c.beginPath();
			c.moveTo(-10, 0);
			c.lineTo(-4, 0);
			c.moveTo(4, 0);
			c.lineTo(10, 0);
			c.moveTo(0, -10);
			c.lineTo(0, -4);
			c.moveTo(0, 4);
			c.lineTo(0, 10);
			c.stroke();
		}],
		concealed: ["#a0a8b8", (c) => {
			ghost(c, .55, () => person(c, 0, 0, 1.4));
			c.beginPath();
			c.arc(0, 0, 9, -2.4, -.7);
			c.stroke();
		}],
		revealed: ["#ffd04a", (c) => eye(c, false)],
		hasted: ["#7dffb0", (c) => chevrons(c, "right")],
		empowered: ["#ffb03a", (c) => chevrons(c, "up")],
		rallied: ["#ff6a4a", (c) => chevrons(c, "up")],
		guarded: ["#7fc0ff", (c) => {
			shieldPath(c);
			c.fill();
		}],
		shielded: ["#8fd0ff", (c) => {
			shieldPath(c);
			c.fill();
		}],
		defending: ["#7fc0ff", (c) => {
			shieldPath(c);
			c.stroke();
		}],
		regenerating: ["#7cf29a", (c) => {
			ring(c, 0, 0, 8.5);
			c.fillRect(-1.5, -5, 3, 10);
			c.fillRect(-5, -1.5, 10, 3);
		}],
		overwatch: ["#ffd04a", (c) => eye(c, false)],
		undying: ["#ff7a7a", (c) => {
			heart(c);
			c.fill();
		}],
		soul_link: ["#d8b8ff", (c) => {
			ring(c, -4, 0, 5);
			ring(c, 4, 0, 5);
		}],
		time_bomb: ["#ffb03a", hourglass],
		charging: ["#ffd04a", (c) => {
			ring(c, 0, 0, 8);
			dot(c, 0, 0, 3.5);
		}]
	};
	var STANCE_COLOR = "#ffd04a";
	var UNKNOWN_COLOR = "#d8d8e0";
	/** 狀態圖示（`stance_*` 為六角，不認得的狀態畫名稱第一個字）。 */
	function statusGlyph(ctx, id) {
		const known = id == null ? void 0 : STATUS[id];
		if (known !== void 0) {
			known[1](ctx);
			return;
		}
		if (id?.startsWith("stance_") === true) {
			ctx.beginPath();
			for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos(i / 6 * TAU$1) * 8, Math.sin(i / 6 * TAU$1) * 8);
			ctx.closePath();
			ctx.stroke();
			return;
		}
		text(ctx, [...id == null || id === "" ? "?" : statusName(id)][0] ?? "?", 12);
	}
	function statusColor(id) {
		if (id == null) return UNKNOWN_COLOR;
		return STATUS[id]?.[0] ?? (id.startsWith("stance_") ? STANCE_COLOR : UNKNOWN_COLOR);
	}
	var SURFACE_COLOR = {
		fire: "#ff7a1a",
		ice: "#cdeeff",
		oil: "#5a4a30",
		water: "#4a9af0",
		holy: "#ffe58a",
		darkness: "#8a5ad0",
		smoke: "#c0c0c8",
		poison: "#86d84a"
	};
	var surfaceColor = (id) => id == null ? "#c8c8c8" : SURFACE_COLOR[id] ?? "#c8c8c8";
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
		}
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
	Object.keys(EFFECT), Object.keys(STATUS), Object.keys(SURFACE_COLOR), Object.keys(COND), Object.keys(TRIG), Object.keys(LINK), Object.keys(COST_ART);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-5ea9fb/client/src/render/skillIcon.ts
	var TAU = Math.PI * 2;
	Object.fromEntries(Object.entries(SHAPE_NAMES).map(([zh, id]) => [id, zh]));
	var DPR = 2;
	var CACHE_LIMIT = 300;
	var FAINT_RING = "rgba(255,255,255,0.3)";
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
	//#endregion
	//#region entry.ts
	window.CUR = {
		drawTile,
		drawObject,
		statusTile,
		tileCanvas,
		surfaceTile,
		ART_T: 52
	};
	//#endregion
})();
