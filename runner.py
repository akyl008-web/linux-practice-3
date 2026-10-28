#!/usr/bin/env python3
"""ПР-3, вариант B. Запускает N дочерних процессов (fork), каждый выполняет команду (exec).
Родитель ждёт всех и выводит код возврата и время работы каждого.
Запуск: python3 runner.py N <команда> [аргументы...]"""
import os
import sys
import time


def main():
    if len(sys.argv) < 3 or not sys.argv[1].isdigit() or int(sys.argv[1]) < 1:
        print("Использование: python3 runner.py N <команда> [аргументы...]", file=sys.stderr)
        print("Пример: python3 runner.py 3 sleep 1", file=sys.stderr)
        sys.exit(1)

    n = int(sys.argv[1])
    cmd = sys.argv[2:]
    started = {}  # PID -> (номер, время запуска)

    for i in range(1, n + 1):
        sys.stdout.flush()  # иначе буфер вывода скопируется в ребёнка и напечатается дважды
        pid = os.fork()
        if pid == 0:
            # ребёнок: заменяем свою программу на команду
            try:
                os.execvp(cmd[0], cmd)
            except OSError as e:
                print(f"exec {cmd[0]}: {e.strerror}", file=sys.stderr, flush=True)
                os._exit(127)  # обязательно выйти, иначе ребёнок продолжит цикл родителя
        started[pid] = (i, time.monotonic())
        print(f"Запущен #{i}: PID={pid}")

    # родитель: ждём всех детей в порядке завершения
    while started:
        pid, status = os.wait()
        i, t0 = started.pop(pid)
        code = os.waitstatus_to_exitcode(status)  # отрицательный — убит сигналом
        print(f"#{i} PID={pid} код={code} время={time.monotonic() - t0:.3f} с")


if __name__ == "__main__":
    main()