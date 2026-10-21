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
    компьютере — стандартный размер 480 × 640 на любом мониторе, низ у низа
    экрана, верх не выше панели кнопок (Константин 21.10.2026: «Подбери
    стандартный размер окна примерно как тут, вне зависимости от экрана»), —
    на 1280, 1440, 1920 и 2560;
  • панель вкладки забирает высоту окна: низ панели — у низа окна, у чата
    поле ввода внутри окна, лента выше, чем в маленьком;
  • во всех пяти вкладках большого окна нет прокрутки вбок, вкладки стоят
    рядом слева направо: зазор не больше 30 px, первая — у левого края окна,
    за последней — свободное место, а не растяжка по ширине;
  • «Уменьшить» возвращает прежний размер, выбор помнится после перезагрузки;
  • на компьютере большое окно тянется за угол и края (Константин 19.10.2026:
    «тянуть вверх/вниз… запоминай… размер для всех пресетов»): угол меняет
    ширину и высоту, верхний край — высоту; окно не закрывается, не выходит
    за экран и под панель кнопок; размер записан один на все пресеты (в
    хранилище браузера, не в пресете) и читается оттуда заново; кнопка у крестика у большого окна
    любого размера одна — «Уменьшить» (цвета темы), и большое открывается
    снова своим размером; дотянули до стандартного места — окно встаёт на
    стандарт; на телефоне краёв для растяжки нет.

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
    стр.evaluate("() => { try { localStorage.removeItem('banya_pc_big'); localStorage.removeItem('banya_pc_big_size'); } catch (e) {} _пкБольшое = false; if (typeof применитьРазмерОкна === 'function') { _пкРазмер = null; применитьРазмерОкна(); } }")
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
        место(стр, н)
    # На компьютере стандарт — 640 в высоту (21.10.2026), маленькое окно там
    # высокое само; поэтому прирост мерится мягче, чем на телефоне.
    if б["выс"] < до["выс"] * (1.3 if ш < 900 else 1.15):
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
    for вк in ("p", "l", "c", "m"):
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
    if ш >= 900:
        try:
            растяжка(стр, н)
        except Exception as e:
            плохо(f"{н} растяжка оборвалась: {str(e).splitlines()[0][:160]}")
    elif стр.evaluate("() => [...document.querySelectorAll('#presetChipCard .pc-rs')].some(э => getComputedStyle(э).display !== 'none')"):
        плохо(f"{н} на телефоне видны края для растяжки окна")
    if стр.evaluate("() => { try { return localStorage.getItem('banya_pc_big'); } catch (e) { return null; } }") != "1":
        плохо(f"{н} выбор большого окна не записан")
    стр.evaluate("() => { try { localStorage.removeItem('banya_pc_big'); } catch (e) {} }")
    if [е for е in ошибки if "supabase.co" not in е]:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


КНОПКА = """() => { const б = document.querySelector('#presetChipCard .pc-big'); const к = document.getElementById('presetChipCard');
  const р = к.getBoundingClientRect(); const ак = getComputedStyle(к).getPropertyValue('--pc-acc').trim();
  const ц = document.createElement('i'); ц.style.color = ак; document.body.appendChild(ц); const цвет = getComputedStyle(ц).color; ц.remove();
  let хр = null; try { хр = localStorage.getItem('banya_pc_big_size'); } catch (e) {}
  return { большое: к.classList.contains('pc-big'), открыто: к.classList.contains('show'), подпись: б.getAttribute('aria-label'), горит: getComputedStyle(б).color === цвет,
    ш: Math.round(р.width), в: Math.round(р.height), верх: Math.round(р.top), лево: Math.round(р.left), W: innerWidth, хр,
    панель: (() => { const п = document.getElementById('headerBtns'); return п && п.classList.contains('sticky') ? Math.round(п.getBoundingClientRect().bottom) : 0; })() }; }"""


