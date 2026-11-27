"""Generate a tiny synthetic screen recording (smoke test): python mkdemo.py out.mp4
Run it with the venv python, or any python that has opencv-python + numpy."""
import sys

import cv2
import numpy as np

w = cv2.VideoWriter(sys.argv[1], cv2.VideoWriter_fourcc(*"mp4v"), 10, (1280, 720))
for i in range(300):
    f = np.full((720, 1280, 3), 255, np.uint8)
    cv2.putText(f, "SAP Easy Access", (50, 60), 0, 1.5, (0, 0, 0), 3)
    if i > 100:
        cv2.putText(f, "Delivery 8001153201", (300, 300), 0, 1.5, (0, 0, 255), 3)
    if i > 200:
        cv2.rectangle(f, (700, 400), (1100, 600), (0, 128, 0), -1)
        cv2.putText(f, "Saved OK", (720, 520), 0, 1.5, (255, 255, 255), 3)
    w.write(f)
w.release()
