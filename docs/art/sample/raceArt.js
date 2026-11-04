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
    // 龍尾（11-04 晚加粗）：根部寬 9、往末端收尖，背上一排背棘、腹面淺色一道；不是細長的貓尾
    dragon: (ctx, look) => {
      const c = look.scaleColor ?? "#a8784a";
      for (const t of [0.22, 0.42, 0.62, 0.8]) fill(ctx, mix(c, "#ffffff", 0.3), () => { const x = 19 * t, y = -16.5 + 15 * t; ctx.moveTo(x - 2, y + 1); ctx.lineTo(x + 0.4, y - 4.2); ctx.lineTo(x + 2.2, y + 1.2); ctx.closePath(); });
      fill(ctx, c, () => { ctx.moveTo(0, -17); ctx.quadraticCurveTo(13, -15.5, 18.5, -3); ctx.lineTo(23, 1.5); ctx.lineTo(16.5, 0.6); ctx.quadraticCurveTo(9, -4.5, 0, -8); ctx.closePath(); });
      fill(ctx, mix(c, "#f4e6c8", 0.45), () => { ctx.moveTo(0, -10); ctx.quadraticCurveTo(8.5, -7, 15.5, -0.6); ctx.lineTo(16.5, 0.6); ctx.quadraticCurveTo(9, -4.5, 0, -8); ctx.closePath(); });
    },
    // 獸耳族的尾巴：貓（細長往上彎）、狼（粗、往下垂）、兔（小圓球）；狐照舊（蓬、末端白）
    cat: (ctx, look) => {
      const c = look.tailColor ?? look.hairColor ?? "#5a3a22";
      ctx.strokeStyle = c; ctx.lineWidth = 2; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(0, -12); ctx.bezierCurveTo(9, -11, 12, -17, 10, -24); ctx.stroke();
      fill(ctx, c, () => ctx.arc(10, -24.2, 1.3, 0, TAU));
    },
    wolf: (ctx, look) => {
      const c = look.tailColor ?? look.hairColor ?? "#7a7a84";
      fill(ctx, c, () => { ctx.moveTo(0, -14); ctx.quadraticCurveTo(9, -14, 11, -6); ctx.quadraticCurveTo(12, 0, 8.5, 2); ctx.quadraticCurveTo(7, -5, 0, -9); ctx.closePath(); });
      fill(ctx, mix(c, "#000000", 0.3), () => { ctx.moveTo(11.3, -2.5); ctx.quadraticCurveTo(12, 0.5, 8.5, 2); ctx.quadraticCurveTo(9.5, -0.5, 11.3, -2.5); ctx.closePath(); });
    },
    rabbit: (ctx, look, view) => {
      // 兔尾是小圓球：背面在正中，側面在後腰邊緣露出，正面被身體擋住
      fill(ctx, look.tailColor ?? mix(look.hairColor ?? "#e8e0c8", "#ffffff", 0.5), () => ctx.arc(view === "back" ? 0 : 6, -10.5, 2.4, 0, TAU));
    },
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
  // 龍裔選項：龍翼（收在背後）與背刺；正面、側面畫在身體後面，背面畫在披風之上
  function wings(ctx, look, view) {
    if (!look.wings) return;
    const c = look.scaleColor ?? "#a8784a", m = mix(c, "#ffffff", 0.25);
    for (const s of [-1, 1]) {
      fill(ctx, dark(c, 0.15), () => { ctx.moveTo(s * 4, -22); ctx.lineTo(s * 15, -34); ctx.lineTo(s * 16, -22); ctx.lineTo(s * 13, -16); ctx.lineTo(s * 9, -19); ctx.lineTo(s * 6, -15); ctx.closePath(); });
      ctx.strokeStyle = m; ctx.lineWidth = 0.9; ctx.beginPath(); ctx.moveTo(s * 5, -21); ctx.lineTo(s * 15, -33); ctx.moveTo(s * 9, -25); ctx.lineTo(s * 13, -16); ctx.stroke();
    }
  }
  function spines(ctx, look) {
    if (!look.spines) return;
    const c = look.scaleColor ?? "#a8784a";
    for (const [x, y] of [[-5, -24], [0, -25], [5, -24]]) fill(ctx, mix(c, "#ffffff", 0.2), () => { ctx.moveTo(x - 1.8, y + 2); ctx.lineTo(x, y - 4); ctx.lineTo(x + 1.8, y + 2); ctx.closePath(); });
  }
  function tail(ctx, look, view, side) {
    wings(ctx, look, view);
    spines(ctx, look);
    const draw = TAIL[look.tail === "fox" && look.beastEars && TAIL[look.beastEars] ? look.beastEars : look.tail];
    if (!draw) return;
    ctx.save();
    // 側面：尾巴朝身後；正面：從角色左腰（畫面右）露出；背面：同一側＝角色左邊，在畫面左（第 7 版；審查：「正面和背面都在畫面右側」是照抄）
    const dir = side === 1 ? -1 : side === -1 ? 1 : view === "back" ? -1 : 1;
    ctx.scale(dir, 1);
    if (view === "back") ctx.translate(0, 2);
    draw(ctx, look, view);
    // 背面：尾巴根部在背上看得到，補一個圓的尾根，不留直線切口（第 7 版）
    const kind = look.tail === "fox" && look.beastEars && TAIL[look.beastEars] ? look.beastEars : look.tail;
    const root = { fox: [-11, 2.3, look.tailColor ?? look.hairColor ?? "#d8762a"], dragon: [-12.5, 4.6, look.scaleColor ?? "#a8784a"], wolf: [-11.5, 2.6, look.tailColor ?? look.hairColor ?? "#7a7a84"], scaled: [-11.5, 2.6, look.tailColor ?? dark(look.skin, 0.15)] }[kind];
    if (view === "back" && root) fill(ctx, root[2], () => ctx.ellipse(0.4, root[0], root[1] * 0.9, root[1], 0, 0, TAU));
    ctx.restore();
  }

  // ---- 臉：紋路、鬍子、獠牙（背面不畫）----
  function face(ctx, look, view, side, west = false) {
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
      // 金屬片在角色的左半邊臉（正面在畫面右）。側面：朝西時左臉在近側→看得到；朝東時左臉在遠側→看不到（第 7 版；審查：「朝東時義體在近側」）
      const s = side === -1 ? -1 : 1;
      if (view !== "side" || west) {
      fill(ctx, "#9aa4b0", () => { ctx.arc(0, -29, 8.5, s > 0 ? -Math.PI / 2 : Math.PI / 2, s > 0 ? Math.PI / 2 : Math.PI * 1.5); ctx.closePath(); });
      ctx.save(); ctx.strokeStyle = "#4ae0d0"; ctx.lineWidth = 0.9; ctx.shadowColor = "#4ae0d0"; ctx.shadowBlur = 2;
      ctx.beginPath(); ctx.moveTo(s * 1, -36); ctx.lineTo(s * 4, -33); ctx.lineTo(s * 4, -25); ctx.lineTo(s * 7, -23); ctx.stroke();
      fill(ctx, "#4ae0d0", () => ctx.arc(ex + s * 2.9, -28.5, 1.5, 0, TAU));
      ctx.restore();
      }
    }
    if (look.pattern === "dragonscale") {
      const c = look.scaleColor ?? "#a8784a";
      fill(ctx, c, () => { for (const [x, y] of [[-7, -27], [-6, -24.5], [-4.5, -22.5], [7, -27], [6, -24.5], [4.5, -22.5], [-7.5, -30], [7.5, -30]]) { ctx.moveTo(ex + x + 1.5, y); ctx.arc(ex + x, y, 1.5, 0, Math.PI); } });
    }
    if (look.pattern === "dragonQ") {
      const c = look.scaleColor ?? "#a8784a";
      // 第 7 版（審查：「金色豎瞳加臉頰短線仍然像貓；側臉的鱗片戳出輪廓」）：拿掉臉頰的半圓鱗（看起來像貓鬍鬚）和豎瞳；
      //   改成太陽穴兩片菱形鱗（接在龍角根部）＋額頭一片，眼睛是一般方眼、琥珀色；全部在頭的輪廓裡面
      const dia = (x, y, r) => { ctx.moveTo(x, y - r * 1.25); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r * 1.25); ctx.lineTo(x - r, y); ctx.closePath(); };
      const pts = view === "side" ? [[2.2, -31.8, 1.1], [0.6, -34.4, 1.0]] : [[-6, -31.4, 1.1], [-4.7, -34.2, 1.0], [6, -31.4, 1.1], [4.7, -34.2, 1.0]];
      fill(ctx, c, () => { for (const [x, y, r] of pts) dia(x, y, r); });
      fill(ctx, c, () => dia(view === "side" ? 5.2 : 0, -35.6, 1.1));
      // 眉骨：眼睛上方一道深色短線（龍的眉棱），和貓的圓眼分開
      ctx.strokeStyle = dark(look.skin, 0.4); ctx.lineWidth = 0.9; ctx.lineCap = "round";
      for (const [x, ok] of [[ex + 2.9, side === 0 || side === 1], [ex - 2.9, side === 0 || side === -1]]) if (ok) { const o = x > ex ? 1 : -1; ctx.beginPath(); ctx.moveTo(x - o * 1.4, -31.6); ctx.lineTo(x + o * 1.3, -31); ctx.stroke(); }
    }
    if (look.ridge) {
      const c = look.scaleColor ?? "#a8784a";
      for (const y of [-35.5, -33, -30.5]) fill(ctx, c, () => { ctx.moveTo(ex - 1.3, y + 1.2); ctx.lineTo(ex, y - 1.2); ctx.lineTo(ex + 1.3, y + 1.2); ctx.closePath(); });
    }
    if (look.slitEyes) {
      ctx.save(); ctx.shadowColor = "#ffcf4a"; ctx.shadowBlur = 3;
      for (const [x, ok] of [[ex + 2.9, side === 0 || side === 1], [ex - 2.9, side === 0 || side === -1]]) if (ok) {
        fill(ctx, "#ffcf4a", () => ctx.ellipse(x, -28.5, 1.5, 1.9, 0, 0, TAU));
        fill(ctx, "#1d1a22", () => ctx.rect(x - 0.35, -30.2, 0.7, 3.4));
      }
      ctx.restore();
    }
    if (look.tusks) for (const s of view === "side" ? [1] : [-1, 1]) fill(ctx, "#f4ecd8", () => { ctx.moveTo(ex + s * 2.5, -24); ctx.lineTo(ex + s * 3.4, -27); ctx.lineTo(ex + s * 4, -24); ctx.closePath(); });
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
  // 獸耳族（原狐族，#138）的四種耳朵：狐（大而尖）、貓（小三角、圓頭）、狼（直立、窄、外緣深色）、兔（長、直立）；花色跟著髮色
  //   view：front／back 兩耳左右對稱；side（朝東）兩耳一前一後疊在頭頂，靠後的那隻稍低（不是正面照抄）
  function beastEar(ctx, look, s, color, view = "front") {
    const c = color ?? look.earColor ?? look.hairColor ?? "#d8762a", kind = look.beastEars ?? "fox", inner = "#f2c8b0";
    const sd = view === "side", back = view === "back";
    // 側面：s=−1 是後耳（往後 3、低 1），s=+1 是前耳；正面、背面照 s 左右
    const X = (x) => (sd ? (s > 0 ? x - 4.5 : x - 8.6) : s * x), dy = sd && s < 0 ? 1 : 0;
    const tri = (pts, col) => fill(ctx, col, () => { pts.forEach(([x, y], i) => (i ? ctx.lineTo(X(x), y + dy) : ctx.moveTo(X(x), y + dy))); ctx.closePath(); });
    const showInner = !color && !back && !(sd && s < 0); // 背面、側面的後耳看不到內側
    if (kind === "cat") { tri([[2.8, -35.5], [5.4, -41.6], [8.4, -34.2]], c); if (showInner) tri([[4, -35.6], [5.4, -39.6], [7.1, -35]], inner); return; }
    if (kind === "wolf") { tri([[3.4, -36], [5.6, -46], [8, -34.6]], c); fill(ctx, mix(c, "#000000", 0.3), () => { ctx.moveTo(X(5.6), -46 + dy); ctx.lineTo(X(8), -34.6 + dy); ctx.lineTo(X(7.1), -36.5 + dy); ctx.closePath(); }); if (showInner) tri([[4.5, -36.2], [5.6, -43], [6.9, -35.6]], inner); return; }
    if (kind === "rabbit") { fill(ctx, c, () => ctx.ellipse(X(4.2), -43 + dy, 2.2, 7.6, sd ? -0.25 : s * 0.12, 0, TAU)); if (showInner) fill(ctx, inner, () => ctx.ellipse(X(4.2), -42.4 + dy, 1.1, 5.6, sd ? -0.25 : s * 0.12, 0, TAU)); return; }
    tri([[2.5, -36], [6.5, -45], [8.5, -34]], c); if (showInner) tri([[4, -36], [6.3, -42], [7.3, -35.5]], inner);
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
      for (const s of [-1, 1]) beastEar(ctx, look, s, undefined, view === "side" && side ? "side" : view);
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
      if (kind === "dragon") {
        // 龍角（11-04 晚重做，使用者：「這龍人太像貓人了」）：象牙色、兩對往後掃。正面看是從太陽穴往外、往後掃的粗角（不往上豎，和獸耳、角魔的上捲大角分開）；
        // 側面從額頭往後掃過頭頂。角上兩道深色環紋。
        if (view === "side") {
          if (s > 0) continue; // 側面兩支疊在一起，只畫一次
          fill(ctx, c, () => { ctx.moveTo(3.8, -35.2); ctx.quadraticCurveTo(-3, -43.5, -13, -40.5); ctx.quadraticCurveTo(-5, -39.2, 0.2, -33.2); ctx.closePath(); });
          fill(ctx, c, () => { ctx.moveTo(-1.5, -32.5); ctx.quadraticCurveTo(-6.5, -35.5, -11, -33); ctx.quadraticCurveTo(-6.5, -32.6, -2.5, -30.3); ctx.closePath(); });
          ctx.strokeStyle = dark(c, 0.28); ctx.lineWidth = 0.7;
          for (const [x0, y0, x1, y1] of [[-2.5, -40.2, -1.2, -37.4], [-7, -41.3, -6.2, -39]]) { ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); }
          continue;
        }
        fill(ctx, c, () => { ctx.moveTo(s * 4, -36); ctx.quadraticCurveTo(s * 10, -41.5, s * 15.5, -38.5); ctx.quadraticCurveTo(s * 10.5, -37.5, s * 7.6, -33.4); ctx.closePath(); });
        fill(ctx, c, () => { ctx.moveTo(s * 7.4, -31.6); ctx.quadraticCurveTo(s * 11.2, -33.6, s * 13.6, -30.6); ctx.quadraticCurveTo(s * 10.6, -30.6, s * 8.2, -29.4); ctx.closePath(); });
        ctx.strokeStyle = dark(c, 0.28); ctx.lineWidth = 0.7;
        for (const [x0, y0, x1, y1] of [[8.4, -39.4, 8.8, -36.4], [11.8, -39.9, 11.6, -37.4]]) { ctx.beginPath(); ctx.moveTo(s * x0, y0); ctx.lineTo(s * x1, y1); ctx.stroke(); }
        continue;
      }
      if (view === "side") {
        // 側面（第 7 版；審查：「角魔側面兩隻角照正面左右攤開」）：近側一支從頭頂往上、往後捲；遠側那支在後面、顏色深一點，只露出角尖
        if (s > 0) continue;
        const big = kind !== "small", horn = (dx, dy) => { ctx.moveTo(3.2 + dx, -36.2 + dy); if (big) { ctx.quadraticCurveTo(5.5 + dx, -47 + dy, -6.5 + dx, -47.5 + dy); ctx.quadraticCurveTo(0.8 + dx, -44 + dy, -0.6 + dx, -37.4 + dy); } else { ctx.quadraticCurveTo(4.6 + dx, -42 + dy, 0.5 + dx, -44 + dy); ctx.quadraticCurveTo(2 + dx, -40.5 + dy, 0 + dx, -37 + dy); } ctx.closePath(); };
        fill(ctx, dark(c, 0.25), () => horn(-3.2, 0.8));
        fill(ctx, c, () => horn(0, 0));
        continue;
      }
      if (kind === "small") fill(ctx, c, () => { ctx.moveTo(s * 3.5, -36); ctx.quadraticCurveTo(s * 6, -42, s * 9.5, -43); ctx.quadraticCurveTo(s * 7, -39, s * 6.5, -35.5); ctx.closePath(); });
      else fill(ctx, c, () => { ctx.moveTo(s * 5, -35); ctx.quadraticCurveTo(s * 14, -38, s * 12, -47); ctx.quadraticCurveTo(s * 10.5, -41, s * 7.5, -38.5); ctx.quadraticCurveTo(s * 7, -36, s * 7, -33); ctx.closePath(); });
    }
  }

  // ---- 10 族（玩法 PM：人類、精靈、狐族、龍裔、矮人、晶能義體人、獸人、角魔、鱗族、海民）----
  const RACES = {
    human: { zh: "人類", realm: "晶冠", look: { skin: "#f1c9a5", hair: "short", hairColor: "#6a3d1e" } },
    elf: { zh: "精靈", realm: "晶冠", look: { skin: "#f6e0cc", hair: "long", hairColor: "#e8e0c8", ears: "pointed", build: "tall" } },
    fox: { zh: "狐族", realm: "雲嶺", look: { skin: "#f1d0b0", hair: "short", hairColor: "#d8762a", ears: "beast", tail: "fox" } },
    // 龍裔（11-04 晚重做、第 7 版改臉）：往後掃的象牙色龍角兩對、太陽穴與額頭菱形鱗、琥珀色方眼＋眉骨、粗龍尾；鱗色走銅、紅、金、黑曜（和鱗族的藍綠分開）
    dragonkin: { zh: "龍裔", realm: "雲嶺", look: { skin: "#d8a878", hair: "short", hairColor: "#3a2418", horns: "dragon", hornColor: "#efe6cc", pattern: "dragonQ", scaleColor: "#a8784a", tail: "dragon", eyes: "#9a4a12" } }, // 第 7 版：拿掉豎瞳（像貓），琥珀色方眼＋眉骨
    dwarf: { zh: "矮人", realm: "樞市", look: { skin: "#e8b890", hair: "short", hairColor: "#a8481e", beard: true, build: "stout" } },
    cyborg: { zh: "晶能義體人", realm: "樞市", look: { skin: "#e6c4a4", hair: "short", hairColor: "#2a2a34", pattern: "circuit" } },
    orc: { zh: "獸人", realm: "灰燼", look: { skin: "#86a060", hair: "short", hairColor: "#1e1a14", tusks: true, build: "tall" } },
    fiend: { zh: "角魔", realm: "灰燼", look: { skin: "#b07a7a", hair: "long", hairColor: "#1e1418", horns: "curved", hornColor: "#3a2a2a", tail: "demon" } },
    scalefolk: { zh: "鱗族", realm: "霜潮", look: { skin: "#78b4aa", ears: "fin", pattern: "scales", eyes: "#103030" } },
    seafolk: { zh: "海民", realm: "霜潮", look: { skin: "#b07a52", hair: "long", hairColor: "#2a8a9a", pattern: "marks", markColor: "#3aa8e0" } },
  };

  return { build, tail, face, ears, hat, horns, RACES, COVERS };
})();
