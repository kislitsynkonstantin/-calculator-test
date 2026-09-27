-- Сверка данных: свой пресет в «Моих» и его копия в «Общих» (и по коду).
--
-- Константин 27.09.2026: «сделай проверку: чтобы была полная синхронизация
-- пресетов моих и опубликованных моих … чтобы 100% был синхрон».
--
-- Запускается в базе (проба в контейнере до неё не достаёт). Только чтение.
-- Пара — строка presets и строка preset_links того же автора с тем же
-- preset_id; удалённые пресеты не считаются. Копия в «Общих» собирается так
-- же, как её собирает калькулятор: полный снимок state, поверх — разделы.
-- Различием считается ключ, у которого значения расходятся; «нет ключа»,
-- null, пустой список, пустой объект и пустая строка приравнены друг к другу —
-- старые снимки пишут их по-разному, и это не расхождение данных.
-- savedAt — отметка времени, а не данные, в сравнение не входит.
--
-- Ответ: по одной строке на расходящуюся пару — код, опубликован ли, замок,
-- какая сторона новее по времени сохранения внутри снимка, совпадает ли итог,
-- список расходящихся ключей. Пустой ответ — всё сходится.
with pairs as (
  select l.short_code, l.is_public, l.locked, p.id as preset_id,
         (p.name is not distinct from l.name) as name_eq,
         p.state as ps,
         coalesce(l.state, '{}'::jsonb) || coalesce(l.spec_state, '{}'::jsonb) || coalesce(l.requisites, '{}'::jsonb)
           || coalesce(l.discount, '{}'::jsonb) || coalesce(l.payment_plan, '{}'::jsonb) as ls
  from public.preset_links l
  join public.presets p on p.id = l.preset_id and p.user_id = l.author_id
  where p.deleted_at is null
), d as (
  select short_code, is_public, locked, name_eq,
    case when coalesce(ps->>'savedAt', '') >= coalesce(ls->>'savedAt', '') then 'мои' else 'общие' end as новее,
    (ps->>'totalNum') is not distinct from (ls->>'totalNum') as итог_тот_же,
    (select array_agg(k order by k)
       from (select jsonb_object_keys(ps) k union select jsonb_object_keys(ls)) ks
      where k <> 'savedAt'
        and nullif(nullif(nullif(nullif(ps->k, 'null'::jsonb), '[]'::jsonb), '{}'::jsonb), '""'::jsonb)
            is distinct from
            nullif(nullif(nullif(nullif(ls->k, 'null'::jsonb), '[]'::jsonb), '{}'::jsonb), '""'::jsonb)) as ключи
  from pairs
)
select short_code, is_public, locked, новее, итог_тот_же, name_eq, ключи
from d
where ключи is not null or not name_eq
order by is_public desc, short_code;
