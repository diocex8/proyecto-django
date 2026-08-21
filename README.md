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

## Endpoints Principales

| Metodo | URL | Descripcion | Rol |
|---|---|---|---|
| POST | `/api/v1/auth/token/` | Obtener tokens JWT | Ninguno |
| POST | `/api/v1/auth/token/refresh/` | Renovar token | Ninguno |
| POST | `/api/v1/auth/registro/` | Registrar usuario | Ninguno |
| GET | `/api/v1/auth/perfil/` | Ver perfil propio | Autenticado |
| GET | `/api/v1/cursos/` | Listar cursos | Autenticado |
| POST | `/api/v1/cursos/` | Crear curso | Profesor |
| PATCH | `/api/v1/cursos/{id}/` | Actualizar curso | Profesor (propietario) |
| DELETE | `/api/v1/cursos/{id}/` | Eliminar curso | Profesor (propietario) |
| GET | `/api/v1/inscripciones/` | Mis inscripciones | Estudiante |
| POST | `/api/v1/inscripciones/` | Inscribirse | Estudiante |
| DELETE | `/api/v1/inscripciones/{id}/` | Desinscribirse | Estudiante (propietario) |
| GET | `/api/v1/asignaciones/` | Listar asignaciones | Autenticado |
| POST | `/api/v1/asignaciones/` | Crear asignacion | Profesor |
| POST | `/api/v1/asignaciones/{id}/entregas/` | Entregar trabajo | Estudiante inscrito |
| PATCH | `/api/v1/asignaciones/{id}/entregas/{eid}/calificar/` | Calificar entrega | Profesor (propietario) |

---

## Como Correr el Proyecto

### Prerequisitos

Tener instalado antes de empezar:

- Python 3.12 o superior: https://www.python.org/downloads/
- PostgreSQL 14 o superior: https://www.postgresql.org/download/
- Git: https://git-scm.com/

---

### Paso 1 - Clonar el repositorio

```powershell
git clone <url-del-repositorio>
cd "Django proyecto"
```

---

### Paso 2 - Crear y activar el entorno virtual

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> Si PowerShell bloquea la ejecucion de scripts, ejecuta primero:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

### Paso 3 - Instalar dependencias

```powershell
pip install -r requirements/development.txt
```

---

### Paso 4 - Configurar las variables de entorno

```powershell
copy .env.example .env
```

Abre el archivo `.env` y edita los valores segun tu entorno local:

```env
DJANGO_ENVIRONMENT=development
SECRET_KEY=django-insecure-clave-solo-para-desarrollo-cambiar-en-produccion
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=gestion_academica
DB_USER=postgres
DB_PASSWORD=tu_contrasena_de_postgres
DB_HOST=localhost
DB_PORT=5432
```

---

### Paso 5 - Crear la base de datos en PostgreSQL

Abre una terminal con acceso a `psql` y ejecuta:

```sql
psql -U postgres -c "CREATE DATABASE gestion_academica;"
```

O desde el cliente grafico pgAdmin: boton derecho en "Databases" > Create > Database > nombre: `gestion_academica`.

---

### Paso 6 - Aplicar las migraciones

```powershell
python manage.py migrate
```

Salida esperada: una lista de migraciones aplicadas sin errores.

---

### Paso 7 - Crear un superusuario (administrador)

```powershell
python manage.py createsuperuser
```

El sistema pedira: email, username, nombre, apellido y contrasena (minimo 10 caracteres).

---

### Paso 8 - Iniciar el servidor de desarrollo

```powershell
python manage.py runserver
```

El servidor queda disponible en:

| Recurso | URL |
|---|---|
| API REST | `http://localhost:8000/api/v1/` |
| Panel de administracion | `http://localhost:8000/admin/` |
| API navegable (DRF) | `http://localhost:8000/api/v1/cursos/` |

---

### Flujo de uso completo (paso a paso)

Una vez el servidor esta corriendo en `http://localhost:8000`, el flujo tipico es el siguiente. Puedes usar el **navegador** para los GET y **curl / Postman / Insomnia** para los POST/PATCH.

---

#### Paso A — Registrar un Profesor

```powershell
curl -X POST http://localhost:8000/api/v1/auth/registro/ `
  -H "Content-Type: application/json" `
  -d '{
    "email": "profesor@ejemplo.com",
    "username": "profesor1",
    "first_name": "Juan",
    "last_name": "Perez",
    "rol": "profesor",
    "password": "ClaveSegura123",
    "password_confirmacion": "ClaveSegura123"
  }'
```

---

#### Paso B — Iniciar sesion y obtener el Token JWT

Despues de registrarte, necesitas un **token de acceso** para poder hacer cualquier otra peticion. Sin este token, todas las peticiones devuelven `401 Unauthorized`.

```powershell
curl -X POST http://localhost:8000/api/v1/auth/token/ `
  -H "Content-Type: application/json" `
  -d '{"email": "profesor@ejemplo.com", "password": "ClaveSegura123"}'
```

La respuesta tiene este formato:

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Guarda el valor de `access`**. Debes enviarlo en todas las peticiones siguientes en el header `Authorization`.

---

#### Paso C — Crear un Curso (como Profesor)

Reemplaza `<TOKEN>` con el valor `access` que obtuviste en el paso B:

```powershell
curl -X POST http://localhost:8000/api/v1/cursos/ `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <TOKEN>" `
  -d '{
    "titulo": "Python Avanzado",
    "codigo": "PY-301",
    "descripcion": "Curso de Python para desarrolladores con experiencia en el lenguaje.",
    "fecha_inicio": "2026-09-01",
    "fecha_fin": "2026-12-15",
    "cupo_maximo": 30
  }'
