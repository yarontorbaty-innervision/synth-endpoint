#!/usr/bin/env node
/**
 * CLI tool to generate desktop applications from workflow definitions.
 */

import * as fs from 'fs';
import * as path from 'path';
import type { WorkflowDefinition, GeneratorConfig, Screen } from '../types/workflow.js';
import { UIBuilder, generateStyles } from '../builder/ui-builder.js';

interface GenerateOptions {
  workflow: string;
  output: string;
  platform?: 'macos' | 'windows' | 'both';
  name?: string;
  speed?: number;
  debug?: boolean;
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const options = parseArgs(args);

  if (!options.workflow) {
    console.error('Usage: generate --workflow <path> --output <dir> [--platform macos|windows|both]');
    process.exit(1);
  }

  console.log('🔧 Innervision Generator');
  console.log('========================\n');

  // Load workflow
  console.log(`📄 Loading workflow: ${options.workflow}`);
  const workflow = loadWorkflow(options.workflow);
  console.log(`   Name: ${workflow.name}`);
  console.log(`   Screens: ${workflow.screens.length}`);
  console.log(`   Actions: ${workflow.actions.length}\n`);

  // Generate app
  const config: GeneratorConfig = {
    outputDir: options.output,
    platform: options.platform || 'both',
    appName: options.name || workflow.name,
    enableSimulation: true,
    simulationSpeed: options.speed || 1.0,
    debug: options.debug || false,
  };

  console.log(`📦 Generating application...`);
  console.log(`   Output: ${config.outputDir}`);
  console.log(`   Platform: ${config.platform}\n`);

  await generateApp(workflow, config);

  console.log('✅ Generation complete!\n');
  console.log('Next steps:');
  console.log(`  cd ${config.outputDir}`);
  console.log('  pnpm install');
  console.log('  pnpm run build:macos  # or build:windows');
}

function parseArgs(args: string[]): GenerateOptions {
  const options: GenerateOptions = {
    workflow: '',
    output: './generated-app',
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--workflow':
      case '-w':
        options.workflow = args[++i];
        break;
      case '--output':
      case '-o':
        options.output = args[++i];
        break;
      case '--platform':
      case '-p':
        options.platform = args[++i] as 'macos' | 'windows' | 'both';
        break;
      case '--name':
      case '-n':
        options.name = args[++i];
        break;
      case '--speed':
      case '-s':
        options.speed = parseFloat(args[++i]);
        break;
      case '--debug':
      case '-d':
        options.debug = true;
        break;
    }
  }

  return options;
}

function loadWorkflow(filePath: string): WorkflowDefinition {
  const content = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(content);
}

async function generateApp(workflow: WorkflowDefinition, config: GeneratorConfig): Promise<void> {
  const outputDir = path.resolve(config.outputDir);
  
  // Create directory structure
  const dirs = [
    outputDir,
    path.join(outputDir, 'src'),
    path.join(outputDir, 'src/renderer'),
    path.join(outputDir, 'src/main'),
    path.join(outputDir, 'src/screens'),
  ];

  for (const dir of dirs) {
    fs.mkdirSync(dir, { recursive: true });
  }

  // Generate screen HTML files
  for (const screen of workflow.screens) {
    const builder = new UIBuilder(screen);
    const html = builder.buildHTML();
    const screenPath = path.join(outputDir, 'src/screens', `${screen.id}.html`);
    fs.writeFileSync(screenPath, html);
    console.log(`   Generated: ${screen.id}.html`);
  }

  // Generate styles
  const styles = generateStyles(workflow.screens);
  fs.writeFileSync(path.join(outputDir, 'src/renderer/styles.css'), styles);
  console.log('   Generated: styles.css');

  // Generate main index.html
  const indexHtml = generateIndexHTML(workflow, config);
  fs.writeFileSync(path.join(outputDir, 'src/renderer/index.html'), indexHtml);
  console.log('   Generated: index.html');

  // Generate renderer script
  const rendererScript = generateRendererScript(workflow, config);
  fs.writeFileSync(path.join(outputDir, 'src/renderer/renderer.js'), rendererScript);
  console.log('   Generated: renderer.js');

  // Generate workflow data
  fs.writeFileSync(
    path.join(outputDir, 'src/renderer/workflow.json'),
    JSON.stringify(workflow, null, 2)
  );
  console.log('   Generated: workflow.json');

  // Generate package.json
  const packageJson = generatePackageJson(config);
  fs.writeFileSync(path.join(outputDir, 'package.json'), JSON.stringify(packageJson, null, 2));
  console.log('   Generated: package.json');

  // Copy main process files (simplified - in production would compile TypeScript)
  const mainScript = generateMainScript();
  fs.writeFileSync(path.join(outputDir, 'src/main/index.js'), mainScript);
  console.log('   Generated: main/index.js');
}

