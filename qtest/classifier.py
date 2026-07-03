import ast

def classify_assertion(source):
    tree = ast.parse(source)
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
                return "strong"
            elif "is_unitary" in method_names:
                return "structural"
            elif "len" in func_names:
                return "weak"
            elif "probabilities_dict" in method_names or "get" in method_names:
                return "probability-only"
            
            else:
                return "unknown"
    
    return "unknown"