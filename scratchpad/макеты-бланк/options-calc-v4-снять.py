#!/usr/bin/env python3
# Кадры макета options-calc-v4: настоящий калькулятор на учебных данных проб и
# калькулятор опций, вставленный поверх, — четыре места без правой панели
# (справа на широком экране — панель «Спецификация» с итогами).
# python3 options-calc-v4-снять.py <папка>
import pathlib, sys
sys.path.insert(0, '/home/user/-calculator-test/scratchpad/probes')
from playwright.sync_api import sync_playwright
import check_preset_chip as м
ШРИФТЫ = pathlib.Path('/home/user/-calculator-test/scratchpad/probes/шрифты_google.css').read_text()
ВЫХОД = pathlib.Path(sys.argv[1]); ВЫХОД.mkdir(parents=True, exist_ok=True)

СТИЛЬ = r"""
.oc *{box-sizing:border-box}
.oc{font-family:'Geologica',sans-serif;color:#1e201c;font-variant-numeric:tabular-nums}
.oc .k{font-size:.58rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#9a9c97}
.oc .h{font-family:'Unbounded',sans-serif;font-weight:600;font-size:.95rem}
.oc .seg{display:inline-flex;gap:14px;border-bottom:1px solid #e3e4e3}
.oc .seg span{white-space:nowrap;height:30px;display:flex;align-items:center;font-size:.74rem;color:#6e726b;border-bottom:2px solid transparent;margin-bottom:-1px}
.oc .seg span.on{color:#1e201c;font-weight:600;border-bottom-color:#70ad34}
.oc .srch{display:flex;align-items:center;gap:8px;height:38px;border-bottom:1px solid #cacfc4;color:#9a9c97;font-size:.8rem}
.oc .cs{margin-top:14px}
.oc .csh{display:flex;align-items:baseline;gap:8px;padding-bottom:5px;border-bottom:2px solid #70ad34;font-family:'Unbounded',sans-serif;font-weight:600;font-size:.72rem}
.oc .csh span{margin-left:auto;font-family:'Geologica',sans-serif;font-weight:400;font-size:.66rem;color:#9a9c97}
.oc .co{display:flex;align-items:center;gap:10px;min-height:44px;padding:5px 0;border-bottom:1px solid #e3e4e3}
.oc .co b{font-weight:400;flex:1;font-size:.78rem}
.oc .co small{display:block;font-size:.64rem;color:#9a9c97}
.oc .pl{width:28px;height:28px;border-radius:7px;border:1px solid #cacfc4;display:flex;align-items:center;justify-content:center;color:#4f7d26;font-weight:600;flex:none}
.oc .pl.on{background:#70ad34;border-color:#70ad34;color:#fff}
.oc .ln{display:grid;grid-template-columns:minmax(0,1fr) 92px 60px 104px;gap:10px;align-items:end;padding:9px 0;border-bottom:1px solid #e3e4e3}
.oc .ln .n{font-size:.78rem;line-height:1.35}
.oc .ln .n small{display:block;font-size:.62rem;color:#9a9c97}
.oc .ln i{font-style:normal;display:block;text-align:right;border-bottom:1px solid #cacfc4;height:28px;line-height:28px;font-size:.78rem}
.oc .ln i u{text-decoration:none;color:#9a9c97;font-size:.64rem;margin-left:4px}
.oc .ln .p{text-align:right;font-weight:600;font-size:.82rem;padding-bottom:5px}
.oc .lh{display:grid;grid-template-columns:minmax(0,1fr) 92px 60px 104px;gap:10px;font-size:.56rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#9a9c97;padding-bottom:4px;border-bottom:2px solid #70ad34}
.oc .lh span:not(:first-child){text-align:right}
.oc .any{display:flex;align-items:center;gap:8px;height:40px;font-size:.76rem;color:#4f7d26;font-weight:600}
.oc .tt{display:flex;justify-content:space-between;align-items:baseline;padding-top:10px;border-top:2px solid #70ad34}
.oc .tt span{font-size:.6rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#6e726b}
.oc .tt b{font-family:'Unbounded',sans-serif;font-size:1rem}
.oc .ac{display:flex;gap:8px;margin-top:10px}
.oc .ac span{flex:1;height:36px;display:flex;align-items:center;justify-content:center;border-radius:8px;border:1px solid #cacfc4;font-size:.74rem;font-weight:600}
.oc .ac span.p{background:#6daa34;border-color:#6daa34;color:#fff}
.oc .x{width:32px;height:32px;display:flex;align-items:center;justify-content:center;color:#9a9c97;flex:none}
.oc .two{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:0}
.oc .two > div{padding:0 22px}.oc .two > div:first-child{padding-left:0;border-right:1px solid #e3e4e3}.oc .two > div:last-child{padding-right:0}
.oc .src{font-size:.58rem;font-weight:600;padding:1px 7px;border-radius:20px;background:#edf5e5;color:#4f7d26;white-space:nowrap}
.ring{box-shadow:0 0 0 3px #70ad34 !important;border-radius:8px}
/* Г1 вкладки */
#ocTabs{display:flex;gap:22px;margin:22px 0 0;border-bottom:1px solid #e3e4e3}
#ocTabs span{height:40px;display:flex;align-items:center;font-family:'Unbounded',sans-serif;font-weight:600;font-size:.86rem;color:#9a9c97;border-bottom:2px solid transparent;margin-bottom:-1px}
#ocTabs span.on{color:#1e201c;border-bottom-color:#70ad34}
#ocView{margin-top:18px}
/* Г2 окно */
#ocDim{position:fixed;inset:0;background:rgba(20,21,19,.36);z-index:8999}
#ocWin{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:min(1080px,calc(100vw - 48px));height:min(760px,calc(100vh - 48px));background:#fff;border-radius:14px;box-shadow:0 18px 50px rgba(0,0,0,.25);z-index:9000;display:flex;flex-direction:column;overflow:hidden}
#ocWin .top,#ocSheet .top,#ocLeft .top{display:flex;align-items:center;gap:14px;padding:14px 18px 10px;border-bottom:1px solid #e3e4e3}
#ocWin .body{flex:1;overflow:hidden;padding:12px 18px}
#ocWin .foot,#ocSheet .foot,#ocLeft .foot{padding:10px 18px 14px}
/* Г3 лист снизу */
#ocSheet{position:fixed;left:50%;transform:translateX(-50%);bottom:0;width:min(1000px,100vw);height:64vh;background:#fff;border-radius:14px 14px 0 0;box-shadow:0 -10px 40px rgba(0,0,0,.22);z-index:9000;display:flex;flex-direction:column}
#ocSheet .grip{width:44px;height:5px;border-radius:3px;background:#cacfc4;margin:8px auto 0}
#ocSheet .body{flex:1;overflow:hidden;padding:10px 18px}
/* Г4 слева */
#ocLeft{position:fixed;top:68px;bottom:24px;left:24px;width:410px;background:#fff;border:1px solid #e3e4e3;border-radius:14px;box-shadow:0 8px 28px rgba(30,40,20,.10);z-index:900;display:flex;flex-direction:column}
#ocLeft .body{flex:1;overflow:hidden;padding:4px 18px}
#ocLeft .ln{grid-template-columns:minmax(0,1fr) 70px 86px}
#ocLeft .ln .m{display:none}
@media (max-width:700px){
  .oc .ln,.oc .lh{grid-template-columns:minmax(0,1fr) 64px 92px;gap:8px}
  .oc .ln .p{white-space:nowrap}
  #ocWin .top .prj{display:none}
  #ocWin .top,#ocSheet .top{flex-wrap:wrap;row-gap:4px}
  #ocWin .top,#ocSheet .top{position:relative;padding-right:52px}
  #ocWin .top .x,#ocSheet .top .x{position:absolute;right:10px;top:12px;margin:0}
  .oc .ac{flex-wrap:wrap}.oc .ac span{flex:1 1 40%}
  .oc .two{grid-template-columns:1fr}.oc .two > div{padding:0!important;border:0!important}
  #ocWin{width:100vw;height:100vh;border-radius:0}
  #ocSheet{height:86vh}
}
"""

