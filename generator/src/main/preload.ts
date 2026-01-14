/**
 * Electron preload script - exposes safe APIs to renderer.
 */

import { contextBridge, ipcRenderer } from 'electron';

/**
 * API exposed to the renderer process.
 */
const api = {
  /**
   * Get the currently loaded workflow.
   */
  getWorkflow: () => ipcRenderer.invoke('get-workflow'),

  /**
   * Load a workflow from file.
   */
  loadWorkflow: (filePath: string) => ipcRenderer.invoke('load-workflow', filePath),

  /**
   * Send workflow control action.
   */
  workflowAction: (action: string, data?: unknown) => {
    ipcRenderer.send('workflow-action', action, data);
  },

  /**
   * Listen for workflow loaded events.
   */
  onWorkflowLoaded: (callback: (workflow: unknown) => void) => {
    ipcRenderer.on('workflow-loaded', (_event, workflow) => callback(workflow));
  },

  /**
   * Listen for error events.
   */
  onError: (callback: (error: string) => void) => {
    ipcRenderer.on('error', (_event, error) => callback(error));
  },

  /**
   * Platform info.
   */
  platform: process.platform,
};

contextBridge.exposeInMainWorld('synthAPI', api);

// TypeScript declaration for the exposed API
declare global {
  interface Window {
    synthAPI: typeof api;
  }
}