function generateIndexHTML(workflow: WorkflowDefinition, config: GeneratorConfig): string {
  const startScreen = workflow.screens.find(s => s.id === workflow.start_screen_id) || workflow.screens[0];
  
  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'">
  <title>${config.appName || workflow.name}</title>
  <link rel="stylesheet" href="styles.css">
  <style>
    #app-container {
      width: 100vw;
      height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #1a1a2e;
    }
    #controls {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      display: flex;
      gap: 10px;
      padding: 10px 20px;
      background: rgba(255, 255, 255, 0.9);
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
      z-index: 1000;
    }
    #controls button {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-weight: 500;
      transition: background 0.2s;
    }
    #controls button.primary {
      background: #0066cc;
      color: white;
    }
    #controls button.primary:hover {
      background: #0052a3;
    }
    #controls button.secondary {
      background: #e0e0e0;
      color: #333;
    }
    #controls button.secondary:hover {
      background: #d0d0d0;
    }
    #status {
      font-size: 14px;
      color: #666;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    #screen-container {
      position: relative;
      background: white;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
      border-radius: 8px;
      overflow: hidden;
    }
  </style>
</head>
<body>
  <div id="app-container">
    <div id="screen-container">
      <!-- Screen content will be loaded here -->
    </div>
  </div>
  
  <div id="controls">
    <button id="btn-play" class="primary">▶ Play</button>
    <button id="btn-pause" class="secondary">⏸ Pause</button>
    <button id="btn-reset" class="secondary">↺ Reset</button>
    <div id="status">
      <span id="status-text">Ready</span>
      <span id="progress">0%</span>
    </div>
  </div>
  
  <script src="renderer.js"></script>
</body>
</html>
  `.trim();
}

function generateRendererScript(workflow: WorkflowDefinition, config: GeneratorConfig): string {
  return `
