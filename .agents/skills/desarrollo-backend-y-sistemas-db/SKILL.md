---
name: desarrollo-backend-y-sistemas-db
description: Guía de buenas prácticas para la construcción de servicios servidor (Backend), APIs REST/GraphQL, controladores, middlewares, desacoplamiento de servicios y gestión asíncrona. Úsala al codificar la lógica del lado del servidor.
---

# Buenas Prácticas de Desarrollo Backend

Esta habilidad establece las reglas de diseño e implementación para construir APIs y servicios del lado del servidor escalables, mantenibles y seguros.

## Estándares de Desarrollo Backend

### 1. Diseño de APIs y Contratos de Interfaz
- Diseñar endpoints RESTful claros o esquemas GraphQL deterministas.
- Validar exhaustivamente los datos de entrada en la capa de middleware mediante esquemas de validación estrictos.
- Utilizar respuestas HTTP estándar y formatos de error uniformes en toda la aplicación.

### 2. Desacoplamiento y Controladores Delgados (Thin Controllers)
- Mantener los controladores delgados: su única función es recibir la petición, validar entradas y retornar la respuesta.
- Delegar toda la lógica de negocio a servicios dedicados e inyectables.
- Encapsular el acceso a datos en repositorios o capas de persistencia abstractas.

### 3. Asincronía y Tareas en Segundo Plano
- Procesar tareas pesadas (envío de notificaciones masivas, procesamiento de imágenes, reportes) de forma asíncrona mediante colas de trabajo (Message Queues / Redis Workers).
- Manejar adecuadamente los estados asíncronos y errores no capturados para evitar caídas del servidor.
