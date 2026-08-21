---
name: gestion-priorizada-y-aprendizaje-de-errores
description: Gestiona la descomposición y ejecución ordenada de tareas por prioridad (Crítica, Alta, Media, Baja) y establece un bucle de aprendizaje continuo sobre fallos pasados para prevenir reincidencias de errores. Úsala en proyectos complejos, tareas multitramo o durante fases de depuración intensa.
---

# Gestión Priorizada y Aprendizaje Continuo de Errores

Esta habilidad proporciona una metodología estructurada para organizar la ejecución de tareas y mantener un proceso de resolución de problemas empírico y libre de regresiones.

## Metodología de Ejecución

### 1. Matriz de Priorización (P0 a P3)
- **P0 (Crítico / Bloqueante)**: Errores que impiden la compilación, vulnerabilidades de seguridad o fallos en dependencias core.
- **P1 (Alta Prioridad)**: Funcionalidades indispensables del plan de desarrollo actual.
- **P2 (Prioridad Media)**: Optimizaciones de rendimiento, mejoras de código o componentes secundarios.
- **P3 (Baja Prioridad)**: Ajustes cosméticos o mejoras opcionales.

*Regla*: Siempre resolver tareas P0 y P1 antes de avanzar a P2 o P3.

### 2. Bucle de Depuración y Aprendizaje de Errores
- **Inspección de Logs**: Leer el registro o stack trace completo antes de formular diagnósticos. Prohibido adivinar causas sin evidencia.
- **Causa Raíz vs Síntomas**: Identificar el contrato o variable violada. Prohibido aplicar arreglos cosméticos, silenciar excepciones o borrar pruebas fallidas.
- **Verificación Obligatoria**: Correr comandos de build o test tras aplicar cambios para confirmar la resolución completa.
