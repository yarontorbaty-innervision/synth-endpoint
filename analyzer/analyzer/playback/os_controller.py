"""
OS-level controller for mouse and keyboard.

Uses pyautogui for cross-platform control of:
- Mouse movement with human-like curves
- Mouse clicks (left, right, double)
- Keyboard typing with realistic timing
- Key combinations (shortcuts)
"""

from __future__ import annotations
import platform
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MouseButton(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


@dataclass
class MousePosition:
    x: int
    y: int


class OSController:
    """
    Controls the actual OS mouse and keyboard.
    
    This makes the synthetic endpoint indistinguishable from a real user
    by controlling the actual cursor and sending real key events.
    
    Usage:
        controller = OSController()
        
        # Move mouse with human-like motion
        controller.move_mouse(500, 300, duration=0.5)
        
        # Click
        controller.click()
        
        # Type with realistic speed
        controller.type_text("Hello World", wpm=60)
    """
    
    def __init__(self, fail_safe: bool = True):
        """
        Initialize the OS controller.
        
        Args:
            fail_safe: If True, moving mouse to corner aborts (pyautogui safety feature)
        """
        self._pyautogui = None
        self._pynput_mouse = None
        self._pynput_keyboard = None
        self.fail_safe = fail_safe
        self.platform = platform.system()
        
        self._init_backends()
    
    def _init_backends(self) -> None:
        """Initialize input control backends."""
        # Try pyautogui first (easier API)
        try:
            import pyautogui
            pyautogui.FAILSAFE = self.fail_safe
            pyautogui.PAUSE = 0.01  # Small pause between actions
            self._pyautogui = pyautogui
            logger.info("Using pyautogui for OS control")
        except ImportError:
            logger.warning("pyautogui not available, trying pynput")
        
        # Fallback to pynput
        if self._pyautogui is None:
            try:
                from pynput.mouse import Controller as MouseController
                from pynput.keyboard import Controller as KeyboardController
                self._pynput_mouse = MouseController()
                self._pynput_keyboard = KeyboardController()
                logger.info("Using pynput for OS control")
            except ImportError:
                raise RuntimeError(
                    "No input control library available. "
                    "Install with: pip install pyautogui pynput"
                )
    
    # =========================================================================
    # Mouse Control
    # =========================================================================
    
    def get_mouse_position(self) -> MousePosition:
        """Get current mouse cursor position."""
        if self._pyautogui:
            pos = self._pyautogui.position()
            return MousePosition(x=pos[0], y=pos[1])
        else:
            pos = self._pynput_mouse.position
            return MousePosition(x=int(pos[0]), y=int(pos[1]))
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        if self._pyautogui:
            return self._pyautogui.size()
        else:
            # Fallback - common resolution
            return (1920, 1080)
    
    def move_mouse(
        self,
        x: int,
        y: int,
        duration: float = 0.5,
        human_like: bool = True
    ) -> None:
        """
        Move mouse to position with optional human-like motion.
        
        Args:
            x: Target X coordinate
            y: Target Y coordinate
            duration: Time to complete movement (seconds)
            human_like: Use curved, natural movement path
        """
        if self._pyautogui:
            if human_like:
                # Use easeOutQuad for natural deceleration
                self._pyautogui.moveTo(
                    x, y,
                    duration=duration,
                    tween=self._pyautogui.easeOutQuad
                )
            else:
                self._pyautogui.moveTo(x, y, duration=duration)
        else:
            # pynput - implement our own smooth movement
            self._smooth_move_pynput(x, y, duration, human_like)
    
    def move_mouse_relative(
        self,
        dx: int,
        dy: int,
        duration: float = 0.3
    ) -> None:
        """Move mouse relative to current position."""
        if self._pyautogui:
            self._pyautogui.move(dx, dy, duration=duration)
        else:
            current = self.get_mouse_position()
            self.move_mouse(current.x + dx, current.y + dy, duration)
    
    def click(
        self,
        button: MouseButton = MouseButton.LEFT,
        clicks: int = 1,
        interval: float = 0.1
    ) -> None:
        """
        Perform mouse click(s).
        
        Args:
            button: Which mouse button to click
            clicks: Number of clicks (2 for double-click)
            interval: Time between clicks
        """
        if self._pyautogui:
            self._pyautogui.click(
                button=button.value,
                clicks=clicks,
                interval=interval
            )
        else:
            from pynput.mouse import Button
            btn = {
                MouseButton.LEFT: Button.left,
                MouseButton.RIGHT: Button.right,
                MouseButton.MIDDLE: Button.middle,
            }[button]
            
            for _ in range(clicks):
                self._pynput_mouse.click(btn)
                if clicks > 1:
                    time.sleep(interval)
    
    def double_click(self, button: MouseButton = MouseButton.LEFT) -> None:
        """Perform double-click."""
        self.click(button=button, clicks=2, interval=0.05)
    
    def right_click(self) -> None:
        """Perform right-click."""
        self.click(button=MouseButton.RIGHT)
    
    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> None:
        """Press and hold mouse button."""
        if self._pyautogui:
            self._pyautogui.mouseDown(button=button.value)
        else:
            from pynput.mouse import Button
            btn = Button.left if button == MouseButton.LEFT else Button.right
            self._pynput_mouse.press(btn)
    
    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> None:
        """Release mouse button."""
        if self._pyautogui:
            self._pyautogui.mouseUp(button=button.value)
        else:
            from pynput.mouse import Button
            btn = Button.left if button == MouseButton.LEFT else Button.right
            self._pynput_mouse.release(btn)
    
    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        button: MouseButton = MouseButton.LEFT
    ) -> None:
        """Drag from one position to another."""
        self.move_mouse(start_x, start_y, duration=0.2)
        time.sleep(0.05)
        
        if self._pyautogui:
            self._pyautogui.drag(
                end_x - start_x,
                end_y - start_y,
                duration=duration,
                button=button.value
            )
        else:
            self.mouse_down(button)
            time.sleep(0.05)
            self.move_mouse(end_x, end_y, duration=duration)
            self.mouse_up(button)
    
    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """
        Scroll the mouse wheel.
        
        Args:
            clicks: Positive = up, negative = down
            x, y: Optional position to scroll at
        """
        if x is not None and y is not None:
            self.move_mouse(x, y, duration=0.1)
        
        if self._pyautogui:
            self._pyautogui.scroll(clicks)
        else:
            self._pynput_mouse.scroll(0, clicks)
    
    # =========================================================================
    # Keyboard Control
    # =========================================================================
    
    def type_text(
        self,
        text: str,
        wpm: int = 60,
        human_like: bool = True
    ) -> None:
        """
        Type text with realistic timing.
        
        Args:
            text: Text to type
            wpm: Words per minute (average ~60 for normal typing)
            human_like: Add random variations to timing
        """
        # Calculate base delay per character
        # Average word = 5 characters, so chars/min = wpm * 5
        chars_per_second = (wpm * 5) / 60
        base_delay = 1.0 / chars_per_second
        
        for char in text:
            delay = base_delay
            
            if human_like:
                # Add random variation (-30% to +50%)
                delay *= random.uniform(0.7, 1.5)
                
                # Longer pause after punctuation
                if char in '.!?':
                    delay += random.uniform(0.2, 0.5)
                elif char in ',;:':
                    delay += random.uniform(0.1, 0.2)
                
                # Occasional longer pause (thinking)
                if random.random() < 0.02:
                    delay += random.uniform(0.3, 0.8)
            
            self._type_char(char)
            time.sleep(delay)
    
    def _type_char(self, char: str) -> None:
        """Type a single character."""
        if self._pyautogui:
            self._pyautogui.write(char, interval=0)
        else:
            self._pynput_keyboard.type(char)
    
    def press_key(self, key: str) -> None:
        """
        Press a single key.
        
        Args:
            key: Key name (e.g., 'enter', 'tab', 'escape', 'a', 'f1')
        """
        if self._pyautogui:
            self._pyautogui.press(key)
        else:
            from pynput.keyboard import Key
            key_map = {
                'enter': Key.enter,
                'return': Key.enter,
                'tab': Key.tab,
                'escape': Key.esc,
                'esc': Key.esc,
                'backspace': Key.backspace,
                'delete': Key.delete,
                'space': Key.space,
                'up': Key.up,
                'down': Key.down,
                'left': Key.left,
                'right': Key.right,
                'home': Key.home,
                'end': Key.end,
                'pageup': Key.page_up,
                'pagedown': Key.page_down,
            }
            
            pynput_key = key_map.get(key.lower())
            if pynput_key:
                self._pynput_keyboard.press(pynput_key)
                self._pynput_keyboard.release(pynput_key)
            else:
                self._pynput_keyboard.type(key)
    
    def hotkey(self, *keys: str) -> None:
        """
        Press a key combination (hotkey).
        
        Args:
            keys: Keys to press together (e.g., 'ctrl', 'c' for Ctrl+C)
        """
        if self._pyautogui:
            self._pyautogui.hotkey(*keys)
        else:
            from pynput.keyboard import Key
            
            modifier_map = {
                'ctrl': Key.ctrl,
                'control': Key.ctrl,
                'alt': Key.alt,
                'option': Key.alt,
                'shift': Key.shift,
                'cmd': Key.cmd,
                'command': Key.cmd,
                'win': Key.cmd,
            }
            
            # Press all modifiers
            pressed = []
            for key in keys[:-1]:
                mod = modifier_map.get(key.lower())
                if mod:
                    self._pynput_keyboard.press(mod)
                    pressed.append(mod)
            
            # Press the final key
            self.press_key(keys[-1])
            
            # Release modifiers in reverse order
            for mod in reversed(pressed):
                self._pynput_keyboard.release(mod)
    
    def key_down(self, key: str) -> None:
        """Press and hold a key."""
        if self._pyautogui:
            self._pyautogui.keyDown(key)
        else:
            from pynput.keyboard import Key
            # Simplified - would need full key mapping
            self._pynput_keyboard.press(key)
    
    def key_up(self, key: str) -> None:
        """Release a key."""
        if self._pyautogui:
            self._pyautogui.keyUp(key)
        else:
            self._pynput_keyboard.release(key)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _smooth_move_pynput(
        self,
        target_x: int,
        target_y: int,
        duration: float,
        human_like: bool
    ) -> None:
        """Implement smooth mouse movement for pynput."""
        current = self.get_mouse_position()
        start_x, start_y = current.x, current.y
        
        steps = max(int(duration * 60), 10)  # ~60 FPS
        step_duration = duration / steps
        
        for i in range(steps + 1):
            t = i / steps
            
            if human_like:
                # Ease out quad
                t = 1 - (1 - t) * (1 - t)
            
            x = int(start_x + (target_x - start_x) * t)
            y = int(start_y + (target_y - start_y) * t)
            
            self._pynput_mouse.position = (x, y)
            time.sleep(step_duration)
    
    def wait(self, seconds: float) -> None:
        """Wait for a specified duration."""
        time.sleep(seconds)
    
    def alert(self, message: str) -> None:
        """Show an alert dialog (useful for debugging)."""
        if self._pyautogui:
            self._pyautogui.alert(message)
        else:
            print(f"ALERT: {message}")
