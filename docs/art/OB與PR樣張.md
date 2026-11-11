# #150／#147 三項介面樣張（OB-5、OB-6、PR-2 用）

畫圖 agent，2026-11-11。依據：`docs/design/21-探索地圖與城鎮.md` 21.5（#150 九點、#147 測試模式）、共用筆記 `盤點-150與147.md` 第 1.1、1.2、3.2、5 節與 `台詞-150與147.md`、`靶場移植需求.md`。

- 樣張頁：`sample/ob-range-class.html`、`sample/ob-range-entry.html`、`sample/practice-battle.html`；共用 `sample/obSamples.js`、`sample/obSamples.css`；截圖外框 `sample/tools/ob-frame.html`。
- 整頁截圖 16 張在 `shots/ob/`，特寫 37 張在 `closeup/ob/`（檔名尾 `-3x`、`-2x` 是倍率）。
- **做法**：三頁直接載入現行的 `client/src/styles/index.css`（只讀），DOM 與 class 照現行元件寫，所以框、按鈕、條、四角飾件和遊戲是同一份樣式；樣張新增的只有 `ob-*`（`obSamples.css`）。四角飾件與區域色照 `client/src/ui/regionCorners.ts`、`content/ui/region_themes.yaml` 重算（主城 filigree、霧渡鎮 cloud）。
- **圖示沿用現行**：技能、武器圖示是現行 C 墨線（`SkillIcon.draw`、`GearArt.draw`），沒有改畫。
- 樣張沒有畫的：大世界四角 HUD（主角卡、小地圖、功能列）。第 2 項只畫場景與面板。

## 1. 靶場「選大類」（`ob-range-class.html`，#150 第 1 點）

`?state=none｜hover｜selected`。版面：標題牌 → 守印人台詞 → 三張大類卡 → 確認列。

### 1.1 內容與出處

| 元素 | 內容 | 出處 |
|---|---|---|
| 大類與入門武器 | 近戰 單手劍、遠程 弓、法器 火焰法杖 | `content/world/newcomer.yaml` `range.starters`；名稱與外觀 `content/weapons.yaml` |
| 入門招 | 近戰 瞬步背刺＋塔盾猛擊；遠程 散彈驅離＋壓制射擊；法器 火焰箭＋火花連鎖 | `newcomer.yaml` `range.demos`、`content/skills/*.yaml`（代價也是讀檔：AP 2・耐力 10／8、AP 1・法力 5） |
| 守印人前兩句 | 「醒了？…」「這裡是工坊靶場。…先挑一條路。」 | 台詞檔 `range.intro` 1、2 |
| 守印人第三句（選了才出現，淡金色） | 「手上這套是借你的。等你摸清路數，葛蘭會幫你換上真正順手的。」 | 台詞檔「入門配備是借的」 |
| 一句定位「貼身打／遠遠射／施法」 | 取自守印人第 2 句 | 台詞檔 |
| 招式說明句、「入門配備是借的，之後會換成你自己的。」、沙盒說明、確認列文字、按鈕字 | **樣張暫寫**，待玩法 PM 定 | 見第 5 節 |

### 1.2 每個元素的畫法

| 元素 | 畫法 |
|---|---|
| 背景 | `WorldPaintedArt.drawBackdrop`（入口畫面的浮島天空，和現行靶場同） |
| 標題牌、每一塊框 | 現行 `EntryPlaque`／`EntryPanel` 的 class（`ui-popup rt-frame ui-popup-inline entry-panel`） |
| 守印人頭像 | `QPortrait.portrait`（`seal_keeper`），桌機 64、手機 48 |
| 卡上的人物 | `QDoll.stamp` 正面，拿入門武器；框是現行的 `.range-preview-slot`（虛線框＋紫光） |
| 武器圖示 | `GearArt.draw` 40px |
| 招式圖示 | `SkillIcon.draw` 40px（規格照 `tools/export_skills.py` 的格式，內容讀自 `content/skills`；`skillsData.js` 缺其中 4 招，所以寫在 `obSamples.js` 的 `SKILL`） |
| 按鈕 | 現行 `.entry-skin button`、`.primary`、`.selected`、`.entry-create-go` |

