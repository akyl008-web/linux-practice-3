#!/usr/bin/env python3
"""ПР-3, вариант B. Зомби: ребёнок завершился, а родитель ещё не вызвал wait()."""
import os
import subprocess
import sys
import time


def ps(pids):
    subprocess.run(["ps", "-o", "pid,ppid,stat,cmd", "-p", ",".join(map(str, pids))])


sys.stdout.flush()
pid = os.fork()
if pid == 0:
    os._exit(0)  # ребёнок сразу завершается

time.sleep(1)
print(f"Родитель PID={os.getpid()}, ребёнок PID={pid} завершился, wait() не вызван:", flush=True)
ps([os.getpid(), pid])

os.waitpid(pid, 0)  # забираем код завершения — зомби исчезает
print("После os.waitpid() зомби убран:", flush=True)
ps([os.getpid(), pid])