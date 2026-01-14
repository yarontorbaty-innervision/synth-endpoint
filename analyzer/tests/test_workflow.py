"""
Tests for workflow models.
"""

import json
import pytest
from pathlib import Path

from analyzer.models.workflow import (
    WorkflowDefinition,
    Screen,
    Action,
    UIElement,
    UIElementType,
    ActionType,
    BoundingBox,
)


class TestBoundingBox:
    """Tests for BoundingBox model."""

    def test_center_calculation(self):
        """Test that center point is calculated correctly."""
        box = BoundingBox(x=100, y=200, width=50, height=30)
        assert box.center == (125, 215)

    def test_zero_size_box(self):
        """Test bounding box with zero dimensions."""
        box = BoundingBox(x=10, y=20, width=0, height=0)
        assert box.center == (10, 20)


class TestUIElement:
    """Tests for UIElement model."""

    def test_create_text_input(self):
        """Test creating a text input element."""
        element = UIElement(
            id="input_1",
            type=UIElementType.TEXT_INPUT,
            bounds=BoundingBox(x=0, y=0, width=200, height=40),
            placeholder="Enter text",
            required=True,
        )
        
        assert element.id == "input_1"
        assert element.type == UIElementType.TEXT_INPUT
        assert element.placeholder == "Enter text"
        assert element.required is True
        assert element.enabled is True  # Default

    def test_create_dropdown(self):
        """Test creating a dropdown element."""
        element = UIElement(
            id="dropdown_1",
            type=UIElementType.DROPDOWN,
            bounds=BoundingBox(x=0, y=0, width=150, height=35),
            options=["Option 1", "Option 2", "Option 3"],
            value="Option 1",
        )
        
        assert element.type == UIElementType.DROPDOWN
        assert element.options == ["Option 1", "Option 2", "Option 3"]
        assert element.value == "Option 1"


class TestScreen:
    """Tests for Screen model."""

    def test_create_screen(self):
        """Test creating a screen with elements."""
        screen = Screen(
            id="screen_1",
            name="Login Screen",
            width=1024,
            height=768,
            elements=[
                UIElement(
                    id="btn_1",
                    type=UIElementType.BUTTON,
                    bounds=BoundingBox(x=100, y=100, width=100, height=40),
                    text="Click Me",
                )
            ],
        )
        
        assert screen.id == "screen_1"
        assert screen.name == "Login Screen"
        assert len(screen.elements) == 1
        assert screen.elements[0].text == "Click Me"


class TestAction:
    """Tests for Action model."""

    def test_create_click_action(self):
        """Test creating a click action."""
        action = Action(
            id="action_1",
            type=ActionType.CLICK,
            screen_id="screen_1",
            element_id="btn_1",
            delay_before=500,
        )
        
        assert action.type == ActionType.CLICK
        assert action.delay_before == 500

    def test_create_type_action(self):
        """Test creating a type action."""
        action = Action(
            id="action_2",
            type=ActionType.TYPE,
            screen_id="screen_1",
            element_id="input_1",
            value="Hello World",
            typing_speed=50,
        )
        
        assert action.type == ActionType.TYPE
        assert action.value == "Hello World"
        assert action.typing_speed == 50


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition model."""

    def test_create_workflow(self):
        """Test creating a complete workflow."""
        workflow = WorkflowDefinition(
            id="workflow_1",
            name="Test Workflow",
            screens=[
                Screen(
                    id="screen_1",
                    name="Screen 1",
                    width=800,
                    height=600,
                    elements=[],
                )
            ],
            actions=[
                Action(
                    id="action_1",
                    type=ActionType.CLICK,
                    screen_id="screen_1",
                )
            ],
            start_screen_id="screen_1",
        )
        
        assert workflow.name == "Test Workflow"
        assert len(workflow.screens) == 1
        assert len(workflow.actions) == 1
        assert workflow.start_screen_id == "screen_1"

    def test_export_json(self, tmp_path: Path):
        """Test exporting workflow to JSON."""
        workflow = WorkflowDefinition(
            id="workflow_export",
            name="Export Test",
            screens=[],
            actions=[],
        )
        
        output_path = tmp_path / "workflow.json"
        workflow.export(output_path, format="json")
        
        assert output_path.exists()
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert data["id"] == "workflow_export"
        assert data["name"] == "Export Test"

    def test_load_from_file(self, tmp_path: Path):
        """Test loading workflow from file."""
        workflow_data = {
            "id": "workflow_load",
            "name": "Load Test",
            "screens": [],
            "actions": [],
        }
        
        input_path = tmp_path / "workflow.json"
        with open(input_path, "w") as f:
            json.dump(workflow_data, f)
        
        workflow = WorkflowDefinition.from_file(input_path)
        
        assert workflow.id == "workflow_load"
        assert workflow.name == "Load Test"
