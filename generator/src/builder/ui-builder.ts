/**
 * UI Builder - Generates UI components from workflow definitions.
 */

import type { Screen, UIElement, UIElementType } from '../types/workflow.js';

/**
 * Generates HTML/CSS for a screen based on its element definitions.
 */
export class UIBuilder {
  private screen: Screen;

  constructor(screen: Screen) {
    this.screen = screen;
  }

  /**
   * Build complete HTML for the screen.
   */
  buildHTML(): string {
    const elements = this.screen.elements
      .map((el) => this.buildElement(el))
      .join('\n');

    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${this.escapeHTML(this.screen.name)}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="screen" id="${this.screen.id}" style="width: ${this.screen.width}px; height: ${this.screen.height}px;">
    ${elements}
  </div>
  <script src="renderer.js"></script>
</body>
</html>
    `.trim();
  }

  /**
   * Build HTML for a single UI element.
   */
  buildElement(element: UIElement): string {
    const style = this.buildPositionStyle(element);
    const dataAttrs = `data-element-id="${element.id}" data-element-type="${element.type}"`;

    switch (element.type) {
      case 'text_input':
        return this.buildTextInput(element, style, dataAttrs);
      case 'password_input':
        return this.buildPasswordInput(element, style, dataAttrs);
      case 'textarea':
        return this.buildTextarea(element, style, dataAttrs);
      case 'dropdown':
      case 'combobox':
        return this.buildDropdown(element, style, dataAttrs);
      case 'checkbox':
        return this.buildCheckbox(element, style, dataAttrs);
      case 'radio':
        return this.buildRadio(element, style, dataAttrs);
      case 'toggle':
        return this.buildToggle(element, style, dataAttrs);
      case 'button':
        return this.buildButton(element, style, dataAttrs);
      case 'link':
        return this.buildLink(element, style, dataAttrs);
      case 'label':
      case 'heading':
        return this.buildText(element, style, dataAttrs);
      case 'table':
        return this.buildTable(element, style, dataAttrs);
      case 'slider':
        return this.buildSlider(element, style, dataAttrs);
      case 'date_picker':
        return this.buildDatePicker(element, style, dataAttrs);
      default:
        return this.buildGenericElement(element, style, dataAttrs);
    }
  }

  private buildPositionStyle(element: UIElement): string {
    const { x, y, width, height } = element.bounds;
    return `position: absolute; left: ${x}px; top: ${y}px; width: ${width}px; height: ${height}px;`;
  }

  private buildTextInput(element: UIElement, style: string, dataAttrs: string): string {
    const placeholder = element.placeholder ? `placeholder="${this.escapeHTML(element.placeholder)}"` : '';
    const value = element.value ? `value="${this.escapeHTML(String(element.value))}"` : '';
    const disabled = !element.enabled ? 'disabled' : '';
    const required = element.required ? 'required' : '';

    return `
      <div class="form-field" style="${style}" ${dataAttrs}>
        ${element.label ? `<label>${this.escapeHTML(element.label)}</label>` : ''}
        <input type="text" id="${element.id}" ${placeholder} ${value} ${disabled} ${required}>
      </div>
    `;
  }

  private buildPasswordInput(element: UIElement, style: string, dataAttrs: string): string {
    const placeholder = element.placeholder ? `placeholder="${this.escapeHTML(element.placeholder)}"` : '';
    const disabled = !element.enabled ? 'disabled' : '';

    return `
      <div class="form-field" style="${style}" ${dataAttrs}>
        ${element.label ? `<label>${this.escapeHTML(element.label)}</label>` : ''}
        <input type="password" id="${element.id}" ${placeholder} ${disabled}>
      </div>
    `;
  }

  private buildTextarea(element: UIElement, style: string, dataAttrs: string): string {
    const placeholder = element.placeholder ? `placeholder="${this.escapeHTML(element.placeholder)}"` : '';
    const value = element.value ? this.escapeHTML(String(element.value)) : '';
    const disabled = !element.enabled ? 'disabled' : '';

    return `
      <div class="form-field" style="${style}" ${dataAttrs}>
        ${element.label ? `<label>${this.escapeHTML(element.label)}</label>` : ''}
        <textarea id="${element.id}" ${placeholder} ${disabled}>${value}</textarea>
      </div>
    `;
  }

  private buildDropdown(element: UIElement, style: string, dataAttrs: string): string {
    const options = (element.options || [])
      .map((opt) => {
        const selected = element.value === opt ? 'selected' : '';
        return `<option value="${this.escapeHTML(opt)}" ${selected}>${this.escapeHTML(opt)}</option>`;
      })
      .join('\n');
    const disabled = !element.enabled ? 'disabled' : '';

    return `
      <div class="form-field" style="${style}" ${dataAttrs}>
        ${element.label ? `<label>${this.escapeHTML(element.label)}</label>` : ''}
        <select id="${element.id}" ${disabled}>
          ${options}
        </select>
      </div>
    `;
  }

  private buildCheckbox(element: UIElement, style: string, dataAttrs: string): string {
    const checked = element.value ? 'checked' : '';
    const disabled = !element.enabled ? 'disabled' : '';

    return `
      <div class="form-field checkbox-field" style="${style}" ${dataAttrs}>
        <input type="checkbox" id="${element.id}" ${checked} ${disabled}>
        ${element.label ? `<label for="${element.id}">${this.escapeHTML(element.label)}</label>` : ''}
      </div>
    `;
  }

  private buildRadio(element: UIElement, style: string, dataAttrs: string): string {
    const checked = element.value ? 'checked' : '';
    const disabled = !element.enabled ? 'disabled' : '';
    const name = element.label || element.id;

    return `
      <div class="form-field radio-field" style="${style}" ${dataAttrs}>
        <input type="radio" id="${element.id}" name="${name}" ${checked} ${disabled}>
        ${element.text ? `<label for="${element.id}">${this.escapeHTML(element.text)}</label>` : ''}
      </div>
    `;
  }

  private buildToggle(element: UIElement, style: string, dataAttrs: string): string {
    const checked = element.value ? 'checked' : '';
    const disabled = !element.enabled ? 'disabled' : '';

    return `
      <div class="form-field toggle-field" style="${style}" ${dataAttrs}>
        <label class="toggle-switch">
          <input type="checkbox" id="${element.id}" ${checked} ${disabled}>
          <span class="toggle-slider"></span>
        </label>
        ${element.label ? `<span class="toggle-label">${this.escapeHTML(element.label)}</span>` : ''}
      </div>
    `;
  }

  private buildButton(element: UIElement, style: string, dataAttrs: string): string {
    const text = element.text || 'Button';
    const disabled = !element.enabled ? 'disabled' : '';

    return `
      <button class="btn" id="${element.id}" style="${style}" ${dataAttrs} ${disabled}>
        ${this.escapeHTML(text)}
      </button>
    `;
  }

  private buildLink(element: UIElement, style: string, dataAttrs: string): string {
    const text = element.text || 'Link';

    return `
      <a href="#" class="link" id="${element.id}" style="${style}" ${dataAttrs}>
        ${this.escapeHTML(text)}
      </a>
    `;
  }

  private buildText(element: UIElement, style: string, dataAttrs: string): string {
    const text = element.text || '';
    const tag = element.type === 'heading' ? 'h2' : 'span';

    return `
      <${tag} class="text-element ${element.type}" id="${element.id}" style="${style}" ${dataAttrs}>
        ${this.escapeHTML(text)}
      </${tag}>
    `;
  }

  private buildTable(element: UIElement, style: string, dataAttrs: string): string {
    // Generate a placeholder table structure
    return `
      <div class="table-container" style="${style}" ${dataAttrs}>
        <table id="${element.id}">
          <thead>
            <tr>
              <th>Column 1</th>
              <th>Column 2</th>
              <th>Column 3</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Data 1</td>
              <td>Data 2</td>
              <td>Data 3</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }

