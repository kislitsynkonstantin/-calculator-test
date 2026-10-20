import sys, pathlib, os
from playwright.sync_api import sync_playwright
имя = sys.argv[1]; вых = pathlib.Path(sys.argv[2])
ф = pathlib.Path(f'/home/user/-calculator-test/mockups/{имя}.html').as_uri()
with sync_playwright() as p:
    бр = p.chromium.launch(executable_path=os.environ.get('BM_CHROMIUM') or None)
    for ш, тема in ((1440,'light'),(390,'light'),(1440,'dark')):
        с = бр.new_page(viewport={'width': ш, 'height': 900}, device_scale_factor=2, color_scheme=тема)
        ош = []; с.on('pageerror', lambda e: ош.append(str(e)))
        с.goto(ф); с.wait_for_timeout(500)
        м = с.evaluate("""() => ({ пере: document.documentElement.scrollWidth - innerWidth,
          шрифт: (() => { const и = document.createElement('span'); и.textContent='Код пресета'; и.style.cssText='position:absolute;font-size:20px';
             document.body.appendChild(и); const ш = f => { и.style.fontFamily = f; return и.getBoundingClientRect().width; };
             const д = Math.abs(ш("'Geologica',monospace") - ш('monospace')) > .5; и.remove(); return д; })(),
          вылет: [...document.querySelectorAll('.win, .dsk, .pcard, .bar')].filter(о => { const п = о.getBoundingClientRect(); return [...о.querySelectorAll('*')].some(э => { const r = э.getBoundingClientRect(); return r.width && (r.right > п.right + .5 || r.left < п.left - .5); }); }).length })""")
        print(ш, тема, м, ош)
        с.screenshot(path=str(вых / f'{имя}-{ш}-{тема}.png'), full_page=True)
    бр.close()
