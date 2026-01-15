/**
 * Auto-generates Electron apps from workflow definitions.
 * 
 * Takes a workflow JSON and creates a complete Electron app with:
 * - Screens for each workflow screen
 * - UI elements (forms, buttons, inputs)
 * - Navigation between screens
 * - Control server for playback coordination
 */

import * as fs from 'fs';
import * as path from 'path';

interface UIElement {
  id: string;
  type: string;
  label?: string;
  text?: string;
  placeholder?: string;
  options?: string[];
  position?: string;
}

interface Screen {
  id: string;
  name: string;
  description?: string;
  elements?: UIElement[];
  timestamp?: number;
  source_frame?: string;
}

interface Action {
  id: string;
  type: string;
  screen_id?: string;
  element_id?: string;
  value?: string;
  next_screen_id?: string;
}

interface Workflow {
  id: string;
  name: string;
  description?: string;
  screens: Screen[];
  actions: Action[];
  start_screen_id?: string;
}

export class ElectronAppGenerator {
  private workflow: Workflow;
  private outputDir: string;

  constructor(workflow: Workflow, outputDir: string) {
    this.workflow = workflow;
    this.outputDir = outputDir;
  }

  /**
   * Generate the complete Electron app
   */
  generate(): void {
    console.log(`Generating Electron app: ${this.workflow.name}`);
    
    // Create directory structure
    this.createDirectories();
    
    // Generate files
    this.generatePackageJson();
    this.generateMainJs();
    this.generatePreloadJs();
    this.generateIndexHtml();
    this.generateRendererJs();
    this.generateStylesCss();
    this.generateWorkflowJson();
    
    console.log(`✅ App generated in: ${this.outputDir}`);
  }

  private createDirectories(): void {
    const dirs = [
      this.outputDir,
      path.join(this.outputDir, 'src'),
      path.join(this.outputDir, 'src', 'main'),
      path.join(this.outputDir, 'src', 'renderer'),
    ];
    
    for (const dir of dirs) {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    }
  }

  private generatePackageJson(): void {
    const appName = this.workflow.name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    
    const pkg = {
      name: appName,
      version: '1.0.0',
      description: this.workflow.description || `Generated from workflow: ${this.workflow.name}`,
      main: 'src/main/index.js',
      scripts: {
        start: 'electron .',
        build: 'electron-builder'
      },
      dependencies: {
        electron: '^28.0.0'
      },
      devDependencies: {
        'electron-builder': '^24.9.1'
      }
    };
    
    fs.writeFileSync(
      path.join(this.outputDir, 'package.json'),
      JSON.stringify(pkg, null, 2)
    );
  }

  private generateMainJs(): void {
    const code = `const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const http = require('http');

let mainWindow;
let controlServer;
let currentScreen = '${this.workflow.start_screen_id || this.workflow.screens[0]?.id || 'screen_1'}';

const pendingResponses = new Map();
let responseId = 0;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    x: 100,
    y: 100,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
    title: '${this.workflow.name}'
  });

  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  startControlServer();
}

function startControlServer() {
  controlServer = http.createServer(async (req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    const url = new URL(req.url, 'http://localhost');
    
    if (req.method === 'GET' && url.pathname === '/status') {
      res.end(JSON.stringify({
        screen: currentScreen,
        window: mainWindow ? mainWindow.getBounds() : null,
        ready: true
      }));
      return;
    }
    
    if (req.method === 'GET' && url.pathname === '/elements') {
      const id = ++responseId;
      const timeout = setTimeout(() => {
        pendingResponses.delete(id);
        res.end(JSON.stringify({ error: 'timeout', elements: {} }));
      }, 3000);
      pendingResponses.set(id, { resolve: (data) => res.end(JSON.stringify(data)), timeout });
      mainWindow.webContents.send('get-elements', id);
      return;
    }
    
    if (req.method === 'POST' && url.pathname.startsWith('/navigate/')) {
      const screenId = url.pathname.replace('/navigate/', '');
      currentScreen = screenId;
      mainWindow.webContents.send('navigate', screenId);
      res.end(JSON.stringify({ success: true, screen: screenId }));
      return;
    }
    
    if (req.method === 'POST' && url.pathname === '/focus-window') {
      mainWindow.show();
      mainWindow.focus();
      res.end(JSON.stringify({ success: true }));
      return;
    }
    
    if (req.method === 'POST' && url.pathname === '/reset') {
      currentScreen = '${this.workflow.start_screen_id || this.workflow.screens[0]?.id || 'screen_1'}';
      mainWindow.webContents.send('navigate', currentScreen);
      res.end(JSON.stringify({ success: true, screen: currentScreen }));
      return;
    }
    
    if (req.method === 'POST' && url.pathname.startsWith('/highlight/')) {
      const elementId = url.pathname.replace('/highlight/', '');
      mainWindow.webContents.send('highlight-element', elementId);
      res.end(JSON.stringify({ success: true }));
      return;
    }
    
    if (req.method === 'GET' && url.pathname === '/focused-element') {
      const id = ++responseId;
      const timeout = setTimeout(() => {
        pendingResponses.delete(id);
        res.end(JSON.stringify({ focused: null }));
      }, 1000);
      pendingResponses.set(id, { resolve: (data) => res.end(JSON.stringify(data)), timeout });
      mainWindow.webContents.send('get-focused-element', id);
      return;
    }
    
    res.statusCode = 404;
    res.end(JSON.stringify({ error: 'Not found' }));
  });
  
  controlServer.listen(9876, () => {
    console.log('🎮 Control server on http://localhost:9876');
  });
}

ipcMain.on('elements-response', (event, id, elements) => {
  const pending = pendingResponses.get(id);
  if (pending) {
    clearTimeout(pending.timeout);
    pendingResponses.delete(id);
    pending.resolve(elements);
  }
});

ipcMain.on('focused-element-response', (event, id, data) => {
  const pending = pendingResponses.get(id);
  if (pending) {
    clearTimeout(pending.timeout);
    pendingResponses.delete(id);
    pending.resolve(data);
  }
});

ipcMain.on('screen-changed', (event, screenId) => {
  currentScreen = screenId;
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (controlServer) controlServer.close();
  if (process.platform !== 'darwin') app.quit();
});
`;
    
    fs.writeFileSync(path.join(this.outputDir, 'src', 'main', 'index.js'), code);
  }

