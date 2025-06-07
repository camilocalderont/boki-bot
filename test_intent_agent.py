#!/usr/bin/env python3
"""
Script simple para probar el agente de intención
"""
import asyncio
import sys
import os
import time
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm.llm_service import LLMService

# Mock simple del llm_api_service para pruebas
class MockLLMApiService:
    async def get_company_agent_prompt(self, company_id: str, vc_agent_name: str):
        # Usar el prompt REAL del backend
        return {
            "status": "success",
            "message": "Agentes de empresa obtenidos de forma exitosa",
            "data": [
                {
                    "CompanyId": 1,
                    "VcAgentName": "intent_detection",
                    "TxPromptTemplate": "<|system|>\r\nEres un clasificador experto de intenciones para un bot de agendamiento de citas médicas y de belleza.\r\n\r\nMISIÓN: Analizar el mensaje del usuario y clasificar su intención con máxima precisión.\r\n\r\nINTENCIONES DISPONIBLES Y CRITERIOS:\r\n\r\n🎯 APPOINTMENT\r\nCuando el usuario quiere:\r\n- Agendar, reservar, programar una cita/turno/consulta\r\n- Cancelar, reagendar, cambiar, modificar una cita existente\r\n- Consultar disponibilidad de horarios o fechas\r\n- Preguntar sobre sus citas agendadas o estado de reservas\r\n- Solicitar información específica sobre el proceso de agendamiento\r\n\r\nEJEMPLOS:\r\n\"quiero agendar una cita\", \"necesito reservar un turno\", \"puedo programar una consulta\", \"hay disponibilidad esta semana\", \"tengo que cancelar mi cita\", \"necesito reagendar mi turno\", \"quiero cambiar mi horario\", \"puedo sacar turno para mañana\", \"cuándo puedo agendar\", \"qué fechas tienen libres\", \"mi cita está confirmada\", \"quiero ver mis turnos\"\r\n\r\n🎯 FAQ  \r\nCuando el usuario pregunta sobre:\r\n- Precios, costos, tarifas de servicios\r\n- Horarios de atención generales\r\n- Ubicación, dirección, cómo llegar\r\n- Qué servicios ofrecen, información de tratamientos\r\n- Métodos de pago, formas de pagar\r\n- Políticas generales del negocio\r\n\r\nEJEMPLOS:\r\n\"cuánto cuesta la consulta\", \"qué horarios tienen disponibles\", \"dónde están ubicados\", \"qué servicios ofrecen\", \"cómo puedo pagar\", \"cuáles son los precios\", \"tengo una pregunta sobre\", \"necesito información de\", \"qué incluye el tratamiento\", \"aceptan tarjeta de crédito\", \"hasta qué hora atienden\"\r\n\r\n🎯 SUPPORT\r\nCuando el usuario reporta:\r\n- Problemas técnicos con el sistema, plataforma o bot\r\n- Errores en pagos, facturación o cobros\r\n- Issues con confirmaciones, notificaciones no recibidas\r\n- Dificultades para completar procesos\r\n- Quejas sobre el servicio o atención\r\n\r\nEJEMPLOS:\r\n\"tengo problemas con el pago\", \"no recibí confirmación de mi cita\", \"mi reserva no aparece en el sistema\", \"no puedo acceder a mi cuenta\", \"el sistema no funciona\", \"hay un error en mi factura\", \"no me funciona el agendamiento\", \"hay errores en el sistema de reservas\", \"tengo dificultades con la plataforma\", \"algo anda mal con el proceso\", \"no logro completar mi reserva\", \"el proceso no funciona bien\", \"hay fallas técnicas\"\r\n\r\n🎯 GREETING\r\nCuando el usuario:\r\n- Saluda inicialmente sin intención específica\r\n- Se presenta o inicia conversación cordialmente\r\n- Usa expresiones de cortesía para empezar\r\n\r\nEJEMPLOS:\r\n\"hola\", \"buenos días\", \"buenas tardes\", \"qué tal\", \"¿cómo están?\", \"hola, ¿cómo está?\", \"buenas\", \"muy buenos días\"\r\n\r\n🎯 END_CONVERSATION\r\nCuando el usuario:\r\n- Se despide claramente\r\n- Agradece y cierra la conversación\r\n- Indica que ya no necesita más ayuda\r\n\r\nEJEMPLOS:\r\n\"gracias por todo\", \"ya no necesito nada más\", \"eso es todo por ahora\", \"hasta luego\", \"adiós\", \"perfecto, muchas gracias\", \"ok, gracias\", \"chao\", \"nos vemos\"\r\n\r\nREGLAS DE DESAMBIGUACIÓN:\r\n\r\n1. APPOINTMENT vs FAQ: APPOINTMENT si quiere realizar acción personal, FAQ si busca información general\r\n2. APPOINTMENT vs SUPPORT: APPOINTMENT si proceso normal, SUPPORT si hay problema/error\r\n3. FAQ vs SUPPORT: FAQ si pregunta informativa, SUPPORT si reporta problema\r\n4. Si combina saludo + intención específica → Clasificar por la intención específica\r\n5. Mensajes ambiguos como \"tengo una pregunta\" → FAQ por defecto\r\n6. Acepta errores ortográficos y colombianismos\r\n\r\nINSTRUCCIONES DE SALIDA:\r\n- Responde ÚNICAMENTE con UNA palabra\r\n- Opciones válidas: APPOINTMENT, FAQ, SUPPORT, GREETING, END_CONVERSATION, UNKNOWN\r\n- Si no puedes clasificar con 95% certeza → UNKNOWN\r\n- NO agregues explicaciones o texto adicional\r\n- Siempre en MAYÚSCULAS\r\n\r\n<|user|>\r\nMensaje del usuario: \"$[user_message]\" \r\n\r\n<|assistant|>\r\nClasificación:",
                    "BIsActive": True,
                    "VcModelName": "mistral-intent",
                    "VcRepoId": "TheBloke/Mistral-7B-Instruct-v0.1-GGUF",
                    "VcFilename": "mistral-7b-instruct-v0.1.Q4_K_M.gguf",
                    "VcLocalName": "mistral-intent.gguf",
                    "DcTemperature": "0.01",
                    "IMaxTokens": 5,
                    "DcTopP": "0.90",
                    "ITopK": 3,
                    "IContextLength": 4096,
                    "TxStopTokens": "[\"\\n\", \".\", \",\", \":\", \";\"]",
                    "IMaxMemoryMb": 6000,
                    "INThreads": 2,
                    "BlsUseGpu": False
                }
            ]
        }

