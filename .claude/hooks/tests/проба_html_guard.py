# -*- coding: utf-8 -*-
"""Проба стража HTML: он обязан краснеть на нарушении и молчать на исправном.

Вторая половина здесь не менее важна первой: страж, срабатывающий на верной
работе, хуже отсутствующего — его вывод перестают читать оба.
"""
import json, os, shutil, subprocess, tempfile

import pathlib as _путь
# Страж берётся тот, рядом с которым лежит проба: файлы скопированы в два
# репозитория, и жёсткий путь проверял бы всегда одну копию.
СТРАЖ = str(_путь.Path(__file__).resolve().parent.parent / 'html-guard.py')
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)

def позвать(путь):
    ввод = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": путь}})
    и = subprocess.run(['python3', СТРАЖ], input=ввод, capture_output=True, text=True, timeout=120)
    return и.returncode, (и.stderr or '').strip()

# ── 1. исправный боевой файл: страж обязан молчать ────────────────────────
for файл in ('/workspace/-calculator-test/index.html', '/workspace/-calculator-test/404.html'):
    код, текст = позвать(файл)
    факт(код == 0, f"на исправном {os.path.basename(файл)} страж молчит: код {код}, {текст[:90]!r}")

# ── 2. синтаксическая ошибка ──────────────────────────────────────────────
врем = tempfile.mkdtemp()
битый = os.path.join(врем, 'страница.html')
open(битый, 'w', encoding='utf-8').write(
    "<html><body><script>\nfunction а() { вернуть 1  // скобка не закрыта\n</script></body></html>")
код, текст = позвать(битый)
факт(код == 2 and 'Синтаксическая ошибка' in текст,
     f"незакрытая скобка ловится: код {код}, {текст.splitlines()[0] if текст else ''!r}")
факт('страница.html' in текст and врем not in текст,
     f"в сообщении стоит имя настоящего файла, а не временного: {текст[:70]!r}")

# ── 3. внешний скрипт синтаксис не ломает ─────────────────────────────────
внешний = os.path.join(врем, 'внешний.html')
open(внешний, 'w', encoding='utf-8').write(
    '<html><body><script src="чужой.js"></script></body></html>')
код, _ = позвать(внешний)
факт(код == 0, f"файл без встроенных скриптов проходит: код {код}")

# ── 4. значки версии разошлись ────────────────────────────────────────────
репо = tempfile.mkdtemp()
subprocess.run(['git', 'init', '-q', репо], check=True)
subprocess.run(['git', '-C', репо, 'config', 'user.email', 'п@п'], check=True)
subprocess.run(['git', '-C', репо, 'config', 'user.name', 'п'], check=True)
главный = os.path.join(репо, 'index.html')
ШАБЛОН = ('<html><body><div id="loginVersionBadge" class="lg">v2.5.7 ({0})</div>'
          '<div class="version-badge" id="versionBadge">v2.5.7 ({1})</div>'
          '<script>var a = 1;</script></body></html>')
open(главный, 'w', encoding='utf-8').write(ШАБЛОН.format(31, 31))
subprocess.run(['git', '-C', репо, 'add', '-A'], check=True)
subprocess.run(['git', '-C', репо, 'commit', '-qm', 'начало'], check=True)

код, текст = позвать(главный)
факт(код == 0, f"совпадающие значки проходят: код {код}, {текст[:60]!r}")

open(главный, 'w', encoding='utf-8').write(ШАБЛОН.format(32, 31))
код, текст = позвать(главный)
факт(код == 2 and 'разошлись' in текст, f"разошедшиеся значки ловятся: {текст[:80]!r}")

open(главный, 'w', encoding='utf-8').write(ШАБЛОН.format(30, 30))
код, текст = позвать(главный)
факт(код == 2 and 'назад' in текст, f"откат счётчика ловится: {текст[:80]!r}")

open(главный, 'w', encoding='utf-8').write(ШАБЛОН.format(31, 31))
код, _ = позвать(главный)
факт(код == 0, "тот же номер при повторной правке в той же пачке проходит")
open(главный, 'w', encoding='utf-8').write(ШАБЛОН.format(32, 32))
код, _ = позвать(главный)
факт(код == 0, "возросший номер проходит")

# ── 5. посторонние файлы страж не трогает ─────────────────────────────────
текстовый = os.path.join(врем, 'заметка.md')
open(текстовый, 'w', encoding='utf-8').write('# заметка')
код, _ = позвать(текстовый)
факт(код == 0, "не-html файлы пропускаются без проверки")
код, _ = позвать(os.path.join(врем, 'нет-такого.html'))
факт(код == 0, "исчезнувший файл не роняет стража")

shutil.rmtree(врем, ignore_errors=True); shutil.rmtree(репо, ignore_errors=True)
print("\n".join(отч)); print()
print("\n".join("ЗАМЕЧАНИЕ: " + з for з in зам) if зам else "Замечаний нет")
