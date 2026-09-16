#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Справка лежит в index.html строкой base64 — достаём и кладём обратно.

Руками её не править: строка склеена из кусков по 120 знаков, и любая
перестановка кусков ломает вид файла. Здесь одно место, где знание о формате.
"""
import base64
import io
import re
import sys

ФАЙЛ = "index.html"
НАЧАЛО = "const _MANUAL_B64 = "
ДЛИНА = 120


def _границы(текст):
    и = текст.index(НАЧАЛО)
    к = текст.index("';\n", и) + 2
    return и + len(НАЧАЛО), к


def достать(путь=ФАЙЛ):
    текст = io.open(путь, encoding="utf-8").read()
    и, к = _границы(текст)
    куски = re.findall(r"'([^']*)'", текст[и:к])
    return base64.b64decode("".join(куски)).decode("utf-8")


def вложить(справка, путь=ФАЙЛ):
    текст = io.open(путь, encoding="utf-8").read()
    и, к = _границы(текст)
    б = base64.b64encode(справка.encode("utf-8")).decode("ascii")
    куски = [б[н:н + ДЛИНА] for н in range(0, len(б), ДЛИНА)]
    строки = ["'" + куски[0] + "' +"]
    строки += ["  '" + ч + "' +" for ч in куски[1:-1]]
    строки.append("  '" + куски[-1] + "';")
    io.open(путь, "w", encoding="utf-8").write(текст[:и] + "\n".join(строки) + текст[к:])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "вложить":
        вложить(io.open(sys.argv[2], encoding="utf-8").read())
        print("справка вложена")
    else:
        куда = sys.argv[2] if len(sys.argv) > 2 else "/tmp/manual.html"
        io.open(куда, "w", encoding="utf-8").write(достать())
        print("справка в", куда)
