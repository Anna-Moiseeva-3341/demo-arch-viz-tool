import textwrap

from extractor import compose
from extractor.model import Graph

def run(tmp_path, text):
    (tmp_path / "docker-compose.yml").write_text(textwrap.dedent(text), encoding="utf-8")
    g = Graph()
    info = compose.extract(tmp_path, g)
    return g.to_dict("0.1", info.application, compose.IMPLEMENTED_RULES), info

def nodes(model):
    return {n["id"]: n for n in model["nodes"]}

def edges(model):
    return {(e["type"], e["from"], e["to"]) for e in model["edges"]}

def test_application_name_from_field_or_directory(tmp_path):
    model, _ = run(tmp_path, "name: shop\nservices: {}\n")
    assert model["application"] == "shop"
    model, _ = run(tmp_path, "services: {}\n")
    assert model["application"] == tmp_path.name

def test_classification(tmp_path):
    model, _ = run(tmp_path, """
    services:
        api: {build: ./api, image: myorg/api:1.0}
        db: {image: docker.io/library/postgres:18}
        mq: {image: rabbitmq:4-management}
        tool: {image: acme/reporter:2.1}
    """)
    n = nodes(model)
    assert(n["api"]["type"], n["api"]["origin"]) == ("Service", "own")
    assert (n["db"]["type"], n["db"]["kind"]) == ("Database", "postgres")
    assert (n["mq"]["type"], n["mq"]["kind"]) == ("MessageBroker", "rabbitmq")
    assert (n["tool"]["type"], n["tool"]["origin"]) == ("Service", "external")

def test_forms_and_missing_service(tmp_path):
    model, _ = run(tmp_path, """
    services:
        a: {build: ., depends_on: [b]}
        b: {build: ., depends_on: {c: {condition: service_healthy}, ghost: {}}}
        c: {image: redis:8}
    """)
    assert {("STARTS_AFTER", "a", "b"), ("STARTS_AFTER", "b", "c")} <= edges(model)
    assert not any(e[2] == "ghost" for e in edges(model))
    assert any("ghost" in w for w in model["warnings"])

def test_ports_and_aliases(tmp_path):
    model, info = run(tmp_path, """
    services:
        a:
            build: .
            ports: ["8080:8000", {target: 9000, published: 9090}]
            hostname: myhost
            networks:
                backend:
                    aliases: [books]
    """)
    a = nodes(model)["a"]
    assert a["ports"] == ["8080:8000", "9090:9000"]
    assert a["aliases"] == ["books"]
    assert "myhost" not in a["aliases"]
    assert info.names["books"] == "a"

def test_c5_links(tmp_path):
    model, _ = run(tmp_path, """
    services:
        a:
            build: .
            environment:
                B_URL: http://bee:8000
                DB_HOST: db
                DB_NAME: a
                MQ_URL: amqp://guest:guest@mq:5672/
                DEAD_URL: http://ghost:8000
                MAIL_URL: https://mail.example.com
        b:
            build: .
            networks:
                backend:
                    aliases: [bee]
        db:
            image: postgres:18
            environment:
                - POSTGRES_USER=a
        mq:
            image: rabbitmq:4
    """)
    e = edges(model)
    assert ("CALLS", "a", "b") in e
    assert("CONNECTS_TO", "a", "db") in e
    assert("CONNECTS_TO", "a", "mq") in e
    assert not any(src == dst for _, src, dst in e)
    assert not any(src == "db" for _, src, _ in e)
    unresolved = {f["host"] for f in model["unresolved"]}
    assert unresolved == {"ghost", "mail.example.com"}