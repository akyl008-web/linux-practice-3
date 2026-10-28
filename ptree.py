#!/usr/bin/env python3
"""ПР-3, вариант B. Дерево процессов текущего пользователя по данным /proc (без ps).
Для каждого процесса показывает PID, состояние и RSS. Запуск: python3 ptree.py"""
import os
from collections import defaultdict


def read_proc(pid):
    """Читает /proc/<pid>/status и cmdline. None — если процесс уже завершился."""
    try:
        with open(f"/proc/{pid}/status") as f:
            fields = dict(line.split(":", 1) for line in f if ":" in line)
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmd = f.read().replace(b"\0", b" ").decode(errors="replace").strip()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    return {
        "ppid": int(fields["PPid"]),
        "state": fields["State"].split()[0],
        "uid": int(fields["Uid"].split()[0]),
        # у потоков ядра нет VmRSS
        "rss": int(fields["VmRSS"].split()[0]) if "VmRSS" in fields else 0,
        "cmd": cmd or f"[{fields['Name'].strip()}]",
    }


def main():
    uid = os.getuid()
    procs = {}
    for entry in os.listdir("/proc"):
        if entry.isdigit():
            info = read_proc(int(entry))
            if info and info["uid"] == uid:
                procs[int(entry)] = info

    # корни дерева — процессы, чей родитель не принадлежит пользователю
    children = defaultdict(list)
    roots = []
    for pid in sorted(procs):
        ppid = procs[pid]["ppid"]
        if ppid in procs:
            children[ppid].append(pid)
        else:
            roots.append(pid)

    def show(pid, depth):
        p = procs[pid]
        branch = "    " * (depth - 1) + "└── " if depth else ""
        print(f"{pid:>7}  {p['state']}  {p['rss']:>8} kB  {branch}{p['cmd'][:70]}")
        for child in children[pid]:
            show(child, depth + 1)

    print(f"{'PID':>7}  S  {'RSS':>11}  CMD")
    for pid in roots:
        show(pid, 0)


if __name__ == "__main__":
    main()