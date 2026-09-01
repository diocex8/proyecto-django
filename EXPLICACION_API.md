# Documentación Técnica — Explicación Profunda de la API REST

> Guía de estudio y exposición del backend del Sistema de Gestión Académica. Orientado a estudiantes y profesores, explicando el "por qué" de las decisiones arquitectónicas, las convenciones y los patrones de código utilizados en Django y Django REST Framework (DRF).

---

## Índice

1. [¿Qué es esta API y qué hace?](#1-qué-es-esta-api-y-qué-hace)
2. [Arquitectura General (Monolito Modular)](#2-arquitectura-general-monolito-modular)
3. [Decisiones en los Modelos (El corazón de los datos)](#3-decisiones-en-los-modelos-el-corazón-de-los-datos)
4. [Serializers (La capa de validación)](#4-serializers-la-capa-de-validación)
5. [ViewSets y Vistas (El controlador HTTP)](#5-viewsets-y-vistas-el-controlador-http)
6. [Autenticación JWT](#6-autenticación-jwt)
7. [Optimizaciones y Prácticas de Vida Real](#7-optimizaciones-y-prácticas-de-vida-real)
8. [Glosario Rápido para Exposición](#8-glosario-rápido-para-exposición)

---

## 1. ¿Qué es esta API y qué hace?

Esta API es el **cerebro del sistema académico**. Es una aplicación web construida con **Django** y **Django REST Framework (DRF)** que no tiene páginas web tradicionales (HTML). En su lugar, responde exclusivamente con **JSON**, un formato de texto estructurado que cualquier cliente (aplicación móvil, web o de escritorio) puede entender.

### Los Dominios del Sistema

| Dominio | Responsabilidad Principal |
|---|---|
| `usuarios` | Registro, login, control de roles y perfiles. |
| `cursos` | Creación, publicación y gestión del catálogo académico. |
| `inscripciones` | Relación entre un estudiante y un curso. |
| `asignaciones` | Tareas, entregas y lógica de calificaciones. |

---

## 2. Arquitectura General (Monolito Modular)

El proyecto es un **monolito modular**. Es un único servidor, pero está dividido en "módulos" independientes llamados **apps**. Cada app es responsable de un solo dominio de negocio.

**¿Por qué hacerlo así?**
- Sigue el principio de **Responsabilidad Única**.
- Si la lógica de cursos falla, no tumba directamente la autenticación.
- Es el paso previo ideal si en el futuro el proyecto necesita separarse en Microservicios.

### El Flujo de 4 Capas

Toda petición sigue un orden estricto de responsabilidades:

1. **Router (URLs):** ¿A dónde vas?
2. **View (Vista):** ¿Quién eres y tienes permiso para estar aquí?
3. **Serializer (Validador):** ¿La información que traes tiene el formato correcto y es válida?
4. **Model (Base de Datos):** Guarda o extrae la información de PostgreSQL.

---

## 3. Decisiones en los Modelos (El corazón de los datos)

En Django, los Modelos son la representación en Python de las tablas de la base de datos. Aquí hay algunas decisiones arquitectónicas "poco comunes" pero muy profesionales:

### 3.1. Extender `AbstractUser` en lugar de usar el `User` por defecto

Django ya trae un modelo de usuarios, pero lo reemplazamos por uno propio heredando de `AbstractUser`.
- **Razón:** El usuario por defecto de Django pide un `username`. Nosotros queremos que la gente inicie sesión con su `email`. Además, necesitábamos agregarle el campo `rol` (Profesor, Estudiante, Administrador). 

### 3.2. El uso del decorador `@property`

En lugar de crear funciones normales como `usuario.es_profesor()`, usamos `@property`:

```python
@property
def es_profesor(self):
    return self.rol == self.Rol.PROFESOR
```

- **Razón:** Esto convierte una función en un "atributo calculado". No se guarda en la base de datos, se calcula en vivo. Permite que el código sea mucho más legible, escribiendo `if usuario.es_profesor:` en lugar de andar comparando strings como `if usuario.rol == 'profesor':` por todo el proyecto.

### 3.3. Uso de `TextChoices` para los estados

En lugar de usar números (`1` = Pendiente, `2` = Publicado), usamos `models.TextChoices`.
- **Razón:** Guarda la palabra literal en la base de datos. Si un administrador entra directamente a PostgreSQL a revisar un error, verá "pendiente" en texto claro, sin necesidad de buscar un manual de qué significa el número 1.

---

## 4. Serializers (La capa de validación)

El Serializer es el **guardia de seguridad del sistema**. Su trabajo es deserializar (convertir el JSON que manda el usuario en datos de Python) y serializar (convertir datos de Python de vuelta a JSON).

### 4.1. ¿Por qué validar en el Serializer y no en la Vista?

Esta es una regla de oro en DRF: **Las vistas deben ser "delgadas", los serializers hacen el trabajo pesado.**

1. **Respuestas Automáticas:** Si el serializer valida que la nota debe ser menor a 20 y alguien envía 25, DRF genera automáticamente un JSON de error estructurado: `{"calificacion": ["La nota no puede superar 20"]}`. Si lo hiciéramos en la vista, tendríamos que escribir `if` y `try/except` interminables.
2. **Formularios Dinámicos:** DRF tiene una interfaz web para probar la API. Al definir reglas en el serializer, DRF sabe exactamente cómo pintar las cajitas de los formularios en la pantalla.

### 4.2. Serializers separados para Lectura y Escritura

A menudo un principiante usa 1 solo serializer para todo. Nosotros usamos varios por modelo:

| Tipo | Ejemplo | ¿Para qué sirve? |
|---|---|---|
| **Lectura** (GET) | `CursoListaSerializer` | Es rico en información. Trae datos cruzados, nombres completos, promedios. Es "pesado" de construir. |
| **Escritura** (POST) | `CursoCrearSerializer` | Es estricto, rápido y plano. Solo pide los campos exactos que el usuario necesita enviar. |

Mezclar ambos genera un anti-patrón donde campos que el usuario no debería poder editar terminan expuestos.

---

## 5. ViewSets y Vistas (El controlador HTTP)

### 5.1. El poder de los ViewSets

Un `ModelViewSet` en DRF es una clase mágica que agrupa automáticamente las 5 operaciones CRUD (Crear, Leer, Leer Uno, Actualizar, Borrar). En lugar de escribir 5 funciones distintas, escribimos 1 sola clase.

### 5.2. Personalización de `get_queryset` y `get_permissions`

En lugar de dejar la seguridad estática, nuestras vistas deciden en vivo qué puede hacer el usuario:

```python
def get_queryset(self):
    if usuario.es_estudiante:
        return Curso.objects.filter(estado='publicado')
    elif usuario.es_profesor:
        return Curso.objects.filter(profesor=usuario)
```

- **Razón:** El mismo endpoint (`GET /cursos/`) responde diferente según quién pregunte. El estudiante solo ve lo publicado, el profesor ve hasta sus borradores. Todo centralizado.

### 5.3. Permisos a nivel de Objeto (Object Permissions)

Una cosa es poder entrar a `/entregas/`, otra muy distinta es poder editar **esa entrega en específico**. Implementamos métodos `has_object_permission` para que, justo en el momento en que alguien intenta tocar una tarea, el sistema verifique: *"¿Eres tú el dueño de esta tarea? ¿O eres el profesor del curso?"*. Si no, bloquea automáticamente con un error 403.

---

## 6. Autenticación JWT

El sistema usa **JSON Web Tokens (JWT)**, una autenticación sin estado (stateless). 
- El servidor no guarda "sesiones". 
- Cuando el usuario hace login, recibe una llave encriptada (Access Token).
- El usuario manda esa llave en cada petición. El servidor simplemente la desencripta matemáticamente para saber quién es.

### Inyección de Claims (Decisión de Diseño)

Sobrescribimos la creación del token para meterle el `rol` y el `nombre_completo` del usuario.
- **Razón:** Al hacer esto, el Frontend (React, Vue, Móvil) puede leer el token y saber inmediatamente qué menú mostrar (Profesor o Estudiante) **sin tener que hacer una segunda petición a la base de datos** para preguntar su perfil.

---

## 7. Optimizaciones y Prácticas de Vida Real

### 7.1. El problema N+1 y cómo se solucionó

Si pides una lista de 50 cursos y cada curso necesita mostrar el nombre de su profesor, Django por defecto hará **51 consultas a la base de datos**. Esto es un desastre en producción.

Usamos `select_related('profesor')` en las vistas.
- **Razón:** Esto hace un JOIN en SQL por debajo de la mesa. En lugar de 51 consultas, trae toda la información de golpe en **1 sola consulta**.

### 7.2. Manejador de Errores Estandarizado (Custom Exception Handler)

Configuramos Django para que **cualquier error** (incluso fallos del servidor 500) responda con un JSON idéntico:

```json
{
    "exito": false,
    "codigo": "error_validacion",
    "mensaje": "Los datos enviados no son válidos.",
    "errores": { ... }
}
```
- **Razón:** Si un Frontend confía en que los errores siempre tendrán esta misma estructura, los desarrolladores de frontend pueden crear alertas automáticas sin importar en qué endpoint falló la app.

### 7.3. Máquinas de Estado Finito (Transiciones Válidas)

Un error muy común en administradores de bases de datos es que un objeto pase de un estado A a un estado C directamente (por ejemplo, de "Archivado" a "Borrador") rompiendo la lógica del negocio. 

Para evitar esto, implementamos "Transiciones Válidas" en nuestros serializadores (ej. `CambiarEstadoCursoSerializer`). 

```python
TRANSICIONES_VALIDAS = {
    Curso.Estado.BORRADOR: [Curso.Estado.PUBLICADO],
    Curso.Estado.PUBLICADO: [Curso.Estado.ARCHIVADO, Curso.Estado.BORRADOR],
    Curso.Estado.ARCHIVADO: [],
}
```

- **Razón:** En vez de confiar en que el Frontend mandará las cosas correctas, el backend tiene un diccionario estricto. Si un curso está en estado `ARCHIVADO`, la lista de a dónde puede ir está vacía `[]`. Si alguien intenta publicarlo, el backend lee este diccionario y lanza un error de validación automático (como el que te ocurrió a ti como administrador). Esto garantiza una total integridad de los datos, simulando una pequeña **Máquina de Estados**.

### 7.4. Lógica Especial en las Vistas (HTML Inyectado y Sobrescritura)

Si revisas las vistas de este proyecto (como `apps/inscripciones/views.py` o `apps/asignaciones/views.py`), notarás algunas decisiones de diseño que van más allá del uso tradicional de DRF (Django REST Framework):

1. **`get_view_description(self, html=False)` (Inyección de Interfaces Visuales):**
   - **Qué hace:** Normalmente, esta función de DRF devuelve una cadena de texto simple para documentar el endpoint en la interfaz interactiva web (la Browsable API). En nuestro proyecto, la **sobreescribimos radicalmente** para inyectar código HTML puro (botones estilizados, tarjetas de estadísticas de notas, colores condicionales según el rendimiento del estudiante, etc.).
   - **Por qué se usó:** Esto permitió construir un **Dashboard Interno completamente funcional y estético sin necesidad de programar un frontend separado (como React o Vue) ni depender del panel del Django Admin**. Al entrar a las URLs de la API desde el navegador, el usuario (Profesor o Estudiante) interactúa con botones visuales que aplican filtros (ej. `?curso=5`) generados desde el backend. Es una técnica extremadamente creativa que ahorra tiempo de desarrollo frontend.

2. **`get_serializer_class(self)` Dinámico:**
   - **Qué hace:** Cambia el Serializer "al vuelo" dependiendo de la acción que se está intentando hacer. Si se hace un `GET` (Listar), devuelve mucha información (nombres, fechas, promedios) usando un Serializer de Lectura. Si se hace un `POST` (Crear), usa un Serializer de Escritura que solo pide los datos estrictamente necesarios (ej. `curso_id`).

3. **Sobrescritura de métodos `update()` y `create()`:**
   - DRF ya trae métodos genéricos prefabricados. Nosotros los sobreescribimos manualmente en varias vistas para poder devolver respuestas en JSON amigables y personalizadas como: `{"exito": true, "mensaje": "Se inscribió exitosamente"}` en lugar del formato por defecto de DRF que suele ser mucho más plano.

---

## 8. Glosario Rápido para Exposición

Para que hables con total fluidez técnica durante la presentación:

- **Endpoint:** La URL de la API a la que el frontend hace la petición (ej. `/api/v1/cursos/`).
- **ORM (Object-Relational Mapping):** La herramienta de Django que nos permite hablar con la base de datos PostgreSQL usando código Python en lugar de escribir sentencias SQL a mano.
- **QuerySet:** Una lista "perezosa" de la base de datos. No hace la consulta real hasta que de verdad se necesita imprimir los datos.
- **Fat Model / Thin View (Modelo Gordo / Vista Delgada):** Patrón de diseño donde toda la lógica de qué hacer con los datos (ej: `entrega.calificar(15)`) vive en los Modelos, mientras que las Vistas solo se encargan del tráfico de internet.
