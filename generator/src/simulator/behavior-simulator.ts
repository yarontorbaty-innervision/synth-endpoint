/**
 * Behavior Simulator - Simulates human-like interactions.
 */

export interface SimulatorConfig {
  /** Base typing speed in characters per second */
  typingSpeed: number;
  /** Mouse movement speed in pixels per second */
  mouseSpeed: number;
  /** Enable human-like variations */
  humanize: boolean;
}

interface MousePosition {
  x: number;
  y: number;
}

/**
 * Simulates realistic human behavior for mouse movements and typing.
 */
export class BehaviorSimulator {
  private config: SimulatorConfig;
  private currentMousePosition: MousePosition = { x: 0, y: 0 };
  private cursorElement: HTMLElement | null = null;

  constructor(config: SimulatorConfig) {
    this.config = config;
  }

  /**
   * Initialize the visual cursor for simulation.
   */
  initCursor(): void {
    if (typeof document === 'undefined') return;

    this.cursorElement = document.createElement('div');
    this.cursorElement.className = 'simulation-cursor';
    document.body.appendChild(this.cursorElement);
    this.updateCursorPosition();
  }

  /**
   * Remove the visual cursor.
   */
  removeCursor(): void {
    if (this.cursorElement) {
      this.cursorElement.remove();
      this.cursorElement = null;
    }
  }

  /**
   * Move mouse to target position with human-like motion.
   */
  async moveMouse(targetX: number, targetY: number): Promise<void> {
    const startX = this.currentMousePosition.x;
    const startY = this.currentMousePosition.y;
    
    // Calculate distance and duration
    const distance = Math.sqrt(Math.pow(targetX - startX, 2) + Math.pow(targetY - startY, 2));
    const baseDuration = (distance / this.config.mouseSpeed) * 1000;
    const duration = this.config.humanize 
      ? this.addVariation(baseDuration, 0.2) 
      : baseDuration;

    // Generate bezier curve control points for natural movement
    const controlPoints = this.generateCurveControlPoints(
      { x: startX, y: startY },
      { x: targetX, y: targetY }
    );

    // Animate along curve
    const steps = Math.max(Math.floor(duration / 16), 10); // ~60fps
    const stepDuration = duration / steps;

    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const pos = this.bezierPoint(
        { x: startX, y: startY },
        controlPoints.cp1,
        controlPoints.cp2,
        { x: targetX, y: targetY },
        this.easeInOutCubic(t)
      );

      this.currentMousePosition = pos;
      this.updateCursorPosition();
      
      await this.sleep(stepDuration);
    }

