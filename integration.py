import sys
import json
import ast
import traceback
from typing import List, Dict, Any, Optional, Union, Set
class FunctionIntegrationMapper:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.source_code = self._read_source_code()
        self.tree = ast.parse(self.source_code)
        self.function_definitions = {}
        self.function_calls = {}
        self.variable_flows = {}
    def _read_source_code(self) -> str:
        with open(self.file_path, 'r', encoding='utf-8') as file:
            return file.read()
    def _infer_type(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            return type(node.n).__name__
        elif isinstance(node, ast.Constant):
            return 'str'
        elif isinstance(node, ast.List):
            return 'list'
        elif isinstance(node, ast.Dict):
            return 'dict'
        elif isinstance(node, ast.Tuple):
            return 'tuple'
        elif isinstance(node, ast.Name):
            return 'variable'
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f'function_call({node.func.id})'
        return 'unknown'
    def _parse_function_definitions(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                arguments = []
                argument_types = {}
                for arg in node.args.args:
                    arg_name = arg.arg
                    arguments.append(arg_name)
                    if arg.annotation:
                        try:
                            if isinstance(arg.annotation, ast.Name):
                                argument_types[arg_name] = arg.annotation.id
                            else:
                                argument_types[arg_name] = 'annotated_type'
                        except:
                            argument_types[arg_name] = 'unknown'
                return_type = 'unknown'
                return_value_types = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Return):
                        if child.value:
                            inferred_type = self._infer_type(child.value)
                            return_value_types.append(inferred_type)
                if return_value_types:
                    non_variable_types = [t for t in return_value_types if t != 'variable']
                    return_type = non_variable_types[0] if non_variable_types else return_value_types[0]
                self.function_definitions[node.name] = {
                    'node': node,
                    'arguments': arguments,
                    'argument_types': argument_types,
                    'returns': self._extract_return_statements(node),
                    'return_type': return_type
                }
    def _extract_return_statements(self, node: ast.FunctionDef) -> List[str]:
        returns = []
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                if isinstance(child.value, ast.Name):
                    returns.append(child.value.id)
                elif isinstance(child.value, ast.Constant):
                    returns.append(str(child.value.value))
        return returns
    def _trace_function_calls(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                self.function_calls[func_name] = []
                for call_node in ast.walk(node):
                    if isinstance(call_node, ast.Call):
                        if isinstance(call_node.func, ast.Name):
                            called_func = call_node.func.id
                            args = []
                            arg_types = []
                            for arg in call_node.args:
                                if isinstance(arg, ast.Name):
                                    args.append(arg.id)
                                    arg_types.append(self._infer_type(arg))
                            self.function_calls[func_name].append({
                                'called_function': called_func,
                                'arguments': args,
                                'argument_types': arg_types
                            })
    def _trace_variable_flows(self):
        self.variable_flows = {}
        for func_name, calls in self.function_calls.items():
            self.variable_flows[func_name] = []
            for call in calls:
                called_func = call['called_function']
                flow_entry = {
                    'source_function': func_name,
                    'target_function': called_func,
                    'variables': call['arguments'],
                    'variable_types': call['argument_types']
                }
                self.variable_flows[func_name].append(flow_entry)
    def generate_integration_map(self) -> Dict[str, Any]:
        self._parse_function_definitions()
        self._trace_function_calls()
        self._trace_variable_flows()
        integration_map = {
            'function_definitions': {
                name: {
                    'arguments': details['arguments'],
                    'argument_types': details['argument_types'],
                    'returns': details['returns'],
                    'return_type': details['return_type']
                } for name, details in self.function_definitions.items()
            },
            'interaction_paths': self._generate_interaction_paths()
        }
        return integration_map
    def _generate_interaction_paths(self) -> List[str]:
        interaction_paths = []
        for source_func, flows in self.variable_flows.items():
            for flow in flows:
                path = f"{flow['target_function']} -> {source_func}"
                interaction_paths.append(path)
        return interaction_paths
class DeadCodeAnalyzer:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.source_code = self._read_source_code()
        self.tree = ast.parse(self.source_code)
        self.defined_variables = set()
        self.used_variables = set()
        self.defined_functions = set()
        self.called_functions = set()
        self.defined_classes = set()
        self.used_classes = set()
        self.variables_affecting_returns = set()
        self.functions_affecting_returns = set()
        self.classes_affecting_returns = set()
        self.variable_contexts = {}  # {nombre: {scope: "función/clase", línea: línea}}
        self.variable_usages = {}  # {variable_name: [function_names]}
        self.global_variables = set()  # Variables usadas en más de una función
        self.local_variables = set()   # Variables usadas en una única función
        self.other_variables = set()   # Variables que no encajan en ninguna categoría
    def _read_source_code(self) -> str:
        with open(self.file_path, 'r', encoding='utf-8') as file:
            return file.read()
    def analyze(self):
        self._find_definitions()
        self._find_usages()
        self._trace_return_dependencies()
        self._classify_variables()
        return self._generate_report()
    def _find_definitions(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                self.defined_functions.add(node.name)
                for arg in node.args.args:
                    var_name = arg.arg
                    self.defined_variables.add(var_name)
                    self.variable_contexts[var_name] = {
                        'scope': node.name,
                        'line': node.lineno
                    }
            elif isinstance(node, ast.ClassDef):
                self.defined_classes.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.defined_variables.add(target.id)
                        scope = self._get_scope(node)
                        self.variable_contexts[target.id] = {
                            'scope': scope,
                            'line': node.lineno
                        }
    def _get_scope(self, node):
        current = node
        for ancestor in ast.walk(self.tree):
            if isinstance(ancestor, (ast.FunctionDef, ast.ClassDef)):
                for child in ast.walk(ancestor):
                    if child == current:
                        if isinstance(ancestor, ast.FunctionDef):
                            return f"function:{ancestor.name}"
                        elif isinstance(ancestor, ast.ClassDef):
                            return f"class:{ancestor.name}"
        return "global"
    def _find_usages(self):
        for var in self.defined_variables:
            self.variable_usages[var] = []
        for node in ast.walk(self.tree):
            current_function = self._get_current_function(node)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.called_functions.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        self.used_variables.add(node.func.value.id)
                        if node.func.value.id in self.variable_usages and current_function:
                            self.variable_usages[node.func.value.id].append(current_function)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    self.used_variables.add(node.id)
                    if node.id in self.variable_usages and current_function:
                        self.variable_usages[node.id].append(current_function)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in self.defined_classes:
                    self.used_classes.add(node.func.id)
    def _get_current_function(self, node):
        for ancestor in ast.walk(self.tree):
            if isinstance(ancestor, ast.FunctionDef):
                for child in ast.walk(ancestor):
                    if child == node:
                        return ancestor.name
        return None
    def _classify_variables(self):
        for var_name, func_list in self.variable_usages.items():
            if var_name in self.defined_variables and var_name in self.used_variables:
                unique_functions = set(func_list)
                if len(unique_functions) > 1:
                    self.global_variables.add(var_name)
                elif len(unique_functions) == 1:
                    self.local_variables.add(var_name)
                else:
                    self.other_variables.add(var_name)
            elif var_name in self.defined_variables:
                self.other_variables.add(var_name)
    def _trace_return_dependencies(self):
        direct_dependencies = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Return) and node.value:
                self._collect_return_dependencies(node.value, direct_dependencies)
        all_dependencies = self._resolve_indirect_dependencies(direct_dependencies)
        for dep in all_dependencies:
            if dep in self.defined_variables:
                self.variables_affecting_returns.add(dep)
            elif dep in self.defined_functions:
                self.functions_affecting_returns.add(dep)
            elif dep in self.defined_classes:
                self.classes_affecting_returns.add(dep)
    def _collect_return_dependencies(self, node, dependencies):
        if isinstance(node, ast.Name):
            dependencies.add(node.id)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                dependencies.add(node.func.id)
            for arg in node.args:
                self._collect_return_dependencies(arg, dependencies)
        elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for elt in node.elts:
                self._collect_return_dependencies(elt, dependencies)
        elif isinstance(node, ast.Dict):
            for key in node.keys:
                self._collect_return_dependencies(key, dependencies)
            for value in node.values:
                self._collect_return_dependencies(value, dependencies)
        elif isinstance(node, ast.BinOp):
            self._collect_return_dependencies(node.left, dependencies)
            self._collect_return_dependencies(node.right, dependencies)
        elif isinstance(node, ast.UnaryOp):
            self._collect_return_dependencies(node.operand, dependencies)
        elif isinstance(node, ast.IfExp):
            self._collect_return_dependencies(node.test, dependencies)
            self._collect_return_dependencies(node.body, dependencies)
            self._collect_return_dependencies(node.orelse, dependencies)
        elif isinstance(node, ast.Compare):
            self._collect_return_dependencies(node.left, dependencies)
            for comparator in node.comparators:
                self._collect_return_dependencies(comparator, dependencies)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                dependencies.add(node.value.id)
    def _resolve_indirect_dependencies(self, direct_deps):
        all_deps = set(direct_deps)
        new_deps = set(direct_deps)
        while new_deps:
            temp_deps = set()
            for func_name in [d for d in new_deps if d in self.defined_functions]:
                calls_inside = self._find_calls_in_function(func_name)
                for call in calls_inside:
                    if call not in all_deps:
                        temp_deps.add(call)
                vars_inside = self._find_vars_in_function(func_name)
                for var in vars_inside:
                    if var not in all_deps:
                        temp_deps.add(var)
            for var_name in [d for d in new_deps if d in self.defined_variables]:
                funcs_affecting_var = self._find_funcs_affecting_var(var_name)
                for func in funcs_affecting_var:
                    if func not in all_deps:
                        temp_deps.add(func)
            new_deps = temp_deps - all_deps
            all_deps.update(new_deps)
        return all_deps
    def _find_calls_in_function(self, func_name):
        calls = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        calls.add(child.func.id)
        return calls
    def _find_vars_in_function(self, func_name):
        vars_used = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                        vars_used.add(child.id)
        return vars_used
    def _find_funcs_affecting_var(self, var_name):
        funcs = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name) and target.id == var_name:
                                funcs.add(node.name)
                                break
        return funcs
    def _generate_report(self):
        unused_variables = self.defined_variables - self.used_variables
        unused_functions = self.defined_functions - self.called_functions
        unused_classes = self.defined_classes - self.used_classes
        used_but_not_affecting_variables = (self.used_variables - self.variables_affecting_returns) & self.defined_variables
        used_but_not_affecting_functions = (self.called_functions - self.functions_affecting_returns) & self.defined_functions
        used_but_not_affecting_classes = (self.used_classes - self.classes_affecting_returns) & self.defined_classes
        
        return {
            "unused": {
                "variables": list(unused_variables),
                "functions": list(unused_functions),
                "classes": list(unused_classes)
            },
            "not_affecting_return": {
                "variables": list(used_but_not_affecting_variables),
                "functions": list(used_but_not_affecting_functions),
                "classes": list(used_but_not_affecting_classes)
            },
            "variable_scope": {
                "global_variables": list(self.global_variables),
                "local_variables": list(self.local_variables),
                "other_variables": list(self.other_variables)
            },
            "contexts": self.variable_contexts,
            "variable_usages": {var: list(set(funcs)) for var, funcs in self.variable_usages.items() if var in self.used_variables}
        }
def generate_function_integration_map(file_path: str) -> Dict[str, Any]:
    mapper = FunctionIntegrationMapper(file_path)
    return mapper.generate_integration_map()
def analyze_dead_code(file_path: str) -> Dict[str, Any]:
    analyzer = DeadCodeAnalyzer(file_path)
    return analyzer.analyze()
def save_dead_code_report(report: Dict[str, Any], output_file: str = "dead_code_report.txt"):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== ANÁLISIS DE CÓDIGO MUERTO ===\n\n")
        f.write("CLASIFICACIÓN DE VARIABLES:\n")
        f.write("-"*40 + "\n")
        f.write("Variables Globales (usadas en más de una función):\n")
        for var in report["variable_scope"]["global_variables"]:
            context = report["contexts"].get(var, {})
            scope = context.get('scope', 'global')
            line = context.get('line', '?')
            functions = ', '.join(report["variable_usages"].get(var, []))
            f.write(f"  - {var} (scope: {scope}, línea: {line}, funciones: {functions})\n")
        f.write("\nVariables Locales (usadas en una única función):\n")
        for var in report["variable_scope"]["local_variables"]:
            context = report["contexts"].get(var, {})
            scope = context.get('scope', 'global')
            line = context.get('line', '?')
            functions = ', '.join(report["variable_usages"].get(var, []))
            f.write(f"  - {var} (scope: {scope}, línea: {line}, función: {functions})\n")
        f.write("\nOtras Variables (no clasificadas como globales ni locales):\n")
        for var in report["variable_scope"]["other_variables"]:
            context = report["contexts"].get(var, {})
            scope = context.get('scope', 'global')
            line = context.get('line', '?')
            f.write(f"  - {var} (scope: {scope}, línea: {line})\n")
        f.write("\n\nELEMENTOS DEFINIDOS PERO NO UTILIZADOS:\n")
        f.write("-"*40 + "\n")
        f.write("Variables:\n")
        for var in report["unused"]["variables"]:
            context = report["contexts"].get(var, {})
            scope = context.get('scope', 'global')
            line = context.get('line', '?')
            f.write(f"  - {var} (scope: {scope}, línea: {line})\n")
        f.write("\nFunciones:\n")
        for func in report["unused"]["functions"]:
            f.write(f"  - {func}\n")
        f.write("\nClases:\n")
        for cls in report["unused"]["classes"]:
            f.write(f"  - {cls}\n")
        f.write("\n\nELEMENTOS QUE NO AFECTAN AL RETURN FINAL:\n")
        f.write("-"*40 + "\n")
        f.write("Variables:\n")
        for var in report["not_affecting_return"]["variables"]:
            context = report["contexts"].get(var, {})
            scope = context.get('scope', 'global')
            line = context.get('line', '?')
            f.write(f"  - {var} (scope: {scope}, línea: {line})\n")
        f.write("\nFunciones:\n")
        for func in report["not_affecting_return"]["functions"]:
            f.write(f"  - {func}\n")
        f.write("\nClases:\n")
        for cls in report["not_affecting_return"]["classes"]:
            f.write(f"  - {cls}\n")
def main():
    if len(sys.argv) < 2:
        print("Por favor, proporciona la ruta al archivo Python a analizar.")
        sys.exit(1)
    file_path = sys.argv[1]
    try:
        integration_map = generate_function_integration_map(file_path)
        output_json_file = 'function_integration_map.json'
        with open(output_json_file, 'w', encoding='utf-8') as f:
            json.dump(integration_map, f, indent=4, ensure_ascii=False)
        print(f"Mapa de integración de funciones guardado en '{output_json_file}'")
        dead_code_report = analyze_dead_code(file_path)
        output_txt_file = 'dead_code_report.txt'
        save_dead_code_report(dead_code_report, output_txt_file)
        print(f"Análisis de código muerto guardado en '{output_txt_file}'")
    except Exception as e:
        print(f"Error al analizar el código: {e}")
        traceback.print_exc()
        sys.exit(1)
if __name__ == "__main__":
    main()
