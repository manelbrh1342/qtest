import ast

def classify_assertion(source):
    tree = ast.parse(source)
    priority = ["strong", "structural", "probability-only", "weak", "unknown"]
    found = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            method_names = []
            func_names = []
            for child in ast.walk(node.test):
                if isinstance(child, ast.Attribute):
                    method_names.append(child.attr)
                elif isinstance(child, ast.Name):
                    func_names.append(child.id)

            if "equiv" in method_names:
                found.append("strong")
            elif "is_unitary" in method_names:
                found.append("structural")
            elif "probabilities_dict" in method_names or "get" in method_names:
                found.append("probability-only")
            elif "len" in func_names:
                found.append("weak")
            else:
                found.append("unknown")

    if not found:
        return "unknown"

    for level in priority:
        if level in found:
            return level