  private buildSlider(element: UIElement, style: string, dataAttrs: string): string {
    const value = typeof element.value === 'number' ? element.value : 50;
    const disabled = !element.enabled ? 'disabled' : '';

    return `
      <div class="form-field slider-field" style="${style}" ${dataAttrs}>
        ${element.label ? `<label>${this.escapeHTML(element.label)}</label>` : ''}
        <input type="range" id="${element.id}" min="0" max="100" value="${value}" ${disabled}>
      </div>
    `;
  }

  private buildDatePicker(element: UIElement, style: string, dataAttrs: string): string {
    const value = element.value ? `value="${this.escapeHTML(String(element.value))}"` : '';
    const disabled = !element.enabled ? 'disabled' : '';

    return `
      <div class="form-field" style="${style}" ${dataAttrs}>
        ${element.label ? `<label>${this.escapeHTML(element.label)}</label>` : ''}
        <input type="date" id="${element.id}" ${value} ${disabled}>
      </div>
    `;
  }

  private buildGenericElement(element: UIElement, style: string, dataAttrs: string): string {
    return `
      <div class="element ${element.type}" id="${element.id}" style="${style}" ${dataAttrs}>
        ${element.text ? this.escapeHTML(element.text) : ''}
      </div>
    `;
  }

  private escapeHTML(str: string): string {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

/**
 * Generate CSS styles for the application.
 */
export function generateStyles(screens: Screen[]): string {
  return `
/* Innervision Synth Endpoint - Generated Styles */

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background: #f5f5f5;
  color: #333;
  line-height: 1.5;
}

.screen {
  position: relative;
  background: #ffffff;
  margin: 0 auto;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

/* Form Fields */
.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-field label {
  font-size: 12px;
  font-weight: 500;
  color: #666;
}

.form-field input[type="text"],
.form-field input[type="password"],
.form-field input[type="date"],
.form-field textarea,
.form-field select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-field input:focus,
.form-field textarea:focus,
.form-field select:focus {
  outline: none;
  border-color: #0066cc;
  box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
}

.form-field input:disabled,
.form-field textarea:disabled,
.form-field select:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

/* Checkbox & Radio */
.checkbox-field,
.radio-field {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.checkbox-field input,
.radio-field input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

/* Toggle Switch */
.toggle-field {
  flex-direction: row;
  align-items: center;
  gap: 12px;
}

.toggle-switch {
  position: relative;
  width: 48px;
  height: 24px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.3s;
  border-radius: 24px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: #0066cc;
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(24px);
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  background: #0066cc;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
}

.btn:hover {
  background: #0052a3;
}

.btn:active {
  transform: scale(0.98);
}

.btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* Links */
.link {
  color: #0066cc;
  text-decoration: none;
  cursor: pointer;
}

.link:hover {
  text-decoration: underline;
}

/* Text Elements */
.text-element {
  display: flex;
  align-items: center;
}

.text-element.heading {
  font-size: 18px;
  font-weight: 600;
}

.text-element.label {
  font-size: 14px;
  color: #666;
}

/* Tables */
.table-container {
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  font-weight: 600;
  background: #f9f9f9;
}

tr:hover {
  background: #f5f5f5;
}

/* Slider */
.slider-field input[type="range"] {
  width: 100%;
  height: 4px;
  background: #ddd;
  border-radius: 2px;
  outline: none;
  -webkit-appearance: none;
}

.slider-field input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: #0066cc;
  border-radius: 50%;
  cursor: pointer;
}

/* Simulation Cursor */
.simulation-cursor {
  position: fixed;
  width: 20px;
  height: 20px;
  pointer-events: none;
  z-index: 10000;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="%23000" d="M7 2l12 11.5-5.5 1 3.5 7-2.5 1-3.5-7L7 18z"/></svg>') no-repeat;
  background-size: contain;
  transition: transform 0.05s ease-out;
}

.simulation-cursor.clicking {
  transform: scale(0.9);
}

/* Typing Indicator */
.typing-indicator {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: #333;
  animation: blink 0.7s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* Highlight Effect */
.element-highlight {
  box-shadow: 0 0 0 2px #0066cc !important;
  transition: box-shadow 0.2s;
}
  `.trim();
}
