// QK-8b（docs/art/QK-8檢查.md 必修 1）：疤面的刀（main_hand saber）被 KNOWN_KINDS 濾掉、畫不出來。
// 這裡檢查疤面地圖紙娃娃有主手，並掃全部 content 的外觀格 kind，確認沒有其他值被 KNOWN_KINDS 濾掉。
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import type { NpcPortrait } from "../api/types";
import { KNOWN_KINDS, resolveDoll, type GearSlot } from "../render/appearance";
import { qWeapon } from "../render/qWeapons";
import { npcFieldLook } from "./npcLook";
import { listFiles, readFile } from "../test/sourceScan";
import cloudYaml from "../../../content/world/npcs/cloud_ridge.yaml?raw";

const CONTENT_DIR = new URL("../../../content/", import.meta.url);

describe("QK-8b：NPC 主手", () => {
  it("疤面有主手（刀 saber），Q 版武器表畫得出來", () => {
    const npcs = (parse(cloudYaml) as { npcs: { id: string; portrait?: NpcPortrait }[] }).npcs;
    const scar = npcs.find((n) => n.id === "scarface");
    expect(scar?.portrait).toBeDefined();
    const look = npcFieldLook({ id: "scarface", portrait: scar!.portrait! })!;
    const spec = resolveDoll({ template: look.template_id, dollLook: look.doll_look, team: "third", summon: false, weaponId: look.weapon_id, weaponClass: look.weapon_class });
    expect(spec.gear.main_hand?.kind).toBe("saber");
    expect(qWeapon(spec.gear.main_hand)).not.toBeNull();
  });

  it("content 裡所有外觀格的 kind 都在 KNOWN_KINDS（不會被濾掉）", () => {
    const missing: string[] = [];
    const walk = (o: unknown, file: string): void => {
      if (Array.isArray(o)) o.forEach((x) => walk(x, file));
      else if (o !== null && typeof o === "object") {
        for (const [k, v] of Object.entries(o)) {
          if (k in KNOWN_KINDS && v !== null && typeof v === "object" && typeof (v as { kind?: unknown }).kind === "string") {
            const kind = (v as { kind: string }).kind;
            if (!KNOWN_KINDS[k as GearSlot].includes(kind)) missing.push(`${file}: ${k}.${kind}`);
          }
          walk(v, file);
        }
      }
    };
    const files = listFiles(CONTENT_DIR, (f) => /^(units|world|ui)\/.*\.ya?ml$/.test(f));
    expect(files.length).toBeGreaterThan(10);
    for (const f of files) walk(parse(readFile(CONTENT_DIR, f)), f);
    expect(missing).toEqual([]);
  });
});
