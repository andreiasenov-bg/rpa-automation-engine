#!/usr/bin/env python3
import subprocess, os, sys, time, signal

# Step 1: git stash + pull
os.chdir('/repo')
r1 = subprocess.run(['git', 'stash'], capture_output=True, text=True)
print(f"git stash: {r1.stdout} {r1.stderr}")
r2 = subprocess.run(['git', 'pull', 'origin', 'main'], capture_output=True, text=True)
print(f"git pull: {r2.stdout} {r2.stderr}")

# Step 2: Find and kill the running deployer to trigger restart
# The container has restart policy, so killing python will restart it
import psutil
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'deployer.py' in ' '.join(proc.info['cmdline'] or []) and proc.pid != os.getpid():
            print(f"Killing deployer PID {proc.pid}")
            proc.kill()
    except:
        pass
print("Done")