    // Ensure we end exactly at target
    this.currentMousePosition = { x: targetX, y: targetY };
    this.updateCursorPosition();
  }

  /**
   * Simulate a mouse click.
   */
  async click(): Promise<void> {
    this.setCursorClicking(true);
    await this.sleep(this.config.humanize ? this.addVariation(100, 0.3) : 100);
    this.setCursorClicking(false);

    // Dispatch click event at current position
    this.dispatchMouseEvent('click');
  }

  /**
   * Simulate a double click.
   */
  async doubleClick(): Promise<void> {
    await this.click();
    await this.sleep(this.config.humanize ? this.addVariation(80, 0.2) : 80);
    await this.click();
    
    this.dispatchMouseEvent('dblclick');
  }

  /**
   * Simulate typing with human-like variations.
   */
  async type(text: string, speed?: number): Promise<void> {
    const baseDelay = 1000 / (speed || this.config.typingSpeed);
    
    for (const char of text) {
      // Variable delay between keystrokes
      let delay = baseDelay;
      if (this.config.humanize) {
        delay = this.addVariation(baseDelay, 0.3);
        
        // Longer pause after punctuation
        if ('.!?,;:'.includes(char)) {
          delay += this.addVariation(200, 0.3);
        }
        
        // Occasional longer pause (thinking)
        if (Math.random() < 0.02) {
          delay += this.addVariation(500, 0.5);
        }
      }

      this.dispatchKeyEvent(char);
      await this.sleep(delay);
    }
  }

  /**
   * Simulate scrolling.
   */
  async scroll(deltaX: number, deltaY: number): Promise<void> {
    // Smooth scroll simulation
    const steps = 10;
    const stepX = deltaX / steps;
    const stepY = deltaY / steps;

    for (let i = 0; i < steps; i++) {
      if (typeof window !== 'undefined') {
        window.scrollBy(stepX, stepY);
      }
      await this.sleep(16);
    }
  }

  /**
   * Get current mouse position.
   */
  getMousePosition(): MousePosition {
    return { ...this.currentMousePosition };
  }

  private updateCursorPosition(): void {
    if (this.cursorElement) {
      this.cursorElement.style.left = `${this.currentMousePosition.x}px`;
      this.cursorElement.style.top = `${this.currentMousePosition.y}px`;
    }
  }

  private setCursorClicking(clicking: boolean): void {
    if (this.cursorElement) {
      if (clicking) {
        this.cursorElement.classList.add('clicking');
      } else {
        this.cursorElement.classList.remove('clicking');
      }
    }
  }

  private generateCurveControlPoints(
    start: MousePosition,
    end: MousePosition
  ): { cp1: MousePosition; cp2: MousePosition } {
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    // Add some randomness to control points for natural movement
    const curviness = this.config.humanize ? Math.random() * 0.3 + 0.1 : 0.2;
    const perpX = -dy / distance;
    const perpY = dx / distance;
    const offset = distance * curviness * (Math.random() > 0.5 ? 1 : -1);

    const cp1: MousePosition = {
      x: start.x + dx * 0.3 + perpX * offset * 0.5,
      y: start.y + dy * 0.3 + perpY * offset * 0.5,
    };

    const cp2: MousePosition = {
      x: start.x + dx * 0.7 + perpX * offset * 0.5,
      y: start.y + dy * 0.7 + perpY * offset * 0.5,
    };

    return { cp1, cp2 };
  }

  private bezierPoint(
    p0: MousePosition,
    p1: MousePosition,
    p2: MousePosition,
    p3: MousePosition,
    t: number
  ): MousePosition {
    const t2 = t * t;
    const t3 = t2 * t;
    const mt = 1 - t;
    const mt2 = mt * mt;
    const mt3 = mt2 * mt;

    return {
      x: mt3 * p0.x + 3 * mt2 * t * p1.x + 3 * mt * t2 * p2.x + t3 * p3.x,
      y: mt3 * p0.y + 3 * mt2 * t * p1.y + 3 * mt * t2 * p2.y + t3 * p3.y,
    };
  }

  private easeInOutCubic(t: number): number {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  private addVariation(value: number, factor: number): number {
    const variation = (Math.random() - 0.5) * 2 * factor * value;
    return Math.max(0, value + variation);
  }

  private dispatchMouseEvent(type: string): void {
    if (typeof document === 'undefined') return;

    const element = document.elementFromPoint(
      this.currentMousePosition.x,
      this.currentMousePosition.y
    );

    if (element) {
      const event = new MouseEvent(type, {
        bubbles: true,
        cancelable: true,
        clientX: this.currentMousePosition.x,
        clientY: this.currentMousePosition.y,
      });
      element.dispatchEvent(event);
    }
  }

  private dispatchKeyEvent(char: string): void {
    if (typeof document === 'undefined') return;

    const activeElement = document.activeElement as HTMLInputElement | HTMLTextAreaElement;
    
    if (activeElement && 'value' in activeElement) {
      // Insert character at cursor position
      const start = activeElement.selectionStart || 0;
      const end = activeElement.selectionEnd || 0;
      const value = activeElement.value;
      
      activeElement.value = value.substring(0, start) + char + value.substring(end);
      activeElement.selectionStart = activeElement.selectionEnd = start + 1;
      
      // Dispatch input event
      activeElement.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
