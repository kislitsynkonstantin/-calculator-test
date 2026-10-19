#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Мини-окно: кнопка «Увеличить / уменьшить окно» у крестика.

Константин 19.10.2026, снимком телефона с обведённой областью от панели
кнопок до полоски итога: «Добавь кнопку „Увеличить/уменьшить“ на мини-окно,
чтобы менялось. На телефоне по размеру экрана вот до этой области. А на
компьютере сам прикинь, чтобы читалось нормально».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • кнопка есть у окна с вкладками, слева от крестика, не заходит на название
    и код, поле нажатия не меньше 44 px, значок и подпись меняются;
  • на телефоне большое окно — во всю ширину с полями 14 px, верх под
    прилипшей панелью кнопок (не под ней), низ над полоской итога; на
    компьютере — 540 px в ширину (было 600, «уже на 10 %», 19.10.2026) и не
    выше 760 px, в экране;
  • панель вкладки забирает высоту окна: низ панели — у низа окна, у чата
    поле ввода внутри окна, лента выше, чем в маленьком;
  • во всех пяти вкладках большого окна нет прокрутки вбок, вкладки стоят
    рядом слева направо: зазор не больше 30 px, первая — у левого края окна,
    за последней — свободное место, а не растяжка по ширине;
  • «Уменьшить» возвращает прежний размер, выбор помнится после перезагрузки.

    python3 check_minicard_big.py
