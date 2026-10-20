# Сборка макетов «Бланка»: base.css + свой css + тело, шрифты и знак вшиты.
# python3 собрать.py <имя>  →  mockups/<имя>.html тестового репозитория
import sys, pathlib, base64
ТУТ = pathlib.Path(__file__).parent
ЛОГО = pathlib.Path('/root/.claude/skills/synced/fa475f62-4013-436c-abd6-e5e9867cf3f1_de16addf-40cf-4f2f-8494-63965e85fc99/design-skill-blank/references/logo')
ШРИФТЫ = pathlib.Path('/home/user/-calculator-test/scratchpad/probes/шрифты_google.css').read_text()
def лого(ф): return 'data:image/png;base64,' + base64.b64encode((ЛОГО / ф).read_bytes()).decode()
имя = sys.argv[1]
заг, тело = (ТУТ / f'{имя}.body.html').read_text().split('\n', 1)
тело = (тело.replace('@@LOGO_DAY@@', лого('banya-msk-day-bmsk.png'))
            .replace('@@LOGO_NIGHT@@', лого('banya-msk-night-bmsk.png')))
свой = (ТУТ / f'{имя}.css').read_text() if (ТУТ / f'{имя}.css').exists() else ''
html = ('<!DOCTYPE html>\n<html lang="ru" data-tone="bmsk">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{заг.strip()}</title>\n<style>{ШРИФТЫ}</style>\n<style>\n'
        + (ТУТ / 'base.css').read_text() + '\n' + (ТУТ / 'mk.css').read_text() + '\n' + свой + '\n</style>\n</head>\n<body>\n' + тело + '\n</body>\n</html>\n')
вых = pathlib.Path('/home/user/-calculator-test/mockups') / f'{имя}.html'
вых.write_text(html)
print(вых, len(html))