**新畫的元素（都是排版，沒有新圖）**：大類卡 `ob-class-card` 的三種狀態、「借」小牌 `ob-loan`、裝備列 `ob-kit-row`、守印人台詞旁放頭像的排法 `ob-speaker`、確認列 `ob-confirm`。

### 1.3 我看到

- `shots/ob/class-1280-none.png`：三張卡等高並排，邊框一樣是金色細框；確認列左邊灰字「先選一條路，才能出發…」，右邊「先離開（下次回到靶場）」和灰掉的「確定出發」，都在框內。守印人只有兩句。
- `shots/ob/class-1280-hover.png`：近戰卡整張往上浮 3px（卡頂比另外兩張高一點），邊框變亮金、外面多一圈細亮邊；其他不變。特寫 `closeup/ob/class-card-hover-2x.png`。
- `shots/ob/class-1280-selected.png`：遠程卡亮金粗框＋外光、上半部底色轉藍、標題變金色、右上角金底「✓ 已選」、人物框從虛線變實線、卡底按鈕變「已選這條路」（金框）。守印人多出第三句（淡金色）。確認列寫「已選：遠程　弓＋散彈驅離、壓制射擊。」，「確定出發」變藍色可按。特寫 `class-card-selected-2x.png`、`class-confirm-enabled-3x.png`。
- `closeup/ob/class-doll-melee-3x.png`：正面，右手（畫面左）握劍柄，護手在拳頭上方，劍尖朝上略偏左；左手垂在身側。
- `closeup/ob/class-doll-ranged-3x.png`：正面，弓橫在胸口前（定案的正面待機），一手握弓把在胸口正中，箭搭在弦上、箭頭朝畫面右下、箭羽在左肩上方；背上有箭袋的帶子。
- `closeup/ob/class-doll-focus-3x.png`：正面，右手握杖身中段，杖直立、杖尾落地，火球在杖頂、比頭高；火球外面有一圈暗紅色光暈（`QDoll` 原本的畫法）。
- `closeup/ob/class-kit-melee-3x.png`、`class-kit-ranged-3x.png`、`class-kit-focus-3x.png`：武器圖示清楚（劍、弓、頂端有火球的杖）。**瞬步背刺、散彈驅離、壓制射擊三個圖示幾乎一樣**（灰藍底、一道斜的白色流星），塔盾猛擊是一道白弧；火焰箭是橘紅底的火彈，火花連鎖是藍底的閃電折線。這是現行圖示的結果，沒有改。
- `closeup/ob/class-keeper-3x.png`：守印人頭像是兜帽、白鬍子的 Q 版臉，金色圓角框；三句台詞各一行。
- `shots/ob/class-390-none.png`、`class-390-selected.png`：三張卡直排；每張卡左邊是人物（約 104 寬）、右邊是武器與兩招；代價（AP・耐力）在手機寬不顯示；說明句會折成兩行。確認列在最下面，兩顆按鈕各佔一半。
- `shots/ob/class-390-selected-viewport.png`（390×844 一個畫面）：確認列黏在畫面底部，蓋在卡片上面，往下捲時一直看得到「確定出發」。特寫 `class-390-card-selected-3x.png`、`class-390-confirm-3x.png`。

### 1.4 和現行靶場畫面差在哪（對照 `shots/tr1/tr1_1600_rack.jpg`）

- 現行：左人物預覽、中武器架 21 把、右 12 個關鍵字。選大類：只有三張卡，沒有關鍵字欄。
- 守印人台詞旁多了頭像（現行只有文字）。
- 「確定出發」沿用同一顆按鈕與字（`CONFIRM_LABEL`）。
- **武器架沒有畫在這一頁**：21.5 第 9 點「架上全部武器都能試」。樣張每張卡有「拿起試打」（試該大類的入門配備）；要試其他武器的入口放哪裡沒有畫，見第 5 節。

## 2. 出發後的靶場入口（`ob-range-entry.html`）

