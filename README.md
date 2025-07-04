# 🧪 Python Tester & Performance Analyzer

## 🚀 Características de Unity.py

- ✅ **Validación automática de parámetros** según las anotaciones de tipo de las funciones.
- 🧪 **Ejecución de pruebas extraídas de los docstrings** de las funciones.
- 📈 **Medición de rendimiento**: tiempo de ejecución, CPU, RAM y velocidad.
- 📄 **Generación de informe JSON** con todos los resultados.
- 🔍 Útil para debugging, testing y profiling de funciones simples o complejas.
## ⚙️ Uso

Asegúrate de que el archivo que deseas analizar contenga funciones con docstrings que incluyan casos de prueba en formato:

```python
def multiplicar_por_dos(x: int) -> int:
    """
    multiplicar_por_dos(0) == 0
    multiplicar_por_dos(2) == 4
    multiplicar_por_dos(5) == 10
    """
    return x * 2
```

## 📖 Interpretación del informe

### 🔹 `tests`
Contiene los resultados de las pruebas definidas en los docstrings.

- `true`: la función devolvió el valor esperado.
- `"Failed parameter validation"` o `"Error: ..."`: error en la prueba o durante la ejecución de la función.

### 🔹 `parameter_validations`
Evalúa si los argumentos usados en las pruebas cumplen con las anotaciones de tipo de la función.

- `"type_validation": "passed"`: el tipo de parámetro es correcto.
- `"type_validation": "failed"`: el tipo de parámetro es incorrecto.

### 🔹 `performance`
Mide el rendimiento total de todas las funciones probadas:

- `execution_time`: tiempo total de ejecución (en segundos).
- `cpu_usage`: porcentaje de CPU utilizado durante la ejecución.
- `ram_usage_mb`: uso de memoria RAM en megabytes.
- `memory_storage_bytes`: cantidad de memoria utilizada por los objetos durante la ejecución (en bytes).
- `execution_speed_lines_per_second`: velocidad de ejecución medida en líneas por segundo (indica eficiencia general).

### 🔹 `test_stability`
Resumen global de los resultados de las pruebas:

- `passed_tests`: número total de pruebas exitosas.
- `total_tests`: número total de pruebas ejecutadas.
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
## 🚀 Características de Integration.py

- ✅ **Mapeo de integración de funciones**: Mapea las funciones, sus parámetros y relaciones entre ellas.
- 🧪 **Análisis de código muerto**: Detecta variables, funciones y clases no utilizadas, y clasifica su impacto.
- 📈 **Generación de informes detallados**: Informa sobre el estado de las variables, funciones, clases y dependencias de retorno.
- 🔍 **Detección de dependencias de retorno**: Detecta qué variables o funciones afectan el valor de retorno final.
- 📄 **Generación de informes en formatos JSON y TXT**: Exporta los resultados a archivos para su análisis y visualización.

## ⚙️ Uso

Asegúrate de que el archivo que deseas analizar contenga funciones con definiciones claras y código ejecutable. Luego, puedes ejecutar el análisis desde la terminal con:

```bash
python integration.py <ruta_del_archivo.py>
```

# 📖 Interpretación del informe

### 🔹 unused
Contiene las variables, funciones y clases definidas pero que no fueron utilizadas en el código.

- **Variables**: Son aquellas variables que se definieron pero no fueron utilizadas en ningún lugar del código.
- **Funciones**: Funciones que fueron definidas pero no llamadas en el código.
- **Clases**: Clases que fueron definidas pero no instanciadas ni utilizadas.

### 🔹 not_affecting_return
Contiene las variables, funciones y clases que son utilizadas pero no afectan el valor de retorno final de la ejecución de la función principal o programa.

- **Variables**: Variables que son utilizadas en el código pero no influyen en el valor retornado por las funciones.
- **Funciones**: Funciones que son llamadas pero no afectan el retorno de la función que las invoca.
- **Clases**: Clases que son usadas pero no tienen un impacto en el valor final retornado.

### 🔹 variable_scope
Clasifica las variables de acuerdo con su alcance en el código:

- **Global Variables**: Variables que son usadas en más de una función.
- **Local Variables**: Variables que solo son utilizadas dentro de una única función.
- **Other Variables**: Variables que no pueden ser clasificadas como globales ni locales, por ejemplo, variables utilizadas en clases o que no tienen un uso claro.

### 🔹 contexts
Contiene información detallada sobre el contexto de las variables:

- **scope**: Indica si la variable pertenece a una función, clase o es global.
- **line**: Número de línea donde la variable fue definida.
- **functions**: Lista de funciones que utilizan la variable.

### 🔹 variable_usages
Lista de las variables usadas en el código y las funciones donde son utilizadas. Este informe muestra en qué funciones o bloques de código se hace uso de cada variable, y su clasificación en términos de alcance.
