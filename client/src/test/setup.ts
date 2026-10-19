// vitest 共用設定：載入真實的名詞對照表（由 /api/glossary 的回應存成，見 docs/phases/Phase3-4a報告.md）。
import glossary from "../battle/fixtures/glossary.json";
import type { Glossary } from "../api/types";
import { setGlossary } from "../battle/glossary";

setGlossary(glossary as unknown as Glossary);
