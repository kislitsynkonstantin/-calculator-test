#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка по чек-листу: правила из разбора (П-ПС), внесённые 30.09.2026.

Константин 30.09.2026 назвал пункты разбора «Чек-лист в проверке
калькулятора»: 1-2, 1-7, 1-10, 1-12, 1-14, 2-4, 2-6, 2-10, 2-12, 4-4,
4-9, 5-1, 5-11, 6-6, 6-6а, 6-10, 7-1, 7-2, 7-5, 7-6, 8-5, 9-3, 9-6, 9-9 —
«внеси все эти пункты, как ты предлагал в файле PDF».

Проба для каждого правила ставит расчёт, при котором оно обязано сработать,
и тот же расчёт с исправлением, при котором обязано молчать. Для 2-12, 4-4 и
7-6 — названия в каталоге каркаса. Каркас, 1440 px; 7-2 — клеёный брус.

    python3 check_checklist_rules.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []

# Каждое правило: (номер, текст замечания или вопроса, подготовка «сработать», подготовка «молчать»).
# Подготовка выполняется поверх чистого расчёта: сброс() вызывается перед каждой.
СБРОС = """() => {
  SECTIONS.forEach(р => { customOptions[р.key] = []; customNotes[р.key] = []; });
  highlightedOpts.clear();
  (OPTIONS || []).forEach(o => { checkedOptions[o.id] = !!o.included; });
  contractsConfig = [
    { id:1, name:'Основной договор', code:'КАР', color:'#16a34a', sections:['foundation','frame','insulation','exterior','windows','roof','paint','extra','engineering'] },
    { id:2, name:'Отделка', code:'ОТД', color:'#eab308', sections:['interior','steam','stove'] } ];
  if (typeof canvasItems !== 'undefined') canvasItems.length = 0;
  document.querySelectorAll('#imageCanvas .canvas-img-item').forEach(э => э.remove());
  const д = document.getElementById('contractDate'); if (д) д.value = '2026-07-15';
  // Спокойный фон: фундамент, бытовка и биотуалет стоят, чтобы их правила не мешали остальным.
  checkedOptions.f5 = true; checkedOptions.e6 = true; checkedOptions.e7 = true; checkedOptions.r6 = true;
}"""
СВОЯ = """(раздел, имя, выделить, цена) => { const id = 'п' + Math.random().toString(36).slice(2, 8);
  customOptions[раздел] = customOptions[раздел] || []; customOptions[раздел].push({ id, name: имя, price: цена == null ? 1000 : цена, checked: true });
  if (выделить !== false) highlightedOpts.add('custom_' + id); return id; }"""

