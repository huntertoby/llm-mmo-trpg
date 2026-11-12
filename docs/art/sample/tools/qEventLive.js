// 自動產生，不要手改：現行事件卡圖示（client/src/render/storyIconArt.ts）與事件插圖（render/eventArt.ts、eventArtParts.ts 的小牌圖示 ICON、泡泡 bubble）的畫法，用 vite 的 lib 模式打包成 IIFE，minify 關閉。
// 只給 Q 版小圖示第 8 批樣張（q-icons-event.html）的「現行」那一欄用，和實機同一份程式：QEventLive.drawStoryIcon(ctx, spec, size)、drawChip、drawD20、SOLUTION_ART、MISC_ART、ATTR_ART、D20_COLOR、ICON、BADGE_ICON_INK、bubble、drawEventArt(ctx, scene, bg)、SCENES、OUTCOME_COLOR。
// 重新產生：做法見 docs/art/Q版小圖示-第8批事件卡.md 第 8 節（進入點 import 上面幾個掛到 window.QEventLive，用主資料夾 client/node_modules 的 vite build：lib、iife、pixi.js external；@wt/ 指到 worktree 的 client/src）。
(function() {
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/artDraw.ts
	var TAU$2 = Math.PI * 2;
	function roundRect(ctx, x, y, w, h, r) {
		ctx.beginPath();
		ctx.roundRect(x, y, w, h, r);
	}
	function flame$1(ctx, x, y, h) {
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
		ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU$2);
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
	function dot$3(ctx, x, y, r, fill) {
		ctx.fillStyle = fill;
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU$2);
		ctx.fill();
	}
	//#endregion
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/inkStyle.ts
	var INK$2 = "#2b1e16";
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
	function smooth$1(ctx, pts, closed = true) {
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
	function outline$1(ctx, pts, sharp) {
		if (sharp !== true) {
			smooth$1(ctx, pts);
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
		outline$1(ctx, pts, sharp);
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
	function ink$1(ctx, key, pts, color, opt = {}) {
		const r = lcg(seedOf(key));
		ctx.save();
		ctx.translate(.45, .35);
		outline$1(ctx, wobble(pts, r, .7), opt.sharp);
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
		ctx.strokeStyle = INK$2;
		ctx.lineJoin = "round";
		ctx.lineCap = "round";
		ctx.lineWidth = w * lineMul(ctx);
		outline$1(ctx, wobble(pts, r, .5), opt.sharp);
		ctx.stroke();
		ctx.lineWidth = w * .45 * lineMul(ctx);
		outline$1(ctx, wobble(pts, r, .85), opt.sharp);
		ctx.stroke();
	}
	/** 開放的抖動線（腰帶、縫線、嘴、骨架線）。 */
	function stroke$1(ctx, key, pts, w = .7, color = INK$2) {
		const r = lcg(seedOf(key));
		ctx.strokeStyle = color;
		ctx.lineWidth = w * lineMul(ctx);
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		smooth$1(ctx, wobble(pts, r, .35), false);
		ctx.stroke();
	}
	/** 小橢圓點（眼睛、手上的點）。 */
	function dot$2(ctx, x, y, rx, ry, c) {
		ctx.fillStyle = c;
		ctx.beginPath();
		ctx.ellipse(x, y, rx, ry, 0, 0, TAU$2);
		ctx.fill();
	}
	/** 地面影子：一排短斜線（不是深色橢圓）。 */
	function shadow$2(ctx, rx = 9) {
		const r = lcg(7);
		ctx.strokeStyle = "rgba(43,30,22,0.5)";
		ctx.lineWidth = .5;
		ctx.beginPath();
		for (let x = -rx; x < rx; x += 2.2) {
			const j = r();
			ctx.moveTo(x + j, 1.2);
			ctx.lineTo(x + j + 2.4, -.6);
		}
		ctx.stroke();
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
	var dollSkinNow = "q";
	var dollSkin = () => dollSkinNow;
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/storyIconArt.ts
	/** 墨線色（樣張的 K）。 */
	var K$1 = "#2b1e16";
	/** 圓環裡的深底。 */
	var CHIP_BG = "#2a241e";
	/** d20 平常的顏色、大成功（金）、大失敗（灰）。 */
	var D20_COLOR = {
		normal: "#f2e6c8",
		crit: "#ffe08a",
		fumble: "#c8c0b8"
	};
	var glowOn = (c, col, b) => {
		c.shadowColor = col;
		c.shadowBlur = b;
	};
	var disc = (c, x, y, r, col) => {
		c.fillStyle = col;
		c.beginPath();
		c.arc(x, y, r, 0, TAU$2);
		c.fill();
	};
	var shine = (c, x, y, rx, ry, rot, col) => {
		c.fillStyle = col;
		c.beginPath();
		c.ellipse(x, y, rx, ry, rot, 0, TAU$2);
		c.fill();
	};
	var SOLUTION_ART = {
		combat: {
			ring: "#d0503a",
			draw(c) {
				for (const [s, k] of [[1, "a"], [-1, "b"]]) {
					c.save();
					c.translate(24, 24);
					c.scale(s, 1);
					c.rotate(-.78);
					ink$1(c, "bl" + k, [
						[-3, -20],
						[0, -23],
						[3, -20],
						[3, 8],
						[-3, 8]
					], "#dfe6ee", {
						w: .8,
						sharp: true
					});
					ink$1(c, "gd" + k, [
						[-9, 8],
						[9, 8],
						[9, 12],
						[-9, 12]
					], "#c8903a", {
						w: .7,
						shade: false
					});
					ink$1(c, "hd" + k, [
						[-2, 12],
						[2, 12],
						[2, 20],
						[-2, 20]
					], "#6a4028", {
						w: .6,
						shade: false
					});
					c.restore();
				}
			}
		},
		persuade: {
			ring: "#e8bb48",
			draw(c) {
				ink$1(c, "bub", [
					[6, 10],
					[42, 10],
					[42, 32],
					[22, 32],
					[12, 40],
					[14, 32],
					[6, 32]
				], "#f2e6c8", { w: .9 });
				ink$1(c, "hrt", [
					[24, 29],
					[16, 21],
					[16, 16],
					[20, 13],
					[24, 16],
					[28, 13],
					[32, 16],
					[32, 21]
				], "#e05a6a", {
					w: .6,
					shade: false
				});
			}
		},
		sneak: {
			ring: "#8a7ab8",
			draw(c) {
				ink$1(c, "hood", [
					[24, 4],
					[38, 14],
					[42, 40],
					[6, 40],
					[10, 14]
				], "#4a3e62", { w: .9 });
				ink$1(c, "face", [
					[24, 16],
					[33, 22],
					[33, 34],
					[15, 34],
					[15, 22]
				], "#1c1712", {
					w: .5,
					shade: false
				});
				c.save();
				glowOn(c, "#c8b8ff", 6);
				disc(c, 20, 26, 1.8, "#e8e0ff");
				disc(c, 28, 26, 1.8, "#e8e0ff");
				c.restore();
			}
		},
		investigate: {
			ring: "#4ab0d0",
			draw(c) {
				ink$1(c, "hdl", [
					[29, 31],
					[33, 27],
					[44, 38],
					[40, 42]
				], "#6a4028", {
					w: .8,
					shade: false
				});
				ink$1(c, "ring", ellPts(20, 20, 13, 13, 18), "#c8903a", {
					w: .9,
					shade: false
				});
				ink$1(c, "lens", ellPts(20, 20, 9.5, 9.5, 16), "#bfe4f2", {
					w: .5,
					shade: false
				});
				shine(c, 16, 16, 3, 4.5, -.6, "rgba(255,255,255,0.7)");
			}
		},
		force: {
			ring: "#e07a4a",
			draw(c) {
				for (const [a, b] of [
					[[6, 8], [12, 14]],
					[[24, 3], [24, 10]],
					[[42, 8], [36, 14]]
				]) stroke$1(c, "imp" + a[0], [a, b], 1.4, "#ffcf6a");
				ink$1(c, "fist", [
					[10, 20],
					[38, 20],
					[40, 30],
					[36, 42],
					[14, 42],
					[10, 34]
				], "#e8b890", { w: .9 });
				for (const x of [
					17,
					24,
					31
				]) stroke$1(c, "kn" + x, [[x, 20], [x, 28]], .8, "#8a5a3a");
				ink$1(c, "thumb", [
					[12, 30],
					[26, 30],
					[26, 34],
					[12, 35]
				], "#f0c8a0", {
					w: .6,
					shade: false
				});
			}
		},
		chance: {
			ring: "#6aa84a",
			draw(c) {
				stroke$1(c, "stem", [
					[24, 26],
					[28, 36],
					[34, 42]
				], 1.2, "#3a6a2a");
				[
					[0, -1],
					[1, 0],
					[0, 1],
					[-1, 0]
				].forEach(([dx, dy], i) => ink$1(c, "lf" + i, ellPts(24 + dx * 8, 22 + dy * 8, 7, 7, 14), "#7ac85a", { w: .7 }));
				c.save();
				glowOn(c, "#fff4a0", 8);
				ink$1(c, "sp", [
					[40, 4],
					[42, 9],
					[47, 11],
					[42, 13],
					[40, 18],
					[38, 13],
					[33, 11],
					[38, 9]
				], "#fff4c0", {
					w: .4,
					shade: false
				});
				c.restore();
			}
		},
		leave: {
			ring: "#9a8e7c",
			draw(c) {
				ink$1(c, "door", [
					[8, 6],
					[26, 6],
					[26, 42],
					[8, 42]
				], "#5a3e28", { w: .9 });
				ink$1(c, "open", [
					[8, 6],
					[18, 10],
					[18, 44],
					[8, 42]
				], "#8a5a3a", { w: .7 });
				disc(c, 16, 26, 1.6, "#e8bb48");
				ink$1(c, "arr", [
					[24, 21],
					[34, 21],
					[34, 15],
					[44, 24],
					[34, 33],
					[34, 27],
					[24, 27]
				], "#f2e6c8", {
					w: .8,
					shade: false
				});
			}
		},
		trade: {
			ring: "#e8bb48",
			draw(c) {
				ink$1(c, "bag", [
					[16, 12],
					[32, 12],
					[28, 18],
					[40, 30],
					[38, 42],
					[10, 42],
					[8, 30],
					[20, 18]
				], "#b08a5a", { w: .9 });
				stroke$1(c, "tie", [[18, 17], [30, 17]], 1.2, "#6a4028");
				for (const [x, y] of [[30, 38], [37, 34]]) {
					ink$1(c, "cn" + x, ellPts(x, y, 6, 6, 14), "#ffd23a", {
						w: .7,
						shade: false
					});
					stroke$1(c, "cm" + x, [[x, y - 3], [x, y + 3]], .8, "#a8781a");
				}
			}
		}
	};
	var MISC_ART = {
		clue: {
			ring: "#e8bb48",
			draw(c) {
				ink$1(c, "note", [
					[8, 8],
					[36, 6],
					[40, 40],
					[12, 42]
				], "#f2e6c8", { w: .9 });
				for (const y of [
					16,
					22,
					28
				]) stroke$1(c, "ln" + y, [[14, y], [32, y - 1]], .7, "#9a8a70");
				c.save();
				glowOn(c, "#ffd23a", 8);
				ink$1(c, "spot", ellPts(30, 34, 5, 5, 12), "#ffd23a", {
					w: .5,
					shade: false
				});
				c.restore();
			}
		},
		model_off: {
			ring: "#9a8e7c",
			draw(c) {
				ink$1(c, "base", [
					[12, 36],
					[36, 36],
					[40, 44],
					[8, 44]
				], "#6a4028", {
					w: .8,
					shade: false
				});
				ink$1(c, "ball", ellPts(24, 22, 14, 14, 18), "#7a8098", { w: .9 });
				stroke$1(c, "crk", [
					[18, 12],
					[23, 19],
					[20, 24],
					[26, 31]
				], 1, K$1);
				shine(c, 18, 16, 3, 5, -.6, "rgba(255,255,255,0.35)");
			}
		},
		narrator: {
			ring: "#a898ff",
			draw(c) {
				ink$1(c, "book", [
					[6, 26],
					[24, 30],
					[42, 26],
					[42, 42],
					[24, 46],
					[6, 42]
				], "#f2e6c8", { w: .8 });
				stroke$1(c, "sp", [[24, 30], [24, 46]], .8, K$1);
				c.save();
				c.translate(26, 20);
				c.rotate(.6);
				ink$1(c, "qf", [
					[0, -18],
					[6, -10],
					[4, 6],
					[0, 12],
					[-4, 6],
					[-6, -10]
				], "#c8bcff", { w: .7 });
				stroke$1(c, "qs", [[0, -14], [0, 16]], .8, K$1);
				c.restore();
			}
		},
		info: {
			ring: "#4ab0d0",
			draw(c) {
				ink$1(c, "disc", ellPts(24, 24, 17, 17, 18), "#bfe4f2", { w: .9 });
				disc(c, 24, 15, 2.8, K$1);
				ink$1(c, "stem", [
					[21, 21],
					[27, 21],
					[27, 35],
					[21, 35]
				], K$1, {
					w: .5,
					shade: false
				});
			}
		},
		thread: {
			ring: "#e8bb48",
			draw(c) {
				stroke$1(c, "th", [
					[8, 34],
					[16, 18],
					[24, 30],
					[32, 16],
					[40, 12]
				], 2.2, "#e8bb48");
				disc(c, 8, 34, 2.4, "#f2e6c8");
				disc(c, 40, 12, 2.4, "#f2e6c8");
			}
		}
	};
	var ATTR_ART = {
		str: {
			ring: "#e07a4a",
			draw(c) {
				ink$1(c, "arm", [
					[10, 34],
					[14, 22],
					[20, 14],
					[28, 12],
					[32, 18],
					[28, 22],
					[24, 22],
					[22, 30],
					[30, 30],
					[38, 34],
					[36, 40],
					[12, 40]
				], "#e8b890", { w: .9 });
				stroke$1(c, "arm-m", [[20, 22], [26, 26]], .8, "#8a5a3a");
			}
		},
		dex: {
			ring: "#6ac0a0",
			draw(c) {
				c.save();
				c.translate(24, 24);
				c.rotate(-.7);
				ink$1(c, "fe", [
					[0, -18],
					[7, -8],
					[6, 8],
					[0, 16],
					[-6, 8],
					[-7, -8]
				], "#c8f0e0", { w: .8 });
				stroke$1(c, "fe-q", [[0, -16], [0, 20]], .8, K$1);
				c.restore();
				stroke$1(c, "wind", [[8, 34], [16, 32]], 1, "#6ac0a0");
				stroke$1(c, "wind2", [[10, 40], [20, 38]], 1, "#6ac0a0");
			}
		},
		con: {
			ring: "#d04a5a",
			draw(c) {
				ink$1(c, "heart", [
					[24, 40],
					[10, 26],
					[10, 16],
					[17, 11],
					[24, 16],
					[31, 11],
					[38, 16],
					[38, 26]
				], "#e04a5a", { w: .9 });
				shine(c, 16, 18, 3, 4, -.4, "rgba(255,255,255,0.4)");
			}
		},
		int: {
			ring: "#7a8aff",
			draw(c) {
				ink$1(c, "book", [
					[9, 14],
					[24, 18],
					[39, 14],
					[39, 38],
					[24, 42],
					[9, 38]
				], "#f2e6c8", { w: .9 });
				stroke$1(c, "spine", [[24, 18], [24, 42]], .9, K$1);
				c.save();
				glowOn(c, "#a898ff", 6);
				ink$1(c, "star", [
					[24, 4],
					[26, 10],
					[32, 10],
					[27, 13],
					[29, 19],
					[24, 15],
					[19, 19],
					[21, 13],
					[16, 10],
					[22, 10]
				], "#c8bcff", {
					shade: false,
					w: .5
				});
				c.restore();
			}
		},
		wis: {
			ring: "#4ab0d0",
			draw(c) {
				ink$1(c, "eye", [
					[6, 24],
					[16, 15],
					[24, 13],
					[32, 15],
					[42, 24],
					[32, 33],
					[24, 35],
					[16, 33]
				], "#f2f0e8", { w: .9 });
				ink$1(c, "iris", ellPts(24, 24, 7, 7, 14), "#4ab0d0", {
					shade: false,
					w: .7
				});
				disc(c, 24, 24, 3, "#1c1712");
				disc(c, 22, 22, 1.4, "#fff");
			}
		},
		wil: {
			ring: "#e8bb48",
			draw(c) {
				c.save();
				glowOn(c, "#ffd23a", 8);
				ink$1(c, "flame", [
					[24, 6],
					[32, 18],
					[34, 30],
					[28, 40],
					[20, 40],
					[14, 30],
					[16, 18],
					[20, 22]
				], "#ffb030", {
					shade: false,
					w: .9
				});
				ink$1(c, "flame-in", [
					[24, 20],
					[28, 30],
					[24, 37],
					[20, 30]
				], "#fff4c0", {
					shade: false,
					w: .5
				});
				c.restore();
			}
		}
	};
	/** d20：六角外形加中央三角面；`n` 給了才寫點數（呼叫端依大小決定）。 */
	function drawD20(c, n, col = D20_COLOR.normal) {
		const P = (a, r) => [24 + Math.cos(a) * r, 24 + Math.sin(a) * r];
		const hex = [
			0,
			1,
			2,
			3,
			4,
			5
		].map((i) => P(-Math.PI / 2 + i * TAU$2 / 6, 21));
		ink$1(c, "hex", hex, col, {
			w: .9,
			sharp: true
		});
		const tri = [
			P(-Math.PI / 2, 12),
			P(Math.PI / 6, 12),
			P(5 * Math.PI / 6, 12)
		];
		ink$1(c, "tri", tri, "#fff8e8", {
			w: .6,
			sharp: true,
			shade: false
		});
		const to = [
			0,
			0,
			1,
			1,
			2,
			2
		];
		for (let i = 0; i < 6; i++) stroke$1(c, "e" + i, [hex[i], tri[to[i]]], .6, K$1);
		if (n !== void 0) {
			c.font = `bold 14px Georgia, serif`;
			c.textAlign = "center";
			c.lineJoin = "round";
			c.lineWidth = D20_HALO_W * 2;
			c.strokeStyle = D20_HALO;
			c.strokeText(String(n), 24, 29);
			c.fillStyle = K$1;
			c.fillText(String(n), 24, 29);
			c.textAlign = "left";
		}
	}
	/** 點數外圈的顏色（6Q-1，和三角面同色）。 */
	var D20_HALO = "#fff8e8";
	/**
	* 點數外圈露在字外的寬度（6Q-1；6N-4 改細，美術 PM 6Q-1 驗收第 1 點：描邊線寬從 5.6 改成 3.5，露在字外 1.75）。
	* 描邊一半在字外，所以 `lineWidth ＝ D20_HALO_W × 2 ＝ 3.5`。
	*/
	var D20_HALO_W = 1.75;
	/** d20 該不該寫字：只有大圖（29px 以上）才寫。 */
	var d20ShowsValue = (size) => size >= 29;
	/** 畫一個圓環小圖示（左上角在原點、大小 s）：深底＋圖示色圓環，圖示縮到圓裡。 */
	function drawChip(c, s, ring, fn) {
		c.save();
		if (ring !== null) {
			c.beginPath();
			c.arc(s / 2, s / 2, s / 2, 0, TAU$2);
			c.fillStyle = CHIP_BG;
			c.fill();
			c.lineWidth = Math.max(1.2, s * .06);
			c.strokeStyle = ring;
			c.stroke();
			c.beginPath();
			c.arc(s / 2, s / 2, s / 2 - 1, 0, TAU$2);
			c.clip();
		}
		c.scale(s / 48, s / 48);
		fn(c);
		c.restore();
	}
	/** 畫一個圖示到 ctx（左上角在原點、大小 size）。 */
	function drawStoryIcon(c, spec, size) {
		switch (spec.kind) {
			case "solution":
				drawChip(c, size, SOLUTION_ART[spec.icon].ring, SOLUTION_ART[spec.icon].draw);
				return;
			case "misc":
				drawChip(c, size, MISC_ART[spec.icon].ring, MISC_ART[spec.icon].draw);
				return;
			case "attr":
				drawChip(c, size, ATTR_ART[spec.attr].ring, ATTR_ART[spec.attr].draw);
				return;
			case "d20": {
				const v = d20ShowsValue(size) ? spec.value : void 0;
				drawChip(c, size, null, (cc) => drawD20(cc, v, spec.color ?? D20_COLOR.normal));
				return;
			}
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/color.ts
	var HEX$1 = /^#[0-9a-f]{6}$/i;
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
		if (!HEX$1.test(a) || !HEX$1.test(b)) return a;
		const [r1, g1, b1] = hexRgb(a);
		const [r2, g2, b2] = hexRgb(b);
		const m = (x, y) => Math.round(x * (1 - t) + y * t);
		return `#${(m(r1, r2) << 16 | m(g1, g2) << 8 | m(b1, b2)).toString(16).padStart(6, "0")}`;
	}
	/** 與黑色混合（暗 t）。 */
	var darken = (c, t) => mix$1(c, "#000000", t);
	/** 與白色混合（亮 t）。 */
	var lighten = (c, t) => mix$1(c, "#ffffff", t);
	/** 把亮度乘上 `f`，回傳 CSS 顏色（`rgb(r,g,b)`，`f` 大於 1 變亮）。 */
	function shade(h, f) {
		const [r, g, b] = hexRgb(h);
		const c = (v) => Math.max(0, Math.min(255, Math.round(v)));
		return `rgb(${c(r * f)},${c(g * f)},${c(b * f)})`;
	}
	function rgba$1(h, a) {
		const [r, g, b] = hexRgb(h);
		return `rgba(${r},${g},${b},${a})`;
	}
	/** Pixi 的數字顏色 → `#rrggbb`。 */
	function numToHex(n) {
		return `#${(n & 16777215).toString(16).padStart(6, "0")}`;
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/hazardTerrainArt.ts
	var T$9 = 52;
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
		ctx.arc(x, y, r, 0, TAU$2);
		ctx.fill();
		ctx.restore();
	}
	/** 一格的雲團（格子座標雜湊；`ox`、`oy` 是這一格相對於畫布的位移，鄰格用 ±T）。 */
	function puffsOf(ctx, x, y, ox, oy, salt) {
		const r = rng(x, y, salt);
		const count = 5 + Math.floor(r() * 3);
		const items = [];
		for (let i = 0; i < count; i++) {
			const px = ox + i / count * T$9 + (r() - .5) * 14;
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
		const g = ctx.createLinearGradient(0, 0, 0, T$9);
		g.addColorStop(0, shade(CLOUD_SEA.deep, .96 + r() * .08));
		g.addColorStop(1, CLOUD_SEA.shallow);
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$9, T$9);
		for (let i = 0; i < 2; i++) {
			const cx = r() * T$9;
			const cy = r() * T$9;
			const rg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14 + r() * 8);
			rg.addColorStop(0, rgba$1("#6f8db4", .5));
			rg.addColorStop(1, rgba$1("#6f8db4", 0));
			ctx.fillStyle = rg;
			ctx.fillRect(0, 0, T$9, T$9);
		}
		for (const [dx, dy] of cloudNeighbors(s)) puffsOf(ctx, s.x + dx, s.y + dy, dx * T$9, dy * T$9, salt);
		puffsOf(ctx, s.x, s.y, 0, 0, salt);
	}
	/** 熔岩的色票（照荒原區域插畫的熔岩河）。 */
	var LAVA$1 = {
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
			const a = k / n * TAU$2;
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
		ctx.fillStyle = LAVA$1.crust;
		ctx.beginPath();
		const steps = 7;
		for (let i = 0; i <= steps; i++) {
			const t = i / steps * T$9;
			const d = depth + r() * 3;
			const px = horizontal ? t : side === "w" ? d : T$9 - d;
			const py = horizontal ? side === "n" ? d : T$9 - d : t;
			if (i === 0) ctx.moveTo(horizontal ? 0 : side === "w" ? 0 : T$9, horizontal ? side === "n" ? 0 : T$9 : 0);
			ctx.lineTo(px, py);
		}
		ctx.lineTo(horizontal ? T$9 : side === "w" ? 0 : T$9, horizontal ? side === "n" ? 0 : T$9 : T$9);
		ctx.closePath();
		ctx.fill();
		ctx.strokeStyle = rgba$1(LAVA$1.hot, .35);
		ctx.lineWidth = 1;
		ctx.stroke();
	}
	/** 熔岩底圖：發光底 → 熱紋 → 岩殼塊 → 冷卻黑殼。`tone` 微調底色（荒原更暗紅）。 */
	function drawLavaBase(ctx, s, salt, tone = 1) {
		const r = rng(s.x, s.y, salt);
		ctx.fillStyle = shade(LAVA$1.base, tone * (.94 + r() * .12));
		ctx.fillRect(0, 0, T$9, T$9);
		const glows = 2 + Math.floor(r() * 2);
		for (let i = 0; i < glows; i++) {
			const cx = r() * T$9;
			const cy = r() * T$9;
			const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 16 + r() * 10);
			gg.addColorStop(0, rgba$1(LAVA$1.bright, .9));
			gg.addColorStop(1, rgba$1(LAVA$1.bright, 0));
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$9, T$9);
		}
		ctx.strokeStyle = rgba$1(LAVA$1.hot, .8);
		ctx.lineWidth = 1.6;
		ctx.lineCap = "round";
		for (let i = 0; i < 2; i++) {
			const x0 = r() * T$9;
			const y0 = 8 + i * 22 + r() * 10;
			ctx.beginPath();
			ctx.moveTo(x0 - 14, y0);
			ctx.bezierCurveTo(x0 - 6, y0 - 5, x0 + 2, y0 + 5, x0 + 12, y0 - 2);
			ctx.stroke();
		}
		const crusts = 2 + Math.floor(r() * 2);
		for (let i = 0; i < crusts; i++) crustPlate(ctx, 8 + r() * 36, 8 + r() * 36, 4 + r() * 4, r, rgba$1(LAVA$1.crust, .8), rgba$1(LAVA$1.crustEdge, .85));
		ctx.strokeStyle = rgba$1(LAVA$1.crustEdge, .7);
		ctx.lineWidth = 1.3;
		ctx.lineCap = "round";
		for (let i = 0; i < 2; i++) {
			let px = r() * T$9;
			let py = r() * T$9;
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
		const x1 = same.e ? T$9 : T$9 - f;
		const y1 = same.s ? T$9 : T$9 - f;
		ctx.fillStyle = rgba$1(color, alpha);
		ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
		const stops = (g, inner) => {
			for (const [t, k] of FEATHER_STOPS) g.addColorStop(inner === 1 ? 1 - t : t, rgba$1(color, alpha * k));
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
		if (!same.s) band(0, T$9, 0, T$9 - f, [
			x0,
			T$9 - f,
			x1 - x0,
			f
		]);
		if (!same.w) band(0, 0, f, 0, [
			0,
			y0,
			f,
			y1 - y0
		]);
		if (!same.e) band(T$9, 0, T$9 - f, 0, [
			T$9 - f,
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
		if (!same.n && !same.e) corner(T$9 - f, f, T$9 - f, 0);
		if (!same.s && !same.e) corner(T$9 - f, T$9 - f, T$9 - f, T$9 - f);
		if (!same.s && !same.w) corner(f, T$9 - f, 0, T$9 - f);
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
		const x1 = same.e ? T$9 : 48;
		const y1 = same.s ? T$9 : 48;
		const cx = x0 + 6 + r() * Math.max(1, x1 - x0 - 12);
		const cy = y0 + 6 + r() * Math.max(1, y1 - y0 - 12);
		const g = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14 + r() * 6);
		g.addColorStop(0, rgba$1(mix$1(color, "#000000", .2), .45));
		g.addColorStop(1, rgba$1(mix$1(color, "#000000", .2), 0));
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
		const cx = ox + r() * T$9;
		const cy = oy + r() * T$9;
		const rad = 20 + r() * 10;
		const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, rad);
		g.addColorStop(0, rgba$1(DEEP_WATER.dark, .32));
		g.addColorStop(1, rgba$1(DEEP_WATER.dark, 0));
		ctx.fillStyle = g;
		ctx.fillRect(cx - rad, cy - rad, rad * 2, rad * 2);
		if (r() < .6) {
			const wx = ox + r() * T$9 - 10;
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
			ctx.fillRect(0, 0, T$9, T$9);
			featherFill(ctx, same, 3, WET, .4);
		}
		featherFill(ctx, same, 12, DEEP_WATER.base, .97);
		const x0 = same.w ? 0 : 12;
		const y0 = same.n ? 0 : 12;
		const x1 = same.e ? T$9 : 40;
		const y1 = same.s ? T$9 : 40;
		ctx.save();
		ctx.beginPath();
		ctx.rect(x0, y0, x1 - x0, y1 - y0);
		ctx.clip();
		ctx.fillStyle = rgba$1(DEEP_WATER.dark, .18);
		ctx.fillRect(0, 0, T$9, T$9);
		for (const [dx, dy] of cloudNeighbors(s)) deepFeatures(ctx, s.x + dx, s.y + dy, dx * T$9, dy * T$9);
		deepFeatures(ctx, s.x, s.y, 0, 0);
		ctx.restore();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/ashenTerrain.ts
	var T$8 = 52;
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
		ctx.fillRect(0, 0, T$8, T$8);
		for (let i = 0; i < 5; i++) dot$3(ctx, r() * T$8, r() * T$8, 3 + r() * 5, "rgba(0,0,0,0.18)");
		for (let i = 0; i < 6; i++) dot$3(ctx, r() * T$8, r() * T$8, 1, "rgba(200,180,160,0.25)");
		if (ashGlowAt(s.x, s.y, 202)) {
			let px = r() * T$8;
			let py = 0;
			const pts = [[px, py]];
			for (let i = 0; i < 5; i++) {
				px += (r() - .5) * 16;
				py += T$8 / 5;
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
		ctx.fillRect(0, 0, T$8, T$8);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,240,200,0.05)" : "rgba(0,0,0,0.07)";
			ctx.beginPath();
			ctx.ellipse(r() * T$8, r() * T$8, 8 + r() * 10, 6 + r() * 8, r() * TAU$2, 0, TAU$2);
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
		ctx.fillRect(0, 0, T$8, T$8);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.07)";
			ctx.beginPath();
			ctx.ellipse(r() * T$8, r() * T$8, 8 + r() * 10, 5 + r() * 7, r() * TAU$2, 0, TAU$2);
			ctx.fill();
		}
		for (let i = 0; i < 14; i++) {
			ctx.fillStyle = r() < .4 ? "rgba(210,200,190,0.35)" : "rgba(30,24,20,0.55)";
			ctx.fillRect(r() * T$8, r() * T$8, 1.8, 1.8);
		}
	}
	/** 焦黑岩壁：深色岩面加岩縫，偶爾有餘燼亮點；南鄰不是牆時畫更深的立面（比單位高）。 */
	function ashWall(ctx, s) {
		const r = rng(s.x, s.y, 205);
		ctx.fillStyle = "#4a3e38";
		ctx.fillRect(0, 0, T$8, T$8);
		ctx.fillStyle = "rgba(255,255,255,0.1)";
		ctx.fillRect(0, 0, T$8, 3);
		ctx.strokeStyle = "rgba(0,0,0,0.6)";
		ctx.lineWidth = 1.5;
		for (let i = 0; i < 4; i++) {
			const x = r() * T$8;
			ctx.beginPath();
			ctx.moveTo(x, r() * T$8 * .3);
			ctx.lineTo(x + (r() - .5) * 10, T$8 * .55);
			ctx.lineTo(x + (r() - .5) * 12, T$8);
			ctx.stroke();
		}
		if (ashGlowAt(s.x, s.y, 206)) for (let i = 0; i < 3; i++) dot$3(ctx, 4 + r() * 44, T$8 * .25 + r() * T$8 * .6, 1.3, ASH.ember);
		if (s.wallFace) {
			ctx.fillStyle = "#2a221e";
			ctx.fillRect(0, 40, T$8, 12);
			ctx.fillStyle = "rgba(0,0,0,0.35)";
			ctx.fillRect(0, 40, T$8, 2);
			ctx.strokeStyle = "rgba(0,0,0,0.6)";
			ctx.lineWidth = 1.2;
			ctx.beginPath();
			for (let k = 8 + r() * 6; k < T$8; k += 13 + r() * 6) {
				ctx.moveTo(k, 42);
				ctx.lineTo(k + (r() - .5) * 4, T$8);
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
		const g = ctx.createLinearGradient(0, 0, 0, T$8);
		g.addColorStop(0, "#0c0806");
		g.addColorStop(1, "#1a0a06");
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$8, T$8);
		const glow = ctx.createRadialGradient(T$8 / 2, T$8, 2, T$8 / 2, T$8, T$8 * .45);
		glow.addColorStop(0, rgba$1("#ff4a10", ASH_RIFT_GLOW_ALPHA));
		glow.addColorStop(1, rgba$1("#ff4a10", 0));
		ctx.fillStyle = glow;
		ctx.fillRect(0, T$8 / 2, T$8, T$8 / 2);
		if (s.lip.n) cliffLip$1(ctx, r, [
			0,
			0,
			T$8,
			0
		], [0, 1]);
		if (s.lip.s) cliffLip$1(ctx, r, [
			0,
			T$8,
			T$8,
			T$8
		], [0, -1]);
		if (s.lip.w) cliffLip$1(ctx, r, [
			0,
			0,
			0,
			T$8
		], [1, 0]);
		if (s.lip.e) cliffLip$1(ctx, r, [
			T$8,
			0,
			T$8,
			T$8
		], [-1, 0]);
		if (s.lip.n) {
			const gg = ctx.createLinearGradient(0, 0, 0, 14);
			gg.addColorStop(0, "rgba(58,48,42,0.85)");
			gg.addColorStop(1, "rgba(58,48,42,0)");
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$8, 14);
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
		ctx.fillRect(0, 0, T$8, T$8);
		ctx.fillStyle = "rgba(150,140,130,0.35)";
		for (let i = 0; i < 4; i++) {
			ctx.beginPath();
			ctx.ellipse(10 + r() * 32, 10 + r() * 32, 5 + r() * 4, 2 + r() * 2, r(), 0, TAU$2);
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
		if (s.lip.n) ctx.fillRect(0, 0, T$8, 4);
		if (s.lip.w) ctx.fillRect(0, 0, 4, T$8);
		if (s.lip.e) ctx.fillRect(48, 0, 4, T$8);
		if (s.lip.s) ctx.fillRect(0, 48, T$8, 4);
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/lowWallArt.ts
	var T$7 = 52;
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
		const x1 = s.joinR ? T$7 : 48;
		const capY = T$7 * .3;
		const capH = T$7 * .16;
		const faceH = T$7 * .26;
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/ashenObjects.ts
	var T$6 = 52;
	var OUT$7 = ASH.outline;
	function box$2(ctx, x, y, w, h, fill, lw = 2, r = 2) {
		roundRect(ctx, x, y, w, h, r);
		ctx.fillStyle = fill;
		ctx.fill();
		ctx.lineWidth = lw;
		ctx.strokeStyle = OUT$7;
		ctx.stroke();
	}
	/** 破木箱：一角破洞，鐵包角（半掩護、可燃）。 */
	function brokenCrate(ctx) {
		shadowEllipse(ctx, 29, 33, T$6 * .34, T$6 * .28);
		const s = T$6 * .62;
		const o = 19.759999999999998 / 2;
		box$2(ctx, o, o, s, s, "#7a5a38", 2, 3);
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
		]) box$2(ctx, cx, cy, 7, 7, ASH.ash, 1.2, 1);
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
		const c = T$6 / 2;
		ctx.fillStyle = "rgba(0,0,0,0.3)";
		ctx.beginPath();
		ctx.moveTo(20, 46);
		ctx.lineTo(32, 46);
		ctx.lineTo(48, 52);
		ctx.lineTo(34, 52);
		ctx.fill();
		box$2(ctx, 15, 40, 22, 8, ASH.ruinFace);
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
		ctx.strokeStyle = OUT$7;
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
		for (const [dx, dy] of [[-4, 24], [2, 34]]) dot$3(ctx, c + dx, dy, 1.6, "#1a120c");
	}
	/** 鐵油桶（鏽）：灰鐵桶身、鏽斑，桶身貼四區共用的危險記號（會爆）。 */
	function rustyBarrel(ctx) {
		shadowEllipse(ctx, 29, 34, T$6 * .3, T$6 * .24);
		const cx = T$6 / 2;
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
		ctx.strokeStyle = OUT$7;
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
		ctx.ellipse(cx, 14, w, 5, 0, 0, TAU$2);
		ctx.fillStyle = "#6a6e70";
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$7;
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
		]) dot$3(ctx, cx + dx, dy, rad, "#9a4a20");
		hazardMark(ctx, 23, 34, 6.5);
	}
	/** 焦黑倒木：中段炭化，上面有餘燼點（半掩護、可燃）。 */
	function charredLog(ctx, s) {
		shadowEllipse(ctx, 28, 35, T$6 * .42, T$6 * .14);
		box$2(ctx, 6, T$6 / 2 - 4, 40, 13, "#4a3628", 2, 6);
		ctx.strokeStyle = "rgba(0,0,0,0.5)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		ctx.moveTo(10, 27);
		ctx.lineTo(36, 26);
		ctx.moveTo(14, 31);
		ctx.lineTo(40, 31);
		ctx.stroke();
		ctx.beginPath();
		ctx.ellipse(44, 28.5, 4, 6.5, 0, 0, TAU$2);
		ctx.fillStyle = "#8a6a48";
		ctx.fill();
		ctx.lineWidth = 1.5;
		ctx.strokeStyle = OUT$7;
		ctx.stroke();
		ctx.fillStyle = "#1a120c";
		ctx.fillRect(16, 23, 10, 11);
		ctx.fillRect(30, 23, 5, 11);
		if (ashGlowAt(s.x, s.y, 212)) for (const x of [20, 32]) dot$3(ctx, x, 28, 1.2, ASH.ember);
	}
	/** 枯草堆（隱蔽、可燃）：一叢較高的乾黃草葉。 */
	function dryTuft(ctx, s) {
		const r = rng(s.x, s.y, 213);
		shadowEllipse(ctx, 28, T$6 * .74, T$6 * .36, T$6 * .12);
		ctx.lineCap = "round";
		ctx.lineWidth = 2.6;
		for (let i = 0; i < 16; i++) {
			const x = 10 + r() * 32;
			const y = T$6 * .72;
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
			ctx.translate(T$6, 0);
			ctx.rotate(Math.PI / 2);
		}
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		ctx.fillRect(9, 0, 40, T$6);
		for (let y = 1; y < T$6; y += 8) {
			box$2(ctx, 8, y, 36, 6.5, shade("#7a5a38", .9 + y * 7 % 10 / 50), 1.4, 1);
			ctx.fillStyle = "#1e140c";
			ctx.fillRect(8, y, 5, 6.5);
			ctx.fillRect(37, y, 7, 6.5);
		}
		for (const y of [0, 44]) {
			box$2(ctx, 3, y, 6, 8, "#3a2a1e", 1.4, 1);
			box$2(ctx, 43, y, 6, 8, "#3a2a1e", 1.4, 1);
		}
		ctx.restore();
	}
	/** 枯樹（本區主場）：焦黑分枝，有餘燼點（擋視線，畫到格頂；可燃、可推倒）。 */
	function charredTree(ctx, s) {
		const c = T$6 / 2;
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		ctx.beginPath();
		ctx.ellipse(29, 46, 12, 4, 0, 0, TAU$2);
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
		for (const [color, extra] of [[OUT$7, 3], ["#3a2a20", 0]]) {
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
		]) dot$3(ctx, x, y, 1.4, ASH.ember);
	}
	/** 灰水上的浮板：木板拼成，架在灰水坑上；受損時木縫變大，最後缺一塊露出灰水（薄冰自己畫裂痕）。 */
	function floatPlanks(ctx, s) {
		const stage = s.hpStage;
		const r = rng(s.x, s.y, 215);
		ctx.fillStyle = "#2c3034";
		ctx.fillRect(0, 0, T$6, T$6);
		ctx.globalAlpha = stage === 2 ? .8 : .95;
		roundRect(ctx, 5, 5, 42, 42, 6);
		ctx.fillStyle = "#8a6a48";
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = "#3a2a1e";
		ctx.stroke();
		ctx.globalAlpha = 1;
		ctx.strokeStyle = rgba$1("#000000", stage === 0 ? .35 : .55);
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
	var OUT$6 = "#1c1712";
	var C$1 = {
		slate: "#7d8c84",
		moss: "#5a8a3a",
		red: "#b8432f",
		redDark: "#8a2f20",
		path: "#b89a62",
		grass: "#689a70",
		rock: "#6e6a62"
	};
	/** explore.js 的 xorshift（地面、地物用）。 */
	function xorshift(seed) {
		let s = seed >>> 0 || 1;
		return () => {
			s ^= s << 13;
			s >>>= 0;
			s ^= s >> 17;
			s ^= s << 5;
			s >>>= 0;
			return s % 1e5 / 1e5;
		};
	}
	var R$1 = (gx, gy, k) => xorshift(gx * 73856093 ^ gy * 19349663 ^ k * 83492791);
	/** realms.js 的種子（mulberry32；石板、竹子用）。 */
	var RR = (gx, gy, k) => seeded(gx * 73856093 ^ gy * 19349663 ^ k * 83492791);
	function rr$2(ctx, x, y, w, h, r) {
		ctx.beginPath();
		ctx.moveTo(x + r, y);
		ctx.arcTo(x + w, y, x + w, y + h, r);
		ctx.arcTo(x + w, y + h, x, y + h, r);
		ctx.arcTo(x, y + h, x, y, r);
		ctx.arcTo(x, y, x + w, y, r);
		ctx.closePath();
	}
	function box$1(ctx, x, y, w, h, fill, stroke = OUT$6, lw = 2, r = 2) {
		rr$2(ctx, x, y, w, h, r);
		ctx.fillStyle = fill;
		ctx.fill();
		if (stroke !== null) {
			ctx.lineWidth = lw;
			ctx.strokeStyle = stroke;
			ctx.stroke();
		}
	}
	function dot$1(ctx, x, y, r, fill) {
		ctx.fillStyle = fill;
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU$2);
		ctx.fill();
	}
	function shadow$1(ctx, cx, cy, rx, ry, a = .3) {
		ctx.fillStyle = `rgba(0,0,0,${a})`;
		ctx.beginPath();
		ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU$2);
		ctx.fill();
	}
	/** 放射光暈（events.js 的 `glow`：`c` 是 `rgba(...)`，外圈透明）。 */
	function glow$1(ctx, x, y, r, c, a) {
		const g = ctx.createRadialGradient(x, y, 0, x, y, r);
		g.addColorStop(0, c);
		g.addColorStop(1, c.replace(/[\d.]+\)$/, "0)"));
		ctx.save();
		ctx.globalAlpha = a;
		ctx.fillStyle = g;
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU$2);
		ctx.fill();
		ctx.restore();
	}
	/** realms.js 的石板（雲嶺青石板）。 */
	function slabs(ctx, x, y, gx, gy) {
		const r = RR(gx, gy, 1);
		ctx.fillStyle = "#56645c";
		ctx.fillRect(x, y, 52, 52);
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
			ctx.fillStyle = shade("#7d8c84", .92 + r() * .16);
			ctx.beginPath();
			ctx.roundRect(x + bx * 52 + 1.5, y + by * 52 + 1.5, bw * 52 - 3, bh * 52 - 3, 3);
			ctx.fill();
			ctx.fillStyle = rgba$1("#ffffff", .12);
			ctx.fillRect(x + bx * 52 + 2, y + by * 52 + 2, bw * 52 - 4, 2);
		}
		if (r() < .45) {
			ctx.fillStyle = rgba$1("#5a8a3a", .75);
			for (let i = 0; i < 4; i++) {
				ctx.beginPath();
				ctx.arc(x + r() * 52, y + r() * 52, 2 + r() * 3, 0, TAU$2);
				ctx.fill();
			}
		}
	}
	/** 黑曜岩石板的顏色（6V-3）：底、石塊、受光、裂紋（同荒原焦土地的熔岩光裂縫，但壓暗成暗紅）。 */
	var OBSIDIAN = {
		base: "#121014",
		block: "#26222a",
		sheen: "rgba(190,180,220,0.22)",
		crack: "#140c08",
		glow: "#b8321e"
	};
	/**
	* 荒原祭壇前的黑曜岩石板（6V-3，RT-2 驗收：青石是雲嶺的材質）：近黑的石塊、左上一道玻璃光澤，
	* 一道暗紅發光的裂紋（先畫黑縫、再疊模糊的暗紅光，同 `ashenTerrain` 的裂縫畫法）。石塊切法、裂紋照格子座標種子。
	*/
	function obsidianSlab(ctx, gx, gy) {
		const x = gx * 52;
		const y = gy * 52;
		const r = RR(gx, gy, 7);
		ctx.fillStyle = OBSIDIAN.base;
		ctx.fillRect(x, y, 52, 52);
		const blocks = r() < .5 ? [
			[
				0,
				0,
				.5,
				.55
			],
			[
				.5,
				0,
				.5,
				.55
			],
			[
				0,
				.55,
				1,
				.45
			]
		] : [
			[
				0,
				0,
				1,
				.5
			],
			[
				0,
				.5,
				.45,
				.5
			],
			[
				.45,
				.5,
				.55,
				.5
			]
		];
		for (const [bx, by, bw, bh] of blocks) {
			ctx.fillStyle = shade(OBSIDIAN.block, .9 + r() * .25);
			ctx.beginPath();
			ctx.roundRect(x + bx * 52 + 1.5, y + by * 52 + 1.5, bw * 52 - 3, bh * 52 - 3, 2);
			ctx.fill();
			ctx.fillStyle = OBSIDIAN.sheen;
			ctx.beginPath();
			ctx.moveTo(x + bx * 52 + 4, y + by * 52 + 4);
			ctx.lineTo(x + bx * 52 + bw * 52 * .45, y + by * 52 + 4);
			ctx.lineTo(x + bx * 52 + 4, y + by * 52 + bh * 52 * .45);
			ctx.closePath();
			ctx.fill();
		}
		let px = x + 52 * (.25 + r() * .5);
		let py = y;
		const pts = [[px, py]];
		for (let i = 0; i < 4; i++) {
			px += (r() - .5) * 14;
			py += 13;
			pts.push([px, py]);
		}
		const trace = () => pts.forEach(([a, b], i) => i === 0 ? ctx.moveTo(a, b) : ctx.lineTo(a, b));
		ctx.strokeStyle = OBSIDIAN.crack;
		ctx.lineWidth = 3;
		ctx.lineCap = "round";
		ctx.beginPath();
		trace();
		ctx.stroke();
		glowLine(ctx, OBSIDIAN.glow, 1.3, 5, trace);
	}
	/** 雲嶺地面：`g` 草地、`p` 黃土路、`s` 青石板（explore.js 的 `ground`）。 */
	function ground$1(ctx, kind, gx, gy) {
		const x = gx * 52;
		const y = gy * 52;
		if (kind === "s") {
			slabs(ctx, x, y, gx, gy);
			return;
		}
		const r = R$1(gx, gy, 3);
		if (kind === "p") {
			ctx.fillStyle = shade(C$1.path, .95 + r() * .1);
			ctx.fillRect(x, y, 52, 52);
			for (let i = 0; i < 8; i++) {
				ctx.fillStyle = r() < .5 ? "rgba(90,70,40,0.4)" : "rgba(255,240,210,0.35)";
				ctx.fillRect(x + r() * 52, y + r() * 52, 2, 2);
			}
			return;
		}
		ctx.fillStyle = shade(C$1.grass, .95 + r() * .1);
		ctx.fillRect(x, y, 52, 52);
		ctx.lineWidth = 1.5;
		ctx.lineCap = "round";
		for (let i = 0; i < 6; i++) {
			const gx2 = x + 5 + r() * 42;
			const gy2 = y + 8 + r() * 39;
			ctx.strokeStyle = r() < .55 ? "#9ccf86" : "#4f8a3a";
			ctx.beginPath();
			ctx.moveTo(gx2, gy2);
			ctx.quadraticCurveTo(gx2 - 1, gy2 - 5, gx2 - 4, gy2 - 8);
			ctx.moveTo(gx2, gy2);
			ctx.quadraticCurveTo(gx2 + 1, gy2 - 5, gx2 + 4, gy2 - 9);
			ctx.stroke();
		}
	}
	var NO_SIDES$1 = {
		n: false,
		s: false,
		w: false,
		e: false
	};
	/** 荒原地面（遊戲的荒原地形畫法）：`stone` 焦土、`lava` 岩漿。 */
	function ashTile(ctx, terrain, gx, gy) {
		const spec = {
			region: "ashen_waste",
			look: "",
			terrain,
			x: gx,
			y: gy,
			height: 0,
			surface: "none",
			surfSame: NO_SIDES$1,
			lip: NO_SIDES$1,
			wallFace: false,
			blocked: terrain === "lava",
			tint: null
		};
		ctx.save();
		ctx.translate(gx * 52, gy * 52);
		ASHEN_TERRAIN[terrain]?.(ctx, spec);
		ctx.restore();
	}
	/** 荒原物件（遊戲的荒原物件畫法），左上角在 (x, y)。 */
	function ashObj(ctx, kind, x, y) {
		const spec = {
			region: "ashen_waste",
			look: "",
			kind,
			x: Math.round(x),
			y: Math.round(y),
			joinL: false,
			joinR: false,
			vertical: false,
			flammable: false,
			turnsLeft: null,
			hpStage: 0
		};
		ctx.save();
		ctx.translate(x, y);
		ASHEN_OBJECTS[kind]?.(ctx, spec);
		ctx.restore();
	}
	/** 事件插圖小牌（深底）上黑色圖示改用的淺色（6C-ART3 順手項）。 */
	var BADGE_ICON_INK = "#f2e6c8";
	var bang = (ctx, x, y, s, ink = OUT$6) => {
		ctx.fillStyle = ink;
		ctx.fillRect(x - s * .12, y - s * .5, s * .24, s * .65);
		ctx.fillRect(x - s * .12, y + s * .3, s * .24, s * .22);
	};
	var ICON$1 = {
		coin(ctx, x, y, s) {
			dot$1(ctx, x, y + s * .1, s * .55, "#e8bb48");
			ctx.lineWidth = 1.5;
			ctx.strokeStyle = OUT$6;
			ctx.beginPath();
			ctx.arc(x, y + s * .1, s * .55, 0, TAU$2);
			ctx.stroke();
			ctx.fillStyle = OUT$6;
			ctx.fillRect(x - s * .15, y - s * .12, s * .3, s * .45);
		},
		sword(ctx, x, y, s) {
			ctx.strokeStyle = OUT$6;
			ctx.lineWidth = 4;
			ctx.beginPath();
			ctx.moveTo(x - s * .5, y + s * .5);
			ctx.lineTo(x + s * .5, y - s * .5);
			ctx.stroke();
			ctx.strokeStyle = "#dfe4ea";
			ctx.lineWidth = 2;
			ctx.stroke();
			ctx.strokeStyle = "#e8bb48";
			ctx.lineWidth = 2.5;
			ctx.beginPath();
			ctx.moveTo(x - s * .45, y + s * .1);
			ctx.lineTo(x - s * .1, y + s * .45);
			ctx.stroke();
		},
		bang,
		ask(ctx, x, y, s, ink = OUT$6) {
			ctx.strokeStyle = ink;
			ctx.lineWidth = s * .22;
			ctx.lineCap = "round";
			ctx.beginPath();
			ctx.arc(x, y - s * .18, s * .28, Math.PI * 1.05, Math.PI * .45);
			ctx.lineTo(x, y + s * .18);
			ctx.stroke();
			dot$1(ctx, x, y + s * .45, s * .12, ink);
		},
		rest(ctx, x, y, s) {
			ctx.fillStyle = "#ff8a2a";
			ctx.beginPath();
			ctx.moveTo(x, y - s * .55);
			ctx.quadraticCurveTo(x + s * .45, y, x, y + s * .4);
			ctx.quadraticCurveTo(x - s * .45, y, x, y - s * .55);
			ctx.fill();
			ctx.fillStyle = "#ffd23a";
			ctx.beginPath();
			ctx.ellipse(x, y + s * .12, s * .15, s * .25, 0, 0, TAU$2);
			ctx.fill();
		},
		portal(ctx, x, y, s) {
			ctx.save();
			ctx.shadowColor = "#8fe0ff";
			ctx.shadowBlur = 6;
			ctx.strokeStyle = "#5ac8f0";
			ctx.lineWidth = 2;
			ctx.beginPath();
			ctx.arc(x, y, s * .45, 0, TAU$2);
			ctx.stroke();
			ctx.beginPath();
			ctx.arc(x, y, s * .2, 0, TAU$2);
			ctx.stroke();
			ctx.restore();
		},
		scroll(ctx, x, y, s) {
			box$1(ctx, x - s * .5, y - s * .4, s, s * .8, "#f2e6c8", OUT$6, 1.5, 1);
			ctx.fillStyle = C$1.redDark;
			ctx.fillRect(x - s * .6, y - s * .5, s * 1.2, s * .15);
			ctx.fillRect(x - s * .6, y + s * .35, s * 1.2, s * .15);
			ctx.strokeStyle = "#8a7a5a";
			ctx.lineWidth = 1;
			for (const k of [
				-.15,
				0,
				.15
			]) {
				ctx.beginPath();
				ctx.moveTo(x - s * .3, y + s * k);
				ctx.lineTo(x + s * .3, y + s * k);
				ctx.stroke();
			}
		},
		notes(ctx, x, y, s) {
			box$1(ctx, x - s * .5, y - s * .4, s, s * .7, "#f2e6c8", OUT$6, 1.5, 3);
			ctx.fillStyle = "#f2e6c8";
			ctx.beginPath();
			ctx.moveTo(x - s * .2, y + s * .28);
			ctx.lineTo(x - s * .3, y + s * .5);
			ctx.lineTo(x, y + s * .28);
			ctx.fill();
			ctx.strokeStyle = "#8a7a5a";
			ctx.lineWidth = 1;
			for (const k of [-.18, .02]) {
				ctx.beginPath();
				ctx.moveTo(x - s * .3, y + s * k);
				ctx.lineTo(x + s * .3, y + s * k);
				ctx.stroke();
			}
		},
		warn(ctx, x, y, s) {
			ctx.beginPath();
			ctx.moveTo(x, y - s * .5);
			ctx.lineTo(x + s * .5, y + s * .4);
			ctx.lineTo(x - s * .5, y + s * .4);
			ctx.closePath();
			ctx.fillStyle = "#ffd23a";
			ctx.fill();
			ctx.lineWidth = 1.5;
			ctx.strokeStyle = OUT$6;
			ctx.stroke();
			bang(ctx, x, y + s * .02, s * .6);
		}
	};
	var BUBBLE_FILL = {
		quest: "#ffd23a",
		talk: "#ffffff",
		danger: "#ff6a5a",
		info: "#bfe8ff"
	};
	/** 頭上的泡泡（只放圖示）：quest 黃、talk 白、danger 紅、info 淺藍。 */
	function bubble(ctx, x, y, icon, kind) {
		const fill = BUBBLE_FILL[kind];
		ctx.save();
		ctx.shadowColor = "rgba(0,0,0,0.35)";
		ctx.shadowOffsetY = 2;
		ctx.shadowBlur = 3;
		rr$2(ctx, x - 13, y - 26, 26, 22, 8);
		ctx.fillStyle = fill;
		ctx.fill();
		ctx.restore();
		ctx.beginPath();
		ctx.moveTo(x - 4, y - 5);
		ctx.lineTo(x, y + 2);
		ctx.lineTo(x + 4, y - 5);
		ctx.fillStyle = fill;
		ctx.fill();
		rr$2(ctx, x - 13, y - 26, 26, 22, 8);
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$6;
		ctx.stroke();
		ctx.fillStyle = fill;
		ctx.fillRect(x - 3, y - 6, 6, 3);
		ICON$1[icon](ctx, x, y - 15, 13);
	}
	function campfire(ctx, gx, gy) {
		const x = gx * 52;
		const y = gy * 52;
		const cx = x + 26;
		const cy = y + 31.2;
		const g = ctx.createRadialGradient(cx, cy, 3, cx, cy, 46);
		g.addColorStop(0, "rgba(255,190,90,0.45)");
		g.addColorStop(1, "rgba(255,190,90,0)");
		ctx.fillStyle = g;
		ctx.beginPath();
		ctx.arc(cx, cy, 46, 0, TAU$2);
		ctx.fill();
		for (let k = 0; k < 7; k++) {
			const a = k / 7 * TAU$2;
			box$1(ctx, cx + Math.cos(a) * 13 - 4, cy + Math.sin(a) * 7 - 3, 8, 6, "#8a8a84", OUT$6, 1.2, 3);
		}
		ctx.strokeStyle = "#5a3a20";
		ctx.lineWidth = 4;
		ctx.beginPath();
		ctx.moveTo(cx - 9, cy + 3);
		ctx.lineTo(cx + 9, cy - 3);
		ctx.moveTo(cx - 9, cy - 3);
		ctx.lineTo(cx + 9, cy + 3);
		ctx.stroke();
		ctx.save();
		ctx.shadowColor = "#ff8a2a";
		ctx.shadowBlur = 12;
		ICON$1.rest(ctx, cx, cy - 8, 22);
		ctx.restore();
	}
	function sparkle(ctx, x, y) {
		ctx.beginPath();
		ctx.moveTo(x, y - 4);
		ctx.lineTo(x + 1.2, y - 1.2);
		ctx.lineTo(x + 4, y);
		ctx.lineTo(x + 1.2, y + 1.2);
		ctx.lineTo(x, y + 4);
		ctx.lineTo(x - 1.2, y + 1.2);
		ctx.lineTo(x - 4, y);
		ctx.lineTo(x - 1.2, y - 1.2);
		ctx.fill();
	}
	function chest(ctx, gx, gy) {
		const x = gx * 52;
		const y = gy * 52;
		const cx = x + 26;
		shadow$1(ctx, cx + 3, y + 40.56, 16, 5);
		box$1(ctx, cx - 14, y + 22, 28, 18, "#8a5a30", OUT$6, 2, 2);
		ctx.beginPath();
		ctx.moveTo(cx - 14, y + 24);
		ctx.quadraticCurveTo(cx, y + 8, cx + 14, y + 24);
		ctx.closePath();
		ctx.fillStyle = "#a06a38";
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$6;
		ctx.stroke();
		ctx.fillStyle = "#e8bb48";
		ctx.fillRect(cx - 15, y + 22, 30, 3);
		box$1(ctx, cx - 3, y + 24, 6, 7, "#e8bb48", OUT$6, 1.2, 1);
		ctx.save();
		ctx.globalAlpha = .9;
		ctx.fillStyle = "#fff4c0";
		for (const [sx, sy] of [
			[-16, 8],
			[15, 12],
			[4, 2]
		]) sparkle(ctx, cx + sx, y + sy);
		ctx.restore();
	}
	function stele(ctx, gx, gy) {
		const x = gx * 52;
		const y = gy * 52;
		const cx = x + 26;
		shadow$1(ctx, cx + 4, y + 52 * .85, 16, 5);
		box$1(ctx, cx - 10, y + 10, 20, 34, "#8a948c", OUT$6, 2, 6);
		ctx.fillStyle = rgba$1(C$1.moss, .8);
		ctx.beginPath();
		ctx.arc(cx - 6, y + 40, 5, 0, TAU$2);
		ctx.fill();
		ctx.strokeStyle = "#4a524c";
		ctx.lineWidth = 1.2;
		for (const k of [
			18,
			24,
			30
		]) {
			ctx.beginPath();
			ctx.moveTo(cx - 5, y + k);
			ctx.lineTo(cx + 5, y + k);
			ctx.stroke();
		}
	}
	/** realms.js 的竹子（一叢 4 根）。 */
	function bamboo(ctx, x, y) {
		const r = RR(x, y, 9);
		shadow$1(ctx, x + 26 + 3, y + 44.72, 18, 5, .35);
		for (let i = 0; i < 4; i++) {
			const bx = x + 10 + i * 10 + r() * 3;
			const top = y + 2 + r() * 8;
			ctx.fillStyle = i % 2 ? "#4f8a3a" : "#6aa84a";
			ctx.fillRect(bx, top, 5, y + 44.72 - top);
			ctx.strokeStyle = OUT$6;
			ctx.lineWidth = 1.5;
			ctx.strokeRect(bx, top, 5, y + 44.72 - top);
			ctx.fillStyle = "#2f5a22";
			for (let k = top + 9; k < y + 41.6; k += 10) ctx.fillRect(bx - 1, k, 7, 2);
			ctx.fillStyle = "#7cc05a";
			ctx.beginPath();
			ctx.ellipse(bx + 9, top + 6 + r() * 6, 7, 2.5, -.5, 0, TAU$2);
			ctx.fill();
		}
	}
	/** 大片竹林（cloudTiles.js）。 */
	function bambooGrove(ctx, x, y, w, h) {
		shadow$1(ctx, x + w * 52 / 2 + 6, y + h * 52 - 8, w * 52 * .5, 12, .35);
		const r = R$1(x, y, 81);
		for (let k = 0; k < w * h * 3; k++) bamboo(ctx, x + r() * (w - 1) * 52, y + r() * (h - .6) * 52);
	}
	/** 枯木林（ashenTiles.js；枯木、枯草用遊戲的荒原物件）。 */
	function deadGrove(ctx, x, y, w, h) {
		shadow$1(ctx, x + w * 52 / 2 + 6, y + h * 52 - 8, w * 52 * .5, 12, .35);
		const r = R$1(x, y, 61);
		for (let k = 0; k < w * h * 2 + 1; k++) ashObj(ctx, "dead_tree", x + r() * (w - .8) * 52, y + r() * (h - .8) * 52);
		for (let k = 0; k < w * h; k++) ashObj(ctx, "grass", x + r() * (w - 1) * 52, y + (h - 1) * 52 * r());
	}
	function pine(ctx, x, y) {
		const cx = x + 26;
		shadow$1(ctx, cx + 4, y + 52 * .9, 20, 6, .35);
		ctx.strokeStyle = OUT$6;
		ctx.lineWidth = 7;
		ctx.lineCap = "round";
		ctx.beginPath();
		ctx.moveTo(cx, y + 47.84);
		ctx.quadraticCurveTo(cx - 6, y + 24, cx + 4, y + 8);
		ctx.stroke();
		ctx.strokeStyle = "#6a4a30";
		ctx.lineWidth = 4.5;
		ctx.stroke();
		for (const [dx, dy, rw] of [
			[
				-14,
				10,
				16
			],
			[
				12,
				4,
				15
			],
			[
				-2,
				-4,
				14
			],
			[
				14,
				20,
				11
			]
		]) {
			ctx.fillStyle = "#2f5a3a";
			ctx.beginPath();
			ctx.ellipse(cx + dx, y + dy, rw, rw * .45, 0, 0, TAU$2);
			ctx.fill();
			ctx.lineWidth = 1.6;
			ctx.strokeStyle = OUT$6;
			ctx.stroke();
			ctx.fillStyle = "rgba(160,220,140,0.25)";
			ctx.beginPath();
			ctx.ellipse(cx + dx - 3, y + dy - 2, rw * .6, rw * .2, 0, 0, TAU$2);
			ctx.fill();
		}
	}
	function boulder(ctx, x, y) {
		shadow$1(ctx, x + 26 + 3, y + 40.56, 20, 6);
		ctx.beginPath();
		ctx.moveTo(x + 8, y + 40);
		ctx.lineTo(x + 12, y + 20);
		ctx.lineTo(x + 26, y + 12);
		ctx.lineTo(x + 40, y + 18);
		ctx.lineTo(x + 45, y + 38);
		ctx.closePath();
		ctx.fillStyle = C$1.rock;
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$6;
		ctx.stroke();
		ctx.fillStyle = "rgba(255,255,255,0.18)";
		ctx.fillRect(x + 16, y + 18, 12, 3);
		dot$1(ctx, x + 34, y + 30, 3, rgba$1(C$1.moss, .8));
	}
	/** 花草（cloudTiles.js；樣張以像素座標當種子）。 */
	function flowers(ctx, x, y, gx, gy) {
		const r = R$1(gx, gy, 91);
		const colors = [
			"#f2e6c8",
			"#e8a0b0",
			"#ffd23a"
		];
		for (let k = 0; k < 6; k++) {
			const px = x + 6 + r() * 40;
			const py = y + 10 + r() * 34;
			ctx.strokeStyle = "#4f8a3a";
			ctx.lineWidth = 1.2;
			ctx.beginPath();
			ctx.moveTo(px, py + 5);
			ctx.lineTo(px, py);
			ctx.stroke();
			dot$1(ctx, px, py, 2.2, colors[k % 3]);
		}
	}
	/** 飄霧（固定時間 `t`，不動）。 */
	function mistWisp(ctx, x, y, t) {
		for (let k = 0; k < 3; k++) {
			const px = x + 10 + k * 14 + Math.sin(t / 900 + k) * 4;
			const py = y + 20 + k * 6;
			const g = ctx.createRadialGradient(px, py, 1, px, py, 16);
			g.addColorStop(0, "rgba(232,232,224,0.45)");
			g.addColorStop(1, "rgba(232,232,224,0)");
			ctx.fillStyle = g;
			ctx.fillRect(x - 10, y, 72, 52);
		}
	}
	/** 雲嶺祭壇：石台＋香爐＋煙。 */
	function altar(ctx, x, y) {
		const cx = x + 26;
		shadow$1(ctx, cx + 3, y + 43.68, 22, 6);
		box$1(ctx, x + 6, y + 26, 40, 16, shade(C$1.slate, 1.1), OUT$6, 2, 2);
		box$1(ctx, x + 10, y + 22, 32, 6, C$1.slate, OUT$6, 1.6, 1);
		ctx.beginPath();
		ctx.ellipse(cx, y + 20, 8, 4, 0, 0, TAU$2);
		ctx.fillStyle = "#8a6a3a";
		ctx.fill();
		ctx.lineWidth = 1.6;
		ctx.strokeStyle = OUT$6;
		ctx.stroke();
		box$1(ctx, cx - 7, y + 14, 14, 7, "#a07a40", OUT$6, 1.6, 2);
		ctx.strokeStyle = "rgba(240,240,235,0.7)";
		ctx.lineWidth = 1.5;
		for (let k = -1; k <= 1; k++) {
			ctx.beginPath();
			ctx.moveTo(cx + k * 3, y + 13);
			ctx.bezierCurveTo(cx + k * 3 - 4, y + 6, cx + k * 3 + 4, y + 2, cx + k * 3, y - 4);
			ctx.stroke();
		}
		dot$1(ctx, x + 12, y + 30, 2, C$1.red);
		dot$1(ctx, x + 52 - 12, y + 30, 2, C$1.red);
	}
	/** 角魔古祭壇（荒原）：黑石台＋兩支彎角＋暗紅符文。 */
	function hornAltar(ctx, x, y) {
		const cx = x + 26;
		shadow$1(ctx, cx + 3, y + 44.72, 22, 6);
		box$1(ctx, x + 6, y + 28, 40, 14, "#2e2622", OUT$6, 2, 2);
		for (const s of [-1, 1]) {
			ctx.beginPath();
			ctx.moveTo(cx + s * 12, y + 30);
			ctx.quadraticCurveTo(cx + s * 22, y + 8, cx + s * 8, y + 2);
			ctx.quadraticCurveTo(cx + s * 16, y + 12, cx + s * 6, y + 30);
			ctx.closePath();
			ctx.fillStyle = "#bfb0a4";
			ctx.fill();
			ctx.lineWidth = 1.6;
			ctx.strokeStyle = OUT$6;
			ctx.stroke();
		}
		ctx.save();
		ctx.shadowColor = "#ff3a2a";
		ctx.shadowBlur = 6;
		ctx.strokeStyle = "#c83a2a";
		ctx.lineWidth = 1.4;
		ctx.beginPath();
		ctx.arc(cx, y + 35, 4, 0, TAU$2);
		ctx.moveTo(cx - 8, y + 35);
		ctx.lineTo(cx + 8, y + 35);
		ctx.stroke();
		ctx.restore();
	}
	/** 運輸車：鐵輪木車＋源晶碎片箱。 */
	function cart(ctx, x, y) {
		shadow$1(ctx, x + 26 + 4, y + 43.68, 24, 6);
		box$1(ctx, x + 4, y + 16, 44, 20, "#7a5a38", OUT$6, 2, 2);
		for (const px of [x + 12, x + 52 - 12]) {
			ctx.beginPath();
			ctx.arc(px, y + 38, 7, 0, TAU$2);
			ctx.fillStyle = "#5a5e60";
			ctx.fill();
			ctx.lineWidth = 1.8;
			ctx.strokeStyle = OUT$6;
			ctx.stroke();
		}
		box$1(ctx, x + 14, y + 8, 22, 10, "#5a4030", OUT$6, 1.4, 1);
		glow$1(ctx, x + 25, y + 12, 10, "rgba(140,220,255,0.9)", .6);
		dot$1(ctx, x + 25, y + 12, 2.6, "#c8f0ff");
	}
	/** 石燈籠（realms.js）。 */
	function stoneLantern(ctx, x, y) {
		shadow$1(ctx, x + 26 + 3, y + 44.72, 13, 4, .35);
		const g = "#9aa39c";
		const rect = (rx, ry, w, h, fill, lw = 2, r = 2) => box$1(ctx, rx, ry, w, h, fill, OUT$6, lw, r);
		rect(x + 18, y + 38, 16, 7, shade(g, .85));
		rect(x + 23, y + 26, 6, 12, g);
		rect(x + 17, y + 16, 18, 11, g);
		const lg = ctx.createRadialGradient(x + 26, y + 21, 0, x + 26, y + 21, 14);
		lg.addColorStop(0, rgba$1("#ffcf6a", .6));
		lg.addColorStop(1, rgba$1("#ffcf6a", 0));
		ctx.fillStyle = lg;
		ctx.beginPath();
		ctx.arc(x + 26, y + 21, 14, 0, TAU$2);
		ctx.fill();
		ctx.fillStyle = "#ffcf6a";
		ctx.fillRect(x + 22, y + 18, 8, 6);
		ctx.beginPath();
		ctx.moveTo(x + 12, y + 16);
		ctx.lineTo(x + 26, y + 6);
		ctx.lineTo(x + 40, y + 16);
		ctx.closePath();
		ctx.fillStyle = shade(g, .75);
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$6;
		ctx.stroke();
		rect(x + 24, y + 2, 4, 5, g, 1.5, 1);
	}
	/** 角魔火盆（RT-2：荒原祭壇取代石燈籠；位置、大小同 `stoneLantern`）：黑鐵三腳架、碗裡有火、火光暈。 */
	function hornBrazier(ctx, x, y) {
		const cx = x + 26;
		shadow$1(ctx, cx + 3, y + 44.72, 13, 4, .35);
		const iron = "#2a2624";
		ctx.lineCap = "round";
		for (const [foot, top] of [
			[-12, -6],
			[12, 6],
			[0, 0]
		]) {
			ctx.beginPath();
			ctx.moveTo(cx + top, y + 24);
			ctx.lineTo(cx + foot, y + 44);
			ctx.lineWidth = 4.5;
			ctx.strokeStyle = OUT$6;
			ctx.stroke();
			ctx.lineWidth = 2.4;
			ctx.strokeStyle = foot === 0 ? "#3e3834" : iron;
			ctx.stroke();
		}
		ctx.lineCap = "butt";
		box$1(ctx, cx - 9, y + 30, 18, 3, iron, OUT$6, 1.2, 1);
		glow$1(ctx, cx, y + 10, 26, "rgba(255,120,40,0.9)", .55);
		ctx.beginPath();
		ctx.moveTo(cx - 15, y + 16);
		ctx.quadraticCurveTo(cx, y + 32, cx + 15, y + 16);
		ctx.closePath();
		ctx.fillStyle = iron;
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$6;
		ctx.stroke();
		for (const s of [-1, 1]) {
			ctx.beginPath();
			ctx.moveTo(cx + s * 13, y + 16);
			ctx.quadraticCurveTo(cx + s * 22, y + 11, cx + s * 19, y + 3);
			ctx.quadraticCurveTo(cx + s * 17, y + 11, cx + s * 9, y + 16);
			ctx.closePath();
			ctx.fillStyle = "#bfb0a4";
			ctx.fill();
			ctx.lineWidth = 1.2;
			ctx.strokeStyle = OUT$6;
			ctx.stroke();
		}
		flame$1(ctx, cx - 6, y + 16, 12);
		flame$1(ctx, cx + 6, y + 16, 11);
		flame$1(ctx, cx, y + 16, 19);
		box$1(ctx, cx - 16, y + 14, 32, 4, "#4a403a", OUT$6, 1.5, 2);
		dot$1(ctx, cx + 7, y - 4, 1.4, "#ffb050");
		dot$1(ctx, cx - 6, y - 8, 1.1, "#ff8a3a");
	}
	/** 敵人腳下的紅色環（enemyArt.js 的 `ring`，非精英）。 */
	function enemyRing(ctx, rx) {
		ctx.save();
		ctx.globalAlpha = .3;
		ctx.fillStyle = "#d24a3a";
		ctx.beginPath();
		ctx.ellipse(0, 0, rx, rx * .3, 0, 0, TAU$2);
		ctx.fill();
		ctx.globalAlpha = .9;
		ctx.strokeStyle = "#d24a3a";
		ctx.lineWidth = 1;
		ctx.stroke();
		ctx.restore();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/townArt.ts
	var U$1 = 52;
	var OUT$5 = "#1c1712";
	var C = {
		slate: "#7d8c84",
		ink: "#56645c",
		red: "#b8432f",
		redDark: "#8a2f20",
		tile: "#3c4a48",
		mist: "#e8e8e0",
		lamp: "#ffcf6a",
		wood: "#8a6440"
	};
	var A$2 = {
		iron: "#5a5e60",
		rust: "#9a4a20",
		rag: "#c8b08a",
		hot: "#ffb030"
	};
	function doorStyleOf(kind) {
		return kind === "scrap_house" || kind === "forge_house" ? "rag" : "wood";
	}
	/** 種類固定的招牌（霧渡鎮的白牆屋舍）；`DOOR_SIGN_KINDS` 的種類改照門通往的室內設施（伺服器的 `sign`）。 */
	var SIGN = {
		tavern: "jar",
		smithy: "anvil",
		hall: "scroll",
		house: null,
		scrap_house: null,
		forge_house: null,
		stone_hall: null,
		mentor_hall: null,
		tent: null,
		fountain: null
	};
	/** 這棟的屋頂往上多蓋幾列。 */
	function roofRows(s) {
		return s.roof ?? 1;
	}
	/** 這棟的招牌圖示（沒有＝`null`）。 */
	function signOf(s) {
		return s.sign !== void 0 ? s.sign : SIGN[s.kind];
	}
	/** 門的中心（格，相對建築左邊）；沒有門的建築在正中央畫一扇關著的裝飾門。 */
	function doorCenters(s) {
		return s.doors.length > 0 ? s.doors.map((d) => d + .5) : [s.w / 2];
	}
	/**
	* 窗戶的中心（格）：由左到右，離每扇門左邊至少 1 格、右邊至少 2 格（右邊掛招牌；沒有招牌時 1 格），
	* 相鄰的窗至少隔 1 格。
	*/
	function windowCenters(s) {
		const right = signOf(s) === null ? 1 : 2;
		const doors = doorCenters(s);
		const out = [];
		let last = -10;
		for (let k = 0; k < s.w; k++) {
			const c = k + .5;
			if (!doors.every((d) => c - d <= -1 || c - d >= right)) continue;
			if (k - last < 2) continue;
			out.push(c);
			last = k;
		}
		return out;
	}
	function box(ctx, x, y, w, h, fill, stroke = OUT$5, lw = 2, r = 2) {
		ctx.beginPath();
		ctx.roundRect(x, y, w, h, r);
		ctx.fillStyle = fill;
		ctx.fill();
		if (stroke !== null) {
			ctx.lineWidth = lw;
			ctx.strokeStyle = stroke;
			ctx.stroke();
		}
	}
	function shadow(ctx, cx, cy, rx, ry, a = .3) {
		ctx.fillStyle = `rgba(0,0,0,${a})`;
		ctx.beginPath();
		ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU$2);
		ctx.fill();
	}
	function glow(ctx, x, y, r, c, a) {
		const g = ctx.createRadialGradient(x, y, 0, x, y, r);
		g.addColorStop(0, c);
		g.addColorStop(1, "rgba(0,0,0,0)");
		ctx.save();
		ctx.globalAlpha = a;
		ctx.fillStyle = g;
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU$2);
		ctx.fill();
		ctx.restore();
	}
	/** 招牌、壁爐共用的小圖示（explore.js 的 ICON）。 */
	var ICON = {
		anvil(ctx, x, y, s) {
			ctx.fillStyle = "#5a5e64";
			ctx.beginPath();
			ctx.moveTo(x - s * .7, y - s * .3);
			ctx.lineTo(x + s * .6, y - s * .3);
			ctx.lineTo(x + s * .3, y);
			ctx.lineTo(x + s * .2, y + s * .1);
			ctx.lineTo(x + s * .4, y + s * .5);
			ctx.lineTo(x - s * .4, y + s * .5);
			ctx.lineTo(x - s * .2, y + s * .1);
			ctx.lineTo(x - s * .3, y - s * .05);
			ctx.closePath();
			ctx.fill();
			ctx.lineWidth = 1.5;
			ctx.strokeStyle = OUT$5;
			ctx.stroke();
		},
		jar(ctx, x, y, s) {
			ctx.fillStyle = "#8a5a30";
			ctx.beginPath();
			ctx.ellipse(x, y + s * .15, s * .45, s * .45, 0, 0, TAU$2);
			ctx.fill();
			ctx.lineWidth = 1.5;
			ctx.strokeStyle = OUT$5;
			ctx.stroke();
			ctx.fillStyle = C.red;
			ctx.fillRect(x - s * .25, y - s * .5, s * .5, s * .25);
			ctx.strokeRect(x - s * .25, y - s * .5, s * .5, s * .25);
		},
		scroll(ctx, x, y, s) {
			box(ctx, x - s * .5, y - s * .4, s, s * .8, "#f2e6c8", OUT$5, 1.5, 1);
			ctx.fillStyle = C.redDark;
			ctx.fillRect(x - s * .6, y - s * .5, s * 1.2, s * .15);
			ctx.fillRect(x - s * .6, y + s * .35, s * 1.2, s * .15);
			ctx.strokeStyle = "#8a7a5a";
			ctx.lineWidth = 1;
			for (const k of [
				-.15,
				0,
				.15
			]) {
				ctx.beginPath();
				ctx.moveTo(x - s * .3, y + s * k);
				ctx.lineTo(x + s * .3, y + s * k);
				ctx.stroke();
			}
		},
		rest(ctx, x, y, s) {
			ctx.fillStyle = "#ff8a2a";
			ctx.beginPath();
			ctx.moveTo(x, y - s * .55);
			ctx.quadraticCurveTo(x + s * .45, y, x, y + s * .4);
			ctx.quadraticCurveTo(x - s * .45, y, x, y - s * .55);
			ctx.fill();
			ctx.fillStyle = "#ffd23a";
			ctx.beginPath();
			ctx.ellipse(x, y + s * .12, s * .15, s * .25, 0, 0, TAU$2);
			ctx.fill();
		}
	};
	/** 掛在門右邊的招牌（只畫圖示）。`dark` ＝ 廢鐵屋的深色框。 */
	function sign(ctx, x, y, icon, dark = false) {
		ctx.strokeStyle = OUT$5;
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		ctx.moveTo(x - 10, y);
		ctx.lineTo(x + 10, y);
		ctx.stroke();
		box(ctx, x - 12, y + 2, 24, 22, dark ? "#3a2a1e" : "#5a3a24", OUT$5, 2, 3);
		box(ctx, x - 9, y + 5, 18, 16, "#f2e6c8", null, 0, 2);
		ICON[icon](ctx, x, y + 13, 13);
	}
	/**
	* 酒館屋簷下燈籠的中心（6Q-1）：畫布 px，原點在建築畫布左上（屋頂那一列，`52` px 一格）。
	* 畫燈籠（`whiteHouse`）和畫光暈（`ambientLayer.drawLights`）共用這一個公式，立面高度改了也不會對不準。
	* 只有白牆屋舍的酒館有燈籠；其他種類回傳空陣列。
	*/
	function lanternCenters(s) {
		if (s.kind !== "tavern" || doorStyleOf(s.kind) === "rag") return [];
		const faceTop = (s.h + roofRows(s) - 1.3) * U$1;
		return windowCenters(s).map((wx) => ({
			x: wx * U$1,
			y: faceTop + 2 + 13 / 2
		}));
	}
	function lantern(ctx, x, y) {
		ctx.save();
		ctx.shadowColor = C.lamp;
		ctx.shadowBlur = 10;
		box(ctx, x - 5, y, 10, 13, C.red, OUT$5, 1.5, 4);
		ctx.restore();
		ctx.fillStyle = C.lamp;
		ctx.fillRect(x - 2, y + 3, 4, 7);
	}
	/** 煙囪冒的煙（靜態的三團灰煙）。 */
	function smoke(ctx, x, y) {
		for (const [dx, dy, r, a] of [
			[
				0,
				0,
				6,
				.55
			],
			[
				5,
				-9,
				7,
				.42
			],
			[
				12,
				-19,
				8,
				.3
			]
		]) {
			ctx.fillStyle = `rgba(200,200,196,${a})`;
			ctx.beginPath();
			ctx.arc(x + dx, y + dy, r, 0, TAU$2);
			ctx.fill();
		}
	}
	/** 白牆黛瓦的屋舍（explore.js 的 house；酒館、鐵匠鋪、導師堂、民宅）。畫布 w×(h+1) 格，原點在屋頂那一列的左上。 */
	function whiteHouse(ctx, s) {
		const H = s.h + roofRows(s);
		const W = s.w * U$1;
		const faceTop = (H - 1.3) * U$1;
		const faceH = 1.3 * U$1;
		shadow(ctx, W / 2 + 6, H * U$1 - 4, W / 2, 8, .35);
		box(ctx, 4, faceTop, W - 8, 63.60000000000001, C.mist, "#1f2a28", 2, 2);
		ctx.fillStyle = "rgba(0,0,0,0.08)";
		ctx.fillRect(6, faceTop + faceH - 18, W - 12, 12);
		box(ctx, 4, faceTop + faceH - 10, W - 8, 6, C.ink, "#1f2a28", 1.5, 1);
		ctx.beginPath();
		ctx.moveTo(2, faceTop + 6);
		ctx.lineTo(8, 4);
		ctx.lineTo(W - 8, 4);
		ctx.lineTo(W - 2, faceTop + 6);
		ctx.quadraticCurveTo(W / 2, faceTop - 2, 2, faceTop + 6);
		ctx.closePath();
		ctx.fillStyle = C.tile;
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = "#141c1a";
		ctx.stroke();
		ctx.strokeStyle = "rgba(255,255,255,0.12)";
		ctx.lineWidth = 1.2;
		for (let k = 12; k < W - 8; k += 7) {
			ctx.beginPath();
			ctx.moveTo(k, 6);
			ctx.lineTo(k + (k - W / 2) * .04, faceTop + 2);
			ctx.stroke();
		}
		box(ctx, 6, 2, W - 12, 5, "#2a3634", "#141c1a", 1.5, 2);
		if (s.kind === "tavern") {
			ctx.fillStyle = C.red;
			ctx.fillRect(6, faceTop + 4, W - 12, 3);
		}
		const lit = s.kind === "tavern";
		const windows = windowCenters(s);
		for (const wx of windows) {
			const x = wx * U$1;
			box(ctx, x - 9, faceTop + 18, 18, 14, "#3a2a1e", "#1f2a28", 1.5, 1);
			ctx.strokeStyle = "#8a6a44";
			ctx.lineWidth = 1;
			ctx.beginPath();
			ctx.moveTo(x, faceTop + 18);
			ctx.lineTo(x, faceTop + 32);
			ctx.stroke();
			if (lit) {
				ctx.fillStyle = rgba$1(C.lamp, .55);
				ctx.fillRect(x - 7, faceTop + 20, 14, 10);
			}
		}
		if (s.doors.length === 0) closedDoor(ctx, doorCenters(s)[0] * U$1, H * U$1, "wood");
		const icon = signOf(s);
		if (icon !== null) sign(ctx, doorCenters(s)[0] * U$1 + 20, faceTop + 6, icon);
		for (const l of lanternCenters(s)) lantern(ctx, l.x, l.y - 13 / 2);
		if (s.kind === "smithy") {
			const cx = W - 26;
			box(ctx, cx - 6, faceTop - 30, 12, 26, "#5a5450", OUT$5, 1.6, 1);
			smoke(ctx, cx, faceTop - 36);
		}
	}
	/** 廢鐵屋（ashenTiles.js 的 scrapHouse）：鏽鐵板拼的牆＋斜鐵皮屋頂；鍛爐屋多一根冒火光的煙囪。 */
	function scrapHouse(ctx, s) {
		const H = s.h + roofRows(s);
		const W = s.w * U$1;
		const faceTop = (H - 1.2) * U$1;
		shadow(ctx, W / 2 + 6, H * U$1 - 4, W / 2, 8, .4);
		const n = s.w * 3;
		for (let k = 0; k < n; k++) box(ctx, 4 + k * (W - 8) / n, faceTop, (W - 8) / n + 1, 1.2 * U$1 - 4, shade(k % 2 ? A$2.iron : A$2.rust, .85 + k % 3 * .08), OUT$5, 1.4, 1);
		for (let k = 0; k < s.w * 2; k++) dot$3(ctx, 10 + k * (W - 20) / (s.w * 2 - 1), faceTop + 6, 1.4, "#c8b8a0");
		ctx.beginPath();
		ctx.moveTo(0, faceTop + 4);
		ctx.lineTo(8, 6);
		ctx.lineTo(W - 2, 14);
		ctx.lineTo(W - 2, faceTop + 6);
		ctx.closePath();
		ctx.fillStyle = shade(A$2.iron, .8);
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$5;
		ctx.stroke();
		ctx.strokeStyle = "rgba(0,0,0,0.35)";
		ctx.lineWidth = 1.2;
		for (let k = 14; k < W - 4; k += 12) {
			ctx.beginPath();
			ctx.moveTo(k, 8 + k * .03);
			ctx.lineTo(k - 6, faceTop + 4);
			ctx.stroke();
		}
		if (s.doors.length === 0) closedDoor(ctx, doorCenters(s)[0] * U$1, H * U$1, "rag");
		if (s.kind === "forge_house") {
			box(ctx, W - 24, 2, 10, 26, A$2.iron, OUT$5, 1.6, 1);
			glow(ctx, W - 19, 6, 16, "rgba(255,140,60,0.9)", .6);
			dot$3(ctx, W - 19, 4, 2.5, A$2.hot);
		}
		const icon = signOf(s);
		if (icon !== null) sign(ctx, doorCenters(s)[0] * U$1 + 22, faceTop + 2, icon, true);
	}
	/** 一棟建築（不含門板；門是另外的節點）。 */
	function drawBuilding(ctx, s) {
		if (doorStyleOf(s.kind) === "rag") scrapHouse(ctx, s);
		else whiteHouse(ctx, s);
	}
	/** 沒有門格的建築正面畫一扇關著的門（純裝飾，沒有入口光圈）；`bottom` ＝ 建築底邊的 y。 */
	function closedDoor(ctx, cx, bottom, style) {
		doorFrame(ctx, cx, bottom, style);
		doorPanel(ctx, cx - 12, bottom, style);
	}
	/** 門框與門洞（暗）；`bottom` ＝ 格子底邊的 y。 */
	function doorFrame(ctx, cx, bottom, style) {
		const top = bottom - 6 - 30;
		box(ctx, cx - 12 - 3, top - 3, 30, 33, style === "rag" ? "#3a2e26" : "#5a3a24", OUT$5, 2, 2);
		ctx.fillStyle = "#14100c";
		ctx.fillRect(cx - 12, top, 24, 30);
		const g = ctx.createLinearGradient(0, top, 0, top + 30);
		g.addColorStop(0, "rgba(255,207,106,0.0)");
		g.addColorStop(1, "rgba(255,207,106,0.28)");
		ctx.fillStyle = g;
		ctx.fillRect(cx - 12, top, 24, 30);
		if (style === "wood") {
			ctx.fillStyle = C.red;
			ctx.fillRect(cx - 12 - 3, top - 3, 30, 4);
		}
	}
	/** 門板（關著的樣子）：左緣是門軸，`x0` ＝ 門軸的 x。 */
	function doorPanel(ctx, x0, bottom, style) {
		const top = bottom - 6 - 30;
		if (style === "rag") {
			box(ctx, x0, top, 24, 30, A$2.rag, OUT$5, 1.6, 2);
			ctx.fillStyle = "rgba(0,0,0,0.25)";
			for (const k of [
				6,
				12,
				18
			]) ctx.fillRect(x0 + k, top + 2, 1.5, 26);
			return;
		}
		box(ctx, x0, top, 24, 30, "#4a3020", "#1f2a28", 2, 2);
		ctx.strokeStyle = "rgba(0,0,0,0.35)";
		ctx.lineWidth = 1;
		for (const k of [8, 16]) {
			ctx.beginPath();
			ctx.moveTo(x0 + k, top + 3);
			ctx.lineTo(x0 + k, top + 30 - 3);
			ctx.stroke();
		}
		dot$3(ctx, x0 + 24 - 5, top + 16.5, 1.8, "#e8bb48");
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/capitalArt.ts
	var U = 52;
	var OUT$4 = "#1c1712";
	/** 晶冠的基準風格（townTiles.js 的 K）。 */
	var K = {
		stone: "#e8dcc0",
		stoneD: "#b8aa8a",
		roof: "#3a5ad0",
		roofD: "#2a4098",
		gold: "#e8bb48",
		crystal: "#c8bcff",
		canvas: "#e0d0a8",
		canvasD: "#b8a47a",
		water: "#3f8ac8"
	};
	/** 任何一種建築的畫法（主城的種類在這裡，其他交給 townArt.ts）。 */
	function paintBuilding(ctx, s) {
		if (s.kind === "stone_hall" || s.kind === "mentor_hall") stoneHall(ctx, s);
		else if (s.kind === "tent") tent(ctx, s);
		else if (s.kind === "fountain") fountain(ctx, s);
		else drawBuilding(ctx, s);
	}
	/** 藍框招牌（townTiles.js 的 stoneHall 招牌）：只畫圖示。 */
	function blueSign(ctx, x, y, icon) {
		box(ctx, x - 12, y, 24, 22, "#2a3a6a", OUT$4, 2, 3);
		box(ctx, x - 9, y + 3, 18, 16, "#f2e6c8", null, 0, 2);
		ICON[icon](ctx, x, y + 11, 12);
	}
	/** 白石藍頂的建築（townTiles.js 的 stoneHall）：立面白石＋金邊、藍色瓦頂、金色屋脊；導師殿多一座發光晶尖塔。 */
	function stoneHall(ctx, s) {
		const H = s.h + roofRows(s);
		const W = s.w * U;
		const faceH = 1.4 * U;
		const faceTop = H * U - faceH;
		const spire = s.kind === "mentor_hall";
		const roofTop = spire && H >= 3 ? .8 * U : 6;
		shadow(ctx, W / 2 + 8, H * U - 2, W / 2, 9, .35);
		box(ctx, 4, faceTop, W - 8, 68.8, K.stone, OUT$4, 2, 2);
		ctx.strokeStyle = "rgba(120,100,70,0.45)";
		ctx.lineWidth = 1;
		for (let k = 1; k < 4; k++) {
			ctx.beginPath();
			ctx.moveTo(6, faceTop + k * 17);
			ctx.lineTo(W - 6, faceTop + k * 17);
			ctx.stroke();
		}
		ctx.fillStyle = K.gold;
		ctx.fillRect(4, faceTop, W - 8, 3);
		ctx.beginPath();
		ctx.moveTo(2, faceTop + 6);
		ctx.lineTo(10, roofTop);
		ctx.lineTo(W - 10, roofTop);
		ctx.lineTo(W - 2, faceTop + 6);
		ctx.closePath();
		ctx.fillStyle = K.roof;
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$4;
		ctx.stroke();
		ctx.strokeStyle = rgba$1(K.roofD, .8);
		ctx.lineWidth = 1.2;
		for (let k = 12; k < W - 8; k += 8) {
			ctx.beginPath();
			ctx.moveTo(k, roofTop + 2);
			ctx.lineTo(k + (k - W / 2) * .08, faceTop + 4);
			ctx.stroke();
		}
		box(ctx, 8, roofTop - 4, W - 16, 6, K.gold, OUT$4, 1.5, 2);
		for (const wx of windowCenters(s)) {
			const x = wx * U;
			box(ctx, x - 7, faceTop + 14, 14, 18, "#3a4a6a", OUT$4, 1.5, 6);
			ctx.fillStyle = "rgba(255,230,160,0.5)";
			ctx.fillRect(x - 5, faceTop + 18, 10, 12);
		}
		if (s.doors.length === 0) closedDoor(ctx, doorCenters(s)[0] * U, H * U, "wood");
		const icon = signOf(s);
		if (icon !== null) {
			const dc = doorCenters(s)[0] * U;
			blueSign(ctx, dc + 20 + 14 <= W ? dc + 20 : dc - 20, faceTop + 6, icon);
		}
		if (spire) crystalSpire(ctx, W / 2, roofTop);
	}
	/** 導師殿屋頂的晶尖塔（發光）：底在 `base`，往上最多到畫布頂。 */
	function crystalSpire(ctx, cx, base) {
		const top = Math.max(2, base - .75 * U);
		glow(ctx, cx, (top + base) / 2, 30, "rgba(143,123,255,0.9)", .55);
		ctx.beginPath();
		ctx.moveTo(cx - 12, base + 4);
		ctx.lineTo(cx, top);
		ctx.lineTo(cx + 12, base + 4);
		ctx.closePath();
		ctx.fillStyle = K.crystal;
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$4;
		ctx.stroke();
		ctx.strokeStyle = "rgba(255,255,255,0.6)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		ctx.moveTo(cx - 3, base);
		ctx.lineTo(cx, top + 8);
		ctx.stroke();
	}
	/** 傭兵營的帆布帳篷：條紋帆布、中間的門簾、兩側的繩與木樁、頂上的小旗。 */
	function tent(ctx, s) {
		const H = s.h + roofRows(s);
		const W = s.w * U;
		const foot = H * U - 6;
		const peak = Math.max(10, H * U - (s.h + .6) * U);
		const cx = W / 2;
		const ground = roofRows(s) * U;
		box(ctx, 0, ground, W, H * U - ground, "#a88a5e", "rgba(60,40,20,0.6)", 1.2, 4);
		ctx.fillStyle = "rgba(255,240,200,0.12)";
		for (let x = 10; x < W - 6; x += 16) ctx.fillRect(x, ground + 4, 6, H * U - ground - 8);
		shadow(ctx, cx + 6, foot, W / 2 - 2, 8, .35);
		ctx.beginPath();
		ctx.moveTo(6, foot);
		ctx.quadraticCurveTo(cx * .55, peak + (foot - peak) * .35, cx, peak);
		ctx.quadraticCurveTo(W - cx * .55, peak + (foot - peak) * .35, W - 6, foot);
		ctx.closePath();
		ctx.fillStyle = K.canvas;
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$4;
		ctx.stroke();
		ctx.save();
		ctx.clip();
		ctx.fillStyle = "rgba(160,60,40,0.35)";
		for (let x = 14; x < W; x += 22) ctx.fillRect(x, peak, 9, foot - peak);
		ctx.restore();
		ctx.beginPath();
		ctx.moveTo(cx - 14, foot);
		ctx.lineTo(cx, foot - 40);
		ctx.lineTo(cx + 14, foot);
		ctx.closePath();
		ctx.fillStyle = "#3a2a1e";
		ctx.fill();
		ctx.lineWidth = 1.5;
		ctx.strokeStyle = OUT$4;
		ctx.stroke();
		ctx.strokeStyle = K.canvasD;
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.moveTo(cx, foot - 40);
		ctx.lineTo(cx - 9, foot);
		ctx.stroke();
		ctx.strokeStyle = "rgba(60,40,20,0.7)";
		ctx.lineWidth = 1;
		for (const [x0, x1] of [[cx * .6, 2], [W - cx * .6, W - 2]]) {
			ctx.beginPath();
			ctx.moveTo(x0, peak + (foot - peak) * .45);
			ctx.lineTo(x1, foot + 2);
			ctx.stroke();
			dot$3(ctx, x1, foot + 2, 2, "#6a4a2a");
		}
		box(ctx, cx - 1.5, peak - 14, 3, 16, "#6a5a4a", OUT$4, 1, 1);
		ctx.beginPath();
		ctx.moveTo(cx + 1.5, peak - 14);
		ctx.lineTo(cx + 14, peak - 10);
		ctx.lineTo(cx + 1.5, peak - 6);
		ctx.closePath();
		ctx.fillStyle = "#c83a2a";
		ctx.fill();
		ctx.lineWidth = 1.2;
		ctx.strokeStyle = OUT$4;
		ctx.stroke();
	}
	function fountainGeom(s) {
		const H = s.h + roofRows(s);
		const W = s.w * U;
		const cx = W / 2;
		const rx = Math.min(W, s.h * U) / 2 - 6;
		const ry = rx * .62;
		const cy = H * U - ry - 12;
		return {
			cx,
			cy,
			rx,
			ry,
			rim: 8,
			lip: 8,
			spoutX: cx,
			spoutY: cy - 30
		};
	}
	/**
	* 許願池（6V-4，Fable 審查第 2 節 C）：圓形石緣水池（透視成橢圓）＋前緣立面、石塊接縫、池水、
	* 中央兩層石座與金色噴口。噴水由環境動態層畫（`ambientAnim.fountainSpray`；減少動態時停在第 0 毫秒），
	* 這裡只畫一圈落水的漣漪。蓋在水表面上（只畫）。
	*/
	function fountain(ctx, s) {
		const g = fountainGeom(s);
		const { cx, cy, rx, ry, rim, lip } = g;
		const top = (s.h + roofRows(s) - s.h) * U;
		ctx.beginPath();
		ctx.roundRect(1, top + 1, s.w * U - 2, s.h * U - 2, 10);
		ctx.fillStyle = "#d8ccb0";
		ctx.fill();
		ctx.lineWidth = 1.6;
		ctx.strokeStyle = "rgba(28,23,18,0.55)";
		ctx.stroke();
		ctx.strokeStyle = "rgba(110,95,70,0.35)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		for (let k = 1; k < s.w * 2; k++) {
			ctx.moveTo(k * U / 2, top + 2);
			ctx.lineTo(k * U / 2, top + s.h * U - 2);
		}
		for (let k = 1; k < s.h * 2; k++) {
			ctx.moveTo(2, top + k * U / 2);
			ctx.lineTo(s.w * U - 2, top + k * U / 2);
		}
		ctx.stroke();
		shadow(ctx, cx + 4, cy + ry + lip - 2, rx, ry * .35, .3);
		ctx.beginPath();
		ctx.ellipse(cx, cy + lip, rx, ry, 0, 0, Math.PI);
		ctx.lineTo(cx - rx, cy);
		ctx.ellipse(cx, cy, rx, ry, 0, Math.PI, 0, true);
		ctx.closePath();
		ctx.fillStyle = "#a89a7c";
		ctx.fill();
		ctx.lineWidth = 2;
		ctx.strokeStyle = OUT$4;
		ctx.stroke();
		ctx.beginPath();
		ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU$2);
		ctx.fillStyle = K.stone;
		ctx.fill();
		ctx.stroke();
		const irx = rx - rim;
		const iry = ry - rim * .62;
		const water = ctx.createLinearGradient(0, cy - iry, 0, cy + iry);
		water.addColorStop(0, "#2f74b8");
		water.addColorStop(1, "#5ab0e8");
		ctx.beginPath();
		ctx.ellipse(cx, cy, irx, iry, 0, 0, TAU$2);
		ctx.fillStyle = water;
		ctx.fill();
		ctx.lineWidth = 1.6;
		ctx.strokeStyle = OUT$4;
		ctx.stroke();
		ctx.strokeStyle = "rgba(90,78,56,0.7)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		for (let k = 0; k < 14; k++) {
			const a = (k + .5) * (TAU$2 / 14);
			const ox = Math.cos(a);
			const oy = Math.sin(a);
			ctx.moveTo(cx + ox * irx, cy + oy * iry);
			ctx.lineTo(cx + ox * rx, cy + oy * ry);
			if (oy > .05) {
				ctx.moveTo(cx + ox * rx, cy + oy * ry);
				ctx.lineTo(cx + ox * rx, cy + oy * ry + lip);
			}
		}
		ctx.stroke();
		ctx.fillStyle = "rgba(255,255,255,0.3)";
		ctx.beginPath();
		ctx.ellipse(cx - rx * .35, cy - ry * .78, rx * .3, 1.6, -.15, 0, TAU$2);
		ctx.fill();
		ctx.strokeStyle = "rgba(220,240,255,0.55)";
		ctx.lineWidth = 1.1;
		for (const k of [.42, .7]) {
			ctx.beginPath();
			ctx.ellipse(cx, cy + 2, irx * k, iry * k, 0, 0, TAU$2);
			ctx.stroke();
		}
		box(ctx, cx - 6, cy - 22, 12, 24, K.stone, OUT$4, 1.6, 2);
		ctx.beginPath();
		ctx.ellipse(cx, cy - 22, 13, 4.5, 0, 0, TAU$2);
		ctx.fillStyle = K.stoneD;
		ctx.fill();
		ctx.lineWidth = 1.6;
		ctx.strokeStyle = OUT$4;
		ctx.stroke();
		ctx.beginPath();
		ctx.ellipse(cx, cy - 23, 9.5, 3, 0, 0, TAU$2);
		ctx.fillStyle = "#5ab0e8";
		ctx.fill();
		box(ctx, cx - 2.5, g.spoutY + 2, 5, cy - 24 - g.spoutY, K.stone, OUT$4, 1.2, 1);
		dot$3(ctx, g.spoutX, g.spoutY + 1, 3.4, K.gold);
	}
	/** 源晶燈：石座加發光晶石。 */
	function drawCrystalLamp(ctx) {
		const cx = U / 2;
		shadow(ctx, 29, 95.68, 13, 4);
		box(ctx, 15, 84, 22, 12, K.stoneD, OUT$4, 1.6, 2);
		box(ctx, 21, 60, 10, 26, K.stone, OUT$4, 1.5, 2);
		ctx.fillStyle = K.gold;
		ctx.fillRect(21, 60, 10, 3);
		glow(ctx, cx, 48, 22, "rgba(143,123,255,0.9)", .7);
		ctx.beginPath();
		ctx.moveTo(cx, 32);
		ctx.lineTo(34, 48);
		ctx.lineTo(cx, 60);
		ctx.lineTo(18, 48);
		ctx.closePath();
		ctx.fillStyle = K.crystal;
		ctx.fill();
		ctx.lineWidth = 1.6;
		ctx.strokeStyle = OUT$4;
		ctx.stroke();
		dot$3(ctx, 24, 45, 2, "#ffffff");
	}
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/arcaneTerrain.ts
	var T$4 = 52;
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
		ctx.fillRect(0, 0, T$4, T$4);
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
			dot$3(ctx, dx, dy, 2, ARCANE.brass);
			dot$3(ctx, dx - .6, dy - .6, .8, "rgba(255,255,255,0.5)");
		}
		if (arcaneLineAt(s.x, s.y)) {
			const horiz = r() < .5;
			glowLine(ctx, rgba$1(ARCANE.energy, ARCANE_LINE.alpha), ARCANE_LINE.width, ARCANE_LINE.blur, () => {
				if (horiz) {
					ctx.moveTo(0, T$4 / 2);
					ctx.lineTo(T$4 * .4, T$4 / 2);
					ctx.lineTo(T$4 * .5, T$4 * .38);
					ctx.lineTo(T$4, T$4 * .38);
				} else {
					ctx.moveTo(T$4 / 2, 0);
					ctx.lineTo(T$4 / 2, T$4 * .6);
					ctx.lineTo(T$4 * .62, T$4 * .7);
					ctx.lineTo(T$4 * .62, T$4);
				}
			});
		}
	}
	/** 鐵格柵下的苔草。 */
	function arcaneGrass(ctx, s) {
		const r = rng(s.x, s.y, 403);
		ctx.fillStyle = shade("#3e4a34", .95 + r() * .1);
		ctx.fillRect(0, 0, T$4, T$4);
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
		for (let k = 6; k < T$4; k += 10) {
			ctx.moveTo(k, 0);
			ctx.lineTo(k, T$4);
		}
		ctx.stroke();
		ctx.strokeRect(1, 1, 50, 50);
	}
	/** 煤渣地：黑點加少量黃銅屑。 */
	function arcaneDirt(ctx, s) {
		const r = rng(s.x, s.y, 404);
		ctx.fillStyle = shade("#3a3430", .94 + r() * .12);
		ctx.fillRect(0, 0, T$4, T$4);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.07)";
			ctx.beginPath();
			ctx.ellipse(r() * T$4, r() * T$4, 8 + r() * 10, 5 + r() * 7, r() * Math.PI * 2, 0, Math.PI * 2);
			ctx.fill();
		}
		for (let i = 0; i < 16; i++) {
			ctx.fillStyle = r() < .4 ? "rgba(176,138,74,0.4)" : "rgba(10,8,6,0.6)";
			ctx.fillRect(r() * T$4, r() * T$4, 1.8, 1.8);
		}
	}
	/** 鐵壁：分板、鉚釘；南鄰不是牆時畫深色立面，下段一條黃銅管線（比單位高）。 */
	function arcaneWall(ctx, s) {
		ctx.fillStyle = ARCANE.iron;
		ctx.fillRect(0, 0, T$4, T$4);
		ctx.fillStyle = "rgba(255,255,255,0.14)";
		ctx.fillRect(0, 0, T$4, 3);
		ctx.strokeStyle = "rgba(0,0,0,0.55)";
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		for (const k of [T$4 * .33, T$4 * .66]) {
			ctx.moveTo(k, 0);
			ctx.lineTo(k, T$4);
		}
		ctx.moveTo(0, T$4 / 2);
		ctx.lineTo(T$4, T$4 / 2);
		ctx.stroke();
		for (const y of [6, 32]) for (const k of [
			8,
			T$4 / 2,
			44
		]) dot$3(ctx, k, y, 1.8, ARCANE.brass);
		if (s.wallFace) {
			ctx.fillStyle = "#3a342c";
			ctx.fillRect(0, 40, T$4, 12);
			ctx.fillStyle = "rgba(0,0,0,0.3)";
			ctx.fillRect(0, 40, T$4, 2);
			ctx.fillStyle = ARCANE.brass;
			ctx.fillRect(0, 44, T$4, 5);
			ctx.fillStyle = "rgba(255,255,255,0.3)";
			ctx.fillRect(0, 44, T$4, 1.5);
		}
	}
	/** 崖緣：和其他地形相接的那一邊是鐵框，邊緣一條煤黑的崖線。 */
	function shaftLip(ctx, s) {
		ctx.fillStyle = ARCANE.iron;
		if (s.lip.n) ctx.fillRect(0, 0, T$4, 9);
		if (s.lip.s) ctx.fillRect(0, 47, T$4, 5);
		if (s.lip.w) ctx.fillRect(0, 0, 5, T$4);
		if (s.lip.e) ctx.fillRect(47, 0, 5, T$4);
		ctx.fillStyle = "rgba(0,0,0,0.5)";
		if (s.lip.n) ctx.fillRect(0, 9, T$4, 2);
		if (s.lip.n) for (const k of [
			6,
			T$4 / 2,
			46
		]) dot$3(ctx, k, 4.5, 1.5, ARCANE.brass);
	}
	/** 機械豎井：深色井底，兩條黃銅管線，幾個晶能光點；邊緣有崖線。 */
	function arcaneChasm(ctx, s) {
		const r = rng(s.x, s.y, 405);
		const g = ctx.createLinearGradient(0, 0, 0, T$4);
		g.addColorStop(0, "#14181a");
		g.addColorStop(1, "#06080a");
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$4, T$4);
		ctx.strokeStyle = rgba$1(ARCANE.brass, .55);
		ctx.lineWidth = 3;
		ctx.beginPath();
		for (const k of [12, 40]) {
			ctx.moveTo(k, 0);
			ctx.lineTo(k, T$4);
		}
		ctx.stroke();
		for (let i = 0; i < 3; i++) dot$3(ctx, 8 + r() * 36, 20 + r() * 28, 1.6, rgba$1(ARCANE.energy, .7));
		shaftLip(ctx, s);
	}
	/** 熔爐槽：岩漿（紅橘）外圍是鐵框，四角鉚釘。 */
	function arcaneLava(ctx, s) {
		const r = rng(s.x, s.y, 406);
		ctx.fillStyle = "#e0400a";
		ctx.fillRect(0, 0, T$4, T$4);
		for (let i = 0; i < 4; i++) {
			const cx = r() * T$4;
			const cy = r() * T$4;
			const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 18);
			gg.addColorStop(0, "#ffb030");
			gg.addColorStop(1, rgba$1("#ffb030", 0));
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$4, T$4);
		}
		ctx.strokeStyle = ARCANE.iron;
		ctx.lineWidth = 4;
		ctx.strokeRect(2, 2, 48, 48);
		for (const [dx, dy] of [
			[5, 5],
			[47, 5],
			[5, 47],
			[47, 47]
		]) dot$3(ctx, dx, dy, 1.6, "#d8b070");
	}
	/** 冷卻槽：冰藍液體 #2a7a9a，外圍黃銅邊（每格一個槽，靠黃銅邊和格子區分；致命）。 */
	function arcaneIceHole(ctx, s) {
		const r = rng(s.x, s.y, 407);
		ctx.fillStyle = ARCANE.plate;
		ctx.fillRect(0, 0, T$4, T$4);
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/cloudRidgeTerrain.ts
	var T$3 = 52;
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
		ctx.fillRect(0, 0, T$3, T$3);
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
			roundRect(ctx, bx * T$3 + 1.5, by * T$3 + 1.5, bw * T$3 - 3, bh * T$3 - 3, 3);
			ctx.fill();
			ctx.fillStyle = "rgba(255,255,255,0.12)";
			ctx.fillRect(bx * T$3 + 2, by * T$3 + 2, bw * T$3 - 4, 2);
		}
		if (r() < .45) {
			ctx.fillStyle = rgba$1(CLOUD.moss, .75);
			for (let i = 0; i < 4; i++) {
				ctx.beginPath();
				ctx.arc(r() * T$3, r() * T$3, 2 + r() * 3, 0, TAU$2);
				ctx.fill();
			}
		}
	}
	/** 偏青的草地：竹葉般細長的草葉。 */
	function cloudGrass(ctx, s) {
		const r = rng(s.x, s.y, 102);
		ctx.fillStyle = shade("#689a70", .96 + r() * .08);
		ctx.fillRect(0, 0, T$3, T$3);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(232,232,224,0.07)" : "rgba(0,0,0,0.05)";
			ctx.beginPath();
			ctx.ellipse(r() * T$3, r() * T$3, 8 + r() * 10, 6 + r() * 8, r() * TAU$2, 0, TAU$2);
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
		ctx.fillRect(0, 0, T$3, T$3);
		const n = 5 + Math.floor(r() * 5);
		for (let i = 0; i < n; i++) {
			ctx.fillStyle = r() < .5 ? "#8a7748" : "#c4b27c";
			ctx.beginPath();
			ctx.ellipse(4 + r() * 44, 4 + r() * 44, 1.5 + r() * 2.5, 1.2 + r() * 1.8, r() * TAU$2, 0, TAU$2);
			ctx.fill();
		}
		ctx.strokeStyle = "rgba(110,90,50,0.35)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		const yy = T$3 * (.3 + r() * .4);
		ctx.moveTo(0, yy);
		ctx.bezierCurveTo(T$3 * .3, yy - 6, T$3 * .6, yy + 6, T$3, yy - 2);
		ctx.stroke();
	}
	/** 白牆黛瓦：頂上一排深色瓦，立面是白牆；比單位高（立面與瓦頂對比強）。 */
	function cloudWall(ctx, s) {
		const r = rng(s.x, s.y, 104);
		ctx.fillStyle = CLOUD.mist;
		ctx.fillRect(0, 0, T$3, T$3);
		ctx.strokeStyle = "rgba(86,100,92,0.28)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		for (let x = 13; x < T$3; x += 13) {
			ctx.moveTo(x + (r() - .5) * 2, 18);
			ctx.lineTo(x + (r() - .5) * 2, T$3);
		}
		ctx.stroke();
		ctx.fillStyle = "rgba(86,100,92,0.12)";
		ctx.fillRect(Math.floor(r() * 3) * 16 + 3, 24 + r() * 8, 12, 10);
		ctx.fillStyle = CLOUD.tile;
		ctx.fillRect(0, 0, T$3, 18);
		ctx.strokeStyle = "rgba(232,232,224,0.22)";
		ctx.lineWidth = 1.2;
		for (let row = 0; row < 2; row++) for (let x = row ? 4 : 0; x < 60; x += 8) {
			ctx.beginPath();
			ctx.arc(x, 4 + row * 7, 4, 0, Math.PI);
			ctx.stroke();
		}
		ctx.fillStyle = "rgba(0,0,0,0.35)";
		ctx.fillRect(0, 18, T$3, 3);
		ctx.fillStyle = "#2a3534";
		ctx.fillRect(0, 16, T$3, 2);
		if (s.wallFace) {
			ctx.fillStyle = "#b9bab0";
			ctx.fillRect(0, 43, T$3, 9);
			ctx.fillStyle = "rgba(0,0,0,0.12)";
			ctx.fillRect(0, 43, T$3, 1.5);
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
			T$3,
			0
		], [0, 1]);
		if (s.lip.s) cliffLip(ctx, r, [
			0,
			T$3,
			T$3,
			T$3
		], [0, -1]);
		if (s.lip.w) cliffLip(ctx, r, [
			0,
			0,
			0,
			T$3
		], [1, 0]);
		if (s.lip.e) cliffLip(ctx, r, [
			T$3,
			0,
			T$3,
			T$3
		], [-1, 0]);
		if (s.lip.n) {
			const gg = ctx.createLinearGradient(0, 0, 0, 14);
			gg.addColorStop(0, "rgba(60,72,66,0.8)");
			gg.addColorStop(1, "rgba(60,72,66,0)");
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$3, 14);
		}
	}
	/** 地熱泉：橘紅的泉水，冒白煙（保留紅色，致命）。 */
	function cloudLava(ctx, s) {
		const r = rng(s.x, s.y, 106);
		ctx.fillStyle = "#d9532a";
		ctx.fillRect(0, 0, T$3, T$3);
		const glow = ctx.createRadialGradient(T$3 / 2, T$3 / 2, 2, T$3 / 2, T$3 / 2, T$3 * .7);
		glow.addColorStop(0, "rgba(255,200,90,0.6)");
		glow.addColorStop(1, "rgba(255,200,90,0)");
		ctx.fillStyle = glow;
		ctx.fillRect(0, 0, T$3, T$3);
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
			ctx.arc(px, py, rad, 0, TAU$2);
			ctx.fill();
		}
	}
	/** 寒潭：深青黑的水，邊緣一圈霜（致命）。 */
	function cloudIceHole(ctx, s) {
		const r = rng(s.x, s.y, 107);
		ctx.fillStyle = "#0e2a2e";
		ctx.fillRect(0, 0, T$3, T$3);
		ctx.strokeStyle = rgba$1("#4f8f8a", .6);
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
		if (s.lip.n) ctx.fillRect(0, 0, T$3, 4);
		if (s.lip.w) ctx.fillRect(0, 0, 4, T$3);
		if (s.lip.e) ctx.fillRect(48, 0, 4, T$3);
		if (s.lip.s) ctx.fillRect(0, 48, T$3, 4);
	}
	/** `floor: plank_walk`：木棧道——橫向的木板，釘孔與木紋。 */
	function plankWalk(ctx, s) {
		const r = rng(s.x, s.y, 108);
		ctx.fillStyle = "#3e2e1c";
		ctx.fillRect(0, 0, T$3, T$3);
		const rows = 4;
		const h = T$3 / rows;
		for (let i = 0; i < rows; i++) {
			ctx.fillStyle = shade("#9a7848", .88 + r() * .2);
			ctx.fillRect(0, i * h + 1, T$3, 11);
			ctx.fillStyle = "rgba(255,240,200,0.14)";
			ctx.fillRect(0, i * h + 1, T$3, 1.5);
			ctx.strokeStyle = "rgba(70,48,24,0.4)";
			ctx.lineWidth = 1;
			ctx.beginPath();
			const gy = i * h + 3 + r() * 7;
			ctx.moveTo(0, gy);
			ctx.lineTo(T$3, gy + (r() - .5) * 2);
			ctx.stroke();
			ctx.fillStyle = "#3e2e1c";
			ctx.beginPath();
			ctx.arc(3.5, i * h + h / 2, 1.1, 0, TAU$2);
			ctx.arc(48.5, i * h + h / 2, 1.1, 0, TAU$2);
			ctx.fill();
		}
	}
	/** `floor: paddy`：泥田＋田埂（四周一圈較高的土埂，裡面是泥水與秧苗）。 */
	function paddy(ctx, s) {
		const r = rng(s.x, s.y, 109);
		ctx.fillStyle = "#a08a58";
		ctx.fillRect(0, 0, T$3, T$3);
		ctx.fillStyle = "rgba(255,255,255,0.12)";
		ctx.fillRect(0, 0, T$3, 2);
		ctx.fillRect(0, 0, 2, T$3);
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
		ctx.fillRect(0, 0, T$3, T$3);
		const cols = [
			"#8a7e6e",
			"#7a6f60",
			"#9a8e7c",
			"#665c4f"
		];
		for (let i = 0; i < 5; i++) {
			const cx = r() * T$3;
			const cy = r() * T$3;
			const n = 5;
			ctx.beginPath();
			for (let k = 0; k < n; k++) {
				const a = k / n * TAU$2 + r() * .6;
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
		let px = T$3 * (.2 + r() * .6);
		let py = 0;
		ctx.moveTo(px, py);
		for (let i = 0; i < 4; i++) {
			px += (r() - .5) * 12;
			py += T$3 / 4;
			ctx.lineTo(px, py);
		}
		ctx.stroke();
		ctx.fillStyle = "rgba(255,255,255,0.08)";
		ctx.fillRect(0, 0, T$3, 3);
		if (s.wallFace) {
			ctx.fillStyle = "#3f372d";
			ctx.fillRect(0, 43, T$3, 9);
			ctx.fillStyle = "rgba(255,255,255,0.08)";
			ctx.fillRect(0, 43, T$3, 1.5);
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
	var T$2 = 52;
	/** 晶冠色票（需求第 3 節）。 */
	var CRYSTAL$1 = {
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
		stroke: CRYSTAL$1.gold,
		glint: CRYSTAL$1.glint
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
		ctx.moveTo(T$2 / 2, 6);
		ctx.lineTo(46, T$2 / 2);
		ctx.lineTo(T$2 / 2, 46);
		ctx.lineTo(6, T$2 / 2);
		ctx.closePath();
		ctx.stroke();
		dot$3(ctx, T$2 / 2, T$2 / 2, 2.5, style.glint);
	}
	/** 深淵上的 4 個晶光碎點（避開北緣崖線）。 */
	function voidGlints(ctx, s) {
		const r = rng(s.x, s.y, 302);
		for (let i = 0; i < 4; i++) dot$3(ctx, 4 + r() * 44, 14 + r() * 34, 1.2, CRYSTAL$1.glint);
	}
	/** 白石城牆：頂面米白錯縫磚；南鄰不是牆時畫正面，頂面和正面之間一條金邊（比單位高）。 */
	function crystalWall(ctx, s) {
		ctx.fillStyle = "#e8dcc0";
		ctx.fillRect(0, 0, T$2, T$2);
		ctx.fillStyle = "rgba(255,255,255,0.2)";
		ctx.fillRect(0, 0, T$2, 3);
		ctx.strokeStyle = "rgba(90,74,50,0.5)";
		ctx.lineWidth = 1.5;
		const rows = 4;
		const rh = T$2 / rows;
		ctx.beginPath();
		for (let i = 1; i < rows; i++) {
			ctx.moveTo(0, i * rh);
			ctx.lineTo(T$2, i * rh);
		}
		for (let i = 0; i < rows; i++) for (let bx = i % 2 === 0 ? T$2 / 4 : T$2 / 2; bx < T$2; bx += T$2 / 2) {
			ctx.moveTo(bx, i * rh);
			ctx.lineTo(bx, (i + 1) * rh);
		}
		ctx.stroke();
		if (s.wallFace) {
			ctx.fillStyle = "#b8aa8a";
			ctx.fillRect(0, 42, T$2, 10);
			ctx.strokeStyle = "rgba(90,74,50,0.6)";
			ctx.lineWidth = 1.2;
			ctx.beginPath();
			for (let bx = 9; bx < T$2; bx += 13) {
				ctx.moveTo(bx, 42);
				ctx.lineTo(bx, T$2);
			}
			ctx.stroke();
			ctx.fillStyle = CRYSTAL$1.gold;
			ctx.fillRect(0, 40, T$2, 2);
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
	var T$1 = 52;
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
		ctx.fillRect(0, 0, T$1, T$1);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.07)";
			ctx.beginPath();
			ctx.ellipse(r() * T$1, r() * T$1, 8 + r() * 10, 5 + r() * 7, r() * TAU$2, 0, TAU$2);
			ctx.fill();
		}
		for (let i = 0; i < n; i++) {
			ctx.fillStyle = fleck2 !== null && r() < .4 ? fleck2 : fleck;
			ctx.fillRect(r() * T$1, r() * T$1, 1.8, 1.8);
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
		ctx.fillRect(0, 0, T$1, T$1);
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
			ctx.quadraticCurveTo(T$1 / 2, y - 4, 46, y);
			ctx.stroke();
		}
	}
	/** 冰崖：頂面冰白、裂紋；南鄰不是牆時畫冰藍立面，頂緣垂著冰柱（比單位高）。和其他地形相接的邊畫 2px 深色外框。 */
	function frostWall(ctx, s) {
		const r = rng(s.x, s.y, 504);
		ctx.fillStyle = "#e8f6ff";
		ctx.fillRect(0, 0, T$1, T$1);
		ctx.fillStyle = "rgba(138,184,216,0.35)";
		for (let i = 0; i < 3; i++) {
			ctx.beginPath();
			ctx.ellipse(r() * T$1, r() * T$1, 6 + r() * 8, 3 + r() * 4, r() * TAU$2, 0, TAU$2);
			ctx.fill();
		}
		ctx.strokeStyle = "rgba(40,80,110,0.4)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		for (let i = 0; i < 2; i++) {
			const x = 6 + r() * 40;
			ctx.moveTo(x, 4 + r() * 10);
			ctx.lineTo(x + (r() - .5) * 12, T$1 * .6);
		}
		ctx.stroke();
		if (s.wallFace) {
			const faceY = 38;
			ctx.fillStyle = "#8ab8d8";
			ctx.fillRect(0, faceY, T$1, 14);
			ctx.strokeStyle = "rgba(255,255,255,0.55)";
			ctx.lineWidth = 1.2;
			ctx.beginPath();
			for (let i = 0; i < 3; i++) {
				const x = 6 + r() * 40;
				ctx.moveTo(x, 40);
				ctx.lineTo(x - 3, T$1);
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
			ctx.fillRect(0, 37, T$1, 1.5);
		}
		ctx.strokeStyle = FROST.outline;
		ctx.lineWidth = 2;
		ctx.beginPath();
		if (s.lip.n) {
			ctx.moveTo(0, 1);
			ctx.lineTo(T$1, 1);
		}
		if (s.lip.s || s.wallFace) {
			ctx.moveTo(0, 51);
			ctx.lineTo(T$1, 51);
		}
		if (s.lip.w) {
			ctx.moveTo(1, 0);
			ctx.lineTo(1, T$1);
		}
		if (s.lip.e) {
			ctx.moveTo(51, 0);
			ctx.lineTo(51, T$1);
		}
		ctx.stroke();
	}
	/** 深海溝：深藍漸層、兩道淡波紋；和其他地形相接的邊是沙色崖線（北緣加深的崖影）。 */
	function frostChasm(ctx, s) {
		const r = rng(s.x, s.y, 505);
		const g = ctx.createLinearGradient(0, 0, 0, T$1);
		g.addColorStop(0, "#123a6a");
		g.addColorStop(1, "#061a34");
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T$1, T$1);
		ctx.strokeStyle = "rgba(160,210,255,0.18)";
		ctx.lineWidth = 1.2;
		for (let i = 0; i < 2; i++) {
			const y = 22 + i * 16 + r() * 4;
			ctx.beginPath();
			ctx.moveTo(8, y);
			ctx.quadraticCurveTo(T$1 / 2, y - 4, 44, y);
			ctx.stroke();
		}
		ctx.fillStyle = "#c8b88a";
		if (s.lip.n) ctx.fillRect(0, 0, T$1, 9);
		if (s.lip.s) ctx.fillRect(0, 48, T$1, 4);
		if (s.lip.w) ctx.fillRect(0, 0, 4, T$1);
		if (s.lip.e) ctx.fillRect(48, 0, 4, T$1);
		ctx.fillStyle = "rgba(0,0,0,0.5)";
		if (s.lip.n) ctx.fillRect(0, 9, T$1, 2);
	}
	/** 海底熱泉（少見）：紅橘岩漿上面多兩團白蒸氣。 */
	function frostLava(ctx, s) {
		const r = rng(s.x, s.y, 506);
		ctx.fillStyle = "#d04010";
		ctx.fillRect(0, 0, T$1, T$1);
		for (let i = 0; i < 4; i++) {
			const cx = r() * T$1;
			const cy = r() * T$1;
			const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 18);
			gg.addColorStop(0, "#ffb030");
			gg.addColorStop(1, rgba$1("#ffb030", 0));
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$1, T$1);
		}
		for (let i = 0; i < 2; i++) {
			const cx = 10 + r() * 32;
			const cy = 10 + r() * 20;
			const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14);
			gg.addColorStop(0, "rgba(240,240,235,0.45)");
			gg.addColorStop(1, "rgba(240,240,235,0)");
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T$1, T$1);
		}
	}
	/** 冰窟（主場）：深藍水；和其他地形相接的邊是冰白外框加淺藍內緣（深色水，致命）。 */
	function frostIceHole(ctx, s) {
		const r = rng(s.x, s.y, 507);
		ctx.fillStyle = "#1e3a5a";
		ctx.fillRect(0, 0, T$1, T$1);
		ctx.strokeStyle = "rgba(255,255,255,0.3)";
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		const wy = 16 + r() * 18;
		ctx.moveTo(12, wy);
		ctx.quadraticCurveTo(20, wy - 4, 28, wy);
		ctx.stroke();
		const edge = (fill, d, w) => {
			ctx.fillStyle = fill;
			if (s.lip.n) ctx.fillRect(0, d, T$1, w);
			if (s.lip.s) ctx.fillRect(0, T$1 - d - w, T$1, w);
			if (s.lip.w) ctx.fillRect(d, 0, w, T$1);
			if (s.lip.e) ctx.fillRect(T$1 - d - w, 0, w, T$1);
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
	function rot$1(p, k, T) {
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
			const [px, py] = rot$1(p, k, T);
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
			const [px, py] = rot$1([t * T, prof(t)], k, T);
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
	var T = 52;
	function drawStone(ctx, s) {
		const r = rng(s.x, s.y, 1);
		ctx.fillStyle = PAL.stoneGap;
		ctx.fillRect(0, 0, T, T);
		const slabs = [];
		const splitV = r() < .5;
		const cut = .35 + r() * .3;
		if (splitV) slabs.push([
			0,
			0,
			T * cut,
			T
		], [
			T * cut,
			0,
			T * (1 - cut),
			T
		]);
		else slabs.push([
			0,
			0,
			T,
			T * cut
		], [
			0,
			T * cut,
			T,
			T * (1 - cut)
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
			let px = T * (.2 + r() * .6);
			let py = T * (.2 + r() * .2);
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
		ctx.fillRect(0, 0, T, T);
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = r() < .5 ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)";
			ctx.beginPath();
			ctx.ellipse(r() * T, r() * T, 8 + r() * 10, 6 + r() * 8, r() * TAU$2, 0, TAU$2);
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
			ctx.arc(6 + r() * 40, 6 + r() * 40, 2, 0, TAU$2);
			ctx.fill();
		}
	}
	function drawDirt(ctx, s) {
		const r = rng(s.x, s.y, 3);
		ctx.fillStyle = shade(PAL.dirt, .95 + r() * .1);
		ctx.fillRect(0, 0, T, T);
		const n = 5 + Math.floor(r() * 5);
		for (let i = 0; i < n; i++) {
			ctx.fillStyle = r() < .5 ? PAL.dirtDark : PAL.dirtLight;
			ctx.beginPath();
			ctx.ellipse(4 + r() * 44, 4 + r() * 44, 1.5 + r() * 2.5, 1.2 + r() * 1.8, r() * TAU$2, 0, TAU$2);
			ctx.fill();
		}
		ctx.strokeStyle = "rgba(90,66,40,0.35)";
		ctx.lineWidth = 1;
		ctx.beginPath();
		const yy = T * (.3 + r() * .4);
		ctx.moveTo(0, yy);
		ctx.bezierCurveTo(T * .3, yy - 6, T * .6, yy + 6, T, yy - 2);
		ctx.stroke();
	}
	function drawWall(ctx, s) {
		ctx.fillStyle = PAL.wallTop;
		ctx.fillRect(0, 0, T, T);
		const r = rng(s.x, s.y, 4);
		ctx.strokeStyle = PAL.wallLine;
		ctx.lineWidth = 2;
		const rows = 4;
		const rh = T / rows;
		for (let i = 0; i < rows; i++) {
			ctx.beginPath();
			ctx.moveTo(0, i * rh);
			ctx.lineTo(T, i * rh);
			ctx.stroke();
			const off = i % 2 === 0 ? 0 : T / 4;
			for (let bx = off; bx < T; bx += T / 2) {
				ctx.beginPath();
				ctx.moveTo(bx, i * rh);
				ctx.lineTo(bx, (i + 1) * rh);
				ctx.stroke();
			}
		}
		for (let i = 0; i < 3; i++) {
			ctx.fillStyle = `rgba(255,255,255,${.04 + r() * .05})`;
			ctx.fillRect(Math.floor(r() * 2) * (T / 2) + 2, Math.floor(r() * rows) * rh + 2, T / 2 - 4, 9);
		}
		if (s.wallFace) {
			ctx.fillStyle = PAL.wallFace;
			ctx.fillRect(0, 43, T, 9);
			ctx.fillStyle = "rgba(255,255,255,0.08)";
			ctx.fillRect(0, 43, T, 1.5);
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
				T,
				0
			], [0, 1]);
			const gg = ctx.createLinearGradient(0, 0, 0, 16);
			gg.addColorStop(0, "rgba(70,64,80,0.9)");
			gg.addColorStop(1, "rgba(70,64,80,0)");
			ctx.fillStyle = gg;
			ctx.fillRect(0, 0, T, 16);
			ctx.fillStyle = PAL.chasmLip;
		}
		if (s.lip.s) jag(ctx, r, [
			0,
			T,
			T,
			T
		], [0, -1]);
		if (s.lip.w) jag(ctx, r, [
			0,
			0,
			0,
			T
		], [1, 0]);
		if (s.lip.e) jag(ctx, r, [
			T,
			0,
			T,
			T
		], [-1, 0]);
	}
	/** 熔岩（6V-2）：橘紅發光、黑色岩殼裂紋、靠岸一圈冷卻黑殼（`hazardTerrainArt.drawLavaBase`）；岩殼慢速漂移在 surfaceAnim。 */
	function drawLava(ctx, s) {
		drawLavaBase(ctx, s, 6);
	}
	function drawIceHole(ctx, s) {
		const r = rng(s.x, s.y, 7);
		ctx.fillStyle = PAL.deep;
		ctx.fillRect(0, 0, T, T);
		ctx.strokeStyle = rgba$1(PAL.deepLight, .6);
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
		if (s.lip.n) ctx.fillRect(0, 0, T, 4);
		if (s.lip.w) ctx.fillRect(0, 0, 4, T);
		if (s.lip.e) ctx.fillRect(48, 0, 4, T);
		if (s.lip.s) ctx.fillRect(0, 48, T, 4);
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
		ctx.fillRect(0, 0, T, T);
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
		const cx = T * (.45 + r() * .2);
		const cy = T * (.5 + r() * .2);
		ctx.moveTo(cx, cy);
		ctx.lineTo(cx + 8, cy + 10);
		ctx.lineTo(cx + 14, cy + 6);
		ctx.moveTo(cx + 8, cy + 10);
		ctx.lineTo(cx + 4 + r() * 6, cy + 16);
		ctx.stroke();
	}
	/** 油：虹彩亮斑＋一抹白色油光。 */
	function oilTexture(ctx, _s, r) {
		const cx = T * (.3 + r() * .3);
		const cy = T * (.3 + r() * .3);
		const g = ctx.createLinearGradient(cx - 12, cy - 6, cx + 12, cy + 6);
		g.addColorStop(0, "rgba(160,90,220,0.4)");
		g.addColorStop(.5, "rgba(80,200,160,0.32)");
		g.addColorStop(1, "rgba(230,200,80,0.3)");
		ctx.fillStyle = g;
		ctx.beginPath();
		ctx.ellipse(cx, cy, 11, 4.5, -.4 + (r() - .5) * .6, 0, TAU$2);
		ctx.fill();
		ctx.fillStyle = "rgba(255,255,255,0.25)";
		ctx.beginPath();
		ctx.ellipse(cx + 11, cy + 11, 6, 2.5, -.4, 0, TAU$2);
		ctx.fill();
	}
	/** 火的焦痕（6V-3）：黑底不規則的燒焦斑＋外圈煙燻暈＋幾點灰燼；全部照格子座標雜湊。 */
	function scorchMarks(ctx, r) {
		const n = 2 + Math.floor(r() * 2);
		for (let i = 0; i < n; i++) {
			const cx = T * (.22 + r() * .56);
			const cy = T * (.45 + r() * .4);
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
				const a = k / 8 * TAU$2;
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
			ctx.arc(6 + r() * 40, T * .55 + r() * T * .38, .9 + r() * .8, 0, TAU$2);
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
		const glow = ctx.createRadialGradient(T / 2, T * .62, 2, T / 2, T * .62, T * .55);
		glow.addColorStop(0, "rgba(255,190,70,0.6)");
		glow.addColorStop(1, "rgba(255,90,20,0)");
		ctx.fillStyle = glow;
		ctx.fillRect(0, 0, T, T);
		const n = 2 + Math.floor(r() * 2);
		for (let i = 0; i < n; i++) fireTongue(ctx, T * ((i + .5) / n) + (r() - .5) * 6, 45 - r() * 9, 13 + r() * 7, (r() - .5) * 1.2);
	}
	function poisonTexture(ctx, _s, r) {
		ctx.strokeStyle = "rgba(220,255,180,0.8)";
		ctx.fillStyle = "rgba(160,230,100,0.6)";
		ctx.lineWidth = 1;
		for (let i = 0; i < 4; i++) {
			ctx.beginPath();
			ctx.arc(8 + r() * 36, 8 + r() * 36, 2 + r() * 3, 0, TAU$2);
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
			ctx.arc(4 + r() * 44, 4 + r() * 44, 9 + r() * 7, 0, TAU$2);
			ctx.fill();
		}
	}
	function holyTexture(ctx, _s, r) {
		const g = ctx.createRadialGradient(T / 2, T / 2, 2, T / 2, T / 2, T * .55);
		g.addColorStop(0, "rgba(255,255,240,0.55)");
		g.addColorStop(1, "rgba(255,255,240,0)");
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T, T);
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
		const g = ctx.createRadialGradient(T / 2, T / 2, 2, T / 2, T / 2, T * .62);
		g.addColorStop(0, rgba$1(PAL.darkness, .6));
		g.addColorStop(1, rgba$1(PAL.darkness, 0));
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, T, T);
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
			fill: (s) => rgba$1(waterColorOf(s, PAL.water), .86),
			edge: {
				color: "rgba(220,240,255,0.55)",
				width: 1.2
			}
		},
		ice: {
			fill: () => rgba$1(PAL.ice, .88),
			texture: iceTexture,
			edge: {
				color: "#ffffff",
				width: 2.2
			}
		},
		oil: {
			fill: () => rgba$1(PAL.oil, .88),
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
			fill: () => rgba$1(PAL.poison, .7),
			texture: poisonTexture,
			edge: {
				color: "rgba(190,240,140,0.85)",
				width: 1.6
			}
		},
		smoke: {
			fill: () => rgba$1(PAL.smoke, .35),
			texture: smokeTexture,
			edge: {
				color: "rgba(235,238,245,0.6)",
				width: 1.4
			}
		},
		holy: {
			fill: () => rgba$1(PAL.holy, .5),
			texture: holyTexture,
			edge: {
				color: "rgba(255,245,200,0.9)",
				width: 1.6
			}
		},
		darkness: {
			fill: () => rgba$1(PAL.darkness, .55),
			texture: darknessTexture,
			edge: {
				color: "rgba(150,90,200,0.75)",
				width: 1.6
			}
		}
	};
	/** 未知表面：灰色併塊、沒有紋理。 */
	var UNKNOWN_SURFACE = {
		fill: () => rgba$1("#9a9aa8", .5),
		edge: {
			color: "rgba(210,210,220,0.6)",
			width: 1.4
		}
	};
	/** 這一格表面的形狀（四鄰、斜鄰的同種旗標 → 併塊）。 */
	function surfaceShape(s) {
		return blobShape(s.x, s.y, s.surfSame, s.surfDiag ?? ALL_CORNERS, T);
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
			ctx.fillStyle = rgba$1(numToHex(s.tint), .3);
			ctx.fillRect(0, 0, T, T);
		}
		if (!s.blocked) heightLight(ctx, s.height);
		if (s.surface !== "none") drawSurface(ctx, s);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/eventArtCapital.ts
	var NO_SIDES = {
		n: false,
		s: false,
		w: false,
		e: false
	};
	/** 主城地面一格（主城實地圖的石板＋金色嵌線）。 */
	function capitalTile(ctx, gx, gy) {
		const spec = {
			region: "capital",
			look: "",
			terrain: "stone",
			x: gx,
			y: gy,
			height: 0,
			surface: "none",
			surfSame: NO_SIDES,
			lip: NO_SIDES,
			wallFace: false,
			blocked: false,
			tint: null
		};
		ctx.save();
		ctx.translate(gx * 52, gy * 52);
		drawTile(ctx, spec);
		ctx.restore();
	}
	/**
	* 兩盞源晶燈的位置（燈畫布的左上角，虛擬單位；畫布 1×2 格、下面那格是燈座；畫時縮成 0.8）：
	* 左邊那盞避開左上角的事件小牌、放低一點；右邊那盞在最上一列的右端。
	*/
	var CAPITAL_LAMPS = [[13, 10.4], [317.2, -15.6]];
	/** 石板上的一層米白（實地圖的石板偏灰；插圖縮小後要讀成「白石板」，照 region-themes.png 右欄）。 */
	var CAPITAL_WASH = "rgba(255,248,232,0.28)";
	/** 遠處藍頂白牆一角：一棟 3 格寬的白石廳，縮小放在右上角、一部分在畫面外。 */
	function distantHall(ctx) {
		ctx.save();
		ctx.translate(218.4, -2.6);
		ctx.scale(.55, .55);
		paintBuilding(ctx, {
			kind: "stone_hall",
			w: 3,
			h: 1,
			doors: [1],
			sign: null
		});
		ctx.restore();
	}
	/** 主城背景的點綴（地面之上、場景之下）：石板提亮、遠處的藍頂白牆一角、兩盞源晶燈。 */
	function capitalBackdrop(ctx) {
		ctx.fillStyle = CAPITAL_WASH;
		ctx.fillRect(0, 0, 364, 156);
		distantHall(ctx);
		for (const [x, y] of CAPITAL_LAMPS) {
			ctx.save();
			ctx.translate(x, y);
			ctx.scale(.8, .8);
			drawCrystalLamp(ctx);
			ctx.restore();
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/creaturePose.ts
	var clamp$1 = (v, a = 0, b = 1) => Math.max(a, Math.min(b, Number.isFinite(v) ? v : 0));
	function cp(p, k) {
		const v = p[k];
		const def = k === "sx" || k === "sy" || k === "alpha" ? 1 : 0;
		return typeof v === "number" && Number.isFinite(v) ? v : def;
	}
	/** 套上姿勢（呼叫端已 save）：位移 → 以腳底為軸傾斜 → 伸縮 → 透明度。值是預設時不加指令。 */
	function applyCreaturePose(ctx, p) {
		const dx = cp(p, "dx");
		const dy = cp(p, "dy");
		if (dx !== 0 || dy !== 0) ctx.translate(dx, dy);
		const rot = cp(p, "rot");
		if (rot !== 0) ctx.rotate(rot);
		const sx = cp(p, "sx");
		const sy = cp(p, "sy");
		if (sx !== 1 || sy !== 1) ctx.scale(sx, sy);
		const a = clamp$1(cp(p, "alpha"));
		if (a !== 1) ctx.globalAlpha = (typeof ctx.globalAlpha === "number" ? ctx.globalAlpha : 1) * a;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/creatureRig.ts
	/** 每款身形固定的 Q 大頭（飛禽依款式另列在 inkCreature 的 BODIES）。 */
	var Q_HEADS = {
		hound: [
			"hd-ear",
			12,
			-22,
			1.3
		],
		boar: [
			"bo-ear",
			11,
			-15,
			1.25
		],
		bear: [
			"be-head",
			11,
			-21,
			1.3
		],
		lizard: [
			"lz-head",
			13,
			-9,
			1.3
		],
		serpent: [
			"sn-head",
			6,
			-23,
			1.3
		],
		shell: [
			"sh-head",
			12,
			-7,
			1.3
		],
		golem: [
			"go-head",
			1,
			-40,
			1.28,
			"go-arm"
		],
		feline: [
			"fe-ear",
			11,
			-12,
			1.35
		]
	};
	var RIG = {
		hound: {
			groups: [
				["hd-lf-12", "BF"],
				["hd-lf6", "FF"],
				["hd-l-9", "BN"],
				["hd-l8", "FN"],
				["hd-tail", "tail"],
				["hd-ear", "head"],
				["hd-head", "head"],
				["hd-fang", "head"]
			],
			pivots: {
				BF: [-10, -15],
				FF: [8, -15],
				BN: [-7, -16],
				FN: [10, -16],
				tail: [-14, -18],
				head: [12, -21],
				body: [0, -12]
			}
		},
		boar: {
			groups: [
				["bo-lf-10", "BF"],
				["bo-lf6", "FF"],
				["bo-l-7", "BN"],
				["bo-l8", "FN"],
				["bo-tail", "tail"],
				["bo-ear", "head"],
				["bo-head", "head"],
				["bo-snout", "head"],
				["bo-tusk", "head"]
			],
			pivots: {
				BF: [-8, -12],
				FF: [8, -12],
				BN: [-5, -12],
				FN: [10, -12],
				tail: [-15, -16],
				head: [11, -15],
				body: [0, -9]
			}
		},
		bear: {
			groups: [
				["be-lf-11", "BF"],
				["be-lf6", "FF"],
				["be-l-6", "BN"],
				["be-l11", "FN"],
				["be-head", "head"],
				["be-ear", "head"],
				["be-snout", "head"]
			],
			pivots: {
				BF: [-11, -15],
				FF: [6, -15],
				BN: [-6, -15],
				FN: [11, -15],
				head: [12, -22],
				body: [0, -10]
			}
		},
		bat: {
			groups: [
				["fl-bwf", "wingF"],
				["fl-bwn", "wingN"],
				["fl-be", "head"],
				["fl-bhead", "head"],
				["fl-bfang", "head"]
			],
			pivots: {
				wingF: [-1, -2],
				wingN: [2, -2],
				head: [4, -3],
				body: [0, 0]
			}
		},
		bird: {
			groups: [
				["fl-wf", "wingF"],
				["fl-tail", "tail"],
				["fl-wn", "wingN"],
				["fl-sh", "wingN"],
				["fl-head", "head"],
				["fl-beak", "head"],
				["fl-claw", "legs"]
			],
			pivots: {
				wingF: [-1, -3],
				wingN: [3, -3],
				tail: [-8, 0],
				head: [6, -2],
				legs: [0, 4],
				body: [0, 0]
			}
		},
		spider: {
			groups: [
				["sp-lf0", "F0"],
				["sp-lf1", "F1"],
				["sp-lf2", "F2"],
				["sp-lf3", "F3"],
				["sp-abd", "abd"],
				["sp-sh", "spikes"],
				["sp-mark", "abd"],
				["sp-head", "head"],
				["sp-eyes", "head"],
				["sp-fang", "head"],
				["sp-l0", "N0"],
				["sp-l1", "N1"],
				["sp-l2", "N2"],
				["sp-l3", "N3"]
			],
			pivots: {
				F0: [-1.2, -10.6],
				F1: [.8, -10.6],
				F2: [2.8, -10.6],
				F3: [4.8, -10.6],
				N0: [1, -10],
				N1: [3, -10],
				N2: [5, -10],
				N3: [7, -10],
				abd: [-3, -10],
				spikes: [-9, -19.5],
				head: [2, -9],
				body: [0, -6]
			}
		},
		beetle: {
			groups: [
				["bt-lf0", "F0"],
				["bt-lf1", "F1"],
				["bt-lf2", "F2"],
				["bt-l0", "N0"],
				["bt-l1", "N1"],
				["bt-l2", "N2"],
				["bt-head", "head"],
				["bt-horn", "head"],
				["bt-eye", "head"],
				["bt-sh", "spikes"]
			],
			pivots: {
				F0: [-6, -7],
				F1: [2, -7],
				F2: [9, -7],
				N0: [-8, -7],
				N1: [0, -7],
				N2: [7, -7],
				head: [11, -10],
				spikes: [-2, -20],
				body: [0, -8]
			}
		},
		lizard: {
			groups: [
				["lz-lf-6", "BF"],
				["lz-lf9", "FF"],
				["lz-l-7", "BN"],
				["lz-l10", "FN"],
				["lz-tail", "tail"],
				["lz-head", "head"]
			],
			pivots: {
				BF: [-6, -7],
				FF: [9, -7],
				BN: [-7, -8],
				FN: [10, -8],
				tail: [-8, -7.5],
				head: [13, -10],
				body: [2, -8]
			}
		},
		serpent: {
			groups: [
				["sn-coil", "coil"],
				["sn-sh", "coil"],
				["sn-neck", "neck"],
				["sn-belly", "neck"],
				["sn-head", "head"],
				["sn-tongue", "head"]
			],
			pivots: {
				coil: [-4, -1],
				neck: [5, -6],
				head: [7, -24],
				body: [0, -6]
			}
		},
		shell: {
			groups: [
				["sh-lf-9", "BF"],
				["sh-lf6", "FF"],
				["sh-l-11", "BN"],
				["sh-l5", "FN"],
				["sh-head", "head"]
			],
			pivots: {
				BF: [-10, -9],
				FF: [5, -9],
				BN: [-9, -9],
				FN: [8, -9],
				head: [12, -8],
				body: [0, -6]
			}
		},
		ooze: {
			groups: [["oz-face", "face"]],
			pivots: {
				face: [6, -10],
				body: [0, 0]
			}
		},
		golem: {
			groups: [
				["go-legf", "legF"],
				["go-armf", "armF"],
				["go-legn", "legN"],
				["go-head", "head"],
				["go-eye", "head"],
				["go-arm", "armN"],
				["go-fist", "armN"]
			],
			pivots: {
				legF: [-4, -17],
				legN: [3, -17],
				armF: [-11, -35],
				armN: [7, -37],
				head: [1, -40],
				body: [0, -16]
			}
		},
		wisp: {
			groups: [
				["wp-or0", "orb0"],
				["wp-or1", "orb1"],
				["wp-or2", "orb2"],
				["wp-core", "core"],
				["wp-in", "core"]
			],
			pivots: {
				orb0: [-11, -5],
				orb1: [10, -8],
				orb2: [3, 9],
				core: [0, 0],
				body: [0, 0]
			}
		},
		feline: {
			groups: [
				["fe-lf-8", "BF"],
				["fe-lf10", "FF"],
				["fe-l-11", "BN"],
				["fe-l7", "FN"],
				["fe-tail", "tail"],
				["fe-ear", "head"],
				["fe-head", "head"],
				["fe-muzzle", "head"]
			],
			pivots: {
				BF: [-8, -12],
				FF: [10, -12],
				BN: [-11, -12],
				FN: [7, -12],
				tail: [-12, -11],
				head: [11, -12],
				body: [0, -9]
			}
		},
		wraith: {
			groups: [
				["wr-arm-l", "armB"],
				["wr-arm-r", "armN"],
				["wr-head", "head"]
			],
			pivots: {
				armB: [-7, -30],
				armN: [7, -30],
				head: [0, -33],
				body: [0, -20]
			}
		},
		pylon: {
			groups: [
				["py-base", "base"],
				["py-ob", "ob"],
				["py-eye", "eye"],
				["py-ring", "ring"]
			],
			pivots: {
				base: [0, 0],
				ob: [0, -5],
				eye: [1.6, -22],
				ring: [0, -22],
				body: [0, -5]
			}
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qCreatureElem.ts
	var CREATURE_ELEM = {
		fire: ["#ff6a1a", "#ffd04a"],
		ice: ["#8fe3ff", "#e8fbff"],
		lightning: ["#fff36b", "#fff7c0"],
		poison: ["#7ddc3a", "#d6f59a"],
		wind: ["#c8ffe8", "#effff8"],
		earth: ["#b0814a", "#e6c89a"],
		holy: ["#fff2b0", "#fffbe0"],
		shadow: ["#9a6ad8", "#c8a8f0"],
		water: ["#3a7bd5", "#d8f0ff"]
	};
	var FIRE = CREATURE_ELEM["fire"];
	/** 元素色（不認得 → 預設）。 */
	var elemOr = (element, d) => element !== void 0 ? CREATURE_ELEM[element] ?? d : d;
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qCreatureLayer.ts
	/** Q 版外框色（同 qDoll 的 OUT）。 */
	var QC_OUT = "#16121a";
	var POOL = [];
	var lent = [];
	function mkc(w, h) {
		const c = POOL.pop() ?? document.createElement("canvas");
		c.width = Math.max(1, w);
		c.height = Math.max(1, h);
		lent.push(c);
		return c;
	}
	function giveBack(list) {
		for (const c of list) if (POOL.length < 24) POOL.push(c);
	}
	function tint(src, color) {
		const c = mkc(src.width, src.height);
		const g = c.getContext("2d");
		g.drawImage(src, 0, 0);
		g.globalCompositeOperation = "source-in";
		g.fillStyle = color;
		g.fillRect(0, 0, c.width, c.height);
		return c;
	}
	/** 圓盤膨脹：N 個方向 × 3 圈（1、0.66、0.33 倍半徑），同樣張。 */
	function dilate$2(src, r, N = 16) {
		const c = mkc(src.width, src.height);
		const g = c.getContext("2d");
		for (const f of [
			1,
			.66,
			.33
		]) for (let i = 0; i < N; i++) {
			const a = i / N * TAU$2;
			g.drawImage(src, Math.cos(a) * r * f, Math.sin(a) * r * f);
		}
		g.drawImage(src, 0, 0);
		return c;
	}
	/** 有沒有 DOM（沒有時呼叫端直接平塗、不做外框）。 */
	var hasDom = () => typeof document !== "undefined";
	/**
	* 在目前座標系的 box [x0, y0, x1, y1]（單位）裡畫一層：`draw(g)` 畫平塗部件；外框 `ow` 單位。
	* 離屏解析度跟著目前的變換走（getTransform）；鏡像由呼叫端的 scale(-1, 1) 處理。
	*/
	function qLayer(ctx, box, draw, o = {}) {
		const outer = lent;
		lent = [];
		try {
			layerInner(ctx, box, draw, o);
		} finally {
			giveBack(lent);
			lent = outer;
		}
	}
	function layerInner(ctx, box, draw, o) {
		const T = ctx.getTransform();
		const m = Math.max(.5, Math.hypot(T.a, T.b));
		const W = Math.ceil((box[2] - box[0]) * m);
		const H = Math.ceil((box[3] - box[1]) * m);
		if (!(W > 0 && H > 0 && W < 16384 && H < 16384)) return;
		const off = mkc(W, H);
		const g = off.getContext("2d");
		g.setTransform(m, 0, 0, m, -box[0] * m, -box[1] * m);
		draw(g);
		const ow = (o.ow ?? 1.3) * m;
		const rim = dilate$2(tint(off, QC_OUT), ow);
		const rg = rim.getContext("2d");
		rg.globalCompositeOperation = "destination-out";
		rg.drawImage(off, 0, 0);
		if (o.fade != null) {
			const [yb, yt] = o.fade;
			for (const c of [off, rim]) {
				const q = c.getContext("2d");
				q.save();
				q.setTransform(m, 0, 0, m, -box[0] * m, -box[1] * m);
				q.globalCompositeOperation = "destination-out";
				[
					.35,
					.65,
					.92
				].forEach((al, i) => {
					const y0 = yt + (yb - yt) * i / 3;
					const y1 = i === 2 ? box[3] : yt + (yb - yt) * (i + 1) / 3;
					q.globalAlpha = al;
					q.fillRect(box[0], y0, box[2] - box[0], y1 - y0);
				});
				q.restore();
			}
		}
		ctx.save();
		const put = (c, a) => {
			ctx.globalAlpha = a;
			ctx.drawImage(c, box[0], box[1], W / m, H / m);
		};
		if (o.flat !== void 0) {
			put(tint(off, o.flat), o.alpha ?? 1);
			ctx.restore();
			return;
		}
		if (o.glow != null) {
			const gl = dilate$2(tint(off, o.glow), ow + (o.glowW ?? 2.6) * m, 24);
			const gg = gl.getContext("2d");
			gg.globalCompositeOperation = "destination-out";
			gg.drawImage(off, 0, 0);
			put(gl, o.glowA ?? .6);
		}
		const a = o.alpha ?? 1;
		put(rim, a < 1 ? Math.min(1, a + .2 * Math.min(1, a * 5)) : 1);
		put(off, a);
		if ((o.flash ?? 0) > 0) put(tint(off, o.flashColor ?? "#ffffff"), Math.min(1, o.flash ?? 0) * a);
		ctx.restore();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qCreatureAnim.ts
	var OUT$3 = QC_OUT;
	var ELEM = {
		fire: CREATURE_ELEM["fire"],
		ice: CREATURE_ELEM["ice"],
		lightning: CREATURE_ELEM["lightning"],
		poison: CREATURE_ELEM["poison"],
		shadow: CREATURE_ELEM["shadow"]
	};
	var cl = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
	var seg = (u, a, b) => cl((u - a) / (b - a));
	var sm = (x) => x * x * (3 - 2 * x);
	var bump = (u, a, b) => Math.sin(Math.PI * seg(u, a, b));
	var S$2 = (u, n = 1, ph = 0) => Math.sin(TAU$2 * (u * n + ph));
	var Cn = (u, n = 1, ph = 0) => Math.cos(TAU$2 * (u * n + ph));
	/** 關鍵格內插：兩格之間用 smoothstep。 */
	function kf(u, pts) {
		const first = pts[0];
		if (u <= first[0]) return first[1];
		for (let i = 1; i < pts.length; i++) {
			const [b, vb] = pts[i];
			if (u <= b) {
				const [a, va] = pts[i - 1];
				return va + (vb - va) * sm((u - a) / (b - a || 1));
			}
		}
		return pts[pts.length - 1][1];
	}
	var MUL = /* @__PURE__ */ new Set([
		"sx",
		"sy",
		"a"
	]);
	function newPose() {
		return {
			root: {},
			parts: {},
			flash: 0,
			alpha: 1,
			shadow: 1,
			fx: []
		};
	}
	function merge(o, f) {
		const rec = o;
		for (const [k, v] of Object.entries(f)) if (k === "pivot") o.pivot = f.pivot;
		else if (MUL.has(k)) rec[k] = (rec[k] ?? 1) * v;
		else rec[k] = (rec[k] ?? 0) + v;
	}
	var A$1 = (p, g, f) => merge(p.parts[g] ?? (p.parts[g] = {}), f);
	var R = (p, f) => merge(p.root, f);
	var FX = (p, f) => void p.fx.push(f);
	/** 飛行物：u 在 [a, b] 從 (x0,y0) 飛到 (x1,y1)，拱高 h；回傳 null＝還沒出手／已到。 */
	function proj(u, a, b, x0, y0, x1, y1, h = 0) {
		if (u < a || u > b) return null;
		const q = seg(u, a, b);
		return [x0 + (x1 - x0) * q, y0 + (y1 - y0) * q - h * Math.sin(Math.PI * q)];
	}
	var TGT = 52;
	/** CB-2c：產卵片段的蛋：從這一格（u）離開身體；起點（腳底座標，朝東）；大小。戰場的拋物線（eggArc）用同一組。 */
	var EGG_FROM_U = .42;
	var EGG_START = [-6, -16];
	var EGG_SCALE = 1.3;
	var elc = (r, d) => elemOr(r.element, d);
	var LEGS4 = [
		["FN", 0],
		["BF", 0],
		["FF", .5],
		["BN", .5]
	];
	function breathe(p, u, amt = .025) {
		R(p, { sy: 1 + amt * (.5 - .5 * Cn(u)) });
	}
	/** 四足對角步：腳底前後＝斜切 kx（往前擺時抬腳＝sy 縮短）；身體一步一顛。 */
	function quadWalk(p, u, c) {
		for (const [g, ph] of LEGS4) {
			const sw = S$2(u, 1, ph);
			const lift = Math.max(0, Cn(u, 1, ph));
			A$1(p, g, {
				kx: -c.amp * sw,
				sy: 1 - c.lift * lift
			});
		}
		R(p, { dy: -c.bob * (.5 - .5 * Cn(u, 2)) });
		A$1(p, "head", { rot: c.nod * S$2(u, 2, .15) });
		if (c.tail) A$1(p, "tail", { rot: c.tail * S$2(u, 1, .25) });
	}
	/** 六腳三腳架步：一組同相。 */
	function hexWalk(p, u, groups, c) {
		groups.forEach((gs, i) => gs.forEach((g) => {
			const sw = S$2(u, 1, i * .5);
			const lift = Math.max(0, Cn(u, 1, i * .5));
			A$1(p, g, c.rot === true ? {
				rot: c.amp * sw,
				dy: -c.lift * lift
			} : {
				kx: -c.amp * sw,
				sy: 1 - c.lift * lift
			});
		}));
		R(p, { dy: -c.bob * (.5 - .5 * Cn(u, 2)) });
	}
	/** 拍翅：翅膀 sy 從上舉到下壓；下拍快（前 40%）、上收慢；下拍時身體往上。 */
	function flap(p, u, c = {}) {
		const q = u < .4 ? sm(u / .4) : 1 - sm((u - .4) / .6);
		const up = c.up ?? 1.05;
		const dn = c.dn ?? -.55;
		A$1(p, "wingN", {
			sy: up + (dn - up) * q,
			rot: .12 * q
		});
		A$1(p, "wingF", {
			sy: up + (dn - up) * cl(q * .92),
			rot: .1 * q
		});
		R(p, { dy: -(c.bob ?? 1.6) * Math.sin(Math.PI * q) + (c.base ?? 0) });
		return q;
	}
	/** 翻面的 sy：跳過 0 附近（不會出現「一條線」的那格）。 */
	var flipSy = (f) => {
		const c = Math.cos(Math.PI * f);
		return Math.abs(c) < .5 ? f < .5 ? .5 : -.5 : c;
	};
	function quadLegsTuck(p, k) {
		for (const [g] of LEGS4) A$1(p, g, { sy: 1 - k });
	}
	/** 以 N 為分母的關鍵格（格號 → u＝格號／N），命中格落在量化格上。 */
	var kfN = (u, N, pts) => kf(u, pts.map(([f, v]) => [f / N, v]));
	/**
	* 腳踩地：腳底留在「靜止位置＋off」、離地 lift，由髖的實際位置反推腿的斜切與長度，不穿地、不打滑；抵消 root 的旋轉。
	* 髖抬太高時腿最多拉到 maxS 倍，再高就自然離地。root 要先設好。
	*/
	function plant(p, e, feet, maxS = 1.12) {
		const piv = RIG[e.r.key]?.pivots ?? {};
		const o = p.root;
		const [rx, ry] = o.pivot ?? [0, 0];
		const th = o.rot ?? 0;
		const c = Math.cos(th);
		const s = Math.sin(th);
		for (const [g, off = 0, lift0 = 0] of feet) {
			const [px, py] = piv[g] ?? [0, 0];
			const a = px - rx;
			const b = py - ry;
			const X = rx + (o.dx ?? 0) + a * c - b * s;
			const Y = ry + (o.dy ?? 0) + a * s + b * c;
			const L = -py;
			const lift = Math.max(lift0, -Y - L * maxS);
			const h = Math.max(1, -Y - lift);
			A$1(p, g, {
				rot: -th,
				kx: (px + off - X) / h,
				sy: h / L
			});
		}
	}
	/** 部件上的一點（靜態座標）算到地面座標：套部件變換、大頭倍率、root。特效要從部件出發時用（pose 先設好）。 */
	function ptOf(p, e, g, x, y) {
		const f = p.parts[g] ?? {};
		const [px, py] = f.pivot ?? RIG[e.r.key]?.pivots[g] ?? [0, 0];
		const o = p.root;
		const [rx, ry] = o.pivot ?? [0, 0];
		let a = (x - px) * (f.sx ?? 1);
		const b = (y - py) * (f.sy ?? 1);
		a += (f.kx ?? 0) * b;
		const r = f.rot ?? 0;
		let X = px + (f.dx ?? 0) + a * Math.cos(r) - b * Math.sin(r);
		let Y = py + (f.dy ?? 0) + a * Math.sin(r) + b * Math.cos(r);
		const qh = g === "head" ? Q_HEADS[e.r.key] : void 0;
		if (qh !== void 0) {
			const [, hx, hy, hs] = qh;
			X = hx + (X - hx) * hs;
			Y = hy + (Y - hy) * hs;
		}
		const th = o.rot ?? 0;
		const c = Math.cos(th);
		const s = Math.sin(th);
		const A0 = X - rx;
		const B0 = Y - ry;
		return [rx + (o.dx ?? 0) + A0 * c - B0 * s, ry + (o.dy ?? 0) + A0 * s + B0 * c];
	}
	function hitCommon(p, u, back = 3, tilt = .08) {
		p.flash = u < .2 ? .9 : 0;
		R(p, {
			dx: -kf(u, [
				[0, 0],
				[.18, back],
				[1, 0]
			]),
			rot: -tilt * kf(u, [
				[0, 0],
				[.18, 1],
				[1, 0]
			])
		});
	}
	var HIT = {
		quad(p, u) {
			hitCommon(p, u);
			A$1(p, "head", { rot: -.28 * kf(u, [
				[0, 0],
				[.18, 1],
				[1, 0]
			]) });
			A$1(p, "tail", { rot: .2 * bump(u, 0, .6) });
			for (const g of ["FN", "FF"]) A$1(p, g, { kx: .18 * bump(u, 0, .7) });
		},
		flyer(p, u) {
			hitCommon(p, u, 4, .22);
			R(p, { dy: -3 * bump(u, 0, .8) });
			for (const g of ["wingN", "wingF"]) A$1(p, g, { sy: 1 + .25 * bump(u, 0, .5) });
			A$1(p, "head", { rot: -.3 * bump(u, 0, .7) });
		},
		crawler(p, u) {
			hitCommon(p, u, 2.5, .1);
			A$1(p, "head", { rot: -.25 * bump(u, 0, .7) });
			for (const g of [
				"N0",
				"N1",
				"N2",
				"N3",
				"F0",
				"F1",
				"F2",
				"F3"
			]) A$1(p, g, { kx: .12 * bump(u, 0, .6) });
		},
		serpent(p, u) {
			hitCommon(p, u, 2, .04);
			const k = kf(u, [
				[0, 0],
				[.18, 1],
				[1, 0]
			]);
			A$1(p, "neck", { kx: .32 * k });
			A$1(p, "head", {
				dx: -5.5 * k,
				rot: -.35 * k
			});
		},
		shell(p, u) {
			hitCommon(p, u, 2, .05);
			const k = kf(u, [
				[0, 0],
				[.15, 1],
				[.7, 1],
				[1, 0]
			]);
			A$1(p, "head", {
				dx: -3.5 * k,
				sx: 1 - .3 * k
			});
			quadLegsTuck(p, .45 * k);
			R(p, { dy: 1.35 * k * .8 });
		},
		ooze(p, u) {
			p.flash = u < .2 ? .9 : 0;
			const k = kf(u, [
				[0, 0],
				[.15, 1],
				[1, 0]
			]);
			const w = Math.sin(u * 14) * (1 - u);
			R(p, {
				dx: -2.5 * k,
				sx: 1 + .2 * k + .06 * w,
				sy: 1 - .2 * k - .06 * w,
				kx: -.12 * k
			});
			A$1(p, "face", {
				dx: -1.5 * k,
				dy: 1.5 * k
			});
		},
		golem(p, u) {
			hitCommon(p, u, 1.5, .05);
			A$1(p, "head", { rot: -.18 * bump(u, 0, .6) });
			A$1(p, "armN", { rot: .25 * bump(u, 0, .6) });
			A$1(p, "armF", { rot: .2 * bump(u, 0, .6) });
		},
		wisp(p, u) {
			p.flash = u < .2 ? .9 : 0;
			const k = kf(u, [
				[0, 0],
				[.15, 1],
				[1, 0]
			]);
			R(p, { dx: -3 * k + (u < .6 ? .8 * Math.sign(Math.sin(u * 40)) * (1 - u) : 0) });
			A$1(p, "core", {
				sx: 1 - .15 * k,
				sy: 1 - .15 * k
			});
			[
				[-1, -.6],
				[1, -1],
				[.3, 1]
			].forEach(([x, y], i) => A$1(p, `orb${i}`, {
				dx: 4 * x * k,
				dy: 4 * y * k
			}));
		},
		wraith(p, u) {
			hitCommon(p, u, 3, .06);
			const k = bump(u, 0, .8);
			A$1(p, "body", { kx: -.25 * k });
			A$1(p, "head", { dx: -2 * k });
			A$1(p, "armN", { rot: .5 * k });
			A$1(p, "armB", { rot: .4 * k });
			p.alpha = 1 - .3 * k;
		},
		pylon(p, u) {
			p.flash = u < .2 ? .9 : 0;
			const j = u < .55 ? Math.sign(Math.sin(u * 46)) * (1 - u / .55) : 0;
			A$1(p, "ob", {
				dx: -1.2 * j,
				rot: -.03 * j
			});
			A$1(p, "eye", {
				dx: -1.2 * j,
				sy: 1 - .6 * bump(u, 0, .5)
			});
			A$1(p, "ring", {
				dx: -1.2 * j,
				dy: 2 * bump(u, 0, .6)
			});
		}
	};
	function deathQuad(p, u, legH, c = {}) {
		p.flash = u < .12 ? .7 : 0;
		const st = bump(u, 0, .35);
		const k = sm(seg(u, .25, .75));
		R(p, {
			dx: -2 * st - 1.5 * k,
			rot: -.07 * st + .04 * k,
			dy: legH * .62 * k
		});
		quadLegsTuck(p, .7 * k);
		A$1(p, "head", {
			rot: -.25 * st + (c.headRot ?? .4) * sm(seg(u, .45, .9)),
			dy: (c.headDy ?? 3) * sm(seg(u, .45, .9))
		});
		A$1(p, "tail", { rot: -.35 * k });
		if (u >= .6) p.eyeShut = true;
		p.shadow = 1 - .15 * k;
	}
	/** 側倒（熊、野豬；QK-4b）：晃一下 → 身體落地、四腳伸直往前後攤開、頭垂到地上、最後閉眼（×）。legH＝腳長。 */
	function deathSide(p, u, legH, c = {}) {
		p.flash = u < .12 ? .7 : 0;
		const st = bump(u, 0, .35);
		const k = sm(seg(u, .25, .75));
		const hk = sm(seg(u, .4, .85));
		R(p, {
			dx: -2 * st - 1 * k,
			rot: -.07 * st + .05 * k,
			dy: legH * (c.drop ?? .6) * k
		});
		for (const [g, sgn, f] of [
			[
				"FN",
				-1,
				1
			],
			[
				"FF",
				-1,
				.75
			],
			[
				"BN",
				1,
				1
			],
			[
				"BF",
				1,
				.75
			]
		]) A$1(p, g, {
			rot: sgn * (c.legRot ?? 1.2) * f * k,
			sy: 1 - .08 * k
		});
		A$1(p, "head", {
			rot: -.25 * st + (c.headRot ?? .5) * hk,
			dy: (c.headDy ?? 3) * hk
		});
		A$1(p, "tail", { rot: .5 * k });
		if (u >= .6) p.eyeShut = true;
		if (u > .55 && u < .9) FX(p, {
			k: "dust",
			x: 0,
			y: -1,
			r: 4,
			a: 1 - seg(u, .55, .9)
		});
		p.shadow = 1 - .1 * k;
	}
	/** 一顆飛行物（出手 → 命中爆開）；飛行與命中標 `ranged`。 */
	function shot(p, u, a, b, from, c, o = {}) {
		const q = proj(u, a, b, from[0], from[1], o.x1 ?? TGT, o.y1 ?? -12, o.h ?? 0);
		if (q !== null) FX(p, {
			k: o.kind ?? "orb",
			x: q[0],
			y: q[1],
			r: o.r ?? 2.6,
			c: c[0],
			c2: c[1],
			...o.kind === void 0 ? { tail: 1 } : {},
			rot: u * 20,
			ranged: true
		});
		if (u > b) {
			const k = seg(u, b, Math.min(1, b + .25));
			if (k < 1) {
				FX(p, {
					k: "glow",
					x: o.x1 ?? TGT,
					y: o.y1 ?? -12,
					r: 10 + 6 * k,
					c: c[0],
					a: 1 - k,
					ranged: true
				});
				FX(p, {
					k: "burst",
					x: o.x1 ?? TGT,
					y: o.y1 ?? -12,
					r: 4 + 4 * k,
					c: c[0],
					c2: c[1],
					a: 1 - k * .8,
					ranged: true
				});
			}
		}
	}
	/** 蓄力：在 at 聚一顆光。 */
	function charge(p, u, a, b, at, c, r = 2.6) {
		if (u >= a && u <= b) {
			const k = seg(u, a, b);
			FX(p, {
				k: "glow",
				x: at[0],
				y: at[1],
				r: 4 + 6 * k,
				c: c[0],
				a: .4 + .6 * k
			});
			FX(p, {
				k: "orb",
				x: at[0],
				y: at[1],
				r: r * (.4 + .6 * k),
				c: c[0],
				c2: c[1]
			});
		}
	}
	var QUAKE = "#ffe9a8";
	function quakeFx(p, u, a, x, c = QUAKE) {
		if (u < a) return;
		const k = seg(u, a, 1);
		FX(p, {
			k: "ring",
			x,
			rx: 8 + 34 * k,
			c,
			a: 1 - k,
			w: 1.8
		});
		FX(p, {
			k: "ring",
			x,
			rx: 4 + 18 * k,
			c,
			a: (1 - k) * .9,
			w: 1.8
		});
		FX(p, {
			k: "glow",
			x,
			y: -2,
			r: 10 * (1 - k) + 4,
			c,
			a: .6 * (1 - k)
		});
		FX(p, {
			k: "dust",
			x: x - 6 - 8 * k,
			y: -1,
			r: 3 + 3 * k,
			a: 1 - k
		});
		FX(p, {
			k: "dust",
			x: x + 6 + 8 * k,
			y: -1,
			r: 3 + 3 * k,
			a: 1 - k
		});
		for (let i = 0; i < 3; i++) FX(p, {
			k: "rock",
			x: x - 8 + i * 8 + (i - 1) * 6 * k,
			y: -1 - 8 * Math.sin(Math.PI * cl(k * 1.6 - i * .1)),
			s: 1.6,
			a: 1 - k
		});
	}
	var chompFx = (p, u, a, b, x, y) => {
		if (u >= a && u <= b) FX(p, {
			k: "chomp",
			x,
			y,
			q: seg(u, a, b),
			a: 1 - .5 * seg(u, a, b)
		});
	};
	var slashFx = (p, u, a, b, x, y, c, r = 6) => {
		if (u >= a && u <= b) FX(p, {
			k: "slash",
			x,
			y,
			r,
			c,
			a: 1 - seg(u, a, b) * .7,
			len: .5 + seg(u, a, b)
		});
	};
	/** 畫特效（地面座標，跟著呼叫端的縮放、鏡像；實體特效有細外框）。 */
	function drawCreatureFx(ctx, fxs, _element, box = [
		-70,
		-90,
		74,
		18
	]) {
		const solid = [];
		for (const f of fxs) {
			const a = f.a ?? 1;
			const x = f.x ?? 0;
			const y = f.y ?? 0;
			const r = f.r ?? 1;
			if (f.k === "dust") {
				ctx.save();
				ctx.fillStyle = f.c ?? "#b8a890";
				for (const [dx, dy, s] of [
					[
						-1,
						0,
						1
					],
					[
						.2,
						-.5,
						1.25
					],
					[
						1.2,
						.1,
						.9
					]
				]) {
					ctx.globalAlpha = .55 * a;
					ctx.beginPath();
					ctx.ellipse(x + dx * r, y + dy * r * .6, r * .7 * s, r * .5 * s, 0, 0, TAU$2);
					ctx.fill();
				}
				ctx.restore();
			} else if (f.k === "ring") {
				const w = f.w ?? 1.4;
				const rx = f.rx ?? 1;
				ctx.save();
				ctx.globalAlpha = a;
				ctx.strokeStyle = OUT$3;
				ctx.lineWidth = w + 1.2;
				ctx.beginPath();
				ctx.ellipse(x, y, rx, rx * .3, 0, 0, TAU$2);
				ctx.stroke();
				ctx.strokeStyle = f.c ?? "#ffffff";
				ctx.lineWidth = w;
				ctx.stroke();
				ctx.restore();
			} else if (f.k === "glow") {
				ctx.save();
				ctx.fillStyle = f.c ?? "#ffffff";
				for (const [s, al] of [
					[1, .18],
					[.65, .26],
					[.35, .4]
				]) {
					ctx.globalAlpha = al * a;
					ctx.beginPath();
					ctx.arc(x, y, r * s, 0, TAU$2);
					ctx.fill();
				}
				ctx.restore();
			} else if (f.k === "cone") {
				ctx.save();
				const n = 5;
				for (let i = 0; i < n; i++) {
					const q = (i + .5) / n;
					if (q > (f.len ?? 1)) continue;
					const d = q * (f.max ?? 30);
					const rr = 2.2 + q * (f.spread ?? 6);
					const ang = f.ang ?? 0;
					const cx = x + Math.cos(ang) * d;
					const cy = y + Math.sin(ang) * d + Math.sin(i * 2.1 + (f.t ?? 0)) * 1.2;
					ctx.globalAlpha = a * (.75 - .4 * q);
					ctx.fillStyle = f.c ?? "#ffffff";
					ctx.beginPath();
					ctx.arc(cx, cy, rr, 0, TAU$2);
					ctx.fill();
					ctx.globalAlpha = a * (.8 - .5 * q);
					ctx.fillStyle = f.c2 ?? "#ffffff";
					ctx.beginPath();
					ctx.arc(cx - rr * .2, cy - rr * .2, rr * .45, 0, TAU$2);
					ctx.fill();
				}
				ctx.restore();
			} else if (f.k === "wave") {
				ctx.save();
				ctx.globalAlpha = a;
				for (const [w, c] of [[2.4, OUT$3], [1.2, f.c ?? "#ffffff"]]) {
					ctx.strokeStyle = c;
					ctx.lineWidth = w;
					ctx.lineCap = "round";
					ctx.beginPath();
					ctx.arc(x, y, r, -.7, .7);
					ctx.stroke();
				}
				ctx.restore();
			} else if (f.k === "puff") {
				ctx.save();
				ctx.globalAlpha = .5 * a;
				ctx.fillStyle = f.c ?? "#eef2f4";
				ctx.beginPath();
				ctx.ellipse(x, y, r, r * .7, 0, 0, TAU$2);
				ctx.fill();
				ctx.restore();
			} else solid.push(f);
		}
		if (solid.length === 0) return;
		const draw = (g) => {
			for (const f of solid) drawSolid(g, f);
		};
		if (hasDom() && typeof ctx.getTransform === "function") qLayer(ctx, box, draw, { ow: .8 });
		else draw(ctx);
	}
	function drawSolid(g, f) {
		const x = f.x ?? 0;
		const y = f.y ?? 0;
		const r = f.r ?? 1;
		const c = f.c ?? "#ffffff";
		g.save();
		g.globalAlpha = f.a ?? 1;
		if (f.k === "orb") {
			g.fillStyle = c;
			g.beginPath();
			g.arc(x, y, r, 0, TAU$2);
			g.fill();
			g.fillStyle = f.c2 ?? "#ffffff";
			g.beginPath();
			g.arc(x - r * .15, y - r * .15, r * .5, 0, TAU$2);
			g.fill();
			if (f.tail) {
				g.globalAlpha *= .6;
				g.fillStyle = c;
				g.beginPath();
				g.ellipse(x - r * 1.6 * f.tail, y, r * 1.3 * f.tail, r * .55, 0, 0, TAU$2);
				g.fill();
			}
		} else if (f.k === "burst") {
			g.fillStyle = c;
			g.beginPath();
			for (let i = 0; i < 14; i++) {
				const an = i / 14 * TAU$2 + .2;
				const d = i % 2 ? r * .45 : r;
				if (i > 0) g.lineTo(x + Math.cos(an) * d, y + Math.sin(an) * d);
				else g.moveTo(x + Math.cos(an) * d, y + Math.sin(an) * d);
			}
			g.closePath();
			g.fill();
			g.fillStyle = f.c2 ?? "#ffffff";
			g.beginPath();
			g.arc(x, y, r * .32, 0, TAU$2);
			g.fill();
		} else if (f.k === "bolt") {
			const x0 = f.x0 ?? 0;
			const y0 = f.y0 ?? 0;
			const x1 = f.x1 ?? 0;
			const y1 = f.y1 ?? 0;
			const pts = [[x0, y0]];
			const n = 5;
			for (let i = 1; i < n; i++) {
				const q = i / n;
				pts.push([x0 + (x1 - x0) * q, y0 + (y1 - y0) * q + (i % 2 ? -2.6 : 2.6) * (f.amp ?? 1)]);
			}
			pts.push([x1, y1]);
			for (const [w, cc] of [[2.2, c], [.8, "#ffffff"]]) {
				g.strokeStyle = cc;
				g.lineWidth = w;
				g.lineJoin = "miter";
				g.lineCap = "round";
				g.beginPath();
				pts.forEach(([px, py], i) => i > 0 ? g.lineTo(px, py) : g.moveTo(px, py));
				g.stroke();
			}
		} else if (f.k === "beam") {
			g.lineCap = "round";
			const w0 = f.w ?? 2;
			for (const [w, cc] of [[w0, c], [w0 * .4, "#ffffff"]]) {
				g.strokeStyle = cc;
				g.lineWidth = w;
				g.beginPath();
				g.moveTo(f.x0 ?? 0, f.y0 ?? 0);
				g.lineTo(f.x1 ?? 0, f.y1 ?? 0);
				g.stroke();
			}
		} else if (f.k === "slash") {
			g.lineCap = "round";
			for (let i = 0; i < 3; i++) {
				g.strokeStyle = c;
				g.lineWidth = 1.1;
				g.beginPath();
				g.arc(x + i * 2.2 - 2.2, y + i * 1.2, r, (f.ang ?? -.3) - .9 * (f.len ?? 1), (f.ang ?? -.3) + .5);
				g.stroke();
			}
		} else if (f.k === "chomp") {
			const o = (1 - (f.q ?? 0)) * 3.2 + .6;
			g.fillStyle = "#ffffff";
			for (const sgn of [-1, 1]) {
				g.beginPath();
				g.moveTo(x - 4, y + sgn * o);
				g.quadraticCurveTo(x, y + sgn * (o + 3), x + 4, y + sgn * o);
				for (let i = 3; i >= 0; i--) {
					const xx = x - 3 + i * 2;
					g.lineTo(xx + 1, y + sgn * (o - 1.6));
					g.lineTo(xx, y + sgn * o);
				}
				g.closePath();
				g.fill();
			}
		} else if (f.k === "shard") {
			g.translate(x, y);
			g.rotate(f.rot ?? 0);
			const s = f.s ?? 2.4;
			g.fillStyle = c;
			g.beginPath();
			g.moveTo(0, -s * 1.5);
			g.lineTo(s * .7, 0);
			g.lineTo(0, s * 1.2);
			g.lineTo(-s * .7, 0);
			g.closePath();
			g.fill();
			g.fillStyle = "#ffffff";
			g.fillRect(-s * .2, -s * .8, s * .3, s * .7);
		} else if (f.k === "egg") {
			const s = f.s ?? 1;
			g.translate(x, y);
			g.rotate(f.rot ?? 0);
			g.fillStyle = f.c ?? "#ffb23a";
			g.beginPath();
			g.ellipse(0, -3.2 * s, 2.6 * s, 3.3 * s, 0, 0, TAU$2);
			g.fill();
			g.fillStyle = "#ffe08a";
			g.beginPath();
			g.ellipse(-.8 * s, -4.4 * s, .8 * s, 1.1 * s, 0, 0, TAU$2);
			g.fill();
			if (f.crack === true) {
				g.strokeStyle = OUT$3;
				g.lineWidth = .6;
				g.beginPath();
				g.moveTo(-2.4 * s, -3.6 * s);
				g.lineTo(-1, -2.4 * s);
				g.lineTo(.4, -3.8 * s);
				g.lineTo(2.4 * s, -2.8 * s);
				g.stroke();
			}
		} else if (f.k === "flame") {
			const h = f.h ?? 6;
			g.fillStyle = c;
			g.beginPath();
			g.moveTo(x - 2.6, y);
			g.quadraticCurveTo(x - 2.8, y - h * .5, x, y - h);
			g.quadraticCurveTo(x + 2.8, y - h * .5, x + 2.6, y);
			g.closePath();
			g.fill();
			g.fillStyle = f.c2 ?? "#ffd04a";
			g.beginPath();
			g.ellipse(x, y - h * .3, 1.2, h * .28, 0, 0, TAU$2);
			g.fill();
		} else if (f.k === "blob") {
			const rx = f.rx ?? r;
			const ry = f.ry ?? r;
			g.fillStyle = c;
			g.beginPath();
			g.ellipse(x, y, rx, ry, 0, 0, TAU$2);
			g.fill();
			if (f.rim !== void 0) {
				g.strokeStyle = f.rim;
				g.lineWidth = .7;
				g.stroke();
			}
			g.fillStyle = "#ffffff";
			g.globalAlpha *= .6;
			g.beginPath();
			g.arc(x - rx * .35, y - ry * .35, Math.min(rx, ry) * .25, 0, TAU$2);
			g.fill();
		} else if (f.k === "sweep") {
			const n = 18;
			const w = f.w ?? 3;
			const a0 = f.a0 ?? 0;
			const a1 = f.a1 ?? 0;
			const at = (q, rr) => [x + Math.cos(a0 + (a1 - a0) * q) * rr, y + Math.sin(a0 + (a1 - a0) * q) * rr];
			g.fillStyle = c;
			g.beginPath();
			for (let i = 0; i <= n; i++) {
				const [px, py] = at(i / n, r);
				if (i > 0) g.lineTo(px, py);
				else g.moveTo(px, py);
			}
			for (let i = n; i >= 0; i--) {
				const q = i / n;
				const [px, py] = at(q, r - w * Math.sin(Math.PI * Math.pow(q, 1.7)));
				g.lineTo(px, py);
			}
			g.closePath();
			g.fill();
		} else if (f.k === "rock") {
			const s = f.s ?? 1;
			g.fillStyle = f.c ?? "#7f8f94";
			g.beginPath();
			g.moveTo(x - s, y);
			g.lineTo(x - s * .6, y - s * 1.2);
			g.lineTo(x + s * .5, y - s * 1.5);
			g.lineTo(x + s, y);
			g.closePath();
			g.fill();
		}
		g.restore();
	}
	var BT_TRI = [[
		"N0",
		"N2",
		"F1"
	], [
		"F0",
		"F2",
		"N1"
	]];
	var SP_TETRA = [[
		"N0",
		"F1",
		"N2",
		"F3"
	], [
		"F0",
		"N1",
		"F2",
		"N3"
	]];
	var ORB_HOME = [
		[-11, -5],
		[10, -8],
		[3, 9]
	];
	function neck(p, kx, rot = 0, extra = 0) {
		A$1(p, "neck", { kx });
		A$1(p, "head", {
			dx: -18 * kx + extra,
			rot
		});
	}
	var GOLEM_TOP = [
		[-30, -70],
		[30, -70],
		[30, -31],
		[7, -33],
		[2, -29.5],
		[-4, -32.5],
		[-30, -30]
	];
	var GOLEM_LEFT = [
		[-30, -30],
		[-4, -32.5],
		[2, -29.5],
		[.5, -24],
		[-2.5, -20],
		[-.5, -8],
		[-30, -8]
	];
	var GOLEM_RIGHT = [
		[2, -29.5],
		[7, -33],
		[30, -31],
		[30, -8],
		[-.5, -8],
		[-2.5, -20],
		[.5, -24]
	];
	var TAILOVER = [
		[
			0,
			0,
			null,
			0,
			"c",
			2,
			-8,
			["p"]
		],
		[
			3,
			.3,
			[
				.04,
				.05,
				.06,
				.06
			],
			-.05,
			"c",
			2,
			-6.6,
			["p"]
		],
		[
			8,
			.55,
			[
				.1,
				.14,
				.16,
				.14
			],
			-.12,
			"c",
			1,
			-5.6,
			["p"]
		],
		[
			45,
			.3,
			[
				-.1,
				-.16,
				-.2,
				-.2
			],
			-.6,
			"s",
			12,
			-7,
			[
				"f",
				.5,
				1
			]
		],
		[
			100,
			.05,
			[
				-.2,
				-.3,
				-.36,
				-.34
			],
			.35,
			"c",
			13,
			-34,
			[
				"a",
				-.5,
				.6,
				.9
			]
		],
		[
			165,
			.2,
			[
				-.3,
				-.4,
				-.44,
				-.4
			],
			.2,
			"c",
			17,
			-26,
			[
				"a",
				.3,
				-.4,
				.9
			]
		],
		[
			198,
			.16,
			[
				.1,
				.08,
				.05,
				0
			],
			-.15,
			"t",
			47,
			-1.2,
			[
				"a",
				-.2,
				.3,
				.95
			]
		],
		[
			186,
			.63,
			[
				.03,
				0,
				-.03,
				0
			],
			-.3,
			"t",
			47,
			-1.2,
			[
				"a",
				.5,
				-.5,
				1
			]
		],
		[
			255,
			-.6,
			[
				-.25,
				-.25,
				-.2,
				-.15
			],
			.3,
			"c",
			15,
			-20,
			[
				"a",
				-.4,
				.5,
				1
			]
		],
		[
			318,
			.7,
			[
				-.12,
				-.17,
				-.17,
				-.17
			],
			.15,
			"c",
			13,
			-24.5,
			[
				"a",
				-.3,
				.2,
				1
			]
		],
		[
			345,
			.5,
			[
				.1,
				.1,
				.1,
				.1
			],
			.2,
			"c",
			12,
			-10,
			[
				"h",
				10,
				-.5,
				1
			]
		],
		[
			362,
			.18,
			[
				-.05,
				-.05,
				0,
				.05
			],
			.1,
			"c",
			13,
			-6,
			["p", 10]
		],
		[
			-8,
			.45,
			[
				.04,
				.05,
				.05,
				.04
			],
			-.05,
			"c",
			7,
			-12.5,
			[
				"p",
				4.5,
				3.5
			]
		],
		[
			3,
			.25,
			[
				.06,
				.08,
				.08,
				.06
			],
			0,
			"c",
			2,
			-6.4,
			["p"]
		],
		[
			0,
			0,
			null,
			0,
			"c",
			2,
			-8,
			["p"]
		]
	];
	var LZ_TAIL = [
		[-8, -7.5],
		[-13, -7.2],
		[-18, -6.7],
		[-23, -5.5],
		[-27.5, -3.4]
	];
	var LZ_TIP = [-32, -1];
	/**
	* 分段彎尾巴：把尾巴組切成 5 段（pose.split），第 i 段繞自己的關節多轉 bends[i-1]、接在上一段的末端；每段是原圖的一塊，花紋跟著彎、沿線長度不變。
	* 相鄰兩段在關節處重疊 1.5 單位（彎的外側不會裂開）。回傳尾尖在尾巴組內的座標。
	*/
	function bendTail(p, bends) {
		const box = (x0, x1) => [
			[x0, -40],
			[x1, -40],
			[x1, 30],
			[x0, 30]
		];
		const pieces = [{ clip: box(-13, -3) }];
		let c = 0;
		let P = LZ_TAIL[1];
		for (let i = 1; i <= 4; i++) {
			c += bends[i - 1];
			const J = LZ_TAIL[i];
			const N = i < 4 ? LZ_TAIL[i + 1] : LZ_TIP;
			const a = N[0] - J[0];
			const b = N[1] - J[1];
			pieces.push({
				pivot: J,
				dx: P[0] - J[0],
				dy: P[1] - J[1],
				rot: c,
				clip: box(i < 4 ? N[0] : -45, J[0] + 1.5)
			});
			P = [P[0] + a * Math.cos(c) - b * Math.sin(c), P[1] + a * Math.sin(c) + b * Math.cos(c)];
		}
		p.split = {
			...p.split ?? {},
			tail: pieces
		};
		return P;
	}
	var BODY_ANIM = {
		hound: {
			kind: "quad",
			mouth: [29, -24],
			units: "灰燼犬、霧狼",
			idle(p, u) {
				breathe(p, u);
				A$1(p, "tail", { rot: .2 * S$2(u, 2) });
				A$1(p, "head", { rot: -.05 * S$2(u, 1, .1) });
			},
			move(p, u) {
				quadWalk(p, u, {
					amp: .3,
					lift: .32,
					bob: .9,
					nod: .06,
					tail: .18
				});
			},
			attacks: {
				bite: {
					zh: "雙咬（fangs／雙牙）",
					type: "melee",
					ms: 760,
					fn(p, u) {
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.18, -2],
								[.32, 6],
								[.42, 4],
								[.55, 7],
								[.7, 6],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.18, -.07],
								[.32, .06],
								[.45, -.02],
								[.55, .07],
								[1, 0]
							]),
							pivot: [-10, 0]
						});
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.18, -.35],
							[.3, .22],
							[.42, -.3],
							[.55, .26],
							[.7, .1],
							[1, 0]
						]) });
						for (const g of ["FN", "FF"]) A$1(p, g, { kx: -.25 * bump(u, .2, .75) });
						for (const g of ["BN", "BF"]) A$1(p, g, { kx: .2 * bump(u, .2, .75) });
						chompFx(p, u, .28, .42, 37, -23);
						chompFx(p, u, .5, .66, 38, -21);
					}
				},
				maul: {
					zh: "撲咬拉扯（咬住後身體後坐、往後拉扯）",
					type: "melee2",
					ms: 1100,
					hitF: 4,
					fn(p, u, e) {
						const k = (pts) => kfN(u, 12, pts);
						const f = Math.round(u * 12);
						const pull = f === 5 || f === 7 ? 1 : f === 9 ? 1.15 : 0;
						const s = k([
							[0, 0],
							[4, 0],
							[5, 1],
							[6, -.45],
							[7, 1],
							[8, -.45],
							[9, 1.15],
							[10, 0],
							[12, 0]
						]);
						const dx = k([
							[0, 0],
							[1, -1.5],
							[2, -3.5],
							[3, 6],
							[4, 13],
							[5, 9.5],
							[9, 9.5],
							[10, 4],
							[11, 0],
							[12, 0]
						]) + (pull ? -4.2 * pull : 2.4 * s);
						const rot = k([
							[0, 0],
							[1, .05],
							[2, .09],
							[3, -.17],
							[4, .08],
							[5, -.1],
							[9, -.1],
							[10, -.08],
							[11, .05],
							[12, 0]
						]) + (pull ? -.1 * pull : .08 * s);
						R(p, {
							dx,
							dy: k([
								[0, 0],
								[1, 1.5],
								[2, 3],
								[3, -6],
								[4, .6],
								[5, 1.6],
								[9, 1.6],
								[10, -6],
								[11, 2],
								[12, 0]
							]) + 2.2 * pull,
							rot,
							pivot: [0, -12]
						});
						A$1(p, "head", {
							rot: k([
								[0, 0],
								[1, .08],
								[2, .16],
								[3, -.42],
								[4, 0],
								[5, .04],
								[9, .04],
								[10, .1],
								[12, 0]
							]) + (pull ? .16 : -.34 * s),
							dx: pull ? -1.5 * pull : -4.2 * s,
							dy: pull ? 0 : .6 * s
						});
						const ff = k([
							[0, 0],
							[2, 0],
							[3, 9],
							[4, 15],
							[9, 15],
							[10, 6],
							[11, 0],
							[12, 0]
						]);
						const bf = k([
							[0, 0],
							[2, 0],
							[3, -3],
							[4, 12],
							[9, 12],
							[10, 3],
							[11, 0],
							[12, 0]
						]);
						const lf = k([
							[2, 0],
							[3, 5],
							[4, 0],
							[9, 0],
							[10, 4],
							[11, 0]
						]);
						const lb = k([
							[2, 0],
							[3, 3],
							[4, 0],
							[9, 0],
							[10, 4],
							[11, 0]
						]);
						plant(p, e, [
							[
								"FN",
								ff,
								lf
							],
							[
								"FF",
								ff,
								lf
							],
							[
								"BN",
								bf,
								lb
							],
							[
								"BF",
								bf,
								lb
							]
						]);
						A$1(p, "tail", { rot: k([
							[0, 0],
							[2, .4],
							[3, -.25],
							[4, .1],
							[9, .1],
							[10, -.3],
							[11, .25],
							[12, 0]
						]) + (pull ? .5 : .75 * s) });
						if (f >= 4 && f <= 9) {
							const [mx, my] = ptOf(p, e, "head", 28, -23.4);
							FX(p, {
								k: "chomp",
								x: mx + .5,
								y: my,
								q: f === 4 ? .3 : pull ? 1 : .72
							});
							if (f === 4) FX(p, {
								k: "burst",
								x: mx + 6.5,
								y: my,
								r: 7,
								c: "#ffffff",
								c2: "#ffe9a8"
							});
						}
					}
				},
				cast: {
					zh: "火種爆燃（口中引爆）",
					type: "cast",
					ms: 900,
					fn(p, u, e) {
						const c = elc(e.r, ELEM.fire);
						R(p, {
							rot: kf(u, [
								[0, 0],
								[.35, -.1],
								[.48, .05],
								[1, 0]
							]),
							pivot: [-10, 0],
							dx: kf(u, [
								[0, 0],
								[.35, -1.5],
								[.48, 2],
								[1, 0]
							])
						});
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.35, -.45],
							[.48, .18],
							[1, 0]
						]) });
						charge(p, u, .08, .42, [29, -27], c);
						shot(p, u, .44, .62, [31, -25], c, { r: 2.2 });
					}
				}
			},
			death(p, u) {
				deathQuad(p, u, 15, {
					headRot: .45,
					headDy: 6
				});
			}
		},
		boar: {
			kind: "quad",
			mouth: [24, -13],
			units: "硫煙獸",
			idle(p, u) {
				breathe(p, u, .03);
				A$1(p, "head", { rot: .05 * S$2(u, 2) });
				A$1(p, "tail", { rot: .4 * Math.max(0, S$2(u, 2, .2)) });
			},
			move(p, u) {
				quadWalk(p, u, {
					amp: .32,
					lift: .3,
					bob: .7,
					nod: .08,
					tail: .3
				});
			},
			attacks: {
				gore: {
					zh: "獠牙撞（fangs）",
					type: "melee",
					ms: 820,
					fn(p, u) {
						A$1(p, "FN", {
							kx: u < .32 ? .35 * S$2(u / .32, 2) : 0,
							sy: u < .32 ? 1 - .2 * Math.max(0, Cn(u / .32, 2)) : 1
						});
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.3, -1.5],
								[.5, 9],
								[.62, 8],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.3, .06],
								[.5, .04],
								[.6, -.1],
								[.75, 0],
								[1, 0]
							]),
							pivot: [-8, 0]
						});
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.3, .32],
							[.5, .25],
							[.6, -.5],
							[.78, 0],
							[1, 0]
						]) });
						for (const [g, ph] of LEGS4) A$1(p, g, { kx: u > .3 && u < .52 ? -.35 * S$2(seg(u, .3, .52), 1, ph) : 0 });
						if (u > .3 && u < .5) FX(p, {
							k: "dust",
							x: -14,
							y: -1,
							r: 3,
							a: 1 - seg(u, .3, .5)
						});
						slashFx(p, u, .55, .7, 34, -18, "#ffffff", 5);
					}
				},
				uptusk: {
					zh: "獠牙上挑（低頭貼地、猛然上挑）",
					type: "melee2",
					ms: 1e3,
					hitF: 5,
					fn(p, u, e) {
						const k = (pts) => kfN(u, 11, pts);
						const f = Math.round(u * 11);
						const rot = k([
							[0, 0],
							[1, .05],
							[2, .09],
							[3, .11],
							[4, .11],
							[5, -.24],
							[6, -.44],
							[7, -.3],
							[8, -.08],
							[9, -.02],
							[11, 0]
						]);
						R(p, {
							dx: k([
								[0, 0],
								[3, -1],
								[4, -1.2],
								[5, 2],
								[6, 2.4],
								[8, 1],
								[11, 0]
							]),
							rot,
							pivot: [-6.5, -12]
						});
						plant(p, e, [
							["FN"],
							["FF"],
							["BN"],
							["BF"]
						]);
						A$1(p, "head", { rot: k([
							[0, 0],
							[1, .16],
							[2, .26],
							[3, .31],
							[4, .33],
							[5, .34],
							[6, .34],
							[7, .3],
							[8, .14],
							[9, .04],
							[11, 0]
						]) });
						A$1(p, "tail", { rot: k([
							[0, 0],
							[3, .6],
							[4, .6],
							[6, -.3],
							[11, 0]
						]) });
						if (f >= 2 && f <= 4) FX(p, {
							k: "dust",
							x: 30,
							y: -1,
							r: 3.5,
							a: f === 4 ? .6 : 1
						});
						if (f >= 5 && f <= 8) {
							const [tx, ty] = ptOf(p, e, "head", 21.4, -17.4);
							const [bx, by] = ptOf(p, e, "head", 20, -11);
							const d = Math.hypot(tx - bx, ty - by);
							const dirx = (tx - bx) / d;
							const diry = (ty - by) / d;
							const [a0, a1] = [
								[.42, -.35],
								[.22, -.82],
								[-.25, -.6]
							][Math.min(f - 5, 2)];
							if (f <= 7) FX(p, {
								k: "sweep",
								x: 15,
								y: -11,
								r: 21,
								a0,
								a1,
								w: f === 7 ? 1.6 : 3.4
							});
							if (f <= 6) {
								FX(p, {
									k: "burst",
									x: tx + dirx * 5.5 + 1.5,
									y: ty + diry * 5.5,
									r: f === 5 ? 6 : 5,
									c: "#ffffff",
									c2: "#ffe9a8"
								});
								for (let i = 0; i < 3; i++) FX(p, {
									k: "rock",
									x: 39 + i * 5 + (f - 5) * 2,
									y: -2 - (f === 5 ? 9 : 15) * (1 + i * .22),
									s: 1.6 * (f === 5 ? 1 : .8)
								});
							}
						}
					}
				},
				breath: {
					zh: "硫煙吐息（錐形）",
					type: "breath",
					ms: 1e3,
					fn(p, u, e) {
						breathe(p, cl(u / .3) * .5, .06 * (u < .3 ? 1 : 0));
						R(p, { dx: kf(u, [
							[0, 0],
							[.28, -1.5],
							[.4, .5],
							[.85, .5],
							[1, 0]
						]) });
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.28, -.3],
							[.4, .12],
							[.85, .1],
							[1, 0]
						]) });
						if (u > .36 && u < .92) FX(p, {
							k: "cone",
							x: 25,
							y: -12,
							max: 36,
							spread: 9,
							len: seg(u, .36, .6),
							c: e.r.element === "poison" || e.r.element === void 0 ? "#c8d040" : elc(e.r, ELEM.poison)[0],
							c2: "#f2f0b0",
							a: 1 - seg(u, .8, .92),
							t: u * 12
						});
					}
				}
			},
			death(p, u) {
				deathSide(p, u, 9, {
					headRot: .35,
					headDy: 2.5
				});
			}
		},
		bear: {
			kind: "quad",
			mouth: [26, -23],
			units: "石背熊",
			idle(p, u) {
				breathe(p, u, .03);
				A$1(p, "head", { rot: .06 * S$2(u, 1) });
				R(p, { kx: .015 * S$2(u, 1, .25) });
			},
			move(p, u) {
				quadWalk(p, u, {
					amp: .24,
					lift: .3,
					bob: .6,
					nod: .05
				});
				R(p, { rot: .025 * S$2(u, 2) });
			},
			attacks: {
				swipe: {
					zh: "熊掌拍（talons）",
					type: "melee",
					ms: 820,
					fn(p, u) {
						R(p, {
							rot: kf(u, [
								[0, 0],
								[.35, -.3],
								[.5, .07],
								[.65, .04],
								[1, 0]
							]),
							pivot: [-8, 0],
							dx: kf(u, [
								[0, 0],
								[.35, -1],
								[.5, 3],
								[1, 0]
							])
						});
						A$1(p, "FN", { rot: kf(u, [
							[0, 0],
							[.35, -1.25],
							[.5, .35],
							[.65, .1],
							[1, 0]
						]) });
						A$1(p, "FF", { rot: kf(u, [
							[0, 0],
							[.38, -.7],
							[.55, .1],
							[1, 0]
						]) });
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.35, -.15],
							[.5, .2],
							[1, 0]
						]) });
						slashFx(p, u, .45, .62, 31, -9, "#ffffff", 7);
					}
				},
				slam: {
					zh: "人立重拍（人立舉掌、單掌拍地）",
					type: "melee2",
					ms: 1100,
					hitF: 7,
					fn(p, u, e) {
						const k = (pts) => kfN(u, 12, pts);
						const f = Math.round(u * 12);
						const rot = k([
							[0, 0],
							[1, -.26],
							[2, -.52],
							[3, -.68],
							[4, -.74],
							[5, -.74],
							[6, -.42],
							[7, .13],
							[8, .13],
							[9, .09],
							[10, -.05],
							[11, .03],
							[12, 0]
						]);
						R(p, {
							rot,
							dx: k([
								[0, 0],
								[2, -1],
								[5, -1.5],
								[6, 5],
								[7, 13],
								[8, 13],
								[9, 11],
								[10, 5],
								[11, 0],
								[12, 0]
							]),
							dy: k([
								[0, 0],
								[5, 0],
								[6, -2],
								[7, 1.5],
								[8, 1.5],
								[9, 1],
								[10, -4],
								[11, 1.5],
								[12, 0]
							]),
							pivot: [-8.5, -15]
						});
						const hb = k([
							[0, 0],
							[5, 0],
							[6, 5],
							[7, 9],
							[9, 9],
							[10, 4],
							[11, 0],
							[12, 0]
						]);
						const hl = k([
							[5, 0],
							[6, 5],
							[7, 0],
							[9, 0],
							[10, 2.5],
							[11, 0]
						]);
						plant(p, e, [[
							"BN",
							hb,
							hl
						], [
							"BF",
							hb,
							hl
						]]);
						const hw = k([
							[0, 0],
							[1, -3],
							[2, -6.5],
							[3, -7.5],
							[5, -8],
							[6, -5],
							[7, 0],
							[12, 0]
						]);
						const hv = k([
							[0, 0],
							[2, -1.5],
							[3, -5],
							[5, -5.5],
							[6, -1],
							[7, -3],
							[8, -3],
							[9, -1.5],
							[10, 0],
							[12, 0]
						]);
						const c = Math.cos(rot);
						const s = Math.sin(rot);
						A$1(p, "head", {
							rot: k([
								[0, 0],
								[1, -.12],
								[2, -.34],
								[3, -.68],
								[5, -.74],
								[6, -.3],
								[7, .3],
								[8, .3],
								[9, .2],
								[10, .08],
								[12, 0]
							]) - rot,
							dx: (hw * c + hv * s) / 1.3,
							dy: (-hw * s + hv * c) / 1.3
						});
						if (f >= 1 && f <= 6) {
							A$1(p, "FN", {
								rot: k([
									[1, -.9],
									[2, -1.75],
									[3, -2.32],
									[4, -2.5],
									[5, -2.5],
									[6, -1.5]
								]) - rot,
								sy: 1.08,
								sx: 1.06,
								dx: k([
									[1, .5],
									[3, 1.6],
									[6, 1.6]
								]),
								dy: k([
									[1, 0],
									[3, 1],
									[6, 1]
								])
							});
							A$1(p, "FF", {
								rot: k([
									[1, -.5],
									[3, -.9],
									[5, -.9],
									[6, -.5]
								]) - rot,
								sy: .85
							});
						} else if (f >= 7) {
							if (f <= 9) A$1(p, "FN", {
								rot: k([
									[7, -1.05],
									[8, -1.05],
									[9, -1.25]
								]) - rot,
								sy: 1.08,
								sx: 1.06
							});
							else plant(p, e, [[
								"FN",
								k([
									[10, 6],
									[11, 0],
									[12, 0]
								]),
								k([[10, 2.5], [11, 0]])
							]]);
							plant(p, e, [[
								"FF",
								k([
									[7, 15],
									[9, 15],
									[10, 6],
									[11, 0],
									[12, 0]
								]),
								k([
									[9, 0],
									[10, 2.5],
									[11, 0]
								])
							]]);
						}
						if (f >= 1 && f <= 6 && e.r.traits?.includes("stone_back") === true) p.split = { body: [{
							clip: [
								[-40, -60],
								[40, -60],
								[40, -26.2],
								[-40, -26.2]
							],
							dy: 2 * cl(-rot / .5)
						}, { clip: [
							[-40, -26.2],
							[40, -26.2],
							[40, 20],
							[-40, 20]
						] }] };
						const cw = [
							0,
							.4,
							.75,
							1,
							1,
							1,
							1,
							1,
							1,
							.5
						][f] ?? 0;
						if (cw > 0) p.claws = cw;
						if (f >= 7 && f <= 10) {
							const q = (f - 7) / 3;
							const px = f <= 8 ? ptOf(p, e, "FN", 11, -1)[0] : 36;
							FX(p, {
								k: "dust",
								x: px + 8 + 6 * q,
								y: -1,
								r: 3.2 + 3 * q,
								a: 1 - q * .8
							});
							if (f <= 8) FX(p, {
								k: "dust",
								x: px - 9 - 5 * q,
								y: -1,
								r: 2.6 + 2 * q,
								a: 1 - q * .8
							});
							if (f === 7) FX(p, {
								k: "burst",
								x: px + 13,
								y: -7,
								r: 6.5,
								c: "#ffffff",
								c2: "#ffe9a8"
							});
							if (f <= 8) FX(p, {
								k: "sweep",
								x: px - 1,
								y: -18,
								r: 17,
								a0: f === 7 ? -.6 : .5,
								a1: 1.35,
								w: f === 7 ? 3.2 : 1.8
							});
						}
					}
				},
				quake: {
					zh: "雙掌震地（震地推倒）",
					type: "area",
					ms: 1050,
					fn(p, u) {
						R(p, {
							rot: kf(u, [
								[0, 0],
								[.4, -.5],
								[.52, .09],
								[.62, .05],
								[1, 0]
							]),
							pivot: [-9, 0],
							dy: u > .5 && u < .6 ? .6 * Math.sign(Math.sin(u * 90)) : 0
						});
						for (const g of ["FN", "FF"]) A$1(p, g, { rot: kf(u, [
							[0, 0],
							[.4, -1.1],
							[.52, .15],
							[.7, 0],
							[1, 0]
						]) });
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.4, -.25],
							[.52, .25],
							[1, 0]
						]) });
						quakeFx(p, u, .5, 24);
					}
				}
			},
			death(p, u) {
				deathSide(p, u, 12, {
					headRot: .45,
					headDy: 4
				});
			}
		},
		feline: {
			kind: "quad",
			mouth: [21, -14],
			units: "山豹",
			idle(p, u) {
				breathe(p, u);
				A$1(p, "tail", {
					rot: .14 * S$2(u, 1),
					kx: .1 * S$2(u, 1, .2)
				});
				A$1(p, "head", { rot: .04 * S$2(u, 1, .4) });
			},
			move(p, u) {
				R(p, { sy: .96 });
				quadWalk(p, u, {
					amp: .34,
					lift: .32,
					bob: .45,
					nod: .03,
					tail: .12
				});
			},
			attacks: {
				claw: {
					zh: "爪擊（talons）",
					type: "melee",
					ms: 640,
					fn(p, u) {
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.25, -1.5],
								[.45, 4],
								[.6, 3],
								[1, 0]
							]),
							sy: kf(u, [
								[0, 1],
								[.25, .92],
								[.45, 1.03],
								[1, 1]
							])
						});
						A$1(p, "FN", { rot: kf(u, [
							[0, 0],
							[.28, -1.3],
							[.45, .35],
							[.6, .1],
							[1, 0]
						]) });
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.25, -.15],
							[.45, .15],
							[1, 0]
						]) });
						A$1(p, "tail", { rot: .3 * bump(u, .1, .7) });
						slashFx(p, u, .4, .58, 29, -12, "#ffffff", 6);
					}
				},
				upcut: {
					zh: "反手上撩爪（壓低身體、前爪由下往上）",
					type: "melee2",
					ms: 1e3,
					hitF: 6,
					fn(p, u, e) {
						const k = (pts) => kfN(u, 11, pts);
						const f = Math.round(u * 11);
						const rot = k([
							[0, 0],
							[1, .05],
							[2, .09],
							[3, .1],
							[4, .1],
							[5, -.24],
							[6, -.56],
							[7, -.5],
							[8, -.22],
							[9, -.07],
							[10, -.01],
							[11, 0]
						]);
						R(p, {
							rot,
							dx: k([
								[0, 0],
								[2, -1],
								[3, -1.5],
								[4, -1.5],
								[5, 2],
								[6, 5],
								[7, 5],
								[8, 3],
								[9, 1],
								[10, .3],
								[11, 0]
							]),
							dy: k([
								[0, 0],
								[1, 2.4],
								[2, 3.6],
								[3, 4.2],
								[4, 4.2],
								[5, 1.5],
								[6, -.5],
								[7, -.3],
								[8, 0],
								[11, 0]
							]),
							pivot: [-9.5, -12]
						});
						plant(p, e, [
							["FF"],
							["BN"],
							["BF"]
						]);
						if (f <= 4 || f >= 10) plant(p, e, [["FN"]]);
						else A$1(p, "FN", {
							rot: k([
								[5, -1.15],
								[6, -1.4],
								[7, -1.62],
								[8, -1.15],
								[9, -.45]
							]) - rot,
							sy: 1.12,
							sx: 1.08
						});
						A$1(p, "head", {
							rot: k([
								[0, 0],
								[2, .12],
								[3, .14],
								[4, .14],
								[5, .12],
								[6, .38],
								[7, .24],
								[8, .02],
								[10, 0],
								[11, 0]
							]),
							dy: k([
								[4, 0],
								[6, -1.5],
								[7, -1.5],
								[8, -.4],
								[9, 0]
							])
						});
						A$1(p, "tail", { rot: k([
							[0, 0],
							[3, -.25],
							[4, -.3],
							[6, .55],
							[11, 0]
						]) });
						if (f >= 5 && f <= 7) {
							const [sx, sy] = ptOf(p, e, "FN", 7, -12);
							const [px, py] = ptOf(p, e, "FN", 7.6, 0);
							const r = Math.hypot(px - sx, py - sy) + 5;
							const a1 = Math.atan2(py - sy, px - sx) - .12;
							FX(p, {
								k: "sweep",
								x: sx,
								y: sy,
								r,
								a0: Math.min(a1 + [
									.9,
									1.15,
									.55
								][f - 5], Math.asin(cl((-2 - sy) / r, -1, 1))),
								a1,
								w: f === 7 ? 1.6 : 3
							});
						}
					}
				},
				pounce: {
					zh: "衝鋒撲擊（衝鋒撞擊）",
					type: "charge",
					ms: 860,
					fn(p, u) {
						const air = seg(u, .3, .66);
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.3, -2],
								[.66, 14],
								[.76, 15],
								[1, 0]
							]),
							dy: u > .3 && u < .66 ? -9 * Math.sin(Math.PI * air) : 0,
							rot: kf(u, [
								[0, 0],
								[.3, .04],
								[.42, -.2],
								[.6, .18],
								[.7, 0],
								[1, 0]
							]),
							sy: kf(u, [
								[0, 1],
								[.3, .86],
								[.38, 1.05],
								[.66, 1],
								[.72, .9],
								[.8, 1]
							]),
							pivot: [0, -6]
						});
						for (const g of ["FN", "FF"]) A$1(p, g, { rot: -1 * bump(u, .32, .68) });
						for (const g of ["BN", "BF"]) A$1(p, g, { rot: .8 * bump(u, .3, .66) });
						A$1(p, "tail", { rot: -.3 * bump(u, .3, .7) });
						if (u > .66 && u < .86) FX(p, {
							k: "dust",
							x: 18,
							y: -1,
							r: 3.5,
							a: 1 - seg(u, .66, .86)
						});
						p.shadow = 1 - .3 * Math.sin(Math.PI * air);
					}
				}
			},
			death(p, u) {
				deathQuad(p, u, 11, {
					headRot: .3,
					headDy: 2.5
				});
			}
		},
		lizard: {
			kind: "quad",
			mouth: [27, -11],
			units: "餘燼蜥、寒燼蜥、殼縫餘燼蜥、熔爐母獸",
			idle(p, u) {
				breathe(p, u, .03);
				A$1(p, "tail", { rot: .1 * S$2(u, 1) });
				R(p, { dy: -.8 * Math.max(0, S$2(u, 2, .1)) });
				A$1(p, "head", { rot: -.06 * Math.max(0, S$2(u, 2, .1)) });
			},
			move(p, u) {
				quadWalk(p, u, {
					amp: .5,
					lift: .35,
					bob: .3,
					nod: 0
				});
				A$1(p, "body", { rot: .05 * S$2(u, 1) });
				A$1(p, "tail", { rot: -.18 * S$2(u, 1, .1) });
				A$1(p, "head", { rot: -.06 * S$2(u, 1) });
			},
			attacks: {
				bite: {
					zh: "咬（fangs／餘燼啃咬）",
					type: "melee",
					ms: 660,
					fn(p, u, e) {
						R(p, { dx: kf(u, [
							[0, 0],
							[.28, -2],
							[.45, 7],
							[.6, 6],
							[1, 0]
						]) });
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.28, -.38],
							[.42, .22],
							[.6, .1],
							[1, 0]
						]) });
						A$1(p, "tail", { rot: kf(u, [
							[0, 0],
							[.28, .2],
							[.45, -.15],
							[1, 0]
						]) });
						for (const g of ["FN", "FF"]) A$1(p, g, { kx: -.35 * bump(u, .25, .7) });
						if (e.r.mat === "magma" && u > .42 && u < .62) {
							const c = elc(e.r, ELEM.fire);
							FX(p, {
								k: "burst",
								x: 36,
								y: -10,
								r: 3 + 3 * seg(u, .42, .62),
								c: c[0],
								c2: c[1],
								a: 1 - seg(u, .42, .62)
							});
						}
						chompFx(p, u, .4, .58, 36, -11);
					}
				},
				tailover: {
					zh: "掄尾砸擊（前翻掄尾砸在身前，翻完一圈落地再跳回）",
					type: "melee2",
					ms: 1250,
					hitF: 6,
					fn(p, u, e) {
						const f = Math.round(u * 14);
						const c0 = [2, -8];
						const [deg, tr, bd, hr, an, wx, wy, lg] = TAILOVER[f];
						const th = deg * Math.PI / 180;
						A$1(p, "tail", { rot: tr });
						A$1(p, "head", { rot: hr });
						const tipL = bd !== null ? bendTail(p, bd) : LZ_TIP;
						const ta = tipL[0] + 8;
						const tb = tipL[1] + 7.5;
						const loc = an === "s" ? [10, -8] : an === "t" ? [-8 + ta * Math.cos(tr) - tb * Math.sin(tr), -7.5 + ta * Math.sin(tr) + tb * Math.cos(tr)] : c0;
						const a = loc[0] - c0[0];
						const b = loc[1] - c0[1];
						const cs = Math.cos(th);
						const sn = Math.sin(th);
						R(p, {
							rot: th,
							dx: wx - c0[0] - (a * cs - b * sn),
							dy: wy - c0[1] - (a * sn + b * cs),
							pivot: c0
						});
						const FR = ["FN", "FF"];
						const HI = ["BN", "BF"];
						const air = (gs, rot, sy) => gs.forEach((g, i) => A$1(p, g, {
							rot: rot * (i > 0 ? .7 : 1),
							sy
						}));
						if (lg[0] === "p") plant(p, e, [...FR, ...HI].map((g) => [
							g,
							lg[1] ?? 0,
							lg[2] ?? 0
						]));
						else if (lg[0] === "f") {
							plant(p, e, FR.map((g) => [g]));
							air(HI, lg[1], lg[2]);
						} else if (lg[0] === "h") {
							plant(p, e, HI.map((g) => [
								g,
								lg[1],
								0
							]));
							air(FR, lg[2], lg[3]);
						} else {
							air(FR, lg[1], lg[3]);
							air(HI, lg[2], lg[3]);
						}
						p.shadow = 1 - .3 * cl(-(p.root.dy ?? 0) / 18);
						if (f >= 5 && f <= 8) {
							const [tx, ty] = ptOf(p, e, "tail", tipL[0], tipL[1]);
							const c = elc(e.r, ELEM.fire);
							if (f <= 6) {
								const [cx, cy] = ptOf(p, e, "tail", -8, -7.5);
								const a1 = Math.atan2(ty - cy, tx - cx);
								FX(p, {
									k: "sweep",
									x: cx,
									y: cy,
									r: Math.hypot(tx - cx, ty - cy),
									a0: a1 - 1.25,
									a1,
									w: 2.8
								});
							}
							if (f >= 6) {
								const q = (f - 6) / 2;
								FX(p, {
									k: "dust",
									x: 54 + 3 * q,
									y: -1,
									r: 3 + 2 * q,
									a: 1 - .7 * q
								});
								FX(p, {
									k: "dust",
									x: 60 + 4 * q,
									y: -1,
									r: 2.2 + 1.6 * q,
									a: 1 - .7 * q
								});
							}
							if (f === 6) FX(p, {
								k: "burst",
								x: tx + 4,
								y: Math.min(ty - 2, -7),
								r: 6.5,
								c: e.r.mat === "magma" ? c[0] : "#ffffff",
								c2: e.r.mat === "magma" ? c[1] : "#ffe9a8"
							});
						}
					}
				},
				cast: {
					zh: "寒霜（口吐冰彈）",
					type: "cast",
					ms: 860,
					fn(p, u, e) {
						const c = e.r.element !== void 0 ? elc(e.r, ELEM.ice) : e.r.mat === "magma" ? ELEM.fire : ELEM.ice;
						const ice = c === ELEM.ice;
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.4, -1.5],
								[.5, 1.5],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.4, -.08],
								[.5, .03],
								[1, 0]
							]),
							pivot: [-6, 0]
						});
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.4, -.35],
							[.5, .15],
							[1, 0]
						]) });
						charge(p, u, .1, .45, [28, -13], c);
						shot(p, u, .46, .66, [30, -11], c, ice ? {
							kind: "shard",
							r: 2.4
						} : { r: 2.4 });
					}
				},
				summon: {
					zh: "產下幼蜥（召喚）",
					type: "summon",
					ms: 1150,
					fn(p, u, e) {
						const c = elc(e.r, ELEM.fire);
						R(p, {
							sy: kf(u, [
								[0, 1],
								[.35, .9],
								[.45, 1.06],
								[.6, 1],
								[1, 1]
							]),
							rot: kf(u, [
								[0, 0],
								[.35, .05],
								[.45, -.06],
								[.6, 0],
								[1, 0]
							]),
							pivot: [0, 0]
						});
						A$1(p, "tail", { rot: kf(u, [
							[0, 0],
							[.35, .45],
							[.5, -.1],
							[.7, 0],
							[1, 0]
						]) });
						const q = proj(u, EGG_FROM_U, .68, EGG_START[0], EGG_START[1], 34, 0, 18);
						if (q !== null) FX(p, {
							k: "egg",
							x: q[0],
							y: q[1],
							s: EGG_SCALE,
							c: c[0],
							rot: u * 8,
							lobbed: true
						});
						if (u >= .68) {
							const wob = u < .85 ? .25 * Math.sin(u * 70) : 0;
							FX(p, {
								k: "egg",
								x: 34,
								y: 0,
								s: EGG_SCALE,
								c: c[0],
								rot: wob,
								crack: u > .8,
								lobbed: true
							});
							if (u > .86) {
								FX(p, {
									k: "glow",
									x: 34,
									y: -4,
									r: 10,
									c: c[1],
									a: 1 - seg(u, .86, 1),
									lobbed: true
								});
								FX(p, {
									k: "burst",
									x: 34,
									y: -4,
									r: 5,
									c: c[0],
									c2: c[1],
									a: 1 - seg(u, .86, 1),
									lobbed: true
								});
							}
						}
					}
				}
			},
			death(p, u) {
				deathQuad(p, u, 8, {
					headRot: .3,
					headDy: 3
				});
				const k = sm(seg(u, .3, .8));
				A$1(p, "tail", { rot: .4 * k });
				for (const g of ["FN", "FF"]) A$1(p, g, {
					kx: -.9 * k,
					sy: 1.5
				});
				for (const g of ["BN", "BF"]) A$1(p, g, {
					kx: .9 * k,
					sy: 1.5
				});
				A$1(p, "body", { sy: 1 - .12 * k });
			}
		},
		shell: {
			kind: "shell",
			mouth: [21, -8],
			units: "噴岩龜",
			idle(p, u) {
				breathe(p, u, .02);
				A$1(p, "head", {
					dx: -.8 * (.5 - .5 * Cn(u, 1)),
					rot: .06 * S$2(u, 2)
				});
			},
			move(p, u) {
				quadWalk(p, u, {
					amp: .28,
					lift: .3,
					bob: .4,
					nod: .04
				});
				R(p, { rot: .02 * S$2(u, 2) });
			},
			attacks: {
				lob: {
					zh: "背火山拋射（fire_staff）",
					type: "cast",
					ms: 950,
					fn(p, u, e) {
						const c = elc(e.r, ELEM.fire);
						R(p, { sy: kf(u, [
							[0, 1],
							[.3, .93],
							[.4, 1.05],
							[.55, 1],
							[1, 1]
						]) });
						A$1(p, "head", { dx: kf(u, [
							[0, 0],
							[.3, -2],
							[.6, 0],
							[1, 0]
						]) });
						quadLegsTuck(p, .2 * bump(u, 0, .45));
						if (u > .36 && u < .5) FX(p, {
							k: "burst",
							x: -2,
							y: -30,
							r: 4 + 3 * seg(u, .36, .5),
							c: c[0],
							c2: c[1],
							a: 1 - seg(u, .36, .5)
						});
						shot(p, u, .38, .78, [-2, -30], c, {
							h: 26,
							y1: -2,
							r: 3
						});
					}
				},
				breath: {
					zh: "火牆（噴吐）",
					type: "breath",
					ms: 1050,
					fn(p, u, e) {
						const c = elc(e.r, ELEM.fire);
						A$1(p, "head", {
							dx: kf(u, [
								[0, 0],
								[.25, -1.5],
								[.35, 2],
								[.85, 2],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.25, -.2],
								[.35, .1],
								[.85, .1],
								[1, 0]
							])
						});
						R(p, { dx: kf(u, [
							[0, 0],
							[.35, -1],
							[.85, -1],
							[1, 0]
						]) });
						if (u > .32 && u < .7) FX(p, {
							k: "cone",
							x: 22,
							y: -7,
							max: 22,
							spread: 5,
							len: seg(u, .32, .5),
							c: c[0],
							c2: c[1],
							a: 1 - seg(u, .6, .7),
							t: u * 12
						});
						if (u > .5) for (let i = 0; i < 4; i++) {
							const k = seg(u, .5 + i * .05, .62 + i * .05);
							if (k > 0) FX(p, {
								k: "flame",
								x: 34 + i * 6,
								y: 0,
								h: (9 + 3 * Math.sin(u * 30 + i)) * k * (1 - seg(u, .88, 1)),
								c: c[0],
								c2: c[1]
							});
						}
					}
				}
			},
			death(p, u) {
				p.flash = u < .12 ? .7 : 0;
				const k = sm(seg(u, .15, .6));
				A$1(p, "head", {
					dx: -3 * k,
					sx: 1 - .5 * k,
					rot: .3 * k
				});
				quadLegsTuck(p, .75 * k);
				R(p, {
					dy: 6.5 * k,
					rot: .08 * sm(seg(u, .55, .9)),
					pivot: [10, 0]
				});
				p.shadow = 1 - .2 * k;
			}
		},
		beetle: {
			kind: "crawler",
			mouth: [22, -14],
			units: "熔岩甲蟲、熔核領主",
			idle(p, u) {
				breathe(p, u, .02);
				A$1(p, "head", { rot: .06 * S$2(u, 2) });
				A$1(p, "N2", { kx: -.2 * Math.max(0, S$2(u, 1, .3)) });
			},
			move(p, u) {
				hexWalk(p, u, BT_TRI, {
					amp: .5,
					lift: .35,
					bob: .4
				});
				A$1(p, "head", { rot: .04 * S$2(u, 2) });
			},
			attacks: {
				horn: {
					zh: "角頂（stone_fist）",
					type: "melee",
					ms: 680,
					fn(p, u) {
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.3, -1],
								[.48, 5],
								[.62, 4],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.3, .1],
								[.48, .06],
								[.58, -.14],
								[.75, 0],
								[1, 0]
							]),
							pivot: [14, 0]
						});
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.3, .28],
							[.48, .15],
							[.58, -.55],
							[.8, 0],
							[1, 0]
						]) });
						slashFx(p, u, .52, .68, 30, -20, "#ffffff", 5);
					}
				},
				ram: {
					zh: "破城衝撞（衝鋒）",
					type: "charge",
					ms: 880,
					fn(p, u) {
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.3, -3],
								[.55, 14],
								[.62, 12.5],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.3, .05],
								[.55, .08],
								[.62, -.06],
								[.8, 0],
								[1, 0]
							]),
							pivot: [12, 0]
						});
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.3, .2],
							[.55, .2],
							[.62, -.25],
							[.85, 0],
							[1, 0]
						]) });
						if (u < .6) hexWalk(p, u * 3 % 1, BT_TRI, {
							amp: .5,
							lift: .35,
							bob: 0
						});
						if (u > .5 && u < .75) {
							FX(p, {
								k: "burst",
								x: 40,
								y: -10,
								r: 5 + 3 * seg(u, .5, .75),
								c: "#ffffff",
								c2: "#ffe08a",
								a: 1 - seg(u, .55, .75)
							});
							FX(p, {
								k: "dust",
								x: 4,
								y: -1,
								r: 3.5,
								a: 1 - seg(u, .5, .75)
							});
						}
					}
				},
				burst: {
					zh: "熔流潰堤（殼爆發）",
					type: "area",
					ms: 950,
					fn(p, u, e) {
						const c = elc(e.r, ELEM.fire);
						R(p, {
							sy: kf(u, [
								[0, 1],
								[.35, .88],
								[.45, 1.08],
								[.6, 1],
								[1, 1]
							]),
							sx: kf(u, [
								[0, 1],
								[.35, 1.04],
								[.45, 1.06],
								[.6, 1],
								[1, 1]
							]),
							dy: u < .35 ? .4 * Math.sign(Math.sin(u * 80)) * seg(u, .1, .35) : 0
						});
						quadLegsTuck(p, 0);
						for (const g of [
							"N0",
							"N1",
							"N2",
							"F0",
							"F1",
							"F2"
						]) A$1(p, g, { sy: 1 - .3 * bump(u, .1, .5) });
						p.flash = u > .2 && u < .42 ? .35 : 0;
						p.flashColor = c[0];
						if (u > .4) {
							const k = seg(u, .4, 1);
							FX(p, {
								k: "ring",
								x: 0,
								rx: 10 + 26 * k,
								c: c[0],
								a: 1 - k
							});
							FX(p, {
								k: "glow",
								x: 0,
								y: -12,
								r: 18 + 8 * k,
								c: c[0],
								a: (1 - k) * .8
							});
							for (let i = 0; i < 5; i++) {
								const an = -Math.PI * (.15 + .7 * (i / 4));
								const d = 8 + 20 * k;
								FX(p, {
									k: "orb",
									x: Math.cos(an) * d,
									y: -12 + Math.sin(an) * d * .8 + 18 * k * k,
									r: 1.6,
									c: c[0],
									c2: c[1],
									a: 1 - k
								});
							}
						}
					}
				}
			},
			death(p, u) {
				p.flash = u < .12 ? .7 : 0;
				const f = sm(seg(u, .15, .55));
				R(p, {
					sy: flipSy(f),
					dy: -7 * Math.sin(Math.PI * seg(u, .15, .55)),
					pivot: [0, -10]
				});
				A$1(p, "spikes", { sy: 1 - .85 * f });
				const kick = u > .55 ? Math.sin(u * 46) * (1 - seg(u, .55, .92)) : 0;
				[
					"N0",
					"N1",
					"N2",
					"F0",
					"F1",
					"F2"
				].forEach((g, i) => A$1(p, g, {
					kx: .4 * kick * (i % 2 ? 1 : -1),
					sy: 1 - .25 * f
				}));
				A$1(p, "head", { rot: .2 * f });
				p.shadow = 1 - .1 * f;
			}
		},
		spider: {
			kind: "crawler",
			mouth: [11, -6],
			units: "（目前沒有單位）",
			idle(p, u) {
				A$1(p, "abd", {
					sy: 1 + .04 * S$2(u, 1),
					sx: 1 + .02 * S$2(u, 1)
				});
				[
					"N0",
					"N1",
					"N2",
					"N3"
				].forEach((g, i) => A$1(p, g, { rot: .05 * S$2(u, 1, i * .25) }));
				A$1(p, "head", { rot: .04 * S$2(u, 2) });
			},
			move(p, u) {
				hexWalk(p, u, SP_TETRA, {
					amp: .32,
					lift: 2.2,
					bob: .6,
					rot: true
				});
				A$1(p, "abd", { rot: .05 * S$2(u, 2) });
			},
			attacks: { bite: {
				zh: "毒咬（前腳舉起撲咬）",
				type: "melee",
				ms: 720,
				fn(p, u) {
					R(p, {
						rot: kf(u, [
							[0, 0],
							[.35, -.22],
							[.5, .1],
							[.65, .05],
							[1, 0]
						]),
						pivot: [-14, 0],
						dx: kf(u, [
							[0, 0],
							[.35, -1],
							[.5, 6],
							[.62, 5],
							[1, 0]
						])
					});
					for (const g of ["N3", "F3"]) A$1(p, g, { rot: kf(u, [
						[0, 0],
						[.35, -.9],
						[.5, .25],
						[1, 0]
					]) });
					for (const g of ["N2", "F2"]) A$1(p, g, { rot: kf(u, [
						[0, 0],
						[.35, -.5],
						[.5, .15],
						[1, 0]
					]) });
					A$1(p, "head", {
						dx: 2 * bump(u, .4, .65),
						rot: .15 * bump(u, .4, .65)
					});
					if (u > .45 && u < .7) FX(p, {
						k: "burst",
						x: 20,
						y: -6,
						r: 3 + 2 * seg(u, .45, .7),
						c: "#7ddc3a",
						c2: "#d6f59a",
						a: 1 - seg(u, .45, .7)
					});
				}
			} },
			death(p, u) {
				p.flash = u < .12 ? .7 : 0;
				const f = sm(seg(u, .15, .5));
				const c = sm(seg(u, .45, .9));
				R(p, {
					sy: flipSy(f),
					dy: -6 * Math.sin(Math.PI * seg(u, .15, .5)),
					pivot: [-2, -10.5]
				});
				A$1(p, "spikes", { sy: 1 - .85 * f });
				[
					"N0",
					"N1",
					"N2",
					"N3"
				].forEach((g) => A$1(p, g, {
					rot: -.7 * c,
					sy: 1 - .3 * c
				}));
				[
					"F0",
					"F1",
					"F2",
					"F3"
				].forEach((g) => A$1(p, g, {
					rot: .7 * c,
					sy: 1 - .3 * c
				}));
			}
		},
		serpent: {
			kind: "serpent",
			mouth: [19, -25],
			units: "（目前沒有單位）",
			idle(p, u) {
				neck(p, .07 * S$2(u, 1), -.05 * S$2(u, 1));
				A$1(p, "coil", { sy: 1 + .03 * S$2(u, 1, .25) });
			},
			move(p, u) {
				A$1(p, "coil", {
					kx: .18 * S$2(u, 1),
					sx: 1 + .06 * S$2(u, 2)
				});
				neck(p, -.1 * S$2(u, 1, .2), .05 * S$2(u, 1, .4));
				R(p, { dx: .8 * S$2(u, 2) });
			},
			attacks: { strike: {
				zh: "突咬",
				type: "melee",
				ms: 620,
				fn(p, u) {
					neck(p, kf(u, [
						[0, 0],
						[.3, .32],
						[.45, -.48],
						[.58, -.42],
						[1, 0]
					]), kf(u, [
						[0, 0],
						[.3, -.3],
						[.45, .2],
						[1, 0]
					]));
					A$1(p, "coil", { kx: .1 * bump(u, .35, .7) });
					R(p, { dx: 2 * bump(u, .35, .7) });
					chompFx(p, u, .4, .58, 34, -24);
				}
			} },
			death(p, u) {
				p.flash = u < .12 ? .7 : 0;
				const k = sm(seg(u, .2, .8));
				A$1(p, "neck", {
					sy: 1 - .75 * k,
					kx: -.3 * k
				});
				A$1(p, "head", {
					dx: 6 * k,
					dy: 16 * k,
					rot: .25 * k
				});
				A$1(p, "coil", { sy: 1 - .15 * k });
			}
		},
		ooze: {
			kind: "ooze",
			mouth: [8, -10],
			units: "熔核蛞蝓",
			idle(p, u) {
				R(p, {
					sx: 1 + .04 * S$2(u, 1),
					sy: 1 - .04 * S$2(u, 1),
					kx: .04 * S$2(u, 1, .25)
				});
				A$1(p, "face", { dy: .5 * S$2(u, 1) });
			},
			move(p, u) {
				R(p, {
					kx: .12 * S$2(u, 1),
					sx: 1 + .1 * S$2(u, 1, .25),
					sy: 1 - .09 * S$2(u, 1, .25),
					dx: 1.2 * S$2(u, 1, .1)
				});
				A$1(p, "face", { dx: .8 * S$2(u, 1) });
			},
			attacks: {
				slam: {
					zh: "彈跳壓（stone_fist）",
					type: "melee",
					ms: 820,
					fn(p, u, e) {
						const air = seg(u, .3, .56);
						R(p, {
							sy: kf(u, [
								[0, 1],
								[.28, .7],
								[.36, 1.25],
								[.55, 1.1],
								[.62, .6],
								[.78, 1.08],
								[.9, .97],
								[1, 1]
							]),
							sx: kf(u, [
								[0, 1],
								[.28, 1.25],
								[.36, .85],
								[.55, .92],
								[.62, 1.4],
								[.78, .95],
								[1, 1]
							]),
							dx: kf(u, [
								[0, 0],
								[.3, 0],
								[.58, 8],
								[.75, 8],
								[1, 0]
							]),
							dy: u > .3 && u < .58 ? -12 * Math.sin(Math.PI * seg(u, .3, .58)) : 0
						});
						A$1(p, "face", { dy: kf(u, [
							[0, 0],
							[.28, 2],
							[.36, -2],
							[.62, 3],
							[1, 0]
						]) });
						if (u > .58 && u < .85) {
							const k = seg(u, .58, .85);
							FX(p, {
								k: "blob",
								x: -8 - 4 * k,
								y: -1,
								rx: 2.4,
								ry: 1.4,
								c: e.r.base,
								a: 1 - k
							});
							FX(p, {
								k: "blob",
								x: 24 + 4 * k,
								y: -1,
								rx: 2.4,
								ry: 1.4,
								c: e.r.base,
								a: 1 - k
							});
							FX(p, {
								k: "dust",
								x: 8,
								y: -1,
								r: 5,
								a: 1 - k
							});
						}
						p.shadow = 1 - .35 * Math.sin(Math.PI * air);
					}
				},
				spit: {
					zh: "燈油瓶（拋吐油團）",
					type: "cast",
					ms: 900,
					fn(p, u, e) {
						R(p, {
							sy: kf(u, [
								[0, 1],
								[.32, .8],
								[.42, 1.18],
								[.55, .96],
								[.7, 1],
								[1, 1]
							]),
							sx: kf(u, [
								[0, 1],
								[.32, 1.15],
								[.42, .88],
								[.55, 1.03],
								[1, 1]
							]),
							kx: kf(u, [
								[0, 0],
								[.32, -.08],
								[.42, .12],
								[.6, 0],
								[1, 0]
							])
						});
						A$1(p, "face", { dy: kf(u, [
							[0, 0],
							[.32, 1.5],
							[.42, -2],
							[.7, 0],
							[1, 0]
						]) });
						const oc = e.r.element !== void 0 ? elc(e.r, ELEM.fire)[0] : "#6a5640";
						const rim = e.r.element !== void 0 ? elc(e.r, ELEM.fire)[1] : "#d8c08a";
						const q = proj(u, .4, .74, 8, -16, 46, -2, 22);
						if (q !== null) FX(p, {
							k: "blob",
							x: q[0],
							y: q[1],
							r: 3.8,
							c: oc,
							rim,
							ranged: true
						});
						if (u > .74) {
							const k = seg(u, .74, 1);
							FX(p, {
								k: "blob",
								x: 46,
								y: 0,
								rx: 5 + 7 * k,
								ry: 1.6 + .6 * k,
								c: oc,
								rim,
								a: 1 - .2 * k,
								ranged: true
							});
							if (k < .7) FX(p, {
								k: "burst",
								x: 46,
								y: -3,
								r: 4 + 4 * k,
								c: oc,
								c2: rim,
								a: 1 - k / .7,
								ranged: true
							});
							for (let i = 0; i < 4; i++) {
								const dx = [
									-1,
									-.4,
									.5,
									1
								][i];
								FX(p, {
									k: "blob",
									x: 46 + dx * (4 + 9 * k),
									y: Math.min(-.5, -2 - (7 - 2 * Math.abs(dx)) * Math.sin(Math.PI * k)),
									r: 1.3,
									c: oc,
									rim,
									a: 1 - .6 * k,
									ranged: true
								});
							}
						}
					}
				}
			},
			death(p, u) {
				p.flash = u < .12 ? .7 : 0;
				const k = sm(seg(u, .1, .8));
				R(p, {
					sy: 1 - .68 * k + .08 * Math.sin(u * 30) * (1 - k),
					sx: 1 + .55 * k
				});
				A$1(p, "face", {
					dy: 5 * k,
					a: 1 - .7 * k
				});
				p.alpha = 1 - .3 * sm(seg(u, .5, 1));
			}
		},
		golem: {
			kind: "golem",
			mouth: [-1, -29],
			units: "晶傀儡、碎晶傀儡、焦岩巨像",
			idle(p, u) {
				breathe(p, u, .015);
				A$1(p, "armN", { rot: -.04 * S$2(u, 1) });
				A$1(p, "armF", { rot: .04 * S$2(u, 1) });
				A$1(p, "head", { rot: .04 * S$2(u, 1, .3) });
			},
			move(p, u) {
				[["legN", 0], ["legF", .5]].forEach(([g, ph]) => A$1(p, g, {
					kx: -.28 * S$2(u, 1, ph),
					sy: 1 - .18 * Math.max(0, Cn(u, 1, ph))
				}));
				R(p, {
					dy: -.9 * Math.abs(Cn(u, 1, .25)),
					rot: .03 * S$2(u, 1)
				});
				A$1(p, "armN", { rot: .22 * S$2(u, 1, .5) });
				A$1(p, "armF", { rot: .22 * S$2(u, 1) });
				A$1(p, "head", { rot: .03 * S$2(u, 2) });
			},
			attacks: {
				smash: {
					zh: "拳砸（stone_fist／碎岩擊）",
					type: "melee",
					ms: 920,
					fn(p, u) {
						A$1(p, "armN", { rot: kf(u, [
							[0, 0],
							[.4, -2.7],
							[.55, -.75],
							[.7, -.7],
							[1, 0]
						]) });
						A$1(p, "armF", { rot: kf(u, [
							[0, 0],
							[.4, .4],
							[.55, -.2],
							[1, 0]
						]) });
						R(p, {
							rot: kf(u, [
								[0, 0],
								[.4, -.09],
								[.55, .13],
								[.7, .1],
								[1, 0]
							]),
							pivot: [-3, 0],
							dx: kf(u, [
								[0, 0],
								[.4, -1],
								[.55, 3],
								[1, 0]
							]),
							dy: u > .55 && u < .65 ? .6 * Math.sign(Math.sin(u * 120)) : 0
						});
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.4, -.12],
							[.55, .15],
							[1, 0]
						]) });
						if (u > .53) {
							const k = seg(u, .53, .85);
							if (k < 1) {
								FX(p, {
									k: "burst",
									x: 27,
									y: -4,
									r: 4 + 3 * k,
									c: "#ffffff",
									c2: "#e8dcc8",
									a: 1 - k
								});
								FX(p, {
									k: "dust",
									x: 27,
									y: -1,
									r: 4 + 2 * k,
									a: 1 - k
								});
							}
						}
					}
				},
				quake: {
					zh: "雙拳震地（震地波）",
					type: "area",
					ms: 1100,
					fn(p, u, e) {
						A$1(p, "armN", { rot: kf(u, [
							[0, 0],
							[.42, -3.05],
							[.55, -.95],
							[.75, -.9],
							[1, 0]
						]) });
						A$1(p, "armF", {
							rot: kf(u, [
								[0, 0],
								[.42, -3.3],
								[.55, -.85],
								[.75, -.8],
								[1, 0]
							]),
							dx: kf(u, [
								[0, 0],
								[.42, 0],
								[.55, 16],
								[.75, 16],
								[1, 0]
							])
						});
						R(p, {
							rot: kf(u, [
								[0, 0],
								[.42, -.14],
								[.55, .2],
								[.75, .16],
								[1, 0]
							]),
							pivot: [-3, 0],
							dy: kf(u, [
								[0, 0],
								[.42, -2.5],
								[.55, 1],
								[.75, .6],
								[1, 0]
							]) + (u > .55 && u < .68 ? .7 * Math.sign(Math.sin(u * 120)) : 0)
						});
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.42, -.15],
							[.55, .2],
							[1, 0]
						]) });
						if (u > .55) {
							const k = seg(u, .55, 1);
							for (let i = 0; i < 4; i++) {
								const q = cl(k * 1.6 - i * .18);
								if (q > 0 && q < 1) FX(p, {
									k: "rock",
									x: 24 + i * 10,
									y: 0,
									s: 2.6 * Math.sin(Math.PI * q) + .5,
									c: e.r.mat === "crystal" ? "#b8a8ff" : "#8a847e"
								});
							}
							FX(p, {
								k: "dust",
								x: 24 + 30 * k,
								y: -1,
								r: 3 + 2 * k,
								a: 1 - k
							});
						}
						quakeFx(p, u, .55, 22);
					}
				},
				cast: {
					zh: "核心聚雷（從胸口放出）",
					type: "cast",
					ms: 920,
					fn(p, u, e) {
						const c = e.r.element !== void 0 ? elc(e.r, ELEM.lightning) : ELEM.lightning;
						A$1(p, "armN", { rot: kf(u, [
							[0, 0],
							[.4, .7],
							[.55, -.9],
							[.8, -.6],
							[1, 0]
						]) });
						A$1(p, "armF", { rot: kf(u, [
							[0, 0],
							[.4, .6],
							[.55, -.3],
							[1, 0]
						]) });
						R(p, {
							rot: kf(u, [
								[0, 0],
								[.4, -.06],
								[.55, .04],
								[1, 0]
							]),
							pivot: [0, 0]
						});
						charge(p, u, .1, .46, [1, -29], c, 3.2);
						if (u > .48 && u < .72) {
							FX(p, {
								k: "bolt",
								x0: 3,
								y0: -29,
								x1: TGT,
								y1: -14,
								c: c[0],
								amp: 1 + .6 * Math.sin(u * 60),
								ranged: true
							});
							FX(p, {
								k: "glow",
								x: TGT,
								y: -14,
								r: 10,
								c: c[0],
								a: 1 - seg(u, .48, .72) * .6,
								ranged: true
							});
						}
					}
				}
			},
			death(p, u) {
				p.flash = u < .12 ? .7 : 0;
				const sh = u < .25 ? .6 * Math.sign(Math.sin(u * 120)) : 0;
				const k = sm(seg(u, .22, .72));
				const k2 = sm(seg(u, .3, .8));
				R(p, { dx: sh });
				p.split = { body: [
					{
						clip: GOLEM_LEFT,
						pivot: [-6, -16],
						dx: -3 * k,
						dy: 13 * k,
						rot: -.35 * k
					},
					{
						clip: GOLEM_RIGHT,
						pivot: [6, -16],
						dx: 5 * k,
						dy: 13 * k,
						rot: .5 * k
					},
					{
						clip: GOLEM_TOP,
						pivot: [-2, -31],
						dx: -1 * k2 + .5 * bump(u, .7, .85),
						dy: 24 * k2 - 2 * bump(u, .78, .9),
						rot: -.25 * k2
					}
				] };
				const roll = sm(seg(u, .25, .95));
				A$1(p, "head", {
					dy: 27 * sm(seg(u, .25, .6)) - 4 * bump(u, .6, .75),
					dx: -15 * roll,
					rot: -(1.6 + TAU$2) * roll
				});
				A$1(p, "armN", {
					dy: 30 * sm(seg(u, .3, .7)),
					dx: 0,
					rot: -1.5 * sm(seg(u, .3, .78))
				});
				A$1(p, "armF", {
					dy: 17 * sm(seg(u, .28, .68)),
					dx: -3 * k,
					rot: .55 * k
				});
				for (const g of ["legN", "legF"]) A$1(p, g, { sy: 1 - .6 * k });
				A$1(p, "legN", { rot: .25 * k });
				A$1(p, "legF", { rot: -.25 * k });
				if (u > .62 && u < 1) {
					FX(p, {
						k: "dust",
						x: -2,
						y: -1,
						r: 6,
						a: 1 - seg(u, .62, 1)
					});
					FX(p, {
						k: "dust",
						x: 24,
						y: -1,
						r: 3.5,
						a: 1 - seg(u, .7, 1)
					});
				}
			}
		},
		wisp: {
			kind: "wisp",
			mouth: [0, -20],
			units: "（灰燼之心另有頭目畫法）",
			idle(p, u) {
				R(p, { dy: -2 * S$2(u, 1) });
				A$1(p, "core", {
					sx: 1 + .04 * S$2(u, 2),
					sy: 1 + .04 * S$2(u, 2)
				});
				ORB_HOME.forEach((_, i) => A$1(p, `orb${i}`, {
					dx: 2 * Cn(u, 1, i / 3),
					dy: 1.4 * S$2(u, 1, i / 3)
				}));
			},
			move(p, u) {
				R(p, {
					dy: -1.5 - 1.5 * S$2(u, 1),
					rot: .1
				});
				ORB_HOME.forEach((_, i) => A$1(p, `orb${i}`, {
					dx: -2.5 + 1.5 * Cn(u, 1, i / 3),
					dy: 1.2 * S$2(u, 1, i / 3)
				}));
			},
			attacks: {
				shards: {
					zh: "晶刺射出（從核心）",
					type: "cast",
					ms: 880,
					fn(p, u, e) {
						R(p, { dy: -1.5 * S$2(u, 1) });
						ORB_HOME.forEach(([hx, hy], i) => {
							const fx = 13 - hx;
							const fy = -3 + (i - 1) * 4 - hy;
							const g = seg(u, .05 + i * .05, .35 + i * .05);
							const fly = seg(u, .42 + i * .06, .62 + i * .06);
							const back = seg(u, .78, 1);
							if (fly >= 1) A$1(p, `orb${i}`, {
								a: back,
								sx: .4 + .6 * back,
								sy: .4 + .6 * back
							});
							else A$1(p, `orb${i}`, {
								dx: fx * sm(g) + 39 * fly,
								dy: fy * sm(g),
								rot: .6 * g + .97 * (fly > 0 ? 1 : 0)
							});
							if (u > .62 + i * .06 && u < .78 + i * .06) FX(p, {
								k: "burst",
								x: TGT,
								y: -20 + (i - 1) * 4,
								r: 4,
								c: e.r.base,
								c2: "#ffffff",
								a: 1 - seg(u, .62 + i * .06, .78 + i * .06),
								ranged: true
							});
						});
						A$1(p, "core", {
							sx: 1 + .15 * bump(u, .3, .55),
							sy: 1 + .15 * bump(u, .3, .55)
						});
					}
				},
				pulse: {
					zh: "晶脈衝（範圍爆發）",
					type: "area",
					ms: 940,
					fn(p, u, e) {
						const k = kf(u, [
							[0, 0],
							[.35, -.25],
							[.48, .3],
							[.7, .05],
							[1, 0]
						]);
						A$1(p, "core", {
							sx: 1 + k,
							sy: 1 + k
						});
						ORB_HOME.forEach(([hx, hy], i) => A$1(p, `orb${i}`, {
							dx: hx * k * 2.2,
							dy: hy * k * 2.2
						}));
						R(p, { dy: -1 * S$2(u, 1) });
						p.flash = u > .42 && u < .52 ? .5 : 0;
						p.flashColor = e.r.accent ?? "#ffffff";
						if (u > .45) {
							const q = seg(u, .45, 1);
							FX(p, {
								k: "ring",
								x: 0,
								rx: 8 + 30 * q,
								c: e.r.base,
								a: 1 - q
							});
							FX(p, {
								k: "glow",
								x: 0,
								y: -20,
								r: 16 + 10 * q,
								c: e.r.base,
								a: 1 - q
							});
						}
					}
				}
			},
			death(p, u, e) {
				p.flash = u < .2 ? .9 : 0;
				const k = seg(u, .18, .4);
				A$1(p, "core", {
					sx: 1 - .85 * sm(k),
					sy: 1 - .85 * sm(k),
					a: 1 - sm(k),
					rot: .6 * k
				});
				ORB_HOME.forEach(([hx, hy], i) => {
					const f = seg(u, .2, .75);
					A$1(p, `orb${i}`, {
						dx: hx * .8 * f,
						dy: (20 - hy - 2.4) * f * f - 8 * Math.sin(Math.PI * f) * (1 - f),
						rot: (i - 1) * 2 * f + 1.57 * sm(f)
					});
				});
				R(p, { dy: 0 });
				p.shadow = 1 - .6 * sm(seg(u, .2, .6));
				if (u > .2) for (let i = 0; i < 6; i++) {
					const an = -Math.PI * (.1 + .8 * (i / 5));
					const f = seg(u, .2, .8);
					const d = 4 + 16 * f;
					FX(p, {
						k: "shard",
						x: Math.cos(an) * d * (i % 2 ? 1 : .7),
						y: Math.min(-1.5, -20 + Math.sin(an) * d * .6 + 26 * f * f),
						rot: an + f * 4 * (i % 2 ? 1 : -1),
						s: 1.8,
						c: lighten(e.r.base, .2)
					});
				}
			}
		},
		wraith: {
			kind: "wraith",
			mouth: [2, -42],
			units: "霧魅、熔晶魅",
			idle(p, u) {
				R(p, { dy: -1.5 * S$2(u, 1) });
				A$1(p, "body", { kx: .06 * S$2(u, 1, .2) });
				A$1(p, "armN", { rot: .1 * S$2(u, 1, .1) });
				A$1(p, "armB", { rot: .1 * S$2(u, 1, .35) });
				A$1(p, "head", { rot: .05 * S$2(u, 1, .5) });
			},
			move(p, u) {
				R(p, {
					dy: -1.5 - 1 * S$2(u, 2),
					rot: .08
				});
				A$1(p, "body", { kx: .12 + .05 * S$2(u, 1) });
				A$1(p, "armN", { rot: .35 + .08 * S$2(u, 1) });
				A$1(p, "armB", { rot: .4 + .08 * S$2(u, 1, .3) });
			},
			attacks: {
				claw: {
					zh: "影刃爪（shade_blades）",
					type: "melee",
					ms: 680,
					fn(p, u, e) {
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.3, -2],
								[.5, 7],
								[.65, 6],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.3, -.06],
								[.5, .14],
								[1, 0]
							]),
							pivot: [0, -20]
						});
						A$1(p, "armN", { rot: kf(u, [
							[0, 0],
							[.3, 1],
							[.5, -1.5],
							[.65, -1.2],
							[1, 0]
						]) });
						A$1(p, "armB", { rot: kf(u, [
							[0, 0],
							[.35, .9],
							[.58, -1.2],
							[.72, -1],
							[1, 0]
						]) });
						A$1(p, "body", { kx: kf(u, [
							[0, 0],
							[.3, -.1],
							[.5, .2],
							[1, 0]
						]) });
						slashFx(p, u, .45, .65, 30, -26, e.r.element !== void 0 ? elc(e.r, ELEM.shadow)[0] : "#c8a8f0", 7);
					}
				},
				blink: {
					zh: "閃現（淡出→淡入）",
					type: "blink",
					ms: 900,
					fn(p, u, e) {
						const v = sm(seg(u, .05, .38)) * (1 - sm(seg(u, .58, .9)));
						R(p, {
							sx: 1 - .6 * v,
							sy: 1 + .35 * v,
							dy: -4 * v
						});
						p.alpha = 1 - v;
						for (let i = 0; i < 4; i++) {
							const an = i / 4 * TAU$2 + u * 6;
							const q = u < .5 ? seg(u, .1, .45) : seg(u, .55, .9);
							FX(p, {
								k: "puff",
								x: Math.cos(an) * (6 + 6 * q),
								y: -20 + Math.sin(an) * 9,
								r: 3.6 * (1 - q * .5),
								c: e.r.base,
								a: Math.sin(Math.PI * q)
							});
						}
					}
				},
				gaze: {
					zh: "威懾凝視（眼放恐懼波）",
					type: "cast",
					ms: 900,
					fn(p, u, e) {
						const c = e.r.element !== void 0 ? elc(e.r, ELEM.shadow) : ELEM.shadow;
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.35, 2],
								[.8, 2],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.35, .06],
								[.8, .06],
								[1, 0]
							]),
							pivot: [0, -20]
						});
						A$1(p, "head", {
							dx: kf(u, [
								[0, 0],
								[.35, 1.5],
								[.8, 1.5],
								[1, 0]
							]),
							sx: 1 + .12 * bump(u, .3, .8),
							sy: 1 + .12 * bump(u, .3, .8)
						});
						A$1(p, "armN", { rot: kf(u, [
							[0, 0],
							[.35, -.6],
							[.8, -.5],
							[1, 0]
						]) });
						A$1(p, "armB", { rot: kf(u, [
							[0, 0],
							[.35, .6],
							[.8, .5],
							[1, 0]
						]) });
						if (u > .3 && u < .5) FX(p, {
							k: "glow",
							x: 3,
							y: -42,
							r: 8,
							c: c[1],
							a: bump(u, .3, .5)
						});
						for (let i = 0; i < 3; i++) {
							const q = seg(u, .38 + i * .1, .72 + i * .1);
							if (q > 0 && q < 1) FX(p, {
								k: "wave",
								x: 6 + 46 * q,
								y: -42 + 26 * q,
								r: 3 + 5 * q,
								c: c[0],
								a: 1 - q * .6,
								ranged: true
							});
						}
					}
				}
			},
			death(p, u, e) {
				p.flash = u < .15 ? .8 : 0;
				const k = sm(seg(u, .1, .9));
				R(p, {
					dy: -7 * k,
					sx: 1 - .45 * k,
					sy: 1 + .4 * k
				});
				A$1(p, "body", { kx: .2 * Math.sin(u * 14) * k });
				A$1(p, "armN", { rot: .8 * k });
				A$1(p, "armB", { rot: .7 * k });
				p.alpha = 1 - k;
				p.shadow = 1 - k;
				for (let i = 0; i < 5; i++) {
					const q = seg(u, .15 + i * .08, .75 + i * .05);
					if (q > 0 && q < 1) FX(p, {
						k: "puff",
						x: (i - 2) * 5,
						y: -12 - i * 6 - 12 * q,
						r: 3 + 2 * q,
						c: e.r.base,
						a: 1 - q
					});
				}
			}
		},
		pylon: {
			kind: "pylon",
			mouth: [2, -22],
			units: "火／霧／雷之源晶柱、陣眼石靈",
			idle(p, u) {
				A$1(p, "ring", {
					dy: 1.2 * S$2(u, 1),
					sx: 1 + .05 * S$2(u, 2)
				});
				A$1(p, "eye", { sy: u > .82 && u < .92 ? .25 : 1 });
				A$1(p, "ob", { sy: 1 + .01 * S$2(u, 1) });
			},
			move(p, u) {
				const lift = -2.5 - .8 * S$2(u, 1);
				for (const g of [
					"ob",
					"eye",
					"ring"
				]) A$1(p, g, {
					dy: lift,
					rot: .05 * S$2(u, 1, .25),
					pivot: [0, -5]
				});
				A$1(p, "ring", { sx: 1 + .06 * S$2(u, 2) });
				p.shadow = .85;
			},
			attacks: {
				beam: {
					zh: "晶射線（fist 普攻）",
					type: "cast",
					ms: 920,
					fn(p, u, e) {
						const c = e.r.element !== void 0 ? elc(e.r, ELEM.lightning) : [e.r.accent ?? "#e4dcff", "#ffffff"];
						A$1(p, "ring", {
							sx: kf(u, [
								[0, 1],
								[.38, .6],
								[.5, 1.2],
								[.8, 1.1],
								[1, 1]
							]),
							dy: kf(u, [
								[0, 0],
								[.38, -3],
								[.5, 1],
								[1, 0]
							])
						});
						A$1(p, "eye", {
							sx: 1 + .4 * bump(u, .1, .8),
							sy: 1 + .4 * bump(u, .1, .8)
						});
						for (const g of [
							"ob",
							"eye",
							"ring"
						]) A$1(p, g, { dx: u > .45 && u < .75 ? -.8 : 0 });
						charge(p, u, .1, .42, [3, -22], c, 2.6);
						if (u > .44 && u < .78) {
							FX(p, {
								k: "beam",
								x0: 4,
								y0: -22,
								x1: TGT,
								y1: -16,
								w: 3.2 * (1 - .6 * seg(u, .65, .78)),
								c: c[0],
								ranged: true
							});
							FX(p, {
								k: "glow",
								x: TGT,
								y: -16,
								r: 9,
								c: c[0],
								a: .8,
								ranged: true
							});
						}
					}
				},
				pulse: {
					zh: "晶脈衝（自身範圍）",
					type: "area",
					ms: 960,
					fn(p, u, e) {
						const c = e.r.element !== void 0 ? elc(e.r, ELEM.fire) : [e.r.base, "#ffffff"];
						A$1(p, "ring", {
							sx: kf(u, [
								[0, 1],
								[.35, .7],
								[.5, 1.9],
								[.75, 1.3],
								[1, 1]
							]),
							a: kf(u, [
								[0, 1],
								[.5, .6],
								[.75, .3],
								[1, 1]
							]),
							dy: kf(u, [
								[0, 0],
								[.35, -4],
								[.5, 0],
								[1, 0]
							])
						});
						p.flash = u > .4 && u < .52 ? .5 : 0;
						p.flashColor = c[0];
						if (u > .45) for (const d of [0, .15]) {
							const q = seg(u, .45 + d, 1);
							if (q > 0 && q < 1) FX(p, {
								k: "ring",
								x: 0,
								rx: 10 + 30 * q,
								c: c[0],
								a: 1 - q
							});
						}
						if (u > .4 && u < .7) FX(p, {
							k: "glow",
							x: 0,
							y: -22,
							r: 16,
							c: c[0],
							a: bump(u, .4, .7)
						});
					}
				}
			},
			death(p, u, e) {
				p.flash = u < .2 ? .8 : 0;
				const j = u < .28 ? .7 * Math.sign(Math.sin(u * 100)) : 0;
				const f = sm(seg(u, .25, .68)) - .06 * bump(u, .68, .8);
				R(p, {
					dx: j,
					rot: 1.42 * f,
					pivot: [5, -5]
				});
				A$1(p, "base", {
					dx: -j,
					rot: -1.42 * f,
					pivot: [5, -5]
				});
				A$1(p, "eye", { a: 1 - .7 * seg(u, .3, .7) });
				A$1(p, "ring", { a: 1 - seg(u, .25, .5) });
				if (u > .66) {
					const k = seg(u, .66, 1);
					FX(p, {
						k: "dust",
						x: 22,
						y: -1,
						r: 5,
						a: 1 - k
					});
					for (let i = 0; i < 4; i++) FX(p, {
						k: "shard",
						x: 14 + i * 7 + 4 * k * (i - 1.5),
						y: Math.min(-1.5, -6 - 6 * Math.sin(Math.PI * k) + i),
						rot: i + 3 * k,
						s: 1.6,
						c: lighten(e.r.base, .2)
					});
				}
			}
		},
		bird: {
			kind: "flyer",
			mouth: [17, -21],
			units: "雷羽鷹",
			idle(p, u) {
				R(p, { dy: 9 });
				p.shadow = 1;
				const sh = u >= .55 && u < .8 ? Math.abs(Math.sin(TAU$2 * seg(u, .55, .8))) : 0;
				A$1(p, "wingN", {
					sy: -.42 - .2 * sh,
					rot: 2.1 + .75 * sh
				});
				A$1(p, "wingF", {
					sy: -.38 - .2 * sh,
					rot: .3 + .5 * sh
				});
				R(p, { dy: -.6 * sh });
				A$1(p, "head", { rot: .07 * S$2(u, 1, .3) });
				A$1(p, "tail", { rot: .06 * S$2(u, 1) + .1 * sh });
			},
			move(p, u) {
				flap(p, u, {
					bob: 2.2,
					dn: -.6,
					base: -6
				});
				R(p, { rot: .08 });
				A$1(p, "tail", { rot: .08 * S$2(u, 1) });
				A$1(p, "legs", { rot: .5 });
			},
			attacks: {
				rake: {
					zh: "爪擊（talons）",
					type: "melee",
					ms: 700,
					fn(p, u) {
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.3, -2],
								[.52, 8],
								[.68, 6],
								[1, 0]
							]),
							dy: kf(u, [
								[0, 0],
								[.3, -6],
								[.52, 3],
								[.68, 1],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.3, -.15],
								[.52, -.3],
								[1, 0]
							])
						});
						const w = kf(u, [
							[0, 1],
							[.3, 1.15],
							[.52, -.3],
							[.7, .4],
							[1, 1]
						]);
						A$1(p, "wingN", { sy: w });
						A$1(p, "wingF", { sy: w });
						A$1(p, "legs", { rot: kf(u, [
							[0, 0],
							[.3, -.4],
							[.5, -1.35],
							[.68, -.8],
							[1, 0]
						]) });
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.5, .2],
							[1, 0]
						]) });
						slashFx(p, u, .48, .65, 26, -10, "#ffffff", 6);
					}
				},
				dive: {
					zh: "俯衝斬（衝鋒）",
					type: "charge",
					ms: 920,
					fn(p, u) {
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.35, -5],
								[.58, 15],
								[.7, 14],
								[1, 0]
							]),
							dy: kf(u, [
								[0, 0],
								[.35, -14],
								[.58, 6],
								[.7, 4],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.35, -.25],
								[.45, .55],
								[.58, .45],
								[.72, -.2],
								[1, 0]
							])
						});
						const w = u < .35 ? 1.05 - 1.6 * Math.max(0, S$2(u / .35, 2)) : kf(u, [
							[.35, 1],
							[.42, .25],
							[.58, .25],
							[.7, -.25],
							[.85, 1],
							[1, 1]
						]);
						A$1(p, "wingN", {
							sy: w,
							rot: u > .38 && u < .6 ? .5 : 0
						});
						A$1(p, "wingF", {
							sy: w,
							rot: u > .38 && u < .6 ? .5 : 0
						});
						A$1(p, "legs", { rot: kf(u, [
							[0, 0],
							[.45, .4],
							[.56, -1.2],
							[.72, -.5],
							[1, 0]
						]) });
						slashFx(p, u, .55, .72, 33, -6, "#ffffff", 7);
						if (u > .55 && u < .8) FX(p, {
							k: "dust",
							x: 30,
							y: -1,
							r: 3.5,
							a: 1 - seg(u, .55, .8)
						});
						p.shadow = 1 - .3 * bump(u, .1, .45);
					}
				},
				cast: {
					zh: "靜電掌（翅尖放電）",
					type: "cast",
					ms: 880,
					fn(p, u, e) {
						const c = elc(e.r, ELEM.lightning);
						const w = kf(u, [
							[0, 1],
							[.38, 1.25],
							[.52, -.55],
							[.7, -.3],
							[1, 1]
						]);
						A$1(p, "wingN", { sy: w });
						A$1(p, "wingF", { sy: w });
						R(p, {
							dy: kf(u, [
								[0, 0],
								[.38, 2],
								[.52, -4],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.38, -.1],
								[.52, .12],
								[1, 0]
							])
						});
						if (u > .1 && u < .5) for (const [x, y] of [[17, -51], [-19, -47]]) FX(p, {
							k: "bolt",
							x0: x - 2,
							y0: y,
							x1: x + 2,
							y1: y + 5,
							c: c[0],
							amp: .5 * Math.sin(u * 50)
						});
						if (u > .5 && u < .72) {
							FX(p, {
								k: "bolt",
								x0: 12,
								y0: -22,
								x1: 36,
								y1: -14,
								c: c[0],
								amp: 1 + .5 * Math.sin(u * 70),
								ranged: true
							});
							FX(p, {
								k: "glow",
								x: 36,
								y: -14,
								r: 10,
								c: c[0],
								a: 1 - seg(u, .5, .72) * .5,
								ranged: true
							});
						}
					}
				}
			},
			death(p, u) {
				p.flash = u < .15 ? .8 : 0;
				const fall = sm(seg(u, .2, .7));
				const j = bump(u, 0, .25);
				R(p, {
					dy: -3 * j + 11 * fall - 1.2 * bump(u, .7, .82),
					rot: -.2 * j + .22 * fall,
					dx: 3 * fall,
					pivot: [0, -18]
				});
				p.softGround = true;
				const w = 1 - .75 * fall;
				A$1(p, "wingN", {
					sy: w,
					rot: .3 * fall
				});
				A$1(p, "wingF", {
					sy: w * .8,
					rot: .2 * fall
				});
				A$1(p, "head", { rot: .5 * sm(seg(u, .6, .95)) });
				A$1(p, "legs", { rot: -.8 * fall });
				p.shadow = 1;
				if (u > .68 && u < .95) FX(p, {
					k: "dust",
					x: 4,
					y: -1,
					r: 4,
					a: 1 - seg(u, .68, .95)
				});
			}
		},
		bat: {
			kind: "flyer",
			mouth: [8, -21],
			units: "火塵蝠",
			idle(p, u) {
				R(p, { dy: -1.6 * S$2(u, 2) });
				flap(p, u * 2 % 1, {
					up: 1,
					dn: .55,
					bob: .6
				});
				A$1(p, "head", { rot: .06 * S$2(u, 1) });
			},
			move(p, u) {
				flap(p, u, {
					bob: 2,
					dn: -.7
				});
				R(p, { rot: .1 });
			},
			attacks: {
				fire: {
					zh: "火焰箭（fire_staff 普攻＋技能，口吐）",
					type: "cast",
					ms: 800,
					fn(p, u, e) {
						const c = elc(e.r, ELEM.fire);
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.35, -3],
								[.48, 2],
								[1, 0]
							]),
							dy: kf(u, [
								[0, 0],
								[.35, -3],
								[.48, 0],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.35, -.2],
								[.48, .15],
								[1, 0]
							])
						});
						flap(p, u * 2 % 1, { bob: .8 });
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.35, -.35],
							[.48, .25],
							[1, 0]
						]) });
						charge(p, u, .08, .42, [10, -24], c, 2.2);
						shot(p, u, .44, .66, [12, -22], c, {
							r: 2.4,
							y1: -16
						});
					}
				},
				bite: {
					zh: "撲咬",
					type: "melee",
					ms: 660,
					fn(p, u) {
						R(p, {
							dx: kf(u, [
								[0, 0],
								[.25, -3],
								[.5, 10],
								[.65, 9],
								[1, 0]
							]),
							dy: kf(u, [
								[0, 0],
								[.25, -4],
								[.5, 3],
								[1, 0]
							]),
							rot: kf(u, [
								[0, 0],
								[.25, -.15],
								[.5, .3],
								[1, 0]
							])
						});
						const w = kf(u, [
							[0, 1],
							[.25, 1.1],
							[.45, .35],
							[.6, -.5],
							[.8, 1],
							[1, 1]
						]);
						A$1(p, "wingN", { sy: w });
						A$1(p, "wingF", { sy: w });
						A$1(p, "head", { rot: kf(u, [
							[0, 0],
							[.3, -.3],
							[.5, .3],
							[1, 0]
						]) });
						chompFx(p, u, .42, .62, 25, -20);
					}
				}
			},
			death(p, u) {
				p.flash = u < .15 ? .8 : 0;
				const fall = sm(seg(u, .18, .65));
				R(p, {
					dy: -2 * bump(u, 0, .2) + 7.6 * fall - 1 * bump(u, .65, .78),
					rot: .4 * fall,
					pivot: [0, -18]
				});
				p.softGround = true;
				A$1(p, "wingN", {
					sy: 1 - .7 * fall,
					rot: .35 * fall
				});
				A$1(p, "wingF", { sy: 1 - .6 * fall });
				A$1(p, "head", { rot: .4 * fall });
				if (u > .64 && u < .92) FX(p, {
					k: "dust",
					x: 0,
					y: -1,
					r: 3.5,
					a: 1 - seg(u, .64, .92)
				});
			}
		}
	};
	var IDLE_MS = {
		hound: 2200,
		boar: 2e3,
		bear: 2400,
		feline: 2200,
		lizard: 2200,
		shell: 2400,
		beetle: 2e3,
		spider: 2e3,
		serpent: 2200,
		ooze: 2e3,
		golem: 2400,
		wisp: 2e3,
		wraith: 2400,
		pylon: 2400,
		bird: 2e3,
		bat: 2e3
	};
	var MOVE_MS = {
		hound: 640,
		boar: 560,
		bear: 820,
		feline: 640,
		lizard: 560,
		shell: 960,
		beetle: 520,
		spider: 480,
		serpent: 720,
		ooze: 760,
		golem: 960,
		wisp: 800,
		wraith: 900,
		pylon: 1e3,
		bird: 520,
		bat: 360
	};
	var DEATH_MS = 1e3;
	var FPS_MS = 1e3 / 12;
	function creatureClipInfo(key, clip) {
		const B = BODY_ANIM[key];
		if (B === void 0) return null;
		const single = (ms) => Math.max(2, Math.round(ms / FPS_MS));
		if (clip === "idle") return {
			ms: IDLE_MS[key] ?? 2e3,
			loop: true,
			zh: "待機",
			n: 8
		};
		if (clip === "move") return {
			ms: MOVE_MS[key] ?? 700,
			loop: true,
			zh: "移動",
			n: 8
		};
		if (clip === "hit") return {
			ms: 400,
			loop: false,
			zh: "受擊",
			n: single(400)
		};
		if (clip === "death") return {
			ms: DEATH_MS,
			loop: false,
			zh: "倒下",
			n: single(DEATH_MS)
		};
		const a = clip.startsWith("atk:") ? B.attacks[clip.slice(4)] : void 0;
		return a === void 0 ? null : {
			ms: a.ms,
			loop: false,
			zh: a.zh,
			type: a.type,
			n: single(a.ms)
		};
	}
	/** 這款身形中某個動作類型的攻擊片段（沒有那個類型 → 依序退回普攻、第一個攻擊）。 */
	function attackClipFor(key, type) {
		const B = BODY_ANIM[key];
		if (B === void 0) return null;
		const list = Object.entries(B.attacks);
		for (const t of {
			melee: ["melee", "charge"],
			melee2: [
				"melee2",
				"melee",
				"charge"
			],
			charge: ["charge", "melee"],
			breath: [
				"breath",
				"cast",
				"area"
			],
			cast: [
				"cast",
				"breath",
				"melee"
			],
			area: [
				"area",
				"cast",
				"melee"
			],
			summon: [
				"summon",
				"cast",
				"area"
			],
			blink: ["blink", "melee"]
		}[type]) {
			const hit = list.find(([, a]) => a.type === t);
			if (hit !== void 0) return `atk:${hit[0]}`;
		}
		return list[0] === void 0 ? null : `atk:${list[0][0]}`;
	}
	/** 待機落地（比飛行低）、移動在空中的身形：移動開頭與結尾約 4 格從落地姿勢過渡（perch 1＝落地、0＝飛行）。 */
	var PERCHERS = /* @__PURE__ */ new Set(["bird"]);
	/** 鳥待機抖翅張最開的那一刻（idle 的 u；過場的半開翅膀用）。 */
	var PERCH_SPREAD_U = .6125;
	var XF_KEYS = [
		"rot",
		"dx",
		"dy",
		"kx",
		"sx",
		"sy",
		"a"
	];
	function blendXf(a, b, k) {
		const out = {};
		for (const key of XF_KEYS) {
			const d = key === "sx" || key === "sy" || key === "a" ? 1 : 0;
			const va = a?.[key] ?? d;
			const vb = b?.[key] ?? d;
			if (va !== d || vb !== d) out[key] = va + (vb - va) * k;
		}
		const pv = (k < .5 ? a?.pivot : b?.pivot) ?? a?.pivot ?? b?.pivot;
		if (pv !== void 0) out.pivot = pv;
		return out;
	}
	/** 兩個姿勢逐欄內插（k 0＝a、1＝b）；特效取 a。 */
	function blendPose(a, b, k) {
		const parts = {};
		for (const g of [.../* @__PURE__ */ new Set([...Object.keys(a.parts), ...Object.keys(b.parts)])].sort()) parts[g] = blendXf(a.parts[g], b.parts[g], k);
		return {
			...a,
			root: blendXf(a.root, b.root, k),
			parts,
			shadow: a.shadow + (b.shadow - a.shadow) * k
		};
	}
	/** 片段在 u 的分部件姿勢。reduce：減少動態（待機、移動 → null；受擊只白閃；倒下最後一格；攻擊只往前推 2）。不認得 → null。 */
	function qCreaturePartPose(r, clip, u0, reduce = false, perch = 0) {
		const strike = clip.startsWith("atk:");
		if ((clip === "move" || strike) && perch > 0 && !reduce && PERCHERS.has(r.key)) {
			const fly = qCreaturePartPose(r, clip, u0);
			const sit = qCreaturePartPose(r, "idle", 0);
			if (fly === null || sit === null) return fly;
			const k = cl(perch);
			const out = blendPose(fly, sit, k);
			const wings = k >= 1 ? sit : k >= .75 ? qCreaturePartPose(r, "idle", PERCH_SPREAD_U) : strike ? qCreaturePartPose(r, "move", 1 - k) : fly;
			for (const g of ["wingN", "wingF"]) {
				const w = wings?.parts[g];
				if (w !== void 0) out.parts[g] = { ...w };
			}
			if (strike) out.fx = [];
			return out;
		}
		const B = BODY_ANIM[r.key];
		const info = creatureClipInfo(r.key, clip);
		if (B === void 0 || info === null) return null;
		const u = cl(u0);
		const p = newPose();
		const e = { r };
		if (r.key === "spider") p.limbRim = true;
		if (reduce) {
			if (clip === "idle" || clip === "move") return null;
			if (clip === "hit") {
				p.flash = u < .2 ? .9 : 0;
				return p;
			}
			if (clip === "death") {
				B.death(p, 1, e);
				p.fx = [];
				return p;
			}
			B.attacks[clip.slice(4)].fn(p, u, e);
			const q = newPose();
			q.fx = p.fx;
			R(q, { dx: 2 * Math.sin(Math.PI * u) });
			return q;
		}
		if (clip === "idle") B.idle(p, u, e);
		else if (clip === "move") B.move(p, u, e);
		else if (clip === "hit") HIT[B.kind](p, u, e);
		else if (clip === "death") B.death(p, u, e);
		else B.attacks[clip.slice(4)].fn(p, u, e);
		return p;
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/battle/glossary.ts
	/** 表面的顏色取自 `render/palette.ts`（單一來源），這裡只決定疊色比例。 */
	var ground = (id, alpha) => ({
		color: parseInt((SURFACE_GROUND_COLOR[id] ?? "#888888").slice(1), 16),
		alpha
	});
	ground("oil", .6), ground("water", .55), ground("fire", .7), ground("ice", .7), ground("poison", .6), ground("holy", .6), ground("darkness", .65), ground("smoke", .6);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/inkRace.ts
	var EARS = [
		"pointed",
		"fin",
		"beast"
	];
	var HORNS = [
		"small",
		"curved",
		"dragon"
	];
	var TAILS = [
		"fox",
		"scaled",
		"demon",
		"dragon"
	];
	var PATTERNS = [
		"scales",
		"marks",
		"circuit",
		"dragonscale"
	];
	var pick = (list, v) => typeof v === "string" ? list.find((x) => x === v) : void 0;
	var dark$2 = (c, t = .3) => darken(c, t);
	var light$1 = (c, t = .3) => lighten(c, t);
	var COVERS$1 = {
		helmet: {
			top: true,
			side: true,
			hair: true
		},
		greathelm: {
			top: true,
			side: true,
			hair: true
		},
		horned_helm: {
			top: true,
			side: true,
			hair: true
		},
		hood: {
			top: true,
			side: true,
			hood: true,
			hair: true
		},
		cap: {
			top: true,
			narrow: true,
			hair: true
		},
		bandana: {
			top: true,
			narrow: true
		},
		crown: { narrow: true },
		wide_hat: {
			top: true,
			tall: true
		},
		wizard_hat: {
			top: true,
			tall: true,
			hair: true
		},
		veil: {
			top: true,
			side: true,
			hair: true
		}
	};
	/** 沒戴＝什麼都不蓋；沒登記的 kind 當作只蓋頭頂。 */
	var coverOf$1 = (head) => head === void 0 ? {} : COVERS$1[head.kind] ?? { top: true };
	var hasHorns = (look) => pick(HORNS, look.horns) !== void 0;
	/** 有種族角時頭部裝備的調整：角盔改畫成一般頭盔（種族角取代裝飾角）、小帽變窄、寬帽與巫師帽抬高。 */
	function hatAdjust(look, head) {
		if (!hasHorns(look)) return {
			item: head,
			dy: 0,
			sx: 1
		};
		if (head.kind === "horned_helm") return {
			item: {
				...head,
				kind: "helmet"
			},
			dy: 0,
			sx: 1
		};
		const c = coverOf$1(head);
		return {
			item: head,
			dy: c.tall === true ? -5 : 0,
			sx: c.narrow === true ? .8 : 1
		};
	}
	/** 正面：從腰側往畫面右邊伸出；側面：往身後（西）伸出；背面：畫在披風之上。畫在身體之前（身體、下襬會蓋住根部）。 */
	function drawInkTail(ctx, look, view) {
		const k = pick(TAILS, look.tail);
		if (k === void 0) return;
		const s = view === "side" ? -1 : 1;
		const P = (pts) => pts.map(([x, y]) => [x * s, y]);
		const skin = look.skin ?? "#eab48a";
		if (k === "fox") {
			const c = look.tailColor ?? look.hairColor ?? "#d8762a";
			ink$1(ctx, `tail-fox-${view}`, P([
				[2, -16],
				[10, -17],
				[16, -10],
				[17, -3],
				[12, -1],
				[9, -8],
				[2, -11]
			]), c);
			ink$1(ctx, `tail-foxtip-${view}`, P([
				[14.6, -5],
				[17.4, -3.6],
				[15.6, -.6],
				[12.4, -1.4]
			]), "#f4ece0", {
				shade: false,
				w: .6
			});
			return;
		}
		if (k === "demon") {
			const c = look.tailColor ?? dark$2(skin, .3);
			const line = P([
				[2, -13],
				[9, -12],
				[13, -6],
				[13.6, -1.6]
			]);
			stroke$1(ctx, `tail-dm-${view}`, line, 1.9);
			stroke$1(ctx, `tail-dm2-${view}`, line, 1.1, c);
			ink$1(ctx, `tail-dmtip-${view}`, P([
				[13.6, -2.4],
				[11.2, .6],
				[13.8, 3.2],
				[16, .4]
			]), c, {
				shade: false,
				w: .6
			});
			return;
		}
		const c = look.tailColor ?? look.scaleColor ?? dark$2(skin, .15);
		const thick = k === "dragon" ? 1.35 : 1;
		ink$1(ctx, `tail-sc-${view}`, P([
			[1, -17 * thick + 1],
			[10, -14],
			[17, -5],
			[21, .6],
			[15, 0],
			[8, -6],
			[1, -9]
		]), c);
		if (k === "dragon") for (const t of [
			.25,
			.48,
			.7
		]) {
			const x = 2 + 16 * t;
			const y = -15 + 13 * t;
			ink$1(ctx, `spine-${t}-${view}`, P([
				[x - 1.6, y - .4],
				[x + .2, y - 4.2],
				[x + 1.8, y + .2]
			]), light$1(c, .35), {
				shade: false,
				w: .5
			});
		}
	}
	/** 尖耳、鰭耳：正面／背面畫在頭之前（頭蓋住耳根，只露出伸出的部分）。兜帽蓋住側耳＝不畫。 */
	function drawEarsUnder(ctx, e) {
		const k = pick(EARS, e.look.ears);
		if (k === void 0 || k === "beast" || e.view === "side") return;
		if (coverOf$1(e.head).hood === true) return;
		const c = e.look.skin ?? "#eab48a";
		for (const sx of [-1, 1]) if (k === "pointed") ink$1(ctx, `ear-p-${sx}`, [
			[sx * 8, -44],
			[sx * 15.6, -48.6],
			[sx * 9, -39.6]
		], c, { w: .7 });
		else ink$1(ctx, `ear-f-${sx}`, [
			[sx * 8.4, -45],
			[sx * 14, -47.6],
			[sx * 13, -42],
			[sx * 14.4, -38.6],
			[sx * 8.4, -39]
		], light$1(c, .15), { w: .7 });
	}
	function sideEar$1(ctx, look, k) {
		const c = look.skin ?? "#eab48a";
		if (k === "pointed") ink$1(ctx, "ear-p-s", [
			[-1, -43.6],
			[-9.6, -48.6],
			[-1.6, -39.2]
		], c, { w: .7 });
		else ink$1(ctx, "ear-f-s", [
			[-.6, -45],
			[-7.4, -48.6],
			[-6, -42.4],
			[-7.8, -38.4],
			[-.6, -39]
		], light$1(c, .15), { w: .7 });
	}
	/** 側面的尖耳／鰭耳：沒有蓋住兩側的頭部裝備時，畫在頭髮之後、頭部裝備之前。 */
	function drawSideEarBeforeHat(ctx, e) {
		const k = pick(EARS, e.look.ears);
		if (e.view !== "side" || k === void 0 || k === "beast") return;
		if (coverOf$1(e.head).side === true) return;
		sideEar$1(ctx, e.look, k);
	}
	/** 獸耳：頭頂兩隻（側面前後各一）。 */
	function drawBeastEars(ctx, e, c, inner, scale) {
		const F = e.view !== "side";
		const pos = F ? [[-1, -5.6], [1, 5.6]] : [[-1, -5], [1, 0]];
		for (const [i, x] of pos) {
			const far = !F && i < 0;
			const lean = (F ? i * 1.2 : -1.4) * scale;
			const top = -48.6 - 9 * scale;
			ink$1(ctx, `ear-b-${e.view}-${i}-${scale}`, [
				[x - 3.6, -48.6],
				[x + lean, top],
				[x + 3.4, -49]
			], far ? dark$2(c, .2) : c, { w: .8 });
			if (inner !== null) ink$1(ctx, `ear-bi-${e.view}-${i}-${scale}`, [
				[x - 1.8, -49.4],
				[x + (F ? i * .8 : -1) * scale, -48.6 - 6.4 * scale],
				[x + 1.6, -49.6]
			], inner, {
				shade: false,
				line: false
			});
		}
	}
	/** 獸耳在頭部裝備之前畫的情形：沒戴、皇冠（不蓋頭頂）。其餘蓋頭頂的頭盔、寬帽、巫師帽藏起來；小帽與兜帽見 `drawEarsAfterHat`。 */
	function drawBeastEarsBeforeHat(ctx, e) {
		if (e.look.ears !== "beast") return;
		if (coverOf$1(e.head).top === true) return;
		drawBeastEars(ctx, e, e.look.hairColor ?? "#d8762a", "#f2c4b8", 1);
	}
	/**
	* 頭部裝備之後才畫的耳朵：
	* - 側面的尖耳／鰭耳戴頭盔時從頭盔兩側伸出（兜帽蓋住＝不畫）；
	* - 獸耳戴小帽（cap、bandana）從帽子兩側穿出；戴兜帽時兜帽頂端多兩個凸起（有耳朵的兜帽，帽色）。
	*/
	function drawEarsAfterHat(ctx, e) {
		const k = pick(EARS, e.look.ears);
		if (k === void 0 || e.head === void 0) return;
		const cov = coverOf$1(e.head);
		if (k === "beast") {
			if (cov.hood === true) drawBeastEars(ctx, e, e.headColor, null, 1);
			else if (cov.narrow === true && cov.top === true) drawBeastEars(ctx, e, e.look.hairColor ?? "#d8762a", "#f2c4b8", 1);
			return;
		}
		if (e.view === "side" && cov.side === true && cov.hood !== true) sideEar$1(ctx, e.look, k);
	}
	/** 角：永遠在最上層。小角、彎角（3R-3c 美術 PM 小修：底寬約 4px 的牛角形）、龍角（龍角的雙叉外形照樣張；鱗色、龍鱗屬 3R-3c）。 */
	function drawInkHorns(ctx, look, view) {
		const k = pick(HORNS, look.horns);
		if (k === void 0) return;
		const c = look.hornColor ?? "#e8d8b8";
		const F = view !== "side";
		const one = (key, s, far) => {
			const P = (pts) => pts.map(([x, y]) => [x * s, y]);
			const col = far ? dark$2(c, .25) : c;
			if (k === "small") ink$1(ctx, key, P(F ? [
				[3, -50],
				[5.4, -56.4],
				[6.4, -49.4]
			] : [
				[.6, -50.6],
				[-2, -57],
				[-2.6, -50]
			]), col, { w: .7 });
			else if (k === "curved") ink$1(ctx, key, P(F ? [
				[7.6, -48.6],
				[10.8, -51.8],
				[12.8, -55.4],
				[12.6, -59],
				[10.2, -55.6],
				[7.8, -53.4],
				[5, -52.4],
				[3.2, -50.4]
			] : [
				[-3.6, -49.4],
				[-7.2, -52],
				[-9.6, -55.2],
				[-10, -58.8],
				[-7.6, -55.2],
				[-5.2, -53.4],
				[-2.2, -52.8],
				[1, -51]
			]), col, { w: .7 });
			else ink$1(ctx, key, P(F ? [
				[3.4, -49.4],
				[8, -57],
				[14.4, -61.6],
				[10.6, -54.6],
				[7.2, -49]
			] : [
				[1.6, -49.6],
				[-4, -56.6],
				[-12.4, -60.6],
				[-7.6, -53],
				[-2, -47.6]
			]), col, { w: .8 });
		};
		if (F) {
			one("horn-l", -1, false);
			one("horn-r", 1, false);
		} else {
			one("horn-far", 1, true);
			ctx.save();
			ctx.translate(2.2, .6);
			one("horn-near", 1, false);
			ctx.restore();
		}
	}
	var INK_EYE = "#1d1a22";
	var DRAGON_FALLBACK = "#a8784a";
	/** 眼睛：豎瞳（金色眼白＋黑色細縫）或一般圓眼。`x` 是眼的橫向位置。 */
	function drawEye(ctx, look, x) {
		if (look.slitEyes === true) {
			dot$2(ctx, x, -41, 1.3, 1.5, "#e8b830");
			dot$2(ctx, x, -41, .35, 1.3, INK_EYE);
		} else dot$2(ctx, x, -41, .9, 1.3, look.eyes ?? INK_EYE);
	}
	function drawFacePattern(ctx, look, view) {
		const F = view === "front";
		const pc = look.scaleColor ?? look.markColor ?? dark$2(look.skin ?? "#eab48a", .25);
		const k = pick(PATTERNS, look.pattern);
		if (k === "scales" || k === "dragonscale") {
			const base = F ? [
				[-6.6, -43.6],
				[-7.4, -41],
				[6.6, -43.6],
				[7.4, -41],
				[0, -48]
			] : [
				[1.6, -44],
				[.4, -41.4],
				[2.6, -47.6]
			];
			const more = k !== "dragonscale" ? [] : F ? [
				[-7, -38.4],
				[7, -38.4],
				[-5.8, -36],
				[5.8, -36]
			] : [[2.4, -38.6], [4, -36]];
			for (const [x, y] of [...base, ...more]) stroke$1(ctx, `scale-${view}-${x}-${y}`, [
				[x - 1.2, y],
				[x, y + 1],
				[x + 1.2, y]
			], k === "dragonscale" ? .8 : .6, pc);
		} else if (k === "marks") {
			const mc = look.markColor ?? pc;
			for (const sx of F ? [-1, 1] : [1]) {
				const x = F ? sx * 6 : 2.6;
				stroke$1(ctx, `mark-${view}-${sx}`, [[x - 1.4, -40.4], [x + 1.4, -39.4]], .8, mc);
				stroke$1(ctx, `mark2-${view}-${sx}`, [[x - 1.4, -38.6], [x + 1.4, -37.6]], .8, mc);
			}
		} else if (k === "circuit") {
			const x = F ? 5 : 1.4;
			const cc = "#3ad0e8";
			stroke$1(ctx, `circ-${view}`, [
				[x, -46],
				[x, -42.6],
				[x + 2.4, -41]
			], .6, cc);
			dot$2(ctx, x + 2.4, -41, .6, .6, cc);
			dot$2(ctx, x, -46, .6, .6, cc);
		}
	}
	/** 臉部紋路、獠牙、鬍子（畫在眼睛與嘴之後、頭髮與頭部裝備之前，所以頭盔、頭髮會蓋住該蓋的部分）。背面不畫。 */
	function drawRaceFace(ctx, look, view) {
		const F = view === "front";
		drawFacePattern(ctx, look, view);
		if (look.tusks === true) for (const x of F ? [-1.8, 1.8] : [6.6]) ink$1(ctx, `tusk-${view}-${x}`, [
			[x - .7, -36.4],
			[x, -39.2],
			[x + .7, -36.4]
		], "#f4ecd8", {
			shade: false,
			w: .45
		});
		if (look.beard === true) {
			const c = look.hairColor ?? "#a8481e";
			if (F) ink$1(ctx, "beard", [
				[-7.6, -40],
				[-4, -37.6],
				[0, -38.2],
				[4, -37.6],
				[7.6, -40],
				[6.4, -32],
				[2.4, -28.6],
				[-2.4, -28.6],
				[-6.4, -32]
			], c);
			else ink$1(ctx, "beard-s", [
				[1, -38.6],
				[9, -37],
				[8, -32],
				[4.4, -28.8],
				[.4, -31]
			], c);
		}
	}
	/** 鱗脊：鼻樑到額頭一排小尖，畫在頭髮之後（不被瀏海蓋住）、頭部裝備之前。 */
	function drawRidge(ctx, look, view) {
		if (look.ridge !== true || view === "back") return;
		const c = look.scaleColor ?? DRAGON_FALLBACK;
		const F = view === "front";
		[
			-46.4,
			-44,
			-41.6
		].forEach((y, i) => {
			const x = F ? 0 : 5.4 - i * .4;
			ink$1(ctx, `ridge-${view}-${i}`, [
				[x - 1.2, y + 1.1],
				[x, y - 1.1],
				[x + 1.2, y + 1.1]
			], light$1(c, .15), {
				shade: false,
				w: .5
			});
		});
	}
	/** 背刺：肩後三根骨刺。正面只從肩頭露出尖端（畫在身體之前，身體蓋住大半）；背面畫在背上；側面在背後。 */
	function drawBackSpines(ctx, look, view) {
		if (look.spines !== true) return;
		const c = light$1(look.scaleColor ?? DRAGON_FALLBACK, .2);
		const spike = (key, x, y, dx, dy) => {
			const n = Math.hypot(dx, dy);
			const px = -dy / n * 1.7;
			const py = dx / n * 1.7;
			ink$1(ctx, key, [
				[x + px, y + py],
				[x + dx, y + dy],
				[x - px, y - py]
			], c, {
				shade: false,
				w: .5
			});
		};
		if (view === "front") for (const x of [-5.6, 5.6]) spike(`spine-f-${x}`, x, -30, 0, -6.5);
		else if (view === "back") for (const x of [
			-4.5,
			0,
			4.5
		]) spike(`spine-b-${x}`, x, -28, 0, -5.2);
		else for (const [x, y] of [
			[-3.6, -30],
			[-4.8, -26.4],
			[-5.2, -22.8]
		]) spike(`spine-s-${y}`, x, y, -4.4, -.6);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qIcon/core.ts
	var TAU$1 = Math.PI * 2;
	/** 剪影外框色（和 Q 版人物 `Q_OUT` 同色）。 */
	var OUT$2 = "#16121a";
	var mat$1 = (id) => MATERIAL[id];
	/** 畫法固定零件的顏色。鋼、鐵、木、皮照 `material.ts`（第 0.0 節第 3 點）；其餘照樣張。 */
	var M = {
		steel: mat$1("steel")[0],
		steelD: mat$1("steel")[1],
		iron: mat$1("iron")[0],
		ironD: mat$1("iron")[1],
		wood: mat$1("wood")[0],
		woodD: mat$1("wood")[1],
		shaft: "#6a4420",
		grip: "#4a3020",
		brass: "#8a6a2a",
		gold: "#d8b04a",
		goldL: "#f6d878",
		leather: mat$1("leather")[0],
		leatherD: mat$1("leather")[1],
		skin: "#f1c9a5",
		cream: "#f2e6c8",
		arcane: "#9a86ff"
	};
	/** 元素色（照 `palette.ts`）：[主色, 亮色]。 */
	var EL = {
		fire: ["#ff6a1a", "#ffd23f"],
		ice: ["#8fe3ff", "#ffffff"],
		lightning: ["#fff36b", "#ffffff"],
		poison: ["#7ddc3a", "#d6f59a"],
		holy: ["#ffd75e", "#fff6c8"],
		shadow: ["#9a6ad8", "#d2b0ff"],
		wind: ["#7fe0c0", "#dcfff1"],
		earth: ["#b0814a", "#f0c890"],
		water: ["#4aa8ff", "#cfe8ff"]
	};
	var HI = "rgba(255,255,255,0.45)";
	var HI2 = "rgba(255,255,255,0.8)";
	var SH = "rgba(0,0,0,0.22)";
	var domCanvas = (w, h) => {
		if (typeof document === "undefined") return null;
		const cv = document.createElement("canvas");
		cv.width = w;
		cv.height = h;
		return cv;
	};
	var factory = domCanvas;
	/** 現在建得出畫布嗎（沒有 DOM、也沒有注入假畫布時不行）。 */
	var qCanvasAvailable = () => factory !== domCanvas || typeof document !== "undefined";
	/** 一張空白畫布（寬 w、高 h 裝置像素）。只在 `render` 裡用（`render` 先確認建得出畫布）。 */
	function blank(w, h = w) {
		const cv = factory(w, h);
		if (cv === null) throw new Error("qIcon: no canvas");
		return cv;
	}
	function ctxOf(cv) {
		const x = cv.getContext("2d");
		if (x === null) throw new Error("qIcon: no 2d context");
		return x;
	}
	var f = (c, col, path) => {
		c.beginPath();
		c.fillStyle = col;
		path(c);
		c.fill();
	};
	var rr$1 = (c, col, x, y, w, h, r) => f(c, col, () => c.roundRect(x, y, w, h, r));
	var ci = (c, col, x, y, r) => f(c, col, () => c.arc(x, y, r, 0, TAU$1));
	var el$1 = (c, col, x, y, rx, ry, rot = 0) => f(c, col, () => c.ellipse(x, y, rx, ry, rot, 0, TAU$1));
	/** 多邊形；round＞0 時用同色粗線把角磨圓（外形往外長 round 單位）。 */
	function poly$1(c, col, pts, round = 0) {
		c.beginPath();
		pts.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y));
		c.closePath();
		c.fillStyle = col;
		c.fill();
		if (round) {
			c.strokeStyle = col;
			c.lineWidth = round * 2;
			c.lineJoin = "round";
			c.stroke();
		}
	}
	function ln(c, col, w, pts, join = "round") {
		c.beginPath();
		pts.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y));
		c.strokeStyle = col;
		c.lineWidth = w;
		c.lineCap = join === "round" ? "round" : "butt";
		c.lineJoin = join;
		c.miterLimit = 6;
		c.stroke();
	}
	function starPts(x, y, R, r, n, rot = -Math.PI / 2) {
		const p = [];
		for (let i = 0; i < n * 2; i++) {
			const a = rot + i * Math.PI / n, q = i % 2 ? r : R;
			p.push([x + Math.cos(a) * q, y + Math.sin(a) * q]);
		}
		return p;
	}
	/** 火焰外形：中心 (x,y)、高 20s、寬 14s，尖端朝上，左邊一小撮分岔。 */
	function flame(c, col, x, y, s) {
		c.save();
		c.translate(x, y);
		c.scale(s, s);
		c.beginPath();
		c.moveTo(.5, -10);
		c.bezierCurveTo(1.5, -5, 7, -3, 7, 3);
		c.bezierCurveTo(7, 7.5, 3.5, 10, 0, 10);
		c.bezierCurveTo(-3.5, 10, -7, 7.5, -7, 3);
		c.bezierCurveTo(-7, 0, -5, -2, -4.2, -4.8);
		c.bezierCurveTo(-3.5, -2.5, -2.6, -2, -1.8, -2.4);
		c.bezierCurveTo(-2.5, -5, -1.5, -8, .5, -10);
		c.closePath();
		c.fillStyle = col;
		c.fill();
		c.restore();
	}
	/** 剪影往一圈方向各位移 r（外圈）與 r/2（內圈）疊起來再染外框色（樣張 dilate；不用逐步膨脹，見樣張註解）。 */
	function dilate$1(src, r, col = OUT$2) {
		const w = src.width, h = src.height, o = blank(w, h), x = ctxOf(o), n = Math.max(16, Math.ceil(r * 5));
		for (const q of [1, .5]) for (let i = 0; i < n; i++) {
			const t = i / n * TAU$1;
			x.drawImage(src, Math.cos(t) * r * q, Math.sin(t) * r * q);
		}
		x.drawImage(src, 0, 0);
		x.globalCompositeOperation = "source-in";
		x.fillStyle = col;
		x.fillRect(0, 0, w, h);
		return o;
	}
	/** 圖樣裡前後重疊的零件：後畫的那一件自己先包一圈外框，兩件才分得開。 */
	function halo(c, o, fn, col = OUT$2, k = 1) {
		if (o.flat) {
			fn(c);
			return;
		}
		const cv = blank(c.canvas.width, c.canvas.height), x = ctxOf(cv);
		x.setTransform(c.getTransform());
		fn(x);
		c.save();
		c.setTransform(1, 0, 0, 1, 0, 0);
		if (o.owPx > 0) c.drawImage(dilate$1(cv, o.owPx * k, col), 0, 0);
		c.drawImage(cv, 0, 0);
		c.restore();
	}
	/** 外框粗細（CSS px）：顯示邊長的 5%，最細 1px、最粗 1.6px。 */
	var outlinePx = (px) => Math.min(1.6, Math.max(1, px * .05));
	/** 只畫圖樣（不含框）：回傳邊長 round(px×res) 的 canvas；建不出畫布時回傳 null。 */
	function render(def, px, res, opt = {}) {
		if (!qCanvasAvailable()) return null;
		const S = Math.max(4, Math.round(px * res)), o = {
			small: px <= 24,
			tiny: px <= 14,
			owPx: (opt.ow ?? outlinePx(px)) * res,
			badge: !!opt.badge,
			u: 48 / px
		};
		const main = blank(S), m = ctxOf(main);
		m.scale(S / 48, S / 48);
		def.d(m, o);
		const out = blank(S), x = ctxOf(out);
		if (def.pre) {
			x.save();
			x.scale(S / 48, S / 48);
			def.pre(x, o);
			x.restore();
		}
		if (o.owPx > 0) {
			const solid = blank(S), s = ctxOf(solid);
			s.scale(S / 48, S / 48);
			def.d(s, {
				...o,
				flat: true
			});
			x.drawImage(dilate$1(solid, o.owPx), 0, 0);
		}
		x.drawImage(main, 0, 0);
		if (def.post) {
			x.save();
			x.scale(S / 48, S / 48);
			def.post(x, o);
			x.restore();
		}
		return out;
	}
	M.steel, M.steelD, M.brass, M.gold, M.wood, M.woodD, M.shaft, M.iron, M.ironD;
	mix$1("#6a4a2e", "#000000", .32);
	M.gold;
	M.goldL;
	var mat = (id) => MATERIAL[id] ?? MATERIAL["cloth"];
	mix$1(mat("cloth")[0], "#ffe6b8", .42);
	M.wood;
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qIcon/legacy48.ts
	/** 水滴外形：中心 (x,y)、高 20s、寬 14s，尖端朝上（樣張 H.drop）。 */
	function drop(c, col, x, y, s) {
		c.save();
		c.translate(x, y);
		c.scale(s, s);
		c.beginPath();
		c.moveTo(0, -10);
		c.bezierCurveTo(4, -4, 7, 0, 7, 4);
		c.bezierCurveTo(7, 8, 3.5, 10, 0, 10);
		c.bezierCurveTo(-3.5, 10, -7, 8, -7, 4);
		c.bezierCurveTo(-7, 0, -4, -4, 0, -10);
		c.closePath();
		c.fillStyle = col;
		c.fill();
		c.restore();
	}
	/** 一根插在土堆上的木雕圖騰柱：頂上一對紅翅、兩張臉（樣張 SKILL_V1.skill_plant_totem.d）。 */
	function totemPole(c, o) {
		el$1(c, "#6a4a2e", 24, 41.5, 14.5, 3.6);
		poly$1(c, "#c0392b", [
			[17, 9],
			[5, 6],
			[8, 11.5],
			[4.5, 13],
			[9.5, 15],
			[17, 15.5]
		], .5);
		poly$1(c, "#c0392b", [
			[31, 9],
			[43, 6],
			[40, 11.5],
			[43.5, 13],
			[38.5, 15],
			[31, 15.5]
		], .5);
		rr$1(c, M.wood, 16.5, 5, 15, 36.5, 3.4);
		f(c, "#b98048", () => c.roundRect(16.5, 5, 4.4, 36.5, [
			3.4,
			0,
			0,
			3.4
		]));
		f(c, M.woodD, () => c.rect(16.5, 21.4, 15, 1.7));
		for (const y of [11, 28]) {
			rr$1(c, "#fff6c8", 19, y, 3.6, 3.6, .8);
			rr$1(c, "#fff6c8", 25.4, y, 3.6, 3.6, .8);
			if (!o.small) {
				f(c, OUT$2, () => c.rect(20.3, y + 1, 1.5, 1.8));
				f(c, OUT$2, () => c.rect(26.7, y + 1, 1.5, 1.8));
			}
		}
		rr$1(c, M.woodD, 20.6, 16.6, 6.8, 2.4, 1);
		poly$1(c, "#e8bb48", [
			[20, 34.5],
			[22, 37.5],
			[24, 34.5],
			[26, 37.5],
			[28, 34.5],
			[28, 36],
			[26, 39],
			[24, 36],
			[22, 39],
			[20, 36]
		]);
	}
	/** 樣張 `QIcons.ART` 裡第 4 批用到的兩類（只搬用到的款）。 */
	var ART = {
		status: {
			prone: {
				zh: "倒地",
				d: (c, o) => {
					const k = "#f2e6c8";
					if (o.tiny) {
						rr$1(c, "#a89878", 1.5, 39.5, 45, 5.5, 2);
						rr$1(c, k, 17, 19.5, 29.5, 15.5, 6.5);
						ci(c, k, 12.5, 25, 11.5);
						f(c, "#ffffff", () => c.ellipse(9, 20.6, 4, 2.8, -.5, 0, TAU$1));
						return;
					}
					halo(c, o, (x) => {
						poly$1(x, "#ffd23f", starPts(24, 11, 10.5, 4.8, 7, -1.2), .5);
						poly$1(x, "#ffffff", starPts(24, 11, 4.8, 2.3, 7, -1.2));
					});
					rr$1(c, "#8a7a6a", 2.5, 40.8, 43, 4, 2);
					halo(c, o, (x) => {
						ln(x, k, 6, [[30, 36.2], [43, 36.6]]);
						ln(x, k, 6, [[30, 33], [39.5, 25.5]]);
						rr$1(x, k, 17, 28.4, 16.5, 11.2, 5);
						ci(x, k, 11.5, 29.6, 9.6);
						f(x, "#ffffff", () => x.ellipse(8.6, 26, 3.2, 2.2, -.5, 0, TAU$1));
						f(x, "rgba(120,90,50,0.3)", () => x.rect(19, 37, 13, 2.6));
					});
				}
			},
			frozen: {
				zh: "冰凍",
				d: (c, o) => {
					poly$1(c, "#8fe3ff", [
						[12, 17],
						[17.5, 25],
						[16.5, 42],
						[7, 42],
						[6, 26]
					], .8);
					poly$1(c, "#8fe3ff", [
						[36.5, 20],
						[42, 28],
						[41, 42],
						[32, 42],
						[31, 28]
					], .8);
					poly$1(c, "#b8efff", [
						[24, 4.5],
						[31.5, 17],
						[29.5, 42],
						[18.5, 42],
						[16.5, 17]
					], .8);
					poly$1(c, "#ffffff", [
						[24, 7],
						[24, 40.5],
						[19.6, 40.5],
						[18, 17.4]
					]);
					if (!o.tiny) {
						poly$1(c, "#3fa6d8", [
							[29.2, 20],
							[30.4, 17.6],
							[28.6, 41],
							[26.4, 41]
						]);
						poly$1(c, "#e8fbff", [
							[11.6, 20],
							[11.6, 41],
							[8.4, 41],
							[7.6, 26.4]
						]);
						poly$1(c, "#e8fbff", [
							[36, 23],
							[36, 41],
							[33.2, 41],
							[32.6, 28.4]
						]);
					}
				}
			},
			hasted: {
				zh: "加速",
				d: (c, o) => {
					if (o.tiny) {
						for (const dx of [.5, 23.5]) {
							poly$1(c, "#7dffb0", [
								[dx, 6],
								[dx + 11, 6],
								[dx + 23, 24],
								[dx + 11, 42],
								[dx, 42],
								[dx + 12, 24]
							]);
							poly$1(c, "#e2fff0", [
								[dx, 6],
								[dx + 11, 6],
								[dx + 23, 24],
								[dx + 12, 24]
							]);
						}
						return;
					}
					for (const dx of [3, 20]) {
						poly$1(c, "#7dffb0", [
							[dx, 9],
							[dx + 10, 9],
							[dx + 22, 24],
							[dx + 10, 39],
							[dx, 39],
							[dx + 12, 24]
						], .9);
						poly$1(c, "#d6ffe6", [
							[dx + 1, 10],
							[dx + 9.6, 10],
							[dx + 20.6, 24],
							[dx + 12, 24]
						]);
					}
				}
			},
			feared: {
				zh: "恐懼",
				d: (c, o) => {
					f(c, "#ece4ff", () => {
						c.moveTo(6, 43);
						c.lineTo(6, 23);
						c.bezierCurveTo(6, 0, 42, 0, 42, 23);
						c.lineTo(42, 43);
						c.lineTo(36, 37.5);
						c.lineTo(30, 43);
						c.lineTo(24, 37.5);
						c.lineTo(18, 43);
						c.lineTo(12, 37.5);
						c.closePath();
					});
					if (!o.tiny) f(c, "rgba(120,90,200,0.3)", () => {
						c.moveTo(33, 7.5);
						c.bezierCurveTo(40, 12, 42, 18, 42, 23);
						c.lineTo(42, 43);
						c.lineTo(36.4, 37.8);
						c.lineTo(36.4, 22);
						c.bezierCurveTo(36.4, 16, 35.4, 11, 33, 7.5);
						c.closePath();
					});
					el$1(c, OUT$2, 17.5, 21, o.tiny ? 4 : 3.3, o.tiny ? 5.6 : 4.8);
					el$1(c, OUT$2, 30.5, 21, o.tiny ? 4 : 3.3, o.tiny ? 5.6 : 4.8);
					if (!o.tiny) el$1(c, OUT$2, 24, 31, 3.2, 2.6);
				}
			}
		},
		hud: {
			ap: {
				zh: "AP（行動點）",
				d: (c, o) => {
					poly$1(c, "#ffd23a", [
						[27, 3.5],
						[9.5, 27],
						[21, 27],
						[16, 44.5],
						[38.5, 19.5],
						[27, 19.5],
						[33.5, 3.5]
					], 1);
					if (!o.tiny) poly$1(c, "#fff3a0", [
						[27.4, 5],
						[12.6, 25.6],
						[17, 25.6],
						[31, 5]
					]);
				}
			},
			mana: {
				zh: "法力",
				d: (c, _o) => {
					drop(c, "#4a8ae0", 24, 24.5, 2.1);
					c.save();
					c.beginPath();
					c.rect(0, 0, 48, 48);
					c.clip();
					f(c, "rgba(20,40,110,0.38)", () => {
						c.moveTo(24, 45.5);
						c.bezierCurveTo(34, 45.5, 40, 38, 38.4, 29.5);
						c.bezierCurveTo(37, 37, 31, 41, 24, 41.5);
						c.closePath();
					});
					c.restore();
					el$1(c, "#cfe4ff", 18, 28.5, 2.6, 5.6, .45);
				}
			},
			stamina: {
				zh: "耐力",
				d: (c, o) => {
					const P = [
						[4.5, 26],
						[13.5, 26],
						[19, 11.5],
						[27.5, 37.5],
						[32.5, 24],
						[43.5, 24]
					];
					ln(c, "#e8bb48", 6.4, P);
					if (!o.tiny) ln(c, "#fff0b0", 1.6, P.map(([x, y]) => [x - .6, y - 1.2]));
				}
			},
			move: {
				zh: "移動",
				d: (c, o) => {
					rr$1(c, "#a07040", 12.5, 5.5, 15.5, 30, 4);
					f(c, "#a07040", () => {
						c.moveTo(12.5, 24);
						c.lineTo(27, 24);
						c.quadraticCurveTo(41.5, 25.5, 42.5, 35.5);
						c.lineTo(42.5, 39);
						c.lineTo(12.5, 39);
						c.closePath();
					});
					rr$1(c, "#5e3b1f", 11, 38, 33, 5.4, 2.2);
					rr$1(c, "#e0c088", 11, 4.5, 18.5, 7.6, 3.2);
					if (!o.tiny) {
						f(c, HI, () => c.rect(15, 13.5, 2.2, 20));
						f(c, "rgba(0,0,0,0.2)", () => {
							c.moveTo(28, 26);
							c.quadraticCurveTo(39.5, 27.5, 41, 36);
							c.lineTo(28, 36);
							c.closePath();
						});
					}
				}
			}
		}
	};
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
		keywordNames: {
			"ignite": "點燃",
			"wet": "潮濕",
			"charged": "帶電",
			"frozen": "冰凍",
			"prone": "倒地",
			"collision": "撞擊",
			"marked": "標記",
			"high_ground": "高處",
			"concealed": "隱蔽",
			"summon": "召喚物",
			"poisoned": "中毒",
			"form": "形態"
		},
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
	Object.fromEntries(gearAppearance_default.kinds.map((k) => [k.id, k]));
	gearAppearance_default.maxKeywords;
	/** 造型清單（供預覽頁與測試用）。 */
	function gearKinds() {
		return gearAppearance_default.kinds;
	}
	Object.fromEntries(Object.entries(ELEMENT_COLORS).map(([id, c]) => [id, {
		name: c.name,
		accent: c.accent,
		dark: c.dark,
		light: c.light
	}]));
	Array.from({ length: 25 }, (_, i) => i % 5 === 2 || Math.floor(i / 5) === 2 ? 1 : 0);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qIcon/skills.ts
	/** 有固定鍵的表：點名取值不會是 undefined；用字串查時可能是 undefined（樣張一律接 `??` 退回）。 */
	var table = () => (o) => o;
	var st$1 = (c, col, w, fn, cap = "round") => {
		c.beginPath();
		fn(c);
		c.strokeStyle = col;
		c.lineWidth = w;
		c.lineCap = cap;
		c.lineJoin = "round";
		c.stroke();
	};
	var at$1 = (c, x, y, k, fn, rot = 0) => {
		c.save();
		c.translate(x, y);
		c.rotate(rot);
		c.scale(k, k);
		fn(c);
		c.restore();
	};
	/** 把畫在 48 格（中心 24,24）的東西縮放後放到 (x,y)。 */
	var place = (c, x, y, k, fn) => {
		c.save();
		c.translate(x, y);
		c.scale(k, k);
		c.translate(-24, -24);
		fn(c);
		c.restore();
	};
	var rgba = (hex, a) => {
		const p = [
			1,
			3,
			5
		].map((i) => parseInt(hex.slice(i, i + 2), 16));
		return `rgba(${p[0]},${p[1]},${p[2]},${a})`;
	};
	table()({
		physical: [
			"#2c313b",
			"#7d8798",
			"#e8ebf0"
		],
		fire: [
			"#4a1104",
			"#e8541a",
			"#ffb23a"
		],
		ice: [
			"#0b2f4e",
			"#3fa6d8",
			"#d8f6ff"
		],
		lightning: [
			"#1d1d4a",
			"#5a5ac8",
			"#fff36b"
		],
		poison: [
			"#12320c",
			"#4f9a28",
			"#b6f06a"
		],
		wind: [
			"#0b3f3a",
			"#3fb59a",
			"#dcfff1"
		],
		earth: [
			"#2e1d0e",
			"#9a6a36",
			"#f0c890"
		],
		holy: [
			"#5a3a06",
			"#e7b23a",
			"#fff6c8"
		],
		shadow: [
			"#10071e",
			"#5a3590",
			"#d2b0ff"
		],
		default: [
			"#221c44",
			"#6a5ad0",
			"#e8e0ff"
		]
	});
	var BASE_ZH = {
		physical: "物理",
		fire: "火",
		ice: "冰",
		lightning: "雷",
		poison: "毒",
		wind: "風",
		earth: "大地",
		holy: "聖光",
		shadow: "暗影",
		default: "（無）"
	};
	table()({
		common: "#9aa0a6",
		rare: "#4da3ff",
		epic: "#b06cff",
		legendary: "#ffbf3a"
	});
	/** 染色：元素色照 qIcons.js 的 EL；另外三個不是元素的——血（流血、標記、易傷）、鋼（守護、煙）、撞擊（倒地、碰撞）。 */
	var TINT = table()({
		...EL,
		arcane: ["#b8a8ff", "#ece6ff"],
		blood: ["#e8455a", "#ffb0b8"],
		steel: ["#c3ccd6", "#ffffff"],
		impact: ["#ffd23f", "#ffffff"],
		stone: ["#b4ac9a", "#ece6d6"]
	});
	var ELEMENT$1 = table()({
		fire: {
			zh: "火焰",
			d: (c) => {
				flame(c, "#ff6a1a", 24, 24, 1.55);
				flame(c, "#ffd23f", 24.5, 28, .98);
				el$1(c, "#ffffff", 24.6, 32, 2.5, 4.2);
			}
		},
		ice: {
			zh: "冰晶",
			d: (c, o) => {
				poly$1(c, "#6fc8ee", [
					[12.5, 17],
					[18, 22],
					[19.5, 39],
					[10.5, 39],
					[8, 25]
				], .6);
				poly$1(c, "#6fc8ee", [
					[35.5, 19],
					[40, 27],
					[37.5, 39],
					[28.5, 39],
					[30, 24]
				], .6);
				poly$1(c, "#8fe3ff", [
					[24, 5],
					[31, 14.5],
					[29, 39.5],
					[19, 39.5],
					[17, 14.5]
				], .6);
				poly$1(c, "#ffffff", [
					[24, 5],
					[17, 14.5],
					[19, 39.5],
					[22.4, 39.5],
					[22.4, 12]
				]);
				poly$1(c, "#4aa8d8", [
					[27.6, 12],
					[31, 14.5],
					[29, 39.5],
					[27.6, 39.5]
				]);
				if (!o.small) {
					poly$1(c, "#e6faff", [
						[12.5, 17],
						[8, 25],
						[10.5, 39],
						[12.6, 39]
					]);
					poly$1(c, "#e6faff", [
						[35.5, 19],
						[30, 24],
						[28.5, 39],
						[31, 39]
					]);
				}
			}
		},
		lightning: {
			zh: "閃電",
			d: (c) => {
				poly$1(c, "#fff36b", [
					[29, 4],
					[11, 26.5],
					[21, 26.5],
					[16, 44],
					[37, 19.5],
					[26.5, 19.5],
					[32.5, 4]
				], .7);
				poly$1(c, "#ffb400", [
					[21, 26.5],
					[16, 44],
					[37, 19.5],
					[31.5, 19.5],
					[22.6, 31.5],
					[24.5, 26.5]
				]);
				poly$1(c, "#ffffff", [
					[28.6, 8],
					[16.5, 23.6],
					[22.4, 23.6],
					[29.6, 8]
				]);
			}
		},
		poison: {
			zh: "毒液",
			d: (c, o) => {
				drop(c, "#7ddc3a", 22.5, 26, 1.58);
				drop(c, "#b6f06a", 21.6, 28, 1.02);
				el$1(c, "#f2ffd8", 18, 28.5, 1.9, 4.2, .4);
				ci(c, "#7ddc3a", 36, 12, 4.2);
				ci(c, "#d6f59a", 35, 11, 1.7);
				if (!o.small) {
					ci(c, "#7ddc3a", 39.5, 22.5, 2.6);
					ci(c, "#3f8a1e", 20, 33.5, 1.5);
					ci(c, "#3f8a1e", 26, 30, 1.2);
				}
			}
		},
		wind: {
			zh: "旋風",
			d: (c, o) => {
				const curl = (x) => {
					x.moveTo(6.5, 29);
					x.bezierCurveTo(6, 11, 33, 6, 37, 18.5);
					x.bezierCurveTo(39.4, 27.5, 26.5, 31.5, 23.4, 24.2);
					x.bezierCurveTo(22, 20, 27, 17.6, 29.4, 20.4);
				};
				st$1(c, "#7fe0c0", 7, curl);
				st$1(c, "#7fe0c0", 5.6, (x) => {
					x.moveTo(11, 39.5);
					x.quadraticCurveTo(28, 44, 41, 33.5);
				});
				st$1(c, "#ffffff", 2, (x) => {
					x.moveTo(8.2, 24);
					x.bezierCurveTo(10, 13.5, 24, 9.5, 31.5, 13);
				});
				if (!o.small) st$1(c, "#dcfff1", 1.5, (x) => {
					x.moveTo(14, 38.6);
					x.quadraticCurveTo(26, 41.4, 35, 36.4);
				});
			}
		},
		earth: {
			zh: "岩石",
			d: (c, o) => {
				poly$1(c, "#b0814a", [
					[8.5, 34],
					[12, 17.5],
					[22.5, 8.5],
					[35.5, 12],
					[40.5, 26.5],
					[35.5, 38.5],
					[14, 39.5]
				], 1.4);
				poly$1(c, "#dab07a", [
					[12, 17.5],
					[22.5, 8.5],
					[35.5, 12],
					[25, 21.5]
				], .6);
				poly$1(c, "#7e5a30", [
					[25, 21.5],
					[35.5, 12],
					[40.5, 26.5],
					[35.5, 38.5],
					[27, 39.5]
				], .6);
				if (!o.small) {
					ln(c, "#5a3d1c", 1.4, [
						[25, 21.5],
						[20.5, 29],
						[23, 34]
					]);
					poly$1(c, "#f6dcb0", [
						[14.5, 19],
						[21.5, 12.6],
						[22.6, 14.4],
						[16, 20.6]
					]);
				}
			}
		},
		holy: {
			zh: "聖光",
			d: (c, _o) => {
				poly$1(c, "#e7a020", starPts(24, 24, 12.5, 6, 4, Math.PI / 4), .6);
				poly$1(c, "#ffd75e", starPts(24, 24, 20.5, 6.4, 4), .8);
				poly$1(c, "#fff6c8", starPts(24, 24, 12.5, 4, 4));
				ci(c, "#ffffff", 24, 24, 4.6);
			}
		},
		shadow: {
			zh: "暗月",
			d: (c, o) => {
				const moon = (x, R, r) => {
					x.arc(24, 24, R, .2417, 4.652, false);
					x.arc(30, 19, r, -2.137, .747, true);
					x.closePath();
				};
				f(c, "#b48aee", () => moon(c, 17, 13.8));
				c.save();
				c.beginPath();
				moon(c, 17, 13.8);
				c.clip();
				f(c, "#e6d2ff", () => c.ellipse(15, 22, 5.5, 13, .25, 0, TAU$1));
				f(c, "#7a4ec0", () => c.ellipse(27, 38, 13, 5, -.5, 0, TAU$1));
				c.restore();
				poly$1(c, "#e6d2ff", starPts(33.5, 16.5, 6.6, 2.5, 4), .3);
				if (!o.small) poly$1(c, "#ffffff", starPts(33.5, 16.5, 3, 1.2, 4));
			}
		},
		water: {
			zh: "水滴與波紋",
			d: (c, _o) => {
				const wave = (y, w) => st$1(c, "#4aa8ff", w, (x) => {
					x.moveTo(6.5, y);
					x.bezierCurveTo(12, y - 6.5, 18, y - 6.5, 24, y);
					x.bezierCurveTo(30, y + 6.5, 36, y + 6.5, 41.5, y);
				});
				wave(39, 6.4);
				wave(30.5, 6.8);
				st$1(c, "#cfe8ff", 1.8, (x) => {
					x.moveTo(8.5, 29);
					x.bezierCurveTo(12.5, 24.6, 17.5, 24.6, 22.5, 28.6);
				});
				drop(c, "#4aa8ff", 24, 14.5, 1.12);
				drop(c, "#8fd0ff", 23.4, 16, .7);
				el$1(c, "#ffffff", 21, 16.5, 1.4, 3, .4);
			}
		},
		arcane: {
			zh: "奧術晶石",
			d: (c, _o) => {
				poly$1(c, "#b8a8ff", [
					[24, 5.5],
					[36.5, 15],
					[36.5, 31],
					[24, 42.5],
					[11.5, 31],
					[11.5, 15]
				], .9);
				poly$1(c, "#ece6ff", [
					[24, 5.5],
					[11.5, 15],
					[24, 20.5]
				]);
				poly$1(c, "#d2c8ff", [
					[11.5, 15],
					[11.5, 31],
					[24, 20.5]
				]);
				poly$1(c, "#7a68c8", [
					[36.5, 15],
					[36.5, 31],
					[24, 42.5],
					[24, 20.5]
				]);
				poly$1(c, "#9a86ff", [
					[11.5, 31],
					[24, 42.5],
					[24, 20.5]
				]);
				poly$1(c, "#ffffff", starPts(24, 21, 5.6, 1.9, 4));
			}
		}
	});
	var eyes$1 = (c, x1, x2, y, rx, ry, col = OUT$2) => {
		el$1(c, col, x1, y, rx, ry);
		el$1(c, col, x2, y, rx, ry);
	};
	function spiritArt(c, o, T) {
		const body = (x) => {
			x.moveTo(24, 5.5);
			x.bezierCurveTo(35.5, 5.5, 39.5, 17, 36.5, 26);
			x.bezierCurveTo(34.5, 32.5, 37.5, 37, 42, 38.6);
			x.bezierCurveTo(33.5, 43.6, 23, 42.5, 16.5, 37.6);
			x.bezierCurveTo(7.5, 31, 7.5, 18.5, 13.5, 11.5);
			x.bezierCurveTo(16.5, 7.6, 20, 5.5, 24, 5.5);
			x.closePath();
		};
		f(c, T[0], () => body(c));
		c.save();
		c.beginPath();
		body(c);
		c.clip();
		f(c, T[1], () => c.ellipse(21, 17, 9.5, 8.6, -.3, 0, TAU$1));
		f(c, SH, () => c.ellipse(34, 36, 13, 6, .5, 0, TAU$1));
		c.restore();
		eyes$1(c, 19.5, 28, 20, 2.3, 3.3);
		if (!o.small) {
			ci(c, "#ffffff", 20.2, 18.8, .8);
			ci(c, "#ffffff", 28.7, 18.8, .8);
			st$1(c, OUT$2, 1.3, (x) => {
				x.moveTo(21.6, 26.4);
				x.quadraticCurveTo(24, 28.4, 26.4, 26.4);
			});
		}
	}
	function shadeArt(c, o, body, hood, eye) {
		const P = (x) => {
			x.moveTo(24, 4.5);
			x.bezierCurveTo(35.5, 4.5, 38.5, 15, 38.5, 25);
			x.lineTo(38.5, 42);
			x.lineTo(33.7, 37);
			x.lineTo(28.8, 42);
			x.lineTo(24, 37);
			x.lineTo(19.2, 42);
			x.lineTo(14.3, 37);
			x.lineTo(9.5, 42);
			x.lineTo(9.5, 25);
			x.bezierCurveTo(9.5, 15, 12.5, 4.5, 24, 4.5);
			x.closePath();
		};
		f(c, body, () => P(c));
		c.save();
		c.beginPath();
		P(c);
		c.clip();
		f(c, mix$1(body, "#ffffff", .4), () => c.rect(9, 4, 6.5, 40));
		f(c, SH, () => c.rect(32.5, 4, 7, 40));
		c.restore();
		el$1(c, hood, 24, 19.5, 9.6, 8.6);
		eyes$1(c, 20, 28, 19.5, 2.4, 3, eye);
		if (!o.small) eyes$1(c, 20, 28, 19.5, 1, 1.5, "#ffffff");
	}
	table()({
		spirit: {
			zh: "靈（元素之靈、火靈、冰靈、雷靈、水精）",
			d: (c, o, T) => spiritArt(c, o, T ?? TINT.arcane)
		},
		guardian: {
			zh: "守護靈",
			d: (c, o) => {
				for (const s of [-1, 1]) poly$1(c, "#fff6c8", [
					[24 + s * 9, 17],
					[24 + s * 21.5, 10],
					[24 + s * 20, 20],
					[24 + s * 22, 26],
					[24 + s * 15, 27.5],
					[24 + s * 9, 30]
				], .8);
				place(c, 24, 26.5, .8, (x) => spiritArt(x, o, ["#ffd75e", "#fff6c8"]));
				if (o.small) st$1(c, "#ffd23f", 3.2, (x) => x.ellipse(24, 7.7, 9.6, 3.4, 0, 0, TAU$1));
				else st$1(c, "#ffe9a8", 2.6, (x) => x.ellipse(24, 6.6, 8, 2.6, 0, 0, TAU$1));
			}
		},
		skeleton: {
			zh: "骷髏戰士",
			d: (c, o) => {
				rr$1(c, "#cfc8b0", 16.5, 27, 15, 12.5, 3.4);
				ci(c, "#e9e3cf", 24, 19.5, 14);
				f(c, HI2, () => c.ellipse(18, 12.5, 5, 3, -.5, 0, TAU$1));
				f(c, SH, () => {
					c.arc(24, 19.5, 14, -.9, 1.3);
					c.closePath();
				});
				eyes$1(c, 18.6, 29.4, 21, 3.6, 4.4, "#2a2230");
				poly$1(c, "#2a2230", [
					[24, 25],
					[26, 29.4],
					[22, 29.4]
				]);
				if (!o.small) for (const x of [
					20.4,
					24,
					27.6
				]) f(c, "#2a2230", () => c.rect(x - .5, 33, 1, 6));
				else f(c, "#2a2230", () => c.rect(18.6, 34.4, 10.8, 1.6));
			}
		},
		shade: {
			zh: "影魅、霧影",
			d: (c, o, T) => T && T[0] === TINT.ice[0] ? shadeArt(c, o, "#a8cfe6", "#2c4a66", "#f2fbff") : shadeArt(c, o, "#9a6ad8", "#2a1650", "#f0e0ff")
		},
		golem: {
			zh: "石像",
			d: (c, o) => {
				ci(c, "#8c8474", 9.5, 28, 6.5);
				ci(c, "#8c8474", 38.5, 28, 6.5);
				rr$1(c, "#9a9282", 10, 22.5, 28, 19, 5.5);
				rr$1(c, "#b4ac9a", 13, 6, 22, 19, 4.5);
				f(c, "#d6cfbe", () => c.roundRect(13, 6, 6, 19, [
					4.5,
					0,
					0,
					4.5
				]));
				f(c, SH, () => c.roundRect(30, 6, 5, 19, [
					0,
					4.5,
					4.5,
					0
				]));
				f(c, "#6e6656", () => c.rect(13, 11.5, 22, 3));
				rr$1(c, "#8ff0e2", 16.6, 15.6, 4.6, 4, 1);
				rr$1(c, "#8ff0e2", 26.8, 15.6, 4.6, 4, 1);
				if (!o.small) {
					ln(c, "#6e6656", 1.3, [
						[24, 26],
						[21.5, 31],
						[25, 35]
					]);
					f(c, "#c8c0ae", () => c.rect(12.5, 25, 5, 2));
				}
			}
		},
		bomb: {
			zh: "爆裂傀儡",
			d: (c, o) => {
				st$1(c, "#a06a36", 3, (x) => {
					x.moveTo(29, 15.5);
					x.quadraticCurveTo(31, 8.5, 37, 8);
				});
				poly$1(c, "#ffd23f", starPts(38.5, 7.5, 6, 2.6, 6), .3);
				ci(c, "#ffffff", 38.5, 7.5, 1.9);
				rr$1(c, "#8a8f99", 22.5, 11.5, 9, 6, 1.6);
				ci(c, "#c8553a", 22.5, 28, 14.5);
				f(c, "#e8826a", () => c.ellipse(16.5, 20.5, 6, 4, -.6, 0, TAU$1));
				f(c, SH, () => {
					c.arc(22.5, 28, 14.5, -.3, 1.9);
					c.closePath();
				});
				poly$1(c, "#fff6c8", [
					[14, 24.6],
					[21, 27],
					[20.4, 31.4],
					[14.6, 30.4]
				], .4);
				poly$1(c, "#fff6c8", [
					[31, 24.6],
					[24, 27],
					[24.6, 31.4],
					[30.4, 30.4]
				], .4);
				if (!o.small) ln(c, "#2a1c14", 1.5, [
					[16.5, 36],
					[19.5, 34],
					[22.5, 36],
					[25.5, 34],
					[28.5, 36]
				], "miter");
			}
		},
		wall: {
			zh: "土牆",
			d: (c, _o) => {
				for (const [x, y, w] of [
					[
						5,
						29.5,
						18.5
					],
					[
						24.5,
						29.5,
						18.5
					],
					[
						5,
						18,
						11.5
					],
					[
						17.5,
						18,
						17.5
					],
					[
						36,
						18,
						7
					],
					[
						9,
						6.5,
						14
					],
					[
						24,
						6.5,
						15
					]
				]) {
					rr$1(c, "#b0814a", x, y, w, 10.5, 2.2);
					f(c, "#dab07a", () => c.roundRect(x, y, w, 3.4, [
						2.2,
						2.2,
						0,
						0
					]));
					f(c, "#7e5a30", () => c.roundRect(x, y + 8, w, 2.5, [
						0,
						0,
						2.2,
						2.2
					]));
				}
				rr$1(c, "#7ab04a", 8, 4.6, 31.5, 3.6, 1.8);
			}
		},
		wolf: {
			zh: "戰狼",
			d: (c, o) => wolfHead(c, o, "#9aa3ad", "#6a737d", "#e6ebf0", "#ffd23f", false)
		},
		hawk: {
			zh: "鷹隼",
			d: (c, o) => {
				for (const s of [-1, 1]) {
					poly$1(c, "#a06a36", [
						[24 + s * 3, 18],
						[24 + s * 20.5, 7.5],
						[24 + s * 19, 17],
						[24 + s * 21.5, 20.5],
						[24 + s * 16.5, 26],
						[24 + s * 4, 29]
					], .8);
					poly$1(c, "#d8b078", [
						[24 + s * 4, 19.6],
						[24 + s * 18, 11],
						[24 + s * 16, 15.6],
						[24 + s * 5, 23]
					]);
				}
				poly$1(c, "#7e5a30", [
					[19.5, 30],
					[28.5, 30],
					[31.5, 41],
					[24, 37.5],
					[16.5, 41]
				], .7);
				el$1(c, "#a06a36", 24, 25, 5.6, 9.6);
				ci(c, "#f2ead8", 24, 14.5, 5.4);
				poly$1(c, "#f0b030", [
					[21.6, 16.5],
					[26.4, 16.5],
					[24, 22]
				], .3);
				if (!o.small) eyes$1(c, 21.8, 26.2, 13.6, .9, 1.1);
			}
		},
		whelp: {
			zh: "餘燼幼蜥",
			d: (c, o) => {
				const B = o.small ? "#ffb44e" : "#ff8a3a", sp = o.small ? "#fff3a8" : "#ffe14d";
				st$1(c, B, 4.4, (x) => {
					x.moveTo(15.5, 34);
					x.quadraticCurveTo(12.5, 42.5, 8.5, 36.5);
				});
				flame(c, "#ff6a1a", 8.6, 28.6, .66);
				flame(c, "#ffd23f", 8.8, 30.2, .38);
				for (const [x0, y0, x1, y1] of [
					[
						18.5,
						22.5,
						11.5,
						19
					],
					[
						26,
						31,
						29.5,
						38.5
					],
					[
						28.5,
						17.5,
						22.5,
						11.5
					],
					[
						31,
						24,
						38,
						27.5
					]
				]) st$1(c, "#e86a1a", 3.6, (x) => {
					x.moveTo(x0, y0);
					x.lineTo(x1, y1);
				});
				st$1(c, B, 9.5, (x) => {
					x.moveTo(15.5, 35);
					x.bezierCurveTo(18, 27, 26, 28, 30, 17.5);
				});
				for (const [x, y, r] of [
					[
						18,
						30.6,
						2.2
					],
					[
						23.2,
						27,
						2.4
					],
					[
						28,
						21.4,
						2.1
					]
				]) ci(c, sp, x, y, r);
				el$1(c, B, 33, 11.5, 7.6, 6.2, -.7);
				f(c, "#ffc078", () => c.ellipse(31, 9.6, 3.4, 2, -.7, 0, TAU$1));
				ci(c, "#fff6c8", 35.4, 9.6, 1.9);
				ci(c, OUT$2, 35.8, 9.6, .9);
			}
		},
		vine: {
			zh: "藤蔓",
			d: (c, o) => {
				const P = (x) => {
					x.moveTo(12.5, 42);
					x.bezierCurveTo(4, 22, 31, 31, 26.5, 15.5);
					x.bezierCurveTo(25, 9.5, 31.5, 5.5, 35.5, 9.5);
				};
				for (const [x, y, r] of [
					[
						13,
						27,
						2.4
					],
					[
						36,
						26,
						-.7
					],
					[
						18.5,
						12.5,
						-2.2
					]
				]) at$1(c, x, y, 1, (k) => {
					el$1(k, "#7ddc3a", 0, 0, 7.4, 4, 0);
					el$1(k, "#b6f06a", -1, -1, 4, 1.4, 0);
				}, r);
				st$1(c, "#4f9a28", 6.6, P);
				st$1(c, "#8fd858", 1.8, (x) => {
					x.moveTo(11.5, 37);
					x.bezierCurveTo(8, 25.5, 27, 30, 24.6, 17.5);
				});
				ci(c, "#e0405a", 36.6, 10.6, 4.4);
				ci(c, "#ffb0b8", 35.6, 9.4, 1.5);
				if (!o.small) for (const [x, y] of [[22.5, 26.5], [28.6, 21]]) poly$1(c, "#e9e3cf", [
					[x, y],
					[x + 4.4, y + 1.6],
					[x + .6, y + 3]
				]);
			}
		},
		totem: {
			zh: "圖騰（戰意、吸引、高台）",
			d: (c, o, T) => {
				totemPole(c, o);
				if (T) {
					rr$1(c, T[0], 16.5, 19.6, 15, 4.2, 1);
					f(c, T[1], () => c.rect(16.5, 19.6, 4.4, 4.2));
					ci(c, T[0], 24, 5.4, 3.8);
					ci(c, T[1], 23, 4.4, 1.4);
				}
			}
		}
	});
	/** 狼頭（戰狼與狼人共用骨架：狼人多獠牙、鬃毛、紅眼）。 */
	function wolfHead(c, o, fur, dark, light, eye, were) {
		for (const s of [-1, 1]) {
			poly$1(c, fur, [
				[24 + s * 14.5, were ? 2.5 : 5],
				[24 + s * 5, 14.5],
				[24 + s * 14.5, 22]
			], .8);
			poly$1(c, were ? "#3a2a36" : "#e0a0a8", [
				[24 + s * 12.6, 8],
				[24 + s * 8.6, 14.5],
				[24 + s * 12.6, 17.5]
			]);
		}
		if (were) for (const s of [-1, 1]) poly$1(c, dark, [
			[24 + s * 12, 20],
			[24 + s * 20.5, 23.5],
			[24 + s * 15, 27],
			[24 + s * 19.5, 32],
			[24 + s * 11, 33]
		], .6);
		poly$1(c, fur, [
			[10.5, 17],
			[24, 10.5],
			[37.5, 17],
			[38, 27],
			[30.5, 37.5],
			[24, 41.5],
			[17.5, 37.5],
			[10, 27]
		], 1.2);
		poly$1(c, mix$1(fur, "#ffffff", .35), [
			[10.5, 17],
			[24, 10.5],
			[24, 14],
			[14, 19.5],
			[13, 27],
			[10, 27]
		]);
		poly$1(c, light, [
			[18, 25.5],
			[30, 25.5],
			[29, 35.5],
			[24, 40.5],
			[19, 35.5]
		], .6);
		poly$1(c, "#2a2230", [
			[21.2, 34.6],
			[26.8, 34.6],
			[24, 38.4]
		], .5);
		poly$1(c, eye, [
			[14.5, 20.4],
			[21.4, 23.4],
			[20.6, 26],
			[15.4, 24.6]
		], .3);
		poly$1(c, eye, [
			[33.5, 20.4],
			[26.6, 23.4],
			[27.4, 26],
			[32.6, 24.6]
		], .3);
		if (!o.small) {
			ci(c, OUT$2, 18.6, 23.6, 1);
			ci(c, OUT$2, 29.4, 23.6, 1);
		}
		if (were) {
			poly$1(c, "#ffffff", [
				[19.4, 37.4],
				[22, 37.6],
				[20.4, 42.6]
			], .2);
			poly$1(c, "#ffffff", [
				[28.6, 37.4],
				[26, 37.6],
				[27.6, 42.6]
			], .2);
			f(c, dark, () => c.rect(13.5, 17.6, 21, 2));
		}
	}
	table()({
		bear: {
			zh: "熊",
			d: (c, o) => {
				for (const x of [12, 36]) {
					ci(c, "#8a5a32", x, 11.5, 6.2);
					ci(c, "#d8a878", x, 12, 3);
				}
				ci(c, "#a06a36", 24, 25.5, 16);
				f(c, "#bd8850", () => c.ellipse(17.5, 16.5, 7, 4.4, -.5, 0, TAU$1));
				f(c, SH, () => {
					c.arc(24, 25.5, 16, -.2, 1.7);
					c.closePath();
				});
				el$1(c, "#ecd2a8", 24, 31.5, 8.6, 6.8);
				el$1(c, "#2a1c14", 24, 28.6, 3.4, 2.4);
				eyes$1(c, 17, 31, 22, 2, 2.2, "#2a1c14");
				if (!o.small) {
					st$1(c, "#2a1c14", 1.3, (x) => {
						x.moveTo(24, 30.6);
						x.lineTo(24, 33.4);
						x.moveTo(21, 34.6);
						x.quadraticCurveTo(24, 36.6, 27, 34.6);
					});
					ci(c, "#ffffff", 17.5, 21.4, .7);
					ci(c, "#ffffff", 31.5, 21.4, .7);
				}
			}
		},
		cat: {
			zh: "貓",
			d: (c, o) => {
				for (const s of [-1, 1]) {
					poly$1(c, "#f5ad4e", [
						[24 + s * 15.5, 4.5],
						[24 + s * 4, 14],
						[24 + s * 14.5, 23]
					], .9);
					poly$1(c, "#ffc8c0", [
						[24 + s * 13.4, 8.6],
						[24 + s * 8, 14.5],
						[24 + s * 13, 18.5]
					]);
				}
				el$1(c, "#f5ad4e", 24, 27, 16, 13.5);
				f(c, "#ffc878", () => c.ellipse(16.5, 20.5, 6, 3.6, -.5, 0, TAU$1));
				for (const x of [
					20,
					24,
					28
				]) poly$1(c, "#d07a20", [
					[x - 1.2, 14.4],
					[x + 1.2, 14.4],
					[x, 19.6]
				]);
				el$1(c, "#fff6e6", 24, 33.4, 6.6, 4.4);
				poly$1(c, "#ff8a9a", [
					[22.2, 30.2],
					[25.8, 30.2],
					[24, 32.6]
				], .3);
				eyes$1(c, 17, 31, 26, 3, 3.4, "#b6f06a");
				eyes$1(c, 17, 31, 26, .9, 3, OUT$2);
				if (!o.small) for (const s of [-1, 1]) {
					ln(c, "#fff6e6", 1, [[24 + s * 7, 33], [24 + s * 16.5, 31]]);
					ln(c, "#fff6e6", 1, [[24 + s * 7, 35], [24 + s * 16, 36.6]]);
				}
			}
		},
		werewolf: {
			zh: "狼人",
			d: (c, o) => wolfHead(c, o, "#6f7a86", "#4a525c", "#c8d0d8", "#ff5a4a", true)
		},
		demon: {
			zh: "惡魔",
			d: (c, o) => {
				for (const s of [-1, 1]) f(c, "#e9e3cf", () => {
					c.moveTo(24 + s * 7, 15);
					c.quadraticCurveTo(24 + s * 9, 6, 24 + s * 19.5, 3.5);
					c.quadraticCurveTo(24 + s * 17.5, 12, 24 + s * 14.5, 17.5);
					c.closePath();
				});
				poly$1(c, "#d8453a", [
					[10.5, 15],
					[37.5, 15],
					[36.5, 28.5],
					[24, 43],
					[11.5, 28.5]
				], 2);
				poly$1(c, "#f07a66", [
					[11, 15.6],
					[22, 15.6],
					[14.5, 28],
					[12, 27.6]
				]);
				poly$1(c, SH, [
					[30.5, 15],
					[38.5, 15],
					[37.5, 29],
					[26, 42],
					[24, 43]
				]);
				poly$1(c, "#ffd23f", [
					[13.5, 20.6],
					[21.6, 24.6],
					[20.4, 27],
					[14.6, 25.4]
				], .3);
				poly$1(c, "#ffd23f", [
					[34.5, 20.6],
					[26.4, 24.6],
					[27.6, 27],
					[33.4, 25.4]
				], .3);
				f(c, "#3a0c0c", () => c.rect(18.4, 32, 11.2, 2.2));
				poly$1(c, "#ffffff", [
					[18.6, 32],
					[21.4, 32],
					[20, 36.4]
				]);
				poly$1(c, "#ffffff", [
					[26.6, 32],
					[29.4, 32],
					[28, 36.4]
				]);
				if (!o.small) {
					ci(c, OUT$2, 18.6, 24.4, .9);
					ci(c, OUT$2, 29.4, 24.4, .9);
				}
			}
		},
		dragon: {
			zh: "龍",
			d: (c, o) => {
				f(c, "#e9e3cf", () => {
					c.moveTo(15, 14);
					c.quadraticCurveTo(8, 12, 3.5, 4);
					c.quadraticCurveTo(13, 5, 21, 11.5);
					c.closePath();
				});
				poly$1(c, "#4fae5a", [
					[6.5, 22],
					[16.5, 11.5],
					[29, 12],
					[43, 21.5],
					[44, 27.5],
					[30, 29.5],
					[8.5, 31.5]
				], 1.3);
				poly$1(c, "#3a8a46", [
					[7, 30],
					[26, 30.5],
					[40, 34],
					[38, 39.6],
					[22, 41],
					[10, 38.6]
				], 1.3);
				poly$1(c, "#8fd88a", [
					[16.5, 11.5],
					[29, 12],
					[36, 16.6],
					[18, 16]
				]);
				poly$1(c, "#fff6c8", [
					[14, 30],
					[17, 35],
					[20, 30.2],
					[23, 35],
					[26, 30.4],
					[29, 35],
					[32, 30.6],
					[35, 34.6],
					[38, 31]
				]);
				el$1(c, "#ffd23f", 24.5, 20, 3.6, 3);
				el$1(c, OUT$2, 24.9, 20, 1.1, 2.6);
				ci(c, "#1e4a26", 39.6, 22.6, 1.3);
				if (!o.small) for (const x of [9.5, 13.5]) poly$1(c, "#e9e3cf", [
					[x, 21],
					[x + 2.8, 14.5],
					[x + 4.6, 20]
				]);
			}
		},
		elemental: {
			zh: "元素化身",
			d: (c, _o) => {
				st$1(c, "#c8f0ff", 2.6, (x) => x.arc(24, 25, 14, 0, TAU$1));
				poly$1(c, "#e8fbff", [
					[24, 13.5],
					[32, 25],
					[24, 36.5],
					[16, 25]
				], .8);
				poly$1(c, "#8fe3ff", [
					[24, 13.5],
					[32, 25],
					[24, 36.5]
				]);
				ci(c, "#ffffff", 21.6, 22, 1.8);
				ci(c, "#ff6a1a", 24, 9, 6.8);
				ci(c, "#ffd23f", 23, 8.4, 3);
				ci(c, "#4aa8ff", 10.5, 34, 6.8);
				ci(c, "#cfe8ff", 9.4, 33, 2.8);
				ci(c, "#fff36b", 37.5, 34, 6.8);
				ci(c, "#ffffff", 36.4, 33, 2.8);
			}
		},
		giant: {
			zh: "巨人",
			d: (c, o) => {
				const S = "#e0b488";
				f(c, S, () => {
					c.moveTo(4, 42);
					c.bezierCurveTo(2.5, 24, 9, 16, 17, 16);
					c.lineTo(31, 16);
					c.bezierCurveTo(39, 16, 45.5, 24, 44, 42);
					c.closePath();
				});
				c.save();
				c.beginPath();
				c.rect(0, 0, 48, 42);
				c.clip();
				f(c, mix$1(S, "#ffffff", .35), () => c.ellipse(11.5, 24, 5, 7.6, .3, 0, TAU$1));
				f(c, SH, () => c.ellipse(41, 34, 6.5, 14, -.15, 0, TAU$1));
				f(c, "#8a5a32", () => {
					c.moveTo(12, 16.5);
					c.lineTo(18, 16.5);
					c.lineTo(37, 42);
					c.lineTo(30, 42);
					c.closePath();
				});
				c.restore();
				const arms = (k) => {
					for (const s of [-1, 1]) {
						st$1(k, S, 8.4, (x) => {
							x.moveTo(24 + s * 15.5, 25);
							x.lineTo(24 + s * 17.5, 12.5);
						});
						ci(k, S, 24 + s * 17.2, 9.6, 5.6);
						f(k, mix$1(S, "#ffffff", .35), () => k.ellipse(24 + s * 17.2 - 1.6, 7.6, 2.4, 1.5, -.5, 0, TAU$1));
					}
				};
				if (o.small) halo(c, o, arms);
				else arms(c);
				poly$1(c, "#8a5a32", [
					[14.6, 15.5],
					[33.4, 15.5],
					[32.6, 25],
					[24, 32.5],
					[15.4, 25]
				], 1.6);
				ci(c, S, 24, 13.4, 9.2);
				f(c, mix$1(S, "#ffffff", .35), () => c.ellipse(20.4, 7.6, 3.6, 2, -.4, 0, TAU$1));
				poly$1(c, "#8a5a32", [
					[15.2, 17],
					[20, 18.6],
					[24, 17.4],
					[28, 18.6],
					[32.8, 17],
					[32.4, 25],
					[24, 32.5],
					[15.6, 25]
				], 1.2);
				f(c, "#b98048", () => c.ellipse(19.6, 22, 2, 3.4, .3, 0, TAU$1));
				rr$1(c, "#5e3b1f", 16.4, 9.8, 15.2, 3.2, 1.3);
				eyes$1(c, 20.2, 27.8, 14.8, 1.5, 1.7, "#2a1c14");
				if (!o.small) {
					el$1(c, "#c8946a", 24, 16.4, 1.9, 1.5);
					ci(c, "#e8bb48", 31.5, 36, 2.2);
				}
			}
		},
		roc: {
			zh: "巨鵰",
			d: (c, _o) => {
				poly$1(c, "#a06a36", [
					[6.5, 31],
					[28.5, 28],
					[29.5, 42],
					[17, 39.6],
					[8, 42]
				], 1.2);
				poly$1(c, "#7e5a30", [
					[9, 34.5],
					[13, 38.5],
					[17, 34.5],
					[21, 38.5],
					[25, 34.5],
					[27.6, 38],
					[28.5, 41.6],
					[9, 41.6]
				]);
				poly$1(c, "#f2ead8", [
					[9.5, 33],
					[8.5, 17.5],
					[17.5, 7.5],
					[29.5, 7.5],
					[36, 13.5],
					[35.5, 23],
					[28, 25],
					[27, 33]
				], 1.6);
				poly$1(c, "#ffffff", [
					[9.6, 18],
					[17.6, 8.6],
					[22, 8.6],
					[13.6, 19],
					[13, 30],
					[10.5, 30]
				]);
				f(c, "#f0b030", () => {
					c.moveTo(33.5, 12.5);
					c.quadraticCurveTo(45.5, 15, 44, 23);
					c.quadraticCurveTo(43, 29, 39.5, 31);
					c.quadraticCurveTo(39.6, 25, 33, 23.5);
					c.closePath();
				});
				f(c, "#c88a1a", () => {
					c.moveTo(33, 23.5);
					c.quadraticCurveTo(39.6, 25, 39.5, 31);
					c.quadraticCurveTo(37, 27, 33, 26);
					c.closePath();
				});
				ci(c, "#ffd23f", 26.5, 15.5, 3.3);
				ci(c, OUT$2, 27, 15.5, 1.6);
				f(c, "#7e5a30", () => {
					c.moveTo(20.5, 10.6);
					c.lineTo(31, 12.4);
					c.lineTo(30.6, 14);
					c.lineTo(20.5, 12.4);
					c.closePath();
				});
			}
		},
		shadow: {
			zh: "暗影形態",
			d: (c, _o) => {
				for (const [x, y, a] of [[
					8.6,
					22.5,
					-.35
				], [
					39.4,
					22.5,
					.35
				]]) at$1(c, x, y, 1, (k) => {
					flame(k, "#7a4ec0", 0, 0, .7);
					flame(k, "#c8a8ff", .2, 2, .36);
				}, a);
				const B = (x) => {
					x.moveTo(4.5, 43);
					x.bezierCurveTo(4.5, 32, 10, 27.5, 18.6, 26);
					x.lineTo(18.6, 22.5);
					x.bezierCurveTo(12.5, 18.5, 13, 4.5, 24, 4.5);
					x.bezierCurveTo(35, 4.5, 35.5, 18.5, 29.4, 22.5);
					x.lineTo(29.4, 26);
					x.bezierCurveTo(38, 27.5, 43.5, 32, 43.5, 43);
					x.closePath();
				};
				f(c, "#8a5ad0", () => B(c));
				c.save();
				c.beginPath();
				B(c);
				c.clip();
				f(c, "#b48aee", () => c.ellipse(17, 10, 5, 7.5, .5, 0, TAU$1));
				f(c, "#b48aee", () => c.ellipse(10, 33, 4, 7, .5, 0, TAU$1));
				f(c, "#5a3590", () => c.ellipse(36, 30, 9, 16, -.2, 0, TAU$1));
				f(c, "#5a3590", () => c.ellipse(24, 25, 6.5, 2.6, 0, 0, TAU$1));
				c.restore();
				poly$1(c, "#ffe14d", [
					[16.6, 12.4],
					[22.6, 15],
					[21.8, 17.6],
					[17.2, 16.4]
				], .3);
				poly$1(c, "#ffe14d", [
					[31.4, 12.4],
					[25.4, 15],
					[26.2, 17.6],
					[30.8, 16.4]
				], .3);
			}
		},
		treant: {
			zh: "樹人",
			d: (c, o) => {
				poly$1(c, "#8a5a32", [
					[15, 17],
					[33, 17],
					[35.5, 42.5],
					[29.5, 39],
					[24, 43],
					[18.5, 39],
					[12.5, 42.5]
				], 1);
				f(c, "#b98048", () => c.rect(15.5, 18, 4, 21));
				f(c, SH, () => c.rect(29, 18, 4.4, 21));
				for (const [x, y, r] of [
					[
						13.5,
						13.5,
						8.6
					],
					[
						34.5,
						13.5,
						8.6
					],
					[
						24,
						9.5,
						10
					]
				]) ci(c, "#4f9a28", x, y, r);
				for (const [x, y, r] of [
					[
						11.5,
						10.5,
						4
					],
					[
						21.5,
						5.6,
						4.6
					],
					[
						33,
						10.5,
						3.4
					]
				]) ci(c, "#8fd858", x, y, r);
				eyes$1(c, 20, 28, 26, 2.3, 2.8, "#ffe14d");
				f(c, "#2a1c14", () => c.ellipse(24, 33.5, 3.2, 2.4, 0, 0, TAU$1));
				if (!o.small) {
					eyes$1(c, 20, 28, 26, .8, 1.6, OUT$2);
					ci(c, "#e0405a", 36, 17.5, 1.8);
				}
			}
		}
	});
	var LIQUID = {
		earth: ["#f0b030", "#fff0b0"],
		water: ["#4aa8ff", "#cfe8ff"],
		poison: ["#7ddc3a", "#d6f59a"],
		holy: ["#ffd75e", "#fff6c8"],
		fire: ["#ff8a2a", "#ffd23f"]
	};
	/** 號角的中心線（二次曲線）：吹口在左下、喇叭口在右上；半寬從 1.9 漸寬到 7.6。 */
	var hornPt = (t) => {
		const [a, b, p] = [
			[6, 41],
			[8, 17],
			[28, 14]
		], u = 1 - t;
		return [u * u * a[0] + 2 * u * t * b[0] + t * t * p[0], u * u * a[1] + 2 * u * t * b[1] + t * t * p[1]];
	};
	var hornSide = (s) => {
		const P = [];
		for (let i = 0; i <= 16; i++) {
			const t = i / 16, [x, y] = hornPt(t), [x1, y1] = hornPt(Math.min(1, t + .01)), [x0, y0] = hornPt(Math.max(0, t - .01)), dx = x1 - x0, dy = y1 - y0, L = Math.hypot(dx, dy), w = 1.9 + 5.7 * t * t;
			P.push([x - dy / L * w * s, y + dx / L * w * s]);
		}
		return P;
	};
	var THINGS = table()({
		flask: {
			zh: "瓶",
			note: "陶瓶：圓肚、短頸、木塞、頸上一圈麻繩，瓶口流下一道液體（液體染色：油琥珀、水藍…）",
			d: (c, o, tint) => {
				const [L0, L1] = LIQUID[tint ?? ""] ?? LIQUID.water;
				at$1(c, 24, 24, 1, (q) => {
					q.translate(-24, -24);
					rr$1(q, "#d08050", 19, 9, 10, 13, 2);
					ci(q, "#d08050", 24, 30.5, 12.6);
					f(q, "#f0b080", () => q.ellipse(18.6, 25.4, 4.2, 6.2, .5, 0, TAU$1));
					f(q, SH, () => {
						q.arc(24, 30.5, 12.6, -.5, 1.9);
						q.arc(24, 30.5, 8.4, 1.9, -.5, true);
						q.closePath();
					});
					if (!o.small) f(q, "#e8a070", () => q.rect(20.2, 10, 2, 11));
					rr$1(q, "#e8a070", 17.6, 8.2, 12.8, 3.8, 1.8);
					rr$1(q, "#f2e6c8", 18.8, 15.2, 10.4, 2.6, 1);
					rr$1(q, "#e8c890", 19.6, 1.4, 8.8, 7.8, 1.8);
					f(q, "#fff0d0", () => q.rect(19.8, 2.2, 2.6, 5.8));
					f(q, L0, () => {
						q.moveTo(28.4, 9.4);
						q.quadraticCurveTo(33.6, 12, 33.4, 19);
						q.quadraticCurveTo(35.2, 25, 34.2, 30);
						q.lineTo(31.6, 29.6);
						q.quadraticCurveTo(32, 23, 30.4, 19.4);
						q.quadraticCurveTo(29.6, 13.6, 27.6, 12);
						q.closePath();
					});
					drop(q, L0, 33.2, 35.4, .5);
					if (!o.small) {
						el$1(q, L1, 32, 15.6, .8, 2.6, -.3);
						ci(q, L1, 32.4, 36.2, .9);
					}
				}, -.32);
			}
		},
		smoke_bomb: {
			zh: "煙霧彈",
			note: "紙包的圓彈（米褐色）、一道橫的深褐腰帶、頂上方的鐵口蓋，引信往左上、尾端一顆橘紅火星（第 2 版）",
			d: (c, o) => {
				st$1(c, "#4a3020", 2.8, (x) => {
					x.moveTo(20.6, 15);
					x.quadraticCurveTo(18.4, 9.6, 13.6, 9.2);
				});
				poly$1(c, "#ff6a1a", starPts(11.4, 8.4, 6.4, 2.6, 6, -.3), .4);
				poly$1(c, "#ffd23f", starPts(11.4, 8.4, 3.6, 1.5, 6, -.3));
				ci(c, "#ffffff", 11.4, 8.4, 1.3);
				ci(c, "#d8c8a0", 22, 29, 13.4);
				f(c, "#f2e6c8", () => c.ellipse(15.8, 23, 4.6, 3.2, -.6, 0, TAU$1));
				f(c, "rgba(90,70,40,0.32)", () => {
					c.arc(22, 29, 13.4, -.4, 2);
					c.arc(22, 29, 9, 2, -.4, true);
					c.closePath();
				});
				c.save();
				c.beginPath();
				c.arc(22, 29, 13.4, 0, TAU$1);
				c.clip();
				f(c, "#6a4420", () => {
					c.moveTo(8, 27.6);
					c.quadraticCurveTo(22, 35.4, 36, 27.6);
					c.lineTo(36, 32.2);
					c.quadraticCurveTo(22, 40, 8, 32.2);
					c.closePath();
				});
				if (!o.small) f(c, "#9a6a36", () => {
					c.moveTo(9, 28.6);
					c.quadraticCurveTo(22, 35.6, 35, 28.6);
					c.lineTo(35, 29.8);
					c.quadraticCurveTo(22, 36.8, 9, 29.8);
					c.closePath();
				});
				c.restore();
				rr$1(c, "#8d969f", 17.2, 13.4, 9.6, 4.2, 1);
				f(c, "#c3ccd6", () => c.rect(18.2, 14, 3, 1.4));
			}
		},
		roar: {
			zh: "吼聲（號角）",
			note: "象牙色的彎號角、金箍與金色喇叭口，口外兩道粗聲波",
			d: (c, o) => {
				const A = hornSide(1), B = hornSide(-1).reverse();
				poly$1(c, "#e9e3cf", [...A, ...B], .6);
				poly$1(c, "#b8ae92", [...hornSide(-1).slice(2).map(([x, y], _i) => [x, y]), ...hornSide(-.1).slice(2).reverse()]);
				for (const t of [.42, .7]) {
					const [x, y] = hornPt(t), [x1, y1] = hornPt(t + .02), a = Math.atan2(y1 - y, x1 - x), w = 1.9 + 5.7 * t * t + .9;
					at$1(c, x, y, 1, (q) => rr$1(q, "#e8bb48", -1.6, -w, 3.2, w * 2, 1), a);
				}
				const [bx, by] = hornPt(1), [px, py] = hornPt(.98), a = Math.atan2(by - py, bx - px);
				at$1(c, bx, by, 1, (q) => {
					el$1(q, "#e8bb48", 0, 0, 2.6, 8.4);
					el$1(q, "#7a5a1a", .6, 0, 1.3, 5.8);
				}, a);
				if (!o.small) ci(c, "#ffffff", 13.4, 25, 1.1);
				for (const [r, w] of [[6.4, 3], [11.6, 3.2]]) st$1(c, "#ffe9a8", w, (x) => x.arc(bx + 1, by, r + 3, a - .75, a + .75), "round");
			}
		},
		boot: {
			zh: "腳／靴",
			note: "踢出去的皮靴：靴尖朝右上、鋼包頭、深色鞋底，靴口一圈淺皮翻邊",
			d: (c, o) => at$1(c, 24, 24, 1, (q) => {
				q.translate(-24, -24);
				rr$1(q, M.leather, 11, 6, 14.6, 26, 4);
				f(q, M.leather, () => {
					q.moveTo(11, 22);
					q.lineTo(25, 22);
					q.quadraticCurveTo(40.6, 23, 41.6, 33.4);
					q.lineTo(41.6, 36.6);
					q.lineTo(11, 36.6);
					q.closePath();
				});
				f(q, "#c3ccd6", () => {
					q.moveTo(33, 24.6);
					q.quadraticCurveTo(41, 26.6, 41.6, 33.4);
					q.lineTo(41.6, 36.6);
					q.lineTo(33, 36.6);
					q.closePath();
				});
				f(q, "#ffffff", () => q.ellipse(36, 27.4, 2.2, 1.1, .4, 0, TAU$1));
				rr$1(q, "#4a3020", 9.6, 35.4, 33.4, 5.2, 2.2);
				if (!o.small) for (const x of [
					15,
					21,
					27,
					33,
					39
				]) ci(q, "#8d969f", x, 38, .9);
				rr$1(q, "#d8a868", 9.6, 4, 17.4, 6.6, 3);
				f(q, "#f2dcb0", () => q.rect(12, 4.8, 12, 1.8));
				f(q, HI, () => q.rect(14, 12, 2.4, 18));
				if (!o.small) ln(q, "#5e3b1f", 1.3, [[25, 22.4], [30.4, 22.8]]);
			}, -.5)
		},
		shoulder: {
			zh: "肩撞",
			note: "米白人形全身側影往右上衝（身體前傾、跨步、手臂收在胸前），頭在最上面，前肩一片比頭小的弧形鋼肩甲（圓頂朝右上），背後兩道速度線（第 2 版）",
			d: (c, o) => {
				const CR = "#f2e6c8", CRD = "#d8ccae";
				if (!o.small) for (const [y, w] of [[19, 6], [26, 4.6]]) rr$1(c, CR, 3, y, w, 2.4, 1.2);
				st$1(c, CRD, 6.4, (x) => {
					x.moveTo(17.6, 31);
					x.lineTo(10.4, 40.6);
				});
				st$1(c, CR, 6.6, (x) => {
					x.moveTo(18.6, 32);
					x.lineTo(27.6, 36.4);
					x.lineTo(25.8, 43.4);
				});
				st$1(c, CR, 12.4, (x) => {
					x.moveTo(17.6, 30.4);
					x.lineTo(31, 22.2);
				});
				halo(c, o, (x) => st$1(x, CR, 5, (q) => {
					q.moveTo(30.6, 26);
					q.lineTo(34.6, 32.4);
					q.lineTo(39.4, 29.6);
				}));
				halo(c, o, (x) => {
					ci(x, CR, 26, 10.6, 6.6);
					if (!o.small) f(x, "#ffffff", () => x.ellipse(23.6, 8.2, 2.2, 1.3, -.6, 0, TAU$1));
				});
				halo(c, o, (x) => at$1(x, 34, 21, 1, (q) => {
					f(q, "#9aa4b0", () => {
						q.moveTo(-5.6, .4);
						q.quadraticCurveTo(0, 2.8, 5.6, .4);
						q.lineTo(5, 3.4);
						q.quadraticCurveTo(0, 6, -5, 3.4);
						q.closePath();
					});
					f(q, "#7d8794", () => {
						q.moveTo(-5, 2.6);
						q.quadraticCurveTo(0, 5, 5, 2.6);
						q.lineTo(5, 3.4);
						q.quadraticCurveTo(0, 6, -5, 3.4);
						q.closePath();
					});
					f(q, "#c3ccd6", () => {
						q.ellipse(0, .4, 6.2, 5, 0, Math.PI, 0);
						q.quadraticCurveTo(0, 2.6, -6.2, .4);
						q.closePath();
					});
					f(q, "#ffffff", () => q.ellipse(-1.8, -2.4, 2.6, 1.1, -.2, 0, TAU$1));
				}, Math.PI / 3.2));
			}
		},
		fang: {
			zh: "獠牙",
			note: "暗紅的下顎肉一彎，兩根往上彎的大象牙色獠牙，中間一排小牙",
			d: (c, o) => {
				f(c, "#a83a3a", () => {
					c.moveTo(4.6, 30);
					c.quadraticCurveTo(24, 46, 43.4, 30);
					c.lineTo(43.4, 36.4);
					c.quadraticCurveTo(24, 50, 4.6, 36.4);
					c.closePath();
				});
				f(c, "#e06a5a", () => {
					c.moveTo(6, 30.8);
					c.quadraticCurveTo(24, 45.4, 42, 30.8);
					c.lineTo(42, 32.6);
					c.quadraticCurveTo(24, 47, 6, 32.6);
					c.closePath();
				});
				if (!o.small) for (const x of [
					19,
					24,
					29
				]) poly$1(c, "#f2ecd8", [
					[x - 2, 38.2],
					[x, 33.8],
					[x + 2, 38.2]
				], .3);
				for (const s of [-1, 1]) {
					const X = (v) => 24 + s * v;
					f(c, "#f2ecd8", () => {
						c.moveTo(X(9.6), 36.4);
						c.quadraticCurveTo(X(17), 22, X(9.6), 4);
						c.quadraticCurveTo(X(9), 18, X(3), 34.4);
						c.closePath();
					});
					f(c, s < 0 ? "#ffffff" : "#c8bfa0", () => {
						c.moveTo(X(8.6), 34);
						c.quadraticCurveTo(X(13.6), 22, X(9.6), 5.6);
						c.quadraticCurveTo(X(11.4), 20, X(6.4), 34.4);
						c.closePath();
					});
				}
			}
		},
		slime: {
			zh: "黏液",
			note: "一團洋紅色的黏液：圓頂、底下攤開成同色的一灘，團裡兩顆氣泡、左上亮點（第 2 版）",
			d: (c, o) => {
				const B = (x) => {
					x.moveTo(9, 41.8);
					x.quadraticCurveTo(4.2, 41.6, 4.6, 35.6);
					x.bezierCurveTo(5, 21.4, 13.4, 13, 22.6, 13.2);
					x.bezierCurveTo(31.4, 13.4, 36.4, 20.6, 36.4, 29.8);
					x.quadraticCurveTo(38, 34, 42.6, 35.4);
					x.quadraticCurveTo(46.2, 40.4, 41, 41.8);
					x.closePath();
				};
				const P = "#e05ab8", PL = "#ffb4ec", PD = "#9a2c7c";
				f(c, P, B);
				c.save();
				c.beginPath();
				B(c);
				c.clip();
				f(c, PD, () => c.ellipse(28, 41, 18, 4.2, -.06, 0, TAU$1));
				f(c, PD, () => c.ellipse(35.4, 27, 3.4, 9, .12, 0, TAU$1));
				c.restore();
				f(c, PL, () => c.ellipse(13.6, 20.4, 4.6, 3, -.8, 0, TAU$1));
				f(c, "#ffffff", () => c.ellipse(12.6, 19.4, 2, 1.1, -.8, 0, TAU$1));
				ci(c, PL, 25, 27, 3.2);
				ci(c, "#ffffff", 24.2, 26.2, 1.1);
				if (!o.small) {
					ci(c, PL, 16.4, 32.4, 1.8);
					f(c, PL, () => c.ellipse(40, 37.6, 2.2, .8, .3, 0, TAU$1));
				}
			}
		}
	});
	/** 一對短楔形（直線突刺、飛刃）：退到握把那一端的兩側、朝右上；底色用元素底的亮色（soft），中間一道細的亮芯，不用純白，長度是第 1 版的四成。
	*  寬度沒有再縮：規則 10 要最粗處 ≥ 顯示邊長 12%（底寬 11 單位），再窄就是細線。 */
	var wedges = (c, soft, A, core = .6) => {
		for (const [x, y] of [[4.6, 29.4], [18.6, 43.4]]) {
			poly$1(c, rgba(soft, .95), [
				[x - 3.9, y - 3.9],
				[x + 3.9, y + 3.9],
				[x + 11.5, y - 11.5]
			], .8);
			poly$1(c, rgba(A, core), [
				[x - .9, y - 2.3],
				[x + 1.4, y],
				[x + 7.6, y - 7.6]
			]);
		}
	};
	table()({
		swing: {
			zh: "揮砍",
			note: "一彎弧形刀光橫過作用端",
			d: (c, _o, A) => {
				f(c, rgba(A, .95), () => {
					c.moveTo(4.5, 25);
					c.quadraticCurveTo(24, -12, 46, 19);
					c.quadraticCurveTo(26, 6.5, 4.5, 25);
					c.closePath();
				});
				f(c, "#ffffff", () => {
					c.moveTo(11, 17.5);
					c.quadraticCurveTo(25, -3, 41.5, 13.6);
					c.quadraticCurveTo(26, 2.6, 11, 17.5);
					c.closePath();
				});
			}
		},
		thrust: {
			zh: "直線突刺",
			note: "握把那一端兩側各一道短楔形（元素底的亮色，不用白）",
			d: (c, _o, A, p) => p.weapon ? wedges(c, p.dim ?? A, A, .4) : wedges(c, p.soft ?? A, A)
		},
		sweep: {
			zh: "扇形橫掃",
			note: "從左下張開的扇面與亮邊",
			d: (c, _o, A) => {
				f(c, rgba(A, .5), () => {
					c.moveTo(5, 43);
					c.arc(5, 43, 40, -1.72, .14);
					c.closePath();
				});
				st$1(c, rgba(A, .98), 7, (x) => x.arc(5, 43, 36.5, -1.6, .02), "butt");
				st$1(c, "#ffffff", 2.2, (x) => x.arc(5, 43, 38, -1.5, -.5), "butt");
			}
		},
		spin: {
			zh: "迴旋",
			note: "繞一圈的粗圓弧加箭頭",
			d: (c, _o, A) => {
				st$1(c, rgba(A, .98), 7, (x) => x.arc(24, 24, 19.5, -.5, 4.2), "butt");
				st$1(c, "#ffffff", 2.2, (x) => x.arc(24, 24, 21, 1.2, 3.6), "butt");
				at$1(c, 24 + Math.cos(-.5) * 19.5, 24 + Math.sin(-.5) * 19.5, 1, (k) => poly$1(k, A, [
					[-7.5, 0],
					[7.5, 0],
					[0, -9.5]
				], .5), -.5 + Math.PI);
			}
		},
		shot: {
			zh: "射出",
			note: "元素道具後面拖一條粗彗尾；飛刃是兩側的短楔形；弓、弩、槍不畫出手線（作用端外側的閃光或記號就是射出去的那一下）",
			d: (c, _o, A, p) => {
				if (p.weapon) return;
				if (p.noTail) return;
				if (p.projectile) wedges(c, p.soft ?? A, A);
				else {
					const w = p.size * .25;
					poly$1(c, rgba(A, .95), [
						[p.x - w, p.y - w * .2],
						[p.x + w * .2, p.y + w],
						[1.5, 46.5]
					], .4);
					poly$1(c, "#ffffff", [
						[p.x - w * .55, p.y + w * .1],
						[p.x - w * .1, p.y + w * .55],
						[6, 42]
					]);
				}
			}
		},
		area: {
			zh: "範圍爆發",
			note: "道具後面一大片尖角爆開",
			d: (c, _o, A) => {
				poly$1(c, rgba(A, .62), starPts(24, 24, 23.5, 15.5, 10, -Math.PI / 2 + .31));
				poly$1(c, "rgba(255,255,255,0.55)", starPts(24, 24, 16.5, 11.5, 10, -Math.PI / 2 + .31));
			}
		},
		chain: {
			zh: "連鎖",
			note: "粗折線跳到第二個火花（包外框，畫在主體裡）",
			d: () => {}
		},
		place: {
			zh: "落點",
			note: "腳下一片發亮的圓地",
			d: (c, _o, A) => {
				el$1(c, rgba(A, .6), 24, 40.5, 21, 6.4);
				el$1(c, "rgba(255,255,255,0.7)", 24, 40.5, 13.5, 3.4);
			}
		},
		aura: {
			zh: "自身光環",
			note: "道具外面一圈粗光環",
			d: (c, _o, A, p) => {
				st$1(c, rgba(A, .5), 8.6, (x) => x.arc(p.x, p.y, Math.min(19.2, 20.6 - Math.max(Math.abs(p.x - 24), Math.abs(p.y - 24))), 0, TAU$1));
			}
		}
	});
	/** 衝刺的兩個 V（後面那個、前面那個的顏色）。預設米黃＋白；配肩撞時換成元素底的亮色（11-12 補道具第 2 版：米白 V 和米白人形黏成火箭）。 */
	var dashV = (c, cols) => {
		c.rotate(-Math.PI / 4);
		c.scale(.82, .82);
		for (const [x, col] of [[-5.8, cols[0]], [3.4, cols[1]]]) poly$1(c, col, [
			[x - 5.4, -7.8],
			[x + 2.6, -7.8],
			[x + 9, 0],
			[x + 2.6, 7.8],
			[x - 5.4, 7.8],
			[x + 1, 0]
		], .5);
	};
	var arrow = (c, col, hi) => {
		poly$1(c, col, [
			[-10.5, -3.6],
			[-.5, -3.6],
			[-.5, -9.6],
			[10.5, 0],
			[-.5, 9.6],
			[-.5, 3.6],
			[-10.5, 3.6]
		], .5);
		poly$1(c, hi, [
			[-10.5, -3.6],
			[-.5, -3.6],
			[-.5, -9.6],
			[10.5, 0],
			[-10.5, 0]
		]);
	};
	var ACT = table()({
		hit: {
			zh: "傷害",
			side: "tr",
			note: "作用端一顆白色四芒閃光",
			d: (c, _o, T) => {
				poly$1(c, T[0], starPts(0, 0, 10.5, 3.6, 4), .4);
				poly$1(c, "#ffffff", starPts(0, 0, 6, 2.2, 4));
			},
			def: ["#ffffff", "#ffffff"]
		},
		combo: {
			zh: "追擊／連擊",
			side: "tr",
			note: "一大一小兩顆四芒閃光（大的白、小的染條件色）＝打兩下",
			d: (c, o, T) => {
				poly$1(c, "#ffffff", starPts(-2, -2, 9.2, 3.6, 4), .4);
				halo(c, o, (x) => {
					poly$1(x, T[0], starPts(4.2, 4.2, 7, 2.9, 4), .4);
					poly$1(x, T[1], starPts(4.2, 4.2, 3.3, 1.4, 4));
				}, OUT$2, .6);
			},
			def: ["#ffd23f", "#fff6c8"]
		},
		finisher: {
			zh: "終結",
			side: "tr",
			note: "一顆骷髏頭、紅眼",
			d: (c) => {
				rr$1(c, "#cfc8b0", -5.8, 3, 11.6, 8.2, 2.6);
				ci(c, "#f2ecd8", 0, -1.6, 9.6);
				f(c, "#ffffff", () => c.ellipse(-3.4, -6.6, 3.6, 2, -.5, 0, TAU$1));
				eyes$1(c, -3.8, 3.8, -.6, 2.9, 3.4, "#c8202a");
				poly$1(c, "#2a1c36", [
					[0, 3],
					[1.6, 6.2],
					[-1.6, 6.2]
				]);
				f(c, "#2a1c36", () => c.rect(-.5, 7.4, 1, 3.8));
			}
		},
		builder: {
			zh: "蓄積／蓄力",
			side: "bl",
			note: "三根越來越高的粗條",
			d: (c, _o, T) => {
				for (const [x, h] of [
					[-10.8, 8],
					[-3.5, 13.5],
					[3.8, 19.5]
				]) {
					rr$1(c, T[0], x, 9.6 - h, 6.8, h, 1.6);
					f(c, T[1], () => c.roundRect(x, 9.6 - h, 6.8, 3, [
						1.6,
						1.6,
						0,
						0
					]));
				}
			},
			def: ["#e8bb48", "#fff6c8"]
		},
		step: {
			zh: "瞬步",
			side: "self",
			note: "道具左下拖兩道紫色殘影，作用端一顆白閃光",
			d: () => {}
		},
		dash: {
			zh: "衝刺／跳躍",
			side: "bl",
			note: "兩個朝右上的粗 V 形箭頭",
			d: (c) => dashV(c, ["#ffe9a8", "#ffffff"])
		},
		knockdown: {
			zh: "擊倒",
			side: "tr",
			note: "黃色七角撞擊星壓在一條地面線上",
			d: (c) => {
				rr$1(c, "#b8862a", -11, 6.4, 22, 4.6, 2);
				poly$1(c, "#ffd23f", starPts(0, -1, 10.5, 5, 7, -1.2), .4);
				poly$1(c, "#ffffff", starPts(0, -1, 5, 2.5, 7, -1.2));
			}
		},
		push: {
			zh: "推開",
			side: "tr",
			note: "朝右上的黃白粗箭頭",
			d: (c) => {
				c.rotate(-Math.PI / 4);
				arrow(c, "#ffd23f", "#ffffff");
			}
		},
		pull: {
			zh: "拉近",
			side: "tr",
			note: "朝左下（往道具）的青色粗箭頭，尾端一個圓鉤",
			d: (c) => {
				c.rotate(Math.PI * .75);
				ci(c, "#6ae0ff", -9.5, 0, 4.6);
				arrow(c, "#6ae0ff", "#d8f8ff");
				ci(c, "#0b2f4e", -9.5, 0, 1.6);
			}
		},
		slow: {
			zh: "緩速",
			side: "tr",
			note: "一只懷錶（金殼、白面、兩根指針、頂上錶冠與提環）",
			d: (c) => {
				st$1(c, "#e8bb48", 2, (x) => x.arc(0, -8.5, 2, 0, TAU$1));
				rr$1(c, "#b8862a", -2.1, -7.6, 4.2, 3.6, 1);
				ci(c, "#e8bb48", 0, 2.4, 9);
				f(c, "#b8862a", () => {
					c.arc(0, 2.4, 9, -.2, 1.8);
					c.arc(0, 2.4, 6.3, 1.8, -.2, true);
					c.closePath();
				});
				ci(c, "#fff6e0", 0, 2.4, 6.3);
				f(c, "#ffffff", () => c.ellipse(-2.3, -.3, 2.5, 1.5, -.6, 0, TAU$1));
				ln(c, "#2a1c36", 1.9, [
					[0, -2.4],
					[0, 2.4],
					[3.5, 4.3]
				]);
				ci(c, "#2a1c36", 0, 2.4, 1.2);
			}
		},
		bind: {
			zh: "控制（冰凍、定身、暈眩、沉默）",
			side: "tr",
			note: "一把鎖（染狀態色）；緩速另用懷錶",
			d: (c, _o, T) => {
				st$1(c, T[1], 4.8, (x) => x.arc(0, -3, 5.2, Math.PI, 0), "butt");
				rr$1(c, T[0], -8.6, -3, 17.2, 13.4, 3.2);
				f(c, T[1], () => c.roundRect(-8.6, -3, 17.2, 4, [
					3.2,
					3.2,
					0,
					0
				]));
				ci(c, OUT$2, 0, 3, 2.3);
				f(c, OUT$2, () => c.rect(-1.1, 3.4, 2.2, 4.2));
			},
			def: ["#ffd84a", "#fff6c8"]
		},
		mark: {
			zh: "標記",
			side: "tr",
			note: "紅色空心環、上下左右四個缺口、中心一顆紅點（準星）",
			d: (c) => {
				ci(c, OUT$2, 0, 0, 8.4);
				for (let i = 0; i < 4; i++) st$1(c, "#ff4a5a", 4.4, (x) => x.arc(0, 0, 9.3, i * Math.PI / 2 + .13, (i + 1) * Math.PI / 2 - .13), "butt");
				st$1(c, "#ffc0c4", 1.5, (x) => x.arc(0, 0, 10, Math.PI + .3, Math.PI * 1.5 - .3), "butt");
				ci(c, "#ff4a5a", 0, 0, 3.5);
				ci(c, "#ffc0c4", -.9, -.9, 1.3);
			}
		},
		curse: {
			zh: "減益（虛弱、易傷、恐懼、致盲、挑釁）",
			side: "tr",
			note: "朝下的粗箭頭加一條頂槓（染狀態色；和增益的朝上箭頭相反）",
			d: (c, _o, T) => {
				poly$1(c, T[0], [
					[0, 11],
					[10, 1],
					[4, 1],
					[4, -4.4],
					[-4, -4.4],
					[-4, 1],
					[-10, 1]
				], .6);
				poly$1(c, T[1], [
					[-4, -4.4],
					[0, -4.4],
					[0, 11],
					[-10, 1],
					[-4, 1]
				]);
				rr$1(c, T[0], -4.6, -10.8, 9.2, 4.4, 1.6);
			},
			def: ["#9a6ad8", "#d2b0ff"]
		},
		dot: {
			zh: "持續傷害（燃燒、中毒、流血）",
			side: "tr",
			note: "燃燒是一團火，中毒與流血是一大一小兩滴；道具是武器時只留一顆、縮小、放在作用端外側",
			d: (c, _o, T, t, one) => {
				if (t === "fire") {
					flame(c, "#ff6a1a", 0, 0, 1.08);
					flame(c, "#ffd23f", .4, 2.6, .64);
				} else if (one) {
					drop(c, T[0], 0, 0, 1.12);
					f(c, T[1], () => c.ellipse(-2.6, 2.4, 1.9, 3.8, .4, 0, TAU$1));
				} else {
					drop(c, T[0], -2.6, 1, .98);
					f(c, T[1], () => c.ellipse(-5, 3, 1.6, 3.4, .4, 0, TAU$1));
					drop(c, T[0], 6.6, -5, .52);
				}
			},
			def: TINT.poison
		},
		heal: {
			zh: "治療",
			side: "bl",
			note: "綠色粗十字",
			d: (c) => {
				rr$1(c, "#4fd07a", -3.7, -10.5, 7.4, 21, 2.2);
				rr$1(c, "#4fd07a", -10.5, -3.7, 21, 7.4, 2.2);
				f(c, "#c8ffd8", () => c.roundRect(-3.7, -10.5, 7.4, 5, [
					2.2,
					2.2,
					0,
					0
				]));
				f(c, "#c8ffd8", () => c.roundRect(-10.5, -3.7, 6.8, 3, [
					2.2,
					0,
					0,
					0
				]));
				f(c, "#ffffff", () => c.rect(-2.4, -9, 1.6, 6));
			}
		},
		shield: {
			zh: "護盾",
			side: "bl",
			note: "淡藍小盾",
			d: (c, _o, T) => {
				poly$1(c, T[0], [
					[-9.4, -9.6],
					[9.4, -9.6],
					[8.8, 2],
					[0, 10],
					[-8.8, 2]
				], 1);
				poly$1(c, T[1], [
					[-9.4, -9.6],
					[0, -9.6],
					[0, 10],
					[-8.8, 2]
				], 1);
				rr$1(c, "#ffffff", -1.4, -7, 2.8, 13, 1);
				rr$1(c, "#ffffff", -6, -3.4, 12, 2.8, 1);
			},
			def: ["#6ab8f0", "#cfe8ff"]
		},
		buff: {
			zh: "增益",
			side: "bl",
			note: "朝上的粗箭頭加一條底槓",
			d: (c, _o, T) => {
				poly$1(c, T[0], [
					[0, -11],
					[10, -1],
					[4, -1],
					[4, 4.4],
					[-4, 4.4],
					[-4, -1],
					[-10, -1]
				], .6);
				poly$1(c, T[1], [
					[0, -11],
					[-10, -1],
					[-4, -1],
					[-4, 4.4],
					[0, 4.4]
				]);
				rr$1(c, T[0], -4.6, 6.4, 9.2, 4.4, 1.6);
			},
			def: ["#ffb23a", "#fff6c8"]
		},
		summon: {
			zh: "召喚",
			side: "tr",
			note: "一隻小小的靈（染召喚物的元素色；道具已經是召喚物時不畫，改成腳下的落點）",
			d: (c, o, T) => {
				c.save();
				c.scale(.5, .5);
				c.translate(-24.6, -24);
				spiritArt(c, {
					...o,
					small: true
				}, T);
				c.restore();
			},
			def: ["#5fd8c8", "#dcfff8"]
		},
		transform: {
			zh: "化身",
			side: "self",
			note: "頭像兩側各一道繞圈的粗弧箭頭",
			d: () => {}
		},
		surface: {
			zh: "地面效果（火、水、冰、毒、油、煙、暗、聖）與地形／障礙",
			side: "tr",
			note: "液體（水、毒、油）：一灘扁平的水漬上面落下一大滴；聖光：地上一圈光；煙、暗霧：兩團雲；冰：薄冰加冰刺；火：餘燼上三撮火苗；地形／障礙（灰石色）：地上兩塊石頭",
			d: (c, o, T, t) => {
				if (t === "stone") {
					el$1(c, "#8c8474", 0, 7.6, 11.6, 3.8);
					poly$1(c, T[0], [
						[-9, 7.6],
						[-7.6, -3],
						[-1.6, -9.2],
						[5.4, -5],
						[7, 7.6]
					], 1.2);
					poly$1(c, T[1], [
						[-7.4, -3],
						[-1.6, -9],
						[5.2, -5],
						[-1, -1.4]
					], .5);
					poly$1(c, "#8c8474", [
						[-1, -1.4],
						[5.3, -4.8],
						[6.8, 7.4],
						[.4, 7.4]
					], .5);
					poly$1(c, T[0], [
						[3.2, 8],
						[4.8, 1.8],
						[9.2, .8],
						[10.4, 8]
					], 1);
					poly$1(c, T[1], [
						[5, 2],
						[9, 1.1],
						[8.4, 3.8],
						[5.8, 4.4]
					], .3);
					return;
				}
				const dk = mix$1(T[0], "#16121a", .3);
				if (t === "holy") {
					el$1(c, T[0], 0, 4.4, 11.6, 6.6);
					el$1(c, T[1], 0, 3.2, 10.2, 4.8);
					el$1(c, "#c8861a", 0, 4.6, 6.4, 2.7);
					halo(c, o, (x) => {
						poly$1(x, T[0], starPts(0, -6.6, 5, 1.9, 4), .3);
						poly$1(x, "#ffffff", starPts(0, -6.6, 2.6, 1, 4));
					}, OUT$2, .5);
					return;
				}
				if (t === "steel" || t === "shadow") {
					const cloud = (c2, col, hi, x, y, k) => at$1(c2, x, y, k, (q) => {
						ci(q, col, -4.6, 1.6, 4.4);
						ci(q, col, .6, -1.4, 5.6);
						ci(q, col, 5.6, 2, 3.8);
						rr$1(q, col, -9, 1.6, 18.4, 4.8, 2.4);
						if (hi) el$1(q, hi, -.6, -3.6, 3.2, 1.5, -.3);
					});
					cloud(c, mix$1(T[0], "#16121a", .2), null, 4.6, -4.4, .72);
					halo(c, o, (x) => {
						cloud(x, T[0], T[1], -2.2, 3.6, 1);
						f(x, dk, () => x.roundRect(-11.2, 7.6, 18.4, 2.4, [
							0,
							0,
							2.4,
							2.4
						]));
					}, OUT$2, .6);
					return;
				}
				if (t === "ice") {
					poly$1(c, T[0], [
						[-10.7, 6.6],
						[-7, 3],
						[4, 2.2],
						[10.7, 5.8],
						[8, 9.8],
						[-5.4, 10.2]
					], .8);
					poly$1(c, T[1], [
						[-9, 6.4],
						[-6.4, 4],
						[3.2, 3.4],
						[-2, 6.6]
					], .3);
					poly$1(c, dk, [
						[10.2, 6.2],
						[7.8, 9.4],
						[-5, 9.8],
						[1, 7.6]
					], .3);
					poly$1(c, T[0], [
						[-7.6, 5.4],
						[-4.2, -6.4],
						[-.6, 5.4]
					], .5);
					poly$1(c, T[0], [
						[-.4, 5.6],
						[4.6, -10.6],
						[8.6, 5.6]
					], .5);
					poly$1(c, T[1], [
						[-7, 5.2],
						[-4.2, -5.4],
						[-4.2, 5.2]
					]);
					poly$1(c, T[1], [
						[.4, 5.4],
						[4.6, -9.4],
						[4.6, 5.4]
					]);
					return;
				}
				if (t === "fire") {
					el$1(c, "#8a3410", 0, 7.8, 11.6, 3.4);
					el$1(c, "#c2531c", -1, 7, 8.6, 1.5);
					for (const [x, y, k] of [
						[
							-6.6,
							2.6,
							.5
						],
						[
							6.4,
							3,
							.46
						],
						[
							0,
							-.6,
							.72
						]
					]) {
						flame(c, T[0], x, y, k);
						flame(c, T[1], x + .2, y + 2.6 * k, k * .55);
					}
					return;
				}
				el$1(c, T[0], 0, 6.6, 11.6, 4.5);
				ci(c, T[0], -8.3, 5.4, 3.2);
				ci(c, T[0], 8.2, 7.6, 3.2);
				el$1(c, T[0], 4.4, 4.2, 4.6, 2.6);
				el$1(c, T[1], -2.6, 6, 5.6, 1.5);
				drop(c, T[0], -2.4, -4.6, .7);
				f(c, T[1], () => c.ellipse(-3.6, -3.4, 1.2, 2.5, .4, 0, TAU$1));
			},
			def: TINT.water
		},
		trap: {
			zh: "陷阱／符文",
			side: "tr",
			note: "張開的捕獸夾（正面看）：一條深色底板上四根朝上的鋼牙，左右對稱",
			d: (c) => {
				for (const x of [
					-7.8,
					-2.6,
					2.6,
					7.8
				]) {
					poly$1(c, "#f2f5f8", [
						[x - 2.9, 6.4],
						[x, -10.8],
						[x + 2.9, 6.4]
					], .4);
					poly$1(c, "#aab3bd", [
						[x, -9.6],
						[x + 2.7, 6.4],
						[x, 6.4]
					]);
				}
				rr$1(c, "#5a6169", -11.2, 4.8, 22.4, 6.4, 2.2);
				f(c, "#8d969f", () => c.roundRect(-11.2, 4.8, 22.4, 2, [
					2.2,
					2.2,
					0,
					0
				]));
			}
		},
		detonate: {
			zh: "引爆／獻祭",
			side: "tr",
			note: "橘色十角爆炸、黃白芯",
			d: (c, _o, T) => {
				poly$1(c, T[0], starPts(0, 0, 11, 6.2, 10), .4);
				poly$1(c, "#ffd23f", starPts(0, 0, 7.4, 3.8, 10, -Math.PI / 2 + .31));
				ci(c, "#ffffff", 0, 0, 2.6);
			},
			def: ["#ff7a2a", "#ffd23f"]
		},
		modify: {
			zh: "修正",
			side: "bl",
			note: "一顆齒輪（染改動的種類）",
			d: (c, _o, T) => {
				for (let i = 0; i < 8; i++) {
					c.save();
					c.rotate(i * Math.PI / 4);
					rr$1(c, T[0], -2.6, -11.4, 5.2, 6, 1);
					c.restore();
				}
				ci(c, T[0], 0, 0, 8.4);
				f(c, T[1], () => {
					c.arc(0, 0, 8.4, 3.5, 5.2);
					c.arc(0, 0, 5.6, 5.2, 3.5, true);
					c.closePath();
				});
				ci(c, OUT$2, 0, 0, 3.2);
			},
			def: ["#e8bb48", "#fff6c8"]
		}
	});
	/** 記號的位置：記號外形在 ±11.6 單位以內，放大 k 倍後離主圖格邊緣留 2.6 單位（外框才不會被格子切掉）。 */
	var corner = (side, k) => {
		const a = 2.6 + 11.6 * k;
		return side === "bl" ? [a, 48 - a] : [48 - a, a];
	};
	corner("tr", 1.06);
	corner("bl", 1.06);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qIcon/parts.ts
	/** 樣張 `QIcons` 用到的部分。 */
	var Q = {
		ART,
		render,
		outlinePx
	};
	var PI$1 = Math.PI;
	var CREAM = "#f2e6c8";
	var ALLY = "#7de0a8";
	var ENEMY = "#ff5a5a";
	var STEEL$1 = "#c3ccd6";
	var GOLD$5 = "#e8bb48";
	var LILAC = "#c8a0d8";
	var STONE = "#b4ac9a";
	var STONE_L = "#ece6d6";
	var STONE_D = "#8c8474";
	var INK$1 = "#2a1c36";
	var st = (c, col, w, fn, cap = "round") => {
		c.beginPath();
		fn(c);
		c.strokeStyle = col;
		c.lineWidth = w;
		c.lineCap = cap;
		c.lineJoin = "round";
		c.stroke();
	};
	var at = (c, x, y, k, fn, rot = 0) => {
		c.save();
		c.translate(x, y);
		c.rotate(rot);
		c.scale(k, k);
		fn(c);
		c.restore();
	};
	/** 第 3 批的效果記號（同一個題材同一個形，直接呼叫）。 */
	var act$1 = (id, T, t) => (c, o) => ACT[id].d(c, o, T ?? ACT[id].def ?? ["#ffd23f", "#ffffff"], t);
	/** 畫在 48 格的既有圖樣：縮到 ±10 單位的座標裡。 */
	var from48$1 = (d, k = .47) => (c, o) => {
		c.save();
		c.scale(k, k);
		c.translate(-24, -24);
		d(c, o);
		c.restore();
	};
	/** 人形（規則 9：單色剪影，圓頭加圓肩的半身）；高約 15k。 */
	var bust = (c, col, x, y, k = 1) => {
		ci(c, col, x, y - 4.6 * k, 3.7 * k);
		f(c, col, () => {
			c.moveTo(x - 6.2 * k, y + 7 * k);
			c.quadraticCurveTo(x - 6.2 * k, y - .4 * k, x, y - .4 * k);
			c.quadraticCurveTo(x + 6.2 * k, y - .4 * k, x + 6.2 * k, y + 7 * k);
			c.closePath();
		});
	};
	/** 朝右的細長箭頭（高 11.2）。 */
	var arrowS = (c, col, hi) => {
		poly$1(c, col, [
			[-10, -2.4],
			[1, -2.4],
			[1, -5.6],
			[10, 0],
			[1, 5.6],
			[1, 2.4],
			[-10, 2.4]
		], .4);
		if (hi) poly$1(c, hi, [
			[-10, -2.4],
			[1, -2.4],
			[1, -5.6],
			[10, 0],
			[-10, 0]
		]);
	};
	var heart = (c, col, x, y, s) => {
		c.save();
		c.translate(x, y);
		c.scale(s, s);
		c.beginPath();
		c.moveTo(0, 7);
		c.bezierCurveTo(-11, -1, -7, -10, 0, -4.5);
		c.bezierCurveTo(7, -10, 11, -1, 0, 7);
		c.closePath();
		c.fillStyle = col;
		c.fill();
		c.restore();
	};
	var heartArt = (c, _o, col = "#f0503e", hi = "#ffb0a0", s = 1.25) => {
		heart(c, col, 0, 1.4, s);
		el$1(c, hi, -3.6 * (s / 1.25), -2.6 * (s / 1.25), 2.6, 1.7, -.6);
	};
	var plus = (c, o, x, y, k = 1, col = "#ffffff") => halo(c, o, (q) => {
		rr$1(q, col, x - 1.5 * k, y - 4.4 * k, 3 * k, 8.8 * k, .8 * k);
		rr$1(q, col, x - 4.4 * k, y - 1.5 * k, 8.8 * k, 3 * k, .8 * k);
	});
	var minus = (c, o, x, y, k = 1, col = "#ffffff") => halo(c, o, (q) => rr$1(q, col, x - 4.4 * k, y - 1.5 * k, 8.8 * k, 3 * k, .8 * k));
	var star4 = (c, col, x, y, R, core = "#ffffff") => {
		poly$1(c, col, starPts(x, y, R, R * .36, 4), .3);
		if (core) poly$1(c, core, starPts(x, y, R * .55, R * .2, 4));
	};
	var burstStar = (c, x, y, R, col = "#ffd23f") => {
		poly$1(c, col, starPts(x, y, R, R * .48, 7, -1.2), .3);
		poly$1(c, "#ffffff", starPts(x, y, R * .48, R * .24, 7, -1.2));
	};
	/** 靴子（HUD「移動」的同一隻，qIcons.js）加兩道速度線：移動過、移動後、移動時共用。 */
	var boot = (c, o) => {
		at(c, 2.6, .4, .4, (q) => {
			q.translate(-27, -24);
			Q.ART.hud.move.d(q, o);
		});
		rr$1(c, CREAM, -10.6, -4.4, 4.6, 2.4, 1.2);
		rr$1(c, CREAM, -10.6, 1.4, 3.4, 2.4, 1.2);
	};
	var bootOnly = (c, o) => at(c, 0, 0, .47, (q) => {
		q.translate(-27, -24);
		Q.ART.hud.move.d(q, o);
	});
	/** 逆時針的回轉箭頭（反應：卡片小圖、骨架徽章、額外反應共用）。 */
	var react = (c, o, col = "#5ad06a", hi = "#c8f8d0") => {
		st(c, col, 4.2, (x) => x.arc(0, .6, 7, -PI$1 * .2, PI$1 * 1.22), "butt");
		if (!o.tiny) st(c, hi, 1.4, (x) => x.arc(0, .6, 8, PI$1 * .25, PI$1 * .8), "butt");
		at(c, -5.6, -3.6, 1, (q) => poly$1(q, col, [
			[-5.4, 1.6],
			[5.4, 1.6],
			[0, -5.6]
		], .4), .85);
	};
	var hourglass = (c, _o) => {
		rr$1(c, "#8ab8f0", -7.8, -10.6, 15.6, 3.4, 1.5);
		rr$1(c, "#8ab8f0", -7.8, 7.2, 15.6, 3.4, 1.5);
		poly$1(c, "#e6f4ff", [
			[-6, -7.4],
			[6, -7.4],
			[1.1, 0],
			[6, 7.4],
			[-6, 7.4],
			[-1.1, 0]
		], .4);
		poly$1(c, "#ffc23a", [
			[-4, -6],
			[4, -6],
			[0, -.8]
		]);
		poly$1(c, "#e8962a", [
			[-4.6, 7],
			[4.6, 7],
			[0, 3.4]
		]);
	};
	var clock = (c, o) => {
		ci(c, "#8ab8f0", 0, 0, 10.2);
		ci(c, "#f2f8ff", 0, 0, 7.3);
		if (!o.tiny) el$1(c, "#ffffff", -2.6, -3, 2.6, 1.5, -.6);
		ln(c, "#26365a", 2.1, [
			[0, -4.6],
			[0, 0],
			[3.7, 2.3]
		]);
	};
	var bolt = (c, o) => {
		poly$1(c, "#ffd23a", [
			[1.6, -10.6],
			[-7.6, 1.6],
			[-1.6, 1.6],
			[-4.2, 10.6],
			[7, -2.6],
			[1, -2.6],
			[4.2, -10.6]
		], .5);
		if (!o.tiny) poly$1(c, "#fff6b0", [
			[1.8, -9.4],
			[-5.6, .6],
			[-3.4, .6],
			[3.2, -9.4]
		]);
	};
	var crystal = (c) => {
		poly$1(c, "#b8a8ff", [
			[0, -10.6],
			[7.8, -4.6],
			[7.8, 4.6],
			[0, 10.6],
			[-7.8, 4.6],
			[-7.8, -4.6]
		], .6);
		poly$1(c, "#f2ecff", [
			[0, -10.6],
			[-7.8, -4.6],
			[0, -1]
		]);
		poly$1(c, "#d6ccff", [
			[-7.8, -4.6],
			[-7.8, 4.6],
			[0, -1]
		]);
		poly$1(c, "#7a68c8", [
			[7.8, -4.6],
			[7.8, 4.6],
			[0, 10.6],
			[0, -1]
		]);
		poly$1(c, "#9a86ff", [
			[-7.8, 4.6],
			[0, 10.6],
			[0, -1]
		]);
	};
	var dice = (c, o) => at(c, 0, 0, 1, (q) => {
		rr$1(q, "#f6f2e6", -8.2, -8.2, 16.4, 16.4, 3.6);
		f(q, "rgba(0,0,0,0.16)", () => q.roundRect(-8.2, 4.6, 16.4, 3.6, [
			0,
			0,
			3.6,
			3.6
		]));
		for (const [x, y] of o.tiny ? [
			[-3.8, -3.8],
			[0, 0],
			[3.8, 3.8]
		] : [
			[-4, -4],
			[4, 4],
			[0, 0],
			[4, -4],
			[-4, 4]
		]) ci(q, INK$1, x, y, o.tiny ? 2.1 : 1.8);
	}, .2);
	var banner = (c, o) => {
		rr$1(c, "#9a6ab8", -8.6, -10.6, 17.2, 3.6, 1.6);
		poly$1(c, LILAC, [
			[-6.6, -8],
			[6.6, -8],
			[6.6, 9.6],
			[0, 4.4],
			[-6.6, 9.6]
		], .8);
		f(c, "#eed8f6", () => c.rect(-6.6, -7, 3, 13));
		if (!o.tiny) star4(c, "#ffffff", 1.2, -1.4, 4.4, null);
	};
	var tag = (c, o) => at(c, 0, 0, .9, (q) => {
		poly$1(q, GOLD$5, [
			[-9.6, 0],
			[-3.4, -7.4],
			[9.6, -7.4],
			[9.6, 7.4],
			[-3.4, 7.4]
		], 1);
		f(q, "#fff0b0", () => q.rect(-2.6, -7.4, 12.2, 3));
		ci(q, "#5a3a06", -4.4, 0, 2.1);
		if (!o.tiny) {
			f(q, "#9c7420", () => q.rect(0, -.6, 7, 1.8));
			f(q, "#9c7420", () => q.rect(0, 3, 5, 1.8));
		}
	}, -.5);
	var wall = (c, x = 5.4) => {
		rr$1(c, STONE, x, -10.4, 5, 20.8, 1.4);
		f(c, STONE_L, () => c.rect(x, -9.4, 1.8, 18.8));
	};
	var puddle = (c, col = "#4aa8ff", hi = "#cfe8ff", y = 7) => {
		el$1(c, col, 0, y, 10.6, 3.6);
		el$1(c, hi, -2.6, y - .8, 5, 1.2);
	};
	var tablet = (c, _o) => {
		f(c, "#9a9282", () => c.roundRect(-7.6, -10.4, 15.2, 20.8, [
			6.4,
			6.4,
			1.8,
			1.8
		]));
		f(c, "#cfc8b6", () => c.roundRect(-7.6, -10.4, 3.8, 20.8, [
			6.4,
			0,
			0,
			1.8
		]));
		poly$1(c, "#ffd23f", [
			[0, -6.2],
			[5, .4],
			[0, 7],
			[-5, .4]
		], .4);
		poly$1(c, "#fff6c8", [
			[0, -2.6],
			[2.4, .4],
			[0, 3.4],
			[-2.4, .4]
		]);
	};
	var paw = (c, o, col = "#c9a0ff", hi = "#ecdcff") => {
		el$1(c, col, 0, 4, 6.4, 5.2);
		for (const [x, y, r] of [
			[
				-7,
				-1.8,
				2.7
			],
			[
				-2.6,
				-6.8,
				3
			],
			[
				2.6,
				-6.8,
				3
			],
			[
				7,
				-1.8,
				2.7
			]
		]) ci(c, col, x, y, r);
		if (!o.tiny) el$1(c, hi, -2, 2.4, 2.6, 1.5, -.4);
	};
	var shieldBlue = (c, _o, T = ["#6ab8f0", "#cfe8ff"]) => {
		poly$1(c, T[0], [
			[-9.4, -9.6],
			[9.4, -9.6],
			[8.8, 2],
			[0, 10],
			[-8.8, 2]
		], 1);
		poly$1(c, T[1], [
			[-9.4, -9.6],
			[0, -9.6],
			[0, 10],
			[-8.8, 2]
		], 1);
	};
	var hood = (c, _o) => {
		f(c, "#8a6ad8", () => {
			c.moveTo(0, -10.6);
			c.bezierCurveTo(8.6, -10.6, 10, -2, 9.6, 10.2);
			c.lineTo(-9.6, 10.2);
			c.bezierCurveTo(-10, -2, -8.6, -10.6, 0, -10.6);
			c.closePath();
		});
		f(c, "#b89af0", () => c.ellipse(-5.6, -3, 2, 6, .25, 0, TAU$1));
		el$1(c, "#2a1650", 0, .6, 5.8, 5.6);
		poly$1(c, "#ffe14d", [
			[-4.4, -.8],
			[-.8, .8],
			[-1.2, 2.4],
			[-4, 1.6]
		], .2);
		poly$1(c, "#ffe14d", [
			[4.4, -.8],
			[.8, .8],
			[1.2, 2.4],
			[4, 1.6]
		], .2);
	};
	var crate = (c, o, x = 0, y = 0, s = 17) => {
		rr$1(c, "#a06a36", x - s / 2, y - s / 2, s, s, s * .12);
		f(c, "#d8a868", () => c.roundRect(x - s / 2, y - s / 2, s, s * .2, [
			s * .12,
			s * .12,
			0,
			0
		]));
		f(c, "#6a4420", () => c.roundRect(x - s / 2, y + s * .32, s, s * .18, [
			0,
			0,
			s * .12,
			s * .12
		]));
		if (!o.small) ln(c, "#6a4420", s * .09, [[x - s * .3, y - s * .2], [x + s * .3, y + s * .24]]);
	};
	var grid3 = (c, lit = "#ffb23a", mid = "#fff6c8") => {
		c.save();
		c.scale(.8, .8);
		for (let i = 0; i < 9; i++) rr$1(c, i === 4 ? mid : lit, -10 + i % 3 * 6.9, -10 + Math.floor(i / 3) * 6.9, 6.2, 6.2, 1.4);
		c.restore();
	};
	var qmark = (c, o, x, y, k = 1) => halo(c, o, (q) => {
		st(q, "#ffe9a8", 2.4 * k, (p) => {
			p.arc(x, y - 2.6 * k, 2.6 * k, PI$1 * 1.05, PI$1 * .5);
			p.lineTo(x, y + 1.6 * k);
		});
		ci(q, "#ffe9a8", x, y + 4.6 * k, 1.4 * k);
	});
	/** 主圖樣縮到左下、右上角壓一個小圖（修正的「改了什麼」、召喚物數值用）。 */
	var withBadge = (base, small, bk = .8, sk = .48) => (c, o, T, opt) => {
		at(c, -2.2, 2.2, bk, (q) => base(q, o));
		halo(c, o, (q) => at(q, 6, -5.6, sk, (p) => small(p, {
			...o,
			tiny: true,
			small: true,
			owPx: 0,
			flat: true
		}, T, opt)));
	};
	var upArrow = (c, _o, T = ["#ffb23a", "#fff6c8"]) => {
		poly$1(c, T[0], [
			[0, -11],
			[10, -1],
			[4, -1],
			[4, 9.6],
			[-4, 9.6],
			[-4, -1],
			[-10, -1]
		], .6);
		poly$1(c, T[1], [
			[0, -11],
			[-10, -1],
			[-4, -1],
			[-4, 9.6],
			[0, 9.6]
		]);
	};
	var downArrow = (c, o, T = ["#6ae0ff", "#d8f8ff"]) => {
		c.save();
		c.scale(1, -1);
		upArrow(c, o, T);
		c.restore();
	};
	/** 修正內容的小箭頭照數值正負（第 2 版；沒給數值當正）：正＝朝上的橘黃、負＝朝下的青色。 */
	var signArrow = (c, o, opt) => (opt?.value ?? 1) < 0 || opt?.value === false ? downArrow(c, o) : upArrow(c, o);
	/** 亮色單手劍（第 2 版：必修 1）。第 1 批 W.swordArt 的柄是深握柄色、護手是暗金，在深色圓底上整把只剩一條灰褐細線；
	*  這裡照規則 6 換亮一階：刃亮鋼加寬到上限（刃寬 5.8／全長 28.5≈1/5）、護手換金、握柄換皮色（混亮一階 #a8703e）、柄頭金。直立座標：刃尖朝 −y，中心在原點。
	*  B＝刃的三色（本色、亮面、暗面），附魔的劍換刃色。 */
	var BLADE_STEEL = [
		STEEL$1,
		"#ffffff",
		"#98a2ae"
	];
	var bladeSword = (c, _o, B = BLADE_STEEL) => {
		c.save();
		c.translate(0, -.65);
		poly$1(c, B[0], [
			[-2.9, 3.6],
			[-2.9, -9.4],
			[0, -13.6],
			[2.9, -9.4],
			[2.9, 3.6]
		], .4);
		poly$1(c, B[1], [
			[-2.9, 3.6],
			[-2.9, -9.4],
			[0, -13.6],
			[-.4, -9.4],
			[-.4, 3.6]
		]);
		f(c, B[2], () => c.rect(1.3, -9, 1.6, 12.6));
		rr$1(c, GOLD$5, -6.4, 3.4, 12.8, 3.4, 1.5);
		f(c, "#fff0b0", () => c.roundRect(-6.4, 3.4, 12.8, 1.2, [
			1.5,
			1.5,
			0,
			0
		]));
		rr$1(c, "#a8703e", -1.7, 6.6, 3.4, 5.4, 1);
		ci(c, GOLD$5, 0, 12.6, 2.4);
		c.restore();
	};
	/** 斜放（刃尖朝右上）的亮劍，k＝縮放。k 0.84 時劍尖、柄頭剛好貼到圓片色環的內緣。 */
	var diagSword = (k = .84, B) => (c, o) => at(c, 0, 0, k, (q) => bladeSword(q, o, B), PI$1 / 4);
	/** 亮鋼匕首（第 2 版：必修 1 的背刺）：刃寬 5.6、刃尖朝 +y。 */
	var dagger$1 = (c, _o) => {
		poly$1(c, STEEL$1, [
			[-2.8, -3.4],
			[2.8, -3.4],
			[2.8, 2.6],
			[0, 8.6],
			[-2.8, 2.6]
		], .4);
		poly$1(c, "#ffffff", [
			[-2.8, -3.4],
			[-.3, -3.4],
			[-.3, 8],
			[-2.8, 2.6]
		]);
		rr$1(c, GOLD$5, -4.8, -5.6, 9.6, 2.8, 1.2);
		rr$1(c, "#a8703e", -1.5, -10, 3, 4.6, 1);
		ci(c, GOLD$5, 0, -10.4, 1.9);
	};
	/** 雙 V（第 2 版：必修 2 的衝鋒、位移徽章）：兩個朝右的粗 V 拉開，中間留 ≥4 單位（12px 圖樣裡約 2.5 個裝置像素）的底色；後面那個降一階色。 */
	var chevron = (c, x, col, hi) => {
		poly$1(c, col, [
			[x - 5.4, -9],
			[x - .4, -9],
			[x + 5.4, 0],
			[x - .4, 9],
			[x - 5.4, 9],
			[x + .4, 0]
		], .5);
		if (hi) poly$1(c, hi, [
			[x - 5.4, -9],
			[x - .4, -9],
			[x + 5.4, 0],
			[x + .4, 0]
		]);
	};
	var dashArt = (c, o) => {
		chevron(c, -5.2, "#b9a57e", o.tiny ? null : "#d8c8a0");
		chevron(c, 5.2, CREAM, o.tiny ? null : "#ffffff");
	};
	/** 範圍徽章（第 2 版：必修 4）：九宮格留給形狀，徽章改成「向外擴的衝擊環」——中心一顆黃白的小爆星，外面一圈斷成四段的橘色粗環（斷口在上下左右），環外四個斜角各一道往外的短衝擊線。 */
	var areaBurst = (c, o) => {
		for (let i = 0; i < 4; i++) {
			const a = i * PI$1 / 2;
			st(c, "#ffb23a", 3.2, (x) => x.arc(0, 0, 7.4, a + .32, a + PI$1 / 2 - .32), "butt");
			at(c, 0, 0, 1, (q) => poly$1(q, "#ffe08a", [
				[9.4, -1.3],
				[11.6, 0],
				[9.4, 1.3]
			], .6), a + PI$1 / 4);
		}
		poly$1(c, "#ffd23f", starPts(0, 0, 4.8, 2.4, 6, -PI$1 / 2), .4);
		ci(c, "#ffffff", 0, 0, 1.7);
		if (!o.tiny) st(c, "#fff0b0", 1.2, (x) => x.arc(0, 0, 8.4, PI$1 * 1.1, PI$1 * 1.4), "butt");
	};
	/** 中間破口的短厚磚牆（第 2 版：必修 3）：上下兩塊石磚，破口邊緣是鋸齒，旁邊兩顆碎石。 */
	var brokenWall = (c, o) => {
		poly$1(c, STONE, [
			[-4, -10.6],
			[4, -10.6],
			[4, -4.6],
			[2, -3.4],
			[.4, -5],
			[-1.8, -3.2],
			[-4, -4.4]
		], .4);
		poly$1(c, STONE, [
			[-4, 10.6],
			[4, 10.6],
			[4, 4.2],
			[1.8, 3.2],
			[0, 4.8],
			[-2, 3.4],
			[-4, 4.8]
		], .4);
		f(c, STONE_L, () => {
			c.rect(-4, -10.6, 8, 1.8);
			c.rect(-4, 4.8, 2, 5.8);
			c.rect(-4, -10.6, 2, 6);
		});
		if (!o.tiny) {
			f(c, STONE_D, () => {
				c.rect(-4, -7.2, 8, 1);
				c.rect(-4, 7.6, 8, 1);
			});
			ci(c, STONE_L, 7.6, -6.6, 1.3);
			ci(c, STONE_L, 8.4, 6.8, 1.1);
		}
	};
	/** 油表面（第 2 版：可修）：第 3 批的「一灘加一滴」染成褐色像一坨醬；圓片裡換成琥珀黃（同一個液體外形），水滴上加白色反光。試過壓扁成一灘不畫那一滴：18px 像麵包、熱狗。 */
	var oilPool = (c, o) => {
		ACT.surface.d(c, o, ["#e8a830", "#fff0b0"], "oil");
		el$1(c, "#ffffff", -3.7, -3.6, 1.1, 2.2, .4);
		if (!o.tiny) el$1(c, "#ffffff", 4.6, 5.2, 2, .7);
	};
	/** 靈魂連結的雙環（11-12：效果「分擔傷害」改用；畫法照抄 qIconsStatus.js 的 NEW.soul_link，一筆不改——這個檔比第⑤批先載入，不能呼叫它）。 */
	var soulRings = (c, o) => {
		const ring = (q, x, a0 = 0, a1 = TAU$1) => st(q, "#c8a0ff", o.tiny ? 3.2 : 2.8, (p) => p.arc(x, .4, 5.6, a0, a1), "butt");
		ring(c, -3.8);
		halo(c, o, (q) => {
			ring(q, 3.8);
			if (!o.tiny) st(q, "#efe2ff", 1.1, (p) => p.arc(3.8, .4, 5.6, PI$1 * 1.15, PI$1 * 1.55), "butt");
		});
		halo(c, o, (q) => ring(q, -3.8, -.75, .05));
		if (!o.tiny) st(c, "#efe2ff", 1.1, (p) => p.arc(-3.8, .4, 5.6, PI$1 * 1.15, PI$1 * 1.55), "butt");
	};
	/** 縮到圓片色環以內（第 2 版：可修「畫出圓片」）：方的、寬的圖樣四角會頂到色環。 */
	var fit = (d, k = .84) => (c, o, T, opt) => at(c, 0, 0, k, (q) => d(q, o, T, opt));
	/** 姿態類狀態（第 2 版：補畫）：骨架徽章「姿態」同一個六角臂章外形，底色與中間的紋章換成各姿態的題材。 */
	var hexPts = (R) => [
		0,
		1,
		2,
		3,
		4,
		5
	].map((i) => [Math.cos(i / 6 * TAU$1 - PI$1 / 2) * R, Math.sin(i / 6 * TAU$1 - PI$1 / 2) * R]);
	var stancePlate = (col, hi, emblem) => (c, o) => {
		const P = hexPts(10.6);
		poly$1(c, col, P, .5);
		poly$1(c, hi, [
			P[0],
			P[5],
			P[4],
			[-5.6, 3],
			[-5.6, -4.4]
		]);
		halo(c, o, (q) => emblem(q, o));
	};
	var SURF_TINT = {
		fire: "fire",
		water: "water",
		ice: "ice",
		poison: "poison",
		holy: "holy",
		oil: "earth",
		darkness: "shadow",
		smoke: "steel"
	};
	var surface = (id) => (c, o) => {
		const t = SURF_TINT[id] ?? "water";
		ACT.surface.d(c, o, TINT[t] ?? TINT.water, t);
	};
	var spirit = (T) => (c, o) => ACT.summon.d(c, o, T ?? ACT.summon.def);
	var EFFECT = {
		damage: {
			zh: "傷害",
			topic: "白色四芒閃光",
			src: "b3:hit",
			d: act$1("hit")
		},
		heal: {
			zh: "治療",
			topic: "綠色粗十字",
			src: "b3:heal",
			d: act$1("heal")
		},
		shield: {
			zh: "護盾",
			topic: "淡藍小盾（白十字紋）",
			src: "b3:shield",
			d: act$1("shield")
		},
		cleanse: {
			zh: "淨化",
			topic: "一大兩小三顆薄荷綠的亮晶晶",
			d: (c, o) => {
				star4(c, "#9af0d0", -2, 1.6, 9);
				star4(c, "#d8fff0", 6.6, -6.4, 4.2, null);
				if (!o.tiny) star4(c, "#d8fff0", 6.4, 6.6, 3, null);
			}
		},
		push: {
			zh: "推擊",
			topic: "朝右上的黃白粗箭頭",
			src: "b3:push",
			d: act$1("push")
		},
		pull: {
			zh: "拉扯",
			topic: "朝左下的青色粗箭頭、尾端圓鉤",
			src: "b3:pull",
			d: act$1("pull")
		},
		knock_prone: {
			zh: "擊倒",
			topic: "黃色撞擊星壓在地面線上",
			src: "b3:knockdown",
			d: act$1("knockdown")
		},
		shockwave: {
			zh: "震波",
			topic: "地面線上一顆撞擊星，兩側各一道往外的弧",
			d: (c, _o) => {
				rr$1(c, "#b8862a", -11, 6.4, 22, 4.4, 2);
				burstStar(c, 0, -.6, 6.6);
				for (const s of [-1, 1]) st(c, "#ffe9a8", 2.8, (x) => x.arc(0, 1, 10.2, s > 0 ? -PI$1 * .36 : PI$1 * 1.1, s > 0 ? -PI$1 * .1 : PI$1 * 1.36), "round");
			}
		},
		teleport: {
			zh: "傳送",
			topic: "紫色傳送圈（看得到洞），中心一顆白閃光",
			d: (c, _o) => {
				ci(c, "#2a1650", 0, 0, 7.6);
				st(c, "#9a6ad8", 4.4, (x) => x.arc(0, 0, 8, 0, TAU$1));
				st(c, "#e0c8ff", 1.6, (x) => x.arc(0, 0, 8.8, PI$1 * 1.05, PI$1 * 1.6), "butt");
				star4(c, "#ffffff", 0, 0, 5.6, null);
			}
		},
		dash: {
			zh: "衝鋒",
			topic: "兩個朝右的粗 V 拉開（前米白、後降一階的褐米色）",
			d: dashArt
		},
		charge_through: {
			zh: "直線衝撞",
			topic: "黃色長箭頭從一道短厚磚牆中間的破口穿過去",
			d: (c, o) => {
				brokenWall(c, o);
				halo(c, o, (q) => at(q, .4, 0, 1.06, (p) => arrowS(p, "#ffd23f", "#ffffff")));
			}
		},
		shadowstep: {
			zh: "瞬步",
			topic: "米白人形背後繞過來一道紫色弧箭頭",
			d: (c, _o) => {
				bust(c, CREAM, 3.4, 2.6, .82);
				st(c, "#b48aee", 3.6, (x) => x.arc(2.6, .6, 9, PI$1 * .6, PI$1 * 1.66), "butt");
				at(c, 2.6 + Math.cos(PI$1 * 1.66) * 9, .6 + Math.sin(PI$1 * 1.66) * 9, 1, (q) => poly$1(q, "#b48aee", [
					[-4.8, -1],
					[4.8, -1],
					[0, 5]
				], .4), -1.1);
			}
		},
		leap: {
			zh: "跳躍",
			topic: "一道拱形的跳躍軌跡，落點朝下的箭頭",
			d: (c, _o) => {
				st(c, CREAM, 3.8, (x) => {
					x.moveTo(-9, 7.6);
					x.quadraticCurveTo(-2, -15.5, 6, 1.6);
				}, "butt");
				poly$1(c, CREAM, [
					[1.4, 1.6],
					[10.8, .4],
					[7.6, 9.6]
				], .5);
				rr$1(c, "#b8862a", -11, 7.6, 6, 3, 1.5);
			}
		},
		swap: {
			zh: "交換位置（傳送他人、任意兩者互換同圖）",
			topic: "上下兩個反向的箭頭（米白朝右、青色朝左）",
			d: (c, _o) => {
				at(c, 0, -5, 1, (q) => arrowS(q, CREAM, "#ffffff"));
				at(c, 0, 5, 1, (q) => arrowS(q, "#6ae0ff", "#d8f8ff"), PI$1);
			}
		},
		apply_status: {
			zh: "施加狀態（沒指定是哪個狀態時）",
			topic: "掛在橫桿上的淡紫小旗（燕尾）",
			d: banner
		},
		create_surface: {
			zh: "產生表面（沒指定哪種表面時）",
			topic: "一灘水漬上落下一滴",
			src: "b3:surface",
			d: surface("water")
		},
		blow_surface: {
			zh: "吹送",
			topic: "一道捲起來的風，吹著一顆水滴",
			d: (c, _o) => {
				st(c, "#7fe0c0", 3.6, (x) => {
					x.moveTo(-10, -2.4);
					x.lineTo(2.6, -2.4);
					x.arc(2.6, -6, 3.6, PI$1 / 2, -PI$1 * .8, true);
				});
				st(c, "#dcfff1", 2.8, (x) => {
					x.moveTo(-9, 3.6);
					x.lineTo(-1.6, 3.6);
				});
				at(c, 6.4, 4.6, .46, (q) => drop(q, "#4aa8ff", 0, 0, 1), -.9);
			}
		},
		enter_form: {
			zh: "進入形態",
			topic: "淡紫色的獸掌印",
			d: (c, o) => paw(c, o)
		},
		leave_form: {
			zh: "解除形態",
			topic: "米白人形，左下一個變暗縮小的掌印",
			d: (c, o) => {
				at(c, -6.4, 5.4, .46, (q) => paw(q, { tiny: true }, "#9a7ad0"));
				halo(c, o, (q) => bust(q, CREAM, 2.6, 1.2, 1.02));
			}
		},
		clear_surface: {
			zh: "清除表面",
			topic: "一把掃帚（木柄、金色帚頭）",
			d: (c, o) => {
				ln(c, "#a06a36", 2.8, [[8, -9.6], [-1, -1]]);
				poly$1(c, GOLD$5, [
					[-4.4, -3.4],
					[2.4, 3.4],
					[-3.4, 9.8],
					[-10.4, 2.8]
				], .6);
				poly$1(c, "#fff0b0", [
					[-4.4, -3.4],
					[-1.6, -.6],
					[-8, 5],
					[-10.4, 2.8]
				]);
				ln(c, "#8a5a32", 2.2, [[-3.6, -2.6], [1.4, 2.4]]);
				if (!o.tiny) star4(c, "#ffffff", 7, 6, 3.6, null);
			}
		},
		destroy_object: {
			zh: "摧毀物件",
			topic: "一個木箱，中間一道裂開的閃電形裂縫",
			d: (c, _o) => {
				crate(c, { small: true }, 0, 0, 18);
				ln(c, OUT$2, 3.6, [
					[-1.6, -9.4],
					[2, -2.6],
					[-2.4, 1.6],
					[1.4, 9.4]
				], "miter");
				ln(c, "#ffd23f", 1.3, [
					[-1.6, -9.4],
					[2, -2.6],
					[-2.4, 1.6],
					[1.4, 9.4]
				], "miter");
			}
		},
		create_obstacle: {
			zh: "產生障礙",
			topic: "三排交錯的灰石磚牆",
			d: fit((c, _o) => {
				for (const [x, y, w] of [
					[
						-10,
						-9.6,
						9.4
					],
					[
						.6,
						-9.6,
						9.4
					],
					[
						-10,
						-3,
						4.6
					],
					[
						-4.2,
						-3,
						8.4
					],
					[
						5.4,
						-3,
						4.6
					],
					[
						-10,
						3.6,
						9.4
					],
					[
						.6,
						3.6,
						9.4
					]
				]) {
					rr$1(c, STONE, x, y, w, 5.6, 1.2);
					f(c, STONE_L, () => c.roundRect(x, y, w, 1.8, [
						1.2,
						1.2,
						0,
						0
					]));
				}
			}, .82)
		},
		raise_terrain: {
			zh: "隆起地形",
			topic: "地面裂開、中間頂出一根高高的石柱，柱頂左上一個小黃箭頭",
			d: (c, o) => {
				rr$1(c, STONE_D, -10.8, 6.6, 21.6, 4, 1.6);
				rr$1(c, STONE, -4.6, -8.6, 9.2, 16.4, 1.4);
				f(c, STONE_L, () => c.roundRect(-4.6, -8.6, 9.2, 2.6, [
					1.4,
					1.4,
					0,
					0
				]));
				f(c, STONE_L, () => c.rect(-4.6, -8.6, 2.4, 16));
				for (const s of [-1, 1]) poly$1(c, STONE, [
					[s * 5.8, 6.6],
					[s * 9.4, 2.6],
					[s * 10.4, 6.6]
				], .3);
				at(c, -7.8, -2.4, .4, (q) => upArrow(q, o, ["#ffd23f", "#ffffff"]));
			}
		},
		lower_terrain: {
			zh: "下陷地形",
			topic: "地面中間凹下去一個坑，上面一個朝下的黃箭頭",
			d: (c, o) => {
				poly$1(c, STONE, [
					[-10.4, 2.6],
					[-5.4, 2.6],
					[-3.6, 8],
					[3.6, 8],
					[5.4, 2.6],
					[10.4, 2.6],
					[10.4, 10.4],
					[-10.4, 10.4]
				], .4);
				f(c, STONE_L, () => {
					c.rect(-10.6, 2.2, 5.4, 1.8);
					c.rect(5.2, 2.2, 5.4, 1.8);
				});
				at(c, 0, -2.8, .6, (q) => {
					q.scale(1, -1);
					upArrow(q, o, ["#ffd23f", "#ffffff"]);
				});
			}
		},
		intercept: {
			zh: "替隊友擋攻擊",
			topic: "米白人形前面擋著一面藍盾",
			d: (c, o) => {
				bust(c, CREAM, -3.6, .6, .98);
				halo(c, o, (q) => at(q, 4.6, 2.8, .62, (p) => ACT.shield.d(p, o, ACT.shield.def)));
			}
		},
		add_stack: {
			zh: "累積層數",
			topic: "三根越來越高的金色粗條",
			src: "b3:builder",
			d: act$1("builder")
		},
		consume_stack: {
			zh: "消耗層數",
			topic: "兩根金色粗條，第三根的位置炸成一顆橘色爆星",
			d: (c, o) => {
				for (const [x, h] of [[-10.6, 7.6], [-3.4, 12.6]]) {
					rr$1(c, GOLD$5, x, 9.6 - h, 6.6, h, 1.6);
					f(c, "#fff6c8", () => c.roundRect(x, 9.6 - h, 6.6, 2.8, [
						1.6,
						1.6,
						0,
						0
					]));
				}
				halo(c, o, (q) => at(q, 5.6, -3.6, .6, (p) => ACT.detonate.d(p, o, ACT.detonate.def)));
			}
		},
		consume_status: {
			zh: "消耗狀態",
			topic: "橘色十角爆炸、黃白芯",
			src: "b3:detonate",
			d: act$1("detonate")
		},
		place_trap: {
			zh: "放置陷阱",
			topic: "底板上一排朝上的鋼牙",
			src: "b3:trap",
			d: fit(act$1("trap"), .8)
		},
		grant_ap: {
			zh: "給予 AP",
			topic: "黃色閃電（和卡片的 AP 同一個）加白色加號",
			d: (c, o) => {
				at(c, -1.6, .6, .95, (q) => bolt(q, o));
				plus(c, o, 6.6, 6, .86);
			}
		},
		reset_cooldown: {
			zh: "重置冷卻",
			topic: "藍邊白面的鐘，右上角一顆白閃光",
			d: (c, o) => {
				at(c, -1.2, 1.2, .9, (q) => clock(q, o));
				halo(c, o, (q) => star4(q, "#ffe14d", 6.6, -6.4, 5, "#ffffff"));
			}
		},
		cheat_death: {
			zh: "免死",
			topic: "紅心，右下一面小藍盾",
			d: (c, o) => {
				at(c, -1.2, -1, 1, (q) => heartArt(q, o));
				halo(c, o, (q) => at(q, 5.6, 5, .5, (p) => ACT.shield.d(p, o, ACT.shield.def)));
			}
		},
		redirect_damage: {
			zh: "分擔傷害",
			topic: "兩個扣在一起的淡紫圓環（前後交扣；同第⑤批狀態「靈魂連結」）",
			src: "b5:status.soul_link",
			d: soulRings
		},
		copy_skill: {
			zh: "複製技能",
			topic: "兩張疊著的卡（後面紫、前面米白有金星）",
			d: (c, o) => {
				rr$1(c, "#9a86d8", -9, -10, 11.4, 14.6, 2);
				halo(c, o, (q) => {
					rr$1(q, CREAM, -2.4, -4.6, 11.4, 14.6, 2);
					poly$1(q, "#e8a020", starPts(3.3, 2.7, 4, 1.7, 5), .2);
				});
			}
		},
		extra_reaction: {
			zh: "額外反應",
			topic: "綠色回轉箭頭（和「反應」同一個）加白色加號",
			d: (c, o) => {
				at(c, -1.4, 1.4, .88, (q) => react(q, o));
				plus(c, o, 6.8, -6.6, .8);
			}
		},
		hurl_object: {
			zh: "投擲物件",
			topic: "一個木箱沿弧線飛出去",
			d: (c, _o) => {
				st(c, CREAM, 2.8, (x) => {
					x.moveTo(-9.8, 9);
					x.quadraticCurveTo(-8.6, -2.6, -1.6, -4.4);
				}, "round");
				crate(c, { small: true }, 3.8, -3.4, 12.4);
			}
		},
		topple: {
			zh: "推倒",
			topic: "一根斜倒的石柱，底下地面線",
			d: (c, o) => {
				rr$1(c, "#b8862a", -11, 6.8, 22, 4, 2);
				at(c, -4.6, 6.6, 1, (q) => {
					rr$1(q, STONE, -3.2, -16.4, 6.4, 16.4, 1.2);
					f(q, STONE_L, () => q.rect(-3.2, -16, 2.2, 15.6));
					rr$1(q, STONE_D, -4.4, -18, 8.8, 3.2, 1);
				}, .74);
				if (!o.tiny) burstStar(c, 7.6, 3.4, 3.4);
			}
		},
		restore_resource: {
			zh: "回復資源",
			topic: "軟木塞圓底藥瓶，裝著藍色的水",
			d: (c, _o) => {
				rr$1(c, "#dcecff", -2.4, -9, 4.8, 6, 1);
				rr$1(c, "#a06a36", -3.2, -11, 6.4, 3, 1);
				ci(c, "#dcecff", 0, 2.6, 8);
				c.save();
				c.beginPath();
				c.rect(-9, -.6, 18, 12);
				c.clip();
				ci(c, "#4a8ae0", 0, 2.6, 6.4);
				c.restore();
				el$1(c, "#ffffff", -3, 4, 1.3, 2.6, .4);
			}
		},
		steal_buff: {
			zh: "奪取增益",
			topic: "紫色馬蹄形磁鐵（白色兩極）吸著一顆金星",
			d: (c, o) => {
				st(c, "#9a6ad8", 5.2, (x) => {
					x.moveTo(-5.6, -1);
					x.lineTo(-5.6, 3.6);
					x.arc(0, 3.6, 5.6, PI$1, 0, true);
					x.lineTo(5.6, -1);
				}, "butt");
				rr$1(c, "#ffffff", -8.2, -4.6, 5.2, 4, .8);
				rr$1(c, "#ffffff", 3, -4.6, 5.2, 4, .8);
				halo(c, o, (q) => poly$1(q, "#ffd23f", starPts(0, -6.6, 4.6, 1.9, 5), .2));
			}
		},
		dispel: {
			zh: "驅散",
			topic: "淡紫的增益箭頭（同「增益」徽章的外形）被一道紅斜槓劃掉",
			d: (c, o) => {
				at(c, 0, .4, .92, (q) => ACT.buff.d(q, o, ["#cfc4ff", "#ffffff"]));
				halo(c, o, (q) => {
					if (o.tiny) ln(q, OUT$2, 5.4, [[-8.6, 8.6], [8.6, -8.6]]);
					ln(q, "#ff4a5a", 3.4, [[-8.6, 8.6], [8.6, -8.6]]);
				});
			}
		},
		reveal: {
			zh: "揭露",
			topic: "一隻睜開的眼睛（米白眼白、藍瞳）",
			d: (c, o) => {
				f(c, CREAM, () => {
					c.moveTo(-10.8, 0);
					c.quadraticCurveTo(0, -11, 10.8, 0);
					c.quadraticCurveTo(0, 11, -10.8, 0);
					c.closePath();
				});
				ci(c, "#4aa8ff", 0, 0, 4.8);
				ci(c, "#16223a", 0, 0, 2.3);
				if (!o.tiny) ci(c, "#ffffff", -1.5, -1.6, 1.1);
			}
		},
		revive: {
			zh: "復活",
			topic: "金色的心，兩側一對白翅膀",
			d: fit((c, o) => {
				for (const s of [-1, 1]) poly$1(c, "#fffaf0", [
					[s * 3.6, -3],
					[s * 11, -9],
					[s * 10.6, -2],
					[s * 8.4, 2.4],
					[s * 4, 3.6]
				], .5);
				heart(c, "#ffd04a", 0, 1.6, 1.02);
				if (!o.tiny) el$1(c, "#fff6c8", -2.8, -1.8, 1.8, 1.2, -.6);
			}, .9)
		},
		delayed_damage: {
			zh: "定時炸彈",
			topic: "圓炸彈、彎引信、引信頭一顆火花",
			d: (c, _o) => {
				st(c, "#a06a36", 2.2, (x) => {
					x.moveTo(2.6, -5.6);
					x.quadraticCurveTo(4.6, -10, 7.6, -8.6);
				});
				rr$1(c, "#8a8f99", -.4, -7.2, 5, 3.6, 1);
				ci(c, "#5f6a8c", -1, 2.8, 7.8);
				el$1(c, "#a8b2d0", -3.8, -.4, 2.8, 1.7, -.6);
				poly$1(c, "#ffd23f", starPts(8.2, -8.2, 3.6, 1.5, 6), .2);
			}
		},
		summon: {
			zh: "召喚",
			topic: "一隻青色的小靈",
			src: "b3:summon",
			d: spirit()
		},
		zone: {
			zh: "持續區域",
			topic: "地上一圈藍色虛線環，上面浮著一個小沙漏",
			d: (c, o) => {
				for (let i = 0; i < 6; i++) st(c, "#8ab8f0", 2.8, (x) => x.ellipse(0, 6.2, 9.6, 3.6, 0, i / 6 * TAU$1 + .18, (i + 1) / 6 * TAU$1 - .18), "butt");
				halo(c, o, (q) => at(q, 0, -3.4, .64, (p) => hourglass(p, o)));
			}
		},
		rule_change: {
			zh: "規則改變",
			topic: "一張卷軸（上下金色卷軸桿、三行字）",
			d: (c, o) => {
				rr$1(c, CREAM, -6.8, -8.4, 13.6, 16.8, 1.2);
				rr$1(c, "#d8b04a", -8.8, -10.6, 17.6, 4, 2);
				rr$1(c, "#d8b04a", -8.8, 6.6, 17.6, 4, 2);
				if (!o.tiny) for (const [y, w] of [
					[-4, 8.4],
					[-.8, 8.4],
					[2.4, 5.4]
				]) f(c, "#8a6a2a", () => c.rect(-4.2, y, w, 1.7));
			}
		},
		gamble: {
			zh: "賭注",
			topic: "一顆斜放的白骰子",
			d: dice
		},
		grant_skill: {
			zh: "暫時獲得技能",
			topic: "一張米白的卡（金星）加白色加號",
			d: (c, o) => {
				rr$1(c, CREAM, -8.8, -8.4, 11.6, 16.4, 2);
				poly$1(c, "#e8a020", starPts(-3, 0, 4, 1.7, 5), .2);
				plus(c, o, 6.6, -5.8, .82);
			}
		},
		sacrifice_summon: {
			zh: "獻祭召喚物",
			topic: "小靈背後一圈橘色的爆炸",
			d: fit((c, o) => {
				poly$1(c, "#ff7a2a", starPts(0, 0, 11, 6.6, 10), .3);
				halo(c, o, (q) => at(q, 0, .6, .74, (p) => ACT.summon.d(p, o, ACT.summon.def)));
			}, .9)
		},
		inscribe: {
			zh: "刻印",
			topic: "圓頂的石碑，上面一個金色菱形符文",
			d: tablet
		},
		detonate_runes: {
			zh: "引爆符文",
			topic: "符文石碑背後一圈橘色的爆炸",
			d: fit((c, o) => {
				poly$1(c, "#ff7a2a", starPts(0, 0, 11, 6.6, 10), .3);
				halo(c, o, (q) => at(q, 0, .4, .64, (p) => tablet(p, o)));
			}, .9)
		}
	};
	var EFFECT_ALIAS = {
		teleport_target: "swap",
		swap_any: "swap"
	};
	var SURFACE = Object.fromEntries(Object.entries({
		water: "水",
		poison: "毒",
		oil: "油",
		fire: "火焰",
		ice: "冰",
		holy: "聖光",
		darkness: "黑暗",
		smoke: "煙霧"
	}).map(([id, zh]) => [id, {
		zh: zh + "表面",
		topic: {
			fire: "餘燼上三撮火苗",
			ice: "薄冰加兩根冰刺",
			holy: "地上一圈金光加一顆光點",
			darkness: "兩團紫色的霧",
			smoke: "兩團灰白的煙",
			oil: "一灘加一滴（琥珀黃、白色反光）"
		}[id] ?? "一灘水漬上落下一滴（染表面色）",
		src: id === "oil" ? "new" : "b3:surface",
		d: id === "oil" ? oilPool : surface(id)
	}]));
	var S48 = (id) => from48$1((c, o) => Q.ART.status[id].d(c, o));
	var STATUS = {
		slow: {
			zh: "緩速",
			topic: "一只金殼懷錶",
			src: "b3:slow",
			d: act$1("slow")
		},
		frozen: {
			zh: "冰凍",
			topic: "三根淡藍冰晶",
			src: "style:status.frozen",
			d: S48("frozen")
		},
		root: {
			zh: "定身",
			topic: "鐵球加兩節鎖鏈（腳鐐）",
			d: (c, _o) => {
				for (const [x, y] of [[-3.6, -3], [-7.2, -6.8]]) st(c, "#e4e9ef", 2.4, (p) => p.ellipse(x, y, 2.5, 1.7, .8, 0, TAU$1));
				ci(c, "#b4bcc6", 3, 3.4, 7.2);
				el$1(c, "#f2f5f8", .4, .6, 2.8, 1.7, -.6);
				f(c, "rgba(0,0,0,0.18)", () => {
					c.arc(3, 3.4, 7.2, -.2, 1.8);
					c.closePath();
				});
			}
		},
		stun: {
			zh: "暈眩",
			topic: "頭上繞一圈的暈眩弧，弧上一大一小兩顆黃星",
			d: (c, o) => {
				st(c, "#fff0b0", 2.4, (x) => x.ellipse(0, 1.6, 10, 4.4, 0, PI$1 * .05, PI$1 * .95), "round");
				poly$1(c, "#ffd23f", starPts(-3.4, -2.4, 7.4, 3.2, 5), .5);
				if (!o.tiny) poly$1(c, "#fff6c8", [
					[-3.4, -9.8],
					[-5.4, -4],
					[-3.4, -2.4]
				]);
				poly$1(c, "#ffd23f", starPts(6.4, 4.4, 4.2, 1.8, 5), .4);
			}
		},
		silenced: {
			zh: "沉默",
			topic: "紫色對話框，裡面一個深色的叉",
			d: fit((c, _o) => {
				poly$1(c, "#c890ff", [
					[-5.4, 3],
					[-6.8, 10],
					[.6, 3.6]
				], .4);
				rr$1(c, "#c890ff", -10, -9.4, 20, 13.8, 5);
				f(c, "#e6ccff", () => c.roundRect(-8.4, -8.4, 16.8, 3, 3));
				ln(c, INK$1, 2.6, [[-4.4, -6], [4.4, 1.6]]);
				ln(c, INK$1, 2.6, [[4.4, -6], [-4.4, 1.6]]);
			}, .86)
		},
		weaken: {
			zh: "虛弱",
			topic: "鋼灰色朝下的粗箭頭加頂槓",
			src: "b3:curse",
			d: act$1("curse", ["#c3ccd6", "#ffffff"])
		},
		vulnerable: {
			zh: "易傷",
			topic: "一面裂開的紅盾",
			d: fit((c, o) => {
				shieldBlue(c, o, ["#e8455a", "#ffb0b8"]);
				ln(c, OUT$2, 2.6, [
					[1.4, -10.4],
					[-1.8, -3.6],
					[2.2, .6],
					[-.8, 5],
					[.6, 10.4]
				], "miter");
			}, .86)
		},
		feared: {
			zh: "恐懼",
			topic: "風格樣張的恐懼",
			src: "style:status.feared",
			d: S48("feared")
		},
		blinded: {
			zh: "致盲",
			topic: "淡紫的眼睛被一道紅斜槓劃掉",
			d: (c, o) => {
				f(c, "#e6d2ff", () => {
					c.moveTo(-10.8, 0);
					c.quadraticCurveTo(0, -9.6, 10.8, 0);
					c.quadraticCurveTo(0, 9.6, -10.8, 0);
					c.closePath();
				});
				ci(c, "#7a4ec0", 0, 0, 4);
				halo(c, o, (q) => ln(q, "#ff5a6a", 3.4, [[-8, 8.4], [8, -8.4]]));
			}
		},
		taunted: {
			zh: "嘲諷",
			topic: "橘紅色的青筋記號（四道彎角）",
			d: (c, _o) => {
				for (let i = 0; i < 4; i++) {
					c.save();
					c.rotate(i * PI$1 / 2);
					st(c, "#ff7a3a", 3.8, (x) => {
						x.moveTo(2.6, 9.4);
						x.quadraticCurveTo(2.6, 2.6, 9.4, 2.6);
					});
					c.restore();
				}
			}
		},
		marked: {
			zh: "被標記",
			topic: "紅色準星",
			src: "b3:mark",
			d: act$1("mark")
		},
		burning: {
			zh: "燃燒",
			topic: "一團火（橘外焰、黃內焰）",
			src: "b3:dot",
			d: act$1("dot", TINT.fire, "fire")
		},
		poison: {
			zh: "中毒",
			topic: "一大顆綠毒滴，右上一顆泡",
			src: "b3:el:poison",
			d: from48$1((c, o) => ELEMENT$1.poison.d(c, {
				...o,
				small: true
			}))
		},
		bleed: {
			zh: "流血",
			topic: "一大一小兩顆紅血滴",
			src: "b3:dot",
			d: act$1("dot", TINT.blood, "blood")
		},
		prone: {
			zh: "倒地",
			topic: "風格樣張的倒地（躺平的人形加撞擊星）",
			src: "style:status.prone",
			d: S48("prone")
		},
		hasted: {
			zh: "加速",
			topic: "風格樣張的加速（綠色雙箭頭）",
			src: "style:status.hasted",
			d: S48("hasted")
		},
		concealed: {
			zh: "隱蔽",
			topic: "紫色兜帽，裡面兩道發亮的斜眼",
			d: hood
		},
		guarded: {
			zh: "護衛",
			topic: "一面圓木盾（鋼邊、直木板、鋼盾心）",
			d: (c, o) => {
				ci(c, "#c3ccd6", 0, 0, 10.4);
				ci(c, "#b8824a", 0, 0, 8.4);
				f(c, "#d6a46a", () => {
					c.arc(0, 0, 8.4, PI$1 * .5, PI$1 * 1.5);
					c.closePath();
				});
				for (const x of [-3.4, 3.4]) f(c, "#7e5a30", () => c.rect(x - .6, -Math.sqrt(70.56 - x * x), 1.2, 2 * Math.sqrt(70.56 - x * x)));
				ci(c, "#c3ccd6", 0, 0, 3.8);
				ci(c, "#ffffff", -1.2, -1.2, 1.5);
				if (!o.tiny) st(c, "#ffffff", 1.2, (x) => x.arc(0, 0, 9.6, PI$1 * 1.05, PI$1 * 1.45), "butt");
			}
		},
		defending: {
			zh: "守護",
			topic: "一面木製鳶形盾（鋼邊、中間一道米白直紋）",
			d: fit((c, o) => {
				const P = [
					[-9.4, -10.2],
					[9.4, -10.2],
					[9.4, .6],
					[0, 10.8],
					[-9.4, .6]
				], I = [
					[-7.2, -8.2],
					[7.2, -8.2],
					[7.2, -.2],
					[0, 7.8],
					[-7.2, -.2]
				];
				poly$1(c, "#c3ccd6", P, 1);
				poly$1(c, "#b8824a", I, .6);
				poly$1(c, "#d0a068", [
					[-7.2, -8.2],
					[0, -8.2],
					[0, 7.8],
					[-7.2, -.2]
				], .6);
				f(c, "#e8e0c8", () => c.rect(-1.6, -8.6, 3.2, 15.4));
				if (!o.tiny) {
					f(c, "#ffffff", () => c.rect(-9.4, -10.2, 18.8, 1.4));
					ci(c, "#ffffff", -4.6, -4.6, 1);
					ci(c, "#ffffff", 4.6, -4.6, 1);
				}
			}, .86)
		},
		stoneskin: {
			zh: "石膚",
			topic: "灰石色的人形，身上幾道石板裂紋",
			d: (c, o) => {
				bust(c, STONE, 0, 1.6, 1.32);
				f(c, STONE_L, () => {
					c.arc(-1.4, -5.6, 2.6, PI$1, PI$1 * 1.6);
					c.lineTo(-1.4, -5.6);
					c.closePath();
				});
				ln(c, "#6e6858", 1.6, [
					[-6.4, 4],
					[-2, 5.4],
					[1.6, 3.4],
					[6, 5.6]
				]);
				ln(c, "#6e6858", 1.6, [[-1.4, -4.6], [1.4, -2.6]]);
				if (!o.tiny) f(c, STONE_L, () => c.rect(-6.6, 6, 3.6, 3));
			}
		},
		regenerating: {
			zh: "再生",
			topic: "一株綠色的嫩芽（一莖兩葉）",
			d: (c, o) => {
				ln(c, "#4aa84a", 2.8, [[0, 10.2], [0, -1.6]]);
				for (const s of [-1, 1]) {
					c.save();
					c.translate(0, -1.4);
					c.scale(s, 1);
					f(c, "#6ad86a", () => {
						c.moveTo(0, 0);
						c.bezierCurveTo(1.4, -7.6, 7.4, -9.6, 10.4, -8.4);
						c.bezierCurveTo(9.6, -3, 5.4, 1.6, 0, 0);
						c.closePath();
					});
					if (!o.tiny) f(c, "#c8f8b8", () => {
						c.moveTo(1.6, -2);
						c.bezierCurveTo(3, -5.4, 6, -7, 8.6, -7.6);
						c.lineTo(8, -6.4);
						c.bezierCurveTo(5.4, -5.6, 3.4, -4, 1.6, -2);
						c.closePath();
					});
					c.restore();
				}
				rr$1(c, "#8a5a32", -6.4, 8, 12.8, 3, 1.4);
			}
		},
		empowered: {
			zh: "激昂",
			topic: "一隻彎起來使力的手臂（膚色、握拳朝上）",
			d: (c, o) => {
				f(c, "#f0c49a", () => {
					c.moveTo(-10.6, 9.4);
					c.lineTo(-10.6, 3);
					c.quadraticCurveTo(-8.6, -1.6, -1.6, .6);
					c.quadraticCurveTo(3.6, -3.4, 1.6, -6.2);
					c.lineTo(6.6, -9);
					c.quadraticCurveTo(10.8, -2, 6.4, 4.6);
					c.quadraticCurveTo(1, 10, -4, 9.4);
					c.closePath();
				});
				ci(c, "#f0c49a", 4.4, -7.6, 4.2);
				el$1(c, "#ffe8d0", -4.4, -.4, 3, 2, -.3);
				if (!o.tiny) {
					el$1(c, "#ffe8d0", 3, -9, 1.8, 1.1, -.5);
					ln(c, "#c8885a", 1.2, [[2.6, -6.2], [5.6, -5.4]]);
				}
			}
		},
		overwatch: {
			zh: "監視",
			topic: "一支斜舉的黃銅望遠鏡（鏡口淡藍）",
			d: (c, o) => at(c, 0, 0, 1, (q) => {
				rr$1(q, "#a06a36", -12.4, -2.4, 7.4, 4.8, 1.2);
				rr$1(q, "#e8bb48", -6, -3.2, 8.6, 6.4, 1.4);
				rr$1(q, "#f6d878", 1.6, -4.2, 9.4, 8.4, 1.6);
				f(q, "#fff6c8", () => {
					q.rect(-6, -3.2, 8.6, 1.6);
					q.rect(1.6, -4.2, 9.4, 1.8);
				});
				rr$1(q, "#9c7420", 1.2, -4.4, 1.6, 8.8, .6);
				el$1(q, "#8fe3ff", 11.2, 0, 1.8, 3.8);
				if (!o.tiny) el$1(q, "#ffffff", 11.4, -1.4, .8, 1.4);
			}, -PI$1 / 4)
		},
		infused_fire: {
			zh: "火焰附魔",
			topic: "刃換成火焰色的斜劍，劍尖一撮火",
			d: (c, o) => {
				diagSword(.8, [
					"#ff8a2a",
					"#ffd23f",
					"#d8501a"
				])(c, o);
				halo(c, o, (q) => flame(q, "#ffd23f", 6.4, -6.6, .34));
			}
		},
		infused_holy: {
			zh: "神聖附魔",
			topic: "刃換成金色的斜劍，劍尖一顆白色四芒光",
			d: (c, o) => {
				diagSword(.8, [
					"#ffd75e",
					"#fff6c8",
					"#d8a830"
				])(c, o);
				halo(c, o, (q) => star4(q, "#ffffff", 6.2, -6.2, 4.6, null));
			}
		},
		shielded_charged: {
			zh: "帶電護盾",
			topic: "淡藍小盾（同「護盾」），盾面一道黃閃電（取代白十字）",
			d: fit((c, o) => {
				shieldBlue(c, o);
				halo(c, o, (q) => at(q, 0, -.2, .72, (p) => bolt(p, o)));
			}, .86)
		},
		stance_guard: {
			zh: "堅守姿態",
			topic: "藍色六角臂章（姿態的外形），中間一面白盾",
			d: stancePlate("#5a86d8", "#9ab8f0", (c, o) => at(c, 0, .4, .5, (q) => shieldBlue(q, o, ["#e8eef6", "#ffffff"])))
		},
		stance_bulwark: {
			zh: "堅壁姿態",
			topic: "沙岩色六角臂章，中間一面亮色磚牆（深色磚縫）",
			d: stancePlate("#c89a5a", "#ecc890", (c) => {
				rr$1(c, "#5e3b1f", -6.6, -5.8, 13.2, 11.6, 1);
				for (const [x, y, w] of [
					[
						-6,
						-5.2,
						5.4
					],
					[
						.6,
						-5.2,
						5.4
					],
					[
						-6,
						-.6,
						2.8
					],
					[
						-2.4,
						-.6,
						4.8
					],
					[
						3.2,
						-.6,
						2.8
					],
					[
						-6,
						4,
						5.4
					],
					[
						.6,
						4,
						5.4
					]
				]) rr$1(c, "#f2dcb0", x, y, w, 3.6, .6);
			})
		},
		stance_ironwall: {
			zh: "鐵壁姿態",
			topic: "深鋼灰六角臂章，中間三根亮色直鐵條",
			d: stancePlate("#7d8794", "#aab4c0", (c, o) => {
				for (const x of [
					-4.6,
					0,
					4.6
				]) {
					rr$1(c, "#eef2f6", x - 1.5, -7, 3, 14, 1.2);
					if (!o.tiny) f(c, "#ffffff", () => c.rect(x - 1.5, -7, 1, 14));
				}
				if (!o.tiny) for (const [x, y] of [
					[-7.6, -2.6],
					[7.6, -2.6],
					[-7.6, 2.6],
					[7.6, 2.6]
				]) ci(c, "#3a4048", x, y, .9);
			})
		},
		stance_fury: {
			zh: "狂怒姿態",
			topic: "紅色六角臂章，中間一團黃火",
			d: stancePlate("#e04a3a", "#ff9a8a", (c) => {
				flame(c, "#ffd23f", 0, .6, .66);
				flame(c, "#ffffff", 0, 3.4, .3);
			})
		},
		stance_holy_1: {
			zh: "聖輝架勢·壹",
			topic: "金色六角臂章，中間一顆白色四芒光",
			d: stancePlate("#e0a830", "#ffe08a", (c) => star4(c, "#ffffff", 0, .4, 7.4, "#fff6c8"))
		},
		stance_shadow_1: {
			zh: "暗影架勢·壹",
			topic: "紫色六角臂章，中間一彎淡紫月牙",
			d: stancePlate("#8a5ac8", "#b89af0", (c) => f(c, "#f0e4ff", () => {
				c.arc(-.6, .4, 6.4, .6, 5.7, false);
				c.arc(2.2, -.8, 5, 4.9, 1.2, true);
				c.closePath();
			}))
		}
	};
	var halfHeart = (c, _o, s = 1.25) => {
		heart(c, "#7a2a3a", 0, 1.4, s);
		c.save();
		c.beginPath();
		c.rect(-12, 1, 24, 12);
		c.clip();
		heart(c, "#ff5a4a", 0, 1.4, s);
		c.restore();
		st(c, "#ff9a8a", 1.5, (x) => {
			x.moveTo(-8.4 * (s / 1.25), 1);
			x.lineTo(8.4 * (s / 1.25), 1);
		}, "butt");
	};
	var COND = {
		height_advantage: {
			zh: "居高臨下",
			topic: "一座山，山頂一個米白小人頭，右上一個朝上的黃箭頭",
			d: (c, o) => {
				poly$1(c, STONE, [
					[-10.6, 9.8],
					[-2.4, -3.6],
					[2.4, 2.6],
					[5, -.6],
					[10.6, 9.8]
				], .6);
				f(c, STONE_L, () => {
					c.moveTo(-10.6, 9.8);
					c.lineTo(-2.4, -3.6);
					c.lineTo(-3.4, 9.8);
					c.closePath();
				});
				poly$1(c, "#f6f2e6", [
					[-2.4, -3.8],
					[.4, 0],
					[-2, 1.4],
					[-4.8, .4]
				], .3);
				ci(c, CREAM, -2.4, -7.6, 2.7);
				if (!o.tiny) poly$1(c, "#ffd23f", [
					[6.6, -10.6],
					[10.8, -5.4],
					[2.4, -5.4]
				], .3);
			}
		},
		target_hp_below: {
			zh: "目標血量低於",
			topic: "一顆心，上半暗紅、下半亮紅",
			d: (c, o) => halfHeart(c, o)
		},
		self_hp_below: {
			zh: "自身血量低於",
			topic: "半滿的心，右下一個米白小人形",
			d: (c, o) => {
				at(c, -2.4, -1.6, .86, (q) => halfHeart(q, o));
				halo(c, o, (q) => bust(q, CREAM, 5.6, 4.6, .62));
			}
		},
		target_has_status: {
			zh: "目標帶有狀態（沒指定狀態時）",
			topic: "淡紫小旗，右上一個問號",
			d: (c, o) => {
				at(c, -2, 1, .9, (q) => banner(q, o));
				qmark(c, o, 7, -5.6, .9);
			}
		},
		target_on_surface: {
			zh: "目標站在表面上",
			topic: "一灘藍水漬上站著米白人形",
			d: (c, o) => {
				puddle(c);
				halo(c, o, (q) => bust(q, CREAM, 0, -.8, .96));
			}
		},
		from_behind: {
			zh: "背刺",
			topic: "米白人形，左上一把亮鋼匕首（金護手、皮柄）刺向背後",
			d: (c, o) => {
				bust(c, CREAM, 5.2, 3.6, .84);
				halo(c, o, (q) => {
					if (o.tiny) at(q, -.4, -.4, .75, (p) => poly$1(p, OUT$2, [
						[-5, -4.6],
						[5, -4.6],
						[5, 3.2],
						[0, 11.6],
						[-5, 3.2]
					], .6), -PI$1 / 4);
					at(q, -.4, -.4, .75, (p) => dagger$1(p, o), -PI$1 / 4);
				});
			}
		},
		flanked: {
			zh: "夾擊",
			topic: "中間米白人形，左右各一個朝內的紅色三角",
			d: (c, _o) => {
				bust(c, CREAM, 0, .8, .8);
				for (const s of [-1, 1]) poly$1(c, ENEMY, [
					[s * 10.8, -4.6],
					[s * 5.6, .6],
					[s * 10.8, 5.8]
				], .5);
			}
		},
		target_isolated: {
			zh: "目標落單",
			topic: "一道從上面打下來的光柱，底下一個米白人形",
			d: (c, o) => {
				f(c, "rgba(255,236,170,0.72)", () => {
					c.moveTo(-2.8, -10.8);
					c.lineTo(2.8, -10.8);
					c.lineTo(9.8, 8);
					c.lineTo(-9.8, 8);
					c.closePath();
				});
				el$1(c, "#ffe9a8", 0, 8, 9.8, 2.6);
				halo(c, o, (q) => bust(q, CREAM, 0, 1.6, .8));
			}
		},
		moved_this_turn: {
			zh: "本回合移動過",
			topic: "一隻褐色的靴子，後面兩道速度線",
			src: "style:hud.move",
			d: boot
		},
		first_round: {
			zh: "第一輪",
			topic: "一個金色的粗體數字 1",
			d: (c, _o) => {
				poly$1(c, "#ffd23f", [
					[-1.6, -10.2],
					[3.2, -10.2],
					[3.2, 6],
					[6.8, 6],
					[6.8, 10.2],
					[-6.2, 10.2],
					[-6.2, 6],
					[-1.6, 6],
					[-1.6, -4.4],
					[-5.8, -2.4],
					[-5.8, -6.8]
				], .5);
				f(c, "#fff6c8", () => c.rect(-1.6, -10.2, 1.8, 16));
			}
		},
		cast_tag_this_turn: {
			zh: "本回合施放過同類技能",
			topic: "一張斜放的金色吊牌（有孔）",
			d: fit(tag, .88)
		},
		self_concealed: {
			zh: "潛行偷襲",
			topic: "紫色兜帽，裡面兩道發亮的斜眼",
			d: hood
		},
		on_own_rune: {
			zh: "目標站在自己的符文上",
			topic: "符文石碑，右下一個米白小人形",
			d: (c, o) => {
				at(c, -2.6, -.6, .86, (q) => tablet(q, o));
				halo(c, o, (q) => bust(q, CREAM, 5.4, 4.6, .62));
			}
		},
		adjacent_ally: {
			zh: "身旁有友方",
			topic: "並排兩個人形（米白與綠）",
			d: (c, o) => {
				bust(c, CREAM, -4.6, 1, .84);
				halo(c, o, (q) => bust(q, ALLY, 4.6, 1, .84));
			}
		},
		target_collided: {
			zh: "目標本回合受過撞擊",
			topic: "米白人形撞在右邊一道石牆上，中間一顆撞擊星",
			d: (c, o) => {
				wall(c, 5.6);
				bust(c, CREAM, -3, 1.2, .86);
				halo(c, o, (q) => burstStar(q, 3.6, -4.6, 4.8));
			}
		},
		wielding_weapon: {
			zh: "手持指定武器",
			topic: "一把斜放的亮色單手劍（亮鋼寬刃、金護手、皮柄）",
			d: diagSword()
		},
		in_form: {
			zh: "在形態中",
			topic: "三道淡紫色的爪痕",
			d: (c, _o) => at(c, 0, 0, 1, (q) => {
				for (const i of [
					-1,
					0,
					1
				]) poly$1(q, i === 0 ? "#e6d2ff" : "#c9a0ff", [
					[i * 6.4 - 2.2, -10],
					[i * 6.4 + 1.6, -10],
					[i * 6.4 + 2.8, 2],
					[i * 6.4 + .2, 10.2],
					[i * 6.4 - 1.8, 2]
				], .3);
			}, .28)
		}
	};
	var COST = {
		source: {
			zh: "源力",
			topic: "六角的淡紫晶石",
			d: crystal
		},
		gamble: {
			zh: "賭注",
			topic: "一顆斜放的白骰子",
			d: dice
		},
		self: {
			zh: "自身代價（失手自傷等）",
			topic: "一顆裂開的紅心",
			d: (c, o) => {
				heartArt(c, o);
				ln(c, OUT$2, 2.6, [
					[.8, -4.6],
					[-2.2, -.6],
					[2, 2.4],
					[-.6, 5.6],
					[.2, 10]
				], "miter");
			}
		},
		stacks: {
			zh: "消耗層數",
			topic: "兩根金條加一顆橘色爆星",
			d: (c, o) => EFFECT.consume_stack.d(c, o)
		},
		once: {
			zh: "每場一次",
			topic: "一張米白票券（兩側缺口），上面一個深色的 1",
			d: (c, _o) => {
				c.scale(.86, .86);
				rr$1(c, CREAM, -10.4, -6.8, 20.8, 13.6, 2.2);
				f(c, "#fffaf0", () => c.roundRect(-10.4, -6.8, 20.8, 3, [
					2.2,
					2.2,
					0,
					0
				]));
				ci(c, OUT$2, -10.6, 0, 2.3);
				ci(c, OUT$2, 10.6, 0, 2.3);
				poly$1(c, "#2a1c14", [
					[-.6, -4.6],
					[2, -4.6],
					[2, 4.6],
					[-1.2, 4.6],
					[-1.2, -1.4],
					[-3.2, -.6],
					[-3.2, -3.2]
				], .2);
			}
		},
		delay: {
			zh: "延遲",
			topic: "沙漏（藍框、白玻璃、金沙）",
			d: hourglass
		}
	};
	var redStar = (c, x, y, R = 5.4) => {
		poly$1(c, "#ff4a5a", starPts(x, y, R, R * .45, 6), .3);
		poly$1(c, "#ffffff", starPts(x, y, R * .5, R * .22, 6));
	};
	var shieldAt = (c, o) => at(c, 4.6, 4.6, .56, (q) => ACT.shield.d(q, o, ACT.shield.def));
	var TRIG = {
		on_hit: {
			zh: "命中時",
			topic: "右上一顆大的黃色撞擊閃光，左下短粗的亮劍刺進去",
			d: fit((c, o) => {
				at(c, -2.2, 2.2, .6, (q) => bladeSword(q, o), PI$1 / 4);
				halo(c, o, (q) => burstStar(q, 3.4, -3.4, 7.6, "#ffd23f"));
			}, .9)
		},
		on_kill: {
			zh: "擊倒時",
			topic: "骷髏頭、紅眼",
			src: "b3:finisher",
			d: fit(act$1("finisher"), .88)
		},
		on_crit: {
			zh: "暴擊時",
			topic: "橘黃兩層的八芒大閃光、白芯",
			d: (c, _o) => {
				poly$1(c, "#ff9a2a", starPts(0, 0, 11, 4.2, 4), .3);
				poly$1(c, "#ffd23f", starPts(0, 0, 8.2, 3.2, 4, -PI$1 / 4), .3);
				poly$1(c, "#ffffff", starPts(0, 0, 5, 1.9, 4));
			}
		},
		on_natural_20: {
			zh: "擲出自然 20 時",
			topic: "淡紫的二十面骰（六角、三個切面），正面寫 20",
			d: (c, o) => {
				poly$1(c, "#cfc4ff", [
					0,
					1,
					2,
					3,
					4,
					5
				].map((i) => [Math.cos(i / 6 * TAU$1 - PI$1 / 2) * 10.6, Math.sin(i / 6 * TAU$1 - PI$1 / 2) * 10.6]), .5);
				poly$1(c, "#8a76d8", [
					[9.2, -5.3],
					[9.2, 5.3],
					[0, 10.6],
					[5.6, 4]
				]);
				poly$1(c, "#8a76d8", [
					[-9.2, 5.3],
					[0, 10.6],
					[-5.6, 4]
				]);
				poly$1(c, "#ffffff", [
					[0, -6.2],
					[5.8, 4],
					[-5.8, 4]
				], .4);
				if (!o.tiny) {
					c.fillStyle = "#3a2a7a";
					c.font = "900 6.2px Arial, sans-serif";
					c.textAlign = "center";
					c.textBaseline = "middle";
					c.fillText("20", 0, 1.2);
				}
			}
		},
		on_move: {
			zh: "移動後",
			topic: "一隻褐色的靴子，後面兩道速度線",
			src: "style:hud.move",
			d: boot
		},
		on_damaged: {
			zh: "受傷時",
			topic: "米白人形，右上一顆紅色撞擊星",
			d: (c, o) => {
				bust(c, CREAM, -1.8, 1.4, 1);
				halo(c, o, (q) => redStar(q, 5, -4.8, 5.6));
			}
		},
		on_status_applied: {
			zh: "施加狀態後",
			topic: "掛在橫桿上的淡紫小旗",
			d: banner
		},
		on_cast_tag: {
			zh: "施放帶標籤的技能後",
			topic: "一張斜放的金色吊牌",
			d: fit(tag, .88)
		},
		on_collision: {
			zh: "造成撞擊後",
			topic: "一個米白的三角撞上右邊的石牆，中間一顆撞擊星",
			d: (c, o) => {
				wall(c, 5.4);
				poly$1(c, CREAM, [
					[-10.6, -4],
					[-3.6, 0],
					[-10.6, 4]
				], .5);
				halo(c, o, (q) => burstStar(q, 2.6, 0, 6));
			}
		},
		on_turn_start: {
			zh: "回合開始時",
			topic: "藍色地平線上升起半個太陽，五道短光芒",
			d: (c, _o) => {
				for (const a of [
					-1.2,
					-.6,
					0,
					.6,
					1.2
				]) at(c, 0, 5, 1, (q) => rr$1(q, "#ffd23f", -1.3, -12.6, 2.6, 3.8, 1.2), a);
				f(c, "#ffb23a", () => {
					c.arc(0, 5, 7.4, PI$1, 0);
					c.closePath();
				});
				f(c, "#ffe14d", () => {
					c.arc(0, 5, 5.4, PI$1, 0);
					c.closePath();
				});
				rr$1(c, "#7ab8f0", -10.4, 5, 20.8, 2.8, 1.4);
			}
		},
		on_turn_end: {
			zh: "回合結束時",
			topic: "地平線上一彎淡紫的月牙",
			d: (c, o) => {
				f(c, "#d8c0ff", () => {
					c.arc(-.6, -2.4, 8.2, .2417, 4.652, false);
					c.arc(2.4, -4.9, 6.6, -2.137, .747, true);
					c.closePath();
				});
				rr$1(c, "#7a5ac8", -11, 6.2, 22, 3.8, 1.9);
				if (!o.tiny) star4(c, "#ffffff", 6.6, -6.6, 2.8, null);
			}
		},
		on_enter_surface: {
			zh: "敵人進入你的表面時",
			topic: "一隻靴子踩進一灘藍水漬",
			d: (c, o) => {
				puddle(c, "#4aa8ff", "#cfe8ff", 7.2);
				halo(c, o, (q) => at(q, .6, -2, .82, (p) => bootOnly(p, o)));
			}
		},
		on_summon_downed: {
			zh: "召喚物倒下時",
			topic: "一隻歪倒、變灰的小靈，右下一個朝下的紅箭頭",
			d: (c, o) => {
				at(c, -1.8, -1.2, .86, (q) => ACT.summon.d(q, o, ["#8ab0a8", "#d6e6e2"]), .5);
				halo(c, o, (q) => poly$1(q, ENEMY, [
					[6, 10.6],
					[10.8, 4.6],
					[8, 4.6],
					[8, -1],
					[4, -1],
					[4, 4.6],
					[1.2, 4.6]
				], .3));
			}
		},
		every_n_hits: {
			zh: "每命中 n 次",
			topic: "由小到大斜排的三顆四芒閃光，最後一顆是金色",
			d: (c, o) => {
				star4(c, "#ffffff", -6.8, 4.6, 4.6, null);
				star4(c, "#ffffff", -.6, .6, 5.2, null);
				halo(c, o, (q) => star4(q, "#ffc23a", 5.6, -4.6, 6.4, "#ffffff"));
			}
		},
		enemy_enters_adjacent: {
			zh: "敵人靠近時",
			topic: "右邊米白人形，左邊一個朝它的紅箭頭",
			d: (c, _o) => {
				bust(c, CREAM, 5, 1.2, .84);
				at(c, -5.6, 1.6, .56, (q) => arrowS(q, ENEMY, "#ffb0a8"));
			}
		},
		enemy_leaves_adjacent: {
			zh: "敵人離開時",
			topic: "左邊米白人形，右邊一個往外的紅箭頭",
			d: (c, o) => {
				bust(c, CREAM, -5, 1.2, .84);
				at(c, 5.6, 1.6, .56, (q) => arrowS(q, ENEMY, "#ffb0a8"));
				if (!o.tiny) {
					rr$1(c, ENEMY, -.6, -4.4, 2.4, 2, 1);
					rr$1(c, ENEMY, -.6, 5.6, 2.4, 2, 1);
				}
			}
		},
		hit_by_spell: {
			zh: "被法術擊中時",
			topic: "左上一顆大的紫色法術星（佔一半），右下一面小藍盾",
			d: (c, o) => {
				shieldAt(c, o);
				halo(c, o, (q) => star4(q, "#c890ff", -3.4, -3.4, 8.6, "#ffffff"));
			}
		},
		hit_by_attack: {
			zh: "被攻擊時",
			topic: "左上一個大的紅箭頭（佔一半）朝右下的小藍盾",
			d: (c, o) => {
				shieldAt(c, o);
				halo(c, o, (q) => at(q, -3.2, -3.2, .88, (p) => arrowS(p, ENEMY, "#ffb0a8"), PI$1 / 4));
			}
		},
		hit_by_melee: {
			zh: "被近戰擊中時",
			topic: "左上一把大的亮劍（佔一半）砍向右下的小藍盾",
			d: (c, o) => {
				shieldAt(c, o);
				halo(c, o, (q) => at(q, -1.8, -1.8, .58, (p) => bladeSword(p, o), PI$1 * .75));
			}
		},
		ally_targeted: {
			zh: "隊友被瞄準時",
			topic: "綠色人形，外面一圈紅色準星",
			d: (c, _o) => {
				bust(c, ALLY, 0, 1.2, .86);
				for (let i = 0; i < 4; i++) st(c, "#ff4a5a", 2.8, (x) => x.arc(0, 0, 9.4, i * PI$1 / 2 + .3, (i + 1) * PI$1 / 2 - .3), "butt");
			}
		},
		ally_downed: {
			zh: "隊友倒下時",
			topic: "躺平的綠色人形，上面一顆小骷髏",
			d: (c, o) => {
				rr$1(c, ALLY, -10, 3, 13.6, 6, 3);
				ci(c, ALLY, 6.6, 5.6, 3.8);
				rr$1(c, "#3f7a5a", -10.6, 9, 21.2, 1.8, .9);
				halo(c, o, (q) => at(q, -1.6, -4.4, .56, (p) => ACT.finisher.d(p, {
					...o,
					small: true
				}, void 0)));
			}
		},
		ally_hit_adjacent: {
			zh: "身旁隊友受擊時",
			topic: "綠色人形，右上一顆紅色撞擊星",
			d: (c, o) => {
				bust(c, ALLY, -3.4, 1.4, .92);
				halo(c, o, (q) => redStar(q, 5.2, -4.6, 5.4));
			}
		}
	};
	/** 名詞表（glossary）有、現行沒有專屬圖的 5 個觸發（現行畫「?」）：建議各用哪一個。不算在 22 個裡。 */
	var TRIG_ALIAS = {
		targeted_by_melee: "hit_by_melee",
		targeted_by_attack: "hit_by_attack",
		enemy_moves_in_range: "enemy_enters_adjacent",
		ally_hit_in_range: "ally_hit_adjacent",
		kin_hit_in_range: "ally_hit_adjacent"
	};
	var LINK = {
		after_action: {
			zh: "接著做",
			topic: "一個朝右的米白粗箭頭",
			d: (c, _o) => {
				poly$1(c, CREAM, [
					[-10.5, -3.6],
					[-.5, -3.6],
					[-.5, -9.6],
					[10.5, 0],
					[-.5, 9.6],
					[-.5, 3.6],
					[-10.5, 3.6]
				], .5);
				poly$1(c, "#ffffff", [
					[-10.5, -3.6],
					[-.5, -3.6],
					[-.5, -9.6],
					[10.5, 0],
					[-10.5, 0]
				]);
			}
		},
		on_hit: {
			zh: "命中才觸發",
			topic: "一個綠色的粗勾",
			d: (c, o) => {
				ln(c, "#5ad06a", 4.8, [
					[-8.4, .8],
					[-2.8, 6.4],
					[8.4, -6.4]
				]);
				if (!o.tiny) ln(c, "#d8ffe0", 1.4, [[-7.4, -.4], [-3.6, 3.4]]);
			}
		},
		on_kill: {
			zh: "擊殺才觸發",
			topic: "骷髏頭、紅眼",
			src: "b3:finisher",
			d: fit(act$1("finisher"), .88)
		},
		delayed: {
			zh: "延遲觸發",
			topic: "沙漏",
			d: hourglass
		},
		after_move: {
			zh: "移動後觸發",
			topic: "靴子加速度線",
			src: "style:hud.move",
			d: boot
		},
		after_gather: {
			zh: "聚集後觸發",
			topic: "左右兩個朝中間的米白大三角，中間一顆金色四芒星",
			d: (c, _o) => {
				for (const s of [-1, 1]) {
					poly$1(c, CREAM, [
						[s * 10.6, -6.4],
						[s * 4.2, 0],
						[s * 10.6, 6.4]
					], .5);
					poly$1(c, "#ffffff", [
						[s * 10.6, -6.4],
						[s * 4.2, 0],
						[s * 10.6, 0]
					]);
				}
				star4(c, "#ffd23f", 0, 0, 4.6, "#ffffff");
			}
		}
	};
	var SKELETON = {
		strike: {
			zh: "打擊",
			topic: "一把斜放的亮色單手劍（亮鋼寬刃、金護手、皮柄，放大到貼色環）",
			d: diagSword()
		},
		area: {
			zh: "範圍",
			topic: "向外擴的衝擊環：中心黃白小爆星，外面一圈斷成四段的橘色粗環，四個斜角各一道往外的淡黃短衝擊",
			d: areaBurst
		},
		control: {
			zh: "控制",
			topic: "一把金鎖",
			src: "b3:bind",
			d: act$1("bind")
		},
		aura: {
			zh: "增益",
			topic: "朝上的粗箭頭加底槓",
			src: "b3:buff",
			d: act$1("buff")
		},
		summon: {
			zh: "召喚",
			topic: "一隻青色的小靈",
			src: "b3:summon",
			d: spirit()
		},
		trap: {
			zh: "陷阱",
			topic: "底板上一排朝上的鋼牙",
			src: "b3:trap",
			d: fit(act$1("trap"), .8)
		},
		displace: {
			zh: "位移",
			topic: "兩個朝右的粗 V 拉開（同效果「衝鋒」）",
			d: dashArt
		},
		rune: {
			zh: "刻印",
			topic: "圓頂石碑加金色菱形符文",
			d: tablet
		},
		consume_status: {
			zh: "引爆狀態",
			topic: "橘色十角爆炸",
			src: "b3:detonate",
			d: act$1("detonate")
		},
		builder_finisher: {
			zh: "累積終結",
			topic: "三根越來越高的金色粗條",
			src: "b3:builder",
			d: act$1("builder")
		},
		stance: {
			zh: "姿態",
			topic: "藍色六角臂章，上面兩道金色 V 形階級條",
			d: (c, _o) => {
				const P = [
					0,
					1,
					2,
					3,
					4,
					5
				].map((i) => [Math.cos(i / 6 * TAU$1 - PI$1 / 2) * 10.6, Math.sin(i / 6 * TAU$1 - PI$1 / 2) * 10.6]);
				poly$1(c, "#5a86d8", P, .5);
				poly$1(c, "#9ab8f0", [
					P[0],
					P[5],
					P[4],
					[-5.6, 3],
					[-5.6, -4.4]
				]);
				for (const y of [-2.6, 3.4]) poly$1(c, "#ffd23f", [
					[-6, y + 1.4],
					[0, y - 3.8],
					[6, y + 1.4],
					[6, y + 4.6],
					[0, y - .6],
					[-6, y + 4.6]
				], .2);
			}
		},
		reaction: {
			zh: "反應",
			topic: "綠色逆時針回轉箭頭",
			d: (c, o) => react(c, o)
		},
		modifier: {
			zh: "改造",
			topic: "一顆金色齒輪",
			src: "b3:modify",
			d: act$1("modify")
		},
		passive: {
			zh: "被動",
			topic: "金色的無限符號（一直生效）",
			d: (c, o) => {
				const P = (x) => {
					x.moveTo(0, 0);
					x.bezierCurveTo(3.6, -8.6, 11, -7, 10, 0);
					x.bezierCurveTo(11, 7, 3.6, 8.6, 0, 0);
					x.bezierCurveTo(-3.6, -8.6, -11, -7, -10, 0);
					x.bezierCurveTo(-11, 7, -3.6, 8.6, 0, 0);
				};
				st(c, "#ffc23a", 4, P);
				if (!o.tiny) st(c, "#fff6c8", 1.3, (x) => {
					x.moveTo(-9, -1.6);
					x.bezierCurveTo(-8.6, -5.4, -4.6, -5.6, -2.6, -2.6);
				});
			}
		},
		combo: {
			zh: "連段",
			topic: "一大一小兩顆四芒閃光",
			src: "b3:combo",
			d: act$1("combo")
		},
		sacrifice: {
			zh: "獻祭",
			topic: "小靈背後一圈橘色的爆炸",
			d: (c, o) => EFFECT.sacrifice_summon.d(c, o)
		}
	};
	var SHAPE_MAP = {
		single: ["單體", "..#/.../@.."],
		self: ["自身", ".../.@./..."],
		ground_tile: ["指定地格", ".v./.#./..."],
		square3: ["3×3", "###/###/###"],
		cross: ["十字", ".#./###/.#."],
		ring: ["環形（自己周圍一圈）", "###/#@#/###"],
		cone: ["錐形", "###/.#./.@."],
		line: ["直線", ".../@##/..."],
		chain: ["連鎖", "#../..#/.#."],
		allies_in_radius: ["範圍內友方", ".a./a@a/.a."],
		unit_then_tile: ["單位再指定格", ".../@>#/..."],
		object_then_tile: ["物件再指定格", ".../o>#/..."],
		unit_pair: ["兩個單位", ".../@=@/..."]
	};
	var UNLIT = "#3a3f4e";
	var LIT = "#ffb23a";
	var shapeArt = (rows) => (c, o) => {
		c.scale(.8, .8);
		rows.split("/").forEach((row, r) => [...row].forEach((ch, i) => {
			const cx = -6.9 + i * 6.9, cy = -6.9 + r * 6.9;
			if (ch === ">") {
				poly$1(c, "#ffffff", [
					[cx - 2.8, cy - 3.4],
					[cx + 3, cy],
					[cx - 2.8, cy + 3.4]
				], .4);
				return;
			}
			if (ch === "=") {
				poly$1(c, "#ffffff", [
					[cx - 3.8, cy],
					[cx - 1.2, cy - 2.8],
					[cx - 1.2, cy - .9],
					[cx + 1.2, cy - .9],
					[cx + 1.2, cy - 2.8],
					[cx + 3.8, cy],
					[cx + 1.2, cy + 2.8],
					[cx + 1.2, cy + .9],
					[cx - 1.2, cy + .9],
					[cx - 1.2, cy + 2.8]
				], .2);
				return;
			}
			if (ch === "v") {
				poly$1(c, "#ffffff", [
					[cx - 3.2, cy - 2.2],
					[cx + 3.2, cy - 2.2],
					[cx, cy + 3]
				], .4);
				return;
			}
			if (ch === "@" || ch === "a") {
				ci(c, ch === "@" ? CREAM : ALLY, cx, cy, 3.5);
				if (!o.tiny) ci(c, "#ffffff", cx - 1.1, cy - 1.1, 1.1);
				return;
			}
			if (ch === "#") {
				rr$1(c, LIT, cx - 3.25, cy - 3.25, 6.5, 6.5, 1.4);
				if (!o.tiny) f(c, "#ffe0a0", () => c.roundRect(cx - 3.25, cy - 3.25, 6.5, 1.8, [
					1.4,
					1.4,
					0,
					0
				]));
				return;
			}
			if (ch === "o") {
				rr$1(c, "#c08a4a", cx - 3, cy - 3, 6, 6, 1);
				f(c, "#8a5a2a", () => c.rect(cx - 3, cy + 1.4, 6, 1.6));
				return;
			}
			rr$1(c, UNLIT, cx - 2.2, cy - 2.2, 4.4, 4.4, 1);
		}));
	};
	var SHAPE = Object.fromEntries(Object.entries(SHAPE_MAP).map(([id, [zh, rows]]) => [id, {
		zh,
		topic: "九宮格示意：" + rows,
		d: shapeArt(rows)
	}]));
	var rangeArt = (c, o) => {
		rr$1(c, "#ffd23a", -10.4, -3.6, 6.6, 7.2, 1.6);
		poly$1(c, "#ffffff", [
			[-2.2, -3.4],
			[1.8, 0],
			[-2.2, 3.4]
		], .5);
		rr$1(c, "#e04a3a", 3.8, -3.6, 6.6, 7.2, 1.6);
		if (!o.tiny) {
			f(c, "#fff3a0", () => c.roundRect(-10.4, -3.6, 6.6, 2, [
				1.6,
				1.6,
				0,
				0
			]));
			f(c, "#ff9a8a", () => c.roundRect(3.8, -3.6, 6.6, 2, [
				1.6,
				1.6,
				0,
				0
			]));
		}
	};
	/** 第 2 版：右上的小箭頭照數值正負（opt.value；正＝朝上橘黃、負＝朝下青色），不再寫死。 */
	var up = (base, bk, sk) => withBadge(base, (c, o, _T, opt) => signArrow(c, o, opt), bk, sk);
	var elementArt = (id) => id === "physical" || !ELEMENT$1[id] ? act$1("hit", [STEEL$1, "#ffffff"]) : from48$1((c, o) => ELEMENT$1[id].d(c, {
		...o,
		small: true
	}));
	var CHANGE = {
		add_element: {
			zh: "加上元素",
			topic: "該元素的道具（第 3 批）加白色加號",
			d: (c, o, _T, opt) => {
				at(c, -1.6, 1.6, .86, (q) => elementArt(opt?.value ?? "fire")(q, o));
				plus(c, o, 6.8, -6.6, .8);
			}
		},
		damage_permille: {
			zh: "傷害增減",
			topic: "白閃光，右上一個小箭頭（照數值正負朝上或朝下）",
			d: up(act$1("hit"))
		},
		hit_bonus: {
			zh: "命中",
			topic: "紅準星，右上一個小箭頭（照正負）",
			d: up(act$1("mark"))
		},
		cooldown_delta: {
			zh: "冷卻",
			topic: "藍鐘，右上一個小箭頭（照正負；冷卻 −1＝朝下青色）",
			d: up(clock)
		},
		area_delta: {
			zh: "範圍",
			topic: "九宮格，右上一個小箭頭（照正負）",
			d: up((c) => grid3(c))
		},
		push_distance_delta: {
			zh: "推距",
			topic: "推開的箭頭，右上一個小箭頭（照正負）",
			d: up(act$1("push"), .74, .44)
		},
		ap_delta: {
			zh: "AP",
			topic: "黃色閃電，右上一個小箭頭（照正負；AP −1＝朝下青色）",
			d: up(bolt)
		},
		range_delta: {
			zh: "射程",
			topic: "黃格、白箭頭、紅格（和卡片的射程同一個），右上一個小箭頭（照正負）",
			d: up(rangeArt)
		},
		add_tags: {
			zh: "加上標籤",
			topic: "金色吊牌加白色加號",
			d: (c, o) => {
				at(c, -1.4, 1.4, .86, (q) => tag(q, o));
				plus(c, o, 6.8, -6.6, .8);
			}
		},
		on_hit_effects: {
			zh: "命中後效果",
			topic: "那個效果的圖，右上一顆小白閃光",
			d: (c, o, _T, opt) => withBadge(opt?.base ?? act$1("detonate"), (q) => star4(q, "#ffffff", 0, 0, 10.6, null))(c, o)
		},
		shape_to: {
			zh: "形狀改為",
			topic: "新形狀的九宮格示意",
			d: (c, o, T, opt) => (SHAPE[String(opt?.value)] ?? SHAPE.square3).d(c, o, T)
		},
		allow_self_target: {
			zh: "可以對自己用",
			topic: "米白人形，外面一圈綠色的環",
			d: (c, _o) => {
				st(c, "#5ad06a", 2.8, (x) => x.arc(0, 0, 9.4, 0, TAU$1));
				bust(c, CREAM, 0, 1.2, .84);
			}
		},
		grant_pierce: {
			zh: "穿透",
			topic: "黃箭頭穿過一道石牆",
			d: (c, o) => EFFECT.charge_through.d(c, o)
		},
		heal_permille: {
			zh: "治療量",
			topic: "綠十字，右上一個小箭頭（照正負）",
			d: up(act$1("heal"))
		},
		summon_hp_permille: {
			zh: "召喚物 HP",
			topic: "小靈，右上一顆紅心",
			d: withBadge(spirit(), (c, _o) => heart(c, "#ff5a4a", 0, 1, 1.3))
		},
		summon_limit_delta: {
			zh: "召喚物上限",
			topic: "小靈，右上一個白色加號（照數值：負＝白色減號）",
			d: (c, o, _T, opt) => {
				at(c, -2.2, 2.2, .8, (q) => spirit()(q, o));
				if (Number(opt?.value ?? 1) < 0) minus(c, o, 6.6, -6.4, .8);
				else plus(c, o, 6.6, -6.4, .8);
			}
		},
		summon_duration_delta: {
			zh: "召喚物持續",
			topic: "小靈，右上一個小沙漏",
			d: withBadge(spirit(), hourglass)
		},
		summon_damage_permille: {
			zh: "召喚物傷害",
			topic: "小靈，右上一顆白閃光",
			d: withBadge(spirit(), (c) => star4(c, "#ffffff", 0, 0, 10.6, null))
		},
		summon_attack_dice: {
			zh: "召喚物攻擊骰",
			topic: "小靈，右上一顆小骰子",
			d: withBadge(spirit(), dice)
		},
		form_upkeep_permille: {
			zh: "形態維持消耗",
			topic: "獸掌印、右下壓一個小沙漏，右上一個小箭頭（照正負；−500‰＝朝下青色）",
			d: up((c, o) => {
				paw(c, o);
				halo(c, o, (q) => at(q, 6.4, 6.6, .46, (p) => hourglass(p, o)));
			})
		},
		form_entry_permille: {
			zh: "形態進入消耗",
			topic: "獸掌印，右上一個小箭頭（照正負）",
			d: up((c, o) => paw(c, o))
		}
	};
	var ELEMENT = Object.fromEntries([
		"physical",
		"fire",
		"ice",
		"lightning",
		"poison",
		"wind",
		"earth",
		"holy",
		"shadow"
	].map((id) => [id, {
		zh: BASE_ZH[id] ?? id,
		topic: id === "physical" ? "鋼白的四芒閃光" : "第 3 批的元素道具：" + ELEMENT$1[id].zh,
		src: id === "physical" ? "b3:hit" : "b3:el:" + id,
		d: elementArt(id)
	}]));
	var hud = (id) => from48$1((c, o) => Q.ART.hud[id].d(c, o), .46);
	var CARD = {
		ap: {
			zh: "AP",
			topic: "黃色閃電（HUD 的 AP 同一個）",
			src: "style:hud.ap",
			px: 16,
			d: hud("ap")
		},
		mana: {
			zh: "法力",
			topic: "藍色水滴（HUD 的法力同一個）",
			src: "style:hud.mana",
			px: 16,
			d: hud("mana")
		},
		stamina: {
			zh: "耐力",
			topic: "金色的脈搏折線（HUD 的耐力同一個）",
			src: "style:hud.stamina",
			px: 16,
			d: hud("stamina")
		},
		hp: {
			zh: "生命",
			topic: "紅心",
			px: 16,
			d: (c, o) => heartArt(c, o, "#f0503e", "#ffb0a0", 1.3)
		},
		source: {
			zh: "源力",
			topic: "六角的淡紫晶石（和圓片的源力同一個；現行是淡紫五角星）",
			px: 16,
			d: crystal
		},
		uses: {
			zh: "次數",
			topic: "米白票券（兩側缺口、中間一道虛線）",
			px: 16,
			d: (c, _o) => {
				c.scale(.86, .86);
				rr$1(c, CREAM, -10.4, -6.8, 20.8, 13.6, 2.2);
				f(c, "#fffaf0", () => c.roundRect(-10.4, -6.8, 20.8, 3, [
					2.2,
					2.2,
					0,
					0
				]));
				ci(c, OUT$2, -10.6, 0, 2.3);
				ci(c, OUT$2, 10.6, 0, 2.3);
				for (const x of [
					-5,
					-1,
					3
				]) f(c, "#8a6a2a", () => c.rect(x, -.9, 2.6, 1.8));
			}
		},
		cooldown: {
			zh: "冷卻",
			topic: "藍邊白面的鐘",
			px: 16,
			d: clock
		},
		range: {
			zh: "射程",
			topic: "黃格（自己）、白箭頭、紅格（目標）",
			px: 16,
			d: rangeArt
		},
		reaction: {
			zh: "反應",
			topic: "綠色逆時針回轉箭頭",
			px: 16,
			d: (c, o) => react(c, o)
		},
		trigger: {
			zh: "觸發",
			topic: "一個橘色的鈴（金色鈴舌）",
			px: 16,
			d: (c, o) => {
				ci(c, "#f0a040", 0, -9.2, 1.8);
				f(c, "#f0a040", () => {
					c.moveTo(-7.8, 5);
					c.quadraticCurveTo(-7, -8.6, 0, -8.6);
					c.quadraticCurveTo(7, -8.6, 7.8, 5);
					c.lineTo(10.2, 7.4);
					c.lineTo(-10.2, 7.4);
					c.closePath();
				});
				ci(c, "#ffd23f", 0, 8.8, 2.3);
				if (!o.tiny) el$1(c, "#ffe0b0", -3.2, -2.6, 1.5, 4.2, .2);
			}
		},
		delayed: {
			zh: "延遲",
			topic: "沙漏（和圓片的延遲同一個；現行是米白的鐘，和冷卻只差顏色）",
			px: 16,
			d: hourglass
		},
		activation: {
			zh: "啟動",
			topic: "金色五角星",
			px: 16,
			d: (c, o) => {
				poly$1(c, "#ffb938", starPts(0, .6, 10.6, 4.5, 5), .5);
				if (!o.tiny) poly$1(c, "#fff0b0", [
					[0, -10],
					[-2.6, -2.8],
					[0, .6]
				]);
			}
		},
		drawback: {
			zh: "缺點",
			topic: "琥珀色警告三角，裡面深色驚嘆號",
			px: 16,
			d: (c, _o) => {
				poly$1(c, "#e0a040", [
					[0, -9.2],
					[9.6, 7.8],
					[-9.6, 7.8]
				], 1.3);
				rr$1(c, "#2a1c14", -1.4, -4.4, 2.8, 7, 1);
				ci(c, "#2a1c14", 0, 5.4, 1.6);
			}
		},
		damage: {
			zh: "傷害",
			topic: "四芒閃光（染元素色；物理是白）",
			src: "b3:hit",
			px: 18,
			d: (c, o, T) => ACT.hit.d(c, o, T ?? ["#e8eef4", "#ffffff"])
		},
		heal: {
			zh: "治療",
			topic: "綠色粗十字",
			src: "b3:heal",
			px: 18,
			d: act$1("heal")
		},
		shield: {
			zh: "護盾",
			topic: "淡藍小盾",
			src: "b3:shield",
			px: 18,
			d: act$1("shield")
		},
		move: {
			zh: "移動",
			topic: "褐色靴子加速度線",
			src: "style:hud.move",
			px: 18,
			d: boot
		},
		status: {
			zh: "狀態",
			topic: "淡紫小旗",
			px: 18,
			d: banner
		},
		surface: {
			zh: "表面",
			topic: "一灘水漬上落下一滴",
			src: "b3:surface",
			px: 18,
			d: surface("water")
		},
		summon: {
			zh: "召喚",
			topic: "青色小靈",
			src: "b3:summon",
			px: 18,
			d: spirit()
		},
		stack: {
			zh: "層數",
			topic: "三根越來越高的金條",
			src: "b3:builder",
			px: 18,
			d: act$1("builder")
		},
		pin: {
			zh: "圖釘",
			topic: "斜放的圖釘：已釘＝紅頭；未釘（opt.pinned false）＝同外形灰鋼色、55% 不透明",
			px: 13,
			d: (c, _o, _T, opt) => {
				const on = opt?.pinned !== false;
				c.save();
				if (!on) c.globalAlpha = .55;
				at(c, 0, 0, 1, (q) => {
					ln(q, on ? STEEL$1 : "#9aa2ac", 2.2, [[0, 2], [0, 10.6]]);
					poly$1(q, on ? "#c8382e" : "#8a929c", [
						[-3, -5],
						[3, -5],
						[5.8, 2.8],
						[-5.8, 2.8]
					], .6);
					rr$1(q, on ? "#f05a48" : "#b4bcc6", -5.4, -10.6, 10.8, 5.4, 2.2);
				}, .6);
				c.restore();
			}
		}
	};
	/** 亮色的弓與箭（遠程技能）：木色弓臂往右鼓、白弦、鋼箭頭朝右（現行是一道弧加一支箭）。 */
	var bowArrow = (c, o) => {
		st(c, "#d8a868", 3.4, (x) => x.arc(-7, 0, 11, -1.15, 1.15), "round");
		if (!o.tiny) st(c, "#fff0d0", 1, (x) => x.arc(-7.6, 0, 11, -.9, -.2), "butt");
		ln(c, "#ffffff", 1.2, [[-2.5, -10], [-2.5, 10]]);
		rr$1(c, "#c3ccd6", -10.4, -1.3, 15, 2.6, 1);
		poly$1(c, "#ffffff", [
			[4, -4.4],
			[10.8, 0],
			[4, 4.4]
		], .4);
		poly$1(c, "#f2e6c8", [
			[-10.8, -4],
			[-6.6, -1.2],
			[-6.6, 1.2],
			[-10.8, 4]
		], .3);
	};
	/** 三張扇開的米白卡（所有技能）：後兩張降一階，前面一張金星。 */
	var cardFan = (c, _o) => {
		for (const [a, col] of [[-.42, "#a8a08a"], [-.14, "#d8ccae"]]) at(c, 0, 4, 1, (q) => rr$1(q, col, -5.4, -14, 10.8, 14.4, 1.8), a);
		at(c, 0, 4, 1, (q) => {
			rr$1(q, CREAM, -5.4, -14, 10.8, 14.4, 1.8);
			poly$1(q, GOLD$5, starPts(0, -6.8, 4, 1.7, 5), .3);
		}, .2);
	};
	var CATS = {
		skeleton: SKELETON,
		effect: EFFECT,
		surface: SURFACE,
		status: STATUS,
		condition: COND,
		cost: COST,
		trigger: TRIG,
		link: LINK,
		shape: SHAPE,
		change: CHANGE,
		element: ELEMENT,
		card: CARD,
		target: {
			all_skills: {
				zh: "所有技能",
				topic: "三張扇開的米白卡（前面一張金星）",
				d: cardFan
			},
			all_attacks: {
				zh: "所有攻擊",
				topic: "兩把交叉的亮色劍（打擊徽章那把，成對）",
				src: "b4:skeleton.strike×2",
				d: (c, o) => {
					diagSword(.76)(c, o);
					halo(c, o, (q) => at(q, 0, 0, 1, (p) => {
						p.scale(-1, 1);
						diagSword(.76)(p, o);
					}));
				}
			},
			attack: {
				zh: "普通攻擊",
				topic: "斜放的亮色單手劍（同打擊徽章）",
				src: "b4:skeleton.strike",
				d: diagSword()
			},
			tag_push: {
				zh: "推擊技能",
				topic: "朝右上的黃白粗箭頭（同效果「推擊」）",
				src: "b3:push",
				d: act$1("push")
			},
			tag_heal: {
				zh: "治療技能",
				topic: "綠色粗十字（同效果「治療」）",
				src: "b3:heal",
				d: act$1("heal")
			},
			tag_control: {
				zh: "控制技能",
				topic: "一把金鎖（同骨架徽章「控制」）",
				src: "b3:bind",
				d: act$1("bind")
			},
			tag_ranged: {
				zh: "遠程技能",
				topic: "木色弓臂、白弦、一支鋼頭箭朝右",
				d: bowArrow
			},
			tag_shout: {
				zh: "吼叫技能",
				topic: "象牙號角加聲波（同第 3 批中性道具「吼聲」）",
				src: "b3:w:roar",
				d: from48$1((c, o) => THINGS.roar.d(c, {
					...o,
					small: true
				}), .44)
			},
			tag_area: {
				zh: "範圍技能",
				topic: "向外擴的衝擊環（同骨架徽章「範圍」）",
				src: "b4:skeleton.area",
				d: areaBurst
			},
			tag_summon: {
				zh: "召喚技能",
				topic: "一隻青色小靈（同效果「召喚」；現行畫傷害閃光）",
				src: "b3:summon",
				d: spirit()
			},
			tag_other: {
				zh: "其他標籤的技能",
				topic: "白色四芒閃光（同現行：沒列的標籤畫傷害）",
				src: "b3:hit",
				d: act$1("hit")
			},
			actions: {
				zh: "其他動作",
				topic: "斜放的亮色單手劍（同普通攻擊；現行同一把劍）",
				src: "b4:skeleton.strike",
				d: diagSword()
			},
			default: {
				zh: "沒寫對象（所有技能）",
				topic: "白色四芒閃光（同現行預設）",
				src: "b3:hit",
				d: act$1("hit")
			}
		}
	};
	/** 沒有 Q 版圖樣的狀態由這個掛鉤畫（樣張頁掛上現行的白色狀態圖樣）；沒掛時畫增益箭頭。 */
	var hooks = { status: null };
	function entry(cat, id) {
		if (cat === "effect" && typeof id === "string") {
			if (id.startsWith("status:")) return entry("status", id.slice(7));
			if (id.startsWith("surface:")) return entry("surface", id.slice(8));
			id = EFFECT_ALIAS[id] ?? id;
		}
		if (cat === "trigger") id = TRIG[id] ? id : TRIG_ALIAS[id] ?? id;
		if (cat === "condition" && typeof id === "string" && id.startsWith("target_has_status:")) {
			const s = entry("status", id.slice(18));
			return {
				zh: "目標帶有狀態：" + (s.zh ?? id.slice(18)),
				topic: "那個狀態的圖，右上一個問號",
				live: s.live,
				d: (c, o, T, opt) => {
					at(c, -1.6, 1.4, .84, (q) => s.d(q, o, T, opt));
					if (!o.tiny) qmark(c, o, 7.4, -6, .8);
				}
			};
		}
		const e = CATS[cat]?.[id];
		if (e) return e;
		if (cat === "status") return {
			zh: id,
			topic: "（沒有 Q 版圖樣：現行圖樣頂著）",
			live: true,
			d: (c, o) => hooks.status ? hooks.status(c, o, id) : ACT.buff.d(c, o, ACT.buff.def)
		};
		return {
			zh: id,
			topic: "（不認得）",
			unknown: true,
			d: (c, o) => qmark(c, {
				...o,
				flat: true
			}, 0, 0, 2)
		};
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qIcon/keywords.ts
	/** 畫在 48 格的既有圖樣：縮到 ±10 單位的座標裡（同 qIconsParts.js 的 from48）。 */
	var from48 = (d, k = .47) => (c, o) => {
		c.save();
		c.scale(k, k);
		c.translate(-24, -24);
		d(c, {
			...o,
			small: true
		});
		c.restore();
	};
	/** 第 3 批的元素道具（畫的時候才查表，見檔頭）。 */
	var el = (id) => from48((c, o) => ELEMENT$1[id].d(c, o));
	var part$1 = (cat, id) => (c, o) => entry(cat, id).d(c, o);
	var act = (id) => (c, o) => ACT[id].d(c, o, ACT[id].def ?? ["#ffd23f", "#ffffff"]);
	/** 第 2 版：撞擊在圖樣 ≤14px（圓章 13、18——裝備格 32、背包格 42）只留一個主體（規則 8）：撞上石牆、炸開的一顆大撞擊星，三角拿掉。
	*  同題材（第 4 批觸發「造成撞擊後」的牆與撞擊星，色與形照抄：qIconsParts.js 的 wall()、burstStar()，那兩個沒有匯出），>14px 照舊呼叫第 4 批。
	*  ≤14px 不包外框，星和牆靠亮度分：牆用暗石色（STONE_D）、左緣一條亮石邊，星是亮黃＋白芯，壓在牆的左緣上。
	*  第 3 版（複審：和倒地都是一顆大黃星）：牆加厚到右半個圓（寬 9.6），星縮小（外徑 9.4→7.8）、往左上移到牆左緣的上半——主體變成「牆」，和倒地「大星壓在地面上」拉開。題材不變。
	*  QI-4a：放在這個檔、不動 `parts.ts` 的 `on_collision`（需求第 4 節第 2 點；技能組裝列 18px 的撞擊部件圓片與 QI-2d 基準不變）。 */
	var COLLIDE_STONE_D = "#8c8474";
	var COLLIDE_STONE_L = "#ece6d6";
	var collision = (c, o) => {
		if (!o.tiny) {
			entry("trigger", "on_collision").d(c, o);
			return;
		}
		rr$1(c, COLLIDE_STONE_D, .8, -10.4, 9.6, 20.8, 1.6);
		f(c, COLLIDE_STONE_L, () => c.rect(.8, -9.4, 2, 18.8));
		poly$1(c, "#ffd23f", starPts(-2.4, -2.8, 7.8, 3.7, 7, -1.2), .3);
		poly$1(c, "#ffffff", starPts(-2.4, -2.8, 3.7, 1.9, 7, -1.2));
	};
	/** 12 個關鍵字（順序同 gearAppearance.json 的 keywords）。k＝圖樣在圓章裡再縮放（方的、四角有東西的收進環內）；src＝沿用哪一批的哪個形。 */
	var LIST = {
		ignite: {
			zh: "點燃",
			topic: "火焰（橘外焰、黃內焰、白芯）",
			src: "b3:el:fire＝b4:element.fire",
			k: 1.04,
			d: el("fire")
		},
		wet: {
			zh: "潮濕",
			topic: "水滴落在兩道波浪上（藍、淺藍、白芯）",
			src: "b3:el:water",
			k: .85,
			d: el("water")
		},
		charged: {
			zh: "帶電",
			topic: "黃閃電（黃、橘暗面、白亮邊）",
			src: "b3:el:lightning＝b4:element.lightning",
			k: 1.02,
			d: el("lightning")
		},
		frozen: {
			zh: "冰凍",
			topic: "三根冰晶（淡藍、深藍暗面、白亮面）",
			src: "b3:el:ice＝b4:element.ice",
			k: 1,
			d: el("ice")
		},
		prone: {
			zh: "倒地",
			topic: "黃色撞擊星壓在地面線上",
			src: "b3:knockdown＝b4:effect.knock_prone",
			k: .74,
			d: act("knockdown")
		},
		collision: {
			zh: "撞擊",
			topic: "米白三角撞上右邊的石牆，中間一顆撞擊星（圖樣 ≤14px：只留石牆＋撞上去的大撞擊星）",
			src: "b4:trigger.on_collision（≤14px 簡化形）",
			k: .76,
			d: collision
		},
		marked: {
			zh: "標記",
			topic: "紅色準星",
			src: "b3:mark＝b4:status.marked＝b5:marked",
			k: .85,
			d: act("mark")
		},
		high_ground: {
			zh: "高地",
			topic: "一座淺石色的山（左坡米白亮面），山頂一個米白小人頭；圖樣 >14px 右上多一個黃箭頭",
			src: "b4:condition.height_advantage",
			k: .73,
			d: part$1("condition", "height_advantage")
		},
		concealed: {
			zh: "隱蔽",
			topic: "紫色兜帽，裡面兩道發亮的斜眼",
			src: "b4:status.concealed＝b5:concealed",
			k: .84,
			d: part$1("status", "concealed")
		},
		summon: {
			zh: "召喚",
			topic: "青色小靈",
			src: "b3:summon＝b4:effect.summon",
			k: 1,
			d: act("summon")
		},
		poisoned: {
			zh: "中毒",
			topic: "綠毒滴，右上一顆泡",
			src: "b3:el:poison＝b4:status.poison＝b5:poison",
			k: .96,
			d: part$1("status", "poison")
		},
		form: {
			zh: "形態",
			topic: "淡紫色的獸掌印",
			src: "b4:effect.enter_form",
			k: .94,
			d: part$1("effect", "enter_form")
		}
	};
	Object.keys(LIST);
	new Set(gearKinds().filter((k) => k.paired).map((k) => k.id));
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/appearance.ts
	/** 元素 → 色（`palette.ts` 的元素主色，與技能特效同一份）；物理與不認得的元素回傳 `undefined`（不套元素色）。 */
	function elementTint(element) {
		return elementTintColors(element)?.primary;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/inkWeaponFrame.ts
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
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/inkSect.ts
	var RED = "#c0392b";
	var HAIR_FALLBACK$1 = "#6a3a1e";
	/** 髮髻（`hair: "bun"`）的正面、側面：短髮＋頭頂一顆髻＋髮帶。回傳 false ＝ 不是髮髻。 */
	function drawBunHair(ctx, look, view) {
		if (look.hair !== "bun") return false;
		const c = look.hairColor ?? HAIR_FALLBACK$1;
		if (view === "back") return true;
		if (view === "front") ink$1(ctx, "hair-bun-f", [
			[-9.6, -42],
			[-10, -48],
			[-5, -52.5],
			[5, -52.5],
			[10, -48],
			[9.6, -42],
			[6, -46.4],
			[0, -47.4],
			[-6, -46.4]
		], c);
		else ink$1(ctx, "hair-bun-s", [
			[-9.2, -38],
			[-9.4, -47],
			[-4, -52.5],
			[3, -52.6],
			[8.6, -48.5],
			[7, -46.4],
			[2, -46],
			[-1.4, -43],
			[-3, -38],
			[-6, -36]
		], c);
		const [bx, by] = view === "front" ? [0, -55.4] : [-2.6, -55];
		drawBun(ctx, view, bx, by, c, look.bunBand);
		return true;
	}
	function drawBun(ctx, view, bx, by, c, band) {
		ink$1(ctx, `bun-${view}`, ellPts(bx, by, 3.4, 3, 12), c);
		stroke$1(ctx, `bun-band-${view}`, [[bx - 2.6, by + 2.2], [bx + 2.6, by + 2.2]], 1, band ?? RED);
	}
	/** 背面頭頂的髮髻（頭髮已照短髮畫好；帽子蓋頭頂時不畫）。 */
	function drawBunBack(ctx, look, coveredTop) {
		if (look.hair !== "bun" || coveredTop) return;
		drawBun(ctx, "back", 0, -55.4, look.hairColor ?? HAIR_FALLBACK$1, look.bunBand);
	}
	var TORSO$2 = {
		front: [
			[-7, -33],
			[7, -33],
			[6, -23],
			[8, -14],
			[0, -12.5],
			[-8, -14],
			[-6, -23]
		],
		side: [
			[-4, -33],
			[3.4, -33],
			[5, -27],
			[4, -22],
			[5.2, -14],
			[-1, -12.5],
			[-5.6, -14],
			[-4.2, -22]
		],
		back: [
			[-7, -33],
			[7, -33],
			[6, -23],
			[8, -14],
			[0, -12.5],
			[-8, -14],
			[-6, -23]
		]
	};
	/** 赤膊（body `kind: "bare"`，護法武僧）：膚色軀幹＋胸線，腰間一條布帶（布帶色＝裝備色）。 */
	function drawBareBody(ctx, view, skin, sash) {
		const F = view !== "side";
		ink$1(ctx, `torso-bare-${view}`, TORSO$2[view], skin);
		if (view === "front") {
			stroke$1(ctx, "pec-l", [[-5, -28.6], [-1.6, -27.4]], .45, darken(skin, .35));
			stroke$1(ctx, "pec-r", [[5, -28.6], [1.6, -27.4]], .45, darken(skin, .35));
		}
		const line = F ? [[-6.4, -22.6], [6.4, -22.6]] : [[-4.2, -22.6], [4.4, -22.6]];
		stroke$1(ctx, `sash-bare-${view}`, line, 2.4, INK$2);
		stroke$1(ctx, `sash-bare2-${view}`, line, 1.6, sash);
	}
	/** 圍裙（robe 的 `apron`，煉丹師）：袍子前面一片；背面看不到。 */
	function drawApron(ctx, it, view) {
		if (it.apron === void 0 || view === "back") return;
		const pts = view === "front" ? [
			[-4.6, -24],
			[4.6, -24],
			[5.6, -6],
			[-5.6, -6]
		] : [
			[1.6, -24],
			[5, -24],
			[6.6, -6],
			[2.2, -6]
		];
		ink$1(ctx, `apron-${view}`, pts, it.apron, { w: .6 });
	}
	/**
	* 背物（`back` 格：`gourd` 藥葫蘆、`puppet_box` 木偶箱）。正面、側面畫在身體後面（`onBody` ＝ false），
	* 背面畫在身體上（`onBody` ＝ true）；呼叫端在兩個時機各叫一次。
	*/
	function drawBackItem(ctx, it, view, onBody) {
		if (it === void 0) return;
		const BK = view === "back";
		if (onBody !== BK) return;
		const S = view === "side";
		if (it.kind === "gourd") {
			const c = it.color ?? "#c8843a";
			const [x, y] = BK ? [2, -24] : S ? [-7, -25] : [-10.6, -37];
			ink$1(ctx, `gourd-b-${view}`, ellPts(x, y, 4, 4.6, 14), c);
			ink$1(ctx, `gourd-t-${view}`, ellPts(x, y - 6.4, 2.6, 2.8, 12), c);
			stroke$1(ctx, `gourd-cord-${view}`, [[x - 2.4, y - 3.4], [x + 2.4, y - 3.4]], .9, RED);
			dot$2(ctx, x, y - 9.4, .9, .9, "#6a4224");
		} else if (it.kind === "puppet_box") {
			const c = it.color ?? MAT.wood;
			const [x0, y0, x1, y1] = BK ? [
				-8,
				-40,
				8,
				-16
			] : S ? [
				-13,
				-45,
				-4,
				-17
			] : [
				-9.4,
				-50,
				9.4,
				-30
			];
			ink$1(ctx, `pbox-${view}`, [
				[x0, y0],
				[x1, y0],
				[x1, y1],
				[x0, y1]
			], c, { sharp: true });
			stroke$1(ctx, `pbox-band-${view}`, [[x0, (y0 + y1) / 2], [x1, (y0 + y1) / 2]], .6);
			if (!S) dot$2(ctx, (x0 + x1) / 2, (y0 + y1) / 2, 1.1, 1.1, MAT.gold);
		}
	}
	/** 腰掛（`waist` 格 `kind: "talismans"`）：黃符三張（側面兩張）；背面看不到。 */
	function drawWaist(ctx, it, view) {
		if (it?.kind !== "talismans" || view === "back") return;
		(view === "side" ? [1.6, 3.6] : [
			-5,
			-2.4,
			4
		]).forEach((x, i) => {
			ink$1(ctx, `tal-${view}-${i}`, [
				[x - 1.1, -22.4],
				[x + 1.1, -22.4],
				[x + 1.3, -15.6],
				[x - .9, -15.4]
			], it.color ?? "#e8c84a", {
				shade: false,
				w: .45,
				sharp: true
			});
			stroke$1(ctx, `tal-m-${view}-${i}`, [
				[x - .3, -21],
				[x + .4, -19.4],
				[x - .3, -17.8]
			], .4, RED);
		});
	}
	/** 念珠（`neck` 格 `kind: "beads"`）；背面看不到。 */
	function drawBeads(ctx, it, view) {
		if (it?.kind !== "beads" || view === "back") return;
		const c = it.color ?? "#6a3a1e";
		const pts = view === "side" ? [
			[-1, -33],
			[.4, -30.6],
			[1.8, -28.4],
			[3, -26.6]
		] : [
			[-5, -33],
			[-4.4, -30.6],
			[-3, -28.6],
			[-1.4, -27.4],
			[0, -27],
			[1.4, -27.4],
			[3, -28.6],
			[4.4, -30.6],
			[5, -33]
		];
		for (const [x, y] of pts) {
			dot$2(ctx, x, y, 1.05, 1.05, INK$2);
			dot$2(ctx, x - .15, y - .15, .75, .75, c);
		}
	}
	/** 白羽披肩（cloak `form: "feather"`）：肩上一圈羽，畫在身體前面；背面不畫（同樣張）。 */
	function drawMantle(ctx, it, view) {
		if (it?.form !== "feather" || view === "back") return;
		const c = it.color ?? "#f2f0ea";
		const pts = view === "side" ? [
			[-5, -34],
			[4, -34],
			[5.6, -28],
			[2, -29],
			[-1.6, -27.4],
			[-5.6, -28.6]
		] : [
			[-9, -34],
			[9, -34],
			[10.6, -28],
			[7, -29.4],
			[3.6, -27.6],
			[0, -29],
			[-3.6, -27.6],
			[-7, -29.4],
			[-10.6, -28]
		];
		ink$1(ctx, `mantle-${view}`, pts, c, { w: .7 });
		if (view === "front") for (const x of [
			-6,
			-2,
			2,
			6
		]) stroke$1(ctx, `mantle-f${x}`, [[x, -33], [x + .6, -29.6]], .4, "#b8b4aa");
	}
	/** 白紗兜帽＋面罩（head `kind: "veil"`，霧行者）：兜帽 70% 半透明。回傳 false ＝ 不是面罩。 */
	function drawVeil(ctx, it, view) {
		if (it.kind !== "veil") return false;
		const vc = it.color ?? "#f2f2f0";
		ctx.save();
		ctx.globalAlpha = .7;
		if (view === "back") ink$1(ctx, "veil-b", [
			[-11, -36],
			[-11.4, -48],
			[-5, -55],
			[5, -55],
			[11.4, -48],
			[11, -30],
			[0, -27],
			[-11, -30]
		], vc);
		else if (view === "front") ink$1(ctx, "veil", [
			[-11, -32],
			[-11.4, -48],
			[-5, -55],
			[5, -55],
			[11.4, -48],
			[11, -32],
			[7.6, -36.6],
			[8.4, -45],
			[0, -48],
			[-8.4, -45],
			[-7.6, -36.6]
		], vc);
		else ink$1(ctx, "veil-s", [
			[-12, -30],
			[-11.4, -46],
			[-5, -55],
			[4, -54.4],
			[9.6, -48.6],
			[9.4, -45],
			[4, -46.6],
			[.6, -42],
			[-1.6, -36],
			[-7, -30]
		], vc);
		ctx.restore();
		if (view !== "back") ink$1(ctx, `mask-${view}`, view === "front" ? [
			[-8, -40],
			[8, -40],
			[6.6, -34.6],
			[-6.6, -34.6]
		] : [
			[2.4, -40],
			[9.6, -40],
			[8, -34.8],
			[2.4, -34.8]
		], "#d8dcdc", { w: .6 });
		return true;
	}
	/** 修士的手持物（主手或副手）：拂塵 `whisk`、符紙 `talisman`、傀儡線 `puppet_cross`。回傳 false ＝ 不是這一層的 kind。 */
	function drawSectHeld(ctx, it, key, x, y, o) {
		if (it.kind !== "whisk" && it.kind !== "talisman" && it.kind !== "puppet_cross") return false;
		ctx.save();
		ctx.translate(x, y);
		if (o.mirror) ctx.scale(-1, 1);
		orientWeapon(ctx, it, o, restLean(ctx, it, o));
		if (it.kind === "whisk") {
			ink$1(ctx, `${key}-handle`, [
				[-.8, 4],
				[.8, 4],
				[.8, -10],
				[-.8, -10]
			], MAT.wood, {
				shade: false,
				w: .6
			});
			ink$1(ctx, `${key}-hair`, [
				[-1.4, -10],
				[1.4, -10],
				[3.6, -16],
				[2.4, -22],
				[0, -19],
				[-2, -23],
				[-3.4, -16]
			], "#f4f0e6", { w: .6 });
		} else if (it.kind === "talisman") {
			ink$1(ctx, `${key}-paper`, [
				[-2, -2],
				[2, -2],
				[2.4, -11],
				[-1.6, -11.4]
			], it.color ?? "#e8c84a", {
				shade: false,
				w: .5,
				sharp: true
			});
			stroke$1(ctx, `${key}-mark`, [
				[0, -10],
				[.8, -8],
				[-.6, -6.4],
				[.6, -4]
			], .5, RED);
		} else {
			ink$1(ctx, `${key}-bar`, [
				[-4.4, -1],
				[4.4, -1],
				[4.4, .6],
				[-4.4, .6]
			], MAT.wood, {
				shade: false,
				w: .5,
				sharp: true
			});
			for (const sx of [
				-4,
				0,
				4
			]) stroke$1(ctx, `${key}-str${sx}`, [[sx, .6], [sx * .6, 11]], .3, "#e8e0d0");
		}
		ctx.restore();
		return true;
	}
	/** 劍穗（sword／dagger 的 `tassel`，劍陣弟子）：在護手下方垂一條；呼叫端已移到手的位置並轉好角度。 */
	function drawTassel(ctx, it, key) {
		if (it.tassel === void 0) return;
		const pts = [
			[0, .6],
			[.8, 4],
			[.2, 7]
		];
		stroke$1(ctx, `${key}-tassel`, pts, 1.6, INK$2);
		stroke$1(ctx, `${key}-tassel2`, pts, 1, it.tassel);
	}
	var SHIELD_FALLBACK = "#2f5fae";
	/** 這一層畫得出來的頭部裝備。 */
	function isInkHeadgear(it) {
		return it.kind === "helmet" || it.kind === "hood" || it.kind === "wizard_hat";
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
	function drawHelmet(ctx, it, view, colors) {
		const m = metalOf(it, colors);
		if (view !== "side") {
			ink$1(ctx, "helm", [
				[-10, -42],
				[-9.6, -49],
				[-4.6, -53.6],
				[4.6, -53.6],
				[9.6, -49],
				[10, -42],
				[10.4, -40],
				[-10.4, -40]
			], m);
			stroke$1(ctx, "helm-band", [[-10, -44.6], [10, -44.6]], .6);
			if (view === "front") ink$1(ctx, "helm-nose", [
				[-.9, -45],
				[.9, -45],
				[.7, -38.6],
				[-.7, -38.6]
			], m, {
				shade: false,
				w: .5
			});
			return;
		}
		ink$1(ctx, "helm-s", [
			[-9.8, -36],
			[-10, -47],
			[-4.6, -53.6],
			[3.6, -53.4],
			[8.8, -48.6],
			[9.6, -44],
			[6, -44.4],
			[2, -43],
			[.4, -38.6],
			[-4, -36.4]
		], m);
		stroke$1(ctx, "helm-band-s", [[-9.8, -44.4], [9.4, -44.6]], .6);
	}
	var HOOD_BACK = [
		[-11, -36],
		[-11.4, -48],
		[-5, -55],
		[5, -55],
		[11.4, -48],
		[11, -36],
		[6, -33],
		[-6, -33]
	];
	var HOOD_FRONT = [
		[-11, -36],
		[-11.4, -48],
		[-5, -55],
		[5, -55],
		[11.4, -48],
		[11, -36],
		[7.6, -36.6],
		[8.4, -45],
		[0, -48],
		[-8.4, -45],
		[-7.6, -36.6]
	];
	var HOOD_SIDE = [
		[-11, -33],
		[-11.4, -46],
		[-5, -55],
		[4, -54.4],
		[9.6, -48.6],
		[9.4, -45],
		[4, -46.6],
		[.6, -42],
		[-1.6, -36],
		[-6, -33.4]
	];
	function drawHood(ctx, view, c) {
		if (view === "back") ink$1(ctx, "hood-b", HOOD_BACK, c);
		else if (view === "front") ink$1(ctx, "hood", HOOD_FRONT, c);
		else ink$1(ctx, "hood-s", HOOD_SIDE, c);
	}
	function drawWizardHat(ctx, it, view, c) {
		const trim = it.trim ?? MAT.gold;
		if (view !== "side") {
			ink$1(ctx, "hat-brim", [
				[-14, -47],
				[-6, -50.6],
				[6, -50.6],
				[14, -47],
				[6, -45.4],
				[-6, -45.4]
			], c);
			ink$1(ctx, "hat-cone", [
				[-6.6, -49],
				[-2, -60],
				[4, -70],
				[3.6, -63],
				[6.6, -49]
			], c);
			stroke$1(ctx, "hat-band", [[-6.4, -50], [6.4, -50]], 1.4, trim);
			return;
		}
		ink$1(ctx, "hat-brim-s", [
			[-13, -47.6],
			[-6, -51],
			[6, -51],
			[13, -47.6],
			[6, -46],
			[-6, -46]
		], c);
		ink$1(ctx, "hat-cone-s", [
			[-6, -49.6],
			[-4, -60],
			[-10, -69.6],
			[-2.4, -63],
			[6.4, -49.6]
		], c);
		stroke$1(ctx, "hat-band-s", [[-6, -50.4], [6.2, -50.4]], 1.4, trim);
	}
	/** 畫 C 畫風的頭部裝備（座標＝C 骨架，頭心 (0,-42)）。不是這一層畫得出來的 kind 回傳 false。 */
	function drawInkHeadgear(ctx, it, view, colors) {
		if (!isInkHeadgear(it)) return false;
		if (it.kind === "helmet") drawHelmet(ctx, it, view, colors);
		else if (it.kind === "hood") drawHood(ctx, view, it.color ?? colors(it)[0]);
		else drawWizardHat(ctx, it, view, it.color ?? colors(it)[0]);
		return true;
	}
	function drawBlade(ctx, it, key, metal, outward = 1) {
		const L = it.kind === "sword" ? 21 : 10;
		const half = it.kind === "sword" && it.form === "broad" ? 1.7 : 1;
		const bow = it.form === "curved" ? 3 * outward : it.form === "kris" ? 3 : 0;
		const bx = (y) => bow * (y / L) ** 2;
		ink$1(ctx, `${key}-blade`, [
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
			ink$1(ctx, `${key}-grip`, [
				[-.9, -2],
				[.9, -2],
				[.9, 4.6],
				[-.9, 4.6]
			], "#3a2a1c", {
				shade: false,
				w: .5
			});
			ink$1(ctx, `${key}-guard`, [
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
		ink$1(ctx, `${key}-guard`, [
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
		ink$1(ctx, `${key}-haft`, [
			[-.8, 9],
			[.8, 9],
			[.8, -24],
			[-.8, -24]
		], wood, {
			shade: false,
			w: .6
		});
		iconHead(ctx, 0, -20, () => {
			ink$1(ctx, `${key}-head`, [
				[.6, -23],
				[7.6, -27],
				[9.4, -20.6],
				[7.6, -14],
				[.6, -18]
			], metal, { w: .8 });
			ink$1(ctx, `${key}-head2`, [
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
		ink$1(ctx, `${key}-pole`, [
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
			ink$1(ctx, `${key}-claw`, [
				[-3, -27],
				[-2.6, -33.4],
				[0, -29],
				[2.6, -33.4],
				[3, -27]
			], wood, {
				shade: false,
				w: .6
			});
			ink$1(ctx, `${key}-orb`, ellPts(0, -30.4, 2.4, 2.4, 10), glow, {
				shade: false,
				w: .6
			});
		});
	}
	/** 弓：弓弦在 +x、弓身往 -x 彎（箭的方向 -x）。`pull`（6M-2）＝ 弓弦中點往 +x 拉開的距離；> 0.5 時搭上一支箭。 */
	function drawBow(ctx, key, wood, pull, metal) {
		stroke$1(ctx, `${key}-string`, pull > 0 ? [
			[2, -15],
			[2 + pull, 0],
			[2, 14]
		] : [[2, -15], [2, 14]], .35, "#e8e0d0");
		ink$1(ctx, `${key}-limb`, [
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
			stroke$1(ctx, `${key}-arrow`, [[2 + pull, 0], [-9, 0]], .9, "#c8a070");
			ink$1(ctx, `${key}-arrowhead`, [
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
	/** 正面圓盾：握在手上，盾心在手的右下方 (0.4, 2.2)（骨架上盾心 (8.6,-21)）。 */
	function drawRoundShield(ctx, it, key, colors) {
		const c = it.color ?? (it.material === void 0 ? SHIELD_FALLBACK : colors(it)[0]);
		const cx = -.4;
		const cy = 2.2;
		ink$1(ctx, `${key}-shield`, ellPts(cx, cy, 6.6, 7, 20), c, { w: 1 });
		stroke$1(ctx, `${key}-shield-rim`, [...ellPts(cx, cy, 5.2, 5.6, 20), [4.8, cy]], .45);
		ink$1(ctx, `${key}-shield-boss`, ellPts(cx, cy, 1.8, 1.8, 10), it.trim ?? MAT.gold, {
			shade: false,
			w: .6
		});
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
	/** 正面圓盾（副手）：以手的位置 (x, y) 為準。不是圓盾回傳 false。 */
	function drawInkShieldFront(ctx, it, x, y, colors) {
		if (it.kind !== "shield_round") return false;
		ctx.save();
		ctx.translate(x, y);
		drawRoundShield(ctx, it, "off", colors);
		ctx.restore();
		return true;
	}
	/** 側面圓盾：一條邊（畫在身體前面、頭與手臂之後）。 */
	function drawInkShieldSide(ctx, it, colors) {
		if (it.kind !== "shield_round") return false;
		const c = it.color ?? (it.material === void 0 ? SHIELD_FALLBACK : colors(it)[0]);
		ink$1(ctx, "shield-s", ellPts(8.5, -23, 2.6, 7, 14), c, { w: .8 });
		return true;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/inkArmor.ts
	var GOLD$4 = MAT.gold;
	var FUR = "#e9e3cf";
	var HORN = "#efe6cc";
	var shiftX = (pts, dx) => pts.map(([x, y]) => [x + dx, y]);
	var COAT = {
		front: [
			[-7, -33],
			[7, -33],
			[6, -23],
			[9.4, -6],
			[1, -5],
			[0, -9.5],
			[-1, -5],
			[-9.4, -6],
			[-6, -23]
		],
		back: [
			[-7, -33],
			[7, -33],
			[6, -23],
			[9.4, -6],
			[0, -4.6],
			[-9.4, -6],
			[-6, -23]
		],
		side: [
			[-4, -33],
			[3.4, -33],
			[5, -27],
			[4, -22],
			[7, -6],
			[-1, -5],
			[-7, -6],
			[-4.2, -22]
		]
	};
	var MAIL = {
		front: [
			[-7, -33],
			[7, -33],
			[6, -23],
			[8, -14],
			[0, -12.5],
			[-8, -14],
			[-6, -23]
		],
		back: [
			[-7, -33],
			[7, -33],
			[6, -23],
			[8, -14],
			[0, -12.5],
			[-8, -14],
			[-6, -23]
		],
		side: [
			[-4, -33],
			[3.4, -33],
			[5, -27],
			[4, -22],
			[5.2, -14],
			[-1, -12.5],
			[-5.6, -14],
			[-4.2, -22]
		]
	};
	function drawCoat(ctx, it, view, c, d) {
		ink$1(ctx, `coat-${view}`, COAT[view], c);
		if (view === "front") {
			ink$1(ctx, "coat-lapel", [
				[-4.4, -33],
				[0, -25.6],
				[4.4, -33],
				[2, -33.4],
				[0, -30.6],
				[-2, -33.4]
			], d, {
				shade: false,
				w: .6
			});
			stroke$1(ctx, "coat-open", [[0, -25], [0, -9.5]], .5);
			for (const y of [
				-23,
				-19,
				-15
			]) dot$2(ctx, 1.8, y, .7, .7, GOLD$4);
		} else if (view === "back") stroke$1(ctx, "coat-split", [[0, -14], [0, -4.8]], .5);
		else stroke$1(ctx, "coat-split-s", [[-1, -12], [-1, -5.2]], .5);
		if (it.form !== "cape") return;
		if (view === "side") ink$1(ctx, "coat-cape-s", ellPts(-.6, -30.4, 4.6, 3, 12), d, { w: .7 });
		else ink$1(ctx, `coat-cape-${view}`, [
			[-9.2, -33.4],
			[9.2, -33.4],
			[10.4, -27],
			[0, -25.6],
			[-10.4, -27]
		], d, { w: .7 });
	}
	function drawMail(ctx, it, view, c) {
		ink$1(ctx, `torso-${view}`, MAIL[view], c);
		const side = view === "side";
		const x0 = side ? -3 : -4.6;
		const x1 = side ? 3 : 4.6;
		const scale = it.form === "scale";
		let row = 0;
		for (let y = -30.4; y < -14; y += 2.6, row++) for (let x = x0 + (row % 2 === 0 ? 0 : 1.3); x <= x1; x += 2.6) {
			const k = `mail-${view}-${row}-${Math.round(x * 10)}`;
			if (scale) stroke$1(ctx, k, [
				[x - 1.1, y],
				[x, y + 1.1],
				[x + 1.1, y]
			], .3);
			else stroke$1(ctx, k, [[x - .4, y], [x + .4, y + .3]], .35);
		}
	}
	/** 身體：mail、coat 的 C 版（含軀幹）。回傳 false ＝ 不是這一層的 kind。 */
	function drawInkBodyArmor(ctx, it, view, colors) {
		const [c, d] = colors(it);
		if (it.kind === "mail") drawMail(ctx, it, view, c);
		else if (it.kind === "coat") drawCoat(ctx, it, view, c, d);
		else return false;
		return true;
	}
	var baseColor = (it, colors) => it.color ?? colors(it)[0];
	function drawWideHat(ctx, it, view, colors) {
		const c = baseColor(it, colors);
		const trim = it.trim ?? darken(c, .4);
		const dx = view === "side" ? -1 : 0;
		ink$1(ctx, `wide-brim-${view}`, [
			[-15.4, -46.4],
			[-8, -49.8],
			[8, -49.8],
			[15.4, -46.4],
			[8, -44.4],
			[-8, -44.4]
		], darken(c, .12));
		ink$1(ctx, `wide-crown-${view}`, shiftX([
			[-7, -47.6],
			[-6.6, -55],
			[-2, -58.4],
			[2, -58.4],
			[6.6, -55],
			[7, -47.6]
		], dx), c);
		stroke$1(ctx, `wide-band-${view}`, [[-7 + dx, -49.4], [7 + dx, -49.4]], 1.4, trim);
	}
	function drawCap(ctx, it, view, colors) {
		const [c, d] = colors(it);
		const fur = it.form === "fur";
		const dx = view === "side" ? -.6 : 0;
		ink$1(ctx, `cap-${view}`, shiftX([
			[-9.6, -43],
			[-9.4, -50],
			[-4.6, -54.4],
			[4.6, -54.4],
			[9.4, -50],
			[9.6, -43]
		], dx), c);
		const bot = fur ? -41.8 : -43.4;
		ink$1(ctx, `cap-band-${view}`, shiftX([
			[-10.2, -46.8],
			[10.2, -46.8],
			[10.4, bot],
			[-10.4, bot]
		], dx), fur ? FUR : d, { w: .7 });
	}
	function drawCirclet(ctx, it, view, colors) {
		const c = baseColor(it, colors);
		const dx = view === "side" ? -.6 : 0;
		if (it.kind === "crown") {
			ink$1(ctx, `crown-${view}`, shiftX([
				[-7, -49.4],
				[-6.6, -56],
				[-3.4, -52.6],
				[0, -57.4],
				[3.4, -52.6],
				[6.6, -56],
				[7, -49.4],
				[0, -48]
			], dx), c, { w: .8 });
			if (view === "front") dot$2(ctx, 0, -51.4, 1.1, 1.1, "#d23c3c");
			return;
		}
		ink$1(ctx, `bandana-${view}`, shiftX([
			[-9.4, -44.4],
			[-9.1, -49.6],
			[-4.6, -53.2],
			[4.6, -53.2],
			[9.1, -49.6],
			[9.4, -44.4],
			[0, -46.4]
		], dx), c);
		const tail = darken(c, .25);
		if (view === "back") ink$1(ctx, "bandana-knot", [
			[-1.8, -47],
			[1.8, -47],
			[3.4, -42],
			[0, -43.6],
			[-3.4, -42]
		], tail, { w: .6 });
		else ink$1(ctx, `bandana-tail-${view}`, shiftX([
			[8.4, -47],
			[13, -44.4],
			[11.8, -40.4],
			[9, -44]
		], dx), tail, { w: .6 });
	}
	var GREAT = {
		front: [
			[-10.4, -34],
			[-10.6, -49],
			[-5, -54.8],
			[5, -54.8],
			[10.6, -49],
			[10.4, -34],
			[5, -32.4],
			[-5, -32.4]
		],
		back: [
			[-10.4, -34],
			[-10.6, -49],
			[-5, -54.8],
			[5, -54.8],
			[10.6, -49],
			[10.4, -34],
			[5, -32.4],
			[-5, -32.4]
		],
		side: [
			[-10, -35],
			[-10.4, -48],
			[-5, -54.6],
			[4, -54.2],
			[9.8, -49],
			[10.6, -39],
			[7.6, -33.6],
			[-6, -33.4]
		]
	};
	function drawGreathelm(ctx, it, view, colors) {
		ink$1(ctx, `great-${view}`, GREAT[view], metalOf(it, colors));
		if (view === "front") {
			ink$1(ctx, "great-slit", [
				[-6.8, -44.6],
				[6.8, -44.6],
				[6.8, -42.6],
				[-6.8, -42.6]
			], "#1d1a22", {
				shade: false,
				w: .5
			});
			stroke$1(ctx, "great-bar", [[0, -42], [0, -34.4]], .7);
		} else if (view === "side") {
			ink$1(ctx, "great-slit-s", [
				[1.4, -44.6],
				[10, -44.6],
				[10, -42.6],
				[1.4, -42.6]
			], "#1d1a22", {
				shade: false,
				w: .5
			});
			stroke$1(ctx, "great-bar-s", [[8, -42], [8, -34.6]], .7);
		} else stroke$1(ctx, "great-seam", [[0, -54], [0, -33.4]], .5);
	}
	function drawHorned(ctx, it, view, colors) {
		if (view === "side") {
			ink$1(ctx, "horn-far", [
				[-1, -50.4],
				[-7, -53.4],
				[-9, -61],
				[-4.2, -57.4],
				[1.6, -52.8]
			], darken(HORN, .3), { w: .7 });
			drawHelmet(ctx, {
				...it,
				kind: "helmet"
			}, view, colors);
			ink$1(ctx, "horn-side", [
				[-3, -50],
				[-9, -53],
				[-10.6, -61],
				[-6, -57],
				[0, -52.6]
			], HORN, { w: .7 });
			return;
		}
		drawHelmet(ctx, {
			...it,
			kind: "helmet"
		}, view, colors);
		for (const s of [-1, 1]) ink$1(ctx, `horn-${view}-${s}`, [
			[s * 9, -48],
			[s * 15.6, -50.4],
			[s * 15.4, -59],
			[s * 11.4, -53.6],
			[s * 7, -52]
		], HORN, { w: .7 });
	}
	/** 其餘頭部裝備（dollGear 已把 helmet 的 horned／greathelm 形制轉成 horned_helm／greathelm kind）。 */
	function drawInkHeadgearMore(ctx, it, view, colors) {
		switch (it.kind) {
			case "wide_hat":
				drawWideHat(ctx, it, view, colors);
				return true;
			case "cap":
				drawCap(ctx, it, view, colors);
				return true;
			case "bandana":
			case "crown":
				drawCirclet(ctx, it, view, colors);
				return true;
			case "greathelm":
				drawGreathelm(ctx, it, view, colors);
				return true;
			case "horned_helm":
				drawHorned(ctx, it, view, colors);
				return true;
			default: return false;
		}
	}
	/**
	* 手與前臂護具。(x, y) ＝ 手心，`ang` ＝ 前臂傾角（弧度；袖口沿前臂往肩膀方向畫）。
	* 沒有手部裝備、`bracers`、露指手套露膚色；其他 kind（含不認得的）用裝備色。
	*/
	function drawInkHand(ctx, hands, key, x, y, ang, skin, colors) {
		ctx.save();
		ctx.translate(x, y);
		ctx.rotate(ang);
		let handC = skin;
		let r = 1.8;
		if (hands !== void 0) {
			const [c, d] = colors(hands);
			if (hands.kind === "gauntlets") {
				const m = metalOf(hands, colors);
				ink$1(ctx, `${key}-cuff`, [
					[-2.7, -5.8],
					[2.7, -5.8],
					[2.4, -1],
					[-2.4, -1]
				], m, { w: .7 });
				if (hands.form === "mail") for (const yy of [
					-4.6,
					-3,
					-1.8
				]) stroke$1(ctx, `${key}-ml${yy}`, [[-1.6, yy], [1.6, yy]], .3);
				else stroke$1(ctx, `${key}-rid`, [[-2.4, -3.4], [2.4, -3.4]], .5);
				handC = m;
				r = 2.2;
			} else if (hands.kind === "bracers") {
				if (hands.form === "ring") ink$1(ctx, `${key}-cuff`, [
					[-2.4, -4.2],
					[2.4, -4.2],
					[2.3, -2.4],
					[-2.3, -2.4]
				], metalOf(hands, colors), {
					shade: false,
					w: .6
				});
				else {
					ink$1(ctx, `${key}-cuff`, [
						[-2.5, -5.4],
						[2.5, -5.4],
						[2.3, -1.4],
						[-2.3, -1.4]
					], c, {
						shade: false,
						w: .7
					});
					stroke$1(ctx, `${key}-strap`, [[-2.2, -3.4], [2.2, -3.4]], .4);
				}
			} else if (hands.form === "fingerless") ink$1(ctx, `${key}-band`, [
				[-2.2, -.3],
				[2.2, -.3],
				[2.2, 1.5],
				[-2.2, 1.5]
			], c, {
				shade: false,
				w: .5
			});
			else {
				if (hands.form === "long") ink$1(ctx, `${key}-cuff`, [
					[-2.6, -6.6],
					[2.6, -6.6],
					[2.3, -1],
					[-2.3, -1]
				], d, {
					shade: false,
					w: .7
				});
				handC = c;
				r = 2.1;
			}
		}
		ink$1(ctx, key, ellPts(0, 0, r, r, 10), handC, {
			shade: false,
			w: .6
		});
		ctx.restore();
	}
	/** 靴筒上緣：shoes 低鞋、iron_boots 高；其餘由 inkDoll 決定。 */
	function footTop(feet) {
		if (feet?.kind === "shoes") return -3.4;
		if (feet?.kind === "iron_boots") return -9;
	}
	/** 鞋靴的額外細節（綁腿、鐵靴鞋尖與護片），畫在腿與靴之後。 */
	/** `only`（6M-1 姿勢用）：只畫一條腿（`sx`；側面只有近側 1）的大腿段（護膝）或小腿靴段（綁腿、鐵靴鞋尖）；不給＝照原本一次畫完。 */
	function drawFootDetail(ctx, feet, view, colors, heavy = false, only) {
		if (feet === void 0) return;
		const sides = only !== void 0 ? [only.sx] : view === "side" ? [1] : [-1, 1];
		const upper = only === void 0 || only.part === "upper";
		const lower = only === void 0 || only.part === "lower";
		if (feet.kind === "shoes" && feet.form === "wrapped") {
			if (!lower) return;
			const d = colors(feet)[1];
			for (const sx of sides) for (const y of [-5.4, -7.2]) {
				const [a, b] = view === "side" ? [-.4, 3.8] : sx > 0 ? [.8, 4.6] : [-4.6, -.8];
				stroke$1(ctx, `wrap-${view}-${sx}-${y}`, [[a, y], [b, y + .9]], .6, d);
			}
		} else if (feet.kind === "greaves" && feet.form === "knee" && view !== "back") {
			if (!upper) return;
			for (const sx of sides) {
				const cx = view === "side" ? 1.6 : sx * 2.7;
				ink$1(ctx, `knee-${view}-${sx}`, ellPts(cx, -9, 2.4, 1.8, 10), heavy ? lighten(metalOf(feet, colors), .35) : metalOf(feet, colors), {
					shade: false,
					w: .6
				});
			}
		} else if (feet.kind === "iron_boots") {
			if (!lower) return;
			for (const sx of sides) if (view === "side") stroke$1(ctx, "ib-cap-s", [[2, -3.2], [6.4, -1.6]], .5);
			else stroke$1(ctx, `ib-cap-${sx}`, [[sx * 1, -2.6], [sx * 4.8, -2.6]], .5);
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/inkOffhand.ts
	var GOLD$3 = MAT.gold;
	var PAGE = "#f2ead6";
	var WOOD$1 = MAT.wood;
	var isKiteShield = (it) => it.kind === "shield_kite";
	var isInkOffhandHeld = (it) => it.kind === "tome" || it.kind === "orb" || it.kind === "shield_kite";
	var bodyColor = (it, colors) => it.color ?? colors(it)[0];
	var KITE = [
		[-6, -6.4],
		[6, -6.4],
		[5.8, 2],
		[0, 12],
		[-5.8, 2]
	];
	var TOWER = [
		[-6, -9.4],
		[6, -9.4],
		[6.4, 11],
		[-6.4, 11]
	];
	function drawKiteFront(ctx, it, colors) {
		const c = bodyColor(it, colors);
		const tower = it.form === "tower";
		ink$1(ctx, "kite", tower ? TOWER : KITE, c, { w: 1 });
		if (tower) {
			stroke$1(ctx, "kite-ridge", [[0, -8.6], [0, 10.4]], .7, "#e8e0c8");
			stroke$1(ctx, "kite-rim", [
				[-4.8, -8],
				[4.8, -8],
				[5.2, 9.6],
				[-5.2, 9.6],
				[-4.8, -8]
			], .4);
			for (const y of [-6, 8]) ink$1(ctx, `kite-rivet-${y}`, ellPts(0, y, .9, .9, 8), GOLD$3, {
				shade: false,
				w: .4
			});
		} else {
			stroke$1(ctx, "kite-ridge", [[0, -5.6], [0, 9.4]], .6, "#e8e0c8");
			stroke$1(ctx, "kite-rim", [
				[-4.6, -4.8],
				[4.6, -4.8],
				[4.4, 1.8],
				[0, 9.6],
				[-4.4, 1.8],
				[-4.6, -4.8]
			], .4);
			ink$1(ctx, "kite-boss", ellPts(0, -.6, 1.7, 1.7, 10), it.trim ?? GOLD$3, {
				shade: false,
				w: .6
			});
		}
	}
	/** 側面鳶盾／塔盾：一條邊（畫在身體前面、頭之前）。回傳 false ＝ 不是這一層的盾。 */
	function drawInkKiteSide(ctx, it, colors) {
		if (!isKiteShield(it)) return false;
		const c = bodyColor(it, colors);
		if (it.form === "tower") {
			ink$1(ctx, "kite-s", [
				[7, -33],
				[10.6, -33],
				[10.8, -10],
				[6.8, -10]
			], c, { w: .8 });
			stroke$1(ctx, "kite-s-ridge", [[10, -32], [10, -11]], .6, "#e8e0c8");
		} else {
			ink$1(ctx, "kite-s", [
				[7.2, -29],
				[10.6, -29],
				[10.2, -17],
				[8.8, -9.6],
				[7.6, -17]
			], c, { w: .8 });
			stroke$1(ctx, "kite-s-ridge", [[9.8, -28], [9.4, -16]], .5, "#e8e0c8");
		}
		return true;
	}
	/** 背面鳶盾／塔盾：木色＋皮帶（座標在鏡像後的背面座標）。 */
	function drawInkKiteBack(ctx, it) {
		const tower = it.form === "tower";
		ctx.save();
		ctx.translate(8.6, -21);
		ink$1(ctx, "kite-b", tower ? TOWER : KITE, WOOD$1, { w: 1 });
		stroke$1(ctx, "kite-strap", tower ? [[-3.6, -3], [3.6, 3]] : [[-3.6, -3.4], [3.6, 2]], 1.2, "#5a3a1e");
		ctx.restore();
	}
	function drawTome(ctx, it, colors, side, shade) {
		const [c0, d0] = colors(it);
		const c = darken(c0, shade);
		const d = darken(d0, shade);
		const trim = darken(it.trim ?? GOLD$3, shade);
		if (it.form === "scroll") {
			const [x0, x1] = side ? [1.4, 5] : [-2.6, 2.6];
			ink$1(ctx, "scroll", [
				[x0, -8.4],
				[x1, -8.4],
				[x1, 5],
				[x0, 5]
			], darken(PAGE, shade), { w: .8 });
			for (const y of [-7.4, 4.2]) ink$1(ctx, `scroll-cap${y}`, [
				[x0 - .6, y - 1],
				[x1 + .6, y - 1],
				[x1 + .6, y + 1],
				[x0 - .6, y + 1]
			], c, {
				shade: false,
				w: .6
			});
			return;
		}
		if (side) {
			ink$1(ctx, "tome-s", [
				[1, -6.4],
				[4.8, -6.4],
				[4.8, 4.6],
				[1, 4.6]
			], c, { w: .8 });
			ink$1(ctx, "tome-s-pages", [
				[4.8, -5.8],
				[5.8, -5.8],
				[5.8, 4],
				[4.8, 4]
			], darken(PAGE, shade), {
				shade: false,
				w: .5
			});
			stroke$1(ctx, "tome-s-band", [[1, -1.4], [4.8, -1.4]], 1, trim);
			return;
		}
		ink$1(ctx, "tome", [
			[-4.8, -6.4],
			[4.8, -6.4],
			[4.8, 3],
			[-4.8, 3]
		], c, { w: .9 });
		ink$1(ctx, "tome-spine", [
			[-4.8, -6.4],
			[-3.4, -6.4],
			[-3.4, 3],
			[-4.8, 3]
		], d, {
			shade: false,
			w: .5
		});
		stroke$1(ctx, "tome-pages", [[-2.6, -5.2], [3.6, -5.2]], .7, darken(PAGE, shade));
		ink$1(ctx, "tome-clasp", ellPts(.4, -1.4, 1.5, 1.5, 8), trim, {
			shade: false,
			w: .5
		});
	}
	function drawOrb(ctx, it, colors, side, shade) {
		const orb = darken(elementTint(it.element) ?? colors(it)[0], shade);
		const floating = it.form === "floating";
		const cx = side ? 3.4 : 0;
		const cy = floating ? -9.4 : -5.6;
		if (floating) stroke$1(ctx, "orb-ring", [...ellPts(cx, cy + 7, 3.8, 1.2, 10), [cx + 3.8, cy + 7]], .4, "rgba(255,255,255,0.7)");
		ctx.save();
		ctx.fillStyle = orb;
		for (const [r, a] of [
			[6.4, .14],
			[5.2, .2],
			[4.4, .28]
		]) {
			ctx.globalAlpha = a;
			ctx.beginPath();
			ctx.arc(cx, cy, r, 0, TAU$2);
			ctx.fill();
		}
		ctx.restore();
		ink$1(ctx, "orb", ellPts(cx, cy, 3.4, 3.4, 12), orb, { w: .8 });
		ink$1(ctx, "orb-hi", ellPts(cx - 1.1, cy - 1.2, .9, .9, 6), "#ffffff", {
			shade: false,
			line: false,
			w: .3
		});
	}
	/**
	* 畫副手手持物。(x, y) ＝ 手心。正面（`side` ＝ false）：鳶盾、書立在身側、法球托在掌上；
	* 側面（遠側手，身體之後）：往前移出身體輪廓外並暗 25%。不是這一層的 kind 回傳 false。
	*/
	function drawInkOffhand(ctx, it, x, y, side, colors, pose = {}) {
		if (!isInkOffhandHeld(it)) return false;
		ctx.save();
		ctx.translate(x, y);
		if (it.kind === "orb" && pose.probe !== void 0) orientWeapon(ctx, it, {
			side,
			probe: pose.probe
		}, null);
		const shade = side ? .25 : 0;
		if (it.kind === "tome") drawTome(ctx, it, colors, side, shade);
		else if (it.kind === "orb") drawOrb(ctx, it, colors, side, shade);
		else if (!side) drawKiteFront(ctx, it, colors);
		ctx.restore();
		return true;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/inkWeapons.ts
	var GOLD$2 = MAT.gold;
	var WOOD = MAT.wood;
	var WOOD_DARK = "#6a4420";
	var STOCK = "#7a5232";
	var GRIP$1 = "#3a2a1c";
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
		ink$1(ctx, `${k}-haft`, rect(-w, y1, w, y0), c, {
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
		ink$1(ctx, `${k}-blade`, pts, c.metal, {
			shade: false,
			w: .8
		});
		stroke$1(ctx, `${k}-fuller`, [[0, -7], [0, -23]], .4, c.dark);
		if (it.form === "serrated") {
			const teeth = [];
			for (let i = 0; i < 6; i += 1) teeth.push([2.3, -8 - i * 3.2], [4.2, -9.4 - i * 3.2]);
			stroke$1(ctx, `${k}-teeth`, teeth, .5, c.metal);
		}
		ink$1(ctx, `${k}-guard`, rect(-5.4, -4.8, 5.4, -3.2), c.gold, {
			shade: false,
			w: .6
		});
		ink$1(ctx, `${k}-grip`, rect(-1, -3.2, 1, 5), c.grip, {
			shade: false,
			w: .5
		});
		ink$1(ctx, `${k}-pommel`, ellPts(0, 6, 1.6, 1.6, 8), c.gold, {
			shade: false,
			w: .5
		});
	}
	function drawHammer(ctx, it, k, c) {
		if (it.form === "mace") {
			haft(ctx, k, 4, -22, c.wood);
			iconHead(ctx, 0, -22, () => {
				ink$1(ctx, `${k}-ball`, ellPts(0, -25, 5, 5, 12), c.metal, { w: .8 });
				stroke$1(ctx, `${k}-flange`, [[-5, -25], [5, -25]], .5, c.dark);
			});
			return;
		}
		if (it.form === "flail") {
			haft(ctx, k, 4, -18, c.wood);
			iconHead(ctx, 0, -18, () => {
				stroke$1(ctx, `${k}-chain`, [
					[0, -18],
					[3.8, -22],
					[3.2, -26]
				], .9, c.dark);
				ink$1(ctx, `${k}-ball`, ellPts(3, -30, 4.4, 4.4, 12), c.metal, { w: .8 });
			});
			return;
		}
		haft(ctx, k, 4, -27, c.wood, 1);
		iconHead(ctx, 0, -26, () => {
			ink$1(ctx, `${k}-head`, rect(-7.6, -35, 7.6, -26), c.metal, {
				w: .9,
				sharp: inIconMode(ctx)
			});
			stroke$1(ctx, `${k}-band`, [[-7.6, -30.5], [7.6, -30.5]], .5, c.dark);
		});
	}
	function drawSpear(ctx, it, k, c) {
		haft(ctx, k, 8, -36, c.wood, 1);
		if (it.form === "trident") {
			for (const sx of [
				-3.6,
				0,
				3.6
			]) ink$1(ctx, `${k}-prong${sx}`, [
				[sx, sx === 0 ? -52 : -49],
				[sx + 1.4, -38],
				[sx - 1.4, -38]
			], c.metal, {
				shade: false,
				w: .6
			});
			ink$1(ctx, `${k}-cross`, rect(-4.4, -39, 4.4, -37.2), c.metal, {
				shade: false,
				w: .6
			});
			return;
		}
		iconHead(ctx, 0, -36, () => {
			const sp = it.form === "halberd" || !inIconMode(ctx) ? 1 : 4 / 3;
			const hp = (x, y) => [x * sp, -36 + (y + 36) * sp];
			ink$1(ctx, `${k}-head`, [
				hp(0, -50),
				hp(3.6, -43),
				hp(0, -36),
				hp(-3.6, -43)
			], c.metal, { w: .8 });
			if (it.form === "halberd") ink$1(ctx, `${k}-axe`, [
				[1.4, -45],
				[8.6, -46.4],
				[8.4, -38.4],
				[1.4, -39.6]
			], c.metal, { w: .8 });
		});
	}
	/** 小圖示的拳套（3T-4d）：正面指虎——壓扁的鋼色方塊、上緣 4 個相連半圓指節（高約方塊 35%）、橫向長條握孔，直立。 */
	function drawFistIcon(ctx, k, c) {
		ink$1(ctx, `${k}-block`, rect(-5.6, -1.5, 5.6, 3.5), c.metal, {
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
			ink$1(ctx, `${k}-knuckle${x}`, arc, c.metal, { w: .7 });
		}
		ink$1(ctx, `${k}-hole`, rect(-3.4, .5, 3.4, 2.1), c.dark, {
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
		ink$1(ctx, `${k}-block`, rect(-3.4, -4, 3.4, 3), c.metal, { w: .8 });
		if (it.form === "knuckle") {
			for (const x of [
				-2.2,
				0,
				2.2
			]) ink$1(ctx, `${k}-stud${x}`, ellPts(x, -4.6, 1.1, 1.1, 8), c.dark, {
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
		for (const x of blades) ink$1(ctx, `${k}-blade${x}`, [
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
		iconHead(ctx, 0, -32, () => ink$1(ctx, `${k}-blade`, [
			[0, -35],
			[7, -38],
			[15, -33],
			[18.4, -22],
			[11, -28],
			[0, -29]
		], c.metal, { w: .8 }));
	}
	function drawWhip(ctx, it, k, c) {
		ink$1(ctx, `${k}-handle`, rect(-1.1, -5, 1.1, 5), c.grip, {
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
		stroke$1(ctx, `${k}-lash`, lash, chain ? 1.3 : 1, chain ? c.dark : c.wood);
		if (chain) for (let i = 1; i < lash.length; i += 1) dot$2(ctx, lash[i][0], lash[i][1], .9, .9, c.metal);
		if (it.form === "bladed") ink$1(ctx, `${k}-tip`, [
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
		ink$1(ctx, `${k}-blade`, [
			[-1.5, -2],
			[-1.3, -19.2],
			[0, -21],
			[1.3, -19.2],
			[1.5, -2]
		], c.metal, {
			shade: false,
			w: .7
		});
		ink$1(ctx, `${k}-groove`, rect(-.6, -18.6, .6, -5), glow, {
			shade: false,
			line: false,
			w: .4
		});
		for (const y of [
			-6.5,
			-10.5,
			-14.5
		]) dot$2(ctx, 0, y, 1, .45, "#e8e2ff");
		ink$1(ctx, `${k}-gear`, ellPts(0, -3.2, 4.6, 2.5, 12), BRASS, {
			shade: false,
			w: .6
		});
		ink$1(ctx, `${k}-crystal`, ellPts(0, -3.2, 1.4, 1.4, 8), glow, {
			shade: false,
			w: .4
		});
		ink$1(ctx, `${k}-grip`, rect(-.9, -1.6, .9, 4.6), c.grip, {
			shade: false,
			w: .5
		});
	}
	function drawScepter(ctx, it, k, c) {
		const gem = elementTint(it.element) ?? c.metal;
		ink$1(ctx, `${k}-shaft`, rect(-1.3, -30, 1.3, 8), WOOD_DARK, {
			shade: false,
			w: .6
		});
		iconHead(ctx, 0, -29, () => {
			const ring = ellPts(0, -34, 6, 6, 16);
			stroke$1(ctx, `${k}-ring`, [...ring, ring[0]], 1.5, c.gold);
			ink$1(ctx, `${k}-gem`, ellPts(0, -34, 3, 3, 10), gem, {
				shade: false,
				w: .6
			});
			dot$2(ctx, -1, -35, .8, .8, "#ffffff");
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
	function drawTotem$1(ctx, it, k) {
		ink$1(ctx, `${k}-pole`, rect(-1.9, -42, 1.9, 8), "#8f5f2c", {
			shade: false,
			w: .6
		});
		for (const [y, col] of [[-39, "#b83a3a"], [-27, "#3a8a8a"]]) {
			ink$1(ctx, `${k}-face${y}`, rect(-5.2, y, 5.2, y + 9), "#b77f3f", { w: .7 });
			stroke$1(ctx, `${k}-brow${y}`, [[-3.4, y + 2], [3.4, y + 2]], 1.2, col);
			stroke$1(ctx, `${k}-mouth${y}`, [[-2.4, y + 6], [2.4, y + 6]], .9, "#1d1a22");
		}
		for (const s of [-1, 1]) ink$1(ctx, `${k}-feather${s}`, [
			[s * 5, -37],
			[s * 10.5, -43],
			[s * 11, -33],
			[s * 5, -31]
		], "#e6e6e0", { w: .6 });
		if (it.glow !== void 0) staffHalo(ctx, it.glow, -46);
		ink$1(ctx, `${k}-orb`, ellPts(0, -46, 3.4, 3.4, 10), it.glow ?? "#7dffb0", {
			shade: false,
			w: .6
		});
		dot$2(ctx, -1, -47, .9, .9, "#ffffff");
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
		ink$1(ctx, `${k}-grip`, grip, it.form === "flintlock" ? STOCK : GRIP$1, {
			shade: false,
			w: .6,
			sharp: inIconMode(ctx)
		});
		ink$1(ctx, `${k}-barrel`, rect(-1.4, -4.4, L, -1.2), c.metal, {
			w: .7,
			sharp: inIconMode(ctx)
		});
		if (it.form === "derringer") ink$1(ctx, `${k}-barrel2`, rect(-1.4, -1.2, L, 1.2), c.dark, {
			shade: false,
			w: .6
		});
		if (it.form === "revolver") ink$1(ctx, `${k}-cyl`, ellPts(1.6, -2.8, 3, 3.2, 10), c.dark, {
			shade: false,
			w: .6
		});
		if (it.form === "flintlock") ink$1(ctx, `${k}-cock`, [
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
		ink$1(ctx, `${k}-stock`, stock, STOCK, {
			shade: false,
			w: .7,
			sharp: icon
		});
		ink$1(ctx, `${k}-grip`, [
			[-1.6, -1],
			[1.2, -1],
			[.8, 4.6],
			[-1.8, 4.6]
		], GRIP$1, {
			shade: false,
			w: .5
		});
		if (icon && it.form !== "blunderbuss") {
			ink$1(ctx, `${k}-barrel`, rect(0, -5.4, L, -2.7), c.metal, {
				w: .8,
				sharp: true
			});
			ink$1(ctx, `${k}-barrel-low`, rect(0, -2.7, L, 0), c.metal, {
				w: .8,
				sharp: true
			});
		} else ink$1(ctx, `${k}-barrel`, rect(0, -5.2, L, -1.2), c.metal, { w: .8 });
		if (it.form === "double" && !icon) ink$1(ctx, `${k}-barrel2`, rect(0, -1.2, L, 1.8), c.dark, {
			shade: false,
			w: .6
		});
		if (it.form === "pump") ink$1(ctx, `${k}-slide`, rect(6, -1.2, 13, 1.6), STOCK, {
			shade: false,
			w: .6
		});
		if (it.form === "blunderbuss") ink$1(ctx, `${k}-flare`, [
			[L - 6, -5.2],
			[L + 2.4, -9],
			[L + 2.4, 3],
			[L - 6, -.8]
		], c.metal, { w: .8 });
	}
	function drawLongGun(ctx, it, k, c) {
		const sniper = it.form === "sniper";
		const L = sniper ? 25 : it.form === "hunting" ? 24 : 22;
		ink$1(ctx, `${k}-stock`, [
			[-10.5, -5],
			[0, -4.6],
			[0, 0],
			[-7.4, 2],
			[-10.5, -1]
		], sniper ? c.dark : STOCK, {
			shade: false,
			w: .7
		});
		ink$1(ctx, `${k}-grip`, [
			[-1.6, -1],
			[1.2, -1],
			[.8, 4.6],
			[-1.8, 4.6]
		], GRIP$1, {
			shade: false,
			w: .5
		});
		ink$1(ctx, `${k}-barrel`, rect(0, -4.6, L, -1.4), c.metal, { w: .8 });
		if (it.form === "hunting") ink$1(ctx, `${k}-fore`, rect(L * .3, -1.4, L, 1), STOCK, {
			shade: false,
			w: .6
		});
		if (it.form === "flintlock") {
			ink$1(ctx, `${k}-cock`, [
				[-.4, -4.6],
				[-2.6, -8.4],
				[.4, -9],
				[2, -4.6]
			], c.dark, {
				shade: false,
				w: .5
			});
			ink$1(ctx, `${k}-band`, rect(L * .45, -4.8, L * .45 + 1.8, -1.2), c.gold, {
				shade: false,
				w: .4
			});
		}
		if (sniper) {
			ink$1(ctx, `${k}-scope`, rect(5, -9, 16, -5.4), "#2a2d33", { w: .7 });
			dot$2(ctx, 16, -7.2, .9, 1.4, "#8fe3ff");
			stroke$1(ctx, `${k}-bipod`, [[20, -1.4], [18.4, 4.6]], .7);
			stroke$1(ctx, `${k}-bipod2`, [[20, -1.4], [22.4, 4.6]], .7);
		}
	}
	function drawCrossbow(ctx, it, k, c) {
		const heavy = it.form === "heavy";
		const span = heavy ? 11.6 : 9.6;
		const tip = heavy ? 15 : 14;
		ink$1(ctx, `${k}-stock`, rect(-3.4, -4.4, tip + 1, -1.4), STOCK, {
			shade: false,
			w: .7
		});
		ink$1(ctx, `${k}-grip`, [
			[-1.4, -1.4],
			[1.4, -1.4],
			[1, 4.4],
			[-1.6, 4.4]
		], GRIP$1, {
			shade: false,
			w: .5
		});
		if (it.form === "repeater") ink$1(ctx, `${k}-mag`, rect(1.6, -9.4, 9.6, -4.4), GRIP$1, { w: .7 });
		stroke$1(ctx, `${k}-string`, [
			[tip, -2.9 - span],
			[tip - 8, -2.9],
			[tip, -2.9 + span]
		], .4, "#e8e0d0");
		stroke$1(ctx, `${k}-arm`, [
			[tip - 1, -2.9 - span],
			[tip + 3, -2.9],
			[tip - 1, -2.9 + span]
		], heavy ? 1.8 : 1.3, c.metal);
		ink$1(ctx, `${k}-bolt`, rect(tip - 12, -5.2, tip + 1, -4.4), c.wood, {
			shade: false,
			w: .4
		});
		ink$1(ctx, `${k}-bolt-tip`, [
			[tip + 1, -5.7],
			[tip + 3.6, -4.8],
			[tip + 1, -3.9]
		], c.metal, {
			shade: false,
			w: .4
		});
		if (heavy) {
			const r = ellPts(tip + 3, -2.9, 2.4, 3.2, 10);
			stroke$1(ctx, `${k}-stirrup`, [...r, r[0]], .8, GRIP$1);
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
		if (it.kind === "staff") return it.form === "totem" ? drawTotem$1 : drawScepter;
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
			wood: darken(WOOD, shade),
			grip: darken(GRIP$1, shade),
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
	Object.freeze({});
	/** 讀一個欄位；沒給或不是有限數字 → 0。 */
	function pz$1(p, k) {
		const v = p?.[k];
		return typeof v === "number" && Number.isFinite(v) ? v : 0;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/inkDoll.ts
	var SKIN_FALLBACK = "#eab48a";
	var HAIR_FALLBACK = "#6a3a1e";
	var PANTS_FALLBACK = "#4a4038";
	var BOOT_FALLBACK = "#5a4030";
	var SHIRT_FALLBACK = "#d8cdb4";
	/** 骨架關節（虛擬像素）：髖（前傾的軸）、側面肩（主手）、側面主手肘；遠側（另一隻手）的肩、肘。 */
	var HIP = [0, -15];
	var SHOULDER_S = [0, -31.6];
	var ELBOW_S = [1.9, -28];
	var SHOULDER_SF = [.6, -32.2];
	var ELBOW_SF = [3.2, -29.4];
	/** 繞 (x,y) 轉 a（畫布旋轉，順時針為正）；a 為 0 時不加任何指令。 */
	function rotAt$1(ctx, x, y, a) {
		if (a === 0) return;
		ctx.translate(x, y);
		ctx.rotate(a);
		ctx.translate(-x, -y);
	}
	/**
	* 一段手臂（RT-5d `reach`）：`k` ≠ 1 時，`fn` 畫的部件沿 a → b 的方向、以 a 為原點拉長 k 倍（寬度不變），
	* 之後的畫布原點跟著移到拉長後的末端（下一段、手接在新的末端，大小不變）。`k` ＝ 1 時直接畫、不多任何指令。
	*/
	function limb$1(ctx, a, b, k, fn) {
		if (k === 1) {
			fn();
			return;
		}
		const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
		ctx.save();
		ctx.translate(a[0], a[1]);
		ctx.rotate(ang);
		ctx.scale(k, 1);
		ctx.rotate(-ang);
		ctx.translate(-a[0], -a[1]);
		fn();
		ctx.restore();
		ctx.translate((b[0] - a[0]) * (k - 1), (b[1] - a[1]) * (k - 1));
	}
	/** 有姿勢時把 `fn` 包在 save／restore 裡、先套 `apply`；沒姿勢時直接畫（不多任何指令）。 */
	function joint(t, apply, fn) {
		if (t.pose === null) {
			fn();
			return;
		}
		t.ctx.save();
		apply(t.ctx, t.pose);
		fn();
		t.ctx.restore();
	}
	/** 正面、背面手臂上下擺（`armL`＝主手側、`armR`＝副手側）。 */
	var swing = (k) => (ctx, p) => {
		const dy = pz$1(p, k);
		if (dy !== 0) ctx.translate(0, dy);
	};
	var colorOf = (h, it, fallback) => it === void 0 ? fallback : h.colors(it)[0];
	function drawLegs(t, view) {
		const { ctx, spec, hooks } = t;
		const { look, gear } = spec;
		const heavy = gear.body?.kind === "plate";
		const pants = heavy ? MAT.iron : look.pants ?? PANTS_FALLBACK;
		const boot = gear.feet !== void 0 ? colorOf(hooks, gear.feet, BOOT_FALLBACK) : heavy ? MAT.steel : BOOT_FALLBACK;
		const by = footTop(gear.feet) ?? (heavy ? -9 : -7);
		const sabaton = gear.feet?.kind === "iron_boots" && gear.feet.form === "sabaton";
		const toeF = sabaton ? 7 : 5.6;
		const toeS = sabaton ? 9.8 : 7.4;
		if (t.pose !== null) {
			drawLegsPosed(t, view, {
				pants,
				boot,
				by,
				toeF,
				toeS,
				heavy
			});
			return;
		}
		if (view !== "side") {
			for (const sx of [-1, 1]) {
				ink$1(ctx, `leg-${sx}`, [
					[sx * .8, -15],
					[sx * 4.6, -15],
					[sx * 4.4, -6],
					[sx * 1, -6]
				], pants);
				ink$1(ctx, `boot-${sx}`, [
					[sx * .6, by],
					[sx * 4.8, by],
					[sx * toeF, -.8],
					[sx * .4, -.4]
				], boot);
			}
			drawFootDetail(ctx, gear.feet, view, hooks.colors, heavy);
			return;
		}
		ink$1(ctx, "leg-far", [
			[-3, -15],
			[.6, -15],
			[-.6, -6],
			[-3.8, -6]
		], darken(pants, .25));
		ink$1(ctx, "boot-far", [
			[-4.2, by],
			[-.4, by],
			[1, -.6],
			[-4.4, -.4]
		], darken(boot, .25));
		ink$1(ctx, "leg-near", [
			[-.6, -15],
			[3.2, -15],
			[3.8, -6],
			[.6, -6]
		], pants);
		ink$1(ctx, "boot-near", [
			[.4, by],
			[4, by],
			[toeS, -.8],
			[.4, -.4]
		], boot);
		drawFootDetail(ctx, gear.feet, view, hooks.colors, heavy);
	}
	/** 有姿勢的腿（6M-1）：正面、背面抬腳（大腿抬 45%、靴再抬 55%）；側面髖、膝兩個關節，並抵銷上半身的前傾，腳才留在地上。部件形狀照沒姿勢的畫法。 */
	function drawLegsPosed(t, view, L) {
		const { ctx, spec, hooks, pose } = t;
		const feet = spec.gear.feet;
		if (view !== "side") {
			for (const sx of [-1, 1]) {
				const up = pz$1(pose, sx < 0 ? "liftL" : "liftR");
				ctx.save();
				if (up !== 0) ctx.translate(0, -up * .45);
				ink$1(ctx, `leg-${sx}`, [
					[sx * .8, -15],
					[sx * 4.6, -15],
					[sx * 4.4, -6],
					[sx * 1, -6]
				], L.pants);
				drawFootDetail(ctx, feet, view, hooks.colors, L.heavy, {
					sx,
					part: "upper"
				});
				if (up !== 0) ctx.translate(0, -up * .55);
				ink$1(ctx, `boot-${sx}`, [
					[sx * .6, L.by],
					[sx * 4.8, L.by],
					[sx * L.toeF, -.8],
					[sx * .4, -.4]
				], L.boot);
				drawFootDetail(ctx, feet, view, hooks.colors, L.heavy, {
					sx,
					part: "lower"
				});
				ctx.restore();
			}
			return;
		}
		ctx.save();
		rotAt$1(ctx, HIP[0], HIP[1], -pz$1(pose, "lean"));
		ctx.save();
		rotAt$1(ctx, -1.2, -15, -pz$1(pose, "hipF"));
		ink$1(ctx, "leg-far", [
			[-3, -15],
			[.6, -15],
			[-.6, -6],
			[-3.8, -6]
		], darken(L.pants, .25));
		rotAt$1(ctx, -2.2, -6.5, pz$1(pose, "kneeF"));
		ink$1(ctx, "boot-far", [
			[-4.2, L.by],
			[-.4, L.by],
			[1, -.6],
			[-4.4, -.4]
		], darken(L.boot, .25));
		ctx.restore();
		ctx.save();
		rotAt$1(ctx, 1.3, -15, -pz$1(pose, "hipN"));
		ink$1(ctx, "leg-near", [
			[-.6, -15],
			[3.2, -15],
			[3.8, -6],
			[.6, -6]
		], L.pants);
		drawFootDetail(ctx, feet, view, hooks.colors, L.heavy, {
			sx: 1,
			part: "upper"
		});
		rotAt$1(ctx, 2.2, -6.5, pz$1(pose, "kneeN"));
		ink$1(ctx, "boot-near", [
			[.4, L.by],
			[4, L.by],
			[L.toeS, -.8],
			[.4, -.4]
		], L.boot);
		drawFootDetail(ctx, feet, view, hooks.colors, L.heavy, {
			sx: 1,
			part: "lower"
		});
		ctx.restore();
		ctx.restore();
	}
	var TORSO$1 = {
		front: [
			[-7, -33],
			[7, -33],
			[6, -23],
			[8, -14],
			[0, -12.5],
			[-8, -14],
			[-6, -23]
		],
		side: [
			[-4, -33],
			[3.4, -33],
			[5, -27],
			[4, -22],
			[5.2, -14],
			[-1, -12.5],
			[-5.6, -14],
			[-4.2, -22]
		],
		back: [
			[-7, -33],
			[7, -33],
			[6, -23],
			[8, -14],
			[0, -12.5],
			[-8, -14],
			[-6, -23]
		]
	};
	function robePts(view, hem) {
		if (view === "side") return [
			[-4, -33],
			[3.4, -33],
			[5, -27],
			[4, -22],
			[7.4, hem],
			[-1, hem + .8],
			[-7.6, hem],
			[-4.2, -22]
		];
		return [
			[-7, -33],
			[7, -33],
			[6, -23],
			[10, hem],
			[0, hem + 1],
			[-10, hem],
			[-6, -23]
		];
	}
	function drawRobe(t, it, view, c) {
		const { ctx } = t;
		const F = view !== "side";
		const hem = it.form === "short" ? -9 : -1.6;
		const trim = t.spec.look.trim ?? it.trim ?? MAT.gold;
		ink$1(ctx, `robe-${view}`, robePts(view, hem), c);
		const hy = hem - 1.6;
		if (view === "front") {
			stroke$1(ctx, "robe-mid", [[0, -31], [0, hem + .2]], 1.4, trim);
			stroke$1(ctx, "robe-mid2", [[0, -31], [0, hem + .2]], .4);
			stroke$1(ctx, "robe-hem", [
				[-9.6, hy],
				[0, hy + 1],
				[9.6, hy]
			], 1.2, trim);
		} else if (view === "back") stroke$1(ctx, "robe-hem-b", [
			[-9.6, hy],
			[0, hy + 1],
			[9.6, hy]
		], 1.2, trim);
		else stroke$1(ctx, "robe-hem-s", [
			[-7.2, hy],
			[-1, hy + .8],
			[7, hy]
		], 1.2, trim);
		stroke$1(ctx, `sash-${view}`, F ? [[-6.2, -23], [6.2, -23]] : [[-4.2, -23], [4.4, -23]], 1.8, darken(c, .4));
	}
	function drawPlateDetail(t, view) {
		const { ctx } = t;
		if (view !== "side") {
			stroke$1(ctx, "plate-c", [[0, -32], [0, -24]], .5);
			stroke$1(ctx, "plate-f", [
				[-7.4, -18.6],
				[0, -17.4],
				[7.4, -18.6]
			], .5);
			for (const sx of [-1, 1]) ink$1(ctx, `pauldron-${sx}`, ellPts(sx * 7.2, -31.4, 3.6, 2.8, 12), MAT.steel, { w: .7 });
			return;
		}
		stroke$1(ctx, "plate-fs", [[-5, -18.6], [5, -18.6]], .5);
		ink$1(ctx, "pauldron-s", ellPts(-.4, -31.4, 3.8, 2.9, 12), MAT.steel, { w: .7 });
	}
	function drawBelt(t, view) {
		const { ctx } = t;
		const F = view !== "side";
		const bx = F ? 6.2 : 4.3;
		const bx0 = F ? -bx : -4.2;
		stroke$1(ctx, `belt-${view}`, [[bx0, -23], [bx, -23]], 1.7, INK$2);
		stroke$1(ctx, `belt2-${view}`, [[bx0, -23], [bx, -23]], .9, "#6b4426");
		if (view === "front") {
			ctx.fillStyle = MAT.gold;
			ctx.fillRect(-1.2, -24.3, 2.4, 2.6);
			stroke$1(ctx, "buckle", [
				[-1.2, -24.3],
				[1.2, -24.3],
				[1.2, -21.7],
				[-1.2, -21.7],
				[-1.2, -24.3]
			], .4);
		}
	}
	function drawBody$1(t, view) {
		const { ctx, spec } = t;
		const it = spec.gear.body;
		const kind = it?.kind ?? "shirt";
		const c = colorOf(t.hooks, it, SHIRT_FALLBACK);
		if (it !== void 0 && kind === "robe") {
			drawRobe(t, it, view, c);
			drawApron(ctx, it, view);
			return;
		}
		if (it !== void 0 && kind === "bare") {
			drawBareBody(ctx, view, t.skin, c);
			return;
		}
		if (it !== void 0 && drawInkBodyArmor(ctx, it, view, t.hooks.colors)) {
			if (kind !== "coat") drawBelt(t, view);
			return;
		}
		const bone = kind === "ribs";
		ink$1(ctx, `torso-${view}`, TORSO$1[view], kind === "plate" ? MAT.steel : bone ? "#d9d2bd" : c);
		const F = view !== "side";
		if (kind === "leather" && view !== "back") {
			stroke$1(ctx, `stitch-${view}`, F ? [[-3.6, -31], [-2.4, -24]] : [[.6, -31], [1.6, -24]], .4);
			if (view === "front") stroke$1(ctx, "stitch2", [[3.6, -31], [2.4, -24]], .4);
		}
		if (kind === "plate") drawPlateDetail(t, view);
		if (kind === "shirt" && view === "front") stroke$1(ctx, "collar", [
			[-2.4, -33],
			[0, -30.4],
			[2.4, -33]
		], .5);
		if (bone && view !== "back") for (const y of [
			-30,
			-27,
			-24,
			-21
		]) stroke$1(ctx, `rib-${view}-${y}`, F ? [
			[-5, y],
			[0, y + 1],
			[5, y]
		] : [
			[-3, y],
			[1, y + 1],
			[3.6, y]
		], .5, "#8a826c");
		if (!bone) drawBelt(t, view);
	}
	function drawCloak(t, view) {
		const { ctx, spec } = t;
		const it = spec.gear.cloak;
		if (it === void 0) return;
		const c = colorOf(t.hooks, it, "#a83030");
		if (view !== "side") ink$1(ctx, `cloak-${view}`, [
			[-8, -33],
			[8, -33],
			[11, -8],
			[5, -6],
			[0, -7.5],
			[-5, -6],
			[-11, -8]
		], c);
		else ink$1(ctx, "cloak-s", [
			[-3, -33],
			[1, -33],
			[-4, -9],
			[-10, -6.5],
			[-13, -9],
			[-8, -22]
		], c);
	}
	function armColor(t) {
		const body = t.spec.gear.body;
		if (body?.kind === "plate") return MAT.steel;
		if (body?.kind === "ribs") return "#d9d2bd";
		if (body?.kind === "bare") return t.skin;
		return colorOf(t.hooks, body, SHIRT_FALLBACK);
	}
	function drawArmFront(t, sx) {
		const pts = sx < 0 ? [
			[-7, -31.5],
			[-4.8, -31],
			[-7.4, -22.5],
			[-9.8, -23.5]
		] : [
			[7, -31.5],
			[4.8, -31],
			[7.4, -22.5],
			[9.8, -23.5]
		];
		ink$1(t.ctx, `arm-${sx}`, pts, armColor(t));
	}
	/** 手（含手套、臂甲的袖口）。`ang` ＝ 前臂傾角。 */
	function drawHand(t, x, y, key, ang) {
		drawInkHand(t.ctx, t.spec.gear.hands, key, x, y, ang, t.skin, t.hooks.colors);
	}
	var HEAD_SIDE = [
		[-8.6, -42],
		[-8, -49],
		[-2, -51.5],
		[5, -50],
		[8.4, -45],
		[8.2, -42],
		[9.6, -39.6],
		[8, -38.6],
		[6.6, -35],
		[0, -34],
		[-6.4, -36]
	];
	function drawHairBack(t, view) {
		const { look } = t.spec;
		if (look.hair !== "long" || look.skull === true) return;
		const c = darken(look.hairColor ?? HAIR_FALLBACK, .15);
		if (view === "front") ink$1(t.ctx, "hair-back", [
			[-10, -44],
			[-9.6, -30],
			[-5, -29],
			[5, -29],
			[9.6, -30],
			[10, -44],
			[0, -52]
		], c);
		else if (view === "side") ink$1(t.ctx, "hair-back-s", [
			[-9.6, -44],
			[-10.6, -29],
			[-5, -28.4],
			[-2, -34],
			[0, -46]
		], c);
	}
	function drawFace(t, view) {
		const { ctx } = t;
		const { look } = t.spec;
		const F = view === "front";
		if (look.skull === true) {
			for (const x of F ? [-3.2, 3.2] : [4.4]) dot$2(ctx, x, -41, 1.9, 2.2, look.eyes ?? "#2b1e16");
			stroke$1(ctx, `skull-teeth-${view}`, F ? [[-2.6, -37], [2.6, -37]] : [[3.4, -37], [7.2, -37]], .7);
			return;
		}
		for (const x of F ? [-3.2, 3.2] : [4.4]) drawEye(ctx, look, x);
		ctx.fillStyle = "rgba(220,90,80,0.32)";
		for (const x of F ? [-5.4, 5.4] : [3.2]) {
			ctx.beginPath();
			ctx.ellipse(x, -38.6, 1.6, .9, 0, 0, Math.PI * 2);
			ctx.fill();
		}
		if (look.beard !== true) stroke$1(ctx, `mouth-${view}`, F ? [
			[-1, -37.4],
			[0, -36.8],
			[1, -37.4]
		] : [[6.4, -37], [7.4, -36.6]], .5);
		drawRaceFace(ctx, look, F ? "front" : "side");
	}
	function drawHair(t, view) {
		const { look, gear } = t.spec;
		if (look.hair === void 0 || look.hair === "none" || look.skull === true) return;
		const c = look.hairColor ?? HAIR_FALLBACK;
		const covered = gear.head !== void 0 && coverOf$1(gear.head).hair === true && hatAdjust(look, gear.head).dy === 0;
		if (view === "back") {
			const pts = look.hair === "long" ? [
				[-9.8, -44],
				[-6, -51.8],
				[6, -51.8],
				[9.8, -44],
				[9.6, -30],
				[0, -28.6],
				[-9.6, -30]
			] : [
				[-9.6, -42],
				[-6, -51.8],
				[6, -51.8],
				[9.6, -42],
				[8, -36],
				[0, -34.4],
				[-8, -36]
			];
			ink$1(t.ctx, "hair-b", pts, c);
			drawBunBack(t.ctx, look, coverOf$1(gear.head).top === true);
			return;
		}
		if (covered) return;
		if (drawBunHair(t.ctx, look, view)) return;
		if (view === "front") ink$1(t.ctx, "hair-f", [
			[-9.6, -41],
			[-10, -48],
			[-5, -52.5],
			[2, -52.5],
			[8, -49.5],
			[10, -42],
			[8, -45],
			[5, -45.5],
			[2, -44],
			[-1, -46],
			[-4, -44.8],
			[-7, -45.5]
		], c);
		else ink$1(t.ctx, "hair-s", [
			[-9.2, -38],
			[-9.4, -47],
			[-4, -52.5],
			[3, -52.6],
			[8.6, -48.5],
			[9.4, -44.6],
			[6, -46],
			[3, -45.5],
			[1, -43],
			[-1.4, -41],
			[-2.6, -37],
			[-6, -35.4]
		], c);
	}
	function earCtx(t, view) {
		const head = t.spec.gear.head;
		return {
			look: t.spec.look,
			view,
			head,
			headColor: colorOf(t.hooks, head, "#7a5a3a")
		};
	}
	function drawHead(t, view) {
		const { ctx } = t;
		const ears = earCtx(t, view);
		drawEarsUnder(ctx, ears);
		if (view === "side") {
			ink$1(ctx, "head-side", HEAD_SIDE, t.skin, { w: 1 });
			ink$1(ctx, "ear-s", ellPts(-2.6, -40, 1.4, 1.9, 10), t.skin, {
				shade: false,
				w: .6
			});
		} else ink$1(ctx, `head-${view}`, ellPts(0, -42, 9.2, 8.6), t.skin, { w: 1 });
		if (view !== "back") drawFace(t, view);
		drawHair(t, view);
		drawRidge(ctx, t.spec.look, view);
		drawSideEarBeforeHat(ctx, ears);
		drawBeastEarsBeforeHat(ctx, ears);
	}
	var HAND_FRONT = [-9, -23.2];
	var HAND_SIDE_NEAR = [4.6, -24];
	var HAND_SIDE_FAR = [5.6, -27];
	var isShield$1 = (it) => it?.kind.startsWith("shield") === true;
	var heldNotMirrored = (it) => isShield$1(it) || it.kind === "tome" || it.kind === "orb";
	/** 副手實際拿的東西：副手欄，或拳套（兩手都戴）。 */
	function offItemOf(spec) {
		return spec.gear.off_hand ?? (spec.gear.main_hand?.kind === "fist" ? spec.gear.main_hand : void 0);
	}
	/** 雙匕首兩把往外多張開 2px，刃身才跳出身體輪廓。 */
	function spreadOf(spec) {
		return spec.gear.main_hand?.kind === "dagger" && offItemOf(spec)?.kind === "dagger" ? 2 : 0;
	}
	/** 手持物（C 畫法：inkGear／inkOffhand／inkWeapons；`resolveDoll` 只留認得的 kind，不會走到畫不出來的）。`inkOpt` ＝ C 畫法專用的 key 與鏡像（背面主手鏡像、副手不鏡像）；`main` ＝ 主手才給的姿勢參數（6M-2：`wpn`、`pull`）。 */
	function drawHeld(t, it, x, y, o, inkOpt, main) {
		if (!o.side && drawInkShieldFront(t.ctx, it, x, y, t.hooks.colors)) return;
		const k = inkOpt ?? {
			key: o.side ? o.far ? "off-s" : "main-s" : o.mirror ? "off" : "main",
			mirror: o.mirror
		};
		const hp = t.hooks.probe;
		const pose = main ?? {};
		const p = hp === void 0 ? pose : {
			...pose,
			probe: (hand, tip, edge) => hp(main !== void 0 ? "main" : "off", hand, tip, edge)
		};
		if (drawInkOffhand(t.ctx, it, x, y, o.side, t.hooks.colors, p)) return;
		const held = {
			mirror: k.mirror,
			side: o.side,
			far: o.far,
			back: !o.front,
			...p
		};
		if (drawSectHeld(t.ctx, it, k.key, x, y, held)) return;
		if (!drawInkWeapon(t.ctx, it, k.key, x, y, held, t.hooks.colors)) drawInkWeaponMore(t.ctx, it, k.key, x, y, held, t.hooks.colors);
	}
	function drawWoodShieldBack(t, off) {
		if (off.kind === "shield_kite") {
			drawInkKiteBack(t.ctx, off);
			return;
		}
		ink$1(t.ctx, "shield-b", ellPts(8.6, -21, 6.6, 7, 20), MAT.wood, { w: 1 });
		stroke$1(t.ctx, "shield-strap", [[5, -24], [12.2, -18]], 1.2, "#5a3a1e");
	}
	function drawHeadgearItem(t, view) {
		const it = t.spec.gear.head;
		if (it === void 0) return;
		const adj = hatAdjust(t.spec.look, it);
		t.ctx.save();
		if (adj.dy !== 0) t.ctx.translate(0, adj.dy);
		if (adj.sx !== 1) t.ctx.scale(adj.sx, 1);
		if (!drawInkHeadgear(t.ctx, adj.item, view, t.hooks.colors) && !drawInkHeadgearMore(t.ctx, adj.item, view, t.hooks.colors)) drawVeil(t.ctx, adj.item, view);
		t.ctx.restore();
	}
	/** 頭部裝備 → 穿出帽子的耳朵（戴頭盔的側面尖耳、小帽的獸耳、兜帽的耳朵凸起）→ 角（永遠在最上層）。 */
	function drawHeadgear(t, view) {
		drawHeadgearItem(t, view);
		drawEarsAfterHat(t.ctx, earCtx(t, view));
		drawInkHorns(t.ctx, t.spec.look, view);
	}
	/** 修士的身上小部件（5A-ART3）：腰掛黃符、念珠、白羽披肩；畫在身體之後、手臂之前。 */
	function drawSectExtras(t, view) {
		const { gear } = t.spec;
		drawWaist(t.ctx, gear.waist, view);
		drawBeads(t.ctx, gear.neck, view);
		drawMantle(t.ctx, gear.cloak, view);
	}
	function drawFront(t) {
		const { spec } = t;
		const { gear } = spec;
		const off = offItemOf(spec);
		const spread = spreadOf(spec);
		drawCloak(t, "front");
		drawInkTail(t.ctx, spec.look, "front");
		drawHairBack(t, "front");
		drawBackItem(t.ctx, gear.back, "front", false);
		drawLegs(t, "front");
		drawBackSpines(t.ctx, spec.look, "front");
		drawBody$1(t, "front");
		drawSectExtras(t, "front");
		joint(t, swing("armR"), () => {
			drawArmFront(t, 1);
			if (off !== void 0) {
				const mirror = !heldNotMirrored(off);
				drawHeld(t, off, -HAND_FRONT[0] + spread, HAND_FRONT[1], {
					front: true,
					mirror,
					far: false,
					side: false
				});
			}
			if (off === void 0 || !isShield$1(off)) drawHand(t, 9, -23.2, "hand-r", -.32);
		});
		drawHead(t, "front");
		drawHeadgear(t, "front");
		joint(t, swing("armL"), () => {
			drawArmFront(t, -1);
			if (gear.main_hand !== void 0) drawHeld(t, gear.main_hand, HAND_FRONT[0] - spread, HAND_FRONT[1], {
				front: true,
				mirror: false,
				far: false,
				side: false
			}, void 0, mainPose(t, false));
			drawHand(t, -9, -23.2, "hand-l", .32);
		});
	}
	/**
	* 主手武器的姿勢參數（6M-2）：`wpn` ＝ 武器相對手的角度（統一座標，見 inkWeaponFrame.ts），只在側面生效（照樣張 storyDoll.js）；
	* `pull` ＝ 弓弦。沒設姿勢、或沒給 `wpn` ＝ 照預設握法（和沒設姿勢時同一個角度）。
	*/
	function mainPose(t, side) {
		const p = t.pose;
		if (p === null) return {};
		return {
			wpn: side && typeof p.wpn === "number" && Number.isFinite(p.wpn) ? p.wpn : void 0,
			pull: pz$1(p, "pull")
		};
	}
	/** 背面（朝北）：左右對調（主手在畫面右）、看不到臉；披風、尾巴蓋在身上，武器在身體後面。 */
	function drawBack(t) {
		const { ctx, spec } = t;
		const { gear } = spec;
		const off = offItemOf(spec);
		const spread = spreadOf(spec);
		ctx.scale(-1, 1);
		const screen = (fn) => {
			ctx.save();
			ctx.scale(-1, 1);
			fn();
			ctx.restore();
		};
		const main = gear.main_hand;
		if (main !== void 0) joint(t, swing("armL"), () => screen(() => drawHeld(t, main, -HAND_FRONT[0] + spread, HAND_FRONT[1], {
			front: false,
			mirror: false,
			far: false,
			side: false
		}, {
			key: "main-b",
			mirror: true
		}, mainPose(t, false))));
		if (off !== void 0 && !isShield$1(off)) joint(t, swing("armR"), () => screen(() => drawHeld(t, off, HAND_FRONT[0] - spread, HAND_FRONT[1], {
			front: false,
			mirror: !heldNotMirrored(off),
			far: false,
			side: false
		}, {
			key: "off-b",
			mirror: false
		})));
		drawLegs(t, "back");
		drawBody$1(t, "back");
		if (t.pose === null) {
			drawArmFront(t, -1);
			drawArmFront(t, 1);
			drawHand(t, -9, -23.2, "hand-bl", .32);
			drawHand(t, 9, -23.2, "hand-br", -.32);
		} else {
			joint(t, swing("armL"), () => {
				drawArmFront(t, -1);
				drawHand(t, -9, -23.2, "hand-bl", .32);
			});
			joint(t, swing("armR"), () => {
				drawArmFront(t, 1);
				drawHand(t, 9, -23.2, "hand-br", -.32);
			});
		}
		drawCloak(t, "back");
		drawBackItem(ctx, gear.back, "back", true);
		drawBackSpines(ctx, spec.look, "back");
		drawInkTail(ctx, spec.look, "back");
		if (off !== void 0 && isShield$1(off)) drawWoodShieldBack(t, off);
		drawHead(t, "back");
		drawHeadgear(t, "back");
	}
	function drawSide(t) {
		const { ctx, spec } = t;
		const { gear } = spec;
		const off = offItemOf(spec);
		drawCloak(t, "side");
		drawInkTail(ctx, spec.look, "side");
		drawHairBack(t, "side");
		drawBackItem(ctx, gear.back, "side", false);
		if (t.pose === null) drawSideFarHeld(t, off);
		else drawSideFarArm(t, off);
		drawLegs(t, "side");
		drawBackSpines(ctx, spec.look, "side");
		drawBody$1(t, "side");
		drawSectExtras(t, "side");
		if (off !== void 0 && isShield$1(off) && !drawInkShieldSide(ctx, off, t.hooks.colors)) drawInkKiteSide(ctx, off, t.hooks.colors);
		drawHead(t, "side");
		drawHeadgear(t, "side");
		const main = gear.main_hand;
		const held = () => {
			if (main !== void 0) drawHeld(t, main, HAND_SIDE_NEAR[0], HAND_SIDE_NEAR[1], {
				front: true,
				mirror: false,
				far: false,
				side: true
			}, void 0, mainPose(t, true));
			drawHand(t, HAND_SIDE_NEAR[0], HAND_SIDE_NEAR[1], "hand-s", -.54);
		};
		if (t.pose === null) {
			ink$1(ctx, "arm-s", [
				[-1.4, -31.5],
				[1.4, -31.8],
				[5, -25],
				[2.6, -23.6]
			], armColor(t));
			held();
			return;
		}
		const pose = t.pose;
		const k = 1 + pz$1(pose, "reach");
		ctx.save();
		rotAt$1(ctx, SHOULDER_S[0], SHOULDER_S[1], pz$1(pose, "arm"));
		limb$1(ctx, SHOULDER_S, ELBOW_S, k, () => ink$1(ctx, "arm-s-up", ARM_S_UPPER, armColor(t)));
		rotAt$1(ctx, ELBOW_S[0], ELBOW_S[1], pz$1(pose, "elbow"));
		limb$1(ctx, ELBOW_S, HAND_SIDE_NEAR, k, () => ink$1(ctx, "arm-s-fore", ARM_S_FORE, armColor(t)));
		held();
		ctx.restore();
	}
	var ARM_S_UPPER = [
		[-1.4, -31.5],
		[1.4, -31.8],
		[3.4, -27.8],
		[.6, -27]
	];
	var ARM_S_FORE = [
		[.4, -28.6],
		[3.2, -29.2],
		[5, -25],
		[2.6, -23.6]
	];
	var ARM_SF_UPPER = [
		[-.6, -32.2],
		[1.8, -32.8],
		[4.2, -29.8],
		[2, -28.6]
	];
	var ARM_SF_FORE = [
		[2, -30.2],
		[4.4, -30.4],
		[6.4, -27.8],
		[4.6, -26.2]
	];
	/** 沒姿勢：遠側手持物（成對武器的副手、書、法球）畫在身體後面，和加鉤子之前一樣。 */
	function drawSideFarHeld(t, off) {
		if (off !== void 0 && !heldNotMirrored(off)) {
			drawHeld(t, off, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], {
				front: true,
				mirror: false,
				far: true,
				side: true
			});
			dot$2(t.ctx, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], 1.7, 1.7, darken(t.skin, .2));
		}
		if (off !== void 0 && !isShield$1(off) && heldNotMirrored(off)) drawHeld(t, off, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], {
			front: true,
			mirror: false,
			far: true,
			side: true
		});
	}
	/** 有姿勢：側面另一隻手（遠側，畫在身體後面）＝ 上臂繞肩 `armF`、前臂繞手肘 `elbowF`；遠側手持物跟著手走，手一律畫出來（較暗）。 */
	function drawSideFarArm(t, off) {
		const { ctx, pose } = t;
		const c = darken(armColor(t), .25);
		ctx.save();
		const k = 1 + pz$1(pose, "reachF");
		rotAt$1(ctx, SHOULDER_SF[0], SHOULDER_SF[1], pz$1(pose, "armF"));
		limb$1(ctx, SHOULDER_SF, ELBOW_SF, k, () => ink$1(ctx, "arm-sf-up", ARM_SF_UPPER, c));
		rotAt$1(ctx, ELBOW_SF[0], ELBOW_SF[1], pz$1(pose, "elbowF"));
		limb$1(ctx, ELBOW_SF, HAND_SIDE_FAR, k, () => ink$1(ctx, "arm-sf-fore", ARM_SF_FORE, c));
		if (off !== void 0 && !isShield$1(off)) drawHeld(t, off, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], {
			front: true,
			mirror: false,
			far: true,
			side: true
		});
		dot$2(ctx, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], 1.7, 1.7, darken(t.skin, .2));
		ctx.restore();
	}
	/** 體型縮放：stout 整個人 ×(1.12, 0.88)、tall ×(0.96, 1.1)；不認得的值不縮放。 */
	function buildScale(look) {
		if (look.build === "stout") return [1.12, .88];
		if (look.build === "tall") return [.96, 1.1];
		return [1, 1];
	}
	/**
	* 畫一個 C 畫風小人（腳底中心在 (0,0)）。facing 的鏡像（西）由呼叫端處理；`ground` ＝ false 時不畫地面影子（倒地）。
	* `pose`（6M-1）：骨架姿勢（見 inkPose.ts）；不給或 `null` 時畫出來和加鉤子之前逐像素相同。影子不跟著起伏。
	*/
	function drawInkFigure(ctx, spec, view, hooks, ground = true, pose = null) {
		const t = {
			ctx,
			spec,
			hooks,
			skin: spec.look.skin ?? SKIN_FALLBACK,
			pose
		};
		withShadeDir(ctx, view === "front" ? 1 : -1, () => {
			ctx.save();
			const [sx, sy] = buildScale(spec.look);
			if (sx !== 1 || sy !== 1) ctx.scale(sx, sy);
			if (ground) shadow$2(ctx);
			if (pose !== null) {
				const bob = pz$1(pose, "bob");
				if (bob !== 0) ctx.translate(0, bob);
				if (view === "side") rotAt$1(ctx, HIP[0], HIP[1], pz$1(pose, "lean"));
			}
			if (view === "front") drawFront(t);
			else if (view === "back") drawBack(t);
			else drawSide(t);
			ctx.restore();
		});
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/itemColors.ts
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
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qCore.ts
	var TAU = Math.PI * 2;
	/** 剪影外框色（樣張 OUT）。 */
	var Q_OUT = "#16121a";
	/** 畫一隻時的共用狀態（樣張的模組變數）；每次 draw 開始時設好、結束時歸零。 */
	var S$1 = {
		POSE: null,
		WEST: false,
		TINT: null,
		NOPAD: false,
		FAR: 0,
		FARH: 0,
		SEAM: false,
		NOBUCKLE: false,
		SEAMIN: false,
		SHEDGE: false,
		FILLARM: false,
		FREEARM: false,
		EBOFF: false,
		BOWP: null,
		BOWM: null,
		CTX: null,
		hooks: null
	};
	/** 讀姿勢欄位；沒給或不是有限數字 → 0。 */
	function pz(k) {
		const v = S$1.POSE?.[k];
		return typeof v === "number" && Number.isFinite(v) ? v : 0;
	}
	function rotAt(ctx, x, y, a) {
		if (!a) return;
		ctx.translate(x, y);
		ctx.rotate(a);
		ctx.translate(-x, -y);
	}
	function rr(ctx, x, y, w, h, r) {
		ctx.beginPath();
		ctx.roundRect(x, y, w, h, r);
	}
	function fill$1(ctx, c, path) {
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
	/** 一件裝備的 [主色, 暗色]；沒有裝備＝預設布衣色。 */
	function colors(it) {
		return it ? S$1.hooks.colors(it) : ["#d8cdb4", "#a89c80"];
	}
	/** 武器顏色：有指定顏色或材質就照它，否則用預設材質（帶元素）。 */
	function wc(it, def) {
		return it && (it.color || it.material) ? colors(it) : S$1.hooks.colors({
			kind: it?.kind ?? "",
			material: def,
			...it?.element ? { element: it.element } : {}
		});
	}
	var ID = {
		a: 1,
		b: 0,
		c: 0,
		d: 1,
		e: 0,
		f: 0
	};
	/** 目前的變換矩陣（測試用的假畫布沒有 getTransform 時當作單位矩陣）。 */
	function getM(ctx) {
		const m = ctx.getTransform?.();
		return m && typeof m.a === "number" ? {
			a: m.a,
			b: m.b,
			c: m.c,
			d: m.d,
			e: m.e,
			f: m.f
		} : { ...ID };
	}
	var tp = (m, x, y) => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f];
	function invM(m) {
		const det = m.a * m.d - m.b * m.c || 1;
		return {
			a: m.d / det,
			b: -m.b / det,
			c: -m.c / det,
			d: m.a / det,
			e: (m.c * m.f - m.d * m.e) / det,
			f: (m.b * m.e - m.a * m.f) / det
		};
	}
	function setM(ctx, m) {
		ctx.setTransform(m.a, m.b, m.c, m.d, m.e, m.f);
	}
	var ARM_SPREAD_SET = {
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
	};
	/** 目前的手臂規則（預設 E；自測比較第 16 版寬度時暫時換成 A）。 */
	var ARMS = { cur: ARM_SPREAD_SET.E };
	var ARM = () => ARMS.cur;
	/** 不是 A（第 16 版）時，正面、背面的袖子也描內框（樣張 SEAMF）。 */
	var SEAMF = () => ARMS.cur !== ARM_SPREAD_SET.A;
	var FA = 5.5;
	var rot = (a, [x, y]) => [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)];
	var SHX = () => 8.5 + ARM().dx;
	var OUTA = () => ARM().a;
	/** 肩角 sA、肘角 eA → 手的位置。 */
	function fk(x, sA, eA, len = null) {
		const ua = len ? len[0] ?? 5 : 5;
		const fa = len ? len[1] ?? 5.5 : FA;
		const e = [x - ua * Math.sin(sA), -20 + ua * Math.cos(sA)];
		return [e[0] - fa * Math.sin(sA + eA), e[1] + fa * Math.cos(sA + eA)];
	}
	/** 反解：手掌目標 t → 關節角度；out＝手肘往哪邊（+1 往 +x、−1、"down"）。 */
	function ik(x, t, out, len = null) {
		const ua = len ? len[0] ?? 5 : 5;
		const fa = len ? len[1] ?? 5.5 : 5.5;
		const reach = ua + fa - .1;
		const dx = (t[0] ?? 0) - x;
		const dy = (t[1] ?? 0) + 20;
		const r0 = Math.hypot(dx, dy);
		const r = Math.min(Math.max(r0, Math.abs(ua - fa) + .05), reach);
		const phi = Math.atan2(-dx, dy);
		const al = Math.acos((ua * ua + r * r - fa * fa) / (2 * ua * r));
		const be = Math.acos((ua * ua + fa * fa - r * r) / (2 * ua * fa));
		let best = null;
		for (const sg of [1, -1]) {
			const sA = phi + sg * al;
			const eA = -sg * (Math.PI - be);
			const sc = out === "down" ? -20 + ua * Math.cos(sA) : (x - ua * Math.sin(sA)) * out;
			if (!best || sc > best.sc) best = {
				sA,
				eA,
				sc
			};
		}
		return {
			sA: best.sA,
			eA: best.eA,
			ok: r0 <= reach
		};
	}
	/** 指定手肘方向（dir：肩 → 手肘），前臂再指向目標 t。 */
	function elbowTo(x, dir, t, len = null) {
		const ua = len ? len[0] ?? 5 : 5;
		const fa = len ? len[1] ?? 5.5 : FA;
		const d0 = dir[0] ?? 0;
		const d1 = dir[1] ?? 0;
		const l = Math.hypot(d0, d1);
		const e = [x + ua * d0 / l, -20 + ua * d1 / l];
		const sA = Math.atan2(-d0 / l, d1 / l);
		const fx = (t[0] ?? 0) - e[0];
		const fy = (t[1] ?? 0) - e[1];
		const fl = Math.hypot(fx, fy) || 1;
		return {
			sA,
			eA: Math.atan2(-fx / fl, fy / fl) - sA,
			ok: true,
			h: [e[0] + fa * fx / fl, e[1] + fa * fy / fl]
		};
	}
	/** 記下手的位置（自測用：POSE.hands）。 */
	var rec = (who) => {
		const hs = S$1.POSE?.hands;
		return hs ? (hand, ctx) => void (hs[who] = tp(getM(ctx), hand[0], hand[1])) : null;
	};
	var mark$1 = (n) => void S$1.POSE?.layers?.push(n);
	var clamp01 = (t) => Math.max(0, Math.min(1, t));
	var isShield = (it) => !!it && String(it.kind).startsWith("shield");
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qGearForms.ts
	var dark$1 = (c, t = .3) => mix(c, "#000000", t);
	var light = (c, t = .3) => mix(c, "#ffffff", t);
	var STEEL = "#b8c0c8";
	var COPPER = "#c8803a";
	var GOLD$1 = "#e8bb48";
	var BONE = "#efe6cc";
	var CORD = "#4a3424";
	function line$2(ctx, c, w, pts) {
		ctx.strokeStyle = c;
		ctx.lineWidth = w;
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		ctx.beginPath();
		pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
		ctx.stroke();
	}
	/** 頸飾、披肩：不蓋臉（挖掉 qDoll 的頭：頭心 (0,−29)、r 8.45）。 */
	function noHead(ctx) {
		ctx.beginPath();
		ctx.rect(-60, -90, 120, 120);
		ctx.arc(0, -29, 8.45, 0, TAU);
		ctx.clip("evenodd");
	}
	/** 身體上的紋（在 body() 裡、軀幹填色之後，側面已壓扁 0.72）。有畫回傳 true（鎖甲的方點就不畫）。 */
	function bodyPattern(ctx, it, d) {
		if (it?.kind === "mail" && it.form === "scale") {
			ctx.save();
			ctx.beginPath();
			ctx.roundRect(-7.5, -21, 15, 13.5, 3);
			ctx.clip();
			ctx.strokeStyle = d;
			ctx.lineWidth = .55;
			let row = 0;
			for (let y = -19.6; y < -11.2; y += 2.3, row++) for (let x = -7.5 + (row % 2 ? 1.2 : 0); x <= 8.5; x += 2.4) {
				ctx.beginPath();
				ctx.arc(x, y, 1.15, .15 * Math.PI, .85 * Math.PI);
				ctx.stroke();
			}
			ctx.restore();
			return true;
		}
		return false;
	}
	/** torso 層：只畫在看得到的軀幹上（身體之後、手臂之前；剪在腰帶以上的軀幹裡）。 */
	function drawTorsoForms(ctx, gear, view) {
		const it = gear.body;
		const hunter = it?.kind === "leather" && it.form === "hunter";
		const ribs = it?.kind === "ribs";
		if (!hunter && !ribs) return;
		const SD = view === "side";
		const F = view === "front";
		const B = view === "back";
		ctx.save();
		ctx.beginPath();
		if (SD) ctx.roundRect(-5.4, -21, 10.8, 11.5, 2.2);
		else ctx.roundRect(-7.5, -21, 15, 11.5, 3);
		ctx.clip();
		if (hunter) {
			const [, d] = colors(it);
			if (F) for (const x of [-4.6, 1.4]) {
				fill$1(ctx, d, () => ctx.roundRect(x, -14.2, 3.2, 1.6, .5));
				fill$1(ctx, GOLD$1, () => ctx.arc(x + 1.6, -13.4, .45, 0, TAU));
			}
			else if (SD) fill$1(ctx, d, () => ctx.roundRect(2.6, -14.2, 2.8, 1.6, .5));
			if (F) line$2(ctx, d, 1, [[-5, -20], [5, -11]]);
			else if (SD) line$2(ctx, d, .85, S$1.WEST ? [[1.5, -20.8], [-3.5, -11]] : [[-1.5, -20.8], [4.6, -11]]);
		}
		if (ribs) {
			const k = "#8a826e";
			if (SD) {
				for (const y of [-18, -15]) line$2(ctx, k, .8, [[-4.6, y], [-1, y + .8]]);
				line$2(ctx, k, .9, [[-4.2, -20], [-4.2, -10]]);
			} else {
				line$2(ctx, k, 1, [[0, -20], [0, -10]]);
				if (B) for (const sx of [-1, 1]) line$2(ctx, k, .8, [
					[sx * 2, -19],
					[sx * 5, -17.6],
					[sx * 3.4, -15]
				]);
				else for (const y of [
					-18.4,
					-15.6,
					-12.8
				]) for (const sx of [-1, 1]) line$2(ctx, k, .8, [
					[sx * 1, y],
					[sx * 4.6, y + .6],
					[sx * 5.6, y + 1.8]
				]);
			}
		}
		ctx.restore();
	}
	/** free 層：不蓋手臂、拳頭、武器（身體之後、手臂之前）：獵裝下襬、全身板甲腿甲裙、圍裙。 */
	function drawFreeForms(ctx, gear, view) {
		const it = gear.body;
		const SD = view === "side";
		const F = view === "front";
		const B = view === "back";
		if (it?.kind === "leather" && it.form === "hunter") {
			const [c, d] = colors(it);
			const w = SD ? 5.9 : 8.2;
			fill$1(ctx, c, () => {
				ctx.moveTo(-w + .6, -7.6);
				ctx.lineTo(w - .6, -7.6);
				ctx.lineTo(w, -3.6);
				ctx.lineTo(-w, -3.6);
				ctx.closePath();
			});
			if (F) fill$1(ctx, dark$1(c, .35), () => {
				ctx.moveTo(-.9, -3.6);
				ctx.lineTo(0, -7.4);
				ctx.lineTo(.9, -3.6);
				ctx.closePath();
			});
			else if (B) line$2(ctx, d, .6, [[0, -7.4], [0, -3.8]]);
			else fill$1(ctx, dark$1(c, .35), () => {
				ctx.moveTo(-w + .3, -3.6);
				ctx.lineTo(-w + 1.6, -6.6);
				ctx.lineTo(-w + 2.4, -3.6);
				ctx.closePath();
			});
		}
		if (it?.kind === "plate" && it.form === "full") {
			const [c, d] = colors(it);
			const plates = SD ? [[-5.4, 4.8], [-.2, 5.6]] : [[-7.6, 7.2], [.4, 7.2]];
			for (const [x, w] of plates) {
				fill$1(ctx, c, () => ctx.roundRect(x, -7.6, w, 4.6, [
					0,
					0,
					1.6,
					1.6
				]));
				line$2(ctx, d, .55, [[x + .6, -5.4], [x + w - .6, -5.4]]);
			}
			if (!SD) line$2(ctx, d, .7, [[0, -7.4], [0, -3.2]]);
		}
	}
	/** 新頸飾形制（吊牌、符牌、骨符）由 drawTopForms 畫；qGear.neckItem 遇到時跳過。 */
	function isNeckForm(it) {
		return it?.kind === "pendant" && it.form === "tag" || it?.kind === "charm" && (it.form === "tablet" || it.form === "bone");
	}
	/** top 層：全身板甲護頸、披風外套的短披肩、吊牌／符牌／骨符（圍裙 QK-8 起由 qNpc 畫）。正面、側面在整隻最後畫；背面在披風之前畫。 */
	function drawTopForms(ctx, gear, view) {
		const body = gear.body;
		const fullPlate = body?.kind === "plate" && body.form === "full";
		const cape = body?.kind === "coat" && body.form === "cape";
		const neck = isNeckForm(gear.neck) ? gear.neck : void 0;
		if (!fullPlate && !cape && !neck) return;
		if (S$1.TINT) return;
		const SD = view === "side";
		const B = view === "back";
		const F = view === "front";
		ctx.save();
		noHead(ctx);
		if (fullPlate) {
			const [c, d] = colors(body);
			fill$1(ctx, c, () => SD ? ctx.roundRect(-4.6, -22.4, 9.4, 2.6, 1.2) : ctx.roundRect(-5.6, -22.4, 11.2, 2.6, 1.2));
			line$2(ctx, d, .5, SD ? [[-4, -20.9], [4.2, -20.9]] : [[-5, -20.9], [5, -20.9]]);
		}
		if (cape) {
			const [c, d] = colors(body);
			const k = dark$1(c, .18);
			if (SD) fill$1(ctx, k, () => {
				ctx.moveTo(-6.2, -21.4);
				ctx.quadraticCurveTo(0, -22, 5.6, -21.4);
				ctx.quadraticCurveTo(7, -18, 5.4, -15.6);
				ctx.quadraticCurveTo(0, -14.4, -6.6, -14.6);
				ctx.quadraticCurveTo(-7.6, -18, -6.2, -21.4);
				ctx.closePath();
			});
			else fill$1(ctx, k, () => {
				ctx.moveTo(-9.6, -21);
				ctx.quadraticCurveTo(0, -22.4, 9.6, -21);
				ctx.quadraticCurveTo(11.6, -17, 10.6, B ? -13.6 : -15.2);
				ctx.quadraticCurveTo(0, B ? -11.6 : -13.2, -10.6, B ? -13.6 : -15.2);
				ctx.quadraticCurveTo(-11.6, -17, -9.6, -21);
				ctx.closePath();
			});
			line$2(ctx, d, .6, SD ? [[-6, -15.6], [5, -16.4]] : [
				[-9.8, -16],
				[0, B ? -12.8 : -14.2],
				[9.8, -16]
			]);
			if (F) fill$1(ctx, GOLD$1, () => ctx.arc(0, -19.4, .9, 0, TAU));
			else if (SD) fill$1(ctx, GOLD$1, () => ctx.arc(5, -19.6, .8, 0, TAU));
		}
		if (neck) neckForm(ctx, neck, view);
		ctx.restore();
	}
	/** 吊牌（pendant・tag）、符牌（charm・tablet）、骨符（charm・bone）：側面掛在胸前前緣、露在手臂前方；背面鏈子被後腦擋住。 */
	function neckForm(ctx, it, view) {
		const tag = it.kind === "pendant";
		const cord = tag ? "#8d969f" : CORD;
		if (view === "back") {
			line$2(ctx, cord, tag ? .6 : .7, [
				[-3.5, -20.8],
				[0, -20.2],
				[3.5, -20.8]
			]);
			return;
		}
		const fang = (x, y) => fill$1(ctx, BONE, () => {
			ctx.moveTo(x - 1.2, y);
			ctx.quadraticCurveTo(x - .8, y + 3, x + .9, y + 4.4);
			ctx.quadraticCurveTo(x + .3, y + 2.4, x + 1.2, y);
			ctx.closePath();
		});
		if (view === "side") {
			line$2(ctx, cord, tag ? .55 : .6, [
				[3.4, -21],
				[5.8, -19.6],
				[6.6, tag ? -18.4 : -18.6]
			]);
			if (tag) {
				fill$1(ctx, STEEL, () => ctx.roundRect(5.6, -18.6, 2.2, 3.4, .6));
				fill$1(ctx, "#6a7078", () => ctx.arc(6.7, -17.8, .35, 0, TAU));
			} else if (it.form === "tablet") {
				fill$1(ctx, GOLD$1, () => ctx.roundRect(5.4, -18.8, 2.6, 4, .5));
				line$2(ctx, "#c0392b", .5, [[6.7, -18], [6.7, -15.6]]);
			} else {
				fill$1(ctx, "#8a5a32", () => ctx.arc(6.6, -18.6, .75, 0, TAU));
				fang(6.8, -18.2);
			}
			return;
		}
		if (tag) {
			line$2(ctx, cord, .55, [
				[-4.2, -20.8],
				[0, -16.4],
				[4.2, -20.8]
			]);
			fill$1(ctx, STEEL, () => ctx.roundRect(-1.3, -16.6, 2.6, 3.6, .7));
			fill$1(ctx, "#6a7078", () => ctx.arc(0, -15.8, .4, 0, TAU));
		} else if (it.form === "tablet") {
			line$2(ctx, cord, .6, [
				[-4.2, -20.8],
				[0, -16.6],
				[4.2, -20.8]
			]);
			fill$1(ctx, GOLD$1, () => ctx.roundRect(-2, -16.8, 4, 4.4, .6));
			line$2(ctx, "#c0392b", .5, [
				[0, -16],
				[-.9, -14.6],
				[.9, -14.2],
				[0, -13.1]
			]);
		} else {
			line$2(ctx, cord, .6, [
				[-4.2, -20.8],
				[0, -16.8],
				[4.2, -20.8]
			]);
			fang(0, -17);
			for (const x of [-2, 2]) fill$1(ctx, "#8a5a32", () => ctx.arc(x, -17.9, .75, 0, TAU));
		}
	}
	/** 斗篷帽（hood・cowl）：兜帽下面接一片披領；正面尖角垂到胸口、和兜帽的接縫順著下巴；背面尖角到肩胛；側面前後各一角。
	*  正面、側面畫在頭下面（臉蓋在披領上），背面畫在兜帽之後（drawQ 的頭那一段呼叫）。 */
	function isCowl(it) {
		return it?.kind === "hood" && it.form === "cowl";
	}
	function cowl(ctx, it, view) {
		const [c, d] = colors(it);
		ctx.save();
		ctx.lineJoin = "round";
		ctx.strokeStyle = d;
		ctx.lineWidth = .6;
		if (view === "side") {
			fill$1(ctx, c, () => {
				ctx.moveTo(-8.4, -24);
				ctx.lineTo(7.4, -24);
				ctx.lineTo(6.6, -16);
				ctx.lineTo(1.6, -18.6);
				ctx.lineTo(-3, -15.4);
				ctx.lineTo(-8.8, -17.6);
				ctx.closePath();
			});
			ctx.beginPath();
			ctx.moveTo(-8.6, -17.6);
			ctx.lineTo(-3, -15.4);
			ctx.lineTo(1.6, -18.6);
			ctx.lineTo(6.6, -16);
			ctx.stroke();
		} else if (view === "back") {
			fill$1(ctx, c, () => {
				ctx.moveTo(-9.6, -23.2);
				ctx.lineTo(9.6, -23.2);
				ctx.lineTo(10.4, -17.6);
				ctx.lineTo(0, -12.6);
				ctx.lineTo(-10.4, -17.6);
				ctx.closePath();
			});
			ctx.beginPath();
			ctx.moveTo(-10.4, -17.6);
			ctx.lineTo(0, -12.6);
			ctx.lineTo(10.4, -17.6);
			ctx.stroke();
		} else {
			fill$1(ctx, c, () => {
				ctx.moveTo(-9.6, -24);
				ctx.lineTo(9.6, -24);
				ctx.lineTo(10.4, -17.6);
				ctx.lineTo(0, -13.8);
				ctx.lineTo(-10.4, -17.6);
				ctx.closePath();
			});
			ctx.beginPath();
			ctx.moveTo(-10.4, -17.6);
			ctx.lineTo(0, -13.8);
			ctx.lineTo(10.4, -17.6);
			ctx.stroke();
			ctx.beginPath();
			ctx.moveTo(-9.4, -22.6);
			ctx.quadraticCurveTo(0, -18.4, 9.4, -22.6);
			ctx.stroke();
		}
		ctx.restore();
	}
	var isFurCap = (it) => it?.kind === "cap" && it.form === "fur";
	/** 頭飾畫之前的剪裁（毛帽側面：皮帽伸出臉前的帽舌不畫）。有剪裁回傳 true，呼叫端畫完頭飾要 restore。 */
	function headgearClip(ctx, it, view) {
		if (!(isFurCap(it) && view === "side")) return false;
		ctx.save();
		ctx.beginPath();
		ctx.rect(-80, -120, 160, 200);
		ctx.rect(8.7, -34.5, 6, 4.4);
		ctx.clip("evenodd");
		return true;
	}
	/** 頭飾之後：毛帽的米白毛邊（圓角、不凸出頭、下緣一排圓凸）與兩側護耳；側面護耳沿後腦垂下一片。 */
	function drawHeadFormTop(ctx, it, view) {
		if (!isFurCap(it) || S$1.TINT) return;
		const FUR = "#ece4cc";
		const FURD = "#c8bc9c";
		const SD = view === "side";
		ctx.save();
		ctx.beginPath();
		ctx.arc(0, -29, 8.5, 0, TAU);
		ctx.arc(SD ? -.4 : 0, -31, 9.1, Math.PI, 0);
		ctx.clip();
		const x0 = SD ? -9.6 : -9.2;
		const x1 = SD ? 8.8 : 9.2;
		const n = 5;
		const st = (x1 - x0) / n;
		fill$1(ctx, FUR, () => {
			ctx.moveTo(x0, -32);
			ctx.quadraticCurveTo(x0, -34.4, x0 + 2, -34.4);
			ctx.lineTo(x1 - 2, -34.4);
			ctx.quadraticCurveTo(x1, -34.4, x1, -32);
			for (let i = 0; i < n; i++) {
				const x = x1 - i * st;
				ctx.quadraticCurveTo(x - st / 2, -29.6, x - st, -31.4);
			}
			ctx.closePath();
		});
		if (SD) {
			fill$1(ctx, FUR, () => {
				ctx.moveTo(-5.2, -31.4);
				ctx.quadraticCurveTo(-6.4, -26.4, -4.2, -23.4);
				ctx.quadraticCurveTo(-1.4, -22.4, .4, -24.8);
				ctx.quadraticCurveTo(1.4, -28, 1, -31.4);
				ctx.closePath();
			});
			line$2(ctx, FURD, .5, [[-2.6, -29.6], [-2.2, -24.6]]);
			ctx.restore();
			return;
		}
		ctx.restore();
		for (const sx of [-1, 1]) {
			fill$1(ctx, FUR, () => ctx.roundRect(sx * 7.6 - 1.9, -31.6, 3.8, 7.6, 1.9));
			line$2(ctx, FURD, .45, [[sx * 7.6, -29.8], [sx * 7.6, -25.6]]);
		}
	}
	/** 拳頭下面：鎖鏈護手的喇叭袖口。 */
	function handFormUnder(ctx, h, x, hy) {
		if (h?.kind === "gauntlets" && h.form === "mail") {
			const [c, d] = colors(h);
			fill$1(ctx, c, () => {
				ctx.moveTo(x - 2.1, hy - 1.2);
				ctx.lineTo(x + 2.1, hy - 1.2);
				ctx.lineTo(x + 3, hy - 5.6);
				ctx.lineTo(x - 3, hy - 5.6);
				ctx.closePath();
			});
			fill$1(ctx, d, () => ctx.rect(x - 3, hy - 5.8, 6, .8));
			ctx.fillStyle = d;
			for (const [dx, dy] of [
				[-1.4, -4.2],
				[.4, -4.2],
				[-.5, -2.8],
				[1.3, -2.8]
			]) ctx.fillRect(x + dx - .3, hy + dy - .3, .6, .6);
		}
	}
	/**
	* 拳頭上面：鎖鏈護手的鎖子點、露指手套的膚色指頭與手套口、長皮手套的護套、臂環。
	* far：遠側暗一階的換色；edge：正面背面空手時拳頭整圈邊（露出的指頭保留下半圈）。
	*/
	function handFormOver(ctx, h, skin, x, hy, far, edge, lift = 0) {
		if (h?.kind === "gauntlets" && h.form === "mail") {
			const [, d] = colors(h);
			ctx.fillStyle = far(d);
			for (const [dx, dy] of [
				[-1.2, -1],
				[.6, -1],
				[-.3, .4],
				[1.4, .4],
				[-1.3, 1.6],
				[.5, 1.6]
			]) ctx.fillRect(x + dx - .3, hy + dy - .3, .6, .6);
		}
		if (h?.kind === "gloves" && h.form === "fingerless") {
			const sk = far(skin);
			const [, d] = colors(h);
			ctx.save();
			ctx.beginPath();
			ctx.arc(x, hy, 2.4, 0, TAU);
			ctx.clip();
			ctx.beginPath();
			ctx.rect(x - 3, hy + .6, 6, 3);
			ctx.clip();
			fill$1(ctx, sk, () => ctx.rect(x - 3, hy + .6, 6, 3));
			if (edge) edge(sk);
			ctx.restore();
			fill$1(ctx, far(d), () => ctx.rect(x - 2.3, hy + .35, 4.6, .5));
			fill$1(ctx, far(d), () => rr(ctx, x - 2.3, hy - 2.9, 4.6, 1.3, .5));
		}
		if (h?.kind === "gloves" && h.form === "long") {
			const [c, d] = colors(h);
			fill$1(ctx, c, () => ctx.roundRect(x - 2.2, hy - 6.2 - lift, 4.4, 5.4 + lift, 1));
			fill$1(ctx, light(c, .22), () => ctx.roundRect(x - 2.6, hy - 6.8 - lift, 5.2, 1.6, .7));
			line$2(ctx, d, .4, [[x - 2, hy - 1.2], [x + 2, hy - 1.2]]);
		}
		if (h?.kind === "bracers" && h.form === "ring") for (const y of [-5.2 - lift, -3.2 - lift]) {
			fill$1(ctx, COPPER, () => ctx.roundRect(x - 2.5, hy + y, 5, 1.1, .5));
			fill$1(ctx, light(COPPER, .5), () => ctx.rect(x - 1.6, hy + y + .2, 1.2, .35));
		}
	}
	/** 臂環不畫成皮護腕（qDoll 的 bracers 一律畫寬皮帶；ring 形制改由 handFormOver 畫兩條細環）。 */
	var isRingBracer = (h) => h?.kind === "bracers" && h.form === "ring";
	/**
	* 一條腿的鞋子形制（腳畫好之後）：綁腿鞋布條、尖頭鐵靴的鞋尖、護膝脛甲的護膝。
	* sx：−1／1（側面 1＝近側）；x：這條腿的中心；part：lower＝小腿段（膝轉之後）、upper＝護膝（同一個座標系，膝蓋那一端）。
	*/
	function drawLegForm(ctx, feet, sx, x, view) {
		if (!feet) return;
		const SD = view === "side";
		if (feet.kind === "shoes" && feet.form === "wrapped") {
			const a = SD ? -4 : x - 2.4;
			const b = SD ? 4 : x + 2.4;
			ctx.save();
			ctx.beginPath();
			ctx.roundRect(x - 2.1, -5.6, 4.2, 4.6, 1.2);
			ctx.clip();
			for (const y of [
				-5,
				-3.3,
				-1.6
			]) fill$1(ctx, "#e2d8bc", () => {
				ctx.moveTo(a, y + .6);
				ctx.lineTo(b, y - .6);
				ctx.lineTo(b, y + .4);
				ctx.lineTo(a, y + 1.6);
				ctx.closePath();
			});
			ctx.restore();
		} else if (feet.kind === "iron_boots" && feet.form === "sabaton") {
			const [c, d] = colors(feet);
			if (SD) {
				if (sx < 0) return;
				fill$1(ctx, c, () => {
					ctx.moveTo(2, -3);
					ctx.lineTo(5.4, -2.4);
					ctx.lineTo(8.6, -.6);
					ctx.lineTo(5.6, .6);
					ctx.lineTo(1.8, .6);
					ctx.closePath();
				});
				line$2(ctx, d, .5, [[3.4, -2.6], [4, .4]]);
				return;
			}
			if (view === "front") fill$1(ctx, c, () => {
				ctx.moveTo(x - 3.4, -1.6);
				ctx.lineTo(x + 3.4, -1.6);
				ctx.lineTo(x + 2.2, -.3);
				ctx.lineTo(x, .8);
				ctx.lineTo(x - 2.2, -.3);
				ctx.closePath();
			});
			line$2(ctx, d, .5, [[x - 3, -1.8], [x + 3, -1.8]]);
		} else if (feet.kind === "greaves" && feet.form === "knee") {
			if (view === "back" || SD && sx < 0) return;
			const [c, d] = colors(feet);
			const kx = SD ? 2.2 : x;
			fill$1(ctx, light(c, .2), () => ctx.ellipse(kx, -5.4, SD ? 2.4 : 2.6, 2, 0, 0, TAU));
			line$2(ctx, d, .45, SD ? [[kx + .4, -6.8], [kx + 1.4, -4.2]] : [[kx, -7], [kx, -3.8]]);
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qNpcHeld.ts
	/** 修士手持物的 kind（qDoll 照持武器規則畫在手上）。 */
	var HELD_KINDS = [
		"whisk",
		"talisman",
		"puppet_strings"
	];
	/** 副手拿這些時畫成對應物件（不是書；樣張 HELD_OFF）。 */
	var HELD_OFF = [
		"orb",
		"whisk",
		"talisman",
		"puppet_strings"
	];
	var isHeldOff = (it) => !!it && HELD_OFF.includes(it.kind);
	/** 四指：橫過握柄的一條（和手同色）＋一條指縫。 */
	function heldFingers(c, it) {
		const k = it?.skin ?? "#f1c9a5";
		fill$1(c, k, () => c.roundRect(-2.3, -1.1, 4.6, 2.2, 1));
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
				fill$1(c, "#8a5a2a", () => c.roundRect(-.65, -6.6, 1.3, 9.4, .6));
				fill$1(c, "#e8bb48", () => c.roundRect(-.9, -7.2, 1.8, 1.2, .5));
				fill$1(c, it?.color ?? "#f2f0ea", () => {
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
				fill$1(c, it?.color ?? "#f2d860", () => c.roundRect(-1.5, -9.4, 3, 8.4, .3));
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
				fill$1(c, "#8a6a48", () => c.roundRect(-4.4, -.6, 8.8, 1.3, .5));
				fill$1(c, "#8a6a48", () => c.roundRect(-.65, -3.6, 1.3, 7.6, .5));
				heldFingers(c, it);
			}
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qWeapons.ts
	function sword(ctx, it, L, W) {
		const [c] = wc(it, "steel");
		fill$1(ctx, c, () => {
			ctx.moveTo(-W / 2, -3);
			ctx.lineTo(-W / 2, -L);
			ctx.lineTo(0, -L - 3);
			ctx.lineTo(W / 2, -L);
			ctx.lineTo(W / 2, -3);
			ctx.closePath();
		});
		if (it?.form === "arcane") {
			const glow = arcaneGlowColor(it, S$1.hooks.tint);
			ctx.save();
			ctx.shadowColor = glow;
			ctx.shadowBlur = 4 + 8 * pz("glow");
			ctx.fillStyle = glow;
			ctx.fillRect(-.55, -L + 1, 1.1, L - 5);
			ctx.restore();
			ctx.fillStyle = "#e8e2ff";
			for (const ry of [
				-6.5,
				-10,
				-13.5
			]) ctx.fillRect(-1.1, ry, 2.2, .8);
			fill$1(ctx, "#b08a4a", () => {
				for (let i = 0; i < 12; i++) {
					const a = i / 12 * TAU;
					const r = i % 2 ? 3.2 : 4.3;
					ctx.lineTo(Math.cos(a) * r, -3 + Math.sin(a) * r * .55);
				}
				ctx.closePath();
			});
			fill$1(ctx, glow, () => ctx.arc(0, -3, 1.2, 0, TAU));
			fill$1(ctx, "#4a3020", () => ctx.rect(-1, -1.5, 2, 3.5));
			return;
		}
		fill$1(ctx, "rgba(255,255,255,0.45)", () => ctx.rect(-W / 2 + .6, -L, .9, L - 4));
		fill$1(ctx, it?.hilt ?? (W >= 4 ? "#d8b04a" : "#8a6a2a"), () => ctx.roundRect(-4.5, -4, 9, 2, 1));
		fill$1(ctx, "#4a3020", () => ctx.rect(-1, -2, 2, W >= 4 ? 8 : 4));
	}
	function dagger(ctx, it) {
		const [c] = wc(it, "iron");
		fill$1(ctx, c, () => {
			ctx.moveTo(-1.3, -2);
			ctx.lineTo(0, -10);
			ctx.lineTo(1.3, -2);
			ctx.closePath();
		});
		fill$1(ctx, "#4a3020", () => ctx.rect(-2.5, -2.5, 5, 1.5));
		fill$1(ctx, "#4a3020", () => ctx.rect(-.8, -1, 1.6, 3));
	}
	/** 魔導劍源晶槽的光色：預設藍紫光；有元素時換元素色。 */
	var arcaneGlowColor = (it, tint) => (it?.element ? tint(it.element) : void 0) ?? "#9a86ff";
	/** 杖頭光點的顏色。 */
	var staffOrbColor = (it) => (it?.element ? STAFF_ORB[it.element] : void 0) ?? it?.glow ?? "#c8bcff";
	/** 法球的顏色。 */
	var orbColor = (it) => it?.color ?? "#a898ff";
	var BOW_R = 8.5;
	var BOW_A = 1.2;
	var BOW_EY = BOW_R - Math.cos(BOW_A) * BOW_R;
	var STAFF_ORB = {
		fire: "#ff6a1a",
		water: "#4aa8ff",
		ice: "#8fe3ff",
		lightning: "#fff36b",
		poison: "#7ddc3a",
		wind: "#7fe0c0",
		earth: "#b0814a",
		holy: "#ffd75e",
		shadow: "#9a6ad8"
	};
	function whipDraw(c, it) {
		c.strokeStyle = it?.color ?? "#5e3b1f";
		c.lineWidth = 1.4;
		c.lineCap = "round";
		if (S$1.POSE && typeof S$1.POSE.wpn === "number") {
			fill$1(c, "#4a3020", () => c.roundRect(-1.1, -5, 2.2, 6.5, .8));
			c.beginPath();
			c.moveTo(0, -5);
			c.quadraticCurveTo(1.2, -15, 0, -24);
			c.stroke();
			c.lineWidth = .8;
			c.beginPath();
			c.moveTo(0, -24);
			c.quadraticCurveTo(-1.5, -27, .6, -29);
			c.stroke();
			return;
		}
		const m = getM(c);
		const det = m.a * m.d - m.b * m.c || 1;
		const loc = (x, y) => {
			const v = [(m.d * x - m.c * y) / det, (-m.b * x + m.a * y) / det];
			const l = Math.hypot(v[0], v[1]) || 1;
			return [v[0] / l, v[1] / l];
		};
		const D = loc(0, 1);
		const N = loc(S$1.WEST ? -1 : 1, 0);
		const E = [D[0] * 4.2, D[1] * 4.2];
		const w = Math.sin(pz("lash") * TAU) * 1.6;
		const at = (u, v) => [E[0] + u * D[0] + v * N[0], E[1] + u * D[1] + v * N[1]];
		c.save();
		c.lineWidth = 2.2;
		c.strokeStyle = "#4a3020";
		c.beginPath();
		c.moveTo(-D[0] * 1.6, -D[1] * 1.6);
		c.lineTo(E[0], E[1]);
		c.stroke();
		c.restore();
		const p1 = at(2, .3);
		const p2 = at(4, .8 + w * .3);
		const p3 = at(5.4, 2.2 + w * .6);
		const p4 = at(5.2, 6.5 + w);
		c.beginPath();
		c.moveTo(E[0], E[1]);
		c.bezierCurveTo(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]);
		c.stroke();
		c.lineWidth = .8;
		c.beginPath();
		c.moveTo(p3[0], p3[1]);
		const q = at(5.8, 4.4 + w);
		c.quadraticCurveTo(q[0], q[1], p4[0], p4[1]);
		c.stroke();
	}
	function bowDraw(c, it) {
		const [k] = wc(it, "wood");
		const BP = S$1.BOWP;
		const pull = BP && BP.pull != null ? BP.pull : typeof S$1.POSE?.pull === "number" ? S$1.POSE.pull : 0;
		const ex = Math.sin(BOW_A) * BOW_R;
		const ey = BOW_EY;
		const st = () => {
			if (S$1.BOWM) {
				c.save();
				setM(c, S$1.BOWM);
				c.stroke();
				c.restore();
			} else c.stroke();
		};
		c.strokeStyle = "#e8e8e8";
		c.lineWidth = .8;
		c.beginPath();
		c.moveTo(-ex, ey);
		c.lineTo(0, ey + pull);
		c.lineTo(ex, ey);
		st();
		c.strokeStyle = k;
		c.lineWidth = 2.2;
		c.lineCap = "round";
		c.beginPath();
		c.arc(0, BOW_R, BOW_R, -Math.PI / 2 - BOW_A, -Math.PI / 2 + BOW_A);
		st();
		fill$1(c, "#4a3020", () => c.roundRect(-1.6, -1.6, 3.2, 3.2, .8));
		if (!(BP && BP.noArrow) && (pull > .5 || pz("nock") > 0 || BP && BP.nock)) {
			c.strokeStyle = "#c8a070";
			c.lineWidth = .9;
			c.beginPath();
			c.moveTo(0, ey + pull);
			c.lineTo(0, -6);
			st();
			if (S$1.BOWM) {
				const m = getM(c);
				const inv = invM(S$1.BOWM);
				const P = (x, y) => {
					const q = tp(m, x, y);
					return tp(inv, q[0], q[1]);
				};
				const a0 = P(0, ey);
				const a1 = P(0, -8);
				const l = Math.hypot(a1[0] - a0[0], a1[1] - a0[1]) || 1;
				const ux = (a1[0] - a0[0]) / l;
				const uy = (a1[1] - a0[1]) / l;
				c.save();
				setM(c, S$1.BOWM);
				fill$1(c, "#c3ccd6", () => {
					c.moveTo(a1[0] - ux * 2.4 - uy * 1.2, a1[1] - uy * 2.4 + ux * 1.2);
					c.lineTo(a1[0], a1[1]);
					c.lineTo(a1[0] - ux * 2.4 + uy * 1.2, a1[1] - uy * 2.4 - ux * 1.2);
					c.closePath();
				});
				c.restore();
			} else fill$1(c, "#c3ccd6", () => {
				c.moveTo(-1.2, -5.6);
				c.lineTo(0, -8);
				c.lineTo(1.2, -5.6);
				c.closePath();
			});
		}
	}
	/** 武器表（QW）：len＝握把到作用端；hold＝預設握法（側面相對手臂、正面絕對角度）。 */
	var QW = {
		...QW_HELD,
		sword: {
			len: 19,
			hold: {
				side: .75,
				front: -.12
			},
			draw: (c, it) => sword(c, it, 16, 2.6)
		},
		greatsword: {
			len: 27,
			hold: {
				side: .75,
				front: -.25
			},
			draw: (c, it) => sword(c, it, 24, 4)
		},
		greatsword_k: {
			len: 17,
			hold: {
				side: .75,
				front: -.25
			},
			draw: (c, it) => sword(c, it, 14, 4)
		},
		greatsword_kf: {
			len: 14.7,
			hold: {
				side: .75,
				front: -.25
			},
			draw: (c, it) => sword(c, it, 11.7, 4)
		},
		arcane_blade: {
			len: 19,
			hold: {
				side: .75,
				front: -.12
			},
			draw: (c, it) => sword(c, {
				...it ?? { kind: "sword" },
				form: "arcane"
			}, 16, 2.6)
		},
		saber: {
			len: 19,
			hold: {
				side: .75,
				front: -.12
			},
			draw: (c, it) => {
				const [k] = wc(it, "steel");
				fill$1(c, k, () => {
					c.moveTo(-1.3, -3);
					c.quadraticCurveTo(-2.2, -12, .6, -19);
					c.lineTo(1.9, -18.4);
					c.quadraticCurveTo(.6, -11, 1.3, -3);
					c.closePath();
				});
				fill$1(c, "rgba(255,255,255,0.45)", () => {
					c.moveTo(-.6, -4);
					c.quadraticCurveTo(-1.3, -11, .4, -16.5);
					c.lineTo(.8, -16.3);
					c.quadraticCurveTo(-.3, -11, .2, -4);
					c.closePath();
				});
				fill$1(c, "#8a6a2a", () => c.ellipse(0, -3, 3.4, 1.4, 0, 0, TAU));
				fill$1(c, "#3a2a1a", () => c.rect(-1, -2, 2, 4.2));
			}
		},
		dagger: {
			len: 10,
			hold: {
				side: .75,
				front: -.6
			},
			draw: dagger
		},
		paired: {
			len: 10,
			hold: {
				side: .75,
				front: -.45
			},
			draw: dagger
		},
		axe: {
			len: 18,
			hold: {
				side: .75,
				front: -.3
			},
			draw: (c, it) => {
				const [k] = wc(it, "iron");
				fill$1(c, "#6a4420", () => c.rect(-1, -18, 2, 20));
				fill$1(c, k, () => {
					c.moveTo(1, -17);
					c.quadraticCurveTo(9, -18, 8, -10);
					c.lineTo(1, -12);
					c.closePath();
				});
			}
		},
		hammer: {
			len: 22,
			hold: {
				side: .75,
				front: -.25
			},
			draw: (c, it) => {
				const [k, d] = wc(it, "iron");
				fill$1(c, "#6a4420", () => c.rect(-1, -18, 2, 21));
				if (it?.form === "mace") fill$1(c, k, () => c.arc(0, -19, 4, 0, TAU));
				else fill$1(c, k, () => c.roundRect(-5.5, -22, 11, 6, 1.2));
				fill$1(c, d, () => c.rect(-5.5, -19.5, 11, 1));
			}
		},
		spear: {
			len: 42,
			hold: {
				side: .15,
				front: 0
			},
			draw: (c, it) => {
				const [k] = wc(it, "steel");
				fill$1(c, "#6a4420", () => c.rect(-.9, -34, 1.8, 45));
				fill$1(c, k, () => {
					c.moveTo(0, -42);
					c.lineTo(2.4, -34);
					c.lineTo(-2.4, -34);
					c.closePath();
				});
				fill$1(c, "#8a6a2a", () => c.rect(-1.6, -34.5, 3.2, 1.4));
			}
		},
		scythe: {
			len: 26,
			hold: {
				side: .6,
				front: -.15
			},
			draw: (c, it) => {
				const [k] = wc(it, "steel");
				fill$1(c, "#6a4420", () => c.rect(-1, -26, 2, 35));
				fill$1(c, k, () => {
					c.moveTo(0, -26);
					c.quadraticCurveTo(12, -28, 14, -18);
					c.quadraticCurveTo(8, -23, 0, -23);
					c.closePath();
				});
			}
		},
		whip: {
			len: 18,
			hold: {
				side: .75,
				front: -.25
			},
			draw: whipDraw
		},
		gauntlet: {
			len: 4,
			hold: {
				side: 1,
				front: 0
			},
			draw: (c, it) => {
				const [k] = wc(it, "steel");
				fill$1(c, k, () => c.arc(0, 0, 2.9, 0, TAU));
				if (it?.form === "katar" || it?.form === "claw") fill$1(c, k, () => {
					c.moveTo(-1.2, -2.6);
					c.lineTo(0, -9);
					c.lineTo(1.2, -2.6);
					c.closePath();
				});
			}
		},
		staff: {
			len: 32,
			hold: {
				side: 0,
				front: 0
			},
			draw: (c, it) => {
				const orb = staffOrbColor(it);
				fill$1(c, "#6a4420", () => c.rect(-1.1, -30, 2.2, 39));
				const g = pz("glow");
				if (!(pz("glowLayer") > 0)) {
					c.save();
					c.globalAlpha = .35 + .35 * g;
					fill$1(c, orb, () => c.arc(0, -32, 6.5 + 2 * g, 0, TAU));
					c.restore();
				}
				fill$1(c, orb, () => c.arc(0, -32, 3.6, 0, TAU));
				fill$1(c, "rgba(255,255,255,0.8)", () => c.arc(-1.2, -33.2, 1.1, 0, TAU));
			}
		},
		orb: {
			len: 6,
			hold: {
				side: .6,
				front: 0
			},
			draw: (c, it) => {
				const orb = orbColor(it);
				const g = pz("glow");
				const oy = -3.4 + pz("orbY");
				c.save();
				c.globalAlpha = .35 + .35 * g;
				fill$1(c, orb, () => c.arc(0, oy, 6 + 2 * g, 0, TAU));
				c.restore();
				fill$1(c, orb, () => c.arc(0, oy, 3.6, 0, TAU));
				fill$1(c, "rgba(255,255,255,0.8)", () => c.arc(-1.2, oy - 1.2, 1.1, 0, TAU));
			}
		},
		bow: {
			len: 4,
			hold: {
				side: Math.PI / 2,
				front: -Math.PI / 2
			},
			draw: bowDraw
		},
		crossbow: {
			len: 14,
			hold: {
				side: 2.2,
				front: Math.PI
			},
			draw: (c, it) => {
				const [k] = wc(it, "iron");
				fill$1(c, "#7a5232", () => c.roundRect(-1.3, -12, 2.6, 16, 1));
				c.strokeStyle = "rgba(240,240,240,0.85)";
				c.lineWidth = .7;
				c.beginPath();
				c.moveTo(-8, -8);
				c.lineTo(0, -5.5);
				c.lineTo(8, -8);
				c.stroke();
				c.strokeStyle = k;
				c.lineWidth = 2;
				c.lineCap = "round";
				c.beginPath();
				c.moveTo(-8, -8);
				c.quadraticCurveTo(0, -13.5, 8, -8);
				c.stroke();
				c.strokeStyle = "#c8a070";
				c.lineWidth = .9;
				c.beginPath();
				c.moveTo(0, -5.5);
				c.lineTo(0, -14);
				c.stroke();
			}
		},
		gun: {
			len: 17,
			hold: {
				side: 2.3,
				front: Math.PI
			},
			draw: (c, it) => {
				const form = it?.form ?? "rifle";
				const L = {
					pistol: 7,
					rifle: 17,
					shotgun: 15,
					energy: 12
				}[form] ?? 17;
				const [k, d] = wc(it, "iron");
				if (form === "rifle" || form === "shotgun") fill$1(c, "#7a5232", () => c.roundRect(-1.8, 0, 3.6, 6.5, 1));
				fill$1(c, "#3a2a1c", () => c.roundRect(-1.2, -1, 2.4, 4, .8));
				fill$1(c, form === "energy" ? "#e8edf2" : k, () => c.roundRect(-1.3, -L, form === "shotgun" ? 3.2 : 2.6, L + 1, 1));
				fill$1(c, d, () => c.rect(-1.5, -L * .55, 3, 1.1));
			}
		}
	};
	var ALIAS = {
		fist: "gauntlet",
		longgun: "gun",
		shotgun: "gun",
		pistol: "gun",
		dual_dagger: "paired",
		puppet_cross: "puppet_strings"
	};
	var GUN_FORM = {
		longgun: "rifle",
		shotgun: "shotgun",
		pistol: "pistol"
	};
	/** 手持物 → 武器表的項目（不在表內＝null，退回 pdHeld）。 */
	function qWeapon(it) {
		if (!it) return null;
		let kind = ALIAS[it.kind] ?? it.kind;
		if (kind === "sword" && it.form === "arcane") kind = "arcane_blade";
		const W = QW[kind];
		if (!W) return null;
		const gf = GUN_FORM[it.kind];
		return {
			W,
			item: ALIAS[it.kind] === "gun" && gf !== void 0 ? {
				...it,
				form: gf
			} : it,
			kind,
			key: kind
		};
	}
	/** 掛在手上：在主手手掌 hand 畫武器，a＝武器的世界角度。short：雙手劍用拄劍長度；offL：副手握點（自測用）；mg：主手握在武器座標 (0,mg)；M：自訂 2×2 變換。 */
	function mainWeapon(ctx, it, hand, a, view, short = false, offL = null, mg = 0, M = null) {
		const q0 = qWeapon(it);
		const q = q0 && short && q0.kind === "greatsword" ? {
			...q0,
			W: short === "f" ? QW["greatsword_kf"] : QW["greatsword_k"],
			key: short === "f" ? "greatsword_kf" : "greatsword_k"
		} : q0;
		const hx = hand[0] ?? 0;
		const hy = hand[1] ?? 0;
		if (!q) {
			if (it) pdHeld(ctx, it, hx, view !== "back");
			return;
		}
		ctx.save();
		ctx.translate(hx, hy);
		if (M) ctx.transform(M[0] ?? 1, M[1] ?? 0, M[2] ?? 0, M[3] ?? 1, 0, 0);
		else ctx.rotate(a);
		if (mg) ctx.translate(0, -mg);
		q.W.draw(ctx, q.item);
		const probe = S$1.POSE?.probe;
		if (probe) {
			const m = getM(ctx);
			probe(q.kind, tp(m, 0, 0), tp(m, 0, -q.W.len), view, offL ? tp(m, offL[0] ?? 0, offL[1] ?? 0) : null, m, q.key);
		}
		ctx.restore();
	}
	/** 副手的匕首：在手的座標系裡畫，角度相對手臂。 */
	function offDagger(ctx, it, hand, a) {
		ctx.save();
		ctx.translate(hand[0], hand[1]);
		ctx.rotate(a);
		dagger(ctx, it);
		ctx.restore();
	}
	var GUN_PD = {
		longgun: "rifle",
		shotgun: "shotgun",
		pistol: "pistol"
	};
	var PD2 = /* @__PURE__ */ new Set([
		"crossbow",
		"fist",
		"scythe",
		"whip",
		"hammer",
		"spear",
		"orb"
	]);
	/** 畫一件手持物在 (x, −9.5)，front＝正面朝向（側面、背面的鏡像握法）。不認得的 kind 不畫（QK-3 補）。 */
	function pdHeld(ctx, it0, x, front) {
		let it = it0;
		const gf = GUN_PD[it.kind];
		if (gf !== void 0) it = {
			...it,
			kind: "gun",
			form: gf
		};
		if (PD2.has(it.kind) || it.kind === "shield_kite" && it.form === "tower") {
			pdHeld2(ctx, it, x, front);
			return;
		}
		const [c, d] = colors(it);
		ctx.save();
		ctx.translate(x, -9.5);
		switch (it.kind) {
			case "sword":
			case "greatsword": {
				const L = it.kind === "greatsword" ? 24 : 16;
				const W = it.kind === "greatsword" ? 4 : 2.6;
				ctx.rotate(front ? -.25 : .25);
				fill$1(ctx, c, () => {
					ctx.moveTo(-W / 2, -3);
					ctx.lineTo(-W / 2, -L);
					ctx.lineTo(0, -L - 3);
					ctx.lineTo(W / 2, -L);
					ctx.lineTo(W / 2, -3);
					ctx.closePath();
				});
				fill$1(ctx, "rgba(255,255,255,0.45)", () => ctx.rect(-W / 2 + .6, -L, .9, L - 4));
				fill$1(ctx, it.hilt ?? "#8a6a2a", () => rr(ctx, -4.5, -4, 9, 2, 1));
				fill$1(ctx, "#4a3020", () => ctx.rect(-1, -2, 2, 4));
				break;
			}
			case "dagger":
				ctx.rotate(front ? -.6 : .6);
				fill$1(ctx, c, () => {
					ctx.moveTo(-1.3, -2);
					ctx.lineTo(0, -10);
					ctx.lineTo(1.3, -2);
					ctx.closePath();
				});
				fill$1(ctx, "#4a3020", () => ctx.rect(-2.5, -2.5, 5, 1.5));
				break;
			case "axe":
				ctx.rotate(front ? -.3 : .3);
				fill$1(ctx, "#6a4420", () => ctx.rect(-1, -18, 2, 20));
				fill$1(ctx, c, () => {
					ctx.moveTo(1, -17);
					ctx.quadraticCurveTo(9, -18, 8, -10);
					ctx.lineTo(1, -12);
					ctx.closePath();
				});
				break;
			case "gun": {
				const L = {
					pistol: 7,
					rifle: 17,
					shotgun: 15,
					energy: 12
				}[it.form ?? ""] ?? 7;
				ctx.rotate(front ? .35 : -.35);
				const s = front ? -1 : 1;
				fill$1(ctx, "#3a2a1c", () => rr(ctx, -1.2, -1, 2.4, 5, .8));
				if (it.form === "rifle" || it.form === "shotgun") fill$1(ctx, it.form === "shotgun" ? "#7a5232" : d, () => rr(ctx, s > 0 ? -6 : 1, -3, 5, 3, 1));
				fill$1(ctx, c, () => rr(ctx, s > 0 ? -1 : -L, -3.2, L + 1, it.form === "shotgun" ? 3.2 : 2.6, 1));
				break;
			}
			case "shield_round":
				fill$1(ctx, d, () => ctx.arc(0, -4, 7.5, 0, TAU));
				fill$1(ctx, c, () => ctx.arc(0, -4, 6, 0, TAU));
				fill$1(ctx, it.trim ?? "#e8bb48", () => ctx.arc(0, -4, 2, 0, TAU));
				break;
			case "shield_kite":
				fill$1(ctx, d, () => {
					ctx.moveTo(-7, -13);
					ctx.lineTo(7, -13);
					ctx.lineTo(6.5, -2);
					ctx.lineTo(0, 6);
					ctx.lineTo(-6.5, -2);
					ctx.closePath();
				});
				fill$1(ctx, c, () => {
					ctx.moveTo(-5.5, -11.5);
					ctx.lineTo(5.5, -11.5);
					ctx.lineTo(5, -2.5);
					ctx.lineTo(0, 3.8);
					ctx.lineTo(-5, -2.5);
					ctx.closePath();
				});
				fill$1(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(-.9, -11, 1.8, 13));
				fill$1(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(-5, -7, 10, 1.8));
				break;
			case "tome":
				fill$1(ctx, c, () => rr(ctx, -4.5, -6, 9, 8, 1));
				fill$1(ctx, "#f2ead6", () => ctx.rect(-3.5, -5.5, 7, 1.2));
				fill$1(ctx, it.trim ?? "#e8bb48", () => ctx.arc(0, -2, 1.6, 0, TAU));
		}
		ctx.restore();
	}
	function pdHeld2(ctx, it, x, front) {
		const [c, d] = colors(it);
		ctx.save();
		ctx.translate(x, -9.5);
		switch (it.kind) {
			case "crossbow": {
				ctx.rotate(front ? .35 : -.35);
				fill$1(ctx, "#7a5232", () => rr(ctx, front ? -12 : 0, -3, 12, 2.6, 1));
				const tip = front ? -10 : 10;
				ctx.strokeStyle = c;
				ctx.lineWidth = 2;
				ctx.beginPath();
				ctx.moveTo(tip, -9);
				ctx.quadraticCurveTo(tip + (front ? -2 : 2), -2, tip, 5);
				ctx.stroke();
				ctx.strokeStyle = "rgba(240,240,240,0.8)";
				ctx.lineWidth = .7;
				ctx.beginPath();
				ctx.moveTo(tip, -9);
				ctx.lineTo(tip + (front ? 3 : -3), -2);
				ctx.lineTo(tip, 5);
				ctx.stroke();
				break;
			}
			case "fist":
				fill$1(ctx, c, () => rr(ctx, -2.5, -3, 5, 5, 1.5));
				break;
			case "scythe":
				ctx.rotate(front ? -.15 : .15);
				fill$1(ctx, "#6a4420", () => ctx.rect(-1, -26, 2, 30));
				fill$1(ctx, c, () => {
					ctx.moveTo(0, -26);
					ctx.quadraticCurveTo(front ? 12 : -12, -28, front ? 14 : -14, -18);
					ctx.quadraticCurveTo(front ? 8 : -8, -23, 0, -23);
					ctx.closePath();
				});
				break;
			case "hammer":
				ctx.rotate(front ? -.25 : .25);
				fill$1(ctx, "#6a4420", () => ctx.rect(-1, -18, 2, 21));
				if (it.form === "mace") fill$1(ctx, c, () => ctx.arc(0, -19, 4, 0, TAU));
				else fill$1(ctx, c, () => rr(ctx, -5.5, -22, 11, 6, 1.2));
				fill$1(ctx, d, () => ctx.rect(-5.5, -19.5, 11, 1));
				break;
			case "spear":
				fill$1(ctx, "#6a4420", () => ctx.rect(-.9, -34, 1.8, 40));
				fill$1(ctx, c, () => {
					ctx.moveTo(0, -42);
					ctx.lineTo(2.4, -34);
					ctx.lineTo(-2.4, -34);
					ctx.closePath();
				});
				break;
			case "orb": {
				const orb = (it.element ? S$1.hooks.tint(it.element) : void 0) ?? c;
				ctx.fillStyle = orb;
				ctx.globalAlpha = .35;
				ctx.beginPath();
				ctx.arc(0, -6, 6, 0, TAU);
				ctx.fill();
				ctx.globalAlpha = 1;
				fill$1(ctx, orb, () => ctx.arc(0, -6, 3.6, 0, TAU));
				fill$1(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-1.2, -7.2, 1.1, 0, TAU));
				break;
			}
			case "shield_kite":
				fill$1(ctx, d, () => rr(ctx, -7.5, -16, 15, 21, 2));
				fill$1(ctx, c, () => rr(ctx, -6, -14.5, 12, 18, 1.5));
				fill$1(ctx, "#e8e0c8", () => ctx.rect(-.9, -14, 1.8, 17));
				break;
			case "whip":
				fill$1(ctx, "#4a3020", () => ctx.rect(-1, -4, 2, 5));
				ctx.strokeStyle = c;
				ctx.lineWidth = 1.4;
				ctx.beginPath();
				ctx.moveTo(0, -4);
				ctx.bezierCurveTo(front ? -8 : 8, -8, front ? -4 : 4, 6, front ? -12 : 12, 8);
				ctx.stroke();
		}
		ctx.restore();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qGear.ts
	var BOOT_TALL = {
		greaves: 4,
		iron_boots: 3,
		shoes: 0
	};
	function leg(ctx, look, feet, sx, hip, knee, lift, side, view = side ? "side" : "front") {
		const pants = look.pants ?? "#4a4038";
		const [b, bd] = feet ? colors(feet) : ["#5a4030", "#3a281c"];
		const tall = feet?.kind === "boots" ? feet.form === "tall" ? 4 : 2.5 : feet ? BOOT_TALL[feet.kind] ?? 0 : 0;
		const x = side ? sx * 1.6 : sx * 3;
		ctx.save();
		ctx.translate(0, -lift);
		rotAt(ctx, x, -9, hip * 1.6);
		fill$1(ctx, pants, () => rr(ctx, x - 2, -9.5, 4, 5, 1.2));
		rotAt(ctx, x, -5, knee * 1.6);
		fill$1(ctx, pants, () => rr(ctx, x - 2, -5.5, 4, 4.5, 1.2));
		if (tall) fill$1(ctx, b, () => rr(ctx, x - 2.2, -2 - tall, 4.4, tall + 1, 1));
		fill$1(ctx, bd, () => ctx.ellipse(x + (side ? side * .8 : 0), -1.2, feet?.kind === "iron_boots" ? 3.6 : 3.2, 2, 0, 0, TAU));
		drawLegForm(ctx, feet, sx, x, view);
		ctx.restore();
	}
	function body(ctx, it, look, side, back = false) {
		const kind = it?.kind ?? "shirt";
		const [c, d] = colors(it);
		ctx.save();
		if (side) ctx.scale(.72, 1);
		if (kind === "robe") {
			const hem = it?.form === "short" ? -6 : -1.5;
			fill$1(ctx, c, () => {
				ctx.moveTo(-7, -21);
				ctx.lineTo(7, -21);
				ctx.lineTo(10, hem);
				ctx.lineTo(-10, hem);
				ctx.closePath();
			});
			const tr = look.trim ?? it?.trim ?? d;
			if (!side && !back) fill$1(ctx, tr, () => ctx.rect(-1.2, -20, 2.4, 18.5));
			else if (side) fill$1(ctx, tr, () => ctx.rect(7.2, -20.5, 1.8, 19));
			fill$1(ctx, tr, () => ctx.rect(-10, hem - 1.5, 20, 1.6));
		} else if (kind === "coat") {
			fill$1(ctx, c, () => {
				ctx.moveTo(-7.5, -21);
				ctx.lineTo(7.5, -21);
				ctx.lineTo(8.5, -3);
				ctx.lineTo(1, -3);
				ctx.lineTo(0, -9);
				ctx.lineTo(-1, -3);
				ctx.lineTo(-8.5, -3);
				ctx.closePath();
			});
			if (!side && !back) {
				fill$1(ctx, d, () => {
					ctx.moveTo(-4, -21);
					ctx.lineTo(0, -15);
					ctx.lineTo(4, -21);
					ctx.closePath();
				});
				for (const y of [
					-17,
					-14,
					-11
				]) fill$1(ctx, "#e8bb48", () => ctx.arc(1.8, y, .7, 0, TAU));
			} else if (side) {
				fill$1(ctx, d, () => {
					ctx.moveTo(5.5, -21);
					ctx.lineTo(7.5, -16);
					ctx.lineTo(7.5, -21);
					ctx.closePath();
				});
				for (const y of [
					-17,
					-14,
					-11
				]) fill$1(ctx, "#e8bb48", () => ctx.arc(6.6, y, .7, 0, TAU));
			}
		} else if (kind === "bare") bareBody(ctx, c, look, side, back);
		else {
			fill$1(ctx, c, () => rr(ctx, -7.5, -21, 15, 13.5, 3));
			if (kind === "plate") {
				if (!back) fill$1(ctx, mix(c, "#ffffff", .35), () => rr(ctx, side ? 1.5 : -5, -19.5, 4, 6, 1.5));
				fill$1(ctx, d, () => ctx.rect(-7.5, -14, 15, 1.2));
			} else if (kind === "mail" && bodyPattern(ctx, it, d)) {} else if (kind === "mail") {
				ctx.fillStyle = d;
				for (let y = -19; y < -9; y += 2.4) for (let x = -6 + (y | 0) % 2; x < 6.5; x += 2.4) ctx.fillRect(x, y, 1, 1);
			} else if (kind === "leather") {
				const k = back ? -1 : 1;
				ctx.strokeStyle = d;
				ctx.lineWidth = 1;
				ctx.beginPath();
				if (side) {
					ctx.moveTo((S$1.WEST ? 1.5 : -1.5) / .72, -20.8);
					ctx.lineTo((S$1.WEST ? -3.5 : 4.6) / .72, -11);
				} else {
					ctx.moveTo(-5 * k, -20);
					ctx.lineTo(5 * k, -11);
				}
				ctx.stroke();
			}
			fill$1(ctx, look.belt ?? "#3a2a1c", () => ctx.rect(-7.5, -9.5, 15, 2));
			if (!side && !back) fill$1(ctx, "#d8b04a", () => ctx.rect(-1, -9.5, 2, 2));
			else if (side && !S$1.NOBUCKLE) fill$1(ctx, "#d8b04a", () => ctx.rect(6.2, -9.5, 1.3, 2));
		}
		ctx.restore();
	}
	/**
	* 赤膊（QK-8，樣張 qDoll.js body.kind "bare"；護法武僧、爐叔）：膚色軀幹（c＝膚色，qNpc.npcPrep 換好）、腰上方收窄 0.5；
	* 腋下陰影、下巴下一道陰影、胸口兩條肌肉線、肚臍；側面只有胸前那半；背面一條脊線。腰帶色＝原本的 body.color（look.belt）。
	*/
	function bareBody(ctx, c, look, side, back) {
		const sh = mix(c, "#000000", .23);
		fill$1(ctx, c, () => {
			ctx.moveTo(-4.5, -21);
			ctx.lineTo(4.5, -21);
			ctx.quadraticCurveTo(7.5, -21, 7.5, -18);
			ctx.lineTo(7.5, -15);
			ctx.quadraticCurveTo(7, -12, 7, -9.5);
			ctx.lineTo(7, -7.5);
			ctx.lineTo(-7, -7.5);
			ctx.lineTo(-7, -9.5);
			ctx.quadraticCurveTo(-7, -12, -7.5, -15);
			ctx.lineTo(-7.5, -18);
			ctx.quadraticCurveTo(-7.5, -21, -4.5, -21);
			ctx.closePath();
		});
		if (!side) for (const s of [-1, 1]) fill$1(ctx, sh, () => ctx.ellipse(s * 6.4, -18.4, 1.1, 2, 0, 0, TAU));
		ctx.strokeStyle = sh;
		ctx.lineCap = "round";
		if (!side && !back) {
			fill$1(ctx, sh, () => ctx.ellipse(0, -20.6, 4.2, 1.1, 0, 0, TAU));
			ctx.lineWidth = .7;
			for (const s of [-1, 1]) {
				ctx.beginPath();
				ctx.moveTo(s * .5, -17.4);
				ctx.quadraticCurveTo(s * 3, -15.4, s * 5.6, -17.2);
				ctx.stroke();
			}
			fill$1(ctx, sh, () => ctx.ellipse(0, -11.4, .5, .7, 0, 0, TAU));
		} else if (side) {
			fill$1(ctx, sh, () => ctx.ellipse(4.2, -20.4, 3.2, 1, 0, 0, TAU));
			ctx.lineWidth = .7;
			ctx.beginPath();
			ctx.moveTo(2.4, -17.6);
			ctx.quadraticCurveTo(5.6, -15, 7.4, -16.8);
			ctx.stroke();
		} else {
			ctx.lineWidth = .6;
			ctx.beginPath();
			ctx.moveTo(0, -19.8);
			ctx.lineTo(0, -12);
			ctx.stroke();
		}
		fill$1(ctx, look.belt ?? "#3a2a1c", () => ctx.rect(-7.5, -9.5, 15, 2));
		if (!side && !back) fill$1(ctx, "#d8b04a", () => ctx.rect(-1, -9.5, 2, 2));
	}
	function cloakFront(ctx, it) {
		const [, d] = colors(it);
		fill$1(ctx, d, () => {
			ctx.moveTo(-8, -21);
			ctx.lineTo(8, -21);
			ctx.lineTo(12, -2);
			ctx.quadraticCurveTo(0, 1, -12, -2);
			ctx.closePath();
		});
	}
	function cloakSide(ctx, it) {
		const [c, d] = colors(it);
		fill$1(ctx, c, () => {
			ctx.moveTo(-1.5, -21.5);
			ctx.lineTo(1.5, -21.5);
			ctx.lineTo(-2.5, -6);
			ctx.quadraticCurveTo(-5.5, -1.8, -9.5, -3.2);
			ctx.lineTo(-8.2, -10);
			ctx.quadraticCurveTo(-6.5, -17, -4.5, -20.5);
			ctx.closePath();
		});
		fill$1(ctx, d, () => {
			ctx.moveTo(-3.2, -5.6);
			ctx.quadraticCurveTo(-5.8, -2.6, -9.5, -3.2);
			ctx.lineTo(-9, -5);
			ctx.quadraticCurveTo(-6, -4, -3.2, -7);
			ctx.closePath();
		});
	}
	function cloakClasp(ctx, it, side) {
		if (!it) return;
		const [, d] = colors(it);
		fill$1(ctx, d, () => ctx.roundRect(side ? -2.5 : -6.5, -21.6, side ? 5 : 13, 1.8, .9));
		fill$1(ctx, "#e8bb48", () => ctx.arc(side ? 1.6 : 0, -20.7, 1.1, 0, TAU));
	}
	function cloakBack(ctx, it) {
		const [c, d] = colors(it);
		fill$1(ctx, c, () => {
			ctx.moveTo(-6.5, -23);
			ctx.lineTo(6.5, -23);
			ctx.quadraticCurveTo(11.2, -22.6, 11.4, -18);
			ctx.lineTo(12.6, -2);
			ctx.quadraticCurveTo(0, 1, -12.6, -2);
			ctx.lineTo(-11.4, -18);
			ctx.quadraticCurveTo(-11.2, -22.6, -6.5, -23);
			ctx.closePath();
		});
		ctx.strokeStyle = d;
		ctx.lineWidth = 1;
		ctx.beginPath();
		ctx.moveTo(-3, -18);
		ctx.lineTo(-5, -3);
		ctx.moveTo(3, -18);
		ctx.lineTo(5, -3);
		ctx.stroke();
	}
	var RIM = "#c3ccd6";
	function shieldFront(ctx, it, x) {
		ctx.save();
		ctx.translate(0, -pz("shieldUp"));
		pdHeld(ctx, it, x, true);
		if (it.kind === "shield_round") {
			ctx.strokeStyle = RIM;
			ctx.lineWidth = .9;
			ctx.beginPath();
			ctx.arc(x, -13.5, 7.1, 0, TAU);
			ctx.stroke();
			if (S$1.SHEDGE) {
				ctx.strokeStyle = Q_OUT;
				ctx.lineWidth = .5;
				ctx.beginPath();
				ctx.arc(x, -13.5, 7.3, 0, TAU);
				ctx.stroke();
			}
		}
		ctx.restore();
	}
	function shieldSide(ctx, it) {
		const [c, d] = colors(it);
		const tower = it.kind === "shield_kite" && it.form === "tower";
		ctx.save();
		ctx.translate(8.6, -13.5 - pz("shieldUp"));
		if (it.kind === "shield_round") {
			fill$1(ctx, d, () => ctx.ellipse(0, 0, 2.9, 7.5, 0, 0, TAU));
			fill$1(ctx, c, () => ctx.ellipse(.6, 0, 2.1, 6.2, 0, 0, TAU));
			ctx.strokeStyle = RIM;
			ctx.lineWidth = .9;
			ctx.beginPath();
			ctx.ellipse(.2, 0, 2.7, 7.2, 0, 0, TAU);
			ctx.stroke();
			fill$1(ctx, it.trim ?? "#e8bb48", () => ctx.ellipse(1.9, 0, 1.1, 2, 0, 0, TAU));
		} else {
			const top = tower ? -9 : -7;
			const bot = tower ? 11 : 9;
			fill$1(ctx, d, () => {
				ctx.moveTo(-1.6, top);
				ctx.lineTo(2.2, top);
				ctx.lineTo(2.2, bot - 6);
				ctx.lineTo(.6, bot);
				ctx.lineTo(-1.6, bot - 7);
				ctx.closePath();
			});
			fill$1(ctx, c, () => {
				ctx.moveTo(-.6, top + 1.2);
				ctx.lineTo(1.4, top + 1.2);
				ctx.lineTo(1.4, bot - 6.4);
				ctx.lineTo(.5, bot - 2.4);
				ctx.lineTo(-.6, bot - 7);
				ctx.closePath();
			});
			fill$1(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(1.3, top + 1, 1, bot - top - 4));
		}
		ctx.restore();
	}
	function shieldBack(ctx, it, x, dy = 0) {
		const [, d] = colors(it);
		const wood = "#7a5232";
		ctx.save();
		ctx.translate(x - 1, (it.kind === "shield_round" ? -11.8 : -16.5) + dy);
		if (it.kind === "shield_round") {
			fill$1(ctx, d, () => ctx.arc(0, 0, 7.5, 0, TAU));
			fill$1(ctx, wood, () => ctx.arc(0, 0, 6.2, 0, TAU));
			ctx.strokeStyle = RIM;
			ctx.lineWidth = .9;
			ctx.beginPath();
			ctx.arc(0, 0, 7.1, 0, TAU);
			ctx.stroke();
		} else if (it.form === "tower") {
			fill$1(ctx, d, () => rr(ctx, -7, -6, 14, 22, 1.5));
			fill$1(ctx, wood, () => rr(ctx, -5.6, -4.6, 11.2, 19.2, 1));
		} else {
			fill$1(ctx, d, () => {
				ctx.moveTo(-7, -4);
				ctx.lineTo(7, -4);
				ctx.lineTo(6.5, 7);
				ctx.lineTo(0, 15);
				ctx.lineTo(-6.5, 7);
				ctx.closePath();
			});
			fill$1(ctx, wood, () => {
				ctx.moveTo(-5.5, -2.5);
				ctx.lineTo(5.5, -2.5);
				ctx.lineTo(5, 6.5);
				ctx.lineTo(0, 12.8);
				ctx.lineTo(-5, 6.5);
				ctx.closePath();
			});
		}
		ctx.restore();
	}
	function arrows(ctx, xs, y0, y1) {
		for (const [x, col] of xs) fill$1(ctx, col, () => {
			ctx.moveTo(x - .7, y0);
			ctx.lineTo(x, y1);
			ctx.lineTo(x + .7, y0);
			ctx.closePath();
		});
	}
	var FEATHERS = [
		[-1.4, "#e8e0c8"],
		[.2, "#d23c3c"],
		[1.6, "#e8e0c8"]
	];
	/** 背掛：quiver 箭袋（右肩出口，斜背到左腰）、backpack 背包、scroll_case 卷軸筒。layer：behind＝身體之前畫、over＝身體之後。 */
	function backItem(ctx, it, view, layer) {
		if (!it) return;
		const [c, d] = colors(it);
		const SD = view === "side";
		const B = view === "back";
		const F = view === "front";
		const strap = it.strap ?? "#4a3020";
		if (it.kind === "quiver" || it.kind === "scroll_case") {
			const tube = it.kind === "scroll_case";
			if (F) {
				if (layer === "behind") {
					ctx.save();
					ctx.translate(-5.5, -23);
					ctx.rotate(-.5);
					if (tube) fill$1(ctx, d, () => rr(ctx, -2, -4, 4, 4, 1.2));
					else arrows(ctx, FEATHERS, 0, -4.2);
					ctx.restore();
				} else {
					ctx.strokeStyle = strap;
					ctx.lineWidth = 1.3;
					ctx.beginPath();
					ctx.moveTo(-6.2, -20.6);
					ctx.lineTo(6.6, -9.8);
					ctx.stroke();
				}
				return;
			}
			if (B) {
				if (layer !== "over") return;
				ctx.save();
				ctx.translate(3.4, -14.6);
				ctx.rotate(.2);
				fill$1(ctx, c, () => rr(ctx, -2.6, -9, 5.2, 15, 1.8));
				fill$1(ctx, d, () => ctx.rect(-2.6, -2, 5.2, 1.2));
				fill$1(ctx, d, () => ctx.rect(-2.6, 3, 5.2, 1.2));
				if (tube) fill$1(ctx, d, () => rr(ctx, -3, -11, 6, 3, 1.2));
				else arrows(ctx, FEATHERS, -9, -13.5);
				ctx.restore();
				return;
			}
			if (SD && layer === "behind") {
				ctx.save();
				ctx.translate(-6, -15.5);
				ctx.rotate(-.28);
				fill$1(ctx, c, () => rr(ctx, -2.4, -9, 4.8, 14, 1.8));
				fill$1(ctx, d, () => ctx.rect(-2.4, -1.5, 4.8, 1.2));
				if (tube) fill$1(ctx, d, () => rr(ctx, -2.8, -11, 5.6, 3, 1.2));
				else arrows(ctx, [
					[-1.3, "#e8e0c8"],
					[.2, "#d23c3c"],
					[1.5, "#e8e0c8"]
				], -9, -13.2);
				ctx.restore();
			}
			if (SD && layer === "over") {
				ctx.strokeStyle = strap;
				ctx.lineWidth = 1.3;
				ctx.beginPath();
				ctx.moveTo(S$1.WEST ? 1.5 : -1.5, -20.8);
				ctx.lineTo(S$1.WEST ? -3.5 : 4.6, -11);
				ctx.stroke();
			}
			return;
		}
		if (it.kind === "backpack") {
			if (F) {
				if (layer === "over") for (const x of [-4.8, 4.8]) fill$1(ctx, strap, () => rr(ctx, x - .9, -21, 1.8, 10, .8));
				return;
			}
			if (B) {
				if (layer === "over") {
					fill$1(ctx, c, () => rr(ctx, -6, -20.5, 12, 11, 2.5));
					fill$1(ctx, d, () => rr(ctx, -6, -20.5, 12, 4, 2));
					fill$1(ctx, "#d8b04a", () => ctx.rect(-.8, -17, 1.6, 1.6));
				}
				return;
			}
			if (SD && layer === "behind") {
				fill$1(ctx, c, () => rr(ctx, -9.6, -20.5, 5.6, 11, 2));
				fill$1(ctx, d, () => rr(ctx, -9.6, -20.5, 5.6, 3.5, 1.6));
			}
			if (SD && layer === "over") fill$1(ctx, strap, () => rr(ctx, -1.6, -21, 1.8, 9, .8));
		}
	}
	/** 腰掛：scabbard 劍鞘（左腰，斜往後下）、pouch 腰包（右腰）。 */
	function waistItem(ctx, it, view, layer) {
		if (!it) return;
		const [c, d] = colors(it);
		const SD = view === "side";
		const B = view === "back";
		const F = view === "front";
		const left = it.kind === "scabbard";
		const near = SD ? left ? S$1.WEST : !S$1.WEST : true;
		if (SD && layer === "behind" !== !near) return;
		if (!SD && layer !== "over") return;
		const x = F ? left ? 7.2 : -7.2 : B ? left ? -7.2 : 7.2 : 0;
		if (it.kind === "scabbard") {
			ctx.save();
			if (SD) {
				ctx.translate(-.5, -9.5);
				ctx.rotate(.95);
			} else {
				ctx.translate(x, -9.5);
				ctx.rotate((F ? -1 : 1) * (left ? .45 : -.45));
			}
			fill$1(ctx, c, () => rr(ctx, -1.5, 0, 3, 11, 1.4));
			fill$1(ctx, d, () => ctx.rect(-1.5, 8.5, 3, 2.5));
			fill$1(ctx, "#d8b04a", () => ctx.rect(-1.7, 0, 3.4, 1.4));
			ctx.restore();
			return;
		}
		if (it.kind === "pouch") {
			const px = SD ? .2 : x * .64;
			fill$1(ctx, c, () => rr(ctx, px - 2.2, -9.2, 4.4, 4.6, 1.4));
			fill$1(ctx, d, () => rr(ctx, px - 2.2, -9.2, 4.4, 1.8, 1));
		}
	}
	/** 頸飾：necklace 項鍊（墜子在胸前）、beads 念珠。 */
	/** 念珠的預設顏色（樣張 qNpc.js 護法武僧）。 */
	var BEAD_COLOR = "#6a3a22";
	function neckItem(ctx, it, view) {
		if (!it || isNeckForm(it)) return;
		if (it.kind === "fur_collar" || it.kind === "feathers") {
			neckWide(ctx, it, view);
			return;
		}
		const bead = it.kind === "beads";
		const c = bead && !it.color ? BEAD_COLOR : colors(it)[0];
		const SD = view === "side";
		if (view === "back") {
			ctx.strokeStyle = c;
			ctx.lineWidth = .8;
			ctx.beginPath();
			ctx.moveTo(-3.5, -20.8);
			ctx.quadraticCurveTo(0, -20.2, 3.5, -20.8);
			ctx.stroke();
			return;
		}
		if (SD) {
			ctx.strokeStyle = c;
			ctx.lineWidth = .8;
			ctx.beginPath();
			ctx.moveTo(-1.5, -20.8);
			ctx.quadraticCurveTo(3.8, -17.6, 5.4, -18.4);
			ctx.stroke();
			fill$1(ctx, bead ? c : "#e8bb48", () => ctx.ellipse(5.4, -17.4, 1, 1.3, 0, 0, TAU));
			return;
		}
		if (bead) for (let i = 0; i <= 6; i++) {
			const t = i / 6;
			const bx = -4.5 + 9 * t;
			const by = -20.5 + 4.2 * Math.sin(t * Math.PI);
			fill$1(ctx, c, () => ctx.arc(bx, by, .9, 0, TAU));
		}
		else {
			ctx.strokeStyle = c;
			ctx.lineWidth = .8;
			ctx.beginPath();
			ctx.moveTo(-4.5, -20.6);
			ctx.quadraticCurveTo(0, -14.5, 4.5, -20.6);
			ctx.stroke();
			fill$1(ctx, "#e8bb48", () => {
				ctx.moveTo(0, -17.8);
				ctx.lineTo(1.4, -16.2);
				ctx.lineTo(0, -14.4);
				ctx.lineTo(-1.4, -16.2);
				ctx.closePath();
			});
		}
	}
	/** 毛領（脖子一圈蓬鬆毛）、白羽披肩（肩上一圈白羽，羽尖到胸口上緣）；樣張 qDoll.js neckWide。顏色照 it.color，沒寫用樣張預設（不走材質色）。 */
	function neckWide(ctx, it, view) {
		const SD = view === "side";
		const fur = it.kind === "fur_collar";
		const c = it.color ?? (fur ? "#d8c8a8" : "#f2f0ea");
		const d = mix(c, "#000000", .2);
		if (fur) {
			const xs = SD ? [
				-5.6,
				-3,
				-.4,
				2.2,
				4.8
			] : [
				-8,
				-5.4,
				-2.7,
				0,
				2.7,
				5.4,
				8
			];
			fill$1(ctx, c, () => {
				for (const x of xs) {
					ctx.moveTo(x + 1.9, -20.4);
					ctx.ellipse(x, -20.4 + Math.abs(x) * .06, 1.9, 1.7, 0, 0, TAU);
				}
			});
			ctx.strokeStyle = d;
			ctx.lineWidth = .4;
			ctx.beginPath();
			ctx.moveTo(xs[0], -19.2);
			ctx.lineTo(xs[xs.length - 1], -19.2);
			ctx.stroke();
			return;
		}
		const tips = SD ? [
			[-6, -16.4],
			[-3.4, -15.6],
			[-.6, -15.8],
			[2.2, -16],
			[5, -16.8]
		] : [
			[-10, -17.2],
			[-6.6, -16.2],
			[-3.2, -15.8],
			[0, -15.6],
			[3.2, -15.8],
			[6.6, -16.2],
			[10, -17.2]
		];
		const top = SD ? [[-7, -21.6], [6.2, -21]] : [[-8.4, -21.6], [8.4, -21.6]];
		fill$1(ctx, c, () => {
			ctx.moveTo(top[0][0], top[0][1]);
			ctx.quadraticCurveTo(0, -22.6, top[1][0], top[1][1]);
			const L = tips.length;
			ctx.lineTo(tips[L - 1][0] + .6, tips[L - 1][1] - 2);
			for (let i = L - 1; i >= 0; i--) {
				const [x, y] = tips[i];
				ctx.quadraticCurveTo(x + 1.2, y + .4, x, y);
				ctx.quadraticCurveTo(x - 1.2, y - 1.6, x - 1.4, y - 2.4);
			}
			ctx.closePath();
		});
		ctx.strokeStyle = d;
		ctx.lineWidth = .45;
		ctx.lineCap = "round";
		for (const [x, y] of tips) {
			ctx.beginPath();
			ctx.moveTo(x, y - .4);
			ctx.lineTo(x * .8, y - 3.4);
			ctx.stroke();
		}
	}
	/** 胸前紋章（body.crest：顏色）：正面在胸口；側面只在胸前前緣露一條；背面不畫。 */
	function crest(ctx, it, view) {
		if (!it?.crest) return;
		const cr = it.crest;
		if (view === "back") return;
		if (view === "side") {
			fill$1(ctx, cr, () => rr(ctx, 4.4, -18.5, 1.6, 5, .6));
			return;
		}
		fill$1(ctx, cr, () => {
			ctx.moveTo(-2.6, -18.8);
			ctx.lineTo(2.6, -18.8);
			ctx.lineTo(2.6, -15.4);
			ctx.lineTo(0, -13.2);
			ctx.lineTo(-2.6, -15.4);
			ctx.closePath();
		});
		fill$1(ctx, "#e8bb48", () => ctx.rect(-.6, -18.2, 1.2, 4));
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qRace.ts
	var dark = (c, t = .3) => mix(c, "#000000", t);
	/** 頭部裝備遮住哪裡：top＝頭頂、side＝兩側、hood＝兜帽（有耳朵版）、tall＝高帽。 */
	var COVERS = {
		helmet: {
			top: true,
			side: true
		},
		greathelm: {
			top: true,
			side: true
		},
		horned_helm: {
			top: true,
			side: true
		},
		hood: {
			top: true,
			side: true,
			hood: true
		},
		cap: { top: true },
		bandana: { top: true },
		crown: {},
		wide_hat: {
			top: true,
			tall: true
		},
		wizard_hat: {
			top: true,
			tall: true
		}
	};
	var coverOf = (head) => head ? COVERS[head.kind] ?? { top: true } : {};
	/** 體型（整個人含裝備一起縮放）：stout ×(1.12, 0.88)、tall ×(0.96, 1.1)。 */
	function raceBuild(ctx, look) {
		if (look.build === "stout") ctx.scale(1.12, .88);
		else if (look.build === "tall") ctx.scale(.96, 1.1);
	}
	var TAIL = {
		dragon: (ctx, look) => {
			const c = look.scaleColor ?? "#a8784a";
			for (const t of [
				.22,
				.42,
				.62,
				.8
			]) fill$1(ctx, mix(c, "#ffffff", .3), () => {
				const x = 19 * t;
				const y = -16.5 + 15 * t;
				ctx.moveTo(x - 2, y + 1);
				ctx.lineTo(x + .4, y - 4.2);
				ctx.lineTo(x + 2.2, y + 1.2);
				ctx.closePath();
			});
			fill$1(ctx, c, () => {
				ctx.moveTo(0, -17);
				ctx.quadraticCurveTo(13, -15.5, 18.5, -3);
				ctx.lineTo(23, 1.5);
				ctx.lineTo(16.5, .6);
				ctx.quadraticCurveTo(9, -4.5, 0, -8);
				ctx.closePath();
			});
			fill$1(ctx, mix(c, "#f4e6c8", .45), () => {
				ctx.moveTo(0, -10);
				ctx.quadraticCurveTo(8.5, -7, 15.5, -.6);
				ctx.lineTo(16.5, .6);
				ctx.quadraticCurveTo(9, -4.5, 0, -8);
				ctx.closePath();
			});
		},
		cat: (ctx, look) => {
			const c = look.tailColor ?? look.hairColor ?? "#5a3a22";
			ctx.strokeStyle = c;
			ctx.lineWidth = 2;
			ctx.lineCap = "round";
			ctx.beginPath();
			ctx.moveTo(0, -12);
			ctx.bezierCurveTo(9, -11, 12, -17, 10, -24);
			ctx.stroke();
			fill$1(ctx, c, () => ctx.arc(10, -24.2, 1.3, 0, TAU));
		},
		wolf: (ctx, look) => {
			const c = look.tailColor ?? look.hairColor ?? "#7a7a84";
			fill$1(ctx, c, () => {
				ctx.moveTo(0, -14);
				ctx.quadraticCurveTo(9, -14, 11, -6);
				ctx.quadraticCurveTo(12, 0, 8.5, 2);
				ctx.quadraticCurveTo(7, -5, 0, -9);
				ctx.closePath();
			});
			fill$1(ctx, mix(c, "#000000", .3), () => {
				ctx.moveTo(11.3, -2.5);
				ctx.quadraticCurveTo(12, .5, 8.5, 2);
				ctx.quadraticCurveTo(9.5, -.5, 11.3, -2.5);
				ctx.closePath();
			});
		},
		rabbit: (ctx, look, view) => {
			const c = look.tailColor ?? "#efe6d6";
			const [x, y] = view === "back" ? [0, -10.5] : [8, -8.5];
			fill$1(ctx, c, () => ctx.arc(x, y, 2.4, 0, TAU));
			ctx.strokeStyle = dark(c, .2);
			ctx.lineWidth = .7;
			ctx.beginPath();
			ctx.arc(x, y, 2.4, 0, TAU);
			ctx.stroke();
		},
		fox: (ctx, look) => {
			fill$1(ctx, look.tailColor ?? look.hairColor ?? "#d8762a", () => {
				ctx.moveTo(0, -13);
				ctx.quadraticCurveTo(10, -14, 14, -6);
				ctx.quadraticCurveTo(17, 2, 11, 0);
				ctx.quadraticCurveTo(8, -6, 0, -9);
				ctx.closePath();
			});
			fill$1(ctx, "#f4ece0", () => ctx.ellipse(13.5, -1.5, 3, 2.4, .4, 0, TAU));
		},
		scaled: (ctx, look) => {
			const c = look.tailColor ?? dark(look.skin, .15);
			fill$1(ctx, c, () => {
				ctx.moveTo(0, -14);
				ctx.quadraticCurveTo(9, -12, 15, -3);
				ctx.lineTo(17, -1);
				ctx.quadraticCurveTo(8, -6, 0, -9);
				ctx.closePath();
			});
			ctx.strokeStyle = dark(c);
			ctx.lineWidth = .8;
			for (const t of [
				.3,
				.55,
				.8
			]) {
				ctx.beginPath();
				ctx.moveTo(15 * t, -13 + 10 * t);
				ctx.lineTo(15 * t + 1.5, -10 + 8 * t);
				ctx.stroke();
			}
		},
		demon: (ctx, look) => {
			const c = look.tailColor ?? dark(look.skin, .25);
			ctx.strokeStyle = c;
			ctx.lineWidth = 1.8;
			ctx.lineCap = "round";
			ctx.beginPath();
			ctx.moveTo(0, -12);
			ctx.quadraticCurveTo(12, -10, 13, -2);
			ctx.stroke();
			fill$1(ctx, c, () => {
				ctx.moveTo(13, -2);
				ctx.lineTo(10.5, 1.5);
				ctx.lineTo(13, 4.5);
				ctx.lineTo(15.5, 1.5);
				ctx.closePath();
			});
		}
	};
	function wings(ctx, look) {
		if (!look.wings) return;
		const c = look.scaleColor ?? "#a8784a";
		const m = mix(c, "#ffffff", .25);
		for (const s of [-1, 1]) {
			fill$1(ctx, dark(c, .15), () => {
				ctx.moveTo(s * 4, -22);
				ctx.lineTo(s * 15, -34);
				ctx.lineTo(s * 16, -22);
				ctx.lineTo(s * 13, -16);
				ctx.lineTo(s * 9, -19);
				ctx.lineTo(s * 6, -15);
				ctx.closePath();
			});
			ctx.strokeStyle = m;
			ctx.lineWidth = .9;
			ctx.beginPath();
			ctx.moveTo(s * 5, -21);
			ctx.lineTo(s * 15, -33);
			ctx.moveTo(s * 9, -25);
			ctx.lineTo(s * 13, -16);
			ctx.stroke();
		}
	}
	function spines(ctx, look) {
		if (!look.spines) return;
		const c = look.scaleColor ?? "#a8784a";
		for (const [x, y] of [
			[-5, -24],
			[0, -25],
			[5, -24]
		]) fill$1(ctx, mix(c, "#ffffff", .2), () => {
			ctx.moveTo(x - 1.8, y + 2);
			ctx.lineTo(x, y - 4);
			ctx.lineTo(x + 1.8, y + 2);
			ctx.closePath();
		});
	}
	var tailKind = (look) => look.tail === "fox" && look.beastEars && TAIL[look.beastEars] ? look.beastEars : look.tail;
	/** 尾巴（含龍翼、背刺）：正面、側面畫在身體後面；背面畫在披風之上。side：側面 1、正面背面 0。 */
	function raceTail(ctx, look, view, side) {
		wings(ctx, look);
		spines(ctx, look);
		const kind = tailKind(look);
		const draw = kind ? TAIL[kind] : void 0;
		if (!draw || !kind) return;
		ctx.save();
		const dir = side === 1 ? -1 : side === -1 ? 1 : view === "back" ? -1 : 1;
		ctx.scale(dir, 1);
		if (kind === "dragon" && view !== "side") ctx.scale(.74, 1);
		if (view === "back") ctx.translate(0, 2);
		draw(ctx, look, view);
		const root = {
			fox: [
				-11,
				2.3,
				look.tailColor ?? look.hairColor ?? "#d8762a"
			],
			dragon: [
				-12.5,
				4.6,
				look.scaleColor ?? "#a8784a"
			],
			wolf: [
				-11.5,
				2.6,
				look.tailColor ?? look.hairColor ?? "#7a7a84"
			],
			scaled: [
				-11.5,
				2.6,
				look.tailColor ?? dark(look.skin, .15)
			]
		}[kind];
		if (view === "back" && root) fill$1(ctx, root[2], () => ctx.ellipse(.4, root[0], root[1] * .9, root[1], 0, 0, TAU));
		ctx.restore();
	}
	/** 臉：紋路、鬍子、獠牙（背面不畫）。遊戲資料的龍鱗 `dragonscale` 畫成 Q 版龍裔的「少量鱗」（dragonQ）。 */
	function raceFace(ctx, look, view, side, west = false) {
		if (view === "back") return;
		const ex = side * 2.6;
		const pattern = look.pattern === "dragonscale" ? "dragonQ" : look.pattern;
		if (pattern === "scales") fill$1(ctx, dark(look.skin, .22), () => {
			for (const [x, y] of [
				[-6, -25],
				[-4.5, -23.5],
				[5.5, -25],
				[4, -23.5],
				[-1, -35],
				[1.5, -35.5]
			]) {
				ctx.moveTo(ex + x + 1.1, y);
				ctx.arc(ex + x, y, 1.1, 0, Math.PI);
			}
		});
		else if (pattern === "marks") {
			ctx.strokeStyle = look.markColor ?? "#2a8ac8";
			ctx.lineWidth = 1.1;
			for (const s of [-1, 1]) {
				ctx.beginPath();
				ctx.moveTo(ex + s * 4, -27);
				ctx.quadraticCurveTo(ex + s * 6, -25, ex + s * 5, -23);
				ctx.stroke();
			}
			ctx.beginPath();
			ctx.moveTo(ex - 1.5, -35);
			ctx.lineTo(ex, -33);
			ctx.lineTo(ex + 1.5, -35);
			ctx.stroke();
		} else if (pattern === "circuit") {
			const s = side === -1 ? -1 : 1;
			if (view !== "side" || west) {
				fill$1(ctx, "#9aa4b0", () => {
					ctx.arc(0, -29, 8.5, s > 0 ? -Math.PI / 2 : Math.PI / 2, s > 0 ? Math.PI / 2 : Math.PI * 1.5);
					ctx.closePath();
				});
				ctx.save();
				ctx.strokeStyle = "#4ae0d0";
				ctx.lineWidth = .9;
				ctx.shadowColor = "#4ae0d0";
				ctx.shadowBlur = 2;
				ctx.beginPath();
				ctx.moveTo(s * 1, -36);
				ctx.lineTo(s * 4, -33);
				ctx.lineTo(s * 4, -25);
				ctx.lineTo(s * 7, -23);
				ctx.stroke();
				fill$1(ctx, "#4ae0d0", () => ctx.arc(ex + s * 2.9, -28.5, 1.5, 0, TAU));
				ctx.restore();
			}
		}
		if (pattern === "dragonQ") {
			const c = look.scaleColor ?? "#a8784a";
			const dia = (x, y, r) => {
				ctx.moveTo(x, y - r * 1.25);
				ctx.lineTo(x + r, y);
				ctx.lineTo(x, y + r * 1.25);
				ctx.lineTo(x - r, y);
				ctx.closePath();
			};
			const pts = view === "side" ? [[
				2.2,
				-31.8,
				1.1
			], [
				.6,
				-34.4,
				1
			]] : [
				[
					-6,
					-31.4,
					1.1
				],
				[
					-4.7,
					-34.2,
					1
				],
				[
					6,
					-31.4,
					1.1
				],
				[
					4.7,
					-34.2,
					1
				]
			];
			fill$1(ctx, c, () => {
				for (const [x, y, r] of pts) dia(x, y, r);
			});
			fill$1(ctx, c, () => dia(view === "side" ? 5.2 : 0, -35.6, 1.1));
			ctx.strokeStyle = dark(look.skin, .4);
			ctx.lineWidth = .9;
			ctx.lineCap = "round";
			for (const [x, ok] of [[ex + 2.9, side === 0 || side === 1], [ex - 2.9, side === 0 || side === -1]]) if (ok) {
				const o = x > ex ? 1 : -1;
				ctx.beginPath();
				ctx.moveTo(x - o * 1.4, -31.6);
				ctx.lineTo(x + o * 1.3, -31);
				ctx.stroke();
			}
		}
		if (look.ridge && pattern !== "dragonQ") {
			const c = look.scaleColor ?? "#a8784a";
			for (const y of [
				-35.5,
				-33,
				-30.5
			]) fill$1(ctx, c, () => {
				ctx.moveTo(ex - 1.3, y + 1.2);
				ctx.lineTo(ex, y - 1.2);
				ctx.lineTo(ex + 1.3, y + 1.2);
				ctx.closePath();
			});
		}
		if (look.slitEyes) {
			const amber = look.eyes ?? "#9a4a12";
			for (const [x, ok] of [[ex + 2.9, side === 0 || side === 1], [ex - 2.9, side === 0 || side === -1]]) if (ok) {
				fill$1(ctx, amber, () => ctx.ellipse(x, -28.5, 1.5, 1.9, 0, 0, TAU));
				fill$1(ctx, "#1d1a22", () => ctx.rect(x - .35, -30.2, .7, 3.4));
			}
		}
		if (look.tusks) for (const s of view === "side" ? [1] : [-1, 1]) fill$1(ctx, "#f4ecd8", () => {
			ctx.moveTo(ex + s * 2.5, -24);
			ctx.lineTo(ex + s * 3.4, -27);
			ctx.lineTo(ex + s * 4, -24);
			ctx.closePath();
		});
		if (look.beard) {
			const c = look.hairColor ?? "#8a4a22";
			const sideClip = view === "side";
			if (sideClip) {
				ctx.save();
				ctx.beginPath();
				ctx.arc(0, -29, 8.5, 0, TAU);
				ctx.moveTo(-14, -27);
				ctx.lineTo(8.26, -27);
				ctx.arc(0, -29, 8.5, Math.asin(2 / 8.5), Math.asin(7 / 8.5));
				ctx.lineTo(2.4, -14);
				ctx.lineTo(-14, -14);
				ctx.closePath();
				ctx.clip("nonzero");
			}
			fill$1(ctx, c, () => {
				ctx.moveTo(ex - 7, -27);
				ctx.quadraticCurveTo(ex - 7, -18, ex, -16);
				ctx.quadraticCurveTo(ex + 7, -18, ex + 7, -27);
				ctx.quadraticCurveTo(ex, -23, ex - 7, -27);
			});
			if (sideClip) ctx.restore();
			fill$1(ctx, dark(c), () => ctx.rect(ex - 2, -25.5, 4, 1));
		}
	}
	function sideEar(ctx, look, s, kind) {
		const c = look.skin;
		if (kind === "pointed") fill$1(ctx, c, () => {
			ctx.moveTo(s * 7.5, -31);
			ctx.lineTo(s * 15, -36);
			ctx.lineTo(s * 8, -27);
			ctx.closePath();
		});
		else {
			fill$1(ctx, mix(c, "#9fe6ff", .25), () => {
				ctx.moveTo(s * 7.5, -32);
				ctx.lineTo(s * 14, -36);
				ctx.lineTo(s * 15, -31);
				ctx.lineTo(s * 13, -27);
				ctx.lineTo(s * 8, -27);
				ctx.closePath();
			});
			ctx.strokeStyle = dark(c, .35);
			ctx.lineWidth = .7;
			for (const [x, y] of [
				[14, -35],
				[14.6, -31],
				[13, -27.5]
			]) {
				ctx.beginPath();
				ctx.moveTo(s * 8, -29.5);
				ctx.lineTo(s * x, y);
				ctx.stroke();
			}
		}
	}
	/** 獸耳族的四種耳朵：狐、貓、狼、兔；花色跟著髮色。側面兩耳一前一後（s −1 是後耳）。 */
	function beastEar(ctx, look, s, color, view = "front") {
		const c = color ?? look.earColor ?? look.hairColor ?? "#d8762a";
		const kind = look.beastEars ?? "fox";
		const inner = "#f2c8b0";
		const sd = view === "side";
		const back = view === "back";
		const X = (x) => sd ? s > 0 ? x - 4.5 : x - 8.6 : s * x;
		const dy = sd && s < 0 ? 1 : 0;
		const tri = (pts, col) => fill$1(ctx, col, () => {
			pts.forEach(([x, y], i) => i ? ctx.lineTo(X(x), y + dy) : ctx.moveTo(X(x), y + dy));
			ctx.closePath();
		});
		const showInner = !color && !back && !(sd && s < 0);
		if (kind === "cat") {
			tri([
				[2.8, -35.5],
				[5.4, -41.6],
				[8.4, -34.2]
			], c);
			if (showInner) tri([
				[4, -35.6],
				[5.4, -39.6],
				[7.1, -35]
			], inner);
			return;
		}
		if (kind === "wolf") {
			tri([
				[4, -36],
				[5.9, -47],
				[7.7, -34.8]
			], c);
			tri([
				[5.9, -47],
				[7.7, -34.8],
				[6.2, -35.3],
				[5.5, -43.8]
			], mix(c, "#000000", .38));
			if (showInner) tri([
				[4.8, -36],
				[5.5, -42.6],
				[6, -35.6]
			], "#a9a9b2");
			return;
		}
		if (kind === "rabbit") {
			fill$1(ctx, c, () => ctx.ellipse(X(4.2), -43 + dy, 2.2, 7.6, sd ? -.25 : s * .12, 0, TAU));
			if (showInner) fill$1(ctx, inner, () => ctx.ellipse(X(4.2), -42.4 + dy, 1.1, 5.6, sd ? -.25 : s * .12, 0, TAU));
			return;
		}
		tri([
			[2.5, -36],
			[6.5, -45],
			[8.5, -34]
		], c);
		if (showInner) tri([
			[4, -36],
			[6.3, -42],
			[7.3, -35.5]
		], inner);
	}
	/** 耳朵（phase "over"＝帽子之後畫）。 */
	function raceEars(ctx, look, view, side, head, phase) {
		const kind = look.ears;
		if (!kind || kind === "none" || phase !== "over") return;
		const cov = coverOf(head);
		if (kind === "pointed" || kind === "fin") {
			if (cov.hood) return;
			const sides = side === 0 || view === "back" ? [-1, 1] : [-side];
			for (const s of sides) sideEar(ctx, look, s, kind);
			return;
		}
		if (kind === "beast") {
			if (cov.hood) {
				for (const s of [-1, 1]) beastEar(ctx, look, s * .9, head?.color ?? "#5a4a3a");
				return;
			}
			if (cov.top && !["cap", "bandana"].includes(head?.kind ?? "")) return;
			for (const s of [-1, 1]) beastEar(ctx, look, s, void 0, view === "side" && side ? "side" : view);
		}
	}
	/** 頭部裝備在有角時的調整：角盔改成一般頭盔、小帽變窄夾在兩角之間、寬帽與巫師帽抬高。 */
	function raceHat(ctx, look, head, draw) {
		if (!head) return;
		if (!(look.horns && look.horns !== "none")) {
			draw(head);
			return;
		}
		if (head.kind === "horned_helm") {
			draw({
				...head,
				kind: "helmet"
			});
			return;
		}
		ctx.save();
		if ([
			"cap",
			"bandana",
			"crown"
		].includes(head.kind)) {
			ctx.translate(0, -29);
			ctx.scale(.8, 1);
			ctx.translate(0, 29);
		} else if (COVERS[head.kind]?.tall) ctx.translate(0, -5);
		draw(head);
		ctx.restore();
	}
	/** 角：永遠在最上層。 */
	function raceHorns(ctx, look, view) {
		const kind = look.horns;
		if (!kind || kind === "none") return;
		const c = look.hornColor ?? "#efe6cc";
		for (const s of [-1, 1]) {
			if (kind === "dragon") {
				if (view === "side") {
					if (s > 0) continue;
					fill$1(ctx, c, () => {
						ctx.moveTo(3.8, -35.2);
						ctx.quadraticCurveTo(-3, -43.5, -13, -40.5);
						ctx.quadraticCurveTo(-5, -39.2, .2, -33.2);
						ctx.closePath();
					});
					fill$1(ctx, c, () => {
						ctx.moveTo(-1.5, -32.5);
						ctx.quadraticCurveTo(-6.5, -35.5, -11, -33);
						ctx.quadraticCurveTo(-6.5, -32.6, -2.5, -30.3);
						ctx.closePath();
					});
					ctx.strokeStyle = dark(c, .28);
					ctx.lineWidth = .7;
					for (const [x0, y0, x1, y1] of [[
						-2.5,
						-40.2,
						-1.2,
						-37.4
					], [
						-7,
						-41.3,
						-6.2,
						-39
					]]) {
						ctx.beginPath();
						ctx.moveTo(x0, y0);
						ctx.lineTo(x1, y1);
						ctx.stroke();
					}
					continue;
				}
				fill$1(ctx, c, () => {
					ctx.moveTo(s * 4, -36);
					ctx.quadraticCurveTo(s * 10, -41.5, s * 15.5, -38.5);
					ctx.quadraticCurveTo(s * 10.5, -37.5, s * 7.6, -33.4);
					ctx.closePath();
				});
				fill$1(ctx, c, () => {
					ctx.moveTo(s * 7.4, -31.6);
					ctx.quadraticCurveTo(s * 11.2, -33.6, s * 13.6, -30.6);
					ctx.quadraticCurveTo(s * 10.6, -30.6, s * 8.2, -29.4);
					ctx.closePath();
				});
				ctx.strokeStyle = dark(c, .28);
				ctx.lineWidth = .7;
				for (const [x0, y0, x1, y1] of [[
					8.4,
					-39.4,
					8.8,
					-36.4
				], [
					11.8,
					-39.9,
					11.6,
					-37.4
				]]) {
					ctx.beginPath();
					ctx.moveTo(s * x0, y0);
					ctx.lineTo(s * x1, y1);
					ctx.stroke();
				}
				continue;
			}
			if (view === "side") {
				if (s > 0) continue;
				const big = kind !== "small";
				const horn = (dx, dy) => {
					ctx.moveTo(3.2 + dx, -36.2 + dy);
					if (big) {
						ctx.quadraticCurveTo(5.5 + dx, -47 + dy, -6.5 + dx, -47.5 + dy);
						ctx.quadraticCurveTo(.8 + dx, -44 + dy, -.6 + dx, -37.4 + dy);
					} else {
						ctx.quadraticCurveTo(4.6 + dx, -42 + dy, .5 + dx, -44 + dy);
						ctx.quadraticCurveTo(2 + dx, -40.5 + dy, 0 + dx, -37 + dy);
					}
					ctx.closePath();
				};
				fill$1(ctx, dark(c, .25), () => horn(-3.2, .8));
				fill$1(ctx, c, () => horn(0, 0));
				continue;
			}
			if (kind === "small") fill$1(ctx, c, () => {
				ctx.moveTo(s * 3.5, -36);
				ctx.quadraticCurveTo(s * 6, -42, s * 9.5, -43);
				ctx.quadraticCurveTo(s * 7, -39, s * 6.5, -35.5);
				ctx.closePath();
			});
			else fill$1(ctx, c, () => {
				ctx.moveTo(s * 5, -35);
				ctx.quadraticCurveTo(s * 14, -38, s * 12, -47);
				ctx.quadraticCurveTo(s * 10.5, -41, s * 7.5, -38.5);
				ctx.quadraticCurveTo(s * 7, -36, s * 7, -33);
				ctx.closePath();
			});
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qHead.ts
	function headShape(ctx, look) {
		switch (look.face) {
			case "oval":
				ctx.ellipse(0, -29, 7.7, 9, 0, 0, TAU);
				break;
			case "square":
				ctx.roundRect(-8.3, -37.3, 16.6, 16.4, 4.6);
				break;
			case "heart":
				ctx.moveTo(0, -20.3);
				ctx.quadraticCurveTo(-8.7, -23.5, -8.6, -30);
				ctx.arc(0, -30, 8.6, Math.PI, 0);
				ctx.quadraticCurveTo(8.7, -23.5, 0, -20.3);
				ctx.closePath();
				break;
			default: ctx.arc(0, -29, 8.5, 0, TAU);
		}
	}
	function eyes(ctx, look, side, ex) {
		const col = look.eyes ?? "#1d1a22";
		const st = look.eyeStyle ?? "square";
		const xs = [];
		if (side === 0 || side === 1) xs.push(ex + 2.9);
		if (side === 0 || side === -1) xs.push(ex - 2.9);
		for (const x of xs) {
			if (st === "dot") fill$1(ctx, col, () => ctx.ellipse(x, -28.6, 1.15, 1.45, 0, 0, TAU));
			else if (st === "smile") {
				ctx.strokeStyle = col;
				ctx.lineWidth = 1.05;
				ctx.lineCap = "round";
				ctx.beginPath();
				ctx.arc(x, -27.7, 1.5, Math.PI * 1.15, Math.PI * 1.85);
				ctx.stroke();
			} else if (st === "big") {
				fill$1(ctx, col, () => ctx.roundRect(x - 1.3, -30.8, 2.6, 4, 1.2));
				fill$1(ctx, "#ffffff", () => ctx.arc(x - .45, -29.7, .6, 0, TAU));
			} else {
				ctx.fillStyle = col;
				ctx.fillRect(x - .9, -30, 1.8, 3);
			}
			if (look.lashes) {
				const o = x > ex ? 1 : -1;
				const up = st === "big" ? .6 : 0;
				ctx.strokeStyle = col;
				ctx.lineWidth = .65;
				ctx.lineCap = "round";
				ctx.beginPath();
				ctx.moveTo(x + o * .8, -30.3 - up);
				ctx.lineTo(x + o * 2, -31.3 - up);
				ctx.stroke();
			}
		}
	}
	function beard(ctx, look, side) {
		const st = look.beardStyle;
		if (!st || st === "full") return;
		const c = look.hairColor ?? "#5a3a22";
		const ex = side * 2.6;
		if (st === "short") {
			ctx.save();
			ctx.beginPath();
			headShape(ctx, look);
			ctx.clip();
			ctx.globalAlpha = .45;
			fill$1(ctx, c, () => {
				ctx.moveTo(ex - 6.9, -26);
				ctx.quadraticCurveTo(ex - 6, -20.6, ex, -20.4);
				ctx.quadraticCurveTo(ex + 6, -20.6, ex + 6.9, -26);
				ctx.quadraticCurveTo(ex, -23.4, ex - 6.9, -26);
			});
			ctx.restore();
		}
		if (st === "goatee") {
			fill$1(ctx, c, () => {
				ctx.moveTo(ex - 1.8, -23.6);
				ctx.lineTo(ex + 1.8, -23.6);
				ctx.lineTo(ex, -19.2);
				ctx.closePath();
			});
			fill$1(ctx, c, () => ctx.rect(ex - 1.8, -25.2, 3.6, .9));
		}
		if (st === "mustache") for (const s2 of side ? [1] : [-1, 1]) fill$1(ctx, c, () => {
			ctx.moveTo(ex, -25.6);
			ctx.quadraticCurveTo(ex + s2 * 2.8, -26.6, ex + s2 * 3.9, -24.1);
			ctx.quadraticCurveTo(ex + s2 * 2, -24.9, ex, -24.7);
			ctx.closePath();
		});
	}
	/** 頭後面的頭髮（側面長髮後片、馬尾、雙馬尾）：正面、側面畫在臉之前。 */
	function hairBehind(ctx, look, view, headgear) {
		if (!look.hair || look.hair === "none" || look.skull || view === "back" || headgear?.kind === "hood") return;
		const c = look.hairColor ?? "#5a3a22";
		const band = look.bunBand ?? "#d23c3c";
		const SD = view === "side";
		if (SD && look.hair === "long") fill$1(ctx, c, () => rr(ctx, -10, -32, 7.2, 14.5, 2.6));
		if (look.hair === "twin") for (const s2 of SD ? [-1] : [-1, 1]) {
			const x = SD ? -6.5 : s2 * 9.6;
			fill$1(ctx, c, () => {
				ctx.moveTo(x - 1.6, -32);
				ctx.quadraticCurveTo(x + s2 * 3.4, -26, x + s2 * 1.6, -17.5);
				ctx.quadraticCurveTo(x - s2 * .6, -21, x - s2 * 2, -27);
				ctx.closePath();
			});
			fill$1(ctx, band, () => ctx.arc(x, -30.6, 1.3, 0, TAU));
		}
		if (look.hair === "ponytail") {
			if (SD) {
				fill$1(ctx, c, () => {
					ctx.moveTo(-6, -34);
					ctx.quadraticCurveTo(-13.5, -32, -12, -20.5);
					ctx.quadraticCurveTo(-10, -26, -7, -28.5);
					ctx.closePath();
				});
				fill$1(ctx, band, () => ctx.arc(-7.4, -32.4, 1.3, 0, TAU));
			} else fill$1(ctx, c, () => {
				ctx.moveTo(6.5, -35);
				ctx.quadraticCurveTo(12.5, -31, 10.5, -21);
				ctx.quadraticCurveTo(9.5, -27, 6, -30);
				ctx.closePath();
			});
		}
	}
	/** 頭：正面照舊版；側面是側臉；背面整顆是頭髮。side：側面 1、正面背面 0。 */
	function drawQHead(ctx, look, view, side, head) {
		const skin = look.skin;
		const SD = view === "side";
		hairBehind(ctx, look, view, head);
		fill$1(ctx, skin, () => headShape(ctx, look));
		if (view === "back") {
			hair(ctx, look, "back", head);
			return;
		}
		if (SD) {
			fill$1(ctx, skin, () => ctx.ellipse(8.45, -27.1, 1.25, 1.05, 0, 0, TAU));
			fill$1(ctx, skin, () => ctx.ellipse(-1.2, -28.2, 1.7, 2.3, 0, 0, TAU));
			fill$1(ctx, mix(skin, "#000000", .18), () => ctx.ellipse(-1, -28.1, .7, 1.2, 0, 0, TAU));
		}
		const ex = side * 3.2;
		eyes(ctx, look, side, ex);
		ctx.fillStyle = "rgba(220,90,90,0.35)";
		if (SD) ctx.fillRect(3.4, -26.3, 2.2, 1.2);
		else {
			ctx.fillRect(ex - 5, -26.5, 2, 1.2);
			ctx.fillRect(ex + 3, -26.5, 2, 1.2);
		}
		raceFace(ctx, look.beardStyle ? {
			...look,
			beard: look.beardStyle === "full"
		} : look, SD ? "side" : view, side, SD && S$1.WEST);
		beard(ctx, look, side);
		hair(ctx, look, SD ? "side" : "front", head);
	}
	var COVERING = [
		"helmet",
		"hood",
		"wizard_hat",
		"horned_helm",
		"greathelm",
		"cap"
	];
	function hair(ctx, look, view, headgear) {
		if (!look.hair || look.hair === "none" || look.skull) return;
		const c = look.hairColor ?? "#5a3a22";
		const band = look.bunBand ?? "#d23c3c";
		const covered = !!headgear && COVERING.includes(headgear.kind);
		if (view === "back") {
			fill$1(ctx, c, () => {
				ctx.beginPath();
				ctx.arc(0, -29, 8.8, 0, TAU);
			});
			if (look.face === "square" || look.face === "heart") fill$1(ctx, c, () => {
				ctx.save();
				ctx.translate(0, -29);
				ctx.scale(1.04, 1.04);
				ctx.translate(0, 29);
				headShape(ctx, look);
				ctx.restore();
			});
			if (look.hair === "long") fill$1(ctx, c, () => rr(ctx, -7, -29, 14, 10, 3));
			if (look.hair === "bob") fill$1(ctx, c, () => rr(ctx, -8.8, -30, 17.6, 8.5, 3.5));
			if (look.hair === "ponytail" && headgear?.kind !== "hood") {
				fill$1(ctx, c, () => rr(ctx, -2, -32, 4, 17.5, 2));
				fill$1(ctx, band, () => rr(ctx, -2.3, -32, 4.6, 1.6, .8));
			}
			if (look.hair === "twin" && headgear?.kind !== "hood") for (const s2 of [-1, 1]) {
				fill$1(ctx, c, () => {
					ctx.moveTo(s2 * 8, -32);
					ctx.quadraticCurveTo(s2 * 13, -26, s2 * 11, -17.5);
					ctx.quadraticCurveTo(s2 * 9.5, -22, s2 * 6.5, -28);
					ctx.closePath();
				});
				fill$1(ctx, band, () => ctx.arc(s2 * 8.6, -30.8, 1.3, 0, TAU));
			}
			if (look.hair === "spiky" && !covered) fill$1(ctx, c, () => {
				for (let i = 0; i < 7; i++) {
					const a = Math.PI * (1.05 + i * .15);
					ctx.moveTo(Math.cos(a - .08) * 8.4, -29 + Math.sin(a - .08) * 8.4);
					ctx.lineTo(Math.cos(a) * 11.6, -29 + Math.sin(a) * 11.6);
					ctx.lineTo(Math.cos(a + .08) * 8.4, -29 + Math.sin(a + .08) * 8.4);
				}
			});
			if (look.hair === "bun" && !covered) fill$1(ctx, look.bunBand ?? c, () => ctx.arc(0, -37, 3, 0, TAU));
			return;
		}
		if (view === "side") {
			if (!covered) fill$1(ctx, c, () => {
				ctx.moveTo(8.3, -32.6);
				ctx.quadraticCurveTo(6.2, -38.8, -.8, -38.6);
				ctx.quadraticCurveTo(-9.4, -37.6, -9.3, -29.2);
				ctx.quadraticCurveTo(-9.2, -24, -6.4, -21.6);
				ctx.lineTo(-3.4, -22.6);
				ctx.quadraticCurveTo(-3.6, -27.5, -2.6, -31.2);
				ctx.quadraticCurveTo(2.5, -33.6, 6.2, -32.4);
				ctx.lineTo(7.4, -31.2);
				ctx.closePath();
			});
			if (covered) fill$1(ctx, c, () => {
				ctx.moveTo(-9.3, -29);
				ctx.quadraticCurveTo(-9.2, -24, -6.4, -21.6);
				ctx.lineTo(-3.4, -22.6);
				ctx.quadraticCurveTo(-4, -26, -4, -29);
				ctx.closePath();
			});
			if (look.hair === "long") fill$1(ctx, c, () => {
				ctx.moveTo(-3.4, -31);
				ctx.quadraticCurveTo(-1.5, -24, -3.2, -19.5);
				ctx.lineTo(-9.6, -19.5);
				ctx.lineTo(-9.4, -30);
				ctx.closePath();
			});
			if (look.hair === "bob") fill$1(ctx, c, () => {
				ctx.moveTo(-2.4, -31.5);
				ctx.quadraticCurveTo(-.6, -25.5, -1.8, -22);
				ctx.lineTo(-9.4, -22.4);
				ctx.lineTo(-9.4, -30);
				ctx.closePath();
			});
			if (look.hair === "spiky" && !covered) fill$1(ctx, c, () => {
				for (let i = 0; i < 6; i++) {
					const a = Math.PI * (1 + i * .13);
					ctx.moveTo(Math.cos(a - .09) * 8.6 - .8, -29.8 + Math.sin(a - .09) * 8.6);
					ctx.lineTo(Math.cos(a) * 12 - 1.6, -29.8 + Math.sin(a) * 12);
					ctx.lineTo(Math.cos(a + .09) * 8.6 - .8, -29.8 + Math.sin(a + .09) * 8.6);
				}
			});
			if (look.hair === "bun" && !covered) fill$1(ctx, look.bunBand ?? c, () => ctx.arc(-5.6, -36, 3, 0, TAU));
			if (look.hair === "twin" && headgear?.kind !== "hood") {
				fill$1(ctx, c, () => {
					ctx.moveTo(-7.6, -33);
					ctx.quadraticCurveTo(-14, -29, -12.4, -19);
					ctx.quadraticCurveTo(-10.6, -24, -8.2, -28.6);
					ctx.closePath();
				});
				fill$1(ctx, look.bunBand ?? "#d23c3c", () => ctx.arc(-8.4, -31.4, 1.4, 0, TAU));
			}
			return;
		}
		if (!covered && (look.face === "square" || look.face === "heart")) {
			ctx.save();
			ctx.beginPath();
			ctx.moveTo(12, -30.05);
			ctx.lineTo(8.78, -30.05);
			ctx.quadraticCurveTo(4, -33, 0, -32.5);
			ctx.quadraticCurveTo(-5, -32, -8.8, -29);
			ctx.lineTo(-12, -29);
			ctx.lineTo(-12, -46);
			ctx.lineTo(12, -46);
			ctx.closePath();
			ctx.clip();
			fill$1(ctx, c, () => {
				ctx.save();
				ctx.translate(0, -29);
				ctx.scale(1.04, 1.04);
				ctx.translate(0, 29);
				headShape(ctx, look);
				ctx.restore();
			});
			ctx.restore();
		}
		if (!covered) fill$1(ctx, c, () => {
			ctx.beginPath();
			ctx.arc(0, -29.5, 8.8, Math.PI * 1.02, Math.PI * 1.98);
			ctx.quadraticCurveTo(4, -33, 0, -32.5);
			ctx.quadraticCurveTo(-5, -32, -8.8, -29);
			ctx.closePath();
		});
		if (look.hair === "long") {
			fill$1(ctx, c, () => rr(ctx, -9.5, -31, 3, 11, 1.5));
			fill$1(ctx, c, () => rr(ctx, 6.5, -31, 3, 11, 1.5));
		}
		if (look.hair === "bob") {
			fill$1(ctx, c, () => rr(ctx, -9.6, -31.5, 3.4, 8.8, 1.7));
			fill$1(ctx, c, () => rr(ctx, 6.2, -31.5, 3.4, 8.8, 1.7));
		}
		if (look.hair === "spiky" && !covered) fill$1(ctx, c, () => {
			for (let i = 0; i < 7; i++) {
				const a = Math.PI * (1.05 + i * .15);
				ctx.moveTo(Math.cos(a - .09) * 8.6, -29.5 + Math.sin(a - .09) * 8.6);
				ctx.lineTo(Math.cos(a) * 11.8, -29.5 + Math.sin(a) * 11.8);
				ctx.lineTo(Math.cos(a + .09) * 8.6, -29.5 + Math.sin(a + .09) * 8.6);
			}
		});
		if (look.hair === "bun") fill$1(ctx, look.bunBand ?? c, () => {
			ctx.beginPath();
			ctx.arc(0, -37, 3, 0, TAU);
		});
	}
	/** 頭飾 × 四方向：正面照舊版；側面（朝東）各自轉成側面；背面看不到臉前的東西。12 種：兜帽、頭盔、角盔、巫師帽、便帽、頭巾、頭冠、寬帽、面紗、護目鏡、王冠、全罩盔。 */
	function drawQHeadgear(ctx, it, view) {
		if (!it) return;
		const [c, d] = colors(it);
		const SD = view === "side";
		const B = view === "back";
		switch (it.kind) {
			case "hood":
				if (SD) {
					ctx.fillStyle = c;
					ctx.beginPath();
					ctx.arc(-.6, -29.6, 10.2, 0, TAU);
					ctx.ellipse(4.4, -28.2, 4.6, 6.4, .12, 0, TAU);
					ctx.fill("evenodd");
					fill$1(ctx, c, () => {
						ctx.moveTo(-10.6, -29);
						ctx.quadraticCurveTo(-11, -22, -6, -20.6);
						ctx.lineTo(1, -21);
						ctx.lineTo(-3, -25);
						ctx.closePath();
					});
					ctx.strokeStyle = d;
					ctx.lineWidth = 1.2;
					ctx.beginPath();
					ctx.ellipse(4.4, -28.2, 4.6, 6.4, .12, -1.9, 1.9);
					ctx.stroke();
					break;
				}
				ctx.fillStyle = c;
				ctx.beginPath();
				ctx.arc(0, -29.5, 10, Math.PI * .85, Math.PI * 2.15);
				ctx.lineTo(9, -22);
				ctx.lineTo(-9, -22);
				ctx.closePath();
				if (!B) ctx.ellipse(0, -28, 6.5, 6, 0, 0, TAU);
				ctx.fill("evenodd");
				fill$1(ctx, d, () => ctx.rect(-9, -23, 18, 1.5));
				if (B) {
					ctx.strokeStyle = d;
					ctx.lineWidth = .8;
					ctx.beginPath();
					ctx.moveTo(0, -38);
					ctx.lineTo(0, -24);
					ctx.stroke();
				}
				break;
			case "helmet":
			case "horned_helm":
				if (SD) {
					fill$1(ctx, c, () => {
						ctx.moveTo(8.8, -31.6);
						ctx.quadraticCurveTo(8, -40.2, -.6, -40);
						ctx.quadraticCurveTo(-9.8, -39.4, -9.8, -29);
						ctx.lineTo(-9.4, -24.5);
						ctx.lineTo(-5, -25.5);
						ctx.lineTo(-4.5, -31.4);
						ctx.lineTo(8.8, -31.6);
						ctx.closePath();
					});
					fill$1(ctx, d, () => ctx.rect(-4.5, -32.6, 13.6, 1.2));
					fill$1(ctx, d, () => ctx.rect(8.2, -32.6, 1.6, 1.8));
					if (it.kind === "horned_helm") fill$1(ctx, "#e8d8b8", () => {
						ctx.moveTo(-2, -38);
						ctx.quadraticCurveTo(-6, -46, -11, -46);
						ctx.quadraticCurveTo(-6, -42, -4.5, -36.5);
						ctx.closePath();
					});
					break;
				}
				if (B) {
					fill$1(ctx, c, () => {
						ctx.beginPath();
						ctx.arc(0, -30, 9.4, Math.PI, 0);
						ctx.lineTo(9.4, -27);
						ctx.lineTo(-9.4, -27);
						ctx.closePath();
					});
					fill$1(ctx, d, () => ctx.rect(-9.4, -27.5, 18.8, 1.2));
					fill$1(ctx, c, () => rr(ctx, -8.6, -27, 17.2, 3, 1));
				} else {
					fill$1(ctx, c, () => {
						ctx.beginPath();
						ctx.arc(0, -31, 9.4, Math.PI, 0);
						ctx.lineTo(9.4, -25.5);
						ctx.lineTo(7.2, -25.5);
						ctx.lineTo(7.2, -31);
						ctx.lineTo(-7.2, -31);
						ctx.lineTo(-7.2, -25.5);
						ctx.lineTo(-9.4, -25.5);
						ctx.closePath();
					});
					fill$1(ctx, d, () => ctx.rect(-9.4, -32.2, 18.8, 1.2));
				}
				if (it.kind === "horned_helm") for (const s of [-1, 1]) fill$1(ctx, "#e8d8b8", () => {
					ctx.beginPath();
					ctx.moveTo(s * 8, -31);
					ctx.lineTo(s * 13, -40);
					ctx.lineTo(s * 10, -30);
					ctx.closePath();
				});
				break;
			case "wizard_hat":
				if (SD) {
					fill$1(ctx, c, () => ctx.ellipse(-.5, -34.2, 12.5, 2.6, -.04, 0, TAU));
					fill$1(ctx, c, () => {
						ctx.moveTo(-6.5, -35.5);
						ctx.lineTo(5.5, -35.5);
						ctx.quadraticCurveTo(1, -44, -6, -51);
						ctx.quadraticCurveTo(-4, -44, -6.5, -35.5);
						ctx.closePath();
					});
					fill$1(ctx, d, () => ctx.rect(-6.3, -37.2, 11.6, 1.4));
					break;
				}
				fill$1(ctx, c, () => {
					ctx.beginPath();
					ctx.moveTo(-12, -34);
					ctx.lineTo(12, -34);
					ctx.lineTo(3, -37);
					ctx.lineTo(2, -52);
					ctx.lineTo(-4, -37);
					ctx.closePath();
				});
				fill$1(ctx, d, () => ctx.rect(-6, -36.5, 12, 1.4));
				break;
			case "cap":
				if (SD) {
					fill$1(ctx, c, () => {
						ctx.moveTo(-9, -31);
						ctx.quadraticCurveTo(-8.6, -39.6, 0, -39.6);
						ctx.quadraticCurveTo(7.6, -39.4, 8.6, -32);
						ctx.closePath();
					});
					fill$1(ctx, d, () => rr(ctx, 4, -32.6, 9.2, 1.8, .9));
					break;
				}
				fill$1(ctx, c, () => {
					ctx.beginPath();
					ctx.arc(0, -31, 9, Math.PI, 0);
					ctx.closePath();
				});
				if (!B) fill$1(ctx, d, () => rr(ctx, -9.5, -32, 19, 1.6, .8));
				break;
			case "bandana":
				if (SD) {
					fill$1(ctx, c, () => {
						ctx.moveTo(-9, -30);
						ctx.quadraticCurveTo(-8.6, -39.6, 0, -39.6);
						ctx.quadraticCurveTo(7.6, -39.4, 8.4, -32.6);
						ctx.lineTo(-9, -30);
						ctx.closePath();
					});
					fill$1(ctx, c, () => {
						ctx.moveTo(-8.4, -31);
						ctx.lineTo(-13, -28);
						ctx.lineTo(-12, -25.5);
						ctx.lineTo(-8.2, -29);
						ctx.closePath();
					});
					fill$1(ctx, d, () => ctx.arc(-8.6, -30.6, 1.3, 0, TAU));
					break;
				}
				fill$1(ctx, c, () => {
					ctx.beginPath();
					ctx.arc(0, -31, 9, Math.PI, 0);
					ctx.closePath();
				});
				if (B) {
					fill$1(ctx, d, () => ctx.arc(0, -31.5, 1.6, 0, TAU));
					for (const s of [-1, 1]) fill$1(ctx, c, () => {
						ctx.moveTo(0, -31.5);
						ctx.lineTo(s * 3, -25);
						ctx.lineTo(s * 1, -24.6);
						ctx.closePath();
					});
				}
				break;
			case "circlet":
				if (SD) {
					fill$1(ctx, c, () => ctx.rect(-8.6, -34.6, 17, 1.6));
					fill$1(ctx, "#a898ff", () => {
						ctx.moveTo(8.6, -36.6);
						ctx.lineTo(9.8, -34);
						ctx.lineTo(8.6, -31.8);
						ctx.lineTo(7.6, -34);
						ctx.closePath();
					});
					break;
				}
				fill$1(ctx, c, () => rr(ctx, -9, -34, 18, 1.6, .8));
				if (!B) fill$1(ctx, "#a898ff", () => {
					ctx.beginPath();
					ctx.moveTo(0, -36.5);
					ctx.lineTo(1.8, -34);
					ctx.lineTo(0, -31.5);
					ctx.lineTo(-1.8, -34);
					ctx.closePath();
				});
				break;
			case "wide_hat":
				if (SD) {
					fill$1(ctx, c, () => ctx.ellipse(0, -34, 14.5, 2.4, 0, 0, TAU));
					fill$1(ctx, d, () => {
						ctx.arc(-.5, -35, 8, Math.PI, 0);
						ctx.closePath();
					});
					break;
				}
				fill$1(ctx, c, () => {
					ctx.beginPath();
					ctx.ellipse(0, -34, 14, 4, 0, 0, TAU);
				});
				fill$1(ctx, d, () => {
					ctx.beginPath();
					ctx.arc(0, -35, 8, Math.PI, 0);
					ctx.closePath();
				});
				break;
			case "veil":
				if (SD) {
					fill$1(ctx, c, () => {
						ctx.moveTo(2.8, -26.6);
						ctx.lineTo(9.4, -26.2);
						ctx.lineTo(8.6, -21);
						ctx.lineTo(3.6, -20.8);
						ctx.closePath();
					});
					ctx.strokeStyle = d;
					ctx.lineWidth = .6;
					ctx.beginPath();
					ctx.moveTo(2.8, -26.4);
					ctx.lineTo(-2, -28.4);
					ctx.stroke();
					break;
				}
				if (B) {
					ctx.strokeStyle = d;
					ctx.lineWidth = .7;
					ctx.beginPath();
					ctx.moveTo(-7.5, -26.5);
					ctx.lineTo(7.5, -26.5);
					ctx.stroke();
					break;
				}
				fill$1(ctx, c, () => rr(ctx, -9, -26, 18, 5, 2));
				break;
			case "goggles":
				if (SD) {
					ctx.strokeStyle = "#3a3a44";
					ctx.lineWidth = 1.2;
					ctx.beginPath();
					ctx.moveTo(6, -30);
					ctx.lineTo(-8.8, -30.6);
					ctx.stroke();
					fill$1(ctx, "#8d969f", () => ctx.ellipse(7.2, -29.5, 2, 2.6, 0, 0, TAU));
					fill$1(ctx, "rgba(160,220,255,0.7)", () => ctx.ellipse(7.8, -29.5, 1.2, 1.9, 0, 0, TAU));
					break;
				}
				if (B) {
					ctx.strokeStyle = "#3a3a44";
					ctx.lineWidth = 1.4;
					ctx.beginPath();
					ctx.moveTo(-8.8, -30);
					ctx.lineTo(8.8, -30);
					ctx.stroke();
					break;
				}
				for (const x of [-3, 3]) {
					fill$1(ctx, "#8d969f", () => {
						ctx.beginPath();
						ctx.ellipse(x, -29.5, 3, 2.6, 0, 0, TAU);
					});
					fill$1(ctx, "rgba(160,220,255,0.7)", () => {
						ctx.beginPath();
						ctx.ellipse(x, -29.5, 2.2, 1.9, 0, 0, TAU);
					});
				}
				break;
			case "crown":
				fill$1(ctx, c, () => rr(ctx, SD ? -6.6 : -7.4, -36, SD ? 13.2 : 14.8, 3, .8));
				for (const x of SD ? [
					-4.5,
					.5,
					5.5
				] : [
					-6,
					0,
					6
				]) fill$1(ctx, c, () => {
					ctx.moveTo(x - 1.6, -35.6);
					ctx.lineTo(x, -39.6);
					ctx.lineTo(x + 1.6, -35.6);
					ctx.closePath();
				});
				if (!B) fill$1(ctx, "#d23c3c", () => ctx.arc(SD ? 5 : 0, -34.5, 1, 0, TAU));
				break;
			case "greathelm":
				fill$1(ctx, c, () => rr(ctx, -9.6, -39.6, 19.2, 18.6, 4.5));
				if (SD) {
					fill$1(ctx, d, () => ctx.rect(4.6, -30.6, 5, 1.4));
					fill$1(ctx, d, () => ctx.rect(-9.6, -27, 19.2, 1));
				} else if (!B) {
					fill$1(ctx, d, () => ctx.rect(-6.5, -30.6, 13, 1.4));
					fill$1(ctx, d, () => ctx.rect(-.6, -30, 1.2, 6));
				}
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qAnimFB.ts
	/**
	* 五類（`fbk` 的值 1～5）＋QK-5b 借用的兩組（6、7；美術 PM QK-5 檢查第 2 題「不另出樣張，借最接近的一組」）：
	* `gun`＝弩、火槍借弓那組的舉起與放箭格（不拉弦：第 2～3 格持平，武器畫在持弓手上、指向目標）；
	* `cast`＝法球、自身／地面施放借法杖那組（杖頭往前那兩格改畫手上的武器；沒有主手武器就空手，副手法球照畫）。
	*/
	var FB_KINDS = [
		"sword",
		"spear",
		"bow",
		"staff",
		"gauntlet",
		"gun",
		"cast"
	];
	var fbKindOfIndex = (i) => FB_KINDS[Math.round(i) - 1] ?? null;
	var arm$1 = (who, L, x = {}) => ({
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
	var SWORD = {
		front: [
			{
				...IDLE_F,
				ops: [
					arm$1("o", "over"),
					arm$1("m", "over"),
					wpn("over", -.12, { wrap: true })
				]
			},
			{
				m: {
					h: [-13, -21.5],
					out: -1
				},
				o: {
					h: [12, -13],
					st: true
				},
				bob: -.4,
				ops: [
					arm$1("o", "over"),
					arm$1("m", "over"),
					wpn("over", -.05, { wrap: true })
				]
			},
			{
				m: {
					h: [-12, -29.5],
					out: -1
				},
				o: {
					h: [11.5, -15],
					st: true
				},
				bob: -.6,
				ops: [
					wpn("under", .8),
					arm$1("o", "over"),
					arm$1("m", "over"),
					wrapOp("over", .8)
				]
			},
			{
				m: {
					h: [-11, -25],
					out: -1
				},
				o: {
					h: [12, -14],
					st: true
				},
				bob: -.3,
				ops: [
					arm$1("o", "over"),
					arm$1("m", "over"),
					wpn("top", -.25, {
						s: .55,
						wd: 1.1,
						wrap: true
					})
				]
			},
			{
				m: {
					h: [-3, -14],
					st: true
				},
				o: {
					h: [12.5, -14],
					st: true
				},
				ops: [
					arm$1("o", "over"),
					arm$1("m", "top"),
					wpn("top", PI - .4, {
						s: .75,
						wd: 1.15,
						wrap: true
					})
				]
			},
			{
				m: {
					h: [-1.5, -13],
					out: "down"
				},
				o: {
					h: [12, -12],
					st: true
				},
				ops: [
					arm$1("o", "over"),
					arm$1("m", "top"),
					wpn("top", 2.25, {
						s: .95,
						wd: 1.05,
						wrap: true
					})
				]
			},
			{
				m: {
					h: [-11, -12],
					st: true
				},
				o: IDLE_F.o,
				ops: [
					arm$1("o", "over"),
					arm$1("m", "over"),
					wpn("over", -.5, { wrap: true })
				]
			}
		],
		back: lean([
			{
				...IDLE_B,
				ops: [
					wpn("under", .12),
					arm$1("o", "over"),
					arm$1("m", "over"),
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
					arm$1("o", "over"),
					arm$1("m", "over"),
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
					arm$1("o", "over"),
					arm$1("m", "over"),
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
					arm$1("o", "over"),
					wpn("over", .1, { s: .6 }),
					arm$1("m", "over"),
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
					arm$1("m", "over", { clip: "out" }),
					arm$1("o", "over")
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
					arm$1("m", "over", { clip: "out" }),
					arm$1("o", "over")
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
					arm$1("o", "over"),
					arm$1("m", "over"),
					wpn("over", .4, { clip: "hand" })
				]
			}
		])
	};
	var SPF = (Lf, hl, hw) => [
		arm$1("o", "over"),
		arm$1("m", "over"),
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
			arm$1("o", "under"),
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
			arm$1("m", "over"),
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
	var SPEAR = {
		front: [
			{
				m: {
					h: [-1, -17.5],
					out: -1
				},
				o: {
					h: [1.5, -13.3],
					out: 1
				},
				ops: SPF(14, 5, 6.5)
			},
			{
				m: {
					h: [-2.5, -19.5],
					out: -1
				},
				o: {
					h: [.5, -15.5],
					out: 1
				},
				bob: -.3,
				ops: SPF(11, 4.5, 6)
			},
			{
				m: {
					h: [-3, -20],
					out: -1
				},
				o: {
					h: [0, -16.3],
					out: 1
				},
				bob: -.5,
				ops: SPF(10, 4.3, 5.8)
			},
			{
				m: {
					h: [-.5, -16],
					st: true
				},
				o: {
					h: [1.5, -12],
					st: true
				},
				liftR: 1.5,
				ops: SPF(18, 6.2, 8.4)
			},
			{
				m: {
					h: [0, -15],
					st: true
				},
				o: {
					h: [2, -11.5],
					st: true
				},
				liftR: 1,
				ops: SPF(20, 7, 9.6)
			},
			{
				m: {
					h: [-.3, -15.5],
					st: true
				},
				o: {
					h: [1.8, -11.8],
					st: true
				},
				ops: SPF(18.5, 6.6, 9)
			},
			{
				m: {
					h: [-1, -17.5],
					out: -1
				},
				o: {
					h: [1.5, -13.3],
					out: 1
				},
				ops: SPF(14, 5, 6.5)
			}
		],
		back: lean([
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
		])
	};
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
		arm$1("o", "top"),
		bow("top", U, pull, nock, F),
		arm$1("m", "top")
	];
	var BB = (U, pull, nock, F, clipM = false) => [
		bow("under", U, pull, nock, F),
		arm$1("o", "over"),
		arm$1("m", "over", clipM ? { clip: "out" } : {})
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
					arm$1("o", "top"),
					bow("top", [-.3, .95], 0, false, [.62, .42]),
					arm$1("m", "over")
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
					arm$1("o", "over", { clip: "out" }),
					arm$1("m", "over", { clip: "out" })
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
					arm$1("o", "over", { clip: "out" }),
					arm$1("m", "over", { clip: "out" })
				]
			}
		])
	};
	var STF = (a, mg = 0) => [
		arm$1("o", "over"),
		arm$1("m", "over"),
		wpn("over", a, {
			mg,
			wrap: true
		})
	];
	var STB = (a, mg = 0) => [
		wpn("under", a, { mg }),
		arm$1("o", "over"),
		arm$1("m", "over")
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
					arm$1("o", "over"),
					arm$1("m", "over"),
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
					arm$1("o", "over"),
					arm$1("m", "over"),
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
					arm$1("o", "over"),
					arm$1("m", "over")
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
					arm$1("o", "over"),
					arm$1("m", "over")
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
	var oOut = arm$1("o", "over", { clip: "out" });
	var GAUNTLET = {
		front: [
			{
				...GD_F,
				ops: [arm$1("o", "over"), arm$1("m", "over")]
			},
			{
				m: {
					h: [-9.5, -12.5],
					out: "down"
				},
				o: GD_F.o,
				bob: -.2,
				ops: [arm$1("m", "over"), arm$1("o", "over")]
			},
			{
				m: {
					h: [-7, -15],
					out: "down"
				},
				o: GD_F.o,
				bob: -.3,
				ops: [arm$1("m", "over"), arm$1("o", "over")]
			},
			{
				m: {
					h: [-3.5, -16],
					st: true
				},
				o: {
					h: [5, -16.5],
					out: "down"
				},
				ops: [arm$1("o", "over"), arm$1("m", "top", { big: 1.4 })]
			},
			{
				m: {
					h: [-1.5, -13.5],
					st: true
				},
				o: {
					h: [5, -16.5],
					out: "down"
				},
				liftR: 1,
				ops: [arm$1("o", "over"), arm$1("m", "top", { big: 2 })]
			},
			{
				m: {
					h: [-2, -14],
					st: true
				},
				o: {
					h: [5, -16.5],
					out: "down"
				},
				ops: [arm$1("o", "over"), arm$1("m", "top", { big: 1.75 })]
			},
			{
				...GD_F,
				ops: [arm$1("o", "over"), arm$1("m", "over")]
			}
		],
		back: lean([
			{
				...GD_B,
				ops: [oOut, arm$1("m", "over", { clip: "out" })]
			},
			{
				m: {
					h: [9.8, -12],
					out: 1
				},
				o: GD_B.o,
				bob: -.2,
				ops: [oOut, arm$1("m", "over", { big: 1.1 })]
			},
			{
				m: {
					h: [9, -17],
					out: 1
				},
				o: GD_B.o,
				bob: -.3,
				ops: [oOut, arm$1("m", "over")]
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
				ops: [oOut, arm$1("m", "over")]
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
				ops: [oOut, arm$1("m", "over")]
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
				ops: [oOut, arm$1("m", "over")]
			},
			{
				...GD_B,
				ops: [oOut, arm$1("m", "over", { clip: "out" })]
			}
		])
	};
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
				arm$1("o", "top"),
				g,
				arm$1("m", i === 6 ? "over" : "top")
			] : [
				g,
				arm$1("o", "over", { clip: "out" }),
				arm$1("m", "over", { clip: "out" })
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
	var GUN = {
		front: gunOf("front"),
		back: gunOf("back")
	};
	/** 法杖那組換成手上的武器：杖頭往前（staffFS）那兩格改畫主手武器（同方向、縮短 0.55），其他格照法杖（武器用 w 畫）。 */
	function castOf(view) {
		return STAFF[view].map((f) => ({
			...f,
			ops: f.ops.map((o) => o.t === "staffFS" ? wpn(o.L, Math.atan2(o.d[0], -o.d[1]), { s: .55 }) : o)
		}));
	}
	var FB_CLIPS = {
		sword: SWORD,
		spear: SPEAR,
		bow: BOW,
		staff: STAFF,
		gauntlet: GAUNTLET,
		gun: GUN,
		cast: {
			front: castOf("front"),
			back: castOf("back")
		}
	};
	var lerp = (a, b, t) => a + (b - a) * t;
	var lerpP = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t)];
	/** 角度走最短的一邊。 */
	var lerpA = (a, b, t) => {
		let d = (b - a) % TAU;
		if (d > Math.PI) d -= TAU;
		if (d < -Math.PI) d += TAU;
		return a + d * t;
	};
	var sig = (ops) => ops.map((o) => `${o.t}:${o.L}:${"who" in o ? o.who : ""}:${"clip" in o ? o.clip ?? "" : ""}:${o.t === "spear" ? (o.d ? "d" : "") + (o.hand ? "h" : "") : ""}:${o.t === "bow" ? (o.F ? "F" : "") + (o.torso ? "t" : "") : ""}:${o.t === "wrap" ? String(o.a === "spA") : ""}:${o.t === "w" ? o.on ?? "" : ""}`).join("|");
	function lerpOp(a, b, t) {
		const out = { ...t < .5 ? a : b };
		const A = a;
		const B = b;
		for (const k of Object.keys(A)) {
			const x = A[k];
			const y = B[k];
			if (typeof x === "number" && typeof y === "number") out[k] = k === "a" ? lerpA(x, y, t) : lerp(x, y, t);
			else if (Array.isArray(x) && Array.isArray(y) && x.length === 2) out[k] = lerpP(x, y, t);
		}
		for (const k of [
			"s",
			"wd",
			"mg",
			"big"
		]) {
			const x = A[k];
			const y = B[k];
			if (typeof x === "number" || typeof y === "number") {
				const d = k === "mg" || k === "big" ? k === "big" ? 1 : 0 : 1;
				out[k] = lerp(typeof x === "number" ? x : d, typeof y === "number" ? y : d, t);
			}
		}
		return out;
	}
	function lerpHand(a, b, t) {
		const n = t < .5 ? a : b;
		const st = !!a.st === !!b.st ? !!a.st : !!n.st;
		return {
			h: lerpP(a.h, b.h, t),
			...st ? { st: true } : {},
			...n.out === void 0 ? {} : { out: n.out },
			...a.f !== void 0 || b.f !== void 0 ? { f: lerp(a.f ?? 1, b.f ?? 1, t) } : {}
		};
	}
	/** 這一類這一面在 `fbt`（0～6）的一格（相鄰兩幀內插）。 */
	function fbFrameAt(kind, view, fbt) {
		const fr = FB_CLIPS[kind][view];
		const u = Math.max(0, Math.min(6, Number.isFinite(fbt) ? fbt : 0));
		const i = Math.min(5, Math.floor(u));
		const t = u - i;
		const A = fr[i];
		const B = fr[i + 1];
		if (t <= 1e-6) return A;
		if (t >= 1 - 1e-6) return B;
		const ops = sig(A.ops) === sig(B.ops) ? A.ops.map((o, k) => lerpOp(o, B.ops[k], t)) : t < .5 ? A.ops : B.ops;
		const num = (k) => lerp(A[k] ?? 0, B[k] ?? 0, t);
		return {
			m: lerpHand(A.m, B.m, t),
			o: lerpHand(A.o, B.o, t),
			bob: num("bob"),
			liftL: num("liftL"),
			liftR: num("liftR"),
			glow: num("glow"),
			lean: num("lean"),
			ops
		};
	}
	/** 樣張 solve：打直（st）＝往鏡頭或往遠處時照距離縮短（不拉長）；否則 IK。 */
	function fbSolve(sx, s) {
		const UA = 5;
		const FA = 5.5;
		if (s.st) {
			const dx = s.h[0] - sx;
			const dy = s.h[1] + 20;
			const f = Math.min(1, Math.hypot(dx, dy) / 10.5);
			const len = [UA * f, FA * f];
			const sA = Math.atan2(-dx, dy);
			return {
				sx,
				sA,
				eA: 0,
				len,
				hand: fk(sx, sA, 0, len)
			};
		}
		const len = s.f ? [UA * s.f, FA * s.f] : null;
		const r = ik(sx, s.h, s.out ?? Math.sign(sx), len);
		return {
			sx,
			sA: r.sA,
			eA: r.eA,
			len,
			hand: fk(sx, r.sA, r.eA, len)
		};
	}
	var fbHands = (fr, view) => {
		const ms = view === "front" ? -8.5 : 8.5;
		return {
			m: fbSolve(ms, fr.m),
			o: fbSolve(-ms, fr.o)
		};
	};
	var SHAFT = "#6a4420";
	var COLLAR = "#8a6a2a";
	var TORSO = [
		-7.5,
		-21,
		15,
		13.5
	];
	var norm = (p) => {
		const l = Math.hypot(p[0] ?? 0, p[1] ?? 0) || 1;
		return [(p[0] ?? 0) / l, (p[1] ?? 0) / l];
	};
	var Mof = (a, s = 1, wd = 1) => s === 1 && wd === 1 ? null : [
		Math.cos(a) * wd,
		Math.sin(a) * wd,
		-Math.sin(a) * s,
		Math.cos(a) * s
	];
	function pole(c, R, d, Lf, Lb, w0, w1) {
		const n = [-d[1], d[0]];
		const B = [R[0] - d[0] * Lb, R[1] - d[1] * Lb];
		const T = [R[0] + d[0] * Lf, R[1] + d[1] * Lf];
		c.beginPath();
		c.moveTo(B[0] + n[0] * w0 / 2, B[1] + n[1] * w0 / 2);
		c.lineTo(T[0] + n[0] * w1 / 2, T[1] + n[1] * w1 / 2);
		c.lineTo(T[0] - n[0] * w1 / 2, T[1] - n[1] * w1 / 2);
		c.lineTo(B[0] - n[0] * w0 / 2, B[1] - n[1] * w0 / 2);
		c.closePath();
		c.fillStyle = SHAFT;
		c.fill();
		return T;
	}
	function spearHead(c, T, d, hl, hw, steel) {
		const n = [-d[1], d[0]];
		const P = [T[0] + d[0] * hl, T[1] + d[1] * hl];
		c.fillStyle = steel;
		c.beginPath();
		c.moveTo(P[0], P[1]);
		c.lineTo(T[0] + n[0] * hw / 2, T[1] + n[1] * hw / 2);
		c.lineTo(T[0] - n[0] * hw / 2, T[1] - n[1] * hw / 2);
		c.closePath();
		c.fill();
		c.fillStyle = "rgba(255,255,255,0.45)";
		c.beginPath();
		c.moveTo(P[0], P[1]);
		c.lineTo(T[0] + n[0] * hw * .12, T[1] + n[1] * hw * .12);
		c.lineTo(T[0] + n[0] * hw * .3, T[1] + n[1] * hw * .3);
		c.closePath();
		c.fill();
		c.fillStyle = COLLAR;
		const cw = hw * .62;
		c.beginPath();
		c.moveTo(T[0] + n[0] * cw / 2, T[1] + n[1] * cw / 2);
		c.lineTo(T[0] - n[0] * cw / 2, T[1] - n[1] * cw / 2);
		c.lineTo(T[0] - n[0] * cw / 2 - d[0] * 1.3, T[1] - n[1] * cw / 2 - d[1] * 1.3);
		c.lineTo(T[0] + n[0] * cw / 2 - d[0] * 1.3, T[1] + n[1] * cw / 2 - d[1] * 1.3);
		c.closePath();
		c.fill();
		return P;
	}
	function staffHead(c, P, sc, g, orb) {
		c.save();
		c.globalAlpha = .35 + .35 * g;
		c.fillStyle = orb;
		c.beginPath();
		c.arc(P[0], P[1], 5.2 * sc, 0, TAU);
		c.fill();
		c.restore();
		c.fillStyle = orb;
		c.beginPath();
		c.arc(P[0], P[1], 3.6 * sc, 0, TAU);
		c.fill();
		c.fillStyle = "rgba(255,255,255,0.8)";
		c.beginPath();
		c.arc(P[0] - 1.2 * sc, P[1] - 1.2 * sc, 1.1 * sc, 0, TAU);
		c.fill();
	}
	var spA = (H) => Math.atan2(H.o.hand[0] - H.m.hand[0], -(H.o.hand[1] - H.m.hand[1]));
	/** 一層：照 ops 依序畫（qDoll.drawBody 在 under、over、top 三個位置呼叫）。 */
	function drawFbLayer(api, fr, layer) {
		const c = api.ctx;
		const H = fbHands(fr, api.view);
		const steel = api.colors(api.main && api.main.kind === "spear" ? api.main : {
			slot: "main_hand",
			kind: "spear",
			material: "steel"
		})[0];
		const offFree = !fr.ops.some((o) => o.t === "bow" || o.t === "spear" || o.t === "wrap" && o.on === "o" || o.t === "w" && o.on === "o");
		if (offFree && layer === "under" && api.view === "back") api.offItem(H.o.hand, "under");
		for (const op of fr.ops) {
			if (op.L !== layer) continue;
			c.save();
			if ("clip" in op && op.clip === "out") {
				c.beginPath();
				c.rect(-80, -120, 160, 200);
				c.rect(TORSO[0], TORSO[1], TORSO[2], TORSO[3]);
				c.clip("evenodd");
			}
			if (op.t === "w" && op.clip === "hand") {
				const h = H.m.hand;
				c.beginPath();
				c.arc(h[0], h[1], 2.6, 0, TAU);
				c.clip();
			}
			switch (op.t) {
				case "arm": {
					const R = H[op.who];
					api.arm(R);
					if (op.big !== void 0 && op.big > 1) {
						const [x, y] = R.hand;
						c.save();
						c.beginPath();
						c.arc(x, y, 3.2 * op.big, 0, TAU);
						c.clip();
						c.translate(x, y);
						c.scale(op.big, op.big);
						c.translate(-x, -y);
						api.arm(R);
						c.restore();
					}
					if (op.who === "o" && offFree && api.view === "front") api.offItem(R.hand, layer);
					break;
				}
				case "w": {
					const h = H[op.on ?? "m"].hand;
					api.weapon(h, op.a, Mof(op.a, op.s ?? 1, op.wd ?? 1), op.mg ?? 0);
					if (op.wrap) api.wrap(h, op.a);
					break;
				}
				case "wrap":
					api.wrap(H[op.on].hand, op.a === "spA" ? spA(H) : op.a);
					break;
				case "spear": {
					const R = H.m.hand;
					const d = op.d ? norm(op.d) : norm([H.o.hand[0] - R[0], H.o.hand[1] - R[1]]);
					if (op.hand) {
						c.beginPath();
						c.arc(R[0], R[1], 2.6, 0, TAU);
						c.clip();
						pole(c, R, d, op.Lf, op.Lb, op.w0, op.w1);
					} else spearHead(c, pole(c, R, d, op.Lf, op.Lb, op.w0, op.w1), d, op.hl, op.hw, steel);
					break;
				}
				case "staffFS":
					staffHead(c, pole(c, H.m.hand, norm(op.d), op.Lf, op.Lb, op.w0, op.w1), op.sc, 1, staffOrbColor(api.main));
					break;
				case "bow": {
					const G = H.o.hand;
					const N = H.m.hand;
					const k = BOW_EY + op.pull;
					const F = op.F ?? [(G[0] - N[0]) / k, (G[1] - N[1]) / k];
					if (op.torso) {
						c.beginPath();
						c.rect(TORSO[0], TORSO[1], TORSO[2], TORSO[3]);
						c.clip();
					}
					api.bow(G, op.U, F, op.pull, op.nock);
					break;
				}
			}
			c.restore();
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qNpc.ts
	var BACK_PARTS = [
		"gourd",
		"puppet_box",
		"mailbag"
	];
	var dk = (c, t = .3) => mix(c, "#000000", t);
	/**
	* 資料 → qDoll 認得的 unit＋新部件（樣張 QNpc.prep；遊戲資料的寫法另外接：圍裙 waist apron、範本 robe 的 apron 色、
	* 霧行者 veil → 白兜帽＋白紗、傀儡線 puppet_cross、頭上 douli／headband／goggles_up、帽上 form goggles／goggles_up）。不改原物件。
	*/
	function npcPrep(unit0, pose, ww) {
		const look = { ...unit0.look };
		const gear = { ...unit0.gear };
		const parts = [];
		const P = (k, o = {}) => void parts.push({
			k,
			...o
		});
		const b = gear.body;
		if (b?.kind === "bare") {
			if (b.color) look.belt = b.color;
			gear.body = {
				kind: "bare",
				color: look.skin
			};
		} else if (b?.apron) {
			const { apron, ...rest } = b;
			gear.body = rest;
			P("apron", { color: apron });
		}
		const w = gear.waist;
		if (w?.kind === "apron") {
			P("apron", {
				color: w.color,
				edge: w.trim,
				pocket: w.material !== "leather"
			});
			delete gear.waist;
		} else if (w?.kind === "talismans") {
			P("talismans", { color: w.color });
			delete gear.waist;
		}
		if (gear.back && BACK_PARTS.includes(gear.back.kind)) {
			P(gear.back.kind, { color: gear.back.color });
			delete gear.back;
		}
		const h = gear.head;
		if (h?.kind === "veil" || h?.kind === "gauze") {
			P("gauze", { color: h.kind === "gauze" ? h.color : void 0 });
			gear.head = {
				kind: "hood",
				color: h.color ?? "#eef2f2"
			};
		} else if (h?.kind === "douli" || h?.kind === "headband") {
			P(h.kind, { color: h.color });
			delete gear.head;
		} else if (h?.kind === "goggles_up") {
			P("goggles_up");
			delete gear.head;
		} else if (h?.form === "goggles_up" || h?.form === "goggles") P(h.form, { cap: true });
		if (gear.cloak?.form === "feather") {
			gear.neck = {
				kind: "feathers",
				...gear.cloak.color ? { color: gear.cloak.color } : {}
			};
			delete gear.cloak;
		}
		const tassel = gear.main_hand?.tassel;
		if (tassel) P("tassel", { color: tassel });
		const skin = gear.hands && gear.hands.kind !== "bracers" ? null : look.skin;
		for (const slot of ["main_hand", "off_hand"]) {
			let it = gear[slot];
			if (!it) continue;
			if (it.kind === "puppet_cross") it = {
				...it,
				kind: "puppet_strings"
			};
			if (HELD_KINDS.includes(it.kind)) {
				gear[slot] = {
					...it,
					skin: it.skin ?? skin ?? "#f1c9a5"
				};
				if (it.kind === "puppet_strings") P("strings", { who: slot });
			}
		}
		const wms = {};
		let p2 = pose;
		if (parts.some((p) => p.k === "tassel" || p.k === "strings")) {
			const inner = pose?.probe;
			p2 = {
				...pose ?? {},
				probe: (kind, hand, tip, view, off, m, wkey) => {
					(wms[kind] ??= []).push(m);
					if (inner) inner(kind, hand, tip, view, off, m, wkey);
				}
			};
		}
		return {
			unit: {
				look,
				gear
			},
			parts,
			pose: p2,
			wms,
			ww
		};
	}
	/** 這隻需不需要外框之外的兩張離屏（白紗、傀儡線）。 */
	function npcNeedsLayers(unit) {
		const h = unit.gear.head?.kind;
		const held = (it) => it?.kind === "puppet_strings" || it?.kind === "puppet_cross";
		return h === "veil" || h === "gauze" || held(unit.gear.main_hand) || held(unit.gear.off_hand);
	}
	var LAYERS = null;
	/** qStamp 畫一隻時設好、畫完清掉。 */
	function setNpcLayers(l) {
		LAYERS = l;
	}
	function line$1(ctx, c, w, pts) {
		ctx.strokeStyle = c;
		ctx.lineWidth = w;
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		ctx.beginPath();
		pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
		ctx.stroke();
	}
	/** 頭下面的部件：挖掉頭。 */
	function headClip(ctx) {
		ctx.beginPath();
		ctx.rect(-80, -120, 160, 200);
		ctx.arc(0, -29, 8.7, 0, TAU);
		ctx.clip("evenodd");
	}
	function gourdShape(ctx, c) {
		fill$1(ctx, c, () => ctx.arc(0, 2.6, 3.4, 0, TAU));
		fill$1(ctx, c, () => ctx.arc(0, -2.4, 2.3, 0, TAU));
		fill$1(ctx, "#c0392b", () => ctx.roundRect(-1.8, -.6, 3.6, 1, .4));
		fill$1(ctx, "#6a4a2a", () => ctx.roundRect(-.8, -5.6, 1.6, 1.6, .4));
		fill$1(ctx, "rgba(255,255,255,0.35)", () => ctx.arc(-1.2, 1.6, .9, 0, TAU));
	}
	function bagShape(ctx, x, y, col, back = false) {
		const c = col ?? "#d8c8a0";
		fill$1(ctx, c, () => rr(ctx, x, y, 6, 5.6, 1.2));
		fill$1(ctx, dk(c, .25), () => rr(ctx, x, y, 6, 2.4, 1));
		if (!back) fill$1(ctx, "#2a2420", () => rr(ctx, x + 2.4, y + 1.8, 1.2, 1.4, .3));
	}
	function partBehind(ctx, v, p, W) {
		if (p.k === "gourd") {
			if (v === "back") return;
			ctx.save();
			if (v === "front") {
				ctx.translate(7.2, -24.6);
				ctx.rotate(.45);
			} else {
				ctx.translate(-8.4, -15);
				ctx.rotate(-.35);
			}
			gourdShape(ctx, p.color ?? "#c8903a");
			ctx.restore();
		} else if (p.k === "puppet_box") {
			const c = p.color ?? "#8a6a48";
			const [x, w, h] = v === "front" ? [
				-11.6,
				23.2,
				7
			] : v === "side" ? [
				-15,
				9.4,
				20
			] : [
				0,
				0,
				0
			];
			if (!w) return;
			fill$1(ctx, c, () => rr(ctx, x, -26, w, h, 1.2));
			fill$1(ctx, dk(c), () => ctx.rect(x, -26, w, 1.4));
			fill$1(ctx, "#c0392b", () => ctx.rect(x, -22.6, w, .9));
		} else if (p.k === "mailbag") {
			if (v === "front") bagShape(ctx, -12.6, -12.2, p.color, true);
			else if (v === "side" && W) bagShape(ctx, -11.2, -12.4, p.color, true);
		}
	}
	function apron(ctx, v, p) {
		const c = p.color ?? "#e8dcc0";
		const d = dk(c, .25);
		const e = p.edge ?? d;
		if (v === "front") {
			fill$1(ctx, e, () => {
				ctx.moveTo(-4.3, -19.2);
				ctx.lineTo(4.3, -19.2);
				ctx.lineTo(5.1, -11);
				ctx.lineTo(6.3, -2.4);
				ctx.lineTo(-6.3, -2.4);
				ctx.lineTo(-5.1, -11);
				ctx.closePath();
			});
			fill$1(ctx, c, () => {
				ctx.moveTo(-3.6, -18.6);
				ctx.lineTo(3.6, -18.6);
				ctx.lineTo(4.4, -11);
				ctx.lineTo(5.6, -3);
				ctx.lineTo(-5.6, -3);
				ctx.lineTo(-4.4, -11);
				ctx.closePath();
			});
			line$1(ctx, e, .7, [[-3.6, -18.8], [-2.6, -20.8]]);
			line$1(ctx, e, .7, [[3.6, -18.8], [2.6, -20.8]]);
			if (p.pocket !== false) fill$1(ctx, d, () => rr(ctx, -2.2, -8, 4.4, 2.6, .6));
		} else if (v === "side") {
			fill$1(ctx, e, () => {
				ctx.moveTo(4.1, -18.8);
				ctx.lineTo(5.6, -18.8);
				ctx.lineTo(6.3, -9.6);
				ctx.lineTo(6.9, -2.8);
				ctx.lineTo(5.2, -2.8);
				ctx.lineTo(4.6, -9.6);
				ctx.closePath();
			});
			fill$1(ctx, c, () => {
				ctx.moveTo(4.3, -18.4);
				ctx.lineTo(5.2, -18.4);
				ctx.lineTo(5.8, -9.6);
				ctx.lineTo(6.4, -3.2);
				ctx.lineTo(5.5, -3.2);
				ctx.lineTo(4.9, -9.6);
				ctx.closePath();
			});
			line$1(ctx, e, .6, [[-5, -9.4], [4.6, -9.4]]);
			line$1(ctx, e, .6, [[4.6, -18.6], [1.6, -21]]);
		} else {
			line$1(ctx, e, .7, [
				[-3, -20.8],
				[0, -21.6],
				[3, -20.8]
			]);
			line$1(ctx, e, .7, [[-5.4, -9.4], [5.4, -9.4]]);
			fill$1(ctx, e, () => ctx.ellipse(0, -9.4, 1.2, .8, 0, 0, TAU));
			line$1(ctx, e, .6, [[0, -9], [-.8, -6.4]]);
			line$1(ctx, e, .6, [[0, -9], [.9, -6.6]]);
		}
	}
	function douli(ctx, v, p) {
		const c = p.color ?? "#c8b07a";
		const d = dk(c, .22);
		if (v === "side") {
			fill$1(ctx, c, () => {
				ctx.moveTo(-12.6, -33.8);
				ctx.quadraticCurveTo(0, -36, 12.4, -32.8);
				ctx.lineTo(.8, -43.4);
				ctx.closePath();
			});
			line$1(ctx, d, .5, [[.8, -43], [-5.4, -34.8]]);
			line$1(ctx, d, .5, [[.8, -43], [6.6, -33.8]]);
			fill$1(ctx, d, () => rr(ctx, -8.6, -35.8, 16.8, 1.2, .6));
			return;
		}
		fill$1(ctx, c, () => {
			ctx.moveTo(-12.6, -33);
			ctx.quadraticCurveTo(0, -31.6, 12.6, -33);
			ctx.lineTo(0, -43.6);
			ctx.closePath();
		});
		for (const x of [
			-6.6,
			0,
			6.6
		]) line$1(ctx, d, .5, [[0, -43.2], [x, -32.4]]);
		line$1(ctx, d, .7, [[-12.6, -33], [12.6, -33]]);
		if (v === "front") {
			line$1(ctx, "#6a4a2a", .6, [[-6.4, -31.8], [-5.2, -24.6]]);
			line$1(ctx, "#6a4a2a", .6, [[6.4, -31.8], [5.2, -24.6]]);
		}
	}
	function headband(ctx, v, p) {
		const c = p.color ?? "#b8432f";
		const d = dk(c, .25);
		if (v === "side") {
			fill$1(ctx, c, () => {
				ctx.moveTo(8.6, -34.2);
				ctx.lineTo(8.9, -32.2);
				ctx.lineTo(-9.4, -31.4);
				ctx.lineTo(-9.2, -33.4);
				ctx.closePath();
			});
			fill$1(ctx, d, () => ctx.arc(-9.4, -32.4, 1.3, 0, TAU));
			fill$1(ctx, c, () => {
				ctx.moveTo(-9.6, -32);
				ctx.lineTo(-13.2, -27.4);
				ctx.lineTo(-11.6, -26.8);
				ctx.lineTo(-9, -31);
				ctx.closePath();
			});
			return;
		}
		fill$1(ctx, c, () => {
			ctx.moveTo(-8.9, -33.6);
			ctx.quadraticCurveTo(0, -35.4, 8.9, -33.6);
			ctx.lineTo(8.7, -31.6);
			ctx.quadraticCurveTo(0, -33.2, -8.7, -31.6);
			ctx.closePath();
		});
		if (v === "back") {
			fill$1(ctx, d, () => ctx.arc(0, -33.2, 1.4, 0, TAU));
			for (const s of [-1, 1]) fill$1(ctx, c, () => {
				ctx.moveTo(0, -33);
				ctx.lineTo(s * 2.6, -25.6);
				ctx.lineTo(s * .8, -25.2);
				ctx.closePath();
			});
		}
	}
	function goggles(ctx, v) {
		const st = "#3a3a44";
		if (v === "back") {
			line$1(ctx, st, 1.4, [[-8.8, -30], [8.8, -30]]);
			return;
		}
		if (v === "side") {
			line$1(ctx, st, 1.2, [[6, -30], [-8.8, -30.6]]);
			fill$1(ctx, "#8d969f", () => ctx.ellipse(7.2, -29.5, 2, 2.6, 0, 0, TAU));
			fill$1(ctx, "rgba(160,220,255,0.7)", () => ctx.ellipse(7.8, -29.5, 1.2, 1.9, 0, 0, TAU));
			return;
		}
		line$1(ctx, st, 1.3, [[-8.8, -29.6], [8.8, -29.6]]);
		for (const x of [-3, 3]) {
			fill$1(ctx, "#8d969f", () => ctx.ellipse(x, -29.5, 3, 2.6, 0, 0, TAU));
			fill$1(ctx, "rgba(160,220,255,0.7)", () => ctx.ellipse(x, -29.5, 2.2, 1.9, 0, 0, TAU));
		}
	}
	function gogglesUp(ctx, v, p) {
		const st = "#3a3a44";
		ctx.save();
		if (p.cap) ctx.translate(0, -1.6);
		if (v === "back") line$1(ctx, st, 1.3, [[-8.8, -33.6], [8.8, -33.6]]);
		else if (v === "side") {
			line$1(ctx, st, 1.2, [[6, -34.6], [-9, -33.4]]);
			fill$1(ctx, "#8d969f", () => ctx.ellipse(6.6, -35.4, 2, 2.2, 0, 0, TAU));
			fill$1(ctx, "rgba(160,220,255,0.85)", () => ctx.ellipse(7.2, -35.4, 1.1, 1.5, 0, 0, TAU));
		} else {
			line$1(ctx, st, 1.3, [[-8.8, -34.4], [8.8, -34.4]]);
			for (const x of [-3.2, 3.2]) {
				fill$1(ctx, "#8d969f", () => ctx.ellipse(x, -35, 2.8, 2.3, 0, 0, TAU));
				fill$1(ctx, "rgba(160,220,255,0.85)", () => ctx.ellipse(x, -35, 1.9, 1.5, 0, 0, TAU));
			}
		}
		ctx.restore();
	}
	function partFront(ctx, v, p, W) {
		switch (p.k) {
			case "apron":
				apron(ctx, v, p);
				break;
			case "gourd":
				if (v === "front") line$1(ctx, "#8a3a2a", .9, [[6.4, -20.8], [-5.6, -10]]);
				else if (v === "side") line$1(ctx, "#8a3a2a", .9, [[-1.6, -20.8], [4.6, -10.6]]);
				else {
					ctx.save();
					headClip(ctx);
					ctx.translate(-3.2, -13.6);
					ctx.rotate(-.42);
					gourdShape(ctx, p.color ?? "#c8903a");
					ctx.restore();
					line$1(ctx, "#8a3a2a", .9, [[-6.4, -20.8], [5.2, -9.6]]);
				}
				break;
			case "puppet_box": {
				const c = p.color ?? "#8a6a48";
				const d = dk(c);
				if (v === "back") {
					ctx.save();
					headClip(ctx);
					fill$1(ctx, c, () => rr(ctx, -9.6, -26, 19.2, 21, 1.2));
					fill$1(ctx, d, () => ctx.rect(-9.6, -26, 19.2, 1.4));
					fill$1(ctx, "#c0392b", () => ctx.rect(-9.6, -22.6, 19.2, .9));
					line$1(ctx, d, .7, [[0, -21.6], [0, -6]]);
					fill$1(ctx, "#e8bb48", () => ctx.arc(-1.3, -14, .7, 0, TAU));
					fill$1(ctx, "#e8bb48", () => ctx.arc(1.3, -14, .7, 0, TAU));
					ctx.restore();
				} else if (v === "front") for (const s of [-1, 1]) line$1(ctx, "#5a3a22", 1.1, [[s * 4.6, -21], [s * 4.8, -11]]);
				else line$1(ctx, "#5a3a22", 1.1, [[-.8, -21], [-.6, -11]]);
				break;
			}
			case "mailbag": {
				const s = "#6a4a2a";
				if (v === "front") line$1(ctx, s, 1.3, [[6.2, -20.6], [-6.4, -9.6]]);
				else if (v === "back") {
					line$1(ctx, s, 1.3, [[-6.2, -20.6], [4.6, -10]]);
					bagShape(ctx, 2.2, -12, p.color);
				} else if (!W) {
					line$1(ctx, s, 1.3, [[2.6, -20.8], [-3.6, -10.4]]);
					bagShape(ctx, -8.4, -12.2, p.color);
				} else line$1(ctx, s, 1.3, [[-1.6, -20.8], [4.8, -11]]);
				break;
			}
			case "talismans": {
				const c = p.color ?? "#f2d860";
				const xs = v === "front" ? [
					2.8,
					4.6,
					6.4
				] : v === "back" ? [
					-6.4,
					-4.6,
					-2.8
				] : W ? [
					-3.8,
					-2,
					-.2
				] : null;
				if (!xs) break;
				xs.forEach((x, i) => {
					const L = 5.6 - Math.abs(i - 1) * .9;
					fill$1(ctx, c, () => rr(ctx, x - .8, -8.4, 1.6, L, .3));
					if (v !== "back") line$1(ctx, "#c0392b", .4, [[x, -7.6], [x, -8.4 + L - 1]]);
				});
				break;
			}
			case "douli":
				douli(ctx, v, p);
				break;
			case "headband":
				headband(ctx, v, p);
				break;
			case "goggles":
				goggles(ctx, v);
				break;
			case "goggles_up": gogglesUp(ctx, v, p);
		}
	}
	/** 白紗面罩（霧行者）：qDoll 畫白兜帽，這裡加半透明面罩（眼睛以下）；背面看不到。不描外框。 */
	function gauze(ctx, v, p) {
		if (v === "back") return;
		ctx.save();
		ctx.globalAlpha = .78;
		const c = p.color ?? "#f4f6f6";
		if (v === "front") fill$1(ctx, c, () => {
			ctx.moveTo(-6.6, -26.6);
			ctx.lineTo(6.6, -26.6);
			ctx.quadraticCurveTo(6.4, -21.4, 0, -20.6);
			ctx.quadraticCurveTo(-6.4, -21.4, -6.6, -26.6);
			ctx.closePath();
		});
		else fill$1(ctx, c, () => {
			ctx.moveTo(1.6, -26.6);
			ctx.lineTo(9.8, -26.6);
			ctx.quadraticCurveTo(9.4, -22, 4.6, -20.8);
			ctx.lineTo(1.6, -22);
			ctx.closePath();
		});
		ctx.restore();
	}
	/** 在另一張離屏用同一個畫布座標畫（沒有離屏＝畫在本體上）。 */
	function onLayer(ctx, target, draw) {
		if (!target || target === ctx) {
			draw(ctx);
			return;
		}
		const m = getM(ctx);
		target.save();
		setM(target, m);
		draw(target);
		target.restore();
	}
	/** B 層：drawBody 一開始（體型、上下晃、側面前傾之後）畫。 */
	function npcBeforeQ(ctx, npc, view) {
		for (const p of npc.parts) partBehind(ctx, view, p, npc.ww);
	}
	/** C 層、劍穗、傀儡線、白紗：drawBody 最後畫。 */
	function npcAfterQ(ctx, npc, view) {
		if (npc.parts.length === 0) return;
		for (const p of npc.parts) partFront(ctx, view, p, npc.ww);
		const S = view === "side";
		const WW = npc.ww;
		const ts = npc.parts.find((p) => p.k === "tassel");
		const sw = ts ? npc.wms[npc.unit.gear.main_hand?.kind ?? ""]?.[0] : void 0;
		if (ts && sw) {
			const k = Math.sqrt(Math.abs(sw.a * sw.d - sw.b * sw.c));
			const [x, y] = tp(sw, 0, 2.2);
			ctx.save();
			ctx.setTransform(k, 0, 0, k, x, y);
			if (WW) ctx.globalCompositeOperation = "destination-over";
			const c = ts.color ?? "#c0392b";
			line$1(ctx, c, .6, [[0, 0], [.4, 2.6]]);
			fill$1(ctx, "#e8bb48", () => ctx.arc(.4, 2.8, .6, 0, TAU));
			fill$1(ctx, c, () => {
				ctx.moveTo(-.6, 3.2);
				ctx.lineTo(1.4, 3.2);
				ctx.lineTo(1.8, 6.6);
				ctx.lineTo(-1, 6.6);
				ctx.closePath();
			});
			ctx.restore();
		}
		for (const p of npc.parts.filter((q) => q.k === "strings")) {
			const both = npc.unit.gear.main_hand?.kind === "puppet_strings";
			const m = (npc.wms["puppet_strings"] ?? [])[p.who === "off_hand" && both ? 1 : 0];
			if (!m) continue;
			const far = S && p.who === "main_hand" === WW;
			const target = far ? LAYERS?.under : LAYERS?.over;
			const k = Math.sqrt(Math.abs(m.a * m.d - m.b * m.c));
			const tops = [
				[-4, 0],
				[4, 0],
				[0, 3.6]
			].map(([x, y]) => tp(m, x, y));
			const bot = Math.max(...tops.map((t) => t[1])) + 10 * k;
			const mx = tops.reduce((a, t) => a + t[0], 0) / 3;
			const draw = (c) => {
				c.save();
				c.setTransform(1, 0, 0, 1, 0, 0);
				if (!target && far) c.globalCompositeOperation = "destination-over";
				c.strokeStyle = "rgba(240,236,220,0.9)";
				c.lineWidth = .4 * k;
				for (const t of tops) {
					c.beginPath();
					c.moveTo(t[0], t[1]);
					c.lineTo(mx + (t[0] - mx) * .4, bot);
					c.stroke();
				}
				fill$1(c, "#c0392b", () => c.arc(mx, bot + .6 * k, .7 * k, 0, TAU));
				c.restore();
			};
			draw(target ?? ctx);
		}
		for (const p of npc.parts) if (p.k === "gauze") onLayer(ctx, LAYERS?.over, (c) => gauze(c, view, p));
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qDoll.ts
	/** 赤膊（QK-8）時手臂內線、拳頭邊、側面描邊的加深量（膚色＋0.23，和胸肌線同色）；其他時候 null＝照舊。 */
	var EDGEK = null;
	/** QK-3 檢查第 1 條：側面拿盾、彎肘的那隻手，長手套護套與臂環往肘那頭多包多少（袖口、臂環壓在鱗甲袖子上面露出來，盾照舊在最上層）。 */
	var HAND_LIFT = 0;
	/** QK-5：正面、背面五類出招這一格（qAnimFB）；null＝照原本的正面、背面畫法。 */
	var FB = null;
	var SHIELD_HAND_LIFT = 2.2;
	/** 副手拿法球、拂塵、符紙、傀儡線（QK-8：畫成對應物件，不是書）。法球沒指定顏色時照元素色（同原本 pdHeld 的副手法球）。 */
	var offHeld = (gear) => {
		const it = gear.off_hand;
		if (!isHeldOff(it)) return null;
		const tint = it.kind === "orb" && !it.color && it.element ? S$1.hooks?.tint(it.element) : void 0;
		return tint ? {
			...it,
			color: tint
		} : it;
	};
	/** inHand：在手的座標系畫手上的東西（畫在手掌上面，握把從拳頭上穿過）；handOnly：只畫手上的東西；len：[上臂, 前臂]。 */
	function arm(ctx, unit, x, shoulderA0, elbowA0, side, inHand = null, handOnly = false, len0 = null) {
		let shoulderA = shoulderA0;
		let elbowA = elbowA0;
		let len = len0;
		let SO = 0;
		let SOd = 0;
		const A = ARM();
		if (A.sideOne && side && elbowA && Math.abs(elbowA) <= .15) {
			const u0 = len ? len[0] ?? 5 : 5;
			const f0 = len ? len[1] ?? 5.5 : FA;
			const r = Math.hypot(f0 * Math.sin(elbowA), u0 + f0 * Math.cos(elbowA));
			SO = elbowA;
			SOd = Math.atan2(f0 * Math.sin(elbowA), u0 + f0 * Math.cos(elbowA));
			shoulderA += SOd;
			len = [u0 * r / (u0 + f0), f0 * r / (u0 + f0)];
			elbowA = 0;
		}
		const { look, gear } = unit;
		const it = gear.body;
		const kind = it?.kind ?? "shirt";
		const [c0] = colors(it);
		const c = S$1.FAR ? mix(c0, "#000000", S$1.FAR) : c0;
		const sleeve = S$1.TINT ?? (S$1.SEAMIN ? mix(c, "#000000", .15) : c);
		const ua = len ? len[0] ?? 5 : 5;
		const fa = len ? len[1] ?? 5.5 : FA;
		const hy = -20 + ua + fa;
		const hc = gear.hands ? colors(gear.hands)[0] : look.skin;
		const seam = (path) => {
			if (!S$1.SEAM || S$1.TINT || handOnly) return;
			if (S$1.SEAMIN) {
				ctx.save();
				ctx.beginPath();
				path();
				ctx.clip();
				ctx.strokeStyle = mix(c, "#000000", .5);
				ctx.lineWidth = 1.6;
				ctx.beginPath();
				path();
				ctx.stroke();
				ctx.restore();
				return;
			}
			ctx.strokeStyle = mix(c, "#000000", EDGEK ?? .38);
			ctx.lineWidth = EDGEK ? .9 : .55;
			ctx.beginPath();
			path();
			ctx.stroke();
		};
		const pad = () => {
			if (!S$1.NOPAD && kind === "plate" && it?.form !== "half") fill$1(ctx, mix(c, "#ffffff", .25), () => ctx.ellipse(x, -19.5, 3.5, 2.5, 0, 0, TAU));
		};
		ctx.save();
		rotAt(ctx, x, -20, shoulderA);
		if (!handOnly) fill$1(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, ua + 1, 2));
		const ONE = S$1.SEAM && !S$1.SEAMIN && (!side || !!A.sideOne) && !elbowA;
		if (!(S$1.SEAMIN && !elbowA) && !ONE) seam(() => ctx.roundRect(x - 2, -21, 4, ua + 1, 2));
		if (!handOnly) pad();
		rotAt(ctx, x, -20 + ua, elbowA);
		if (!handOnly) fill$1(ctx, sleeve, () => rr(ctx, x - 2, -20.5 + ua, 4, fa, 2));
		const free = (S$1.FILLARM || S$1.FREEARM) && !side && !elbowA;
		if (!handOnly && free) fill$1(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, ua + fa + .5, 2));
		if (!handOnly && free && !S$1.SEAM && !S$1.TINT && A.edge) armEdge(ctx, sleeve, x, ua + fa + .5);
		if (ONE) {
			if (!handOnly && !S$1.TINT) {
				fill$1(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, ua + fa + .5, 2));
				seam(() => ctx.roundRect(x - 2, -21, 4, ua + fa + .5, 2));
				pad();
			}
		} else if (!(S$1.SEAMIN && !elbowA)) seam(() => ctx.roundRect(x - 2, -20.5 + ua, 4, fa, 2));
		else if (!handOnly && !S$1.TINT) {
			seam(() => ctx.roundRect(x - 2, -21, 4, ua + fa + .5, 2));
			pad();
		}
		if (!handOnly && gear.hands && gear.hands.kind === "bracers" && !isRingBracer(gear.hands)) {
			const [bc, bd] = colors(gear.hands);
			fill$1(ctx, S$1.TINT ?? bc, () => rr(ctx, x - 2.3, hy - 3.1, 4.6, 2.4, .8));
			fill$1(ctx, S$1.TINT ?? bd, () => ctx.rect(x - 2.3, hy - 1.7, 4.6, .6));
		}
		const k0 = gear.hands && gear.hands.kind !== "bracers" ? hc : look.skin;
		const fistC = S$1.TINT ?? (S$1.FARH ? mix(k0, "#000000", S$1.FARH) : k0);
		if (!handOnly && !S$1.TINT) handFormUnder(ctx, gear.hands, x, hy);
		if (!handOnly) fill$1(ctx, fistC, () => ctx.arc(x, hy, 2.4, 0, TAU));
		const gauntlet = qWeapon(gear.main_hand)?.kind === "gauntlet";
		const ringEdge = free && !S$1.SEAM && !!A.edge?.fist && !gauntlet;
		if (!handOnly && ringEdge && !S$1.TINT) fistEdge(ctx, sleeve, fistC, x, hy, ua, fa);
		if (!handOnly && !S$1.TINT) handFormOver(ctx, gear.hands, look.skin, x, hy, (k) => S$1.FARH ? mix(k, "#000000", S$1.FARH) : k, ringEdge ? (k) => fistEdge(ctx, sleeve, k, x, hy, ua, fa) : null, side && elbowA ? HAND_LIFT : 0);
		if (!handOnly && !S$1.TINT && gauntlet && gear.main_hand) glove(ctx, gear.main_hand, x, hy);
		rotAt(ctx, x, hy, SO - SOd);
		if (inHand) inHand([x, hy], ctx);
		ctx.restore();
		return [x, hy];
	}
	/** 布料類空手的手臂：沿「上臂＋前臂合成的一條」描邊（inner＝只畫靠身體那側），clip 在手臂裡（輪廓不變寬）。 */
	function armEdge(ctx, sleeve, x, h) {
		const e = ARM().edge;
		ctx.save();
		ctx.beginPath();
		ctx.roundRect(x - 2, -21, 4, h, 2);
		ctx.clip();
		if (e.mode === "inner") {
			ctx.beginPath();
			if (x > 0) ctx.rect(x - 2.5, -22, 2.5, h + 2);
			else ctx.rect(x, -22, 2.5, h + 2);
			ctx.clip();
		}
		ctx.strokeStyle = mix(sleeve, "#000000", EDGEK ?? e.k);
		ctx.lineWidth = e.w;
		ctx.beginPath();
		ctx.roundRect(x - 2, -21, 4, h, 2);
		ctx.stroke();
		ctx.restore();
	}
	/** 空手的拳頭一圈深色邊（ring），clip 在拳頭圓裡。 */
	function fistEdge(ctx, sleeve, fistC, x, hy, ua, fa) {
		const f = ARM().edge.fist;
		ctx.save();
		ctx.beginPath();
		ctx.arc(x, hy, 2.4, 0, TAU);
		ctx.clip();
		if (f.mode === "seam") {
			ctx.beginPath();
			ctx.roundRect(x - 2, -20.5 + ua, 4, fa, 2);
			ctx.clip();
		}
		ctx.strokeStyle = mix(f.mode === "seam" ? sleeve : fistC, "#000000", EDGEK ?? f.k);
		ctx.lineWidth = f.w;
		ctx.beginPath();
		ctx.arc(x, hy, 2.4, 0, TAU);
		ctx.stroke();
		ctx.restore();
	}
	/** 拳套（第 8 版）：包住拳頭、前臂那頭護腕、指節板。 */
	function glove(ctx, it, x, y) {
		const [k, d] = it.color || it.material ? colors(it) : S$1.hooks.colors({
			kind: it.kind,
			material: "steel",
			...it.element ? { element: it.element } : {}
		});
		fill$1(ctx, d, () => rr(ctx, x - 2.7, y - 4.4, 5.4, 2.4, .8));
		fill$1(ctx, k, () => ctx.arc(x, y, 2.9, 0, TAU));
		fill$1(ctx, d, () => rr(ctx, x - 2.5, y + 1, 5, 1.3, .6));
		fill$1(ctx, "rgba(255,255,255,0.35)", () => ctx.arc(x - 1, y - .8, .9, 0, TAU));
	}
	/** 背面持盾的左手臂：打直往外下方，前臂套臂帶，拳頭握盾背正中央的握把；前臂與手外面一圈深色輪廓和盾緣分開。 */
	function shieldArmBack(ctx, unit) {
		S$1.TINT = S$1.POSE?.tintOff ?? null;
		const k = {
			sA: OUTA(),
			eA: 0
		};
		const sx = -SHX();
		const h = fk(sx, k.sA, k.eA);
		const strap = "#3a2414";
		if (!S$1.TINT) {
			ctx.save();
			rotAt(ctx, sx, -20, k.sA);
			fill$1(ctx, Q_OUT, () => rr(ctx, sx - 2.45, -15.9, 4.9, FA + .8, 2.4));
			ctx.restore();
			fill$1(ctx, Q_OUT, () => ctx.arc(h[0], h[1], 2.85, 0, TAU));
			ctx.save();
			ctx.translate(h[0], h[1]);
			ctx.rotate(k.sA);
			fill$1(ctx, strap, () => rr(ctx, -4.4, -.8, 8.8, 1.6, .6));
			ctx.restore();
		}
		S$1.EBOFF = true;
		arm(ctx, unit, sx, k.sA, k.eA, 0, rec("off"));
		S$1.EBOFF = false;
		if (!S$1.TINT) {
			const hc = unit.gear.hands && unit.gear.hands.kind !== "bracers" ? colors(unit.gear.hands)[0] : unit.look.skin;
			ctx.save();
			ctx.translate(h[0], h[1]);
			ctx.rotate(k.sA);
			fill$1(ctx, mix(hc, "#000000", .1), () => rr(ctx, -2.1, .2, 4.2, 1.9, .9));
			ctx.strokeStyle = mix(hc, "#000000", .45);
			ctx.lineWidth = .32;
			ctx.beginPath();
			for (const xx of [
				-1.05,
				0,
				1.05
			]) {
				ctx.moveTo(xx, .35);
				ctx.lineTo(xx, 1.95);
			}
			ctx.moveTo(-2, .2);
			ctx.lineTo(2, .2);
			ctx.stroke();
			ctx.restore();
		}
		S$1.TINT = null;
		const m = fk(sx, k.sA, 0, [6.6, 0]);
		ctx.save();
		ctx.translate(m[0], m[1]);
		ctx.rotate(k.sA);
		fill$1(ctx, strap, () => rr(ctx, -2.6, -.75, 5.2, 1.5, .5));
		ctx.restore();
	}
	var CLASS_OF = {
		greatsword: "greatsword",
		spear: "polearm",
		scythe: "polearm",
		bow: "bow",
		crossbow: "gun",
		gun: "gun",
		staff: "staff"
	};
	var SSH = 2;
	/** QK-1c：拄劍、待機的雙手劍遠側暗袖子——暗度與上臂、前臂長度（肩到拳頭距離的倍數，> 0.5 才會往下垂出手肘）。 */
	var GS_SLEEVE_DARK = .2;
	var GS_SLEEVE_SAG = .75;
	var tailG = (T, hw, a, hy) => T - (.85 - hy - hw * Math.sin(a)) / Math.cos(a);
	var tiltG = (mg) => mg;
	/** 雙手劈：從拄劍把劍提起來 → 舉到臉前上方 → 往前下方劈；朝東、朝西同一組（第 17 版）。 */
	var GS_ATK = {
		from: {
			hand: [11, -15.5],
			a: .8
		},
		mid: {
			hand: [13.4, -24.4],
			a: .45
		},
		to: {
			hand: [10.5, -12],
			a: 1.9,
			elbow: 1
		},
		og: [0, 6.8],
		mg: 1.2
	};
	/** 關鍵姿勢表（依目前的手臂規則算；手臂規則換了就重算）。 */
	function buildKey() {
		const OH = fk(SHX(), -OUTA(), 0);
		const OH16 = fk(8.5, -ARM_SPREAD_SET.A.a, 0);
		const SHD = fk(SSH, -.87, 0);
		const SHP = fk(SSH, -1.07, 0);
		const sideW = fk(SSH, -1, 0);
		return {
			greatsword: {
				zh: "拄劍：雙手疊握劍柄在胸前，劍垂直往下，劍尖點在兩腳之間",
				front: {
					hand: [-.5, -13.4],
					a: Math.PI,
					og: [0, 3.2],
					short: "f"
				},
				back: {
					hand: [.5, -13.4],
					a: Math.PI,
					og: [0, 3.2],
					short: "f"
				},
				side: {
					hand: [7.4, -15.8],
					a: Math.PI + .06,
					og: [0, 4],
					short: true
				},
				sideW: {
					hand: [7.2, -19.8],
					a: Math.PI + .06,
					og: [0, 0],
					mg: 4,
					short: true
				},
				atk: GS_ATK
			},
			polearm: {
				zh: "右手單手拄地、手臂打直往外、柄直立，左手垂下",
				front: {
					hand: [-OH[0], OH[1]],
					a: 0,
					grip: tiltG(-2.6 + OH[1] + 12.8),
					gripS: tiltG(-4.6 + OH[1] + 12.8),
					flipS: true,
					st: true
				},
				back: {
					hand: [OH[0], OH[1]],
					a: 0,
					grip: tiltG(-2.6 + OH[1] + 12.8),
					gripS: tiltG(-4.6 + OH[1] + 12.8),
					st: true
				},
				side: {
					hand: SHP,
					a: .06,
					grip: tailG(11, .9, .06, SHP[1]),
					gripS: tailG(9, 1, .06, SHP[1]),
					animOg: [0, -8],
					st: true
				},
				atk: {
					from: {
						hand: [2, -14],
						a: 1.25
					},
					to: {
						hand: [6, -17.5],
						a: Math.PI / 2 + .03
					},
					og: [0, -6]
				},
				atkScythe: {
					from: {
						hand: [7, -15],
						a: .45
					},
					to: {
						hand: [5, -17],
						a: 2
					},
					og: [0, -6]
				}
			},
			bow: {
				zh: "持弓待機：弓在胸口前、靠中線，左手握弓把、右手扣弦上的箭尾，箭朝前下；背面弓和兩手被身體擋住",
				front: {
					wh: "off",
					hand: [3, -11.5],
					s: [-1.1, -14.6],
					tilt: .72,
					nt: 1.9,
					ah: 4.2,
					a: 0
				},
				back: {
					wh: "off",
					hand: [-3, -11.5],
					s: [1.1, -14.6],
					tilt: .72,
					nt: 1.9,
					ah: 4.2,
					a: 0
				},
				side: {
					hand: [11.6, -12.6],
					a: Math.PI / 2 + .6,
					farX: 5.4
				},
				aim: {
					hand: [16.6, -21.5],
					a: Math.PI / 2,
					farX: 6.4,
					nearX: -1.5,
					edir: [-1, -.3]
				}
			},
			gun: {
				zh: "正面橫持在胸前、口朝右下；背面口從左腰外露出；側面持槍待命、口朝前上",
				front: {
					hand: [-3, -15],
					a: 1.87,
					og: [0, -6.8]
				},
				back: {
					hand: [3, -15],
					a: -1.87,
					og: [0, -6.8]
				},
				backX: {
					hand: [1, -15.5],
					a: 0,
					og: [0, -6.8],
					fore: [
						1.35,
						0,
						.25,
						-.3
					]
				},
				side: {
					hand: [6, -11],
					a: .9,
					og: [0, -5]
				},
				atk: {
					from: {
						hand: [6, -11],
						a: .9
					},
					to: {
						hand: [11, -20],
						a: Math.PI / 2,
						farX: 6.5,
						elbow: "down"
					},
					og: [0, -5]
				}
			},
			staff: {
				zh: "單手握杖：手臂打直往外下方伸、杖身穿過拳頭；正面杖在畫面左、背面在畫面右；側面杖往前傾",
				front: {
					hand: [-OH[0], OH[1]],
					a: 0,
					grip: tiltG(-3.72 + (OH[1] - OH16[1])),
					st: true
				},
				back: {
					hand: [OH[0], OH[1]],
					a: 0,
					grip: tiltG(-3.72 + (OH[1] - OH16[1])),
					st: true
				},
				side: {
					hand: SHD,
					a: .2,
					aW: .2,
					grip: tailG(9, 1.1, .2, SHD[1]),
					gripW: tailG(9, 1.1, .2, SHD[1]),
					st: true
				},
				sideW: {
					hand: sideW,
					a: .2,
					mg: tailG(9, 1.1, .2, sideW[1]),
					needOff: true,
					st: true
				}
			}
		};
	}
	var KEYS = /* @__PURE__ */ new Map();
	function KEY() {
		const a = ARM();
		let k = KEYS.get(a);
		if (k === void 0) {
			k = buildKey();
			KEYS.set(a, k);
		}
		return k;
	}
	function keyOf(gear) {
		const q = qWeapon(gear.main_hand);
		if (!q) return null;
		const c = CLASS_OF[q.kind];
		if (!c) return null;
		if (c !== "staff" && gear.off_hand) return null;
		return {
			c,
			K: KEY()[c],
			kind: q.kind
		};
	}
	var backKey = (key) => key ? key.kind === "crossbow" && key.K.backX ? key.K.backX : key.K.back : null;
	var ogLocal = (og) => og && og !== "string" ? [og[0] ?? 0, og[1] ?? 0] : og === "string" ? [0, BOW_EY] : null;
	var armTo = (sx, hand, out) => ik(sx, hand, out);
	/** 持單手武器的手臂往外張開的角度；空手、拳套用最小可見縫 ea。 */
	var outOf = (gear) => {
		const q = qWeapon(gear.main_hand);
		return gear.main_hand && q && q.kind !== "gauntlet" ? OUTA() : SEAMF() ? ARM().ea ?? 0 : 0;
	};
	var armK = (sx, k, out) => k.st ? {
		sA: Math.atan2(-((k.hand[0] ?? 0) - sx), (k.hand[1] ?? 0) + 20),
		eA: 0
	} : armTo(sx, k.hand, out);
	var sxOf = (gear) => outOf(gear) ? SHX() : 8.5;
	var robeX = (gear) => ARM().robe && gear.body?.kind === "robe" ? ARM().robe : 0;
	var SWORDISH = [
		"sword",
		"arcane_blade",
		"saber"
	];
	var swOn = (gear) => SWORDISH.includes(qWeapon(gear.main_hand)?.kind ?? "");
	var swOff = (p, s, gear) => ARM().sw && swOn(gear) ? [p[0] + s * ARM().sw, p[1]] : p;
	var holdA = (gear) => outOf(gear) ? outOf(gear) + ARM().hold + robeX(gear) : 0;
	var stK = (sx, k, out, gear) => {
		const r = armK(sx, k, out);
		if (k.st && robeX(gear)) r.sA += (sx > 0 ? -1 : 1) * robeX(gear);
		return r;
	};
	var stMg = (sx, k, k0, mg, gear) => k.st && robeX(gear) ? mg + (fk(sx, k0.sA, k0.eA)[1] - (k.hand[1] ?? 0)) / Math.cos(k.a) : mg;
	var holdOf = (it, which) => {
		const q = qWeapon(it);
		return q ? q.W.hold[which] : which === "side" ? .75 : -.25;
	};
	/** 弓手預設背箭袋。 */
	var backOf = (gear) => gear.back ?? (qWeapon(gear.main_hand)?.kind === "bow" ? {
		slot: "back",
		kind: "quiver",
		material: "leather"
	} : null);
	/** 四指握法的武器（QK-1 第 0.3 節第 2 點單手劍；QK-1b 加匕首、成對武器，鞭不改）→ 握柄寬、顏色。 */
	var GRIP = {
		sword: [2, "#4a3020"],
		arcane_blade: [2, "#4a3020"],
		saber: [2, "#3a2a1a"],
		dagger: [1.6, "#4a3020"],
		paired: [1.6, "#4a3020"]
	};
	var gripOf = (gear) => GRIP[qWeapon(gear.main_hand)?.kind ?? ""] ?? null;
	/**
	* 四指握法：四指橫過握把，握柄從拳頭上下穿出（柄尾從拳頭下緣露出來）。
	* wpos＝武器原點（正面、背面單手劍往外偏 sw）；clipR＝四指只畫在拳頭輪廓裡（伸到身前的遠側手）。
	*/
	function swordGrip(ctx, unit, hand, a, wpos = hand, clipR = 0) {
		const g = gripOf(unit.gear);
		if (!g) return;
		ctx.save();
		ctx.translate(wpos[0], wpos[1]);
		ctx.rotate(a);
		fill$1(ctx, g[1], () => ctx.rect(-g[0] / 2, 1, g[0], 2.9));
		ctx.restore();
		ctx.save();
		if (clipR) {
			ctx.beginPath();
			ctx.arc(hand[0], hand[1], clipR, 0, TAU);
			ctx.clip();
		}
		wrap(ctx, unit, hand, a);
		ctx.restore();
	}
	/** 側面走路（擺髖、沒有出招姿勢）。 */
	var walkingSide = (anim) => !anim && typeof S$1.POSE?.atk !== "number" && (pz("hipN") !== 0 || pz("hipF") !== 0 || pz("kneeN") !== 0 || pz("kneeF") !== 0);
	function sidePlan(unit, key, anim, W) {
		const { gear } = unit;
		const walking = walkingSide(anim);
		const gsWalk = walking && key?.c === "greatsword";
		const atkOn = typeof S$1.POSE?.atk === "number" || gsWalk;
		const bowK = !!key && key.c === "bow";
		const SX = atkOn ? {
			main: W ? 3 : 4.5,
			off: W ? 4.5 : 3
		} : bowK ? {
			main: SSH,
			off: W ? 4.5 : 3
		} : {
			main: SSH,
			off: SSH
		};
		const nearWho = W ? "off" : "main";
		let P;
		let bowT = 0;
		if (key && !anim) {
			const ks = W && key.K.sideW && !(key.K.sideW.needOff && !gear.off_hand) ? key.K.sideW : key.K.side;
			const bow = key.c === "bow";
			let hand = W && ks.hw ? ks.hw : ks.hand;
			let a = W && ks.aW != null ? ks.aW : ks.a;
			let og = ks.og ?? null;
			let mg = ks.mg ?? (key.kind === "scythe" && ks.gripS != null ? ks.gripS : W && ks.gripW != null ? ks.gripW : ks.grip) ?? 0;
			let short = !!ks.short;
			let layer = ks.layer ?? null;
			let elbow = -1;
			let olen = ks.olen ?? null;
			let hlen = null;
			if (ks.farX && !W) SX.off = ks.farX;
			const AK = key.kind === "scythe" && key.K.atkScythe || key.K.atk;
			if (AK && atkOn) {
				const fr = AK.from;
				const t = gsWalk ? 0 : clamp01(S$1.POSE.atk ?? 0);
				const [P0, P1, tt] = AK.mid ? t < .5 ? [
					fr,
					AK.mid,
					t * 2
				] : [
					AK.mid,
					AK.to,
					t * 2 - 1
				] : [
					fr,
					AK.to,
					t
				];
				const L = (p, q) => p + (q - p) * tt;
				hand = [L(P0.hand[0] ?? 0, P1.hand[0] ?? 0), L(P0.hand[1] ?? 0, P1.hand[1] ?? 0)];
				a = L(P0.a, P1.a);
				og = AK.og;
				mg = AK.mg ?? 0;
				short = false;
				elbow = tt > .5 ? P1.elbow ?? -1 : P0.elbow ?? -1;
				if (P0.farX || P1.farX) SX.off = L(P0.farX ?? SX.off, P1.farX ?? SX.off);
				if (P0.og) og = tt < .5 ? P0.og : AK.og;
				olen = tt < .5 ? P0.olen ?? null : null;
				layer = tt < .5 && P0.layer ? P0.layer : Math.sin(a) < -.3 ? "head" : null;
			}
			if (bow) {
				const t = clamp01(pz("bowAim"));
				const A2 = key.K.aim;
				const th = t <= .4 ? t : Math.min(1, .4 + (t - .4) * 1.5);
				if (t) {
					hand = [(hand[0] ?? 0) + ((A2.hand[0] ?? 0) - (hand[0] ?? 0)) * th, (hand[1] ?? 0) + ((A2.hand[1] ?? 0) - (hand[1] ?? 0)) * th];
					a += (A2.a - a) * th;
					if (A2.farX) SX.off += (A2.farX - SX.off) * th;
					if (A2.nearX != null) SX.main += (A2.nearX - SX.main) * t;
				}
				og = "string";
				layer = W ? "head" : "mid";
				bowT = t;
			}
			const wh = bow ? "off" : "main";
			hlen = ks.hlen && !pz("bowAim") ? ks.hlen : null;
			let k;
			let dy = 0;
			if (ks.st && !atkOn) {
				k = {
					sA: Math.atan2(-((hand[0] ?? 0) - SX[wh]), (hand[1] ?? 0) + 20),
					eA: 0
				};
				if (W && wh === "main" && (key.c === "polearm" || key.c === "staff" && !gear.off_hand)) {
					const h0 = fk(SX[wh], k.sA, 0);
					SX[wh] = SSH - WEST_FAR_BACK;
					dy = WEST_FAR_DROP;
					const ex = h0[0] - SX[wh];
					const ey = h0[1] + 20 - dy;
					const r = Math.hypot(ex, ey);
					hlen = [5 * r / (5 + FA), FA * r / (5 + FA)];
					k = {
						sA: Math.atan2(-ex, ey),
						eA: 0
					};
				}
			} else k = ik(SX[wh], hand, elbow, hlen);
			const pole = walking && (key.c === "staff" || key.c === "polearm");
			const sw = pz("arm") * (gsWalk ? .25 : pole ? .5 : 1);
			P = {
				wh,
				sA: k.sA + sw,
				eA: k.eA,
				a: a + pz("arm") * (gsWalk ? .25 : pole ? .3 : 1) + pz("dw"),
				og,
				mg,
				short,
				layer,
				split: true,
				farX: ks.farX,
				olen,
				hlen,
				dy
			};
		} else {
			const gq = qWeapon(gear.main_hand);
			const empty = W && (!gear.main_hand || gq?.kind === "gauntlet" && !anim);
			if (empty) SX.main = -4.5;
			const sA = empty ? pz("armR") * .6 - .1 : pz("arm");
			const eA = empty ? .15 : Math.min(0, sA * .35);
			const w = anim ? S$1.POSE.wpn : holdOf(gear.main_hand, "side");
			const kc2 = key && key.c !== "bow" && key.c !== "staff" ? key.K.side.animOg ?? key.K.side.og : null;
			P = {
				wh: "main",
				sA,
				eA,
				a: sA + w,
				og: kc2 && anim ? kc2 : null,
				mg: key?.K.side.mg ?? 0,
				short: false,
				layer: null,
				split: false,
				olen: null,
				hlen: null
			};
		}
		const h0 = fk(SX[P.wh], P.sA, P.eA, P.hlen);
		const h = [h0[0], h0[1] + (P.dy ?? 0)];
		const who2 = P.wh === "main" ? "off" : "main";
		const A = { [P.wh]: {
			who: P.wh,
			sx: SX[P.wh],
			sA: P.sA,
			eA: P.eA,
			len: P.hlen,
			dy: P.dy ?? 0
		} };
		let ol = null;
		let pull = null;
		let og = P.og;
		const released = og === "string" && pz("bowAim") > .9 && !(pz("pull") > .5);
		if (released) og = null;
		const hands = S$1.POSE?.hands;
		if (og) {
			const ol0 = og === "string" ? [0, BOW_EY + (pz("pull") || 0)] : [og[0] ?? 0, og[1] ?? 0];
			const o = rot(P.a, [ol0[0], ol0[1] - P.mg]);
			const t = [h[0] + o[0], h[1] + o[1]];
			if (og === "string" && bowT >= .6) {
				const k = elbowTo(SX[who2], key.K.aim.edir, t);
				const ax = rot(P.a, [0, 1]);
				A[who2] = {
					who: who2,
					sx: SX[who2],
					sA: k.sA,
					eA: k.eA
				};
				pull = Math.max(0, (k.h[0] - h[0]) * ax[0] + (k.h[1] - h[1]) * ax[1] - BOW_EY);
				ol = [0, BOW_EY + pull];
				if (hands) hands["offTwo"] = true;
			} else {
				const k = ik(SX[who2], t, -1, P.olen);
				if (k.ok) {
					A[who2] = {
						who: who2,
						sx: SX[who2],
						sA: k.sA,
						eA: k.eA,
						len: P.olen
					};
					ol = ol0;
					if (hands) hands["offTwo"] = true;
				}
			}
		}
		if (!A[who2] && released) {
			const k = elbowTo(SX[who2], key.K.aim.edir, h);
			A[who2] = {
				who: who2,
				sx: SX[who2],
				sA: k.sA,
				eA: k.eA
			};
		}
		if (!A[who2]) {
			if (qWeapon(gear.main_hand)?.kind === "paired") {
				const att = anim && S$1.POSE.wpn !== void 0 && !S$1.POSE.idle;
				const k = ik(SX.off, att ? [10.2, -18.4] : [10.8, -19], -1);
				const da = att ? .55 : .75;
				A.off = {
					who: "off",
					sx: SX.off,
					sA: k.sA,
					eA: k.eA,
					item: (hand) => {
						offDagger(S$1.CTX, gear.main_hand, hand, da - k.sA - k.eA);
						swordGrip(S$1.CTX, unit, hand, da - k.sA - k.eA);
					}
				};
			} else if (isShield(gear.off_hand)) {
				const k = ik(SX.off, [8.6, -13.5 - pz("shieldUp")], -1);
				A.off = {
					who: "off",
					sx: SX.off,
					sA: k.sA,
					eA: k.eA,
					item: null,
					shield: true
				};
			} else if (offHeld(gear)) {
				const oh = offHeld(gear);
				const item = (hand) => mainWeapon(S$1.CTX, oh, hand, holdOf(oh, "side"), "side");
				A.off = W ? {
					who: "off",
					sx: SX.off,
					sA: .12,
					eA: .05,
					item
				} : {
					who: "off",
					sx: -4.5,
					sA: pz("armL") * .6 - .1,
					eA: .15,
					item
				};
			} else if (pz("armF") && !gear.off_hand) {
				const aF = pz("armF");
				A.off = {
					who: "off",
					sx: SSH,
					sA: aF,
					eA: Math.min(0, aF * .35),
					item: null
				};
			} else if (W) A.off = {
				who: "off",
				sx: SX.off,
				sA: gear.off_hand ? -.15 : .12,
				eA: gear.off_hand ? .1 : .05,
				item: gear.off_hand ? (hand) => pdHeld(S$1.CTX, gear.off_hand, hand[0] + 1, true) : null
			};
			else if (gear.off_hand) A.off = {
				who: "off",
				sx: SSH,
				sA: 0,
				eA: 0,
				item: (hand) => pdHeld(S$1.CTX, gear.off_hand, hand[0] - (gear.body?.kind === "robe" ? 0 : 1.5), true)
			};
			else A.off = {
				who: "off",
				sx: -4.5,
				sA: pz("armL") * .6 - .1,
				eA: .15,
				item: null
			};
		}
		const stretch = (X, r) => {
			if (X && r && !X.item && !(X.who === "main" && gear.main_hand)) X.len = [(X.len?.[0] ?? 5) * (1 + r), (X.len?.[1] ?? 5.5) * (1 + r)];
		};
		stretch(A.main, pz("reach"));
		stretch(A.off, pz("reachF"));
		const farWho = nearWho === "main" ? "off" : "main";
		const near = A[nearWho];
		const far = A[farWho];
		far.front = fk(far.sx, far.sA, far.eA, far.len ?? null)[0] > 4.6 && far.sx > 0;
		const bowHand = !!key && key.c === "bow" && !anim;
		const plan = {
			...P,
			og,
			h,
			ol,
			pull,
			released,
			near,
			far,
			bowHand,
			nearLate: bowHand && !W && bowT >= .6,
			late: false,
			nearDone: false
		};
		if (!plan.layer) plan.layer = plan.wh === farWho && !far.front ? "back" : "front";
		return plan;
	}
	/** QK-1 第 0.3 節第 3 點：朝西遠側握長柄的手，肩點往後移多少（拳頭不動）。 */
	var WEST_FAR_BACK = 1.4;
	/** QK-1b：同一隻手的肩點再往下移多少（上臂壓低，和下巴之間露出縫）。 */
	var WEST_FAR_DROP = 2.5;
	/** 正面、背面的弓：弓座標 (x, y) → 畫面 x·U − y·F；線寬照畫面算（BOWM）。 */
	function bowFace(ctx, it, hand, U, F, view, off = null) {
		ctx.save();
		ctx.translate(hand[0], hand[1]);
		S$1.BOWM = getM(ctx);
		ctx.transform(U[0], U[1], -F[0], -F[1], 0, 0);
		QW["bow"].draw(ctx, it);
		const probe = S$1.POSE?.probe;
		if (probe) {
			const m = getM(ctx);
			const T = (x, y) => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f];
			probe("bow", T(0, 0), T(0, -QW["bow"].len), view, T(off ? off[0] : 0, off ? off[1] : BOW_EY), m, "bow");
		}
		S$1.BOWM = null;
		ctx.restore();
	}
	/** 持弓待機（第 13 版）：弓在胸口前、靠中線；左手握弓把、右手扣弦上的箭尾。背面整組在身體之前畫（pre），被身體擋住。 */
	function bowStill(ctx, unit, view, pre = false) {
		const k = KEY()["bow"][view];
		const B = view === "back";
		const o = B ? -1 : 1;
		const ls = 8.5 * o;
		const ph = k.tilt ?? 0;
		if (B !== pre) return;
		const U = [-o * Math.sin(ph), Math.cos(ph)];
		const F = [o * Math.cos(ph), Math.sin(ph)];
		const sP = k.s;
		const nt = k.nt;
		const G = [(sP[0] ?? 0) + BOW_EY * F[0], (sP[1] ?? 0) + BOW_EY * F[1]];
		const N = [(sP[0] ?? 0) - nt * U[0], (sP[1] ?? 0) - nt * U[1]];
		const kl = ik(ls, G, o);
		const kr = ik(-ls, N, "down");
		const it = unit.gear.main_hand;
		const leftArm = () => void arm(ctx, unit, ls, kl.sA, kl.eA, 0, rec("off"));
		const rightArm = () => void arm(ctx, unit, -ls, kr.sA, kr.eA, 0, rec("main"));
		const bowArrow = () => {
			S$1.BOWP = {
				nock: false,
				noArrow: true
			};
			bowFace(ctx, it, G, U, F, view, [-nt, BOW_EY]);
			S$1.BOWP = null;
			mark$1("weapon");
			const dx = G[0] - N[0];
			const dy = G[1] - N[1];
			const dl = Math.hypot(dx, dy);
			const ux = dx / dl;
			const uy = dy / dl;
			const T = [G[0] + ux * k.ah, G[1] + uy * k.ah];
			ctx.strokeStyle = "#c8a070";
			ctx.lineWidth = .9;
			ctx.lineCap = "round";
			ctx.beginPath();
			ctx.moveTo(N[0] - ux, N[1] - uy);
			ctx.lineTo(T[0], T[1]);
			ctx.stroke();
			fill$1(ctx, "#c3ccd6", () => {
				ctx.moveTo(T[0] + ux * 2.4, T[1] + uy * 2.4);
				ctx.lineTo(T[0] - uy * 1.2, T[1] + ux * 1.2);
				ctx.lineTo(T[0] + uy * 1.2, T[1] - ux * 1.2);
				ctx.closePath();
			});
		};
		if (B) {
			const bodyPath = () => {
				ctx.beginPath();
				ctx.rect(-7.4, -21, 14.8, 13.4);
			};
			ctx.save();
			bodyPath();
			ctx.clip();
			bowArrow();
			ctx.restore();
			ctx.save();
			bodyPath();
			ctx.rect(-40, -60, 80, 43.5);
			ctx.clip();
			leftArm();
			rightArm();
			ctx.restore();
			return;
		}
		leftArm();
		bowArrow();
		rightArm();
	}
	/** 握住直的柄（法杖、拄地長柄、劍柄）：一條橫過柄的四指（和手同色、稍暗），柄從拳頭上下穿出。dk＝遠側手再加深。 */
	function wrap(ctx, unit, hand, a, dk = 0) {
		const { look, gear } = unit;
		const hc = gear.hands && gear.hands.kind !== "bracers" ? colors(gear.hands)[0] : look.skin;
		ctx.save();
		ctx.translate(hand[0], hand[1]);
		ctx.rotate(a);
		fill$1(ctx, mix(hc, "#000000", .05 + dk), () => rr(ctx, -2.35, -1.25, 4.7, 2.5, 1.1));
		ctx.strokeStyle = mix(hc, "#000000", .4);
		ctx.lineWidth = .35;
		ctx.beginPath();
		ctx.moveTo(-1.9, 0);
		ctx.lineTo(1.9, 0);
		ctx.stroke();
		ctx.restore();
	}
	function drawBody(ctx, unit, view, npc) {
		const { look, gear } = unit;
		const F = view === "front";
		const B = view === "back";
		const SD = view === "side";
		S$1.CTX = ctx;
		const side = SD ? 1 : 0;
		const W = SD && S$1.WEST;
		const key = keyOf(gear);
		const anim = !!S$1.POSE && typeof S$1.POSE.wpn === "number";
		const bk = backOf(gear);
		const mq = qWeapon(gear.main_hand);
		const armed = !!(gear.main_hand && mq && mq.kind !== "gauntlet");
		const armor = ["plate", "mail"].includes(gear.body?.kind ?? "");
		S$1.FILLARM = !SD && !key && SEAMF() && !armed;
		S$1.SHEDGE = F && SEAMF() && armor;
		S$1.SEAMIN = !SD && !key && !(B && isShield(gear.off_hand)) && SEAMF() && armor;
		S$1.SEAM = SD || !!key || B && isShield(gear.off_hand) || S$1.SEAMIN;
		ctx.save();
		raceBuild(ctx, look);
		if (look.frame === "slim") ctx.scale(.92, 1.02);
		else if (look.frame === "broad") ctx.scale(1.08, .98);
		ctx.translate(0, pz("bob"));
		if (SD) rotAt(ctx, 0, -9, pz("lean"));
		const fb = !SD && FB ? FB : null;
		const fbApi = fb ? fbApiOf(ctx, unit, fb.view) : null;
		const FBL = (layer) => {
			if (fb && fbApi) drawFbLayer(fbApi, fb.frame, layer);
		};
		const leanK = fb && B ? 1 + .5 * (fb.frame.lean ?? 0) : 1;
		if (leanK !== 1) {
			ctx.translate(0, -9);
			ctx.scale(1, leanK);
			ctx.translate(0, 9);
		}
		npcBeforeQ(ctx, npc, view);
		if (gear.cloak && F) cloakFront(ctx, gear.cloak);
		if (F) backItem(ctx, bk, "front", "behind");
		if (gear.cloak && SD) {
			cloakSide(ctx, gear.cloak);
			mark$1("cloak");
		}
		if (SD) backItem(ctx, bk, "side", "behind");
		if (!B) raceTail(ctx, look, F ? "front" : "side", side);
		FBL("under");
		if (B && !fb) drawBackPre(ctx, unit, key);
		const SP = SD ? sidePlan(unit, key, anim, W) : null;
		const sideArm = (A, clip) => {
			ctx.save();
			if (clip) {
				ctx.beginPath();
				if (clip === "hand") {
					const hh = fk(A.sx, A.sA, A.eA, A.len ?? null);
					ctx.arc(hh[0], hh[1] + (A.dy ?? 0), 2.6, 0, TAU);
				} else if (clip === "chest") ctx.rect(-80, -80, 160, 120);
				else if (clip === "sleeve") ctx.rect(A.sx, -80, 80, 120);
				else ctx.rect(3.2, -80, 80, 120);
				ctx.clip();
			}
			if (clip) {
				S$1.FAR = clip === "sleeve" ? GS_SLEEVE_DARK : .12;
				S$1.FARH = 0;
			}
			S$1.NOPAD = A === SP.far;
			if (A.dy) ctx.translate(0, A.dy);
			const r = rec(A.who);
			const inHand = A.item ? (hand, c) => {
				A.item(hand, c);
				if (r) r(hand, c);
			} : r;
			HAND_LIFT = A.shield ? SHIELD_HAND_LIFT : 0;
			arm(ctx, unit, A.sx, A.sA, A.eA, side, inHand, false, A.len ?? null);
			HAND_LIFT = 0;
			S$1.FAR = 0;
			S$1.FARH = 0;
			S$1.NOPAD = false;
			ctx.restore();
		};
		/**
		* QK-1 第 0.3 節第 1 點（QK-1b 重做）：雙手劍遠側（上面那隻）拳頭要接自己暗一階的前臂（同成對武器）。
		* 遠側拳頭在近側手臂「下方」（出招 atk：提劍、舉劍、劈）→ 遠側手臂橫過胸前，整隻畫在身體上、近側手臂之下（gsChest）；
		* 在「上方」（拄劍、待機）→ 近側手臂畫好後，從肩到拳頭補一段打直的暗袖子，蓋在近側上臂上緣（gsFarSleeve）。
		*/
		const gsFar = (sp) => {
			if (key?.c !== "greatsword" || !sp.far.front || !sp.ol) return null;
			const N = sp.near;
			const b = fk(N.sx, N.sA, N.eA, N.len ?? null);
			const f = fk(sp.far.sx, sp.far.sA, sp.far.eA, sp.far.len ?? null);
			return (b[0] - N.sx) * (f[1] + 20) - (b[1] + 20) * (f[0] - N.sx) < 0 ? "sleeve" : "chest";
		};
		const gsFarSleeve = (sp) => {
			const F0 = sp.far;
			const fh = fk(F0.sx, F0.sA, F0.eA, F0.len ?? null);
			const r = Math.hypot(fh[0] - F0.sx, fh[1] + 20);
			const len = [GS_SLEEVE_SAG * r, GS_SLEEVE_SAG * r];
			const k = ik(F0.sx, fh, "down", len);
			sideArm({
				...F0,
				item: null,
				sA: k.sA,
				eA: k.eA,
				len
			}, "sleeve");
		};
		const sideWeapon = () => {
			const sp = SP;
			if (key && key.c === "bow") S$1.BOWP = {
				pull: sp.pull,
				nock: !sp.released
			};
			mainWeapon(ctx, gear.main_hand, sp.h, sp.a, "side", sp.short, sp.ol, sp.mg);
			S$1.BOWP = null;
			mark$1("weapon");
			if (key && !anim && typeof S$1.POSE?.atk !== "number" && !(walkingSide(anim) && key.c === "greatsword") && (key.c === "staff" || key.c === "polearm" || key.c.startsWith("greatsword"))) {
				const one = (pos, who) => {
					if (!(sp.far.who === who && sp.far.front)) {
						wrap(ctx, unit, pos, sp.a);
						return;
					}
					ctx.save();
					ctx.beginPath();
					ctx.arc(pos[0], pos[1], 2.4, 0, TAU);
					ctx.clip();
					wrap(ctx, unit, pos, sp.a);
					ctx.restore();
					if (sp.nearDone && sp.near.who !== sp.wh && !sp.ol) {
						const N = sp.near;
						ctx.save();
						ctx.beginPath();
						ctx.arc(pos[0], pos[1], 2.9, 0, TAU);
						ctx.clip();
						arm(ctx, unit, N.sx, N.sA, N.eA, side, null, false, N.len ?? null);
						ctx.restore();
					}
				};
				one(sp.h, sp.wh);
				if (sp.ol && key.c.startsWith("greatsword")) {
					const o = rot(sp.a, [sp.ol[0], sp.ol[1] - sp.mg]);
					one([sp.h[0] + o[0], sp.h[1] + o[1]], sp.wh === "main" ? "off" : "main");
				}
			}
		};
		if (SP) {
			if (!SP.far.front) sideArm(SP.far, false);
			if (SP.layer === "back") {
				sideWeapon();
				if (!SP.split) sideSwordGrip(ctx, unit, SP, false);
			}
		}
		if (SD) waistItem(ctx, gear.waist, "side", "behind");
		const sink = Math.max(0, pz("bob"));
		const legFix = leanK !== 1 || sink > 0;
		if (legFix) ctx.save();
		if (sink > 0) ctx.translate(0, -sink);
		if (leanK !== 1) {
			ctx.translate(0, -9);
			ctx.scale(1, 1 / leanK);
			ctx.translate(0, 9);
		}
		leg(ctx, look, gear.feet, -1, pz("hipF"), pz("kneeF"), pz("liftL"), side, view);
		leg(ctx, look, gear.feet, 1, pz("hipN"), pz("kneeN"), pz("liftR"), side, view);
		if (legFix) ctx.restore();
		if (SP && gear.main_hand) S$1.NOBUCKLE = mq?.kind === "gauntlet" && !anim || [SP.near, SP.far].some((N) => {
			const nh = fk(N.sx, N.sA, N.eA, N.len ?? null);
			return nh[0] > 1.5 && nh[0] < 9.5 && nh[1] > -13 && nh[1] < -4.5;
		});
		body(ctx, gear.body, look, side, B);
		mark$1("body");
		S$1.NOBUCKLE = false;
		const v = F ? "front" : B ? "back" : "side";
		drawTorsoForms(ctx, gear, v);
		drawFreeForms(ctx, gear, v);
		crest(ctx, gear.body, v);
		neckItem(ctx, gear.neck, v);
		waistItem(ctx, gear.waist, v, "over");
		if (!B) backItem(ctx, bk, F ? "front" : "side", "over");
		if (B && !fb) drawBackPost(ctx, unit, key);
		if (B && isShield(gear.off_hand) && !fb) shieldArmBack(ctx, unit);
		FBL("over");
		if (SP) {
			cloakClasp(ctx, gear.cloak, true);
			if (!W && isShield(gear.off_hand)) {
				if (SP.far.shield) sideArm(SP.far, true);
				shieldSide(ctx, gear.off_hand);
			}
		}
		if (B) {
			drawTopForms(ctx, gear, "back");
			if (gear.cloak) {
				cloakBack(ctx, gear.cloak);
				mark$1("cloak");
			}
			backItem(ctx, bk, "back", "over");
			raceTail(ctx, look, "back", 0);
		}
		if (F && gear.cloak) cloakClasp(ctx, gear.cloak, false);
		const twoF = F && key && (key.K.front.og || key.K.front.wh === "off");
		if (F && !twoF && !fb) drawFrontOff(ctx, unit, key);
		if (SP && SP.split) {
			SP.late = W && !!SP.near.item && SP.layer === "front";
			const gf = gsFar(SP);
			if (SP.far.front) sideArm(SP.far, gf === "chest" ? "chest" : true);
			if (SP.layer === "mid") sideWeapon();
			if (!SP.late && !SP.nearLate) {
				sideArm(SP.near, false);
				SP.nearDone = true;
				if (gf === "sleeve") gsFarSleeve(SP);
			}
			if (SP.layer === "head") sideWeapon();
			if (W && SP.bowHand && SP.far.front) sideArm(SP.far, "hand");
			if (W && SP.bowHand && SP.far.front) {
				const N = SP.near;
				const nh = fk(N.sx, N.sA, N.eA, N.len ?? null);
				ctx.save();
				ctx.beginPath();
				ctx.rect(-80, -120, 160, 200);
				ctx.arc(nh[0], nh[1], 3, 0, TAU);
				ctx.clip("evenodd");
				ctx.beginPath();
				ctx.rect(-80, -120, 80 + nh[0] - 1.6, 200);
				ctx.clip();
				arm(ctx, unit, N.sx, N.sA, N.eA, side, null, false, N.len ?? null);
				ctx.restore();
			}
		} else if (SP) {
			if (SP.layer === "head") sideWeapon();
			if (SP.far.front && SP.layer !== "front" && !SP.far.shield) sideArm(SP.far, true);
		}
		mark$1("head");
		ctx.save();
		rotAt(ctx, 0, -29, SD ? pz("lean") * .3 : 0);
		if (isCowl(gear.head) && !B) cowl(ctx, gear.head, v);
		drawQHead(ctx, look, v, side, gear.head);
		raceEars(ctx, look, v, side, gear.head, "under");
		const hc = headgearClip(ctx, gear.head, v);
		raceHat(ctx, look, gear.head, (it) => drawQHeadgear(ctx, it, v));
		if (hc) ctx.restore();
		drawHeadFormTop(ctx, gear.head, v);
		raceEars(ctx, look, v, side, gear.head, "over");
		raceHorns(ctx, look, v);
		if (isCowl(gear.head) && B) cowl(ctx, gear.head, "back");
		ctx.restore();
		if (fb) FBL("top");
		else if (F && key && key.c === "bow") bowStill(ctx, unit, "front");
		else if (F && key) drawFrontKey(ctx, unit, key);
		else if (F) {
			const rm = rec("main");
			const oF = holdA(gear);
			ctx.save();
			ctx.translate(0, pz("armL"));
			arm(ctx, unit, -sxOf(gear), oF, 0, 0, (hand, c) => {
				const a = holdOf(gear.main_hand, "front") - oF - ARM().swa;
				mainWeapon(ctx, gear.main_hand, swOff(hand, -1, gear), a, "front");
				swordGrip(ctx, unit, hand, a, swOff(hand, -1, gear));
				if (rm) rm(hand, c);
			});
			ctx.restore();
		} else if (SP && SP.split) {
			if (SP.layer === "front") sideWeapon();
			if (SP.late || SP.nearLate) sideArm(SP.near, false);
		} else if (SP) {
			const inNear = SP.wh === (W ? "off" : "main");
			if (SP.layer === "front") {
				if (SP.far.front && !SP.far.shield) sideArm(SP.far, true);
				if (inNear) {
					sideArm(SP.near, false);
					sideWeapon();
					sideSwordGrip(ctx, unit, SP, false);
				} else {
					sideWeapon();
					sideSwordGrip(ctx, unit, SP, true);
					sideArm(SP.near, false);
				}
			} else sideArm(SP.near, false);
			if (W && isShield(gear.off_hand)) shieldSide(ctx, gear.off_hand);
		}
		if (!B) drawTopForms(ctx, gear, v);
		npcAfterQ(ctx, npc, view);
		ctx.restore();
		S$1.SEAM = false;
		S$1.SEAMIN = false;
		S$1.SHEDGE = false;
		S$1.FILLARM = false;
		S$1.FREEARM = false;
	}
	/** 側面單手劍：四指橫過握把（遠側手只畫在拳頭裡、暗一階）。 */
	function sideSwordGrip(ctx, unit, SP, farFront) {
		swordGrip(ctx, unit, SP.h, SP.a, SP.h, farFront && SP.far.who === SP.wh ? 2.4 : 0);
	}
	/** 背面：拿在身體前方的東西（雙手武器、弓、杖）連手一起先畫，被身體擋住。 */
	function drawBackPre(ctx, unit, key) {
		const { gear } = unit;
		const kb = backKey(key);
		if (kb && kb.og) {
			const who = kb.wh ?? "main";
			const sx = who === "main" ? 8.5 : -8.5;
			const k0 = armTo(sx, kb.hand, sx > 0 ? 1 : -1);
			const h = fk(sx, k0.sA, k0.eA);
			const ol = ogLocal(kb.og);
			const M = kb.fore ?? null;
			const o = M ? [(M[0] ?? 0) * ol[0] + (M[2] ?? 0) * ol[1], (M[1] ?? 0) * ol[0] + (M[3] ?? 0) * ol[1]] : rot(kb.a, ol);
			const io = ik(-sx, [h[0] + o[0], h[1] + o[1]], sx > 0 ? -1 : 1);
			S$1.BOWP = { nock: true };
			mainWeapon(ctx, gear.main_hand, h, kb.a, "back", kb.short ?? false, ol, 0, M);
			S$1.BOWP = null;
			mark$1("weapon");
			arm(ctx, unit, -sx, io.sA, io.eA, 0, rec(who === "main" ? "off" : "main"));
			arm(ctx, unit, sx, k0.sA, k0.eA, 0, rec(who));
		} else {
			if (key && key.c === "bow") bowStill(ctx, unit, "back", true);
			if (key && kb && (key.c === "staff" || key.c === "polearm")) {
				const k0 = stK(SHX(), kb, 1, gear);
				const h = fk(SHX(), k0.sA, k0.eA);
				const mgB = stMg(SHX(), kb, k0, (key.kind === "scythe" && kb.gripS != null ? kb.gripS : kb.grip) ?? 0, gear);
				const po = ARM().po;
				mainWeapon(ctx, gear.main_hand, po ? [h[0] + po, h[1]] : h, kb.a, "back", false, null, mgB);
				mark$1("weapon");
			}
			if (gear.main_hand && !(key && (key.c === "staff" || key.c === "bow" || key.c === "polearm"))) {
				ctx.save();
				ctx.translate(0, pz("armR"));
				mainWeapon(ctx, gear.main_hand, swOff(fk(sxOf(gear), -holdA(gear), 0), 1, gear), -holdOf(gear.main_hand, "front") + ARM().swa, "back");
				ctx.restore();
				mark$1("weapon");
			}
		}
		mark$1("arms");
		if (isShield(gear.off_hand)) {
			const sh = fk(-SHX(), OUTA(), 0);
			const oh = gear.off_hand;
			shieldBack(ctx, oh, sh[0] + 1, sh[1] + (oh.kind === "shield_round" ? 11.8 : oh.form === "tower" ? 11.5 : 11));
			mark$1("shield");
		}
	}
	/** 背面：垂在身側、看得到的手（法杖在畫面右、弓、空手、單手武器、書）。 */
	function drawBackPost(ctx, unit, key) {
		const { gear } = unit;
		const kb = backKey(key);
		const paired = qWeapon(gear.main_hand)?.kind === "paired";
		if (key && key.c === "bow") bowStill(ctx, unit, "back");
		else if (key && kb && (key.c === "staff" || key.c === "polearm")) {
			const k0 = stK(SHX(), kb, 1, gear);
			arm(ctx, unit, SHX(), k0.sA, k0.eA, 0, rec("main"));
		} else if (!(kb && kb.og)) {
			const rm = rec("main");
			ctx.save();
			ctx.translate(0, pz("armR"));
			const guard = swOn(gear);
			const oB = holdA(gear);
			const a = -holdOf(gear.main_hand, "front") + oB + ARM().swa;
			arm(ctx, unit, sxOf(gear), -oB, 0, 0, gear.main_hand ? (hand, c) => {
				c.save();
				c.beginPath();
				c.arc(hand[0], hand[1], 2.6, 0, TAU);
				if (guard) {
					c.save();
					c.translate(hand[0], hand[1]);
					c.translate(swOn(gear) ? ARM().sw : 0, 0);
					c.rotate(a);
					c.rect(-4.8, -4.6, 9.6, 3.2);
					c.restore();
				}
				c.clip();
				mainWeapon(ctx, gear.main_hand, swOff(hand, 1, gear), a, "back");
				c.restore();
				swordGrip(ctx, unit, hand, a, swOff(hand, 1, gear));
				if (rm) rm(hand, c);
			} : rm);
			ctx.restore();
		}
		const OHB = offHeld(gear);
		if (gear.off_hand && !isShield(gear.off_hand) && !OHB) {
			ctx.save();
			ctx.translate(0, pz("armL"));
			S$1.TINT = S$1.POSE?.tintOff ?? null;
			const bookA = OUTA() + robeX(gear);
			arm(ctx, unit, -SHX(), bookA, 0, 0, rec("off"));
			S$1.TINT = null;
			const bh = fk(-SHX(), bookA, 0);
			const [bc, bd] = colors(gear.off_hand);
			if (SEAMF()) {
				const rb = gear.body?.kind === "robe";
				const hem = gear.body?.form === "short" ? -6 : -1.5;
				ctx.beginPath();
				ctx.rect(-80, -120, 160, 200);
				if (rb) {
					ctx.moveTo(-7, -21);
					ctx.lineTo(7, -21);
					ctx.lineTo(10, hem);
					ctx.lineTo(-10, hem);
					ctx.closePath();
				} else ctx.rect(-7.5, -21, 15, 13.5);
				ctx.clip("evenodd");
			}
			ctx.translate(bh[0] - (ARM().bk ?? 2), bh[1] + .1);
			fill$1(ctx, bc, () => rr(ctx, -4.5, -6, 9, 8, 1));
			fill$1(ctx, bd, () => rr(ctx, 2.9, -6, 1.6, 8, .6));
			ctx.restore();
			mark$1("shield");
		}
		if ((!gear.off_hand || OHB) && !(kb && kb.og) && key?.c !== "bow") {
			S$1.FREEARM = !key && !paired && !S$1.SEAMIN && !OHB;
			arm(ctx, unit, -sxOf(gear), OHB ? OUTA() : outOf(gear), 0, 0, OHB ? (hand, c) => {
				mainWeapon(ctx, OHB, hand, holdOf(OHB, "front") - OUTA(), "back");
				const r = rec("off");
				if (r) r(hand, c);
			} : paired ? (hand, c) => {
				offDagger(ctx, gear.main_hand, hand, holdOf(gear.main_hand, "front") - OUTA());
				swordGrip(ctx, unit, hand, holdOf(gear.main_hand, "front") - OUTA());
				const r = rec("off");
				if (r) r(hand, c);
			} : rec("off"));
			S$1.FREEARM = false;
		}
	}
	/** 正面：空著或拿盾、書的左手（打直往外下方），盾心對準拳頭、書往外。 */
	function drawFrontOff(ctx, unit, key) {
		const { gear } = unit;
		const pairedF = qWeapon(gear.main_hand)?.kind === "paired";
		const off = gear.off_hand;
		const OHF = offHeld(gear);
		const freeF = OHF ? OUTA() : off ? isShield(off) ? ARM().shA ?? OUTA() : OUTA() + robeX(gear) : outOf(gear);
		ctx.save();
		ctx.translate(0, pz("armR"));
		S$1.FREEARM = !key && !pairedF && !S$1.SEAMIN && !OHF;
		const sx = freeF ? SHX() : 8.5;
		arm(ctx, unit, sx, -freeF, 0, 0, OHF ? (hand, c) => {
			mainWeapon(ctx, OHF, hand, -holdOf(OHF, "front") + OUTA(), "front");
			const r = rec("off");
			if (r) r(hand, c);
		} : pairedF ? (hand, c) => {
			offDagger(ctx, gear.main_hand, hand, -holdOf(gear.main_hand, "front") + OUTA());
			swordGrip(ctx, unit, hand, -holdOf(gear.main_hand, "front") + OUTA());
			const r = rec("off");
			if (r) r(hand, c);
		} : rec("off"));
		S$1.FREEARM = false;
		const bh = fk(sx, -freeF, 0);
		ctx.translate(0, bh[1] + 9.6 + (ARM().shf && isShield(off) ? 3.9 : 0));
		if (off && isShield(off)) {
			if (ARM().shf) ctx.translate(0, off.kind !== "shield_kite" ? 0 : off.form === "tower" ? 1.5 : -.5);
			else if (off.kind === "shield_kite" && off.form !== "tower") ctx.translate(0, 3.5);
			shieldFront(ctx, off, bh[0] + (ARM().shf ? 0 : 2.7));
		} else if (off && !OHF) pdHeld(ctx, off, bh[0] + (ARM().bk ?? 2), true);
		ctx.restore();
	}
	/** 正面關鍵姿勢：兩隻手臂先畫，武器畫在手上面；杖、拄地長柄、雙手劍四指橫過柄。 */
	function drawFrontKey(ctx, unit, key) {
		const { gear } = unit;
		const k = key.K.front;
		const who = k.wh ?? "main";
		const sx = (who === "main" ? -1 : 1) * (k.st ? SHX() : 8.5);
		const k0 = stK(sx, k, who === "main" ? -1 : 1, gear);
		const h = fk(sx, k0.sA, k0.eA);
		const ol = ogLocal(k.og);
		if (ol) {
			const o = rot(k.a, ol);
			const io = ik(-sx, [h[0] + o[0], h[1] + o[1]], sx < 0 ? 1 : -1);
			arm(ctx, unit, -sx, io.sA, io.eA, 0, rec(who === "main" ? "off" : "main"));
		}
		arm(ctx, unit, sx, k0.sA, k0.eA, 0, rec(who));
		if (who === "off" && !ol) arm(ctx, unit, -8.5, 0, 0, 0, rec("main"));
		const mgF = stMg(sx, k, k0, (key.kind === "scythe" && k.gripS != null ? k.gripS : k.grip) ?? 0, gear);
		const MF = k.flipS && key.kind === "scythe" ? [
			-1,
			0,
			0,
			1
		] : null;
		const po = ARM().po;
		S$1.BOWP = { nock: true };
		mainWeapon(ctx, gear.main_hand, po && k.st ? [h[0] - po, h[1]] : h, k.a, "front", k.short ?? false, ol, mgF, MF);
		S$1.BOWP = null;
		if (key.c === "staff" || key.c === "polearm" || key.c.startsWith("greatsword")) wrap(ctx, unit, h, k.a);
		if (ol && key.c.startsWith("greatsword")) {
			const o = rot(k.a, ol);
			wrap(ctx, unit, [h[0] + o[0], h[1] + o[1]], k.a);
		}
	}
	/** QK-5：正面、背面五類出招的畫圖工具（樣張 fbApiOf）。手臂：彎肘兩段描邊、打直一圈（SEAM 開、SEAMIN 關）。 */
	function fbApiOf(ctx, unit, view) {
		const { gear } = unit;
		return {
			ctx,
			view,
			main: gear.main_hand,
			arm: (A) => {
				const s0 = [
					S$1.SEAM,
					S$1.SEAMIN,
					S$1.FILLARM,
					S$1.FREEARM,
					S$1.FAR
				];
				S$1.SEAM = true;
				S$1.SEAMIN = false;
				S$1.FILLARM = false;
				S$1.FREEARM = false;
				S$1.FAR = 0;
				arm(ctx, unit, A.sx, A.sA, A.eA, 0, null, false, A.len);
				[S$1.SEAM, S$1.SEAMIN, S$1.FILLARM, S$1.FREEARM, S$1.FAR] = s0;
			},
			weapon: (hand, a, M, mg) => mainWeapon(ctx, gear.main_hand, hand, a, view, false, null, mg, M),
			wrap: (hand, a) => wrap(ctx, unit, hand, a),
			bow: (hand, U, F, pull, nock) => {
				S$1.BOWP = {
					pull,
					nock,
					noArrow: !nock
				};
				bowFace(ctx, gear.main_hand, hand, U, F, view);
				S$1.BOWP = null;
			},
			offItem: (hand) => {
				const off = gear.off_hand;
				if (!off && qWeapon(gear.main_hand)?.kind === "paired") {
					const a = view === "front" ? -holdOf(gear.main_hand, "front") + OUTA() : holdOf(gear.main_hand, "front") - OUTA();
					offDagger(ctx, gear.main_hand, hand, a);
					swordGrip(ctx, unit, hand, a);
					return;
				}
				if (!off) return;
				const OH = offHeld(gear);
				ctx.save();
				if (OH) mainWeapon(ctx, OH, hand, view === "front" ? -holdOf(OH, "front") + OUTA() : holdOf(OH, "front") - OUTA(), view);
				else if (view === "front") {
					ctx.translate(0, hand[1] + 9.6 + (ARM().shf && isShield(off) ? 3.9 : 0));
					if (isShield(off)) {
						if (ARM().shf) ctx.translate(0, off.kind !== "shield_kite" ? 0 : off.form === "tower" ? 1.5 : -.5);
						shieldFront(ctx, off, hand[0]);
					} else pdHeld(ctx, off, hand[0] + (ARM().bk ?? 2), true);
				} else if (isShield(off)) shieldBack(ctx, off, hand[0] + 1, hand[1] + (off.kind === "shield_round" ? 11.8 : off.form === "tower" ? 11.5 : 11));
				else if (off.kind !== "tome") {
					ctx.translate(0, hand[1] + 9.6);
					pdHeld(ctx, off, hand[0] - (ARM().bk ?? 2), false);
				} else {
					const [bc, bd] = colors(off);
					ctx.translate(hand[0] - (ARM().bk ?? 2), hand[1] + .1);
					fill$1(ctx, bc, () => rr(ctx, -4.5, -6, 9, 8, 1));
					fill$1(ctx, bd, () => rr(ctx, 2.9, -6, 1.6, 8, .6));
				}
				ctx.restore();
			},
			colors: (it) => it ? colors(it) : ["#c8ccd4", "#8a8e96"]
		};
	}
	/** 畫一隻 Q 版小人（腳底中心在原點、朝東的座標；朝西由呼叫端鏡像並給 west＝true）。不畫外框（外框由 qStamp 做）。 */
	function drawQ(ctx, unit, view, hooks, pose = null, west = false) {
		const keep = {
			POSE: S$1.POSE,
			WEST: S$1.WEST,
			hooks: S$1.hooks,
			EDGEK,
			FB
		};
		const npc = npcPrep(unit, pose, view === "side" && west);
		S$1.POSE = npc.pose;
		const fbk = fbKindOfIndex(npc.pose?.fbk ?? 0);
		FB = null;
		if (fbk !== null && view !== "side") {
			const frame = fbFrameAt(fbk, view, npc.pose?.fbt ?? 0);
			FB = {
				kind: fbk,
				frame,
				view
			};
			const p0 = npc.pose ?? {};
			S$1.POSE = {
				...p0,
				bob: (p0.bob ?? 0) + (frame.bob ?? 0),
				liftL: (p0.liftL ?? 0) + (frame.liftL ?? 0),
				liftR: (p0.liftR ?? 0) + (frame.liftR ?? 0),
				glow: Math.max(p0.glow ?? 0, frame.glow ?? 0),
				armL: 0,
				armR: 0
			};
		}
		S$1.WEST = west && view === "side";
		S$1.hooks = hooks;
		EDGEK = npc.unit.gear.body?.kind === "bare" ? .23 : null;
		try {
			drawBody(ctx, npc.unit, view, npc);
		} finally {
			S$1.POSE = keep.POSE;
			S$1.WEST = keep.WEST;
			S$1.hooks = keep.hooks;
			EDGEK = keep.EDGEK;
			FB = keep.FB;
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qStamp.ts
	/** 離屏畫布（單位）：128×112、腳下留 14（出招時長槍、法杖伸出去不被切掉）。 */
	var Q_BOX = {
		W: 128,
		H: 112,
		FOOT: 14
	};
	/** 外框半徑（單位）。 */
	var Q_LINE = 1.3;
	function canvas(w, h) {
		const c = document.createElement("canvas");
		c.width = Math.max(1, Math.ceil(w));
		c.height = Math.max(1, Math.ceil(h));
		return c;
	}
	/** 剪影膨脹 r（離屏像素）：12 個方向各做一次 5 步的短線段膨脹（Minkowski 和），每一步都連續，細線和尖端外框是平滑的一圈。 */
	function dilate(src, r) {
		const N = 12;
		const a = r * Math.PI / 24;
		const P = [canvas(src.width, src.height), canvas(src.width, src.height)];
		let cur = src;
		let n = 0;
		for (let i = 0; i < N; i++) {
			const t = Math.PI * i / N;
			const ux = Math.cos(t) * a;
			const uy = Math.sin(t) * a;
			const c = P[n++ % 2];
			const g = c.getContext("2d");
			g.clearRect(0, 0, c.width, c.height);
			for (const f of [
				-1,
				-.5,
				0,
				.5,
				1
			]) g.drawImage(cur, ux * f, uy * f);
			cur = c;
		}
		const o = canvas(src.width, src.height);
		o.getContext("2d").drawImage(cur, 0, 0);
		return o;
	}
	function tinted(src, color) {
		const g = src.getContext("2d");
		g.globalCompositeOperation = "source-in";
		g.fillStyle = color;
		g.fillRect(0, 0, src.width, src.height);
		g.globalCompositeOperation = "source-over";
		return src;
	}
	function inverse(src) {
		const c = canvas(src.width, src.height);
		const g = c.getContext("2d");
		g.fillStyle = "#000";
		g.fillRect(0, 0, c.width, c.height);
		g.globalCompositeOperation = "destination-out";
		g.drawImage(src, 0, 0);
		return c;
	}
	/**
	* QK-8：白紗面罩、傀儡線不描外框（樣張 qNpc 的 D 層），朝西遠側手的傀儡線在外框之下（B0 層）。
	* 需要時開兩張和本體同大小的離屏，畫完後 under 貼在外框之前、over 貼在本體之後。
	*/
	function drawWithNpc(o, unit, view, hooks, pose, west) {
		if (!npcNeedsLayers(unit)) {
			drawQ(o, unit, view, hooks, pose, west);
			return null;
		}
		const under = canvas(o.canvas.width, o.canvas.height);
		const over = canvas(o.canvas.width, o.canvas.height);
		setNpcLayers({
			under: under.getContext("2d"),
			over: over.getContext("2d")
		});
		try {
			drawQ(o, unit, view, hooks, pose, west);
		} finally {
			setNpcLayers(null);
		}
		return {
			under,
			over
		};
	}
	/** 有 DOM 才能做外框（vitest 的 node 環境沒有，直接畫填色）。 */
	var canStamp = () => typeof document !== "undefined" && typeof document.createElement === "function";
	/**
	* 在 ctx 目前的座標系裡，把小人（腳底在 (0,0)、size 單位）連外框一起畫上去。
	* 解析度依 ctx 目前的縮放決定（× dpr 倍取樣再縮小貼上）；沒有 DOM 時直接畫填色、不畫外框。
	*/
	function qStampLocal(ctx, unit, view, west, hooks, pose, opt = {}) {
		if (!canStamp()) {
			ctx.save();
			if (west) ctx.scale(-1, 1);
			drawQ(ctx, unit, view, hooks, pose, west);
			ctx.restore();
			return;
		}
		const m = getM(ctx);
		const k = Math.max(.25, Math.hypot(m.a, m.b), Math.hypot(m.c, m.d));
		const sc = Math.min(12, k * (opt.dpr ?? 3));
		const { W, H, FOOT } = Q_BOX;
		const off = canvas(W * sc, H * sc);
		const o = off.getContext("2d");
		o.scale(sc, sc);
		o.translate(W / 2, H - FOOT);
		if (west) o.scale(-1, 1);
		const npcL = drawWithNpc(o, unit, view, hooks, pose, west);
		ctx.save();
		ctx.imageSmoothingEnabled = true;
		if (npcL) ctx.drawImage(npcL.under, -W / 2, -(H - FOOT), W, H);
		if (opt.outline !== false) {
			const sil = canvas(off.width, off.height);
			sil.getContext("2d").drawImage(off, 0, 0);
			tinted(sil, Q_OUT);
			const r = Q_LINE * sc;
			const close = opt.close ?? (qWeapon(unit.gear.main_hand)?.kind === "bow" && view !== "back");
			let line;
			if (close) {
				const O = dilate(sil, r);
				const rc = 1.5 * sc;
				const cl = canvas(off.width, off.height);
				const g = cl.getContext("2d");
				g.drawImage(inverse(dilate(inverse(dilate(O, rc)), rc)), 0, 0);
				g.drawImage(O, 0, 0);
				line = tinted(cl, Q_OUT);
			} else line = tinted(dilate(sil, r), Q_OUT);
			ctx.drawImage(line, -W / 2, -(H - FOOT), W, H);
		}
		ctx.drawImage(off, -W / 2, -(H - FOOT), W, H);
		if (npcL) ctx.drawImage(npcL.over, -W / 2, -(H - FOOT), W, H);
		ctx.restore();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qSpec.ts
	/** 遊戲畫面用的顏色：裝備色照 itemColors（材質色表 material.ts）、元素色照 palette。 */
	var GAME_HOOKS = {
		colors: (it) => itemColors({ ...it }),
		tint: elementTint
	};
	function qUnitOf(spec) {
		const look = { ...spec.look };
		const gear = { ...spec.gear };
		if (gear.main_hand?.kind === "fist") delete gear.main_hand;
		if (gear.off_hand?.kind === "fist") delete gear.off_hand;
		const main = gear.main_hand;
		const off = gear.off_hand;
		if (main?.kind === "dagger" && off?.kind === "dagger") {
			gear.main_hand = {
				...main,
				kind: "paired"
			};
			delete gear.off_hand;
		}
		return {
			look,
			gear
		};
	}
	/**
	* QK-5：Q 版腿短（大腿 4、小腿 5，C 是 15），C 的片段（跳躍收腿、蹲低、跪地、滑倒、倒下前的膝軟）照搬會讓腿折進身體、腳浮到腰上。
	* Q 版只在這裡收斂（片段資料不改，C 畫法照舊）：膝 ≤ 0.9、髖 −0.7～0.75（qGear.leg 再 ×1.6）；往下沉的 bob 照腿長比例 ×0.6、最多 3.2。
	*/
	var Q_LEG = {
		knee: .9,
		hipMin: -.7,
		hipMax: .75,
		bobK: .6,
		bobMax: 3.2
	};
	function qLegFit(p) {
		const out = { ...p };
		const cl = (v, a, b) => Math.max(a, Math.min(b, v));
		for (const k of ["kneeN", "kneeF"]) if (typeof out[k] === "number") out[k] = cl(out[k], -Q_LEG.knee, Q_LEG.knee);
		for (const k of ["hipN", "hipF"]) if (typeof out[k] === "number") out[k] = cl(out[k], Q_LEG.hipMin, Q_LEG.hipMax);
		if (typeof out.bob === "number" && out.bob > 0) out.bob = Math.min(Q_LEG.bobMax, out.bob * Q_LEG.bobK);
		return out;
	}
	/** inkPose 的姿勢欄位 Q 版照用（elbow、armF、reach 等 C 專用的欄位 Q 版不吃；腿照 qLegFit 收斂）。 */
	var qPoseOf = (p) => p === null ? null : qLegFit(p);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/paperdoll.ts
	/**
	* 戰場縮放：C 畫風 3U-2 定案 52px 格約 0.92 倍；QK-5 起 Q 版放大 1.15 倍 → 1.06（美術 PM 建議、使用者「不 照建議」）。
	* Q 版頭頂 38 → 52px 格約 40px，頭頂超出本格上緣一點；高帽（巫師帽、角盔）會伸進上一格，畫布上方的頭頂預留 28 不變。
	*/
	var DOLL_SCALE = 1.06;
	/** 小人骨架取裝備顏色的掛勾。 */
	var HOOKS = { colors: itemColors };
	function fill(ctx, color, path) {
		ctx.fillStyle = color;
		ctx.beginPath();
		path();
		ctx.fill();
	}
	/** 圖騰柱（召喚的圖騰）：木柱＋刻出的臉＋頂端寶珠。 */
	function drawTotem(ctx) {
		fill(ctx, "rgba(0,0,0,0.25)", () => ctx.ellipse(0, -1, 9, 3, 0, 0, TAU$2));
		fill(ctx, "#6e4620", () => roundRect(ctx, -6, -40, 12, 40, 2));
		fill(ctx, "#8f5f2c", () => roundRect(ctx, -6, -40, 4, 40, 2));
		fill(ctx, "#b77f3f", () => roundRect(ctx, -8, -28, 16, 5, 1));
		fill(ctx, "#b77f3f", () => roundRect(ctx, -8, -14, 16, 5, 1));
		ctx.fillStyle = "#1d1a22";
		ctx.fillRect(-4, -36, 2.4, 3);
		ctx.fillRect(1.6, -36, 2.4, 3);
		ctx.fillRect(-2.5, -31, 5, 1.4);
		fill(ctx, "rgba(143,240,226,0.4)", () => ctx.arc(0, -44, 6.5, 0, TAU$2));
		fill(ctx, "#8ff0e2", () => ctx.arc(0, -44, 3.6, 0, TAU$2));
		fill(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-1.2, -45.2, 1.1, 0, TAU$2));
	}
	/** 畫一個小人（腳底中心在 (0, 0)）。facing：south ＝ 正面、north ＝ 背面、east／west ＝ 側面（西 ＝ 東的左右鏡像）。C 畫風（Phase C-1a）。 */
	/** `pose`（6M-1）：骨架姿勢（inkPose.ts）；不給＝和加鉤子之前逐像素相同。圖騰柱不吃姿勢。 */
	function drawFigure(ctx, spec, facing, ground = true, pose = null) {
		if (spec.totem === true) {
			drawTotem(ctx);
			return;
		}
		const view = facing === "north" ? "back" : facing === "south" ? "front" : "side";
		if (dollSkin() === "q") {
			if (ground) {
				ctx.fillStyle = "rgba(0,0,0,0.25)";
				ctx.beginPath();
				ctx.ellipse(0, 0, Q_SHADOW[0], Q_SHADOW[1], 0, 0, TAU$2);
				ctx.fill();
			}
			qStampLocal(ctx, qUnitOf(spec), view, facing === "west", GAME_HOOKS, qPoseOf(pose));
			return;
		}
		ctx.save();
		if (facing === "west") ctx.scale(-1, 1);
		drawInkFigure(ctx, spec, view, HOOKS, ground, pose);
		ctx.restore();
	}
	/** Q 版地上影子的半徑（同 closeups 的影子：38／3.4 × 7／3.4 單位）。 */
	var Q_SHADOW = [11.2, 2.1];
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/qBoss.ts
	/** 單位範本 → 頭目畫法。 */
	var BOSS_TEMPLATES = {
		ashen_heart: "ah",
		rift_shard_lord: "sl"
	};
	/** 各頭目的階段數（不認得 → 預設）。 */
	var PHASES = {
		ah: 3,
		sl: 4
	};
	/** 範本 → 頭目與階段；不是頭目 → null。灰燼之心沒有階段資料時：有熔殼＝1、沒有＝2。 */
	function bossOf(template, phase, statuses = []) {
		const id = template !== void 0 ? BOSS_TEMPLATES[template] : void 0;
		if (id === void 0) return null;
		let p = typeof phase === "number" && Number.isInteger(phase) && phase >= 1 && phase <= PHASES[id] ? phase : 0;
		if (p === 0) p = id === "ah" ? statuses.includes("molten_shell") ? 1 : 2 : 1;
		return {
			id,
			phase: p
		};
	}
	var LAYER_BOX = [
		-100,
		-130,
		100,
		20
	];
	var OUT$1 = QC_OUT;
	var clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
	var rnd = (key, k = 0) => seedOf(`${key}:${k}`) % 1e4 / 1e4;
	var seam = (c) => mix$1(c, OUT$1, .55);
	function poly(g, pts, c, line = true) {
		g.beginPath();
		pts.forEach(([x, y], i) => i > 0 ? g.lineTo(x, y) : g.moveTo(x, y));
		g.closePath();
		g.fillStyle = c;
		g.fill();
		if (line) {
			g.strokeStyle = seam(c);
			g.lineWidth = .6;
			g.lineJoin = "round";
			g.stroke();
		}
	}
	function ell(g, x, y, rx, ry, c, opt = {}) {
		g.beginPath();
		g.ellipse(x, y, rx, ry, opt.rot ?? 0, 0, TAU$2);
		g.fillStyle = c;
		g.fill();
		if (opt.line !== false) {
			g.strokeStyle = seam(c);
			g.lineWidth = .6;
			g.stroke();
		}
	}
	function line(g, pts, w, c) {
		g.save();
		g.strokeStyle = c;
		g.lineWidth = w;
		g.lineCap = "round";
		g.lineJoin = "round";
		g.beginPath();
		pts.forEach(([x, y], i) => i > 0 ? g.lineTo(x, y) : g.moveTo(x, y));
		g.stroke();
		g.restore();
	}
	/** 平塗光暈：3 圈半透明同心圓（取代 C 的放射漸層）。 */
	function flatGlow(ctx, x, y, r, c, a) {
		ctx.save();
		ctx.fillStyle = c;
		for (const [k, al] of [
			[1, .16],
			[.72, .2],
			[.46, .26]
		]) {
			ctx.globalAlpha = al * a;
			ctx.beginPath();
			ctx.arc(x, y, r * k, 0, TAU$2);
			ctx.fill();
		}
		ctx.restore();
	}
	/** 有 DOM：剪影外框層；沒有（測試）：直接平塗。 */
	function layer(ctx, draw, o) {
		if (hasDom() && typeof ctx.getTransform === "function") {
			qLayer(ctx, LAYER_BOX, draw, o);
			return;
		}
		ctx.save();
		draw(ctx);
		ctx.restore();
	}
	var GOLD = "#ffbf3a";
	/** 頭目外光（QK-4b，同樣張 qBoss.js GLOW_W／GLOW_A）：沿輪廓一圈＝黑外框再往外 2.2 單位的實心半透明色帶。 */
	var BOSS_GLOW_W = 2.2;
	var BOSS_GLOW_A = .8;
	/** 頭目照 huge 尺寸畫（QK-4b，同樣張 QBoss.SIZE＝QCreature.SIZES.huge）：戰場上整隻（含外光）×1.6，腳底在自己那格。 */
	var BOSS_FIELD_SCALE = 1.6;
	/** 待機一圈的長度（毫秒）。 */
	var IDLE_LOOP_MS = 5278;
	/** 線性循環（圈數）：一般＝t／週期；待機一圈時取整成整數圈。 */
	function cyc(t, period, loop) {
		if (loop === void 0) return t / period;
		return 1200 / period + Math.max(1, Math.round(IDLE_LOOP_MS / period)) * loop;
	}
	/**
	* 振盪的相位（弧度）：一般＝t／週期；待機一圈（loop＝0～1）時把週期取整成一圈的整數次（QK-4b：碎晶之主待機接回第一格不跳），
	* 起點同 t＝1200。
	*/
	function osc(t, period, loop) {
		if (loop === void 0) return t / period;
		const n = Math.max(1, Math.round(IDLE_LOOP_MS / (TAU$2 * period)));
		return 1200 / period + TAU$2 * n * loop;
	}
	var BASALT$1 = "#4a3b36";
	var BASALT_L = "#6a5a52";
	var LAVA = "#ff6a1a";
	var LAVA_HOT = "#ffd23a";
	var CORE = "#ffb23a";
	/** 殼片：[名稱, 掛點 x, 掛點 y, 旋轉, 寬, 高]（和 bossArt.js 的 PLATES 同一份）。 */
	var PLATES = [
		[
			"p-back-l",
			-20,
			-34,
			-.5,
			18,
			13
		],
		[
			"p-back-r",
			20,
			-34,
			.5,
			18,
			13
		],
		[
			"p-top",
			0,
			-44,
			0,
			20,
			12
		],
		[
			"p-left",
			-26,
			-20,
			-.9,
			16,
			14
		],
		[
			"p-right",
			26,
			-20,
			.9,
			16,
			14
		],
		[
			"p-low-l",
			-18,
			-8,
			-.3,
			20,
			12
		],
		[
			"p-low-r",
			18,
			-8,
			.3,
			20,
			12
		],
		[
			"p-front",
			0,
			-12,
			0,
			22,
			12
		],
		[
			"p-mid-l",
			-12,
			-30,
			-.2,
			14,
			11
		],
		[
			"p-mid-r",
			12,
			-30,
			.2,
			14,
			11
		]
	];
	/** 一片甲蟲殼（Q）：圓背甲＋中線＋鋸齒殼縫（熱度越高越黃）＋左上一塊亮面。 */
	function plate(g, w, h, heat) {
		ell(g, 0, 0, w / 2, h / 2, BASALT_L);
		g.save();
		g.beginPath();
		g.ellipse(0, 0, w / 2, h / 2, 0, 0, TAU$2);
		g.clip();
		ell(g, -w * .16, -h * .18, w * .22, h * .16, lighten(BASALT_L, .22), {
			line: false,
			rot: -.3
		});
		g.restore();
		line(g, [[0, -h / 2 + .8], [0, h / 2 - .8]], .9, OUT$1);
		const z = [
			[-w * .34, .6],
			[-w * .17, -1.2],
			[0, 1],
			[w * .17, -1],
			[w * .34, .8]
		];
		line(g, z, 2, "#7a2a08");
		line(g, z, 1, mix$1(LAVA, LAVA_HOT, clamp(heat)));
	}
	function heartCore(g, cx, cy, breath, crack, die = 0) {
		const s = (1 + .06 * breath) * (1 - .55 * die);
		g.save();
		g.translate(cx, cy);
		g.scale(s, s);
		const pts = [
			[0, -15],
			[10, -8],
			[11, 4],
			[4, 13],
			[-6, 12],
			[-11, 3],
			[-9, -9]
		];
		let c = mix$1(CORE, "#fff4d0", .35 * breath + .4 * crack);
		if (die > 0) c = mix$1(c, "#5a4a44", die);
		poly(g, pts, c);
		g.save();
		g.beginPath();
		pts.forEach(([x, y], i) => i > 0 ? g.lineTo(x, y) : g.moveTo(x, y));
		g.closePath();
		g.clip();
		poly(g, [
			[0, -15],
			[-9, -9],
			[-11, 3],
			[1, 0]
		], lighten(c, .35), false);
		poly(g, [
			[11, 4],
			[4, 13],
			[1, 0]
		], darken(c, .12), false);
		g.restore();
		g.fillStyle = "#ffffff";
		g.fillRect(-5, -9, 2.2, 4.4);
		g.fillRect(-2, -10.4, 1.4, 1.4);
		if (crack > 0) {
			g.save();
			g.globalAlpha = clamp(crack);
			line(g, [
				[-2, -12],
				[2, -4],
				[-1, 3],
				[3, 10]
			], 1.6, "#ffffff");
			line(g, [
				[8, -6],
				[3, -2],
				[7, 6]
			], 1.3, "#fff4c0");
			g.restore();
		}
		g.restore();
	}
	/** 殼片的掛點：熔殼在＝貼著並隨呼吸張開；脫落＝依名稱雜湊飛出、落地（落點收在 ±36，不超過 2 格寬）。 */
	function plateAnchor(p, shell, bt, breath) {
		const [key, x, y, r] = p;
		if (shell > 0) {
			const open = .6 * breath;
			return {
				x: x * (1 + .02 * open),
				y: y - open * .6,
				r,
				a: 1
			};
		}
		const dir = Math.sign(x || rnd(key) - .5) || 1;
		const spin = (rnd(key, 3) - .5) * 6;
		const fx = Math.max(-36, Math.min(36, x * 1.15 + dir * (4 + 4 * rnd(key, 1))));
		const fy = -2 - 2 * rnd(key, 4);
		const hop = 14 + 12 * rnd(key, 2);
		if (bt >= 1) return {
			x: fx,
			y: fy,
			r: r + spin * .8,
			a: .8
		};
		const u = clamp(bt);
		return {
			x: x + (fx - x) * u,
			y: y + (fy - y) * u * u - hop * Math.sin(Math.PI * u),
			r: r + spin * .8 * u,
			a: 1
		};
	}
	var num = (v, d) => typeof v === "number" && Number.isFinite(v) ? v : d;
	/** 灰燼之心（Q）。腳底 (0,0)，寬約 76 單位。外光＝沿輪廓的傳說金（QK-4b）；核心光暈只在火焰箭蓄力（flare）時亮。 */
	function drawAshenHeart(ctx, st = {}, opt = {}) {
		const t = num(st.t, 0);
		const lp = st.loop;
		const breath = .5 + .5 * Math.sin(osc(t, 420, lp));
		const phase = st.phase === 2 || st.phase === 3 ? st.phase : 1;
		const crack = phase === 3 ? .6 + .4 * Math.sin(osc(t, 160, lp)) : 0;
		const shell = clamp(num(st.shell, phase === 1 ? 1 : 0));
		const bt = clamp(num(st.breakT, shell > 0 ? 0 : 1));
		const inhale = clamp(num(st.inhale, 0));
		const spout = clamp(num(st.spout, 0));
		const die = clamp(num(st.dieT, 0));
		const cy = -28 - inhale * 2 + 14 * die;
		opt.ring?.(ctx, 40);
		if (opt.ground !== false) {
			ctx.fillStyle = "rgba(10,8,14,0.35)";
			ctx.beginPath();
			ctx.ellipse(0, 0, 40, 8, 0, 0, TAU$2);
			ctx.fill();
		}
		if (opt.ground === "only") return;
		if (phase === 3) flatGlow(ctx, 0, -6, 50, "#ff6e1e", 1 - die);
		if (num(opt.flare, 0) > 0) flatGlow(ctx, 0, cy, 32 * (1 + .06 * breath), "#ffaa3c", num(opt.flare, 0));
		layer(ctx, (g) => {
			g.save();
			g.beginPath();
			g.moveTo(-38, 0);
			g.quadraticCurveTo(-36, -12, -20, -16);
			g.quadraticCurveTo(0, -20, 20, -16);
			g.quadraticCurveTo(36, -12, 38, 0);
			g.closePath();
			g.fillStyle = BASALT$1;
			g.fill();
			g.restore();
			for (const x of [
				-24,
				-8,
				10,
				26
			]) {
				ell(g, x, -6, 7, 4.4, BASALT_L);
				line(g, [[x - 5, -3], [x - 8, 0]], 1, OUT$1);
				ell(g, x + 6.4, -6.4, 2, 1.8, BASALT$1);
			}
			heartCore(g, 0, cy, breath, die > 0 ? crack * (1 - die) : crack, die);
			if (spout > 0) {
				g.save();
				g.fillStyle = LAVA;
				g.beginPath();
				g.moveTo(-6, -46);
				g.quadraticCurveTo(-9, -60 - 30 * spout, 0, -70 - 36 * spout);
				g.quadraticCurveTo(9, -60 - 30 * spout, 6, -46);
				g.closePath();
				g.fill();
				g.fillStyle = LAVA_HOT;
				g.beginPath();
				g.ellipse(0, -58 - 20 * spout, 2.6, 10 * spout, 0, 0, TAU$2);
				g.fill();
				g.restore();
			}
			for (const p of PLATES) {
				const A = plateAnchor(p, shell, bt, breath);
				g.save();
				g.globalAlpha = A.a;
				g.translate(A.x, A.y);
				g.rotate(A.r);
				plate(g, p[4], p[5], shell > 0 ? breath : .15);
				g.restore();
			}
		}, {
			glow: opt.glowOff === true || die > 0 ? null : opt.glow ?? GOLD,
			glowW: BOSS_GLOW_W,
			glowA: BOSS_GLOW_A,
			flash: num(opt.flash, 0)
		});
		const parts = [];
		if (inhale > 0) for (let k = 0; k < 12; k++) {
			const a = rnd("in", k) * TAU$2;
			const d = 60 * (1 - (t / 600 + rnd("in2", k)) % 1);
			parts.push([
				Math.cos(a) * d,
				cy + Math.sin(a) * d * .6,
				1.8,
				LAVA_HOT
			]);
		}
		if (phase === 3 && die < .3) for (let k = 0; k < 4; k++) {
			const ph = (cyc(t, 900, lp) + rnd("drip", k)) % 1;
			parts.push([
				-20 + k * 13,
				-14 + ph * 14,
				1.8,
				LAVA
			]);
		}
		if (parts.length > 0) layer(ctx, (g) => {
			for (const [x, y, r, c] of parts) {
				g.fillStyle = c;
				g.beginPath();
				g.arc(x, y, r, 0, TAU$2);
				g.fill();
			}
		}, {
			ow: .8,
			alpha: inhale > 0 && phase !== 3 ? Math.max(.3, inhale) : 1
		});
	}
	var CRYST = "#b8a8ff";
	var CRYST_D = "#7a6ae0";
	var RIFT = "#8a4ad0";
	var CORE2 = "#e0ffff";
	/** 掛點（相對身體原點；浮空的上下位移另外加）。Q 版：頭放大成 r≈11（大頭），軀幹縮短。 */
	var SL_ANCHORS = {
		head: [0, -62],
		torso: [0, -36],
		core2: [0, -40],
		"sh-l": [-17, -48],
		"sh-r": [17, -48],
		"hand-l": [-26, -36],
		"hand-r": [26, -36],
		...Object.fromEntries([
			0,
			1,
			2,
			3,
			4
		].map((k) => [`crown-${k}`, [-10 + k * 5, -73 - (k === 2 ? 5 : k % 2 ? 2.4 : 0)]])),
		...Object.fromEntries([
			0,
			1,
			2,
			3,
			4
		].map((k) => [`tail-${k}`, [0, -16 + k * 4.4]]))
	};
	var A = (k) => SL_ANCHORS[k] ?? [0, 0];
	function shard(g, x, y, len, wid, rot, color) {
		g.save();
		g.translate(x, y);
		g.rotate(rot);
		poly(g, [
			[0, -len],
			[wid, -len * .25],
			[wid * .6, len * .4],
			[0, len * .5],
			[-wid * .7, len * .3],
			[-wid, -len * .3]
		], color);
		poly(g, [
			[0, -len],
			[-wid, -len * .3],
			[-wid * .7, len * .3],
			[0, len * .5]
		], lighten(color, .3), false);
		g.restore();
	}
	function slBody(g, st, hover, cast, tint, phase, t) {
		g.save();
		g.translate(0, hover);
		const spread = phase === 4 ? 1.8 : 1;
		const orbs = phase >= 2 ? [
			0,
			1,
			2,
			3,
			4,
			5
		].map((k) => {
			const a = osc(t, 800, st.loop) + rnd("orb", k) * TAU$2;
			const r = 30 + 4 * Math.sin(osc(t, 300, st.loop) + k);
			return {
				k,
				a,
				x: Math.cos(a) * r,
				y: -38 + Math.sin(a) * r * .35,
				front: Math.sin(a) >= 0
			};
		}) : [];
		for (const o of orbs) if (!o.front) shard(g, o.x, o.y, 5, 2.8, o.a, tint(o.k % 2 ? RIFT : CRYST));
		for (let k = 0; k < 5; k++) {
			const ph = osc(t, 700, st.loop) + rnd("tail", k) * TAU$2;
			const [ax, ay] = A(`tail-${k}`);
			shard(g, ax + Math.sin(ph) * 3 * spread + (rnd("tx", k) - .5) * 8 * spread, ay + k * .6 * (spread - 1) * 5, 7 - k, 4.4 - k * .6, Math.sin(ph) * .3, tint(k % 2 ? CRYST_D : CRYST));
		}
		shard(g, A("sh-l")[0], A("sh-l")[1], 9, 4.4, -.9, tint(CRYST_D));
		shard(g, A("sh-r")[0], A("sh-r")[1], 9, 4.4, .9, tint(CRYST_D));
		poly(g, [
			[-14, -50],
			[14, -50],
			[9, -32],
			[3, -20],
			[-3, -20],
			[-9, -32]
		], tint(CRYST));
		poly(g, [
			[-14, -50],
			[0, -50],
			[0, -36],
			[-3, -20],
			[-9, -32]
		], tint(lighten(CRYST, .22)), false);
		line(g, [
			[-14, -50],
			[0, -38],
			[14, -50]
		], .7, tint(CRYST_D));
		const over = phase >= 3 ? .7 + .3 * Math.sin(osc(t, 130, st.loop)) : .4 + .2 * Math.sin(osc(t, 400, st.loop));
		const [cx, cy] = A("core2");
		poly(g, [
			[cx, cy - 6.4],
			[cx + 5.6, cy],
			[cx, cy + 6.4],
			[cx - 5.6, cy]
		], mix$1(phase === 4 ? "#ffc0d8" : CORE2, "#ffffff", over * .5));
		g.fillStyle = "#ffffff";
		g.fillRect(cx - 2, cy - 3, 1.6, 2.4);
		if (phase >= 3) line(g, [
			[cx - 2, cy - 5],
			[cx + 1, cy - 1],
			[cx - 1, cy + 4]
		], 1.2, "#ffffff");
		const [hx, hy] = A("head");
		for (let k = 0; k < 5; k++) {
			const [x, y] = A(`crown-${k}`);
			shard(g, x, y, 6 + (k === 2 ? 5 : 2), 2.6, (k - 2) * .24, tint(k === 2 ? CORE2 : CRYST));
		}
		poly(g, [
			[hx - 9, hy - 9],
			[hx + 9, hy - 9],
			[hx + 11.5, hy],
			[hx + 7, hy + 9],
			[hx - 7, hy + 9],
			[hx - 11.5, hy]
		], tint(lighten(CRYST, .15)));
		poly(g, [
			[hx - 9, hy - 9],
			[hx, hy - 9],
			[hx - 4, hy + 9],
			[hx - 7, hy + 9],
			[hx - 11.5, hy]
		], tint(lighten(CRYST, .35)), false);
		for (const x of [-4.2, 4.2]) if (phase >= 3) {
			g.fillStyle = OUT$1;
			g.fillRect(hx + x - 2.2, hy - 3, 4.4, 5.2);
			g.fillStyle = "#a0f0ff";
			g.fillRect(hx + x - 1.7, hy - 2.5, 3.4, 4.2);
			g.fillStyle = "#ffffff";
			g.fillRect(hx + x - 1.1, hy - 1.9, 2.2, 3);
			line(g, [[hx + x, hy - 5], [hx + x, hy - 3.4]], .7, "#ffffff");
			line(g, [[hx + x + 2.6, hy - .4], [hx + x + 3.8, hy - .4]], .7, "#ffffff");
		} else {
			g.fillStyle = OUT$1;
			g.fillRect(hx + x - 1.6, hy - 2.4, 3.2, 4);
			g.fillStyle = CORE2;
			g.fillRect(hx + x - 1, hy - 1.8, 2, 2.8);
		}
		let hxr = 26 + 16 * cast;
		let hyr = -36 - 4 * Math.sin(osc(t, 360, st.loop));
		let hrot = .4 + 1.2 * cast;
		if (typeof st.swingA === "number") {
			const a = st.swingA;
			const R0 = num(st.swingR, 15);
			hxr = A("sh-r")[0] + Math.cos(a) * R0;
			hyr = A("sh-r")[1] + Math.sin(a) * R0;
			hrot = a - .53;
		}
		shard(g, -hxr + 30 * cast, hyr + 4, 9.5, 5.4, -.4 + 1.6 * cast, tint(CRYST));
		shard(g, hxr, hyr, 9.5, 5.4, hrot, tint(CRYST));
		for (const o of orbs) if (o.front) shard(g, o.x, o.y, 5, 2.8, o.a, tint(o.k % 2 ? RIFT : CRYST));
		g.restore();
		return [hxr, hyr + hover];
	}
	/** 碎晶之主（Q）。正面對稱；東側（朝西）時呼叫端整隻鏡像。外光預設傳說金（`glow: false` 不畫）。 */
	function drawShardLord(ctx, st = {}, opt = {}) {
		const die = clamp(num(st.dieT, 0));
		const t = num(st.t, 0);
		const phase = st.phase === 2 || st.phase === 3 || st.phase === 4 ? st.phase : 1;
		const hover = (-10 - 3 * Math.sin(osc(t, 500, st.loop))) * (1 - die);
		const cast = clamp(num(st.cast, 0));
		const blink = clamp(num(st.blink, 0));
		const tint = phase === 4 ? (c) => mix$1(c, "#ff5a8a", .35) : (c) => c;
		opt.ring?.(ctx, 26);
		if (opt.ground !== false) {
			ctx.fillStyle = "rgba(10,8,14,0.3)";
			ctx.beginPath();
			ctx.ellipse(0, 0, 24, 5, 0, 0, TAU$2);
			ctx.fill();
		}
		if (opt.ground === "only") return;
		flatGlow(ctx, 0, hover - 40, 24, phase === 4 ? "#ff5a8c" : "#a0f0ff", (phase >= 3 ? 1 : .7) * (1 - die));
		if (blink > 0) for (const [gx, al] of [[2, .35], [1, .55]]) {
			ctx.save();
			ctx.translate(-gx * 16, 0);
			layer(ctx, (o) => void slBody(o, st, hover, cast, tint, phase, t), {
				alpha: al * blink,
				flat: tint("#c8b8ff")
			});
			ctx.restore();
		}
		if (phase === 1 && st.channel !== false) for (let k = 0; k < 3; k++) {
			const a = [
				-2.75,
				-.4,
				-2.25
			][k];
			const c = [
				"#ff7a2a",
				"#9ad8c8",
				"#c8a0ff"
			][k];
			const p0 = [Math.cos(a) * 95, hover - 40 + Math.sin(a) * 70];
			const p1 = [0, hover - 40];
			ctx.save();
			ctx.globalAlpha = .75 + .2 * Math.sin(osc(t, 200, st.loop) + k);
			line(ctx, [p0, p1], 4.4, OUT$1);
			line(ctx, [p0, p1], 3, c);
			line(ctx, [p0, p1], .9, "#ffffff");
			ctx.restore();
		}
		const lo = {
			glow: opt.glowOff === true || die > 0 ? null : opt.glow ?? GOLD,
			glowW: BOSS_GLOW_W,
			glowA: BOSS_GLOW_A
		};
		if ((opt.flash ?? 0) > 0) lo.flash = opt.flash ?? 0;
		if (die > 0) {
			ctx.save();
			ctx.globalAlpha = 1 - .55 * die;
			layer(ctx, (g) => {
				g.scale(1 + .3 * die, 1 - .62 * die);
				slBody(g, {
					...st,
					phase: 4
				}, hover, 0, phase === 4 ? tint : (c) => mix$1(c, "#6a6480", .5 * die), 4, t);
			}, lo);
			ctx.restore();
			return;
		}
		let hand = [0, 0];
		layer(ctx, (g) => {
			hand = slBody(g, st, hover, cast, tint, phase, t);
		}, lo);
		if (cast > 0) {
			const [hx, hy] = hand;
			layer(ctx, (g) => {
				g.fillStyle = "#d8b8ff";
				g.beginPath();
				g.arc(hx + 10, hy, 4.4 * cast, 0, TAU$2);
				g.fill();
				g.fillStyle = "#ffffff";
				g.beginPath();
				g.arc(hx + 10, hy, 2 * cast, 0, TAU$2);
				g.fill();
			}, { ow: .9 });
			flatGlow(ctx, hx + 10, hy, 16, "#c8a0ff", cast);
		}
	}
	var kfB = (u, pts) => {
		const first = pts[0];
		if (u <= first[0]) return first[1];
		for (let i = 1; i < pts.length; i++) {
			const [b, vb] = pts[i];
			if (u <= b) {
				const [a, va] = pts[i - 1];
				const x = (u - a) / (b - a || 1);
				return va + (vb - va) * x * x * (3 - 2 * x);
			}
		}
		return pts[pts.length - 1][1];
	};
	var segB = (u, a, b) => clamp((u - a) / (b - a));
	var bumpB = (u, a, b) => Math.sin(Math.PI * segB(u, a, b));
	/** 頭目的片段（含待機）。 */
	var BOSS_CLIPS = {
		ah: [
			"spout",
			"firebolt",
			"ram",
			"hit",
			"death"
		],
		sl: [
			"thunder",
			"swing",
			"hit",
			"death"
		]
	};
	/** 片段長度（毫秒）。待機 16 格一圈（灰燼之心呼吸兩次）。 */
	var BOSS_MS = {
		idle: 5278,
		spout: 1300,
		firebolt: 950,
		ram: 900,
		thunder: 1e3,
		swing: 800,
		hit: 400,
		death: 1500
	};
	/**
	* CB-4b：戰場上頭目貼圖（朝東、腳底原點、不含大小）裡，東西向相鄰目標格中心的 x（單位）＝ 一格 48 px 換回單位 ≈ 30.66。
	* 片段裡的「相鄰目標」點 `CREATURE_FX_TARGET_X`（52）在頭目放大後落在 81.4 px，比目標格中心多約 33 px。
	*/
	var BOSS_EW_TARGET_X = 52 / (DOLL_SCALE * BOSS_FIELD_SCALE);
	/**
	* CB-4b（美術驗收 `QI-2c-2d-3a-3b驗收.md` 第 5.3 節）：東西向（同一排、特效畫進身體貼圖）時片段特效的位置。
	* 只改灰燼之心 `ram`：星爆（接觸點）水平放在目標格中心（同正南北的 0；高度照片段）；塵土照剪切跟著目標格
	* （相對「相鄰目標」點的距離照舊、原點換成目標格中心 → 往施放者側 8 單位 ≈ 12.5 px，同南北、斜向）。其他片段、碎晶之主原樣回傳。
	*/
	function bossSameRowFx(who, clip, fx) {
		if (who !== "ah" || clip !== "ram") return fx;
		return fx.map((f) => {
			if (f.k === "burst") return {
				...f,
				x: BOSS_EW_TARGET_X
			};
			if (f.k === "dust") return {
				...f,
				x: BOSS_EW_TARGET_X + (f.x ?? 0) - 52
			};
			return f;
		});
	}
	/** 依動作類型挑頭目的攻擊片段（不認得的類型 → 該頭目的普攻）。 */
	function bossAttackClip(id, type0, phase) {
		const type = type0 === "melee2" ? "melee" : type0;
		if (id === "ah") {
			if (type === "area") return "spout";
			if ((type === "melee" || type === "charge") && phase === 1) return "ram";
			return "firebolt";
		}
		return type === "cast" || type === "area" || type === "breath" ? "thunder" : "swing";
	}
	/**
	* 畫頭目的一個片段在 u（0～1，已量化）的那一格（腳底 (0,0)，呼叫端已縮放／鏡像）。`clip`：idle、spout、firebolt、ram、thunder、swing、hit、death；
	* 不認得 → 靜態。opt.reduce：姿勢固定在當下階段的靜止狀態，只留白閃與特效；倒下直接最後一格。
	*/
	function bossAct(ctx, who, clip, u0, opt = {}) {
		const P = bossPlan(who, clip, u0, opt);
		const base = {
			ring: opt.ring,
			ground: opt.ground ?? true
		};
		ctx.save();
		ctx.translate(P.dx, 0);
		if (P.rot) {
			const [px, py] = P.who === "ah" ? [-30, 0] : [0, -40];
			ctx.translate(px, py);
			ctx.rotate(P.rot);
			ctx.translate(-px, -py);
		}
		if (P.who === "ah") drawAshenHeart(ctx, P.st, {
			...P.o,
			...base
		});
		else drawShardLord(ctx, P.st, {
			...P.o,
			...base
		});
		ctx.restore();
		const fx = opt.sameRow === true ? bossSameRowFx(who, clip, P.fx) : P.fx;
		if (fx.length > 0 && opt.ground !== "only" && opt.noFx !== true) drawCreatureFx(ctx, opt.fxAll === true ? fx : fx.filter((f) => f.ranged !== true), void 0, [
			-110,
			-160,
			120,
			20
		]);
	}
	function bossPlan(who, clip, u0, opt = {}) {
		const c = clip === "idle" || (BOSS_CLIPS[who] ?? []).includes(clip) ? clip : "static";
		const ms = BOSS_MS[c] ?? 0;
		let u = clamp(u0);
		if (opt.reduce === true && c === "death") u = 1;
		const tt = c === "idle" ? 1200 + u * ms : opt.reduce === true || c === "static" ? 1200 : 1200 + u * ms;
		const fx = [];
		const o = { flash: Math.max(opt.flash ?? 0, c === "hit" && u < .2 ? .9 : c === "death" && u < .12 ? .7 : 0) };
		let dx = 0;
		let rot = 0;
		if (who === "ah") {
			const ph = opt.phase === 2 || opt.phase === 3 ? opt.phase : 1;
			const lp = c === "idle" ? { loop: u } : {};
			const phaseSt = ph === 1 ? {
				phase: 1,
				shell: 1,
				t: tt,
				...lp
			} : {
				phase: ph,
				shell: 0,
				breakT: 1,
				t: tt,
				...lp
			};
			let st = { ...phaseSt };
			if (c === "spout") {
				st = {
					phase: 1,
					shell: 1,
					t: tt,
					inhale: bumpB(u, 0, .42),
					spout: kfB(u, [
						[0, 0],
						[.4, 0],
						[.52, 1],
						[.8, .9],
						[1, 0]
					])
				};
				if (u > .5) {
					const k = segB(u, .5, 1);
					fx.push({
						k: "ring",
						x: 0,
						rx: 30 + 40 * k,
						c: LAVA,
						a: 1 - k
					}, {
						k: "ring",
						x: 0,
						rx: 22 + 26 * k,
						c: LAVA_HOT,
						a: (1 - k) * .8
					});
					for (let i = 0; i < 6; i++) {
						const an = -Math.PI * (.1 + .8 * (i / 5));
						const d = 20 + 50 * k;
						fx.push({
							k: "orb",
							x: Math.cos(an) * d,
							y: -2 - 46 * Math.sin(Math.PI * k) * (.6 + .4 * (i % 2)),
							r: 2.4,
							c: LAVA,
							c2: LAVA_HOT,
							a: 1 - .5 * k
						});
					}
				}
			} else if (c === "firebolt") {
				o.flare = .6 * bumpB(u, .05, .55);
				if (u > .08 && u < .46) fx.push({
					k: "orb",
					x: 0,
					y: -28,
					r: 3 + 4 * segB(u, .08, .46),
					c: LAVA,
					c2: LAVA_HOT
				});
				if (u >= .46 && u <= .72) fx.push({
					k: "orb",
					x: 6 + 78 * segB(u, .46, .72),
					y: -28 + 8 * segB(u, .46, .72),
					r: 4.4,
					c: LAVA,
					c2: LAVA_HOT,
					tail: 1,
					ranged: true
				});
				if (u > .72) {
					const k = segB(u, .72, 1);
					fx.push({
						k: "glow",
						x: 84,
						y: -20,
						r: 14 + 6 * k,
						c: LAVA,
						a: 1 - k,
						ranged: true
					}, {
						k: "burst",
						x: 84,
						y: -20,
						r: 7 + 4 * k,
						c: LAVA,
						c2: LAVA_HOT,
						a: 1 - k,
						ranged: true
					});
				}
			} else if (c === "ram") {
				st = {
					phase: 1,
					shell: 1,
					t: 1200 + 900 * bumpB(u, .1, .55)
				};
				dx = kfB(u, [
					[0, 0],
					[.35, -5],
					[.55, 10],
					[.68, 8],
					[1, 0]
				]);
				rot = kfB(u, [
					[0, 0],
					[.35, -.06],
					[.55, .08],
					[1, 0]
				]);
				if (u > .52 && u < .8) {
					const k = segB(u, .52, .8);
					fx.push({
						k: "burst",
						x: 50,
						y: -24,
						r: 7 + 4 * k,
						c: "#ffffff",
						c2: "#ffe08a",
						a: 1 - k
					}, {
						k: "dust",
						x: 44,
						y: -1,
						r: 6,
						a: 1 - k
					});
				}
			} else if (c === "hit") dx = u < .6 ? 1.6 * Math.sign(Math.sin(u * 60)) * (1 - u / .6) : 0;
			else if (c === "death") {
				st = {
					phase: 3,
					shell: 0,
					breakT: 1,
					t: tt,
					dieT: segB(u, .25, 1)
				};
				dx = u < .3 ? 1.4 * Math.sign(Math.sin(u * 90)) : 0;
				if (u > .55 && u < .95) fx.push({
					k: "dust",
					x: 0,
					y: -1,
					r: 12,
					a: 1 - segB(u, .55, .95)
				});
			}
			if (opt.reduce === true) {
				dx = 0;
				rot = 0;
				if (c !== "death") st = { ...phaseSt };
				delete o.flare;
			}
			return {
				who: "ah",
				st,
				dx,
				rot,
				fx,
				o
			};
		}
		{
			const phaseSt = {
				phase: opt.phase === 1 || opt.phase === 3 || opt.phase === 4 ? opt.phase : 2,
				t: tt,
				...c === "idle" ? { loop: u } : {}
			};
			let st = { ...phaseSt };
			if (c === "thunder") {
				st.cast = kfB(u, [
					[0, 0],
					[.35, 1],
					[.8, 1],
					[1, 0]
				]);
				const hand = [26 + 16 * (opt.reduce === true ? 0 : st.cast) + 10, -46];
				if (u > .15 && u < .45) fx.push({
					k: "glow",
					x: hand[0],
					y: hand[1],
					r: 8 + 8 * segB(u, .15, .45),
					c: "#fff36b",
					a: .8
				});
				if (u >= .45 && u <= .75) fx.push({
					k: "bolt",
					x0: hand[0],
					y0: hand[1],
					x1: 84,
					y1: -18,
					c: "#fff36b",
					amp: 1.4 + .6 * Math.sin(u * 80),
					ranged: true
				}, {
					k: "glow",
					x: 84,
					y: -18,
					r: 14,
					c: "#fff36b",
					a: .9,
					ranged: true
				});
			} else if (c === "swing") {
				st.swingA = kfB(u, [
					[0, .93],
					[.35, -2.2],
					[.55, .7],
					[.7, .75],
					[1, .93]
				]);
				st.swingR = kfB(u, [
					[0, 15],
					[.35, 20],
					[.55, 26],
					[.7, 25],
					[1, 15]
				]);
				dx = kfB(u, [
					[0, 0],
					[.35, -2],
					[.55, 6],
					[1, 0]
				]);
				if (u > .45 && u < .68) fx.push({
					k: "slash",
					x: 44,
					y: -38,
					r: 14,
					c: "#e0d8ff",
					a: 1 - segB(u, .45, .68) * .7,
					len: 1.4
				});
			} else if (c === "hit") {
				dx = -kfB(u, [
					[0, 0],
					[.18, 5],
					[1, 0]
				]);
				rot = -.06 * kfB(u, [
					[0, 0],
					[.18, 1],
					[1, 0]
				]);
			} else if (c === "death") {
				st = {
					phase: 3,
					t: tt,
					dieT: segB(u, .2, 1)
				};
				dx = u < .25 ? 1.4 * Math.sign(Math.sin(u * 90)) : 0;
			}
			if (opt.reduce === true) {
				dx = 0;
				rot = 0;
				if (c !== "death") st = { ...phaseSt };
			}
			return {
				who: "sl",
				st,
				dx,
				rot,
				fx,
				o
			};
		}
	}
	/** 片段名（`CreaturePose.clip`）→ 頭目片段：idle、move（不動）→ 待機；atk:xxx → xxx；hit、death 照舊。 */
	function bossClipOf(boss, clip) {
		if (clip === void 0) return "static";
		if (clip === "move") return "idle";
		if (clip.startsWith("atk:@")) return bossAttackClip(boss.id, clip.slice(5), boss.phase);
		return clip.startsWith("atk:") ? clip.slice(4) : clip;
	}
	/** inkCreature 用：畫頭目貼圖的一格（呼叫端已平移到腳底、鏡像）。 */
	function drawBossFrame(ctx, boss, pose, ground) {
		ctx.save();
		if (pose !== null && ground !== "only") applyCreaturePose(ctx, pose);
		const flash = pose === null ? 0 : cp(pose, "flash");
		bossAct(ctx, boss.id, bossClipOf(boss, pose?.clip), pose?.u ?? 0, {
			phase: boss.phase,
			ground,
			fxAll: pose?.fxAll === true,
			flash,
			...pose?.fxTurn === void 0 ? { sameRow: true } : { noFx: true }
		});
		ctx.restore();
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/inkCreature.ts
	var CRYSTAL = "#9a86ff";
	/** Q 版玄武岩（C 的 #3b2c28 提亮一階，黑外框裡才看得出形狀）。 */
	var BASALT = "#4a3631";
	var MAGMA_ELEM = { holy: ["#fff4dc", "#ffbf3a"] };
	var MAGMA_CROSS = { holy: "#fffbe8" };
	var CRYSTAL_SHADOW = "#4e3a8e";
	var OUT = QC_OUT;
	var INK = OUT;
	var MATERIALS = [
		"fur",
		"magma",
		"crystal",
		"stone",
		"wood",
		"mist"
	];
	var SIZES = {
		tiny: .62,
		small: .8,
		medium: 1,
		large: 1.25,
		huge: 1.6
	};
	/** 戰場上的大小（Phase 5A-ART5，`docs/archive/art/5A-ART檢查.md` 1）：tiny、small 放大，medium 以上不變；樣張頁與其他畫面照 `SIZES`。 */
	var FIELD_SIZES = {
		...SIZES,
		tiny: .8,
		small: .9
	};
	/** 精英的大小倍率（頭目不乘）。 */
	var ELITE_SCALE = 1.15;
	/** 頭目外光色（同紙娃娃 `RARITY_GLOW`）。 */
	var CREATURE_GLOW = {
		epic: "#b06cff",
		legendary: "#ffbf3a"
	};
	var isMaterial = (m) => m != null && MATERIALS.includes(m);
	function paletteOf(material, element, tint, fur, lite = false) {
		const el = element === void 0 ? void 0 : CREATURE_ELEM[element];
		let base;
		let accent;
		let eye;
		if (material === "magma") {
			const me = (element !== void 0 ? MAGMA_ELEM[element] : void 0) ?? el;
			base = tint ?? "#4a3631";
			accent = me?.[0] ?? FIRE[0];
			eye = me?.[1] ?? FIRE[1];
		} else if (material === "stone") {
			base = tint ?? "#7f8f94";
			accent = el?.[0] ?? "#8fe3ff";
			eye = el?.[1] ?? "#e8fbff";
		} else if (material === "wood") {
			base = tint ?? "#a8763e";
			accent = el?.[0] ?? null;
			eye = "#2b1e16";
		} else if (material === "mist") {
			base = tint ?? (el !== void 0 ? mix$1("#e6ecef", el[0], .45) : "#e6ecef");
			accent = el?.[0] ?? "#b8c4cc";
			eye = el?.[1] ?? "#5a6a7a";
		} else if (material === "crystal") {
			base = element === "shadow" ? CRYSTAL_SHADOW : el !== void 0 ? mix$1(CRYSTAL, el[0], .4) : tint ?? CRYSTAL;
			accent = el?.[1] ?? "#e4dcff";
			eye = "#ffffff";
		} else {
			base = tint ?? fur;
			if (el !== void 0) base = mix$1(base, el[0], .22);
			accent = el?.[0] ?? null;
			eye = el?.[1] ?? "#ffd23a";
		}
		return {
			mat: material,
			base,
			d: darken(base, .28),
			l: lighten(base, .3),
			accent,
			eye,
			cross: material === "magma" && element !== void 0 ? MAGMA_CROSS[element] : void 0,
			sharp: material === "crystal" || material === "stone",
			alpha: material === "mist" ? .62 : void 0,
			lite
		};
	}
	var S = {
		qhead: null,
		inHead: false,
		headDone: false,
		pose: null,
		groups: null,
		pivots: null,
		last: "body",
		depth: 0
	};
	function headHook(ctx, key) {
		const q = S.qhead;
		if (q === null) return;
		const end = q[4];
		if (S.inHead && end !== void 0 && key.startsWith(end)) {
			ctx.restore();
			S.inHead = false;
			S.headDone = true;
			return;
		}
		if (S.inHead || S.headDone || !key.startsWith(q[0])) return;
		const [, x, y, s] = q;
		S.inHead = true;
		ctx.save();
		ctx.translate(x, y);
		ctx.scale(s, s);
		ctx.translate(-x, -y);
	}
	var UNIVERSAL = [["tr-scar", "head"], ["af-bz", "head"]];
	function groupOf(key) {
		for (const [p, g] of S.groups ?? []) if (key.startsWith(p)) return g;
		for (const [p, g] of UNIVERSAL) if (key.startsWith(p)) return g;
		return "body";
	}
	/** 套一組的變換（呼叫端 save 過）；沒有這組時回傳 false。 */
	function applyPartXf(ctx, f, pivot) {
		if (f === void 0) return false;
		const [px, py] = f.pivot ?? pivot;
		ctx.save();
		ctx.translate(px + (f.dx ?? 0), py + (f.dy ?? 0));
		if (f.rot) ctx.rotate(f.rot);
		if (f.kx) ctx.transform(1, 0, f.kx, 1, 0, 0);
		ctx.scale(f.sx ?? 1, f.sy ?? 1);
		ctx.translate(-px, -py);
		if (f.a !== void 0) ctx.globalAlpha *= Math.max(0, Math.min(1, f.a));
		return true;
	}
	/** QK-4b 斷塊：同一組畫好幾次，每次只畫 clip 多邊形裡的那一塊（傀儡崩塌）。 */
	function drawSplit(ctx, pieces, fn) {
		for (const q of pieces) {
			ctx.save();
			const [px, py] = q.pivot ?? [0, 0];
			ctx.translate(px + (q.dx ?? 0), py + (q.dy ?? 0));
			if (q.rot) ctx.rotate(q.rot);
			ctx.translate(-px, -py);
			ctx.beginPath();
			q.clip.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
			ctx.closePath();
			ctx.clip();
			fn();
			ctx.restore();
		}
	}
	function inPart(ctx, g, fn) {
		if (S.pose === null || S.depth > 0) {
			fn();
			return;
		}
		S.depth++;
		const on = applyPartXf(ctx, S.pose.parts[g], S.pivots?.[g] ?? [0, 0]);
		try {
			const sp = S.pose.split?.[g];
			if (sp) drawSplit(ctx, sp, fn);
			else fn();
		} finally {
			if (on) ctx.restore();
			S.depth--;
		}
	}
	function part(ctx, key, fn) {
		headHook(ctx, key);
		if (S.pose === null) {
			fn();
			return;
		}
		S.last = groupOf(key);
		inPart(ctx, S.last, fn);
	}
	function mark(key) {
		if (S.pose !== null) S.last = groupOf(key);
	}
	/** 圓潤的部件用「中點二次曲線」（不抖）。 */
	function smooth(ctx, pts, closed = true) {
		ctx.beginPath();
		const n = pts.length;
		const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
		if (!closed) {
			ctx.moveTo(pts[0][0], pts[0][1]);
			for (let i = 1; i < n - 1; i++) {
				const m = mid(pts[i], pts[i + 1]);
				ctx.quadraticCurveTo(pts[i][0], pts[i][1], m[0], m[1]);
			}
			ctx.lineTo(pts[n - 1][0], pts[n - 1][1]);
			return;
		}
		const m0 = mid(pts[n - 1], pts[0]);
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
	/** 平塗一塊；部件之間一條細縫線（本色加深），外輪廓由剪影外框負責。 */
	function ink(ctx, key, pts, color, opt = {}) {
		part(ctx, key, () => {
			ctx.save();
			outline(ctx, pts, opt.sharp);
			ctx.fillStyle = color;
			ctx.fill();
			if (opt.line !== false) {
				ctx.strokeStyle = mix$1(color, OUT, .55);
				ctx.lineWidth = .55;
				ctx.lineJoin = "round";
				ctx.stroke();
			}
			ctx.restore();
		});
	}
	function stroke(ctx, key, pts, w = .7, color = OUT) {
		part(ctx, key, () => {
			ctx.save();
			ctx.strokeStyle = color;
			ctx.lineWidth = w;
			ctx.lineCap = "round";
			ctx.lineJoin = "round";
			smooth(ctx, pts, false);
			ctx.stroke();
			ctx.restore();
		});
	}
	/** 粗線肢體：縫線色底＋色線；動畫的 limbRim（蜘蛛）改亮邊、加粗。 */
	function limb(ctx, key, pts, w, color) {
		const rim = S.pose?.limbRim === true;
		stroke(ctx, key, pts, w + 1.1 + (rim ? .5 : 0), rim ? lighten(color, .38) : mix$1(color, OUT, .55));
		stroke(ctx, key, pts, w + (rim ? .7 : 0), color);
	}
	function dot(ctx, x, y, rx, ry, c) {
		inPart(ctx, S.last, () => {
			ctx.fillStyle = c;
			ctx.beginPath();
			ctx.ellipse(x, y, rx, ry, 0, 0, TAU$2);
			ctx.fill();
		});
	}
	function bbox(pts) {
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
		return {
			x0,
			x1,
			y0,
			y1
		};
	}
	function clipTo(ctx, pts, P) {
		ctx.save();
		outline(ctx, pts, P.sharp);
		ctx.clip();
	}
	function polyline(ctx, pts) {
		ctx.beginPath();
		pts.forEach(([x, y], j) => j > 0 ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
	}
	/** 熔岩：一～兩道鋸齒裂縫（暗紅底＋亮色芯）；聖＝裂縫上方的小十字亮點。 */
	function cracks(ctx, key, pts, P) {
		const b = bbox(pts);
		const r = lcg(seedOf(key));
		const n = !P.lite && b.x1 - b.x0 > 18 ? 2 : 1;
		clipTo(ctx, pts, P);
		for (let i = 0; i < n; i++) {
			const y = b.y0 + (b.y1 - b.y0) * (n === 1 ? .5 : .35 + .3 * i);
			const line = [];
			for (let x = b.x0 + 2; x <= b.x1 - 2; x += 3.6) line.push([x, y + (line.length % 2 ? -1.4 : 1.4) + (r() - .5) * 1.2]);
			if (line.length < 2) continue;
			ctx.save();
			ctx.strokeStyle = "#7a2a08";
			ctx.lineWidth = 2;
			ctx.lineJoin = "miter";
			polyline(ctx, line);
			ctx.stroke();
			ctx.strokeStyle = P.accent ?? FIRE[0];
			ctx.lineWidth = 1;
			ctx.stroke();
			ctx.restore();
		}
		if (P.cross !== void 0) {
			const cs = P.lite ? [[.4, .22]] : [[.24, .22], [.56, .18]];
			for (const [fx, fy] of cs) {
				const x = b.x0 + (b.x1 - b.x0) * fx;
				const y = b.y0 + (b.y1 - b.y0) * fy + 1.2;
				const h = 2.3;
				ctx.save();
				ctx.lineCap = "round";
				for (const [c, w] of [["#7a2a08", 1.9], [P.cross, .9]]) {
					ctx.strokeStyle = c;
					ctx.lineWidth = w;
					ctx.beginPath();
					ctx.moveTo(x - h, y);
					ctx.lineTo(x + h, y);
					ctx.moveTo(x, y - h);
					ctx.lineTo(x, y + h);
					ctx.stroke();
				}
				ctx.restore();
			}
		}
		ctx.restore();
	}
	/** 源晶：左上一塊亮面（色塊）＋一條晶面線。 */
	function facets(ctx, key, pts, P) {
		const b = bbox(pts);
		const w = b.x1 - b.x0;
		const h = b.y1 - b.y0;
		clipTo(ctx, pts, P);
		ctx.fillStyle = lighten(P.base, .28);
		ctx.beginPath();
		ctx.moveTo(b.x0 - 1, b.y0 - 1);
		ctx.lineTo(b.x0 + w * .5, b.y0 - 1);
		ctx.lineTo(b.x0 + w * .22, b.y1 + 1);
		ctx.lineTo(b.x0 - 1, b.y1 + 1);
		ctx.closePath();
		ctx.fill();
		if (!P.lite) stroke(ctx, `${key}-f2`, [
			[b.x0 + w * .6, b.y0],
			[b.x0 + w * .5, b.y0 + h * .6],
			[b.x1, b.y0 + h * .7]
		], .7, lighten(P.base, .55));
		ctx.restore();
	}
	/** 青石：發光刻符 ᛉ（平塗兩層線；lite 只畫一豎）。 */
	function runes(ctx, _key, pts, P) {
		const b = bbox(pts);
		const cx = (b.x0 + b.x1) / 2;
		const cy = (b.y0 + b.y1) / 2;
		const lines = P.lite ? [[[cx, cy - 3], [cx, cy + 3]]] : [[[cx, cy - 3.6], [cx, cy + 3.6]], [
			[cx - 2.6, cy - 3],
			[cx, cy - .4],
			[cx + 2.6, cy - 3]
		]];
		clipTo(ctx, pts, P);
		for (const l of lines) {
			ctx.save();
			ctx.lineJoin = "miter";
			ctx.lineCap = "round";
			polyline(ctx, l);
			ctx.strokeStyle = darken(P.base, .35);
			ctx.lineWidth = 1.8;
			ctx.stroke();
			ctx.strokeStyle = P.accent ?? "#8fe3ff";
			ctx.lineWidth = .85;
			ctx.stroke();
			ctx.restore();
		}
		ctx.restore();
	}
	/** 木：一～兩道木紋（平塗深色線）。 */
	function grain(ctx, key, pts, P) {
		const b = bbox(pts);
		clipTo(ctx, pts, P);
		for (const i of P.lite ? [1.5] : [1, 2]) {
			const y = b.y0 + (b.y1 - b.y0) * i / 3;
			stroke(ctx, `${key}-gr${i}`, [
				[b.x0, y],
				[(b.x0 + b.x1) / 2, y - .8],
				[b.x1, y + .4]
			], .7, P.d);
		}
		ctx.restore();
	}
	/** 毛皮：肚子下緣一塊亮色（平塗）。 */
	function furBelly(ctx, pts, P) {
		const b = bbox(pts);
		const w = b.x1 - b.x0;
		const h = b.y1 - b.y0;
		if (w < 8 || h < 6) return;
		clipTo(ctx, pts, P);
		ctx.fillStyle = P.l;
		ctx.beginPath();
		ctx.ellipse((b.x0 + b.x1) / 2 + w * .08, b.y1 + h * .08, w * .36, h * .32, 0, 0, TAU$2);
		ctx.fill();
		ctx.restore();
	}
	/** 霧：一道亮色漩渦線（平塗）。 */
	function swirl(ctx, pts, P) {
		const b = bbox(pts);
		const w = b.x1 - b.x0;
		const h = b.y1 - b.y0;
		if (w < 6 || h < 5) return;
		clipTo(ctx, pts, P);
		ctx.save();
		ctx.strokeStyle = "#ffffff";
		ctx.lineWidth = .9;
		ctx.lineCap = "round";
		ctx.beginPath();
		ctx.ellipse((b.x0 + b.x1) / 2 - w * .05, (b.y0 + b.y1) / 2, w * .22, h * .2, 0, Math.PI * .9, Math.PI * 2.3);
		ctx.stroke();
		ctx.restore();
		ctx.restore();
	}
	/** 一塊身體：材質色平塗；`main` ＝ 主要部位，再加材質紋樣（Q 的大頭保持乾淨：頭上只有源晶的亮面）。 */
	function mass(ctx, key, pts, P, opt = {}) {
		part(ctx, key, () => {
			ink(ctx, key, pts, opt.color ?? P.base, {
				sharp: opt.sharp ?? P.sharp,
				...opt.line === false ? { line: false } : {}
			});
			if (opt.main !== true) return;
			if (/head/.test(key) && P.mat !== "crystal") return;
			if (P.mat === "magma") cracks(ctx, key, pts, P);
			else if (P.mat === "crystal") facets(ctx, key, pts, P);
			else if (P.mat === "stone") runes(ctx, key, pts, P);
			else if (P.mat === "wood") grain(ctx, key, pts, P);
			else if (P.mat === "mist" && !P.lite) swirl(ctx, pts, P);
			else if (P.mat === "fur" && opt.color === void 0 && !P.lite && /body|blob|torso|abd/.test(key)) furBelly(ctx, pts, P);
		});
	}
	/** 背上的小東西：毛（短毛三角）、熔岩（火星方塊）、源晶（晶刺）、青石（苔點）；木頭、霧不加。lite 只畫第一個。 */
	function back(ctx, key, list, P) {
		list.forEach(([x, y], i) => part(ctx, `${key}-sh${i}`, () => {
			if (P.lite && i > 0) return;
			if (P.mat === "crystal") {
				const h = 5 + i % 2 * 2.4;
				ink(ctx, `${key}-sh${i}`, [
					[x - 2, y + 1],
					[x + .6, y - h],
					[x + 2.4, y + 1]
				], lighten(P.base, .25), { sharp: true });
				stroke(ctx, `${key}-shl${i}`, [[x + .2, y - h + 1.6], [x - .6, y]], .6, "#ffffff");
			} else if (P.mat === "stone") dot(ctx, x, y + .6, 1.8, 1, "#6a9a4a");
			else if (P.mat === "wood" || P.mat === "mist") {} else if (P.mat === "magma") {
				ctx.fillStyle = P.accent ?? FIRE[0];
				ctx.fillRect(x + .2, y - 3.8 - i % 2 * 2.4, 1.6, 1.6);
			} else ink(ctx, `${key}-tuft${i}`, [
				[x - 1.8, y + .8],
				[x, y - 2.6],
				[x + 1.6, y + .6]
			], P.d, {
				sharp: true,
				line: false
			});
		}));
	}
	/** Q 的眼睛：圓角方眼（眼色）＋方瞳＋一點高光。 */
	function eye(ctx, x, y, P, r = 1) {
		inPart(ctx, S.last, () => {
			const s = r * 1.25;
			if (S.pose?.eyeShut) {
				ctx.save();
				ctx.strokeStyle = OUT;
				ctx.lineWidth = .7 * s;
				ctx.lineCap = "round";
				ctx.beginPath();
				ctx.moveTo(x - 1.05 * s, y - 1.05 * s);
				ctx.lineTo(x + 1.05 * s, y + 1.05 * s);
				ctx.moveTo(x + 1.05 * s, y - 1.05 * s);
				ctx.lineTo(x - 1.05 * s, y + 1.05 * s);
				ctx.stroke();
				ctx.restore();
				return;
			}
			ctx.fillStyle = P.eye;
			ctx.beginPath();
			ctx.roundRect(x - 1.15 * s, y - 1.25 * s, 2.3 * s, 2.5 * s, .7 * s);
			ctx.fill();
			ctx.fillStyle = OUT;
			ctx.fillRect(x - .2 * s, y - .95 * s, 1 * s, 1.9 * s);
			ctx.fillStyle = "#ffffff";
			ctx.fillRect(x + .15 * s, y - .85 * s, .45 * s, .45 * s);
		});
	}
	var fang = (ctx, key, x, y, h = 2) => ink(ctx, key, [
		[x - .8, y],
		[x, y + h],
		[x + .8, y]
	], "#f4ecd8", {
		sharp: true,
		line: false
	});
	function drawHound(ctx, P) {
		for (const x of [-12, 6]) mass(ctx, `hd-lf${x}`, [
			[x, -12],
			[x + 4, -12],
			[x + 4.4, 0],
			[x - .4, 0]
		], P, { color: P.d });
		mass(ctx, "hd-tail", [
			[-14, -20],
			[-22, -25],
			[-26, -21],
			[-20, -17],
			[-13, -15]
		], P);
		mass(ctx, "hd-body", [
			[-16, -12],
			[-17, -20],
			[-10, -25],
			[4, -25],
			[12, -22],
			[13, -12],
			[0, -10]
		], P, { main: true });
		back(ctx, "hd", [
			[-10, -25],
			[-4, -25.6],
			[2, -25.4]
		], P);
		for (const x of [-9, 8]) mass(ctx, `hd-l${x}`, [
			[x, -13],
			[x + 4, -13],
			[x + 4.6, 0],
			[x - .4, 0]
		], P);
		mass(ctx, "hd-ear", [
			[12, -29],
			[13, -36],
			[16.4, -30]
		], P, {
			color: P.d,
			sharp: true
		});
		mass(ctx, "hd-head", [
			[8, -22],
			[11, -30],
			[17, -31],
			[22, -28],
			[28, -26],
			[28, -23],
			[21, -21],
			[14, -18]
		], P, { main: true });
		dot(ctx, 28, -25, .9, .8, INK);
		eye(ctx, 19, -27.4, P);
		fang(ctx, "hd-fang", 24, -22.2);
	}
	function drawBoar(ctx, P) {
		for (const x of [-10, 6]) mass(ctx, `bo-lf${x}`, [
			[x, -9],
			[x + 4, -9],
			[x + 4, 0],
			[x, 0]
		], P, { color: P.d });
		stroke(ctx, "bo-tail", [
			[-15, -16],
			[-18, -18],
			[-17.4, -20]
		], .8);
		mass(ctx, "bo-body", [
			[-15, -8],
			[-16, -18],
			[-8, -24],
			[4, -25],
			[12, -20],
			[13, -9],
			[0, -7]
		], P, { main: true });
		[
			-11,
			-6,
			-1,
			4
		].forEach((x, i) => ink(ctx, `bo-br${i}`, [
			[x - 2, -23 - (x > -8 ? 1 : 0)],
			[x, -27.4],
			[x + 2, -24]
		], P.d, { sharp: true }));
		back(ctx, "bo", [[-8, -24], [6, -23]], P);
		for (const x of [-7, 8]) mass(ctx, `bo-l${x}`, [
			[x, -9],
			[x + 4, -9],
			[x + 4, 0],
			[x, 0]
		], P);
		mass(ctx, "bo-ear", [
			[11, -21],
			[12, -26],
			[15, -21]
		], P, {
			color: P.d,
			sharp: true
		});
		mass(ctx, "bo-head", [
			[9, -22],
			[16, -21],
			[22, -16],
			[23, -11],
			[17, -9],
			[10, -11]
		], P, { main: true });
		ink(ctx, "bo-snout", ellPts(22.4, -13.2, 2.2, 2.8, 10), P.l);
		ink(ctx, "bo-tusk", [
			[18.6, -11.4],
			[21.4, -17.4],
			[20.4, -11]
		], "#f4ecd8", { sharp: true });
		eye(ctx, 16.6, -17.4, P, .9);
	}
	function drawBear(ctx, P) {
		for (const x of [-11, 6]) mass(ctx, `be-lf${x}`, [
			[x - 2.8, -12],
			[x + 2.8, -12],
			[x + 3, 0],
			[x - 3, 0]
		], P, { color: P.d });
		mass(ctx, "be-body", [
			[-17, -9],
			[-17, -22],
			[-8, -29.6],
			[4, -29],
			[14, -22],
			[15, -9],
			[-2, -7]
		], P, { main: true });
		back(ctx, "be", [
			[-10, -28.4],
			[-3, -29.8],
			[4, -29.2]
		], P);
		for (const x of [-6, 11]) mass(ctx, `be-l${x}`, [
			[x - 3, -12],
			[x + 3, -12],
			[x + 3.4, 0],
			[x - 3.2, 0]
		], P);
		mass(ctx, "be-head", [
			[9, -26],
			[14, -31],
			[21, -29.4],
			[25.6, -23],
			[23.6, -19.6],
			[16, -18],
			[10, -20]
		], P, { main: true });
		mass(ctx, "be-ear", ellPts(13.6, -30.6, 2.2, 2.2, 10), P);
		ink(ctx, "be-snout", ellPts(23.4, -22.2, 2.6, 2, 10), P.l);
		dot(ctx, 25.2, -23, .9, .8, INK);
		eye(ctx, 18.6, -25.6, P, .9);
	}
	function drawBat(ctx, P) {
		mass(ctx, "fl-bwf", [
			[-1, -3],
			[-10, -16],
			[-20, -14],
			[-17, -9],
			[-22, -6],
			[-15, -3],
			[-16, 2],
			[-4, 1]
		], P, { color: P.d });
		mass(ctx, "fl-bbody", ellPts(0, 0, 6, 7, 16), P, { main: true });
		mass(ctx, "fl-bwn", [
			[1, -3],
			[10, -18],
			[21, -17],
			[18, -11],
			[24, -8],
			[16, -4],
			[17, 1],
			[4, 1]
		], P, { main: true });
		for (const [x, t] of [[3, -14], [7.4, -14.6]]) mass(ctx, `fl-be${x}`, [
			[x - 1.6, -8.4],
			[x, t],
			[x + 1.6, -8.4]
		], P, { sharp: true });
		mass(ctx, "fl-bhead", ellPts(5, -6.4, 4, 3.6, 12), P);
		eye(ctx, 7, -7, P, .8);
		fang(ctx, "fl-bfang", 7.6, -3.6, 1.6);
	}
	function drawBird(ctx, P) {
		mass(ctx, "fl-wf", [
			[-2, -4],
			[-12, -26],
			[-20, -30],
			[-16, -22],
			[-22, -24],
			[-14, -12],
			[-4, 2]
		], P, {
			color: P.d,
			sharp: true
		});
		mass(ctx, "fl-tail", [
			[-8, 2],
			[-18, 8],
			[-16, 2],
			[-20, 4],
			[-9, -1]
		], P, {
			color: P.d,
			sharp: true
		});
		mass(ctx, "fl-body", ellPts(0, 0, 9, 6, 16), P, { main: true });
		ink(ctx, "fl-belly", ellPts(1.5, 2, 6, 3, 12), P.mat === "fur" ? "#f0e6d0" : P.l);
		mass(ctx, "fl-wn", [
			[2, -4],
			[10, -28],
			[18, -34],
			[15, -24],
			[22, -27],
			[14, -12],
			[4, 2]
		], P, {
			main: true,
			sharp: true
		});
		mass(ctx, "fl-head", ellPts(9, -4, 4.2, 4.2, 12), P);
		ink(ctx, "fl-beak", [
			[12.5, -5.2],
			[17, -3],
			[12.5, -1]
		], "#e8bb48", { sharp: true });
		eye(ctx, 10.6, -5, P, .8);
		for (const x of [-2, 3]) stroke(ctx, `fl-claw${x}`, [[x, 5], [x, 9]], 1.4, "#e8bb48");
		back(ctx, "fl", [[10, -28], [18, -34]], P);
	}
	function drawFlyer(ctx, P, v) {
		ctx.save();
		ctx.translate(0, -18);
		if (v === "bat") drawBat(ctx, P);
		else drawBird(ctx, P);
		ctx.restore();
	}
	function drawSpider(ctx, P) {
		const legs = [
			[
				[1, -10],
				[-6, -19],
				[-13, 0]
			],
			[
				[3, -10],
				[0, -21],
				[-4, 0]
			],
			[
				[5, -10],
				[9, -21],
				[8, 0]
			],
			[
				[7, -10],
				[16, -18],
				[18, 0]
			]
		];
		legs.forEach((l, i) => limb(ctx, `sp-lf${i}`, l.map(([x, y]) => [x - 2.2, y - .6]), .9, P.d));
		mass(ctx, "sp-abd", ellPts(-9, -12, 9, 8, 18), P, { main: true });
		back(ctx, "sp", [[-12, -19.6], [-6, -19.4]], P);
		stroke(ctx, "sp-mark", [
			[-11, -15],
			[-8, -11],
			[-11, -8]
		], 1.2, P.accent ?? "#c0392b");
		mass(ctx, "sp-head", ellPts(5, -9, 6, 5, 14), P);
		legs.forEach((l, i) => limb(ctx, `sp-l${i}`, l, 1, P.base));
		mark("sp-eyes");
		for (const [x, y] of [
			[9.4, -11],
			[10.6, -9.4],
			[8.6, -9.2]
		]) dot(ctx, x, y, .7, .7, P.eye);
		fang(ctx, "sp-fang", 10, -6, 2);
	}
	function drawBeetle(ctx, P) {
		const legs = [
			[
				[-8, -6],
				[-12, -3],
				[-13, 0]
			],
			[
				[0, -6],
				[-1, -2],
				[-2, 0]
			],
			[
				[7, -6],
				[9, -3],
				[11, 0]
			]
		];
		legs.forEach((l, i) => limb(ctx, `bt-lf${i}`, l.map(([x, y]) => [x + 2, y]), .8, P.d));
		mass(ctx, "bt-shell", [
			[-14, -8],
			[-13, -15],
			[-6, -20],
			[4, -20],
			[11, -15],
			[12, -8],
			[0, -6]
		], P, { main: true });
		stroke(ctx, "bt-seam", [
			[-13, -10],
			[-4, -14.6],
			[8, -16.6]
		], .6);
		back(ctx, "bt", [[-6, -20], [1, -20.4]], P);
		mass(ctx, "bt-head", [
			[11, -14],
			[16, -15],
			[19, -11],
			[17, -7],
			[11, -7]
		], P, { color: P.d });
		mass(ctx, "bt-horn", [
			[16, -13.4],
			[23, -18],
			[19.4, -11]
		], P, {
			color: P.l,
			sharp: true
		});
		legs.forEach((l, i) => limb(ctx, `bt-l${i}`, l, .9, P.base));
		mark("bt-eye");
		eye(ctx, 15.6, -11.6, P, .8);
	}
	function drawLizard(ctx, P) {
		for (const x of [-6, 9]) mass(ctx, `lz-lf${x}`, [
			[x - 2, -6],
			[x + 2, -6],
			[x + 1, 0],
			[x - 3, 0]
		], P, { color: P.d });
		mass(ctx, "lz-tail", [
			[-8, -10],
			[-20, -9],
			[-30, -3],
			[-32, -1],
			[-22, -4],
			[-8, -5]
		], P, { main: true });
		mass(ctx, "lz-body", [
			[-10, -5],
			[-10, -11],
			[-2, -14],
			[10, -13],
			[14, -9],
			[12, -5],
			[0, -4]
		], P, { main: true });
		for (const x of [
			-6,
			-1,
			4
		]) ink(ctx, `lz-sp${x}`, [
			[x - 2, -13.4],
			[x, -18.4],
			[x + 2, -13.6]
		], P.mat === "fur" ? "#c0392b" : P.l, { sharp: true });
		back(ctx, "lz", [[-14, -9], [8, -13]], P);
		for (const x of [-7, 10]) mass(ctx, `lz-l${x}`, [
			[x - 2, -7],
			[x + 2, -7],
			[x + 3, 0],
			[x - 2.6, 0]
		], P);
		mass(ctx, "lz-head", [
			[12, -12],
			[16, -15],
			[23, -14],
			[27, -11],
			[26, -9],
			[18, -8],
			[13, -8]
		], P, { main: true });
		eye(ctx, 19, -12.4, P, .85);
	}
	function drawSerpent(ctx, P) {
		mass(ctx, "sn-coil", ellPts(-4, -3.6, 13, 4.2, 20), P, { main: true });
		mass(ctx, "sn-coil2", ellPts(-2, -7.4, 8.4, 3.2, 16), P, { color: P.d });
		mass(ctx, "sn-neck", [
			[1, -6],
			[8, -6],
			[10, -16],
			[9, -24],
			[4, -24],
			[5, -16]
		], P, { main: true });
		stroke(ctx, "sn-belly", [
			[8.6, -7],
			[9.4, -16],
			[8.4, -23]
		], 1.4, P.mat === "fur" ? "#e8dca0" : P.l);
		back(ctx, "sn", [[-10, -7], [-1, -10.4]], P);
		mass(ctx, "sn-head", [
			[3, -25],
			[8, -29.4],
			[15, -28.4],
			[18.4, -25],
			[14, -22],
			[6, -22]
		], P, { main: true });
		stroke(ctx, "sn-tongue", [
			[18.4, -24.6],
			[21.6, -24.6],
			[23, -26]
		], .5, "#d23c3c");
		stroke(ctx, "sn-tongue2", [[21.6, -24.6], [23, -23.4]], .5, "#d23c3c");
		eye(ctx, 12, -26.4, P, .85);
	}
	function drawShell(ctx, P) {
		for (const x of [-9, 6]) mass(ctx, `sh-lf${x}`, [
			[x - 3, -7],
			[x + 2, -7],
			[x + 2, 0],
			[x - 3.4, 0]
		], P, { color: P.d });
		mass(ctx, "sh-dome", [
			[-15, -6],
			[-14, -15],
			[-7, -22],
			[4, -22],
			[11, -16],
			[12, -6],
			[0, -5]
		], P, { main: true });
		[
			[[-8, -21], [-9, -7]],
			[[3, -21], [2, -7]],
			[[-14, -12.4], [11.4, -12.4]]
		].forEach((l, i) => stroke(ctx, `sh-plate${i}`, l, .6));
		stroke(ctx, "sh-rim", [[-16, -6], [13, -6]], 2.2, INK);
		stroke(ctx, "sh-rim2", [[-16, -6], [13, -6]], 1.2, P.l);
		back(ctx, "sh", [
			[-9, -21],
			[-2, -22.6],
			[5, -21.4]
		], P);
		for (const x of [-11, 5]) mass(ctx, `sh-l${x}`, [
			[x, -7],
			[x + 5, -7],
			[x + 5.6, 0],
			[x - .4, 0]
		], P, { color: P.l });
		mass(ctx, "sh-head", [
			[11, -11],
			[16, -12],
			[20, -9],
			[19, -5],
			[13, -5]
		], P, { color: P.l });
		eye(ctx, 17, -9.4, P, .8);
	}
	function drawOoze(ctx, P) {
		mass(ctx, "oz-blob", [
			[-13, 0],
			[-14, -6],
			[-10, -13],
			[-3, -17],
			[5, -16],
			[11, -11],
			[13, -4],
			[12, 0]
		], P, { main: true });
		for (const [x, y, r] of [
			[
				-6,
				-6,
				1.8
			],
			[
				-2,
				-11,
				1.2
			],
			[
				8,
				-5,
				1.4
			]
		]) ink(ctx, `oz-bub${x}`, ellPts(x, y, r, r, 8), P.l);
		back(ctx, "oz", [[-6, -15], [2, -16.6]], P);
		mark("oz-face");
		eye(ctx, 4.6, -10, P, .9);
		eye(ctx, 8.4, -10.2, P, .8);
	}
	function drawGolem(ctx, P) {
		mass(ctx, "go-legf", [
			[-7, -16],
			[-1, -16],
			[-1.6, 0],
			[-8, 0]
		], P, { color: P.d });
		mass(ctx, "go-armf", [
			[-10, -37],
			[-15, -34],
			[-17, -18],
			[-12, -17],
			[-11, -30]
		], P, { color: P.d });
		mass(ctx, "go-legn", [
			[0, -16],
			[6, -16],
			[6.6, 0],
			[-.4, 0]
		], P);
		mass(ctx, "go-torso", [
			[-11, -38],
			[8, -40],
			[12, -30],
			[9, -16],
			[-9, -16],
			[-12, -28]
		], P, { main: true });
		back(ctx, "go", [[-9, -38.4], [-3, -39.6]], P);
		mass(ctx, "go-head", [
			[-4, -40],
			[-3, -47],
			[4, -48],
			[7, -43],
			[5, -39]
		], P);
		ink(ctx, "go-eye", [
			[2.4, -44.6],
			[6.4, -44.6],
			[6.4, -43],
			[2.4, -43]
		], P.accent ?? "#ffd23a", { sharp: true });
		mass(ctx, "go-arm", [
			[4, -38],
			[11, -38],
			[16, -24],
			[16, -14],
			[10, -14],
			[9, -24]
		], P, { main: true });
		mass(ctx, "go-fist", ellPts(13, -12, 4, 3.6, 12), P);
	}
	function drawWisp(ctx, P) {
		ctx.save();
		ctx.translate(0, -20);
		for (const [i, [x, y, s]] of [
			[
				-11,
				-5,
				2.4
			],
			[
				10,
				-8,
				2
			],
			[
				3,
				9,
				1.8
			]
		].entries()) mass(ctx, `wp-or${i}`, [
			[x, y - s * 1.6],
			[x + s, y],
			[x, y + s * 1.6],
			[x - s, y]
		], P, {
			sharp: true,
			color: P.l
		});
		mass(ctx, "wp-core", [
			[0, -11],
			[7.4, 0],
			[0, 11],
			[-7.4, 0]
		], P, {
			main: true,
			sharp: true
		});
		ink(ctx, "wp-in", [
			[0, -5],
			[3.4, 0],
			[0, 5],
			[-3.4, 0]
		], P.accent ?? P.eye, { sharp: true });
		dot(ctx, 1.2, -.6, .9, 1.3, INK);
		ctx.restore();
	}
	function drawFeline(ctx, P) {
		for (const x of [-8, 10]) mass(ctx, `fe-lf${x}`, [
			[x - 1.6, -9],
			[x + 1.6, -9],
			[x + 1.8, 0],
			[x - 1.8, 0]
		], P, { color: P.d });
		mass(ctx, "fe-tail", [
			[-12, -12.4],
			[-21, -12],
			[-26, -7],
			[-24, -5.4],
			[-20, -9],
			[-12, -9]
		], P);
		mass(ctx, "fe-body", ellPts(0, -11, 14, 5, 20), P, { main: true });
		back(ctx, "fe", [[-6, -15.6], [2, -16]], P);
		for (const x of [-11, 7]) mass(ctx, `fe-l${x}`, [
			[x - 1.7, -9],
			[x + 1.7, -9],
			[x + 2, 0],
			[x - 2, 0]
		], P);
		for (const x of [13, 17.4]) mass(ctx, `fe-ear${x}`, [
			[x - 2.2, -16.6],
			[x, -21.6],
			[x + 2.2, -16.6]
		], P, { sharp: true });
		mass(ctx, "fe-head", ellPts(15, -14.5, 5.4, 4.6, 16), P, { main: true });
		ink(ctx, "fe-muzzle", ellPts(19.2, -13, 2.2, 1.6, 10), P.l);
		eye(ctx, 17.2, -15.4, P, .9);
		dot(ctx, 21, -13.4, .6, .5, INK);
	}
	function drawWraith(ctx, P) {
		ctx.save();
		ctx.translate(0, -4);
		limb(ctx, "wr-arm-l", [
			[-7, -30],
			[-12, -22],
			[-14, -16]
		], 2.2, P.base);
		mass(ctx, "wr-body", [
			[-8, -34],
			[-10, -20],
			[-7, -8],
			[-4, -2],
			[-1, -6],
			[2, -1],
			[5, -6],
			[9, -18],
			[8, -34]
		], P, { main: true });
		mass(ctx, "wr-head", ellPts(0, -38, 6, 6.4, 14), P);
		for (const x of [-2.4, 2.4]) {
			dot(ctx, x, -38, 1.9, 2.1, darken(P.base, .55));
			eye(ctx, x, -38, { eye: lighten(P.eye, .4) }, .85);
		}
		limb(ctx, "wr-arm-r", [
			[7, -30],
			[12, -23],
			[15, -18]
		], 2.2, P.base);
		ctx.restore();
	}
	function drawPylon(ctx, P) {
		ink(ctx, "py-base", [
			[-8, 0],
			[-9, -5],
			[9, -5],
			[8, 0]
		], "#6a645e");
		mass(ctx, "py-ob", [
			[-5, -5],
			[-4, -30],
			[0, -38],
			[4, -30],
			[5, -5]
		], P, {
			main: true,
			sharp: true
		});
		ink(ctx, "py-eye", ellPts(1.6, -22, 1.8, 2.4, 10), P.accent ?? P.eye);
		dot(ctx, 2, -22, .5, 1.2, INK);
		ctx.save();
		ctx.globalAlpha = .8;
		stroke(ctx, "py-ring", [...ellPts(0, -22, 8.6, 2.4, 20), [8.6, -22]], .7, P.accent ?? P.l);
		ctx.restore();
	}
	var BODIES = {
		hound: {
			zh: "犬狼",
			fur: "#7a7a82",
			top: -36,
			head: [20, -28],
			len: 24,
			sp: [
				[-10, -25],
				[-4, -25.6],
				[2, -25.4]
			],
			qHead: Q_HEADS["hound"],
			draw: drawHound
		},
		boar: {
			zh: "野豬",
			fur: "#6a4a36",
			top: -28,
			head: [16, -18],
			len: 22,
			sp: [
				[-8, -24],
				[-1, -25],
				[6, -23]
			],
			qHead: Q_HEADS["boar"],
			draw: drawBoar
		},
		bear: {
			zh: "熊",
			fur: "#6a4a32",
			top: -33,
			head: [18, -26],
			len: 22,
			sp: [
				[-10, -28.4],
				[-3, -29.8],
				[4, -29.2]
			],
			qHead: Q_HEADS["bear"],
			draw: drawBear
		},
		flyer: {
			zh: "飛禽",
			fur: "#a07a4a",
			top: -50,
			head: [9, -22],
			len: 20,
			hover: true,
			sp: [
				[-4, -22],
				[0, -24],
				[4, -22]
			],
			qHeadBy: {
				bat: [
					"fl-be",
					4,
					-2,
					1.25
				],
				bird: [
					"fl-head",
					6,
					-2,
					1.18,
					"fl-claw"
				]
			},
			draw: drawFlyer
		},
		crawler: {
			zh: "爬蟲",
			fur: "#3a3440",
			top: -24,
			head: [15, -12],
			len: 18,
			sp: [[-8, -20], [-2, -20.4]],
			draw: (ctx, P, v) => v === "spider" ? drawSpider(ctx, P) : drawBeetle(ctx, P)
		},
		lizard: {
			zh: "蜥蜴",
			fur: "#6a7a3a",
			top: -19,
			core: [2, -7.4],
			head: [20, -12],
			len: 30,
			sp: [
				[-6, -13.6],
				[-1, -14],
				[4, -13.6]
			],
			qHead: Q_HEADS["lizard"],
			draw: drawLizard
		},
		serpent: {
			zh: "蛇",
			fur: "#5a7a3a",
			top: -30,
			head: [12, -26],
			len: 17,
			sp: [[-10, -7], [-1, -10.4]],
			qHead: Q_HEADS["serpent"],
			draw: drawSerpent
		},
		shell: {
			zh: "龜殼",
			fur: "#5a6a4a",
			top: -23,
			head: [16, -9],
			len: 20,
			sp: [
				[-9, -21],
				[-2, -22.6],
				[5, -21.4]
			],
			qHead: Q_HEADS["shell"],
			draw: drawShell
		},
		ooze: {
			zh: "軟泥",
			fur: "#6a9a5a",
			top: -18,
			head: [6, -10],
			len: 15,
			sp: [[-6, -15], [2, -16.6]],
			draw: drawOoze
		},
		golem: {
			zh: "傀儡",
			fur: "#8a847e",
			top: -49,
			core: [-1, -29],
			head: [2, -44],
			len: 17,
			sp: [
				[-9, -38.4],
				[-3, -39.6],
				[3, -40]
			],
			qHead: Q_HEADS["golem"],
			draw: drawGolem
		},
		wisp: {
			zh: "晶靈",
			fur: "#9a86ff",
			top: -34,
			core: [0, -20],
			head: [0, -22],
			len: 12,
			hover: true,
			sp: [[0, -31]],
			draw: drawWisp
		},
		feline: {
			zh: "豹",
			fur: "#c8a060",
			top: -23,
			head: [15, -15],
			len: 22,
			sp: [
				[-8, -15],
				[-2, -16],
				[4, -15.6]
			],
			qHead: Q_HEADS["feline"],
			draw: drawFeline
		},
		wraith: {
			zh: "霧魅",
			fur: "#e6ecef",
			top: -46,
			head: [0, -42],
			len: 12,
			hover: true,
			sp: [[-4, -40], [4, -40]],
			draw: drawWraith
		},
		pylon: {
			zh: "晶塔",
			fur: "#8a847e",
			top: -40,
			head: [1, -24],
			len: 9,
			sp: [[0, -38]],
			draw: drawPylon
		}
	};
	Object.keys(BODIES);
	/** 有款式的身形：第一個是預設款。 */
	var BODY_VARIANTS = {
		flyer: ["bird", "bat"],
		crawler: ["beetle", "spider"]
	};
	/** 動畫掛點用的身形鍵（飛禽、爬蟲分款式）。 */
	var rigKey = (r) => r.body === "flyer" || r.body === "crawler" ? r.variant : r.body;
	function crust(ctx, a) {
		const [cx, cy] = a.core ?? a.head;
		[
			[
				-7,
				3,
				-.5
			],
			[
				6.6,
				3.4,
				.5
			],
			[
				-8.6,
				-5,
				-1.1
			],
			[
				8,
				-5.6,
				1.1
			],
			[
				-3.4,
				-10.6,
				-.3
			],
			[
				3.8,
				-10.4,
				.35
			],
			[
				0,
				6.6,
				0
			]
		].forEach(([dx, dy, rot], i) => {
			const x = cx + dx;
			const y = cy + dy;
			const c = Math.cos(rot);
			const sn = Math.sin(rot);
			const q = (u, v) => [x + u * c - v * sn, y + u * sn + v * c];
			ink(ctx, `tr-cr${i}`, [
				q(-4.4, 2.6),
				q(-3.6, -2.4),
				q(0, -3.6),
				q(3.6, -2.4),
				q(4.4, 2.6),
				q(0, 3.4)
			], BASALT);
			stroke(ctx, `tr-crl${i}`, [q(0, -3.2), q(0, 3)], .45, "#1c1412");
		});
		[
			[
				-2,
				-1,
				2,
				-2
			],
			[
				-4,
				6,
				-1,
				9
			],
			[
				3,
				5,
				5,
				8
			]
		].forEach(([x0, y0, x1, y1], i) => stroke(ctx, `tr-crg${i}`, [[cx + x0, cy + y0], [cx + x1, cy + y1]], .9, FIRE[1]));
	}
	/** 特徵：`soft` ＝ 無外框、半透明，畫在剪影外（霧團、黃煙）；`behind` ＝ 畫在身體後面（霧氣繞身）。 */
	var TRAITS = {
		stone_back: {
			zh: "背上石板",
			draw: (ctx, a) => a.sp.forEach(([x, y], i) => ink(ctx, `tr-sb${i}`, [
				[x - 3, y + 1.4],
				[x - 1.6, y - 4.4 - i % 2 * 1.6],
				[x + 2.6, y - 3.4],
				[x + 3, y + 1.4]
			], "#8a8f94", { sharp: true }))
		},
		volcano: {
			zh: "背上小火山",
			draw: (ctx, a, P) => {
				const [x, y] = a.sp[Math.floor(a.sp.length / 2)] ?? a.head;
				ink(ctx, "tr-vc", [
					[x - 6, y + 2],
					[x - 2, y - 6],
					[x + 2, y - 6],
					[x + 6, y + 2]
				], "#4a3a34");
				ink(ctx, "tr-vc-mouth", ellPts(x, y - 6, 2, .8, 10), P?.accent ?? FIRE[0]);
				[[
					-.6,
					-9.6,
					1.6
				], [
					1.6,
					-12.4,
					1.9
				]].forEach(([dx, dy, r], i) => ink(ctx, `tr-vc-sm${i}`, ellPts(x + dx, y + dy, r, r, 10), "#9a9490"));
			}
		},
		smoke: {
			zh: "黃煙",
			soft: true,
			draw: (ctx, a) => [
				[
					-a.len * .25,
					a.top - 1,
					2,
					.6
				],
				[
					-a.len * .1,
					a.top - 5.5,
					2.8,
					.45
				],
				[
					a.len * .05,
					a.top - 11,
					3.6,
					.3
				]
			].forEach(([x, y, r, al], i) => {
				ctx.save();
				ctx.globalAlpha = al;
				ink(ctx, `tr-sk${i}`, ellPts(x, y, r, r * .85, 12), "#e8d860", { line: false });
				ctx.restore();
			})
		},
		mist: {
			zh: "霧氣繞身",
			soft: true,
			draw: (ctx, a) => {
				ctx.save();
				ctx.globalAlpha = .55;
				[
					[
						-a.len * .7,
						-2,
						3.4
					],
					[
						-a.len * .1,
						-1,
						4
					],
					[
						a.len * .6,
						-2.4,
						3
					]
				].forEach(([x, y, r], i) => ink(ctx, `tr-ms${i}`, ellPts(x, y, r, r * .55, 12), "#eef2f4", { line: false }));
				stroke(ctx, "tr-ms-l", [
					[-a.len, -6],
					[-a.len * .4, -8],
					[0, -6]
				], .5, "#ffffff");
				ctx.restore();
			}
		},
		core: {
			zh: "熔核",
			draw: (ctx, a, P) => {
				const [x, y] = a.core ?? a.head;
				const c = P?.accent ?? FIRE[0];
				ink(ctx, "tr-core", ellPts(x, y, 3.2, 3.2, 12), c);
				dot(ctx, x - .6, y - .8, 1.2, 1.2, lighten(c, .6));
			}
		},
		crust: {
			zh: "甲蟲殼堆（熔殼）",
			draw: crust
		},
		scar: {
			zh: "疤",
			draw: (ctx, a) => {
				const [x, y] = a.head;
				stroke(ctx, "tr-scar1", [[x - 3, y - 3], [x + 1, y + 2]], .8, "#5a2a22");
				stroke(ctx, "tr-scar2", [[x - 1.6, y - 1.2], [x - 3, y]], .6, "#5a2a22");
			}
		},
		brood: {
			zh: "背負卵囊",
			draw: (ctx, a, P) => a.sp.forEach(([x, y], i) => ink(ctx, `tr-egg${i}`, ellPts(x, y - 2, 2.4, 3, 10), P?.accent ?? "#ffb23a"))
		},
		lava_pool: {
			zh: "背負熔岩池",
			draw: (ctx, a, P) => {
				const [x0, y0] = a.sp[0] ?? a.head;
				const x1 = (a.sp[a.sp.length - 1] ?? a.head)[0];
				ink(ctx, "tr-pool-rim", [
					[x0 - 5, y0 + 1],
					[x0 - 3, y0 - 3],
					[x1 + 3, y0 - 4],
					[x1 + 5, y0],
					[x1 + 3, y0 + 3],
					[x0 - 3, y0 + 3]
				], "#4a3a34");
				ink(ctx, "tr-pool", ellPts((x0 + x1) / 2, y0 - 1.4, (x1 - x0) / 2 + 2, 1.4, 14), P?.accent ?? FIRE[0]);
			}
		},
		spots: {
			zh: "斑紋",
			draw: (ctx, _a, P) => {
				mark("tr-spots");
				[
					[-8, -12],
					[-3, -14],
					[2, -11.4],
					[-5, -9.4],
					[8, -12.4]
				].forEach(([x, y]) => dot(ctx, x, y, 1.1, .8, P?.d ?? "#5a4a3a"));
			}
		},
		sparks: {
			zh: "電光",
			draw: (ctx, a) => [[-a.len * .5, a.top * .75], [a.len * .6, a.top * .85]].forEach(([x, y], i) => stroke(ctx, `tr-spk${i}`, [
				[x, y],
				[x + 2, y + 2],
				[x, y + 3],
				[x + 2.4, y + 5.4]
			], .9, "#fff36b"))
		}
	};
	/** 連心的青色（頭上的結與到相鄰同門的虛線；虛線由戰場畫）。 */
	var LINK_COLOR = "#3fd0c0";
	var AFFIX = {
		berserk: {
			zh: "狂暴的",
			draw: (ctx, a) => {
				const [hx, hy] = a.head;
				[
					[
						-3,
						-6,
						1.8
					],
					[
						1,
						-9,
						2.2
					],
					[
						4.6,
						-6.4,
						1.6
					]
				].forEach(([dx, dy, r], i) => ink(ctx, `af-bz${i}`, ellPts(hx + dx, hy + dy, r, r, 10), "#ff8a7a"));
				for (const s of [-1, 1]) stroke(ctx, `af-bzv${s}`, [
					[hx - 1 + s * 1.4, hy - 3.2],
					[hx + s * .6, hy - 2],
					[hx + 1 + s * 1.4, hy - 3.2]
				], .8, "#e02a2a");
			}
		},
		regen: {
			zh: "再生的",
			draw: (ctx, a) => [
				[-a.len * .7, a.top * .45],
				[a.len * .5, a.top * .75],
				[-a.len * .2, a.top * .95],
				[a.len * .85, a.top * .3]
			].forEach(([x, y], i) => {
				stroke(ctx, `af-rg${i}a`, [[x - 1.8, y], [x + 1.8, y]], 1.1, "#3f9a4a");
				stroke(ctx, `af-rg${i}b`, [[x, y - 1.8], [x, y + 1.8]], 1.1, "#3f9a4a");
				stroke(ctx, `af-rg${i}c`, [[x - 1.4, y], [x + 1.4, y]], .55, "#b6f0a0");
				stroke(ctx, `af-rg${i}d`, [[x, y - 1.4], [x, y + 1.4]], .55, "#b6f0a0");
			})
		},
		armored: {
			zh: "堅甲的",
			draw: (ctx, a) => {
				const y = a.armorY ?? a.top * (a.hover === true ? .55 : .6);
				[-a.len * .35, a.len * .1].forEach((x, i) => ink(ctx, `af-ar${i}`, [
					[x - 4, y - 1.4],
					[x + 4, y - 2.4],
					[x + 4.6, y + 3],
					[x - 3.6, y + 3.6]
				], "#8d969f"));
				for (const x of [-a.len * .35, a.len * .1]) dot(ctx, x, y + .6, .6, .6, "#3c4248");
			}
		},
		swift: {
			zh: "迅捷的",
			draw: (ctx, a) => [
				a.top * .3,
				a.top * .55,
				a.top * .8
			].forEach((y, i) => stroke(ctx, `af-sw${i}`, [[-a.len - 3 - i * 2, y], [-a.len - 11 - i * 2, y]], .9, "#e8e8ea"))
		},
		elemental: {
			zh: "元素的",
			draw: (ctx, a) => {
				const c = (a.element !== void 0 ? CREATURE_ELEM[a.element] : void 0) ?? FIRE;
				[
					-a.len * .6,
					a.len * .1,
					a.len * .75
				].forEach((x, i) => {
					ink(ctx, `af-el${i}`, [
						[x - 2, .6],
						[x - .6, -4.4],
						[x, -2.4],
						[x + 1, -6.4],
						[x + 2.2, .6]
					], c[0], { sharp: true });
					dot(ctx, x + .2, -1, .8, 1, c[1]);
				});
			}
		},
		mist_hidden: {
			zh: "霧隱的",
			soft: true,
			draw: (ctx, a) => {
				ctx.save();
				ctx.globalAlpha = .6;
				[
					[
						-a.len * .8,
						a.top * .4,
						3.6
					],
					[
						a.len * .7,
						a.top * .65,
						3.2
					],
					[
						-a.len * .2,
						a.top * .95,
						3
					],
					[
						a.len * .2,
						-1.4,
						4
					]
				].forEach(([x, y, r], i) => ink(ctx, `af-mh${i}`, ellPts(x, y, r, r * .7, 12), "#eef2f4", { line: false }));
				ctx.restore();
			}
		},
		linked: {
			zh: "連心的",
			draw: (ctx, a) => {
				const [hx] = a.head;
				const y = a.top - 4;
				for (const s of [-1, 1]) stroke(ctx, `af-lk${s}`, [
					[hx + s * 1.6, y + 2],
					[hx + s * 3.4, y - .4],
					[hx + s * 1.6, y - 2.4],
					[hx, y - .6]
				], 1, LINK_COLOR);
			}
		},
		blazing: {
			zh: "熾熱的",
			draw: (ctx, a) => [
				-a.len * .5,
				0,
				a.len * .5
			].forEach((x, i) => stroke(ctx, `af-bl${i}`, [
				[x, a.top - 1],
				[x + 1.4, a.top - 3.4],
				[x - .4, a.top - 5.8],
				[x + 1, a.top - 8]
			], .8, "#ffb23a"))
		},
		hardshell: {
			zh: "硬殼的",
			draw: (ctx, a) => {
				a.sp.forEach(([x, y], i) => {
					if (i < 2) stroke(ctx, `af-hs${i}`, [[x - 2.4, y + 2], [x + 1.6, y + .6]], 1.1, "#ffffff");
				});
				const s0 = a.sp[0] ?? a.head;
				dot(ctx, s0[0] + 3, s0[1] - 1, .9, .9, "#ffffff");
			}
		}
	};
	/** 內容詞綴 ID（`content/world/enemies.yaml`）→ 美術特效 id；資料有寫 `look` 時不會用到。 */
	var AFFIX_ALIAS = {
		regenerating: "regen",
		mist_veiled: "mist_hidden",
		heart_linked: "linked",
		hard_shelled: "hardshell"
	};
	/** 詞綴清單 → 認得的特效 id（含 mirror；去重、保持順序）；不認得的略過（只剩精英金環）。 */
	function knownAffixes(list) {
		const out = [];
		for (const raw of list ?? []) {
			const id = AFFIX_ALIAS[raw] ?? raw;
			if ((AFFIX[id] !== void 0 || id === "mirror") && !out.includes(id)) out.push(id);
		}
		return out;
	}
	var HEX = /^#[0-9a-f]{6}$/i;
	/** 驗證並補預設：永遠回傳畫得出來的外觀。 */
	function resolveCreature(input) {
		const look = input.look;
		const body = BODIES[look.body] !== void 0 ? look.body : "ooze";
		const variants = BODY_VARIANTS[body] ?? [""];
		const variant = variants.find((v) => v === look.variant) ?? variants[0] ?? "";
		const material = isMaterial(look.material) ? look.material : "fur";
		const element = look.element != null && CREATURE_ELEM[look.element] !== void 0 ? look.element : void 0;
		const tint = look.tint != null && HEX.test(look.tint) ? look.tint : void 0;
		const glow = input.rarity != null ? CREATURE_GLOW[input.rarity] : void 0;
		const elite = input.elite === true && glow === void 0;
		const table = input.field === true ? FIELD_SIZES : SIZES;
		const size = (look.size != null ? table[look.size] ?? 1 : 1) * (elite ? ELITE_SCALE : 1);
		const lite = look.size != null && (SIZES[look.size] ?? 1) < .95;
		const traits = [];
		const add = (t) => {
			if (TRAITS[t] !== void 0 && !traits.includes(t)) traits.push(t);
		};
		for (const t of look.traits ?? []) add(t);
		const statuses = input.statusIds ?? [];
		const byStatus = look.status_traits ?? {};
		for (const sid of Object.keys(byStatus).sort()) if (statuses.includes(sid)) for (const t of byStatus[sid] ?? []) add(t);
		const out = {
			body,
			variant,
			material,
			element,
			tint,
			size,
			lite,
			traits,
			affixes: knownAffixes(input.affixes),
			glow
		};
		const boss = bossOf(input.template, input.bossPhase, statuses);
		if (boss !== null) out.boss = boss;
		return out;
	}
	function fxInfo(r) {
		const b = BODIES[r.body];
		return {
			head: b.head,
			top: b.top,
			len: b.len,
			sp: b.sp,
			core: b.core,
			hover: b.hover,
			element: r.element
		};
	}
	/** 一隻的色票（tiny／small 簡化紋樣）。 */
	function creaturePalette(r) {
		return paletteOf(r.material, r.element, r.tint, BODIES[r.body].fur, r.lite);
	}
	/** 畫身體（平塗部件，不含外框）：特徵（soft、電光除外）畫在身上。`part` 為分部件姿勢。 */
	function drawParts(ctx, r, P) {
		const b = BODIES[r.body];
		S.qhead = (b.qHeadBy !== void 0 ? b.qHeadBy[r.variant] : b.qHead) ?? null;
		S.inHead = false;
		S.headDone = false;
		S.last = "body";
		S.depth = 0;
		try {
			b.draw(ctx, P, r.variant);
			if (S.inHead) ctx.restore();
			S.qhead = null;
			S.inHead = false;
			S.headDone = false;
			const info = fxInfo(r);
			for (const t of r.traits) if (TRAITS[t].soft !== true && t !== "sparks") TRAITS[t].draw(ctx, info, P);
		} finally {
			S.qhead = null;
			S.inHead = false;
			S.headDone = false;
			S.depth = 0;
		}
	}
	/** 分部件姿勢在整隻（身體、特徵、詞綴）畫完之前都有效（同樣張 stamp 的 POSE）。 */
	function withPose(r, pose, fn) {
		const rig = pose === null ? void 0 : RIG[rigKey(r)];
		S.pose = pose;
		S.groups = rig?.groups ?? null;
		S.pivots = rig?.pivots ?? null;
		S.last = "body";
		try {
			fn();
		} finally {
			S.pose = null;
			S.groups = null;
			S.pivots = null;
			S.last = "body";
			S.depth = 0;
		}
	}
	/** 剪影外框層的範圍（單位，同樣張 BOX）。 */
	var BOX = [
		-62,
		-84,
		62,
		18
	];
	/** 一層：有 DOM 時用剪影外框層，沒有時（測試）直接平塗。 */
	function layered(ctx, draw, o) {
		if (hasDom() && typeof ctx.getTransform === "function") {
			qLayer(ctx, BOX, draw, o);
			return;
		}
		ctx.save();
		if ((o?.alpha ?? 1) !== 1) ctx.globalAlpha = o?.alpha ?? 1;
		draw(ctx);
		ctx.restore();
	}
	/** CB-3：熊人立重拍的乳白三爪（照樣張 atk:slam 的 pose.over）：畫在近側前掌的掌端，跟著前腿組的變換；自己一層細外框。 */
	function drawClaws(ctx, pp, key) {
		const piv = RIG[key]?.pivots["FN"];
		const cw = pp.claws ?? 0;
		if (piv === void 0 || cw <= 0) return;
		const fn = pp.parts["FN"] ?? {};
		const draw = (g) => {
			g.translate(piv[0] + (fn.dx ?? 0), piv[1] + (fn.dy ?? 0));
			g.rotate(fn.rot ?? 0);
			g.transform(1, 0, fn.kx ?? 0, 1, 0, 0);
			g.scale(fn.sx ?? 1, fn.sy ?? 1);
			g.fillStyle = "#f4ecd8";
			for (const dx of [
				-2.6,
				0,
				2.6
			]) {
				g.beginPath();
				g.moveTo(dx - 1, 13);
				g.lineTo(dx + .6, 13 + 3.4 * cw);
				g.lineTo(dx + 1, 13);
				g.closePath();
				g.fill();
			}
		};
		if (hasDom() && typeof ctx.getTransform === "function") {
			qLayer(ctx, [
				-70,
				-90,
				74,
				18
			], draw, { ow: .5 });
			return;
		}
		ctx.save();
		draw(ctx);
		ctx.restore();
	}
	/** 片段的分部件姿勢（沒有片段 → `null`）。 */
	function partPoseOf(r, P, pose) {
		if (pose?.clip === void 0) return null;
		const key = rigKey(r);
		const clip = pose.clip.startsWith("atk:@") ? attackClipFor(key, pose.clip.slice(5)) : pose.clip;
		if (clip === null) return null;
		const part = qCreaturePartPose({
			key,
			element: r.element,
			mat: P.mat,
			base: P.base,
			accent: P.accent,
			traits: r.traits
		}, clip, pose.u ?? 0, pose.reduce === true, pose.perch ?? 0);
		return part !== null && pose.inPlace === true ? {
			...part,
			root: {
				...part.root,
				dx: 0
			}
		} : part;
	}
	/**
	* 畫一隻異形（腳底在原點、朝東，已乘上大小；呼叫端鏡像）：影子、分身、本體（霧隱 75%）、軟特效、詞綴特效、動畫特效。地面環由戰場畫。
	* `pose`：片段（`clip`、`u`）＋整隻的伸縮、傾斜、透明（跳躍）；不給或 `null` 時是靜態。
	* `ground`：false ＝ 不畫地上的影子；`"only"` ＝ 只畫影子。
	*/
	function drawCreature(ctx, r, pose = null, ground = true) {
		if (r.boss !== void 0) {
			drawBossFrame(ctx, r.boss, pose, ground);
			return;
		}
		const b = BODIES[r.body];
		const P = creaturePalette(r);
		const info = fxInfo(r);
		const pp = partPoseOf(r, P, pose);
		ctx.save();
		ctx.scale(r.size, r.size);
		const sh = pp?.shadow ?? 1;
		if (ground !== false && sh > 0) {
			ctx.save();
			ctx.fillStyle = "rgba(10,8,14,0.32)";
			ctx.beginPath();
			ctx.ellipse(pp?.root.dx ?? 0, .2, Math.max(7, b.len * .62) * sh, 2.4 * sh, 0, 0, TAU$2);
			ctx.fill();
			ctx.restore();
		}
		if (ground === "only") {
			ctx.restore();
			return;
		}
		if (pose !== null) applyCreaturePose(ctx, pose);
		const T0 = typeof ctx.getTransform === "function" ? ctx.getTransform() : null;
		const soft = (fn) => {
			if (pp?.softGround !== true || T0 === null) {
				fn();
				return;
			}
			ctx.save();
			ctx.setTransform(T0);
			fn();
			ctx.restore();
		};
		const rootOn = pp !== null && applyPartXf(ctx, pp.root, [0, 0]);
		const pa = pp?.alpha ?? 1;
		const flash = Math.max(pp?.flash ?? 0, pose === null ? 0 : cp(pose, "flash"));
		const ow = 1.3 / r.size;
		const mist = P.mat === "mist" ? .62 : 1;
		const hid = r.affixes.includes("mist_hidden") ? .75 : 1;
		withPose(r, pp, () => {
			if (r.traits.includes("mist")) soft(() => TRAITS["mist"].draw(ctx, info, P));
			const fade = P.mat === "mist" ? [1, b.top * .3] : null;
			if (r.affixes.includes("mirror")) layered(ctx, (g) => {
				g.translate(-9, -1);
				drawParts(g, r, P);
			}, {
				ow,
				alpha: .35 * pa,
				fade
			});
			layered(ctx, (g) => drawParts(g, r, P), {
				ow,
				alpha: mist * hid * pa,
				glow: r.glow,
				fade,
				flash,
				flashColor: pp?.flashColor
			});
			if (pp?.claws !== void 0 && pp.claws > 0) drawClaws(ctx, pp, rigKey(r));
			for (const t of r.traits) if (TRAITS[t].soft === true && t !== "mist") soft(() => TRAITS[t].draw(ctx, info, P));
			for (const a of r.affixes) if (AFFIX[a]?.soft === true) soft(() => AFFIX[a].draw(ctx, info));
			const fx = r.affixes.filter((a) => AFFIX[a] !== void 0 && AFFIX[a].soft !== true);
			const sparks = r.traits.includes("sparks");
			if (fx.length > 0 || sparks) layered(ctx, (g) => {
				if (sparks) TRAITS["sparks"].draw(g, info, P);
				for (const a of fx) AFFIX[a].draw(g, info);
			}, pa < 1 ? {
				ow: .8 / r.size,
				alpha: pa
			} : { ow: .8 / r.size });
		});
		if (rootOn) ctx.restore();
		if (pp !== null && pp.fx.length > 0 && pose?.fxTurn === void 0) drawCreatureFx(ctx, creatureFxShown(pp.fx, pose), r.element);
		ctx.restore();
	}
	/** 貼圖裡要畫的片段特效：樣張頁（`fxAll`）全畫；戰場上飛向目標的與蛋由技能特效畫，不畫進貼圖。 */
	function creatureFxShown(fx, pose) {
		return pose?.fxAll === true ? fx : fx.filter((f) => f.ranged !== true && f.lobbed !== true);
	}
	Object.fromEntries(Object.entries({
		str: "力量",
		dex: "敏捷",
		con: "體質",
		int: "智力",
		wis: "感知",
		wil: "意志"
	}).map(([k, v]) => [v, k]));
	/** 結果的顏色（成功綠、勉強黃、失敗紅）。 */
	var OUTCOME_COLOR = {
		success: "#5ad06a",
		partial: "#e8bb48",
		failure: "#e04a3a"
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/art-pm-9-027334/client/src/render/eventArtAwaken.ts
	/** 傳送陣中心（虛擬單位）。 */
	var AWAKEN_RING = {
		x: 208,
		y: 106.6
	};
	/**
	* 坐起：兩腿以髖為軸往前 90°（平貼地面），上身往後仰約 34°，兩手在髖部後方打直撐地。
	* RT-5d（必修 1，美術 PM）：RT-5c 的手停在髖部高度、沒碰到地。Q 版的手臂只到腰（肩到手約 8.9），上身後仰 30～35° 時肩膀離地約 14，
	* 原長怎麼轉都撐不到地，所以用骨架的臂長加量 `reach`／`reachF`（上臂、前臂沿方向拉長，手的大小不變）。
	* 數字由「手的下緣落在地面線上」反推：近側的手在髖後約 12.5、遠側的手再往後約 4（從近側的手後面露出來；兩條手臂都往後斜），
	* 遠側較遠、接地點在畫面上略高約 1 像素（遠側的手臂部件本來較短，又要伸得更後面，所以加量較多）。
	*/
	var AWAKEN_SIT_POSE = Object.freeze({
		hipN: Math.PI / 2,
		hipF: Math.PI / 2,
		lean: -.6,
		arm: 1.37,
		reach: .55,
		armF: 1.87,
		reachF: 1.1
	});
	var AWAKEN_HERO = {
		0: {
			x: AWAKEN_RING.x + 96,
			y: AWAKEN_RING.y + 30,
			rot: -1.5,
			pose: null,
			drop: 0
		},
		1: {
			x: AWAKEN_RING.x + 66,
			y: AWAKEN_RING.y + 44,
			rot: 0,
			pose: AWAKEN_SIT_POSE,
			drop: 13.5
		}
	};
	Object.freeze({
		hipN: -.5,
		hipF: -.5,
		lean: -.6,
		arm: .98,
		reach: .26,
		armF: 1.23,
		reachF: .45
	});
	AWAKEN_HERO[0], { ...AWAKEN_HERO[1] };
	/** 插圖的虛擬大小（事件卡上照卡寬等比縮放）。 */
	var EVENT_ART_W = 364;
	var EVENT_ART_H = 156;
	/** 已知的場景 ID（順序同樣張；伺服器 `EVENT_ART_IDS` 同一份）。 */
	var EVENT_ART_IDS = [
		"ambush",
		"chest",
		"stele",
		"altar",
		"villager",
		"caravan",
		"trap",
		"camp",
		"anomaly",
		"friend"
	];
	var HERO = {
		look: {
			skin: "#f1c9a5",
			hair: "short",
			hairColor: "#3a2414"
		},
		gear: {
			body: {
				kind: "leather",
				color: "#2f5a5a"
			},
			feet: {
				kind: "boots",
				material: "leather"
			},
			main_hand: {
				kind: "sword",
				material: "steel"
			}
		}
	};
	var BANDIT = {
		look: {
			skin: "#a8724c",
			hair: "short",
			hairColor: "#1a1a1a"
		},
		gear: {
			body: {
				kind: "leather",
				color: "#7a6a4a"
			},
			feet: {
				kind: "boots",
				material: "leather"
			},
			main_hand: {
				kind: "axe",
				material: "iron"
			},
			head: {
				kind: "hood",
				color: "#6a5a3a"
			}
		}
	};
	var VILLAGER = {
		look: {
			skin: "#e8b890",
			hair: "bun",
			hairColor: "#3a2414",
			bunBand: "#b8432f"
		},
		gear: {
			body: {
				kind: "robe",
				color: "#8a6a3a"
			},
			feet: {
				kind: "shoes",
				color: "#3a2a1a"
			}
		}
	};
	var MERCHANT = {
		look: {
			skin: "#f1c9a5",
			hair: "short",
			hairColor: "#2a1a10"
		},
		gear: { body: {
			kind: "robe",
			color: "#3a5ad0",
			trim: "#e8bb48"
		} }
	};
	/** 紙娃娃（腳底在 (x, y)）：`front` 正面、`side` 側面；`west` 朝左。 */
	function person(ctx, x, y, who, view, west = false, k = 1.1) {
		ctx.save();
		ctx.translate(x, y);
		ctx.scale(west ? -k : k, k);
		drawFigure(ctx, who, view === "front" ? "south" : "east");
		ctx.restore();
	}
	/** 異形犬（霧狼／灰燼犬）：腳下紅環＋本體（朝左）。 */
	function hound(ctx, x, y, bg) {
		const r = resolveCreature({ look: {
			body: "hound",
			material: bg === "ashen" ? "magma" : "fur",
			tint: "#c8ccd0"
		} });
		ctx.save();
		ctx.translate(x, y);
		enemyRing(ctx, 13);
		ctx.scale(-1, 1);
		drawCreature(ctx, r);
		ctx.restore();
	}
	function drawTrap(ctx, bg) {
		const cx = 182;
		const cy = 98.8;
		ctx.save();
		ctx.strokeStyle = OUT$6;
		ctx.lineWidth = 4;
		ctx.beginPath();
		ctx.ellipse(cx, cy, 20, 11, 0, 0, Math.PI * 2);
		ctx.stroke();
		ctx.strokeStyle = "#9aa0a8";
		ctx.lineWidth = 2.4;
		ctx.stroke();
		ctx.fillStyle = "#c8ccd0";
		for (let k = 0; k < 10; k++) {
			const a = k / 10 * Math.PI * 2;
			ctx.beginPath();
			ctx.moveTo(cx + Math.cos(a) * 20 - 2, cy + Math.sin(a) * 11);
			ctx.lineTo(cx + Math.cos(a) * 13, cy + Math.sin(a) * 6);
			ctx.lineTo(cx + Math.cos(a) * 20 + 2, cy + Math.sin(a) * 11);
			ctx.fill();
		}
		ctx.restore();
		if (bg !== "capital") ashObj(ctx, "grass", 2.9 * 52, 1.3 * 52);
		ctx.save();
		ctx.strokeStyle = "rgba(255,255,255,0.95)";
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.moveTo(196, 86.8);
		ctx.lineTo(204, 78.8);
		ctx.moveTo(200, 88.8);
		ctx.lineTo(208, 86.8);
		ctx.stroke();
		ctx.restore();
		person(ctx, 72.8, 2.85 * 52, HERO, "side");
	}
	function drawAnomaly(ctx) {
		const cx = 182;
		glow$1(ctx, cx, 83.2, 90, "rgba(160,120,255,0.9)", .6);
		ctx.save();
		ctx.shadowColor = "#c8a0ff";
		ctx.shadowBlur = 14;
		ctx.strokeStyle = "#e8d8ff";
		ctx.lineWidth = 3;
		ctx.beginPath();
		ctx.moveTo(122, 93.2);
		ctx.lineTo(162, 79.2);
		ctx.lineTo(cx, 95.2);
		ctx.lineTo(208, 75.2);
		ctx.lineTo(246, 89.2);
		ctx.stroke();
		ctx.restore();
		for (const [dx, h] of [
			[-30, 26],
			[8, 34],
			[40, 22]
		]) {
			ctx.beginPath();
			ctx.moveTo(cx + dx - 6, 91.2);
			ctx.lineTo(cx + dx, 91.2 - h);
			ctx.lineTo(cx + dx + 6, 91.2);
			ctx.closePath();
			ctx.fillStyle = "#c8bcff";
			ctx.fill();
			ctx.lineWidth = 1.5;
			ctx.strokeStyle = OUT$6;
			ctx.stroke();
		}
	}
	function drawStele(ctx, bg) {
		stele(ctx, 3, .8);
		ctx.save();
		ctx.shadowColor = "#8fe0ff";
		ctx.shadowBlur = 8;
		ctx.strokeStyle = "#8fe0ff";
		ctx.lineWidth = 1.4;
		for (const y of [
			1.15,
			1.3,
			1.45
		]) {
			ctx.beginPath();
			ctx.moveTo(3.4 * 52, y * 52);
			ctx.lineTo(3.6 * 52, y * 52);
			ctx.stroke();
		}
		ctx.restore();
		if (bg !== "capital") {
			mistWisp(ctx, 78, 62.4, 300);
			mistWisp(ctx, 218.4, 72.8, 900);
		}
		person(ctx, 1.8 * 52, 2.9 * 52, HERO, "side");
	}
	function drawFriend(ctx) {
		ctx.fillStyle = "rgba(255,255,255,0.85)";
		for (let k = 0; k < 7; k++) {
			const x = 31.2 + k * .55 * 52;
			const y = 114.4 - k * 6 + k % 2 * 8;
			ctx.beginPath();
			ctx.ellipse(x, y, 4, 6, .4, 0, Math.PI * 2);
			ctx.fill();
		}
		stele(ctx, 4.6, .7);
		bubble(ctx, 265.2, .9 * 52, "scroll", "info");
	}
	/** 祭壇的光：荒原紅光、雲嶺暖黃光、主城紫晶光。 */
	var ALTAR_GLOW = {
		cloud: "rgba(255,220,140,0.9)",
		ashen: "rgba(255,90,60,0.9)",
		capital: "rgba(170,150,255,0.9)"
	};
	/** 十種場景（需求第 3 節第 2 點）：小牌文字、小牌圖示、畫法。 */
	var SCENES = {
		ambush: {
			zh: "遭遇・伏擊",
			icon: "sword",
			draw(ctx, bg) {
				if (bg === "ashen") deadGrove(ctx, 0, 0, 2, 1);
				else if (bg === "cloud") {
					bambooGrove(ctx, 0, 0, 2, 1);
					bambooGrove(ctx, 260, 0, 2, 1);
				}
				person(ctx, 83.2, 2.85 * 52, HERO, "side");
				person(ctx, 239.2, 2.6 * 52, BANDIT, "side", true);
				person(ctx, 291.2, 114.4, BANDIT, "side", true);
				hound(ctx, 197.6, 2.9 * 52, bg);
				bubble(ctx, 239.2, 59.8, "bang", "danger");
			}
		},
		chest: {
			zh: "寶箱",
			icon: "coin",
			draw(ctx, bg) {
				chest(ctx, 3, 1);
				glow$1(ctx, 182, 1.55 * 52, 60, "rgba(255,230,140,0.9)", .45);
				if (bg === "ashen") ashObj(ctx, "dead_tree", 20.8, 0);
				else if (bg === "cloud") {
					pine(ctx, 20.8, 0);
					flowers(ctx, 234, 78, 4, 1);
				}
				boulder(ctx, 5.2 * 52, 62.4);
			}
		},
		stele: {
			zh: "古碑",
			icon: "ask",
			draw: drawStele
		},
		altar: {
			zh: "祭壇・機遇",
			icon: "rest",
			draw(ctx, bg) {
				if (bg === "ashen") for (let gx = 2; gx < 5; gx++) obsidianSlab(ctx, gx, 1);
				else if (bg !== "capital") for (let gx = 2; gx < 5; gx++) ground$1(ctx, "s", gx, 1);
				if (bg === "ashen") hornAltar(ctx, 156, 31.2);
				else altar(ctx, 156, 31.2);
				glow$1(ctx, 182, 62.4, 70, ALTAR_GLOW[bg], .35);
				if (bg === "ashen") {
					hornBrazier(ctx, 83.2, 31.2);
					hornBrazier(ctx, 228.8, 31.2);
				} else if (bg === "cloud") {
					stoneLantern(ctx, 83.2, 31.2);
					stoneLantern(ctx, 228.8, 31.2);
				}
			}
		},
		villager: {
			zh: "村民求助",
			icon: "bang",
			draw(ctx, bg) {
				cart(ctx, 3.6 * 52, 1.3 * 52);
				if (bg !== "capital") ground$1(ctx, "p", 3, 2);
				ashObj(ctx, "crate", 239.2, 98.8);
				person(ctx, 124.8, 145.6, VILLAGER, "front");
				bubble(ctx, 124.8, 1.55 * 52, "bang", "quest");
			}
		},
		caravan: {
			zh: "商隊",
			icon: "coin",
			draw(ctx) {
				cart(ctx, 114.4, 62.4);
				cart(ctx, 3.4 * 52, 1.3 * 52);
				ashObj(ctx, "crate", 239.2, 1.7 * 52);
				person(ctx, 280.8, 2.85 * 52, MERCHANT, "side", true);
				bubble(ctx, 280.8, 83.2, "coin", "talk");
				campfire(ctx, .8, 1.5);
			}
		},
		trap: {
			zh: "陷阱",
			icon: "warn",
			draw: drawTrap
		},
		camp: {
			zh: "營火休息",
			icon: "rest",
			draw(ctx) {
				campfire(ctx, 3, 1);
				glow$1(ctx, 182, 83.2, 90, "rgba(255,170,80,0.9)", .35);
				person(ctx, 119.6, 2.6 * 52, HERO, "side", false, 1);
				person(ctx, 244.4, 2.6 * 52, VILLAGER, "side", true, 1);
				ctx.fillStyle = "rgba(20,24,40,0.35)";
				ctx.fillRect(0, 0, EVENT_ART_W, EVENT_ART_H);
			}
		},
		anomaly: {
			zh: "異象・源晶裂痕",
			icon: "portal",
			draw: drawAnomaly
		},
		friend: {
			zh: "朋友的足跡",
			icon: "notes",
			draw: drawFriend
		}
	};
	/** 7×3 格的地面：雲嶺草地＋中間一段黃土路；荒原焦土＋右上角熔岩；主城白石板＋金色嵌線，再加遠處白牆與兩盞源晶燈。 */
	function drawGround(ctx, bg) {
		for (let gy = 0; gy < 3; gy++) for (let gx = 0; gx < 7; gx++) if (bg === "ashen") ashTile(ctx, gy === 0 && gx > 4 ? "lava" : "stone", gx, gy);
		else if (bg === "capital") capitalTile(ctx, gx, gy);
		else ground$1(ctx, gy === 1 && gx > 1 && gx < 5 ? "p" : "g", gx, gy);
		if (bg === "capital") capitalBackdrop(ctx);
	}
	var BADGE_FONT = "bold 13px 'Noto Sans TC', 'Microsoft JhengHei', sans-serif";
	/** 畫一張事件插圖（左上角在原點、大小 EVENT_ART_W×EVENT_ART_H）。 */
	function drawEventArt(ctx, scene, bg) {
		const s = SCENES[scene];
		const W = EVENT_ART_W;
		const H = EVENT_ART_H;
		ctx.save();
		ctx.beginPath();
		ctx.roundRect(0, 0, W, H, 12);
		ctx.clip();
		drawGround(ctx, bg);
		s.draw(ctx, bg);
		const v = ctx.createRadialGradient(W / 2, H / 2, H * .4, W / 2, H / 2, W * .62);
		v.addColorStop(0, "rgba(0,0,0,0)");
		v.addColorStop(1, "rgba(10,8,6,0.65)");
		ctx.fillStyle = v;
		ctx.fillRect(0, 0, W, H);
		ctx.restore();
		ctx.lineWidth = 2;
		ctx.strokeStyle = "#c8a868";
		ctx.beginPath();
		ctx.roundRect(1, 1, W - 2, H - 2, 12);
		ctx.stroke();
		ctx.font = BADGE_FONT;
		const tw = (ctx.measureText(s.zh)?.width ?? s.zh.length * 13) + 34;
		ctx.fillStyle = "rgba(24,20,16,0.85)";
		ctx.beginPath();
		ctx.roundRect(8, 8, tw, 24, 12);
		ctx.fill();
		ctx.strokeStyle = "#c8a868";
		ctx.lineWidth = 1.2;
		ctx.stroke();
		ICON$1[s.icon](ctx, 21, 20, 13, BADGE_ICON_INK);
		ctx.fillStyle = "#f2e6c8";
		ctx.textBaseline = "middle";
		ctx.fillText(s.zh, 32, 21);
	}
	//#endregion
	//#region entry.ts
	window.QEventLive = {
		ATTR_ART,
		CHIP_BG,
		D20_COLOR,
		MISC_ART,
		SOLUTION_ART,
		drawChip,
		drawD20,
		drawStoryIcon,
		d20ShowsValue,
		BADGE_ICON_INK,
		ICON: ICON$1,
		bubble,
		EVENT_ART_H,
		EVENT_ART_IDS,
		EVENT_ART_W,
		SCENES,
		drawEventArt,
		OUTCOME_COLOR
	};
	//#endregion
})();
