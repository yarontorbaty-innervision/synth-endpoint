"""
Command-line interface for the Innervision Analyzer.
"""

import click
from pathlib import Path

from analyzer.pipeline import AnalysisPipeline
from analyzer.config import AnalyzerConfig


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Innervision Analyzer - Extract workflows from screen recordings."""
    pass


@main.command()
@click.option(
    "--input", "-i",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to input video file"
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Path to output workflow definition file"
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to configuration file"
)
@click.option(
    "--format", "-f",
    type=click.Choice(["json", "yaml"]),
    default="json",
    help="Output format for workflow definition"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
def analyze(
    input: Path,
    output: Path,
    config: Path | None,
    format: str,
    verbose: bool
):
    """Analyze a video recording and extract workflow definition."""
    click.echo(f"🎬 Analyzing video: {input}")
    
    # Load configuration
    analyzer_config = AnalyzerConfig.from_file(config) if config else AnalyzerConfig()
    
    # Run analysis pipeline
    pipeline = AnalysisPipeline(config=analyzer_config, verbose=verbose)
    workflow = pipeline.process(input)
    
    # Export workflow
    workflow.export(output, format=format)
    
    click.echo(f"✅ Workflow exported to: {output}")
    click.echo(f"   - {len(workflow.screens)} screens detected")
    click.echo(f"   - {len(workflow.actions)} actions captured")


@main.command()
@click.option(
    "--input", "-i",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to input video file"
)
@click.option(
    "--output-dir", "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Directory to save extracted frames"
)
@click.option(
    "--interval", "-n",
    type=float,
    default=1.0,
    help="Interval between frames in seconds"
)
def extract_frames(input: Path, output_dir: Path, interval: float):
    """Extract frames from a video at regular intervals."""
    from analyzer.extractors.frame_extractor import FrameExtractor
    
    click.echo(f"🎞️  Extracting frames from: {input}")
    
    extractor = FrameExtractor()
    frames = extractor.extract(input, interval=interval)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, frame in enumerate(frames):
        frame_path = output_dir / f"frame_{i:05d}.png"
        frame.save(frame_path)
    
    click.echo(f"✅ Extracted {len(frames)} frames to: {output_dir}")


@main.command()
@click.option(
    "--workflow", "-w",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to workflow definition file"
)
def validate(workflow: Path):
    """Validate a workflow definition file."""
    from analyzer.models.workflow import WorkflowDefinition
    
    click.echo(f"🔍 Validating workflow: {workflow}")
    
    try:
        definition = WorkflowDefinition.from_file(workflow)
        click.echo("✅ Workflow is valid!")
        click.echo(f"   - Name: {definition.name}")
        click.echo(f"   - Screens: {len(definition.screens)}")
        click.echo(f"   - Actions: {len(definition.actions)}")
    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
