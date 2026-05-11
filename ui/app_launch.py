# Cell 39 — Launch WealthOS (fixed)
import subprocess, sys, time

print("Starting WealthOS — this takes 60-90 seconds for model to load...")
print("Watch for the gradio.live URL below:\n")

process = subprocess.Popen(
    [sys.executable, "/content/WealthOS/ui/app.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Stream output live for 3 minutes max
import time
start = time.time()
while time.time() - start < 180:
    line = process.stdout.readline()
    if line:
        print(line, end="", flush=True)
        if "gradio.live" in line or "127.0.0.1" in line:
            print("\n✅ WealthOS is live! Click the URL above.")
            break
    else:
        time.sleep(0.5)