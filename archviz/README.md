# экстрактор архитектурной модели

## установка
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## запуск
```
python -m extractor ../prototype -o out/model.json
pytest
```

## структура
- `extractor/rules.py` - список правил
- `extractor/model.py` - граф модели и происхождение элементов
- `extractor/compose.py` - правила Docker Compose
- `extractor/resolve.py` - нормализация данных модели
- `loader/` - загрузка модели в neo4j
- `tests/` - тесты правил

## загрузка в neo4j
```
docker compose up -d
python -m loader out/model.json
```

## сравнение с эталоном
Эталонная модель (`../prototype/ground_truth.json`) загружается в Neo4j как отдельное приложение `library-truth`, после чего результат экстрактора сравнивается с ней через запросы.
```
python -m extractor ../prototype -o out/model.json
python -m loader out/model.json
python -m loader ../prototype/ground_truth.json --application library-truth
```
Сравнивается та часть эталона, которую должны находить реализованные правила (S1, C1-C7).
```
// количество узлов (ожидается 28/11/11)
MATCH (t:Element {application: 'library-truth'})
WITH t, any(r IN t.expected_rules WHERE r = 'S1' OR r STARTS WITH 'C') AS now,
EXISTS { MATCH (:Element {application: 'library', id: t.id}) } AS found RETURN count(*) AS reference,
sum(CASE WHEN now THEN 1 ELSE 0 END) AS expected,
sum(CASE WHEN found THEN 1 ELSE 0 END) AS found_count;

// количество связей (ожидается: 48/28/28)
MATCH (a:Element {application: 'library-truth'})-[t]->(b)
WITH a, t, b, any(r IN t.expected_rules WHERE r = 'S1' OR r STARTS WITH 'C') AS now,
EXISTS {
    MATCH (:Element {application: 'library', id: a.id})-[m]->(:Element {application: 'library', id: b.id})
    WHERE type(m) = type(t)
} AS found RETURN count(*) AS reference,
sum(CASE WHEN now THEN 1 ELSE 0 END) AS expected,
sum(CASE WHEN found THEN 1 ELSE 0 END) AS found_count;

// лишние связи - отсутствуют в эталоне (ожидается пустой результат)
MATCH (a:Element {application: 'library'})-[m]->(b)
WHERE NOT EXISTS {
    MATCH (:Element {application: 'library-truth', id: a.id})-[t]->(:Element {application: 'library-truth', id: b.id})
    WHERE type(t) = type(m)
} RETURN a.id AS source, type(m) AS relation, b.id AS target;

// пропущенные связи (ожидается пустой результат)
MATCH (a:Element {application: 'library-truth'})-[t]->(b)
WHERE any(r IN t.expected_rules WHERE r = 'S1' OR r STARTS WITH 'C')
AND NOT EXISTS {
    MATCH (:Element {application: 'library', id: a.id})-[m]->(:Element {application: 'library', id: b.id})
    WHERE type(m) = type(t)
} RETURN a.id AS source, type(t) AS relation, b.id AS target;

// поиск ложных узлов и связей (ожидается пустой результат)
MATCH (a:Element {application: 'library'})-[r]->(b)
WHERE [a.id, b.id] IN [['gateway', 'reports'], ['users-db', 'users'], ['holds-db', 'holds'], ['holds', 'holds'], ['holds', 'notifications']] OR b.id IN ['reports', 'books']
RETURN a.id AS source, type(r) AS relation, b.id AS target;

// эталон (часть, которая покрыта реализованными правилами)
MATCH (a:Element {application: 'library-truth'})-[t]->(b)
WHERE any(r IN t.expected_rules WHERE r = 'S1' OR r STARTS WITH 'C')
RETURN a, t, b;

// для визуального сравнения: взаимодействия в модели экстрактора
MATCH p = (a:Element {application: 'library'})-[:CALLS|CONNECTS_TO]->(b) RETURN p;

// для визуального сравнения: те же взаимодействия в эталоне
MATCH p = (a:Element {application: 'library-truth'})-[t:CALLS|CONNECTS_TO]->(b)
WHERE any(r IN t.expected_rules WHERE r STARTS WITH 'C')
RETURN p;
```

## запросы neo4j для проверки
```
// просмотр модели приложения
MATCH (n:Element {application: 'library'})
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m;

// архитектура взаимодействий узлов
MATCH p = (a: Element {application: 'library'})-[:CALLS|CONNECTS_TO]->(b)
RETURN p;

// анализ влияния (какие компоненты затронет отказ catalog-db)
MATCH p = (s:Service {application: 'library'})-[:CALLS|CONNECTS_TO*1..3]->(:Database {id: 'catalog-db'})
RETURN p;

// выведенные связи узлов
MATCH (a:Element {application: 'library'})-[r]->(b)
WHERE r.confidence = 'inferred'
RETURN a.id AS откуда, type(r) AS связь, b.id AS куда, r.rules AS правила, r.variables AS переменные
ORDER BY откуда;

// вызовы, которых нет в порядке запуска (depends_on)
MATCH (a:Service {application: 'library'})-[:CALLS]->(b:Service)
WHERE NOT (a)-[:STARTS_AFTER]->(b)
RETURN a.id AS сервис, b.id AS вызывает;

// точки входа
MATCH (n:Element {application: 'library'})
WHERE n.ports IS NOT NULL
RETURN n.id AS компонент, n.ports AS порты;
```