// Innervision Synth Endpoint - Renderer
(function() {
  'use strict';

  // Load workflow data
  const workflow = ${JSON.stringify(workflow, null, 2)};
  
  // Configuration
  const config = {
    speed: ${config.simulationSpeed || 1.0},
    humanize: true,
    debug: ${config.debug || false}
  };

  // State
  let currentScreenIndex = 0;
  let currentActionIndex = 0;
  let isPlaying = false;
  let isPaused = false;

  // DOM Elements
  const screenContainer = document.getElementById('screen-container');
  const btnPlay = document.getElementById('btn-play');
  const btnPause = document.getElementById('btn-pause');
  const btnReset = document.getElementById('btn-reset');
  const statusText = document.getElementById('status-text');
  const progressText = document.getElementById('progress');

  // Initialize
  function init() {
    loadScreen(0);
    setupControls();
    
    if (config.debug) {
      console.log('Workflow loaded:', workflow.name);
      console.log('Screens:', workflow.screens.length);
      console.log('Actions:', workflow.actions.length);
    }
  }

  // Load a screen by index
  function loadScreen(index) {
    if (index < 0 || index >= workflow.screens.length) return;
    
    const screen = workflow.screens[index];
    currentScreenIndex = index;
    
    // Build screen HTML
    screenContainer.innerHTML = buildScreenHTML(screen);
    screenContainer.style.width = screen.width + 'px';
    screenContainer.style.height = screen.height + 'px';
    
    if (config.debug) {
      console.log('Loaded screen:', screen.name);
    }
  }

  // Build HTML for a screen
  function buildScreenHTML(screen) {
    let html = '<div class="screen" style="position: relative; width: 100%; height: 100%;">';
    
    for (const element of screen.elements) {
      html += buildElementHTML(element);
    }
    
    html += '</div>';
    return html;
  }

  // Build HTML for an element
  function buildElementHTML(element) {
    const style = 'position: absolute; left: ' + element.bounds.x + 'px; top: ' + element.bounds.y + 'px; ' +
                  'width: ' + element.bounds.width + 'px; height: ' + element.bounds.height + 'px;';
    
    switch (element.type) {
      case 'button':
        return '<button class="btn" id="' + element.id + '" style="' + style + '">' + 
               (element.text || 'Button') + '</button>';
      case 'text_input':
        return '<div class="form-field" style="' + style + '">' +
               (element.label ? '<label>' + element.label + '</label>' : '') +
               '<input type="text" id="' + element.id + '" placeholder="' + (element.placeholder || '') + '" ' +
               'value="' + (element.value || '') + '"></div>';
      case 'dropdown':
        let options = (element.options || []).map(opt => 
          '<option value="' + opt + '">' + opt + '</option>'
        ).join('');
        return '<div class="form-field" style="' + style + '">' +
               (element.label ? '<label>' + element.label + '</label>' : '') +
               '<select id="' + element.id + '">' + options + '</select></div>';
      case 'label':
      case 'heading':
        return '<span class="text-element ' + element.type + '" id="' + element.id + '" style="' + style + '">' +
               (element.text || '') + '</span>';
      default:
        return '<div class="element" id="' + element.id + '" style="' + style + '">' +
               (element.text || '') + '</div>';
    }
  }

  // Setup control buttons
  function setupControls() {
    btnPlay.addEventListener('click', play);
    btnPause.addEventListener('click', pause);
    btnReset.addEventListener('click', reset);
  }

  // Play workflow
  async function play() {
    if (isPlaying && !isPaused) return;
    
    isPlaying = true;
    isPaused = false;
    btnPlay.textContent = '▶ Playing...';
    statusText.textContent = 'Running';
    
    await executeActions();
  }

  // Pause workflow
  function pause() {
    isPaused = true;
    btnPlay.textContent = '▶ Resume';
    statusText.textContent = 'Paused';
  }

  // Reset workflow
  function reset() {
    isPlaying = false;
    isPaused = false;
    currentActionIndex = 0;
    loadScreen(0);
    btnPlay.textContent = '▶ Play';
    statusText.textContent = 'Ready';
    progressText.textContent = '0%';
  }

  // Execute workflow actions
  async function executeActions() {
    while (isPlaying && !isPaused && currentActionIndex < workflow.actions.length) {
      const action = workflow.actions[currentActionIndex];
      
      // Update progress
      const progress = Math.round((currentActionIndex / workflow.actions.length) * 100);
      progressText.textContent = progress + '%';
      
      // Find target screen
      const screenIndex = workflow.screens.findIndex(s => s.id === action.screen_id);
      if (screenIndex !== -1 && screenIndex !== currentScreenIndex) {
        loadScreen(screenIndex);
        await sleep(300 / config.speed);
      }
      
      // Execute action
      await executeAction(action);
      
      currentActionIndex++;
    }
    
    if (currentActionIndex >= workflow.actions.length) {
      statusText.textContent = 'Complete';
      progressText.textContent = '100%';
      btnPlay.textContent = '▶ Play';
      isPlaying = false;
    }
  }

  // Execute a single action
  async function executeAction(action) {
    const delay = (action.delay_before || 500) / config.speed;
    await sleep(delay);
    
    const element = document.getElementById(action.element_id);
    
    switch (action.type) {
      case 'click':
        if (element) {
          highlightElement(element);
          await sleep(200 / config.speed);
          element.click();
        }
        break;
        
      case 'type':
        if (element && action.value) {
          highlightElement(element);
          element.focus();
          await typeText(element, String(action.value));
        }
        break;
        
      case 'select':
        if (element && action.value) {
          highlightElement(element);
          element.value = action.value;
          element.dispatchEvent(new Event('change', { bubbles: true }));
        }
        break;
        
      default:
        if (config.debug) {
          console.log('Action:', action.type, action);
        }
    }
  }

  // Type text with human-like speed
  async function typeText(element, text) {
    element.value = '';
    const baseDelay = 50 / config.speed;
    
    for (const char of text) {
      element.value += char;
      element.dispatchEvent(new Event('input', { bubbles: true }));
      
      // Variable delay for human-like typing
      let delay = baseDelay + (Math.random() - 0.5) * baseDelay * 0.6;
      if ('.!?,;:'.includes(char)) delay += baseDelay * 3;
      
      await sleep(delay);
    }
  }

  // Highlight an element temporarily
  function highlightElement(element) {
    element.classList.add('element-highlight');
    setTimeout(() => element.classList.remove('element-highlight'), 500);
  }

  // Sleep helper
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Start
  document.addEventListener('DOMContentLoaded', init);
})();
  `.trim();
}

function generatePackageJson(config: GeneratorConfig): object {
  return {
    name: (config.appName || 'synth-app').toLowerCase().replace(/\s+/g, '-'),
    version: '1.0.0',
    description: 'Generated Innervision Synth Endpoint Application',
    main: 'src/main/index.js',
    scripts: {
      start: 'electron .',
      'build:macos': 'electron-builder --mac',
      'build:windows': 'electron-builder --win',
      build: 'electron-builder',
    },
    devDependencies: {
      electron: '^28.1.0',
      'electron-builder': '^24.9.1',
    },
    build: {
      appId: 'ai.innervision.synth.' + (config.appName || 'app').toLowerCase().replace(/\s+/g, '-'),
      productName: config.appName || 'Synth App',
      directories: {
        output: 'release',
      },
      mac: {
        category: 'public.app-category.developer-tools',
        target: ['dmg', 'zip'],
      },
      win: {
        target: ['nsis', 'portable'],
      },
      files: ['src/**/*'],
    },
  };
}

function generateMainScript(): string {
  return `
const { app, BrowserWindow } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
  `.trim();
}

main().catch(console.error);
