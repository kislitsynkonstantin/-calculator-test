#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Справка и руководство: сборка документа из частей.

Раньше справка лежала прямо в `index.html` строкой base64 — 475 КБ текста,
которые отдавались всякому, кто знал адрес страницы: вход для этого не
требовался, а репозиторий вдобавок открыт. Теперь документ лежит в базе
(таблица `public.app_docs`) и приходит только вошедшему, а внутренняя глава
«Лог развития» — только администратору.

Источник текста живёт в **закрытом** репозитории рабочей области,
`docs/справка/`, а не здесь: этот репозиторий публичный, и положить справку
рядом с пробой значило бы вернуть ровно ту дыру, ради которой всё и
переносилось. Путь можно задать переменной среды `BM_MANUAL_SRC`.

Правило сборки одно и то же в браузере и здесь: документ — это часть `shell`,
в которой метка `<!--ГЛАВЫ-->` заменена на главы, склеенные через перевод
строки в порядке `ord`. У руководства глав нет — одна оболочка.

    python3 справка.py                     # собрать справку в /tmp/manual.html
    python3 справка.py собрать guide файл  # собрать руководство
    python3 справка.py сверить             # что разошлось с описью базы
    python3 справка.py sql ch-updates      # готовый запрос на заливку части
"""
import hashlib
import io
import json
import os
import pathlib
import sys

ПАПКА = pathlib.Path(os.environ.get(
    "BM_MANUAL_SRC", "/home/user/vscode-workspace/docs/справка"))
МЕТКА = "<!--ГЛАВЫ-->"


def _опись():
    if not (ПАПКА / "опись.json").exists():
        raise SystemExit(
            f"Источника справки нет: {ПАПКА}\n"
            "Он лежит в закрытом репозитории рабочей области (docs/справка/).\n"
            "Подключи его или укажи путь переменной BM_MANUAL_SRC.")
    return json.load(io.open(ПАПКА / "опись.json", encoding="utf-8"))


def части(документ="manual"):
    """Части документа в порядке `ord`, с текстом из файлов."""
    вышло = []
    for ч in _опись():
        if ч["doc"] != документ:
            continue
        путь = ПАПКА / f"{ч['doc']}--{ч['part']}.html"
        вышло.append(dict(ч, html=io.open(путь, encoding="utf-8").read().strip("\n")))
    return sorted(вышло, key=lambda ч: ч["ord"])


def достать(документ="manual"):
    """Собранный документ — ровно то же, что получает браузер из базы."""
    все = части(документ)
    оболочка = next((ч for ч in все if ч["part"] == "shell"), None)
    if оболочка is None:
        raise SystemExit(f"у документа «{документ}» нет оболочки")
    главы = "\n".join(ч["html"] for ч in все if ч["part"] != "shell")
    # str.replace подставляет строку как есть; в браузере на этом же месте
    # стоит замена функцией — там `String.replace` прочитал бы знак «$» в
    # тексте справки как ссылку на совпадение.
    return оболочка["html"].replace(МЕТКА, главы)


def сверить():
    """Что в папке разошлось с тем, что записано в базе.

    Опись — снимок залитого: длина и md5 каждой части. Правка текста даёт
    расхождение, и оно же есть список того, что надо переложить в базу.
    """
    разошлись = []
    for ч in _опись():
        путь = ПАПКА / f"{ч['doc']}--{ч['part']}.html"
        текст = io.open(путь, encoding="utf-8").read().strip("\n")
        if hashlib.md5(текст.encode("utf-8")).hexdigest() != ч["md5"]:
            разошлись.append((ч["doc"], ч["part"], ч["len"], len(текст)))
    return разошлись


def запрос(часть, документ="manual"):
    """Готовый SQL на заливку части. Долларовые кавычки — потому что внутри
    текста есть и апострофы, и обратные косые."""
    ч = next((ч for ч in части(документ) if ч["part"] == часть), None)
    if ч is None:
        raise SystemExit(f"части «{часть}» у документа «{документ}» нет")
    return (
        "insert into public.app_docs (doc, part, ord, staff_only, html)\n"
        f"values ('{документ}', '{часть}', {ч['ord']}, "
        f"{'true' if ч['staff_only'] else 'false'}, $док${ч['html']}$док$)\n"
        "on conflict (doc, part) do update set html = excluded.html,\n"
        "  ord = excluded.ord, staff_only = excluded.staff_only, updated_at = now();\n"
        "select part, length(html), md5(html) from public.app_docs\n"
        f" where doc = '{документ}' and part = '{часть}';")


if __name__ == "__main__":
    дело = sys.argv[1] if len(sys.argv) > 1 else "собрать"
    if дело == "сверить":
        р = сверить()
        if not р:
            print("папка и база сходятся")
        for документ, часть, было, стало in р:
            print(f"{документ}/{часть}: в базе {было} знаков, в папке {стало} — переложить")
    elif дело == "sql":
        print(запрос(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "manual"))
    else:
        документ = sys.argv[2] if len(sys.argv) > 2 else "manual"
        куда = sys.argv[3] if len(sys.argv) > 3 else "/tmp/manual.html"
        io.open(куда, "w", encoding="utf-8").write(достать(документ))
        print(документ, "в", куда)