### 2.1 主城工坊師傅的選單（`?part=master&state=normal｜hover`）

現行：工坊師傅點了只開說明卡（`content/world/fields/capital/capital.yaml` 的 `note_zh`「工坊還在整理。」），沒有選單，所以這是新面板。

| 元素 | 畫法 |
|---|---|
| 場景 | `TownTiles.plaza`／`stoneHall`（主城白石地磚、工坊）、三座武器架（`PaperDoll.drawWeapon`，照 `range.html`）、木樁、滑軌、水池（見第 4 節） |
| 工坊師傅、主角 | `QNpc.stamp`（`workshop_master`，側面朝東，手上鎚）、`QDoll.stamp`（側面朝西，單手劍） |
| 面板 | 現行大世界彈窗 `ui-popup rt-frame ui-popup-hud world-hud-panel`，寬 520，上緣 84；關閉鈕 `world-hud-panel-close`；標頭用郵差面板的 `mail-head`（頭像 56＋名字＋身分） |
| 頭像 | `QPortrait.portrait`（`workshop_master`） |
| 選單項目的小圖 | 靶場試玩＝木樁（同場上木樁的畫法縮小）；改造技能＝`GearArt.draw` 的鎚 |

**新畫的元素**：選單列 `ob-menu-item`（一般、滑過、停用）、金底「新」小牌、地名牌 `ob-place`。

我看到：
- `shots/ob/entry-master-1280-normal.png`：面板在畫面中上，兩列選單。第一列「靶場試玩〔新〕／用你現在的技能與裝備打木樁，看看打起來怎麼樣」，右邊一個「›」；第二列「改造技能／之後開放」整列變暗，右邊寫「還沒開放」。面板下面一行灰字說明測試模式。場景：左邊三座武器架（近戰、遠程、法器，各有小牌），左上藍屋頂的工坊（鐵砧招牌），右邊水池裡一個木樁、池外一個、下方滑軌上一個。面板沒有蓋到人物與木樁。
- `shots/ob/entry-master-1280-hover.png`：第一列底色變藍、亮金框，「›」變白；其他不變。特寫 `entry-master-panel-normal-3x.png`、`entry-master-panel-hover-3x.png`。
- `closeup/ob/entry-master-people-3x.png`：工坊師傅朝右，護目鏡推在額頭、大鬍子、皮圍裙，鎚子握在手上、鎚頭朝前上方；主角朝左，劍握在手上、劍尖朝前上方（朝向師傅那一側），兩人面對面。
- `closeup/ob/entry-master-dummies-2x.png`：三個木樁都是圓布頭（有兩道縫線）、麻布身（有橫向綁繩）、兩邊伸出的橫臂、細木樁、深色底座；滑軌是兩條灰鐵軌加一排直立的木枕；水池四邊是淺色石條，有接縫。
- `closeup/ob/entry-master-racks-2x.png`：近戰架上是劍、斧、矛、鎚；遠程架是弓、弩、手槍（弓和弩疊在一起）；法器架是兩支杖和一顆球。和 `shots/misc/range.png` 同一畫法。
- `shots/ob/entry-master-390-normal.png`、`entry-master-390-hover.png`：面板寬度貼齊螢幕（左右各留 8），說明句折成兩行；場景放大，只看得到師傅、主角和一部分木樁。

### 2.2 葛蘭開的「正式選定」畫面與試打入口（`?part=gran`）

整張面板蓋在霧渡鎮導師堂上面（四角是雲嶺的雲紋飾件），內容照現行靶場 `RangeScreen` 的三欄（左預覽、中武器架、右關鍵字），最上面是葛蘭的兩句台詞。

