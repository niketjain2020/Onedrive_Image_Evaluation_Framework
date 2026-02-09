"""
True Parallel AI Restyle Test Runner
Runs multiple browser instances simultaneously using shared auth state.

Usage:
    1. First run: python parallel_runner.py --setup-auth
       (Opens browser for you to log in, saves auth state)

    2. Then run: python parallel_runner.py --images 1,2 --styles 3
       (Runs parallel tests using saved auth)
"""

import argparse
import json
import os
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright

# Style presets (first 3 for quick test, all 14 available)
STYLE_PRESETS = [
    "Movie Poster", "Plush Toy", "Anime", "Chibi Sticker", "Caricature",
    "Superhero", "Toy Model", "Graffiti", "Crochet Art", "Doodle",
    "Pencil Portrait", "Storybook", "Photo Booth", "Pop Art"
]

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE = os.path.join(OUTPUT_DIR, "auth_state.json")
RESULTS_DIR = os.path.join(OUTPUT_DIR, "results")


def setup_auth():
    """Open browser and wait for login, then save auth state."""
    print("Opening browser for authentication...")
    print("Please log in to OneDrive. Will auto-detect when you're logged in.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="msedge")
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        page.goto("https://onedrive.live.com/?view=8")

        # Wait for Photos list to appear (indicates successful login)
        print("Waiting for login... (looking for Photos gallery)")
        try:
            page.wait_for_selector('[aria-label="Photos list"]', timeout=180000)  # 3 min timeout
            print("Login detected! Saving auth state...")
            time.sleep(2)  # Let page fully load
        except:
            print("Timeout waiting for login. Saving current state anyway...")

        # Save auth state
        context.storage_state(path=AUTH_FILE)
        print(f"Auth state saved to: {AUTH_FILE}")

        browser.close()


def test_image(image_position: int, num_styles: int, thread_id: int):
    """Test one image with specified number of styles."""
    results = {
        "image_position": image_position,
        "thread_id": thread_id,
        "start_time": datetime.now().isoformat(),
        "styles_tested": [],
        "success_count": 0,
        "failure_count": 0
    }

    image_dir = os.path.join(RESULTS_DIR, f"image_{image_position}")
    os.makedirs(image_dir, exist_ok=True)

    print(f"[Thread {thread_id}] Starting Image {image_position} with {num_styles} styles")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="msedge",
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            storage_state=AUTH_FILE,
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()

        try:
            # Navigate to OneDrive Photos gallery
            print(f"[Thread {thread_id}] Navigating to OneDrive Photos...")
            page.goto("https://onedrive.live.com/?view=8", timeout=60000)

            # Wait for page to settle
            time.sleep(3)
            current_url = page.url
            print(f"[Thread {thread_id}] Current URL: {current_url}")

            # Check if redirected to login
            if "login" in current_url.lower():
                page.screenshot(path=os.path.join(image_dir, "login_redirect.png"))
                raise Exception(f"Redirected to login page. Auth state may be invalid. URL: {current_url}")

            # If we're on Files view, click Photos tab
            try:
                photos_tab = page.get_by_role("tab", name="Photos")
                if photos_tab.is_visible():
                    print(f"[Thread {thread_id}] Clicking Photos tab...")
                    photos_tab.click()
                    time.sleep(2)
            except:
                pass  # Already on Photos view

            # Wait for Photos list with retry
            print(f"[Thread {thread_id}] Waiting for Photos gallery to load...")
            try:
                page.wait_for_selector('[aria-label="Photos list"]', timeout=45000)
            except:
                # Take debug screenshot on failure
                page.screenshot(path=os.path.join(image_dir, "page_state.png"))
                print(f"[Thread {thread_id}] Page URL: {page.url}")
                print(f"[Thread {thread_id}] Page title: {page.title()}")
                raise Exception(f"Photos list not found. Page may not have loaded correctly.")

            time.sleep(2)

            # Click on target image - use the Photos list aria-label for reliable selection
            images = page.locator('[aria-label="Photos list"] > [role="listitem"] a').all()
            print(f"[Thread {thread_id}] Found {len(images)} images in gallery")

            # If no images found, wait a bit more and retry
            if len(images) == 0:
                print(f"[Thread {thread_id}] No images found, waiting for gallery to populate...")
                time.sleep(5)
                images = page.locator('[aria-label="Photos list"] > [role="listitem"] a').all()
                print(f"[Thread {thread_id}] Retry: Found {len(images)} images")

            if image_position > len(images):
                page.screenshot(path=os.path.join(image_dir, "gallery_state.png"))
                raise Exception(f"Image {image_position} not found (only {len(images)} images)")

            images[image_position - 1].click()
            print(f"[Thread {thread_id}] Clicked image {image_position}, waiting for viewer...")

            # Wait for viewer menubar to appear (contains Restyle with AI)
            page.wait_for_selector('[role="menubar"]', timeout=15000)
            # Also wait specifically for the Restyle button to be ready
            page.wait_for_selector('text="Restyle with AI"', timeout=15000)
            time.sleep(2)  # Extra time for UI to stabilize
            print(f"[Thread {thread_id}] Viewer opened successfully")

            # Test each style
            for i, style_name in enumerate(STYLE_PRESETS[:num_styles]):
                style_result = {"style": style_name, "success": False, "time": None}

                try:
                    print(f"[Thread {thread_id}] Image {image_position}: Testing {style_name}")

                    # Open Restyle panel
                    page.get_by_role("menuitem", name="Restyle with AI").click()
                    page.wait_for_selector('text="Let\'s enhance this shot!"', timeout=10000)
                    time.sleep(1)

                    # Click style
                    start = time.time()
                    page.locator(f'img[alt="{style_name}"]').first.click()
                    time.sleep(0.5)
                    page.get_by_role("button", name="Send").click()

                    # Wait for completion (check for Save copy button enabled)
                    page.wait_for_selector('button:has-text("Save copy"):not([disabled])', timeout=120000)
                    elapsed = time.time() - start

                    # Screenshot
                    screenshot_path = os.path.join(image_dir, f"{style_name.lower().replace(' ', '_')}.png")
                    page.screenshot(path=screenshot_path)

                    style_result["success"] = True
                    style_result["time"] = round(elapsed, 1)
                    style_result["screenshot"] = screenshot_path
                    results["success_count"] += 1

                    print(f"[Thread {thread_id}] Image {image_position}: {style_name} SUCCESS ({elapsed:.1f}s)")

                    # Reset for next style
                    page.get_by_role("button", name="Reset").click()
                    time.sleep(1)

                except Exception as e:
                    style_result["error"] = str(e)
                    results["failure_count"] += 1
                    print(f"[Thread {thread_id}] Image {image_position}: {style_name} FAILED - {e}")

                    # Try to recover
                    try:
                        page.get_by_role("button", name="Close editor").click()
                        time.sleep(1)
                    except:
                        pass

                results["styles_tested"].append(style_result)

        except Exception as e:
            results["error"] = str(e)
            print(f"[Thread {thread_id}] Image {image_position}: FATAL ERROR - {e}")

        finally:
            results["end_time"] = datetime.now().isoformat()

            # Save results
            with open(os.path.join(image_dir, "results.json"), "w") as f:
                json.dump(results, f, indent=2)

            browser.close()

    return results


def run_parallel_tests(image_positions: list, num_styles: int):
    """Run tests on multiple images in parallel."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"PARALLEL AI RESTYLE TEST")
    print(f"Images: {image_positions}")
    print(f"Styles per image: {num_styles}")
    print(f"{'='*60}\n")

    all_results = []

    with ThreadPoolExecutor(max_workers=len(image_positions)) as executor:
        futures = {
            executor.submit(test_image, pos, num_styles, i+1): pos
            for i, pos in enumerate(image_positions)
        }

        for future in as_completed(futures):
            result = future.result()
            all_results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")

    total_success = sum(r.get("success_count", 0) for r in all_results)
    total_tests = sum(len(r.get("styles_tested", [])) for r in all_results)

    for r in all_results:
        print(f"Image {r['image_position']}: {r.get('success_count', 0)}/{len(r.get('styles_tested', []))} passed")

    if total_tests > 0:
        print(f"\nOverall: {total_success}/{total_tests} ({100*total_success/total_tests:.0f}% success rate)")
    else:
        print(f"\nOverall: No tests completed (check auth state)")
    print(f"Results saved to: {RESULTS_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Parallel AI Restyle Tester")
    parser.add_argument("--setup-auth", action="store_true", help="Set up authentication (run first)")
    parser.add_argument("--images", type=str, help="Comma-separated image positions (e.g., '1,2')")
    parser.add_argument("--styles", type=int, default=3, help="Number of styles to test per image (default: 3)")

    args = parser.parse_args()

    if args.setup_auth:
        setup_auth()
        return

    if not args.images:
        print("Usage:")
        print("  First:  python parallel_runner.py --setup-auth")
        print("  Then:   python parallel_runner.py --images 1,2 --styles 3")
        return

    if not os.path.exists(AUTH_FILE):
        print(f"Auth file not found: {AUTH_FILE}")
        print("Run with --setup-auth first to log in and save auth state.")
        return

    image_positions = [int(x) for x in args.images.split(",")]
    run_parallel_tests(image_positions, args.styles)


if __name__ == "__main__":
    main()
