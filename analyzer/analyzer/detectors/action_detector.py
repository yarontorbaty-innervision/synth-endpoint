"""
User action detection from video frames.
"""

from typing import Any
import logging
import uuid

import numpy as np
from PIL import Image

from analyzer.config import ActionDetectionConfig
from analyzer.models.frame import Frame
from analyzer.models.detection import UIDetection, ActionDetection
from analyzer.models.workflow import ActionType


logger = logging.getLogger(__name__)


class ActionDetector:
    """
    Detects user actions by analyzing frame sequences.
    
    Detects:
    - Mouse clicks (by analyzing cursor movement and pauses)
    - Typing (by analyzing text field changes)
    - Scrolling (by analyzing content movement)
    - Navigation (by analyzing screen transitions)
    """
    
    def __init__(self, config: ActionDetectionConfig | None = None):
        self.config = config or ActionDetectionConfig()
    
    def detect_actions(
        self,
        frames: list[Frame],
        ui_detections: list[UIDetection]
    ) -> list[ActionDetection]:
        """
        Detect user actions from a sequence of frames.
        
        Args:
            frames: List of video frames
            ui_detections: UI detection results for each frame
            
        Returns:
            List of detected actions in chronological order
        """
        if len(frames) < 2:
            return []
        
        actions = []
        
        # Detect various action types
        click_actions = self._detect_clicks(frames, ui_detections)
        typing_actions = self._detect_typing(frames, ui_detections)
        scroll_actions = self._detect_scrolling(frames)
        
        # Combine and sort by timestamp
        all_actions = click_actions + typing_actions + scroll_actions
        all_actions.sort(key=lambda a: a.timestamp)
        
        # Filter out duplicate/overlapping actions
        filtered_actions = self._filter_actions(all_actions)
        
        return filtered_actions
    
    def _detect_clicks(
        self,
        frames: list[Frame],
        ui_detections: list[UIDetection]
    ) -> list[ActionDetection]:
        """
        Detect click actions by analyzing cursor position and UI changes.
        
        Clicks are identified when:
        1. Cursor pauses over a clickable element
        2. UI state changes (e.g., button appears pressed)
        3. Screen transitions occur
        """
        clicks = []
        
        for i in range(1, len(frames)):
            prev_frame = frames[i - 1]
            curr_frame = frames[i]
            prev_detection = ui_detections[i - 1]
            curr_detection = ui_detections[i]
            
            # Analyze frame difference to detect click effects
            diff = self._compute_frame_diff(prev_frame.image, curr_frame.image)
            
            # If significant local change detected, likely a click
            if diff > self.config.click_threshold:
                # Find the region of change
                change_region = self._find_change_region(prev_frame.image, curr_frame.image)
                
                if change_region:
                    x, y = change_region
                    
                    # Check if there's a clickable element at this position
                    target_element = prev_detection.get_element_at(x, y)
                    
                    action = ActionDetection(
                        type=ActionType.CLICK,
                        timestamp=curr_frame.timestamp,
                        frame_number=curr_frame.frame_number,
                        x=x,
                        y=y,
                        target_element_id=target_element.id if target_element else None,
                        confidence=min(diff, 1.0)
                    )
                    
                    clicks.append(action)
        
        return clicks
    
    def _detect_typing(
        self,
        frames: list[Frame],
        ui_detections: list[UIDetection]
    ) -> list[ActionDetection]:
        """
        Detect typing actions by analyzing text field changes.
        """
        if not self.config.typing_detection:
            return []
        
        typing_actions = []
        
        # Track text fields across frames
        text_field_values: dict[str, str] = {}
        
        for i, (frame, detection) in enumerate(zip(frames, ui_detections)):
            for element in detection.elements:
                if element.type.value in ("text_input", "textarea", "password_input"):
                    current_value = str(element.value) if element.value else ""
                    
                    if element.id in text_field_values:
                        prev_value = text_field_values[element.id]
                        
                        if current_value != prev_value:
                            # Text has changed - typing detected
                            new_text = current_value[len(prev_value):] if current_value.startswith(prev_value) else current_value
                            
                            action = ActionDetection(
                                type=ActionType.TYPE,
                                timestamp=frame.timestamp,
                                frame_number=frame.frame_number,
                                text=new_text,
                                x=element.bounds.center[0],
                                y=element.bounds.center[1],
                                target_element_id=element.id,
                                confidence=0.9
                            )
                            
                            typing_actions.append(action)
                    
                    text_field_values[element.id] = current_value
        
        return typing_actions
    
    def _detect_scrolling(self, frames: list[Frame]) -> list[ActionDetection]:
        """
        Detect scroll actions by analyzing content movement.
        """
        if not self.config.scroll_detection:
            return []
        
        scroll_actions = []
        
        for i in range(1, len(frames)):
            prev_frame = frames[i - 1]
            curr_frame = frames[i]
            
            # Detect vertical scrolling by analyzing image shift
            scroll_delta = self._detect_scroll_delta(prev_frame.image, curr_frame.image)
            
            if abs(scroll_delta) > 10:  # Minimum scroll threshold
                action = ActionDetection(
                    type=ActionType.SCROLL,
                    timestamp=curr_frame.timestamp,
                    frame_number=curr_frame.frame_number,
                    scroll_delta_y=scroll_delta,
                    confidence=0.8
                )
                
                scroll_actions.append(action)
        
        return scroll_actions
    
    def _compute_frame_diff(self, img1: Image.Image, img2: Image.Image) -> float:
        """Compute normalized difference between two frames."""
        arr1 = np.array(img1.convert("L"))
        arr2 = np.array(img2.convert("L"))
        
        if arr1.shape != arr2.shape:
            return 1.0
        
        diff = np.abs(arr1.astype(float) - arr2.astype(float))
        return diff.sum() / (255 * arr1.size)
    
    def _find_change_region(
        self,
        img1: Image.Image,
        img2: Image.Image
    ) -> tuple[int, int] | None:
        """Find the center of the region with most change."""
        arr1 = np.array(img1.convert("L"))
        arr2 = np.array(img2.convert("L"))
        
        if arr1.shape != arr2.shape:
            return None
        
        diff = np.abs(arr1.astype(float) - arr2.astype(float))
        
        # Find region with highest change using a simple approach
        # In production, this would use more sophisticated methods
        threshold = diff.max() * 0.5
        changed_pixels = np.where(diff > threshold)
        
        if len(changed_pixels[0]) == 0:
            return None
        
        # Return center of changed region
        y = int(np.mean(changed_pixels[0]))
        x = int(np.mean(changed_pixels[1]))
        
        return (x, y)
    
    def _detect_scroll_delta(self, img1: Image.Image, img2: Image.Image) -> int:
        """
        Detect vertical scroll amount between frames.
        
        Uses template matching to find how much content has shifted.
        """
        import cv2
        
        arr1 = np.array(img1.convert("L"))
        arr2 = np.array(img2.convert("L"))
        
        if arr1.shape != arr2.shape:
            return 0
        
        height = arr1.shape[0]
        
        # Take a horizontal strip from the middle of the first image
        strip_height = height // 10
        strip_start = height // 2 - strip_height // 2
        template = arr1[strip_start:strip_start + strip_height, :]
        
        # Search for this strip in the second image
        result = cv2.matchTemplate(arr2, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        if max_val < 0.7:
            return 0  # Not a good match, probably not scrolling
        
        # Calculate scroll delta
        delta = max_loc[1] - strip_start
        
        return delta
    
    def _filter_actions(self, actions: list[ActionDetection]) -> list[ActionDetection]:
        """
        Filter out duplicate or overlapping actions.
        """
        if not actions:
            return []
        
        filtered = [actions[0]]
        
        for action in actions[1:]:
            prev_action = filtered[-1]
            
            # Check time gap
            time_gap = action.timestamp - prev_action.timestamp
            
            if time_gap < self.config.min_action_gap:
                # Too close together - might be duplicate
                # Keep the one with higher confidence
                if action.confidence > prev_action.confidence:
                    filtered[-1] = action
            else:
                filtered.append(action)
        
        return filtered