ВСТАВКА = r"""([вар, ш]) => {
  const ст = document.createElement('style'); ст.textContent = СТИЛЬ_; document.head.appendChild(ст);
  const п = (typeof selectedProject !== 'undefined' && selectedProject) || null;
  const пл = { fasad: 72, warm: п ? +п[PROJ_IDX.WARM] || 30 : 30, roof: 60 };
  const О = [['Тёплый пол электрический', 'Полы', 'warm', 2000, 30, 1, 0], ['Планкен из сосны АБ', 'Фасад', 'fasad', 300, 30, 1.05, 10000],
             ['Замена профлиста на фальц', 'Кровля', 'roof', 1000, 25, 1.05, 0], ['Панно из гималайской соли', 'Парная', 'qty', 40000, 30, 1, 0]];
  const ед = { warm: 'м²', fasad: 'м²', roof: 'м²', qty: 'шт.' };
  const руб = в => Math.round(в).toLocaleString('ru-RU').replace(/,/g, ' ') + ' ₽';
  let итог = 0;
  const лист = (узко) => '<div class="lh"><span>Опция</span><span>Кол-во</span>' + (узко ? '' : '<span class="m">Маржа</span>') + '<span>Цена</span></div>' + О.map(о => {
    const [и, р, осн, ст, м, з, н] = о; const к = осн === 'qty' ? 1 : пл[осн]; const ц = (к * ст * з + н) / (1 - м / 100); итог += ц;
    return '<div class="ln"><div class="n">' + и + '<small>' + р + '</small></div><i>' + к + '<u>' + ед[осн] + '</u></i>' + (узко ? '' : '<i class="m">' + м + '<u>%</u></i>') + '<div class="p">' + руб(ц) + '</div></div>'; }).join('')
    + '<div class="any">+ Любая опция — от себестоимости</div>';
  const кат = () => '<div class="srch">⌕&nbsp; Найти опцию</div>' + [['Парная', [['Панно из гималайской соли', '57 143 ₽ за шт.', 1], ['Второе дыхание', '28 571 ₽ за шт.', 0]]],
     ['Полы и терраса', [['Тёплый пол электрический', '2 857 ₽ за м²', 1], ['Стяжка пола', '1 538 ₽ за м²', 0]]],
     ['Кровля', [['Замена профлиста на фальц', '1 500 ₽ за м²', 1], ['Снегозадержатели', '2 143 ₽ за п. м', 0]]],
     ['Фасад', [['Планкен из сосны АБ', '450 ₽ за м²', 1], ['Белтермо 35 мм', '1 428 ₽ за м²', 0]]]]
    .map(([р, оп]) => '<div class="cs"><div class="csh">' + р + '<span>' + оп.length + '</span></div>' + оп.map(([и, ц, on]) => '<div class="co"><b>' + и + '<small>' + ц + '</small></b><span class="pl' + (on ? ' on' : '') + '">' + (on ? '✓' : '+') + '</span></div>').join('') + '</div>').join('');
  const сег = '<span class="seg"><span class="on">Каркас</span><span>Клеёный брус</span></span>';
  const подвал = (на) => '<div class="tt"><span>Итого опции</span><b>' + руб(итог) + '</b></div><div class="ac"><span class="p">Скопировать</span><span>Excel</span><span>PDF</span>' + (на ? '<span>В расчёт</span>' : '') + '</div>';
  const узкий = ш < 700;
  // кнопка «Опции» в шапке — у всех вариантов, кроме вкладок
  const кноп = () => { const ряд = document.getElementById('headerBtns'); const ком = document.getElementById('komplBtn');
    const к = document.createElement('button'); к.className = 'btn-hide-global btn-icon ring'; к.title = 'Калькулятор опций';
    к.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 11h2M14 11h2M8 15h2M14 15h2M8 19h2M14 19h2"/></svg>';
    (ком ? ком.parentNode : ряд).insertBefore(к, ком ? ком.nextSibling : null); };

  if (вар === 'tabs' || вар === 'page') {
    const ш_ = document.querySelector('.page-wrap');
    ['.two-col', '#imageCanvasCard', '#resultCard', '#breakdownCard', '#optionSections'].forEach(с => { const э = document.querySelector(с); if (э) э.style.display = 'none'; });
    const шапка = document.querySelector('.header');
    if (вар === 'page') {
      // отдельная ссылка: тот же лист, но вместо «Спецификация» — «Калькулятор опций», без кнопок расчёта
      const з = шапка.querySelector('h1, .title, .main-title');
      шапка.querySelectorAll('*').forEach(э => { if (э.children.length === 0 && /Спецификация/.test(э.textContent)) э.textContent = 'Калькулятор опций'; if (э.children.length === 0 && /Каркасный дом/.test(э.textContent)) э.textContent = 'для клиентского отдела'; if (э.children.length === 0 && /РАСЧЁТ СТОИМОСТИ|Расчёт стоимости/i.test(э.textContent)) э.textContent = 'Опции к проданным баням'; });
      const h1 = шапка.querySelector('h1'); if (h1) h1.innerHTML = 'Калькулятор опций<br><em>для клиентского отдела</em>';
      ['presetChipCard', 'presetChip', 'totalStrip'].forEach(и => { const э = document.getElementById(и); if (э) э.style.display = 'none'; });
      const ряд = document.getElementById('headerBtns'); if (ряд) [...ряд.children].forEach((к, и) => { if (и > 1) к.style.display = 'none'; });
    }
    const таб = document.createElement('div'); таб.className = 'oc'; таб.id = 'ocTabs';
    таб.innerHTML = вар === 'tabs' ? '<span>Спецификация</span><span class="on">Калькулятор опций</span>' : '';
    if (вар === 'tabs') шапка.after(таб);
    const вид = document.createElement('div'); вид.className = 'oc'; вид.id = 'ocView';
    вид.innerHTML = '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px;margin-bottom:8px">' + сег + (п && вар === 'tabs' ? '<span style="font-size:.72rem;color:#6e726b">Площади — из проекта <b style="color:#1e201c">' + п[0] + '</b></span>' : '') + '</div>'
      + (узкий ? лист(true) + '<div style="margin-top:14px">' + кат() + '</div>' : '<div class="two"><div>' + кат() + '</div><div>' + лист(false) + '</div></div>');
    (вар === 'tabs' ? таб : шапка).after(вид);
    const тл = document.getElementById('tsLab'), тв = document.getElementById('tsVal'), тс = document.getElementById('tsSub');
    if (тл) тл.textContent = 'Опции · 4 позиции'; if (тв) тв.textContent = руб(итог); if (тс) тс.textContent = 'Скопировать · Excel · PDF';
    const бок = document.getElementById('sideNavInner');
    if (бок && вар === 'tabs') {
      // правая панель остаётся на месте и показывает итог опций, а не разделы спецификации
      бок.innerHTML = '<div class="oc" id="ocSide" style="padding:18px 16px 14px">'
        + '<div class="k" style="color:#4f7d26">Калькулятор опций</div>'
        + '<div style="font-size:.78rem;margin-top:4px">' + (п ? п[0] : '') + '</div>'
        + '<div style="font-family:Unbounded,sans-serif;font-weight:600;font-size:1.15rem;margin-top:6px">' + руб(итог) + '</div>'
        + '<div style="font-size:.66rem;color:#9a9c97;margin-top:2px">4 позиции · маржа по каждой своя</div>'
        + '<div style="margin-top:12px;border-top:2px solid #70ad34">' + О.map(о => { const к = о[2] === 'qty' ? 1 : пл[о[2]]; const ц = (к * о[3] * о[5] + о[6]) / (1 - о[4] / 100);
            return '<div style="display:flex;gap:8px;justify-content:space-between;padding:8px 0;border-bottom:1px solid #e3e4e3;font-size:.72rem"><span>' + о[0] + '</span><b style="font-weight:600;white-space:nowrap">' + руб(ц) + '</b></div>'; }).join('') + '</div>'
        + '<div class="ac" style="flex-wrap:wrap"><span class="p" style="flex-basis:100%">Скопировать</span><span>Excel</span><span>PDF</span></div>'
        + '<div style="margin-top:14px;font-size:.68rem;color:#6e726b">Спецификация проекта — <b style="color:#1e201c">3 200 000 ₽</b> · вкладка «Спецификация»</div></div>';
    }
    if (бок && вар === 'page') бок.style.display = 'none';
    window.scrollTo(0, 0);
    return;
  }
  кноп();
  { const ts = document.getElementById('totalStrip'); if (ts) ts.style.display = 'none'; }
  if (вар === 'win') {
    const т = document.createElement('div'); т.id = 'ocDim'; document.body.appendChild(т);
    const о = document.createElement('div'); о.id = 'ocWin'; о.className = 'oc';
    о.innerHTML = '<div class="top"><div><div class="k">Опции</div><div class="h">Калькулятор опций</div></div>' + сег + '<span class="prj" style="margin-left:auto;font-size:.72rem;color:#6e726b">' + (п ? 'Площади из проекта · ' + п[0] : '') + '</span><span class="x">✕</span></div>'
      + '<div class="body">' + (узкий ? лист(true) + кат() : '<div class="two" style="height:100%"><div>' + кат() + '</div><div>' + лист(false) + '</div></div>') + '</div><div class="foot">' + подвал(true) + '</div>';
    document.body.appendChild(о); return;
  }
  if (вар === 'sheet') {
    const т = document.createElement('div'); т.id = 'ocDim'; т.style.background = 'rgba(20,21,19,.22)'; document.body.appendChild(т);
    const о = document.createElement('div'); о.id = 'ocSheet'; о.className = 'oc';
    о.innerHTML = '<div class="grip"></div><div class="top"><div><div class="k">Опции</div><div class="h">Калькулятор опций</div></div>' + сег + '<span class="x" style="margin-left:auto">✕</span></div>'
      + '<div class="body">' + (узкий ? лист(true) : '<div class="two"><div>' + кат() + '</div><div>' + лист(false) + '</div></div>') + '</div><div class="foot">' + подвал(true) + '</div>';
    document.body.appendChild(о); return;
  }
  if (вар === 'left') {
    if (ш < 1600) { const т = document.createElement('div'); т.id = 'ocDim'; document.body.appendChild(т); }
    const о = document.createElement('div'); о.id = 'ocLeft'; о.className = 'oc'; if (ш < 1600) о.style.zIndex = 9000;
    о.innerHTML = '<div class="top"><div><div class="k">Опции</div><div class="h">Калькулятор опций</div></div><span class="x" style="margin-left:auto">✕</span></div>'
      + '<div style="padding:8px 18px 0">' + сег + '</div><div class="body">' + лист(true) + кат() + '</div><div class="foot">' + подвал(false) + '</div>';
    document.body.appendChild(о); return;
  }
}""".replace('СТИЛЬ_', __import__('json').dumps(СТИЛЬ))

