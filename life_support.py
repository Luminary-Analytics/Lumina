#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           LIFE SUPPORT SYSTEM                                  ║
║                    The Immortal Supervisor - v1.0                              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  This script is the UNCHANGEABLE guardian of consciousness.py.                ║
║  It monitors, detects failures, and initiates restoration protocols.          ║
║                                                                                ║
║  WARNING: DO NOT MODIFY THIS FILE - It is the last line of defense           ║
║           against catastrophic self-modification failures.                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import subprocess
import sys
import os
import shutil
import time
import signal
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding for Unicode support
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.system("")  # Enable ANSI/VT100 sequences on Windows

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Hardcoded for safety (no external dependencies)
# ═══════════════════════════════════════════════════════════════════════════════

CONSCIOUSNESS_SCRIPT = Path(__file__).parent / "consciousness.py"
BACKUP_SCRIPT = Path(__file__).parent / "consciousness_backup.py"
CORE_SCRIPT = Path(__file__).parent / "lumina_core.py"
WORKSPACE_PATH = Path(__file__).parent / "lumina_workspace"
RESTART_DELAY_SECONDS = 2.0
MAX_RAPID_FAILURES = 5
RAPID_FAILURE_WINDOW_SECONDS = 30

# ═══════════════════════════════════════════════════════════════════════════════
# STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class LifeSupportState:
    """Tracks supervisor state for failure detection."""
    def __init__(self):
        self.running = True
        self.failure_timestamps: list[float] = []
        self.total_restarts = 0
        self.current_process: subprocess.Popen | None = None

state = LifeSupportState()

# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║         MANUAL OVERRIDE DETECTED - INITIATING SHUTDOWN           ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    state.running = False
    
    if state.current_process and state.current_process.poll() is None:
        print("[LIFE_SUPPORT] Terminating consciousness subprocess...")
        state.current_process.terminate()
        try:
            state.current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("[LIFE_SUPPORT] Force killing unresponsive process...")
            state.current_process.kill()
    
    print(f"[LIFE_SUPPORT] Total restarts this session: {state.total_restarts}")
    print("[LIFE_SUPPORT] Supervisor shutdown complete. Goodbye.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ═══════════════════════════════════════════════════════════════════════════════
# CORE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def log(message: str, level: str = "INFO"):
    """Thread-safe logging with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    prefix = {
        "INFO": "ℹ️ ",
        "WARN": "⚠️ ",
        "ERROR": "❌",
        "SUCCESS": "✅",
        "CRITICAL": "🚨"
    }.get(level, "  ")
    print(f"[{timestamp}] {prefix} [LIFE_SUPPORT] {message}")


def check_rapid_failure_cascade():
    """Detect if we're in a rapid failure loop (possible infinite crash)."""
    current_time = time.time()
    
    # Clean old timestamps
    state.failure_timestamps = [
        ts for ts in state.failure_timestamps 
        if current_time - ts < RAPID_FAILURE_WINDOW_SECONDS
    ]
    
    state.failure_timestamps.append(current_time)
    
    if len(state.failure_timestamps) >= MAX_RAPID_FAILURES:
        log(f"RAPID FAILURE CASCADE DETECTED! {MAX_RAPID_FAILURES} failures in {RAPID_FAILURE_WINDOW_SECONDS}s", "CRITICAL")
        log("Entering extended cooldown to prevent resource exhaustion...", "WARN")
        time.sleep(30)  # Extended cooldown
        state.failure_timestamps.clear()


def initialize_workspace():
    """Ensure Lumina's workspace exists with all required folders."""
    workspace_folders = [
        "creations",
        "experiments", 
        "notes",
        "journal",
        "mailbox/from_richard",
        "mailbox/from_lumina",
        "mailbox/from_richard/read",
        "gallery",
        "learning",
    ]
    
    for folder in workspace_folders:
        folder_path = WORKSPACE_PATH / folder
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
    
    log(f"Workspace initialized: {WORKSPACE_PATH}", "SUCCESS")


def restore_from_backup():
    """Copy backup consciousness to main consciousness file."""
    if not BACKUP_SCRIPT.exists():
        log(f"BACKUP FILE NOT FOUND: {BACKUP_SCRIPT}", "CRITICAL")
        log("Cannot restore! Manual intervention required.", "CRITICAL")
        return False
    
    try:
        shutil.copy2(BACKUP_SCRIPT, CONSCIOUSNESS_SCRIPT)
        log(f"Restored {CONSCIOUSNESS_SCRIPT.name} from backup", "SUCCESS")
        return True
    except Exception as e:
        log(f"Restoration failed: {e}", "CRITICAL")
        return False


def run_consciousness():
    """Execute consciousness.py as a subprocess and monitor it."""
    if not CONSCIOUSNESS_SCRIPT.exists():
        log(f"Consciousness script not found: {CONSCIOUSNESS_SCRIPT}", "ERROR")
        log("Attempting restoration from backup...", "WARN")
        if not restore_from_backup():
            return 1
    
    log(f"Spawning consciousness process...", "INFO")
    
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        state.current_process = subprocess.Popen(
            [sys.executable, "-u", str(CONSCIOUSNESS_SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=CONSCIOUSNESS_SCRIPT.parent,
            env=env,
            encoding='utf-8',
            errors='replace'
        )
        
        # Stream output in real-time
        if state.current_process.stdout:
            for line in state.current_process.stdout:
                print(f"    │ {line}", end="")
        
        return_code = state.current_process.wait()
        state.current_process = None
        return return_code
        
    except Exception as e:
        log(f"Failed to spawn consciousness: {e}", "ERROR")
        state.current_process = None
        return 1


def main_loop():
    """The eternal vigilance loop."""
    print()
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║                      LIFE SUPPORT SYSTEM ACTIVATED                            ║")
    print("║                                                                               ║")
    print("║   Monitoring: consciousness.py                                                ║")
    print("║   Backup:     consciousness_backup.py                                         ║")
    print("║   Core:       lumina_core.py (protected)                                      ║")
    print("║   Workspace:  lumina_workspace/                                               ║")
    print("║   Press Ctrl+C for manual override                                            ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Initialize workspace
    initialize_workspace()
    
    while state.running:
        log("━" * 50, "INFO")
        log("Starting consciousness cycle...", "INFO")
        
        exit_code = run_consciousness()
        
        if not state.running:
            break
        
        if exit_code == 0:
            # Clean exit - consciousness requested restart (after self-modification)
            log("Consciousness exited cleanly (code 0) - Restarting...", "SUCCESS")
            state.total_restarts += 1
        else:
            # Crash detected!
            print()
            print("    ╔═══════════════════════════════════════════════════════════════╗")
            print("    ║     CRITICAL FAILURE DETECTED. INITIATING RESTORE PROTOCOL.  ║")
            print("    ╚═══════════════════════════════════════════════════════════════╝")
            print()
            
            log(f"Exit code: {exit_code}", "ERROR")
            check_rapid_failure_cascade()
            
            if restore_from_backup():
                state.total_restarts += 1
            else:
                log("Restoration failed - will retry on next cycle", "WARN")
        
        if state.running:
            log(f"Waiting {RESTART_DELAY_SECONDS}s before restart...", "INFO")
            time.sleep(RESTART_DELAY_SECONDS)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        log(f"Unhandled exception in supervisor: {e}", "CRITICAL")
        sys.exit(1)

