"""
Prompts for VLM-based video analysis.
"""

# System context for all analysis
SYSTEM_CONTEXT = """You are an expert UI/UX analyst specializing in understanding business software interfaces.
Your task is to analyze screenshots from screen recordings and extract structured information about:
1. UI elements (buttons, inputs, dropdowns, tables, etc.)
2. User actions (clicks, typing, navigation)
3. Application workflow patterns

Always respond with valid JSON that can be parsed programmatically."""


UI_ELEMENT_DETECTION_PROMPT = """Analyze this screenshot and identify ALL UI elements visible in the interface.

For each element, provide:
- type: The element type (one of: text_input, password_input, textarea, dropdown, combobox, checkbox, radio, toggle, button, link, tab, menu_item, table, date_picker, slider, label, heading, icon, image, modal, panel, sidebar, toolbar, navigation)
- bounds: Approximate position as {x, y, width, height} in pixels (estimate based on the image)
- text: Any visible text content
- placeholder: Placeholder text if visible
- label: Associated label text
- enabled: Whether the element appears enabled (true/false)
- value: Current value if visible

Focus on interactive elements and important labels. Group related elements logically.

Respond with a JSON object in this exact format:
```json
{
  "screen_name": "descriptive name for this screen",
  "screen_description": "what this screen is for",
  "application": "name of the application if identifiable",
  "elements": [
    {
      "type": "button",
      "bounds": {"x": 100, "y": 200, "width": 120, "height": 40},
      "text": "Submit",
      "enabled": true
    }
  ]
}
```"""


ACTION_DETECTION_PROMPT = """Compare these two consecutive screenshots and identify what user action occurred between them.

Analyze:
1. What changed between the frames?
2. What element was likely interacted with?
3. What type of action was performed?

Action types:
- click: Mouse click on an element
- double_click: Double-click
- type: Text was entered
- select: Option was selected from dropdown
- check/uncheck: Checkbox was toggled
- scroll: Page was scrolled
- navigate: User navigated to different screen

Respond with a JSON object:
```json
{
  "action_detected": true,
  "action": {
    "type": "click",
    "target_element": "description of the element clicked",
    "target_bounds": {"x": 100, "y": 200, "width": 50, "height": 30},
    "value": null,
    "description": "User clicked the Submit button"
  },
  "screen_changed": false,
  "confidence": 0.9
}
```

If no significant action is detected, set action_detected to false."""


WORKFLOW_MAPPING_PROMPT = """Analyze this sequence of screenshots showing a complete user workflow.

Your task:
1. Identify the distinct screens/views in the workflow
2. Understand the purpose of each screen
3. Map the sequence of user actions
4. Identify the overall workflow goal

For each screen, note:
- What application/system is shown
- Key UI elements and their purpose
- Data being displayed or entered

Respond with a JSON object:
```json
{
  "workflow_name": "descriptive name",
  "workflow_description": "what this workflow accomplishes",
  "applications_used": ["App1", "App2"],
  "screens": [
    {
      "id": "screen_1",
      "name": "Login Screen",
      "description": "User authentication",
      "key_elements": ["username input", "password input", "login button"],
      "frame_indices": [0, 1, 2]
    }
  ],
  "workflow_steps": [
    {
      "step": 1,
      "screen_id": "screen_1",
      "action": "type",
      "target": "username input",
      "value": "user@example.com",
      "description": "Enter username"
    }
  ]
}
```"""


SCREEN_SIMILARITY_PROMPT = """Compare these two screenshots and determine if they represent the same screen/view in the application.

Consider:
- Overall layout similarity
- Same set of UI elements
- Same application/context
- Minor differences (scroll position, input values) don't make screens different

Respond with JSON:
```json
{
  "same_screen": true,
  "similarity_score": 0.95,
  "differences": ["different scroll position", "input field has new value"],
  "reasoning": "Both screenshots show the same login form with minor value changes"
}
```"""


DATA_EXTRACTION_PROMPT = """Extract all visible text data and values from this screenshot.

Focus on:
- Form field labels and values
- Table data (headers and cells)
- Status messages and notifications
- Navigation labels
- Any numbers, dates, or identifiers

Respond with JSON:
```json
{
  "form_fields": [
    {"label": "Username", "value": "john.doe@example.com", "type": "text_input"},
    {"label": "Amount", "value": "1,234.56", "type": "text_input"}
  ],
  "table_data": {
    "headers": ["Date", "Description", "Amount"],
    "rows": [
      ["10/15/2025", "Invoice #12345", "$500.00"]
    ]
  },
  "labels": ["Dashboard", "Settings", "Logout"],
  "messages": ["Payment successful"],
  "identifiers": ["INV-2025-001", "Customer #4567"]
}
```"""


def get_ui_detection_prompt() -> str:
    """Get the UI element detection prompt."""
    return UI_ELEMENT_DETECTION_PROMPT


def get_action_detection_prompt() -> str:
    """Get the action detection prompt for frame comparison."""
    return ACTION_DETECTION_PROMPT


def get_workflow_mapping_prompt() -> str:
    """Get the workflow mapping prompt for full video analysis."""
    return WORKFLOW_MAPPING_PROMPT


def get_screen_similarity_prompt() -> str:
    """Get the screen similarity comparison prompt."""
    return SCREEN_SIMILARITY_PROMPT


def get_data_extraction_prompt() -> str:
    """Get the data extraction prompt."""
    return DATA_EXTRACTION_PROMPT
