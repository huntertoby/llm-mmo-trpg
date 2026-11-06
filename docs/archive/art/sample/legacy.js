// 「目前的畫面」與「Kenney 資源包版」的重現：照 client/src/render/BattleRenderer.ts（main）與
// 3-13 進行中的修改（agent worktree 未合併的 sprites.ts 對照表）用 Canvas 2D 畫出同一場景。
window.LegacyRender = (() => {
  const S = window.SCENE;
  const U = window.SCENE_UTIL;
  const T = 52;
  const TERRAIN = { stone: 0x9a968c, grass: 0x6f9a52, dirt: 0x9b7a55, chasm: 0x111118, lava: 0xd8471c, ice_hole: 0x17345c, wall: 0x4a4440 };
  const SURF = {
    oil: [0x2b2416, 0.6], water: [0x3a7bd5, 0.55], fire: [0xff7a1a, 0.7], ice: [0xc8ecff, 0.7],
    poison: [0x7bc043, 0.6], smoke: [0xb8b8c0, 0.6],
  };
  const OBJ = {
    wooden_bridge: ["橋", 0x8a5a2b, true], oil_barrel: ["油", 0x5a3a1a, false], stone_pillar: ["柱", 0x6b6b6b, false],
    crate: ["箱", 0xb07a3a, false], earth_wall: ["土", 0x7a5a3a, false], low_wall: ["矮", 0x8a8070, false],
    fallen_log: ["木", 0x6a4a2a, false], dead_tree: ["樹", 0x5a4a32, false],
  };
  const TEAM = { ally: 0x2f7de1, enemy: 0xd23c3c };
  const SUMMON = 0x5eead4;
  const ACTIVE = 0xffe14d;
  const DEADLY = 0xff3030;
  const FLAM = 0xe0a040;

  const ch = (c, s) => (c >> s) & 0xff;
  const rgb = (r, g, b) => {
    const c = (v) => Math.max(0, Math.min(255, Math.round(v)));
    return (c(r) << 16) | (c(g) << 8) | c(b);
  };
  const blend = (base, over, a) => {
    const m = (s) => ch(base, s) * (1 - a) + ch(over, s) * a;
    return rgb(m(16), m(8), m(0));
  };
  const shade = (color, h) => {
    const f = 0.78 + 0.12 * Math.max(0, Math.min(3, h));
    return rgb(ch(color, 16) * f, ch(color, 8) * f, ch(color, 0) * f);
  };
  const css = (n, a = 1) => `rgba(${ch(n, 16)},${ch(n, 8)},${ch(n, 0)},${a})`;
  const FONT = '"Noto Sans TC","Microsoft JhengHei",sans-serif';

  function text(ctx, s, x, y, size, color, { align = "center", base = "middle", stroke = 0, alpha = 1 } = {}) {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.font = `700 ${size}px ${FONT}`;
    ctx.textAlign = align;
    ctx.textBaseline = base;
    if (stroke) {
      ctx.lineWidth = stroke;
      ctx.strokeStyle = "#000";
      ctx.lineJoin = "round";
      ctx.strokeText(s, x, y);
    }
    ctx.fillStyle = color;
    ctx.fillText(s, x, y);
    ctx.restore();
  }

  function poly(ctx, pts) {
    ctx.beginPath();
    ctx.moveTo(pts[0], pts[1]);
    for (let i = 2; i < pts.length; i += 2) ctx.lineTo(pts[i], pts[i + 1]);
    ctx.closePath();
  }

  // ---- Kenney 圖庫 ----
  const KT = {
    stone: ["tiny-town", "0109"], grass: ["tiny-town", "0000"], dirt: ["tiny-town", "0025"], wall: ["tiny-dungeon", "0058"],
    lava: ["tiny-town", "0109", 0xff6a2a], chasm: ["tiny-town", "0109", 0x2a2a3c], ice_hole: ["tiny-town", "0109", 0x3a6aa8],
  };
  const KO = {
    wooden_bridge: ["tiny-dungeon", "0080"], oil_barrel: ["tiny-town", "0130"], stone_pillar: ["tiny-dungeon", "0018"],
    crate: ["tiny-dungeon", "0089"], earth_wall: ["tiny-dungeon", "0057", 0xc8a070], low_wall: ["tiny-dungeon", "0077"],
    fallen_log: ["tiny-town", "0106"], dead_tree: ["tiny-town", "0003"],
  };
  const KU = {
    hero_fighter: ["tiny-dungeon", "0096"], hero_mage: ["tiny-dungeon", "0084"], hero_archer: ["tiny-dungeon", "0099"],
    bandit: ["tiny-dungeon", "0085"], bandit_archer: ["tiny-dungeon", "0112"], bandit_shieldbearer: ["tiny-dungeon", "0097"],
    bandit_boss: ["tiny-dungeon", "0110"], summon_skeleton_warrior: ["tiny-dungeon", "0098"],
  };
  const images = new Map();
  function loadKenney() {
    const refs = [...Object.values(KT), ...Object.values(KO), ...Object.values(KU)];
    return Promise.all(
      refs.map(([pack, tile]) => {
        const key = `${pack}/${tile}`;
        if (images.has(key)) return null;
        const img = new Image();
        images.set(key, img);
        img.src = `kenney/${pack}/tile_${tile}.png`;
        return img.decode().catch(() => images.delete(key));
      }),
    );
  }
  // 與 PixiJS 的 tint 相同：圖的顏色乘上 tint
  function sprite(ctx, ref, x, y, size, tint = 0xffffff, alpha = 1) {
    const img = images.get(`${ref[0]}/${ref[1]}`);
    if (!img) return false;
    const off = document.createElement("canvas");
    off.width = img.width;
    off.height = img.height;
    const o = off.getContext("2d");
    o.drawImage(img, 0, 0);
    if (tint !== 0xffffff) {
      o.globalCompositeOperation = "multiply";
      o.fillStyle = css(tint);
      o.fillRect(0, 0, off.width, off.height);
      o.globalCompositeOperation = "destination-in";
      o.drawImage(img, 0, 0);
    }
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.globalAlpha = alpha;
    ctx.drawImage(off, x, y, size, size);
    ctx.restore();
    return true;
  }

  function drawTile(ctx, x, y, kenney) {
    const t = U.terrainAt(x, y);
    const h = U.heightAt(x, y);
    const s = U.surfaceAt(x, y);
    const blocked = U.BLOCKED.has(t);
    const ox = x * T;
    const oy = y * T;
    const ref = kenney ? KT[t] : null;
    if (ref) {
      const tint = ref[2] ?? 0xffffff;
      sprite(ctx, ref, ox, oy, T, blocked && t !== "wall" ? tint : shade(tint, h));
      if (s) {
        ctx.fillStyle = css(SURF[s][0], SURF[s][1]);
        ctx.fillRect(ox, oy, T, T);
      }
    } else {
      const base = s ? blend(TERRAIN[t], SURF[s][0], SURF[s][1]) : TERRAIN[t];
      ctx.fillStyle = css(shade(base, h));
      ctx.fillRect(ox, oy, T, T);
      if (t === "wall") {
        ctx.strokeStyle = "#2a2522";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(ox, oy + T / 2); ctx.lineTo(ox + T, oy + T / 2);
        ctx.moveTo(ox + T / 2, oy); ctx.lineTo(ox + T / 2, oy + T / 2);
        ctx.moveTo(ox + T / 4, oy + T / 2); ctx.lineTo(ox + T / 4, oy + T);
        ctx.moveTo(ox + (3 * T) / 4, oy + T / 2); ctx.lineTo(ox + (3 * T) / 4, oy + T);
        ctx.stroke();
      }
    }
    ctx.strokeStyle = "rgba(0,0,0,0.35)";
    ctx.lineWidth = 1;
    ctx.strokeRect(ox + 0.5, oy + 0.5, T - 1, T - 1);
    if (U.DEADLY.has(t)) {
      ctx.strokeStyle = css(DEADLY, 0.8);
      ctx.lineWidth = 2;
      ctx.strokeRect(ox + 3, oy + 3, T - 6, T - 6);
      ctx.strokeStyle = css(DEADLY, 0.6);
      ctx.beginPath();
      ctx.moveTo(ox + T * 0.3, oy + T * 0.3); ctx.lineTo(ox + T * 0.7, oy + T * 0.7);
      ctx.moveTo(ox + T * 0.7, oy + T * 0.3); ctx.lineTo(ox + T * 0.3, oy + T * 0.7);
      ctx.stroke();
    }
    if (!blocked || t === "wall") text(ctx, String(h), ox + 3, oy + 1, 11, "#000", { align: "left", base: "top", alpha: 0.55 });
  }

  function drawObject(ctx, o, kenney) {
    const [glyph, fill, floor] = OBJ[o.kind];
    const ox = o.x * T;
    const oy = o.y * T;
    const ref = kenney ? KO[o.kind] : null;
    let has = false;
    if (ref) {
      const size = floor ? T : T * 0.92;
      const off = (T - size) / 2;
      has = sprite(ctx, ref, ox + off, oy + off, size, ref[2] ?? 0xffffff, floor ? 0.9 : 1);
    }
    if (!has) {
      ctx.fillStyle = css(fill, floor ? 0.75 : 1);
      if (floor) ctx.fillRect(ox + 2, oy + 2, T - 4, T - 4);
      else {
        ctx.beginPath();
        ctx.roundRect(ox + T * 0.18, oy + T * 0.18, T * 0.64, T * 0.64, 6);
        ctx.fill();
      }
    }
    if (U.FLAMMABLE.has(o.kind)) {
      ctx.fillStyle = css(FLAM);
      ctx.beginPath();
      ctx.arc(ox + T - 8, oy + 8, 4, 0, Math.PI * 2);
      ctx.fill();
    }
    if (!has) text(ctx, glyph, ox + T / 2, oy + (floor ? T - 10 : T / 2), floor ? 12 : 16, "#fff");
  }

  function drawUnit(ctx, u, kenney) {
    const cx = u.x * T + T / 2;
    const cy = u.y * T + T / 2;
    const r = T * 0.32;
    const fill = u.summon ? 0x3a9a8a : TEAM[u.team];
    const ref = kenney ? KU[u.template] : null;
    const art = !!(ref && images.has(`${ref[0]}/${ref[1]}`));
    ctx.save();
    ctx.translate(cx, cy);
    const d = r * 1.25;
    if (u.summon) {
      poly(ctx, [0, -d, d, 0, 0, d, -d, 0]);
      ctx.fillStyle = css(fill, art ? 0.4 : 1);
      ctx.fill();
      ctx.lineWidth = 3;
      ctx.strokeStyle = css(SUMMON);
      ctx.stroke();
    } else {
      ctx.beginPath();
      ctx.arc(0, 0, art ? r + 1 : r, 0, Math.PI * 2);
      ctx.fillStyle = css(fill, art ? 0.55 : 1);
      ctx.fill();
      if (art) {
        ctx.lineWidth = 2;
        ctx.strokeStyle = css(fill);
        ctx.stroke();
      }
      if (u.hero) {
        ctx.beginPath();
        ctx.arc(0, 0, r + (art ? 4 : 2), 0, Math.PI * 2);
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#fff";
        ctx.stroke();
      }
      if (u.active) {
        ctx.beginPath();
        ctx.arc(0, 0, r + (art ? 7 : 5), 0, Math.PI * 2);
        ctx.lineWidth = 3;
        ctx.strokeStyle = css(ACTIVE);
        ctx.stroke();
      }
    }
    if (art) {
      const size = T * 0.86;
      sprite(ctx, ref, -size / 2, -size / 2 - 1, size);
    }
    poly(ctx, U.facingArrow(u.facing, u.summon ? d : r));
    ctx.fillStyle = "#fff";
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#000";
    ctx.stroke();
    if (art) text(ctx, u.marker, -T * 0.34, -T * 0.34, 13, "#fff", { stroke: 4 });
    else text(ctx, u.marker, 0, 0, 18, "#fff");
    const w = T * 0.8;
    ctx.fillStyle = "#000";
    ctx.fillRect(-w / 2, T * 0.36, w, 5);
    ctx.fillStyle = U.hpColor(u.hp);
    ctx.fillRect(-w / 2, T * 0.36, w * u.hp, 5);
    ctx.restore();
  }

  function render(canvas, kenney, scale = 2) {
    canvas.width = S.w * T * scale;
    canvas.height = S.h * T * scale;
    canvas.style.width = `${S.w * T}px`;
    canvas.style.height = `${S.h * T}px`;
    const ctx = canvas.getContext("2d");
    ctx.scale(scale, scale);
    for (let y = 0; y < S.h; y++) for (let x = 0; x < S.w; x++) drawTile(ctx, x, y, kenney);
    for (const o of S.objects) drawObject(ctx, o, kenney);
    for (const u of S.units) drawUnit(ctx, u, kenney);
  }

  return { render, loadKenney, T };
})();
