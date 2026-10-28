#!/usr/bin/env python3
"""ПР-3, вариант B. Ленивое копирование памяти после fork (copy-on-write).
Ребёнок измеряет свою память до и после изменения большого списка, унаследованного от родителя."""
import os
import sys

N = 3_000_000  # ~110 МБ: массив ссылок + объекты int


def mem():
    """RSS, общие и личные страницы процесса в МБ (из /proc/self/smaps_rollup)."""
    kb = {}
    with open("/proc/self/smaps_rollup") as f:
        for line in f:
            key, _, rest = line.partition(":")
            if rest.strip().endswith("kB"):
                kb[key] = int(rest.split()[0])
    shared = kb["Shared_Clean"] + kb["Shared_Dirty"]
    private = kb["Private_Clean"] + kb["Private_Dirty"]
    return kb["Rss"] / 1024, shared / 1024, private / 1024


def show(who, when):
    rss, shared, private = mem()
    print(f"{who:<9}{when:<26}RSS={rss:7.1f} МБ  общие={shared:7.1f} МБ  личные={private:7.1f} МБ",
          flush=True)


data = list(range(N))
show("родитель", "после создания списка")

sys.stdout.flush()
pid = os.fork()
if pid == 0:
    show("ребёнок", "сразу после fork")
    for i in range(N):
        data[i] = -i  # запись в унаследованный список
    show("ребёнок", "после изменения списка")
    os._exit(0)

os.waitpid(pid, 0)
show("родитель", "после завершения ребёнка")