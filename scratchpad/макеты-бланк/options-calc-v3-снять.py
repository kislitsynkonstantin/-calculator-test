#!/usr/bin/env python3
# Кадры для макета options-calc-v3: настоящий калькулятор на учебных данных
# (заглушка базы проб) + кнопка «Опции» в шапке и панель, вставленные поверх.
# Калькулятор не меняется — вставка живёт только в странице пробы.
import json, pathlib, sys
sys.path.insert(0, '/home/user/-calculator-test/scratchpad/probes')
from playwright.sync_api import sync_playwright
import check_preset_chip as м
ШРИФТЫ = pathlib.Path('/home/user/-calculator-test/scratchpad/probes/шрифты_google.css').read_text()
ВЫХОД = pathlib.Path(sys.argv[1]); ВЫХОД.mkdir(parents=True, exist_ok=True)

СТИЛЬ = r"""
#ocBtn{position:relative}
#ocBtn.ring{box-shadow:0 0 0 3px #70ad34}
#ocPanel{position:fixed;top:0;right:0;bottom:0;width:min(460px,100vw);z-index:9000;background:#fff;border-left:1px solid #e3e4e3;
  box-shadow:-12px 0 34px rgba(30,32,28,.16);display:flex;flex-direction:column;font-family:'Geologica',sans-serif;color:#1e201c;font-variant-numeric:tabular-nums}
body.dark #ocPanel{background:#1d1f1c;color:#edefea;border-color:#353f2d}
#ocPanel .t{display:flex;align-items:flex-start;gap:10px;padding:16px 18px 0}
#ocPanel .k{font-size:.58rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#9a9c97}
#ocPanel .n{font-family:'Unbounded',sans-serif;font-weight:600;font-size:.95rem;margin-top:2px}
#ocPanel .x{margin-left:auto;width:32px;height:32px;display:flex;align-items:center;justify-content:center;color:#9a9c97}
#ocPanel .seg{display:flex;gap:16px;margin:10px 18px 0;border-bottom:1px solid #e3e4e3}
#ocPanel .seg span{height:32px;display:flex;align-items:center;font-size:.76rem;color:#6e726b;border-bottom:2px solid transparent;margin-bottom:-1px}
#ocPanel .seg span.on{color:#1e201c;font-weight:600;border-bottom-color:#70ad34}
#ocPanel .prj{display:flex;align-items:center;gap:8px;padding:10px 18px;font-size:.74rem;color:#6e726b;border-bottom:1px solid #e3e4e3;flex-wrap:wrap}
#ocPanel .prj b{color:#1e201c}
#ocPanel .sw{display:inline-flex;margin-left:auto;border:1px solid #cacfc4;border-radius:8px;overflow:hidden}
#ocPanel .sw span{height:28px;padding:0 10px;display:flex;align-items:center;font-size:.68rem;color:#6e726b}
#ocPanel .sw span.on{background:#24271f;color:#fff}
#ocPanel .body{flex:1;overflow:auto;padding:4px 18px}
#ocPanel .srch{display:flex;align-items:center;gap:8px;height:40px;border-bottom:1px solid #cacfc4;color:#9a9c97;font-size:.8rem;margin-top:6px}
#ocPanel .ln{padding:11px 0;border-bottom:1px solid #e3e4e3}
#ocPanel .lt{display:flex;gap:10px}
#ocPanel .lt div{flex:1;font-size:.8rem;line-height:1.35}
#ocPanel .lt small{display:block;font-size:.64rem;color:#9a9c97}
#ocPanel .lt b{font-size:.84rem;white-space:nowrap}
#ocPanel .lf{display:flex;gap:16px;align-items:flex-end;margin-top:6px}
#ocPanel .f label{display:block;font-size:.58rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#9a9c97}
#ocPanel .f i{display:block;font-style:normal;width:84px;height:30px;line-height:30px;text-align:right;border-bottom:1px solid #cacfc4;font-size:.8rem}
#ocPanel .f.m i{width:56px}
#ocPanel .u{font-size:.66rem;color:#9a9c97;padding-bottom:8px;width:24px}
#ocPanel .src{font-size:.6rem;font-weight:600;padding:1px 8px;border-radius:20px;background:#edf5e5;color:#4f7d26;margin-bottom:8px;white-space:nowrap}
#ocPanel .src.man{background:none;color:#9a9c97;box-shadow:inset 0 0 0 1px #cacfc4}
#ocPanel .add{display:flex;align-items:center;gap:8px;height:40px;margin-top:8px;font-size:.76rem;color:#4f7d26;font-weight:600}
#ocPanel .ft{border-top:2px solid #70ad34;padding:12px 18px 16px}
#ocPanel .tt{display:flex;justify-content:space-between;align-items:baseline}
#ocPanel .tt span{font-size:.6rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#6e726b}
#ocPanel .tt b{font-family:'Unbounded',sans-serif;font-size:1.02rem}
#ocPanel .ac{display:flex;gap:8px;margin-top:12px}
#ocPanel .ac span{flex:1;height:38px;display:flex;align-items:center;justify-content:center;border-radius:8px;border:1px solid #cacfc4;font-size:.76rem;font-weight:600}
#ocPanel .ac span.p{background:#6daa34;border-color:#6daa34;color:#fff}
#ocPanel .lf{flex-wrap:wrap}
@media (max-width:500px){#ocPanel .src{order:9}}
#ocDim{position:fixed;inset:0;background:rgba(20,21,19,.28);z-index:8999}
"""

