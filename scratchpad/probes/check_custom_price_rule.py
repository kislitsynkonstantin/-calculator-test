#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«Проверка»: цена своего проекта — по правилу калькулятора.

Константин 17.10.2026, снимком строки «Цена своего проекта» разбора проверок:
«Тут добавь да в проверку пункт, когда у менеджера ручной расчёт, чтобы
проверял по правилам калькулятора и писал в правках отклонение/нарушение для
проверяющего».

Держит, у каркаса и клеёного бруса:
  • цена своего проекта, посчитанная правилом формы (ставка по этажности и
    тёплому контуру, террасы, «Женева» / «без отделки»), — пункта нет;
    отклонение меньше 1 % — нет;
  • цена ниже или выше правила от 1 % — замечание с обеими ценами, процентом
    и тем, откуда цена: «вписана руками», «взята из прайса проекта «…»»;
    раздел «Выбор проекта», ведёт к цене проекта;
  • у проекта без записи о типе этажности и галочке (старый, из чужого
    пресета) правило перебирает варианты и не ругает подходящий;
  • тёплый контур не указан — замечание, что цену не проверить;
  • проект каталога из архива — молчит; цена проекта каталога, исправленная
    руками, — замечание «изменена руками … вместо … по каталогу»;
  • запись о цене (тип этажности, галочка, источник) едет в пресете и
    возвращается при открытии.
Ставки бруса в пробе выдуманы: репозиторий публичный.

    python3 check_custom_price_rule.py
