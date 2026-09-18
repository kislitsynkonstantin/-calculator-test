# -*- coding: utf-8 -*-
"""Проба сверки черновика: она обязана говорить то же, что страж конца хода.

Смысл сверки в том, чтобы дурной ответ не попал в переписку вовсе, — значит
важнее всего, чтобы её приговор совпадал с приговором стража. Разойдись они,
и черновик выходил бы чистым, а ход всё равно задерживался: ровно та беда,
ради которой сверка написана, только наоборот.
"""
import json, os, pathlib, subprocess, tempfile

КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent
СВЕРКА = str(КОРЕНЬ / 'сверить-ответ.py')
СТРАЖ = str(КОРЕНЬ / 'response-guard.py')
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)


def сверить(текст):
    ф = tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8')
    ф.write(текст); ф.close()
    и = subprocess.run(['python3', СВЕРКА, ф.name], capture_output=True, text=True, timeout=60)
    os.unlink(ф.name)
    return и.returncode, (и.stdout or '').strip()


def стражем(текст):
    с = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False, encoding='utf-8')
    с.write(json.dumps({"type": "assistant", "message": {"role": "assistant",
            "content": [{"type": "text", "text": текст}]}}, ensure_ascii=False) + "\n")
    с.close()
    ввод = json.dumps({"transcript_path": с.name, "stop_hook_active": False})
    и = subprocess.run(['python3', СТРАЖ], input=ввод, capture_output=True, text=True, timeout=60)
    os.unlink(с.name)
    return и.returncode, (и.stderr or '').strip()


ВЕРНЫЙ = """## What changed [Что изменилось]

The client page now renders the print sheet, with the same classes and sizes.

[Клиентская страница теперь собирает печатный лист теми же классами и кеглями.]

| Step | Result |
|---|---|
| Syntax | passed |

Both rows of the table say the same: the syntax check passed with no findings.

[Обе строки таблицы говорят одно: проверка синтаксиса пройдена, замечаний нет.]

## Summary [Итого]

1. The sheet is rebuilt on the print markup.
2. Probes are green.

[1. Лист пересобран на печатной разметке.
2. Пробы зелёные.]

*Отличный макет, внедряй для клиента*"""

# Обе половины по-русски — тот самый дефект, который дошёл до переписки
# 18.09.2026, потому что сверки перед отправкой не было.
ДВАЖДЫ_ПО_РУССКИ = ВЕРНЫЙ.replace(
    "The client page now renders the print sheet, with the same classes and sizes.",
    "Клиентская страница теперь собирает печатный лист теми же классами и кеглями.")

код, вывод = сверить(ВЕРНЫЙ)
факт(код == 0 and 'Чисто' in вывод, f"на верном черновике сверка молчит: {вывод[:80]!r}")

код, вывод = сверить(ДВАЖДЫ_ПО_РУССКИ)
факт(код == 1 and 'не переведена, а повторена' in вывод,
     f"обе половины по-русски — сверка не пускает (код {код}): {вывод[:100]!r}")

код, вывод = сверить("Остановился.\n\n[Stopped.]")
факт(код == 0, f"короткая реплика сводки и эха не требует: {вывод[:60]!r}")

# Главное: приговор сверки и приговор стража совпадают.
for имя, текст in (("верный", ВЕРНЫЙ), ("дважды по-русски", ДВАЖДЫ_ПО_РУССКИ),
                   ("без эха", ВЕРНЫЙ.rsplit("*Отличный", 1)[0])):
    кс, вс = сверить(текст)
    кг, вг = стражем(текст)
    факт((кс != 0) == (кг != 0),
         f"«{имя}»: сверка и страж сходятся (сверка {кс}, страж {кг})")

# Путь передаётся напрямую: «сверить» пишет свой довод во временный файл,
# и отсутствующего пути через неё не проверить.
и = subprocess.run(['python3', СВЕРКА, '/этого/файла/нет.md'],
                   capture_output=True, text=True, timeout=60)
факт(и.returncode == 2 and 'Файла нет' in и.stderr,
     f"на отсутствующем файле сверка отвечает внятно, а не падает: {и.stderr.strip()[:60]!r}")

print("\n".join(отч)); print()
print("\n".join("ЗАМЕЧАНИЕ: " + з for з in зам) if зам else "Замечаний нет")
