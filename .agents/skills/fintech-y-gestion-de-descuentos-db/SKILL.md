---
name: fintech-y-gestion-de-descuentos-db
description: Guía de buenas prácticas y patrones de dominio para diseñar motores de cupones, promociones, reglas de descuento, validación anti-abuso y auditoría contable. Úsala cuando se definan las reglas de negocio de beneficios y descuentos.
---

# Patrones para Motores de Descuentos y Promociones

Esta habilidad proporciona pautas de arquitectura de dominio para implementar motores de cupones, validaciones promocionales y auditorías de beneficios.

## Principios de Dominio para Descuentos

### 1. Pipeline de Validación de Promociones
Todo motor de validación de descuentos debe evaluar en orden determinista:
- **Vigencia Temporal**: Verificación de rango de fechas y estado activo.
- **Disponibilidad de Cupos**: Verificación de límites globales de canje.
- **Límites por Usuario**: Verificación de frecuencia máxima de uso por cuenta.
- **Condiciones de Carrito**: Verificación de montos mínimos de compra o categorías aplicables.
- **Elegibilidad de Usuario**: Verificación de estados de cuenta o requisitos de seguridad.

### 2. Control de Concurrencia y Anti-Abuso
- Implementar mecanismos de bloqueo o control de concurrencia al reclamar cupones de stock limitado para prevenir condiciones de carrera.
- Aplicar rate limiting y validación de identidad para evitar la creación masiva de cuentas falsas con fines de explotación de promociones.

### 3. Registro y Auditoría Contable (Ledger)
- Registrar cada transacción o canje en un historial inmutable de auditoría que consigne el monto original, el beneficio aplicado, la fecha y los actores involucrados.
- Asegurar trazabilidad completa para conciliación entre comercios y la plataforma.
