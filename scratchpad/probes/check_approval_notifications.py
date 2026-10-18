#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Согласование в колокольчике — каждым шагом; всплывающие уведомления.

Константин 18.10.2026: «В уведомлениях показывай каждую запись согласования
как уведомление, с красной точкой. И менеджеру показывай всплывающее
уведомление, когда расчет согласован (который он отправил согласовать), когда
вернули с правками. И когда долго не заходит в чат, там написали комментарии
по расчету/правки. Долго, давай будет 1 час».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • колокольчик берёт шаги из preset_approval_log: каждый шаг — отдельное
    уведомление, новыми первыми, с текстом шага и именем того, кто его
    сделал; свой шаг тоже новый и зажигает красную точку; менеджеру — только
    шаги по расчётам, которые отправил он; журнал пуст — каждый шаг
    нынешнего круга из строки расчёта: отправка, место, итог или возврат;
  • новое уведомление — значок на бледном круге, черты слева нет ни у
    одной строки, круг не касается черты под шапкой и края окна;
  • всплывашка «Расчёт согласован» и «Расчёт вернули с правками» — тому,
    кто отправил, и только за решение другого человека; решение до первого
    захода не всплывает; одно решение второй раз не всплывает; «Открыть
    расчёт» ведёт в пресет на «Проверку», крест закрывает;
  • всплывашка «Непрочитанное в чате пресета» — по preset_chat_unread, с
    числом сообщений; тот же чат второй раз не всплывает, новое сообщение в
    нём — всплывает снова; «Открыть чат» ведёт к первому непрочитанному;
  • не больше трёх карточек разом;
  • вёрстка на 390 и 1440, днём, ночью и в «Модерне»: карточки в экране и
    ниже панели кнопок, поля нажатия кнопки и креста не меньше 44 px,
    кнопка не налезает на текст.

    python3 check_approval_notifications.py
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


ЖУРНАЛ = """(код) => { const д = Date.now(), мин = 60e3, т = window.__ТАБЛИЦЫ;
  const ш = (ид, вид, место, кто, имя, назад, отправил) => ({ id: ид, code: код, event: вид, slot: место, by_id: кто, by_name: имя,
    sent_by: отправил || 'u-проба', preset_name: 'Баня «Проба»', project_name: 'Проба', at: new Date(д - назад * мин).toISOString() });
  т.preset_approval_log = [ш(1, 'sent', null, 'u-проба', 'Проба', 50), ш(2, 'approved_part', 'price', 'u-ред', 'Ольга Проверкина', 40),
    ш(3, 'returned', 'check', 'u-спец', 'Анна Специалист', 30), ш(4, 'approved', 'all', 'u-проба', 'Проба', 10),
    ш(5, 'sent', null, 'u-другой', 'Пётр Автор', 5, 'u-другой')];
}"""

КОЛОКОЛЬЧИК = """async () => { await собратьУведомления(); обновитьТочкуКолокольчика();
  return { шаги: _уведомления.filter(у => у.согласование).map(у => ({ т: у.текст.replace(/<[^>]+>/g, ''), кто: у.автор, своё: у.своё })),
    точка: getComputedStyle(document.getElementById('bellDot')).display !== 'none' }; }"""

КАРТОЧКИ = """() => [...document.querySelectorAll('#ntPop .nt-pop-i')].map(к => ({ к: к.dataset.k, з: к.querySelector('.nt-pop-h').textContent,
  т: к.querySelector('.nt-pop-t').textContent, м: (к.querySelector('.nt-pop-m') || {}).textContent || '', кн: к.querySelector('.nt-pop-go').textContent }))"""

ВЁРСТКА = """() => { const н = [], W = document.documentElement.clientWidth, H = innerHeight;
  const пан = document.querySelector('#headerBtns.sticky'), низПанели = пан ? пан.getBoundingClientRect().bottom : 0;
  document.querySelectorAll('#ntPop .nt-pop-i').forEach(к => { const r = к.getBoundingClientRect();
    if (r.left < 0 || r.right > W + .5 || r.bottom > H) н.push('карточка за экраном');
    if (r.top < низПанели - .5) н.push('карточка под панелью кнопок');
    к.querySelectorAll('button').forEach(б => { const бр = б.getBoundingClientRect(), с = getComputedStyle(б, '::before');
      const h = бр.height - (parseFloat(с.top) || 0) - (parseFloat(с.bottom) || 0);
      if (h < 43.5) н.push('поле нажатия «' + (б.textContent || б.getAttribute('aria-label')) + '» по высоте ' + Math.round(h)); });
    const т = к.querySelector('.nt-pop-b'), x = к.querySelector('.nt-pop-x');
    if (т.getBoundingClientRect().right > x.getBoundingClientRect().left + .5) н.push('текст налезает на крест');
    if (к.scrollWidth > к.clientWidth + 1) н.push('карточка шире себя'); });
  if (document.documentElement.scrollWidth > W + 1) н.push('страница шире экрана');
  return н; }"""


