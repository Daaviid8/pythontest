import sys
import os
import time
import psutil
import gc
import json
import ast
import re
import importlib.util
import traceback
import inspect
from typing import Dict, Any, List, Union, Optional
def validate_function_parameters(func: callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
    signature = inspect.signature(func)
    parameter_validation = {
        "function_name": func.__name__,
        "parameters": {},
        "validation_status": "passed"
    }
    try:
        bound_arguments = signature.bind(*args, **kwargs)
        bound_arguments.apply_defaults()
        for param_name, param_value in bound_arguments.arguments.items():
            param_info = {
                "value": param_value,
                "type": type(param_value).__name__,
                "source": "unknown"
            }
            try:
                frame = inspect.currentframe()
                while frame:
                    local_vars = frame.f_locals
                    for var_name, var_value in local_vars.items():
                        if var_value is param_value:
                            param_info["source"] = f"local variable: {var_name}"
                            break
                    frame = frame.f_back
                    if param_info["source"] != "unknown":
                        break
            except Exception:
                pass
            param = signature.parameters[param_name]
            if param.annotation != inspect.Parameter.empty:
                try:
                    if not isinstance(param_value, param.annotation):
                        param_info["type_validation"] = "failed"
                        parameter_validation["validation_status"] = "failed"
                    else:
                        param_info["type_validation"] = "passed"
                except Exception:
                    param_info["type_validation"] = "validation_error"
            parameter_validation["parameters"][param_name] = param_info
    except TypeError as e:
        parameter_validation["validation_status"] = "failed"
        parameter_validation["error"] = str(e)
    return parameter_validation
def load_module(file_path: str) -> Any:
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        raise ImportError(f"Error loading module: {e}")
def run_tests(file_path: str) -> Dict[str, Dict[str, Union[bool, str]]]:
    test_results = {}
    parameter_validations = {}
    try:
        module = load_module(file_path)
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        tree = ast.parse(content)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                func = getattr(module, func_name)
                docstring = ast.get_docstring(node)
                test_cases = extract_test_cases(docstring)
                if test_cases:
                    test_results[func_name] = {}
                    parameter_validations[func_name] = {}
                    for test_case in test_cases:
                        try:
                            match = re.match(r'\w+\((.*)\)', test_case['input'])
                            if match:
                                args = [arg.strip() for arg in match.group(1).split(',')]
                                evaluated_args = [eval(arg) for arg in args]
                                param_validation = validate_function_parameters(func, evaluated_args, {})
                                parameter_validations[func_name][test_case['input']] = param_validation
                                if param_validation['validation_status'] == 'passed':
                                    result = func(*evaluated_args)
                                    is_passing = abs(result - test_case['expected']) < 1e-6
                                    test_results[func_name][test_case['input']] = is_passing
                                else:
                                    test_results[func_name][test_case['input']] = "Failed parameter validation"
                            else:
                                test_results[func_name][test_case['input']] = "Error: Invalid test case format"
                        except Exception as e:
                            test_results[func_name][test_case['input']] = f"Error: {str(e)}"
    except Exception as e:
        return {"error": str(traceback.format_exc())}
    return {
        "test_results": test_results,
        "parameter_validations": parameter_validations
    }
def extract_test_cases(docstring: str) -> List[Dict[str, Union[str, float]]]:
    test_cases = []
    pattern = r'(\w+\([^)]*\))\s*==\s*(-?\d+(?:\.\d+)?)'
    matches = re.findall(pattern, docstring or '')
    for case, expected in matches:
        test_cases.append({
            'input': case,
            'expected': float(expected)
        })
    return test_cases
def measure_performance(module: Any, functions: List[str], iterations: int = 100) -> Dict[str, Union[str, float]]:
    start_time = time.time()
    process = psutil.Process(os.getpid())
    cpu_usage_start = process.cpu_percent(interval=None)
    ram_usage_start = process.memory_info().rss
    executed_lines = 0
    try:
        for func_name in functions:
            func = getattr(module, func_name)
            for _ in range(iterations):
                func()
                executed_lines += 1
    except Exception as e:
        print(f"Error executing function {func_name}: {e}")
    end_time = time.time()
    cpu_usage_end = process.cpu_percent(interval=None)
    ram_usage_end = process.memory_info().rss
    execution_time = end_time - start_time
    cpu_usage = cpu_usage_end - cpu_usage_start
    ram_usage = ram_usage_end - ram_usage_start
    memory_size = sum(sys.getsizeof(obj) for obj in gc.get_objects())
    execution_speed = executed_lines / execution_time if execution_time > 0 else 0
    return {
        "execution_time": round(execution_time, 4),
        "cpu_usage": round(cpu_usage, 2),
        "ram_usage_mb": round(ram_usage / (1024 ** 2), 4),
        "memory_storage_bytes": memory_size,
        "execution_speed_lines_per_second": round(execution_speed, 2),
    }
def generate_performance_report(file_path: str) -> Dict[str, Any]:
    test_data = run_tests(file_path)
    module = load_module(file_path)
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    tree = ast.parse(content)
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    performance_metrics = measure_performance(module, functions)
    test_summary = {
        "passed_tests": sum(all(v.values()) for v in test_data['test_results'].values() if isinstance(v, dict)),
        "total_tests": sum(len(v) for v in test_data['test_results'].values() if isinstance(v, dict))
    }
    return {
        "tests": test_data['test_results'],
        "parameter_validations": test_data['parameter_validations'],
        "performance": performance_metrics,
        "test_stability": test_summary
    }
def main():
    if len(sys.argv) < 2:
        print("Please provide the path to the Python file to test.")
        sys.exit(1)
    file_path = sys.argv[1]
    try:
        report = generate_performance_report(file_path)
        output_file = 'performance_report.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        print(json.dumps(report, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"Error generating performance report: {e}")
        traceback.print_exc()
        sys.exit(1)
if __name__ == "__main__":
    main()
