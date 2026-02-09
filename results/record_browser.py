import cv2
import numpy as np
import mss
import pygetwindow as gw
import time
from pathlib import Path

# Find the browser window
windows = gw.getWindowsWithTitle('OneDrive')
if not windows:
    windows = gw.getWindowsWithTitle('Chrome')

if not windows:
    print("Browser window not found!")
    exit(1)

win = windows[0]
print(f"Found window: {win.title}")
print(f"Position: {win.left}, {win.top}, {win.width}, {win.height}")

# Activate the window
win.activate()
time.sleep(0.5)

# Define the monitor region (browser window area)
monitor = {
    "left": win.left,
    "top": win.top,
    "width": win.width,
    "height": win.height
}

# Video settings
output_path = str(Path(__file__).resolve().parent / 'Claude_Code_BugBash_Demo_Browser.mp4')
fps = 15
duration = 45  # seconds
total_frames = fps * duration

# Initialize video writer
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (monitor["width"], monitor["height"]))

print(f"Recording {duration} seconds at {fps} fps...")
print(f"Output: {output_path}")

with mss.mss() as sct:
    start_time = time.time()
    frame_count = 0

    while frame_count < total_frames:
        # Capture screen
        img = sct.grab(monitor)
        frame = np.array(img)

        # Convert BGRA to BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        # Write frame
        out.write(frame)
        frame_count += 1

        # Control frame rate
        elapsed = time.time() - start_time
        expected_time = frame_count / fps
        if expected_time > elapsed:
            time.sleep(expected_time - elapsed)

        # Progress update every second
        if frame_count % fps == 0:
            print(f"Recording: {frame_count // fps}s / {duration}s")

out.release()
print(f"\nRecording complete! Saved to: {output_path}")
