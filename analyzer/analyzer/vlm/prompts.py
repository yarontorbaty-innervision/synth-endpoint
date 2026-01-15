"""
Optimized prompts for VLM-based video analysis.

These prompts are designed to get structured, actionable output
from vision language models like moondream, llava, etc.
"""

# =============================================================================
# Screen Analysis Prompts
# =============================================================================

SCREEN_ANALYSIS_PROMPT = """Analyze this screenshot and provide:

APP: [application name visible in title bar or UI]
TYPE: [login/form/list/dashboard/detail/modal/menu]
ELEMENTS:
- [element type]: [label/text] at [position description]
- [element type]: [label/text] at [position description]
...

Example response:
APP: SwipeSimple
TYPE: login
ELEMENTS:
- input: "Username" at top center
- input: "Password" at middle center  
- button: "Sign In" at bottom center
- link: "Forgot Password?" at bottom"""

UI_ELEMENTS_PROMPT = """List ALL interactive elements visible in this screenshot.

For each element, provide:
TYPE | LABEL | LOCATION

Types: button, input, dropdown, checkbox, link, tab, menu

Example:
button | Sign In | bottom center
input | Email | top center
dropdown | Select Card | middle left
checkbox | Remember me | bottom left

List elements now:"""

SCREEN_DIFF_PROMPT = """Compare these two screenshots.

Answer:
1. SAME_SCREEN: yes/no
2. CHANGES: [what changed between them]
3. ACTION: [what user action caused the change - click/type/scroll/navigate]
4. TARGET: [what element was interacted with]

Be specific and brief."""

# =============================================================================
# Action Detection Prompts  
# =============================================================================

ACTION_DETECTION_PROMPT = """Look at these two consecutive screenshots.

What user action happened between them?

Answer in this format:
ACTION: [click/type/select/scroll/navigate/none]
TARGET: [what was clicked/typed into]
VALUE: [text typed or option selected, if any]
RESULT: [what changed after the action]

Be specific. If no action detected, say ACTION: none"""

TYPING_DETECTION_PROMPT = """Compare these screenshots.

Is there new text typed in any field?

Answer:
TYPING: yes/no
FIELD: [which field]
TEXT: [what was typed]"""

# =============================================================================
# Workflow Extraction Prompts
# =============================================================================

WORKFLOW_SUMMARY_PROMPT = """Analyze this sequence of screenshots showing a user workflow.

Describe:
1. WORKFLOW_NAME: [descriptive name]
2. APPLICATION: [main app being used]
3. STEPS: 
   - Step 1: [action and purpose]
   - Step 2: [action and purpose]
   ...
4. DATA_ENTERED: [any text/values the user entered]

Be specific about what the user did."""

# =============================================================================
# Element Extraction (JSON-focused)
# =============================================================================

JSON_SCREEN_PROMPT = """Analyze this screenshot. Output ONLY valid JSON, no other text.

{
  "app": "application name",
  "screen": "screen name or type",
  "elements": [
    {"type": "button", "label": "text on button", "position": "top/middle/bottom left/center/right"},
    {"type": "input", "label": "field label", "position": "position"},
    {"type": "dropdown", "label": "dropdown label", "position": "position"}
  ]
}

Output JSON only:"""

JSON_ACTION_PROMPT = """Compare these two screenshots. Output ONLY valid JSON.

{
  "action_detected": true or false,
  "action_type": "click/type/select/scroll/navigate",
  "target_element": "what was interacted with",
  "value": "text typed or option selected",
  "screen_changed": true or false
}

Output JSON only:"""

# =============================================================================
# Helper functions
# =============================================================================

def get_ui_detection_prompt() -> str:
    """Get prompt for UI element detection."""
    return UI_ELEMENTS_PROMPT

def get_action_detection_prompt() -> str:
    """Get prompt for action detection between frames."""
    return ACTION_DETECTION_PROMPT

def get_workflow_mapping_prompt() -> str:
    """Get prompt for workflow summary."""
    return WORKFLOW_SUMMARY_PROMPT

def get_screen_similarity_prompt() -> str:
    """Get prompt for comparing two screens."""
    return SCREEN_DIFF_PROMPT

def get_data_extraction_prompt() -> str:
    """Get prompt for extracting data/values."""
    return TYPING_DETECTION_PROMPT

def get_structured_screen_prompt() -> str:
    """Get prompt for structured JSON screen analysis."""
    return JSON_SCREEN_PROMPT

def get_structured_action_prompt() -> str:
    """Get prompt for structured JSON action detection."""
    return JSON_ACTION_PROMPT
