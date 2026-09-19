#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба комплектаций: добор из нижнего уровня и копирование из чужого проекта.

19.09.2026, по двум снимкам Константина. Комплектация хранит список опций, а
цены за ними принадлежат проекту, — отсюда обе беды: верхний уровень каждый раз
добирают из нижнего вручную, а копирование из другого проекта молча приносит
чужие деньги.

Проба держит четыре правила и одно обещание:

  • полоса над списком показывает, сколько опций не хватает из нижнего уровня,
    и «Добрать» переносит ровно их;
  • добор ничего не удаляет: своё в верхнем уровне остаётся, снятые базовые
    опции не трогаются — иначе нажатие меняло бы деньги в собранной
    комплектации;
  • диалог копирования называет числа до нажатия: с ценой, нулём, отсутствующие
    в каталоге, ручные с чужими ценами;
  • ручная позиция из чужого проекта приезжает с меткой «проверить цену», и
    метка снимается нажатием;
  • замок «комплектации готовы» не закрывается, пока метки не сняты.

Обещание — «сделанные комплектации не сломай»: состав, пришедший из базы,
не должен измениться ни от открытия редактора, ни от переключения вкладок.

    python3 check_kits_copy.py
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

# Корень можно подменить: так проба проверяется возвращением дефекта — её
# гоняют по прежней версии файла и смотрят, что она краснеет.
КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
ПРОЕКТ = "Проба 6×4"
ЧУЖОЙ = "Чужой 9×5"
ПУСТОЙ = "Пустой 4×4"
НАХОДКИ = []


def хром():
    из_среды = os.environ.get("BM_CHROMIUM")
    if из_среды and pathlib.Path(из_среды).exists():
        return из_среды
    найденные = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    if not найденные:
        raise SystemExit("Chromium в /opt/pw-browsers не найден — запусти "
                         ".claude/hooks/session-start.sh")
    return str(найденные[-1])


ХРОМ = хром()


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def плохо(текст):
    НАХОДКИ.append(текст)


def спросить(стр, js, *арг):
    """Вычисление на странице, которое может не найти новой функции.

    Проба проверяется возвращением дефекта — прогоном по прежней версии файла,
    где ни полосы добора, ни метки ещё нет. Падение на первой же отсутствующей
    функции показало бы одну находку вместо всех, и остальные проверки остались
    бы непроверенными сами.
    """
    try:
        return стр.evaluate(js, *арг)
    except Exception as e:
        плохо("на странице нет того, что проверяется: " + str(e).split("\n")[0][:120])
        return None


# Два проекта: в один копируем, из другого копируют. Цены стоят только у части
# опций — иначе «встанут нулём» нечем было бы проверить.
def проект(имя, порядок, кровля="двускатная", этажей=1):
    return {"product": "frame", "sort": порядок, "slug": имя, "name": имя,
            "price_100": 1000000, "price_150": 1200000, "price_200": 1400000,
            "floors": этажей, "roof_type": кровля, "warm": True,
            "open_area": 10, "closed_area": 20, "facade_area": 60,
            "paint_area": 60, "roof_area": 40}


ТАБЛИЦЫ = {
    "pricing_projects": [проект(ПРОЕКТ, 1), проект(ЧУЖОЙ, 2),
                         проект(ПУСТОЙ, 3, кровля="односкатная", этажей=2)],
    "pricing_matrix": [],
    "pricing_options": [],
    "pricing_sections": [],
    "project_kits": [],
    "project_kit_locks": [],
    "profiles": [{"id": "u-проба", "role": "admin", "full_name": "Проба"}],
}

