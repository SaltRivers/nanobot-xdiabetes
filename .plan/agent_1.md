```
基于`https://github.com/SaltRivers/nanobot-xdiabetes/tree/xdiabetes`的xdiabetes分支，回答以下问题：

<<仓库介绍>>{
● Recommended onboarding sequence:
1. CLAUDE.md - Quick overview
- Project purpose and architecture
    - Common commands reference
    - Key files map
  2. docs/XDIABETES_QUICKSTART.md - Getting started guide
  3. docs/XDIABETES_ARCHITECTURE.md - System design and components
  4. docs/XDIABETES_DTMH_ADAPTER.md - Core DTMH integration (the heart of the system)

  Best example command to demonstrate:

  # Setup first
  python -m venv .venv
  source .venv/bin/activate  # or .venv\Scripts\activate on Windows
  pip install -e .

  # Initialize
  x-diabetes onboard

  # Run the example query (shows the core workflow)
  x-diabetes agent -m "Check whether patient 4 in Dataset/private_fundus has diabetes"

  This example is ideal because it:
  - Demonstrates the primary use case (diabetes inference via DTMH)
  - Shows the full runtime path: CLI → AgentLoop → DTMH tool → HTTP adapter → remote model
  - Requires the DTMH service to be running (teaches about the architecture)
  - Produces structured output the engineer can inspect

  Optional follow-up examples:
  - x-diabetes agent - Interactive mode
  - x-diabetes agent --mode patient - Patient-facing mode
  - x-diabetes learning status - Continuous learning features
}<</仓库介绍>>

<<你的任务>>{
1. 基于仓库介绍理解当前仓库的工作流程。
2. 当前仓库基于一个agent仓库改进而来，然而其中还有很多地方不符合xdiabetes的设计。以实现“Foundation_Agent_Purpose.md”为目标，基于当前repo内容给出一个改进方案。
}<</你的任务>>

```