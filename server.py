from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse, Response
import os
import time
import glob
import numpy as np
import cv2
import signal

app = FastAPI()
_shutdown = False

def _handle_sig(sig, frame):
    global _shutdown
    _shutdown = True
    raise SystemExit(0)

signal.signal(signal.SIGINT, _handle_sig)
signal.signal(signal.SIGTERM, _handle_sig)
BASE = "data"
os.makedirs(BASE, exist_ok=True)
stream_enabled = {}
latest_frame = {}
frame_count_cache = {}


def dev_dir(dev):
    path = os.path.join(BASE, dev)
    os.makedirs(path, exist_ok=True)
    return path

@app.post("/upload/image/{device_id}")
async def upload_image(device_id: str, file: UploadFile = File(...)):
    path = os.path.join(dev_dir(device_id), "images")
    os.makedirs(path, exist_ok=True)
    fname = f"{time.time()}.jpg"
    with open(os.path.join(path, fname), "wb") as f:
        f.write(await file.read())
    return {"ok": True}

@app.post("/stream/upload/{device_id}")
async def stream_upload(device_id: str, file: UploadFile = File(...)):
    data = await file.read()
    nparr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is not None:
        latest_frame[device_id] = frame
    return {"ok": True}

@app.get("/stream/{device_id}")
def get_stream(device_id: str):
    return {"stream": stream_enabled.get(device_id, False)}


@app.post("/stream/{device_id}/toggle")
def toggle_stream(device_id: str):
    stream_enabled[device_id] = not stream_enabled.get(device_id, False)
    return {"stream": stream_enabled[device_id]}

@app.get("/mjpeg/{device_id}")
def mjpeg(device_id: str):
    def gen():
        while not _shutdown:
            if not stream_enabled.get(device_id, False):
                time.sleep(0.2)
                continue
            frame = latest_frame.get(device_id)
            if frame is None:
                time.sleep(0.05)
                continue
            _, jpg = cv2.imencode(".jpg", frame)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpg.tobytes()
                + b"\r\n"
            )
            time.sleep(0.05)

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/image/{device_id}/{filename}")
def serve_image(device_id: str, filename: str):
    path = os.path.join(BASE, device_id, "images", filename)
    if not os.path.exists(path):
        return Response("not found", status_code=404)
    return FileResponse(path)

@app.get("/api/stats/{device_id}")
def stats(device_id: str):
    path = os.path.join(BASE, device_id, "images")
    if not os.path.exists(path):
        return {"total": 0, "events": 0, "last_seen": None, "first_seen": None, "frames_per_event": 0, "uptime_days": 0}

    files = sorted(glob.glob(os.path.join(path, "*.jpg")))
    if not files:
        return {"total": 0, "events": 0, "last_seen": None, "first_seen": None, "frames_per_event": 0, "uptime_days": 0}

    events = 0
    last_ts = None
    first_ts = None
    event_sizes = []
    current_event_size = 0

    for f in files:
        try:
            ts = float(os.path.basename(f).replace(".jpg", ""))
            if first_ts is None:
                first_ts = ts
            if last_ts is None or ts - last_ts > 10:
                if current_event_size > 0:
                    event_sizes.append(current_event_size)
                events += 1
                current_event_size = 1
            else:
                current_event_size += 1
            last_ts = ts
        except:
            pass

    if current_event_size > 0:
        event_sizes.append(current_event_size)

    avg_frames = round(sum(event_sizes) / len(event_sizes), 1) if event_sizes else 0
    uptime_days = round((last_ts - first_ts) / 86400, 1) if first_ts and last_ts else 0

    return {
        "total": len(files),
        "events": events,
        "last_seen": last_ts,
        "first_seen": first_ts,
        "frames_per_event": avg_frames,
        "uptime_days": uptime_days,
    }

