# AI 操作瀏覽器：通用安裝與操作指南

目的：讓任何 AI 助理（或人）能在使用者**已登入的瀏覽器**中讀取畫面、點擊、輸入、截圖、執行頁面腳本。本文不含任何組織或帳號資訊，可直接公開使用。

## 1. 運作原理

Chrome／Edge（Chromium 系）可開啟「遠端除錯埠」，外部程式透過 Chrome DevTools Protocol（CDP，WebSocket + JSON）控制分頁。

```
AI（執行 shell 指令）→ cdp.mjs（Node）→ ws://127.0.0.1:9222 → 瀏覽器分頁
```

優點：沿用使用者已登入的工作階段，不需要處理密碼或 MFA；AI 只做「人手能做的操作」。

## 2. 需要安裝的元件

| 元件 | 用途 | 備註 |
|---|---|---|
| Chromium 系瀏覽器（Chrome、Edge） | 被控制的對象 | 需能加啟動參數 |
| Node.js 18 以上 | 執行控制腳本；內建 `fetch` | `node -v` 檢查 |
| npm 套件 `ws` | WebSocket 連線 | `npm install ws` |
| bash 或任何可執行指令的環境 | AI 呼叫腳本、`curl` 查分頁 | Windows 可用 Git Bash |
| （選用）截圖檢視能力 | AI 需能看 PNG | 多數 AI 編碼工具內建 |

不需要 Selenium、Playwright、ChromeDriver。

## 3. 安裝步驟

```bash
mkdir browser-ctl && cd browser-ctl
npm init -y
npm install ws
# 並在 package.json 加入 "type": "module"（使用 .mjs 可省略）
# 將第 6 節的 cdp.mjs 存到此資料夾
```

## 4. 啟動瀏覽器（含除錯埠）

**務必使用獨立的使用者資料夾**（新版 Chrome 對預設資料夾會忽略除錯埠），並只綁定本機。

Windows：
```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1 --user-data-dir="%USERPROFILE%\chrome-ctl-profile"
```
macOS：
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-ctl-profile"
```
Linux：
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-ctl-profile"
```

接著由**人**在該視窗登入需要的網站（密碼與 MFA 不交給 AI）。

驗證：
```bash
curl -s http://127.0.0.1:9222/json/version   # 有 JSON 即成功
curl -s http://127.0.0.1:9222/json           # 列出所有分頁（id、url、title）
```

需要同時用多個帳號時：再開一個**不同 `--user-data-dir` 與不同埠**（如 9223）的瀏覽器，或使用無痕視窗（同一埠，分頁各自獨立工作階段）。

## 5. 安全注意事項

- 除錯埠等同「完全控制該瀏覽器」：只綁 `127.0.0.1`，不要對外開放或做埠轉發。
- 使用獨立 profile，避免控制到日常個人帳號。
- 不要讀取、列印或儲存 cookie、權杖、密碼。
- 只在**已獲授權**的網站與帳號上操作；刪除、付款、對外分享、變更權限等不可逆動作先問使用者。
- 作業完成後關閉該瀏覽器或結束除錯埠。

## 6. 控制腳本 `cdp.mjs`

```js
// 用法：node cdp.mjs <指令> [參數]
// 選分頁：環境變數 CDP_TAB=<分頁id前綴> 或 CDP_MATCH=<網址片段>；皆未設則取第一個分頁
import fs from 'fs';
import ws from 'ws';
const WebSocket = ws.default || ws;
const [, , cmd, ...args] = process.argv;
const PORT = process.env.CDP_PORT || 9222;

const pages = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).filter(p => p.type === 'page');
const T = process.env.CDP_TAB, M = process.env.CDP_MATCH;
const page = T ? pages.find(p => p.id.startsWith(T)) : M ? pages.find(p => p.url.includes(M)) : pages[0];
if (!page) { console.error('找不到分頁'); process.exit(1); }

const sock = new WebSocket(page.webSocketDebuggerUrl);
await new Promise(r => sock.on('open', r));
let id = 0; const pending = new Map();
sock.on('message', d => { const m = JSON.parse(d); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); sock.send(JSON.stringify({ id: i, method, params })); });
const keyCodes = { Enter: 13, Tab: 9, Escape: 27, Backspace: 8, ArrowDown: 40, ArrowUp: 38, PageDown: 34, Home: 36 };
const ctrl = async (key, code, vk) => { for (const type of ['keyDown', 'keyUp']) await send('Input.dispatchKeyEvent', { type, key, code, windowsVirtualKeyCode: vk, modifiers: 2 }); };

try {
  if (cmd === 'eval' || cmd === 'evalfile') {            // 在頁面執行 JS（可 await）
    const expression = cmd === 'eval' ? args[0] : fs.readFileSync(args[0], 'utf8');
    const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (r.result?.exceptionDetails) console.error('ERR', JSON.stringify(r.result.exceptionDetails.exception?.description));
    else { const v = r.result.result.value; console.log(typeof v === 'string' ? v : JSON.stringify(v, null, 2)); }
  } else if (cmd === 'shot') {                           // 截圖存檔
    const r = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(args[0], Buffer.from(r.result.data, 'base64')); console.log('saved', args[0]);
  } else if (cmd === 'click' || cmd === 'dblclick') {    // 座標點擊（CSS 像素）
    const [x, y] = args.map(Number); const n = cmd === 'dblclick' ? 2 : 1;
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
    for (let c = 1; c <= n; c++) for (const type of ['mousePressed', 'mouseReleased'])
      await send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: c });
    console.log(cmd, x, y);
  } else if (cmd === 'type') { await send('Input.insertText', { text: args[0] }); console.log('typed'); }
  else if (cmd === 'typefile') { await send('Input.insertText', { text: fs.readFileSync(args[0], 'utf8') }); console.log('typed file'); }
  else if (cmd === 'key') {                              // 單一按鍵
    for (const type of ['keyDown', 'keyUp']) await send('Input.dispatchKeyEvent', { type, key: args[0], code: args[0], windowsVirtualKeyCode: keyCodes[args[0]] });
    console.log('key', args[0]);
  } else if (cmd === 'selectall') { await ctrl('a', 'KeyA', 65); console.log('selectall'); }
  else if (cmd === 'paste') { await ctrl('v', 'KeyV', 86); console.log('paste'); }
  else if (cmd === 'scroll') {                           // scroll x y deltaY
    const [x, y, dy] = args.map(Number);
    await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x, y, deltaX: 0, deltaY: dy }); console.log('scrolled', dy);
  } else if (cmd === 'dialog') {                         // 處理 alert/confirm/beforeunload
    await Promise.race([send('Page.enable'), new Promise(r => setTimeout(r, 1500))]);
    console.log(JSON.stringify(await send('Page.handleJavaScriptDialog', { accept: args[0] !== 'dismiss' })));
  } else if (cmd === 'navigate') { await send('Page.navigate', { url: args[0] }); console.log('navigated'); }
  else if (cmd === 'front') { await send('Page.bringToFront'); console.log('brought to front'); }  // 僅在需要時：把分頁/視窗切到最前面
  else console.error('未知指令', cmd);
} finally { sock.close(); }
```

