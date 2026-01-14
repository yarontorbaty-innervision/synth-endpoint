"""
Command-line interface for the Innervision Analyzer.
"""

from __future__ import annotations
import asyncio
import os
from pathlib import Path
from typing import Optional

import click

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
    config: Optional[Path],
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
    "--provider", "-p",
    type=click.Choice(["ollama", "openai", "gemini"]),
    default="ollama",
    help="VLM provider to use"
)
@click.option(
    "--model", "-m",
    type=str,
    default=None,
    help="Model name (default: llava:13b for ollama, gpt-4o for openai, gemini-1.5-pro for gemini)"
)
@click.option(
    "--api-key", "-k",
    type=str,
    default=None,
    help="API key for cloud providers (or set OPENAI_API_KEY / GEMINI_API_KEY env var)"
)
@click.option(
    "--frame-interval", "-f",
    type=float,
    default=2.0,
    help="Interval between frames to analyze (seconds)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
def analyze_vlm(
    input: Path,
    output: Path,
    provider: str,
    model: Optional[str],
    api_key: Optional[str],
    frame_interval: float,
    verbose: bool
):
    """Analyze a video using Vision Language Models (VLM)."""
    from analyzer.vlm import VLMClient, VLMConfig, VLMAnalyzer
    from analyzer.vlm.client import VLMProvider
    from analyzer.extractors.frame_extractor import FrameExtractor
    from analyzer.config import FrameExtractionConfig
    
    click.echo(f"🎬 VLM-powered video analysis: {input}")
    
    # Configure VLM
    if provider == "ollama":
        # Check if Ollama is running
        if not VLMClient.check_ollama_available():
            click.echo("❌ Ollama is not running. Start it with: ollama serve", err=True)
            click.echo("   Then pull a vision model: ollama pull llava:13b", err=True)
            raise SystemExit(1)
        
        available_models = VLMClient.list_ollama_models()
        vision_models = [m for m in available_models if any(v in m.lower() for v in ["llava", "bakllava", "moondream", "cogvlm"])]
        
        if not vision_models:
            click.echo("❌ No vision models found in Ollama.", err=True)
            click.echo("   Pull one with: ollama pull llava:13b", err=True)
            raise SystemExit(1)
        
        model = model or vision_models[0]
        click.echo(f"   Using local model: {model}")
        config = VLMConfig.local(model)
        
    elif provider == "openai":
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            click.echo("❌ OpenAI API key required. Set --api-key or OPENAI_API_KEY env var", err=True)
            raise SystemExit(1)
        model = model or "gpt-4o"
        click.echo(f"   Using OpenAI: {model}")
        config = VLMConfig.openai(api_key, model)
        
    elif provider == "gemini":
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            click.echo("❌ Gemini API key required. Set --api-key or GEMINI_API_KEY env var", err=True)
            raise SystemExit(1)
        model = model or "gemini-1.5-pro"
        click.echo(f"   Using Gemini: {model}")
        config = VLMConfig.gemini(api_key, model)
    
    # Extract frames
    click.echo(f"\n📽️  Extracting frames (every {frame_interval}s)...")
    extractor = FrameExtractor(FrameExtractionConfig(interval=frame_interval))
    frames = extractor.extract(input)
    click.echo(f"   Extracted {len(frames)} frames")
    
    # Run VLM analysis
    click.echo(f"\n🧠 Running VLM analysis...")
    analyzer = VLMAnalyzer(config)
    
    # Run async analysis
    workflow = asyncio.run(analyzer.analyze_workflow(frames))
    
    # Export
    output_format = "yaml" if output.suffix in (".yaml", ".yml") else "json"
    workflow.export(output, format=output_format)
    
    click.echo(f"\n✅ Workflow exported to: {output}")
    click.echo(f"   - {len(workflow.screens)} screens detected")
    click.echo(f"   - {len(workflow.actions)} actions captured")


@main.command()
def check_vlm():
    """Check VLM availability and list available models."""
    from analyzer.vlm import VLMClient
    
    click.echo("🔍 Checking VLM availability...\n")
    
    # Check Ollama
    click.echo("Local (Ollama):")
    if VLMClient.check_ollama_available():
        click.echo("  ✅ Ollama is running")
        models = VLMClient.list_ollama_models()
        vision_models = [m for m in models if any(v in m.lower() for v in ["llava", "bakllava", "moondream", "cogvlm", "minicpm"])]
        if vision_models:
            click.echo(f"  📦 Vision models available:")
            for m in vision_models:
                click.echo(f"     - {m}")
        else:
            click.echo("  ⚠️  No vision models found. Install with:")
            click.echo("     ollama pull llava:13b")
            click.echo("     ollama pull moondream")
    else:
        click.echo("  ❌ Ollama not running")
        click.echo("     Start with: ollama serve")
    
    click.echo("\nCloud APIs:")
    
    # Check OpenAI
    import os
    if os.environ.get("OPENAI_API_KEY"):
        click.echo("  ✅ OPENAI_API_KEY is set")
    else:
        click.echo("  ⚠️  OPENAI_API_KEY not set")
    
    # Check Gemini
    if os.environ.get("GEMINI_API_KEY"):
        click.echo("  ✅ GEMINI_API_KEY is set")
    else:
        click.echo("  ⚠️  GEMINI_API_KEY not set")


if __name__ == "__main__":
    main()
