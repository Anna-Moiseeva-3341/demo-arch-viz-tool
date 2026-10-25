from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import resolve

IMPLEMENTED_RULES = ["S1", "C1", "C2", "C3", "C4", "C5", "C6", "C7"]
COMPOSE_FILE_NAMES = ["compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml"]

KNOWN_IMAGES = {
    "postgres": ("Database", "postgres"),
    "mysql": ("Database", "mysql"),
    "mongo": ("Database", "mongo"),
    "redis": ("Database", "redis"),
    "rabbitmq": ("MessageBroker", "rabbitmq"),
    "kafka": ("MessageBroker", "kafka")
}

@dataclass
class ComposeProject:
    application: str
    file: Path
    services: dict
    kinds: dict = field(default_factory=dict)
    names: dict = field(default_factory=dict)
    env: dict = field(default_factory=dict)

def find_compose_file(project):
    for name in COMPOSE_FILE_NAMES:
        if (project / name).is_file():
            return project / name
    raise FileNotFoundError(f"В {project} нет файла Compose({', '.join(COMPOSE_FILE_NAMES)})")

def image_base_name(image):
    last_part = image.split("@")[0].rsplit("/", 1)[-1]
    return last_part.split(":")[0].lower()

def classify(svc):
    if "build" in svc:
        return "Service", {"origin": "own"}, "C1"
    known = KNOWN_IMAGES.get(image_base_name(svc.get("image", "")))
    if known:
        node_type, kind = known
        return node_type, {"kind": kind}, "C2"
    return "Service", {"origin": "external"}, "C3"

def depends_on(svc):
    return list(svc.get("depends_on") or [])

def ports(svc):
    result = []
    for port in svc.get("ports") or []:
        if isinstance(port, dict):
            host_port = port.get("published")
            result.append(f"{host_port}:{port['target']}" if host_port else str(port["target"]))
        else:
            result.append(str(port))
    return result

def aliases(name, svc):
    found = [svc.get("container_name")]
    networks = svc.get("networks")
    if isinstance(networks, dict):
        for network in networks.values():
            found += (network or {}).get("aliases", [])
    return [a for i, a in enumerate(found) if a and a != name and a not in found[:i]]

def env_file_paths(svc):
    files = svc.get("env_file") or []
    if isinstance(files, (str, dict)):
        files = [files]
    return [f["path"] if isinstance(f, dict) else f for f in files]

def read_env_file(path):
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env

def environment(svc):
    env = svc.get("environment") or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) for item in env if "=" in item)
    return {key: str(value) for key, value in env.items() if value is not None}

def collect_env(base_dir, svc, source, graph, name):
    env = {}
    for file_name in env_file_paths(svc):
        path = base_dir / file_name
        if path.is_file():
            env.update({k: (v, file_name) for k, v in read_env_file(path).items()})
        else:
            graph.warn(f"{source}: у {name} указан env_file {file_name}, но файла нет")
    env.update({k: (v, source) for k, v in environment(svc).items()})
    return env

def link_by_environment(info, graph):
    for name in info.services:
        if info.kinds[name] != "Service":
            continue
        for key, (value, source) in info.env[name].items():
            if not resolve.is_address_key(key):
                continue
            host = resolve.host_of(value)
            if host is None:
                continue
            target = resolve.component_for(host, info.names)
            if target is None:
                graph.add_unresolved(service=name, variable=key, host=host, source=source)
                continue
            if target == name:
                continue
            edge_type = "CALLS" if info.kinds[target] == "Service" else "CONNECTS_TO"
            graph.add_edge(edge_type, name, target, "C5", source, variables=[key])

def extract(project, graph):
    path = find_compose_file(project)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    source = path.name

    app = data.get("name") or project.resolve().name
    graph.add_node(app, "Application", "S1", source)

    services = {name: svc or {} for name, svc in (data.get("services") or {}).items()}
    info = ComposeProject(application=app, file=path, services=services)

    for name, svc in services.items():
        node_type, props, rule = classify(svc)
        graph.add_node(name, node_type, rule, source, **props)
        graph.add_edge("CONTAINS", app, name, "S1", source)
        info.kinds[name] = node_type
        info.names[name] = name
        info.env[name] = collect_env(path.parent, svc, source, graph, name)

        if service_ports := ports(svc):
            graph.add_node(name, node_type, "C6", source, ports=service_ports)

        if service_aliases := aliases(name, svc):
            graph.add_node(name, node_type, "C7", source, aliases=service_aliases)
            for alias in service_aliases:
                info.names[alias] = name

    for name, svc in services.items():
        for dependency in depends_on(svc):
            if dependency in services:
                graph.add_edge("STARTS_AFTER", name, dependency, "C4", source)
            else:
                graph.warn(f"{source}: {name} зависит от несуществующего сервиса {dependency}")

    link_by_environment(info, graph)

    return info 