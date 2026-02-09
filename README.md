# AI Restyle Parallel Test Agent

Automated testing system for OneDrive Photos AI Restyle feature.

## Setup

1. Install dependencies:
```bash
pip install playwright
playwright install chromium
```

2. Ensure you're logged into OneDrive in Edge/Chrome browser

## Usage

### Option 1: Run parallel tests from command line
```bash
# Test images 1, 2, and 3 in parallel
python run_parallel_tests.py --images 1,2,3 --output-dir ./results

# Test images 1 through 5 with max 3 parallel browsers
python run_parallel_tests.py --images 1-5 --max-parallel 3 --output-dir ./results

# Run in headless mode
python run_parallel_tests.py --images 1-3 --headless --output-dir ./results
```

### Option 2: Run single image test
```bash
python restyle_agent.py --image-position 1 --output-dir ./results
```

### Option 3: Run via Claude Code parallel agents
In Claude Code, you can launch parallel Task agents:

```
Test images 1, 2, and 3 for AI Restyle - run them in parallel
```

## Output Structure
```
results/
  image_1/
    results.json           # Test results for image 1
    movie_poster.png       # Screenshots for each style
    plush_toy.png
    ...
  image_2/
    results.json
    ...
  test_report.json         # Overall summary report
  auth_state.json          # Saved auth for future runs
```

## Style Presets Tested (14 total)
1. Movie Poster
2. Plush Toy
3. Anime
4. Chibi Sticker
5. Caricature
6. Superhero
7. Toy Model
8. Graffiti
9. Crochet Art
10. Doodle
11. Pencil Portrait
12. Storybook
13. Photo Booth
14. Pop Art

## Notes
- Each image test takes ~15-20 minutes (14 styles x ~65 seconds per generation)
- First run requires manual login; subsequent runs use saved auth state
- Use `--max-parallel` to control resource usage (recommended: 2-3 browsers)