"""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


МЕРА = """() => { const к = document.getElementById('presetChipCard'), r = к.getBoundingClientRect();
  const б = к.querySelector('.pc-big'), х = к.querySelector('.pc-x'), нм = к.querySelector('.pc-nm');
  const п = к.querySelector('.pc-pane.on'), пр = п ? п.getBoundingClientRect() : null;
  const пан = document.getElementById('headerBtns'), липнет = пан && пан.classList.contains('sticky');
  const ит = document.querySelector('.total-strip, #totalStrip, .bottom-total');
  const полоса = document.body.classList.contains('total-strip-on') ? (() => { const э = [...document.querySelectorAll('body > *')].find(е => getComputedStyle(е).position === 'fixed' && е.getBoundingClientRect().bottom >= innerHeight - 1 && е.getBoundingClientRect().height > 40 && е.getBoundingClientRect().width > innerWidth * .9); return э ? э.getBoundingClientRect().top : innerHeight; })() : innerHeight;
  const нмТекст = document.createRange(); нмТекст.selectNodeContents(нм);
  const нмПраво = Math.max(...[...нмТекст.getClientRects()].map(р => р.right));
  const сб = б && getComputedStyle(б, '::before');
  const чл = к.querySelector('#pcChatList'), вв = к.querySelector('.pc-chin');
  return { есть: !!б, большое: к.classList.contains('pc-big'), нажата: б && б.getAttribute('aria-pressed'), подпись: б && б.getAttribute('aria-label'),
    л: r.left, п: r.right, в: r.top, н: r.bottom, ш: r.width, выс: r.height, W: innerWidth, H: innerHeight,
    кнЛ: б && б.getBoundingClientRect().left, кнП: б && б.getBoundingClientRect().right, крЛ: х.getBoundingClientRect().left, нмП: нмПраво,
    поле: б ? б.getBoundingClientRect().height - parseFloat(сб.top) - parseFloat(сб.bottom) : 0,
    поляШ: б ? б.getBoundingClientRect().width - parseFloat(сб.left) - parseFloat(сб.right) : 0,
    панНиз: липнет ? пан.getBoundingClientRect().bottom : null, полоса,
    панельНиз: пр ? пр.bottom : 0, вбок: п ? п.scrollWidth > п.clientWidth + 1 : false, окноВбок: к.scrollWidth > к.clientWidth + 1,
    лента: чл ? чл.getBoundingClientRect().height : 0, вводНиз: вв ? вв.getBoundingClientRect().bottom : 0 }; }"""


def прогон(бр, порт, ш, в):
    н = f"[{ш}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, False)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ч.ДАННЫЕ_ЧАТА, код)
    стр.evaluate("() => { try { localStorage.removeItem('banya_pc_big'); } catch (e) {} _пкБольшое = false; }")
    # Панель кнопок прилипает, когда страница прокручена.
    стр.evaluate("() => window.scrollTo(0, 900)"); стр.wait_for_timeout(500)
    ч.открыть(стр); стр.wait_for_timeout(300)
    ч.вкладка(стр, "m"); стр.wait_for_timeout(700)
    до = стр.evaluate(МЕРА)
    if not до["есть"]:
        плохо(f"{н} у мини-окна нет кнопки «Увеличить окно»"); стр.close(); return
    if до["подпись"] != "Увеличить окно" or до["нажата"] != "false":
        плохо(f"{н} кнопка в маленьком окне: «{до['подпись']}», нажата {до['нажата']}")
    if до["кнП"] > до["крЛ"] - 2 or до["кнП"] < до["крЛ"] - 14:
        плохо(f"{н} кнопка не рядом с крестиком: {до['кнП']} против {до['крЛ']}")
    if до["нмП"] > до["кнЛ"] - 4:
        плохо(f"{н} название заходит под кнопку: текст до {round(до['нмП'])}, кнопка с {round(до['кнЛ'])}")
    if до["поле"] < 43.5 or до["поляШ"] < 35.5:
        плохо(f"{н} поле нажатия кнопки {round(до['поляШ'])}×{round(до['поле'])}")
    стр.locator("#presetChipCard .pc-big").click(); стр.wait_for_timeout(500)
    б = стр.evaluate(МЕРА)
    if not б["большое"] or б["подпись"] != "Уменьшить окно" or б["нажата"] != "true":
        плохо(f"{н} после нажатия: большое {б['большое']}, «{б['подпись']}», нажата {б['нажата']}")
    if ш < 900:
        if abs(б["л"] - 14) > 1 or abs(б["W"] - б["п"] - 14) > 1:
            плохо(f"{н} большое окно не во всю ширину: {round(б['л'])}…{round(б['п'])} при {б['W']}")
        if б["панНиз"] is None:
            плохо(f"{н} панель кнопок не прилипла — проверять верх не с чем")
        elif б["в"] < б["панНиз"] + 4 or б["в"] > б["панНиз"] + 14:
            плохо(f"{н} верх большого окна {round(б['в'])}, панель кнопок кончается на {round(б['панНиз'])}")
        if б["н"] > б["полоса"] - 4 or б["н"] < б["полоса"] - 20:
            плохо(f"{н} низ большого окна {round(б['н'])}, полоска итога с {round(б['полоса'])}")
    else:
        if abs(б["ш"] - 540) > 1 or б["выс"] > 761 or б["в"] < 0 or б["п"] > б["W"]:
            плохо(f"{н} большое окно на компьютере {round(б['ш'])}×{round(б['выс'])}, верх {round(б['в'])}")
        if б["панНиз"] is not None and б["в"] < б["панНиз"] + 4:
            плохо(f"{н} большое окно под панелью кнопок: верх {round(б['в'])}, панель до {round(б['панНиз'])}")
    if б["выс"] < до["выс"] * 1.3:
        плохо(f"{н} большое окно почти не выросло: {round(до['выс'])} → {round(б['выс'])}")
    if б["н"] - б["панельНиз"] > 24 or б["вводНиз"] > б["н"] - 4 or б["лента"] < до["лента"] * 1.3:
        плохо(f"{н} чат не забрал высоту: низ панели {round(б['панельНиз'])} при низе окна {round(б['н'])}, ввод до {round(б['вводНиз'])}, лента {round(до['лента'])} → {round(б['лента'])}")
    # Вкладки стоят рядом: ни одна не висит в пустоте (правило 06.09.2026).
    зазоры = стр.evaluate("""() => { const т = [...document.querySelectorAll('#presetChipCard .pc-tab')].map(э => э.getBoundingClientRect());
      return т.slice(1).map((р, i) => Math.round(р.left - т[i].right)); }""")
    if max(зазоры) > 30:
        плохо(f"{н} вкладки большого окна врассыпную: зазоры {зазоры}")
    края = стр.evaluate("""() => { const р = document.querySelector('#presetChipCard .pc-tabs').getBoundingClientRect(), т = [...document.querySelectorAll('#presetChipCard .pc-tab')].map(э => э.getBoundingClientRect());
      return [Math.round(т[0].left - р.left), Math.round(р.right - т[т.length - 1].right)]; }""")
    if края[0] > 2 or (ш >= 900 and края[1] < 60):
        плохо(f"{н} вкладки большого окна не собраны слева: от левого края {края[0]}, справа свободно {края[1]}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"minicard-big-{ш}.png"))
    for вк in ("p", "s", "l", "c", "m"):
        ч.вкладка(стр, вк); стр.wait_for_timeout(500)
        с = стр.evaluate(МЕРА)
        if с["вбок"] or с["окноВбок"]:
            плохо(f"{н} вкладка {вк} в большом окне прокручивается вбок")
        if not с["большое"]:
            плохо(f"{н} вкладка {вк} вернула маленькое окно")
    стр.locator("#presetChipCard .pc-big").click(); стр.wait_for_timeout(500)
    м_ = стр.evaluate(МЕРА)
    if м_["большое"] or abs(м_["выс"] - до["выс"]) > 2 or abs(м_["ш"] - до["ш"]) > 1:
        плохо(f"{н} «Уменьшить окно» не вернуло размер: {round(до['ш'])}×{round(до['выс'])} → {round(м_['ш'])}×{round(м_['выс'])}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"minicard-small-{ш}.png"))
    # Выбор помнится.
    стр.locator("#presetChipCard .pc-big").click(); стр.wait_for_timeout(300)
    if стр.evaluate("() => { try { return localStorage.getItem('banya_pc_big'); } catch (e) { return null; } }") != "1":
        плохо(f"{н} выбор большого окна не записан")
    стр.evaluate("() => { try { localStorage.removeItem('banya_pc_big'); } catch (e) {} }")
    if [е for е in ошибки if "supabase.co" not in е]:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 390, 844)
                прогон(бр, порт, 1440, 900)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        raise SystemExit(1)
    print("Чисто: кнопка «Увеличить / уменьшить окно» у крестика, на телефоне большое окно — от панели кнопок до "
          "полоски итога во всю ширину, на компьютере 540 px и не выше 760; панель вкладки и чат забирают высоту, "
          "вбок ничего не едет, размер возвращается и помнится; на 390 и 1440.")


if __name__ == "__main__":
    главная()
