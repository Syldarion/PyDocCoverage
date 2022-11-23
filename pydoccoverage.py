import ast


CONFIG_EXCLUDE_FOLDERS = "exclude_folders"
CONFIG_EXCLUDE_FILES = "exclude_files"
CONFIG_SKIP_MAGIC = "skip_magic_funcs"
CONFIG_SKIP_PRIVATE = "skip_private_funcs"
CONFIG_REPORT_PERCENT_ONLY = "report_percent_only"

CONFIG_FIELDS = [
    CONFIG_EXCLUDE_FOLDERS,
    CONFIG_EXCLUDE_FILES,
    CONFIG_SKIP_MAGIC,
    CONFIG_SKIP_PRIVATE,
    CONFIG_REPORT_PERCENT_ONLY
]

CONFIG_DEFAULT = {
    CONFIG_EXCLUDE_FOLDERS: [
        "venv"
    ],
    CONFIG_EXCLUDE_FILES: [],
    CONFIG_SKIP_MAGIC: True,
    CONFIG_SKIP_PRIVATE: True,
    CONFIG_REPORT_PERCENT_ONLY: False
}


def _collect_python_files(root_folder, config):
    import os
    py_files = []

    for root, dirs, files in os.walk(root_folder):
        dirs[:] = [d for d in dirs if d not in config[CONFIG_EXCLUDE_FOLDERS]]
        for file in files:
            if file.endswith(".py") and file not in config[CONFIG_EXCLUDE_FILES]:
                py_files.append(os.path.join(root, file))
    return py_files


def count_matching(iterable, *predicates):
    v = [0] * len(predicates)
    for e in iterable:
        for i, p in enumerate(predicates):
            if p(e):
                v[i] += 1
    return tuple(v)


def _analyze_file(file_path, config):
    # returns a dictionary with the module docstring and the docstrings of each function

    file_data = {
        "module_docstring": None,
        "class_coverage": {
            "documented": 0,
            "total": 0,
            "percentage": 1.0
        },
        "function_coverage": {
            "documented": 0,
            "total": 0,
            "percentage": 1.0
        },
        "classes": [],
        "functions": []
    }

    file_source = None
    with open(file_path, "r") as source:
        file_source = source.read()

    ast_tree = ast.parse(file_source)

    file_data["module_docstring"] = ast.get_docstring(ast_tree)

    for node in ast.walk(ast_tree):
        if isinstance(node, ast.ClassDef):
            file_data["classes"].append({
                "name": node.name,
                "line": node.lineno,
                "docstring": ast.get_docstring(node)
            })
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            if config[CONFIG_SKIP_MAGIC] and node.name.startswith("__") and node.name.endswith("__"):
                continue
            if config[CONFIG_SKIP_PRIVATE] and node.name.startswith("_"):
                continue
            file_data["functions"].append({
                "name": node.name,
                "line": node.lineno,
                "docstring": ast.get_docstring(node)
            })

    documented_classes = count_matching(file_data["classes"], lambda a: a["docstring"] is not None)
    total_classes = len(file_data["classes"])

    file_data["class_coverage"] = {
        "documented": documented_classes[0],
        "total": total_classes,
        "percentage": documented_classes[0] / max(total_classes, 1)
    }

    documented_functions = count_matching(file_data["functions"], lambda a: a["docstring"] is not None)
    total_functions = len(file_data["functions"])

    file_data["function_coverage"] = {
        "documented": documented_functions[0],
        "total": total_functions,
        "percentage": documented_functions[0] / max(total_functions, 1)
    }

    return file_data


def _report_data(ast_data, config):
    if config[CONFIG_REPORT_PERCENT_ONLY]:
        _report_percent_only(ast_data)
    else:
        _report_all(ast_data)


def _report_all(ast_data: dict):
    for file_name in ast_data:
        file_data = ast_data[file_name]
        file_reports = []
        if file_data["module_docstring"] is None:
            file_reports.append("Missing docstring for module")
        for class_data in file_data["classes"]:
            if class_data["docstring"] is None:
                lineno = class_data["line"]
                file_reports.append(f"Line {lineno}: Missing docstring for class \'{class_data['name']}\'")
        for function_data in file_data["functions"]:
            if function_data["docstring"] is None:
                lineno = function_data["line"]
                file_reports.append(f"Line {lineno}: Missing docstring for function \'{function_data['name']}\'")
        if file_reports:
            reports_delimited = "\n".join(file_reports)
            class_cov = file_data["class_coverage"]
            func_cov = file_data["function_coverage"]
            class_cov_line = f"{class_cov['documented']} of {class_cov['total']} classes documented ({class_cov['percentage'] * 100:.1f}%)"
            func_cov_line = f"{func_cov['documented']} of {func_cov['total']} functions documented ({func_cov['percentage'] * 100:.1f}%)"
            report_sections = [
                file_name,
                class_cov_line,
                func_cov_line,
                ('-' * len(file_name)),
                reports_delimited,
                "\n"
            ]
            print("\n".join(report_sections))


def _report_percent_only(ast_data: dict):
    for file_name in ast_data:
        file_data = ast_data[file_name]
        class_cov = file_data["class_coverage"]
        func_cov = file_data["function_coverage"]
        class_doc = class_cov["documented"]
        func_doc = func_cov["documented"]
        class_total = class_cov["total"]
        func_total = func_cov["total"]
        class_perc = class_cov["percentage"] * 100
        func_perc = func_cov["percentage"] * 100
        file_report_line = f"{file_name} | Classes: {class_doc}/{class_total} ({class_perc:.1f}%), Functions: {func_doc}/{func_total} ({func_perc:.1f}%)"
        print(file_report_line)


def _overwrite_config(base, new):
    for field in CONFIG_FIELDS:
        if field in new:
            base[field] = new[field]

    return base


def run():
    import sys
    import json

    config = CONFIG_DEFAULT
    try:
        with open(sys.argv[2], "r") as conf:
            config = _overwrite_config(config, json.load(conf))
    except Exception as e:
        pass

    py_files = _collect_python_files(sys.argv[1], config)
    file_data = {}
    for file in py_files:
        file_data[file] = _analyze_file(file, config)
    _report_data(file_data, config)


if __name__ == "__main__":
    run()
