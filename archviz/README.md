# Экстрактор архитектурной модели

## установка
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## запуск
```
python -m extractor ../prototype -o out/model.json
python -m validation ../prototype/ground_truth.json out/model.json --report out/report.md
pytest
```

## структура
- `extractor/rules.py` - список правил
- `extractor/model.py` - граф модели и происхождение элементов
- `extractor/compose.py` - правила Docker Compose
- `extractor/resolve.py` - нормализация данных модели
- `loader/` - загрузка модели в neo4j
- `validation/` - сравнение модели с эталоном: precision, recall и F1 по типам узлов и связей, пропущенные и лишние элементы
- `tests/` - тесты правил

## загрузка в neo4j
```
docker compose up -d
python -m loader out/model.json
```

Neo4j Browser: http://localhost:7474
```
// модель приложения
MATCH (n:Element {application: 'library'})
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m;

// анализ влияния
MATCH p = (s:Service {application: 'library'})-[:CALLS|CONNECTS_TO*1..3]->(:Database {id: 'catalog-db'}) RETURN p;
```

## сравнение с эталоном
```
python -m validation ../prototype/ground_truth.json out/model.json --report out/report.md
```
Отчет выводится в консоль и при указании флага `--report` дополнительно сохраняется в указанном файле. Содержимое отчета:
- precision, recall и F1 для узлов и связей;
- те же метрики без учета элементов, правила которых еще не реализованы;
- пропущенные элементы с разделением на ошибки и ожидаемые пропуски для нереализованных правил, лишние элементы.

Код возврата при наличии ошибок - 1 (лишние элементы, пропуски по реализованным правилам).

Текущий результат (реализованы правила S1, C1-C7): узлы 11/28, связи 28/48, precision 1.00, recall 1.00.