// 紙娃娃小人（美術樣張）：一個基本身體＋依裝備欄位疊上的圖層，裝備換了外觀就跟著換。
// 欄位對應 docs/design/08-裝備.md 8.10：主手、副手、頭、身、手、腳（項鍊、戒指太小，不畫）＋外觀用的頭髮、膚色、披風。
// 裝備外觀只看資料：種類（kind）＋材質（material）＋顏色（color，可省略）＋元素（element，可省略）＋稀有度。
// 新裝備不用新圖：例如 LLM 生成「霜紋鎖甲」= {slot: body, kind: mail, material: iron, element: ice}。
window.PaperDoll = (() => {
  const TAU = Math.PI * 2;

  // 材質 → 主色／暗色（布料可以自己指定顏色）
  const MATERIAL = {
    cloth: ["#8a8f99", "#5d6168"],
    leather: ["#8a5a32", "#5e3b1f"],
    iron: ["#8d969f", "#5a6169"],
    steel: ["#c3ccd6", "#7d8794"],
    gold: ["#e8bb48", "#9c7420"],
    wood: ["#a06a36", "#6a4420"],
    bone: ["#e9e3cf", "#a8a08a"],
  };
  // 元素詞條會讓裝備帶一點元素色（與技能特效、技能圖示同一份色票）
  const ELEMENT_TINT = {
    fire: "#ff6a1a", ice: "#8fe3ff", lightning: "#fff36b", poison: "#7ddc3a", wind: "#7fe0c0",
    earth: "#b0814a", holy: "#ffd75e", shadow: "#9a6ad8",
  };
  const RARITY_GLOW = { epic: "#b06cff", legendary: "#ffbf3a" };

  function mix(a, b, t) {
    const pa = parseInt(a.slice(1), 16);
    const pb = parseInt(b.slice(1), 16);
    const ch = (p, s) => (p >> s) & 255;
    const m = (s) => Math.round(ch(pa, s) * (1 - t) + ch(pb, s) * t);
    return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
  }
  function darker(c, f = 0.68) {
    return mix(c, "#000000", 1 - f);
  }
  /** 一件裝備的 [主色, 暗色]。 */
  function itemColors(item) {
    let [main, dark] = item.color ? [item.color, darker(item.color)] : MATERIAL[item.material] ?? MATERIAL.cloth;
    if (item.element && ELEMENT_TINT[item.element]) {
      main = mix(main, ELEMENT_TINT[item.element], 0.45);
      dark = mix(dark, ELEMENT_TINT[item.element], 0.3);
    }
    return [main, dark];
  }

  function rr(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
  }
  function fill(ctx, color, path) {
    ctx.fillStyle = color;
    ctx.beginPath();
    path();
    ctx.fill();
  }

  // ===== 各部位（座標：腳底中心為原點，往上是負；身高約 46）=====
  function drawCloak(ctx, it, view) {
    const [c, d] = itemColors(it);
    ctx.fillStyle = view === "back" ? c : d;
    ctx.beginPath();
    ctx.moveTo(-8, -21);
    ctx.lineTo(8, -21);
    ctx.lineTo(12, -2);
    ctx.quadraticCurveTo(0, 1, -12, -2);
    ctx.closePath();
    ctx.fill();
    if (view === "back") {
      ctx.strokeStyle = d;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(-3, -18); ctx.lineTo(-5, -3);
      ctx.moveTo(3, -18); ctx.lineTo(5, -3);
      ctx.stroke();
    }
  }
  function drawLegs(ctx, look, feet) {
    const pants = look.pants ?? "#4a4038";
    fill(ctx, pants, () => rr(ctx, -5, -9, 4, 8, 1));
    fill(ctx, pants, () => rr(ctx, 1, -9, 4, 8, 1));
    const [b, bd] = feet ? itemColors(feet) : ["#5a4030", "#3a281c"];
    const tall = feet?.kind === "greaves" ? 4 : feet?.kind === "boots" ? 2.5 : 0;
    for (const sx of [-1, 1]) {
      if (tall) fill(ctx, b, () => rr(ctx, sx * 3 - 2.2, -2 - tall, 4.4, tall + 1, 1));
      fill(ctx, bd, () => {
        ctx.beginPath();
        ctx.ellipse(sx * 3.2, -1.2, 3.2, 2, 0, 0, TAU);
      });
    }
  }
  function drawBody(ctx, it, look) {
    const kind = it?.kind ?? "shirt";
    const [c, d] = it ? itemColors(it) : ["#d8cdb4", "#a89c80"];
    if (kind === "ribs") {
      // 骷髏：肋骨
      fill(ctx, "#d9d2bd", () => rr(ctx, -1.5, -21, 3, 13, 1));
      ctx.strokeStyle = "#d9d2bd";
      ctx.lineWidth = 2;
      for (let i = 0; i < 4; i++) {
        ctx.beginPath();
        ctx.moveTo(-6, -19 + i * 3);
        ctx.quadraticCurveTo(0, -17 + i * 3, 6, -19 + i * 3);
        ctx.stroke();
      }
      fill(ctx, "#d9d2bd", () => rr(ctx, -5, -9, 10, 2.5, 1));
      return;
    }
    if (kind === "robe") {
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.moveTo(-7, -21);
        ctx.lineTo(7, -21);
        ctx.lineTo(10, -1.5);
        ctx.lineTo(-10, -1.5);
        ctx.closePath();
      });
      fill(ctx, look.trim ?? d, () => ctx.rect(-1.2, -20, 2.4, 18.5));
      fill(ctx, look.trim ?? d, () => ctx.rect(-10, -3, 20, 1.6));
    } else {
      fill(ctx, c, () => rr(ctx, -7.5, -21, 15, 13.5, 3));
      if (kind === "plate") {
        fill(ctx, mix(c, "#ffffff", 0.35), () => rr(ctx, -5, -19.5, 4, 6, 1.5));
        fill(ctx, d, () => ctx.rect(-7.5, -14, 15, 1.2));
      } else if (kind === "mail") {
        ctx.fillStyle = d;
        for (let y = -19; y < -9; y += 2.4) for (let x = -6 + ((y | 0) % 2); x < 6.5; x += 2.4) ctx.fillRect(x, y, 1, 1);
      } else if (kind === "leather") {
        ctx.strokeStyle = d;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(-5, -20); ctx.lineTo(5, -11);
        ctx.stroke();
      }
      // 腰帶
      fill(ctx, look.belt ?? "#3a2a1c", () => ctx.rect(-7.5, -9.5, 15, 2));
      fill(ctx, "#d8b04a", () => ctx.rect(-1, -9.5, 2, 2));
    }
    // 手臂
    const sleeve = kind === "ribs" ? "#d9d2bd" : c;
    fill(ctx, sleeve, () => rr(ctx, -10.5, -20, 4, 10, 2));
    fill(ctx, sleeve, () => rr(ctx, 6.5, -20, 4, 10, 2));
    if (kind === "plate") {
      fill(ctx, mix(c, "#ffffff", 0.25), () => { ctx.beginPath(); ctx.ellipse(-8.5, -19.5, 3.5, 2.5, 0, 0, TAU); });
      fill(ctx, mix(c, "#ffffff", 0.25), () => { ctx.beginPath(); ctx.ellipse(8.5, -19.5, 3.5, 2.5, 0, 0, TAU); });
    }
  }
  function drawHands(ctx, look, hands) {
    const c = hands ? itemColors(hands)[0] : look.skin;
    for (const x of [-8.5, 8.5]) fill(ctx, c, () => { ctx.beginPath(); ctx.arc(x, -9.5, 2.4, 0, TAU); });
  }
  function drawHead(ctx, look, view, side) {
    const skin = look.skin;
    fill(ctx, skin, () => { ctx.beginPath(); ctx.arc(0, -29, 8.5, 0, TAU); });
    if (view === "back") return;
    // 臉：側面時眼睛往朝向那邊偏
    const ex = side * 2.6;
    ctx.fillStyle = look.eyes ?? "#1d1a22";
    if (look.skull) {
      ctx.beginPath();
      ctx.arc(ex - 3, -29, 2.2, 0, TAU);
      ctx.arc(ex + 3, -29, 2.2, 0, TAU);
      ctx.fill();
      ctx.fillRect(ex - 2.5, -24.5, 5, 1.2);
      return;
    }
    if (side === 0 || side === 1) ctx.fillRect(ex + 2, -30, 1.8, 3);
    if (side === 0 || side === -1) ctx.fillRect(ex - 3.8, -30, 1.8, 3);
    ctx.fillStyle = "rgba(220,90,90,0.35)";
    ctx.fillRect(ex - 5, -26.5, 2, 1.2);
    ctx.fillRect(ex + 3, -26.5, 2, 1.2);
  }
  function drawHair(ctx, look, view, head) {
    if (!look.hair || look.skull) return;
    const c = look.hairColor ?? "#5a3a22";
    // 戴著蓋住頭的帽子就不畫頭髮頂
    const covered = head && ["helmet", "hood", "wizard_hat", "horned_helm"].includes(head.kind);
    if (view === "back") {
      fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -29, 8.8, 0, TAU); });
      if (look.hair === "long") fill(ctx, c, () => rr(ctx, -7, -29, 14, 10, 3));
      return;
    }
    if (!covered) {
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.arc(0, -29.5, 8.8, Math.PI * 1.02, Math.PI * 1.98);
        ctx.quadraticCurveTo(4, -33, 0, -32.5);
        ctx.quadraticCurveTo(-5, -32, -8.8, -29);
        ctx.closePath();
      });
    }
    if (look.hair === "long") {
      fill(ctx, c, () => rr(ctx, -9.5, -31, 3, 11, 1.5));
      fill(ctx, c, () => rr(ctx, 6.5, -31, 3, 11, 1.5));
    }
  }
  function drawHeadgear(ctx, it, view) {
    if (!it) return;
    const [c, d] = itemColors(it);
    switch (it.kind) {
      case "hood":
        // 兜帽：正面挖出臉的洞（evenodd）
        ctx.fillStyle = c;
        ctx.beginPath();
        ctx.arc(0, -29.5, 10, Math.PI * 0.85, Math.PI * 2.15);
        ctx.lineTo(9, -22);
        ctx.lineTo(-9, -22);
        ctx.closePath();
        if (view !== "back") ctx.ellipse(0, -28, 6.5, 6, 0, 0, TAU);
        ctx.fill("evenodd");
        fill(ctx, d, () => ctx.rect(-9, -23, 18, 1.5));
        break;
      case "helmet":
      case "horned_helm":
        fill(ctx, c, () => {
          ctx.beginPath();
          ctx.arc(0, -30, 9.4, Math.PI, 0);
          ctx.lineTo(9.4, -27);
          ctx.lineTo(-9.4, -27);
          ctx.closePath();
        });
        fill(ctx, d, () => ctx.rect(-9.4, -28, 18.8, 1.6));
        if (view !== "back") fill(ctx, d, () => ctx.rect(-1, -28, 2, 5));
        fill(ctx, mix(c, "#ffffff", 0.4), () => rr(ctx, -5, -37, 4, 3, 1.5));
        if (it.kind === "horned_helm") {
          for (const s of [-1, 1]) {
            fill(ctx, "#efe6cc", () => {
              ctx.beginPath();
              ctx.moveTo(s * 8, -33);
              ctx.quadraticCurveTo(s * 15, -35, s * 14, -42);
              ctx.quadraticCurveTo(s * 11, -37, s * 6, -36);
              ctx.closePath();
            });
          }
        }
        break;
      case "wizard_hat":
        fill(ctx, c, () => {
          ctx.beginPath();
          ctx.moveTo(-8, -34);
          ctx.lineTo(3, -50);
          ctx.lineTo(8, -34);
          ctx.closePath();
        });
        fill(ctx, d, () => { ctx.beginPath(); ctx.ellipse(0, -34, 12, 3, 0, 0, TAU); });
        fill(ctx, it.trim ?? "#e8bb48", () => ctx.rect(-7, -36.5, 14, 1.8));
        break;
      case "bandana":
        fill(ctx, c, () => {
          ctx.beginPath();
          ctx.arc(0, -30, 9, Math.PI * 1.05, Math.PI * 1.95);
          ctx.closePath();
        });
        fill(ctx, c, () => ctx.rect(-9, -31.5, 18, 3));
        fill(ctx, d, () => {
          ctx.beginPath();
          ctx.moveTo(view === "back" ? 0 : 8, -30);
          ctx.lineTo((view === "back" ? 0 : 8) + 5, -27);
          ctx.lineTo((view === "back" ? 0 : 8) + 2, -25);
          ctx.closePath();
        });
        break;
      case "crown":
        fill(ctx, c, () => {
          ctx.beginPath();
          ctx.moveTo(-6, -35); ctx.lineTo(-6, -41); ctx.lineTo(-3, -38); ctx.lineTo(0, -42); ctx.lineTo(3, -38); ctx.lineTo(6, -41); ctx.lineTo(6, -35);
          ctx.closePath();
        });
        fill(ctx, "#d23c3c", () => { ctx.beginPath(); ctx.arc(0, -37, 1.3, 0, TAU); });
        break;
      default:
        break;
    }
  }
  function drawWeapon(ctx, it, x, front) {
    if (!it) return;
    const [c, d] = itemColors(it);
    const hy = -9.5;
    ctx.save();
    ctx.translate(x, hy);
    switch (it.kind) {
      case "sword":
      case "greatsword": {
        const L = it.kind === "greatsword" ? 24 : 16;
        const W = it.kind === "greatsword" ? 4 : 2.6;
        ctx.rotate(front ? -0.25 : 0.25);
        fill(ctx, c, () => {
          ctx.beginPath();
          ctx.moveTo(-W / 2, -3); ctx.lineTo(-W / 2, -L); ctx.lineTo(0, -L - 3); ctx.lineTo(W / 2, -L); ctx.lineTo(W / 2, -3);
          ctx.closePath();
        });
        fill(ctx, "rgba(255,255,255,0.45)", () => ctx.rect(-W / 2 + 0.6, -L, 0.9, L - 4));
        fill(ctx, it.hilt ?? "#8a6a2a", () => rr(ctx, -4.5, -4, 9, 2, 1));
        fill(ctx, "#4a3020", () => ctx.rect(-1, -2, 2, 4));
        break;
      }
      case "dagger":
        ctx.rotate(front ? -0.6 : 0.6);
        fill(ctx, c, () => {
          ctx.beginPath();
          ctx.moveTo(-1.3, -2); ctx.lineTo(0, -10); ctx.lineTo(1.3, -2);
          ctx.closePath();
        });
        fill(ctx, "#4a3020", () => ctx.rect(-2.5, -2.5, 5, 1.5));
        break;
      case "axe":
        ctx.rotate(front ? -0.3 : 0.3);
        fill(ctx, "#6a4420", () => ctx.rect(-1, -18, 2, 20));
        fill(ctx, c, () => {
          ctx.beginPath();
          ctx.moveTo(1, -17); ctx.quadraticCurveTo(9, -18, 8, -10); ctx.lineTo(1, -12);
          ctx.closePath();
        });
        break;
      case "staff": {
        fill(ctx, "#6a4420", () => ctx.rect(-1.1, -30, 2.2, 34));
        const orb = it.element ? ELEMENT_TINT[it.element] : c;
        ctx.fillStyle = orb;
        ctx.globalAlpha = 0.35;
        ctx.beginPath();
        ctx.arc(0, -32, 6.5, 0, TAU);
        ctx.fill();
        ctx.globalAlpha = 1;
        fill(ctx, orb, () => { ctx.beginPath(); ctx.arc(0, -32, 3.6, 0, TAU); });
        fill(ctx, "rgba(255,255,255,0.8)", () => { ctx.beginPath(); ctx.arc(-1.2, -33.2, 1.1, 0, TAU); });
        break;
      }
      case "gun": {
        // 槍（樣張）：槍口朝前下方；形制決定長度與外型
        const L = { pistol: 7, rifle: 17, shotgun: 15, energy: 12 }[it.form] ?? 7;
        ctx.rotate(front ? 0.35 : -0.35);
        const s = front ? -1 : 1;
        fill(ctx, "#3a2a1c", () => rr(ctx, -1.2, -1, 2.4, 5, 0.8)); // 握把
        if (it.form === "rifle" || it.form === "shotgun") fill(ctx, it.form === "shotgun" ? "#7a5232" : d, () => rr(ctx, s > 0 ? -6 : 1, -3, 5, 3, 1)); // 槍托
        fill(ctx, it.form === "energy" ? "#e8edf2" : c, () => rr(ctx, s > 0 ? -1 : -L, -3.2, L + 1, it.form === "shotgun" ? 3.2 : 2.6, 1));
        if (it.form === "energy") fill(ctx, it.element ? ELEMENT_TINT[it.element] : "#5ad8ff", () => rr(ctx, s > 0 ? 1 : -L + 1, -2.6, L - 3, 1.2, 0.6));
        else if (it.element) fill(ctx, ELEMENT_TINT[it.element], () => { ctx.beginPath(); ctx.arc(s * (L - 0.5), -2, 1.3, 0, TAU); });
        break;
      }
      case "bow":
        ctx.strokeStyle = c;
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.arc(front ? -4 : 4, -8, 13, front ? -1.2 : Math.PI - 1.2, front ? 1.2 : Math.PI + 1.2);
        ctx.stroke();
        ctx.strokeStyle = "rgba(240,240,240,0.8)";
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        const sx = (front ? -4 : 4) + (front ? 1 : -1) * Math.cos(1.2) * 13;
        ctx.moveTo(sx, -8 - Math.sin(1.2) * 13);
        ctx.lineTo(sx, -8 + Math.sin(1.2) * 13);
        ctx.stroke();
        break;
      case "shield_round":
        fill(ctx, d, () => { ctx.beginPath(); ctx.arc(0, -4, 7.5, 0, TAU); });
        fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -4, 6, 0, TAU); });
        fill(ctx, it.trim ?? "#e8bb48", () => { ctx.beginPath(); ctx.arc(0, -4, 2, 0, TAU); });
        break;
      case "shield_kite":
        fill(ctx, d, () => {
          ctx.beginPath();
          ctx.moveTo(-7, -13); ctx.lineTo(7, -13); ctx.lineTo(6.5, -2); ctx.lineTo(0, 6); ctx.lineTo(-6.5, -2);
          ctx.closePath();
        });
        fill(ctx, c, () => {
          ctx.beginPath();
          ctx.moveTo(-5.5, -11.5); ctx.lineTo(5.5, -11.5); ctx.lineTo(5, -2.5); ctx.lineTo(0, 3.8); ctx.lineTo(-5, -2.5);
          ctx.closePath();
        });
        fill(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(-0.9, -11, 1.8, 13));
        fill(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(-5, -7, 10, 1.8));
        break;
      case "tome":
        fill(ctx, c, () => rr(ctx, -4.5, -6, 9, 8, 1));
        fill(ctx, "#f2ead6", () => ctx.rect(-3.5, -5.5, 7, 1.2));
        fill(ctx, it.trim ?? "#e8bb48", () => { ctx.beginPath(); ctx.arc(0, -2, 1.6, 0, TAU); });
        break;
      default:
        break;
    }
    ctx.restore();
  }

  /**
   * 畫一個小人。`unit = { look, gear }`：look 是外觀（膚色、髮型、髮色、褲子），gear 是各欄位的裝備。
   * facing：south＝正面、north＝背面、east／west＝側面（左右鏡射）。腳底中心在 (0, 0)。
   */
  function drawFigure(ctx, unit, facing) {
    const { look, gear } = unit;
    const view = facing === "north" ? "back" : "front";
    const side = facing === "east" ? 1 : facing === "west" ? -1 : 0;
    // 慣用手：正面時角色右手在畫面左邊；背面相反；側面時武器在前方
    let mainX = -8.5;
    let offX = 8.5;
    if (view === "back") [mainX, offX] = [8.5, -8.5];
    if (side !== 0) [mainX, offX] = [side * 8.5, -side * 8.5];
    const offInFront = gear.off_hand && gear.off_hand.kind?.startsWith("shield");
    ctx.save();
    if (side !== 0) ctx.scale(0.9, 1);
    if (gear.cloak && view !== "back") drawCloak(ctx, gear.cloak, view);
    if (view === "back") {
      drawWeapon(ctx, gear.main_hand, mainX, false);
      if (gear.off_hand) drawWeapon(ctx, gear.off_hand, offX, false);
    } else if (gear.main_hand?.kind === "bow" || gear.main_hand?.kind === "staff") {
      // 長武器畫在身體後面一點
    }
    drawLegs(ctx, look, gear.feet);
    drawBody(ctx, gear.body, look);
    drawHands(ctx, look, gear.hands);
    if (gear.cloak && view === "back") drawCloak(ctx, gear.cloak, view);
    drawHead(ctx, look, view, side);
    drawHair(ctx, look, view, gear.head);
    drawHeadgear(ctx, gear.head, view);
    if (view !== "back") {
      drawWeapon(ctx, gear.main_hand, mainX, true);
      if (gear.off_hand) drawWeapon(ctx, gear.off_hand, offX + (offInFront ? side * 2 : 0), true);
    }
    ctx.restore();
  }

  /**
   * 畫到格子上：先在離屏 canvas 畫好，再描一圈深色外框（像像素小人那樣清楚），最後貼上。
   * (cx, cy) 是腳底位置，size 是縮放（1 ＝ 身高約 46 px）。
   */
  function stamp(ctx, unit, facing, cx, cy, size = 1, opts = {}) {
    const dpr = opts.dpr ?? 2;
    const W = 64;
    const H = 64;
    const off = document.createElement("canvas");
    off.width = W * size * dpr;
    off.height = H * size * dpr;
    const o = off.getContext("2d");
    o.scale(size * dpr, size * dpr);
    o.translate(W / 2, H - 6);
    drawFigure(o, unit, facing);
    // 外框：把剪影往 8 個方向各偏一點塗深色
    const sil = document.createElement("canvas");
    sil.width = off.width;
    sil.height = off.height;
    const s = sil.getContext("2d");
    s.drawImage(off, 0, 0);
    s.globalCompositeOperation = "source-in";
    s.fillStyle = opts.outline ?? "#16121a";
    s.fillRect(0, 0, sil.width, sil.height);
    const glow = RARITY_GLOW[unit.rarity];
    const k = 1.3 * size * dpr;
    const dx0 = cx - (W / 2) * size;
    const dy0 = cy - (H - 6) * size;
    if (glow) {
      // 史詩、傳說裝備：外圍淡淡的光
      const g = document.createElement("canvas");
      g.width = off.width;
      g.height = off.height;
      const gc = g.getContext("2d");
      gc.drawImage(off, 0, 0);
      gc.globalCompositeOperation = "source-in";
      gc.fillStyle = glow;
      gc.fillRect(0, 0, g.width, g.height);
      ctx.save();
      ctx.globalAlpha = 0.5;
      for (let a = 0; a < 12; a++) {
        const ang = (a / 12) * TAU;
        ctx.drawImage(g, dx0 + Math.cos(ang) * 2.6 * size, dy0 + Math.sin(ang) * 2.6 * size, W * size, H * size);
      }
      ctx.restore();
    }
    for (const [ox, oy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]) {
      ctx.drawImage(sil, dx0 + (ox * k) / dpr, dy0 + (oy * k) / dpr, W * size, H * size);
    }
    ctx.drawImage(off, dx0, dy0, W * size, H * size);
  }

  // ===== 裝備資料（樣張用；正式版由裝備的 kind／material／element／rarity 欄位決定）=====
  const I = (slot, kind, material, extra = {}) => ({ slot, kind, material, ...extra });
  const ITEMS = {
    tunic: I("body", "shirt", "cloth", { color: "#4f7fbf" }),
    leather_vest: I("body", "leather", "leather"),
    green_leather: I("body", "leather", "leather", { color: "#4f7a3a" }),
    chain_mail: I("body", "mail", "iron"),
    plate_armor: I("body", "plate", "steel"),
    mage_robe: I("body", "robe", "cloth", { color: "#5a3fa0" }),
    frost_mail: I("body", "mail", "iron", { element: "ice" }),
    boots: I("feet", "boots", "leather"),
    greaves: I("feet", "greaves", "steel"),
    gloves: I("hands", "gloves", "leather"),
    gauntlets: I("hands", "gauntlets", "steel"),
    hood_green: I("head", "hood", "cloth", { color: "#3f6a32" }),
    hood_brown: I("head", "hood", "cloth", { color: "#6a4a2e" }),
    helmet: I("head", "helmet", "steel"),
    iron_helmet: I("head", "helmet", "iron"),
    horned_helm: I("head", "horned_helm", "iron"),
    wizard_hat: I("head", "wizard_hat", "cloth", { color: "#5a3fa0" }),
    bandana_red: I("head", "bandana", "cloth", { color: "#b33a3a" }),
    crown: I("head", "crown", "gold"),
    sword: I("main_hand", "sword", "steel"),
    rusty_sword: I("main_hand", "sword", "iron", { color: "#9a8a76" }),
    greatsword: I("main_hand", "greatsword", "steel"),
    flame_greatsword: I("main_hand", "greatsword", "steel", { element: "fire" }),
    dagger: I("main_hand", "dagger", "iron"),
    axe: I("main_hand", "axe", "iron"),
    bow: I("main_hand", "bow", "wood"),
    fire_staff: I("main_hand", "staff", "wood", { element: "fire" }),
    lightning_staff: I("main_hand", "staff", "wood", { element: "lightning" }),
    round_shield: I("off_hand", "shield_round", "wood", { color: "#2f5fae" }),
    kite_shield: I("off_hand", "shield_kite", "wood", { color: "#8a5a32" }),
    holy_shield: I("off_hand", "shield_kite", "steel", { element: "holy" }),
    tome: I("off_hand", "tome", "leather", { color: "#7a2a3a" }),
    red_cape: I("cloak", "cape", "cloth", { color: "#a32a2a" }),
    blue_cape: I("cloak", "cape", "cloth", { color: "#2c4f8a" }),
  };
  function build(look, ids, rarity) {
    const gear = {};
    for (const id of ids) gear[ITEMS[id].slot] = ITEMS[id];
    return { look, gear, rarity };
  }
  const SKIN = ["#f1c9a5", "#d9a47a", "#a8724c", "#7a4e32"];
  // 單位範本 → 預設外觀與裝備（正式版：英雄讀身上的裝備；敵人讀範本的 weapon 與標籤）
  const TEMPLATES = {
    hero_fighter: build({ skin: SKIN[0], hair: "short", hairColor: "#6a3d1e" }, ["plate_armor", "greaves", "gauntlets", "sword", "round_shield", "blue_cape"]),
    hero_mage: build({ skin: SKIN[1], hair: "long", hairColor: "#c8c0b0", trim: "#e8bb48" }, ["mage_robe", "boots", "wizard_hat", "fire_staff", "tome"]),
    hero_archer: build({ skin: SKIN[0], hair: "long", hairColor: "#c27a2c", pants: "#3a3a2a" }, ["green_leather", "boots", "gloves", "hood_green", "bow"]),
    bandit: build({ skin: SKIN[2], hair: "short", hairColor: "#2a1c14" }, ["leather_vest", "boots", "bandana_red", "dagger"]),
    bandit_archer: build({ skin: SKIN[1], hair: "short", hairColor: "#3a2a1c" }, ["leather_vest", "boots", "hood_brown", "bow"]),
    bandit_shieldbearer: build({ skin: SKIN[3], hair: "short", hairColor: "#1c1410" }, ["chain_mail", "boots", "iron_helmet", "rusty_sword", "kite_shield"]),
    bandit_boss: build({ skin: SKIN[2], hair: "short", hairColor: "#1c1410" }, ["chain_mail", "greaves", "gauntlets", "horned_helm", "greatsword", "red_cape"], "epic"),
    summon_skeleton_warrior: build({ skin: "#e9e3cf", skull: true, pants: "#d9d2bd", eyes: "#2a1030" }, ["rusty_sword"]),
  };
  TEMPLATES.summon_skeleton_warrior.gear.body = { kind: "ribs" };

  return { drawFigure, stamp, ITEMS, TEMPLATES, build, SKIN, itemColors };
})();
