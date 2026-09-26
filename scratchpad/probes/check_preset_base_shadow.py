#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пресет не заводит двойника проекта из списка.

Константин 26.09.2026: у названия проекта «Хай-тек баня «Виго» 7,7х8,2»
на время появлялся значок папки, а в списке проектов стоял двойник со
звездой. Причина: в снимке пресета, в списке своих проектов, лежала копия
базового проекта — однажды восстановленная «из архива». Каждое открытие
заводило её снова, выбирало вместо базового и сохраняло обратно в пресет.

Проба держит:
  • копия базового проекта из снимка не заводится: выбран проект из списка,
    звезды и значка у названия нет, двойника в списке нет;
  • уже попавшая в память копия снимается при открытии;
  • новый снимок копию не пишет;
  • свой проект из аккаунта с тем же названием по-прежнему выбирается первым;
  • проект, которого нет в списке, восстанавливается из архива — без эмодзи.

    python3 check_preset_base_shadow.py
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


СЦЕНАРИЙ = """async () => {
  const ждать = мс => new Promise(r => setTimeout(r, мс));
  const ярлык = () => document.getElementById('projectSelectLabel').textContent;
  const эмодзи = s => /[\\u{1F300}-\\u{1FAFF}]/u.test(s);
  selectProjectOption(0); calc(); await ждать(150);
  const база = PROJECTS[0], имя = база[0];
  const снимок = collectState();
  // В снимок подложена копия базового проекта — как в старых пресетах.
  снимок.customProjects = [{ data: [...база], matrixOv: {} }];
  window._пресеты = { p_shadow: { id: 'p_shadow', name: 'Тень', savedAt: new Date().toISOString(), shortCode: '555666', state: снимок } };
  // И одна копия уже сидит в памяти, помеченная архивной.
  const тень = [...база]; тень._archived = true; customProjects.push(тень);
  selectProjectOption(-1); await ждать(100);
  loadPreset('p_shadow'); await ждать(700);
  const итог = { имя, ярлык: ярлык(), выбранБазовый: PROJECTS.includes(selectedProject),
    двойников: customProjects.filter(p => p[0] === имя).length,
    вСнимке: (collectState().customProjects || []).filter(c => c.data[0] === имя).length };
  итог.эмодзи = эмодзи(итог.ярлык);
  // Свой проект из аккаунта с тем же названием — первым.
  const свой = [...база]; свой._cloudId = 'cp_проба'; customProjects.push(свой);
  loadPreset('p_shadow'); await ждать(700);
  итог.свойПервым = selectedProject === свой;
  customProjects.splice(customProjects.indexOf(свой), 1);
  // Проекта нет в списке — архив, без эмодзи.
  const снимок2 = collectState(); снимок2.project = { name: 'Проект, которого нет', data: [...база] };
  снимок2.project.data[0] = 'Проект, которого нет';
  window._пресеты.p_arch = { id: 'p_arch', name: 'Архив', savedAt: new Date().toISOString(), shortCode: '777888', state: снимок2 };
  loadPreset('p_arch'); await ждать(700);
  итог.архивЯрлык = ярлык(); итог.архивЭмодзи = эмодзи(итог.архивЯрлык);
  итог.архивВыбран = !!(selectedProject && selectedProject._archived);
  return итог;
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
              const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none'; }""")
            р = стр.evaluate(СЦЕНАРИЙ)
            print("  " + json.dumps(р, ensure_ascii=False))
            if not р["выбранБазовый"]: плохо("выбрана копия, а не проект из списка")
            if р["ярлык"].strip() != р["имя"]: плохо(f"у названия проекта лишнее: {р['ярлык']!r}")
            if р["эмодзи"]: плохо("у названия проекта эмодзи")
            if р["двойников"]: плохо(f"в списке остался двойник проекта ({р['двойников']})")
            if р["вСнимке"]: плохо("новый снимок пишет копию базового проекта")
            if not р["свойПервым"]: плохо("свой проект из аккаунта с тем же названием не выбран первым")
            if not р["архивВыбран"]: плохо("проект, которого нет в списке, не восстановлен из архива")
            if р["архивЭмодзи"]: плохо(f"у архивного проекта эмодзи: {р['архивЯрлык']!r}")
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
    print("Чисто: копия базового проекта из снимка не заводится и снимается из памяти, выбран проект из списка, "
          "новый снимок её не пишет; свой проект из аккаунта выбирается первым; архивный — без эмодзи.")


if __name__ == "__main__":
    главная()
