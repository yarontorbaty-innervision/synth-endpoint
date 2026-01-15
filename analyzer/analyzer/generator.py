"""
Electron app generator - Python interface.

Generates Electron apps from workflow definitions.
"""

from __future__ import annotations
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def generate_electron_app(
    workflow_path: Path,
    output_dir: Path,
    install_deps: bool = True
) -> Path:
    """
    Generate an Electron app from a workflow definition.
    
    Args:
        workflow_path: Path to workflow JSON file
        output_dir: Directory to generate app in
        install_deps: Whether to run npm install
        
    Returns:
        Path to generated app directory
    """
    # Load workflow
    with open(workflow_path) as f:
        workflow = json.load(f)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate using Python (simpler than calling TypeScript)
    generator = PythonAppGenerator(workflow, output_dir)
    generator.generate()
    
    # Install dependencies
    if install_deps:
        print("📦 Installing dependencies...")
        subprocess.run(
            ["npm", "install"],
            cwd=output_dir,
            capture_output=True
        )
    
    print(f"✅ App generated: {output_dir}")
    return output_dir


class PythonAppGenerator:
    """Pure Python Electron app generator."""
    
    def __init__(self, workflow: dict, output_dir: Path):
        self.workflow = workflow
        self.output_dir = output_dir
        
    def generate(self) -> None:
        """Generate all app files."""
        self._create_dirs()
        self._write_package_json()
        self._write_main_js()
        self._write_index_html()
        self._write_renderer_js()
        self._write_styles_css()
        self._write_workflow_json()
        
    def _create_dirs(self) -> None:
        (self.output_dir / "src" / "main").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "src" / "renderer").mkdir(parents=True, exist_ok=True)
        
    def _write_package_json(self) -> None:
        name = self.workflow.get("name", "app").lower()
        name = "".join(c if c.isalnum() else "-" for c in name).strip("-")
        
        pkg = {
            "name": name,
            "version": "1.0.0",
            "description": self.workflow.get("description", "Generated app"),
            "main": "src/main/index.js",
            "scripts": {"start": "electron ."},
            "dependencies": {"electron": "^28.0.0"}
        }
        
        (self.output_dir / "package.json").write_text(json.dumps(pkg, indent=2))
        
    def _write_main_js(self) -> None:
        start_screen = self.workflow.get("start_screen_id") or \
                       (self.workflow["screens"][0]["id"] if self.workflow.get("screens") else "screen_1")
        
        code = f'''const {{ app, BrowserWindow, ipcMain }} = require('electron');
const path = require('path');
const http = require('http');

let mainWindow;
let controlServer;
let currentScreen = '{start_screen}';
const pendingResponses = new Map();
let responseId = 0;

function createWindow() {{
  mainWindow = new BrowserWindow({{
    width: 1200, height: 800, x: 100, y: 100,
    webPreferences: {{ nodeIntegration: true, contextIsolation: false }},
    title: '{self.workflow.get("name", "App")}'
  }});
  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  startControlServer();
}}

function startControlServer() {{
  controlServer = http.createServer(async (req, res) => {{
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');
    const url = new URL(req.url, 'http://localhost');
    
    if (req.method === 'GET' && url.pathname === '/status') {{
      res.end(JSON.stringify({{ screen: currentScreen, window: mainWindow?.getBounds(), ready: true }}));
      return;
    }}
    if (req.method === 'GET' && url.pathname === '/elements') {{
      const id = ++responseId;
      const timeout = setTimeout(() => {{ pendingResponses.delete(id); res.end(JSON.stringify({{ elements: {{}} }})); }}, 3000);
      pendingResponses.set(id, {{ resolve: (d) => res.end(JSON.stringify(d)), timeout }});
      mainWindow.webContents.send('get-elements', id);
      return;
    }}
    if (req.method === 'POST' && url.pathname.startsWith('/navigate/')) {{
      currentScreen = url.pathname.replace('/navigate/', '');
      mainWindow.webContents.send('navigate', currentScreen);
      res.end(JSON.stringify({{ success: true, screen: currentScreen }}));
      return;
    }}
    if (req.method === 'POST' && url.pathname === '/focus-window') {{
      mainWindow.show(); mainWindow.focus();
      res.end(JSON.stringify({{ success: true }}));
      return;
    }}
    if (req.method === 'POST' && url.pathname === '/reset') {{
      currentScreen = '{start_screen}';
      mainWindow.webContents.send('navigate', currentScreen);
      res.end(JSON.stringify({{ success: true, screen: currentScreen }}));
      return;
    }}
    if (req.method === 'POST' && url.pathname.startsWith('/highlight/')) {{
      mainWindow.webContents.send('highlight-element', url.pathname.replace('/highlight/', ''));
      res.end(JSON.stringify({{ success: true }}));
      return;
    }}
    res.statusCode = 404;
    res.end(JSON.stringify({{ error: 'Not found' }}));
  }});
  controlServer.listen(9876, () => console.log('🎮 Control server on http://localhost:9876'));
}}

ipcMain.on('elements-response', (event, id, elements) => {{
  const p = pendingResponses.get(id);
  if (p) {{ clearTimeout(p.timeout); pendingResponses.delete(id); p.resolve(elements); }}
}});
ipcMain.on('screen-changed', (event, screenId) => {{ currentScreen = screenId; }});

app.whenReady().then(createWindow);
app.on('window-all-closed', () => {{ if (controlServer) controlServer.close(); if (process.platform !== 'darwin') app.quit(); }});
'''
        (self.output_dir / "src" / "main" / "index.js").write_text(code)
        
    def _write_index_html(self) -> None:
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'">
  <title>{self.workflow.get("name", "App")}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div id="app"></div>
  <script src="renderer.js"></script>
