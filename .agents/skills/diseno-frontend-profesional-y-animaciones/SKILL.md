---
name: diseno-frontend-profesional-y-animaciones
description: Guía de diseño UI/UX profesional, definición de sistemas de diseño (Design Tokens), paletas HSL, tipografía moderna y micro-animaciones fluidas aceleradas por GPU. Úsala al construir interfaces web y móviles estéticamente memorables.
---

# Diseño Frontend Profesional y Micro-Animaciones

Esta habilidad dicta las directrices estéticas e interactivas para construir interfaces de usuario elegantes, modernas y alejadas de plantillas genéricas.

## Directrices de Estética e Interacción

### 1. Sistema de Diseño (Tokens)
- Usar variables CSS/Tokens para colores, espaciados, bordes y tipografías.
- Crear paletas de color equilibradas con contraste en modos claro y oscuro.
- Incorporar jerarquía tipográfica con fuentes modernas de alta calidad (Google Fonts).

### 2. Animaciones de Alto Rendimiento (60 FPS)
- Animar exclusivamente propiedades aceleradas por GPU (`transform`, `opacity`).
- Evitar animar propiedades que causen el recalculado del layout (`width`, `height`, `top`, `margin`).
- Diseñar micro-interacciones suaves para hovers, clics, modales y transiciones de estado.

### 3. Principios de UX
- Feedback visual inmediato ante cualquier acción del usuario.
- Estados de carga animados (skeleton screens) en lugar de spinners genéricos.
