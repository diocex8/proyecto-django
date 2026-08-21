---
name: ciberseguridad-y-hardened-app
description: Directrices de ciberseguridad informática, mitigación del OWASP Top 10, protección contra fraude, autenticación segura, sanitización de datos y robustecimiento de código. Úsala al auditar o implementar capas de seguridad.
---

# Ciberseguridad y Robustecimiento de Aplicaciones

Esta habilidad proporciona el protocolo de seguridad activa para prevenir vulnerabilidades y proteger los datos del sistema y de los usuarios.

## Pilares de Ciberseguridad

### 1. Mitigación del OWASP Top 10
- **Prevención de Inyecciones**: Usar consultas preparadas o parámetros vinculados en bases de datos. No concatenar cadenas en consultas.
- **Prevención de XSS**: Escapar y sanitizar todas las salidas renderizadas en el cliente. Usar políticas Content Security Policy (CSP).
- **Protección CSRF & CORS**: Configurar SameSite en cookies de sesión y restringir orígenes permitidos en CORS.

### 2. Autenticación y Gestión de Secretos
- Cero secretos o credenciales hardcodeados en el código fuente. Utilizar variables de entorno protegidas.
- Implementar hash seguro de contraseñas (bcrypt, Argon2).
- Usar tokens de sesión de vida corta con mecanismos seguros de rotación.

### 3. Firmado de Peticiones y Anti-Abuso
- Aplicar firmas criptográficas (HMAC) o verificación de integridad en peticiones críticas procedentes de clientes móviles o web.
- Implementar limitación de tasa (rate limiting) por dirección IP, usuario o dispositivo en endpoints sensibles.
