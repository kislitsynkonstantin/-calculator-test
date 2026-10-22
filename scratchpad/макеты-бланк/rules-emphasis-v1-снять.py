#!/usr/bin/env python3
# Кадры макета rules-emphasis-v1: настоящие правила эксплуатации бруса с
# парной, пункты 3.1 и 4.1 (сейчас целиком полужирные) в четырёх оформлениях.
# python3 rules-emphasis-v1-снять.py <папка>
import json, pathlib, sys
sys.path.insert(0, '/home/user/-calculator-test/scratchpad/probes')
import check_glulam_sections as г, check_preset_chip as м, check_glulam_contracts as кд
from playwright.sync_api import sync_playwright
ШРИФТЫ = pathlib.Path('/home/user/-calculator-test/scratchpad/probes/шрифты_google.css').read_text()
ВЫХОД = pathlib.Path(sys.argv[1]); ВЫХОД.mkdir(parents=True, exist_ok=True)

# Слова, которые остаются полужирными, — суть пункта и следствие.
КЛЮЧ = {
  '3.1': ['Нарушения из этого раздела повреждают', 'гарантией не покрываются'],
  '4.1': ['Печь и бак — на гарантии производителя', 'гарантия Подрядчика на установку печи и дымохода не действует', 'гарантией не покрываются'],
}

ОБЩЕЕ = r"""
p.clause.imp b{font-weight:inherit}
p.clause.imp .k{font-weight:600}
"""
ВАРИАНТЫ = {
  'now': '',
  # А — плашка: бледная заливка акцентом и волосяная рамка по кругу.
  'a': ОБЩЕЕ + r"""
p.clause.imp{background:color-mix(in srgb,var(--bl-acc) 8%,var(--bl-sheet,#fff));border:1px solid color-mix(in srgb,var(--bl-acc) 35%,var(--bl-sheet,#fff));
  border-radius:8px;padding:8px 12px 8px calc(2.9em + 12px);margin:.15em 0 .9em}
""",
  # Б — пометка «Важно» в начале пункта и линейка под ним.
  'b': ОБЩЕЕ + r"""
p.clause.imp{border-bottom:1px solid var(--bl-rule2);padding-bottom:.55em;margin-bottom:.8em}
p.clause.imp .imp-tag{display:inline-block;text-indent:0;margin-right:.5em;padding:.05em .55em;border-radius:20px;vertical-align:.08em;
  font-family:'Unbounded',sans-serif;font-weight:600;font-size:.62em;letter-spacing:.12em;text-transform:uppercase;
  color:var(--bl-small,var(--bl-acc));background:color-mix(in srgb,var(--bl-acc) 12%,var(--bl-sheet,#fff))}
""",
  # В — знак предупреждения перед текстом, полужирное только у сути.
  'c': ОБЩЕЕ + r"""
p.clause.imp .warn-i{display:inline-block;width:1.05em;height:1.05em;vertical-align:-.17em;margin-right:.35em;color:var(--bl-acc)}
""",
}
ЗНАК = '<svg class="warn-i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>'

ПРАВКА = r"""([вар, ключ, знак]) => {
  document.querySelectorAll('p.clause').forEach(p => {
    const н = (p.querySelector('.clause-num') || {}).textContent || '';
    const k = н.replace(/\.$/, '').trim();
    const b = p.querySelector(':scope > b');
    if (!b || !ключ[k]) return;
    p.classList.add('imp');
    if (вар === 'now') return;
    let html = b.innerHTML;
    ключ[k].forEach(ф => { html = html.replace(ф, '<span class="k">' + ф + '</span>'); });
    b.innerHTML = (вар === 'c' ? знак : вар === 'b' ? '<span class="imp-tag">Важно</span>' : '') + html;
  });
}"""

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=м.хром())
    с, порт = м.сервер()
    стр = бр.new_page()
    стр.add_init_script(г.ЗАГЛУШКА)
    стр.add_init_script("window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {}; Object.assign(window.__ТАБЛИЦЫ, " + json.dumps(кд.таблицы(), ensure_ascii=False) + ");")
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    кд.открыть(стр, 'glulam')
    html = стр.evaluate("() => сПалитрой(buildRulesHtml(getContractVarsKar(естьДоговор(2) ? 2 : 1)))")
    for вар, css in ВАРИАНТЫ.items():
        п = бр.new_page(viewport={'width': 1000, 'height': 1400}, device_scale_factor=2)
        п.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=ШРИФТЫ))
        п.route('**/fonts.gstatic.com/**', lambda r: r.abort())
        п.set_content(html, wait_until='load'); п.wait_for_timeout(600)
        п.evaluate(ПРАВКА, [вар, КЛЮЧ, ЗНАК])
        п.add_style_tag(content=css + '\n.page{box-shadow:none!important}')
        п.wait_for_timeout(200)
        for раздел, до in (('3', '3.2'), ('4', '4.3')):
            рамка = п.evaluate("""([р, до]) => {
              const h = [...document.querySelectorAll('h2.section')].find(x => (x.querySelector('.num') || {}).textContent === р + '.');
              const к = [...document.querySelectorAll('p.clause')].find(x => ((x.querySelector('.clause-num') || {}).textContent || '').trim() === до + '.');
              const лист = document.querySelector('.page').getBoundingClientRect();
              const а = h.getBoundingClientRect(), б = к.getBoundingClientRect();
              return { x: лист.left + 30, y: а.top + scrollY - 14, width: лист.width - 60, height: б.bottom - а.top + 22 }; }""", [раздел, до])
            п.screenshot(path=str(ВЫХОД / f'{вар}-{раздел}.png'), clip=рамка, full_page=True)
        п.close()
        print(вар)
    с.shutdown(); бр.close()
