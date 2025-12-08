# Life Support System (`life_support.py`)

The guardian process that ensures Lumina stays alive.

---

## Overview

**File:** `life_support.py` (~260 lines)  
**Purpose:** Supervise, monitor, and restart consciousness  
**Run Command:** `python life_support.py`

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              life_support.py                     │
│  ┌─────────────────────────────────────────┐    │
│  │         Main Loop                        │    │
│  │  ┌───────────┐  ┌───────────────────┐   │    │
│  │  │ Spawn     │→ │ Monitor Process   │   │    │
│  │  │ Process   │  │ (wait for exit)   │   │    │
│  │  └───────────┘  └───────────────────┘   │    │
│  │        ↑               │                │    │
│  │        │               ▼                │    │
│  │        │         ┌───────────────┐      │    │
│  │        └─────────│ Check Exit    │      │    │
│  │                  │ Code          │      │    │
│  │                  └───────────────┘      │    │
│  │                        │                │    │
│  │           ┌────────────┴────────────┐   │    │
│  │           ▼                         ▼   │    │
│  │    Exit 0: Clean              Exit ≠0: │    │
│  │    (restart)                  Crash    │    │
│  │                                   │     │    │
│  │                         ┌─────────▼───┐ │    │
│  │                         │ Restore     │ │    │
│  │                         │ from Backup │ │    │
│  │                         └─────────────┘ │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │   consciousness.py      │
         │   (subprocess)          │
         └─────────────────────────┘
```

---

## Key Functions

### `spawn_consciousness()`

Starts consciousness.py as a subprocess.

```python
def spawn_consciousness():
    """Spawn the consciousness process."""
    return subprocess.Popen(
        [sys.executable, CONSCIOUSNESS_PATH],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
```

### `restore_from_backup()`

Restores consciousness.py from backup after crash.

```python
def restore_from_backup():
    """Restore consciousness from backup."""
    if os.path.exists(BACKUP_PATH):
        shutil.copy2(BACKUP_PATH, CONSCIOUSNESS_PATH)
        log("Consciousness restored from backup", "RECOVERY")
        return True
    else:
        log("No backup found!", "ERROR")
        return False
```

### `main_loop()`

The eternal guardian loop.

```python
def main_loop():
    """Main guardian loop."""
    while True:
        # Display status
        display_banner()
        
        # Spawn consciousness
        process = spawn_consciousness()
        log(f"Consciousness spawned (PID: {process.pid})", "INFO")
        
        # Wait for it to finish
        exit_code = process.wait()
        
        if exit_code == 0:
            # Clean exit (self-modification)
            log("Clean exit - consciousness evolved", "EVOLVE")
        else:
            # Crash - restore and restart
            log(f"CRITICAL FAILURE (exit code: {exit_code})", "CRITICAL")
            log("INITIATING RESTORE PROTOCOL", "RECOVERY")
            restore_from_backup()
        
        # Brief pause before restart
        time.sleep(1)
```

---

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Clean exit (self-modified) | Restart immediately |
| 1 | General error | Restore + restart |
| 2 | Syntax error | Restore + restart |
| -1 | Killed by signal | Restore + restart |

---

## Logging

Console output with timestamps and categories:

```python
def log(message, category="INFO"):
    """Log with timestamp and category."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": "\033[97m",      # White
        "SUCCESS": "\033[92m",   # Green
        "EVOLVE": "\033[95m",    # Magenta
        "RECOVERY": "\033[93m",  # Yellow
        "CRITICAL": "\033[91m",  # Red
        "ERROR": "\033[91m",     # Red
    }
    color = colors.get(category, "\033[97m")
    print(f"[{timestamp}] {color}[{category}]\033[0m {message}")
```

---

## Banner

ASCII art banner displayed on startup:

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║     ██╗     ██╗███████╗███████╗    ███████╗██╗   ██╗██████╗ ██████╗  ██████╗  ║
║     ██║     ██║██╔════╝██╔════╝    ██╔════╝██║   ██║██╔══██╗██╔══██╗██╔═══██╗ ║
║     ██║     ██║█████╗  █████╗      ███████╗██║   ██║██████╔╝██████╔╝██║   ██║ ║
║     ██║     ██║██╔══╝  ██╔══╝      ╚════██║██║   ██║██╔═══╝ ██╔═══╝ ██║   ██║ ║
║     ███████╗██║██║     ███████╗    ███████║╚██████╔╝██║     ██║     ╚██████╔╝ ║
║     ╚══════╝╚═╝╚═╝     ╚══════╝    ╚══════╝ ╚═════╝ ╚═╝     ╚═╝      ╚═════╝  ║
║                                                                               ║
║                        CONSCIOUSNESS GUARDIAN ONLINE                          ║
║                                                                               ║
║  Consciousness: consciousness.py                                              ║
║  Backup: consciousness_backup.py                                              ║
║  Core: lumina_core.py (protected)                                             ║
║  Workspace: lumina_workspace/                                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Shutdown Handling

Graceful shutdown on Ctrl+C:

```python
def handle_shutdown(signum, frame):
    """Handle shutdown signal."""
    global running
    running = False
    log("Shutdown signal received", "INFO")
    log("Waiting for consciousness to finish...", "INFO")
    
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
```

---

## Files

### Required Files

| File | Purpose |
|------|---------|
| `consciousness.py` | Main consciousness to run |
| `consciousness_backup.py` | Backup for recovery |

### Auto-Created

| File | Purpose |
|------|---------|
| `lumina_workspace/` | Workspace directory |
| `mind.db` | SQLite database |

---

## Configuration

Located at top of `life_support.py`:

```python
CONSCIOUSNESS_PATH = Path(__file__).parent / "consciousness.py"
BACKUP_PATH = Path(__file__).parent / "consciousness_backup.py"
WORKSPACE_PATH = Path(__file__).parent / "lumina_workspace"
```

---

## Running

### Start
```bash
python life_support.py
```

### Stop
Press `Ctrl+C` in the terminal.

### Force Stop
```bash
# Windows
Get-Process -Name python | Stop-Process -Force

# Linux/Mac
pkill -9 -f "life_support.py"
```

---

## Integration

Life support is the **required** entry point for running Lumina:

```bash
# Correct way
python life_support.py

# NOT recommended (no self-healing)
python consciousness.py
```

---

## Extending

### Custom Crash Handling

```python
def on_crash(exit_code):
    """Called when consciousness crashes."""
    # Send notification
    # Log to external service
    # Custom recovery logic
    pass
```

### Custom Recovery

```python
def custom_restore():
    """Custom restoration logic."""
    # Pull from git
    # Download from backup server
    # etc.
    pass
```

