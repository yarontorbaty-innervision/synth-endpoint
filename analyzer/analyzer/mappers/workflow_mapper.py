"""
Maps detected UI elements and actions to workflow definitions.
"""

from datetime import datetime
from pathlib import Path
import logging
import uuid
import hashlib

import numpy as np
from PIL import Image

from analyzer.config import WorkflowMappingConfig
from analyzer.models.frame import Frame
from analyzer.models.detection import UIDetection, ActionDetection
from analyzer.models.workflow import (
    WorkflowDefinition,
    Screen,
    Action,
    ActionType,
)


logger = logging.getLogger(__name__)


class WorkflowMapper:
    """
    Maps detected UI elements and actions to a structured workflow definition.
    
    Responsibilities:
    - Group similar frames into screens
    - Map actions to screens and elements
    - Build navigation graph
    - Generate workflow definition
    """
    
    def __init__(self, config: WorkflowMappingConfig | None = None):
        self.config = config or WorkflowMappingConfig()
    
    def map_workflow(
        self,
        frames: list[Frame],
        ui_detections: list[UIDetection],
        actions: list[ActionDetection],
        source_video: str | None = None
    ) -> WorkflowDefinition:
        """
        Map frames, UI detections, and actions to a workflow definition.
        
        Args:
            frames: Extracted video frames
            ui_detections: UI detections for each frame
            actions: Detected user actions
            source_video: Name of source video file
            
        Returns:
            Complete workflow definition
        """
        # Step 1: Identify unique screens
        screens = self._identify_screens(frames, ui_detections)
        
        # Step 2: Map frames to screens
        frame_to_screen = self._map_frames_to_screens(frames, screens)
        
        # Step 3: Map actions to workflow actions
        workflow_actions = self._map_actions(actions, frame_to_screen, ui_detections)
        
        # Step 4: Infer navigation between screens
        if self.config.infer_navigation:
            workflow_actions = self._infer_navigation(workflow_actions, frame_to_screen, frames)
        
        # Step 5: Build workflow definition
        workflow = WorkflowDefinition(
            id=f"workflow_{uuid.uuid4().hex[:8]}",
            name=self._generate_workflow_name(source_video),
            description=f"Workflow extracted from {source_video}" if source_video else None,
            source_video=source_video,
            screens=screens,
            actions=workflow_actions,
            start_screen_id=screens[0].id if screens else None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        return workflow
    
    def _identify_screens(
        self,
        frames: list[Frame],
        ui_detections: list[UIDetection]
    ) -> list[Screen]:
        """
        Identify unique screens from frames.
        
        Groups similar frames together and creates screen definitions.
        """
        if not frames:
            return []
        
        screens: list[Screen] = []
        screen_frames: list[list[int]] = []  # Frame indices for each screen
        
        for i, (frame, detection) in enumerate(zip(frames, ui_detections)):
            # Check similarity with existing screens
            matched_screen_idx = None
            
            if self.config.merge_similar_screens:
                for j, screen in enumerate(screens):
                    # Compare with representative frame of each screen
                    rep_frame_idx = screen_frames[j][0]
                    rep_frame = frames[rep_frame_idx]
                    
                    similarity = self._compute_frame_similarity(frame.image, rep_frame.image)
                    
                    if similarity >= self.config.similarity_threshold:
                        matched_screen_idx = j
                        break
            
            if matched_screen_idx is not None:
                # Add frame to existing screen
                screen_frames[matched_screen_idx].append(i)
            else:
                # Create new screen
                screen = Screen(
                    id=f"screen_{uuid.uuid4().hex[:8]}",
                    name=f"Screen {len(screens) + 1}",
                    width=frame.metadata.width,
                    height=frame.metadata.height,
                    elements=detection.elements.copy(),
                    source_frame=frame.frame_number,
                    timestamp=frame.timestamp
                )
                
                screens.append(screen)
                screen_frames.append([i])
        
        logger.info(f"Identified {len(screens)} unique screens from {len(frames)} frames")
        
        return screens
    
    def _map_frames_to_screens(
        self,
        frames: list[Frame],
        screens: list[Screen]
    ) -> dict[int, str]:
        """
        Map each frame index to a screen ID.
        """
        if not screens:
            return {}
        
        frame_to_screen: dict[int, str] = {}
        
        for i, frame in enumerate(frames):
            best_match = None
            best_similarity = 0.0
            
            for screen in screens:
                # Get reference frame for screen
                ref_frame_idx = next(
                    (j for j, f in enumerate(frames) if f.frame_number == screen.source_frame),
                    0
                )
                ref_frame = frames[ref_frame_idx]
                
                similarity = self._compute_frame_similarity(frame.image, ref_frame.image)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = screen.id
            
            if best_match:
                frame_to_screen[i] = best_match
        
        return frame_to_screen
    
    def _map_actions(
        self,
        actions: list[ActionDetection],
        frame_to_screen: dict[int, str],
        ui_detections: list[UIDetection]
    ) -> list[Action]:
        """
        Convert detected actions to workflow actions.
        """
        workflow_actions: list[Action] = []
        
        for i, action in enumerate(actions):
            # Find screen for this action
            screen_id = frame_to_screen.get(action.frame_number)
            
            if not screen_id:
                # Find closest frame
                closest_frame = min(
                    frame_to_screen.keys(),
                    key=lambda f: abs(f - action.frame_number),
                    default=None
                )
                if closest_frame is not None:
                    screen_id = frame_to_screen[closest_frame]
            
            if not screen_id:
                continue
            
            workflow_action = Action(
                id=f"action_{uuid.uuid4().hex[:8]}",
                type=ActionType(action.type.value),
                screen_id=screen_id,
                element_id=action.target_element_id,
                x=action.x,
                y=action.y,
                value=action.text,
                timestamp=action.timestamp,
                confidence=action.confidence
            )
            
            # Calculate delay from previous action
            if workflow_actions:
                prev_action = workflow_actions[-1]
                if prev_action.timestamp and action.timestamp:
                    delay = action.timestamp - prev_action.timestamp
                    workflow_action.delay_before = max(0.0, delay)
            
            workflow_actions.append(workflow_action)
        
        return workflow_actions
    
    def _infer_navigation(
        self,
        actions: list[Action],
        frame_to_screen: dict[int, str],
        frames: list[Frame]
    ) -> list[Action]:
        """
        Infer navigation between screens from action sequence.
        """
        if len(actions) < 2:
            return actions
        
        # Build frame number to screen mapping by timestamp
        timestamp_to_screen: list[tuple[float, str]] = []
        for frame_idx, screen_id in frame_to_screen.items():
            if frame_idx < len(frames):
                timestamp_to_screen.append((frames[frame_idx].timestamp, screen_id))
        timestamp_to_screen.sort(key=lambda x: x[0])
        
        # Update actions with next_screen_id
        for i, action in enumerate(actions):
            if action.type == ActionType.CLICK:
                # Look for screen change after this action
                action_time = action.timestamp or 0
                
                # Find next screen transition
                for ts, screen_id in timestamp_to_screen:
                    if ts > action_time and screen_id != action.screen_id:
                        action.next_screen_id = screen_id
                        break
        
        return actions
    
    def _compute_frame_similarity(self, img1: Image.Image, img2: Image.Image) -> float:
        """
        Compute structural similarity between two images.
        """
        # Resize for faster comparison
        size = (256, 256)
        img1_resized = img1.resize(size, Image.Resampling.LANCZOS).convert("L")
        img2_resized = img2.resize(size, Image.Resampling.LANCZOS).convert("L")
        
        arr1 = np.array(img1_resized, dtype=float)
        arr2 = np.array(img2_resized, dtype=float)
        
        # Compute normalized cross-correlation
        arr1_norm = (arr1 - arr1.mean()) / (arr1.std() + 1e-8)
        arr2_norm = (arr2 - arr2.mean()) / (arr2.std() + 1e-8)
        
        correlation = (arr1_norm * arr2_norm).mean()
        
        # Convert to 0-1 similarity score
        similarity = (correlation + 1) / 2
        
        return similarity
    
    def _generate_workflow_name(self, source_video: str | None) -> str:
        """Generate a human-readable workflow name."""
        if source_video:
            # Extract name from video filename
            name = Path(source_video).stem
            # Convert underscores/dashes to spaces and title case
            name = name.replace("_", " ").replace("-", " ").title()
            return f"{name} Workflow"
        
        return f"Workflow {datetime.now().strftime('%Y%m%d_%H%M%S')}"
