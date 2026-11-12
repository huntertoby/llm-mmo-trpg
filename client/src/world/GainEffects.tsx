// 升級光柱與拿到物品飛進背包（Phase 6N-10；動畫方案 2.8）。只看前後兩次伺服器畫面的差（gainFx.ts），不改任何東西。
// - `LevelPillar`：疊在實地地圖上（跟著鏡頭平移，和頭頂圖示同一層），升級時主角腳下升起光柱、浮出「Lv N」。
// - `ItemFly`：疊在 HUD 裡（相對 HUD 絕對定位，不是彈出層），拿到的物品圖示從畫面中央（鏡頭跟著主角）拋物線飛進功能列的背包圖示。
// 減少動態時：光柱與 Lv 直接顯示一下就收，物品直接出現在背包圖示上淡出（不飛）。
import { useEffect, useRef, useState } from "react";
import type { Pos, WorldView } from "../api/types";
import { heightAt, tileLift, topReserve, type HeightGrid } from "../battle/elevation";
import { TILE_SIZE } from "../battle/geometry";
import "../ui/uiMotion.css";
import { prefersReducedMotion } from "./frameLoop";
import { GearIcon } from "../ui/GearIcon";
import { ItemIcon } from "../ui/ItemIcon";
import { FLY_MS, FLY_STAGGER_MS, flyAt, gainedItems, gainIconOf, levelUp, PILLAR_MS, type Gain, type GainIconChoice } from "./gainFx";

/** 主角腳底在畫布上的位置（CSS 像素，含縮放與抬高）。 */
export function feetAnchor(grid: HeightGrid, p: Pos, scale: number): { left: number; top: number } {
  const top = topReserve(grid) + (p.y + 0.86) * TILE_SIZE - tileLift(heightAt(grid, p));
  return { left: (p.x + 0.5) * TILE_SIZE * scale, top: top * scale };
}

/** 記住上一次的畫面（第一次 `null`）。 */
function usePrevious<T>(value: T): T | null {
  const ref = useRef<{ v: T } | null>(null);
  const prev = ref.current?.v ?? null;
  useEffect(() => {
    ref.current = { v: value };
  }, [value]);
  return prev;
}

export function LevelPillar({ view, grid, at, scale }: { view: WorldView; grid: HeightGrid; at: Pos; scale: number }) {
  const prev = usePrevious(view);
  const [shown, setShown] = useState<{ level: number; n: number } | null>(null);
  const count = useRef(0);
  useEffect(() => {
    const lv = levelUp(prev, view);
    if (lv === null) return;
    count.current += 1;
    setShown({ level: lv, n: count.current });
  }, [view]);
  // 6R-F（前端審查第 3 點）：收掉的計時器跟著「這一次光柱」（n），不跟著 view；升級後馬上又來一次畫面更新時不會被清掉而殘留
  const n = shown?.n ?? null;
  useEffect(() => {
    if (n === null) return undefined;
    const timer = window.setTimeout(() => setShown((s) => (s?.n === n ? null : s)), PILLAR_MS);
    return () => window.clearTimeout(timer);
  }, [n]);
  if (shown === null) return null;
  const pos = feetAnchor(grid, at, scale);
  return (
    <div key={shown.n} className="level-pillar" style={{ left: pos.left, top: pos.top }} data-testid="level-pillar" aria-hidden="true">
      <div className="ring" />
      <div className="beam" />
      <div className="lv">Lv {shown.level}</div>
    </div>
  );
}

/** 通用圖示（QI-7 起是 Q 版畫布，深底圓金邊含在畫布裡）：沒外觀的裝備一把劍（`gain_gear`），表裡沒有的物品一個布袋（`gain_item`），不畫字。 */
export function GainIcon({ gear }: { gear: boolean }) {
  return <ItemIcon id={gear ? "gain_gear" : "gain_item"} size={28} frame="fly" />;
}

