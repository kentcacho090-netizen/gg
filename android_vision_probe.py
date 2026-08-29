#!/usr/bin/env python3
"""Android vision smoke-test for the CoC automation project.

Run this BEFORE enabling any automated taps. It verifies:
  1. Android screenshot capture
  2. OpenCV image decoding
  3. whether the installed Ultralytics/PyTorch stack can start without a
     native crash on this Android/Termux environment
  4. YOLO model loading and detections, when that stack is available

The reference project's model is downloaded from its public repository only
when --download-model is supplied.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://raw.githubusercontent.com/anugrhaswi/Coc-Auto-Farm/main/models/best.pt"
)
DEFAULT_MODEL = Path("models/best.pt")


def say(label: str, value: object) -> None:
    print(f"[{label}] {value}", flush=True)


def check_native_stack() -> bool:
    """Import Ultralytics in a child process so a native segfault is contained."""
    code = (
        "import cv2; print('opencv=' + cv2.__version__); "
        "from ultralytics import YOLO; print('ultralytics=OK')"
    )
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    if p.returncode == 0:
        say("ML", "Ultralytics import OK")
        if p.stdout.strip():
            print(p.stdout.strip())
        return True

    if p.returncode < 0:
        say("ML", f"native process crash (signal {-p.returncode}); YOLO disabled")
    else:
        say("ML", f"import failed (exit {p.returncode}); YOLO disabled")
    if p.stderr.strip():
        print(p.stderr.strip())
    return False


def download_model(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    say("MODEL", f"downloading {MODEL_URL}")
    with urllib.request.urlopen(MODEL_URL, timeout=60) as src, tmp.open("wb") as dst:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
    if tmp.stat().st_size < 1_000_000:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Downloaded model is unexpectedly small")
    tmp.replace(path)
    say("MODEL", f"saved {path} ({path.stat().st_size:,} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="autoc_test.png")
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--download-model", action="store_true")
    parser.add_argument("--conf", type=float, default=0.35)
    args = parser.parse_args()

    image_path = Path(args.image).expanduser().resolve()
    model_path = Path(args.model).expanduser().resolve()

    # Import our tiny controller first. It has no ML dependencies.
    from android_controller import AndroidController

    controller = AndroidController(image_path)
    try:
        captured = controller.capture()
        say("SCREEN", captured)
    except Exception as exc:
        say("ERROR", exc)
        return 2

    try:
        import cv2
    except Exception as exc:
        say("ERROR", f"OpenCV unavailable: {exc}")
        return 3

    frame = cv2.imread(str(image_path))
    if frame is None:
        say("ERROR", "OpenCV could not decode the screenshot")
        return 4
    say("IMAGE", f"{frame.shape[1]}x{frame.shape[0]} BGR")

    if args.download_model and not model_path.exists():
        try:
            download_model(model_path)
        except Exception as exc:
            say("ERROR", f"model download failed: {exc}")
            return 5

    if not model_path.exists():
        say("MODEL", f"not found: {model_path}")
        say("NEXT", "rerun with --download-model")
        return 0

    if not check_native_stack():
        say("NEXT", "keep the current non-YOLO screenshot/OCR diagnostics; do not run YOLO yet")
        return 6

    try:
        from ultralytics import YOLO
        model = YOLO(str(model_path))
        results = model.predict(source=frame, conf=args.conf, verbose=False)
        detections = []
        for box in results[0].boxes:
            cls_id = int(box.cls.item())
            name = str(model.names[cls_id])
            conf = float(box.conf.item())
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().tolist()
            detections.append({
                "name": name,
                "confidence": round(conf, 3),
                "center": [round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1)],
                "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
            })
        say("DETECTIONS", json.dumps(detections, separators=(",", ":")))
        return 0
    except Exception as exc:
        say("ERROR", f"YOLO inference failed: {exc}")
        return 7


if __name__ == "__main__":
    raise SystemExit(main())
