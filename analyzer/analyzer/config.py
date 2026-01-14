"""
Configuration management for the Innervision Analyzer.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
import yaml


class FrameExtractionConfig(BaseModel):
    """Configuration for frame extraction."""
    
    interval: float = Field(default=0.5, description="Interval between frames in seconds")
    max_frames: int = Field(default=10000, description="Maximum number of frames to extract")
    resize_width: Optional[int] = Field(default=None, description="Resize frames to this width")
    quality: int = Field(default=95, description="JPEG quality for saved frames")


class UIDetectionConfig(BaseModel):
    """Configuration for UI element detection."""
    
    model_name: str = Field(default="ui-detector-v1", description="Name of detection model")
    confidence_threshold: float = Field(default=0.7, description="Minimum confidence for detections")
    nms_threshold: float = Field(default=0.4, description="Non-maximum suppression threshold")
    detect_text: bool = Field(default=True, description="Enable OCR for text detection")
    ocr_language: str = Field(default="eng", description="OCR language")


class ActionDetectionConfig(BaseModel):
    """Configuration for action detection."""
    
    click_threshold: float = Field(default=0.8, description="Confidence threshold for click detection")
    typing_detection: bool = Field(default=True, description="Enable typing detection")
    scroll_detection: bool = Field(default=True, description="Enable scroll detection")
    min_action_gap: float = Field(default=0.1, description="Minimum gap between actions in seconds")


class WorkflowMappingConfig(BaseModel):
    """Configuration for workflow mapping."""
    
    merge_similar_screens: bool = Field(default=True, description="Merge similar screens")
    similarity_threshold: float = Field(default=0.9, description="Threshold for screen similarity")
    infer_navigation: bool = Field(default=True, description="Infer navigation between screens")


class AnalyzerConfig(BaseModel):
    """Main configuration for the analyzer."""
    
    frame_extraction: FrameExtractionConfig = Field(default_factory=FrameExtractionConfig)
    ui_detection: UIDetectionConfig = Field(default_factory=UIDetectionConfig)
    action_detection: ActionDetectionConfig = Field(default_factory=ActionDetectionConfig)
    workflow_mapping: WorkflowMappingConfig = Field(default_factory=WorkflowMappingConfig)
    
    output_format: str = Field(default="json", description="Default output format")
    verbose: bool = Field(default=False, description="Enable verbose logging")
    
    @classmethod
    def from_file(cls, path: Path) -> AnalyzerConfig:
        """Load configuration from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_file(self, path: Path) -> None:
        """Save configuration to a YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)