/**
 * 飛行的圖示：有外觀的裝備畫 `GearIcon` 的實際圖示（6Q-1；`.gain-gear` 直徑 32 的深色圓底、金邊畫在圓外）；物品畫自己的 Q 版圖示（QI-7）、
 * 其他用 `GainIcon`。物品與通用圖示的飛行圓照 GainIcon 是 28 格裡直徑 26 的圓、金邊壓在圓上，和裝備的 32 不同（外徑差約 6px；
 * 開發 PM 定物品移植需求第 5 節第 8 點選 (a)：維持現況）。
 */
export function GainFlyIcon({ choice }: { choice: GainIconChoice }) {
  if (choice.kind === "generic") return <GainIcon gear={choice.gear} />;
  if (choice.kind === "item") return <ItemIcon id={choice.item} size={28} frame="fly" color={choice.color} rare={choice.rare} />;
  return (
    <span className="gain-gear">
      <GearIcon look={choice.look} slot={choice.slot ?? undefined} size={32} />
    </span>
  );
}

interface Flight {
  key: string;
  gain: Gain;
  icon: GainIconChoice;
  delay: number;
}

const BAG_SELECTOR = '[data-hud="btn-bag"]';

/** 元素中心，相對 `base`（HUD 本身）的左上角。 */
function centerOf(el: Element | null, base: DOMRect): { x: number; y: number } | null {
  if (el === null) return null;
  const r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2 - base.left, y: r.top + r.height / 2 - base.top };
}

function FlyingIcon({ flight, onDone }: { flight: Flight; onDone(key: string): void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [still, setStill] = useState(false);
  useEffect(() => {
    const el = ref.current;
    const hud = el?.closest(".world-hud") ?? null;
    const base = hud?.getBoundingClientRect();
    const to = base === undefined ? null : centerOf(hud!.querySelector(BAG_SELECTOR), base);
    if (el === null || base === undefined || to === null) {
      onDone(flight.key);
      return undefined;
    }
    // 起點：HUD 中央（鏡頭跟著主角，主角大約在中央）
    const from = { x: base.width / 2, y: base.height / 2 };
    if (prefersReducedMotion() || typeof el.animate !== "function") {
      el.style.transform = `translate(${to.x}px, ${to.y}px)`;
      setStill(true);
      const timer = window.setTimeout(() => onDone(flight.key), 600);
      return () => window.clearTimeout(timer);
    }
    const frames = Array.from({ length: 13 }, (_, i) => {
      const f = flyAt(from, to, i / 12);
      return { transform: `translate(${f.x}px, ${f.y}px) scale(${f.scale})`, opacity: f.alpha };
    });
    el.style.transform = frames[0]!.transform;
    const anim = el.animate(frames, { duration: FLY_MS, delay: flight.delay, fill: "both", easing: "linear" });
    anim.onfinish = () => onDone(flight.key);
    return () => anim.cancel();
  }, [flight, onDone]);
  return (
    <div ref={ref} className={`item-fly${still ? " still" : ""}`} data-testid="item-fly" data-item={flight.gain.item} aria-hidden="true">
      <GainFlyIcon choice={flight.icon} />
    </div>
  );
}

export function ItemFly({ view }: { view: WorldView }) {
  const prev = usePrevious(view.inventory ?? null);
  const [flights, setFlights] = useState<Flight[]>([]);
  const serial = useRef(0);
  const sameChar = useRef(view.character.character_id);
  useEffect(() => {
    const switched = sameChar.current !== view.character.character_id;
    sameChar.current = view.character.character_id;
    if (switched) return;
    const gains = gainedItems(prev, view.inventory ?? null);
    if (gains.length === 0) return;
    const start = serial.current;
    serial.current += gains.length;
    const now = view.inventory ?? null;
    setFlights((f) => [...f, ...gains.map((g, i) => ({ key: `${start + i}:${g.item}`, gain: g, icon: gainIconOf(now, g), delay: i * FLY_STAGGER_MS }))]);
  }, [view]);
  const done = useRef((key: string) => setFlights((f) => f.filter((x) => x.key !== key))).current;
  return (
    <>
      {flights.map((f) => (
        <FlyingIcon key={f.key} flight={f} onDone={done} />
      ))}
    </>
  );
}
