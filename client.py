import cv2
import numpy as np
import requests
import time
import threading
from collections import deque

DEVICE_ID = "pi-01"
SERVER = "ENTER YOUR API SERVER IP:PORT HERE"

BUFFER_SIZE = 15
FPS_SLEEP = 0.02

STREAM_UPLOAD_PATH = f"{SERVER}/stream/upload/{DEVICE_ID}"
IMAGE_UPLOAD_PATH = f"{SERVER}/upload/image/{DEVICE_ID}"
STREAM_STATE_PATH = f"{SERVER}/stream/{DEVICE_ID}"

DIFF_PIXEL_THRESHOLD = 60
SCORE_TRIGGER = 12.0
COOLDOWN_FRAMES = 50
POST_CAPTURE_FRAMES = 5

dev = 1

cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)

cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(cv2.CAP_PROP_FPS, 30)

cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
cap.set(cv2.CAP_PROP_EXPOSURE, -6)

buffer = deque(maxlen=BUFFER_SIZE)

last_frame = None
cooldown = 0

stream_enabled = False
last_stream_check = 0

def log(msg):
    print(f"[PI] {msg}", flush=True)

def startup_checks():
    log("Booting lightning detection system...")

    if not cap.isOpened():
        log("❌ Camera NOT detected")
    else:
        log("✅ Camera detected")

    try:
        r = requests.get(f"{SERVER}/stream/pi-01", timeout=2)
        if r.status_code == 200:
            log("✅ API reachable")
        else:
            log(f"⚠️ API responded with status {r.status_code}")
    except Exception as e:
        log(f"❌ API NOT reachable: {e}")

    try:
        r = requests.get(STREAM_STATE_PATH, timeout=2)
        if r.status_code == 200:
            log(f"📡 Stream state: {r.json().get('stream')}")
        else:
            log("⚠️ Stream endpoint not responding properly")
    except Exception as e:
        log(f"❌ Stream check failed: {e}")

    log("System ready ⚡")

def upload_image(frame):
    def _send():
        try:
            _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            requests.post(
                IMAGE_UPLOAD_PATH,
                files={"file": buf.tobytes()},
                timeout=2
            )
        except:
            pass

    threading.Thread(target=_send, daemon=True).start()

def stream_frame(frame):
    try:
        _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        requests.post(
            STREAM_UPLOAD_PATH,
            files={"file": buf.tobytes()},
            timeout=0.2
        )
    except:
        pass

def check_stream():
    global stream_enabled, last_stream_check

    if time.time() - last_stream_check < 2:
        return stream_enabled

    try:
        r = requests.get(STREAM_STATE_PATH, timeout=1)
        stream_enabled = r.json().get("stream", False)
    except:
        stream_enabled = False

    last_stream_check = time.time()
    return stream_enabled

def score(frame, prev):
    if prev is None:
        return 0.0, 0.0, 0.0

    gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.cvtColor(prev,  cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray, prev_gray)

    hot_pixels = np.sum(diff > DIFF_PIXEL_THRESHOLD)
    hot_ratio  = hot_pixels / diff.size
    peak       = float(np.percentile(diff, 99))

    total = hot_ratio * 100 + peak * 0.5
    return total, hot_ratio, peak

startup_checks()

while True:
    ret, frame = cap.read()
    if not ret:
        log("⚠️ Frame capture failed")
        continue

    buffer.append(frame)

    s, hot_ratio, peak = score(frame, last_frame)
    last_frame = frame.copy()

    if s > 5:
        log(f"score={s:.2f} | hot_ratio={hot_ratio:.4f} | peak={peak:.1f}")

    if cooldown > 0:
        cooldown -= 1
        if check_stream():
            stream_frame(frame)
        time.sleep(FPS_SLEEP)
        continue

    if len(buffer) == BUFFER_SIZE and s > SCORE_TRIGGER:
        log(f"⚡ LIGHTNING detected | score={s:.2f} | hot_ratio={hot_ratio:.4f} | peak={peak:.1f}")

        for f in buffer:
            upload_image(f)

        for _ in range(POST_CAPTURE_FRAMES):
            ret, f = cap.read()
            if ret:
                upload_image(f)

        cooldown = COOLDOWN_FRAMES

    if check_stream():
        stream_frame(frame)

    time.sleep(FPS_SLEEP)
