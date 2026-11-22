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
  else console.error('未知指令', cmd);
} finally { sock.close(); }
