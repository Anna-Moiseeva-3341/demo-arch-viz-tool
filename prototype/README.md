# Приложение для проверки работы экстрактора

Сервис библиотеки: есть каталог книг, в нем для каждой книги указано название и число доступных экземпляров, читатели берут книги из каталога.
Содержит сервисы на Python, Postgres, MongoDB, Redis, RabbitMQ и внешнюю систему: почтовый API (вымышленный, используется для демонстрации работы с внешними зависимостями).

## Структура проекта
- `docker-compose.yml` - конфигурация развёртывания
- `services/*/main.py` - исходный код сервисов
- `ground_truth.json` - эталонная модель проекта (для валидации)


## Запуск
```
docker compose up --build
```

## Проверка работоспособности
```
curl http://localhost:8080/api/books
curl http://localhost:8080/api/users/1
curl -X POST http://localhost:8080/api/holds -H "Content-Type: application/json" -d '{"user_id": 1, "book_id": 2}'
curl -X POST http://localhost:8080/api/holds -H "Content-Type: application/json" -d '{"user_id": 2, "book_id": 2}'
docker compose logs
# должно появиться уведомление "ID брони [1]: книга Капитанская дочка"
# второй запрос должен вернуть код 409 (книга 2 не имеет доступных экземпляров)
```