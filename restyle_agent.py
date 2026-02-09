"""
AI Restyle Test Agent
Tests all 14 AI Restyle presets for a given image position in OneDrive Photos gallery.
Can be run in parallel for different images.

Usage:
    python restyle_agent.py --image-position 1 --output-dir ./results
"""

import argparse
import json
import time
import os
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# All 14 AI Restyle presets
STYLE_PRESETS = [
    "Movie Poster",
    "Plush Toy",
    "Anime",
    "Chibi Sticker",
    "Caricature",
    "Superhero",
    "Toy Model",
    "Graffiti",
    "Crochet Art",
    "Doodle",
    "Pencil Portrait",
    "Storybook",
    "Photo Booth",
    "Pop Art"
]

def wait_for_generation(page, timeout_seconds=120):
    """Wait for AI generation to complete by monitoring for result or checking UI state."""
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        # Check if Save copy button is enabled (indicates generation complete)
        try:
            save_btn = page.get_by_role("button", name="Save copy")
            if save_btn.is_enabled():
                return True
        except:
            pass

        # Check for error states
        try:
            error_elem = page.locator("text=Something went wrong")
            if error_elem.is_visible():
                return False
        except:
            pass

        time.sleep(2)

    return False

def test_restyle_for_image(image_position: int, output_dir: str, headless: bool = False, browser_type: str = "chromium"):
    """
    Test all AI Restyle presets for a specific image in the gallery.

    Args:
        image_position: 1-based position of image in gallery (1 = first image)
        output_dir: Directory to save screenshots and results
        headless: Run browser in headless mode
        browser_type: Browser to use ("chromium", "edge", "firefox")

    Returns:
        dict with test results
    """
    results = {
        "image_position": image_position,
        "browser": browser_type,
        "start_time": datetime.now().isoformat(),
        "presets": [],
        "success_count": 0,
        "failure_count": 0
    }

    # Create output directory for this image
    image_output_dir = os.path.join(output_dir, f"image_{image_position}")
    os.makedirs(image_output_dir, exist_ok=True)

    with sync_playwright() as p:
        # Use Edge's actual user profile for authentication
        edge_user_data = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")

        # Launch browser with Edge's existing profile (has auth cookies)
        context = p.chromium.launch_persistent_context(
            user_data_dir=edge_user_data,
            headless=headless,
            channel="msedge",
            viewport={"width": 1920, "height": 1080},
            args=[
                "--disable-blink-features=AutomationControlled",
                f"--profile-directory=Profile {image_position}"  # Use different profile per agent
            ]
        )

        page = context.pages[0] if context.pages else context.new_page()

        try:
            # Navigate to OneDrive Photos
            print(f"[Image {image_position}] Navigating to OneDrive Photos...")
            page.goto("https://onedrive.live.com/?view=8", wait_until="networkidle", timeout=60000)

            # Wait for gallery to load
            page.wait_for_selector('[aria-label="Photos list"]', timeout=30000)
            time.sleep(3)  # Additional wait for images to render

            # Get all image links in gallery
            image_links = page.locator('main [role="list"] [role="listitem"] a').all()

            if image_position > len(image_links):
                raise Exception(f"Image position {image_position} exceeds gallery size ({len(image_links)} images)")

            # Click on the target image (0-indexed)
            target_image = image_links[image_position - 1]
            image_name = target_image.get_attribute("aria-label") or f"image_{image_position}"
            results["image_name"] = image_name

            print(f"[Image {image_position}] Opening image: {image_name}")
            target_image.click()

            # Wait for image viewer to open
            page.wait_for_selector('[role="menubar"]', timeout=10000)
            time.sleep(2)

            # Test each style preset
            for i, style_name in enumerate(STYLE_PRESETS):
                preset_result = {
                    "style": style_name,
                    "success": False,
                    "generation_time_seconds": None,
                    "error": None,
                    "screenshot": None
                }

                print(f"[Image {image_position}] Testing style {i+1}/14: {style_name}")

                try:
                    # Click Restyle with AI button
                    restyle_btn = page.get_by_role("menuitem", name="Restyle with AI")
                    restyle_btn.click()

                    # Wait for restyle panel to open
                    page.wait_for_selector('text="Let\'s enhance this shot!"', timeout=10000)
                    time.sleep(1)

                    # Find and click the style preset
                    style_btn = page.locator(f'img[alt="{style_name}"]').first

                    generation_start = time.time()
                    style_btn.click()

                    # Wait for generation to complete
                    success = wait_for_generation(page, timeout_seconds=120)
                    generation_time = time.time() - generation_start

                    preset_result["generation_time_seconds"] = round(generation_time, 2)

                    if success:
                        # Take screenshot of result
                        screenshot_path = os.path.join(image_output_dir, f"{style_name.replace(' ', '_').lower()}.png")
                        page.screenshot(path=screenshot_path)
                        preset_result["screenshot"] = screenshot_path
                        preset_result["success"] = True
                        results["success_count"] += 1
                        print(f"[Image {image_position}] {style_name}: SUCCESS ({generation_time:.1f}s)")
                    else:
                        preset_result["error"] = "Generation timeout or error"
                        results["failure_count"] += 1
                        print(f"[Image {image_position}] {style_name}: FAILED")

                    # Close editor to reset for next style
                    close_btn = page.get_by_role("button", name="Close editor")
                    if close_btn.is_visible():
                        close_btn.click()
                        time.sleep(1)

                except Exception as e:
                    preset_result["error"] = str(e)
                    results["failure_count"] += 1
                    print(f"[Image {image_position}] {style_name}: ERROR - {e}")

                    # Try to recover by closing any open dialogs
                    try:
                        close_btn = page.get_by_role("button", name="Close editor")
                        if close_btn.is_visible():
                            close_btn.click()
                    except:
                        pass

                results["presets"].append(preset_result)

        except Exception as e:
            results["error"] = str(e)
            print(f"[Image {image_position}] Fatal error: {e}")

        finally:
            results["end_time"] = datetime.now().isoformat()

            # Save results JSON
            results_path = os.path.join(image_output_dir, "results.json")
            with open(results_path, "w") as f:
                json.dump(results, f, indent=2)

            context.close()

    return results

def main():
    parser = argparse.ArgumentParser(description="AI Restyle Test Agent")
    parser.add_argument("--image-position", type=int, required=True, help="1-based position of image in gallery")
    parser.add_argument("--output-dir", type=str, default="./results", help="Output directory for results")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--browser", type=str, default="edge", choices=["chromium", "edge", "firefox"], help="Browser to use")

    args = parser.parse_args()

    print(f"Starting AI Restyle test for image at position {args.image_position} using {args.browser}")
    results = test_restyle_for_image(args.image_position, args.output_dir, args.headless, args.browser)

    print(f"\nTest complete: {results['success_count']}/14 presets succeeded")
    return results

if __name__ == "__main__":
    main()
