#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно входа: живое ожидание, предел ожидания, сеть и короткий повторный вход.

Константин 24.09.2026 выбрал в макете login-v3 вид 01 для первого входа и вид
04 для повторного: «первичный и повторный ввод вот так». Проба меряет
поведение и вид, в обеих темах оформления, днём и ночью, на 390 и 1440 px:

  • ожидание: кнопка залита тем же акцентом, что в покое (и под курсором,
    который после нажатия остаётся над ней), в ней
    «Проверяем…» и знак вращения, поля только для чтения; второе нажатие
    второго запроса не шлёт;
  • 15 секунд без ответа — спокойная плашка словами, кнопка «Попробовать
    ещё раз», поля снова правятся (время подгоняется часами браузера);
  • запрос, оборвавшийся на полпути, возвращает кнопку в «Войти» и говорит
    об ошибке — кнопка не застревает;
  • неверный пароль — прежнее «Неверный email или пароль»;
  • нет сети — плашка стоит сразу, до нажатия, и нажатие запроса не шлёт;
  • удачный вход запоминает почту на устройстве, а имя — из профиля;
  • повторный вход: вместо поля почты строка с именем, буквами и почтой,
    «Сменить» возвращает пустое поле почты и забывает прежнего;
  • строка с именем не выходит за лист, «Сменить» не прилипает к краю, палец
    ловит его в 14 px над и под серединой, а нарисован он не выше 22 px.

    python3 check_login_states.py
