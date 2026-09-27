#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Точка открытого пресета — одного цвета везде, и это цвет схемы.

Константин 27.09.2026, тремя снимками в «Сливе»: «активный пресет подсвечивает
точкой цветовой схемы. Тогда такой же цвет точек показывай где „Активный“ в
разделе Пресеты … в видах на скриншотах». В «Общих» точка перед открытым
пресетом уже была цветом схемы, а на кнопке «Пресеты», на «Активном» и перед
открытым пресетом в «Моих» — серой.

Проба держит, на 390 и 1440, в «Бирюзовом», «Зелёном-графите» и «Сливе», днём и
ночью: точка на кнопке «Пресеты», точки «Активного» на всех вкладках окна,
точка перед открытым пресетом в «Моих» и в «Общих» — одного цвета, и он равен
цвету схемы (--green-mid), а не серому.

    python3 check_active_dot.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
СЕРЫЙ = "rgb(154, 167, 173)"
НАХОДКИ = []

ЦВЕТА = """() => {
  const цвет = э => { if (!э) return null; const с = getComputedStyle(э); return с.backgroundColor !== 'rgba(0, 0, 0, 0)' ? с.backgroundColor : с.color; };
  const s = document.createElement('span'); s.style.color = 'var(--green-mid)'; document.body.appendChild(s);
  const схема = getComputedStyle(s).color; s.remove();
  const точкаМоих = [...document.querySelectorAll('#presetPanel .pcard.pcard-active .pcard-name > span')].find(э => э.textContent === '●');
  const точкаОбщих = [...document.querySelectorAll('#presetPanel .shared-pcard.pcard-active .shared-pcard-name > span')].find(э => э.textContent === '●');
  return { схема, кнопка: цвет(document.querySelector('#presetDot.on')),
           активный: [...document.querySelectorAll('#presetPanel .ptb-dot')].map(цвет),
           мои: цвет(точкаМоих), общие: цвет(точкаОбщих) };
}"""


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а): pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def прогон(бр, порт, ш):
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА); стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load"); стр.wait_for_timeout(2500)
    стр.evaluate("""async () => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      selectProjectOption(0); await new Promise(r => setTimeout(r, 700));
      const в = loadAllPresets(); в['проба-т'] = { id: 'проба-т', name: 'Проба точки', savedAt: new Date().toISOString(), state: collectState() };
      saveAllPresets(в); setActivePreset('проба-т'); }""")
    for тон in ("teal", "bmsk", "plum"):
        for ночь in (False, True):
            н = f"[{ш} {тон}{' ночь' if ночь else ''}]"
            стр.evaluate("([т, н]) => { applyTone(т, false); document.body.classList.toggle('dark', н); }", [тон, ночь])
            # свой открытый: кнопка, «Активный», точка в «Моих»
            стр.evaluate("() => { _activeSharedCode = null; setActivePreset('проба-т'); updateSharedModeIndicator(); openPresetPanel(); switchPresetTab('my'); }")
            стр.wait_for_timeout(700)
            с = стр.evaluate(ЦВЕТА)
            # чужой общий открытый: точка в «Общих»
            стр.evaluate("""() => { _sharedPresets.length = 0; _sharedPresets.push({ short_code: '777888', id: '777888', name: 'Общий проба',
                author_id: 'u-другой', author_name: 'Ирина В.', is_public: true, visibility: 'public', locked: true,
                created_at: '2026-09-25T10:00:00Z', updated_at: '2026-09-25T10:00:00Z', state: { project: { name: 'Проба' }, thickness: 1, totalNum: 1, tech: 'frame' } });
                window.__ТАБЛИЦЫ.preset_links = _sharedPresets.map(п => Object.assign({}, п));
                _activeSharedCode = '777888'; updateSharedModeIndicator(); switchPresetTab('shared'); }""")
            стр.wait_for_timeout(900)
            с["общие"] = стр.evaluate(ЦВЕТА)["общие"]
            точки = {"кнопка «Пресеты»": с["кнопка"], "открытый в «Моих»": с["мои"], "открытый в «Общих»": с["общие"]}
            for i, ц in enumerate(с["активный"]):
                точки[f"«Активный» №{i + 1}"] = ц
            нет = [к for к, ц in точки.items() if ц is None]
            if нет or not с["активный"]:
                НАХОДКИ.append(f"{н} точки не найдены: {нет or '«Активный»'}")
            чужие = {к: ц for к, ц in точки.items() if ц and ц != с["схема"]}
            if чужие:
                НАХОДКИ.append(f"{н} не цветом схемы {с['схема']}: " + "; ".join(f"{к} — {ц}{' (серая)' if ц == СЕРЫЙ else ''}" for к, ц in чужие.items()))
            стр.evaluate("() => { closePresetPanel(); _activeSharedCode = null; updateSharedModeIndicator(); }")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"[{ш}] ошибка страницы: {о[:160]}")
    стр.close()


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                прогон(бр, порт, ш)
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: точка открытого пресета — на кнопке «Пресеты», у «Активного» на всех вкладках, в «Моих» и «Общих» — "
          "одного цвета, цвета схемы, в трёх схемах днём и ночью, на 390 и 1440.")


if __name__ == "__main__":
    главная()
