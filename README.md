# Sistema de Gestion de Actividades Academicas

## Descripcion del Proyecto

API REST construida con Django y Django REST Framework que gestiona el ciclo completo de actividades academicas: profesores que crean y administran cursos y asignaciones, estudiantes que se inscriben y entregan sus trabajos, y un sistema de calificaciones con validaciones de negocio reales.

---

## Tecnologias Utilizadas

| Categoria | Tecnologia | Version |
|---|---|---|
| Lenguaje | Python | 3.12+ |
| Framework web | Django | 5.1.4 |
| API REST | Django REST Framework | 3.15.2 |
| Autenticacion | djangorestframework-simplejwt | 5.3.1 |
| Variables de entorno | django-environ | 0.11.2 |
| Base de datos | PostgreSQL | 14+ |
| Driver de BD | psycopg2-binary | 2.9.10 |
| CORS | django-cors-headers | 4.6.0 |
| Archivos estaticos | WhiteNoise | 6.8.2 |
| Servidor WSGI | Gunicorn | 23.0.0 |
| Filtrado avanzado | django-filter | 24.3 |

---

## Arquitectura del Proyecto

### Estructura de Directorios

```
Django proyecto/
|
|-- apps/                          # Todas las aplicaciones del dominio
|   |-- __init__.py
|   |-- usuarios/                  # Autenticacion, roles y usuarios
|   |   |-- models.py              # Modelo Usuario (extiende AbstractUser)
|   |   |-- serializers.py         # Serializadores con validaciones
|   |   |-- views.py               # ViewSets y vistas de autenticacion
|   |   |-- permissions.py         # Permisos personalizados a nivel de objeto
|   |   |-- services.py            # Capa de servicio (logica de negocio)
|   |   |-- urls.py                # Enrutamiento de la app
|   |   |-- admin.py               # Registro en el panel de administracion
|   |   `-- apps.py                # Configuracion de la aplicacion
|   |
|   |-- cursos/                    # Gestion de cursos academicos
|   |   |-- models.py              # Modelos Curso, Categoria
|   |   |-- serializers.py
|   |   |-- views.py
|   |   |-- permissions.py
|   |   |-- services.py
|   |   |-- urls.py
|   |   `-- apps.py
|   |
|   |-- inscripciones/             # Inscripcion de estudiantes a cursos
|   |   |-- models.py              # Modelo Inscripcion (tabla intermedia)
|   |   |-- serializers.py
|   |   |-- views.py
|   |   |-- urls.py
|   |   `-- apps.py
|   |
|   `-- asignaciones/              # Asignaciones y entregas de trabajos
|       |-- models.py              # Modelos Asignacion, Entrega
|       |-- serializers.py
|       |-- views.py
|       |-- permissions.py
|       |-- services.py
|       |-- urls.py
|       `-- apps.py
|
|-- config/                        # Configuracion central del proyecto
|   |-- settings/
|   |   |-- __init__.py
|   |   |-- base.py                # Settings compartidos (todos los entornos)
|   |   |-- development.py         # Settings de desarrollo local
|   |   `-- production.py          # Settings de produccion (seguridad maxima)
|   |-- exceptions.py              # Manejador de excepciones personalizado
|   |-- pagination.py              # Clases de paginacion centralizadas
|   |-- urls.py                    # Enrutador principal con versionado /api/v1/
|   |-- wsgi.py                    # Punto de entrada WSGI para Gunicorn
|   `-- asgi.py
|
|-- requirements/
|   |-- base.txt                   # Dependencias compartidas
|   |-- development.txt            # Dependencias de desarrollo
|   `-- production.txt             # Dependencias de produccion
|
|-- logs/                          # Archivos de log (no se versionan)
|-- staticfiles/                   # Estaticos compilados (no se versionan)
|-- venv/                          # Entorno virtual (no se versiona)
|-- .env                           # Variables de entorno (no se versiona)
|-- .env.example                   # Plantilla de variables (se versiona)
|-- .gitignore
|-- Procfile                       # Comando de proceso para PaaS (Heroku, Railway)
|-- gunicorn.conf.py               # Configuracion avanzada de Gunicorn
`-- manage.py
```

### Principios de Arquitectura Aplicados

**Monolito Modular**: El proyecto sigue una arquitectura de monolito modular donde cada aplicacion Django encapsula su propio dominio. Este patron es el correcto para la escala y equipo de este proyecto.

**12-Factor App**: La configuracion se separa completamente del codigo (Factor III). Ningun valor sensible existe en el codigo fuente; todo proviene de variables de entorno gestionadas por django-environ.

**Controladores Delgados (Thin Views)**: Las vistas solo reciben la peticion, validan entradas via serializadores y retornan la respuesta. La logica de negocio compleja se delega a capas de servicio (services.py).

---

## Modelos de Dominio

### Usuario (apps.usuarios)

Extiende `AbstractUser` de Django. Usa `email` como campo de autenticacion. Incluye un campo `rol` con tres valores: `profesor`, `estudiante`, `administrador`, implementado con `TextChoices`.

### Curso (apps.cursos)

Representa un curso academico. Tiene un `profesor` (ForeignKey a Usuario), un `estado` (borrador, publicado, archivado) y una relacion ManyToMany con estudiantes a traves de la tabla intermedia Inscripcion.

### Inscripcion (apps.inscripciones)

Tabla intermedia personalizada entre Curso y Usuario (estudiante) con campos adicionales: fecha de inscripcion, estado de la inscripcion.

### Asignacion (apps.asignaciones)

Tarea o examen creado por un profesor dentro de un curso. Tiene fecha de entrega, valor maximo y tipo (tarea, examen, proyecto).

### Entrega (apps.asignaciones)

Registra la entrega de un estudiante a una asignacion. Contiene el contenido enviado, la calificacion y el estado de la entrega.

---

## Flujo de Autenticacion

El sistema usa JWT mediante `djangorestframework-simplejwt`:

1. El cliente envia `email` y `password` a `POST /api/v1/auth/token/`.
2. El servidor devuelve un token `access` (valido 30 minutos) y un `refresh` (valido 7 dias).
3. El cliente incluye el access token en cada peticion: `Authorization: Bearer <token>`.
4. Al expirar, el cliente usa `POST /api/v1/auth/token/refresh/` para renovar.
5. El refresh token usado se agrega a la blacklist para invalidarlo.

El payload del JWT incluye `rol`, `nombre` y `email` del usuario para evitar consultas extra a la base de datos en cada request.

---

## Permisos y Roles

El sistema implementa permisos a nivel de objeto:

- **EsProfesor**: Solo profesores pueden crear cursos y asignaciones.
- **EsEstudiante**: Solo estudiantes pueden inscribirse y entregar trabajos.
- **EsPropietarioDelCurso**: Un profesor solo modifica los cursos que el creo.
- **EsEstudianteInscrito**: Un estudiante solo accede a cursos en los que esta inscrito.
- **EsPropietarioDeLaEntrega**: Un estudiante solo ve y edita sus propias entregas.

---

## Seguridad Implementada

| Amenaza | Mitigacion |
|---|---|
| Inyeccion SQL | Uso exclusivo del ORM. Nunca se concatenan strings en consultas. |
| Fuerza bruta | Rate limiter a nivel de servidor (nginx) o django-axes. |
| Tokens comprometidos | Vida util corta (30 min) + blacklist de refresh tokens. |
| Contrasenas debiles | Validadores Django: min 10 chars, no comunes, no solo numericas. |
| CSRF | Proteccion nativa con CSRF_TRUSTED_ORIGINS configurado. |
| Clickjacking | Header X-Frame-Options: DENY en produccion. |
| MIME sniffing | Header X-Content-Type-Options: nosniff. |
| HTTP plano | SECURE_SSL_REDIRECT=True y HSTS en produccion. |
| CORS no controlado | django-cors-headers con lista blanca de origenes. |
| Credenciales en codigo | django-environ + .env excluido del repositorio. |

---

## Optimizacion de Consultas

Todos los ViewSets usan `select_related` y `prefetch_related` en `get_queryset()` para eliminar el problema N+1. En desarrollo, `django.db.backends` en nivel DEBUG muestra cada SQL ejecutada en consola para detectar ineficiencias.

---

## Paginacion

Todos los endpoints de lista usan paginacion global. Estructura de respuesta:

```json
{
    "paginacion": {
        "total_registros": 150,
        "total_paginas": 8,
        "pagina_actual": 1,
        "siguiente": "http://api.ejemplo.com/api/v1/cursos/?pagina=2",
        "anterior": null
    },
    "resultados": []
}
```

---

## Respuestas de Error Estandarizadas

El manejador personalizado en `config/exceptions.py` garantiza que todo error, incluyendo los 500, sea JSON:

```json
{
    "exito": false,
    "codigo": "not_found",
    "mensaje": "El recurso solicitado no fue encontrado.",
    "errores": {
        "nombre_campo": ["El mensaje de error especifico."]
    }
}
```
El campo `errores` solo aparece en errores de validacion.

---

### Endpoints Principales

| Recurso | Metodo | URL | Descripcion | Permisos |
|---|---|---|---|---|
| **Registro** | `GET` / `POST` | `/api/v1/auth/registro/` | Registrar estudiante o profesor | Publico |
| **Login JWT** | `POST` | `/api/v1/auth/token/` | Obtener par de tokens JWT | Publico |
| **Login Navegador** | `GET` / `POST` | `/api-auth/login/` | Iniciar sesion para la API navegable | Publico |
| **Refrescar Token** | `POST` | `/api/v1/auth/token/refresh/` | Renovar access token | Publico |
| **Mi Perfil** | `GET` / `PATCH` | `/api/v1/auth/perfil/` | Ver y editar perfil + estadisticas | Autenticado |
| **Cambiar Clave** | `POST` | `/api/v1/auth/cambiar-password/` | Actualizar contrasena | Autenticado |
| **Cursos** | `GET` / `POST` | `/api/v1/cursos/` | Listar cursos / Crear nuevo curso | Autenticado (Crear: Profesor) |
| **Detalle Curso** | `GET` / `PATCH` / `DELETE` | `/api/v1/cursos/{id}/` | Ver, editar o eliminar curso | Autenticado (Editar: Propietario) |
| **Cambiar Estado Curso** | `POST` | `/api/v1/cursos/{id}/cambiar-estado/` | Publicar o archivar un curso | Profesor propietario |
| **Asignaciones de Curso** | `GET` | `/api/v1/cursos/{id}/asignaciones/` | Listar asignaciones de ese curso | Alumno inscrito / Profesor |
| **Inscripciones de Curso** | `GET` | `/api/v1/cursos/{id}/inscripciones/` | Listar alumnos inscritos | Profesor propietario |
| **Inscripciones** | `GET` / `POST` | `/api/v1/inscripciones/` | Mis cursos inscritos / Inscribirme | Estudiante |
| **Detalle Inscripcion** | `GET` / `DELETE` | `/api/v1/inscripciones/{id}/` | Ver detalle o retirarse de curso | Estudiante propietario |
| **Asignaciones** | `GET` / `POST` | `/api/v1/asignaciones/` | Listar tareas / Crear tarea (`?curso=ID`) | Autenticado (Crear: Profesor) |
| **Detalle Asignacion** | `GET` / `PATCH` / `DELETE` | `/api/v1/asignaciones/{id}/` | Ver o editar tarea | Autenticado (Editar: Propietario) |
| **Entregas de Tarea** | `GET` / `POST` | `/api/v1/asignaciones/{id}/entregas/` | Ver entregas / Enviar solucion | Autenticado (Enviar: Estudiante) |
| **Detalle Entrega** | `GET` | `/api/v1/asignaciones/{id}/entregas/{eid}/` | Ver solucion y nota de alumno | Alumno propietario / Profesor |
| **Calificar Entrega** | `GET` / `PATCH` / `POST` | `/api/v1/asignaciones/{id}/entregas/{eid}/calificar/` | Asignar nota y retroalimentacion | Profesor propietario |
| **Panel Admin** | `GET` | `/admin/` | Panel visual de administracion Django | Superusuario / Staff |

---

## Guia de Uso Completa (Paso a Paso en Navegador Web)

Puedes interactuar con toda la API directamente desde Google Chrome, Firefox o Edge utilizando la interfaz navegable interactiva (Browsable API).

> **URL de Produccion (Render)**: `https://api-gestion-academica-4kzs.onrender.com`  
> **URL de Desarrollo Local**: `http://localhost:8000`