</body>
</html>'''
        (self.output_dir / "src" / "renderer" / "index.html").write_text(html)
        
    def _write_renderer_js(self) -> None:
        screens_config = self._build_screens_config()
        navigation = self._build_navigation()
        start_screen = self.workflow.get("start_screen_id") or \
                       (self.workflow["screens"][0]["id"] if self.workflow.get("screens") else "screen_1")
        
        code = f'''const {{ ipcRenderer }} = require('electron');

const screens = {json.dumps(screens_config, indent=2)};
const navigation = {json.dumps(navigation, indent=2)};
let currentScreenId = '{start_screen}';

function renderScreen(screenId) {{
  const screen = screens[screenId];
  if (!screen) return;
  currentScreenId = screenId;
  
  document.getElementById('app').innerHTML = `
    <div class="screen">
      <header><h1>${{screen.title}}</h1><span class="screen-id">${{screenId}}</span></header>
      <main><form class="form" onsubmit="return false;">${{screen.elements.map(renderElement).join('')}}</form></main>
    </div>`;
  
  document.querySelectorAll('button').forEach(btn => btn.addEventListener('click', () => {{
    const next = navigation[btn.id];
    if (next) {{ btn.classList.add('clicked'); setTimeout(() => renderScreen(next), 200); }}
  }}));
  
  ipcRenderer.send('screen-changed', screenId);
  const first = document.querySelector('input, select, button');
  if (first) first.focus();
}}

function renderElement(el) {{
  const attrs = `id="${{el.id}}" data-element-id="${{el.id}}" tabindex="${{el.tabIndex || 0}}"`;
  switch (el.type) {{
    case 'text': case 'password': case 'email':
      return `<div class="form-group"><label>${{el.label}}</label><input type="${{el.type}}" ${{attrs}} placeholder="${{el.placeholder || el.label}}"/></div>`;
    case 'select':
      return `<div class="form-group"><label>${{el.label}}</label><select ${{attrs}}><option value="">Select...</option>${{(el.options||[]).map(o => `<option value="${{o}}">${{o}}</option>`).join('')}}</select></div>`;
    case 'button':
      return `<div class="form-group button-group"><button type="button" ${{attrs}} class="btn">${{el.label}}</button></div>`;
    default:
      return `<div class="form-group"><label>${{el.label}}</label><span ${{attrs}}>${{el.value || ''}}</span></div>`;
  }}
}}

function getAllElementBounds() {{
  const elements = {{}};
  document.querySelectorAll('[data-element-id]').forEach(el => {{
    const r = el.getBoundingClientRect();
    elements[el.dataset.elementId] = {{
      id: el.dataset.elementId,
      x: Math.round(r.x), y: Math.round(r.y),
      width: Math.round(r.width), height: Math.round(r.height),
      centerX: Math.round(r.x + r.width/2), centerY: Math.round(r.y + r.height/2)
    }};
  }});
  return {{ screen: currentScreenId, window: {{ x: window.screenX, y: window.screenY }}, elements }};
}}

