---
name: despliegue-ci-cd-y-devops
description: Guía de despliegue continuo, Dockerización, pipelines de GitHub Actions, hosting en Vercel/Cloudflare CDN y administración de servidores. Úsala al planificar la infraestructura de despliegue y servidores.
---

# Buenas Prácticas de Despliegue CI/CD y DevOps

Esta habilidad define las estrategias de automatización, empaquetado y publicación para entornos de desarrollo, pruebas y producción.

## Principios de Infraestructura y Despliegue

### 1. Integración y Entrega Continua (CI/CD)
- **Automatización de Pruebas**: Ejecutar suite de pruebas unitarias y linter en cada Pull Request antes de permitir la integración.
- **Despliegues Automáticos por Entorno**:
  - Rama `main` / `prod` $\rightarrow$ Entorno de Producción.
  - Rama `develop` / `staging` $\rightarrow$ Entorno de Pruebas.

### 2. Empaquetado en Contenedores (Docker)
- Crear construcciones multietapa (*Multi-stage builds*) para reducir el tamaño final de las imágenes.
- Ejecutar contenedores con usuarios sin privilegios de root por motivos de seguridad.
- Inyectar variables de entorno en tiempo de ejecución, nunca empacar secretos dentro de la imagen.

### 3. Redes de Distribución de Contenido (CDN) y Caché Edge
- Configurar cabeceras `Cache-Control` adecuadas según el tipo de recurso (assets estáticos e inmutables vs páginas HTML dinámicas).
- Forzar comunicaciones HTTPS/TLS 1.3 con certificados SSL renovados automáticamente.
