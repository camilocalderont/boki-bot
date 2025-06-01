#!/usr/bin/env python3
"""
Script para verificar que la migración a llama-cpp-python funciona.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Agregar path del proyecto
sys.path.append(str(Path(__file__).parent.parent))

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def test_migration():
    """Prueba completa de la migración."""

    print("🔄 Probando migración Ollama → LlamaCpp...")

    # Test 1: Importaciones
    try:
        from app.services.llm.llamacpp_provider import LlamaCppProvider
        from app.services.llm.model_downloader import ModelDownloader
        from app.services.llm.llm_manager import LLMManager
        print("✅ Importaciones correctas")
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False

    # Test 2: Model Downloader
    try:
        downloader = ModelDownloader()
        model_info = downloader.get_model_info()
        print("✅ ModelDownloader funciona")
        print(f"   Modelos configurados: {list(model_info.keys())}")
    except Exception as e:
        print(f"❌ Error en ModelDownloader: {e}")
        return False

    # Test 3: Provider básico
    try:
        provider = LlamaCppProvider()
        print("✅ LlamaCppProvider instanciado")

        # Verificar disponibilidad (sin cargar modelos)
        try:
            import llama_cpp
            print("✅ llama-cpp-python está instalado")
        except ImportError:
            print("❌ llama-cpp-python NO está instalado")
            print("   Ejecuta: pip install llama-cpp-python==0.2.77")
            return False

    except Exception as e:
        print(f"❌ Error en LlamaCppProvider: {e}")
        return False

    # Test 4: Mock de BokiApi para LLMManager
    class MockBokiApi:
        async def close(self):
            pass

    try:
        llm_manager = LLMManager(MockBokiApi())
        print("✅ LLMManager instanciado correctamente")
    except Exception as e:
        print(f"❌ Error en LLMManager: {e}")
        return False

    # Test 5: Descarga de modelos (opcional)
    print("\n🤔 ¿Quieres probar la descarga de modelos? (tardará varios minutos)")
    print("   Escribe 'y' para descargar, cualquier otra cosa para saltar:")

    try:
        user_input = input().strip().lower()
        if user_input == 'y':
            print("📥 Iniciando descarga de modelos...")

            # Descargar solo modelo pequeño para testing
            success, path = await downloader.ensure_model_available("intent")

            if success:
                print(f"✅ Modelo de intenciones descargado: {path}")
                print("✅ ¡Migración completamente funcional!")
            else:
                print("❌ Error descargando modelo")
                return False
        else:
            print("⏭️ Saltando descarga de modelos")
            print("✅ Migración lista (modelos se descargarán automáticamente)")

    except KeyboardInterrupt:
        print("\n⏭️ Saltando descarga de modelos")

    print("\n🎉 ¡Migración a llama-cpp-python completada!")
    print("\n📋 Próximos pasos:")
    print("   1. Ejecutar: uvicorn app.main:app --reload")
    print("   2. Enviar mensaje de prueba al webhook")
    print("   3. Los modelos se descargarán automáticamente en primer uso")

    return True

if __name__ == "__main__":
    success = asyncio.run(test_migration())
    sys.exit(0 if success else 1)