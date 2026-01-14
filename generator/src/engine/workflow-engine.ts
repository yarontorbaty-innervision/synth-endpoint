/**
 * Workflow Engine - Executes workflow scripts with human-like behavior.
 */

import type { WorkflowDefinition, Action, Screen } from '../types/workflow.js';
import { BehaviorSimulator } from '../simulator/behavior-simulator.js';

export interface WorkflowEngineConfig {
  /** Speed multiplier (1.0 = real-time) */
  speed: number;
  /** Enable human-like behavior simulation */
  humanize: boolean;
  /** Pause between actions (ms) */
  actionDelay: number;
  /** Loop workflow continuously */
  loop: boolean;
  /** Callback for action events */
  onAction?: (action: Action, screen: Screen) => void;
  /** Callback for screen changes */
  onScreenChange?: (screen: Screen) => void;
  /** Callback for workflow completion */
  onComplete?: () => void;
}

const DEFAULT_CONFIG: WorkflowEngineConfig = {
  speed: 1.0,
  humanize: true,
  actionDelay: 500,
  loop: false,
};

/**
 * Executes workflow actions in sequence, simulating user behavior.
 */
export class WorkflowEngine {
  private workflow: WorkflowDefinition;
  private config: WorkflowEngineConfig;
  private simulator: BehaviorSimulator;
  private currentActionIndex: number = 0;
  private currentScreenId: string | null = null;
  private isRunning: boolean = false;
  private isPaused: boolean = false;

  constructor(workflow: WorkflowDefinition, config: Partial<WorkflowEngineConfig> = {}) {
    this.workflow = workflow;
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.simulator = new BehaviorSimulator({
      typingSpeed: 50, // chars per second
      mouseSpeed: 500, // pixels per second
      humanize: this.config.humanize,
    });
  }

  /**
   * Start executing the workflow.
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      console.warn('Workflow is already running');
      return;
    }

    this.isRunning = true;
    this.isPaused = false;
    this.currentActionIndex = 0;

    // Navigate to start screen
    const startScreenId = this.workflow.start_screen_id || this.workflow.screens[0]?.id;
    if (startScreenId) {
      await this.navigateToScreen(startScreenId);
    }

    // Execute actions
    await this.executeActions();
  }

  /**
   * Pause workflow execution.
   */
  pause(): void {
    this.isPaused = true;
  }

  /**
   * Resume workflow execution.
   */
  resume(): void {
    if (this.isPaused) {
      this.isPaused = false;
      this.executeActions();
    }
  }

  /**
   * Stop workflow execution.
   */
  stop(): void {
    this.isRunning = false;
    this.isPaused = false;
  }

  /**
   * Reset to beginning.
   */
  reset(): void {
    this.stop();
    this.currentActionIndex = 0;
    this.currentScreenId = null;
  }

  /**
   * Get current workflow state.
   */
  getState() {
    return {
      isRunning: this.isRunning,
      isPaused: this.isPaused,
      currentActionIndex: this.currentActionIndex,
      totalActions: this.workflow.actions.length,
      currentScreenId: this.currentScreenId,
      progress: this.workflow.actions.length > 0
        ? this.currentActionIndex / this.workflow.actions.length
        : 0,
    };
  }

  private async executeActions(): Promise<void> {
    while (this.isRunning && !this.isPaused && this.currentActionIndex < this.workflow.actions.length) {
      const action = this.workflow.actions[this.currentActionIndex];
      const screen = this.workflow.screens.find((s) => s.id === action.screen_id);

      if (!screen) {
        console.warn(`Screen not found for action: ${action.id}`);
        this.currentActionIndex++;
        continue;
      }

      // Navigate to screen if needed
      if (this.currentScreenId !== action.screen_id) {
        await this.navigateToScreen(action.screen_id);
      }

      // Execute action with delay
      const delay = (action.delay_before || this.config.actionDelay) / this.config.speed;
      await this.sleep(delay);

      await this.executeAction(action, screen);
      
      this.config.onAction?.(action, screen);

      // Handle navigation
      if (action.next_screen_id) {
        await this.navigateToScreen(action.next_screen_id);
      }

      this.currentActionIndex++;
    }

    // Handle completion
    if (this.currentActionIndex >= this.workflow.actions.length) {
      if (this.config.loop) {
        this.currentActionIndex = 0;
        await this.executeActions();
      } else {
        this.isRunning = false;
        this.config.onComplete?.();
      }
    }
  }

