# Innervision Synth Endpoint

> Automated generation of synthetic workflow software from screen recordings

## Overview

Synth Endpoint transforms video recordings of users working on ERP and business software into native desktop applications that faithfully replicate those workflows. The generated applications serve as synthetic endpoints for testing and validating Innervision's AI/ML-powered workflow intelligence platform.

## Purpose

This project creates realistic mock environments that:
- **Replicate real user workflows** captured from screen recordings
- **Generate native desktop apps** for both macOS and Windows
- **Simulate authentic user behavior** including typing, mouse movements, and interactions
- **Provide testing endpoints** for Innervision's screen capture and workflow analysis solutions

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VIDEO INPUT                                  │
│              Screen recordings of ERP/business software              │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ANALYSIS PIPELINE                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Frame     │  │    UI       │  │  Workflow   │  │   Action   │ │
│  │ Extraction  │→ │  Detection  │→ │   Mapping   │→ │  Sequence  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     WORKFLOW DEFINITION                              │
│                  (JSON/YAML workflow scripts)                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      APP GENERATOR                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │    UI       │  │  Workflow   │  │   Behavior  │  │   Native   │ │
│  │  Builder    │→ │   Engine    │→ │  Simulator  │→ │   Bundle   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      OUTPUT APPLICATIONS                             │
│         Native macOS (.app) and Windows (.exe) applications          │
│    - Realistic mock UIs (forms, dropdowns, toggles, tables)         │
│    - Automated workflow playback with human-like behavior           │
│    - No backend operations (visual simulation only)                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
synth-endpoint/
├── analyzer/                 # Python video analysis pipeline
│   ├── extractors/          # Frame and UI element extraction
│   ├── detectors/           # UI component detection (ML models)
│   ├── mappers/             # Workflow sequence mapping
│   └── exporters/           # Workflow definition exporters
│
├── generator/               # Desktop app generation (TypeScript/Electron)
│   ├── src/
│   │   ├── builder/        # UI component builders
│   │   ├── engine/         # Workflow execution engine
│   │   ├── simulator/      # Human behavior simulation
│   │   └── components/     # Reusable UI components
│   └── templates/          # App templates and themes
│
├── schemas/                 # Workflow and UI definition schemas
│   ├── workflow.schema.json
│   └── ui.schema.json
│
├── examples/               # Example workflows and generated apps
│
└── docs/                   # Documentation
```

## Key Features

### Video Analysis
- Frame-by-frame extraction from screen recordings
- ML-powered UI element detection and classification
- Action sequence recognition (clicks, typing, navigation)
- Workflow graph construction

### UI Generation
- Authentic form controls: text inputs, dropdowns, date pickers, toggles
- Data tables with realistic content
- Navigation elements and menu systems
- Theme matching to source application aesthetics

### Behavior Simulation
- Human-like typing with variable speed and occasional corrections
- Natural mouse movement curves
- Realistic click timing and hover behaviors
- Workflow step transitions with appropriate delays

### Cross-Platform Output
- Native macOS applications (.app bundles)
- Native Windows applications (.exe)
- Consistent behavior across platforms

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- pnpm 8+

### Installation

```bash
# Clone the repository
git clone https://github.com/innervision/synth-endpoint.git
cd synth-endpoint

# Install Python dependencies
cd analyzer
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install Node dependencies
cd ../generator
pnpm install
```

### Quick Start

```bash
# Analyze a video recording
python -m analyzer.cli analyze --input recording.mp4 --output workflow.json

# Generate a desktop application
cd generator
pnpm run generate --workflow ../workflow.json --platform macos
```

## Development

### Running Tests

```bash
# Python tests
cd analyzer
pytest

# TypeScript tests
cd generator
pnpm test
```

### Building

```bash
# Build for macOS
pnpm run build:macos

# Build for Windows
pnpm run build:windows
```

## License

Proprietary - Innervision © 2026

## Contributing

Internal Innervision team only. See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.
