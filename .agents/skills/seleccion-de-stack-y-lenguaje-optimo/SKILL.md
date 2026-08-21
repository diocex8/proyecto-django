---
name: seleccion-de-stack-y-lenguaje-optimo
description: Evalúa los requerimientos funcionales y no funcionales del proyecto para determinar y recomendar el lenguaje de programación, framework, base de datos y arquitectura tecnológica más óptima para la tarea. Úsala al planificar la pila tecnológica de un proyecto o componente.
---

# Selección de Stack Tecnológico y Lenguaje Óptimo

Esta habilidad establece una matriz de decisión objetiva para evaluar los requerimientos del usuario y seleccionar la combinación más eficiente de lenguajes, frameworks e infraestructura.

## Matriz de Evaluación de Stack

Cuando el usuario defina las necesidades del proyecto, analiza los siguientes criterios:

### 1. Criterios de Selección por Tipo de Proyecto

| Requerimiento Dominante | Lenguajes & Frameworks Recomendados | Justificación Técnica |
|---|---|---|
| **Landing Page / Web de Alta Conversión** | HTML5 + CSS Vanilla / Astro / Next.js | Velocidad de carga extrema, SSR/SSG nativo para SEO y Core Web Vitals. |
| **API Backend de Alta Concurrencia** | Go (Golang) / Node.js (Fastify/NestJS) | Manejo eficiente de goroutines/Event Loop y baja latencia I/O. |
| **Plataforma Fintech / Transaccional** | TypeScript / Java (Spring Boot) / Go | Tipado estático fuerte, ecosistema de seguridad robusto e integridad de tipos. |
| **Procesamiento de Datos / AI / Analytics** | Python (FastAPI / PyTorch / Pandas) | Ecosistema maduro de ciencia de datos, bibliotecas de IA y prototipado rápido. |
| **Aplicación Móvil Multiplataforma** | Flutter (Dart) / React Native (TypeScript) | Código único para iOS y Android con rendimiento nativo compilado. |

### 2. Criterios de Selección de Base de Datos

- **Relacional (PostgreSQL / MySQL)**: Cuando se requieran transacciones ACID complejas, relaciones fuertemente estructuradas (1:N, N:M) y consistencia estricta.
- **Documental / NoSQL (MongoDB)**: Para datos no estructurados o esquemas de alta variabilidad con patrones de lectura jerárquicos.
- **Almacenamiento en Memoria (Redis)**: Para caché de baja latencia, colas de mensajes, rate limiting y sesiones de usuario.

### 3. Procedimiento de Recomendación

1. Inspeccionar los requerimientos expuestos por el usuario.
2. Evaluar el balance entre:
   - **Rendimiento**: Latencia y throughput requeridos.
   - **Mantenibilidad**: Facilidad de lectura, tipado y ecosistema.
   - **Tiempo de desarrollo**: Curva de aprendizaje y ecosistema de paquetes.
3. Presentar una propuesta de stack justificada técnicamente antes de escribir cualquier código.
