from .compare import Score, show_edge, show_node

def number(value):
    return "-" if value is None else f"{value:.2f}"

def score_row(name, s):
    return (f"| {name} | {len(s.truth)} | {len(s.found)} | {len(s.correct)} "
            f"| {number(s.precision)} | {number(s.recall)} | {number(s.f1)} |")

def score_table(rows):
    out = ["| | Эталон | Найдено | Верно | Precision | Recall | F1 |", "|---|---:|---:|---:|---:|---:|---:|"]
    out += [score_row(name, s) for name, s in rows.items()]
    return out

def items(keys, show, rules = None):
    if not keys:
        return ["нет"]
    result = []
    for k in sorted(keys):
        line = f"- `{show(k)}`"
        if rules and rules.get(k):
            line += f" - ожидаемые правила: {', '.join(rules[k])}"
        result.append(line)
    return result

def build_report(c, truth_path, model_path, model):
    out = ["# Сравнение модели с эталоном", "",
           f"Эталон: `{truth_path}`  ",
           f"Модель: `{model_path}`  ",
           f"Приложение: {model.get('application', '-')}  ",
           f"Включенные правила: {', '.join(model.get('rules_enabled', [])) or '-'}", ""]
    out += ["## Итог", ""] + score_table({"Узлы": c.nodes, "Связи": c.edges})
    implemented = {
        "Узлы": Score(c.nodes.truth - c.deferred, c.nodes.found),
        "Связи": Score(c.edges.truth - c.deferred, c.edges.found),
    }
    if c.deferred:
        out += ["", "Без элементов, правила которых еще не реализованы:", ""] + score_table(implemented)

    out += ["", "## Узлы по типам", ""] + score_table(c.node_types)
    out += ["", "## Связи по типам", ""] + score_table(c.edge_types)
    out += ["", f"## Ловушки: сработало {len(c.traps)}", ""]
    if c.traps:
        for trap, matched in c.traps:
            out.append(f"- {trap.get('reason', '')}: {', '.join(f'`{m}`' for m in matched)}")
    else:
        out.append("нет")

    for title, score, show in (("узлы", c.nodes, show_node), ("связи", c.edges, show_edge)):
        errors = c.missing_errors(score)
        out += ["", f"## Пропущенные {title}: ошибки ({len(errors)})", ""]
        out += items(errors, show, c.expected_rules)
        later = score.missing & c.deferred
        if later:
            out += ["", f"## Пропущенные {title}: правило еще не реализовано ({len(later)})", ""]
            out += items(later, show, c.expected_rules)
        out += ["", f"## Лишние {title} ({len(score.extra)})", ""] + items(score.extra, show)

    if c.retyped:
        out += ["", "## Узлы с другим типом", ""]
        out += [f"- `{node_id}`: в эталоне {want}, в модели {got}" for node_id, want, got in c.retyped]
    
    if model.get("warnings"):
        out += ["", f"## Предупреждения экстрактора ({len(model['warnings'])})", ""]
        out += [f"- {w}" for w in model["warnings"]]

    return "\n".join(out) + "\n"