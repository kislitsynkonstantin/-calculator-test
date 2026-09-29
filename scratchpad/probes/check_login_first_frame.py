#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Без сохранённого входа экран входа стоит с первого кадра, калькулятор не мелькает.

Константин 30.09.2026: «зашёл с другого компьютера по тестовому домену,
сначала на секунду загрузился калькулятор, а потом встал экран входа». Экран
входа показывал общий скрипт в конце документа — после разбора всего файла и
ответа getSession(), а браузер к этому времени уже рисовал калькулятор.

Проба смотрит на страницу в тот миг, когда разборщик дошёл до шапки
калькулятора (общий скрипт ещё не выполнен), и на каждом кадре до загрузки:

  • входа на устройстве нет — экран входа уже стоит, и ни в одном кадре
    калькулятор не виден без него;
  • входа нет, но почта прошлого входа помнится — экран уже в виде
    повторного входа, с именем;
  • вход сохранён — экран входа не появляется ни в одном кадре (обратной
    вспышки нет);
  • ссылка восстановления пароля — экран входа не ставится: её встречает окно
    нового пароля.

    python3 check_login_first_frame.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_preset_chip as м
from playwright.sync_api import sync_playwright

НАХОДКИ = []
КЛЮЧ = "sb-jogylulfstjsznduirub-auth-token"

# Сессии нет: getSession отвечает пусто, с задержкой, как сеть.
БЕЗ_СЕССИИ = """(() => {
  const было = window.supabase.createClient;
  window.supabase.createClient = function () {
    const к = было.apply(this, arguments);
    к.auth.getSession = () => new Promise(r => setTimeout(() => r({ data: { session: null }, error: null }), 400));
    // Настоящая библиотека без сессии шлёт INITIAL_SESSION с пустотой, а не SIGNED_IN.
    к.auth.onAuthStateChange = об => { setTimeout(() => { try { об('INITIAL_SESSION', null); } catch (e) {} }, 0);
      return { data: { subscription: { unsubscribe() {} } } }; };
    return к;
  };
})();"""

# Кадры: в миг, когда разобрана шапка, и на каждом кадре до загрузки.
КАДРЫ = """(() => {
  window.__кадры = []; window.__уШапки = null;
  const вид = () => {
    const э = document.getElementById('loginScreen'), ш = document.getElementById('versionBadge');
    const вход = !!э && getComputedStyle(э).display !== 'none';
    return { вход, шапка: !!ш, повтор: !!э && э.classList.contains('repeat'),
             кто: (document.getElementById('loginWhoName') || {}).textContent || '' };
  };
  new MutationObserver((_, н) => {
    if (document.getElementById('versionBadge')) { window.__уШапки = вид(); н.disconnect(); }
  }).observe(document, { childList: true, subtree: true });
  const шаг = () => { window.__кадры.push(вид()); if (window.__кадры.length < 400) requestAnimationFrame(шаг); };
  requestAnimationFrame(шаг);
})();"""


def прогон(бр, порт, имя, сессия, память, хвост=""):
    к = бр.new_context(viewport={"width": 1440, "height": 900})
    стр = к.new_page()
    ошибки = []
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.add_init_script(м.ЗАГЛУШКА)
    стр.add_init_script(м.ТАБЛИЦЫ_JS)
    if not сессия:
        стр.add_init_script(БЕЗ_СЕССИИ)
    подготовка = f"localStorage.removeItem('{КЛЮЧ}'); localStorage.removeItem('bm_last_login');"
    if сессия:
        подготовка += f"localStorage.setItem('{КЛЮЧ}', JSON.stringify({{access_token:'проба'}}));"
    if память:
        подготовка += "localStorage.setItem('bm_last_login', JSON.stringify({email:'proba@example.ru', имя:'Проба Пробная'}));"
    стр.add_init_script("if (location.protocol === 'http:') { " + подготовка + " }")
    стр.add_init_script(КАДРЫ)
    стр.goto(f"http://127.0.0.1:{порт}/index.html{хвост}", wait_until="load")
    стр.wait_for_timeout(3000)
    у = стр.evaluate("() => window.__уШапки")
    кадры = стр.evaluate("() => window.__кадры")
    конец = стр.evaluate("() => getComputedStyle(document.getElementById('loginScreen')).display")
    for о in [о for о in ошибки if "supabase.co" not in о][:3]:
        НАХОДКИ.append(f"[{имя}] ошибка страницы: {о[:160]}")
    к.close()
    return у, кадры, конец


def главная():
    с, порт = м.сервер()
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=м.хром(), args=["--no-sandbox"])

            у, кадры, конец = прогон(бр, порт, "нет входа", False, False)
            if not у or not у["вход"]:
                НАХОДКИ.append(f"[нет входа] у разобранной шапки экрана входа ещё нет: {у}")
            голые = [i for i, к in enumerate(кадры) if к["шапка"] and not к["вход"]]
            if голые:
                НАХОДКИ.append(f"[нет входа] калькулятор виден без экрана входа в {len(голые)} кадрах, первый — №{голые[0]}")
            if конец == "none":
                НАХОДКИ.append("[нет входа] после загрузки экрана входа нет")

            у, кадры, конец = прогон(бр, порт, "помнит почту", False, True)
            if not у or not у["вход"] or not у["повтор"] or "Проба" not in у["кто"]:
                НАХОДКИ.append(f"[помнит почту] у разобранной шапки нет повторного входа с именем: {у}")

            у, кадры, конец = прогон(бр, порт, "вход сохранён", True, False)
            вспышки = [i for i, к in enumerate(кадры) if к["вход"]]
            if (у and у["вход"]) or вспышки:
                НАХОДКИ.append(f"[вход сохранён] экран входа мелькнул: у шапки {у and у['вход']}, кадров {len(вспышки)}")
            if конец != "none":
                НАХОДКИ.append("[вход сохранён] после загрузки стоит экран входа")

            у, кадры, конец = прогон(бр, порт, "восстановление", False, False, "#type=recovery")
            if у and у["вход"]:
                НАХОДКИ.append("[восстановление] экран входа поставлен поверх ссылки восстановления пароля")

            бр.close()
    finally:
        с.shutdown()
    if НАХОДКИ:
        print("НАХОДКИ:")
        for н in НАХОДКИ:
            print("  ✗", н)
        raise SystemExit(1)
    print("Чисто: без сохранённого входа экран входа стоит уже у разобранной шапки и калькулятор "
          "не виден ни в одном кадре; помнящий почту сразу в виде повторного входа; при сохранённом "
          "входе экран не мелькает; ссылку восстановления пароля ранний шаг не трогает.")


if __name__ == "__main__":
    главная()