ВСТАВКА = r"""([безПроекта, телефон]) => {
  const ст = document.createElement('style'); ст.textContent = СТИЛЬ_; document.head.appendChild(ст);
  // кнопка в шапке — рядом с «Комплектациями», тем же классом, что соседи
  const ряд = document.getElementById('headerBtns'); const ком = document.getElementById('komplBtn');
  const к = document.createElement('button'); к.id = 'ocBtn'; к.className = 'btn-hide-global btn-icon ring'; к.title = 'Калькулятор опций';
  к.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 11h2M14 11h2M8 15h2M14 15h2M8 19h2M14 19h2"/></svg>';
  (ком ? ком.parentNode : ряд).insertBefore(к, ком ? ком.nextSibling : null);
  if (телефон === 'шапка') return;
  const п = (typeof selectedProject !== "undefined" && selectedProject) || null;
  const пл = { fasad: п ? +п[PROJ_IDX.FASAD_AREA] || 0 : 0, warm: п ? +п[PROJ_IDX.WARM] || 0 : 0, roof: п ? +п[PROJ_IDX.ROOF_AREA] || 0 : 0 };
  const имя = п ? п[PROJ_IDX.NAME] : '';
  // учебные ставки: [название, раздел, основание, ставка, маржа, запас, надбавка, вписано]
  const О = [['Тёплый пол электрический', 'Полы', 'warm', 2000, 30, 1, 0], ['Планкен из сосны АБ', 'Фасад', 'fasad', 300, 30, 1.05, 10000],
             ['Замена профлиста на фальц', 'Кровля', 'roof', 1000, 25, 1.05, 0], ['Панно из гималайской соли', 'Парная', 'qty', 40000, 30, 1, 0]];
  const руб = в => Math.round(в).toLocaleString('ru-RU').replace(/,/g, ' ') + ' ₽';
  const ед = { warm: 'м²', fasad: 'м²', roof: 'м²', qty: 'шт.' };
  const назв = { warm: 'тёплый контур', fasad: 'фасад', roof: 'кровля' };
  const ручн = { warm: 36, fasad: 60, roof: 50, qty: 1 };
  let итог = 0;
  const строки = О.map(о => { const [и, р, осн, ст, м, з, н] = о; const изП = !безПроекта && осн !== 'qty' && пл[осн] > 0;
    const к = осн === 'qty' ? 1 : (изП ? пл[осн] : ручн[осн]); const ц = (к * ст * з + н) / (1 - м / 100); итог += ц;
    const метка = осн === 'qty' ? '' : (изП ? '<span class="src">из проекта · ' + назв[осн] + '</span>' : '<span class="src man">вписано</span>');
    return '<div class="ln"><div class="lt"><div>' + и + '<small>' + р + '</small></div><b>' + руб(ц) + '</b></div><div class="lf"><div class="f"><label>' + (осн === 'qty' ? 'Количество' : 'Основание') + '</label><i>' + String(к).replace('.', ',') + '</i></div><span class="u">' + ед[осн] + '</span><div class="f m"><label>Маржа, %</label><i>' + м + '</i></div>' + метка + '</div></div>'; }).join('');
  const пан = document.createElement('div'); пан.id = 'ocPanel';
  пан.innerHTML = '<div class="t"><div><div class="k">Опции</div><div class="n">Калькулятор опций</div></div><span class="x">✕</span></div>'
    + '<div class="seg"><span class="on">Каркас</span><span>Клеёный брус</span></div>'
    + '<div class="prj">' + (имя ? 'Проект: <b>' + имя + '</b>' : 'Проект не выбран') + '<span class="sw"><span class="' + (безПроекта ? '' : 'on') + '">С проектом</span><span class="' + (безПроекта ? 'on' : '') + '">Без проекта</span></span></div>'
    + '<div class="body"><div class="srch">⌕&nbsp; Найти опцию в каталоге</div>' + строки + '<div class="add">+ Любая опция — от себестоимости</div></div>'
    + '<div class="ft"><div class="tt"><span>Итого</span><b>' + руб(итог) + '</b></div><div class="ac"><span class="p">Скопировать</span><span>Excel</span><span>PDF</span>' + (безПроекта ? '' : '<span>В пресет</span>') + '</div></div>';
  const тень = document.createElement('div'); тень.id = 'ocDim';
  document.body.appendChild(тень); document.body.appendChild(пан);
}""".replace('СТИЛЬ_', json.dumps(СТИЛЬ))

with sync_playwright() as p:
    бр = p.chromium.launch(executable_path=м.хром())
    с, порт = м.сервер()
    for имя, ш, в, безП, тел in (('desk-proj', 1440, 900, False, ''), ('desk-noproj', 1440, 900, True, ''),
                                 ('phone-head', 390, 844, False, 'шапка'), ('phone-panel', 390, 844, False, '')):
        стр = бр.new_page(viewport={'width': ш, 'height': в}, device_scale_factor=2, locale='ru-RU')
        стр.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=ШРИФТЫ))
        стр.route('**/fonts.gstatic.com/**', lambda r: r.abort())
        ош = []; стр.on('pageerror', lambda e: ош.append(str(e)))
        стр.add_init_script(м.ЗАГЛУШКА); стр.add_init_script(м.ТАБЛИЦЫ_JS)
        стр.goto(f'http://127.0.0.1:{порт}/index.html', wait_until='load'); стр.wait_for_timeout(2500)
        стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; }")
        стр.evaluate("async () => { selectProjectOption(0); await new Promise(r => setTimeout(r, 900)); window.scrollTo(0, 0); }")
        стр.evaluate(ВСТАВКА, [безП, тел]); стр.wait_for_timeout(400)
        стр.mouse.move(2, 2)
        стр.screenshot(path=str(ВЫХОД / f'{имя}.png'))
        print(имя, 'ошибки:', ош[:2])
        стр.close()
    с.shutdown(); бр.close()
