# AI Restyle Test Agent Instructions

## Agent Purpose
Test AI Restyle feature on a specific image in OneDrive Photos gallery.

## Parameters
- IMAGE_POSITION: Which image to test (1 = first image, 2 = second, etc.)
- NUM_STYLES: How many styles to test (default: 3, max: 14)

## Style Presets Available (14 total)
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

## Test Steps for Each Image

### 1. Navigate to OneDrive Photos
- Go to: https://onedrive.live.com/?view=8
- If on Files view, click the "Photos" tab
- Wait for Photos list to load

### 2. Open Target Image
- Find images in the gallery using selector: `[aria-label="Photos list"] > [role="listitem"] a`
- Click on the image at position IMAGE_POSITION (1-indexed)
- Wait for viewer menubar to appear

### 3. For Each Style (up to NUM_STYLES):
a. Click "Restyle with AI" menuitem
b. Wait for panel with "Let's enhance this shot!" text
c. Click the style preset image (e.g., `img[alt="Movie Poster"]`)
d. Click "Send" button
e. Wait for "Save copy" button to become enabled (generation complete)
f. Take screenshot and record time
g. Click "Reset" button to try next style

### 4. Report Results
- Success/failure for each style
- Generation time for successful styles
- Screenshots saved

## Output Directory
Save results to: `results/image_{IMAGE_POSITION}/` (relative to the project root)

## How to Run Parallel Agents

In Claude Code, use:
```
Run 2 parallel agents to test AI Restyle:
- Agent 1: Test image 1 with 3 styles
- Agent 2: Test image 2 with 3 styles
```

Each agent uses Playwright MCP tools independently.