def прогон(бр, порт, ш, в, ночь, модерн):
    н = f"[{ш}{' ночь' if ночь else ''}{' модерн' if модерн else ''}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    if модерн:
        стр.evaluate("() => applyUiStyle('modern', false)")
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate("() => { window._sbProfile.role = 'admin'; appSettings.notifReadAt = new Date(Date.now() - 3600e3).toISOString(); }")
    стр.evaluate(ЖУРНАЛ, код)
    # ── колокольчик: каждый шаг ──
    к = стр.evaluate(КОЛОКОЛЬЧИК)
    ждали = ["Отправлен на согласование: Баня «Проба»|", "Расчёт согласован за всех: Баня «Проба»|",
             "Расчёт вернули с правками: Баня «Проба»|Анна Специалист", "Цена согласована: Баня «Проба»|Ольга Проверкина",
             "Отправлен на согласование: Баня «Проба»|"]
    вышло = [х["т"] + "|" + х["кто"] for х in к["шаги"]]
    if вышло != ["Ждёт согласования: Баня «Проба»|Пётр Автор"] + ждали[1:4] + [ждали[0]]:
        плохо(f"{н} шаги в колокольчике администратора: {вышло}")
    if any(х["своё"] for х in к["шаги"]) or not к["точка"]:
        плохо(f"{н} свой шаг не зажигает точку или помечен своим: {к}")
    стр.evaluate("() => { window._sbProfile.role = 'manager'; }")
    к = стр.evaluate(КОЛОКОЛЬЧИК)
    if any("Пётр Автор" in х["кто"] or "Ждёт" in х["т"] for х in к["шаги"]) or len(к["шаги"]) != 4:
        плохо(f"{н} менеджеру — чужой расчёт или не все свои шаги: {[х['т'] for х in к['шаги']]}")
    # Журнал пуст — каждый шаг нынешнего круга из строки расчёта, а не одна
    # строка на расчёт (Константин 18.10.2026: «по одному пресету если
    # проходит новое согласование, то в уведомлениях старое затирает»).
    стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ, д = Date.now(), в = м => new Date(д - м * 60e3).toISOString();
      т.preset_approval_log = [];
      т.preset_approvals = [{ code: код, state: 'approved', preset_name: 'Баня «Проба»', sent_by: _sbUser.id, sent_name: 'Проба', sent_at: в(50), sent_print: 'о1',
        price_by: 'u-ред', price_name: 'Ольга Проверкина', price_at: в(40), price_print: 'о1',
        check_by: 'u-спец', check_name: 'Анна Специалист', check_at: в(20), check_print: 'о1',
        decided_by: 'u-спец', decided_name: 'Анна Специалист', decided_at: в(20), approved_at: в(20), for_all: false },
        { code: '888888', state: 'returned', preset_name: 'Баня «Возврат»', sent_by: _sbUser.id, sent_name: 'Проба', sent_at: в(35), sent_print: 'о2',
        decided_by: 'u-ред', decided_name: 'Ольга Проверкина', decided_at: в(15), for_all: false }]; }""", код)
    к = стр.evaluate(КОЛОКОЛЬЧИК)
    вышло = [х["т"] + "|" + х["кто"] for х in к["шаги"]]
    if вышло != ["Расчёт вернули с правками: Баня «Возврат»|Ольга Проверкина", "Расчёт согласован: Баня «Проба»|Анна Специалист",
                 "Отправлен на согласование: Баня «Возврат»|", "Цена согласована: Баня «Проба»|Ольга Проверкина",
                 "Отправлен на согласование: Баня «Проба»|"]:
        плохо(f"{н} без журнала шаги круга затёрты: {вышло}")
    стр.evaluate("() => { window.__ТАБЛИЦЫ.preset_approvals = []; window._sbProfile.role = 'admin'; }")
    # Новое уведомление — без черты слева: значок на бледном круге, круг не
    # касается черты под шапкой и края окна.
    стр.evaluate(ЖУРНАЛ, код)
    стр.evaluate("() => { appSettings.notifReadAt = new Date(Date.now() - 3600e3).toISOString(); }")
    стр.locator("#bellBtn").click(); стр.wait_for_timeout(700)
    о = стр.evaluate("""() => { const м = document.getElementById('bellMenu'), н = [];
      if (!м || getComputedStyle(м).display === 'none') return ['окно уведомлений не открылось'];
      const нов = м.querySelectorAll('.nt-i.new');
      if (!нов.length) н.push('нет новых строк');
      const мр = м.getBoundingClientRect(), ш = м.querySelector('.nt-h').getBoundingClientRect();
      м.querySelectorAll('.nt-i').forEach(и => { const с = getComputedStyle(и);
        if (parseFloat(с.borderLeftWidth) >= 1.5) н.push('черта слева у строки: ' + с.borderLeftWidth);
        if (/inset/.test(с.boxShadow)) н.push('черта тенью у строки'); });
      нов.forEach(и => { const з = и.querySelector('svg:not(.nt-go)'), зр = з.getBoundingClientRect();
        if (getComputedStyle(з).backgroundColor === 'rgba(0, 0, 0, 0)') н.push('у нового значка нет круга');
        if (зр.left - мр.left < 4) н.push('круг у края окна: ' + Math.round(зр.left - мр.left));
        if (зр.top - ш.bottom < 4 && зр.top > ш.bottom - 1) н.push('круг касается черты под шапкой: ' + Math.round(зр.top - ш.bottom));
        if (зр.bottom > и.getBoundingClientRect().bottom) н.push('круг вылез из строки');
        const с = и.querySelector('.nt-go');
        if (с && getComputedStyle(с).backgroundColor !== 'rgba(0, 0, 0, 0)') н.push('круг и у стрелки справа'); });
      return н; }""")
    for т in о:
        плохо(f"{н} колокольчик: {т}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"bell-{ш}{'-n' if ночь else ''}{'-m' if модерн else ''}.png"))
    стр.evaluate("() => закрытьОкноУведомлений()"); стр.wait_for_timeout(200)
    # ── всплывашки о решении ──
    стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ; т.preset_approvals = т.preset_approvals || [];
      window.__ОТКРЫТО = []; window.открытьСогласование = к => window.__ОТКРЫТО.push('пров:' + к); window.открытьУпоминание = (к, и) => window.__ОТКРЫТО.push('чат:' + к + ':' + и);
      try { localStorage.removeItem('banya_pop_ap_' + _sbUser.id); localStorage.removeItem('banya_pop_chat_' + _sbUser.id); } catch (e) {}
      document.getElementById('ntPop') && document.getElementById('ntPop').remove(); }""", код)
    стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ, д = Date.now();
      т.preset_approvals.push({ code: код, state: 'approved', preset_name: 'Баня «Старое»', sent_by: _sbUser.id, decided_by: 'u-ред',
        decided_name: 'Ольга Проверкина', decided_at: new Date(д - 600e3).toISOString(), for_all: false }); }""", код)
    стр.evaluate("() => всплывающиеУведомления()"); стр.wait_for_timeout(300)
    if стр.evaluate(КАРТОЧКИ):
        плохо(f"{н} всплыло решение, принятое до первого захода")
    стр.evaluate("""(код) => { const т = window.__ТАБЛИЦЫ, д = Date.now(), пл = (к, с, кто, имя, всех) => ({ code: к, state: с, preset_name: 'Баня «' + к + '»',
        sent_by: _sbUser.id, decided_by: кто, decided_name: имя, decided_at: new Date(д + 1000).toISOString(), for_all: всех });
      т.preset_approvals.push(пл('111111', 'approved', 'u-ред', 'Ольга Проверкина', true), пл('222222', 'returned', 'u-спец', 'Анна Специалист', false),
        пл('333333', 'approved', _sbUser.id, 'Проба', false)); }""", код)
    стр.evaluate("() => всплывающиеУведомления()"); стр.wait_for_timeout(400)
    к = стр.evaluate(КАРТОЧКИ)
    if sorted((х["з"], х["т"], х["кн"]) for х in к) != sorted([("Расчёт согласован за всех", "Баня «111111»", "Открыть расчёт"),
                                                               ("Расчёт вернули с правками", "Баня «222222»", "Открыть правки")]):
        плохо(f"{н} всплывашки о решении: {к}")
    if any("Ольга П." not in х["м"] and "Анна С." not in х["м"] for х in к):
        плохо(f"{н} в подписи нет того, кто решил: {[х['м'] for х in к]}")
    стр.evaluate("() => всплывающиеУведомления()"); стр.wait_for_timeout(300)
    if len(стр.evaluate(КАРТОЧКИ)) != 2:
        плохо(f"{н} одно и то же решение всплыло второй раз")
    # ── всплывашка о чате ──
    стр.evaluate("""() => { const д = Date.now(); window.__RPC.preset_chat_unread = () => [{ code: '444444', preset_name: 'Баня «Чат»', unread: 3,
        first_id: 'c0000000-0000-4000-8000-000000000009', first_at: new Date(д - 7200e3).toISOString(), last_at: new Date(д - 4000e3).toISOString() }]; }""")
    стр.evaluate("() => всплывающиеУведомления()"); стр.wait_for_timeout(400)
    к = стр.evaluate(КАРТОЧКИ)
    чат = [х for х in к if х["к"].startswith("chat:")]
    if len(к) != 3 or not чат or чат[0]["т"] != "Баня «Чат» — 3 сообщения больше часа" or чат[0]["кн"] != "Открыть чат":
        плохо(f"{н} всплывашка о чате: {к}")
    for т in стр.evaluate(ВЁРСТКА):
        плохо(f"{н} {т}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"popups-{ш}{'-n' if ночь else ''}{'-m' if модерн else ''}.png"))
    стр.evaluate("() => всплывающиеУведомления()"); стр.wait_for_timeout(300)
    if len(стр.evaluate(КАРТОЧКИ)) != 3:
        плохо(f"{н} тот же непрочитанный чат всплыл второй раз")
    # Переход и закрытие.
    for сел in ("#ntPop .nt-pop-i[data-k^='chat:'] .nt-pop-go", "#ntPop .nt-pop-i[data-k^='ap:111111'] .nt-pop-go", "#ntPop .nt-pop-i .nt-pop-x"):
        л = стр.locator(сел)
        if not л.count():
            плохо(f"{н} нет карточки для нажатия: {сел}"); continue
        л.first.click(); стр.wait_for_timeout(300)
    о = стр.evaluate("() => window.__ОТКРЫТО")
    if о != ["чат:444444:c0000000-0000-4000-8000-000000000009", "пров:111111"]:
        плохо(f"{н} переходы из всплывашек: {о}")
    if стр.evaluate(КАРТОЧКИ):
        плохо(f"{н} после нажатий карточки остались: {стр.evaluate(КАРТОЧКИ)}")
    # Новое сообщение в том же чате — всплывает снова; больше трёх разом — нет.
    стр.evaluate("""() => { const д = Date.now(); window.__RPC.preset_chat_unread = () => ['444444', '555555', '666666', '777777'].map((к, и) => ({ code: к, preset_name: 'Баня «' + к + '»',
        unread: 1 + и, first_id: null, first_at: new Date(д - 7200e3).toISOString(), last_at: new Date(д - 3000e3 + и).toISOString() })); }""")
    стр.evaluate("() => всплывающиеУведомления()"); стр.wait_for_timeout(400)
    к = стр.evaluate(КАРТОЧКИ)
    if len(к) != 3:
        плохо(f"{н} предел трёх карточек: {[х['к'] for х in к]}")
    стр.evaluate("() => { document.getElementById('ntPop').remove(); window.__RPC.preset_chat_unread = () => [{ code: '444444', preset_name: 'Баня «Чат»', unread: 4, first_id: null, first_at: new Date(Date.now() - 7200e3).toISOString(), last_at: new Date(Date.now() - 100).toISOString() }]; }")
    стр.evaluate("() => всплывающиеУведомления()"); стр.wait_for_timeout(300)
    if not any(х["к"].startswith("chat:444444") for х in стр.evaluate(КАРТОЧКИ)):
        плохо(f"{н} новое сообщение в уже показанном чате не всплыло")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900, False, False)
                прогон(бр, порт, 390, 844, False, False)
                прогон(бр, порт, 390, 844, True, False)
                прогон(бр, порт, 1440, 900, False, True)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: каждый шаг согласования — своё уведомление с точкой; всплывашки о решении другого и о чате, непрочитанном больше часа, "
          "без повторов, не больше трёх, с переходом и крестом; вёрстка на 390 и 1440, днём, ночью и в «Модерне».")


if __name__ == "__main__":
    главная()
