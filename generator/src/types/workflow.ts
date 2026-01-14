/**
 * Type definitions for workflow definitions.
 * Mirrors the Python models for cross-language compatibility.
 */

export type UIElementType =
  | 'text_input'
  | 'password_input'
  | 'textarea'
  | 'dropdown'
  | 'combobox'
  | 'checkbox'
  | 'radio'
  | 'toggle'
  | 'button'
  | 'link'
  | 'tab'
  | 'menu_item'
  | 'table'
  | 'table_row'
  | 'table_cell'
  | 'date_picker'
  | 'time_picker'
  | 'slider'
  | 'progress_bar'
  | 'label'
  | 'heading'
  | 'icon'
  | 'image'
  | 'modal'
  | 'tooltip'
  | 'panel'
  | 'sidebar'
  | 'toolbar'
  | 'navigation';

export type ActionType =
  | 'click'
  | 'double_click'
  | 'right_click'
  | 'type'
  | 'select'
  | 'check'
  | 'uncheck'
  | 'toggle'
  | 'scroll'
  | 'drag'
  | 'drop'
  | 'hover'
  | 'focus'
  | 'blur'
  | 'submit'
  | 'navigate'
  | 'wait';

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface UIElement {
  id: string;
  type: UIElementType;
  bounds: BoundingBox;
  text?: string | null;
  placeholder?: string | null;
  value?: unknown;
  options?: string[] | null;
  label?: string | null;
  enabled?: boolean;
  visible?: boolean;
  required?: boolean;
  confidence?: number;
  style?: Record<string, unknown>;
}

export interface Screen {
  id: string;
  name: string;
  description?: string | null;
  width: number;
  height: number;
  elements: UIElement[];
  background_color?: string | null;
  screenshot_path?: string | null;
  source_frame?: number | null;
  timestamp?: number | null;
}

export interface Action {
  id: string;
  type: ActionType;
  screen_id: string;
  element_id?: string | null;
  x?: number | null;
  y?: number | null;
  value?: unknown;
  delay_before?: number;
  duration?: number;
  typing_speed?: number | null;
  mouse_speed?: number | null;
  next_screen_id?: string | null;
  timestamp?: number | null;
  confidence?: number;
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  description?: string | null;
  version?: string;
  source_video?: string | null;
  source_application?: string | null;
  screens: Screen[];
  actions: Action[];
  start_screen_id?: string | null;
  settings?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface GeneratorConfig {
  /** Output directory for generated app */
  outputDir: string;
  /** Target platform */
  platform: 'macos' | 'windows' | 'both';
  /** App name override */
  appName?: string;
  /** Enable behavior simulation */
  enableSimulation?: boolean;
  /** Simulation speed multiplier (1.0 = real-time) */
  simulationSpeed?: number;
  /** Theme override */
  theme?: 'light' | 'dark' | 'auto';
  /** Include debug tools */
  debug?: boolean;
}
