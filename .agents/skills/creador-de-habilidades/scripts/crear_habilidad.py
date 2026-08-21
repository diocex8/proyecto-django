#!/usr/bin/env python3
"""
Script auxiliar para andamiar y crear la estructura base de una nueva habilidad (skill) para Antigravity.
"""

import sys
import os
import argparse

PLANTILLA_SKILL = """---
name: {name}
description: {description}
---

# {title}

Descripción detallada de la habilidad y el problema que resuelve.

## Cuándo usar esta habilidad

- Usa esta habilidad cuando el usuario solicite...
- Es útil para tareas relacionadas con...

## Flujo de Trabajo

1. **Paso 1: Análisis**: Inspeccionar los requerimientos y el estado del proyecto.
2. **Paso 2: Ejecución**: Aplicar los cambios o transformaciones necesarias.
3. **Paso 3: Verificación**: Comprobar que los cambios son correctos.

## Reglas e Instrucciones Específicas

- Mantener la coherencia del proyecto y buenas prácticas de desarrollo.
- Si la habilidad incluye scripts en `scripts/`, ejecútalos primero con `--help`.
"""

def main():
    parser = argparse.ArgumentParser(description="Crea la estructura base para una nueva habilidad de Antigravity.")
    parser.add_argument("name", help="Nombre de la habilidad (ej. generador-de-pruebas)")
    parser.add_argument("--desc", default="Descripción en tercera persona de la habilidad y cuándo activarla.", help="Descripción para el frontmatter YAML")
    parser.add_argument("--target-dir", default=".agents/skills", help="Directorio destino para la habilidad")
    
    args = parser.parse_args()
    
    skill_name = args.name.lower().replace(" ", "-")
    skill_dir = os.path.join(args.target_dir, skill_name)
    
    os.makedirs(os.path.join(skill_dir, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(skill_dir, "examples"), exist_ok=True)
    os.makedirs(os.path.join(skill_dir, "resources"), exist_ok=True)
    
    title = skill_name.replace("-", " ").title()
    skill_md_content = PLANTILLA_SKILL.format(
        name=skill_name,
        description=args.desc,
        title=title
    )
    
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    with open(skill_md_path, "w", encoding="utf-8") as f:
        f.write(skill_md_content)
        
    print(f"Habilidad '{skill_name}' creada con éxito en: {skill_dir}")
    print(f"Archivo principal generado: {skill_md_path}")

if __name__ == "__main__":
    main()
