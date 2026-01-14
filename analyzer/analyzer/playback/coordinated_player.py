"""
Coordinated playback controller that synchronizes with an Electron app.

This player communicates with the Electron app to:
1. Get element positions in real-time
2. Navigate between screens
3. Perform mouse/keyboard actions at actual element locations
"""

from __future__ import annotations
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

from analyzer.playback.os_controller import OSController, MouseButton

logger = logging.getLogger(__name__)


class ElectronAppConnection:
    """Connection to the Electron app's control server."""
    
    def __init__(self, host: str = "localhost", port: int = 9876):
        self.base_url = f"http://{host}:{port}"
        self.window_offset = (0, 0)
    
    def _request(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        """Make HTTP request to control server."""
        url = f"{self.base_url}{path}"
        req = Request(url, method=method)
        
        if data:
            req.data = json.dumps(data).encode()
            req.add_header("Content-Type", "application/json")
        
        try:
            with urlopen(req, timeout=5) as response:
                return json.loads(response.read())
        except URLError as e:
            logger.error(f"Connection error: {e}")
            return {"error": str(e)}
    
    def get_status(self) -> dict:
        """Get app status including current screen and window position."""
        return self._request("GET", "/status")
    
    def get_elements(self) -> dict:
        """Get all element bounds on current screen."""
        return self._request("GET", "/elements")
    
    def get_element(self, element_id: str) -> Optional[dict]:
        """Get bounds for a specific element."""
        result = self._request("GET", f"/element/{element_id}")
        return result if result and "error" not in result else None
    
    def navigate(self, screen_id: str) -> bool:
        """Navigate to a specific screen."""
        result = self._request("POST", f"/navigate/{screen_id}")
        return result.get("success", False)
    
    def focus_element(self, element_id: str) -> bool:
        """Focus an element (for Tab navigation)."""
        result = self._request("POST", f"/focus/{element_id}")
        return result.get("success", False)
    
    def highlight_element(self, element_id: str) -> bool:
        """Highlight an element visually."""
        result = self._request("POST", f"/highlight/{element_id}")
        return result.get("success", False)
    
    def focus_window(self) -> bool:
        """Bring the app window to the foreground."""
        result = self._request("POST", "/focus-window")
        return result.get("success", False)
    
    def reset(self) -> bool:
        """Reset app to initial screen."""
        result = self._request("POST", "/reset")
        return result.get("success", False)
    
    def get_focused_element(self) -> Optional[str]:
        """Get the currently focused element ID."""
        result = self._request("GET", "/focused-element")
        return result.get("focused")
    
    def is_connected(self) -> bool:
        """Check if app is connected and ready."""
        try:
            status = self.get_status()
            return status.get("ready", False)
        except:
            return False
    
    def wait_for_connection(self, timeout: float = 10.0) -> bool:
        """Wait for app to be ready."""
        start = time.time()
        while time.time() - start < timeout:
            if self.is_connected():
                return True
            time.sleep(0.5)
        return False
    
    def get_element_screen_position(self, element_id: str) -> Optional[tuple]:
        """
        Get element position in screen coordinates.
        
        Returns center point (x, y) adjusted for window position.
        """
        status = self.get_status()
        window = status.get("window", {})
        
        elements = self.get_elements()
        element = elements.get("elements", {}).get(element_id)
        
        if not element or not window:
            return None
        
        # Element position is relative to window content area
        # Add window offset + title bar height (macOS ~28px, Windows ~32px)
        import platform
        title_bar_height = 28 if platform.system() == "Darwin" else 32
        
        screen_x = window.get("x", 0) + element.get("centerX", 0)
        screen_y = window.get("y", 0) + element.get("centerY", 0) + title_bar_height
        
        return (screen_x, screen_y)


class CoordinatedPlayer:
    """
    Playback controller that coordinates with an Electron app.
    
    Usage:
        player = CoordinatedPlayer()
        
        # Wait for app
        if not player.connect():
            print("App not running!")
            return
        
        # Execute a sequence
        player.click_element("username")
        player.type_text("admin")
        player.press_tab()
        player.type_text("password123")
        player.click_element("login-btn")
        
        # Or run a full workflow
        player.run_workflow(workflow_definition)
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9876,
        speed: float = 1.0,
        human_like: bool = True,
        typing_wpm: int = 60
    ):
        self.app = ElectronAppConnection(host, port)
        self.controller = OSController()
        self.speed = speed
        self.human_like = human_like
        self.typing_wpm = typing_wpm
        
        # Callbacks
        self.on_action: Optional[Callable[[str, str], None]] = None
        self.on_screen_change: Optional[Callable[[str], None]] = None
    
    def connect(self, timeout: float = 10.0, reset: bool = False) -> bool:
        """Connect to the Electron app and bring it to foreground."""
        logger.info("Connecting to Electron app...")
        if self.app.wait_for_connection(timeout):
            status = self.app.get_status()
            logger.info(f"Connected! Current screen: {status.get('screen')}")
            
            # Reset to initial screen if requested
            if reset:
                logger.info("Resetting to initial screen...")
                self.app.reset()
                time.sleep(0.3)
            
            # Bring window to foreground
            self.app.focus_window()
            time.sleep(0.3)
            return True
        logger.error("Could not connect to app")
        return False
    
    def verify_screen(self, expected_screen: str) -> bool:
        """Verify we're on the expected screen."""
        current = self.get_current_screen()
        if current != expected_screen:
            logger.warning(f"Expected screen '{expected_screen}' but on '{current}'")
            return False
        return True
    
    def verify_focus(self, expected_element: str) -> bool:
        """Verify the expected element is focused."""
        focused = self.app.get_focused_element()
        if focused != expected_element:
            logger.warning(f"Expected '{expected_element}' focused but got '{focused}'")
            return False
        return True
    
    def ensure_screen(self, screen_id: str) -> bool:
        """Ensure we're on the specified screen, navigate if not."""
        if not self.verify_screen(screen_id):
            logger.info(f"Navigating to {screen_id}")
            return self.navigate_to_screen(screen_id)
        return True
    
    def _log_action(self, action: str, target: str = ""):
        """Log and callback for action."""
        if self.on_action:
            self.on_action(action, target)
        logger.debug(f"Action: {action} {target}")
    
    def _wait(self, seconds: float):
        """Wait, adjusted for speed."""
        time.sleep(seconds / self.speed)
    
    # =========================================================================
    # Element-based actions
    # =========================================================================
    
    def click_element(self, element_id: str, verify: bool = True) -> bool:
        """Click on an element by ID."""
        self._log_action("click", element_id)
        
        pos = self.app.get_element_screen_position(element_id)
        if not pos:
            logger.warning(f"Element not found: {element_id}")
            return False
        
        # Highlight for visual feedback
        self.app.highlight_element(element_id)
        
        # Move and click
        duration = 0.3 / self.speed if self.human_like else 0.1 / self.speed
        self.controller.move_mouse(pos[0], pos[1], duration=duration, human_like=self.human_like)
        self._wait(0.05)
        self.controller.click()
        self._wait(0.15)
        
        # Verify focus if requested
        if verify:
            focused = self.app.get_focused_element()
            if focused != element_id:
                logger.debug(f"Focus after click: {focused} (expected {element_id})")
        
        return True
    
    def double_click_element(self, element_id: str) -> bool:
        """Double-click on an element."""
        self._log_action("double_click", element_id)
        
        pos = self.app.get_element_screen_position(element_id)
        if not pos:
            return False
        
        self.app.highlight_element(element_id)
        duration = 0.3 / self.speed
        self.controller.move_mouse(pos[0], pos[1], duration=duration)
        self.controller.double_click()
        self._wait(0.1)
        
        return True
    
    def focus_element(self, element_id: str) -> bool:
        """Focus an element (without clicking)."""
        self._log_action("focus", element_id)
        return self.app.focus_element(element_id)
    
    def hover_element(self, element_id: str, duration: float = 0.5) -> bool:
        """Hover over an element."""
        self._log_action("hover", element_id)
        
        pos = self.app.get_element_screen_position(element_id)
        if not pos:
            return False
        
        move_duration = 0.3 / self.speed
        self.controller.move_mouse(pos[0], pos[1], duration=move_duration)
        self._wait(duration)
        
        return True
    
    # =========================================================================
    # Keyboard actions
    # =========================================================================
    
    def type_text(self, text: str) -> None:
        """Type text with human-like timing."""
        self._log_action("type", text[:20] + "..." if len(text) > 20 else text)
        self.controller.type_text(text, wpm=int(self.typing_wpm * self.speed), human_like=self.human_like)
    
    def press_key(self, key: str) -> None:
        """Press a key."""
        self._log_action("key", key)
        self.controller.press_key(key)
        self._wait(0.05)
    
    def press_tab(self) -> None:
        """Press Tab to move to next element."""
        self.press_key("tab")
    
    def press_enter(self) -> None:
        """Press Enter to submit."""
        self.press_key("enter")
    
    def press_escape(self) -> None:
        """Press Escape."""
        self.press_key("escape")
    
    def hotkey(self, *keys: str) -> None:
        """Press a key combination."""
        self._log_action("hotkey", "+".join(keys))
        self.controller.hotkey(*keys)
        self._wait(0.05)
    
    # =========================================================================
    # Navigation
    # =========================================================================
    
    def navigate_to_screen(self, screen_id: str) -> bool:
        """Navigate to a specific screen."""
        self._log_action("navigate", screen_id)
        
        result = self.app.navigate(screen_id)
        if result and self.on_screen_change:
            self.on_screen_change(screen_id)
        
        self._wait(0.3)  # Wait for screen transition
        return result
    
    def get_current_screen(self) -> str:
        """Get current screen ID."""
        status = self.app.get_status()
        return status.get("screen", "unknown")
    
    # =========================================================================
    # Select/Dropdown
    # =========================================================================
    
    def select_option(self, element_id: str, option: str) -> bool:
        """Select an option from a dropdown."""
        self._log_action("select", f"{element_id}={option}")
        
        # Click to open dropdown
        if not self.click_element(element_id):
            return False
        
        self._wait(0.2)
        
        # Type to filter (many selects support this)
        self.controller.type_text(option[:15], wpm=120, human_like=False)
        self._wait(0.1)
        
        # Press enter to select
        self.controller.press_key("enter")
        self._wait(0.1)
        
        return True
    
    # =========================================================================
    # Workflow execution
    # =========================================================================
    
    def run_sequence(self, actions: List[Dict[str, Any]]) -> None:
        """
        Run a sequence of actions.
        
        Each action is a dict with:
        - type: "click", "type", "select", "navigate", "wait", "tab", "enter"
        - element: element ID (for click, select)
        - value: text to type or option to select
        - delay: delay before action
        """
        for i, action in enumerate(actions):
            action_type = action.get("type", "")
            element = action.get("element", "")
            value = action.get("value", "")
            delay = action.get("delay", 0)
            
            if delay > 0:
                self._wait(delay)
            
            if action_type == "click":
                self.click_element(element)
            
            elif action_type == "double_click":
                self.double_click_element(element)
            
            elif action_type == "type":
                self.type_text(str(value))
            
            elif action_type == "select":
                self.select_option(element, str(value))
            
            elif action_type == "navigate":
                self.navigate_to_screen(value)
            
            elif action_type == "wait":
                self._wait(float(value) if value else 1.0)
            
            elif action_type == "tab":
                self.press_tab()
            
            elif action_type == "enter":
                self.press_enter()
            
            elif action_type == "escape":
                self.press_escape()
            
            elif action_type == "hover":
                self.hover_element(element)


def demo_sequence() -> List[Dict[str, Any]]:
    """Demo sequence for the Credit Card Payments app."""
    return [
        # Login screen
        {"type": "click", "element": "username"},
        {"type": "type", "value": "admin@company.com"},
        {"type": "tab"},
        {"type": "type", "value": "SecureP@ssw0rd!"},
        {"type": "click", "element": "login-btn"},
        {"type": "wait", "value": 1},
        
        # Virtual Terminal
        {"type": "select", "element": "card-select", "value": "VISA 8701"},
        {"type": "click", "element": "amount"},
        {"type": "type", "value": "25934.00"},
        {"type": "tab"},
        {"type": "type", "value": "Invoice payment - October"},
        {"type": "click", "element": "process-btn"},
        {"type": "wait", "value": 1},
        
        # Payments List
        {"type": "click", "element": "new-payment-btn"},
        {"type": "wait", "value": 0.5},
        
        # Record Payment
        {"type": "select", "element": "vendor-select", "value": "A & A Fresh"},
        {"type": "select", "element": "contact-select", "value": "Chen Li"},
        {"type": "click", "element": "payment-amount"},
        {"type": "type", "value": "7452.00"},
        {"type": "select", "element": "payment-method", "value": "Cash"},
        {"type": "click", "element": "payment-date"},
        {"type": "type", "value": "10/21/2025"},
        {"type": "click", "element": "save-btn"},
    ]
