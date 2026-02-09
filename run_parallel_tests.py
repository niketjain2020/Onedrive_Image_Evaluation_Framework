"""
Parallel AI Restyle Test Runner
Launches multiple test agents to test different images simultaneously.

Usage:
    python run_parallel_tests.py --images 1,2,3 --output-dir ./results
    python run_parallel_tests.py --images 1-5 --output-dir ./results
"""

import argparse
import subprocess
import sys
import os
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def parse_image_range(image_arg: str) -> list:
    """Parse image positions from argument like '1,2,3' or '1-5'"""
    positions = []
    for part in image_arg.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            positions.extend(range(start, end + 1))
        else:
            positions.append(int(part))
    return sorted(set(positions))

def run_agent(image_position: int, output_dir: str, headless: bool = False) -> dict:
    """Run a single agent as a subprocess."""
    script_dir = Path(__file__).parent
    agent_script = script_dir / "restyle_agent.py"

    cmd = [
        sys.executable,
        str(agent_script),
        "--image-position", str(image_position),
        "--output-dir", output_dir
    ]

    if headless:
        cmd.append("--headless")

    print(f"[Runner] Starting agent for image {image_position}")
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout per image
        )

        elapsed = time.time() - start_time
        print(f"[Runner] Agent for image {image_position} completed in {elapsed:.1f}s")

        # Load results from file
        results_path = os.path.join(output_dir, f"image_{image_position}", "results.json")
        if os.path.exists(results_path):
            with open(results_path, 'r') as f:
                return json.load(f)

        return {
            "image_position": image_position,
            "error": result.stderr or "Unknown error",
            "stdout": result.stdout
        }

    except subprocess.TimeoutExpired:
        return {
            "image_position": image_position,
            "error": "Timeout - agent took longer than 30 minutes"
        }
    except Exception as e:
        return {
            "image_position": image_position,
            "error": str(e)
        }

def generate_report(all_results: list, output_dir: str):
    """Generate a summary report of all test results."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_images_tested": len(all_results),
        "total_presets_per_image": 14,
        "results_summary": [],
        "overall_success_rate": 0
    }

    total_success = 0
    total_tests = 0

    for result in all_results:
        img_summary = {
            "image_position": result.get("image_position"),
            "image_name": result.get("image_name", "Unknown"),
            "success_count": result.get("success_count", 0),
            "failure_count": result.get("failure_count", 0),
            "error": result.get("error")
        }

        if "presets" in result:
            avg_time = sum(
                p.get("generation_time_seconds", 0) or 0
                for p in result["presets"]
            ) / len(result["presets"])
            img_summary["avg_generation_time_seconds"] = round(avg_time, 2)

            total_success += result.get("success_count", 0)
            total_tests += len(result["presets"])

        report["results_summary"].append(img_summary)

    if total_tests > 0:
        report["overall_success_rate"] = round(total_success / total_tests * 100, 1)

    # Save report
    report_path = os.path.join(output_dir, "test_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Images tested: {len(all_results)}")
    print(f"Total tests: {total_tests}")
    print(f"Successes: {total_success}")
    print(f"Success rate: {report['overall_success_rate']}%")
    print(f"\nDetailed report saved to: {report_path}")
    print("="*60)

    return report

def main():
    parser = argparse.ArgumentParser(description="Parallel AI Restyle Test Runner")
    parser.add_argument("--images", type=str, required=True, help="Image positions to test (e.g., '1,2,3' or '1-5')")
    parser.add_argument("--output-dir", type=str, default="./results", help="Output directory for results")
    parser.add_argument("--max-parallel", type=int, default=3, help="Maximum parallel agents (browser instances)")
    parser.add_argument("--headless", action="store_true", help="Run browsers in headless mode")

    args = parser.parse_args()

    # Parse image positions
    image_positions = parse_image_range(args.images)
    print(f"Testing {len(image_positions)} images: {image_positions}")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Run agents in parallel
    all_results = []

    with ThreadPoolExecutor(max_workers=args.max_parallel) as executor:
        # Submit all tasks
        futures = {
            executor.submit(run_agent, pos, args.output_dir, args.headless): pos
            for pos in image_positions
        }

        # Collect results as they complete
        for future in as_completed(futures):
            pos = futures[future]
            try:
                result = future.result()
                all_results.append(result)
            except Exception as e:
                all_results.append({
                    "image_position": pos,
                    "error": str(e)
                })

    # Sort results by image position
    all_results.sort(key=lambda x: x.get("image_position", 0))

    # Generate report
    generate_report(all_results, args.output_dir)

if __name__ == "__main__":
    main()
