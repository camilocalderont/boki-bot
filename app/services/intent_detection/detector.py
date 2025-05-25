import logging
import numpy as np
from enum import Enum, auto
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class Intent(Enum):
    """Enum para los tipos de intención."""
    UNKNOWN = auto()
    FAQ = auto()
    APPOINTMENT = auto()
    END_CONVERSATION = auto()
    SUPPORT = auto()  # Nueva intención para soporte

class EnhancedIntentDetector:
    """
    Detector de intenciones mejorado usando sentence embeddings.
    """

    def __init__(self):
        logger.info("[INTENT] Inicializando detector mejorado...")

        try:
            # Cargar modelo - se descarga automáticamente la primera vez
            self.model = SentenceTransformer('distiluse-base-multilingual-cased')
            logger.info("[INTENT] Modelo sentence-transformers cargado exitosamente")
        except Exception as e:
            logger.error(f"[INTENT] Error cargando modelo: {e}")
            # Fallback al detector básico si falla
            self.model = None

        # Ejemplos de entrenamiento por intención
        self.intent_examples = {
            Intent.APPOINTMENT: [
                "quiero agendar una cita",
                "necesito reservar un turno",
                "puedo programar una consulta",
                "hay disponibilidad esta semana",
                "tengo que cancelar mi cita",
                "necesito reagendar mi turno",
                "quiero cambiar mi horario",
                "puedo sacar turno para mañana"
            ],
            Intent.FAQ: [
                "cuánto cuesta la consulta",
                "qué horarios tienen disponibles",
                "dónde están ubicados",
                "qué servicios ofrecen",
                "cómo puedo pagar",
                "cuáles son los precios",
                "tengo una pregunta sobre",
                "necesito información de"
            ],
            Intent.SUPPORT: [
                "tengo problemas con el pago",
                "no recibí confirmación de mi cita",
                "mi reserva no aparece en el sistema",
                "no puedo acceder a mi cuenta",
                "el sistema no funciona",
                "hay un error en mi factura",
                "tengo problemas con el flujo de citas",
                "no me funciona el agendamiento",
                "hay errores en el sistema de reservas",
                "tengo dificultades con la plataforma",
                "algo anda mal con el proceso",
                "no logro completar mi reserva",
                "el proceso no funciona bien",
                "hay fallas técnicas"
            ],
            Intent.END_CONVERSATION: [
                "gracias por todo",
                "ya no necesito nada más",
                "eso es todo por ahora",
                "hasta luego",
                "adiós",
                "perfecto, muchas gracias"
            ]
        }

        # Pre-calcular embeddings solo si el modelo está disponible
        self.intent_embeddings = None
        if self.model:
            self._precompute_embeddings()

    def _precompute_embeddings(self):
        """Pre-calcula embeddings de ejemplos para optimizar rendimiento."""
        logger.info("[INTENT] Pre-calculando embeddings...")

        self.intent_embeddings = {}
        for intent, examples in self.intent_examples.items():
            try:
                embeddings = self.model.encode(examples)
                self.intent_embeddings[intent] = embeddings
                logger.debug(f"[INTENT] Embeddings calculados para {intent}: {len(examples)} ejemplos")
            except Exception as e:
                logger.error(f"[INTENT] Error calculando embeddings para {intent}: {e}")

        logger.info("[INTENT] Pre-cálculo completado")

    def detect_intent(self, message: str) -> Intent:
        """
        Detecta la intención del mensaje usando similitud de coseno.

        Args:
            message: Texto del mensaje a analizar

        Returns:
            Intent: La intención detectada
        """
        if not self.model or not self.intent_embeddings:
            # Fallback a detección básica si el modelo no está disponible
            return self._fallback_detection(message)

        try:
            # Encoding del mensaje del usuario
            message_embedding = self.model.encode([message])

            best_intent = Intent.UNKNOWN
            best_score = 0.0
            scores = {}


            scores = {}
            for intent, examples_embeddings in self.intent_embeddings.items():
                similarities = cosine_similarity(message_embedding, examples_embeddings)[0]
                scores[intent] = float(np.max(similarities))

            # Ordenar por score
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            best_intent, best_score = sorted_scores[0]
            second_best_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0

            # Estrategia de umbral dinámico
            confidence_gap = best_score - second_best_score

            logger.debug(f"[INTENT] Scores: {scores}")
            logger.debug(f"[INTENT] Mejor: {best_intent} ({best_score:.3f})")
            logger.debug(f"[INTENT] Gap de confianza: {confidence_gap:.3f}")

            # Criterios más inteligentes
            if best_score >= 0.75:  # Alta confianza absoluta
                return best_intent
            elif best_score >= 0.55 and confidence_gap >= 0.15:  # Confianza relativa
                logger.info(f"[INTENT] Detectado por gap: {best_intent} ({best_score:.3f})")
                return best_intent
            elif best_score >= 0.45 and confidence_gap >= 0.25:  # Gap muy claro
                logger.info(f"[INTENT] Detectado por gap alto: {best_intent} ({best_score:.3f})")
                return best_intent
            else:
                logger.info(f"[INTENT] No hay confianza suficiente ({best_score:.3f}, gap: {confidence_gap:.3f})")
                return Intent.UNKNOWN

        except Exception as e:
            logger.error(f"[INTENT] Error en detección: {e}")
            return self._fallback_detection(message)

    def _fallback_detection(self, message: str) -> Intent:
        """Detección básica usando palabras clave como fallback."""
        message_lower = message.lower()

        logger.debug(f"[INTENT] Usando detección básica para: {message}")
        # Palabras clave básicas
        if any(word in message_lower for word in ['cita', 'turno', 'agendar', 'reservar', 'programar']):
            return Intent.APPOINTMENT
        elif any(word in message_lower for word in ['precio', 'costo', 'horario', 'servicio', 'información']):
            return Intent.FAQ
        elif any(word in message_lower for word in ['gracias', 'adiós', 'chao', 'hasta luego']):
            return Intent.END_CONVERSATION
        elif any(word in message_lower for word in ['problema', 'error', 'no funciona', 'ayuda']):
            return Intent.SUPPORT

        return Intent.UNKNOWN

    def get_confidence_scores(self, message: str) -> Dict[Intent, float]:
        """
        Retorna scores de confianza para todas las intenciones.
        Útil para debugging y análisis.
        """
        if not self.model or not self.intent_embeddings:
            return {Intent.UNKNOWN: 1.0}

        try:
            message_embedding = self.model.encode([message])
            scores = {}

            for intent, examples_embeddings in self.intent_embeddings.items():
                similarities = cosine_similarity(message_embedding, examples_embeddings)[0]
                scores[intent] = float(np.max(similarities))

            return scores
        except Exception as e:
            logger.error(f"[INTENT] Error obteniendo scores: {e}")
            return {Intent.UNKNOWN: 1.0}