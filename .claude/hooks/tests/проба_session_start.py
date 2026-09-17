#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Двусторонняя проба хука запуска сессии.

Хук ставит оснастку визуальных проб и обязан выполнять три обещания:
на машине Константина молчать, в облаке ставить и называть браузер,
и ни при каких обстоятельствах не валить сессию.
"""
import os
import pathlib
import subprocess
import sys
import tempfile

ХУК = pathlib.Path(__file__).resolve().parent.parent / "session-start.sh"
НАХОДКИ = []


def запустить(среда):
    окружение = dict(os.environ)
    окружение.pop("CLAUDE_CODE_REMOTE", None)
    окружение.update(среда)
    return subprocess.run(["bash", str(ХУК)], capture_output=True, text=True,
                          env=окружение, timeout=600)


def главная():
    if not os.access(ХУК, os.X_OK):
        НАХОДКИ.append("хук не помечен исполняемым — Claude Code его не запустит")

    # ── на машине Константина: тишина ────────────────────────────────────────
    итог = запустить({})
    if итог.returncode != 0:
        НАХОДКИ.append(f"вне облака хук вышел с {итог.returncode}, а должен молча с нулём")
    if итог.stdout.strip():
        НАХОДКИ.append(f"вне облака хук что-то печатает: {итог.stdout.strip()[:80]!r}")

    # ── в облаке: ставит, называет браузер, кладёт его в переменную ──────────
    with tempfile.TemporaryDirectory() as каталог:
        файл = pathlib.Path(каталог) / "env"
        итог = запустить({"CLAUDE_CODE_REMOTE": "true", "CLAUDE_ENV_FILE": str(файл)})
        if итог.returncode != 0:
            НАХОДКИ.append(f"в облаке хук вышел с {итог.returncode}: {итог.stderr[:200]}")
        for пакет in ("playwright", "pillow"):
            if пакет not in итог.stdout:
                НАХОДКИ.append(f"хук ничего не сказал про {пакет}")
        if "браузер:" not in итог.stdout:
            НАХОДКИ.append("хук не назвал путь к браузеру")
        записано = файл.read_text(encoding="utf-8") if файл.exists() else ""
        if "BM_CHROMIUM=" not in записано:
            НАХОДКИ.append("путь к браузеру не попал в переменные сессии")
        elif not pathlib.Path(записано.split('"')[1]).exists():
            НАХОДКИ.append("в переменную записан путь, которого нет")

    # ── браузера нет: говорим словами, но сессию не валим ───────────────────
    with tempfile.TemporaryDirectory() as пусто:
        итог = запустить({"CLAUDE_CODE_REMOTE": "true", "BM_BROWSERS": пусто})
        if итог.returncode != 0:
            НАХОДКИ.append("без браузера хук уронил сессию — а должен только сказать")
        if "не найден" not in итог.stdout:
            НАХОДКИ.append("без браузера хук промолчал — пробы встали бы без объяснения")

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: молчит на своей машине, ставит в облаке, без браузера говорит и не валит.")


if __name__ == "__main__":
    главная()