МЕСТО = """() => { const к = document.getElementById('presetChipCard'), р = к.getBoundingClientRect();
  const кол = document.querySelector('.page-wrap .two-col'), пр = кол.lastElementChild.getBoundingClientRect();
  const пан = document.getElementById('headerBtns').getBoundingClientRect();
  return { л: Math.round(р.left), п: Math.round(р.right), в: Math.round(р.top), н: Math.round(р.bottom), кол: Math.round(пр.left),
    пан: Math.round(пан.bottom), W: innerWidth, H: innerHeight, большое: к.classList.contains('pc-big') }; }"""


def место(стр, н):
    """Стандартное большое окно — 480 × 640 при любом мониторе: низ у низа
    экрана, верх не выше 8 px под панелью кнопок."""
    стр.evaluate("() => местоБольшогоОкна()"); стр.wait_for_timeout(200)
    м_ = стр.evaluate(МЕСТО)
    верх = max(12, м_["пан"]) + 8
    if not м_["большое"] or abs((м_["п"] - м_["л"]) - 480) > 1 or abs((м_["н"] - м_["в"]) - min(640, м_["н"] - верх)) > 2 \
            or м_["в"] < верх - 1 or м_["н"] > м_["H"] - 8 or м_["н"] < м_["H"] - 30 or м_["п"] > м_["W"]:
        плохо(f"{н} стандартное большое окно не 480 × 640 у низа экрана: {м_}")
    return м_


def тянуть(стр, сел, dx, dy):
    б = стр.locator("#presetChipCard " + сел).bounding_box()
    x, y = б["x"] + б["width"] / 2, б["y"] + б["height"] / 2
    стр.mouse.move(x, y); стр.mouse.down()
    for и in range(1, 9):
        стр.mouse.move(x + dx * и / 8, y + dy * и / 8)
    стр.mouse.up(); стр.wait_for_timeout(400)


