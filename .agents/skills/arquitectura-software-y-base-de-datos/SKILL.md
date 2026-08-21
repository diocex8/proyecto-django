---
name: arquitectura-software-y-base-de-datos
description: Proporciona marcos de trabajo y buenas prácticas para la planificación arquitectónica de software y el diseño estructurado de bases de datos relacionales o NoSQL. Úsala cuando el usuario pida definir la arquitectura o diseñar el modelo de datos basándose en requerimientos reales.
---

# Buenas Prácticas de Arquitectura de Software y Diseño de Bases de Datos

Esta habilidad establece los criterios técnicos para auditar requerimientos, seleccionar patrones arquitectónicos y modelar bases de datos desde cero según las necesidades del proyecto.

## Principios y Metodología de Diseño

### 1. Levantamiento de Requerimientos y Casos de Uso
- Identificar entidades principales, volumen proyectado y tasa estimada de lectura vs escritura.
- Definir los patrones de acceso más frecuentes para orientar la indexación y el almacenamiento.

### 2. Selección de Patrón Arquitectónico
- **Monolito Modular**: Para proyectos en etapa inicial o de crecimiento medio, facilitando la velocidad y el despliegue simple.
- **Clean Architecture / Arquitectura Hexagonal**: Separación estricta entre Presentación, Aplicación, Dominio e Infraestructura.
- **Microservicios / Event-Driven**: Solo cuando la escala de equipos o la carga distribuida lo justifique.

### 3. Principios de Diseño de Bases de Datos
- **Normalización**: Aplicar 3NF en modelos relacionales para asegurar consistencia, desnormalizando solo con justificación de rendimiento.
- **Integridad Referencial**: Definir claves primarias (UUIDs o autoincrementales), claves foráneas explícitas y restricciones `CHECK` / `UNIQUE`.
- **Estrategia de Índices**: Indexar columnas utilizadas frecuentemente en cláusulas `WHERE`, `JOIN` y `ORDER BY`, evitando sobre-indexación en tablas con alta tasa de escritura.
- **Estrategia de Caching**: Diseñar capas de caché en memoria (Redis/Memcached) para lecturas intensivas de datos de poca variación.
