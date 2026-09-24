#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Журнал действий: подпись и значение в подробностях стоят рядом.

Константин 24.09.2026, снимком раскрытого «Набора опций» на компьютере:
«зачем такой интервал?». Колонка подписей была шириной 130 px на всех, и от
коротких «Добавлены» и «Итог» до значений оставалось около восьмидесяти
пикселей пустоты — значение висело, ни к чему не прислонившись.

Проба меряет расстояния, а не разметку:

  • на компьютере от конца самой длинной подписи события до значений —
    не больше 26 px (правило дома: больше — элемент висит в пустоте);
  • значения одного события начинаются с одной вертикали — колонка
    сохранилась, а не рассыпалась лесенкой;
  • длинная подпись («Цена в печати показана») не наезжает на значение;
  • на телефоне подпись стоит над значением, как и раньше.

    python3 check_log_detail_gap.py
"""
import functools
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []
ПУСТОТА = 26


def событие(и, вид, проект, строки, когда):
    return {"id": и, "user_id": "u-проба", "event_type": вид, "project_name": проект,
            "total_price": 6694122, "options_count": 14, "thickness": 150, "discount": 0,
            "cash_discount": False, "checked_options": {}, "created_at": когда,
            "details": {"obj": проект, "rows": строки}}


СОБЫТИЯ = [
    событие(1, "options_batch", "Каркасная баня с террасой 15.5 × 4.8",
            [{"k": "Добавлены", "a": "", "b": "\n".join(f"Позиция набора № {i:02d}" for i in range(1, 6))},
             {"k": "Итог", "a": "5 587 994 ₽", "b": "6 694 122 ₽"}], "2026-09-23T09:51:00Z"),
    событие(2, "marks_batch", "Фахверковая баня «Берлин» 9×5",
            [{"k": "Цена в печати показана", "a": "", "b": "Отливы на цоколь (металл)"},
             {"k": "Выделены", "a": "", "b": "Подсветка полков стандарт"}], "2026-09-23T09:40:00Z"),
]
ТАБЛИЦЫ = {
    "events": СОБЫТИЯ,
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
    "preset_links": [], "presets": [],
    "pricing_projects": [{"product": "frame", "sort": 1, "slug": "Проба 6×4", "name": "Проба 6×4",
                          "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
                          "floors": 1, "roof_type": "двускатная", "warm": True, "open_area": 10,
                          "closed_area": 20, "facade_area": 60, "paint_area": 60, "roof_area": 40}],
    "pricing_matrix": [], "pricing_options": [], "pricing_sections": [],
}


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    н = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not н:
        raise SystemExit("Chromium в /opt/pw-browsers не найден")
    return str(н[-1])


def сервер():
    к = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), к)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(т):
    НАХОДКИ.append(т)


МЕРА = """() => {
  // Ширина подписи — по тексту, а не по коробке: в колонке сетки коробка
  // растянута до самой длинной подписи, и пустота за короткой была бы не видна.
  const поТексту = э => { const р = document.createRange(); р.selectNodeContents(э); return р.getBoundingClientRect(); };
  return [...document.querySelectorAll('#alFeed .al-row.open .al-more')].map(м => {
    const ряды = [...м.querySelectorAll('.al-d')].map(д => {
      const к = поТексту(д.querySelector('.al-dk'));
      const зн = д.querySelector('.al-dv');
      // Начало значения — там, где начинается нарисованное: у списка это
      // маркер-точка, у обычного значения — первый знак текста.
      const точка = зн.querySelector('.al-dlist li');
      const в = точка
        ? { left: точка.getBoundingClientRect().left + parseFloat(getComputedStyle(точка, '::before').left || 0),
            top: точка.getBoundingClientRect().top }
        : поТексту(зн.querySelector('.al-da, .al-db') || зн);
      return { подпись: д.querySelector('.al-dk').textContent, кП: Math.round(к.right), кН: Math.round(к.bottom),
               вЛ: Math.round(в.left), вВ: Math.round(в.top) };
    });
    return ряды;
  });
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for тема in ("Модерн", "Бланк"):
                for ш in (390, 768, 1440):
                    где = f"{тема} · {ш}px"
                    стр = бр.new_page(viewport={"width": ш, "height": 950})
                    ошибки = []
                    стр.on("pageerror", lambda e, о=ошибки: о.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА)
                    стр.add_init_script("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
                                        + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");")
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                    стр.wait_for_timeout(2500)
                    стр.evaluate("""async ([бланк]) => {
                      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
                      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
                      _sbProfile = { role: 'admin', full_name: 'Проба' };
                      document.body.classList.toggle('ui-blank', бланк);
                      openActionLog(); _alПодробно = true; await loadActionLog(true);
                      await new Promise(r => setTimeout(r, 500)); alРисовать();
                      document.querySelectorAll('#alFeed .al-row').forEach(с => с.classList.add('open'));
                    }""", [тема == "Бланк"])
                    стр.wait_for_timeout(300)
                    события = стр.evaluate(МЕРА)
                    if len(события) < 2:
                        плохо(f"[{где}] раскрытых событий {len(события)} — мерить нечего")
                    for ряды in события:
                        if ш > 640:
                            край = max(р["кП"] for р in ряды)
                            левый = min(р["вЛ"] for р in ряды)
                            зазор = левый - край
                            if зазор > ПУСТОТА:
                                плохо(f"[{где}] от подписи до значения {зазор} px — значение висит в пустоте")
                            if зазор < 6:
                                плохо(f"[{где}] подпись и значение сошлись вплотную ({зазор} px)")
                            # Маркер списка стоит на 2 px правее края клетки — это
                            # отступ самой точки, а не лесенка.
                            if max(р["вЛ"] for р in ряды) - левый > 2:
                                плохо(f"[{где}] значения одного события начинаются с разных вертикалей: "
                                      f"{[р['вЛ'] for р in ряды]}")
                            print(f"  {где}: «{max(ряды, key=lambda р: р['кП'])['подпись']}» → значение {зазор} px")
                        else:
                            for р in ряды:
                                if р["вВ"] < р["кН"] - 1:
                                    плохо(f"[{где}] на телефоне значение «{р['подпись']}» встало рядом, а не под подписью")
                    if ошибки:
                        плохо(f"[{где}] ошибки страницы: " + "; ".join(ошибки)[:200])
                    стр.close()
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: на компьютере значение стоит в 6–26 px от самой длинной подписи события, "
          "значения держат одну колонку, а на телефоне подпись по-прежнему над значением.")


if __name__ == "__main__":
    главная()