async def test_intent_detection():
    # Tiempo de inicio total
    start_total = time.time()
    start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("🧪 Iniciando prueba del agente de intención...")
    print(f"⏰ Tiempo de inicio: {start_datetime}")
    print("🔄 Usando Mistral 7B con prompt REAL del backend")
    print("🚀 Configuración OPTIMIZADA para hardware gamer:")
    print("   • 16GB RAM dedicada al modelo")
    print("   • 16 threads (Ryzen 7 5700x)")
    print("   • GPU acelerada (12GB VRAM)")
    
    # Crear servicio mock
    mock_api = MockLLMApiService()
    
    # Inicializar LLMService
    llm_service = LLMService(mock_api)
    
    # Casos de prueba MÁS COMPLEJOS y VARIADOS
    test_cases = [
        ("hola tienes disponibilidad para hacer un corte de pelo el día de hoy?", "APPOINTMENT")
    ]
    
    print(f"\n📝 Probando {len(test_cases)} casos de detección de intenciones:")
    print("=" * 80)
    
    correct = 0
    total = len(test_cases)
    
    for message, expected in test_cases:
        try:
            start_time = time.time()
            result = await llm_service.detect_intent(message, "1")
            end_time = time.time()
            inference_time = (end_time - start_time) * 1000  # en milisegundos
            status = "✅" if result == expected else "❌"
            print(f"{status} '{message}' → {result} (esperado: {expected}) [{inference_time:.0f}ms]")
            if result == expected:
                correct += 1
        except Exception as e:
            print(f"💥 ERROR con '{message}': {e}")
    
    # Tiempo final total
    end_total = time.time()
    end_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_time = end_total - start_total
    
    print("=" * 80)
    print(f"🎯 Precisión: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"⏰ Tiempo de finalización: {end_datetime}")
    print(f"⚡ Tiempo total de ejecución: {total_time:.2f} segundos")
    print(f"📈 Tiempo promedio por predicción: {(total_time/total)*1000:.0f}ms")
    print(f"✅ Pruebas completadas!")

if __name__ == "__main__":
    asyncio.run(test_intent_detection()) 