#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Заключение о согласовании в чат и отметка «Подписан».

Константин 18.10.2026: «Сделай, чтобы после того как согласован пресет, в чат
формировался PDF, оформленный по скилу бланк, в котором бы были указаны
пункты, которые пропустили и правки в договоре, которые были внесены…
После того, как пресет согласован, в проверке должна появиться кнопка
«Подписан»… В чате это отображается. И менеджеру прилетает уведомление со
ссылкой на чат написать резюме по заключению или прикрепить файл резюме. Код
чтобы его идентифицировал».

Проба держит, на заглушке базы и в настоящих Geologica и Unbounded, с
библиотеками PDF из пакетов npm вместо cdnjs:
  • лист заключения: код пресета, проект, сумма, кто отправил и кто
    согласовал оба места, пропущенные пункты «Проверки» (замечание с разделом
    и вопрос), правки договора «было — стало» и убранный пункт, правки из
    чата; тон «Зелёный-графит», знак с зелёной крышей;
  • согласование вторым местом само кладёт в чат сообщение с PDF-вложением:
    файл ушёл в хранилище чата, это настоящий PDF A4, страниц не меньше
    одной, на каждой подвал «Стр. N из M», страницы не пустые;
  • до согласования кнопки «Подписан» нет; после — «Подписан» и
    «Заключение в чат»; нажатие зовёт preset_approval_sign с кодом, плашка
    «Договор подписан», кнопки «Подписан» больше нет, действие в журнале;
  • автору: строка в колокольчике с кодом и «резюме», переход в чат с полем,
    начатым словами «Резюме по заключению договора (код …)»;
  • отдельными разделами: пропущенные правки (убранная из проверки и
    отмеченная выполненной без изменений расчёта) и ручные позиции с ценами
    (своя позиция, сумма в опции без цены, цена, поправленная карандашом,
    формула со сменённой маржой, если она есть в каталоге заглушки);
    без журнала пресета лист говорит, что правки не проверены;
  • вёрстка на 390 и 1440: блок внутри карточки, поля нажатия не меньше 44 px.

    python3 check_approval_report.py