---

### Paso 1: Registrar un Profesor y un Estudiante
1. Entra en tu navegador a: **`/api/v1/auth/registro/`**
2. En el formulario inferior, completa los datos:
   - `email`: `profesor@ejemplo.com`
   - `username`: `profesor1`
   - `first_name`: `Juan`
   - `last_name`: `Perez`
   - `rol`: `profesor`
   - `password`: `PasswordSegura123!`
   - `password_confirmacion`: `PasswordSegura123!`
3. Haz clic en **POST**.
4. Repite el mismo proceso para registrar un estudiante con rol `estudiante` (ej: `estudiante@ejemplo.com`).

---

### Paso 2: Iniciar Sesion en el Navegador
1. Entra a: **`/api-auth/login/`**
2. Ingresa el `email` y `password` del **Profesor**.
3. Haz clic en **Log in**. Ahora veras tu nombre en la esquina superior derecha del navegador.

---

### Paso 3: Crear y Publicar un Curso (como Profesor)
1. Ve a: **`/api/v1/cursos/`**
2. En el formulario inferior, llena los datos del curso (ej: `codigo`: `PY-101`, `nombre`: `Programacion Python`, `capacidad_maxima`: `30`, `fecha_inicio`: `2026-09-01`, `fecha_fin`: `2026-12-15`) y haz clic en **POST**.
3. **Publicar el curso**: Por defecto el curso se crea en *Borrador*. Para que los estudiantes puedan verlo e inscribirse:
   - Entra a: **`/api/v1/cursos/1/cambiar-estado/`** (reemplaza `1` por el ID del curso).
   - En el formulario escribe `{"nuevo_estado": "publicado"}` y haz clic en **POST** (o hazlo desde el panel `/admin/cursos/curso/`).

