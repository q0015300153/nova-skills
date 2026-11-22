// Usage: node ensure-browser.mjs [startUrl]
// Detects a CDP-enabled browser on 127.0.0.1:$CDP_PORT (default 9222).
// If none, launches a dedicated-profile Chromium browser and waits for it. Also ensures `ws` is installed.
// Env: CDP_PORT, NOVA_GHOST_PROFILE (profile dir), NOVA_GHOST_BROWSER (browser executable path)
import fs from 'fs';
import os from 'os';
import path from 'path';
import { spawn, execSync } from 'child_process';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';

const PORT = process.env.CDP_PORT || 9222;
const PROFILE = process.env.NOVA_GHOST_PROFILE || path.join(os.homedir(), '.nova-ghost', `profile-${PORT}`);
const base = `http://127.0.0.1:${PORT}`;
const here = path.dirname(fileURLToPath(import.meta.url));
const out = o => console.log(JSON.stringify(o, null, 2));

const probe = async () => { try { const r = await fetch(`${base}/json/version`, { signal: AbortSignal.timeout(1500) }); return r.ok ? await r.json() : null; } catch { return null; } };

// 1. ws dependency (needed by cdp.mjs)
try { createRequire(path.join(here, 'x.js')).resolve('ws'); }
catch { try { execSync('npm install ws --no-save --no-audit --no-fund', { cwd: here, stdio: 'ignore' }); } catch { out({ status: 'error', step: 'install-ws', hint: `run: cd "${here}" && npm install ws` }); process.exit(1); } }

// 2. already running?
let v = await probe();
let launched = false;
if (!v) {
  // 3. find a browser
  const home = os.homedir(), env = process.env;
  const w = (k, ...p) => env[k] ? path.join(env[k], ...p) : '';
  const cands = process.platform === 'win32' ? [
    w('ProgramFiles', 'Google', 'Chrome', 'Application', 'chrome.exe'), w('ProgramFiles(x86)', 'Google', 'Chrome', 'Application', 'chrome.exe'),
    w('LOCALAPPDATA', 'Google', 'Chrome', 'Application', 'chrome.exe'), w('ProgramFiles(x86)', 'Microsoft', 'Edge', 'Application', 'msedge.exe'), w('ProgramFiles', 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
  ] : process.platform === 'darwin' ? [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge', '/Applications/Chromium.app/Contents/MacOS/Chromium',
  ] : ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge'].map(n => { try { return execSync(`command -v ${n}`, { encoding: 'utf8' }).trim(); } catch { return ''; } });
  const exe = process.env.NOVA_GHOST_BROWSER || cands.find(p => p && fs.existsSync(p));
  if (!exe) { out({ status: 'error', step: 'find-browser', hint: 'No Chrome/Edge/Chromium found. Install one or set NOVA_GHOST_BROWSER to its path.' }); process.exit(1); }
  fs.mkdirSync(PROFILE, { recursive: true });
  const args = [`--remote-debugging-port=${PORT}`, '--remote-debugging-address=127.0.0.1', `--user-data-dir=${PROFILE}`, '--no-first-run', '--no-default-browser-check'];
  if (process.argv[2]) args.push(process.argv[2]);
  spawn(exe, args, { detached: true, stdio: 'ignore' }).unref();
  launched = true;
  for (let i = 0; i < 30 && !v; i++) { await new Promise(r => setTimeout(r, 500)); v = await probe(); }
  if (!v) { out({ status: 'error', step: 'wait-port', hint: `Port ${PORT} did not open. If a browser already uses this profile or port, close it or set CDP_PORT / NOVA_GHOST_PROFILE.`, profile: PROFILE }); process.exit(1); }
}

// 4. report
const tabs = (await (await fetch(`${base}/json/list`)).json()).filter(p => p.type === 'page').map(p => ({ id: p.id.slice(0, 4), title: p.title, url: p.url }));
out({ status: launched ? 'launched' : 'ready', port: Number(PORT), browser: v.Browser, profile: PROFILE, tabs,
  note: launched ? 'Fresh dedicated profile: the human must sign in to any sites needed (never hand over passwords/MFA).' : 'Reusing the existing debug browser.' });