- **結論：試打入口不用新位置**。① 武器卡下面的「拿起試打」、② 每個關鍵字右邊的「看示範」，位置都和現行靶場一樣；葛蘭畫面與主城靶場是同一個元件。樣張上用金色圓圈 1、2 標出，面板下方虛線以下是標號說明（不是遊戲畫面）。
- 畫法：人物 `QDoll.stamp`、葛蘭頭像 `QPortrait.portrait`（`gran`，綠框）、武器鈕上的小圖 `GearArt.draw` 26px、關鍵字小圖照 `range.html` 那一組、背景 `TownTiles.room` 與書架、燭台（照 `gran-doll.html`）。
- **新畫的元素**：金底「推薦」小牌 `ob-rec`、標題列「正式選定」、標號圓圈。
- 關鍵字名稱與弓的起始技能名照現行畫面（`shots/tr1/tr1_1600_rack.jpg`）。「推薦」標在倒地、撞擊，以及那一行觸發關係，是**示意**，不是照規則算出來的。

我看到：
- `shots/ob/entry-gran-1280.png`：面板幾乎佔滿畫面，導師堂只在面板上方露出一條，**背景幾乎看不到**。左欄主角拿弓；中欄 21 把武器鈕（弓亮起）與武器卡，卡底藍色「拿起試打」右邊是圓圈 1；右欄 12 個關鍵字，倒地、撞擊兩列亮起、右側有金底「推薦」，每列右邊一顆「看示範」，第一列的「看示範」左邊是圓圈 2（壓在點燃那一列的右端）。右下「之後再選」「確定選這套」。
- `closeup/ob/entry-gran-head-3x.png`：葛蘭白髮白鬍、臉上有疤，綠色框；左上角是紅點加綠色雲紋的飾件。
- `closeup/ob/entry-gran-try-3x.png`、`entry-gran-keywords-3x.png`、`entry-gran-actions-3x.png`、`entry-gran-preview-3x.png`：按鈕與標號清楚。
- `closeup/ob/entry-gran-racks-3x.png`：26px 的武器小圖看得出劍、斧、矛、鐮刀、鞭；**單手劍、雙手劍、魔導劍三個幾乎一樣，鎚像釘頭鎚，拳套像一根尖刺**（現行 `GearArt` 小圖的結果）。
- `shots/ob/entry-gran-390.png`：三欄直排成一欄，很長（約 1900 高）；「拿起試打」在武器架下面，要捲過 21 把武器才看得到。

## 3. 測試模式戰鬥版面（`practice-battle.html`，#147）

`?mode=practice｜current`、`?view=compare`。場景：主角拿弓，選了普攻，游標在滑軌木樁上。

### 3.1 和現行戰鬥版面差在哪（`shots/ob/practice-compare.png`，左右並排、同一個場景）

| # | 位置 | 現行 | 測試模式 |
|---|---|---|---|
| 1 | 上方中央 | 行動順序列 | 拿掉；同一個位置放一條提示：「測試模式」徽章＋「每次出手後自動過一輪，資源立刻補滿，木樁不會倒」 |
| 2 | 右下 | 「結束回合」大按鈕 | 拿掉；同一格放「離開靶場」（一般按鈕色、矮一點、前面是現行的離開圖示） |
| 3 | 左側預覽 | 命中照實際機率 | 命中寫綠色粗體 100%；下面多一行淡金色「靶場木樁必中，實戰會有失手」（21.5 指定的句子） |
| 4 | 右上戰況 | 輪數＋勝利條件圖示 | 輪數留著；勝利條件換成「沙盒・不算勝負」 |
| 5 | 技能列 | 代價後面有「・冷卻 N 回合」；提示寫「點選紅框敵人攻擊（3 個）」 | 不寫冷卻；提示改「點選紅框的木樁出手」 |

沒變：主角卡、工具鈕（含右上角的離開圖示）、戰鬥紀錄、縮放、移動／普攻／跑步／守護、更多動作、播放速度、上方可關閉的「靶場試打：弓＋…」訊息。

實機的現行靶場試打畫面是 `shots/tr1/tr1_1600_trial.jpg`；樣張的 HUD 和它是同一份 CSS。兩者不同的地方：實機的木樁目前是戴紅帽的人形、地圖是技能工坊的靶場圖；樣張照 `靶場移植需求.md` 畫木樁、滑軌、水池。

### 3.2 每個元素的畫法

