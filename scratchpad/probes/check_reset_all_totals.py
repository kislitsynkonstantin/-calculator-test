#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Сбросить всё» обнуляет цифры и в боковой панели «Спецификация».

Константин 26.09.2026, снимком боковой панели: «когда был открыт пресет по
коду — нажимаю сбросить, а цифры остаются». Панель писала «Проект не выбран»
и под этим — полную цену и суммы разделов прежнего расчёта: без проекта
calc() выходил раньше, чем обновлялись итог, кэш сумм разделов и панель.

Проба на 390 и 1440, для чужого пресета «только просмотр», своего открытого
общего и расчёта без пресета, жмёт «Сбросить → Сбросить всё» и держит:
  • общий пресет закрыт, полоски внизу нет, проекта нет;
  • итог расчёта 0, в шапке панели нет прежней цены, у всех разделов «—»;
  • у чужого пресета «только просмотр» пункт не заперт: сброс не правит
    пресет, а выходит из него;
  • у него же прочие пункты меню серые (кроме звёзд опций), подсказка
    называет «Сбросить всё»; у своего и без пресета пункт выбранных опций жив.

    python3 check_reset_all_totals.py
"""
import functools, http.server, json, os, pathlib, re, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'admin', first_name: 'Проба', app_settings: {} }];")
СНИМКИ = pathlib.Path(os.environ.get("BM_SHOTS") or "/tmp")
НАХОДКИ = []


def плохо(т):
    НАХОДКИ.append(т)


def хром():
    и = os.environ.get("BM_CHROMIUM")
    if и and pathlib.Path(и).exists():
        return и
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    class Тихий(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *а):
            pass
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


ОТКРЫТЬ = """async (вид) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
  applyUiStyle('blank', false); applyThemeMode('dark', false);
  selectProjectOption(0); await ждать(700);
  // Одна не базовая опция — чтобы пункту «Выбранные опции» было что сбрасывать.
  const оп = OPTIONS.find(о => !о.included && о.price && !checkedOptions[о.id] && о.status !== 'legacy');
  if (оп) { try { toggleOpt(оп.id); } catch (e) {} }
  const снимок = collectState(); снимок.tech = 'frame';
  window.__т = []; window.showToast = т => window.__т.push(String(т));
  if (вид !== 'без') {
    _sharedPresets.push({ short_code: '365484', id: '365484', preset_id: 'preset_x',
      author_id: вид === 'свой' ? _sbUser.id : 'u-другой', author_name: вид === 'свой' ? 'Проба' : 'Максим Григорьев',
      name: 'Пресет пробы', state: снимок, is_public: вид === 'свой', visibility: 'public',
      created_at: '2026-09-14T10:00:00Z', updated_at: '2026-09-25T12:41:32Z', locked: false });
    openSharedPreset('365484'); await ждать(900);
  }
  try { openSideNav(); } catch (e) {}
  await ждать(400);
  return { итог: _currentTotal, код: _activeSharedCode };
}"""

МЕНЮ = """async () => {
  toggleResetDropdown(); await new Promise(r => setTimeout(r, 200));
  const живые = [...document.querySelectorAll('#resetDropdownMenu .reset-dropdown-item')]
    .filter(х => !х.classList.contains('reset-all-item') && !х.disabled && !х.classList.contains('rd-off')).map(х => х.id);
  const п = document.getElementById('rdHint');
  const подсказка = п && getComputedStyle(п).display !== 'none' ? п.textContent : '';
  const м = document.getElementById('resetDropdownMenu').getBoundingClientRect();
  const зазор = Math.round(innerWidth - м.right);
  closeResetDropdown(); await new Promise(r => setTimeout(r, 100));
  return { живые, подсказка, зазор };
}"""

СБРОС = """async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  toggleResetDropdown(); await ждать(200);
  const п = document.querySelector('#resetDropdownMenu .reset-all-item');
  п.click(); await ждать(900);
  try { openSideNav(); } catch (e) {}
  await ждать(300);
  const разделы = SECTIONS.map(s => (document.getElementById('snVal_' + s.key) || {}).textContent || '');
  const полоска = document.getElementById('presetChip'); // значок общего пресета в углу
  return { итог: _currentTotal, код: _activeSharedCode, проект: selectedProject && selectedProject[0],
    имя: (document.getElementById('snHeadName') || {}).textContent || '',
    сумма: (document.getElementById('snHeadSum') || {}).textContent || '',
    база: (document.getElementById('snHeadBase') || {}).textContent || '',
    разделыСЦифрами: разделы.filter(т => /\\d/.test(т)),
    полоска: !!(полоска && полоска.classList.contains('pc-shared') && полоска.offsetWidth), тосты: window.__т };
}"""


def главная():
    СНИМКИ.mkdir(parents=True, exist_ok=True)
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for ш in (390, 1440):
                for вид in ("чужой", "свой", "без"):
                    н = f"[{ш} {вид}]"
                    стр = бр.new_page(viewport={"width": ш, "height": 900})
                    ошибки = []
                    стр.on("pageerror", lambda e: ошибки.append(str(e)))
                    стр.add_init_script(ЗАГЛУШКА)
                    стр.add_init_script(ТАБЛИЦЫ_JS)
                    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
                    стр.wait_for_timeout(2500)
                    до = стр.evaluate(ОТКРЫТЬ, вид)
                    if not до["итог"]:
                        плохо(f"{н} до сброса итога нет — проверять нечего ({до})")
                    меню = стр.evaluate(МЕНЮ)
                    print("  " + н, "меню", меню)
                    if меню["зазор"] < 8:
                        плохо(f"{н} меню «Сбросить» у края экрана: зазор {меню['зазор']} px")
                    if вид == "чужой":
                        if [и for и in меню["живые"] if и != "rdStars"]:
                            плохо(f"{н} в пресете «только просмотр» живые пункты сброса: {меню['живые']}")
                        if "Сбросить всё" not in меню["подсказка"]:
                            плохо(f"{н} подсказка меню не говорит про «Сбросить всё»: «{меню['подсказка']}»")
                    elif "rdChecked" not in меню["живые"]:
                        плохо(f"{н} пункт «Сбросить выбранные опции» серый без замка: {меню['живые']}")
                    р = стр.evaluate(СБРОС)
                    print("  " + н, json.dumps(р, ensure_ascii=False)[:300])
                    if any("заблокирован" in т for т in р["тосты"]):
                        плохо(f"{н} «Сбросить всё» заперто замком: {р['тосты']}")
                    if р["код"] or р["полоска"]:
                        плохо(f"{н} общий пресет не закрылся (код {р['код']!r}, полоска {р['полоска']})")
                    if р["проект"]:
                        плохо(f"{н} проект остался: {р['проект']!r}")
                    if р["итог"]:
                        плохо(f"{н} итог расчёта после сброса {р['итог']}")
                    if re.search(r"[1-9]", р["сумма"]) or re.search(r"[1-9]", р["база"]):
                        плохо(f"{н} в шапке панели осталась цена: «{р['сумма']}» / «{р['база']}»")
                    if р["разделыСЦифрами"]:
                        плохо(f"{н} у разделов в панели остались суммы: {р['разделыСЦифрами'][:4]}")
                    if вид == "чужой":
                        стр.screenshot(path=str(СНИМКИ / f"reset-all-{ш}.png"))
                    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                        плохо(f"{н} ошибка страницы: {о[:160]}")
                    стр.close()
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ[:40]:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: «Сбросить всё» закрывает пресет — и чужой «только просмотр», и свой, — а итог, шапка "
          "боковой панели и суммы разделов обнуляются; без пресета — так же.")


if __name__ == "__main__":
    главная()
