"""
UI element detection using ML models.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import logging
import uuid

from PIL import Image

from analyzer.config import UIDetectionConfig
from analyzer.models.detection import UIDetection
from analyzer.models.workflow import UIElement, UIElementType, BoundingBox


logger = logging.getLogger(__name__)


# Mapping from model labels to UI element types
LABEL_TO_TYPE: Dict[str, UIElementType] = {
    "button": UIElementType.BUTTON,
    "text_input": UIElementType.TEXT_INPUT,
    "textbox": UIElementType.TEXT_INPUT,
    "input": UIElementType.TEXT_INPUT,
    "dropdown": UIElementType.DROPDOWN,
    "select": UIElementType.DROPDOWN,
    "combobox": UIElementType.COMBOBOX,
    "checkbox": UIElementType.CHECKBOX,
    "radio": UIElementType.RADIO,
    "toggle": UIElementType.TOGGLE,
    "switch": UIElementType.TOGGLE,
    "link": UIElementType.LINK,
    "tab": UIElementType.TAB,
    "menu": UIElementType.MENU_ITEM,
    "table": UIElementType.TABLE,
    "label": UIElementType.LABEL,
    "text": UIElementType.LABEL,
    "heading": UIElementType.HEADING,
    "icon": UIElementType.ICON,
    "image": UIElementType.IMAGE,
    "modal": UIElementType.MODAL,
    "dialog": UIElementType.MODAL,
    "panel": UIElementType.PANEL,
    "sidebar": UIElementType.SIDEBAR,
    "toolbar": UIElementType.TOOLBAR,
    "navbar": UIElementType.NAVIGATION,
}


class UIDetector:
    """
    Detects UI elements in screenshots using ML models.
    
    Uses YOLO-based detection for UI components and OCR for text extraction.
    """
    
    def __init__(self, config: Optional[UIDetectionConfig] = None):
        self.config = config or UIDetectionConfig()
        self.model = None
        self.ocr = None
        self._initialized = False
    
    def _initialize(self) -> None:
        """Lazy initialization of ML models."""
        if self._initialized:
            return
        
        logger.info("Initializing UI detection models...")
        
        # Initialize YOLO model for UI detection
        # In production, this would load a fine-tuned model for UI detection
        try:
            from ultralytics import YOLO
            # Use a placeholder - in production this would be a custom-trained model
            self.model = YOLO("yolov8n.pt")
            logger.info("YOLO model loaded")
        except Exception as e:
            logger.warning(f"Could not load YOLO model: {e}")
            self.model = None
        
        # Initialize OCR
        if self.config.detect_text:
            try:
                import easyocr
                self.ocr = easyocr.Reader([self.config.ocr_language])
                logger.info("OCR initialized")
            except Exception as e:
                logger.warning(f"Could not initialize OCR: {e}")
                self.ocr = None
        
        self._initialized = True
    
    def detect(self, image: Image.Image) -> UIDetection:
        """
        Detect UI elements in an image.
        
        Args:
            image: PIL Image to analyze
            
        Returns:
            UIDetection with detected elements
        """
        self._initialize()
        
        detection = UIDetection(frame_number=0, elements=[])
        
        # Run object detection
        if self.model:
            detection = self._detect_elements(image, detection)
        
        # Run OCR
        if self.ocr and self.config.detect_text:
            detection = self._detect_text(image, detection)
        
        return detection
    
    def _detect_elements(self, image: Image.Image, detection: UIDetection) -> UIDetection:
        """Run UI element detection."""
        import numpy as np
        
        # Convert PIL to numpy for YOLO
        img_array = np.array(image)
        
        # Run inference
        results = self.model(img_array, conf=self.config.confidence_threshold)
        
        for result in results:
            boxes = result.boxes
            
            if boxes is None:
                continue
            
            for i, box in enumerate(boxes):
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = box.conf[0].item()
                class_id = int(box.cls[0].item())
                label = result.names[class_id]
                
                # Map label to UI element type
                element_type = LABEL_TO_TYPE.get(label.lower(), UIElementType.PANEL)
                
                bounds = BoundingBox(
                    x=int(x1),
                    y=int(y1),
                    width=int(x2 - x1),
                    height=int(y2 - y1)
                )
                
                element = UIElement(
                    id=f"elem_{uuid.uuid4().hex[:8]}",
                    type=element_type,
                    bounds=bounds,
                    confidence=confidence
                )
                
                detection.elements.append(element)
                detection.raw_boxes.append(bounds)
                detection.raw_labels.append(label)
                detection.raw_scores.append(confidence)
        
        return detection
    
    def _detect_text(self, image: Image.Image, detection: UIDetection) -> UIDetection:
        """Run OCR text detection."""
        import numpy as np
        
        img_array = np.array(image)
        
        # Run OCR
        results = self.ocr.readtext(img_array)
        
        for bbox, text, confidence in results:
            if confidence < self.config.confidence_threshold:
                continue
            
            # Convert polygon bbox to rectangle
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            x1, y1 = min(x_coords), min(y_coords)
            x2, y2 = max(x_coords), max(y_coords)
            
            bounds = BoundingBox(
                x=int(x1),
                y=int(y1),
                width=int(x2 - x1),
                height=int(y2 - y1)
            )
            
            detection.ocr_texts.append(text)
            detection.ocr_boxes.append(bounds)
            
            # Try to associate text with existing elements
            self._associate_text_with_elements(text, bounds, detection)
        
        return detection
    
    def _associate_text_with_elements(
        self,
        text: str,
        text_bounds: BoundingBox,
        detection: UIDetection
    ) -> None:
        """Associate detected text with UI elements."""
        text_center = text_bounds.center
        
        for element in detection.elements:
            elem_bounds = element.bounds
            
            # Check if text center is within element bounds
            if (elem_bounds.x <= text_center[0] <= elem_bounds.x + elem_bounds.width and
                elem_bounds.y <= text_center[1] <= elem_bounds.y + elem_bounds.height):
                
                # Assign text based on element type
                if element.type in (UIElementType.BUTTON, UIElementType.LINK, UIElementType.TAB):
                    element.text = text
                elif element.type in (UIElementType.TEXT_INPUT, UIElementType.TEXTAREA):
                    if element.value is None:
                        element.value = text
                    else:
                        element.placeholder = text
                elif element.type == UIElementType.LABEL:
                    element.text = text
                
                break
