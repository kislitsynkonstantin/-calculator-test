#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Страж HTML: синтаксис встроенных скриптов и значок версии.

Срабатывает после каждой записи в *.html (PostToolUse на Edit и Write).

Почему это вынесено из CLAUDE.md в хук. Оба правила отвечают трём условиям:
у них есть механический признак, их нарушение мне в момент нарушения не видно,
и стоит оно дорого. Опечатка в собранном скрипте не видна до открытия страницы
в браузере; забытый значок версии расходится с журналом обновлений, и потом
неясно, какая версия что содержит. Правила, которые я нарушаю осознанно, в хук
не выносятся — там довольно текста.

Что именно проверяется:

1. Синтаксис. Из файла вынимаются все встроенные <script> без src, склеиваются
   и проверяются node --check. Ровно тот же приём, каким я проверяю правки
   вручную, — теперь он не зависит от того, вспомнил я о нём или нет.

2. Значок версии в index.html. Их два — на экране входа и в самом расчёте, —
   и они обязаны совпадать между собой: разошлись однажды, и по значку стало
   невозможно понять, что перед тобой. Счётчик итераций не убывает: правило
   «одна выкладка — одна итерация» допускает несколько правок под тем же
   номером, но откат номера назад означает, что журнал и файл разъехались.

Отказ возвращается кодом 2 и текстом в stderr: он попадает в переписку, и
правка чинится сразу, а не всплывает на выкладке.
"""
import json
import os
import re
import subprocess
import sys
import tempfile


def прочитать_ввод():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def встроенные_скрипты(текст):
    """Скрипты без src — только они исполняются из самого файла."""
    return re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", текст, re.S)


def проверить_синтаксис(путь, текст):
    куски = встроенные_скрипты(текст)
    if not куски:
        return None
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as ф:
        ф.write("\n;\n".join(куски))
        временный = ф.name
    try:
        итог = subprocess.run(["node", "--check", временный],
                              capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # node недоступен — молчим: страж не должен останавливать работу
        # из-за собственной неисправности.
        return None
    finally:
        os.unlink(временный)
    if итог.returncode == 0:
        return None
    # В сообщении node стоит имя временного файла — подменяем на настоящее,
    # иначе строка ошибки указывает в никуда.
    сообщение = (итог.stderr or "").replace(временный, os.path.basename(путь))
    return "Синтаксическая ошибка в " + os.path.basename(путь) + ":\n" + сообщение.strip()


ЗНАЧОК = re.compile(r'id="(loginVersionBadge|versionBadge)"[^>]*>\s*v([\d.]+)\s*\((\d+)\)')


def значки(текст):
    return {и: (в, int(н)) for и, в, н in ЗНАЧОК.findall(текст)}


def проверить_значок(путь, текст):
    если_не_главный = os.path.basename(путь) != "index.html"
    if если_не_главный:
        return None
    нынешние = значки(текст)
    if len(нынешние) < 2:
        return None  # значков нет — файл не тот, о котором правило
    значения = set(нынешние.values())
    if len(значения) > 1:
        части = ", ".join(f"{и}: v{в} ({н})" for и, (в, н) in нынешние.items())
        return ("Значки версии разошлись между собой — " + части +
                ". На экране входа и в расчёте должен стоять один и тот же номер.")
    версия, номер = значения.pop()

    каталог = os.path.dirname(os.path.abspath(путь))
    имя = os.path.basename(путь)
    try:
        было = subprocess.run(["git", "-C", каталог, "show", "HEAD:" + имя],
                              capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if было.returncode != 0:
        return None  # файл ещё не под версионным контролем
    прежние = значки(было.stdout)
    if not прежние:
        return None
    _, прежний_номер = next(iter(прежние.values()))
    if номер < прежний_номер:
        return (f"Счётчик итераций пошёл назад: в коммите ({прежний_номер}), "
                f"в файле ({номер}). Номер не убывает даже при откате — "
                f"после ({прежний_номер}) идёт ({прежний_номер + 1}).")
    return None


def главная():
    ввод = прочитать_ввод()
    сведения = ввод.get("tool_input") or {}
    путь = сведения.get("file_path") or ""
    if not путь.lower().endswith(".html") or not os.path.exists(путь):
        sys.exit(0)
    try:
        текст = open(путь, encoding="utf-8").read()
    except OSError:
        sys.exit(0)

    беды = [б for б in (проверить_синтаксис(путь, текст),
                        проверить_значок(путь, текст)) if б]
    if беды:
        print("\n\n".join(беды), file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    главная()
