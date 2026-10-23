// 可玩種族的部件（美術樣張，2026-10-24；使用者：「種族 A、美術乙，好 寫入，開始畫樣張」）。
// 同一副紙娃娃骨架＋種族部件：體型、尾巴、臉部紋路、耳朵、角；頭部裝備照常疊上去。
// 外觀全部由 look 的欄位決定（都選填，不認得的值＝沒有，不會出錯）：
//   build: normal|stout|tall   tail: none|fox|scaled|demon   pattern: none|scales|marks|circuit
//   ears: none|pointed|fin|beast   horns: none|small|curved   beard: bool   tusks: bool   + 既有的 skin、hair、hairColor
// 和頭部裝備的衝突規則寫在「頭部裝備種類」上（COVERS），新增帽子或種族時不用一一配對。
// 由 paperdoll.js 的 drawFigure 呼叫（window.RaceArt 存在時）。
window.RaceArt = (() => {
  const TAU = Math.PI * 2;
  function fill(ctx, c, path) { ctx.fillStyle = c; ctx.beginPath(); path(); ctx.fill(); }
  function hexRgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  function mix(a, b, t) {
    const [r1, g1, b1] = hexRgb(a), [r2, g2, b2] = hexRgb(b);
    const m = (x, y) => Math.round(x * (1 - t) + y * t);
    return `#${((m(r1, r2) << 16) | (m(g1, g2) << 8) | m(b1, b2)).toString(16).padStart(6, "0")}`;
  }
  const dark = (c, t = 0.3) => mix(c, "#000000", t);

  // 頭部裝備遮住哪裡：top＝頭頂、side＝兩側、hood＝兜帽（有耳朵版）
  const COVERS = {
    helmet: { top: true, side: true }, greathelm: { top: true, side: true }, horned_helm: { top: true, side: true },
    hood: { top: true, side: true, hood: true },
    cap: { top: true }, bandana: { top: true }, crown: {},
    wide_hat: { top: true, tall: true }, wizard_hat: { top: true, tall: true },
  };
  const coverOf = (head) => (head ? COVERS[head.kind] ?? { top: true } : {});

  // ---- 體型（整個人含裝備一起縮放；腳底為原點） ----
  function build(ctx, look) {
    if (look.build === "stout") ctx.scale(1.12, 0.88);
    else if (look.build === "tall") ctx.scale(0.96, 1.1);
  }

  // ---- 尾巴：正面、側面畫在身體後面（從腰側露出）；背面畫在披風之上 ----
  const TAIL = {
    fox: (ctx, look) => {
      const c = look.tailColor ?? look.hairColor ?? "#d8762a";
      fill(ctx, c, () => { ctx.moveTo(0, -13); ctx.quadraticCurveTo(10, -14, 14, -6); ctx.quadraticCurveTo(17, 2, 11, 0); ctx.quadraticCurveTo(8, -6, 0, -9); ctx.closePath(); });
      fill(ctx, "#f4ece0", () => ctx.ellipse(13.5, -1.5, 3, 2.4, 0.4, 0, TAU));
    },
    scaled: (ctx, look) => {
      const c = look.tailColor ?? dark(look.skin, 0.15);
      fill(ctx, c, () => { ctx.moveTo(0, -14); ctx.quadraticCurveTo(9, -12, 15, -3); ctx.lineTo(17, -1); ctx.quadraticCurveTo(8, -6, 0, -9); ctx.closePath(); });
      ctx.strokeStyle = dark(c); ctx.lineWidth = 0.8;
      for (const t of [0.3, 0.55, 0.8]) { ctx.beginPath(); ctx.moveTo(15 * t, -13 + 10 * t); ctx.lineTo(15 * t + 1.5, -10 + 8 * t); ctx.stroke(); }
    },
    demon: (ctx, look) => {
      const c = look.tailColor ?? dark(look.skin, 0.25);
      ctx.strokeStyle = c; ctx.lineWidth = 1.8; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(0, -12); ctx.quadraticCurveTo(12, -10, 13, -2); ctx.stroke();
      fill(ctx, c, () => { ctx.moveTo(13, -2); ctx.lineTo(10.5, 1.5); ctx.lineTo(13, 4.5); ctx.lineTo(15.5, 1.5); ctx.closePath(); });
    },
  };
  function tail(ctx, look, view, side) {
    const draw = TAIL[look.tail];
    if (!draw) return;
    ctx.save();
    // 側面：尾巴朝身後；正面：從右腰露出；背面：往右下垂
    const dir = side === 1 ? -1 : side === -1 ? 1 : 1;
    ctx.scale(dir, 1);
    if (view === "back") ctx.translate(0, 2);
    draw(ctx, look);
    ctx.restore();
  }

  // ---- 臉：紋路、鬍子、獠牙（背面不畫）----
  function face(ctx, look, view, side) {
    if (view === "back") return;
    const ex = side * 2.6;
    if (look.pattern === "scales") {
      fill(ctx, dark(look.skin, 0.22), () => { for (const [x, y] of [[-6, -25], [-4.5, -23.5], [5.5, -25], [4, -23.5], [-1, -35], [1.5, -35.5]]) { ctx.moveTo(ex + x + 1.1, y); ctx.arc(ex + x, y, 1.1, 0, Math.PI); } });
    } else if (look.pattern === "marks") {
      ctx.strokeStyle = look.markColor ?? "#2a8ac8"; ctx.lineWidth = 1.1;
      for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(ex + s * 4, -27); ctx.quadraticCurveTo(ex + s * 6, -25, ex + s * 5, -23); ctx.stroke(); }
      ctx.beginPath(); ctx.moveTo(ex - 1.5, -35); ctx.lineTo(ex, -33); ctx.lineTo(ex + 1.5, -35); ctx.stroke();
    } else if (look.pattern === "circuit") {
      // 晶能義體人：半邊臉的金屬片＋晶能線＋發光義眼
      const s = side === -1 ? -1 : 1;
      fill(ctx, "#9aa4b0", () => { ctx.arc(0, -29, 8.5, s > 0 ? -Math.PI / 2 : Math.PI / 2, s > 0 ? Math.PI / 2 : Math.PI * 1.5); ctx.closePath(); });
      ctx.save(); ctx.strokeStyle = "#4ae0d0"; ctx.lineWidth = 0.9; ctx.shadowColor = "#4ae0d0"; ctx.shadowBlur = 2;
      ctx.beginPath(); ctx.moveTo(s * 1, -36); ctx.lineTo(s * 4, -33); ctx.lineTo(s * 4, -25); ctx.lineTo(s * 7, -23); ctx.stroke();
      fill(ctx, "#4ae0d0", () => ctx.arc(ex + s * 2.9, -28.5, 1.5, 0, TAU));
      ctx.restore();
    }
    if (look.tusks) for (const s of [-1, 1]) fill(ctx, "#f4ecd8", () => { ctx.moveTo(ex + s * 2.5, -24); ctx.lineTo(ex + s * 3.4, -27); ctx.lineTo(ex + s * 4, -24); ctx.closePath(); });
    if (look.beard) {
      const c = look.hairColor ?? "#8a4a22";
      fill(ctx, c, () => { ctx.moveTo(ex - 7, -27); ctx.quadraticCurveTo(ex - 7, -18, ex, -16); ctx.quadraticCurveTo(ex + 7, -18, ex + 7, -27); ctx.quadraticCurveTo(ex, -23, ex - 7, -27); });
      fill(ctx, dark(c), () => ctx.rect(ex - 2, -25.5, 4, 1)); // 嘴
    }
  }

  // ---- 耳朵 ----
  function sideEar(ctx, look, s, kind) {
    const c = look.skin;
    if (kind === "pointed") fill(ctx, c, () => { ctx.moveTo(s * 7.5, -31); ctx.lineTo(s * 15, -36); ctx.lineTo(s * 8, -27); ctx.closePath(); });
    else {
      // 鰭耳：扇形＋骨線
      fill(ctx, mix(c, "#9fe6ff", 0.25), () => { ctx.moveTo(s * 7.5, -32); ctx.lineTo(s * 14, -36); ctx.lineTo(s * 15, -31); ctx.lineTo(s * 13, -27); ctx.lineTo(s * 8, -27); ctx.closePath(); });
      ctx.strokeStyle = dark(c, 0.35); ctx.lineWidth = 0.7;
      for (const [x, y] of [[14, -35], [14.6, -31], [13, -27.5]]) { ctx.beginPath(); ctx.moveTo(s * 8, -29.5); ctx.lineTo(s * x, y); ctx.stroke(); }
    }
  }
  function beastEar(ctx, look, s, color) {
    const c = color ?? look.earColor ?? look.hairColor ?? "#d8762a";
    fill(ctx, c, () => { ctx.moveTo(s * 2.5, -36); ctx.lineTo(s * 6.5, -45); ctx.lineTo(s * 8.5, -34); ctx.closePath(); });
    if (!color) fill(ctx, "#f2c8b0", () => { ctx.moveTo(s * 4, -36); ctx.lineTo(s * 6.3, -42); ctx.lineTo(s * 7.3, -35.5); ctx.closePath(); });
  }
  function ears(ctx, look, view, side, head, phase) {
    const kind = look.ears;
    if (!kind || kind === "none" || phase !== "over") return;
    const cov = coverOf(head);
    if (kind === "pointed" || kind === "fin") {
      if (cov.hood) return; // 兜帽蓋住側耳
      const sides = side === 0 || view === "back" ? [-1, 1] : [-side]; // 側面只看得到靠鏡頭那一側（樣張簡化：畫遠側的伸出）
      for (const s of sides) sideEar(ctx, look, s, kind);
      return;
    }
    if (kind === "beast") {
      if (cov.hood) { for (const s of [-1, 1]) beastEar(ctx, look, s * 0.9, head.color ?? "#5a4a3a"); return; } // 有耳朵的兜帽
      if (cov.top && !["cap", "bandana"].includes(head?.kind)) return; // 頭盔、寬帽、巫師帽：藏起來
      for (const s of [-1, 1]) beastEar(ctx, look, s);
    }
  }

  // ---- 頭部裝備的調整（有角時）----
  function hat(ctx, look, head, draw) {
    if (!head) return;
    const horned = look.horns && look.horns !== "none";
    if (!horned) { draw(head); return; }
    if (head.kind === "horned_helm") { draw({ ...head, kind: "helmet" }); return; } // 種族角取代角盔的裝飾角
    ctx.save();
    if (["cap", "bandana", "crown"].includes(head.kind)) { ctx.translate(0, -29); ctx.scale(0.8, 1); ctx.translate(0, 29); } // 戴在兩角之間
    else if (COVERS[head.kind]?.tall) ctx.translate(0, -5); // 寬帽、巫師帽抬高、架在角上
    draw(head);
    ctx.restore();
  }

  // ---- 角：永遠在最上層 ----
  function horns(ctx, look, view, side) {
    const kind = look.horns;
    if (!kind || kind === "none") return;
    const c = look.hornColor ?? "#efe6cc";
    for (const s of [-1, 1]) {
      if (kind === "small") fill(ctx, c, () => { ctx.moveTo(s * 3.5, -36); ctx.quadraticCurveTo(s * 6, -42, s * 9.5, -43); ctx.quadraticCurveTo(s * 7, -39, s * 6.5, -35.5); ctx.closePath(); });
      else fill(ctx, c, () => { ctx.moveTo(s * 5, -35); ctx.quadraticCurveTo(s * 14, -38, s * 12, -47); ctx.quadraticCurveTo(s * 10.5, -41, s * 7.5, -38.5); ctx.quadraticCurveTo(s * 7, -36, s * 7, -33); ctx.closePath(); });
    }
  }

  // ---- 10 族（玩法 PM：人類、精靈、狐族、龍裔、矮人、晶能義體人、獸人、角魔、鱗族、海民）----
  const RACES = {
    human: { zh: "人類", realm: "晶冠", look: { skin: "#f1c9a5", hair: "short", hairColor: "#6a3d1e" } },
    elf: { zh: "精靈", realm: "晶冠", look: { skin: "#f6e0cc", hair: "long", hairColor: "#e8e0c8", ears: "pointed", build: "tall" } },
    fox: { zh: "狐族", realm: "雲嶺", look: { skin: "#f1d0b0", hair: "short", hairColor: "#d8762a", ears: "beast", tail: "fox" } },
    dragonkin: { zh: "龍裔", realm: "雲嶺", look: { skin: "#d8a878", hair: "short", hairColor: "#3a2418", horns: "small", hornColor: "#e8d8b8", pattern: "scales", tail: "scaled", tailColor: "#a8784a" } },
    dwarf: { zh: "矮人", realm: "樞市", look: { skin: "#e8b890", hair: "short", hairColor: "#a8481e", beard: true, build: "stout" } },
    cyborg: { zh: "晶能義體人", realm: "樞市", look: { skin: "#e6c4a4", hair: "short", hairColor: "#2a2a34", pattern: "circuit" } },
    orc: { zh: "獸人", realm: "灰燼", look: { skin: "#86a060", hair: "short", hairColor: "#1e1a14", tusks: true, build: "tall" } },
    fiend: { zh: "角魔", realm: "灰燼", look: { skin: "#b07a7a", hair: "long", hairColor: "#1e1418", horns: "curved", hornColor: "#3a2a2a", tail: "demon" } },
    scalefolk: { zh: "鱗族", realm: "霜潮", look: { skin: "#78b4aa", ears: "fin", pattern: "scales", eyes: "#103030" } },
    seafolk: { zh: "海民", realm: "霜潮", look: { skin: "#b07a52", hair: "long", hairColor: "#2a8a9a", pattern: "marks", markColor: "#3aa8e0" } },
  };

  return { build, tail, face, ears, hat, horns, RACES, COVERS };
})();
