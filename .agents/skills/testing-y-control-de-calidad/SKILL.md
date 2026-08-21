---
name: testing-y-control-de-calidad
description: Habilidad recomendada para la creación y ejecución de pruebas unitarias, de integración y pruebas E2E (End-to-End). Úsala para garantizar la estabilidad del código, prevenir regresiones y aplicar metodologías TDD (Test-Driven Development).
---

# Testing y Control de Calidad de Software (QA)

Esta habilidad proporciona una metodología integral para garantizar que el software cuente con una cobertura de pruebas automatizadas sólida y mantenible.

## Pirámide y Estándares de Testing

### 1. Niveles de Pruebas
- **Pruebas Unitarias**: Validar funciones puras, servicios y algoritmos en aislamiento rápido.
- **Pruebas de Integración**: Verificar la comunicación entre servicios, controladores y capas de persistencia.
- **Pruebas End-to-End (E2E)**: Simular flujos completos de usuario sobre la interfaz web o móvil.

### 2. Patrón AAA (Arrange, Act, Assert)
- **Arrange (Preparar)**: Establecer los datos de prueba, estados e inconsistencias requeridas.
- **Act (Ejecutar)**: Invocación directa del método o acción bajo prueba.
- **Assert (Verificar)**: Comprobación estricta del resultado esperado contra el valor devuelto.

### 3. Principios de Pruebas Robustas
- Evitar esperas por tiempos arbitrarios (`sleep`); utilizar esperas basadas en eventos o cambios de estado.
- Garantizar que las pruebas sean deterministas y repetibles en cualquier entorno (local o CI/CD).
