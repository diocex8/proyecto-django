---
name: clean-code-principios-acid-y-refactorizacion
description: Aplica los principios de Clean Code, SOLID, DRY (Don't Repeat Yourself) y la garantía de propiedades ACID en transacciones de base de datos. Úsala durante refactorizaciones, revisiones de código y diseño de algoritmos.
---

# Clean Code, Principios ACID y Refactorización

Esta habilidad asegura la legibilidad del código, la eliminación de redundancias y el cumplimiento estricto de la integridad transaccional ACID.

## Principios de Calidad de Código

### 1. Clean Code & SOLID
- **Single Responsibility (SRP)**: Cada módulo, clase o función debe tener una única responsabilidad.
- **Open/Closed (OCP)**: Entidades abiertas a extensión pero cerradas a modificación.
- **DRY (Don't Repeat Yourself)**: Extraer lógica repetida a utilidades o funciones puras desacopladas.
- **Legibilidad**: Nombres descriptivos para variables y funciones. Evitar comentarios superfluos que expliquen qué hace el código en lugar de por qué se tomó una decisión.

### 2. Transacciones ACID en Bases de Datos
- **Atomicidad**: Operaciones compuestas se ejecutan por completo o se revierten totalmente (rollback).
- **Consistencia**: Preservar todas las restricciones de integridad antes y después de la transacción.
- **Aislamiento**: Prevenir lecturas sucias o condiciones de carrera mediante el nivel de aislamiento de transacción adecuado.
- **Durabilidad**: Confirmación persistente de cambios una vez completada la transacción.
