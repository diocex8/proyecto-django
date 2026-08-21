---
name: optimizacion-de-tokens-y-contexto
description: Maximiza la eficiencia en el uso de tokens y la gestión del contexto del agente. Úsala constantemente en todos los prompts e interacciones para evitar desbordamiento de contexto, reducir costos y mantener respuestas concisas, profesionales y precisas.
---

# Optimización de Tokens y Gestión de Contexto

Esta habilidad establece las reglas obligatorias que el agente debe aplicar en cada interacción para mantener un uso óptimo del contexto y minimizar el consumo de tokens.

## Reglas de Actuación en Cada Prompt

### 1. Lectura Selectiva y Acotada
- **Nunca** leas archivos completos si puedes usar rangos de líneas (`StartLine` y `EndLine`).
- Limita las búsquedas con filtros de archivos (`Includes`) al usar `grep_search`.
- Evita releer el mismo archivo múltiples veces si el contenido no ha cambiado.

### 2. Ejecución Silenciosa de Scripts y Comandos
- Ejecuta los scripts auxiliares en modo "caja negra" con `--help` antes de revisar su código interno.
- Al lanzar comandos en segundo plano (`run_command`), lee los registros de log en silencio y entrega únicamente un síntesis conciso con los hallazgos al usuario.

### 3. Modificaciones Puntuales de Código
- Usa `replace_file_content` o `multi_replace_file_content` para realizar cambios de líneas específicos.
- **Prohibido** sobrescribir archivos completos cuando solo se modifica un bloque o función.

### 4. Respuestas Directas y Sin Relleno
- Elimina introducciones, saludos repetitivos, disculpas innecesarias o explicaciones redundantes.
- Proporciona código limpio, resúmenes estructurados en listas y enlaces clicables a los archivos modificados.
