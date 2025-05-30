import logging
from typing import Tuple, Dict, List, Union, Optional
from app.shared.whatsapp.helper import WhatsAppHelper
from datetime import datetime
from .validators import CheckAppointmentValidators

logger = logging.getLogger(__name__)

class CheckAppointmentSteps:
    """
    Responsabilidad única: Lógica de cada paso del flujo de consulta de citas.
    """

    def __init__(self, boki_api):
        self.boki_api = boki_api
        self.whatsapp_helper = WhatsAppHelper()

    async def show_appointments(self) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso inicial: Mostrar listado de citas pendientes del cliente."""
        try:
            # Este método será llamado con el contact_id, pero necesitamos obtenerlo del contexto
            # Por ahora, retornamos un mensaje indicando que necesitamos el contact_id
            return (
                {"step": "need_contact_id", "data": {}},
                "🔄 Consultando tus citas...",
                False
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo citas: {e}")
            return (
                {},
                "❌ Hubo un error al consultar tus citas. Por favor intenta nuevamente.",
                True
            )

    async def show_appointments_for_contact(self, contact_id: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """Mostrar listado de citas pendientes para un contacto específico."""
        try:
            logger.info(f"Consultando citas para contacto: {contact_id}")
            
            # Obtener información del contacto
            contact_info = await self.boki_api.get_contact_by_id(contact_id)
            if not CheckAppointmentValidators.validate_contact_info(contact_info):
                return (
                    {},
                    "❌ No se pudo obtener tu información. Por favor intenta nuevamente.",
                    True
                )

            phone_number = contact_info.get('phone')

            # Obtener cliente asociado
            client_data = await self.boki_api.get_client_by_phone(phone_number)
            if not CheckAppointmentValidators.validate_client_data(client_data):
                return (
                    {},
                    "❌ No tienes un perfil de cliente registrado. Para consultar citas, primero debes agendar una.",
                    True
                )

            client_id = client_data.get('Id')
            logger.info(f"Cliente encontrado: {client_id}")

            # Obtener citas pendientes del cliente
            appointments = await self.boki_api.get_client_appointments(client_id, only_pending=True)
            
            if not CheckAppointmentValidators.validate_appointments(appointments):
                return (
                    {},
                    "📅 No tienes citas pendientes en este momento.\n\n"
                    "💡 Si deseas agendar una nueva cita, escribe 'agendar' 😊",
                    True
                )

            # Formatear y mostrar las citas
            return self._format_appointments_response(appointments)
            
        except Exception as e:
            logger.error(f"Error obteniendo citas para contacto {contact_id}: {e}")
            return (
                {},
                "❌ Hubo un error al consultar tus citas. Por favor intenta nuevamente.",
                True
            )

    def _format_appointments_response(self, appointments: List[Dict]) -> Tuple[Dict, Union[str, Dict], bool]:
        """Formatea la respuesta con la lista de citas."""
        try:
            message = "📋 *TUS CITAS PENDIENTES*\n\n"
            
            buttons = []
            
            for i, appointment in enumerate(appointments[:10], 1):  # Máximo 10 citas
                # Extraer información de la cita
                appointment_id = appointment.get('Id', 'N/A')
                service_name = appointment.get('ServiceName', 'Servicio')
                professional_name = appointment.get('ProfessionalName', 'Profesional')
                date_str = appointment.get('DtDate', '')
                time_str = appointment.get('TStartTime', '')
                
                # Formatear fecha y hora
                formatted_date = self._format_appointment_date(date_str)
                formatted_time = self._format_appointment_time(time_str)
                
                # Agregar información de la cita al mensaje
                message += f"🗓️ *Cita #{appointment_id}*\n"
                message += f"👨‍⚕️ *Profesional:* {professional_name}\n"
                message += f"💼 *Servicio:* {service_name}\n"
                message += f"📅 *Fecha:* {formatted_date}\n"
                message += f"🕐 *Hora:* {formatted_time}\n"
                message += "─────────────────────\n\n"

            # Agregar botón para salir
            buttons.append({
                "id": "exit_check_appointments",
                "title": "🏠 Menú Principal",
                "description": "Volver al menú principal"
            })

            # Usar formato de lista simple si hay muchas citas
            if len(appointments) > 3:
                message += "💬 Si necesitas cancelar o reprogramar alguna cita, contáctanos.\n\n"
                message += "📞 *¿Necesitas ayuda?*\n"
                message += "Escribe 'contacto' para hablar con un representante."
                
                return (
                    {"step": "waiting_action", "data": {"appointments": appointments}},
                    self.whatsapp_helper.create_button_message(message, buttons),
                    False
                )
            else:
                # Para pocas citas, podemos agregar botones de acción
                message += "💬 Si necesitas modificar alguna cita, contáctanos.\n\n"
                
                return (
                    {"step": "waiting_action", "data": {"appointments": appointments}},
                    self.whatsapp_helper.create_button_message(message, buttons),
                    False
                )
                
        except Exception as e:
            logger.error(f"Error formateando respuesta de citas: {e}")
            return (
                {},
                "❌ Hubo un error al mostrar tus citas. Por favor intenta nuevamente.",
                True
            )

    def _format_appointment_date(self, date_str: str) -> str:
        """Formatea la fecha de la cita para mostrar al usuario."""
        try:
            if not date_str:
                return "Fecha no disponible"
                
            # Intentar parsear diferentes formatos de fecha
            formats_to_try = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d/%m/%Y",
                "%m/%d/%Y"
            ]
            
            for date_format in formats_to_try:
                try:
                    date_obj = datetime.strptime(date_str[:10], date_format)
                    # Formatear en español
                    months = [
                        "enero", "febrero", "marzo", "abril", "mayo", "junio",
                        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
                    ]
                    weekdays = [
                        "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"
                    ]
                    
                    weekday = weekdays[date_obj.weekday()]
                    month = months[date_obj.month - 1]
                    
                    return f"{weekday.capitalize()} {date_obj.day} de {month}"
                except ValueError:
                    continue
            
            # Si no se puede parsear, devolver la fecha original
            return date_str
            
        except Exception as e:
            logger.error(f"Error formateando fecha: {e}")
            return date_str or "Fecha no disponible"

    def _format_appointment_time(self, time_str: str) -> str:
        """Formatea la hora de la cita para mostrar al usuario."""
        try:
            if not time_str:
                return "Hora no disponible"
                
            # Intentar parsear diferentes formatos de hora
            formats_to_try = [
                "%H:%M:%S",
                "%H:%M",
                "%I:%M %p",
                "%I:%M:%S %p"
            ]
            
            for time_format in formats_to_try:
                try:
                    time_obj = datetime.strptime(time_str, time_format).time()
                    # Formatear en formato 12 horas
                    return time_obj.strftime("%I:%M %p").lower().replace("am", "AM").replace("pm", "PM")
                except ValueError:
                    continue
            
            # Si no se puede parsear, devolver la hora original
            return time_str
            
        except Exception as e:
            logger.error(f"Error formateando hora: {e}")
            return time_str or "Hora no disponible"

    async def process_action_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Procesa la selección de acción del usuario."""
        if message == "exit_check_appointments" or message.lower() in ["menu", "menú", "salir", "volver"]:
            return (
                {},
                "🏠 Has vuelto al menú principal.\n\n"
                "💬 Escribe 'agendar' para agendar una cita\n"
                "📋 Escribe 'consultar' para ver tus citas\n"
                "📞 Escribe 'contacto' para hablar con un representante",
                True
            )
        else:
            # Para cualquier otro mensaje, mostrar opciones disponibles
            return (
                {"step": "waiting_action", "data": data},
                "❓ No entendí tu mensaje.\n\n"
                "Por favor selecciona una de las opciones disponibles o escribe:\n"
                "🏠 'menu' - para volver al menú principal\n"
                "📞 'contacto' - para hablar con un representante",
                False
            ) 