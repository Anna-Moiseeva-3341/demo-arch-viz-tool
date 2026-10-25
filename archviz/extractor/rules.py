EXPLICIT = "explicit"
INFERRED = "inferred"

RULES = {
    "S1": ("компоненты описаны в одном compose-файле -> Application, CONTAINS", INFERRED),
    "C1": ("build -> Service {origin: own}", EXPLICIT),
    "C2": ("image из словаря -> Database/MessageBroker {kind}", INFERRED),
    "C3": ("image не из словаря и без build -> Service {origin: external}", INFERRED),
    "C4": ("depends_on -> STARTS_AFTER", EXPLICIT),
    "C5": ("значение в environment ссылается на компонент -> CALLS/CONNECTS_TO", INFERRED),
    "C6": ("ports -> свойство ports", EXPLICIT),
    "C7": ("container_name, aliases -> свойство aliases", EXPLICIT),
}