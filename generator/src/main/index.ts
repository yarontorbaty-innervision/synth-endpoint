/**
 * Electron main process entry point.
 */

import { app, BrowserWindow, ipcMain } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import type { WorkflowDefinition } from '../types/workflow.js';

let mainWindow: BrowserWindow | null = null;
let currentWorkflow: WorkflowDefinition | null = null;

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    titleBarStyle: 'hiddenInset',
    show: false,
  });

  // Load the index.html
  const indexPath = path.join(__dirname, '../renderer/index.html');
  
  if (fs.existsSync(indexPath)) {
    mainWindow.loadFile(indexPath);
  } else {
    // Development mode - load from local server or show error
    mainWindow.loadURL('about:blank');
    mainWindow.webContents.on('did-finish-load', () => {
      mainWindow?.webContents.send('error', 'No index.html found. Run the generator first.');
    });
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
    
    // Start workflow if loaded
    if (currentWorkflow) {
      mainWindow?.webContents.send('workflow-loaded', currentWorkflow);
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Load workflow from command line or default path
function loadWorkflow(): void {
  const workflowPath = process.argv.find((arg) => arg.endsWith('.json'));
  
  if (workflowPath && fs.existsSync(workflowPath)) {
    try {
      const content = fs.readFileSync(workflowPath, 'utf-8');
      currentWorkflow = JSON.parse(content);
      console.log(`Loaded workflow: ${currentWorkflow?.name}`);
    } catch (error) {
      console.error('Failed to load workflow:', error);
    }
  }
}

// IPC Handlers
ipcMain.handle('get-workflow', () => currentWorkflow);

ipcMain.handle('load-workflow', async (_event, filePath: string) => {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    currentWorkflow = JSON.parse(content);
    return { success: true, workflow: currentWorkflow };
  } catch (error) {
    return { success: false, error: String(error) };
  }
});

ipcMain.on('workflow-action', (_event, action: string, data?: unknown) => {
  console.log(`Workflow action: ${action}`, data);
  // Handle workflow control actions (play, pause, stop, etc.)
});

// App lifecycle
app.whenReady().then(() => {
  loadWorkflow();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Security: Prevent new window creation
app.on('web-contents-created', (_event, contents) => {
  contents.setWindowOpenHandler(() => {
    return { action: 'deny' };
  });
});
