from extractor.resolve import component_for, host_of, is_address_key

def test_address_keys():
    for key in ["DB_URL", "REDIS_HOST", "MONGO_URI", "AMQP_URL", "db_host"]:
        assert is_address_key(key)
    for key in ["DB_NAME", "POSTGRES_USER", "POSTGRES_DB", "LOG_LEVEL"]:
        assert not is_address_key(key)

def test_host_of_url_dsn():
    assert host_of("postgresql://users:pass@users-db:5432/users") == "users-db"
    assert host_of("amqp://guest:guest@broker:5672/") == "broker"
    assert host_of("http://books:8000") == "books"
    assert host_of("https://api.mail.example.com") == "api.mail.example.com"
    assert host_of("cache") == "cache"
    assert host_of("cache:6379") == "cache"
    assert host_of("users_db") == "users_db"

def test_host_rejects():
    assert host_of("") is None
    assert host_of("a b") is None
    assert host_of("/var/lib/data") is None

def test_component_user_aliases():
    names = {"catalog": "catalog", "books": "catalog"}
    assert component_for("books", names) == "catalog"
    assert component_for("Catalog", names) == "catalog"
    assert component_for("reports", names) is None