"""
import base64, os, pathlib, re, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
import check_preset_approval as па
from playwright.sync_api import sync_playwright

ЗДЕСЬ = pathlib.Path(__file__).parent
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
ЛИБЫ = pathlib.Path(os.environ.get("BM_LIBS") or "/tmp/claude-0/-home-user-vscode-workspace/0db66daf-36ea-5fb3-b079-395424f89a35/scratchpad/либы")
JSPDF = ЛИБЫ / "jspdf/package/dist/jspdf.umd.min.js"
H2C = ЛИБЫ / "h2c/package/dist/html2canvas.min.js"
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


# Хранилище чата держит сам файл: проба читает PDF, который ушёл бы в базу.
ХРАНИЛИЩЕ = """() => { const из = _sb.storage.from.bind(_sb.storage);
  window.__PDF = [];
  _sb.storage.from = к => { const о = из(к), груз = о.upload;
    о.upload = async (путь, файл, наст) => { if (файл && /pdf/.test(файл.type || '')) {
        const б = new Uint8Array(await файл.arrayBuffer()); let с = ''; for (let i = 0; i < б.length; i += 8192) с += String.fromCharCode.apply(null, б.subarray(i, i + 8192));
        window.__PDF.push({ путь, имя: файл.name, данные: btoa(с) }); }
      return груз(путь, файл, наст); };
    return о; };
  window.__RPC.preset_approval_sign = (а) => {
    window.__ВЫЗОВЫ.push(['sign', JSON.parse(JSON.stringify(а))]);
    const с = window.__ТАБЛИЦЫ.preset_approvals.find(х => х.code === а.p_code);
    if (!с || с.state !== 'approved') return { __ошибка: 'расчёт не согласован' };
    Object.assign(с, { signed_at: new Date().toISOString(), signed_by: 'u-проба', signed_name: 'Проба Пробная' });
    // Шаг в журнал согласования — как пишет триггер базы.
    (window.__ТАБЛИЦЫ.preset_approval_log = window.__ТАБЛИЦЫ.preset_approval_log || []).push({ id: 900, code: а.p_code, event: 'signed', slot: null,
      by_id: с.signed_by, by_name: с.signed_name, sent_by: с.sent_by, preset_name: с.preset_name, project_name: с.project_name, at: с.signed_at });
    window.__ТАБЛИЦЫ.preset_messages.push({ id: 'bbbbbbbb-2222-4222-8222-222222222222', code: а.p_code, author_id: 'u-проба', author_name: 'Проба Пробная',
      body: 'Проба Пробная', reply_to: null, attachments: [], review_state: null, kind: 'event', event: 'signed', ref: null, created_at: с.signed_at });
    return Object.assign({}, с); }; }"""

# Пропуски «Проверки» и правки договора — те, что должны лечь в лист.
ПРАВКИ = """() => {
  пропускиПроверки().add(ключПроверки('з', 'Добавить водосточную систему', 'roof'));
  пропускиПроверки().add(ключПроверки('в', 'Уточнить у заказчика цвет кровли'));
  buildContractHtmlKar(getContractVarsKar(1));
  const тип = _типовыеПункты.kar || {}, номера = Object.keys(тип).filter(н => простойТекстПункта(тип[н].части, тип[н].метки).length > 40);
  const [н1, н2] = [номера[3], номера[7]];
  _правкиДоговора.kar = _правкиДоговора.kar || {};
  _правкиДоговора.kar[н1] = { части: [{ т: 'Срок монтажа — сорок рабочих дней с даты поступления аванса.' }], база: тип[н1].части, кто: 'Ольга Проверкина', когда: new Date().toISOString() };
  _правкиДоговора.kar[н2] = { убран: true, база: тип[н2].части, кто: 'Ольга Проверкина', когда: new Date().toISOString() };
  return [н1, н2, простойТекстПункта(тип[н1].части, тип[н1].метки).slice(0, 30)]; }"""


# Ручное в расчёте и пропущенные правки (Константин, 18.10.2026: «дописывай,
# какие правки пропустили в расчёте. Какие пункты ручные, и цены к ним.
# Отдельном прям пиши в файле»). Своя позиция, сумма в опции без цены,
# формула со сменённой маржой; в чате — правка, отмеченная выполненной без
# изменений расчёта, правка, убранная из проверки, и правка, после которой
# расчёт менялся. Всё ставится, лист собирается, и всё снимается обратно:
# иначе отпечаток расчёта разошёлся бы с отправленным на согласование.
РУЧНЫЕ = """() => {
  const код = пресетКарточки().код;
  const былЧат = { код: _чат.код, сообщения: _чат.сообщения }, былЖурнал = _журналПресета;
  const былиГалочки = Object.assign({}, checkedOptions), былиФормулы = JSON.parse(JSON.stringify(formulaOverrides));
  getCustomOpts('roof').push({ id: 'zk-свой', name: 'Проба: своя позиция', price: 45000, checked: true });
  const без = OPTIONS.find(o => !o.included && !getOptPrice(o) && document.getElementById('por_' + o.id));
  const поле = без && document.getElementById('por_' + без.id), былоПоле = поле ? поле.value : '';
  if (без) { checkedOptions[без.id] = true; поле.value = '12 345'; }
  const ф = OPTIONS.find(o => !o.included && o.status === 'formula' && o.formula && o.formula.areaSrc !== 'qty' && o.formula.defaultMargin != null && getOptPrice(o));
  if (ф) { checkedOptions[ф.id] = true; formulaOverrides[ф.id] = Object.assign({}, formulaOverrides[ф.id], { margin: ф.formula.defaultMargin + 0.05 }); }
  // Цена, поправленная карандашом: в таблице проекта своя.
  const табл = PRICE_MATRIX[selectedProject[0]] || {};
  // В заглушке таблица проекта пустая — её клетку проба ставит сама.
  const кар = OPTIONS.find(o => !o.included && !o.formula && o !== без && ценаПоПравилу(o.id, selectedProject) === undefined && Number(getOptPrice(o)) > 0);
  const былиЦены = matrixOverrides.has(selectedProject) ? Object.assign({}, matrixOverrides.get(selectedProject)) : null;
  const былаТаблица = PRICE_MATRIX[selectedProject[0]];
  if (кар) { const ц = Number(getOptPrice(кар)); PRICE_MATRIX[selectedProject[0]] = Object.assign({}, табл, { [кар.id]: ц });
    checkedOptions[кар.id] = true; matrixOverrides.set(selectedProject, Object.assign({}, былиЦены || {}, { [кар.id]: ц + 1000 })); }
  const t0 = Date.now() - 600000, iso = н => new Date(t0 + н).toISOString();
  const м = (id, body, review_state, done) => ({ id, code: код, kind: 'msg', body, review_state, created_at: iso(0), done_at: done == null ? null : iso(done), author_name: 'Ольга Проверкина', attachments: [] });
  _чат.код = код;
  _чат.сообщения = (былЧат.код === код && былЧат.сообщения ? былЧат.сообщения.slice() : []).concat([
    м('zk-1', 'Поменяйте цвет кровли на графит', 'done', 60000),
    м('zk-2', 'Добавьте второй вход в парную', null),
    м('zk-3', 'Уберите лишнюю террасу', 'done', 120000)]);
  _журналПресета = { код, ошибка: '', грузится: false, когда: Date.now(), события: [
    { id: 1, created_at: iso(30000), event_type: 'review_removed', user_id: 'u-ред', details: { obj: 'Добавьте второй вход в парную', rows: [{ k: 'Правка', a: '', b: 'Добавьте второй вход в парную' }] } },
    { id: 2, created_at: iso(90000), event_type: видыПравокПресета()[0], user_id: 'u-проба', details: { obj: 'проба', rows: [] } }] };
  let д, h, безЖурнала;
  try {
    const а = Object.assign({}, согласованиеПресета(), { state: 'approved', approved_at: new Date().toISOString() });
    д = данныеЗаключения(а); h = htmlЗаключения(д);
    _журналПресета = { код, ошибка: 'нет связи', грузится: false, когда: Date.now(), события: null };
    безЖурнала = htmlЗаключения(данныеЗаключения(а));
  } finally {
    customOptions.roof = getCustomOpts('roof').filter(с => с.id !== 'zk-свой');
    Object.keys(checkedOptions).forEach(к => { if (!(к in былиГалочки)) delete checkedOptions[к]; });
    Object.assign(checkedOptions, былиГалочки);
    formulaOverrides = былиФормулы;
    if (былиЦены) matrixOverrides.set(selectedProject, былиЦены); else matrixOverrides.delete(selectedProject);
    if (былаТаблица === undefined) delete PRICE_MATRIX[selectedProject[0]]; else PRICE_MATRIX[selectedProject[0]] = былаТаблица;
    if (поле) поле.value = былоПоле;
    _чат.код = былЧат.код; _чат.сообщения = былЧат.сообщения; _журналПресета = былЖурнал;
  }
  const текст = х => х.replace(/<style>[\\s\\S]*?<\\/style>/, '').replace(/<[^>]+>/g, ' ').replace(/\\s+/g, ' ');
  return { без: без ? без.name : '', ф: ф ? ф.name : '', кар: кар ? кар.name : '', пропущено: д.пропущено, ручные: д.ручные, текст: текст(h), безЖурнала: текст(безЖурнала) }; }"""


def начать(бр, порт, ш, в):
    стр = бр.new_page(viewport={"width": ш, "height": в})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.on("console", lambda с: ошибки.append(с.text) if "[заключение]" in с.text else None)
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=па.ШРИФТЫ))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.route("**/cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js", lambda r: r.fulfill(status=200, content_type="text/javascript", body=JSPDF.read_bytes()))
    стр.route("**/cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js", lambda r: r.fulfill(status=200, content_type="text/javascript", body=H2C.read_bytes()))
    стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle('blank', false); appSettings.showCheckBadge = true;
      window.__тосты = []; const был = window.showToast; window.showToast = function (т) { window.__тосты.push(String(т)); return был.apply(this, arguments); };
      selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); }""")
    стр.locator("#presetChip .pc-body").click(); стр.wait_for_timeout(300)
    стр.locator("#presetChipCard .pc-save").click(); стр.wait_for_timeout(300)
    if стр.locator("#pcName").count():
        стр.locator("#pcName").press("Enter")
    стр.wait_for_timeout(2600)
    return стр, ошибки