  private async executeAction(action: Action, screen: Screen): Promise<void> {
    const element = screen.elements.find((e) => e.id === action.element_id);

    switch (action.type) {
      case 'click':
        await this.executeClick(action, element);
        break;
      case 'double_click':
        await this.executeDoubleClick(action, element);
        break;
      case 'type':
        await this.executeType(action, element);
        break;
      case 'select':
        await this.executeSelect(action, element);
        break;
      case 'check':
      case 'uncheck':
      case 'toggle':
        await this.executeToggle(action, element);
        break;
      case 'scroll':
        await this.executeScroll(action);
        break;
      case 'hover':
        await this.executeHover(action, element);
        break;
      case 'wait':
        await this.executeWait(action);
        break;
      default:
        console.log(`Unknown action type: ${action.type}`);
    }
  }

  private async executeClick(action: Action, element?: { bounds: { x: number; y: number; width: number; height: number } }): Promise<void> {
    const x = action.x ?? (element ? element.bounds.x + element.bounds.width / 2 : 0);
    const y = action.y ?? (element ? element.bounds.y + element.bounds.height / 2 : 0);

    // Move mouse to position
    await this.simulator.moveMouse(x, y);
    
    // Click
    await this.simulator.click();
  }

  private async executeDoubleClick(action: Action, element?: { bounds: { x: number; y: number; width: number; height: number } }): Promise<void> {
    const x = action.x ?? (element ? element.bounds.x + element.bounds.width / 2 : 0);
    const y = action.y ?? (element ? element.bounds.y + element.bounds.height / 2 : 0);

    await this.simulator.moveMouse(x, y);
    await this.simulator.doubleClick();
  }

  private async executeType(action: Action, element?: { id: string }): Promise<void> {
    if (!action.value) return;

    const text = String(action.value);
    const speed = action.typing_speed || 50;

    // Focus element if specified
    if (element) {
      this.focusElement(element.id);
    }

    // Type with human-like behavior
    await this.simulator.type(text, speed / this.config.speed);
  }

  private async executeSelect(action: Action, element?: { id: string }): Promise<void> {
    if (!element || !action.value) return;

    // Simulate click on dropdown
    await this.executeClick(action, element as any);
    
    // Wait for dropdown to open
    await this.sleep(200 / this.config.speed);
    
    // Select value
    this.setElementValue(element.id, action.value);
  }

  private async executeToggle(action: Action, element?: { id: string }): Promise<void> {
    if (!element) return;

    // Click the toggle/checkbox
    await this.executeClick(action, element as any);
  }

  private async executeScroll(action: Action): Promise<void> {
    await this.simulator.scroll(0, action.value as number || 100);
  }

  private async executeHover(action: Action, element?: { bounds: { x: number; y: number; width: number; height: number } }): Promise<void> {
    const x = action.x ?? (element ? element.bounds.x + element.bounds.width / 2 : 0);
    const y = action.y ?? (element ? element.bounds.y + element.bounds.height / 2 : 0);

    await this.simulator.moveMouse(x, y);
    await this.sleep(300 / this.config.speed);
  }

  private async executeWait(action: Action): Promise<void> {
    const duration = (action.duration || 1000) / this.config.speed;
    await this.sleep(duration);
  }

  private async navigateToScreen(screenId: string): Promise<void> {
    const screen = this.workflow.screens.find((s) => s.id === screenId);
    if (!screen) {
      console.warn(`Screen not found: ${screenId}`);
      return;
    }

    this.currentScreenId = screenId;
    this.config.onScreenChange?.(screen);
  }

  private focusElement(elementId: string): void {
    // In browser context, this would focus the actual element
    if (typeof document !== 'undefined') {
      const element = document.getElementById(elementId);
      if (element && 'focus' in element) {
        (element as HTMLElement).focus();
      }
    }
  }

  private setElementValue(elementId: string, value: unknown): void {
    // In browser context, this would set the element value
    if (typeof document !== 'undefined') {
      const element = document.getElementById(elementId) as HTMLInputElement | HTMLSelectElement;
      if (element) {
        element.value = String(value);
        element.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