| 元素 | 畫法 |
|---|---|
| 地磚、牆、水面 | `CUR.drawTile`（現行戰場畫法的打包，`current.js`）：石地、最上一排牆、2×2 水面 |
| 主角 | `QDoll.stamp` 側面朝東；腳下藍色橢圓、白色朝向箭頭、綠色 HP 條（照現行戰場） |
| 木樁、滑軌、水池石緣 | 見第 4 節 |
| 可攻擊目標 | 紅色圓角框；游標所在的那個加粗、框內淡紅 |
| HUD | 現行 class：`hero-card … panel hud`、`stat-bar`、`stat-chip`、`mode-panel`＋`preview-box`、`bhud-status`、`battle-top-tools`＋`bhud-tool`、`skill-bar`＋`skill-button`、`turn-controls`＋`resident-button`、`speed-control`、`log-dock`、`zoom-controls`、`notice-banner` |
| HUD 小圖示 | SVG 路徑原樣取自 `ui/SkillCardGlyphs.tsx`、`ui/StatusCardParts.tsx`、`ui/BattleToolIcons.tsx`、`ui/BattleLogDock.tsx` |
| 主角頭像 | `QPortrait.portrait` |
| 「測試模式」徽章 | 現行 `test-mode-badge`（`TestModeBadge.tsx`） |

**新畫的元素**：提示條 `ob-practice-bar`、「離開靶場」按鈕 `ob-leave`、「沙盒・不算勝負」小牌 `ob-sandbox-tag`、預覽裡的 100% 與必中那一行（`ob-sure`、`ob-sure-note`）、**整個手機寬版面**（`ob-phone`）。

### 3.3 我看到

- `shots/ob/practice-1280.png`（1280×720）：戰場在中間，12×8 格；最上一排是磚牆。主角在左中，朝右，手上有弓。滑軌在上方偏右，軌上一個木樁（紅框加粗、框內淡紅）；右邊 2×2 藍色水池、四邊石條，木樁站在水池右下那一格；左下一個普通木樁。三個木樁都有紅框、沒有血條。上方中央是提示條；其下是可關閉的訊息。左上主角卡、其下「普攻」面板（預覽：命中 100%　暴擊 5%　傷害 3–10）；右上地點與「第 3 輪」「沙盒・不算勝負」、六個工具鈕；左下三行紀錄；右下縮放；底部技能列（兩招，只寫 AP 2・耐力 8）與回合操作（四顆常駐鈕、「離開靶場」、更多動作、播放）。沒有行動順序列，沒有「結束回合」。
- `shots/ob/practice-1280-current.png`：同一場景；上方中央是 A、a、b、c 四顆行動順序章；預覽寫命中 75%；右上是輪數加交叉劍圖示；技能列有「・冷卻 3 回合」；右下有藍色「結束回合」大按鈕。
- `closeup/ob/practice-hero-preview-3x.png`：主角卡頭像、三條、四個圖示（AP 四顆亮、移動 5、反應、源力 1 亮 2 暗）；預覽第一行在卡寬內折成兩行（「傷害」後面換行）。
- `closeup/ob/practice-topbar-3x.png`、`practice-status-3x.png`、`practice-bottom-3x.png`、`practice-log-zoom-2x.png`：字都沒有被截斷；「離開靶場」和「更多動作」同寬、比上面四顆矮一點、不是藍色。
- `closeup/ob/practice-board-hero-3x.png`：主角側面朝右，持弓手在身前握弓把，箭搭在弦上、箭頭朝右（朝外），箭袋在背後；腳下藍圈，右邊白色小三角。
- `closeup/ob/practice-board-dummies-3x.png`：木樁底座落在格子下緣，頭頂沒有超出格子上緣太多；游標所在的木樁身上蓋了一層淡紅。水面和石緣之間露出一小圈地磚（水面是現行畫法的圓角）。
- `closeup/ob/practice-current-top-3x.png`、`practice-current-bottom-3x.png`：對照用。
- `shots/ob/practice-390.png`（390×844）：由上到下一欄——主角卡（三條排成一列＋圖示）→ 地點與輪數、工具鈕 → 提示條 → 戰場（整張地圖縮到 61%，一格約 32px）→ 普攻預覽 → 空白 → 技能列（兩招並排）→ 回合操作。全部在一個畫面內。手機版沒有畫紀錄、縮放、上方訊息。特寫 `practice-390-top-3x.png`、`practice-390-board-3x.png`、`practice-390-bottom-3x.png`。

