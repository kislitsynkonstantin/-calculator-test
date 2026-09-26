#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пресет другой технологии открывается активным.

Константин 26.09.2026: «когда калькулятор в режиме бруса и открываю пресет
каркаса, все становится, но пресет как активный не отображается. А когда
выбираю из каркаса — все ок». Причина: restoreState переключает технологию,
а switchTech начинает расчёт заново и снимает активный пресет — тот самый,
который только что открыли.

Проба держит, в обе стороны (брус → каркасный пресет, каркас → брусовый):
  • технология переключилась и проект разложился;
  • активным стоит открытый пресет, точка у «Пресетов» горит;
  • «Активный» в окне пресетов находит его, а не говорит «Нет активного пресета»;
  • «Активный» снимает фильтр технологии и строку поиска, если они прячут
    открытый пресет, и переходит к нему;
  • ручная смена технологии по-прежнему снимает активный пресет.

    python3 check_preset_cross_tech_active.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
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


СЦЕНАРИЙ = """async ([откуда, куда]) => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  // Снимок расчёта технологии «куда».
  if (currentTech !== куда) { await switchTech(куда); await ждать(300); }
  selectProjectOption(0); calc(); await ждать(200);
  const снимок = collectState();
  const ярлык = () => (document.getElementById('projectSelectLabel') || {}).textContent || '';
  const проект = ярлык();
  const ид = 'p_' + куда;
  window._пресеты = Object.assign(window._пресеты || {}, { [ид]: { id: ид, name: 'Проба ' + куда,
    savedAt: new Date().toISOString(), shortCode: куда === 'frame' ? '111222' : '333444', state: снимок } });
  setActivePreset(null);
  // Уходим в другую технологию и открываем пресет оттуда.
  await switchTech(откуда); await ждать(300);
  openPresetPanel(); renderPresetList();
  loadPreset(ид);
  await ждать(2600);
  const тостДо = (document.getElementById('toastMsg') || {}).textContent || '';
  openPresetPanel(); renderPresetList();
  const т = document.getElementById('toastMsg'); if (т) т.textContent = '';
  try { scrollToActivePreset(); } catch (e) {}
  await ждать(200);
  const тост = (т || {}).textContent || '';
  closePresetPanel();
  const точка = document.getElementById('presetDot');
  return { ид, тех: currentTech, проект: ярлык(), ждали: проект,
           активный: activePresetId, точка: !!(точка && точка.classList.contains('on')), тост };
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(ТАБЛИЦЫ_JS)
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            стр.evaluate("""() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
              const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
              window.GLULAM_ROLES = ['admin', 'editor', 'manager']; }""")
            for откуда, куда in (("glulam", "frame"), ("frame", "glulam")):
                р = стр.evaluate(СЦЕНАРИЙ, [откуда, куда])
                м = f"{откуда} → пресет {куда}"
                if р["тех"] != куда:
                    плохо(f"{м}: технология не переключилась ({р['тех']})")
                if not р["ждали"] or р["ждали"] == "Выберите проект" or р["проект"] != р["ждали"]:
                    плохо(f"{м}: проект не разложился ({р['проект']!r} вместо {р['ждали']!r})")
                if р["активный"] != р["ид"]:
                    плохо(f"{м}: открытый пресет не активен ({р['активный']!r})")
                if not р["точка"]:
                    плохо(f"{м}: точка у «Пресетов» не горит")
                if "Нет активного" in р["тост"]:
                    плохо(f"{м}: «Активный» не находит открытый пресет: {р['тост']!r}")
                print(f"  {м}: {json.dumps(р, ensure_ascii=False)}")
            # «Активный» снимает фильтр технологии и строку поиска, если они прячут
            # открытый пресет (Константин 26.09.2026: «когда стоит фильтр на брус,
            # а нажимаю Активный каркас — не найден»).
            р = стр.evaluate("""async () => {
              const ждать = мс => new Promise(r => setTimeout(r, мс));
              const ид = activePresetId, тех = техПресета(loadAllPresets()[ид]);
              openPresetPanel(); renderPresetList();
              const итог = {};
              for (const как of ['фильтр', 'поиск']) {
                if (как === 'фильтр') { ТЕХ_ВЫБОР.my.clear(); ТЕХ_ВЫБОР.my.add(тех === 'frame' ? 'glulam' : 'frame'); }
                else { const п = document.getElementById('presetSearchInput'); п.value = 'нет такого'; syncPresetSearch(п); }
                renderPresetList();
                const было = !!document.querySelector('.pcard-active');
                const т = document.getElementById('toastMsg'); if (т) т.textContent = '';
                await scrollToActivePreset(); await ждать(200);
                итог[как] = { было, стало: !!document.querySelector('.pcard-active'), фильтр: ТЕХ_ВЫБОР.my.size,
                              поиск: document.getElementById('presetSearchInput').value, тост: (т || {}).textContent || '' };
              }
              closePresetPanel();
              return итог; }""")
            for как, х in р.items():
                if х["было"]:
                    плохо(f"«Активный» при {как}е: карточка и так была видна — сценарий ничего не проверил")
                if not х["стало"] or "не найден" in х["тост"]:
                    плохо(f"«Активный» при {как}е не нашёл открытый пресет: {х}")
                if как == "фильтр" and х["фильтр"]:
                    плохо("«Активный» не снял фильтр технологии")
                if как == "поиск" and х["поиск"]:
                    плохо("«Активный» не очистил строку поиска")
            print(f"  «Активный» под фильтром и поиском: {json.dumps(р, ensure_ascii=False)}")

            # Ручная смена технологии по-прежнему начинает расчёт заново.
            р = стр.evaluate("""async () => { const был = currentTech; await switchTech(был === 'frame' ? 'glulam' : 'frame');
              await new Promise(r => setTimeout(r, 300)); return activePresetId; }""")
            if р:
                плохо(f"ручная смена технологии не сняла активный пресет ({р})")
            for о in [о for о in ошибки if "supabase.co" not in о][:3]:
                плохо("ошибка страницы: " + о[:160])
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: пресет другой технологии открывается активным в обе стороны — точка горит, «Активный» его находит, "
          "снимая фильтр технологии и строку поиска, если они его прячут; "
          "ручная смена технологии по-прежнему снимает активный пресет.")


if __name__ == "__main__":
    главная()
