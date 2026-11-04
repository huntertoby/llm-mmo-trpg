// 武器專屬待機（美術 PM，2026-11-04 晚；使用者：「要有待機動化 就是沒輪到他它會在那邊晃 每個武器不一樣動作」）。
// 每種武器一個循環 pose(u)（u ＝ 0～1），疊在 6M-4 的呼吸上；同一隊的人用單位 id 的 FNV-1a 雜湊錯開相位（同 idleClips 的 breathPhase），
// 不用 Math.random、不讀時間；同一個 id、同一個時鐘永遠同一格。「減少動態」開啟時一律回到站好（REST）。
// 姿勢鍵和 6M／6N 同一份，另加只影響畫法的鍵：shieldUp（盾往上抬）、glow（光 0～1）、orbY（法球上下）、lash（鞭梢 0～1）、dw（武器在手上的角度偏移）。
// 有關鍵姿勢的武器（雙手劍、長柄、弓、弩與槍、法杖）不給絕對的 wpn，只給 arm／dw 偏移，疊在 qDoll 的 KEY 上（武器跟著手走）。
window.IdleWeapons = (() => {
  const TAU = Math.PI * 2;
  const S = (u, k = 1) => Math.sin(u * TAU * k);
  const C = (u, k = 1) => Math.cos(u * TAU * k);
  const bump = (u, a, b) => (u < a || u > b ? 0 : Math.sin(((u - a) / (b - a)) * Math.PI)); // a～b 之間 0→1→0
  const ease = (t) => t * t * (3 - 2 * t);
  const breath = (u) => ({ bob: -0.5 * (0.5 - 0.5 * C(u)) });
  // ms：循環長度；zh：說明；pose(u)：側面姿勢（正面、背面只用 bob、glow、orbY、shieldUp、pull）
  const IDLE = {
    sword: { ms: 2400, zh: "劍：劍尖輕輕晃、重心微移", pose: (u) => ({ ...breath(u), wpn: 0.75 + 0.08 * S(u), arm: 0.05 * S(u), hipN: 0.05 * S(u), hipF: -0.05 * S(u) }) },
    sword_shield: { ms: 2400, zh: "劍盾：舉盾微晃", pose: (u) => ({ ...breath(u), shieldUp: 1.6 * (0.5 - 0.5 * C(u)), wpn: 0.75 + 0.05 * S(u), lean: -0.03 * (0.5 - 0.5 * C(u)) }) },
    saber: { ms: 2400, zh: "刀：刀尖畫小圈", pose: (u) => ({ ...breath(u), wpn: 0.75 + 0.16 * S(u), arm: 0.08 * C(u) }) },
    arcane_blade: { ms: 2400, zh: "魔導劍：劍槽符文光脈動", pose: (u) => ({ ...breath(u), wpn: 0.75 + 0.05 * S(u), glow: 0.5 - 0.5 * C(u) }) },
    // 成對武器（第 7 版）：一手一把；手腕往前轉、刃尖往前下壓再收回（刃一直朝前，不翻向自己；審查：「一把刃朝身體內側，另一把浮在胸前」）
    paired: { ms: 2400, zh: "成對武器：一手一把，手腕轉一下匕首", pose: (u) => ({ ...breath(u), idle: 1, wpn: 0.75 + 0.45 * bump(u, 0.3, 0.65), arm: -0.15 * bump(u, 0.25, 0.65) }) },
    spear: { ms: 2400, zh: "長槍：槍尖往前點兩下", pose: (u) => { const k = bump(u, 0.15, 0.3) + bump(u, 0.35, 0.5); return { ...breath(u), dw: 0.1 * k, arm: -0.04 * k }; } },
    scythe: { ms: 2400, zh: "鐮：刃緩慢前後擺", pose: (u) => ({ ...breath(u), dw: 0.08 * S(u), lean: 0.03 * S(u) }) },
    whip: { ms: 1200, zh: "鞭：鞭梢甩動", pose: (u) => ({ ...breath(u), lash: u, arm: 0.06 * S(u) }) },
    gauntlet: { ms: 1200, zh: "拳套：舉拳原地小跳", pose: (u) => { const h = Math.abs(S(u)); return { bob: -2.2 * h, arm: -0.55, wpn: 1.0, kneeN: 0.35 * (1 - h), kneeF: 0.35 * (1 - h), liftL: 0.8 * h, liftR: 0.8 * h }; } },
    staff: { ms: 2400, zh: "法杖：杖頭光點脈動、杖身微晃", pose: (u) => ({ ...breath(u), glow: 0.5 - 0.5 * C(u), dw: 0.04 * S(u) }) },
    orb: { ms: 2400, zh: "法球：法球在掌上浮沉、光脈動", pose: (u) => ({ ...breath(u), orbY: -1.4 * (0.5 - 0.5 * C(u)), glow: 0.5 - 0.5 * C(u) }) },
    // 弓：箭搭在弦上、弓口朝前下，持弓手垂在身側，弦放鬆；循環中段把弓抬起來看一下再放下（使用者：「收先不可能是這樣拉弓待機」）
    bow: { ms: 2400, zh: "弓：箭搭在弦上、弓口朝下，偶爾把弓抬起來看一下", pose: (u) => { const k = bump(u, 0.35, 0.8); return { ...breath(u), nock: 1, arm: -0.3 * k, dw: -0.2 * k }; } },
    crossbow: { ms: 2400, zh: "弩：托著待命，弩口往下點一下再抬回", pose: (u) => { const k = bump(u, 0.2, 0.6); return { ...breath(u), dw: 0.25 * k, arm: 0.06 * k }; } },
    gun: { ms: 2400, zh: "火槍：持槍待命、重心左右換", pose: (u) => ({ ...breath(u), dw: 0.08 * bump(u, 0.1, 0.35), hipN: 0.08 * S(u), hipF: -0.08 * S(u), lean: 0.03 * S(u) }) },
    // 雙手劍：拄劍站著，重心左右換（劍跟著手走）
    greatsword: { ms: 2400, zh: "雙手劍：拄劍、重心左右換", pose: (u) => ({ ...breath(u), dw: 0.03 * S(u), hipN: 0.1 * S(u), hipF: -0.1 * S(u), lean: 0.03 * S(u) }) },
  };
  /** FNV-1a（同 client idleClips.idHash）。 */
  function idHash(id) { let h = 2166136261; for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619); return h >>> 0; }
  const phaseOf = (id) => (idHash(`${id}:weaponIdle`) % 1000) / 1000;
  /** 量化成 8 格（同裝備、同朝向、同一格共用貼圖；光、法球浮沉這類疊加層不量化）。 */
  const FRAMES = 8;
  function frame(kind, id, ms, opt = {}) {
    const I = IDLE[kind] ?? IDLE.sword;
    if (opt.reduce) return { pose: {}, frame: 0 };
    const u = (ms / I.ms + phaseOf(id)) % 1;
    const q = opt.quantize === false ? u : Math.floor(u * FRAMES) / FRAMES;
    const p = I.pose(q), live = I.pose(u);
    return { pose: { ...p, glow: live.glow, orbY: live.orbY }, frame: Math.floor(u * FRAMES), u };
  }
  return { IDLE, frame, phaseOf, idHash, FRAMES };
})();