def растяжка(стр, н):
    к = стр.evaluate(КНОПКА)
    if not к["большое"] or not к["горит"] or к["подпись"] != "Уменьшить окно":
        плохо(f"{н} стандартное большое окно: кнопка не цвета темы или подпись «{к['подпись']}»: {к}")
    # Стандартное окно стоит до панели кнопок: тянуть вверх некуда — сперва вниз.
    тянуть(стр, ".pc-rs-t", 0, 120)
    к = стр.evaluate(КНОПКА)
    ш0, в0 = к["ш"], к["в"]
    тянуть(стр, ".pc-rs-tl", -120, -60)
    к = стр.evaluate(КНОПКА)
    if not к["открыто"] or not к["большое"]:
        плохо(f"{н} растяжка закрыла или уменьшила окно: {к}")
    if abs(к["ш"] - (ш0 + 120)) > 3 or abs(к["в"] - (в0 + 60)) > 3:
        плохо(f"{н} угол: ждали {ш0 + 120}×{в0 + 60}, вышло {к['ш']}×{к['в']}")
    if not к["горит"] or к["подпись"] != "Уменьшить окно" or not к["хр"]:
        плохо(f"{н} своё большое: кнопка {к['подпись']!r}, горит {к['горит']}, записано {к['хр']}")
    тянуть(стр, ".pc-rs-t", 0, 200)
    к = стр.evaluate(КНОПКА)
    if abs(к["в"] - (в0 + 60 - 200)) > 3 or abs(к["ш"] - (ш0 + 120)) > 3:
        плохо(f"{н} верхний край: ждали высоту {в0 - 140} при ширине {ш0 + 120}, вышло {к['ш']}×{к['в']}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / "minicard-resized-1440.png"))
    # Тянут далеко за экран: окно упирается в края и в панель кнопок.
    тянуть(стр, ".pc-rs-tl", -3000, -3000)
    к = стр.evaluate(КНОПКА)
    if к["лево"] < 24 - 1 or к["верх"] < max(12, к["панель"] + 4) - 1:
        плохо(f"{н} окно вытянули за экран или под панель кнопок: лево {к['лево']}, верх {к['верх']}, панель {к['панель']}")
    тянуть(стр, ".pc-rs-tl", 0, 0)
    тянуть(стр, ".pc-rs-tl", 1800, 1800)
    к = стр.evaluate(КНОПКА)
    if к["ш"] < 379 or к["в"] < 359:
        плохо(f"{н} окно сжали меньше 380×360: {к['ш']}×{к['в']}")
    тянуть(стр, ".pc-rs-t", 0, -150)
    свой = стр.evaluate(КНОПКА)
    # Размер общий и переживает перезагрузку.
    # Как при новой загрузке страницы: состояние в памяти сброшено и читается
    # из хранилища браузера тем же разбором, что при загрузке.
    стр.evaluate("""() => { _пкРазмер = null; применитьРазмерОкна();
      try { const р = JSON.parse(localStorage.getItem('banya_pc_big_size') || 'null'); if (р && р.w > 0 && р.h > 0) _пкРазмер = { w: Math.round(р.w), h: Math.round(р.h) }; } catch (e) {}
      _пкБольшое = localStorage.getItem('banya_pc_big') === '1'; применитьРазмерОкна(); заполнитьКарточкуЗначка(); }""")
    стр.wait_for_timeout(500)
    к = стр.evaluate(КНОПКА)
    if not к["большое"] or abs(к["ш"] - свой["ш"]) > 2 or abs(к["в"] - свой["в"]) > 2:
        плохо(f"{н} после перезагрузки окно {к['ш']}×{к['в']}, ждали своё {свой['ш']}×{свой['в']}")
    # Кнопка у своего большого — «Уменьшить»; большое открывается снова своим.
    стр.locator("#presetChipCard .pc-big").click(); стр.wait_for_timeout(400)
    к = стр.evaluate(КНОПКА)
    if к["большое"]:
        плохо(f"{н} из своего большого кнопка не уменьшила окно: {к}")
    стр.locator("#presetChipCard .pc-big").click(); стр.wait_for_timeout(400)
    к = стр.evaluate(КНОПКА)
    if not к["большое"] or abs(к["ш"] - свой["ш"]) > 2 or abs(к["в"] - свой["в"]) > 2 or not к["горит"]:
        плохо(f"{н} большое открылось не своим размером {свой['ш']}×{свой['в']}: {к}")
    # Дотянули до стандартного места — окно встало на стандарт, своё стёрто.
    ст = 480
    тянуть(стр, ".pc-rs-tl", к["ш"] - ст + 5, 0)
    к = стр.evaluate(КНОПКА)
    тянуть(стр, ".pc-rs-t", 0, к["в"] - 640 + 5)
    к = стр.evaluate(КНОПКА)
    if к["хр"]:
        плохо(f"{н} дотянули до стандарта (ширина {ст}), а записан свой размер: {к}")
    место(стр, н)


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 390, 844)
                прогон(бр, порт, 1440, 900)
                for ш, в in ((1280, 800), (1920, 1080), (2560, 1440)):
                    стр, ошибки = ч.начать(бр, порт, ш, в, False)
                    стр.evaluate("() => { try { localStorage.removeItem('banya_pc_big_size'); } catch (e) {} _пкРазмер = null; применитьРазмерОкна(); _пкБольшое = true; }")
                    ч.открыть(стр); стр.wait_for_timeout(500)
                    место(стр, f"[{ш}, шапка]")
                    стр.evaluate("() => window.scrollTo(0, 900)"); стр.wait_for_timeout(500)
                    место(стр, f"[{ш}, прокручено]")
                    стр.mouse.move(5, 5)
                    стр.screenshot(path=str(СНИМКИ / f"minicard-std-{ш}.png"))
                    стр.close()
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
          "полоски итога во всю ширину, на компьютере — стандартные 480 × 640 у низа экрана на 1280–2560, кнопка у большого любого размера — «Уменьшить», дотянутое до стандарта встаёт на него; панель вкладки и чат забирают высоту, "
          "вбок ничего не едет, размер возвращается и помнится; на 390 и 1440.")


if __name__ == "__main__":
    главная()