  private generatePreloadJs(): void {
    const code = `// Preload script - empty for now as we use nodeIntegration
`;
    fs.writeFileSync(path.join(this.outputDir, 'src', 'main', 'preload.js'), code);
  }

  private generateIndexHtml(): void {
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'">
  <title>${this.workflow.name}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div id="app"></div>
  <script src="renderer.js"></script>
</body>
</html>
`;
    fs.writeFileSync(path.join(this.outputDir, 'src', 'renderer', 'index.html'), html);
  }

  private generateRendererJs(): void {
    const screens = this.workflow.screens;
    const screensJson = JSON.stringify(this.buildScreensConfig(), null, 2);
    const navigationJson = JSON.stringify(this.buildNavigationConfig(), null, 2);
    
    const code = `const { ipcRenderer } = require('electron');

// Screen definitions
const screens = ${screensJson};

// Navigation rules (button -> next screen)
const navigation = ${navigationJson};

let currentScreenId = '${this.workflow.start_screen_id || screens[0]?.id || 'screen_1'}';

function renderScreen(screenId) {
  const screen = screens[screenId];
  if (!screen) {
    console.error('Unknown screen:', screenId);
    return;
  }
  
  currentScreenId = screenId;
  
  const container = document.getElementById('app');
  container.innerHTML = \`
    <div class="screen" data-screen="\${screenId}">
      <header>
        <h1>\${screen.title}</h1>
        <span class="screen-id">\${screenId}</span>
      </header>
      <main>
        <form class="form" onsubmit="return false;">
          \${screen.elements.map(el => renderElement(el)).join('')}
        </form>
      </main>
    </div>
  \`;
  
  setupListeners();
  ipcRenderer.send('screen-changed', screenId);
  
  const firstInput = container.querySelector('input, select, button');
  if (firstInput) firstInput.focus();
}

function renderElement(el) {
  const attrs = \`id="\${el.id}" data-element-id="\${el.id}" tabindex="\${el.tabIndex || 0}"\`;
  
  switch (el.type) {
    case 'text':
    case 'password':
    case 'email':
      return \`
        <div class="form-group" data-element-container="\${el.id}">
          <label for="\${el.id}">\${el.label}</label>
          <input type="\${el.type}" \${attrs} placeholder="\${el.placeholder || el.label}" />
        </div>\`;
    
    case 'textarea':
      return \`
        <div class="form-group" data-element-container="\${el.id}">
          <label for="\${el.id}">\${el.label}</label>
          <textarea \${attrs} placeholder="\${el.placeholder || el.label}" rows="3"></textarea>
        </div>\`;
    
    case 'select':
      return \`
        <div class="form-group" data-element-container="\${el.id}">
          <label for="\${el.id}">\${el.label}</label>
          <select \${attrs}>
            <option value="">Select...</option>
            \${(el.options || []).map(opt => \`<option value="\${opt}">\${opt}</option>\`).join('')}
          </select>
        </div>\`;
    
    case 'button':
      return \`
        <div class="form-group button-group" data-element-container="\${el.id}">
          <button type="button" \${attrs} class="btn \${el.variant || 'primary'}">\${el.label}</button>
        </div>\`;
    
    case 'label':
      return \`
        <div class="form-group readonly" data-element-container="\${el.id}">
          <label>\${el.label}</label>
          <span \${attrs} class="value">\${el.value || ''}</span>
        </div>\`;
    
    default:
      return \`<div data-element-container="\${el.id}">\${el.label || el.id}</div>\`;
  }
}

function setupListeners() {
  document.querySelectorAll('[data-element-id]').forEach(el => {
    el.addEventListener('focus', () => el.classList.add('focused'));
    el.addEventListener('blur', () => el.classList.remove('focused'));
  });
  
  document.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => handleButtonClick(btn.id));
  });
}

function handleButtonClick(buttonId) {
  const nextScreen = navigation[buttonId];
  if (nextScreen) {
    const btn = document.getElementById(buttonId);
    btn.classList.add('clicked');
    setTimeout(() => renderScreen(nextScreen), 200);
  }
}

function getElementBounds(elementId) {
  const el = document.querySelector(\`[data-element-id="\${elementId}"]\`);
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  return {
    id: elementId,
    x: Math.round(rect.x),
    y: Math.round(rect.y),
    width: Math.round(rect.width),
    height: Math.round(rect.height),
    centerX: Math.round(rect.x + rect.width / 2),
    centerY: Math.round(rect.y + rect.height / 2)
  };
}

function getAllElementBounds() {
  const elements = {};
  document.querySelectorAll('[data-element-id]').forEach(el => {
    const bounds = getElementBounds(el.dataset.elementId);
    if (bounds) elements[el.dataset.elementId] = bounds;
  });
  return {
    screen: currentScreenId,
    window: { x: window.screenX, y: window.screenY },
    elements
  };
}

// IPC handlers
ipcRenderer.on('get-elements', (event, requestId) => {
  ipcRenderer.send('elements-response', requestId, getAllElementBounds());
});

ipcRenderer.on('navigate', (event, screenId) => {
  renderScreen(screenId);
});

ipcRenderer.on('highlight-element', (event, elementId) => {
  const el = document.querySelector(\`[data-element-id="\${elementId}"]\`);
  if (el) {
    el.classList.add('highlighted');
    setTimeout(() => el.classList.remove('highlighted'), 500);
  }
});

ipcRenderer.on('get-focused-element', (event, requestId) => {
  const focused = document.activeElement;
  ipcRenderer.send('focused-element-response', requestId, {
    focused: focused?.dataset?.elementId || null
  });
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  renderScreen(currentScreenId);
});
`;
    
    fs.writeFileSync(path.join(this.outputDir, 'src', 'renderer', 'renderer.js'), code);
  }

  private buildScreensConfig(): Record<string, any> {
    const config: Record<string, any> = {};
    
    for (const screen of this.workflow.screens) {
      config[screen.id] = {
        title: screen.name || screen.id,
        elements: this.generateElementsForScreen(screen)
      };
    }
    
    return config;
  }

  private generateElementsForScreen(screen: Screen): any[] {
    // If screen has elements, use them
    if (screen.elements && screen.elements.length > 0) {
      return screen.elements.map((el, i) => ({
        id: el.id || `elem_${i}`,
        type: this.mapElementType(el.type),
        label: el.label || el.text || el.placeholder || `Element ${i + 1}`,
        placeholder: el.placeholder,
        options: el.options,
        tabIndex: i + 1
      }));
    }
    
    // Otherwise generate default elements based on screen name/type
    return this.generateDefaultElements(screen);
  }

  private generateDefaultElements(screen: Screen): any[] {
    const name = (screen.name || '').toLowerCase();
    
    // Login screen
    if (name.includes('login') || name.includes('sign in')) {
      return [
        { id: 'username', type: 'text', label: 'Username', tabIndex: 1 },
        { id: 'password', type: 'password', label: 'Password', tabIndex: 2 },
        { id: 'login-btn', type: 'button', label: 'Sign In', tabIndex: 3 }
      ];
    }
    
    // Form screen
    if (name.includes('form') || name.includes('entry') || name.includes('record')) {
      return [
        { id: 'field1', type: 'text', label: 'Field 1', tabIndex: 1 },
        { id: 'field2', type: 'text', label: 'Field 2', tabIndex: 2 },
        { id: 'field3', type: 'select', label: 'Select Option', options: ['Option A', 'Option B', 'Option C'], tabIndex: 3 },
        { id: 'submit-btn', type: 'button', label: 'Submit', tabIndex: 4 }
      ];
    }
    
    // List screen
    if (name.includes('list') || name.includes('table') || name.includes('view')) {
      return [
        { id: 'search', type: 'text', label: 'Search', tabIndex: 1 },
        { id: 'filter', type: 'select', label: 'Filter', options: ['All', 'Active', 'Archived'], tabIndex: 2 },
        { id: 'new-btn', type: 'button', label: '+ New', tabIndex: 3 }
      ];
    }
    
    // Default
    return [
      { id: 'action-btn', type: 'button', label: 'Continue', tabIndex: 1 }
    ];
  }

  private mapElementType(type: string): string {
    const typeMap: Record<string, string> = {
      'text_input': 'text',
      'password_input': 'password',
      'dropdown': 'select',
      'button': 'button',
      'textarea': 'textarea',
      'label': 'label',
      'checkbox': 'checkbox'
    };
    return typeMap[type] || type || 'text';
  }

  private buildNavigationConfig(): Record<string, string> {
    const nav: Record<string, string> = {};
    
    // Build from actions
    for (const action of this.workflow.actions) {
      if (action.next_screen_id && action.element_id) {
        nav[action.element_id] = action.next_screen_id;
      }
    }
    
    // Also connect screens sequentially if no explicit navigation
    for (let i = 0; i < this.workflow.screens.length - 1; i++) {
      const current = this.workflow.screens[i];
      const next = this.workflow.screens[i + 1];
      
      // Find buttons on this screen and connect to next
      const elements = this.generateElementsForScreen(current);
      const buttons = elements.filter(e => e.type === 'button');
      
      for (const btn of buttons) {
        if (!nav[btn.id]) {
          nav[btn.id] = next.id;
        }
      }
    }
    
    return nav;
  }

  private generateStylesCss(): void {
    const css = `:root {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --accent: #e94560;
  --accent-hover: #ff6b6b;
  --text-primary: #eaeaea;
  --text-secondary: #a0a0a0;
  --input-bg: #0d1b2a;
  --input-border: #1b3a5c;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
}

.screen {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

header {
  background: var(--bg-secondary);
  padding: 20px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--input-border);
}

header h1 { font-size: 1.4rem; font-weight: 600; }
.screen-id { font-size: 0.75rem; color: var(--text-secondary); background: var(--bg-primary); padding: 4px 12px; border-radius: 12px; }

main {
  flex: 1;
  padding: 40px;
  display: flex;
  justify-content: center;
}

.form {
  width: 100%;
  max-width: 450px;
  background: var(--bg-secondary);
  padding: 30px;
  border-radius: 12px;
  border: 1px solid var(--input-border);
}

.form-group { margin-bottom: 20px; }
.form-group label {
  display: block;
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

input, select, textarea {
  width: 100%;
  padding: 12px 16px;
  font-size: 1rem;
  color: var(--text-primary);
  background: var(--input-bg);
  border: 2px solid var(--input-border);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s;
}

input:focus, select:focus, textarea:focus {
  border-color: var(--accent);
}

.button-group { margin-top: 25px; }

.btn {
  width: 100%;
  padding: 14px;
  font-size: 1rem;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn.primary, .btn {
  background: var(--accent);
  color: white;
}

.btn:hover { background: var(--accent-hover); }
.btn:active, .btn.clicked { transform: scale(0.98); }

.focused::after {
  content: '';
  position: absolute;
  inset: -3px;
  border: 2px solid var(--accent);
  border-radius: 10px;
  pointer-events: none;
}

.highlighted { animation: highlight 0.5s ease; }

@keyframes highlight {
  50% { box-shadow: 0 0 20px var(--accent); }
}

.readonly .value {
  display: block;
  padding: 12px;
  background: var(--input-bg);
  border-radius: 8px;
  font-weight: 600;
  color: var(--accent);
}
`;
    fs.writeFileSync(path.join(this.outputDir, 'src', 'renderer', 'styles.css'), css);
  }

  private generateWorkflowJson(): void {
    fs.writeFileSync(
      path.join(this.outputDir, 'src', 'renderer', 'workflow.json'),
      JSON.stringify(this.workflow, null, 2)
    );
  }
}

// CLI entry point
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length < 2) {
    console.log('Usage: npx ts-node auto-generator.ts <workflow.json> <output-dir>');
    process.exit(1);
  }
  
  const [workflowPath, outputDir] = args;
  
  const workflow = JSON.parse(fs.readFileSync(workflowPath, 'utf-8'));
  const generator = new ElectronAppGenerator(workflow, outputDir);
  generator.generate();
}

export { ElectronAppGenerator };
