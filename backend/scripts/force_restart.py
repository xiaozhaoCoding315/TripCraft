# -*- coding: utf-8 -*-
"""
Force kill all backend processes and restart
"""

import subprocess
import time
import os
import signal
import sys

def force_kill_and_restart():
    """Force kill all uvicorn processes and restart"""

    print("=" * 70)
    print("[TripCraft] Force Restart Backend")
    print("=" * 70)

    # Step 1: Find all PIDs on port 8000
    print("\n[Step 1] Finding processes on port 8000...")
    result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    pids = set()
    for line in lines:
        if ':8000' in line and 'LISTENING' in line:
            pid = line.strip().split()[-1]
            pids.add(pid)

    print(f"Found {len(pids)} processes: {', '.join(pids)}")

    # Step 2: Kill each process
    print("\n[Step 2] Killing processes...")
    for pid in pids:
        try:
            # Use taskkill to force kill
            result = subprocess.run(
                ['taskkill', '/PID', pid, '/F'],
                capture_output=True,
                text=True,
                timeout=5
            )
            print(f"  Killed PID {pid}")
        except Exception as e:
            print(f"  Failed to kill PID {pid}: {e}")

    # Step 3: Wait and verify
    print("\n[Step 3] Waiting for processes to die...")
    time.sleep(3)

    result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    remaining = [line for line in lines if ':8000' in line and 'LISTENING' in line]

    if remaining:
        print(f"[WARNING] {len(remaining)} processes still running on port 8000")
        print("You may need to kill them manually in Task Manager")
        return False
    else:
        print("[OK] Port 8000 is now free!")
        return True

def start_backend():
    """Start the backend server"""

    print("\n" + "=" * 70)
    print("[Step 4] Starting backend server...")
    print("=" * 70)

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(backend_dir)

    print(f"Working directory: {os.getcwd()}")

    try:
        # Start uvicorn
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], check=True)
    except KeyboardInterrupt:
        print("\n[STOP] Backend server stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Backend server failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    success = force_kill_and_restart()
    if success:
        start_backend()
    else:
        print("\n[CANCEL] Cannot start backend while port is in use")
        print("Please kill the processes manually and run again")
        sys.exit(1)