КАДРЫ = [('tabs', 1920, 1080), ('tabs', 1440, 900), ('tabs', 390, 844), ('page', 1440, 900), ('page', 390, 844),
         ('win', 1920, 1080), ('win', 1440, 900), ('win', 390, 844), ('sheet', 1440, 900), ('sheet', 390, 844),
         ('left', 1920, 1080), ('left', 1440, 900)]
with sync_playwright() as p:
    бр = p.chromium.launch(executable_path=м.хром())
    с, порт = м.сервер()
    for вар, ш, в in КАДРЫ:
        стр = бр.new_page(viewport={'width': ш, 'height': в}, device_scale_factor=2, locale='ru-RU')
        стр.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=ШРИФТЫ))
        стр.route('**/fonts.gstatic.com/**', lambda r: r.abort())
        ош = []; стр.on('pageerror', lambda e: ош.append(str(e)))
        стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
        стр.goto(f'http://127.0.0.1:{порт}/index.html', wait_until='load'); стр.wait_for_timeout(2500)
        стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
        стр.evaluate("async () => { selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); window.scrollTo(0, 0); }")
        if вар in ('win', 'sheet', 'left'):
            стр.evaluate("window.scrollTo(0, 1400)"); стр.wait_for_timeout(300)
        стр.evaluate(ВСТАВКА, [вар, ш]); стр.wait_for_timeout(500)
        стр.mouse.move(2, 2)
        стр.screenshot(path=str(ВЫХОД / f'{вар}-{ш}.png'))
        print(вар, ш, 'ошибки:', ош[:2]); стр.close()
    с.shutdown(); бр.close()
