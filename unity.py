import sys
import os
import time
import psutil
import json
import ast
import re
import importlib.util
import traceback
import inspect
import hashlib
from typing import *
from dataclasses import dataclass
from contextlib import contextmanager
import signal

@dataclass
class SecurityConfig:
    """Configuración de seguridad para la ejecución de código"""
    max_execution_time: int = 30
    max_memory_mb: int = 512
    max_file_size_mb: int = 10
    allowed_imports: set = None
    forbidden_patterns: List[str] = None
    
    def __post_init__(self):
        if self.allowed_imports is None:
            self.allowed_imports = {'math', 'random', 'datetime', 'collections', 'itertools','functools', 'operator', 'typing', 'decimal', 'fractions'}
        if self.forbidden_patterns is None:
            self.forbidden_patterns = [r'__import__',r'exec\s*\(',r'eval\s*\(',r'compile\s*\(',r'open\s*\(',r'file\s*\(',r'input\s*\(',r'raw_input\s*\(',r'subprocess',r'os\.',r'sys\.',r'socket',r'urllib',r'requests',r'pickle',r'marshal',r'shelve']

class SecurityError(Exception):
    """Excepción para errores de seguridad"""
    pass

class TimeoutError(Exception):
    """Excepción para timeouts"""
    pass

class CodeValidator:
    """Validador de código para verificar seguridad"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        
    def validate_file_size(self, file_path: str) -> bool:
        """Valida el tamaño del archivo"""
        try:
            file_size = os.path.getsize(file_path)
            max_size = self.config.max_file_size_mb * 1024 * 1024
            if file_size > max_size:
                raise SecurityError(f"Archivo demasiado grande: {file_size} bytes")
            return True
        except OSError as e:
            raise SecurityError(f"Error al acceder al archivo: {e}")
    
    def validate_code_patterns(self, code: str) -> bool:
        """Valida que el código no contenga patrones peligrosos"""
        for pattern in self.config.forbidden_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise SecurityError(f"Patrón peligroso detectado: {pattern}")
        return True
    
    def validate_imports(self, tree: ast.AST) -> bool:
        """Valida las importaciones en el código"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self.config.allowed_imports:
                        raise SecurityError(f"Importación no permitida: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module not in self.config.allowed_imports:
                    raise SecurityError(f"Importación no permitida: {node.module}")
        return True
    
    def validate_code(self, file_path: str, code: str) -> bool:
        """Validación completa del código"""
        try:
            self.validate_file_size(file_path)
            self.validate_code_patterns(code)
            tree = ast.parse(code)
            self.validate_imports(tree)
            return True
        except SyntaxError as e:
            raise SecurityError(f"Error de sintaxis: {e}")

@contextmanager
def timeout_handler(seconds: int):
    """Context manager para manejar timeouts"""
    def signal_handler(signum, frame):
        raise TimeoutError(f"Operación cancelada por timeout ({seconds}s)")
    
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        yield

class SafeParameterValidator:
    """Validador seguro de parámetros de función"""
    
    @staticmethod
    def validate_function_parameters(func: callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """
        Valida los parámetros de una función de manera segura
        """
        parameter_validation = {"function_name": func.__name__,"parameters": {},"validation_status": "passed","timestamp": time.time()}
        try:
            signature = inspect.signature(func)
            bound_arguments = signature.bind(*args, **kwargs)
            bound_arguments.apply_defaults()
            for param_name, param_value in bound_arguments.arguments.items():
                param_info = {"value": str(param_value)[:100],"type": type(param_value).__name__,"size_bytes": sys.getsizeof(param_value)}
                param = signature.parameters[param_name]
                if param.annotation != inspect.Parameter.empty:
                    try:
                        if not isinstance(param_value, param.annotation):
                            param_info["type_validation"] = "failed"
                            parameter_validation["validation_status"] = "failed"
                        else:
                            param_info["type_validation"] = "passed"
                    except Exception as e:
                        param_info["type_validation"] = f"validation_error: {str(e)}"
                
        except TypeError as e:
            parameter_validation["validation_status"] = "failed"
            parameter_validation["error"] = str(e)
        except Exception as e:
            parameter_validation["validation_status"] = "error"
            parameter_validation["error"] = str(e)
        return parameter_validation

class SecureModuleLoader:
    """Cargador seguro de módulos"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.validator = CodeValidator(config)
        
    def load_module(self, file_path: str) -> Any:
        """Carga un módulo de manera segura"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        if not os.path.isfile(file_path):
            raise ValueError(f"La ruta no es un archivo: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.validator.validate_code(file_path, content)
            module_name = f"safe_module_{hashlib.md5(content.encode()).hexdigest()[:8]}"
            with timeout_handler(self.config.max_execution_time):
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"No se pudo crear spec para {file_path}")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            return module
        except Exception as e:
            raise ImportError(f"Error loading module: {e}")

class TestCaseExtractor:
    """Extractor mejorado de casos de prueba"""
    
    @staticmethod
    def extract_test_cases(docstring: str) -> List[Dict[str, Union[str, float]]]:
        """
        Extrae casos de prueba del docstring de manera más robusta
        """
        if not docstring:
            return []
        test_cases = []
        patterns = [r'(\w+\([^)]*\))\s*==\s*(-?\d+(?:\.\d+)?)',r'(\w+\([^)]*\))\s*->\s*(-?\d+(?:\.\d+)?)',r'>>>\s*(\w+\([^)]*\))\s*(-?\d+(?:\.\d+)?)']
        for pattern in patterns:
            matches = re.findall(pattern, docstring)
            for case, expected in matches:
                try:
                    expected_value = float(expected)
                    test_cases.append({'input': case.strip(),'expected': expected_value,'pattern_used': pattern})
                except ValueError:
                    continue
        return test_cases

class SafeTestRunner:
    """Ejecutor seguro de pruebas"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.loader = SecureModuleLoader(config)
        self.validator = SafeParameterValidator()
        self.extractor = TestCaseExtractor()
        
    def run_tests(self, file_path: str) -> Dict[str, Any]:
        """Ejecuta las pruebas de manera segura"""
        test_results = {}
        parameter_validations = {}
        try:
            module = self.loader.load_module(file_path)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            tree = ast.parse(content)
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    if not hasattr(module, func_name):
                        continue
                    func = getattr(module, func_name)
                    docstring = ast.get_docstring(node)
                    test_cases = self.extractor.extract_test_cases(docstring)
                    if test_cases:
                        test_results[func_name] = {}
                        parameter_validations[func_name] = {}
                        for test_case in test_cases:
                            test_input = test_case['input']
                            try:
                                args = self._parse_function_call(test_input)
                                if args is None:
                                    test_results[func_name][test_input] = "Error: Formato de prueba inválido"
                                    continue
                                param_validation = self.validator.validate_function_parameters(func, args, {})
                                parameter_validations[func_name][test_input] = param_validation
                                if param_validation['validation_status'] == 'passed':
                                    with timeout_handler(5):  # 5 segundos por test
                                        result = func(*args)
                                    expected = test_case['expected']
                                    if isinstance(result, (int, float)):
                                        is_passing = abs(result - expected) < 1e-9
                                    else:
                                        is_passing = result == expected
                                    test_results[func_name][test_input] = is_passing
                                else:
                                    test_results[func_name][test_input] = "Failed parameter validation"
                            except TimeoutError:
                                test_results[func_name][test_input] = "Error: Timeout"
                            except Exception as e:
                                test_results[func_name][test_input] = f"Error: {str(e)}"
        except Exception as e:
            return {"error": str(e),"traceback": traceback.format_exc()}
        return {"test_results": test_results,"parameter_validations": parameter_validations,"execution_timestamp": time.time()}
    
    def _parse_function_call(self, call_str: str) -> Optional[tuple]:
        """Parsea una llamada de función de manera segura"""
        try:
            match = re.match(r'\w+\((.*)\)', call_str)
            if not match:
                return None
            args_str = match.group(1).strip()
            if not args_str:
                return ()
            args = []
            for arg in args_str.split(','):
                arg = arg.strip()
                try:
                    if re.match(r'^-?\d+(\.\d+)?$', arg):  # Números
                        args.append(float(arg) if '.' in arg else int(arg))
                    elif arg.startswith('"') and arg.endswith('"'):  # Strings
                        args.append(arg[1:-1])
                    elif arg.startswith("'") and arg.endswith("'"):  # Strings
                        args.append(arg[1:-1])
                    elif arg.lower() in ['true', 'false']:  # Booleanos
                        args.append(arg.lower() == 'true')
                    elif arg.lower() == 'none':  # None
                        args.append(None)
                    else:
                        if arg.startswith('[') and arg.endswith(']'):
                            args.append(ast.literal_eval(arg))
                        else:
                            return None
                except:
                    return None
            return tuple(args)
        except Exception:
            return None

class PerformanceAnalyzer:
    """Analizador de rendimiento mejorado"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        
    def measure_performance(self, module: Any, functions: List[str], iterations: int = 100) -> Dict[str, Any]:
        """Mide el rendimiento de las funciones"""
        if iterations > 1000:
            iterations = 1000
        metrics = {"iterations": iterations,"functions_tested": len(functions),"timestamp": time.time()}
        try:
            process = psutil.Process(os.getpid())
            start_time = time.time()
            cpu_percent_start = process.cpu_percent()
            memory_start = process.memory_info().rss
            executed_operations = 0
            with timeout_handler(self.config.max_execution_time):
                for func_name in functions:
                    if not hasattr(module, func_name):
                        continue
                    func = getattr(module, func_name)
                    try:
                        sig = inspect.signature(func)
                        if len(sig.parameters) == 0:
                            for _ in range(iterations):
                                func()
                                executed_operations += 1
                    except Exception as e:
                        continue
            end_time = time.time()
            cpu_percent_end = process.cpu_percent()
            memory_end = process.memory_info().rss
            execution_time = end_time - start_time
            memory_used = memory_end - memory_start
            metrics.update({"execution_time_seconds": round(execution_time, 4),"cpu_usage_percent": round(cpu_percent_end - cpu_percent_start, 2),"memory_usage_mb": round(memory_used / (1024 ** 2), 4),"operations_executed": executed_operations,"operations_per_second": round(executed_operations / execution_time, 2) if execution_time > 0 else 0,"average_operation_time_ms": round((execution_time / executed_operations) * 1000, 4) if executed_operations > 0 else 0})
        except TimeoutError:
            metrics["error"] = "Timeout during performance measurement"
        except Exception as e:
            metrics["error"] = str(e)
        return metrics

class UnityAnalyzer:
    """Clase principal del analizador Unity"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        self.test_runner = SafeTestRunner(self.config)
        self.performance_analyzer = PerformanceAnalyzer(self.config)
        
    def generate_performance_report(self, file_path: str) -> Dict[str, Any]:
        """Genera un reporte completo de rendimiento y pruebas"""
        report = {"file_path": file_path,"analysis_timestamp": time.time(),"config": {"max_execution_time": self.config.max_execution_time,"max_memory_mb": self.config.max_memory_mb,"max_file_size_mb": self.config.max_file_size_mb}}
        try:
            test_data = self.test_runner.run_tests(file_path)
            if "error" in test_data:
                report["error"] = test_data["error"]
                return report
            module = self.test_runner.loader.load_module(file_path)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            tree = ast.parse(content)
            functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
            performance_metrics = self.performance_analyzer.measure_performance(module, functions)
            test_summary = self._calculate_test_summary(test_data.get('test_results', {}))
            report.update({"tests": test_data.get('test_results', {}),"parameter_validations": test_data.get('parameter_validations', {}),"performance": performance_metrics,"test_summary": test_summary,"functions_found": functions,"status": "success"})
        except Exception as e:
            report["error"] = str(e)
            report["traceback"] = traceback.format_exc()
            report["status"] = "error"
        return report
    
    def _calculate_test_summary(self, test_results: Dict) -> Dict[str, Any]:
        """Calcula resumen de pruebas"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        error_tests = 0
        for func_results in test_results.values():
            if isinstance(func_results, dict):
                for result in func_results.values():
                    total_tests += 1
                    if result is True:
                        passed_tests += 1
                    elif result is False:
                        failed_tests += 1
                    else:
                        error_tests += 1
        return {"total_tests": total_tests,"passed_tests": passed_tests,"failed_tests": failed_tests,"error_tests": error_tests,"pass_rate": round(passed_tests / total_tests * 100, 2) if total_tests > 0 else 0}

def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("Uso: python unity.py <archivo_python>")
        print("Ejemplo: python unity.py mi_modulo.py")
        sys.exit(1)
    file_path = sys.argv[1]
    config = SecurityConfig(max_execution_time=30,max_memory_mb=512,max_file_size_mb=10)
    try:
        analyzer = UnityAnalyzer(config)
        report = analyzer.generate_performance_report(file_path)
        output_file = 'performance_report.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        print(json.dumps(report, indent=4, ensure_ascii=False))
        if report.get("status") == "success":
            print(f"\n✅ Análisis completado exitosamente")
            print(f"📊 Reporte guardado en: {output_file}")
        else:
            print(f"\n❌ Error durante el análisis")
            sys.exit(1)
    except Exception as e:
        print(f"Error crítico: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