def страницыPdf(данные, н):
    """PDF во временную папку, страницы — картинками; возвращает пути и размер."""
    п = pathlib.Path(tempfile.mkdtemp(prefix="zk-"))
    ф = п / "z.pdf"
    ф.write_bytes(данные)
    if not данные.startswith(b"%PDF-"):
        плохо(f"{н} вложение не PDF: {данные[:12]!r}"); return [], ""
    инфо = subprocess.run(["pdfinfo", str(ф)], capture_output=True, text=True).stdout
    subprocess.run(["pdftoppm", "-r", "60", "-png", str(ф), str(п / "с")], check=True)
    return sorted(п.glob("с-*.png")), инфо


def прогон(бр, порт, ш, в, полный):
    н = f"[{ш}]"
    стр, ошибки = начать(бр, порт, ш, в)
    код = стр.evaluate("() => { const p = loadAllPresets()[activePresetId]; return p && (p.shortCode || p.sharedId); }")
    if not код:
        плохо(f"{н} пресету не выдан код"); стр.close(); return
    стр.evaluate(па.ДАННЫЕ, код)
    стр.evaluate(ХРАНИЛИЩЕ)
    стр.evaluate("""() => { window.__проверкаБыла = проверкаПоЧекЛисту;
      window.проверкаПоЧекЛисту = function () { const п = window.__проверкаБыла.apply(this, arguments); п.замечания = п.замечания.filter(з => !з.стоп); return п; }; }""")
    правки = стр.evaluate(ПРАВКИ)
    па.открытьПроверку(стр)
    па.нажать(стр, "ap-send"); стр.wait_for_timeout(600)
    if стр.locator("#presetChipCard [data-act='ap-sign']").count():
        плохо(f"{н} «Подписан» есть до согласования")

    # ── лист заключения ──
    if полный:
        лист = стр.evaluate("""() => { const а = Object.assign({}, согласованиеПресета(), { state: 'approved', price_name: 'Ольга Проверкина', price_at: new Date().toISOString(),
            check_name: 'Нина Офисная', check_at: new Date().toISOString(), approved_at: new Date().toISOString() });
          const д = данныеЗаключения(а), h = htmlЗаключения(д);
          return { д: { код: д.код, проект: д.проект, итог: д.итог, пропуски: д.пропуски, правкиДог: д.правкиДог.map(п => ({ н: п.н, убран: п.убран, было: !!п.было, стало: п.стало })) },
            тон: /data-tone="bmsk"/.test(h), цифры: /tabular-nums|letter-spacing:-/.test(h), знак: h.indexOf(_картинкиТонов.bmsk && _картинкиТонов.bmsk.dark || '\\u0000') >= 0,
            текст: h.replace(/<style>[\\s\\S]*?<\\/style>/, '').replace(/<[^>]+>/g, ' ').replace(/\\s+/g, ' ') }; }""")
        т = лист["текст"]
        for что in ["Заключение о согласовании", "Пропущенные пункты проверки", "Добавить водосточную систему", "Уточнить у заказчика цвет кровли",
                    "вопрос", "Правки договора", "Срок монтажа — сорок рабочих дней", "убран", "Было", "Стало", "Ольга", "Нина"]:
            if что not in т:
                плохо(f"{н} в листе заключения нет «{что}»")
        if len(лист["д"]["правкиДог"]) != 2 or not all(п["было"] for п in лист["д"]["правкиДог"]):
            плохо(f"{н} правки договора в листе: {лист['д']['правкиДог']}")
        if re.search(r"₽\s*₽", т):
            плохо(f"{н} в листе заключения знак рубля стоит дважды")
        # html2canvas рисует цифры холстом без font-variant-numeric и
        # отрицательной разрядки: раскладка и рисунок расходятся, пробелы в
        # суммах и датах пропадают или раздуваются.
        if лист["цифры"]:
            плохо(f"{н} в листе заключения моноширинные цифры или сжатая разрядка — снимок их разъедет")
        if not лист["тон"]:
            плохо(f"{н} лист заключения не в тоне «Зелёный-графит»")

        # ── ручные позиции и пропущенные правки ──
        р = стр.evaluate(РУЧНЫЕ)
        т = р["текст"]
        for что in ["Пропущенные правки", "Ручные позиции и цены"]:
            if что not in т:
                плохо(f"{н} в листе заключения нет раздела «{что}»")
        if т.find("Пропущенные правки") > т.find("Ручные позиции и цены") or т.find("Ручные позиции и цены") > т.find("Особенности расчёта"):
            плохо(f"{н} порядок разделов: пропущенные правки, ручные позиции, особенности")
        пр = {п["т"]: п["что"] for п in (р["пропущено"] or [])}
        if set(пр) != {"Поменяйте цвет кровли на графит", "Добавьте второй вход в парную"}:
            плохо(f"{н} пропущенные правки: {р['пропущено']}")
        else:
            if "не менялся" not in пр["Поменяйте цвет кровли на графит"] or "убрана" not in пр["Добавьте второй вход в парную"]:
                плохо(f"{н} пропущенные правки названы неверно: {пр}")
        ру = {х["т"]: х for х in (р["ручные"] or [])}
        с = ру.get("Проба: своя позиция")
        if not с or с["ц"] != 45000 or "своя позиция" not in с["что"]:
            плохо(f"{н} своя позиция в ручных: {с}")
        if not р["без"] or not р["кар"]:
            плохо(f"{н} не нашлось опции без цены или с ценой в таблице для пробы: {р['без']!r}, {р['кар']!r}")
        else:
            б = ру.get(р["без"])
            if not б or б["ц"] != 12345 or "вписана руками" not in б["что"]:
                плохо(f"{н} сумма, вписанная в опцию без цены, в ручных: {б}")
            к = ру.get(р["кар"])
            if not к or "в таблице проекта" not in к["что"] or not к["ц"]:
                плохо(f"{н} цена, поправленная карандашом, в ручных: {к}")
        # Формул с маржой в заглушке каталога может не быть — тогда эта
        # ветка проверяется только там, где формула есть.
        if р["ф"]:
            ф = ру.get(р["ф"])
            if not ф or "маржа" not in ф["что"] or not ф["ц"]:
                плохо(f"{н} формула со сменённой маржой в ручных: {ф}")
        if "Своя позиция Проба" in т:
            плохо(f"{н} своя позиция осталась и в «Особенностях расчёта»")
        if "не загрузился" not in р["безЖурнала"]:
            плохо(f"{н} без журнала пресета лист молчит о непроверенных правках")

    # ── согласование вторым местом: заключение уходит в чат само ──
    стр.evaluate("() => { window.__ТАБЛИЦЫ.preset_approvals.forEach(с => { с.price_by = 'u-ред'; с.price_name = 'Ольга Проверкина'; с.price_at = new Date().toISOString(); с.price_print = с.sent_print; }); _согласование.когда = 0; }")
    па.роль(стр, "specialist")
    стр.evaluate("() => загрузитьСогласование && загрузитьСогласование(true)") if стр.evaluate("() => typeof загрузитьСогласование === 'function'") else None
    стр.wait_for_timeout(500)
    стр.evaluate("() => решитьСогласование('approved', 'check')")
    for _ in range(60):
        стр.wait_for_timeout(500)
        if стр.evaluate("() => window.__PDF.length && window.__ТАБЛИЦЫ.preset_messages.some(с => (с.attachments || []).some(в => /\\.pdf$/.test(в.name || '')))"):
            break
    сост = стр.evaluate("() => ({ согл: (согласованиеПресета() || {}).state, pdf: window.__PDF.map(п => ({ путь: п.путь, имя: п.имя })), "
                        "сообщ: window.__ТАБЛИЦЫ.preset_messages.filter(с => (с.attachments || []).length).map(с => ({ т: с.body, в: с.attachments.map(в => в.name) })), "
                        "тосты: window.__тосты.slice(-4) })")
    if сост["согл"] != "approved":
        плохо(f"{н} расчёт не согласован вторым местом: {сост}")
    if not сост["pdf"] or not сост["сообщ"]:
        плохо(f"{н} заключение не ушло в чат: {сост}; {ошибки[:3]}")
    else:
        if not re.match(rf"^{код}/.+\.pdf$", сост["pdf"][0]["путь"]) or not сост["pdf"][0]["имя"].startswith(f"Заключение_{код}_"):
            плохо(f"{н} путь или имя файла заключения: {сост['pdf'][0]}")
        if полный:
            данные = base64.b64decode(стр.evaluate("() => window.__PDF[0].данные"))
            картинки, инфо = страницыPdf(данные, н)
            if "595.28 x 841.89" not in инфо and "595 x 842" not in инфо:
                плохо(f"{н} заключение не A4: {инфо!r}")
            if not картинки:
                плохо(f"{н} в PDF заключения нет страниц")
            from PIL import Image
            for и, к in enumerate(картинки):
                кадр = Image.open(к).convert("L")
                тёмных = sum(1 for p in кадр.getdata() if p < 160) / (кадр.width * кадр.height)
                if тёмных < 0.01:
                    плохо(f"{н} страница {и + 1} заключения пустая ({тёмных:.3%})")
                (СНИМКИ / f"approval-report-p{и + 1}.png").write_bytes(к.read_bytes())
            # Крупный снимок первой страницы — для чтения глазами.
            ф = pathlib.Path(tempfile.mkdtemp(prefix="zk-big-")) / "z.pdf"; ф.write_bytes(данные)
            subprocess.run(["pdftoppm", "-r", "110", "-png", "-f", "1", "-l", "2", str(ф), str(СНИМКИ / "approval-report-big")], check=True)

    # ── «Подписан» ──
    па.роль(стр, "manager")
    па.открытьПроверку(стр)
    кн = стр.evaluate("() => [...document.querySelectorAll('#presetChipCard .pc-ap-blk .pc-row button')].map(б => б.getAttribute('data-act'))")
    if "ap-sign" not in кн or "ap-report" not in кн:
        плохо(f"{н} после согласования нет «Подписан» и «Заключение в чат»: {кн}")
    па.вёрстка(стр, н, "«Согласовано» с «Подписан»")
    стр.mouse.move(5, 5)
    стр.screenshot(path=str(СНИМКИ / f"approval-sign-before-{ш}.png"))
    if "ap-sign" in кн:
        па.нажать(стр, "ap-sign"); стр.wait_for_timeout(900)
        с = стр.evaluate("""(код) => { const б = document.querySelector('#presetChipCard .pc-ap-blk');
          return { вызов: window.__ВЫЗОВЫ.filter(х => х[0] === 'sign').map(х => х[1]), плашки: [...б.querySelectorAll('.pc-st')].map(х => х.innerText.replace(/\\s+/g, ' ').trim()),
            кнопки: [...б.querySelectorAll('.pc-row button')].map(х => х.getAttribute('data-act')),
            журнал: (window.__ТАБЛИЦЫ.events || []).some(е => е.event_type === 'approval_signed'), тосты: window.__тосты.slice(-3) }; }""", код)
        if с["вызов"] != [{"p_code": код}]:
            плохо(f"{н} preset_approval_sign: {с['вызов']}")
        if not any("Договор подписан" in п for п in с["плашки"]) or "ap-sign" in с["кнопки"]:
            плохо(f"{н} после «Подписан»: {с}")
        if not с["журнал"]:
            плохо(f"{н} отметка «Подписан» не записана в журнал действий")
        па.вёрстка(стр, н, "«Договор подписан»")
        стр.mouse.move(5, 5)
        стр.screenshot(path=str(СНИМКИ / f"approval-sign-after-{ш}.png"))

        # Колокольчик и резюме — автору.
        у = стр.evaluate("""async (код) => {
          const ш = []; await уведомленияСогласования(ш);
          return { пункты: ш.map(х => ({ т: String(х.текст || '').replace(/<[^>]+>/g, ''), резюме: !!х.резюме, код: х.код })), начало: началоРезюме(код) }; }""", код)
        if not any(п["резюме"] and п["код"] == код and "напишите резюме" in п["т"] for п in у["пункты"]):
            плохо(f"{н} в колокольчике автора нет строки о резюме: {у['пункты']}")
        стр.evaluate("(код) => открытьРезюме(код)", код); стр.wait_for_timeout(2600)
        поле = стр.evaluate("() => { const п = document.getElementById('pcChatText'); return п ? п.value : null; }")
        if not поле or not поле.startswith(у["начало"]) or "код " not in у["начало"]:
            плохо(f"{н} поле чата после «Написать резюме»: {поле!r}, ждали «{у['начало']}»")
        лента = стр.evaluate("() => [...document.querySelectorAll('#presetChipCard .pc-chev-ap')].map(х => х.innerText.replace(/\\s+/g, ' ').trim())")
        if not any("Договор подписан" in л for л in лента):
            плохо(f"{н} в чате нет строки «Договор подписан»: {лента}")
        вспл = стр.evaluate("() => [...document.querySelectorAll('body *')].filter(х => х.children.length === 0 && /код\\s\\d{3}/.test(х.textContent)).map(х => х.textContent)")
        if any(re.search(r"код \d{3} \d{3}", в) for в in вспл):
            плохо(f"{н} код пресета во всплывающем окне может переломиться посередине: {вспл[:3]}")
        стр.mouse.move(5, 5)
        стр.screenshot(path=str(СНИМКИ / f"approval-resume-{ш}.png"))
    if ошибки:
        плохо(f"{н} ошибки страницы: {ошибки[:3]}")
    стр.close()


def главная():
    if not JSPDF.exists() or not H2C.exists():
        print(f"нет библиотек PDF в {ЛИБЫ}: распакуйте jspdf 2.5.1 и html2canvas 1.4.1 из npm"); sys.exit(2)
    с, порт = м.сервер()
    try:
        with sync_playwright() as п:
            бр = п.chromium.launch(executable_path=м.хром())
            try:
                прогон(бр, порт, 1440, 900, True)
                прогон(бр, порт, 390, 844, False)
            finally:
                бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for т in НАХОДКИ:
            print(" —", т)
        sys.exit(1)
    print("Чисто: заключение — пропуски проверки, правки договора «было — стало», оба места согласования, тон «Зелёный-графит»; "
          "уходит в чат PDF-вложением A4 само при согласовании; «Подписан» только после согласования, зовёт базу с кодом, "
          "плашка и журнал; автору — строка о резюме и поле чата, начатое с кодом; вёрстка на 390 и 1440.")


if __name__ == "__main__":
    главная()