ipcRenderer.on('get-elements', (e, id) => ipcRenderer.send('elements-response', id, getAllElementBounds()));
ipcRenderer.on('navigate', (e, screenId) => renderScreen(screenId));
ipcRenderer.on('highlight-element', (e, elemId) => {{
  const el = document.querySelector(`[data-element-id="${{elemId}}"]`);
  if (el) {{ el.classList.add('highlighted'); setTimeout(() => el.classList.remove('highlighted'), 500); }}
}});

document.addEventListener('DOMContentLoaded', () => renderScreen(currentScreenId));
'''
        (self.output_dir / "src" / "renderer" / "renderer.js").write_text(code)
        
    def _build_screens_config(self) -> dict:
        config = {}
        for screen in self.workflow.get("screens", []):
            elements = screen.get("elements") or self._default_elements(screen)
            config[screen["id"]] = {
                "title": screen.get("name", screen["id"]),
                "elements": [
                    {
                        "id": e.get("id", f"elem_{i}"),
                        "type": self._map_type(e.get("type", "text")),
                        "label": e.get("label") or e.get("text") or f"Field {i+1}",
                        "placeholder": e.get("placeholder"),
                        "options": e.get("options"),
                        "tabIndex": i + 1
                    }
                    for i, e in enumerate(elements)
                ]
            }
        return config
    
    def _default_elements(self, screen: dict) -> list:
        name = (screen.get("name") or "").lower()
        if "login" in name:
            return [
                {"id": "username", "type": "text", "label": "Username"},
                {"id": "password", "type": "password", "label": "Password"},
                {"id": "login-btn", "type": "button", "label": "Sign In"}
            ]
        elif "form" in name or "record" in name:
            return [
                {"id": "field1", "type": "text", "label": "Field 1"},
                {"id": "field2", "type": "text", "label": "Field 2"},
                {"id": "submit-btn", "type": "button", "label": "Submit"}
            ]
        else:
            return [{"id": "continue-btn", "type": "button", "label": "Continue"}]
    
    def _map_type(self, t: str) -> str:
        return {"text_input": "text", "password_input": "password", "dropdown": "select"}.get(t, t)
    
    def _build_navigation(self) -> dict:
        nav = {}
        screens = self.workflow.get("screens", [])
        for i, screen in enumerate(screens[:-1]):
            elements = screen.get("elements") or self._default_elements(screen)
            for e in elements:
                if e.get("type") == "button":
                    nav[e.get("id", f"btn_{i}")] = screens[i + 1]["id"]
        return nav
        
    def _write_styles_css(self) -> None:
        css = ''':root { --bg: #1a1a2e; --bg2: #16213e; --accent: #e94560; --text: #eaeaea; --text2: #a0a0a0; --input-bg: #0d1b2a; --border: #1b3a5c; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
.screen { display: flex; flex-direction: column; min-height: 100vh; animation: fadeIn 0.3s; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
header { background: var(--bg2); padding: 20px 30px; display: flex; justify-content: space-between; border-bottom: 1px solid var(--border); }
header h1 { font-size: 1.4rem; }
.screen-id { font-size: 0.75rem; color: var(--text2); background: var(--bg); padding: 4px 12px; border-radius: 12px; }
main { flex: 1; padding: 40px; display: flex; justify-content: center; }
.form { width: 100%; max-width: 450px; background: var(--bg2); padding: 30px; border-radius: 12px; border: 1px solid var(--border); }
.form-group { margin-bottom: 20px; }
.form-group label { display: block; font-size: 0.875rem; color: var(--text2); margin-bottom: 8px; }
input, select, textarea { width: 100%; padding: 12px 16px; font-size: 1rem; color: var(--text); background: var(--input-bg); border: 2px solid var(--border); border-radius: 8px; outline: none; }
input:focus, select:focus { border-color: var(--accent); }
.button-group { margin-top: 25px; }
.btn { width: 100%; padding: 14px; font-size: 1rem; font-weight: 600; background: var(--accent); color: white; border: none; border-radius: 8px; cursor: pointer; }
.btn:hover { background: #ff6b6b; }
.btn.clicked { transform: scale(0.98); }
.highlighted { animation: highlight 0.5s; }
@keyframes highlight { 50% { box-shadow: 0 0 20px var(--accent); } }
'''
        (self.output_dir / "src" / "renderer" / "styles.css").write_text(css)
        
    def _write_workflow_json(self) -> None:
        (self.output_dir / "src" / "renderer" / "workflow.json").write_text(
            json.dumps(self.workflow, indent=2)
        )
