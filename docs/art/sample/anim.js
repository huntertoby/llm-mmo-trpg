// 動畫樣張（美術 PM，2026-11-04，第二版）：用遊戲裡實際的 C 手繪墨線紙娃娃（storyDoll.js）做程式骨架動畫。
// 做法：現有部件不改畫法，只在關節（髖、膝、肩、腕）外面包一層旋轉（storyDoll.setPose）；每個動作是一個「片段」：t（0→1）→ 姿勢。
// 技能動畫＝依引擎事件順序把片段串起來播；LLM 不參與。武器一律「握把在手、作用端（刃尖、槍口、杖頭、箭）朝攻擊方向」，頁首有自測。
// 使用者原話（專案 PM 轉達）：「人不是我們 原本紙娃娃樣子阿 還是這只是掩飾 2. 為啥拿劍柄去揮人 3. 槍也反了」
window.Anim = (() => {
  const SD = StoryDoll, { ink, stroke, ellPts, INK } = SD.H;
  const TAU = Math.PI * 2;
  const OUT = "#1c1712";
  const ELEM = { fire: ["#ff7a2a", "#ffd23a"], ice: ["#7ad8ff", "#e8f8ff"], lightning: ["#c8a0ff", "#fff4a0"], physical: ["#e8eef4", "#ffffff"], holy: ["#ffe080", "#fffbe0"], arcane: ["#5ae0f0", "#e0ffff"], crit: ["#ffb020", "#fff6c0"] };
  const ease = { in: (t) => t * t, out: (t) => 1 - (1 - t) * (1 - t), inOut: (t) => (t < 0.5 ? 2 * t * t : 1 - 2 * (1 - t) * (1 - t)) };
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const mix = (a, b, t) => a + (b - a) * t;
  const STEEL = "#c3ccd6", IRON = "#8d969f", WOOD = "#a06a36", GOLD = "#e8bb48", LEATHER = "#8a5a32";

  // ---------------- 武器（握把在原點，作用端朝 -y；len＝原點到作用端）----------------
  const WEAPONS = {
    sword: { len: 21, hold: { side: 0.75, front: 0 }, draw: (c, k) => { ink(c, `${k}-grip`, [[-0.8, 0], [0.8, 0], [0.8, 4], [-0.8, 4]], LEATHER, { shade: false, w: 0.5 }); ink(c, `${k}-blade`, [[-1.1, -2], [-1, -19.4], [0, -21], [1, -19.4], [1.1, -2]], STEEL, { shade: false, w: 0.7 }); ink(c, `${k}-guard`, [[-3.4, -3.2], [3.4, -3.2], [3.4, -1.6], [-3.4, -1.6]], GOLD, { shade: false, w: 0.6 }); } },
    saber: { len: 21, hold: { side: 0.75, front: 0 }, draw: (c, k) => { ink(c, `${k}-grip`, [[-0.8, 0], [0.8, 0], [0.8, 4], [-0.8, 4]], "#3a2a1a", { shade: false, w: 0.5 }); ink(c, `${k}-blade`, [[-1, -2], [-1.6, -11], [-0.4, -19], [1.6, -21.2], [1.4, -11], [1, -2]], STEEL, { shade: false, w: 0.7 }); ink(c, `${k}-guard`, ellPts(0, -2.4, 2.6, 1.2, 10), GOLD, { shade: false, w: 0.5 }); } },
    arcane_blade: { len: 21, hold: { side: 0.75, front: 0 }, draw: (c, k) => { WEAPONS.sword.draw(c, k); c.save(); c.shadowColor = "#5ae0f0"; c.shadowBlur = 6; stroke(c, `${k}-rune`, [[0, -4], [0.4, -9], [-0.4, -13], [0.3, -18]], 0.9, "#5ae0f0"); c.restore(); } },
    paired: { len: 10, hold: { side: 0.75, front: 0 }, draw: (c, k) => { for (const [dx, r] of [[-1.6, -0.35], [1.6, 0.35]]) { c.save(); c.translate(dx, 0); c.rotate(r); ink(c, `${k}-d${dx}`, [[-0.9, -1], [-0.8, -8.6], [0, -10], [0.8, -8.6], [0.9, -1]], STEEL, { shade: false, w: 0.6 }); ink(c, `${k}-g${dx}`, [[-2.2, -1.6], [2.2, -1.6], [2.2, -0.4], [-2.2, -0.4]], GOLD, { shade: false, w: 0.5 }); c.restore(); } } },
    spear: { len: 34, hold: { side: 0.15, front: 0 }, draw: (c, k) => { ink(c, `${k}-shaft`, [[-0.8, 12], [0.8, 12], [0.8, -28], [-0.8, -28]], WOOD, { shade: false, w: 0.6 }); ink(c, `${k}-tip`, [[-1.8, -27.6], [0, -34], [1.8, -27.6]], STEEL, { shade: false, w: 0.6, sharp: true }); } },
    scythe: { len: 26, hold: { side: 0.6, front: 0 }, draw: (c, k) => { ink(c, `${k}-pole`, [[-0.8, 10], [0.8, 10], [0.8, -26], [-0.8, -26]], "#5a4030", { shade: false, w: 0.6 }); ink(c, `${k}-blade`, [[0.6, -26], [8, -27], [14, -22], [7, -24.2], [0.6, -23]], STEEL, { shade: false, w: 0.6 }); } },
    whip: { len: 7, hold: { side: 0.75, front: 0 }, draw: (c, k) => { ink(c, `${k}-handle`, [[-0.9, 1], [0.9, 1], [0.9, -7], [-0.9, -7]], LEATHER, { shade: false, w: 0.5 }); stroke(c, `${k}-lash`, [[0, -7], [3, -14], [1, -21], [-4, -24], [-6, -20]], 1.4, "#3a2414"); } },
    gauntlet: { len: 4, hold: { side: 1.0, front: 0 }, draw: (c, k) => { ink(c, `${k}-fist`, ellPts(0, -1.6, 3, 3.4, 12), IRON, { w: 0.7 }); stroke(c, `${k}-knuckle`, [[-2, -4], [2, -4]], 0.8, INK); } },
    staff: { len: 30, hold: { side: 0, front: 0 }, draw: (c, k) => { ink(c, `${k}-pole`, [[-0.8, 22], [0.8, 22], [0.9, -27], [-0.9, -27]], WOOD, { shade: false, w: 0.6 }); ink(c, `${k}-claw`, [[-3, -27], [-2.6, -33.4], [0, -29], [2.6, -33.4], [3, -27]], WOOD, { shade: false, w: 0.6 }); ink(c, `${k}-orb`, ellPts(0, -30.4, 2.4, 2.4, 10), "#c8bcff", { shade: false, w: 0.6 }); } },
    orb: { len: 7, hold: { side: 0.6, front: 0 }, draw: (c, k) => { c.save(); c.shadowColor = "#a898ff"; c.shadowBlur = 8; ink(c, `${k}-orb`, ellPts(0, -6, 3.6, 3.6, 12), "#c8bcff", { shade: false, w: 0.6 }); c.restore(); } },
    bow: { len: 6, hold: { side: Math.PI / 2, front: Math.PI / 2 }, draw: (c, k) => {
      const pull = typeof c.__pull === "number" ? c.__pull : 0;
      stroke(c, `${k}-string`, [[-14.6, 1.6], [0, 1.6 + pull], [14.6, 1.6]], 0.35, "#e8e0d0");
      ink(c, `${k}-limb`, [[-15, 1.6], [-9, -2.4], [0, -3.6], [9, -2.4], [15, 1.6], [15.4, 0.4], [9, -4.4], [0, -5.8], [-9, -4.4], [-15.4, 0.4]], WOOD, { shade: false, w: 0.6 });
      if (pull > 0.5) { stroke(c, `${k}-arrow`, [[0, 1.6 + pull], [0, -9]], 0.9, "#c8a070"); ink(c, `${k}-head`, [[-1.2, -8.6], [0, -11], [1.2, -8.6]], STEEL, { shade: false, w: 0.4, sharp: true }); }
    } },
    crossbow: { len: 15, hold: { side: 2.2, front: Math.PI }, draw: (c, k) => { ink(c, `${k}-stock`, [[-1.4, 5], [1.4, 5], [1.2, -14], [-1.2, -14]], WOOD, { shade: false, w: 0.6 }); stroke(c, `${k}-prod`, [[-9, -9.6], [0, -13], [9, -9.6]], 1.6, IRON); stroke(c, `${k}-string`, [[-9, -9.6], [0, -6], [9, -9.6]], 0.35, "#e8e0d0"); stroke(c, `${k}-bolt`, [[0, -6], [0, -15]], 0.8, "#c8a070"); } },
    gun: { len: 26, hold: { side: 2.3, front: Math.PI }, draw: (c, k) => { ink(c, `${k}-stock`, [[-2, 7], [2.2, 5], [1.4, -2], [-1.4, -2]], WOOD, { shade: false, w: 0.6 }); ink(c, `${k}-barrel`, [[-1, -2], [1, -2], [0.9, -26], [-0.9, -26]], IRON, { shade: false, w: 0.6 }); ink(c, `${k}-band`, [[-1.4, -12], [1.4, -12], [1.4, -10.6], [-1.4, -10.6]], GOLD, { shade: false, w: 0.4 }); } },
  };
  for (const [kind, w] of Object.entries(WEAPONS)) SD.registerWeapon(kind, w);
  const WEAPON_ZH = { sword: "劍", saber: "刀", spear: "槍（長兵）", bow: "弓", crossbow: "弩", gun: "火槍", staff: "法杖", orb: "法球", gauntlet: "拳套", whip: "鞭", scythe: "鐮", paired: "成對武器", arcane_blade: "魔導劍" };

  // ---------------- 角色（照遊戲紙娃娃的 look／gear 欄位）----------------
  const unit = (kind, extra = {}) => ({ look: { skin: "#f1c9a5", hair: "short", hairColor: "#3a2414", ...extra.look }, gear: { body: { kind: "shirt", color: "#2f5a5a" }, feet: { kind: "boots", material: "leather" }, main_hand: { kind }, ...extra.gear } });
  const HERO = unit("sword");
  const MAGE = unit("staff", { look: { hair: "long", hairColor: "#1a1a1a" }, gear: { body: { kind: "robe", color: "#5a3a9a" } } });
  const FOE = { look: { skin: "#a8724c", hair: "short", hairColor: "#1a1a1a" }, gear: { body: { kind: "shirt", color: "#7a6a4a" }, feet: { kind: "boots", material: "leather" }, main_hand: { kind: "axe", material: "iron" }, head: { kind: "hood", color: "#8a7a5a" } } };

  // ---------------- 姿勢 ----------------
  /** 角度是畫布旋轉（順時針為正）。arm：主手繞肩；wpn：武器相對手臂的角度（null＝照武器的預設握法）。 */
  const REST = { bob: 0, lean: 0, hipN: 0, hipF: 0, kneeN: 0, kneeF: 0, arm: 0, wpn: null, liftL: 0, liftR: 0, armL: 0, armR: 0, pull: 0, flash: 0 };
  const VIEW = { east: ["side", false], west: ["side", true], south: ["front", false], north: ["back", false] };
  /** 畫一個人；回傳主手武器的握把與作用端（目前畫布座標）。 */
  function figure(ctx, x, y, dir, P, opt = {}) {
    const u = opt.unit ?? HERO, s = opt.scale ?? 1.5, [view, west] = VIEW[dir];
    let probe = null;
    const pose = { ...P, wpn: P.wpn === null ? undefined : P.wpn, probe: (kind, hand, tip) => { probe = { hand, tip }; } };
    ctx.save(); ctx.__pull = P.pull;
    SD.setPose(pose); SD.stamp(ctx, u, view, x, y - (opt.air ?? 0), s, west); SD.setPose(null);
    if (P.flash > 0) { ctx.save(); ctx.filter = `brightness(0) invert(1) opacity(${P.flash.toFixed(3)})`; SD.setPose({ ...pose, probe: null }); SD.stamp(ctx, u, view, x, y - (opt.air ?? 0), s, west); SD.setPose(null); ctx.restore(); }
    const inv = ctx.getTransform().inverse(); ctx.__pull = 0; ctx.restore();
    if (!probe) return null;
    const back = (p) => { const q = inv.transformPoint(p); return [q.x, q.y]; };
    return { hand: back(probe.hand), tip: back(probe.tip), shoulder: [x, y - (opt.air ?? 0) - 31.6 * s] };
  }
  /** 走路循環。kind：walk／run／sneak。 */
  function walkPose(phase, kind = "walk") {
    const amp = kind === "run" ? 0.75 : kind === "sneak" ? 0.35 : 0.5, sn = Math.sin(phase);
    const P = { ...REST, hipN: amp * sn, hipF: -amp * sn, kneeN: 0.9 * Math.max(0, -Math.sin(phase + 0.9)), kneeF: 0.9 * Math.max(0, Math.sin(phase + 0.9)), arm: -0.35 * sn, bob: -Math.abs(Math.cos(phase)) * (kind === "run" ? 2.2 : 1.2), liftL: 3.2 * Math.max(0, sn), liftR: 3.2 * Math.max(0, -sn), armL: 1.6 * sn, armR: -1.6 * sn };
    if (kind === "run") { P.lean = 0.2; P.arm = -0.6 * sn - 0.3; }
    if (kind === "sneak") { P.lean = 0.3; P.bob += 2.5; P.kneeN += 0.5; P.kneeF += 0.5; P.arm = -0.6; }
    return P;
  }

  // ---------------- 片段 ----------------
  // 揮砍：武器的絕對角度＝arm＋wpn。由上往下：蓄力時刃朝後上方，命中時朝前下方，所以一定是刃在前、握把在手。
  const slash = (from, to, armFrom, armTo, dur, extra = {}) => ({ dur, pose: (t) => ({ ...REST, arm: mix(armFrom, armTo, ease.in(t)), wpn: mix(from, to, ease.in(t)), lean: mix(-0.1, 0.18, t), hipN: 0.45, hipF: -0.3, ...extra }), hitAt: 0.62, trail: true });
  const windup = (armTo, wpnTo, extra = {}) => ({ dur: 260, pose: (t) => ({ ...REST, arm: mix(0, armTo, ease.out(t)), wpn: mix(0.75, wpnTo, ease.out(t)), lean: -0.1 * t, hipN: 0.25 * t, hipF: -0.2 * t, ...extra }) });
  const CLIP = {
    // 揮砍 3 種變體（同一個「揮砍」位置；命中時間點一樣）
    windup: windup(-2.5, 1.7), slash: slash(1.7, 1.85, -2.5, 0.15, 220),
    windup_lo: windup(0.9, -3.3, { bob: 1.5 }), slash_lo: slash(-3.3, 2.6, 0.9, -1.6, 220),
    windup_side: windup(-1.2, -0.4), slash_side: { ...slash(-0.4, -3.5, -1.2, -1.2, 200), squash: 0.42 },
    // 突刺（矛）／出拳（拳套）
    thrust_in: { dur: 220, pose: (t) => ({ ...REST, arm: mix(0, 0.5, ease.out(t)), wpn: mix(0.15, 0.9, t), lean: -0.08 * t }) },
    thrust: { dur: 200, pose: (t) => ({ ...REST, arm: mix(0.5, -1.0, ease.in(t)), wpn: mix(0.9, 2.57, ease.in(t)), lean: 0.2 * t, hipN: 0.5 * t, hipF: -0.35 * t }), move: (t) => [8 * ease.out(t), 0, 0], hitAt: 0.7 },
    // 射擊：弓＝舉弓拉弦→放；弩、火槍＝舉起瞄準→擊發（後座）
    aim: { dur: 360, pose: (t) => ({ ...REST, arm: mix(0, -1.3, ease.out(t)), wpn: mix(2.3, 2.87, ease.out(t)), pull: 6 * ease.out(clamp((t - 0.3) / 0.7)), lean: -0.05 }) },
    release: { dur: 300, pose: (t) => ({ ...REST, arm: -1.3 - 0.25 * Math.sin(Math.min(1, t * 3) * Math.PI), wpn: 2.87 - 0.2 * Math.sin(Math.min(1, t * 3) * Math.PI), lean: -0.08 * (1 - t) }), shot: true, hitAt: 0.95 },
    // 施法（法杖、法球）：詠唱（舉杖、腳下法陣）→施放（杖頭指向目標）
    channel: { dur: 520, pose: (t) => ({ ...REST, arm: mix(0, -2.5, ease.out(clamp(t * 1.6))), wpn: mix(0, 2.7, ease.out(clamp(t * 1.6))), lean: -0.06, bob: -1.2 * Math.sin(t * Math.PI) }), circle: true },
    cast: { dur: 420, pose: (t) => ({ ...REST, arm: mix(-2.5, -1.2, ease.out(clamp(t * 3))), wpn: mix(2.7, 2.4, clamp(t * 3)), lean: 0.12 }), shot: true, hitAt: 0.95 },
    // 魔導劍＋飛行物 選項 A：劍指畫符（劍尖朝前，劍尖畫出符陣，火球從劍尖射出）
    sigil: { dur: 480, pose: (t) => ({ ...REST, arm: mix(0, -1.25, ease.out(clamp(t * 2))), wpn: mix(0.75, 2.82, ease.out(clamp(t * 2))), lean: -0.04 }), sigil: true },
    sigil_cast: { dur: 380, pose: (t) => ({ ...REST, arm: -1.25 - 0.15 * Math.sin(Math.min(1, t * 3) * Math.PI), wpn: 2.82, lean: 0.08 }), shot: true, hitAt: 0.95, afterSigil: true },
    // 魔導劍＋飛行物 選項 B：揮劍斬出（照揮砍，劍揮到前方時從劍尖放出火球）
    slash_wave: { ...slash(1.7, 1.85, -2.5, 0.15, 260), hitAt: undefined, shot: true, shotFrom: 0.55, shotHit: 0.98 },
    // 劍的普攻變體 4：突刺（用劍尖刺，不是揮）；變體 5：小跳斬（跳起來由上往下劈）
    stab_in: { dur: 200, pose: (t) => ({ ...REST, arm: mix(0, 0.6, ease.out(t)), wpn: mix(0.75, 1.0, t), lean: -0.1 * t, hipN: 0.2 * t }) },
    stab: { dur: 180, pose: (t) => ({ ...REST, arm: mix(0.6, -1.15, ease.in(t)), wpn: mix(1.0, 2.72, ease.in(t)), lean: 0.25 * t, hipN: 0.55 * t, hipF: -0.4 * t }), move: (t) => [10 * ease.out(t), 0, 0], hitAt: 0.7 },
    hop_windup: { dur: 280, pose: (t) => ({ ...REST, arm: mix(0, -2.7, ease.out(t)), wpn: mix(0.75, 1.9, ease.out(t)), kneeN: 1.0 * Math.sin(t * Math.PI), kneeF: 1.1 * Math.sin(t * Math.PI), hipN: 0.6 * Math.sin(t * Math.PI) }), move: (t) => [6 * t, 0, 16 * Math.sin(t * Math.PI * 0.9)] },
    hop_slash: { dur: 220, pose: (t) => ({ ...REST, arm: mix(-2.7, 0.35, ease.in(t)), wpn: mix(1.9, 1.75, t), lean: mix(0, 0.3, t), hipN: 0.5, hipF: -0.3, kneeN: 0.6 * (1 - t), kneeF: 0.7 * (1 - t) }), move: (t) => [6 + 4 * t, 0, 16 * Math.sin((0.9 + 0.1 * t) * Math.PI) * (1 - t)], hitAt: 0.65, trail: true },
    // 火球的詠唱變體：B＝杖橫在胸前畫圈（法陣在身前）；C＝杖頓地再上揚（法陣在腳下、火從地面捲起）
    channel_b: { dur: 520, pose: (t) => ({ ...REST, arm: mix(0, -1.4, ease.out(clamp(t * 1.6))) + 0.25 * Math.sin(t * Math.PI * 4), wpn: mix(0, 3.0, ease.out(clamp(t * 1.6))), lean: -0.04 }), circleFront: true },
    channel_c: { dur: 520, pose: (t) => { const down = clamp(t * 2.5), up = clamp((t - 0.45) * 2); return { ...REST, arm: mix(mix(0, 0.5, down), -2.2, ease.out(up)), wpn: mix(mix(0, -0.4, down), 2.6, ease.out(up)), lean: mix(0.1, -0.08, up), bob: 1.5 * down * (1 - up) }; }, circle: true, swirl: true },
    dash: { dur: 260, pose: () => ({ ...REST, lean: 0.35, hipN: 0.8, hipF: -0.7, kneeF: 0.9, arm: 0.6 }), move: (t) => [ease.inOut(t), 0, 0], ghost: true },
    leap: { dur: 420, pose: (t) => { const k = Math.sin(t * Math.PI); return { ...REST, hipN: 0.9 * k, kneeN: 1.5 * k, hipF: 0.5 * k, kneeF: 1.7 * k, arm: -0.9 * k }; }, move: (t) => [ease.inOut(t), 0, 34 * Math.sin(t * Math.PI)] },
    hit: { dur: 360, pose: (t) => ({ ...REST, lean: -0.3 * Math.sin(Math.min(1, t * 2) * Math.PI), arm: -0.5 * Math.sin(t * Math.PI), flash: Math.max(0, 1 - t * 4) * 0.85 }), move: (t) => [-7 * Math.sin(Math.min(1, t * 1.6) * Math.PI), 0, 0] },
    idle: { dur: 400, pose: (t) => ({ ...REST, bob: -0.5 * Math.sin(t * TAU) }) },
  };
  /** 每種武器的攻擊片段（起手＋出招）；出招片段最後的姿勢就是「命中瞬間」，自測用它。 */
  const ATTACK = {
    sword: ["windup", "slash"], saber: ["windup", "slash"], arcane_blade: ["windup", "slash"], paired: ["windup", "slash"], scythe: ["windup", "slash"], whip: ["windup", "slash"],
    spear: ["thrust_in", "thrust"], gauntlet: ["thrust_in", "thrust"],
    bow: ["aim", "release"], crossbow: ["aim", "release"], gun: ["aim", "release"],
    staff: ["channel", "cast"], orb: ["channel", "cast"],
  };

  // ---------------- 特效 ----------------
  function arcTrail(ctx, S, tip0, tip, el, alpha, squash = 1, wk = 1) {
    const [c1, c2] = ELEM[el]; const a0 = Math.atan2(tip0[1] - S[1], tip0[0] - S[0]); const a1 = Math.atan2(tip[1] - S[1], tip[0] - S[0]);
    let d = a1 - a0; while (d > Math.PI) d -= TAU; while (d < -Math.PI) d += TAU;
    const r = Math.hypot(tip[0] - S[0], tip[1] - S[1]);
    ctx.save(); ctx.globalAlpha = clamp(alpha); ctx.lineCap = "round"; if (wk > 1) { ctx.shadowColor = c2; ctx.shadowBlur = 16; }
    for (const [w, col] of [[9 * wk, c1], [3.5 * wk, c2]]) { ctx.strokeStyle = col; ctx.lineWidth = w; ctx.beginPath(); for (let k = 0; k <= 18; k++) { const a = a0 + d * k / 18; const px = S[0] + Math.cos(a) * r, py = S[1] + Math.sin(a) * r * squash + (squash < 1 ? r * (1 - squash) * 0.6 : 0); k ? ctx.lineTo(px, py) : ctx.moveTo(px, py); } ctx.stroke(); }
    ctx.restore();
  }
  function projectile(ctx, from, to, t, el, kind, traj = "arc") {
    if (t <= 0 || t >= 1) return;
    const [c1, c2] = ELEM[el];
    let x = mix(from[0], to[0], t), y = mix(from[1], to[1], t);
    if (traj === "arc") y -= Math.sin(t * Math.PI) * (kind === "orb" ? 14 : 3);
    else if (traj === "spiral") { const r = 9 * Math.sin(t * Math.PI); y += Math.sin(t * 18) * r; x += Math.cos(t * 18) * r * 0.4; }
    else if (traj === "high") y -= Math.sin(t * Math.PI) * 38;
    ctx.save();
    if (kind === "arrow" || kind === "bullet") { const a = Math.atan2(to[1] - from[1], to[0] - from[0]); ctx.translate(x, y); ctx.rotate(a); if (kind === "arrow") { ctx.strokeStyle = OUT; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(-14, 0); ctx.lineTo(4, 0); ctx.stroke(); ctx.strokeStyle = "#c8a070"; ctx.lineWidth = 1.6; ctx.stroke(); ctx.fillStyle = "#dfe4ea"; ctx.beginPath(); ctx.moveTo(8, 0); ctx.lineTo(2, -3); ctx.lineTo(2, 3); ctx.fill(); } else { ctx.fillStyle = "#fff4c0"; ctx.fillRect(-8, -1.2, 12, 2.4); } }
    else { ctx.shadowColor = c1; ctx.shadowBlur = 14; ctx.fillStyle = c1; ctx.beginPath(); ctx.arc(x, y, 7, 0, TAU); ctx.fill(); ctx.fillStyle = c2; ctx.beginPath(); ctx.arc(x, y, 3.5, 0, TAU); ctx.fill(); for (let k = 1; k < 5; k++) { ctx.globalAlpha = 0.5 - k * 0.1; ctx.fillStyle = c1; ctx.beginPath(); ctx.arc(x - Math.sign(to[0] - from[0]) * 5 * k, y + k, 6 - k, 0, TAU); ctx.fill(); } }
    ctx.restore();
  }
  function muzzle(ctx, p, t) { if (t <= 0 || t >= 1) return; ctx.save(); ctx.globalAlpha = 1 - t; ctx.fillStyle = "#ffd23a"; ctx.shadowColor = "#ff8a2a"; ctx.shadowBlur = 10; ctx.beginPath(); ctx.arc(p[0], p[1], 6 * (1 - t) + 2, 0, TAU); ctx.fill(); ctx.restore(); }
  function castCircle(ctx, foot, t, el) {
    if (t <= 0) return;
    const [c1] = ELEM[el]; ctx.save(); ctx.globalAlpha = clamp(t * 1.5); ctx.shadowColor = c1; ctx.shadowBlur = 10; ctx.strokeStyle = c1; ctx.lineWidth = 2;
    const r = 26 * ease.out(clamp(t * 1.4));
    ctx.beginPath(); ctx.ellipse(foot[0], foot[1], r, r * 0.35, 0, 0, TAU); ctx.stroke(); ctx.beginPath(); ctx.ellipse(foot[0], foot[1], r * 0.65, r * 0.23, 0, 0, TAU); ctx.stroke();
    ctx.restore();
  }
  function sigilAt(ctx, p, t, el) { // 劍尖畫出的小符陣
    if (t <= 0) return; const [c1, c2] = ELEM[el]; ctx.save(); ctx.globalAlpha = clamp(t * 2); ctx.shadowColor = c1; ctx.shadowBlur = 10; ctx.strokeStyle = c1; ctx.lineWidth = 1.8;
    const r = 11 * ease.out(clamp(t * 1.5)); ctx.beginPath(); ctx.arc(p[0], p[1], r, 0, TAU * clamp(t * 1.4)); ctx.stroke();
    ctx.strokeStyle = c2; ctx.beginPath(); for (let k = 0; k < 5; k++) { const a = -Math.PI / 2 + k * TAU * 2 / 5; ctx[k ? "lineTo" : "moveTo"](p[0] + Math.cos(a) * r * 0.7, p[1] + Math.sin(a) * r * 0.7); } ctx.closePath(); ctx.stroke(); ctx.restore();
  }
  function burst(ctx, p, t, el, shape = "rays") {
    if (t <= 0 || t >= 1) return;
    const [c1, c2] = ELEM[el]; ctx.save(); ctx.globalAlpha = 1 - t; ctx.shadowColor = c1; ctx.shadowBlur = 12;
    if (shape === "ring") { ctx.strokeStyle = c1; ctx.lineWidth = 4 * (1 - t) + 1; ctx.beginPath(); ctx.ellipse(p[0], p[1], 6 + 24 * t, 4 + 14 * t, 0, 0, TAU); ctx.stroke(); ctx.strokeStyle = c2; ctx.lineWidth = 2; ctx.beginPath(); ctx.ellipse(p[0], p[1], 3 + 14 * t, 2 + 8 * t, 0, 0, TAU); ctx.stroke(); }
    else if (shape === "star") { ctx.fillStyle = c1; ctx.beginPath(); for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + k * Math.PI / 5, r = (k % 2 ? 6 : 16 + 10 * t) * (0.6 + t); ctx[k ? "lineTo" : "moveTo"](p[0] + Math.cos(a) * r, p[1] + Math.sin(a) * r); } ctx.closePath(); ctx.fill(); ctx.fillStyle = c2; ctx.beginPath(); ctx.arc(p[0], p[1], 5 * (1 - t) + 1, 0, TAU); ctx.fill(); }
    else for (let k = 0; k < 8; k++) { const a = k / 8 * TAU; ctx.strokeStyle = k % 2 ? c1 : c2; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(p[0] + Math.cos(a) * 6 * t, p[1] + Math.sin(a) * 6 * t); ctx.lineTo(p[0] + Math.cos(a) * (8 + 18 * t), p[1] + Math.sin(a) * (8 + 18 * t)); ctx.stroke(); }
    ctx.restore();
  }
  function damageNumber(ctx, p, t, n, crit = false) {
    if (t <= 0 || t >= 1) return;
    const size = (crit ? 24 : 16) + (crit ? 14 : 6) * Math.max(0, 1 - t * 4), label = crit ? `暴擊 −${n}` : `−${n}`;
    ctx.save(); ctx.globalAlpha = t > 0.7 ? (1 - t) / 0.3 : 1; ctx.font = `bold ${size}px 'Microsoft JhengHei', sans-serif`; ctx.textAlign = "center";
    ctx.lineWidth = crit ? 5 : 4; ctx.strokeStyle = OUT; ctx.strokeText(label, p[0], p[1] - 22 * ease.out(t)); ctx.fillStyle = crit ? "#ffd23a" : "#ff5a48"; ctx.fillText(label, p[0], p[1] - 22 * ease.out(t));
    ctx.restore();
  }

  // ---------------- 串接器 ----------------
  let PC = null;
  function probeCtx() { if (!PC) { const c = document.createElement("canvas"); c.width = 4; c.height = 4; PC = c.getContext("2d"); } PC.setTransform(1, 0, 0, 1, 0, 0); return PC; }
  /** seq：[{clip, to?}]——片段依序播；to 是位移片段的終點（來自引擎事件的落點）。opt：{unit, crit}。 */
  function sequence(seq, startX, target, el, opt = {}) {
    const u = opt.unit ?? HERO, parts = []; let t0 = 0, x = startX;
    for (const s of seq) { const c = CLIP[s.clip]; parts.push({ ...s, c, t0, x0: x, x1: s.to ?? x }); t0 += c.dur; if (s.to !== undefined) x = s.to; }
    const animTotal = t0;
    let hitAt = -1;
    for (const p of parts) { if (p.c.hitAt !== undefined) hitAt = p.t0 + p.c.dur * p.c.hitAt; if (p.c.shotHit !== undefined) hitAt = p.t0 + p.c.dur * p.c.shotHit; }
    const crit = !!opt.crit, SLOW_IN = 140, SLOW_K = 0.3, STOP = 110, slowReal = SLOW_IN / SLOW_K;
    const warp = (r) => { if (!crit || hitAt < 0) return r; const a0 = hitAt - SLOW_IN; if (r < a0) return r; if (r < a0 + slowReal) return a0 + (r - a0) * SLOW_K; if (r < a0 + slowReal + STOP) return hitAt; return r - (slowReal - SLOW_IN) - STOP; };
    const total = crit && hitAt >= 0 ? animTotal + (slowReal - SLOW_IN) + STOP : animTotal;
    const hitReal = crit && hitAt >= 0 ? hitAt - SLOW_IN + slowReal : hitAt;
    const wk = u.gear.main_hand.kind, shotKind = wk === "bow" || wk === "crossbow" ? "arrow" : wk === "gun" ? "bullet" : "orb";
    function draw(ctx, realMs, groundY, dir = "east") {
      const ms = warp(Math.min(realMs, total));
      ctx.save();
      if (crit && realMs >= hitReal && realMs < hitReal + 260) { const k2 = 1 - (realMs - hitReal) / 260; ctx.translate(Math.sin(realMs * 0.9) * 4 * k2, Math.cos(realMs * 1.3) * 3 * k2); }
      const r = drawAt(ctx, Math.min(ms, animTotal), groundY, dir);
      ctx.restore();
      if (crit && realMs >= hitReal && realMs < hitReal + 70) { ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = "rgba(255,250,230,0.35)"; ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height); ctx.restore(); }
      return r;
    }
    function drawAt(ctx, k, groundY, dir) {
      let cur = parts[parts.length - 1], local = 1;
      for (const p of parts) if (k >= p.t0 && k < p.t0 + p.c.dur) { cur = p; local = (k - p.t0) / p.c.dur; break; }
      const P = cur.c.pose(local), m = cur.c.move ? cur.c.move(local) : [0, 0, 0];
      const ax = cur.to !== undefined ? mix(cur.x0, cur.x1, m[0]) : cur.x0 + m[0];
      const sign = dir === "west" ? -1 : 1;
      if (cur.c.ghost) for (let g = 1; g <= 3; g++) { ctx.save(); ctx.globalAlpha = 0.18; figure(ctx, mix(cur.x0, cur.x1, Math.max(0, m[0] - g * 0.12)), groundY, dir, P, { unit: u }); ctx.restore(); }
      const tl = hitAt >= 0 && k >= hitAt ? (k - hitAt) / CLIP.hit.dur : -1;
      const TP = tl >= 0 && tl < 1 ? CLIP.hit.pose(tl) : CLIP.idle.pose((k / 1600) % 1);
      const tdx = tl >= 0 && tl < 1 ? CLIP.hit.move(tl)[0] : 0;
      figure(ctx, target - tdx * sign, groundY, dir === "east" ? "west" : "east", TP, { unit: FOE });
      const B = [target, groundY - 46];
      const W = figure(ctx, ax, groundY, dir, P, { unit: u, air: m[2] });
      const el2 = crit ? "crit" : el;
      if (cur.c.trail && W) { const W0 = figure(probeCtx(), ax, groundY, dir, cur.c.pose(0), { unit: u, air: m[2] }); if (W0) arcTrail(ctx, W.shoulder, W0.tip, W.tip, cur.c.shot ? el : el2, 1 - Math.max(0, local - 0.8) * 5, cur.c.squash ?? 1, crit ? 1.7 : 1); }
      if (cur.c.circle) castCircle(ctx, [ax, groundY], local, el);
      if (cur.c.circleFront && W) { ctx.save(); ctx.translate(W.hand[0] + 14 * sign, W.hand[1] - 4); ctx.scale(0.35, 1); castCircle(ctx, [0, 0], local, el); ctx.restore(); }
      if (cur.c.swirl) { const [c1] = ELEM[el]; ctx.save(); ctx.globalAlpha = clamp(local * 2) * (1 - clamp((local - 0.8) * 5)); ctx.strokeStyle = c1; ctx.lineWidth = 2; ctx.shadowColor = c1; ctx.shadowBlur = 8; ctx.beginPath(); for (let q = 0; q <= 30; q++) { const a = q / 30 * TAU * 2 + local * 6, r = 14 - q * 0.3; ctx[q ? "lineTo" : "moveTo"](ax + Math.cos(a) * r, groundY - q * 1.6 * local); } ctx.stroke(); ctx.restore(); }
      if (cur.c.sigil && W) sigilAt(ctx, W.tip, local, el);
      if (cur.c.afterSigil && W) sigilAt(ctx, W.tip, 1 - local, el);
      if (cur.c.shot && W) {
        const from = cur.c.shotFrom ?? 0, upto = cur.c.shotHit ?? cur.c.hitAt;
        if (local >= from) {
          // 出發點＝出招瞬間的作用端（劍尖、槍口、杖頭）
          const W1 = figure(probeCtx(), ax, groundY, dir, cur.c.pose(from), { unit: u, air: m[2] }) ?? W;
          const tt = clamp((local - from) / (upto - from));
          projectile(ctx, W1.tip, B, tt, el, shotKind, opt.traj ?? "arc");
          if (shotKind === "bullet") muzzle(ctx, W1.tip, tt * 3);
        }
      }
      if (tl >= 0) { burst(ctx, B, tl * (crit ? 0.9 : 1.4), el2, opt.burst ?? "rays"); damageNumber(ctx, [target, groundY - 70], tl * 0.6, crit ? 24 : 12, crit); }
      return { clip: cur.clip, parts, weapon: W };
    }
    return { total, draw };
  }

  // ---------------- 高低差：照遊戲規格（格子 48、每一級抬高 6，client battle/elevation.ts 的 TILE_SIZE／RAISE）----------------
  const TILE = 48, RAISE = 6;
  /** 一排格子（由西到東），heights 是每格的高度級數；人從第 0 格走到最後一格。高一級＝走上去（抬腳），高兩級以上＝跳。 */
  function heightRow(ctx, x0, y0, heights, ms, sc = 1) {
    const n = heights.length;
    // 地面：兩列格子（後列、人站的列），每格依高度往上抬 RAISE×級數，南側畫立面
    for (const row of [0, 1]) for (let i = 0; i < n; i++) {
      const h = heights[i], x = x0 + i * TILE, y = y0 + row * TILE - h * RAISE;
      ctx.fillStyle = ["#7d8c84", "#8a998f", "#97a69c"][Math.min(2, h)]; ctx.fillRect(x, y, TILE, TILE); ctx.fillStyle = "rgba(255,255,255,0.10)"; ctx.fillRect(x + 3, y + 3, TILE - 6, 2);
      ctx.strokeStyle = "rgba(0,0,0,0.25)"; ctx.lineWidth = 1; ctx.strokeRect(x + 0.5, y + 0.5, TILE - 1, TILE - 1);
      if (h > 0 && row === 1) { ctx.fillStyle = "#5e665f"; ctx.fillRect(x, y + TILE, TILE, h * RAISE); for (let k = 1; k < h; k++) { ctx.fillStyle = "rgba(0,0,0,0.3)"; ctx.fillRect(x, y + TILE + k * RAISE, TILE, 1); } }
      if (row === 0 && h > 0) { ctx.fillStyle = "rgba(255,255,255,0.18)"; ctx.fillRect(x, y, TILE, 2); }
    }
    // 人：每格 0.55 秒；同高或差一級＝走（差一級時腳先抬，身體在後半段升 6）；差兩級以上＝跳（拋物線、落地揚塵）
    const per = 550, total = per * (n - 1) + 700, t = ms % total, seg = Math.min(n - 2, Math.floor(t / per)), u = clamp((t - seg * per) / per);
    const hA = heights[seg], hB = heights[seg + 1], diff = hB - hA, footY = y0 + TILE * 1.62;
    let x = x0 + (seg + 0.5 + (t >= per * (n - 1) ? 1 : ease.inOut(u))) * TILE, lift, P, air = 0;
    if (t >= per * (n - 1)) { lift = heights[n - 1] * RAISE; P = { ...CLIP.idle.pose((ms / 1600) % 1) }; x = x0 + (n - 0.5) * TILE; }
    else if (Math.abs(diff) <= 1) {
      lift = (hA + diff * ease.inOut(clamp((u - 0.4) / 0.6))) * RAISE;
      P = walkPose(u * Math.PI * 2);
      if (diff > 0) { P.hipN += 0.4 * Math.sin(u * Math.PI); P.kneeN += 0.7 * Math.sin(u * Math.PI); P.lean = 0.1; }
    } else {
      lift = mix(hA, hB, ease.inOut(u)) * RAISE; air = Math.sin(u * Math.PI) * (14 + Math.abs(diff) * RAISE) * (diff > 0 ? 1 : 0.7);
      P = CLIP.leap.pose(u);
      if (u > 0.85) { ctx.save(); ctx.globalAlpha = (1 - u) * 5; ctx.fillStyle = "#c8b890"; for (let k = -2; k <= 2; k++) { ctx.beginPath(); ctx.arc(x + k * 6, footY - lift + 2, 3, 0, TAU); ctx.fill(); } ctx.restore(); }
    }
    figure(ctx, x, footY - lift, "east", P, { unit: HERO, scale: 0.9 * sc, air });
    return { diff, seg };
  }
  // ---------------- 舊的示意樓梯（第一版，已不用）----------------
  function stairs(ctx, x0, gy, ms) {
    const steps = 4, sw = 34, sh = 12, period = 3600;
    for (let k = 0; k < steps; k++) { const x = x0 + 70 + k * sw; ctx.fillStyle = k % 2 ? "#8a948c" : "#9aa39c"; ctx.fillRect(x, gy - (k + 1) * sh, sw * (steps - k) + 40, sh); ctx.strokeStyle = OUT; ctx.lineWidth = 1.5; ctx.strokeRect(x, gy - (k + 1) * sh, sw * (steps - k) + 40, sh); ctx.fillStyle = "rgba(0,0,0,0.25)"; ctx.fillRect(x, gy - (k + 1) * sh + sh - 3, sw * (steps - k) + 40, 3); }
    const t = (ms % period) / period, x = x0 + 20 + t * (70 + steps * sw + 20);
    const stepIdx = clamp((x - (x0 + 70) + 12) / sw, 0, steps), base = Math.floor(stepIdx), frac = stepIdx - base;
    const rise = (base + ease.inOut(clamp((frac - 0.55) / 0.45))) * sh;
    const phase = t * 12 * Math.PI, P = walkPose(phase);
    if (x > x0 + 60 && x < x0 + 70 + steps * sw) { P.kneeN += 0.6 * Math.max(0, Math.sin(phase)); P.hipN += 0.35 * Math.max(0, Math.sin(phase)); P.lean = 0.08; }
    figure(ctx, x, gy - Math.min(steps * sh, rise), "east", P);
  }

  // ---------------- 自測：每種武器朝東、朝西出招的瞬間，作用端都在手的前方；正面、背面握在柄上 ----------------
  function selfTest() {
    const rows = [];
    for (const kind of Object.keys(WEAPONS)) {
      const u = unit(kind), P = CLIP[ATTACK[kind][1]].pose(1), res = {};
      for (const dir of ["east", "west"]) { const W = figure(probeCtx(), 100, 100, dir, P, { unit: u }); const sign = dir === "west" ? -1 : 1; res[dir] = W ? (W.tip[0] - W.hand[0]) * sign : NaN; }
      for (const dir of ["south", "north"]) { const W = figure(probeCtx(), 100, 100, dir, REST, { unit: u }); res[dir] = W ? Math.hypot(W.tip[0] - W.hand[0], W.tip[1] - W.hand[1]) / (WEAPONS[kind].len * 1.5) : NaN; }
      rows.push({ kind, zh: WEAPON_ZH[kind], east: res.east > 2, west: res.west > 2, south: res.south > 0.9, north: res.north > 0.9, dx: [res.east, res.west] });
    }
    return rows;
  }

  /** 同 client/src/render/inkStyle.ts 的 seedOf（FNV-1a）。 */
  function seedOf(str) { let h = 2166136261; for (const ch of str) h = Math.imul(h ^ (ch.codePointAt(0) ?? 0), 16777619); return h >>> 0; }
  const SLASH_VARIANTS = [["windup", "slash", "由上往下"], ["windup_lo", "slash_lo", "由下往上"], ["windup_side", "slash_side", "橫掃"]];
  function pickVariant(battleId, eventSeq, unitId, n) { return seedOf(`${battleId}:${eventSeq}:${unitId}:anim`) % n; }

  return { CLIP, ELEM, REST, WEAPONS, WEAPON_ZH, ATTACK, figure, walkPose, sequence, stairs, heightRow, TILE, RAISE, selfTest, ease, unit, HERO, MAGE, FOE, seedOf, pickVariant, SLASH_VARIANTS };
})();