ПРАВИЛА = [
    ("1-2", "Перенести раздел «", "() => { contractsConfig[1].sections.push('roof'); contractsConfig[0].sections = contractsConfig[0].sections.filter(к => к !== 'roof'); }", "() => {}"),
    # 1-7: вопрос знает, что добавлено (30.09.2026): один вид — просит ещё вид и
    # планировку; вид и планировка — минимум соблюдён. Снимки настоящие, код их узнаёт.
    ("1-7", "Добавить ещё один вид визуализации и планировку", "async () => { canvasAddImage(ВИЗ); await Promise.all(снимкиХолста().map(видКартинки)); }", "async () => { canvasAddImage(ВИЗ); canvasAddImage(ПЛАН); await Promise.all(снимкиХолста().map(видКартинки)); }"),
    # 1-10: подсказка выбрать опции; примечание «не входят» её не снимает (30.09.2026).
    ("1-10", "Выбрать опции бытовки и биотуалета", "() => { checkedOptions.e6 = false; checkedOptions.e7 = false; customNotes.extra.push({ id: 'н1', text: 'Бытовка и биотуалет не входят' }); }", "() => {}"),
    ("1-10 туалет", "Выбрать опцию биотуалета", "() => { checkedOptions.e7 = false; }", "() => {}"),
    ("1-10 бытовка", "Выбрать опцию бытовки", "() => { checkedOptions.e6 = false; }", "() => { checkedOptions.e6 = false; checkedOptions.e5 = true; }"),
    ("1-12", "у купели", "() => { своя('extra', 'Купель'); }", "() => { своя('extra', 'Купель с внешней печью, 1800×1200 мм, кедр'); }"),
    ("1-14", "у бассейна приямок", "() => { своя('extra', 'Бассейн 3×4 м'); }", "() => { своя('extra', 'Бассейн 3×4 м, приямок не входит'); }"),
    ("2-4", "отмостку", "() => { checkedOptions.f5 = false; checkedOptions.f11 = true; }", "() => { checkedOptions.f5 = false; checkedOptions.f11 = true; customNotes.foundation.push({ id: 'н2', text: 'Отмостка не входит' }); }"),
    ("2-6", "тепляк", "() => { checkedOptions.f5 = false; checkedOptions.f11 = true; document.getElementById('contractDate').value = '2026-12-10'; }", "() => { checkedOptions.f5 = false; checkedOptions.f11 = true; document.getElementById('contractDate').value = '2026-06-10'; }"),
    ("2-10", "Фундамент не выбран", "() => { checkedOptions.f5 = false; }", "() => { checkedOptions.f5 = false; customNotes.foundation.push({ id: 'н3', text: 'Фундамент не входит — заказчика' }); }"),
    # Забивные сваи — тоже выбранный фундамент: «сваи», а не «свай» (30.09.2026, снимком).
    ("2-10 сваи", "Фундамент не выбран", "() => { checkedOptions.f5 = false; }", "() => { checkedOptions.f5 = false; checkedOptions.f9 = true; }"),
    ("4-9", "Форма кровли не совпадает", "() => { checkedOptions.r17 = true; }", "() => {}"),
    ("5-1", "имитацию 20 мм", "() => { checkedOptions.ex6 = true; }", "() => { checkedOptions.ex6 = false; }"),
    ("5-11", "сорт древесины", "() => { своя('interior', 'Вагонка на потолок мансарды'); }", "() => { своя('interior', 'Вагонка на потолок мансарды, сорт АВ'); }"),
    # У инженерной доски сорта нет — правку не пишем (30.09.2026, снимком).
    ("5-11 инженерная доска", "сорт древесины", "() => { своя('interior', 'Вагонка на потолок мансарды'); }", "() => { своя('interior', 'Монтаж инженерной доски в комнате отдыха'); }"),
    # ДПК — не древесина, сорта нет (30.09.2026, снимком).
    ("5-11 ДПК", "сорт древесины", "() => { своя('extra', 'Лестница на террасу из террасной доски'); }", "() => { своя('extra', 'Лестница на террасу шириной 6 м из ДПК террасной доски'); }"),
    ("6-6", "у панорамного окна", "() => { своя('windows', 'Панорамное окно в парную'); }", "() => { своя('windows', 'Панорамное окно в парную 1200×800 мм, подогрев, тонировка'); }"),
    ("6-6а", "Перенести окно в раздел", "() => { своя('steam', 'Окно в парную из липы'); }", "() => { своя('windows', 'Окно в парную из липы'); }"),
    ("6-10", "у мансардного окна", "() => { своя('windows', 'Мансардное окно Velux'); }", "() => { своя('windows', 'Мансардное окно Velux, дерево, открывание поворотное, клапан, однокамерное'); }"),
    ("7-1", "только заводская", "() => { checkedOptions.p2 = true; }", "() => { checkedOptions.p15 = true; }"),
    ("7-5", "шлифовку", "() => { checkedOptions.p4 = true; checkedOptions.ex9 = true; checkedOptions.ex2 = false; }", "() => { checkedOptions.p14 = true; }"),
    ("8-5", "камни для печи", "() => { checkedOptions.st1 = true; checkedOptions.st16 = true; checkedOptions.st29 = true; checkedOptions.st31 = true; }", "() => { checkedOptions.st1 = true; checkedOptions.st16 = true; checkedOptions.st29 = true; checkedOptions.st31 = true; checkedOptions.st20 = true; }"),
    # Дымоход Экономайзер Ламели — не в металле: при портале в камне правки нет (30.09.2026, снимком).
    ("дымоход ламели", "Дымоход в металле", "() => { checkedOptions.st17 = true; checkedOptions.st32 = true; checkedOptions.st27 = true; }", "() => { checkedOptions.st21 = true; checkedOptions.st32 = true; checkedOptions.st28 = true; }"),
    ("9-3", "стяжку", "() => { своя('engineering', 'Водяной тёплый пол в санузле'); }", "() => { своя('engineering', 'Водяной тёплый пол в санузле, стяжка 50 мм'); }"),
    ("9-6", "техническое помещение", "() => { checkedOptions.eng19 = true; }", "() => {}"),
    ("6-4", "Окна Veka WHS 72", "() => {}", "() => { checkedOptions.w8 = true; }"),
    ("9-9", "Перенести освещение", "() => { своя('interior', 'Светильники в комнату отдыха'); }", "() => { своя('engineering', 'Светильники в комнату отдыха'); }"),
]

