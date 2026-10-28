#!/usr/bin/env python3
"""ПР-3, вариант B. Сирота: родитель завершается раньше ребёнка."""
import os
import subprocess
import sys
import time

parent = os.getpid()
sys.stdout.flush()
pid = os.fork()
if pid == 0:
    print(f"Ребёнок PID={os.getpid()}, родитель PPID={os.getppid()}", flush=True)
    for _ in range(50):  # ждём, пока родитель завершится (до 5 с)
        if os.getppid() != parent:
            break
        time.sleep(0.1)
    new = os.getppid()
    with open(f"/proc/{new}/cmdline", "rb") as f:
        name = f.read().replace(b"\0", b" ").decode().strip()
    print(f"Родитель завершился. Новый родитель: PPID={new} ({name})", flush=True)
    subprocess.run(["ps", "-o", "pid,ppid,stat,cmd", "-p", f"{os.getpid()},{new}"])
    os._exit(0)

print(f"Родитель PID={parent} завершается, не дожидаясь ребёнка", flush=True)