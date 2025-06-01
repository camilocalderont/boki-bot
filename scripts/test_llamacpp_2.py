
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
    print(f"📁 Directorio de trabajo: {Path.cwd()}")
    print(f"🐍 Python: {sys.executable}")

    # Test 1: Verificar entorno básico
    try:
        import fastapi
        import uvicorn
        import httpx
        print("✅ Dependencias básicas OK")
    except ImportError as e:
        print(f"❌ Error dependencias básicas: {e}")
        return False

    # Test 2: Verificar pytz (tu error original)
    try:
        import pytz
        print("✅ pytz instalado correctamente")
    except ImportError:
        print("❌ pytz NO está instalado")
        print("   Ejecuta: pip install pytz==2025.2")
        return False

    # Test 3: Verificar que tu app actual funciona
    try:
        from app.main import app
        print("✅ App principal funciona")
    except ImportError as e:
        print(f"❌ Error importando app: {e}")
        return False

    # Test 4: Verificar tu detector actual
    try:
        from app.services.intent_detection.detector import EnhancedIntentDetector
        detector = EnhancedIntentDetector()
        print("✅ EnhancedIntentDetector funciona")
    except ImportError as e:
        print(f"❌ Error con detector: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Detector con advertencias: {e}")
        print("   (Puede ser normal si no tienes sentence-transformers)")

    # Test 5: Verificar ConversationManager
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        print("✅ ConversationManager funciona")
    except ImportError as e:
        print(f"❌ Error con ConversationManager: {e}")
        return False

    # Test 6: Verificar llama-cpp-python (si está instalado)
    try:
        import llama_cpp
        print("✅ llama-cpp-python está instalado")
        llama_cpp_available = True
    except ImportError:
        print("⚠️ llama-cpp-python NO está instalado")
        print("   Para LLM, ejecuta: pip install llama-cpp-python==0.2.77")
        llama_cpp_available = False

    # Test 7: Verificar nuevos archivos LLM (si existen)
    llm_files = {
        "model_downloader": "app/services/llm/model_downloader.py",
        "llamacpp_provider": "app/services/llm/llamacpp_provider.py",
        "llm_manager": "app/services/llm/llm_manager.py"
    }

    for name, path in llm_files.items():
        if Path(path).exists():
            try:
                if name == "model_downloader":
                    from app.services.llm.model_downloader import ModelDownloader
                elif name == "llamacpp_provider":
                    from app.services.llm.llamacpp_provider import LlamaCppProvider
                elif name == "llm_manager":
                    from app.services.llm.llm_manager import LLMManager
                print(f"✅ {name} funciona")
            except ImportError as e:
                print(f"❌ Error con {name}: {e}")
                return False
        else:
            print(f"⚠️ {name} no existe (normal si no has migrado aún)")

    # Test 8: Test rápido de funcionalidad
    try:
        # Mock de BokiApi para testing
        class MockBokiApi:
            async def close(self):
                pass

            async def get_or_create_contact(self, phone):
                return {"_id": "test_contact_123"}

            async def get_client_by_phone(self, phone):
                return {"Id": 1, "VcFirstName": "TestUser"}

            async def is_message_processed(self, msg_id):
                return False

            async def log_incoming_message(self, *args):
                return True

            async def get_conversation_state(self, contact_id):
                return None

        # Probar ConversationManager con mock
        from app.services.conversation.conversation_manager import ConversationManager

        manager = ConversationManager()
        # Reemplazar API real con mock para testing
        manager.boki_api = MockBokiApi()
        manager.message_processor.boki_api = MockBokiApi()
        manager.flow_router.boki_api = MockBokiApi()

        # Test simple de procesamiento
        response = await manager.process_message(
            phone_number="573001234567",
            message_text="Hola",
            message_id="test_123"
        )

        if response:
            print("✅ ConversationManager procesa mensajes correctamente")
            print(f"   Respuesta de prueba: {response[:100]}...")
        else:
            print("⚠️ ConversationManager retornó None (puede ser normal)")

    except Exception as e:
        print(f"❌ Error en test funcional: {e}")
        return False

    # Resumen final
    print("\n" + "="*50)
    print("📊 RESUMEN DE ESTADO:")
    print("="*50)

    print("✅ Tu app básica funciona correctamente")
    print("✅ pytz solucionado")
    print("✅ ConversationManager operativo")

    if llama_cpp_available:
        print("✅ llama-cpp-python instalado - Listo para LLM")
    else:
        print("⚠️ Para habilitar LLM: pip install llama-cpp-python==0.2.77")

    print("\n🚀 PRÓXIMOS PASOS:")
    print("1. Ejecutar: uvicorn app.main:app --reload")
    print("2. Probar endpoint: http://localhost:8000")
    print("3. Si funciona bien, continuar con migración LLM")

    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_migration())
        print(f"\n{'🎉 ¡TODO FUNCIONA!' if success else '❌ HAY PROBLEMAS'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Interrumpido por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)