---

### Paso 4: Crear una Asignacion o Tarea (como Profesor)
1. Ve a: **`/api/v1/asignaciones/?curso=1`** (reemplaza `1` por el ID de tu curso).
2. En el formulario inferior completa:
   - `titulo`: `Tarea 1: Algoritmos`
   - `descripcion`: `Resolver los ejercicios del capitulo 1.`
   - `tipo`: `tarea`
   - `valor_maximo`: `20.00`
   - `fecha_entrega`: `2026-09-30 23:59`
3. Haz clic en **POST**. El ID de la asignacion sera generado (ej: `1`).

---

### Paso 5: Inscribirse a un Curso (como Estudiante)
1. Ve a **`/api-auth/logout/`** para cerrar sesion del profesor.
2. Inicia sesion en **`/api-auth/login/`** con las credenciales del **Estudiante**.
3. Ve a: **`/api/v1/inscripciones/`**
4. En el campo **Curso id** selecciona el curso publicado y haz clic en **POST**.

---

### Paso 6: Entregar la Tarea (como Estudiante)
1. Como estudiante, entra a: **`/api/v1/asignaciones/1/entregas/`** (donde `1` es el ID de la asignacion).
2. En la casilla `Contenido`, escribe tu respuesta o desarrollo de la tarea.
3. Haz clic en **POST**. Se generara tu entrega con su respectivo ID (ej: `1`).