## 4. 木樁、滑軌、水池（照 `靶場移植需求.md` 第 2 節）

- **木樁**：`range.html`（#134 已定案）的 `dummy()` 原樣搬到 `obSamples.js`：底座、木樁、橫臂、麻布身、布頭；被打中閃白的參數留著，樣張沒有用。三種的差別在站的地方：滑軌上、水池裡、平地。
- **滑軌**：同 `range.html` 的畫法（兩條鐵軌加枕木），枕木改成方角（`ink` 的 `sharp`），放大後不會像一排橢圓。
- **水池石緣**：`range.html` 是一整圈圓角；戰場上放大後像一團，所以改成四條方角石條加接縫短線，同一套 `StoryDoll.H.ink`／`stroke`。**這是和已定案樣張不同的地方**，請美術 PM 看 `closeup/ob/practice-board-dummies-3x.png` 決定要不要。
- 木樁沒有血條、沒有陣營圈（照移植需求「沒有血條」）。

## 5. 還沒定的事

### 給玩法 PM

1. **文字待定**（樣張暫寫）：六招的一句說明、卡底「入門配備是借的，之後會換成你自己的。」、「選這條路／已選這條路」、確認列兩句、沙盒說明、工坊師傅選單的項目名與說明、葛蘭畫面的「之後再選」「確定選這套」「正式選定」、測試模式提示句「每次出手後自動過一輪，資源立刻補滿，木樁不會倒」、「沙盒・不算勝負」。
2. **入門武器下三招只剩傷害**（盤點第 0 節：塔盾猛擊的倒地、散彈驅離的推開、壓制射擊的緩速都綁別的武器）。樣張的說明句因此只寫「傷害高」，兩招看起來一樣。要不要換招或放寬，由玩法 PM 定。
3. **工坊師傅沒有台詞**。台詞檔的「出發後回靶場」是守印人說的，但 21.5 定的入口在工坊師傅；樣張的師傅面板沒有放台詞。要補一句師傅的話，或把那句改給師傅。
4. **項目名**：樣張用「靶場試玩」（`capital.yaml` 與 21.5 現有的說法）；派工單寫的是「靶場試招」。
5. **`newcomer.yaml` 的 `range.intro`、`range.done` 還是舊句**，和台詞檔不同（樣張照台詞檔）。
6. 「推薦」標哪兩個、觸發關係那一行，樣張是示意。

### 給美術 PM／開發 PM

7. **選大類時怎麼試其他武器**：21.5 第 9 點說架上全部都能試；樣張只有每張卡的「拿起試打」。選項：卡片下面加一顆「打開武器架」，或三張卡各自展開該大類的武器。
8. **「離開靶場」放在原本「結束回合」那一格**：好處是不用多找位置；風險是打慣實戰的人順手按到。另一做法是只留右上角的離開圖示，那一格空著。
9. **輪數要不要留**：樣張留著（狀態的剩餘回合看它）。
10. **測試模式要不要寫冷卻**：樣張不寫。寫的話可以教玩家實戰的冷卻。
11. **手機寬的戰鬥版面是新提案**：現行戰鬥 HUD 在 900 以下是左欄 230、右欄 210，沒有 390 的排法。樣張的一欄排法只為這次出圖，要不要照做、其他戰鬥要不要一起改，由開發 PM 與美術 PM 定。
12. **葛蘭畫面是整頁還是蓋在導師堂上**：盤點說後兩種模式「不能佔住整個世界畫面」。樣張畫成蓋在導師堂上的大面板，但面板幾乎佔滿畫面。
13. **守印人、葛蘭台詞旁加頭像**是樣張多的，現行靶場只有文字。
14. 水池石緣改方角（第 4 節）。