"""
import functools
import http.server
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get("BM_ROOT")
                      or pathlib.Path(__file__).resolve().parent.parent.parent)
ЗАГЛУШКА = (pathlib.Path(__file__).parent / "stub_sb.js").read_text(encoding="utf-8")
НАХОДКИ = []


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


# Вход подменяется управляемым: «висит», «обрыв», «неверно», «удача».
ПОДМЕНА = """(исход) => {
  window.__входов = 0;
  _sb.auth.signInWithPassword = function () {
    window.__входов++;
    if (исход === 'висит') return new Promise(() => {});
    if (исход === 'обрыв') return Promise.reject(new TypeError('Failed to fetch'));
    if (исход === 'неверно') return Promise.resolve({ data: {}, error: { message: 'Invalid login credentials' } });
    return Promise.resolve({ data: {}, error: null });
  };
}"""

СОСТОЯНИЕ = """() => {
  const кн = document.getElementById('loginBtn'), с = getComputedStyle(кн);
  const н = document.getElementById('loginNote'), о = document.getElementById('loginError');
  const экран = document.getElementById('loginScreen');
  const виден = э => !!э && getComputedStyle(э).display !== 'none' && э.getBoundingClientRect().height > 0;
  return {
    текст: кн.textContent.trim(), ждёт: кн.classList.contains('wait'),
    знак: !!кн.querySelector('.lg-spin'), фон: с.backgroundColor,
    почтаЧтение: document.getElementById('loginEmail').readOnly,
    парольЧтение: document.getElementById('loginPassword').readOnly,
    плашка: виден(н) ? н.textContent : '', ошибка: виден(о) ? о.textContent : '',
    повтор: экран.classList.contains('repeat'),
    полеПочты: виден(document.getElementById('loginEmailFld')),
    кто: виден(document.getElementById('loginWho')) ? document.getElementById('loginWho').textContent.replace(/\\s+/g, ' ').trim() : '',
    почта: document.getElementById('loginEmail').value,
    память: localStorage.getItem('bm_last_login'),
    входов: window.__входов || 0,
  };
}"""

КТО_ГЕОМ = """() => {
  const ряд = document.getElementById('loginWho'), лист = document.querySelector('#loginScreen .lg-paper');
  const см = ряд.querySelector('.lg-who-ch');
  const р = ряд.getBoundingClientRect(), л = лист.getBoundingClientRect(), к = см.getBoundingClientRect();
  const x = к.left + к.width / 2, y = к.top + к.height / 2;
  const ловит = [y - 14, y + 14].every(ty => { const э = document.elementFromPoint(x, ty); return э === см; });
  return { внутри: р.left >= л.left && р.right <= л.right + 0.5,
           доКрая: Math.round(р.right - к.right), высота: Math.round(к.height), ловит,
           обрезано: [...ряд.querySelectorAll('.lg-who-m')].some(м => м.scrollWidth > м.clientWidth + 1) };
}"""


def открыть(бр, порт, ш, в, бланк, ночь, память=None):
    к = бр.new_context(viewport={"width": ш, "height": в})
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(ЗАГЛУШКА)
    стр.clock.install()
    стр.goto(f"http://127.0.0.1:{порт}/index.html", wait_until="load")
    стр.clock.run_for(2500)
    стр.evaluate("""([бланк, ночь, память]) => {
      const б = document.getElementById('pricingErrorScreen'); if (б) б.style.display = 'none';
      applyUiStyle(бланк ? 'blank' : 'light', false);
      applyThemeMode(ночь ? 'dark' : 'light', false);
      if (память) localStorage.setItem('bm_last_login', JSON.stringify(память));
      else localStorage.removeItem('bm_last_login');
      showLoginScreen();
    }""", [бланк, ночь, память])
    return к, стр, ошибки


def ввести(стр):
    стр.fill("#loginEmail", "manager@bania-msk.ru") if стр.is_visible("#loginEmail") else None
    стр.fill("#loginPassword", "проба-пароль")


def проверить(бр, порт, ш, в, бланк, ночь):
    где = f"{'Бланк' if бланк else 'Модерн'} · {'ночь' if ночь else 'день'} · {ш}px"

    # ── первый вход: ожидание, «долго», повтор ──
    к, стр, ошибки = открыть(бр, порт, ш, в, бланк, ночь)
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["повтор"] or not с["полеПочты"]:
        плохо(где, "без памяти об устройстве поля почты нет или стоит строка повторного входа")
    стр.evaluate(ПОДМЕНА, "висит")
    ввести(стр)
    стр.click("#loginBtn")
    стр.clock.run_for(300)
    с = стр.evaluate(СОСТОЯНИЕ)
    if not с["ждёт"] or "Проверяем" not in с["текст"] or not с["знак"]:
        плохо(где, f"в ожидании кнопка не живая: «{с['текст']}», знак {с['знак']}")
    if с["фон"] in ("rgba(0, 0, 0, 0)", "transparent"):
        плохо(где, "в ожидании кнопка погасла до рамки — выглядит выключенной")
    покой = стр.evaluate("() => getComputedStyle(document.querySelector('#loginScreen')).getPropertyValue('--lg-acc').trim()")
    фон_покоя = стр.evaluate("(ц) => { const э = document.createElement('i'); э.style.color = ц; document.body.appendChild(э); const р = getComputedStyle(э).color; э.remove(); return р; }", покой)
    if с["фон"] != фон_покоя:
        плохо(где, f"в ожидании кнопка другого цвета, чем в покое: {с['фон']} против {фон_покоя} — курсор над ней красит её наведением")
    if not (с["почтаЧтение"] and с["парольЧтение"]):
        плохо(где, "в ожидании поля можно править")
    стр.click("#loginBtn", force=True)
    стр.clock.run_for(300)
    if стр.evaluate(СОСТОЯНИЕ)["входов"] != 1:
        плохо(где, "второе нажатие в ожидании отправило второй запрос")
    стр.clock.run_for(15000)
    с = стр.evaluate(СОСТОЯНИЕ)
    if "дольше обычного" not in с["плашка"]:
        плохо(где, f"после 15 секунд нет плашки «долго»: «{с['плашка'][:60]}»")
    if с["ждёт"] or "ещё раз" not in с["текст"]:
        плохо(где, f"после 15 секунд кнопка «{с['текст']}», ждёт {с['ждёт']}")
    if с["почтаЧтение"] or с["парольЧтение"]:
        плохо(где, "после 15 секунд поля так и остались только для чтения")
    if с["ошибка"]:
        плохо(где, "«долго» показано красной ошибкой, а не плашкой")
    # ── обрыв запроса ──
    стр.evaluate(ПОДМЕНА, "обрыв")
    стр.click("#loginBtn")
    стр.clock.run_for(300)
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["ждёт"] or с["текст"] != "Войти" or not с["ошибка"]:
        плохо(где, f"после обрыва кнопка «{с['текст']}», ждёт {с['ждёт']}, ошибка «{с['ошибка']}»")
    if с["плашка"]:
        плохо(где, "после нового нажатия осталась плашка «долго»")
    # ── неверный пароль ──
    стр.evaluate(ПОДМЕНА, "неверно")
    стр.click("#loginBtn")
    стр.clock.run_for(300)
    с = стр.evaluate(СОСТОЯНИЕ)
    if "Неверный email или пароль" not in с["ошибка"] or с["текст"] != "Войти":
        плохо(где, f"неверный пароль: ошибка «{с['ошибка']}», кнопка «{с['текст']}»")
    # ── удача запоминает почту ──
    стр.evaluate(ПОДМЕНА, "удача")
    стр.click("#loginBtn")
    стр.clock.run_for(300)
    с = стр.evaluate(СОСТОЯНИЕ)
    if not с["память"] or "manager@bania-msk.ru" not in с["память"]:
        плохо(где, f"удачный вход не запомнил почту: {с['память']!r}")
    if ошибки:
        плохо(где, "ошибки страницы: " + "; ".join(ошибки)[:200])
    к.close()

    # ── нет сети ──
    к, стр, ошибки = открыть(бр, порт, ш, в, бланк, ночь)
    стр.evaluate(ПОДМЕНА, "удача")
    к.set_offline(True)
    стр.clock.run_for(300)
    с = стр.evaluate(СОСТОЯНИЕ)
    if "Нет связи" not in с["плашка"]:
        плохо(где, "без сети плашки нет до нажатия")
    ввести(стр)
    стр.click("#loginBtn")
    стр.clock.run_for(300)
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["входов"] or с["ждёт"]:
        плохо(где, "без сети нажатие отправило запрос или повисло в ожидании")
    к.set_offline(False)
    стр.clock.run_for(300)
    if "Нет связи" in стр.evaluate(СОСТОЯНИЕ)["плашка"]:
        плохо(где, "сеть вернулась, а плашка «нет связи» осталась")
    к.close()

    # ── повторный вход ──
    к, стр, ошибки = открыть(бр, порт, ш, в, бланк, ночь,
                             {"email": "manager@bania-msk.ru", "имя": "Иван Петров"})
    с = стр.evaluate(СОСТОЯНИЕ)
    if not с["повтор"] or с["полеПочты"]:
        плохо(где, "при памяти об устройстве стоит поле почты, а не строка с именем")
    if "Иван Петров" not in с["кто"] or "ИП" not in с["кто"] or "manager@bania-msk.ru" not in с["кто"]:
        плохо(где, f"строка повторного входа: «{с['кто']}»")
    if с["почта"] != "manager@bania-msk.ru":
        плохо(где, "почта для входа не подставлена в скрытое поле")
    г = стр.evaluate(КТО_ГЕОМ)
    if not г["внутри"] or г["обрезано"]:
        плохо(где, f"строка с именем выходит за лист или обрезана: {г}")
    if г["доКрая"] > 26:
        плохо(где, f"«Сменить» висит в {г['доКрая']} px от края строки")
    if not г["ловит"] or г["высота"] > 22:
        плохо(где, f"«Сменить»: палец ловит {г['ловит']}, нарисован {г['высота']} px")
    стр.click(".lg-who-ch")
    стр.clock.run_for(200)
    с = стр.evaluate(СОСТОЯНИЕ)
    if с["повтор"] or not с["полеПочты"] or с["почта"] or с["память"]:
        плохо(где, f"«Сменить» не вернул пустое поле почты или не забыл прежнего: {с}")
    if ошибки:
        плохо(где, "ошибки страницы: " + "; ".join(ошибки)[:200])
    к.close()
    print(f"  {где}: проверено")


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
    print("Чисто: ожидание живое и ограничено 15 секундами, кнопка не застревает, "
          "нет сети — сказано сразу, повторный вход с именем и «Сменить».")


if __name__ == "__main__":
    главная()