---

### Paso 7: Revisar y Calificar la Entrega (como Profesor)
1. Cierra sesion y vuelve a iniciar sesion como el **Profesor**.
2. Ve a: **`/api/v1/asignaciones/1/entregas/`** para ver la lista de entregas enviadas por tus alumnos.
3. Para calificar al estudiante, entra a: **`/api/v1/asignaciones/1/entregas/1/calificar/`**
4. En el formulario:
   - En la casilla **`Calificacion`**: escribe la nota (ejemplo: `19.5`).
   - En la casilla **`Retroalimentacion`**: escribe tus comentarios u observaciones.
5. Haz clic en el boton **`PATCH`**. ¡La entrega quedara oficialmente calificada!

---

## Como Correr el Proyecto en Local

### 1. Prerrequisitos
- Python 3.12 o superior
- PostgreSQL 14 o superior
- Git

### 2. Instalacion y Puesta en Marcha

```powershell
# Clonar y entrar al repositorio
git clone <url-del-repositorio>
cd "Django proyecto"

# Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements/development.txt

# Configurar variables de entorno
copy .env.example .env

# Aplicar migraciones
python manage.py migrate

# Crear superusuario local
python manage.py createsuperuser

# Iniciar servidor local
python manage.py runserver
```

---

## Despliegue en Render.com (Produccion)

El repositorio incluye el archivo de infraestructura como codigo `render.yaml` y el script de construccion `build.sh`.

Para desplegar:
1. En Render.com, selecciona **New +** -> **Blueprint**.
2. Conecta el repositorio de GitHub.
3. Render creara de forma 100% automatica la base de datos PostgreSQL, ejecutara las migraciones, recolectara los archivos estaticos y creara el superusuario inicial (`admin@admin.com` / `Admin123456!`).
