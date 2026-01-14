"""
VLM-powered video analyzer.
"""

from __future__ import annotations
import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from analyzer.vlm.client import VLMClient, VLMConfig
from analyzer.vlm.prompts import (
    get_ui_detection_prompt,
    get_action_detection_prompt,
    get_workflow_mapping_prompt,
    get_screen_similarity_prompt,
    get_data_extraction_prompt,
)
from analyzer.models.workflow import (
    WorkflowDefinition,
    Screen,
    Action,
    UIElement,
    UIElementType,
    ActionType,
    BoundingBox,
)
from analyzer.models.frame import Frame

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of VLM analysis."""
    success: bool
    data: Optional[Dict[str, Any]]
    raw_response: str
    error: Optional[str] = None


class VLMAnalyzer:
    """
    Analyzes video frames using Vision Language Models.
    
    This is the core analysis engine that:
    1. Detects UI elements in frames
    2. Identifies user actions between frames
    3. Maps frames to screens
    4. Generates workflow definitions
    """
    
    def __init__(self, config: Optional[VLMConfig] = None):
        self.config = config or VLMConfig()
        self.client = VLMClient(self.config)
    
    async def analyze_frame(self, frame: Frame) -> AnalysisResult:
        """
        Analyze a single frame to detect UI elements.
        
        Args:
            frame: Video frame to analyze
            
        Returns:
            AnalysisResult with detected UI elements
        """
        prompt = get_ui_detection_prompt()
        
        try:
            response = await self.client.analyze_image(frame.image, prompt)
            data = self._parse_json_response(response)
            
            return AnalysisResult(
                success=True,
                data=data,
                raw_response=response
            )
        except Exception as e:
            logger.error(f"Frame analysis failed: {e}")
            return AnalysisResult(
                success=False,
                data=None,
                raw_response="",
                error=str(e)
            )
    
    async def detect_action(
        self,
        frame_before: Frame,
        frame_after: Frame
    ) -> AnalysisResult:
        """
        Detect user action between two consecutive frames.
        
        Args:
            frame_before: Frame before the action
            frame_after: Frame after the action
            
        Returns:
            AnalysisResult with detected action
        """
        prompt = get_action_detection_prompt()
        
        try:
            response = await self.client.analyze_images(
                [frame_before.image, frame_after.image],
                prompt
            )
            data = self._parse_json_response(response)
            
            return AnalysisResult(
                success=True,
                data=data,
                raw_response=response
            )
        except Exception as e:
            logger.error(f"Action detection failed: {e}")
            return AnalysisResult(
                success=False,
                data=None,
                raw_response="",
                error=str(e)
            )
    
    async def compare_screens(
        self,
        frame1: Frame,
        frame2: Frame
    ) -> AnalysisResult:
        """
        Compare two frames to determine if they show the same screen.
        
        Args:
            frame1: First frame
            frame2: Second frame
            
        Returns:
            AnalysisResult with similarity assessment
        """
        prompt = get_screen_similarity_prompt()
        
        try:
            response = await self.client.analyze_images(
                [frame1.image, frame2.image],
                prompt
            )
            data = self._parse_json_response(response)
            
            return AnalysisResult(
                success=True,
                data=data,
                raw_response=response
            )
        except Exception as e:
            logger.error(f"Screen comparison failed: {e}")
            return AnalysisResult(
                success=False,
                data=None,
                raw_response="",
                error=str(e)
            )
    
    async def extract_data(self, frame: Frame) -> AnalysisResult:
        """
        Extract text data and values from a frame.
        
        Args:
            frame: Frame to extract data from
            
        Returns:
            AnalysisResult with extracted data
        """
        prompt = get_data_extraction_prompt()
        
        try:
            response = await self.client.analyze_image(frame.image, prompt)
            data = self._parse_json_response(response)
            
            return AnalysisResult(
                success=True,
                data=data,
                raw_response=response
            )
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            return AnalysisResult(
                success=False,
                data=None,
                raw_response="",
                error=str(e)
            )
    
    async def analyze_workflow(
        self,
        frames: List[Frame],
        batch_size: int = 8
    ) -> WorkflowDefinition:
        """
        Analyze a sequence of frames and generate a workflow definition.
        
        This is the main entry point for video analysis.
        
        Args:
            frames: List of video frames
            batch_size: Number of frames to analyze in parallel
            
        Returns:
            Complete WorkflowDefinition
        """
        logger.info(f"Analyzing {len(frames)} frames...")
        
        # Step 1: Analyze keyframes to identify unique screens
        logger.info("Step 1: Identifying unique screens...")
        screen_analyses = await self._analyze_screens(frames, batch_size)
        
        # Step 2: Detect actions between frames
        logger.info("Step 2: Detecting user actions...")
        actions = await self._detect_all_actions(frames, batch_size)
        
        # Step 3: Build workflow from analyses
        logger.info("Step 3: Building workflow definition...")
        workflow = self._build_workflow(frames, screen_analyses, actions)
        
        return workflow
    
    async def _analyze_screens(
        self,
        frames: List[Frame],
        batch_size: int
    ) -> List[AnalysisResult]:
        """Analyze frames for UI elements in batches."""
        results = []
        
        for i in range(0, len(frames), batch_size):
            batch = frames[i:i + batch_size]
            
            # Analyze batch in parallel
            tasks = [self.analyze_frame(frame) for frame in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            logger.info(f"Analyzed {min(i + batch_size, len(frames))}/{len(frames)} frames")
        
        return results
    
    async def _detect_all_actions(
        self,
        frames: List[Frame],
        batch_size: int
    ) -> List[AnalysisResult]:
        """Detect actions between consecutive frames."""
        if len(frames) < 2:
            return []
        
        results = []
        frame_pairs = list(zip(frames[:-1], frames[1:]))
        
        for i in range(0, len(frame_pairs), batch_size):
            batch = frame_pairs[i:i + batch_size]
            
            tasks = [
                self.detect_action(before, after)
                for before, after in batch
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            logger.info(f"Analyzed {min(i + batch_size, len(frame_pairs))}/{len(frame_pairs)} frame transitions")
        
        return results
    
    def _build_workflow(
        self,
        frames: List[Frame],
        screen_analyses: List[AnalysisResult],
        action_analyses: List[AnalysisResult]
    ) -> WorkflowDefinition:
        """Build workflow definition from analysis results."""
        
        # Group similar screens
        screens: List[Screen] = []
        screen_map: Dict[int, str] = {}  # frame index -> screen id
        
        for i, analysis in enumerate(screen_analyses):
            if not analysis.success or not analysis.data:
                continue
            
            data = analysis.data
            frame = frames[i]
            
            # Check if this is a new screen or existing one
            screen_id = self._find_or_create_screen(
                screens, data, frame, screen_map
            )
            screen_map[i] = screen_id
        
        # Build action sequence
        actions: List[Action] = []
        
        for i, analysis in enumerate(action_analyses):
            if not analysis.success or not analysis.data:
                continue
            
            data = analysis.data
            
            if not data.get("action_detected", False):
                continue
            
            action_data = data.get("action", {})
            action_type = self._map_action_type(action_data.get("type", "click"))
            
            # Get screen ID for this action
            screen_id = screen_map.get(i, screens[0].id if screens else "unknown")
            next_screen_id = screen_map.get(i + 1)
            
            action = Action(
                id=f"action_{uuid.uuid4().hex[:8]}",
                type=action_type,
                screen_id=screen_id,
                value=action_data.get("value"),
                delay_before=0.5,
                next_screen_id=next_screen_id if next_screen_id != screen_id else None,
                timestamp=frames[i].timestamp if i < len(frames) else None,
                confidence=data.get("confidence", 0.8)
            )
            
            # Try to set position from target bounds
            bounds = action_data.get("target_bounds")
            if bounds:
                action.x = bounds.get("x", 0) + bounds.get("width", 0) // 2
                action.y = bounds.get("y", 0) + bounds.get("height", 0) // 2
            
            actions.append(action)
        
        # Create workflow
        workflow = WorkflowDefinition(
            id=f"workflow_{uuid.uuid4().hex[:8]}",
            name="Extracted Workflow",
            description="Workflow automatically extracted from video recording",
            screens=screens,
            actions=actions,
            start_screen_id=screens[0].id if screens else None
        )
        
        return workflow
    
    def _find_or_create_screen(
        self,
        screens: List[Screen],
        data: dict,
        frame: Frame,
        screen_map: Dict[int, str]
    ) -> str:
        """Find existing screen or create new one."""
        
        screen_name = data.get("screen_name", f"Screen {len(screens) + 1}")
        
        # Simple heuristic: if screen name matches, use existing
        for screen in screens:
            if screen.name == screen_name:
                return screen.id
        
        # Create new screen
        elements = self._parse_elements(data.get("elements", []))
        
        screen = Screen(
            id=f"screen_{uuid.uuid4().hex[:8]}",
            name=screen_name,
            description=data.get("screen_description"),
            width=frame.metadata.width,
            height=frame.metadata.height,
            elements=elements,
            source_frame=frame.frame_number,
            timestamp=frame.timestamp
        )
        
        screens.append(screen)
        return screen.id
    
    def _parse_elements(self, elements_data: List[dict]) -> List[UIElement]:
        """Parse element data into UIElement objects."""
        elements = []
        
        for elem_data in elements_data:
            try:
                elem_type = self._map_element_type(elem_data.get("type", "label"))
                
                bounds_data = elem_data.get("bounds", {})
                bounds = BoundingBox(
                    x=bounds_data.get("x", 0),
                    y=bounds_data.get("y", 0),
                    width=bounds_data.get("width", 100),
                    height=bounds_data.get("height", 30)
                )
                
                element = UIElement(
                    id=f"elem_{uuid.uuid4().hex[:8]}",
                    type=elem_type,
                    bounds=bounds,
                    text=elem_data.get("text"),
                    placeholder=elem_data.get("placeholder"),
                    value=elem_data.get("value"),
                    label=elem_data.get("label"),
                    enabled=elem_data.get("enabled", True)
                )
                
                elements.append(element)
            except Exception as e:
                logger.warning(f"Failed to parse element: {e}")
        
        return elements
    
    def _map_element_type(self, type_str: str) -> UIElementType:
        """Map string to UIElementType enum."""
        type_map = {
            "text_input": UIElementType.TEXT_INPUT,
            "textbox": UIElementType.TEXT_INPUT,
            "input": UIElementType.TEXT_INPUT,
            "password_input": UIElementType.PASSWORD_INPUT,
            "password": UIElementType.PASSWORD_INPUT,
            "textarea": UIElementType.TEXTAREA,
            "dropdown": UIElementType.DROPDOWN,
            "select": UIElementType.DROPDOWN,
            "combobox": UIElementType.COMBOBOX,
            "checkbox": UIElementType.CHECKBOX,
            "radio": UIElementType.RADIO,
            "toggle": UIElementType.TOGGLE,
            "switch": UIElementType.TOGGLE,
            "button": UIElementType.BUTTON,
            "link": UIElementType.LINK,
            "tab": UIElementType.TAB,
            "menu_item": UIElementType.MENU_ITEM,
            "menu": UIElementType.MENU_ITEM,
            "table": UIElementType.TABLE,
            "date_picker": UIElementType.DATE_PICKER,
            "datepicker": UIElementType.DATE_PICKER,
            "slider": UIElementType.SLIDER,
            "label": UIElementType.LABEL,
            "text": UIElementType.LABEL,
            "heading": UIElementType.HEADING,
            "title": UIElementType.HEADING,
            "icon": UIElementType.ICON,
            "image": UIElementType.IMAGE,
            "modal": UIElementType.MODAL,
            "dialog": UIElementType.MODAL,
            "panel": UIElementType.PANEL,
            "sidebar": UIElementType.SIDEBAR,
            "toolbar": UIElementType.TOOLBAR,
            "navigation": UIElementType.NAVIGATION,
            "navbar": UIElementType.NAVIGATION,
        }
        
        return type_map.get(type_str.lower(), UIElementType.LABEL)
    
    def _map_action_type(self, type_str: str) -> ActionType:
        """Map string to ActionType enum."""
        type_map = {
            "click": ActionType.CLICK,
            "double_click": ActionType.DOUBLE_CLICK,
            "doubleclick": ActionType.DOUBLE_CLICK,
            "right_click": ActionType.RIGHT_CLICK,
            "rightclick": ActionType.RIGHT_CLICK,
            "type": ActionType.TYPE,
            "typing": ActionType.TYPE,
            "input": ActionType.TYPE,
            "select": ActionType.SELECT,
            "check": ActionType.CHECK,
            "uncheck": ActionType.UNCHECK,
            "toggle": ActionType.TOGGLE,
            "scroll": ActionType.SCROLL,
            "drag": ActionType.DRAG,
            "drop": ActionType.DROP,
            "hover": ActionType.HOVER,
            "focus": ActionType.FOCUS,
            "blur": ActionType.BLUR,
            "submit": ActionType.SUBMIT,
            "navigate": ActionType.NAVIGATE,
            "wait": ActionType.WAIT,
        }
        
        return type_map.get(type_str.lower(), ActionType.CLICK)
    
    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON from VLM response, handling markdown code blocks."""
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            logger.debug(f"Raw response: {response}")
            return {}