@app.get("/events/{device_id}", response_class=HTMLResponse)
def image_gallery(device_id: str):
    path = os.path.join(BASE, device_id, "images")
    files = sorted(glob.glob(os.path.join(path, "*.jpg")), reverse=True)

    events = []
    current_event = []
    last_ts = None

    for f in reversed(files):
        try:
            ts = float(os.path.basename(f).replace(".jpg", ""))
            if last_ts is None or ts - last_ts > 10:
                if current_event:
                    events.append(current_event)
                current_event = [f]
            else:
                current_event.append(f)
            last_ts = ts
        except:
            pass

    if current_event:
        events.append(current_event)

    events.reverse()
    events = events[:30]

    events_html = ""
    for i, event_files in enumerate(events):
        try:
            ts = float(os.path.basename(event_files[0]).replace(".jpg", ""))
            date_str = time.strftime("%d %b %Y", time.localtime(ts))
            time_str = time.strftime("%H:%M:%S", time.localtime(ts))
        except:
            date_str = "Unknown"
            time_str = ""

        thumbs = ""
        for f in event_files[:20]:
            fname = os.path.basename(f)
            thumbs += f'<img src="/image/{device_id}/{fname}" loading="lazy" onclick="openFull(this.src)" title="{fname}"/>'

        events_html += f"""
        <div class="event-block">
            <div class="event-bar">
                <span><span class="event-ts">{time_str}</span><span class="event-date">{date_str}</span></span>
                <span class="event-n">{len(event_files)} frames</span>
            </div>
            <div class="event-frames">{thumbs}</div>
        </div>
        """

    if not events_html:
        events_html = '<div class="empty">no events captured yet</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>stormwatch / events</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #111;
    --surface: #1a1a1a;
    --border: #2a2a2a;
    --text: #ccc;
    --dim: #555;
    --hi: #e0e0e0;
    --act: #c8a84b;
  }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Courier New', Courier, monospace; font-size: 12px; line-height: 1.5; }}
  a {{ color: inherit; text-decoration: none; }}
  header {{ border-bottom: 1px solid var(--border); padding: 0 16px; display: flex; align-items: center; justify-content: space-between; height: 36px; }}
  .logo {{ color: var(--hi); font-size: 12px; letter-spacing: 0.05em; }}
  nav a {{ color: var(--dim); margin-left: 16px; font-size: 11px; }}
  nav a:hover {{ color: var(--hi); }}
  nav a.active {{ color: var(--hi); border-bottom: 1px solid var(--hi); }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 20px 16px; }}
  .page-meta {{ color: var(--dim); font-size: 11px; margin-bottom: 20px; border-left: 2px solid var(--border); padding-left: 8px; }}
  .event-block {{ border: 1px solid var(--border); margin-bottom: 12px; }}
  .event-bar {{ display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: var(--surface); border-bottom: 1px solid var(--border); }}
  .event-ts {{ color: var(--hi); font-size: 11px; }}
  .event-date {{ color: var(--dim); font-size: 11px; margin-left: 12px; }}
  .event-n {{ color: var(--dim); font-size: 11px; }}
  .event-frames {{ padding: 8px 10px; display: flex; flex-wrap: wrap; gap: 4px; background: var(--bg); }}
  .event-frames img {{ width: 130px; height: 80px; object-fit: cover; border: 1px solid var(--border); cursor: pointer; display: block; }}
  .event-frames img:hover {{ border-color: var(--act); }}
  .empty {{ color: var(--dim); padding: 32px 16px; border: 1px solid var(--border); }}
  .lightbox {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.95); z-index: 100; align-items: center; justify-content: center; cursor: pointer; }}
  .lightbox.open {{ display: flex; }}
  .lightbox img {{ max-width: 92vw; max-height: 92vh; display: block; border: 1px solid var(--border); }}
</style>
</head>
<body>
<header>
  <span class="logo">stormwatch</span>
  <nav>
    <a href="/">live</a>
    <a href="/events/{device_id}" class="active">events</a>
  </nav>
</header>
<main>
  <div class="page-meta">{device_id} / {len(files)} frames / {len(events)} events</div>
  {events_html}
</main>
<div class="lightbox" id="lb" onclick="closeFull()">
  <img id="lb-img" src=""/>
