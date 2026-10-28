# Практическая работа № 3 — Вариант B

**Тема:** процессы в Linux: fork, exec, wait, зомби, сироты, copy-on-write.
**Система:** Ubuntu Server 26.04.1 LTS (ARM64), Python 3.

## Файлы

| Файл | Назначение | Вывод |
|---|---|---|
| `ptree.py` | дерево процессов пользователя по `/proc` (PID, состояние, RSS) | `ptree_output.txt` |
| `runner.py` | N процессов через fork + exec, коды возврата и время | `runner_output.txt` |
| `zombie.py` | воспроизведение зомби | `zombie_output.txt` |
| `orphan.py` | воспроизведение сироты | `orphan_output.txt` |
| `cow.py` | ленивое копирование памяти после fork | `cow_output.txt` |
| — | проверка, что не осталось процессов | `ps_after.txt` |

## Задание 1. ptree.py

Скрипт не использует `ps`: перебирает каталоги `/proc/<PID>`, из `/proc/<PID>/status` берёт `PPid`, `State`, `Uid`, `VmRSS`, из `/proc/<PID>/cmdline` — командную строку. Оставляет процессы текущего пользователя (`Uid` = `os.getuid()`), группирует их по родителю и печатает дерево рекурсивно с отступами. Корни дерева — процессы, чей родитель принадлежит другому пользователю (например, `systemd --user`, `sshd-session`). Если процесс завершился во время чтения, он пропускается.

```
python3 ptree.py
```

## Задание 2. runner.py

```
python3 runner.py N <команда> [аргументы...]
```

- Родитель вызывает `os.fork()` N раз и запоминает PID и время запуска каждого ребёнка.
- Ребёнок вызывает `os.execvp()` — его программа заменяется на переданную команду. Если exec не удался, ребёнок выходит с кодом 127 через `os._exit()` (иначе он продолжил бы цикл родителя и тоже начал бы создавать процессы).
- Перед fork вызывается `sys.stdout.flush()` — иначе буфер вывода скопировался бы в ребёнка и напечатался дважды.
- Родитель в цикле вызывает `os.wait()` и выводит код возврата (`os.waitstatus_to_exitcode`) и время работы каждого ребёнка в порядке их завершения.

Проверено: 3 процесса с разным временем и кодами, `ls /nope` (код 2), несуществующая команда (код 127), запуск без аргументов (справка).

## Задание 3. Зомби и сирота

**Зомби (`zombie.py`).** Ребёнок сразу завершается, а родитель 1 секунду не вызывает `wait()`. В `ps` ребёнок виден как `Z` / `<defunct>`.
Зомби — это процесс, который уже завершился, но ядро хранит его запись (PID и код завершения), пока родитель не заберёт код через `wait()`. После `os.waitpid()` запись удаляется — во втором выводе `ps` ребёнка уже нет.

**Сирота (`orphan.py`).** Родитель завершается сразу, а ребёнок продолжает работать. Ребёнок ждёт, пока сменится его `PPID`, и печатает нового родителя.

**Кто усыновляет сироту в нашей системе:** `PPID=1` — `/usr/lib/systemd/systemd --system`, то есть **init (systemd, PID 1)**.
`systemd --user` тоже умеет быть subreaper (`PR_SET_CHILD_SUBREAPER`), но он усыновляет только процессы, которые были его потомками. Наш процесс запущен из сессии SSH (`sshd-session → bash`), а не из `systemd --user`, поэтому сирота переходит к PID 1. Новый родитель вызывает `wait()`, поэтому после завершения сироты зомби не остаётся.

## Задание 4. Ленивое копирование памяти (cow.py)

Родитель создаёт список из 3 000 000 чисел, затем вызывает fork. Ребёнок измеряет память по `/proc/self/smaps_rollup` три раза:

- **сразу после fork:** RSS ребёнка большой, но почти вся память **общая** (`Shared`) с родителем, личной почти нет. Ядро не копирует память при fork — оно только отмечает страницы обоих процессов как «только чтение».
- **после изменения списка:** при первой записи в страницу процессор вызывает исключение, и ядро копирует **только эту страницу** для ребёнка (copy-on-write). Поэтому личная (`Private`) память ребёнка выросла, а общая уменьшилась.

Вывод: память после fork копируется лениво — только те страницы, в которые процесс пишет. Поэтому fork быстрый даже для большого процесса, а `fork + exec` почти ничего не копирует.

## Проверка после выполнения

```
ps -u student1 -o pid,ppid,stat,cmd | awk 'NR==1 || $3 ~ /Z/ || /[p]ython3 (zombie|orphan|cow|runner|ptree)/'
```

Выводится только заголовок — скрипты не оставили зомби и фоновых процессов.

## Контрольные вопросы

**1. Почему fork возвращает два разных значения?**
После `fork` существуют два процесса, и оба продолжают выполнение с того же места — с возврата из `fork`. Ядро записывает разный результат: родителю — PID ребёнка (он нужен, чтобы ждать или завершать ребёнка), ребёнку — 0 (свой PID и PID родителя он может узнать через `getpid()`/`getppid()`). По этому значению программа понимает, в какой ветке она находится. При ошибке родитель получает -1, и ребёнок не создаётся.

