"""
Workflow player that replays workflows using OS-level control.
"""

from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from analyzer.models.workflow import WorkflowDefinition, Screen, Action, ActionType
from analyzer.playback.os_controller import OSController, MouseButton

logger = logging.getLogger(__name__)


class WorkflowPlayer:
    """
    Plays back a workflow definition using real OS mouse/keyboard control.
    
    This creates a realistic simulation that looks exactly like a real user
    by actually moving the mouse cursor and pressing keys.
    
    Usage:
        player = WorkflowPlayer.from_file("workflow.json")
        
        # Set screen offset if app window isn't at (0,0)
        player.set_window_offset(100, 50)
        
        # Play the workflow
        player.play()
    """
    
    def __init__(
        self,
        workflow: WorkflowDefinition,
        speed: float = 1.0,
        human_like: bool = True,
        typing_wpm: int = 60
    ):
        """
        Initialize the workflow player.
        
        Args:
            workflow: The workflow definition to play
            speed: Playback speed multiplier (1.0 = real-time, 2.0 = 2x speed)
            human_like: Enable human-like variations in timing
            typing_wpm: Words per minute for typing speed
        """
        self.workflow = workflow
        self.speed = speed
        self.human_like = human_like
        self.typing_wpm = typing_wpm
        
        self.controller = OSController()
        
        # Window offset (if app isn't at screen origin)
        self.offset_x = 0
        self.offset_y = 0
        
        # Callbacks
        self.on_action: Optional[Callable[[Action], None]] = None
        self.on_screen_change: Optional[Callable[[Screen], None]] = None
        self.on_complete: Optional[Callable[[], None]] = None
        
        # State
        self.is_playing = False
        self.is_paused = False
        self.current_action_index = 0
        self.current_screen: Optional[Screen] = None
        
        # Build screen lookup
        self._screens: Dict[str, Screen] = {s.id: s for s in workflow.screens}
    
    @classmethod
    def from_file(cls, path: Path, **kwargs) -> WorkflowPlayer:
        """Load workflow from file and create player."""
        workflow = WorkflowDefinition.from_file(Path(path))
        return cls(workflow, **kwargs)
    
    def set_window_offset(self, x: int, y: int) -> None:
        """
        Set the offset of the application window.
        
        All coordinates in the workflow will be adjusted by this offset.
        Use this when the app window isn't at screen position (0, 0).
        
        Args:
            x: X offset of window from screen left
            y: Y offset of window from screen top
        """
        self.offset_x = x
        self.offset_y = y
        logger.info(f"Window offset set to ({x}, {y})")
    
    def _adjust_coords(self, x: int, y: int) -> tuple:
        """Adjust coordinates for window offset."""
        return (x + self.offset_x, y + self.offset_y)
    
    def play(self, start_index: int = 0) -> None:
        """
        Play the workflow from the beginning or specified action.
        
        Args:
            start_index: Action index to start from
        """
        self.is_playing = True
        self.is_paused = False
        self.current_action_index = start_index
        
        logger.info(f"Starting playback: {self.workflow.name}")
        logger.info(f"Speed: {self.speed}x, Actions: {len(self.workflow.actions)}")
        
        # Navigate to start screen
        start_screen_id = self.workflow.start_screen_id
        if start_screen_id and start_screen_id in self._screens:
            self.current_screen = self._screens[start_screen_id]
            if self.on_screen_change:
                self.on_screen_change(self.current_screen)
        
        # Execute actions
        self._execute_actions()
    
    def pause(self) -> None:
        """Pause playback."""
        self.is_paused = True
        logger.info("Playback paused")
    
    def resume(self) -> None:
        """Resume playback."""
        if self.is_paused:
            self.is_paused = False
            logger.info("Playback resumed")
            self._execute_actions()
    
    def stop(self) -> None:
        """Stop playback."""
        self.is_playing = False
        self.is_paused = False
        logger.info("Playback stopped")
    
    def _execute_actions(self) -> None:
        """Execute workflow actions."""
        while (self.is_playing and 
               not self.is_paused and 
               self.current_action_index < len(self.workflow.actions)):
            
            action = self.workflow.actions[self.current_action_index]
            
            # Handle screen changes
            if action.screen_id and action.screen_id in self._screens:
                new_screen = self._screens[action.screen_id]
                if new_screen != self.current_screen:
                    self.current_screen = new_screen
                    if self.on_screen_change:
                        self.on_screen_change(new_screen)
            
            # Pre-action delay
            delay = (action.delay_before or 0) / self.speed
            if delay > 0:
                time.sleep(delay)
            
            # Execute action
            logger.debug(f"Executing action {self.current_action_index}: {action.type.value}")
            self._execute_action(action)
            
            # Callback
            if self.on_action:
                self.on_action(action)
            
            # Handle navigation
            if action.next_screen_id and action.next_screen_id in self._screens:
                self.current_screen = self._screens[action.next_screen_id]
                if self.on_screen_change:
                    self.on_screen_change(self.current_screen)
            
            self.current_action_index += 1
        
        # Completion
        if self.current_action_index >= len(self.workflow.actions):
            self.is_playing = False
            logger.info("Playback complete")
            if self.on_complete:
                self.on_complete()
    
    def _execute_action(self, action: Action) -> None:
        """Execute a single action."""
        # Get target position
        target_x, target_y = self._get_action_position(action)
        
        if action.type == ActionType.CLICK:
            self._execute_click(target_x, target_y)
        
        elif action.type == ActionType.DOUBLE_CLICK:
            self._execute_double_click(target_x, target_y)
        
        elif action.type == ActionType.RIGHT_CLICK:
            self._execute_right_click(target_x, target_y)
        
        elif action.type == ActionType.TYPE:
            self._execute_type(action.value, target_x, target_y)
        
        elif action.type == ActionType.SELECT:
            self._execute_select(action.value, target_x, target_y)
        
        elif action.type in (ActionType.CHECK, ActionType.UNCHECK, ActionType.TOGGLE):
            self._execute_click(target_x, target_y)
        
        elif action.type == ActionType.SCROLL:
            scroll_amount = int(action.value) if action.value else 3
            self.controller.scroll(scroll_amount, target_x, target_y)
        
        elif action.type == ActionType.HOVER:
            duration = (action.duration or 500) / 1000 / self.speed
            self.controller.move_mouse(target_x, target_y, duration=duration)
        
        elif action.type == ActionType.DRAG:
            # Would need end coordinates from action
            pass
        
        elif action.type == ActionType.WAIT:
            duration = (action.duration or 1000) / 1000 / self.speed
            time.sleep(duration)
        
        elif action.type == ActionType.NAVIGATE:
            # Navigation is handled via next_screen_id
            pass
        
        elif action.type == ActionType.SUBMIT:
            self.controller.press_key('enter')
    
    def _get_action_position(self, action: Action) -> tuple:
        """Get the target position for an action."""
        # Use explicit coordinates if provided
        if action.x is not None and action.y is not None:
            return self._adjust_coords(action.x, action.y)
        
        # Otherwise, find element and get its center
        if action.element_id and self.current_screen:
            for element in self.current_screen.elements:
                if element.id == action.element_id:
                    center = element.bounds.center
                    return self._adjust_coords(center[0], center[1])
        
        # Fallback to current mouse position
        pos = self.controller.get_mouse_position()
        return (pos.x, pos.y)
    
    def _execute_click(self, x: int, y: int) -> None:
        """Execute a click action."""
        # Move to target with human-like motion
        duration = 0.3 / self.speed if self.human_like else 0.1 / self.speed
        self.controller.move_mouse(x, y, duration=duration, human_like=self.human_like)
        
        # Small pause before clicking (human-like)
        if self.human_like:
            time.sleep(0.05 / self.speed)
        
        self.controller.click()
    
    def _execute_double_click(self, x: int, y: int) -> None:
        """Execute a double-click action."""
        duration = 0.3 / self.speed if self.human_like else 0.1 / self.speed
        self.controller.move_mouse(x, y, duration=duration, human_like=self.human_like)
        self.controller.double_click()
    
    def _execute_right_click(self, x: int, y: int) -> None:
        """Execute a right-click action."""
        duration = 0.3 / self.speed if self.human_like else 0.1 / self.speed
        self.controller.move_mouse(x, y, duration=duration, human_like=self.human_like)
        self.controller.right_click()
    
    def _execute_type(
        self,
        text: Any,
        x: Optional[int] = None,
        y: Optional[int] = None
    ) -> None:
        """Execute a typing action."""
        if text is None:
            return
        
        # Click to focus if position provided
        if x is not None and y is not None:
            self._execute_click(x, y)
            time.sleep(0.1 / self.speed)
        
        # Type the text
        text_str = str(text)
        adjusted_wpm = int(self.typing_wpm * self.speed)
        self.controller.type_text(text_str, wpm=adjusted_wpm, human_like=self.human_like)
    
    def _execute_select(
        self,
        value: Any,
        x: int,
        y: int
    ) -> None:
        """Execute a select/dropdown action."""
        # Click to open dropdown
        self._execute_click(x, y)
        time.sleep(0.2 / self.speed)
        
        # Type to search (many dropdowns support this)
        if value:
            self.controller.type_text(str(value), wpm=120, human_like=False)
            time.sleep(0.1 / self.speed)
            self.controller.press_key('enter')
    
    def get_progress(self) -> dict:
        """Get current playback progress."""
        total = len(self.workflow.actions)
        return {
            "current_action": self.current_action_index,
            "total_actions": total,
            "progress_percent": (self.current_action_index / total * 100) if total > 0 else 0,
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "current_screen": self.current_screen.name if self.current_screen else None,
        }