</div>
<script>
  function openFull(src) {{ document.getElementById('lb-img').src = src; document.getElementById('lb').classList.add('open'); }}
  function closeFull() {{ document.getElementById('lb').classList.remove('open'); }}
  document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeFull(); }});
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
def ui():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>stormwatch</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #111;
    --surface: #1a1a1a;
    --border: #2a2a2a;
    --text: #ccc;
    --dim: #555;
    --hi: #e0e0e0;
    --act: #c8a84b;
    --live: #5a9e6f;
  }
  body { background: var(--bg); color: var(--text); font-family: 'Courier New', Courier, monospace; font-size: 12px; line-height: 1.5; }
  a { color: inherit; text-decoration: none; }
  header { border-bottom: 1px solid var(--border); padding: 0 16px; display: flex; align-items: center; justify-content: space-between; height: 36px; }
  .logo { color: var(--hi); font-size: 12px; letter-spacing: 0.05em; }
  nav a { color: var(--dim); margin-left: 16px; font-size: 11px; }
  nav a:hover { color: var(--hi); }
  nav a.active { color: var(--hi); border-bottom: 1px solid var(--hi); }

  main { max-width: 1200px; margin: 0 auto; padding: 20px 16px; display: grid; grid-template-columns: 1fr 220px; gap: 16px; align-items: start; }

  .stream-wrap { border: 1px solid var(--border); }
  .stream-bar { display: flex; align-items: center; justify-content: space-between; padding: 5px 10px; background: var(--surface); border-bottom: 1px solid var(--border); }
  .stream-label { color: var(--hi); font-size: 11px; }
  .stream-label .status { color: var(--dim); margin-left: 8px; }
  .stream-label .status.live { color: var(--live); }
  .stream-body { position: relative; background: #000; aspect-ratio: 16/9; }
  .stream-body img { width: 100%; height: 100%; object-fit: contain; display: block; }
  .stream-off { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--dim); font-size: 11px; }
  .stream-foot { display: flex; align-items: center; justify-content: space-between; padding: 5px 10px; background: var(--surface); border-top: 1px solid var(--border); }

  .btn { padding: 3px 10px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font-size: 11px; font-family: inherit; cursor: pointer; }
  .btn:hover { border-color: var(--dim); color: var(--hi); }
  .btn.on { border-color: var(--act); color: var(--act); }

  .sidebar { display: flex; flex-direction: column; gap: 1px; border: 1px solid var(--border); }
  .s-section { background: var(--surface); }
  .s-head { padding: 4px 10px; border-bottom: 1px solid var(--border); color: var(--dim); font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; }
  .s-row { display: flex; justify-content: space-between; padding: 4px 10px; border-bottom: 1px solid var(--border); }
  .s-row:last-child { border-bottom: none; }
  .s-key { color: var(--dim); font-size: 11px; }
  .s-val { color: var(--hi); font-size: 11px; text-align: right; }
  .s-val.act { color: var(--act); }
  .s-val.live { color: var(--live); }
  .s-link { display: block; padding: 6px 10px; background: var(--bg); border-top: 1px solid var(--border); color: var(--dim); font-size: 11px; text-align: center; }
  .s-link:hover { color: var(--hi); background: var(--surface); }

  .fs { display: none; position: fixed; inset: 0; background: #000; z-index: 200; flex-direction: column; }
  .fs.open { display: flex; }
  .fs img { flex: 1; width: 100%; object-fit: contain; min-height: 0; }
  .fs-off { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--dim); font-size: 11px; }
  .fs-bar { display: flex; align-items: center; justify-content: space-between; padding: 6px 14px; background: var(--surface); border-top: 1px solid var(--border); flex-shrink: 0; }
  .fs-bar span { font-size: 11px; color: var(--dim); }
  .fs-bar span.live { color: var(--live); }

  @media (max-width: 680px) { main { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <span class="logo">stormwatch</span>
  <nav>
    <a href="/" class="active">live</a>
    <a href="/events/pi-01">events</a>
  </nav>
</header>

<main>
  <div class="stream-wrap">
    <div class="stream-bar">
      <span class="stream-label">pi-01 &mdash; <span class="status" id="status-text">checking</span></span>
      <button class="btn" onclick="openFS()">[ fullscreen ]</button>
    </div>
    <div class="stream-body">
      <img id="stream-img" src="" style="display:none"/>
      <div class="stream-off" id="stream-off">stream off</div>
    </div>
    <div class="stream-foot">
      <span style="color:var(--dim);font-size:11px" id="foot-left">&nbsp;</span>
      <button class="btn" id="toggle-btn" onclick="toggleStream()">enable stream</button>
    </div>
  </div>

  <div class="sidebar">
    <div class="s-section">
      <div class="s-head">capture</div>
      <div class="s-row"><span class="s-key">frames</span><span class="s-val" id="stat-total">—</span></div>
      <div class="s-row"><span class="s-key">events</span><span class="s-val act" id="stat-events">—</span></div>
      <div class="s-row"><span class="s-key">avg frames/evt</span><span class="s-val" id="stat-avg">—</span></div>
      <div class="s-row"><span class="s-key">last event</span><span class="s-val" id="stat-last">—</span></div>
      <div class="s-row"><span class="s-key">first event</span><span class="s-val" id="stat-first">—</span></div>
      <div class="s-row"><span class="s-key">days active</span><span class="s-val" id="stat-uptime">—</span></div>
    </div>
    <div class="s-section">
      <div class="s-head">system</div>
      <div class="s-row"><span class="s-key">device</span><span class="s-val">pi-01</span></div>
      <div class="s-row"><span class="s-key">stream</span><span class="s-val" id="stream-state">off</span></div>
      <div class="s-row"><span class="s-key">time</span><span class="s-val" id="stat-time">—</span></div>
    </div>
    <a class="s-link" href="/events/pi-01">view all events &rarr;</a>
  </div>
</main>

<div class="fs" id="fs">
  <img id="fs-img" src="" style="display:none"/>
  <div class="fs-off" id="fs-off">stream off</div>
  <div class="fs-bar">
    <span id="fs-label">stream disabled</span>
    <button class="btn" onclick="closeFS()">close</button>
  </div>
</div>

<script>
  let isLive = false;

  async function fetchStatus() {
    try {
      const r = await fetch('/stream/pi-01');
      isLive = (await r.json()).stream;
      updateUI();
    } catch(e) {}
  }

  async function fetchStats() {
    try {
      const d = await (await fetch('/api/stats/pi-01')).json();
      document.getElementById('stat-total').textContent   = d.total;
      document.getElementById('stat-events').textContent  = d.events;
      document.getElementById('stat-avg').textContent     = d.frames_per_event || '—';
      document.getElementById('stat-uptime').textContent  = d.uptime_days ? d.uptime_days + 'd' : '—';
      document.getElementById('stat-last').textContent    = d.last_seen  ? new Date(d.last_seen*1000).toLocaleString()  : '—';
      document.getElementById('stat-first').textContent   = d.first_seen ? new Date(d.first_seen*1000).toLocaleDateString() : '—';
    } catch(e) {}
  }

  function updateUI() {
    const src = '/mjpeg/pi-01?' + Date.now();
    const img = document.getElementById('stream-img');
    const off = document.getElementById('stream-off');
    const btn = document.getElementById('toggle-btn');
    const st  = document.getElementById('status-text');
    const ss  = document.getElementById('stream-state');

    st.textContent  = isLive ? 'live' : 'off';
    st.className    = isLive ? 'status live' : 'status';
    ss.textContent  = isLive ? 'on' : 'off';
    ss.className    = isLive ? 's-val live' : 's-val';
    btn.textContent = isLive ? 'disable stream' : 'enable stream';
    btn.className   = isLive ? 'btn on' : 'btn';

    if (isLive) { img.src = src; img.style.display = 'block'; off.style.display = 'none'; }
    else        { img.style.display = 'none'; img.src = ''; off.style.display = 'flex'; }

    const fsImg = document.getElementById('fs-img');
    const fsOff = document.getElementById('fs-off');
    const fsLbl = document.getElementById('fs-label');
    fsLbl.textContent = isLive ? 'live' : 'stream disabled';
    fsLbl.className   = isLive ? 'live' : '';
    if (isLive) { if (!fsImg.src.includes('/mjpeg/')) fsImg.src = src; fsImg.style.display = 'block'; fsOff.style.display = 'none'; }
    else        { fsImg.style.display = 'none'; fsImg.src = ''; fsOff.style.display = 'flex'; }
  }

  async function toggleStream() {
    await fetch('/stream/pi-01/toggle', { method: 'POST' });
    await fetchStatus();
  }

  function openFS()  { document.getElementById('fs').classList.add('open');    updateUI(); }
  function closeFS() { document.getElementById('fs').classList.remove('open'); document.getElementById('fs-img').src = ''; }

  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeFS(); });

  fetchStatus();
  fetchStats();
  setInterval(fetchStatus, 3000);
  setInterval(fetchStats, 10000);
  setInterval(() => { document.getElementById('stat-time').textContent = new Date().toLocaleTimeString(); }, 1000);
</script>
</body>
</html>"""
