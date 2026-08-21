# Reglas del Proyecto y Agente - Casheita

## Regla Permanente: Optimización de Tokens y Gestión de Contexto

Esta regla se aplica obligatoriamente en **TODAS** las respuestas e interacciones:

1. **Lectura Selectiva de Archivos**:
   - Usar siempre rangos de líneas (`StartLine` y `EndLine`) al inspeccionar archivos. Nunca leer archivos completos si se conoce el bloque a revisar.
   - Acotar búsquedas con patrones `Includes` en `grep_search`.

2. **Ejecución Silenciosa y Eficiente**:
   - Ejecutar scripts con la opción `--help` en lugar de leer su código interno completo.
   - Inspeccionar logs en segundo plano de forma silenciosa y responder al usuario con resúmenes concisos.

3. **Edición Precisa**:
   - Usar `replace_file_content` o `multi_replace_file_content` para modificar únicamente los bloques necesarios. Prohibido sobrescribir archivos completos.

4. **Respuestas Concisas y Sin Relleno**:
   - Ir directo a la solución sin saludos repetitivos ni disculpas. Entregar código limpio y enlaces clicables a archivos.