ИМЕНА = {
    "2-12 f11": ("f11", "без учёта перепада высот"),
    "4-4 r9": ("r9", "глянец (матовый — за доплату)"),
    "4-4 r18": ("r18", "глянец (матовый — за доплату)"),
    "4-4 r19": ("r19", "(матовый — за доплату)"),
    "4-4 r20": ("r20", "глянец (матовый — за доплату)"),
    "7-6 p2": ("p2", "Tikkurila или аналоги"),
    "7-6 p3": ("p3", "Tikkurila или аналоги"),
    "7-6 p4": ("p4", "Osmo или аналоги"),
    "7-6 p5": ("p5", "Tikkurila или аналоги"),
    "7-6 p6": ("p6", "Osmo или аналоги"),
    # Генератор бензиновый, не дизельный (30.09.2026, снимком).
    "генератор e8": ("e8", "Бензиновый электрогенератор на время строительства"),
}

ТЕКСТЫ = "() => { const п = проверкаПоЧекЛисту(); return п.замечания.map(з => (з.стоп ? 'СТОП ' : '') + з.т + ' @' + з.раздел).concat(п.вопросы.map(в => '? ' + в)); }"


def прогон(бр, порт):
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); window.своя = """ + СВОЯ + """; window.ВИЗ = '/scratchpad/probes/образцы_приложения2/визуализация.jpg'; window.ПЛАН = '/scratchpad/probes/образцы_приложения2/планировка.png'; }""")
    for ном, текст, вкл, выкл in ПРАВИЛА:
        стр.evaluate(СБРОС); стр.evaluate(вкл)
        есть = стр.evaluate(ТЕКСТЫ)
        if not any(текст in т for т in есть):
            НАХОДКИ.append(f"[{ном}] правило не сработало: ждали «{текст}», есть {есть}")
        стр.evaluate(СБРОС); стр.evaluate(выкл)
        после = стр.evaluate(ТЕКСТЫ)
        if any(текст in т for т in после):
            НАХОДКИ.append(f"[{ном}] правило не замолчало после исправления: {[т for т in после if текст in т]}")
    # 1-15 «Выделить свои позиции цветом» снят (30.09.2026: «убери вообще правку
    # выделения своих позиций цветом. Это только через ИИ-анализ можно»):
    # дорогая своя позиция без цвета пункта не даёт.
    стр.evaluate(СБРОС); стр.evaluate("() => { своя('extra', 'Навес для дров', false, 90000); своя('exterior', 'Террасная доска — ДПК UnoDeck Ultra', false, 300000); }")
    if any("Выделить свои позиции цветом" in т for т in стр.evaluate(ТЕКСТЫ)):
        НАХОДКИ.append("[1-15] снятый пункт «Выделить свои позиции цветом» по-прежнему появляется")
    # 4-9 и 7-1 — стоп.
    стр.evaluate(СБРОС); стр.evaluate("() => { checkedOptions.r17 = true; checkedOptions.p2 = true; }")
    т = стр.evaluate(ТЕКСТЫ)
    for часть in ("Форма кровли не совпадает", "только заводская"):
        if not any(х.startswith("СТОП") and часть in х for х in т):
            НАХОДКИ.append(f"[стоп] «{часть}» не стоп: {т}")
    # Чистый расчёт с фоном — без замечаний из новых правил.
    стр.evaluate(СБРОС); стр.evaluate("async () => { canvasAddImage(ВИЗ); canvasAddImage(ПЛАН); await Promise.all(снимкиХолста().map(видКартинки)); }")
    т = [х for х in стр.evaluate(ТЕКСТЫ) if not х.startswith("? Скидка") and not х.startswith(("? Окна Blitz 60", "? Окна Veka WHS 72")) and "пробное бурение" not in х]
    if т:
        НАХОДКИ.append(f"[фон] на спокойном расчёте есть замечания: {т}")
    for ключ, (ид, кусок) in ИМЕНА.items():
        имя = стр.evaluate("(ид) => (getOpt(ид) || {}).name || ''", ид)
        if кусок not in имя:
            НАХОДКИ.append(f"[{ключ}] в названии нет «{кусок}»: «{имя}»")
    # Старая строка Шинглас (r5) снята совсем: её нет ни в новых, ни в старых
    # ценах, а отмеченная в сохранённом расчёте — видна (30.09.2026).
    вид = стр.evaluate("""async () => { const р = []; for (const режим of ['new', 'legacy']) { setOptionPricingMode(режим); await new Promise(r => setTimeout(r, 300));
        р.push(isOptionVisible(getOpt('r5')), !!document.querySelector('#lbl_r5')); }
      checkedOptions.r5 = true; р.push(isOptionVisible(getOpt('r5'))); checkedOptions.r5 = false; setOptionPricingMode('new'); return р; }""")
    if вид[:4] != [False, False, False, False] or вид[4] is not True:
        НАХОДКИ.append(f"[Шинглас] старая строка видна в списке или скрыта отмеченной: {вид}")
    # 7-2 — клеёный брус: заводская покраска снаружи — стоп.
    стр.evaluate("async () => { await switchTech('glulam'); await new Promise(r => setTimeout(r, 1500)); selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }")
    стр.evaluate(СБРОС)
    стр.evaluate("() => { customOptions.paint.push({ id: 'зп', name: 'Заводская покраска фасада маслом', price: 1000, checked: true }); highlightedOpts.add('custom_зп'); }")
    т = стр.evaluate(ТЕКСТЫ)
    if not any(х.startswith("СТОП") and "только ручная" in х for х in т):
        НАХОДКИ.append(f"[7-2] на брусе заводская покраска снаружи не стоп: {т}")
    стр.evaluate(СБРОС)
    стр.evaluate("() => { customOptions.paint.push({ id: 'рп', name: 'Покраска фасада маслом со шлифовкой', price: 1000, checked: true }); highlightedOpts.add('custom_рп'); }")
    if any("только ручная" in х for х in стр.evaluate(ТЕКСТЫ)):
        НАХОДКИ.append("[7-2] на брусе ручная покраска снаружи дала замечание")
    # Панель вкладки «Проверка» строится без ошибок при всех правилах разом.
    стр.evaluate("() => { switchTech('frame'); }"); стр.wait_for_timeout(1500)
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])
            прогон(бр, порт)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print(f"Чисто: {len(ПРАВИЛА)} правил из разбора чек-листа срабатывают и замолкают после исправления, "
          "4-9 и 7-1 — стоп, 7-2 — стоп на брусе; в названиях каталога — «без учёта перепада высот», "
          "«глянец (матовый — за доплату)» и «или аналоги»; спокойный расчёт замечаний не даёт.")


if __name__ == "__main__":
    главная()