# Опции берём не выдуманные, а первые платные из каталога самой страницы:
# добор фильтрует по KOMPL_OPT_MAP, и на выдуманных именах проба зеленела бы,
# ничего не проверив.
ПОДГОТОВКА = """async () => {
  const беда = document.getElementById('pricingErrorScreen');
  if (беда) беда.style.display = 'none';
  const индекс = PROJECTS.findIndex(p => p[0] === %s);
  if (индекс < 0) return { беда: 'проекта нет в списке' };
  selectProjectOption(индекс);
  await new Promise(r => setTimeout(r, 400));
  const платные = OPTIONS.filter(o => !o.included && o.status !== 'legacy').slice(0, 7);
  if (платные.length < 7) return { беда: 'в каталоге меньше семи платных опций' };
  const ид = платные.map(o => o.id);
  // Одна опция обязана остаться без цены — иначе «встанут нулём» проверять
  // нечем. Своя цена в файле у неё тоже снимается.
  платные[5].price = null;
  const цены = {};
  ид.forEach((и, н) => { if (н !== 5) цены[и] = 10000 * (н + 1); });
  PRICE_MATRIX[%s] = Object.assign(PRICE_MATRIX[%s] || {}, цены);
  PRICE_MATRIX[%s] = Object.assign(PRICE_MATRIX[%s] || {}, цены);
  // Строки адресуются ключом проекта, который страница считает сама: выдуманный
  // ключ не совпал бы ни с одной выборкой, и проба зеленела бы на пустом месте.
  const ключ = projectSlug(%s), ключЧужого = projectSlug(%s);
  window.__ТАБЛИЦЫ.project_kits = [
    // «Стандарт» — пять опций; «Комфорт» — две из них плюс своя шестая.
    { project_key: ключ, name: 'Стандарт', option_ids: ид.slice(0, 5), base_off: [], custom_items: [] },
    { project_key: ключ, name: 'Комфорт', option_ids: [ид[0], ид[1], ид[6]], base_off: [], custom_items: [] },
    { project_key: ключ, name: 'Тёплый контур', option_ids: [], base_off: [], custom_items: [] },
    { project_key: ключ, name: 'Премиум', option_ids: [], base_off: [], custom_items: [] },
    // Чужой проект: набор с ценой, без цены и ручная позиция со своей суммой.
    { project_key: ключЧужого, name: 'Стандарт',
      option_ids: [ид[2], ид[5]], base_off: [],
      custom_items: [{ id: 'cu_чужая', name: 'Терраса по проекту', price: 145000, section: 'extra' }] },
  ];
  await loadKitsForCurrentProject();
  return { ид };
}""" % (json.dumps(ПРОЕКТ, ensure_ascii=False), json.dumps(ПРОЕКТ, ensure_ascii=False),
        json.dumps(ПРОЕКТ, ensure_ascii=False), json.dumps(ЧУЖОЙ, ensure_ascii=False),
        json.dumps(ЧУЖОЙ, ensure_ascii=False), json.dumps(ПРОЕКТ, ensure_ascii=False),
        json.dumps(ЧУЖОЙ, ensure_ascii=False))

СОСТАВ = """() => {
  const с = {};
  kitKeys().forEach(k => { с[k] = [...(KOMPL_CONFIGS[k] || [])].sort(); });
  с._базовыеСняты = {};
  kitKeys().forEach(k => { с._базовыеСняты[k] = [...(KOMPL_BASE_OFF[k] || [])].sort(); });
  с._ручные = KOMPL_CUSTOM.map(ci => ci.name + '|' + ci.price).sort();
  return с;
}"""


def главная():
    с, порт = сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=ХРОМ, args=["--no-sandbox"])
            стр = бр.new_page(viewport={"width": 1440, "height": 900})
            ошибки = []
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.add_init_script(ЗАГЛУШКА)
            стр.add_init_script(
                "window.__ТАБЛИЦЫ = window.__ТАБЛИЦЫ || {};\n"
                "Object.assign(window.__ТАБЛИЦЫ, "
                + json.dumps(ТАБЛИЦЫ, ensure_ascii=False) + ");\n"
                "window.addEventListener('DOMContentLoaded', function () {\n"
                "  window._sbProfile = { role: 'admin', full_name: 'Проба' };\n"
                "});")
            стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
            стр.wait_for_timeout(2500)
            готово = стр.evaluate(ПОДГОТОВКА)
            if готово.get("беда"):
                плохо("подготовка не удалась: " + готово["беда"])
                бр.close()
                return
            проверить(стр)
            проверить_сборку(стр)
            важные = [о for о in ошибки if "supabase.co" not in о and "цены" not in о]
            for о in важные[:3]:
                плохо("ошибка страницы: " + о[:160])
            бр.close()
    finally:
        с.shutdown()

    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        sys.exit(1)
    print("Чисто: добор из нижнего уровня, разбор в диалоге, метка «проверить цену», "
          "замок, неприкосновенность собранного состава и сборка по образцу.")


