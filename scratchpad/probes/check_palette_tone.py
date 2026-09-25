#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цвет оформления: бирюзовый по умолчанию, синий — выбором в настройках.

Константин 24.09.2026: «переключатель конечно в настройках, по умолчанию
также стоит бирюза». Проба меряет отрисованное, а не разметку, в обеих темах
оформления, днём и ночью, на 390 и 1440 px:

  • без выбора — бирюза: признака тона нет, акцент бирюзовый, логотип в шапке
    и на экране входа — основной, значки — основные;
  • в настройках строка «Цвет оформления» — выпадающий список «Бирюзовый /
    Синий», выбран бирюзовый, список не вылезает за строку и не раздут; под
    ней превью пяти ролей палитры, цвета и значения выбранного тона, ничего
    не обрезано и не выходит за окно (Константин 24.09.2026: «выпадающий
    список… плюс добавь превью цвета оформления»);
  • хвойный, индиго, графит и титан (поворот тона со своей
    насыщенностью): страница, логотип,
    отдельный документ, снимок и лист клиента в тоне; логотипы страница
    рисует сама на холсте — проба читает их пиксели: бирюзовых нет, крыша
    светлого логотипа той же яркости, что бирюзовая;
  • аналитика — свой документ в кадре — при синем не несёт ни одного
    бирюзового цвета на отрисовке, при возврате бирюза возвращается;
  • «Синий» — акцент синий в самой странице, логотип в шапке и на входе —
    синий (картинка тона, а не основная), значок вкладки и приложения —
    синие; выбор ушёл в профиль аккаунта (app_settings.tone);
  • документ, собранный отдельно (печать, договор, справка — через
    сПалитрой), тоже синий и с синим логотипом; лист печати в самой
    странице — с синим логотипом;
  • снимок для ссылки клиенту несёт тон, а лист клиента по такому снимку
    встаёт синим, и его синий логотип-файл действительно грузится;
  • «Бирюзовый» возвращает всё байт в байт: адреса значков, логотипы, цвет.

    python3 check_palette_tone.py
