#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Журнал действий: в место итога идёт только сумма, а не названия.

Константин 09.10.2026, двумя снимками журнала с телефона (тест, «Магдебург»,
события «Своя опция изменена»): «Это поправь в журнале действий». Справа в
строке события стоит итог — зелёным, в одну строку. Туда же попадала первая
пара «было → стало» любого события, и у переименования своей опции это были
два длинных названия: зелёная строка без переноса уходила за край ленты, а на
телефоне вставала над событием крупнее его самого.

Проба на 390 и 1440 рисует журнал из заглушки и держит:

  • у переименования своей опции место итога пустое, а сама опция названа в
    строке события — новым именем, с переносом, в пределах ленты;
  • у правки примечания место итога тоже пустое;
  • у правки цены своей опции и у события с итогом «было → стало» сумма на
    месте итога остаётся;
  • ни один элемент строк не выходит за правый край ленты.

    python3 check_log_sum_slot.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_custom_opt_log as к
from playwright.sync_api import sync_playwright

НАХОДКИ = []
СТАРОЕ = "Межкомнатные двери - двери МДФ размер по проекту (доборы, наличники, ручки в комплекте) за 1 дверь"
НОВОЕ = "Межкомнатные двери - двери МДФ размер по проекту (доборы, наличники, ручки в комплекте) за 2 двери"
ПРОЕКТ = 'Баня из клееного бруса "Магдебург" 6х6'


def событие(ид, вид, строки, итог=None):
    return {"id": ид, "created_at": "2026-10-09T12:16:00.000Z", "user_id": "u-проба", "event_type": вид,
            "project_name": ПРОЕКТ, "total_price": итог,
            "details": {"obj": ПРОЕКТ, "rows": [{"k": k, "a": a, "b": b} for k, a, b in строки], "sum": "",
                        "preset": "Проба пресет", "presetCode": "276043"}}


СОБЫТИЯ = [
    событие(1, "custom_opt_edited", [("Раздел", "", "Окна и двери"), ("Название", СТАРОЕ, НОВОЕ)]),
    событие(2, "custom_opt_edited", [("Раздел", "", "Окна и двери"), ("Опция", "", "Проба опция"),
                                     ("Цена", "100 000 ₽", "120 000 ₽")]),
    событие(3, "note_edited", [("Раздел", "", "Фундамент и цоколь"),
                               ("Текст", "Отделка цоколя не входит в расчёт",
                                "Отделка цоколя и отливы не входят в расчёт, согласуются отдельно")]),
    событие(4, "options_batch", [("Добавлены", "", "Сборка лесов"), ("Итог", "10 000 000 ₽", "10 096 721 ₽")],
            итог=10096721),
]

МЕРА = """() => {
  const лента = document.getElementById('alFeed').getBoundingClientRect();
  const строка = ид => document.querySelector('#alFeed .al-row[data-ev="' + ид + '"]');
  const итог = ид => { const с = строка(ид); return с ? (с.querySelector('.al-sum') || {}).textContent.replace(/\\u00a0/g, ' ').trim() : null; };
  const текст = ид => { const с = строка(ид); return с ? (с.querySelector('.al-text') || {}).textContent.replace(/\\u00a0/g, ' ') : null; };
  const за = [];
  document.querySelectorAll('#alFeed .al-row *').forEach(э => { const r = э.getBoundingClientRect();
    if (r.width && r.right > лента.right + 1) за.push((э.className || э.tagName) + ' ' + Math.round(r.right - лента.right) + ' px'); });
  return { итог1: итог(1), текст1: текст(1), итог2: итог(2), итог3: итог(3), итог4: итог(4), за: за.slice(0, 4) };
}"""


def главная():
    с, порт = к.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=к.хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                н = f"[{ш}]"
                стр = бр.new_page(viewport={"width": ш, "height": 900})
                ош = []
                стр.on("pageerror", lambda e: ош.append(str(e)))
                стр.add_init_script(к.ЗАГЛУШКА)
                стр.add_init_script(к.ТАБЛИЦЫ_JS)
                стр.add_init_script("window.__ТАБЛИЦЫ.events = " + json.dumps(СОБЫТИЯ, ensure_ascii=False) + ";")
                стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                стр.wait_for_timeout(2500)
                стр.evaluate("""async () => {
                  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
                  const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
                  window._sbProfile = { role: 'admin', full_name: 'Проба' };
                  const сейчас = new Date().toISOString(); (window.__ТАБЛИЦЫ.events || []).forEach(с => { с.created_at = сейчас; });
                  openActionLog(); _alПодробно = true; await loadActionLog(true); await new Promise(r => setTimeout(r, 500));
                  alРисовать(); }""")
                м = стр.evaluate(МЕРА)
                if м["итог1"] is None:
                    НАХОДКИ.append(f"{н} события в журнале нет — проба смотрит мимо")
                else:
                    if м["итог1"]:
                        НАХОДКИ.append(f"{н} переименование своей опции: на месте итога «{м['итог1'][:60]}…», ждали пусто")
                    if НОВОЕ not in (м["текст1"] or ""):
                        НАХОДКИ.append(f"{н} переименование своей опции: в строке события нет нового названия — «{(м['текст1'] or '')[:80]}»")
                    if м["итог3"]:
                        НАХОДКИ.append(f"{н} правка примечания: на месте итога «{м['итог3'][:60]}», ждали пусто")
                    if м["итог2"] != "100 000 ₽ → 120 000 ₽":
                        НАХОДКИ.append(f"{н} правка цены своей опции: на месте итога «{м['итог2']}», ждали «100 000 ₽ → 120 000 ₽»")
                    if м["итог4"] != "10 000 000 ₽ → 10 096 721 ₽":
                        НАХОДКИ.append(f"{н} событие с итогом: на месте итога «{м['итог4']}», ждали «10 000 000 ₽ → 10 096 721 ₽»")
                    if м["за"]:
                        НАХОДКИ.append(f"{н} за правым краем ленты: {м['за']}")
                стр.screenshot(path=str(pathlib.Path(__file__).parent / f"log-sum-slot-{ш}.png"))
                for о in [о for о in ош if "supabase.co" not in о][:3]:
                    НАХОДКИ.append(f"{н} ошибка страницы: {о[:160]}")
                print(f"  {н} итоги: «{м['итог1']}» / «{м['итог2']}» / «{м['итог3']}» / «{м['итог4']}»")
                стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: в месте итога только суммы — у правки цены и у события с итогом; переименование своей опции "
          "и правка примечания его не занимают, опция названа в строке события, за край ленты ничего не выходит — на 390 и 1440.")


if __name__ == "__main__":
    главная()
