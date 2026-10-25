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