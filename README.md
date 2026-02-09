# AI Restyle Benchmark Framework

Automated quality evaluation pipeline for the OneDrive Photos AI Restyle feature. Uses Claude Code + Playwright for browser automation, Gemini for feasibility scoring, and Opus for preference ranking.

## Pipeline

```
CAPTURE  →  EVALUATE  →  RANK  →  SYNTHESIZE  →  COMPARE  →  REPORT  →  PERSIST
Playwright    ACRUE v3    Gemini     Weighted      Baseline     DOCX      Excel
+ Claude      via Gemini  + Opus     synthesis     deltas       report    tracker
```

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt
playwright install

# 2. Configure
copy .env.example .env          # Add your API keys
copy .mcp.json.example .mcp.json # Add your Gemini key

# 3. Run a benchmark
python benchmark_orchestrator.py validate
python benchmark_orchestrator.py init
# ... capture via Claude Code + Playwright MCP ...
python run_acrue_v3.py --batch runs/<run_id>/batch_config.json --output runs/<run_id>/acrue.json
python benchmark_orchestrator.py compute-rankings
python benchmark_orchestrator.py synthesize
python benchmark_orchestrator.py persist
```

See [GETTING_STARTED.md](GETTING_STARTED.md) for full setup instructions.

## ACRUE v3 Evaluation

The framework uses ACRUE v3 (Hybrid Assertions + Confidence) to score restyled images across 5 dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **A** - Accuracy | 1.0 | Style fidelity and transformation quality |
| **C** - Completeness | 1.0 | Full coverage of the image |
| **R** - Relevance | 0.5 | Appropriate for the requested style |
| **U** - Usefulness | 0.5 | Practical value of the output |
| **E** - Exceptional Value | 2.0 | Wow factor and shareability |

```bash
# Evaluate a single image pair
python run_acrue_v3.py -o original.jpg -r restyled.png -s "Storybook"

# Preview evaluation plan without running
python run_acrue_v3.py -o original.jpg -r restyled.png -s "Storybook" --plan-only
```

## Baseline Comparison

Every run automatically compares to the previous baseline, flagging regressions:

```bash
python compare_runs.py --current Run_2026_02_09 --baseline Run_2026_02_03

# Output:
# === COMPARISON vs Run_2026_02_03 ===
#   Anime            31.9% ->  45.2%  (+13.3%)  IMPROVED
#   Pop Art          92.0% ->  90.1%  (-1.9%)   REGRESSION
#   Storybook        86.7% ->  88.0%  (+1.3%)   IMPROVED
#
#   VERDICT: 2 improved, 1 regressed, 0 unchanged

# View all runs
python compare_runs.py --history
```

## 14 Style Presets

Movie Poster, Plush Toy, Anime, Chibi Sticker, Caricature, Superhero, Toy Model, Graffiti, Crochet Art, Doodle, Pencil Portrait, Storybook, Photo Booth, Pop Art

## Project Structure

```
config.py                  # Shared paths & constants
benchmark_orchestrator.py  # Pipeline orchestrator
run_acrue_v3.py            # ACRUE v3 evaluation engine
compare_runs.py            # Baseline comparison CLI
run_dual_llm_pipeline.py   # Dual-LLM (Gemini + Opus) pipeline
restyle_agent.py           # Playwright automation agent
parallel_runner.py         # Parallel agent runner
style_assertions.json      # Style-specific ACRUE assertions
style_definitions.json     # Style evaluation context
acrue_v3_prompt.md         # ACRUE v3 prompt template
run_spec.json              # Run configuration
reports/                   # Report generators (DOCX, PPTX)
results/                   # Generated reports & presentations
runs/                      # Per-run output directories
lt_demo/                   # Leadership presentation materials
```

## Requirements

- Windows 10+ (tested on Windows 11)
- Python 3.10+
- Node.js 18+ (for Playwright MCP)
- Gemini API key ([get one](https://aistudio.google.com/apikey))
- Anthropic API key (optional, for Opus preference judge)
- OneDrive account with Photos AI Restyle enabled
