---
name: creador-de-habilidades
description: Guía y automatiza la creación de nuevas habilidades (skills) para el agente en idioma español siguiendo las especificaciones oficiales de Antigravity. Úsala cuando el usuario pida crear una nueva habilidad, empaquetar un flujo de trabajo o estructurar carpetas de habilidades.
---

# Creador de Habilidades (Skill Creator)

Esta habilidad proporciona una metodología paso a paso, plantillas y herramientas auxiliares para crear habilidades modularizadas, claras y efectivas para el agente en idioma español.

## ¿Qué es una Habilidad (Skill)?
Una habilidad es una carpeta estructurada con instrucciones y recursos opcionales que extiende las capacidades del agente para resolver tareas especializadas. El agente las descubre automáticamente al inicio de la sesión basándose en el Frontmatter YAML y las activa según el contexto del usuario.

## Ubicación de las Habilidades
Las habilidades pueden residir en:
- **Nivel de Proyecto / Workspace**: `.agents/skills/<nombre-de-la-habilidad>/`
- **Nivel Global del Usuario**: `C:\Users\USER\.gemini\config\skills\<nombre-de-la-habilidad>/` (o `~/.gemini/config/skills/`)

---

## Estructura Recomendada de una Habilidad
```
.agents/skills/<nombre-de-la-habilidad>/
├── SKILL.md           # Archivo principal de instrucciones (OBLIGATORIO)
├── scripts/           # Scripts de automatización en Python/Bash (opcional)
├── examples/          # Ejemplos prácticos e implementaciones de referencia (opcional)
└── resources/         # Plantillas, esquemas o archivos auxiliares (opcional)
```

---

## Especificaciones del Archivo `SKILL.md`

### 1. Frontmatter YAML (Obligatorio)
Debe ubicarse al inicio estricto del archivo:
```yaml
---
name: nombre-de-la-habilidad
description: Descripción detallada en tercera persona que explique QUÉ hace la habilidad y CUÁNDO debe usarse. Incluye palabras clave relevantes.
---
```

**Reglas del Frontmatter:**
- `name`: Nombre único en minúsculas, usando guiones como separadores (ejemplo: `analizador-de-codigo`). Si se omite, se asumirá el nombre del directorio.
- `description`: Redactada en tercera persona. Es el elemento crítico que evalúa el agente para decidir la relevancia y activación de la habilidad.

### 2. Cuerpo del Documento (Markdown)
El contenido principal debe ser determinista, estructurado y fácil de seguir:
- **Propósito y Contexto**: Qué problema soluciona la habilidad.
- **Cuándo Usar la Habilidad**: Situaciones específicas e indicadores clave de activación.
- **Flujo de Trabajo Paso a Paso**: Secuencia lógica de tareas.
- **Árboles de Decisión o Reglas**: Criterios ante diferentes condiciones.
- **Uso de Scripts Auxiliares**: Instruir al agente a ejecutar scripts con `--help` primero antes de inspeccionar todo el código.

---

## Procedimiento Paso a Paso para Crear una nueva Habilidad

Cuando el usuario solicite crear una nueva habilidad, sigue estos pasos:

### Paso 1: Definición de Requisitos
Reúne la siguiente información con el usuario o determina según el contexto:
1. **Nombre de la habilidad**: Minúsculas separadas por guiones (ej. `generador-de-pruebas`).
2. **Propósito**: Objetivo principal de la habilidad.
3. **Casos de uso y activadores**: Frases o contexto donde aplica.
4. **Recursos adicionales**: Scripts, ejemplos o plantillas auxiliares requeridas.

### Paso 2: Generar la Estructura de Directorios
Puedes usar el script incluido para andamiar la estructura:
```powershell
python .agents/skills/creador-de-habilidades/scripts/crear_habilidad.py <nombre-habilidad> --desc "<descripcion>"
```

### Paso 3: Redactar el Archivo `SKILL.md`
Aplica la plantilla ubicada en `resources/plantilla_skill.md` completando las instrucciones detalladas en español.

### Paso 4: Agregar Recursos Adicionales (Opcional)
- Si incluye scripts, ubícalos en `scripts/`.
- Si incluye datos, plantillas o esquemas, colócalos en `resources/`.
- Si incluye ejemplos de uso o salida esperada, agrégalos en `examples/`.

### Paso 5: Validación y Confirmación
- Revisa que el bloque YAML no tenga errores sintácticos.
- Verifica que las rutas a los recursos sean correctas.
- Muestra al usuario un resumen de la habilidad creada y su ubicación.
