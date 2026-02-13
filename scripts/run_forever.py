import argparse
import random
import subprocess
import sys
import time
from datetime import datetime

def run_once(script_path: str) -> int:
    # Use the current venv's python to run the monitor script
    return subprocess.call([sys.executable, script_path])

def main():
    parser = argparse.ArgumentParser(description="Run divergence_monitor.py on a schedule")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between runs (default: 60)")
    parser.add_argument("--jitter", type=int, default=5, help="Random jitter in seconds added/subtracted (default: 5)")
    parser.add_argument("--script", type=str, default="scripts/divergence_monitor.py", help="Path to monitor script")
    args = parser.parse_args()

    interval = max(5, args.interval)
    jitter = max(0, args.jitter)

    print(f"[run_forever] script={args.script} interval={interval}s jitter=±{jitter}s")
    print("[run_forever] Ctrl+C to stop.\n")

    run_idx = 0
    while True:
       run_idx += 1
        started = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[run_forever] run #{run_idx} start {started}")

        try:
            rc = run_once(args.script)
            ended = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            if rc == 0:
                print(f"[run_forever] run #{run_idx} OK ({ended})\n")
            else:
                print(f"[run_forever] run #{run_idx} FAILED rc={rc} ({ended})\n")
        except KeyboardInterrupt:
            print("\n[run_forever] Stopped by user.")
            break
        except Exception as e:
            print(f"[run_forever] run #{run_idx} ERROR: {e}\n")

        # sleep with jitter so you don't hit APIs at perfectly regular times
        sleep_for = interval + random.randint(-jitter, jitter) if jitter else interval
        sleep_for = max(1, sleep_for)
        time.sleep(sleep_for)

if __name__ == "__main__":
    main()