def проверить(стр):
    # ── обещание: открытие редактора ничего не меняет ────────────────────────
    было = стр.evaluate(СОСТАВ)
    стр.evaluate("() => { openKompl(); switchKomplTab('editor'); }")
    стр.wait_for_timeout(500)
    for вкладка in ("econom", "standart", "comfort", "premium"):
        стр.evaluate("(к) => switchKedTab(к)", вкладка)
        стр.wait_for_timeout(80)
    стало = стр.evaluate(СОСТАВ)
    if было != стало:
        плохо("состав комплектаций изменился от одного открытия редактора — "
              "собранное ломается самим заходом в него")

    # ── полоса добора ────────────────────────────────────────────────────────
    стр.evaluate("() => switchKedTab('comfort')")
    стр.wait_for_timeout(200)
    полоса = спросить(стр, """() => {
      const п = document.getElementById('kedInheritBar');
      const т = document.getElementById('kedInheritTxt');
      const к = document.getElementById('kedInheritBtn');
      if (!п) return { нет: true };
      const видна = getComputedStyle(п).display !== 'none';
      const кор = к ? к.getBoundingClientRect() : null;
      const полосаКор = п.getBoundingClientRect();
      return { видна, текст: т ? т.textContent : '', кнопка: к ? к.textContent : '',
               зазорСправа: кор ? Math.round(полосаКор.right - кор.right) : null,
               высотаКнопки: кор ? Math.round(кор.height) : null };
    }""")
    if полоса is None or полоса.get("нет"):
        плохо("полосы добора нет в разметке вовсе")
        полоса = None
    if полоса and not полоса["видна"]:
        плохо("в «Комфорте» не хватает трёх опций «Стандарта», а полоса добора скрыта")
    if полоса and "3 опций" not in полоса["текст"]:
        плохо(f"полоса считает неверно: «{полоса['текст']}» — не хватает трёх опций")
    if полоса and "Стандарт" not in полоса["кнопка"]:
        плохо(f"кнопка добора не называет уровень: «{полоса['кнопка']}»")
    if полоса and полоса["зазорСправа"] is not None and полоса["зазорСправа"] < 8:
        плохо(f"кнопка добора прижата к краю полосы: {полоса['зазорСправа']} px")

    # ── добор переносит ровно недостающее ────────────────────────────────────
    до = стр.evaluate(СОСТАВ)
    спросить(стр, "() => добратьИзПредыдущего()")
    стр.wait_for_timeout(300)
    после = стр.evaluate(СОСТАВ)
    ушло = set(до["comfort"]) - set(после["comfort"])
    пришло = set(после["comfort"]) - set(до["comfort"])
    if ушло:
        плохо(f"добор убрал из «Комфорта» {len(ушло)} опц. — он обязан только добавлять")
    if len(пришло) != 3:
        плохо(f"добор перенёс {len(пришло)} опц. вместо трёх недостающих")
    if после["standart"] != до["standart"]:
        плохо("добор изменил «Стандарт» — источник трогать нельзя")
    if после["_базовыеСняты"] != до["_базовыеСняты"]:
        плохо("добор тронул снятые базовые опции — это чужие деньги в собранной комплектации")
    ещё = спросить(стр, "() => { const п = document.getElementById('kedInheritBar');"
                        " return п ? getComputedStyle(п).display : 'none'; }")
    if ещё != "none":
        плохо("после добора полоса осталась на месте — расхождения уже нет")

    # ── разбор в диалоге копирования ─────────────────────────────────────────
    стр.evaluate("async () => { await openKomplCopyDialog(); }")
    стр.wait_for_timeout(400)
    индекс = стр.evaluate("""() => _komplCopySources.findIndex(s => s.group === 'remote')""")
    if индекс < 0:
        плохо("в списке источников нет комплектации чужого проекта")
        return
    стр.evaluate("(и) => onKomplCopyPickSource(и)", индекс)
    стр.wait_for_timeout(250)
    разбор = стр.evaluate("""() => document.getElementById('komplCopyOverlay').innerText""")
    стр.locator("#komplCopyOverlay > div").screenshot(
        path=str(pathlib.Path(__file__).parent / "комплектации-разбор.png"))
    if "без цены" not in разбор:
        плохо("диалог не сказал, что опция без цены встанет нулём: «"
              + " ".join(разбор.split())[:140] + "»")
    if "ручная позиция" not in разбор and "ручных позиций" not in разбор:
        плохо("диалог не сказал про ручные позиции с ценами источника")
    if "145 000" not in разбор.replace(" ", " "):
        плохо("диалог не назвал сумму ручных позиций источника")

    # ── ручная приезжает с меткой ────────────────────────────────────────────
    стр.evaluate("(и) => applyKomplCopy(и, 'merge')", индекс)
    стр.wait_for_timeout(400)
    метка = спросить(стр, """() => {
      const ci = KOMPL_CUSTOM.find(x => x.name === 'Терраса по проекту');
      const видно = document.getElementById('kedOptsList').innerText.includes('проверить цену');
      return { есть: !!ci, помечена: !!(ci && ci.проверить), источник: ci ? ci.источник : null, видно };
    }""")
    метка = метка or {}
    if not метка.get("есть"):
        плохо("ручная позиция из чужого проекта не приехала вовсе")
    if not метка.get("помечена"):
        плохо("ручная позиция приехала с чужой ценой и без метки «проверить цену»")
    if not метка.get("видно"):
        плохо("метка «проверить цену» есть в данных, но её не видно в списке")
    if метка.get("источник") and ЧУЖОЙ not in метка["источник"]:
        плохо(f"метка не называет источник: «{метка['источник']}»")
    # Метку смотрим кадром и меркой, а не только в данных: подпись рядом с ценой
    # легко оказывается прижатой к соседу или уехавшей за край строки. Проверка
    # на переполнение этого не видит — формально всё внутри.
    зазоры = спросить(стр, """() => {
      const строки = [...document.querySelectorAll('#kedOptsList > div')];
      const строка = строки.find(э => э.textContent.includes('Терраса по проекту'));
      if (!строка) return { нет: true };
      строка.scrollIntoView({ block: 'center' });
      const метка = [...строка.querySelectorAll('span')]
        .find(э => (э.textContent || '').trim() === 'проверить цену');
      if (!метка) return { безМетки: true };
      const м = метка.getBoundingClientRect();
      const р = строка.getBoundingClientRect();
      const соседи = [...строка.children].filter(э => э !== метка && !э.contains(метка))
        .map(э => э.getBoundingClientRect());
      const щели = соседи.map(с => с.left >= м.right ? с.left - м.right
                                 : (м.left >= с.right ? м.left - с.right : 0));
      return { ближний: Math.round(Math.min(...щели)),
               заКраем: m_за(м, р), высота: Math.round(м.height) };
      function m_за(м, р) { return м.right > р.right + 1 || м.left < р.left - 1; }
    }""")
    if зазоры and зазоры.get("нет"):
        плохо("строки с ручной позицией нет в списке — метку не на чем смотреть")
    elif зазоры and зазоры.get("безМетки"):
        плохо("в строке ручной позиции нет подписи «проверить цену»")
    elif зазоры:
        if зазоры["заКраем"]:
            плохо("метка «проверить цену» вылезла за край строки")
        if зазоры["ближний"] < 6:
            плохо(f"метка «проверить цену» прижата к соседу: {зазоры['ближний']} px")
    try:
        стр.wait_for_timeout(200)
        стр.locator("#kedOptsList div", has_text="Терраса по проекту").last.screenshot(
            path=str(pathlib.Path(__file__).parent / "комплектации-метка.png"))
    except Exception:
        pass

    # ── замок не закрывается поверх метки ────────────────────────────────────
    стр.evaluate("async () => { await toggleKitLock(); }")
    стр.wait_for_timeout(400)
    закрыт = стр.evaluate("() => !!_kitLocks[currentProjectSlug()]")
    if закрыт:
        плохо("замок «комплектации готовы» закрылся поверх непроверенной чужой цены")
    спросить(стр, """() => {
      const ci = KOMPL_CUSTOM.find(x => x.name === 'Терраса по проекту');
      if (ci) снятьМеткуРучной(ci.id);
    }""")
    стр.wait_for_timeout(200)
    стр.evaluate("async () => { await toggleKitLock(); }")
    стр.wait_for_timeout(400)
    if not стр.evaluate("() => !!_kitLocks[currentProjectSlug()]"):
        плохо("метки сняты, а замок всё равно не закрылся")

    # ── кадр целиком: переполнения нет ни на одной ширине ────────────────────
    стр.evaluate("async () => { await toggleKitLock(); openKompl(); switchKomplTab('editor'); }")
    стр.wait_for_timeout(300)
    стр.evaluate("() => switchKedTab('premium')")   # у «Премиума» расхождение есть
    куда = pathlib.Path(__file__).parent
    for ш in (390, 768, 1440):
        стр.set_viewport_size({"width": ш, "height": 900})
        стр.wait_for_timeout(350)
        мера = стр.evaluate("""() => {
          const п = document.getElementById('komplPanel');
          const пер = п.scrollWidth - п.clientWidth;
          const полоса = document.getElementById('kedInheritBar');
          const беды = [];
          if (полоса && getComputedStyle(полоса).display !== 'none') {
            const к = полоса.getBoundingClientRect();
            polосаДети(полоса).forEach(э => {
              const r = э.getBoundingClientRect();
              if (r.right > к.right + 1 || r.left < к.left - 1) beds(э, r);
            });
            function beds(э, r) { беды.push('за краем полосы: ' + (э.id || э.tagName)); }
          }
          function polосаДети(у) { return [...у.children]; }
          return { переполнение: пер, беды };
        }""")
        if мера["переполнение"] > 1:
            плохо(f"[{ш}] окно комплектаций переполнено по горизонтали на {мера['переполнение']} px")
        for б in мера["беды"]:
            плохо(f"[{ш}] {б}")
        стр.locator("#komplPanel").screenshot(path=str(куда / f"комплектации-{ш}.png"))