"""
import functools
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗДЕСЬ = pathlib.Path(__file__).parent
ЗАГЛУШКА = (ЗДЕСЬ / "stub_sb.js").read_text(encoding="utf-8")
ДАННЫЕ = json.loads((ЗДЕСЬ / "kit_fixture.json").read_text(encoding="utf-8"))
ТАБЛИЦЫ_JS = ("window.__ТАБЛИЦЫ = Object.assign(window.__ТАБЛИЦЫ || {}, "
              + json.dumps(ДАННЫЕ, ensure_ascii=False) + ");\n"
              # Строка профиля, куда ложится сохранённая настройка аккаунта.
              "window.__ТАБЛИЦЫ.profiles = [{ id: 'u-проба', role: 'manager', first_name: 'Проба', app_settings: {} }];")
НАХОДКИ = []
КОД = "abcd2345"


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    return str(sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))[-1])


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(где, т):
    НАХОДКИ.append(f"[{где}] {т}")


def синий(rgb):
    """Синий — канал B заметно больше G; бирюза — G и B почти равны."""
    import re
    ч = [int(x) for x in re.findall(r"\d+", rgb)[:3]]
    return len(ч) == 3 and ч[2] - ч[1] > 25


def не_бирюза(rgb):
    """Бирюза: зелёный и синий каналы близки, красный заметно ниже."""
    import re
    ч = [int(x) for x in re.findall(r"\d+", rgb)[:3]]
    return not (len(ч) == 3 and abs(ч[1] - ч[2]) < 20 and ч[1] - ч[0] > 30)


СТРОКА = """() => {
  const с = document.getElementById('stToneSelect');
  if (!с) return null;
  const ряд = с.closest('.st-row').getBoundingClientRect(), б = с.getBoundingClientRect();
  const пр = document.querySelector('.st-tone-prev');
  const тело = document.getElementById('settingsBody') || document.body;
  const т = тело.getBoundingClientRect();
  const образцы = пр ? [...пр.querySelectorAll('.st-sw')] : [];
  return {
    варианты: [...с.options].map(о => о.textContent.trim()), выбран: с.value,
    внутри: б.left >= ряд.left - 0.5 && б.right <= ряд.right + 0.5, высота: Math.round(б.height),
    стрелка: getComputedStyle(с).backgroundImage.includes('svg'),
    превью: образцы.map(о => о.querySelector('.st-sw-h').textContent),
    превьюЦвет: образцы.map(о => getComputedStyle(о.querySelector('.st-sw-c')).backgroundColor),
    превьюЗаКраем: образцы.some(о => { const r = о.getBoundingClientRect(); return r.right > т.right + 0.5 || r.left < т.left - 0.5; }),
    обрезано: образцы.some(о => [...о.querySelectorAll('.st-sw-h')].some(х => х.scrollWidth > х.clientWidth + 1)),
  };
}"""

АНАЛИТИКА = """async () => {
  // Аналитика — свой документ в кадре со своими цветами: считаем фирменные
  // бирюзовые цвета на отрисовке — в цвете, фоне, рамке, заливке и обводке.
  if (typeof openStats === 'function') { try { await openStats(); } catch (e) {} }
  await new Promise(r => setTimeout(r, 1500));
  const ф = document.getElementById('statsFrame');
  const д = ф && ф.contentDocument;
  if (!д || !д.body) return null;
  const бирюза = (с) => {
    const ч = (с.match(/\d+(\.\d+)?/g) || []).map(Number);
    if (ч.length < 3 || (ч.length > 3 && ч[3] === 0)) return false;
    const [r, g, b] = ч, M = Math.max(r, g, b), m = Math.min(r, g, b);
    if (M - m < 6) return false;
    let h = M === r ? ((g - b) / (M - m)) % 6 : M === g ? (b - r) / (M - m) + 2 : (r - g) / (M - m) + 4;
    h = (h * 60 + 360) % 360;
    return h >= 175 && h <= 195;
  };
  let всего = 0, бир = 0;
  д.querySelectorAll('*').forEach(э => {
    const с = getComputedStyle(э);
    ['color', 'backgroundColor', 'borderTopColor', 'fill', 'stroke'].forEach(к => {
      const в = с[к]; if (!в || в === 'none') return;
      всего++; if (бирюза(в)) бир++;
    });
  });
  return { всего, бир };
}"""


ЛОГОТИП_ПИКСЕЛИ = """async () => {
  // Логотип в шапке рисует сама страница на холсте: читаем его пиксели.
  const и = document.getElementById('headerLogo');
  await (и.decode ? и.decode().catch(() => {}) : Promise.resolve());
  const х = document.createElement('canvas'); х.width = и.naturalWidth; х.height = и.naturalHeight;
  const к = х.getContext('2d'); к.drawImage(и, 0, 0);
  const п = к.getImageData(0, 0, х.width, х.height).data;
  let бир = 0, свет = 0, тём = 0; const цвет = new Map();
  for (let i = 0; i < п.length; i += 4) {
    if (п[i + 3] < 200) continue;
    const r = п[i], g = п[i + 1], b = п[i + 2], M = Math.max(r, g, b), m = Math.min(r, g, b);
    if (M - m < 6) { if (M > 200) свет++; else if (M < 60) тём++; continue; }
    let h = M === r ? ((g - b) / (M - m)) % 6 : M === g ? (b - r) / (M - m) + 2 : (r - g) / (M - m) + 4;
    h = (h * 60 + 360) % 360;
    if (h >= 175 && h <= 195 && (M - m) > 25) бир++;
    const ключ = r + ',' + g + ',' + b; цвет.set(ключ, (цвет.get(ключ) || 0) + 1);
  }
  const главный = [...цвет.entries()].sort((a, b) => b[1] - a[1])[0];
  let я = 0;
  if (главный) {
    const [r, g, b] = главный[0].split(',').map(Number).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    я = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }
  return { бирюзовых: бир, светлый: свет > тём, яркость: я };
}"""


ЗАМЕР = """() => {
  const к = document.createElement('i'); к.style.color = 'var(--br-38)'; document.body.appendChild(к);
  const акцент = getComputedStyle(к).color; к.remove();
  const шапка = document.getElementById('headerLogo'), вход = document.getElementById('loginLogo');
  const основы = [_LOGO_DARK, _LOGO_LIGHT];
  return {
    признак: document.documentElement.dataset.tone || '',
    акцент,
    шапкаОснова: основы.includes(шапка.getAttribute('src')),
    входОснова: основы.includes(вход.getAttribute('src')),
    значок: document.querySelector('link[rel="icon"]').getAttribute('href'),
    прил: document.querySelector('link[rel="apple-touch-icon"]').getAttribute('href'),
    профиль: ((window.__ТАБЛИЦЫ.profiles || []).find(p => p.id === 'u-проба') || {}).app_settings || null,
  };
}"""

ДОКУМЕНТ = """async () => {
  // Отдельный документ — как печать и договор: через сПалитрой, в кадре.
  const ф = document.createElement('iframe'); document.body.appendChild(ф);
  ф.srcdoc = сПалитрой('<!doctype html><html><head></head><body><i id="к" style="color:var(--br-38)">к</i>'
    + '<img id="л" src="' + _LOGO_DARK + '"></body></html>');
  await new Promise(r => ф.onload = r);
  const д = ф.contentDocument;
  const итог = { акцент: getComputedStyle(д.getElementById('к')).color,
                 логотипОснова: д.getElementById('л').getAttribute('src') === _LOGO_DARK };
  ф.remove();
  // Лист печати в самой странице.
  try { buildPrintDoc(); } catch (e) {}
  const лп = [...document.querySelectorAll('img[alt="Баня-МСК"]')].map(и => и.getAttribute('src'));
  итог.печатьОснова = лп.some(с => с === _LOGO_DARK);
  итог.печатьЕсть = лп.length;
  итог.снимокТон = (window._снимокКлиента || {}).тон || '';
  итог.снимок = window._снимокКлиента || null;
  return итог;
}"""


def открыть(бр, порт, ш, в, бланк, ночь):
    к = бр.new_context(viewport={"width": ш, "height": в})
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.add_init_script(ТАБЛИЦЫ_JS)
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.wait_for_timeout(2500)
    стр.evaluate("""([бланк, ночь]) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      const в = document.getElementById('loginScreen'); if (в) в.style.display = 'none';
      applyUiStyle(бланк ? 'blank' : 'light', false);
      applyThemeMode(ночь ? 'dark' : 'light', false);
      selectProjectOption(0);
    }""", [бланк, ночь])
    стр.wait_for_timeout(600)
    return к, стр, ошибки


def лист_клиента(бр, порт, снимок, ночь):
    с404 = (КОРЕНЬ / "404.html").read_text(encoding="utf-8")
    ответ = {"status": "ok", "snapshot_at": "2026-09-24T09:00:00+00:00", "price_until": None, "snapshot": снимок}
    к = бр.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark" if ночь else "light")
    к.route(f"http://127.0.0.1:{порт}/{КОД}*",
            lambda м: м.fulfill(status=200, content_type="text/html; charset=utf-8", body=с404))
    к.route("**/rest/v1/rpc/**",
            lambda м: м.fulfill(status=200, content_type="application/json",
                                body=json.dumps(ответ if м.request.url.endswith("client_link_get") else {"status": "ok"})))
    стр = к.new_page()
    стр.goto(f"http://127.0.0.1:{порт}/{КОД}", wait_until="load")
    стр.wait_for_timeout(1500)
    итог = стр.evaluate("""() => {
      const к = document.createElement('i'); к.style.color = 'var(--br-38)'; document.body.appendChild(к);
      const акцент = getComputedStyle(к).color; к.remove();
      const лого = [...document.querySelectorAll('img.cl-logo, img.bl-logo-doc')];
      return { признак: document.documentElement.getAttribute('data-tone') || '', акцент,
               адреса: лого.map(и => и.getAttribute('src')),
               загружены: лого.filter(и => getComputedStyle(и).display !== 'none').every(и => и.complete && и.naturalWidth > 0) };
    }""")
    к.close()
    return итог


def проверить(бр, порт, ш, в, бланк, ночь):
    где = f"{'Бланк' if бланк else 'Модерн'} · {'ночь' if ночь else 'день'} · {ш}px"
    к, стр, ошибки = открыть(бр, порт, ш, в, бланк, ночь)
    до = стр.evaluate(ЗАМЕР)
    if до["признак"] or синий(до["акцент"]) or not до["шапкаОснова"] or not до["входОснова"]:
        плохо(где, f"без выбора не бирюза: {до['признак']!r}, акцент {до['акцент']}, "
                   f"шапка основная {до['шапкаОснова']}, вход основной {до['входОснова']}")
    # ── строка в настройках ──
    стр.evaluate("() => { openSettings && openSettings(); }")
    стр.wait_for_timeout(400)
    строка = стр.evaluate(СТРОКА)
    if not строка:
        плохо(где, "в настройках нет выпадающего списка «Цвет оформления»")
    else:
        if строка["варианты"] != ["Бирюзовый", "Зелёный-графит", "Синий", "Тёмно-синий", "Янтарь", "Слива", "Индиго", "Графит", "Титан"] \
                or строка["выбран"] != "teal":
            плохо(где, f"список цвета: {строка}")
        if not строка["стрелка"]:
            плохо(где, "у списка цвета нет стрелки — не видно, что он раскрывается")
        if not строка["внутри"] or строка["высота"] > 36:
            плохо(где, f"список цвета вылезает за строку или раздут: {строка}")
        if len(строка["превью"]) != 5 or any(синий(ц) or не_бирюза(ц) for ц in строка["превьюЦвет"][:3]):
            плохо(где, f"превью бирюзового: {строка['превью']} {строка['превьюЦвет']}")
        if строка["превьюЗаКраем"] or строка["обрезано"]:
            плохо(где, f"превью вылезает или обрезано: за краем {строка['превьюЗаКраем']}, обрезано {строка['обрезано']}")
        стр.select_option("#stToneSelect", "blue")
        стр.wait_for_timeout(400)
        try:
            стр.wait_for_function("() => window.__картинкиТонаГотовы === 'blue'", timeout=8000)
        except Exception:
            плохо(где, "логотипы синего так и не нарисовались")
        с2 = стр.evaluate(СТРОКА)
        if not с2 or с2["выбран"] != "blue" or not all(синий(ц) for ц in с2["превьюЦвет"][:3]):
            плохо(где, f"после выбора синего список или превью не синие: {с2 and (с2['выбран'], с2['превьюЦвет'])}")
        elif с2["превью"][:3] == строка["превью"][:3]:
            плохо(где, "подписи значений в превью не сменились вместе с цветом")
    после = стр.evaluate(ЗАМЕР)
    if после["признак"] != "blue" or not синий(после["акцент"]):
        плохо(где, f"«Синий» не перекрасил страницу: признак {после['признак']!r}, акцент {после['акцент']}")
    if после["шапкаОснова"] or после["входОснова"]:
        плохо(где, "при синем логотип в шапке или на входе остался бирюзовым")
    if после["значок"] == до["значок"] or после["прил"] == до["прил"]:
        плохо(где, "при синем значок вкладки или приложения остался бирюзовым")
    if not после["профиль"] or после["профиль"].get("tone") != "blue":
        плохо(где, f"выбор не ушёл в профиль аккаунта: {после['профиль'] and после['профиль'].get('tone')!r}")
    if ш == 1440 and not ночь:
        ан = стр.evaluate(АНАЛИТИКА)
        if not ан:
            плохо(где, "аналитика не открылась — проверить нечем")
        elif ан["бир"]:
            плохо(где, f"аналитика при синем осталась бирюзовой: {ан['бир']} бирюзовых цветов из {ан['всего']}")
        стр.evaluate("() => { try { closeStats(); } catch (e) {} }")
    д = стр.evaluate(ДОКУМЕНТ)
    if not синий(д["акцент"]) or д["логотипОснова"]:
        плохо(где, f"отдельный документ не синий: акцент {д['акцент']}, логотип основной {д['логотипОснова']}")
    if д["печатьОснова"]:
        плохо(где, "лист печати в странице — с бирюзовым логотипом")
    if д["снимокТон"] != "blue":
        плохо(где, f"снимок для ссылки не несёт тон: {д['снимокТон']!r}")
    if ш == 390 and д["снимок"]:
        кл = лист_клиента(бр, порт, д["снимок"], ночь)
        if кл["признак"] != "blue" or not синий(кл["акцент"]):
            плохо(где, f"лист клиента по синему снимку не синий: {кл}")
        if not all("-blue.png" in а for а in кл["адреса"]) or not кл["загружены"]:
            плохо(где, f"логотип на листе клиента не синий или не загрузился: {кл['адреса']}, загружены {кл['загружены']}")
    лого = стр.evaluate(ЛОГОТИП_ПИКСЕЛИ)
    if лого["бирюзовых"]:
        плохо(где, f"логотип в шапке при синем несёт {лого['бирюзовых']} бирюзовых пикселей")
    # ── графит и титан: не поворот тона, а своя насыщенность ──
    # Синий, зелёный Баня-МСК, янтарь и слива (25.09.2026) — не чистый
    # поворот: у них своя светлота и насыщенность, и ровно поэтому их
    # логотипы и документы проверяются тем же кругом, что и прежние тона.
    for тон in ("sky", "bmsk", "amber", "plum", "indigo", "graphite", "titan"):
        стр.select_option("#stToneSelect", тон)
        try:
            стр.wait_for_function(f"() => window.__картинкиТонаГотовы === '{тон}'", timeout=8000)
        except Exception:
            плохо(где, f"логотипы тона {тон} так и не нарисовались")
            continue
        з = стр.evaluate(ЗАМЕР)
        л = стр.evaluate(ЛОГОТИП_ПИКСЕЛИ)
        if з["признак"] != тон or not не_бирюза(з["акцент"]):
            плохо(где, f"{тон}: признак {з['признак']!r}, акцент {з['акцент']} — страница не перекрашена")
        if з["шапкаОснова"] or з["входОснова"] or л["бирюзовых"]:
            плохо(где, f"{тон}: логотип бирюзовый (основа {з['шапкаОснова']}/{з['входОснова']}, пикселей {л['бирюзовых']})")
        if л["светлый"] and abs(л["яркость"] / 0.2206 - 1) > 0.06:
            плохо(где, f"{тон}: крыша светлого логотипа ярче или темнее бирюзовой ({л['яркость']:.3f} против 0.221)")
        if not з["профиль"] or з["профиль"].get("tone") != тон:
            плохо(где, f"{тон}: выбор не ушёл в профиль")
        д_т = стр.evaluate(ДОКУМЕНТ)
        if not не_бирюза(д_т["акцент"]) or д_т["логотипОснова"] or д_т["снимокТон"] != тон:
            плохо(где, f"{тон}: отдельный документ или снимок не в тоне: {д_т['акцент']}, {д_т['логотипОснова']}, {д_т['снимокТон']!r}")
        if ш == 390 and д_т["снимок"]:
            кл = лист_клиента(бр, порт, д_т["снимок"], ночь)
            if кл["признак"] != тон or not all(f"-{тон}.png" in а for а in кл["адреса"]) or not кл["загружены"]:
                плохо(где, f"{тон}: лист клиента не в тоне: {кл}")
    стр.select_option("#stToneSelect", "blue")
    стр.wait_for_timeout(300)
    # ── «Хвойный» снят: у кого он был выбран, встаёт бирюза, а не пустота ──
    хв = стр.evaluate("() => { applyTone('pine', false); return [document.documentElement.dataset.tone || '', "
                      "[...document.querySelectorAll('#stToneSelect option')].some(о => о.value === 'pine')]; }")
    if хв != ['', False]:
        плохо(где, f"снятый «Хвойный» не вернулся к бирюзе или остался в списке: {хв}")
    # ── обратно ──
    стр.evaluate("() => applyTone('teal')")
    стр.wait_for_timeout(300)
    назад = стр.evaluate(ЗАМЕР)
    for ключ in ("признак", "акцент", "шапкаОснова", "входОснова", "значок", "прил"):
        if назад[ключ] != до[ключ]:
            плохо(где, f"«Бирюзовый» не вернул {ключ}: было {str(до[ключ])[:60]}, стало {str(назад[ключ])[:60]}")
    if ш == 1440 and not ночь:
        ан2 = стр.evaluate(АНАЛИТИКА)
        if not ан2 or not ан2["бир"]:
            плохо(где, f"после возврата к бирюзе аналитика не бирюзовая: {ан2}")
        стр.evaluate("() => { try { closeStats(); } catch (e) {} }")
    д2 = стр.evaluate(ДОКУМЕНТ)
    if синий(д2["акцент"]) or not д2["логотипОснова"] or д2["снимокТон"]:
        плохо(где, "после возврата к бирюзе документ или снимок остались синими")
    if ошибки:
        плохо(где, "ошибки страницы: " + "; ".join(ошибки)[:200])
    к.close()
    print(f"  {где}: бирюза {до['акцент']} → синий {после['акцент']}")


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=хром(), args=["--no-sandbox"])
            for бланк in (False, True):
                for ночь in (False, True):
                    for ш, в in ((390, 844), (1440, 900)):
                        try:
                            проверить(бр, порт, ш, в, бланк, ночь)
                        except Exception as e:
                            плохо(f"{бланк}/{ночь}/{ш}", f"проба оборвалась: {e!s:.300}")
            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: по умолчанию бирюза; «Синий» в настройках перекрашивает страницу, логотипы, "
          "значки, отдельные документы и лист клиента и уходит в аккаунт; «Бирюзовый» "
          "возвращает всё как было.")


if __name__ == "__main__":
    главная()
