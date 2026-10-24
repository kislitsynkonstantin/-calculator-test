# Снимки нынешнего блока согласования (сняты пробой из сборки v2.5.20) — в тело макета.
# python3 approval-simple-v1-вшить.py <папка со снимками ap-blk-*.png>
import sys, pathlib, base64, io
from PIL import Image
ТУТ = pathlib.Path(__file__).parent
папка = pathlib.Path(sys.argv[1])
т = (ТУТ / 'approval-simple-v1.tpl.html').read_text()
for ф in sorted(папка.glob('ap-blk-*.png')):
    н = ф.name.split('-')[2]
    im = Image.open(ф).convert('RGB')
    б = io.BytesIO(); im.save(б, 'JPEG', quality=86, optimize=True)
    т = т.replace(f'@@IMG_{н}@@', 'data:image/jpeg;base64,' + base64.b64encode(б.getvalue()).decode())
assert '@@IMG_' not in т, 'не все снимки вшиты'
(ТУТ / 'approval-simple-v1.body.html').write_text(т)
print('тело', len(т))
