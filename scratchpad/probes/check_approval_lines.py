#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Расчёт согласован» — бледным цветом темы в журналах и строкой в чате пресета.

Константин 18.10.2026, снимком журнала пресета: «Расчёт согласован в журнале
выделяй цветом темы бледным и дублируй сообщение о согласовании в чат
пресета».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded:
  • в журнале мини-окна строка «Расчёт согласован» залита бледным цветом
    темы (тот же цвет, что --pc-tint), текст — цветом акцента; соседние
    строки — «Согласована часть расчёта», печать — без заливки; лента не
    прокручивается вбок;
  • в полном журнале действий, в «Модерне» и «Бланке», строка «Расчёт
    согласован» залита бледным цветом темы и при наведении остаётся такой,
    соседняя — без заливки;
  • в чате пресета строки-события о согласовании, которые кладёт база:
    «Расчёт согласован — за всех», «Согласована часть расчёта: цена»,
    «Расчёт возвращён с правками — чек-лист»; согласование — в заливке
    акцента, возврат — без неё; это записи, а не кнопки; в поле мини-окна;
  • на 390 и 1440, днём и ночью.

    python3 check_approval_lines.py
"""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_chat as ч
import check_log_chevron as л
from даты_событий import освежить
from playwright.sync_api import sync_playwright

СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


ДАННЫЕ = """(код) => {
  const т = window.__ТАБЛИЦЫ, д = Date.now(), мин = 60e3;
  т.profiles.push({ id: 'u-коллега', role: 'editor', first_name: 'Ольга', last_name: 'Проверкина' });
  const соб = (ид, вид, тело, назад) => ({ id: ид, code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина', body: тело, reply_to: null,
    review_state: null, kind: 'event', event: вид, ref: null, attachments: [], created_at: new Date(д - назад * мин).toISOString() });
  т.preset_messages = [
    { id: 'b0000000-0000-4000-8000-000000000001', code: код, author_id: 'u-коллега', author_name: 'Ольга Проверкина', body: 'Посмотрела расчёт',
      reply_to: null, review_state: null, kind: 'msg', attachments: [], created_at: new Date(д - 40 * мин).toISOString() },
    соб('b0000000-0000-4000-8000-000000000002', 'returned', 'чек-лист', 30),
    соб('b0000000-0000-4000-8000-000000000003', 'approved_part', 'цена', 20),
    соб('b0000000-0000-4000-8000-000000000004', 'approved', 'за всех', 10),
  ];
  window.__RPC.preset_chat_join = (а) => а.p_code === код ? new Date(д).toISOString() : null;
  window.__RPC.preset_chat_read = () => null;
  _чат = { код: '', сообщения: null, прочитано: 0, ошибка: '', грузится: false, когда: 0, нет: false };
  const ж = (вид, назад, rows) => ({ id: 'j' + вид, created_at: new Date(д - назад * мин).toISOString(), event_type: вид, user_id: 'u-проба',
    details: { presetCode: код, obj: null, rows: rows || [] } });
  window.__ЖУРНАЛ = [ж('approval_approved', 10, [{ k: 'Согласование', a: '', b: 'За всех' }]), ж('print', 9), ж('approval_part', 20, [{ k: 'Согласование', a: '', b: 'Цена' }])];
}"""

ЖУРНАЛ = """() => { const лента = document.querySelector('#presetChipCard .pc-lg-sc'), н = [];
  const ли = [...document.querySelectorAll('#presetChipCard .pc-lg > li[data-ev]')];
  const тинт = (() => { const п = document.createElement('i'); п.style.color = getComputedStyle(document.getElementById('presetChipCard')).getPropertyValue('--pc-tint'); document.body.appendChild(п); const ц = getComputedStyle(п).color; п.remove(); return ц; })();
  const строки = ли.map(л => ({ т: (л.querySelector('.pc-lg-w') || {}).textContent || '', ок: л.classList.contains('pc-lg-ok'), фон: getComputedStyle(л).backgroundColor,
    цвет: getComputedStyle(л.querySelector('.pc-lg-w')).color }));
  if (лента && лента.scrollWidth > лента.clientWidth + 1) н.push('лента журнала прокручивается вбок');
  return { строки, тинт, акцент: getComputedStyle(document.getElementById('presetChipCard')).getPropertyValue('--pc-acc'), н }; }"""

ЧАТ = """() => { const к = document.getElementById('presetChipCard'), r = к.getBoundingClientRect(), cs = getComputedStyle(к);
  const л = r.left + parseFloat(cs.paddingLeft), п = r.right - parseFloat(cs.paddingRight), н = [];
  const строки = [...к.querySelectorAll('.pc-chev-ap')].map(э => { const б = э.querySelector('.pc-chev-b'), бр = б.getBoundingClientRect();
    if (бр.left < л - .5 || бр.right > п + .5) н.push('строка о согласовании за полем карточки');
    return { т: б.textContent.replace(/\\s+/g, ' ').trim(), ок: э.classList.contains('ok'), кнопка: !!э.querySelector('button'), фон: getComputedStyle(б).backgroundColor }; });
  return { строки, н }; }"""


def мини(бр, порт, ш, в, ночь):
    н = f"[{ш}{' ночь' if ночь else ''}]"
    стр, ошибки = ч.начать(бр, порт, ш, в, ночь)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(ДАННЫЕ, код)
    ч.открыть(стр); ч.вкладка(стр, "m"); стр.wait_for_timeout(800)
    с = стр.evaluate(ЧАТ)
    ждали = [("Расчёт возвращён с правками — чек-лист", False), ("Согласована часть расчёта: цена", True), ("Расчёт согласован — за всех", True)]
    if [(х["т"], х["ок"]) for х in с["строки"]] != ждали:
        плохо(f"{н} строки о согласовании в чате: {[(х['т'], х['ок']) for х in с['строки']]}")
    if any(х["кнопка"] for х in с["строки"]):
        плохо(f"{н} строка о согласовании в чате — кнопка, а нажимать её некуда")
    if с["строки"] and len({х["фон"] for х in с["строки"] if х["ок"]}) != 1:
        плохо(f"{н} заливка строк согласования разная")
    for т in с["н"]:
        плохо(f"{н} чат: {т}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"approval-chat-{ш}{'-n' if ночь else ''}.png"))
    стр.evaluate("(код) => { _журналПресета = { код: String(код), события: window.__ЖУРНАЛ, ошибка: '', грузится: false, когда: Date.now(), заранее: false }; }", код)
    ч.вкладка(стр, "l"); стр.wait_for_timeout(500)
    ж = стр.evaluate(ЖУРНАЛ)
    ок = [х for х in ж["строки"] if х["ок"]]
    if len(ок) != 1 or not ок[0]["т"].endswith("Расчёт согласован"):
        плохо(f"{н} журнал мини-окна: выделены {[х['т'] for х in ок]}")
    elif ок[0]["фон"] != ж["тинт"]:
        плохо(f"{н} строка «Расчёт согласован» залита {ок[0]['фон']}, а не бледным цветом темы {ж['тинт']}")
    for х in ж["строки"]:
        if not х["ок"] and х["фон"] not in ("rgba(0, 0, 0, 0)", "transparent"):
            плохо(f"{н} журнал мини-окна: залита и «{х['т']}»")
    for т in ж["н"]:
        плохо(f"{н} журнал: {т}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"approval-log-{ш}{'-n' if ночь else ''}.png"))
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


ПОЛНЫЙ = """() => [...document.querySelectorAll('#alFeed .al-row')].map(р => ({ т: (р.querySelector('.al-text') || {}).textContent || '',
  ок: р.classList.contains('al-ok'), фон: getComputedStyle(р).backgroundColor, тинт: (() => { const п = document.createElement('i'); п.style.color = getComputedStyle(document.body).getPropertyValue('--green-bg'); document.body.appendChild(п); const ц = getComputedStyle(п).color; п.remove(); return ц; })() }))"""


def полный(бр, порт, ш, в, бланк):
    н = f"[полный журнал {'Бланк' if бланк else 'Модерн'} {ш}]"
    события = [dict(л.СОБЫТИЯ[1], id=11, event_type="approval_approved", created_at="2026-09-23T08:40:00Z"),
               dict(л.СОБЫТИЯ[1], id=12, event_type="approval_part", created_at="2026-09-23T08:39:00Z")]
    таблицы = dict(л.ТАБЛИЦЫ, events=освежить(события))
    стр = бр.new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(л.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\nObject.assign(window.__ТАБЛИЦЫ, " + json.dumps(таблицы, ensure_ascii=False) + ");")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async ([бланк]) => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display='none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display='none';
      _sbProfile = { role: 'admin', full_name: 'Проба' }; document.body.classList.toggle('ui-blank', бланк);
      openActionLog(); await loadActionLog(true); await new Promise(r => setTimeout(r, 600)); }""", [бланк])
    р = стр.evaluate(ПОЛНЫЙ)
    ок = [х for х in р if х["ок"]]
    if len(ок) != 1 or "Расчёт согласован" not in ок[0]["т"]:
        плохо(f"{н} выделены: {[х['т'][:40] for х in ок]}")
    elif ок[0]["фон"] != ок[0]["тинт"]:
        плохо(f"{н} строка «Расчёт согласован» залита {ок[0]['фон']}, а не {ок[0]['тинт']}")
    else:
        стр.locator("#alFeed .al-row.al-ok").hover(); стр.wait_for_timeout(250)
        if стр.evaluate(ПОЛНЫЙ)[р.index(ок[0])]["фон"] != ок[0]["тинт"] and ш > 600:
            плохо(f"{н} при наведении строка «Расчёт согласован» теряет заливку")
    for х in р:
        if not х["ок"] and "Согласована часть" in х["т"] and х["фон"] not in ("rgba(0, 0, 0, 0)", "transparent"):
            плохо(f"{н} залита и «Согласована часть расчёта»")
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"approval-al-{'blank' if бланк else 'modern'}-{ш}.png"))
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                for ш, в in ((1440, 900), (390, 844)):
                    for ночь in (False, True):
                        мини(бр, порт, ш, в, ночь)
                    for бланк in (False, True):
                        полный(бр, порт, ш, в, бланк)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: «Расчёт согласован» залит бледным цветом темы в журнале мини-окна и в полном журнале (Модерн и Бланк), "
          "соседние строки без заливки; в чате — строки о согласовании, части и возврате, записями, в поле мини-окна; 390 и 1440, день и ночь.")


if __name__ == "__main__":
    главная()