### 圖示（不在這次範圍，記給「墨線圖示改 Q 版」那一項）

15. 瞬步背刺、散彈驅離、壓制射擊三個技能圖示幾乎一樣；單手劍、雙手劍、魔導劍的小圖幾乎一樣；鎚像釘頭鎚、拳套像尖刺。

## 6. 給開發移植的重點

| 項目 | 元件 | 尺寸與 class |
|---|---|---|
| 選大類 | `RangeScreen` 的 `pick_class` 模式 | 三欄 `repeat(3, 1fr)`、間距 14；< 1040 改一欄，卡內改成「人物 104 ＋ 內容」兩欄；人物框高 168（窄版最少 132）；圖示 40；卡片內距 14×18；滑過上浮 3px；已選＝亮金 2px 外框＋外光 |
| 確認列 | 同頁最下面一塊 `EntryPanel` | 兩欄 `minmax(0,1fr) auto`；≤ 560 改一欄並黏在底部（`position: sticky; bottom: 6px`）；「確定出發」`min-width` 要寫死（樣張 220）：現行的 `min(260px, 100%)` 放在 `auto` 欄會被算成 0，按鈕會凸出框外 |
| 工坊師傅選單 | 新面板，接 `objectHud` 的 `panel` | `world-hud-panel` 寬 520；標頭 `mail-head`；選單列高約 58、圖 40、標題 15px、說明 12.5px |
| 葛蘭畫面 | `RangeScreen` 的正式選定模式 | 版面照現行三欄；加「推薦」小牌（金底深字 11px）；試打入口不動 |
| 測試模式 | `BattleScreen` 依 `view.practice` | `.bhud-top` 不放 `TurnBar`，改放提示條（同 HUD 框，內距 6×12，13px）；`TurnControls` 不放 `end-turn-button`，改放 `resident-button`（`grid-column: 1 / -1`、高 34）；`PreviewBox` 加一行；`BattleStatusBox` 的勝利條件換成小牌；`costParts` 不出冷卻 |

截圖指令（無頭 Chrome；`ob-frame.html` 用 iframe 給準確的版面寬，視窗大小先用 `--dump-dom` 讀 `<html data-w data-h>`）：

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --mute-audio --no-first-run \
  --user-data-dir=<暫存>/chrome-profile --allow-file-access-from-files --hide-scrollbars --virtual-time-budget=12000 \
  --window-size=<data-w>,<data-h> --screenshot=<輸出.png> \
  "file:///<worktree>/docs/art/sample/tools/ob-frame.html?src=<encodeURIComponent(樣張頁?參數)>&w=390&h=auto&z=3&sel=<選擇器>&n=0&pad=6"
```

同一個 `--user-data-dir` 不能同時跑兩個 Chrome（後開的那個不會存圖）。

## 7. 自查

- 幾何占位：沒有。圓形只用在樣張標號（1、2…）與現行的 AP／源力圓點。
- 人物朝向：正面三張、側面朝東（戰場主角、工坊師傅）、側面朝西（師傅前的主角）都看過 3 倍特寫，握把在手、作用端朝外。導師堂的葛蘭與主角被面板蓋住，看不到，沒有檢查。
- 和已定案並排：場景對 `shots/misc/range.png`（同一套地磚、武器架、木樁）；HUD 對 `shots/tr1/tr1_1600_trial.jpg`、`shots/tr1/tr1_1600_rack.jpg`。
- 沒有逐張打開的截圖：`class-390-selected.png`（看過改版前的同一張與一個畫面版）、`entry-master-390-hover.png`（看過改武器前的同一張）、`entry-gran-1280.png`（看過加關閉鈕定位後的同一版）、`class-card-none-2x.png`、`class-confirm-enabled-3x.png`、`entry-master-panel-normal-3x.png`。
- 已知小問題：測試模式的操作提示寫「點選藍色格子移動」，但樣張畫的是普攻模式，場上沒有藍色格子；手機寬的葛蘭畫面太長。
