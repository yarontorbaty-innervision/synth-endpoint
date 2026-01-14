"""
Main analysis pipeline for processing video recordings.
"""

from pathlib import Path
from typing import Generator
import logging

from analyzer.config import AnalyzerConfig
from analyzer.models.workflow import WorkflowDefinition, Screen, Action
from analyzer.extractors.frame_extractor import FrameExtractor
from analyzer.detectors.ui_detector import UIDetector
from analyzer.detectors.action_detector import ActionDetector
from analyzer.mappers.workflow_mapper import WorkflowMapper


logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """
    Main pipeline for analyzing video recordings and extracting workflows.
    
    The pipeline processes videos through several stages:
    1. Frame extraction - Extract frames at regular intervals
    2. UI detection - Detect UI elements in each frame
    3. Action detection - Detect user actions (clicks, typing, etc.)
    4. Workflow mapping - Map detected elements and actions to workflow
    """
    
    def __init__(self, config: AnalyzerConfig | None = None, verbose: bool = False):
        self.config = config or AnalyzerConfig()
        self.verbose = verbose
        
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        
        # Initialize pipeline components
        self.frame_extractor = FrameExtractor(config=self.config.frame_extraction)
        self.ui_detector = UIDetector(config=self.config.ui_detection)
        self.action_detector = ActionDetector(config=self.config.action_detection)
        self.workflow_mapper = WorkflowMapper(config=self.config.workflow_mapping)
    
    def process(self, video_path: Path) -> WorkflowDefinition:
        """
        Process a video file and extract workflow definition.
        
        Args:
            video_path: Path to the input video file
            
        Returns:
            WorkflowDefinition containing extracted screens and actions
        """
        logger.info(f"Starting analysis of: {video_path}")
        
        # Stage 1: Extract frames
        logger.info("Stage 1: Extracting frames...")
        frames = list(self.frame_extractor.extract(video_path))
        logger.info(f"Extracted {len(frames)} frames")
        
        # Stage 2: Detect UI elements
        logger.info("Stage 2: Detecting UI elements...")
        ui_detections = []
        for frame in frames:
            detection = self.ui_detector.detect(frame.image)
            ui_detections.append(detection)
        logger.info(f"Detected UI elements in {len(ui_detections)} frames")
        
        # Stage 3: Detect actions
        logger.info("Stage 3: Detecting user actions...")
        actions = self.action_detector.detect_actions(frames, ui_detections)
        logger.info(f"Detected {len(actions)} actions")
        
        # Stage 4: Map to workflow
        logger.info("Stage 4: Mapping workflow...")
        workflow = self.workflow_mapper.map_workflow(
            frames=frames,
            ui_detections=ui_detections,
            actions=actions,
            source_video=video_path.name
        )
        logger.info(f"Workflow mapped: {len(workflow.screens)} screens, {len(workflow.actions)} actions")
        
        return workflow
    
    def process_streaming(self, video_path: Path) -> Generator[dict, None, WorkflowDefinition]:
        """
        Process a video file with streaming progress updates.
        
        Yields progress updates during processing, then returns the final workflow.
        
        Args:
            video_path: Path to the input video file
            
        Yields:
            Progress update dictionaries
            
        Returns:
            WorkflowDefinition containing extracted screens and actions
        """
        yield {"stage": "init", "message": "Initializing pipeline..."}
        
        # Stage 1: Extract frames
        yield {"stage": "extraction", "message": "Extracting frames...", "progress": 0}
        frames = []
        for i, frame in enumerate(self.frame_extractor.extract_streaming(video_path)):
            frames.append(frame)
            if i % 10 == 0:
                yield {"stage": "extraction", "message": f"Extracted {i} frames", "progress": i}
        
        yield {"stage": "extraction", "message": f"Extracted {len(frames)} frames", "progress": 100}
        
        # Stage 2: Detect UI elements
        yield {"stage": "detection", "message": "Detecting UI elements...", "progress": 0}
        ui_detections = []
        for i, frame in enumerate(frames):
            detection = self.ui_detector.detect(frame.image)
            ui_detections.append(detection)
            progress = int((i / len(frames)) * 100)
            yield {"stage": "detection", "message": f"Processing frame {i}/{len(frames)}", "progress": progress}
        
        # Stage 3: Detect actions
        yield {"stage": "actions", "message": "Detecting user actions...", "progress": 0}
        actions = self.action_detector.detect_actions(frames, ui_detections)
        yield {"stage": "actions", "message": f"Detected {len(actions)} actions", "progress": 100}
        
        # Stage 4: Map workflow
        yield {"stage": "mapping", "message": "Mapping workflow...", "progress": 0}
        workflow = self.workflow_mapper.map_workflow(
            frames=frames,
            ui_detections=ui_detections,
            actions=actions,
            source_video=video_path.name
        )
        yield {"stage": "mapping", "message": "Workflow mapped", "progress": 100}
        
        yield {"stage": "complete", "message": "Analysis complete", "workflow": workflow}
        
        return workflow