```

La respuesta incluye el `id` del curso creado. **Guarda ese `id`** para los pasos siguientes.

---

#### Paso D — Publicar el Curso

Un curso en estado `borrador` no es visible para estudiantes. Para publicarlo:

```powershell
curl -X POST http://localhost:8000/api/v1/cursos/<ID_CURSO>/publicar/ `
  -H "Authorization: Bearer <TOKEN>"
```

---

#### Paso E — Registrar un Estudiante e Inscribirse

En una nueva terminal (o en Postman), registra un estudiante:

```powershell
curl -X POST http://localhost:8000/api/v1/auth/registro/ `
  -H "Content-Type: application/json" `
  -d '{
    "email": "estudiante@ejemplo.com",
    "username": "estudiante1",
    "first_name": "Maria",
    "last_name": "Lopez",
    "rol": "estudiante",
    "password": "ClaveSegura456",
    "password_confirmacion": "ClaveSegura456"
  }'
```

Obtener su token:

```powershell
curl -X POST http://localhost:8000/api/v1/auth/token/ `
  -H "Content-Type: application/json" `
  -d '{"email": "estudiante@ejemplo.com", "password": "ClaveSegura456"}'
```

Inscribirse al curso (usando el token del **estudiante**):

```powershell
curl -X POST http://localhost:8000/api/v1/inscripciones/ `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <TOKEN_ESTUDIANTE>" `
  -d '{"curso": <ID_CURSO>}'
```

---

#### Paso F — Crear una Asignacion (como Profesor)

Con el token del **profesor**:

```powershell
curl -X POST http://localhost:8000/api/v1/asignaciones/?curso=<ID_CURSO> `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <TOKEN_PROFESOR>" `
  -d '{
    "titulo": "Tarea 1: Variables y tipos",
    "descripcion": "Resuelve los ejercicios del capitulo 1.",
    "tipo": "tarea",
    "fecha_entrega": "2026-09-20T23:59:00Z",
    "valor_maximo": 20.00
  }'
```

---

#### Paso G — Entregar la Asignacion (como Estudiante)

Con el token del **estudiante** y el `<ID_ASIGNACION>` del paso F:

```powershell
curl -X POST http://localhost:8000/api/v1/asignaciones/<ID_ASIGNACION>/entregas/ `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <TOKEN_ESTUDIANTE>" `
  -d '{"contenido": "Aqui va mi respuesta al ejercicio del capitulo 1."}'
```

---

#### Paso H — Calificar la Entrega (como Profesor)

Con el `<ID_ENTREGA>` recibido en la respuesta del paso G:

```powershell
curl -X POST http://localhost:8000/api/v1/asignaciones/<ID_ASIGNACION>/entregas/<ID_ENTREGA>/calificar/ `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <TOKEN_PROFESOR>" `
  -d '{"calificacion": 18.5, "retroalimentacion": "Excelente trabajo, muy claro."}'
```

---

#### Alternativa visual: API Navegable de DRF

Si prefieres no usar curl, abre el navegador en `http://localhost:8000/api/v1/` y usa la interfaz navegable de Django REST Framework. Puedes autenticarte con el boton **"Log in"** usando el usuario del panel de administracion.

---

### Resumen de comandos en un solo bloque

Para quienes ya tienen todo configurado y solo quieren arrancar el proyecto:

```powershell
.\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver
```

API disponible en: `http://localhost:8000/api/v1/`
Panel de administracion: `http://localhost:8000/admin/`

---

## Despliegue en Produccion

**Variables de entorno requeridas en produccion**:

```
DJANGO_ENVIRONMENT=production
SECRET_KEY=<clave-aleatoria-de-50-caracteres>
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com
DB_NAME=gestion_academica
DB_USER=<usuario-produccion>
DB_PASSWORD=<contrasena-segura>
DB_HOST=<host-db>
DB_PORT=5432
CORS_ALLOWED_ORIGINS=https://tu-frontend.com
```

**Comandos de despliegue**:

```bash
# 1. Instalar dependencias de produccion
pip install -r requirements/production.txt

# 2. Compilar archivos estaticos (WhiteNoise los sirve desde staticfiles/)
python manage.py collectstatic --no-input

# 3. Aplicar migraciones pendientes
python manage.py migrate

# 4. Iniciar con Gunicorn usando la configuracion dedicada
gunicorn -c gunicorn.conf.py config.wsgi:application

# Alternativa rapida sin archivo de configuracion:
# gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
```

---

## Sistema de Logging

| Entorno | Nivel | Destino |
|---|---|---|
| Desarrollo | DEBUG | Consola (incluye todas las SQL) |
| Produccion | INFO / WARNING | Archivos rotativos en /logs/ (max 10 MB, 5 backups) |

---

## Para que Sirve este Proyecto

1. **Base de produccion**: Punto de partida para cualquier LMS, sistema universitario o plataforma de cursos.

2. **Referencia de buenas practicas**: JWT, permisos a nivel de objeto, optimizacion N+1, manejo de errores y separacion de entornos en un proyecto Django real.

3. **Plantilla de arquitectura**: La estructura modular y la capa de servicios son aplicables a cualquier proyecto Django de mediana o gran escala.

4. **Ejemplo de seguridad aplicada**: Multiples capas de defensa implementadas sin sacrificar la productividad del equipo de desarrollo.