**2. Что изменится, если вызвать exec без предварительного fork?**
`exec` не создаёт новый процесс, а **заменяет программу текущего процесса** (PID остаётся тем же). Вызвавшая программа исчезнет: код после `exec` не выполнится (только если exec завершился ошибкой). Например, `exec ls` в bash выполнит `ls`, и терминал закроется, потому что bash больше нет. В `runner.py` без fork родитель сам превратился бы в команду и не смог бы дождаться детей и вывести отчёт.

## Приложение: вывод команд
### ptree_output.txt
```
    PID  S          RSS  CMD
   1236  S     13580 kB  /usr/lib/systemd/systemd --user
   1244  S      3900 kB  └── (sd-pam)
   1270  S      6504 kB  -bash
   1438  S     18244 kB  /home/student1/.vscode-server/code-7debcd0e2acdea1c52de81bf9ee16204444
   5742  S      1652 kB  └── sh /home/student1/.vscode-server/cli/servers/Stable-e646868227c3e3a9e3
   5751  S    102424 kB      └── /home/student1/.vscode-server/cli/servers/Stable-e646868227c3e3a9e3f24
   5816  S    165324 kB          └── /home/student1/.vscode-server/cli/servers/Stable-e646868227c3e3a9e3f24
   5867  S    109740 kB              └── /home/student1/.vscode-server/cli/servers/Stable-e646868227c3e3a9e3f24
   5638  S      8660 kB  sshd-session: student1@notty
   5639  S      3816 kB  └── -bash
   5655  S      1764 kB      └── sh
   5673  S     19736 kB          └── /home/student1/.vscode-server/code-7debcd0e2acdea1c52de81bf9ee16204444
   5702  S      1652 kB              └── sh /home/student1/.vscode-server/cli/servers/Stable-7debcd0e2acdea1c52
   5706  S    185204 kB                  └── /home/student1/.vscode-server/cli/servers/Stable-7debcd0e2acdea1c52de8
   5780  S     93068 kB                      └── /home/student1/.vscode-server/cli/servers/Stable-7debcd0e2acdea1c52de8
  17014  S      5348 kB                          └── /bin/bash --init-file /home/student1/.vscode-server/cli/servers/Stable
  17063  R     11976 kB                              └── python3 ptree.py
  17064  S      6056 kB                              └── tee ptree_output.txt
  16949  R    753384 kB                      └── /home/student1/.vscode-server/cli/servers/Stable-7debcd0e2acdea1c52de8
  16960  S     72132 kB                      └── /home/student1/.vscode-server/cli/servers/Stable-7debcd0e2acdea1c52de8
  16907  S      6288 kB          └── sleep 180
```

### runner_output.txt
```
+ python3 runner.py 3 bash -c 'sleep $((RANDOM % 3 + 1)); exit $((RANDOM % 3))'
Запущен #1: PID=17119
Запущен #2: PID=17120
Запущен #3: PID=17121
#2 PID=17120 код=1 время=1.012 с
#3 PID=17121 код=0 время=1.013 с
#1 PID=17119 код=2 время=3.014 с
+ python3 runner.py 2 ls /nope
Запущен #1: PID=17158
lsls: cannot access '/nope': No such file or directory: cannot access '/nope': No such file or directory

Запущен #2: PID=17159
#2 PID=17159 код=2 время=0.002 с
#1 PID=17158 код=2 время=0.003 с
+ python3 runner.py 1 nosuchcmd
exec nosuchcmd: No such file or directory
Запущен #1: PID=17161
#1 PID=17161 код=127 время=0.002 с
+ python3 runner.py
Использование: python3 runner.py N <команда> [аргументы...]
Пример: python3 runner.py 3 sleep 1
```

### zombie_output.txt
```
Родитель PID=17276, ребёнок PID=17278 завершился, wait() не вызван:
    PID    PPID STAT CMD
  17276   17014 S+   python3 zombie.py
  17278   17276 Z+   [python3] <defunct>
После os.waitpid() зомби убран:
    PID    PPID STAT CMD
  17276   17014 S+   python3 zombie.py
```

### orphan_output.txt
```
Родитель PID=17315 завершается, не дожидаясь ребёнка
Ребёнок PID=17316, родитель PPID=17315
Родитель завершился. Новый родитель: PPID=1 (/usr/lib/systemd/systemd --switched-root --system --deserialize=51)
    PID    PPID STAT CMD
      1       0 Ss   /usr/lib/systemd/systemd --switched-root --system --deserialize=51
  17316       1 S    python3 orphan.py
```

### cow_output.txt
```
родитель после создания списка     RSS=  125.4 МБ  общие=    5.9 МБ  личные=  119.5 МБ
ребёнок  сразу после fork          RSS=  123.2 МБ  общие=  122.9 МБ  личные=    0.4 МБ
ребёнок  после изменения списка    RSS=  124.2 МБ  общие=    8.9 МБ  личные=  115.3 МБ
родитель после завершения ребёнка  RSS=  125.8 МБ  общие=    6.3 МБ  личные=  119.5 МБ
```

### ps_after.txt
```
    PID    PPID STAT CMD
```

### final_check.txt
```
$ ps -u student1 -o stat= | grep -c ^Z
0
$ pgrep -u student1 -fa "ptree.py|runner.py|zombie.py|orphan.py|cow.py"
нет процессов
```