"""
import functools, http.server, json, os, pathlib, socketserver, threading
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT") or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ФИКСТУРА = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ЦЕНЫ = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, " + json.dumps(ФИКСТУРА, ensure_ascii=False) + ");"
        "window.addEventListener('DOMContentLoaded', () => { window._sbProfile = Object.assign(window._sbProfile || {}, { role: 'manager' }); });")
НАХОДКИ, ОТЧЁТ = [], []


def факт(ок, т):
    (ОТЧЁТ if ок else НАХОДКИ).append(т)


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а):
        pass


# Свой проект собирается так же, как форма: цены — правилом технологии.
СВОЙ = """([имя, тип, тёплый, откр, крыт, флаг, источник, множитель, без_записи, этажи]) => {
  const брус = currentTech === 'glulam';
  const ц = брус ? cpЦеныБруса(тип, тёплый, откр, крыт, флаг) : [0, 1, 2].map(к => cpCalcBasePrice(тип, тёплый, откр, крыт, флаг, к));
  const п = [имя, Math.round(ц[0] * множитель), Math.round(ц[1] * множитель), Math.round(ц[2] * множитель), этажи, 'двускатная', тёплый, откр, крыт, null, null, null];
  п._tech = currentTech; п._cloudId = 'проба-' + имя;
  if (!без_записи) п._params = Object.assign({ floorType: тип, source: источник }, брус ? { noFinish: флаг } : { zheneva: флаг });
  if (источник === 'price') п._basedOn = 'Учебный образец 6×6';
  customProjects.push(п); selectedProject = п; currentThickness = 1; calc();
  return п[2]; }"""
ПУНКТ = """() => { const з = проверкаПоЧекЛисту().замечания.filter(х => х.раздел === 'project');
  return з.map(х => ({ т: х.т, эл: х.эл, имя: имяРаздела(х.раздел) })); }"""

socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
хром = os.environ.get("BM_CHROMIUM") or str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def свой(стр, *а):
    стр.evaluate(СВОЙ, list(а)); стр.wait_for_timeout(200)
    return стр.evaluate(ПУНКТ)


with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1440, "height": 1000})
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ЦЕНЫ)
    стр.goto(f"http://127.0.0.1:{с.server_address[1]}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("() => { const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none'; selectProjectOption(0); calc(); }")
    стр.wait_for_timeout(500)

    # ── Каркас ──
    п = свой(стр, "Проба своя 1", "1", 30, 0, 10, False, "calc", 1, False, 1)
    факт(not п, f"каркас: цена по правилу — пункта нет: {п}")
    п = свой(стр, "Проба своя 2", "1", 30, 0, 10, False, "manual", 0.94, False, 1)
    факт(len(п) == 1 and п[0]["т"].startswith("Цена своего проекта ниже правила калькулятора на 6 %: ") and п[0]["т"].endswith(" по правилу — вписана руками")
         and п[0]["эл"] == "priceChip" and п[0]["имя"] == "Выбор проекта", f"каркас: цена на 6 % ниже, вписана руками — пункт с обеими ценами: {п}")
    п = свой(стр, "Проба своя 3", "1", 30, 0, 10, False, "manual", 1.005, False, 1)
    факт(not п, f"каркас: отклонение 0,5 % — пункта нет: {п}")
    п = свой(стр, "Проба своя 4", "2", 110, 12, 0, True, "price", 1.12, False, 2)
    факт(len(п) == 1 and "выше правила калькулятора на 12 %" in п[0]["т"] and п[0]["т"].endswith("взята из прайса проекта «Учебный образец 6×6»"),
         f"каркас: цена из прайса образца на 12 % выше — пункт называет образец: {п}")
    п = свой(стр, "Проба своя 5", "mansard", 80, 0, 0, True, "calc", 1, True, 1.5)
    факт(not п, f"каркас: старый проект без записи — мансарда и «Женева» найдены перебором, пункта нет: {п}")
    п = свой(стр, "Проба своя 6", "1", 30, 0, 0, False, "manual", 1, False, 1)
    стр.evaluate("() => { selectedProject[6] = 0; calc(); }")
    п = стр.evaluate(ПУНКТ)
    факт(len(п) == 1 and п[0]["т"] == "У своего проекта не указан тёплый контур — цену по правилу калькулятора не проверить", f"каркас: без тёплого контура — пункт: {п}")
    п = свой(стр, "Проба своя 7", "1", 30, 0, 10, False, "manual", 0.8, False, 1)
    стр.evaluate("() => { selectedProject._изКаталога = true; calc(); }")
    факт(not стр.evaluate(ПУНКТ), "каркас: проект каталога из архива — пункта нет")

    # Запись о цене едет в пресете.
    свой(стр, "Проба своя 8", "1.5", 70, 0, 0, True, "manual", 0.9, False, 1.5)
    д = стр.evaluate("""() => { const сост = collectState(); const з = (сост.customProjects || []).find(х => х.data[0] === 'Проба своя 8');
      const params = з && з.params; const н = customProjects.findIndex(х => х[0] === 'Проба своя 8'); customProjects.splice(н, 1);
      restoreState(сост); const п = customProjects.find(х => х[0] === 'Проба своя 8');
      return { params, после: п && п._params }; }""")
    факт(bool(д["params"]) and д["params"].get("source") == "manual" and bool(д["после"]) and д["после"].get("floorType") == "1.5" and д["после"].get("zheneva") is True,
         f"запись о цене в пресете и после открытия: {д}")

    # Цена проекта каталога, исправленная руками.
    стр.evaluate("() => { selectProjectOption(0); currentThickness = 1; calc(); projectOverrides.set(selectedProject, [...selectedProject]); selectedProject[2] = Math.round(selectedProject[2] * 0.95); calc(); }")
    п = стр.evaluate(ПУНКТ)
    факт(len(п) == 1 and п[0]["т"].startswith("Цена проекта изменена руками: ") and " по каталогу — ниже на 5 %" in п[0]["т"],
         f"каталог: цена исправлена руками — пункт с обеими ценами: {п}")
    стр.evaluate("() => { const о = projectOverrides.get(selectedProject); selectedProject[2] = о[2]; projectOverrides.delete(selectedProject); calc(); }")
    факт(not стр.evaluate(ПУНКТ), "каталог: цена каталожная — пункта нет")

    # ── Брус ──
    стр.evaluate("async () => { await switchTech('glulam'); await new Promise(r => setTimeout(r, 600)); selectProjectOption(0); calc(); }")
    стр.wait_for_timeout(600)
    стр.evaluate("""() => { _ставкиРучного.glulam = Object.assign(_ставкиРучного.glulam || {}, {
      cp_rates: { '1': [{ max: 40, rate: 61000 }, { max: null, rate: 55000 }], '2': [{ max: null, rate: 48000 }] },
      cp_coef: { sections: [0.9, 1, 1.155], glazing: 0.05, no_finish: 0.12, terrace_open: 9000, terrace_closed: 18000 } }); }""")
    факт(стр.evaluate("() => currentTech") == "glulam" and стр.evaluate("() => !!cpСтавкиБруса()"), "брус открыт, учебные ставки на месте")
    п = свой(стр, "Брус своя 1", "1", 36, 8, 0, False, "calc", 1, False, 1)
    факт(not п, f"брус: цена по правилу — пункта нет: {п}")
    п = свой(стр, "Брус своя 2", "1", 36, 8, 0, True, "manual", 1.1, False, 1)
    факт(len(п) == 1 and "выше правила калькулятора на 10 %" in п[0]["т"] and п[0]["т"].endswith("вписана руками"), f"брус: цена на 10 % выше — пункт: {п}")
    п = свой(стр, "Брус своя 3", "2", 90, 0, 12, True, "calc", 1, True, 2)
    факт(not п, f"брус: старый проект без записи — «без отделки» найдено перебором, пункта нет: {п}")
    факт(not ошибки, f"ошибок страницы нет: {ошибки[:2]}")
    бр.close()
с.shutdown()

for т in ОТЧЁТ:
    print("    ок  " + т)
if НАХОДКИ:
    print("НАХОДКИ:")
    for т in НАХОДКИ:
        print("  ✗ " + т)
    raise SystemExit(1)
print("Чисто: цена своего проекта сверяется с правилом калькулятора у каркаса и бруса; отклонение от 1 % — пункт с обеими ценами.")
