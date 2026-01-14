"""
Video frame extraction.
"""

from __future__ import annotations
from pathlib import Path
from typing import Generator, List, Optional
import logging

import cv2
from PIL import Image

from analyzer.config import FrameExtractionConfig
from analyzer.models.frame import Frame, FrameMetadata


logger = logging.getLogger(__name__)


class FrameExtractor:
    """
    Extracts frames from video files at regular intervals.
    """
    
    def __init__(self, config: Optional[FrameExtractionConfig] = None):
        self.config = config or FrameExtractionConfig()
    
    def extract(
        self,
        video_path: Path,
        interval: Optional[float] = None
    ) -> List[Frame]:
        """
        Extract frames from video at regular intervals.
        
        Args:
            video_path: Path to video file
            interval: Time between frames in seconds (overrides config)
            
        Returns:
            List of extracted frames
        """
        return list(self.extract_streaming(video_path, interval))
    
    def extract_streaming(
        self,
        video_path: Path,
        interval: Optional[float] = None
    ) -> Generator[Frame, None, None]:
        """
        Extract frames from video as a generator.
        
        Args:
            video_path: Path to video file
            interval: Time between frames in seconds (overrides config)
            
        Yields:
            Extracted frames
        """
        interval = interval or self.config.interval
        
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            frame_interval = int(fps * interval)
            
            logger.info(f"Video: {video_path.name}")
            logger.info(f"  FPS: {fps}, Total frames: {total_frames}")
            logger.info(f"  Size: {width}x{height}")
            logger.info(f"  Extracting every {frame_interval} frames ({interval}s)")
            
            frame_count = 0
            extracted_count = 0
            
            while True:
                ret, cv_frame = cap.read()
                
                if not ret:
                    break
                
                if frame_count % frame_interval == 0:
                    # Convert BGR to RGB
                    rgb_frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(rgb_frame)
                    
                    # Resize if configured
                    if self.config.resize_width:
                        aspect = height / width
                        new_height = int(self.config.resize_width * aspect)
                        pil_image = pil_image.resize(
                            (self.config.resize_width, new_height),
                            Image.Resampling.LANCZOS
                        )
                        output_width = self.config.resize_width
                        output_height = new_height
                    else:
                        output_width = width
                        output_height = height
                    
                    metadata = FrameMetadata(
                        frame_number=frame_count,
                        timestamp=frame_count / fps,
                        width=output_width,
                        height=output_height,
                        source_video=video_path.name
                    )
                    
                    yield Frame(image=pil_image, metadata=metadata)
                    
                    extracted_count += 1
                    
                    if extracted_count >= self.config.max_frames:
                        logger.warning(f"Reached max frames limit: {self.config.max_frames}")
                        break
                
                frame_count += 1
            
            logger.info(f"Extracted {extracted_count} frames from {frame_count} total")
            
        finally:
            cap.release()
    
    def extract_keyframes(self, video_path: Path) -> List[Frame]:
        """
        Extract keyframes (scene changes) from video.
        
        Uses frame differencing to detect significant visual changes.
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of keyframes
        """
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            keyframes = []
            prev_frame = None
            frame_count = 0
            
            # Threshold for detecting scene changes
            change_threshold = 0.15
            
            while True:
                ret, cv_frame = cap.read()
                
                if not ret:
                    break
                
                # Convert to grayscale for comparison
                gray = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # Calculate frame difference
                    diff = cv2.absdiff(gray, prev_frame)
                    change_ratio = diff.sum() / (255 * gray.size)
                    
                    if change_ratio > change_threshold:
                        # Significant change detected - this is a keyframe
                        rgb_frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(rgb_frame)
                        
                        metadata = FrameMetadata(
                            frame_number=frame_count,
                            timestamp=frame_count / fps,
                            width=width,
                            height=height,
                            source_video=video_path.name
                        )
                        
                        keyframes.append(Frame(image=pil_image, metadata=metadata))
                        
                        if len(keyframes) >= self.config.max_frames:
                            break
                else:
                    # First frame is always a keyframe
                    rgb_frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(rgb_frame)
                    
                    metadata = FrameMetadata(
                        frame_number=0,
                        timestamp=0.0,
                        width=width,
                        height=height,
                        source_video=video_path.name
                    )
                    
                    keyframes.append(Frame(image=pil_image, metadata=metadata))
                
                prev_frame = gray
                frame_count += 1
            
            logger.info(f"Extracted {len(keyframes)} keyframes")
            return keyframes
            
        finally:
            cap.release()