開新分頁：`curl -s -X PUT "http://127.0.0.1:9222/json/new?https://example.com"`（部分版本用 GET）。
切到前景（一般不需要，僅在內容無法載入／截圖空白／讀取逾時時使用）：`node cdp.mjs front`（`Page.bringToFront`，連視窗一起拉到最前），或 `curl -s http://127.0.0.1:9222/json/activate/<分頁完整id>`（只切分頁）。

## 7. 指令速查

| 指令 | 範例 |
|---|---|
| 列分頁 | `curl -s localhost:9222/json` |
| 執行 JS | `CDP_TAB=AB12 node cdp.mjs eval "document.title"` |
| 截圖 | `rm -f s.png; node cdp.mjs shot s.png` |
| 點擊 | `node cdp.mjs click 320 240` |
| 輸入 | `node cdp.mjs type "hello"`、長文用 `typefile` |
| 按鍵 | `node cdp.mjs key Enter` |
| 全選後覆寫 | `selectall` → `typefile` |
| 滾動 | `node cdp.mjs scroll 400 400 600` |
| 處理對話框 | `node cdp.mjs dialog accept` |
| 前往網址 | `node cdp.mjs navigate https://example.com` |
| 切到最前面（僅必要時） | `node cdp.mjs front` |

## 8. AI 標準工作迴圈

1. **看**：`shot` 截圖＋`eval` 讀 DOM 文字，確認目前頁面與登入身分。
2. **做**：一次只做一個動作（點擊、輸入、導覽）。
3. **驗**：再截圖或讀 DOM，確認動作生效，再進下一步。
4. 遇登入、MFA、驗證碼、權限同意：停下請使用者處理。
5. 遇不可逆動作或被安全機制擋下：停下詢問，不要繞過。

## 9. 操作技巧與常見問題

| 問題 | 做法 |
|---|---|
| 點擊位置偏掉 | 截圖像素 ÷ `devicePixelRatio`（常見 1.25、2）才是 `click` 座標；用 `eval "devicePixelRatio"` 查 |
| 截圖沒更新 | 腳本失敗時可能沿用舊檔；截圖前先 `rm` |
| 指令逾時／內容空白 | 分頁在背景被節流：先 `node cdp.mjs front`（或 `activate`）再重試；加 `timeout 40` 避免卡死 |
| 點不到按鈕 | 優先用 DOM：`eval "[...document.querySelectorAll('button')].find(b=>b.textContent.includes('送出')).click()"` |
| 輸入沒反應 | 先點欄位取得焦點；`selectall` 後再 `type`；React／Monaco 編輯器用 `typefile`／`paste` 較穩 |
| 元素在 iframe | `eval` 只看得到同源 iframe；跨網域 iframe 改用座標點擊與 `key` |
| 跳出 alert 後所有指令失效 | 先 `dialog accept` 或 `dismiss` |
| 頁面有未儲存變更 | 不要重新整理或換頁，否則會卡在離開確認 |
| 下拉選單、彈出層 | 常在 DOM 末端，用文字搜尋再 `.click()` |
| 讀取結構化資料 | 同源 `fetch` 唯讀 API 比解析畫面可靠；寫入仍建議走介面 |
| 分頁 id 變了 | 關閉分頁後重新 `curl /json` |
| 看不到除錯埠 | 確認用了獨立 `--user-data-dir`、完全關閉舊的 Chrome 程序後再啟動 |

## 10. 疑難排解

- `fetch failed`／連不上：瀏覽器沒用除錯參數啟動，或埠被占用（換 9223 並設 `CDP_PORT`）。
- 找不到分頁：`CDP_TAB` 前綴打錯，或分頁已關閉。
- `Input.insertText` 無效：目標未取得焦點。
- 企業電腦若禁止除錯埠：需向管理者確認政策，不要規避。

## 11. 擴充方向

- 加入 `waitFor`（輪詢 DOM 條件）減少固定等待。
- 對 `Network.enable` 監聽請求，除錯時觀察 API 呼叫（注意不要記錄敏感標頭）。
- 改用 Playwright 的 `connectOverCDP` 取得更高階 API，同一個除錯埠即可連線。
