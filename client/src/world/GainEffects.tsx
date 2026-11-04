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
import { FLY_MS, FLY_STAGGER_MS, flyAt, gainedItems, levelUp, PILLAR_MS, type Gain } from "./gainFx";

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
    if (lv === null) return undefined;
    count.current += 1;
    setShown({ level: lv, n: count.current });
    const timer = window.setTimeout(() => setShown(null), PILLAR_MS);
    return () => window.clearTimeout(timer);
  }, [view]);
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

/** 物品圖示：裝備是一把劍，其他是一個布袋（不畫字）。 */
export function GainIcon({ gear }: { gear: boolean }) {
  return gear ? (
    <svg viewBox="0 0 28 28" width="28" height="28">
      <circle cx="14" cy="14" r="13" fill="#2a2018" stroke="#e8bb48" strokeWidth="1.6" />
      <path d="M8 20 L19 9" stroke="#1c1712" strokeWidth="4.4" strokeLinecap="round" />
      <path d="M8 20 L19 9" stroke="#e6ecf2" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M7 15 L13 21" stroke="#e8bb48" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  ) : (
    <svg viewBox="0 0 28 28" width="28" height="28">
      <circle cx="14" cy="14" r="13" fill="#2a2018" stroke="#e8bb48" strokeWidth="1.6" />
      <path d="M9 12 Q14 8 19 12 L20 19 Q14 23 8 19 Z" fill="#c89858" stroke="#1c1712" strokeWidth="1.4" />
      <path d="M10.5 11.5 Q14 13.5 17.5 11.5" stroke="#7a4e2a" strokeWidth="1.4" fill="none" />
    </svg>
  );
}

interface Flight {
  key: string;
  gain: Gain;
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
      <GainIcon gear={flight.gain.gear} />
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
    setFlights((f) => [...f, ...gains.map((g, i) => ({ key: `${start + i}:${g.item}`, gain: g, delay: i * FLY_STAGGER_MS }))]);
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
