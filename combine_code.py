#!/usr/bin/env python3
"""
Script para combinar todos los archivos de código Python del proyecto boki-bot
en un solo archivo con el formato: #ruta/archivo.py seguido del contenido
"""

import os
import sys
from pathlib import Path

def should_include_file(file_path):
    """
    Determina si un archivo debe ser incluido en la combinación
    """
    # Extensiones de archivo a incluir (expandido para más tipos de proyecto)
    included_extensions = {
        # Python
        '.py', '.pyx', '.pyi',
        # Web/JavaScript/TypeScript
        '.js', '.ts', '.jsx', '.tsx', '.vue', '.svelte',
        # Configuración y datos
        '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf',
        # Documentación y texto
        '.md', '.txt', '.rst', '.adoc',
        # Configuración de entorno
        '.env.local', '.env.example',
        # Estilos y templates
        '.css', '.scss', '.sass', '.less', '.html', '.htm',
        # Configuración de build y CI
        '.dockerfile', '.dockerignore', '.gitignore', '.gitattributes',
        # Otros archivos de código
        '.sql', '.graphql', '.gql', '.proto',
        # Archivos de configuración sin extensión común
        'Dockerfile', 'Makefile', 'Procfile'
    }

    # Carpetas a excluir
    excluded_dirs = {
        '.git', '__pycache__', '.venv', 'venv', '.vscode',
        'node_modules', '.pytest_cache', '.mypy_cache',
        'logs', '.DS_Store', 'dist', 'build', '.next',
        'coverage', '.nyc_output', '.cache', 'public',
        'static', 'assets/images', 'assets/img'
    }

    # Archivos específicos a excluir
    excluded_files = {
        '.DS_Store', '.gitignore', 'combine_code.py',
        'combined_code.txt', 'package-lock.json', 'yarn.lock',
        'pnpm-lock.yaml', '.eslintcache'
    }

    # Verificar si está en una carpeta excluida
    for part in file_path.parts:
        if part in excluded_dirs:
            return False

    # Verificar si es un archivo excluido
    if file_path.name in excluded_files:
        return False

    # Verificar extensión
    if file_path.suffix.lower() in included_extensions:
        return True

    # Verificar archivos sin extensión pero con nombres específicos
    if file_path.name in included_extensions:
        return True

    # Incluir archivos sin extensión que puedan ser archivos de configuración
    if not file_path.suffix and file_path.is_file():
        try:
            # Intentar leer el archivo para ver si es texto
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(100)  # Leer solo los primeros 100 caracteres
                # Verificar si parece ser texto válido
                if len(content) > 0 and content.isprintable():
                    return True
        except:
            return False

    return False

def combine_files(root_dir, output_file):
    """
    Combina todos los archivos relevantes del directorio en un solo archivo
    """
    root_path = Path(root_dir)

    if not root_path.exists():
        print(f"Error: El directorio {root_dir} no existe")
        return False

    combined_content = []
    file_count = 0
    file_types = {}

    # Recorrer todos los archivos recursivamente
    for file_path in sorted(root_path.rglob('*')):
        if file_path.is_file() and should_include_file(file_path):
            try:
                # Obtener la ruta relativa
                relative_path = file_path.relative_to(root_path)

                # Contar tipos de archivo para estadísticas
                extension = file_path.suffix.lower() or 'sin_extension'
                file_types[extension] = file_types.get(extension, 0) + 1

                # Leer el contenido del archivo
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Agregar al contenido combinado
                combined_content.append(f"# {relative_path}")
                combined_content.append(content)
                combined_content.append("")  # Línea en blanco entre archivos

                file_count += 1
                print(f"Procesado: {relative_path}")

            except Exception as e:
                print(f"Error al procesar {file_path}: {e}")

    # Escribir el archivo combinado
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(combined_content))

        print(f"\n✅ Éxito: {file_count} archivos combinados en '{output_file}'")

        # Mostrar estadísticas por tipo de archivo
        if file_types:
            print("\n📊 Estadísticas por tipo de archivo:")
            for ext, count in sorted(file_types.items()):
                print(f"  {ext}: {count} archivo(s)")

        return True

    except Exception as e:
        print(f"Error al escribir el archivo de salida: {e}")
        return False

def main():
    """
    Función principal
    """
    # Directorio del proyecto (directorio actual por defecto)
    project_dir = "."
    output_file = "combined_code.txt"

    # Permitir especificar directorio como argumento
    if len(sys.argv) > 1:
        project_dir = sys.argv[1]

    # Permitir especificar archivo de salida como segundo argumento
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    print(f"🚀 Combinando archivos del directorio: {os.path.abspath(project_dir)}")
    print(f"📁 Archivo de salida: {output_file}")
    print("-" * 50)

    success = combine_files(project_dir, output_file)

    if success:
        print(f"\n📋 El código combinado está disponible en: {os.path.abspath(output_file)}")
    else:
        print("\n❌ Hubo errores al combinar los archivos")
        sys.exit(1)

if __name__ == "__main__":
    main()