def проверить_сборку(стр):
    """Сборка всех четырёх уровней по образцу другого проекта.

    Проверяется то, чего глазами не увидеть за один заход: что разбор считает до
    нажатия, что расхождение по кровле названо словами, что уровень, которого у
    образца нет, остаётся пустым, что ручная позиция приезжает помеченной и что
    замок после сборки остаётся открытым — собранное не опубликовано.
    """
    ушли = спросить(стр, """async (имя) => {
      const и = PROJECTS.findIndex(p => p[0] === имя);
      if (и < 0) return { беда: 'пустого проекта нет в списке' };
      selectProjectOption(и);
      await new Promise(r => setTimeout(r, 500));
      openKompl(); switchKomplTab('editor');
      return { опцийСейчас: kitKeys().reduce((с, к) => с + (KOMPL_CONFIGS[к] ? KOMPL_CONFIGS[к].size : 0), 0) };
    }""", ПУСТОЙ)
    if not ушли or ушли.get("беда"):
        плохо("сборка: " + ((ушли or {}).get("беда") or "не удалось перейти в пустой проект"))
        return
    if ушли["опцийСейчас"]:
        плохо(f"сборка: в пустом проекте уже {ушли['опцийСейчас']} опц. — проверять нечего")

    есть = спросить(стр, """() => {
      const к = document.getElementById('kedSeedBtn');
      if (!к) return { нет: true };
      const р = к.getBoundingClientRect();
      return { видна: getComputedStyle(к).display !== 'none', текст: к.textContent.trim(),
               высота: Math.round(р.height) };
    }""")
    if not есть or есть.get("нет"):
        плохо("кнопки «Собрать из проекта…» нет в разметке")
        return
    if not есть["видна"]:
        плохо("кнопка «Собрать из проекта…» не показана администратору")

    стр.evaluate("async () => { await openKomplSeedDialog(); }")
    стр.wait_for_timeout(500)
    индекс = спросить(стр, "(имя) => _komplSeedSources.findIndex(s => s.name === имя)", ЧУЖОЙ)
    if индекс is None or индекс < 0:
        плохо("в списке образцов нет проекта с собранными комплектациями")
        return
    стр.evaluate("(и) => onKomplSeedPick(и)", индекс)
    стр.wait_for_timeout(250)
    разбор = стр.evaluate("() => document.getElementById('komplSeedOverlay').innerText")
    if "Кровля" not in разбор:
        плохо("разбор сборки молчит о разной кровле: «" + " ".join(разбор.split())[:140] + "»")
    if "Этажность" not in разбор:
        плохо("разбор сборки молчит о разной этажности")
    if "проверить цену" not in разбор:
        плохо("разбор сборки не предупреждает про ручные позиции с ценами образца")
    if "145 000" not in разбор.replace("\u00a0", " "):
        плохо("разбор сборки не называет сумму ручных позиций")
    стр.locator("#komplSeedOverlay > div").screenshot(
        path=str(pathlib.Path(__file__).parent / "комплектации-сборка.png"))

    стр.evaluate("(и) => applyKomplSeed(и)", индекс)
    стр.wait_for_timeout(600)
    итог = спросить(стр, """(чужой) => {
      const состав = {};
      kitKeys().forEach(к => { состав[к] = [...(KOMPL_CONFIGS[к] || [])].sort(); });
      const ручная = KOMPL_CUSTOM.find(ci => ci.name === 'Терраса по проекту'
        && kitKeys().some(к => ci.kitChecked && ci.kitChecked[к] === true));
      const окно = document.getElementById('komplSeedOverlay');
      return { состав, помечена: !!(ручная && ручная.проверить),
               источник: ручная ? ручная.источник : null,
               замок: !!_kitLocks[currentProjectSlug()],
               итогВидно: okno_текст(okno_есть()), };
      function okno_есть() { return окно && getComputedStyle(окно).display !== 'none' ? окно : null; }
      function okno_текст(у) { return у ? у.innerText : ''; }
    }""", ЧУЖОЙ)
    итог = итог or {}
    состав = итог.get("состав") or {}
    if len(состав.get("standart") or []) != 2:
        плохо(f"сборка: в «Стандарт» приехало {len(состав.get('standart') or [])} опц. вместо двух")
    for уровень in ("econom", "comfort", "premium"):
        if состав.get(уровень):
            плохо(f"сборка: уровень «{уровень}» заполнен, хотя у образца его нет")
    if not итог.get("помечена"):
        плохо("сборка: ручная позиция приехала без метки «проверить цену»")
    if итог.get("источник") and ЧУЖОЙ not in итог["источник"]:
        плохо(f"сборка: метка не называет образец: «{итог['источник']}»")
    if итог.get("замок"):
        плохо("сборка закрыла замок — собранное оказалось опубликовано без проверки")
    видно = итог.get("итогВидно") or ""
    if "Что проверить" not in видно:
        плохо("после сборки не показан список того, что проверить")
    if "Замок остался открытым" not in видно:
        плохо("в итоге сборки не сказано, что замок остался открытым")
    стр.locator("#komplSeedOverlay > div").screenshot(
        path=str(pathlib.Path(__file__).parent / "комплектации-сборка-итог.png"))
    стр.evaluate("() => closeKomplSeedDialog()")


if __name__ == "__main__":
    главная()
