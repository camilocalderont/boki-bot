import logging
from typing import Tuple, Dict, Optional, List, Union
from app.services.conversation.flows.base_flow import BaseFlow
from app.services.boki_api import BokiApi
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class AppointmentFlow(BaseFlow):
    """Implementa el flujo de agendamiento de citas."""

    def __init__(self):
        self.boki_api = BokiApi()

    def _create_buttons_response(self, text: str, buttons: List[Dict], max_buttons: int = 3) -> Union[str, Dict]:
        """
        Crea una respuesta con botones para WhatsApp.
        
        Args:
            text: Texto del mensaje
            buttons: Lista de botones con formato [{"id": "1", "title": "Opción 1"}, ...]
            max_buttons: Máximo número de botones (WhatsApp limita a 3 botones por mensaje)
        """
        # Código para botones reales
        if len(buttons) <= max_buttons:
            return {
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": text},
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": btn["id"],
                                    "title": btn["title"][:20]  # WhatsApp limita a 20 caracteres
                                }
                            } for btn in buttons
                        ]
                    }
                }
            }
        else:
            # Si hay más de 3 opciones, usar lista
            return self._create_list_response(text, buttons)

    def _create_list_response(self, text: str, options: List[Dict], button_text: str = "Seleccionar") -> Union[str, Dict]:
        """
        Crea una respuesta con lista para WhatsApp cuando hay más de 3 opciones.
        """
        return {
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": text},
                "action": {
                    "button": button_text,
                    "sections": [
                        {
                            "title": "Opciones disponibles",
                            "rows": [
                                {
                                    "id": opt["id"],
                                    "title": opt["title"][:20],  # WhatsApp limita a 20 caracteres
                                    "description": opt.get("description", "")[:72]  # Límite de 72 caracteres
                                } for opt in options
                            ]
                        }
                    ]
                }
            }
        }

    def _extract_user_selection(self, message: str, options_data: List[Dict]) -> Optional[Dict]:
        """
        Extrae la selección del usuario y retorna el objeto seleccionado.
        
        Args:
            message: Mensaje del usuario (puede ser ID de botón, número, o título)
            options_data: Lista de opciones disponibles con sus datos completos
        """
        logger.debug(f"[APPOINTMENT] Extrayendo selección de mensaje: '{message}'")
        logger.debug(f"[APPOINTMENT] Opciones disponibles: {[opt.get('button_id') for opt in options_data]}")
        
        # 1. Primero intentar buscar por ID directo (ej: "cat_id_1", "srv_id_2")
        for option in options_data:
            button_id = option.get('button_id')
            if message == button_id:
                logger.debug(f"[APPOINTMENT] Selección encontrada por ID: {message} -> {option.get('real_id', 'N/A')}")
                return option
        
        # 2. Intentar buscar por título exacto del servicio/categoría
        message_clean = message.strip().lower()
        for option in options_data:
            if 'data' in option:
                title = option['data'].get('VcName', '').strip().lower()
                if message_clean == title:
                    logger.debug(f"[APPOINTMENT] Selección encontrada por título exacto: '{message}' -> '{title}'")
                    return option
        
        # 3. Intentar por número de índice
        try:
            selection = int(message.strip())
            if 1 <= selection <= len(options_data):
                selected_option = options_data[selection - 1]
                logger.debug(f"[APPOINTMENT] Selección encontrada por número: {selection} -> {selected_option.get('real_id', 'N/A')}")
                return selected_option
        except ValueError:
            logger.debug(f"[APPOINTMENT] Mensaje no es un número válido: {message}")
        
        # 4. Intentar buscar por coincidencia parcial en el título (fallback)
        for option in options_data:
            if 'data' in option:
                title = option['data'].get('VcName', '').lower()
                if message_clean in title or title in message_clean:
                    logger.debug(f"[APPOINTMENT] Selección encontrada por coincidencia parcial: '{message}' -> '{title}'")
                    return option
        
        # 5. Para profesionales, intentar buscar por nombre completo
        for option in options_data:
            if 'data' in option:
                professional = option['data']
                # Si tiene campos de profesional, construir nombre completo
                if 'VcFirstName' in professional:
                    full_name = self._format_professional_name(professional).lower()
                    if message_clean == full_name or message_clean in full_name:
                        logger.debug(f"[APPOINTMENT] Selección encontrada por nombre de profesional: '{message}' -> '{full_name}'")
                        return option
        
        logger.warning(f"[APPOINTMENT] No se pudo extraer selección de: '{message}' con {len(options_data)} opciones")
        logger.debug(f"[APPOINTMENT] Títulos disponibles: {[opt.get('data', {}).get('VcName', 'N/A') for opt in options_data]}")
        return None

    def _clean_data_for_storage(self, data):
        """Limpia los datos para almacenamiento, removiendo campos pesados como imágenes."""
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                # Omitir campos de imágenes que son muy pesados
                if key in ['TxPicture', 'TxPhoto','TxLogo','TxImages']:
                    continue
                elif isinstance(value, (dict, list)):
                    cleaned[key] = self._clean_data_for_storage(value)
                else:
                    cleaned[key] = value
            return cleaned
        elif isinstance(data, list):
            return [self._clean_data_for_storage(item) for item in data]
        else:
            return data

    async def process_message(self, state: Dict, message: str, contact_id: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """
        Procesa un mensaje en el flujo de agendamiento.

        Returns:
            Tuple[Dict, str, bool]: (nuevo_estado, respuesta, flujo_completado)
        """
        current_step = state.get("step", "initial")
        data = state.get("data", {})

        logger.info(f"[APPOINTMENT] Procesando paso '{current_step}' para contacto {contact_id}")
        logger.info(f"[APPOINTMENT] Estado actual: {state}")
        logger.info(f"[APPOINTMENT] Mensaje: '{message}'")

        try:
            result = None
            
            # Si es la primera vez (estado vacío o inicial), mostrar categorías
            if current_step in ["initial", ""] or not state:
                logger.info(f"[APPOINTMENT] Iniciando flujo - mostrando categorías")
                result = await self._show_categories()
            
            elif current_step == "waiting_category":
                logger.info(f"[APPOINTMENT] Procesando selección de categoría")
                result = await self._process_category_selection(message, data)
            
            elif current_step == "waiting_service":
                logger.info(f"[APPOINTMENT] Procesando selección de servicio")
                result = await self._process_service_selection(message, data)
            
            elif current_step == "waiting_professional":
                logger.info(f"[APPOINTMENT] Procesando selección de profesional")
                result = await self._process_professional_selection(message, data)
            
            elif current_step == "waiting_availability":
                logger.info(f"[APPOINTMENT] Procesando selección de disponibilidad")
                result = await self._process_availability_selection(message, data)
            
            elif current_step == "waiting_confirmation":
                logger.info(f"[APPOINTMENT] Procesando confirmación")
                result = await self._process_confirmation(message, data)
            
            else:
                logger.warning(f"[APPOINTMENT] Paso no reconocido: {current_step}")
                result = await self._show_categories()  # Reiniciar flujo

            # Verificar el resultado antes de retornarlo
            if result is None:
                logger.error(f"[APPOINTMENT] ¡RESULTADO ES NONE! Paso: {current_step}, Mensaje: '{message}'")
                # Fallback: reiniciar flujo
                result = await self._show_categories()
            
            new_state, response, is_completed = result
            logger.info(f"[APPOINTMENT] Resultado - Estado: {type(new_state)} {new_state is not None}, Respuesta: {type(response)}, Completado: {is_completed}")
            
            return result

        except Exception as e:
            logger.error(f"[APPOINTMENT] Error procesando mensaje: {e}", exc_info=True)
            logger.error(f"[APPOINTMENT] Detalles - Paso: {current_step}, Mensaje: '{message}', Estado: {state}")
            return await self._show_categories()

    async def _start_flow(self) -> Tuple[Dict, Union[str, Dict], bool]:
        """Inicia el flujo mostrando las categorías de servicios."""
        try:
            categories = await self.boki_api.get_category_services()
            
            if not categories:
                return (
                    {},
                    "Lo siento, no hay servicios disponibles en este momento. Por favor intenta más tarde.",
                    True  # Completar flujo por error
                )
            
            # Filtrar solo categorías de servicios (excluir políticas, reservas, etc.)
            service_categories = [cat for cat in categories if cat.get('BIsService', True)]
            
            if not service_categories:
                return (
                    {},
                    "Lo siento, no hay servicios de belleza disponibles en este momento.",
                    True
                )
            
            # Preparar datos de opciones con ID real
            options_data = []
            buttons = []
            
            for i, category in enumerate(service_categories, 1):
                category_id = category.get('Id')
                category_name = category.get('VcName', 'Servicio')
                button_id = f"cat_id_{category_id}"  # ID que incluye el ID real
                
                option_data = {
                    'button_id': button_id,
                    'real_id': category_id,
                    'data': category,
                    'index': i
                }
                options_data.append(option_data)
                
                buttons.append({
                    "id": button_id,
                    "title": category_name,
                    "description": f"Ver servicios de {category_name}"
                })
            
            text = "¡Perfecto! Te ayudo a agendar tu cita 📅\n\n¿Qué tipo de servicio necesitas?"
            
            # Si hay 3 o menos categorías, usar botones; si hay más, usar lista
            if len(service_categories) <= 3:
                response = self._create_buttons_response(text, buttons)
            else:
                response = self._create_list_response(text, buttons, "Ver servicios")
            
            new_state = {
                "step": "waiting_category",
                "data": {
                    "categories": service_categories,
                    "options_data": options_data  # Guardar mapeo completo
                }
            }
            
            return (new_state, response, False)
            
        except Exception as e:
            logger.error(f"[APPOINTMENT] Error iniciando flujo: {e}")
            return (
                {},
                "Hubo un error al cargar los servicios. Por favor intenta más tarde.",
                True
            )

    async def _process_category_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Procesa la selección de categoría de servicio."""
        options_data = data.get("options_data", [])
        
        logger.debug(f"[APPOINTMENT] Procesando selección de categoría: '{message}'")
        logger.debug(f"[APPOINTMENT] Datos disponibles: {len(options_data)} opciones")
        
        # Extraer selección usando el nuevo método
        selected_option = self._extract_user_selection(message, options_data)
        
        if selected_option is None:
            # Recrear botones para mostrar error con más información
            categories = data.get("categories", [])
            text = f"❌ No pude entender tu selección '{message}'.\n\n"
            text += "Por favor selecciona una de estas categorías:"
            
            # Respetar límite de WhatsApp: máximo 3 botones
            if len(categories) <= 3:
                buttons = []
                for category in categories:
                    buttons.append({
                        "type": "reply",
                        "reply": {
                            "id": f"cat_id_{category['Id']}",
                            "title": category['VcName'][:20]
                        }
                    })
                
                response = {
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": text},
                        "action": {"buttons": buttons}
                    }
                }
            else:
                # Usar lista para más de 3 categorías
                rows = []
                for category in categories:
                    rows.append({
                        "id": f"cat_id_{category['Id']}",
                        "title": category['VcName'][:20],  # ✅ CORREGIDO: máximo 20 caracteres
                        "description": f"Ver servicios de {category['VcName']}"[:72]
                    })
                
                response = {
                    "type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {"text": text},
                        "action": {
                            "button": "Ver categorías",
                            "sections": [{
                                "title": "Selecciona una categoría",
                                "rows": rows
                            }]
                        }
                    }
                }
            
            return (
                {"step": "waiting_category", "data": data},
                response,
                False
            )
        
        # Categoría seleccionada correctamente
        selected_category = selected_option["data"]
        category_id = selected_category["Id"]
        
        logger.info(f"[APPOINTMENT] Categoría seleccionada: {selected_category['VcName']} (ID: {category_id})")
        
        # Obtener servicios de la categoría
        services = await self.boki_api.get_services_by_category(category_id)
        
        if not services:
            return (
                {"step": "waiting_category", "data": data},
                f"❌ No hay servicios disponibles para la categoría {selected_category['VcName']}. Por favor selecciona otra categoría.",
                False
            )
        
        logger.info(f"[APPOINTMENT] Encontrados {len(services)} servicios para categoría {category_id}")
        
        # Limpiar datos pesados antes de guardar en el estado
        cleaned_services = self._clean_data_for_storage(services)
        cleaned_categories = self._clean_data_for_storage(data.get("categories", []))
        cleaned_selected_category = self._clean_data_for_storage(selected_category)
        
        # Preparar opciones de servicios para botones
        service_options_data = []
        for i, service in enumerate(services[:10], 1):  # Limitar a 10 servicios
            service_options_data.append({
                "button_id": f"srv_id_{service['Id']}",
                "real_id": service['Id'],
                "data": self._clean_data_for_storage(service),
                "index": i
            })
        
        # Crear botones de servicios
        if len(services) <= 3:
            # Usar botones para pocos servicios
            buttons = []
            for service in services[:3]:
                price_text = f"${service.get('IRegularPrice', 0):,}" if service.get('IRegularPrice') else ""
                title = f"{service['VcName'][:20]}"
                
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"srv_id_{service['Id']}",
                        "title": title
                    }
                })
            
            response = {
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": f"Servicios disponibles en {selected_category['VcName']}:"},
                    "action": {"buttons": buttons}
                }
            }
        else:
            # Usar lista para muchos servicios
            rows = []
            for service in services[:10]:
                price_text = f"${service.get('IRegularPrice', 0):,}" if service.get('IRegularPrice') else ""
                description = f"{price_text} - {service.get('VcTime', 'N/A')}"
                
                rows.append({
                    "id": f"srv_id_{service['Id']}",
                    "title": service['VcName'][:20],  # ✅ CORREGIDO: máximo 20 caracteres
                    "description": description[:72]
                })
            
            response = {
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {"text": f"Servicios disponibles en {selected_category['VcName']}:"},
                    "action": {
                        "button": "Ver servicios",
                        "sections": [{
                            "title": "Selecciona un servicio",
                            "rows": rows
                        }]
                    }
                }
            }
        
        # Nuevo estado (con datos limpios)
        new_state = {
            "step": "waiting_service",
            "data": {
                "categories": cleaned_categories,
                "options_data": data.get("options_data", []),
                "selected_category": cleaned_selected_category,
                "services": cleaned_services,
                "service_options_data": service_options_data
            }
        }
        
        logger.info(f"[APPOINTMENT] Resultado - Estado: {type(new_state)} {bool(new_state)}, Respuesta: {type(response)}, Completado: False")
        
        return (new_state, response, False)

    async def _process_service_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Procesa la selección de servicio y muestra profesionales."""
        service_options_data = data.get("service_options_data", [])
        
        logger.debug(f"[APPOINTMENT] Procesando selección de servicio: '{message}'")
        
        # Extraer selección
        selected_option = self._extract_user_selection(message, service_options_data)
        
        if selected_option is None:
            return (
                {"step": "waiting_service", "data": data},
                "❌ Por favor selecciona un servicio válido de las opciones mostradas.",
                False
            )
        
        selected_service = selected_option['data']
        service_id = selected_option['real_id']
        
        logger.info(f"[APPOINTMENT] Servicio seleccionado: {selected_service.get('VcName')} (ID: {service_id})")
        
        # Obtener profesionales para este servicio
        professionals = await self.boki_api.get_professionals_by_service(service_id)
        
        if not professionals:
            logger.warning(f"[APPOINTMENT] No hay profesionales para servicio {service_id}")
            return (
                {"step": "waiting_service", "data": data},
                f"❌ No hay profesionales disponibles para el servicio '{selected_service.get('VcName')}'. Por favor selecciona otro.",
                False
            )
        
        # Agregar servicio seleccionado a los datos
        data["selected_service"] = selected_service
        logger.info(f"[APPOINTMENT] Encontrados {len(professionals)} profesionales para servicio {service_id}")
        
        # Usar la función mejorada que maneja automáticamente 1 vs múltiples profesionales
        return await self._show_professionals_selection(data, professionals)

    def _format_professional_name(self, professional: Dict) -> str:
        """Formatea el nombre completo del profesional."""
        first_name = professional.get('VcFirstName', '').strip()
        second_name = professional.get('VcSecondName', '').strip() if professional.get('VcSecondName') else ''
        first_lastname = professional.get('VcFirstLastName', '').strip()
        second_lastname = professional.get('VcSecondLastName', '').strip() if professional.get('VcSecondLastName') else ''
        
        name_parts = [first_name]
        
        if second_name:
            name_parts.append(second_name)
        if first_lastname:
            name_parts.append(first_lastname)
        if second_lastname:
            name_parts.append(second_lastname)
        
        return ' '.join(name_parts)

    async def _show_professionals_selection(self, data: Dict, professionals: List[Dict]) -> Tuple[Dict, Union[str, Dict], bool]:
        """Muestra la lista de profesionales disponibles para selección con información detallada."""
        
        # Solo mostrar selección si hay más de 1 profesional
        if len(professionals) <= 1:
            if len(professionals) == 1:
                professional = professionals[0]
                data["selected_professional"] = professional
                
                service_name = data["selected_service"].get('VcName')
                
                logger.info(f"[APPOINTMENT] Solo un profesional disponible, saltando a disponibilidad")
                
                # Mensaje informativo con detalles del profesional
                prof_info = self._format_professional_detailed_info(professional)
                data["single_professional_message"] = f"✅ *Servicio:* {service_name}\n{prof_info}\n\n"
                
                return await self._show_availability(data)
            else:
                return (
                    {"step": "waiting_service", "data": data},
                    "❌ No hay profesionales disponibles para este servicio.",
                    False
                )
        
        # Para múltiples profesionales, crear mensaje informativo + lista de selección
        service_name = data["selected_service"].get('VcName')
        
        # Crear mensaje con información detallada de profesionales
        message = f"✅ *Servicio:* {service_name}\n\n"
        message += "👥 *NUESTROS PROFESIONALES DISPONIBLES:*\n\n"
        
        for i, professional in enumerate(professionals, 1):
            name = self._format_professional_name(professional)
            specialization = professional.get('VcSpecialization', '')
            profession = professional.get('VcProfession', '')
            years_exp = professional.get('IYearsOfExperience', 0)
            
            message += f"*{i}. {name}*\n"
            
            # Agregar profesión/especialización
            if specialization and profession and specialization.lower() != profession.lower():
                message += f"   📋 {profession} - Esp. en {specialization}\n"
            elif specialization:
                message += f"   📋 Especialista en {specialization}\n"
            elif profession:
                message += f"   📋 {profession}\n"
            
            # Agregar experiencia
            if years_exp > 0:
                message += f"   🎯 {years_exp} años de experiencia\n"
            
            # Separador entre profesionales (excepto el último)
            if i < len(professionals):
                message += "\n"
        
        message += "\n💡 Selecciona tu profesional de preferencia:"
        
        # Crear datos para la lista de selección
        prof_options_data = []
        buttons = []
        
        for i, professional in enumerate(professionals, 1):
            prof_id = professional.get('Id')
            
            # Crear nombre para mostrar en la lista
            first_name = professional.get('VcFirstName', '').strip()
            last_name = professional.get('VcFirstLastName', '').strip()
            
            # Nombre optimizado para la lista (máximo 20 caracteres)
            if last_name:
                if len(f"{first_name} {last_name}") <= 20:
                    display_name = f"{first_name} {last_name}"
                else:
                    display_name = f"{first_name} {last_name[0]}."
            else:
                display_name = first_name
            
            # Asegurar que no exceda 20 caracteres
            display_name = display_name[:20]
            
            button_id = f"prof_id_{prof_id}"
            
            option_data = {
                'button_id': button_id,
                'real_id': prof_id,
                'data': professional,
                'index': i
            }
            prof_options_data.append(option_data)
            
            # Crear descripción para la lista
            specialization = professional.get('VcSpecialization', '')
            years_exp = professional.get('IYearsOfExperience', 0)
            
            description_parts = []
            if specialization:
                description_parts.append(f"Esp. {specialization}")
            if years_exp > 0:
                description_parts.append(f"{years_exp}a exp.")
            
            description = " • ".join(description_parts)
            if len(description) > 72:
                description = description[:69] + "..."
            
            if not description:
                description = "Profesional disponible"
            
            buttons.append({
                "id": button_id,
                "title": display_name,
                "description": description
            })
        
        # Crear respuesta con lista interactiva
        response = {
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": message},
                "action": {
                    "button": "Seleccionar",
                    "sections": [{
                        "title": "Profesionales",  # ✅ CORREGIDO: máximo 24 caracteres
                        "rows": [
                            {
                                "id": btn["id"],
                                "title": btn["title"][:20],
                                "description": btn["description"][:72]
                            } for btn in buttons
                        ]
                    }]
                }
            }
        }
        
        new_state = {
            "step": "waiting_professional",
            "data": {
                **data,
                "professionals": professionals,
                "prof_options_data": prof_options_data
            }
        }
        
        return (new_state, response, False)


    async def _process_professional_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Procesa la selección de profesional."""
        prof_options_data = data.get("prof_options_data", [])
        
        logger.debug(f"[APPOINTMENT] Procesando selección de profesional: '{message}'")
        
        # Extraer selección
        selected_option = self._extract_user_selection(message, prof_options_data)
        
        if selected_option is None:
            # Recrear lista de profesionales para mostrar error
            professionals = data.get("professionals", [])
            service_name = data.get("selected_service", {}).get('VcName', 'el servicio')
            
            text = f"❌ No pude entender tu selección: '{message}'\n\n"
            text += f"Por favor selecciona uno de los profesionales disponibles para {service_name}:"
            
            # Recrear botones
            buttons = []
            for opt in prof_options_data:
                professional = opt['data']
                prof_name = self._format_professional_name(professional)
                prof_specialization = professional.get('VcSpecialization', '')
                
                description = ""
                if prof_specialization:
                    description = f"Especialista en {prof_specialization}"
                
                buttons.append({
                    "id": opt['button_id'],
                    "title": prof_name[:20],  # ✅ CORREGIDO: máximo 20 caracteres
                    "description": description[:72]
                })
            
            response = self._create_list_response(text, buttons, "Seleccionar profesional")
            
            return (
                {"step": "waiting_professional", "data": data},
                response,
                False
            )
        
        selected_professional = selected_option['data']
        prof_name = self._format_professional_name(selected_professional)
        
        logger.info(f"[APPOINTMENT] Profesional seleccionado: {prof_name} (ID: {selected_professional.get('Id')})")
        
        data["selected_professional"] = selected_professional
        return await self._show_availability(data)

    async def _show_availability(self, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Muestra la disponibilidad general del profesional."""
        professional = data["selected_professional"]
        service = data["selected_service"]
        
        professional_id = professional.get('Id')
        service_id = service.get('Id')
        
        logger.info(f"[APPOINTMENT] Obteniendo disponibilidad para profesional {professional_id}, servicio {service_id}")
        
        # Obtener disponibilidad general
        availability = await self.boki_api.get_general_availability(professional_id, service_id)
        
        if not availability:
            logger.warning(f"[APPOINTMENT] No hay disponibilidad para profesional {professional_id}")
            return (
                {"step": "waiting_service", "data": data},
                "❌ No hay fechas disponibles para este profesional. Por favor selecciona otro servicio o profesional.",
                False
            )
        
        logger.info(f"[APPOINTMENT] Encontradas {len(availability)} fechas disponibles")
        
        # Preparar datos de fechas
        date_options_data = []
        buttons = []
        
        # Mostrar solo las primeras 3 fechas inicialmente
        displayed_dates = availability[:3]
        
        for i, date_info in enumerate(displayed_dates, 1):
            date_str = date_info.get('date', date_info.get('fecha', ''))
            available_slots = date_info.get('available_slots', date_info.get('slots_disponibles', 0))
            button_id = f"date_{i}"  # Para fechas usamos índice simple
            
            option_data = {
                'button_id': button_id,
                'date': date_str,
                'data': date_info,
                'index': i
            }
            date_options_data.append(option_data)
            
            # Formatear fecha para mostrar
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d/%m - %a')
                # Traducir días de la semana
                day_translations = {
                    'Mon': 'Lun', 'Tue': 'Mar', 'Wed': 'Mié', 
                    'Thu': 'Jue', 'Fri': 'Vie', 'Sat': 'Sáb', 'Sun': 'Dom'
                }
                for eng, esp in day_translations.items():
                    formatted_date = formatted_date.replace(eng, esp)
            except:
                formatted_date = date_str
            
            buttons.append({
                "id": button_id,
                "title": formatted_date,
                "description": f"{available_slots} horarios disponibles"
            })
        
        # Si hay más fechas, agregar botón "Ver más"
        if len(availability) > 3:
            buttons.append({
                "id": "date_more",
                "title": "📅 Ver más fechas",
                "description": f"{len(availability) - 3} fechas adicionales"
            })
        
        # Construir mensaje
        prof_name = self._format_professional_name(professional)
        service_name = service.get('VcName')
        
        # Verificar si hay mensaje de profesional único
        single_prof_message = data.get("single_professional_message", "")
        
        if single_prof_message:
            # Caso: un solo profesional
            text = single_prof_message
            text += "📅 Selecciona una fecha disponible:"
        else:
            # Caso: profesional seleccionado de una lista
            text = f"¡Excelente! Has seleccionado:\n"
            text += f"👨‍⚕️ *Profesional:* {prof_name}\n"
            text += f"💼 *Servicio:* {service_name}\n\n"
            text += "📅 Selecciona una fecha disponible:"
        
        # Usar lista para fechas ya que puede haber muchas opciones
        response = self._create_list_response(text, buttons, "Seleccionar fecha")
        
        new_state = {
            "step": "waiting_date",
            "data": {
                **data,
                "availability": availability,
                "date_options_data": date_options_data
            }
        }
        
        return (new_state, response, False)

    async def _process_date_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Procesa la selección de fecha."""
        # Manejar "Ver más fechas"
        if message == "date_more":
            return await self._show_more_dates(data)
        
        date_options_data = data.get("date_options_data", [])
        
        # Extraer selección
        selected_option = self._extract_user_selection(message, date_options_data)
        
        if selected_option is None:
            return (
                {"step": "waiting_date", "data": data},
                "Por favor selecciona una fecha válida de las opciones mostradas.",
                False
            )
        
        selected_date_info = selected_option['data']
        return await self._show_time_slots(data, selected_date_info)

    async def _show_more_dates(self, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Muestra más fechas disponibles."""
        availability = data.get("availability", [])
        additional_dates = availability[3:8]  # Mostrar 5 más (del 4 al 8)
        
        if not additional_dates:
            return (
                {"step": "waiting_date", "data": data},
                "No hay más fechas disponibles.",
                False
            )
        
        text = "📅 *Fechas adicionales disponibles:*"
        
        # Preparar datos de fechas adicionales
        date_options_data = []
        buttons = []
        
        for i, date_info in enumerate(additional_dates, 4):
            date_str = date_info.get('date', date_info.get('fecha', ''))
            available_slots = date_info.get('available_slots', date_info.get('slots_disponibles', 0))
            button_id = f"date_{i}"
            
            option_data = {
                'button_id': button_id,
                'date': date_str,
                'data': date_info,
                'index': i
            }
            date_options_data.append(option_data)
            
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d/%m - %a')
            except:
                formatted_date = date_str
            
            buttons.append({
                "id": button_id,
                "title": formatted_date,
                "description": f"{available_slots} horarios disponibles"
            })
        
        # Agregar botón para volver
        buttons.append({
            "id": "date_back",
            "title": "⬅️ Volver",
            "description": "Ver primeras fechas"
        })
        
        response = self._create_list_response(text, buttons, "Seleccionar fecha")
        
        # Actualizar opciones disponibles
        data["date_options_data"] = date_options_data
        data["viewing_extended"] = True
        
        return (
            {"step": "waiting_date", "data": data},
            response,
            False
        )

    async def _show_time_slots(self, data: Dict, selected_date_info: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Muestra los horarios disponibles para la fecha seleccionada."""
        professional = data["selected_professional"]
        service = data["selected_service"]
        
        professional_id = professional.get('Id')
        service_id = service.get('Id')
        selected_date = selected_date_info.get('date', selected_date_info.get('fecha'))
        
        # Obtener slots disponibles
        slots = await self.boki_api.get_available_slots(professional_id, service_id, selected_date)
        
        if not slots:
            return (
                {"step": "waiting_date", "data": data},
                "No hay horarios disponibles para esta fecha. Por favor selecciona otra fecha.",
                False
            )
        
        data["selected_date"] = selected_date
        data["selected_date_info"] = selected_date_info
        
        # Preparar datos de horarios
        time_options_data = []
        buttons = []
        
        for i, slot in enumerate(slots, 1):
            start_time = slot.get('start_time', slot.get('hora_inicio', ''))
            end_time = slot.get('end_time', slot.get('hora_fin', ''))
            button_id = f"time_{i}"
            
            option_data = {
                'button_id': button_id,
                'data': slot,
                'index': i
            }
            time_options_data.append(option_data)
            
            time_display = start_time
            if end_time:
                time_display += f" - {end_time}"
            
            buttons.append({
                "id": button_id,
                "title": time_display,
                "description": "Horario disponible"
            })
        
        # Formatear fecha para mostrar
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y - %A')
        except:
            formatted_date = selected_date
        
        text = f"📅 *Fecha seleccionada:* {formatted_date}\n\n🕐 Selecciona tu horario preferido:"
        
        if len(slots) <= 3:
            response = self._create_buttons_response(text, buttons)
        else:
            response = self._create_list_response(text, buttons, "Seleccionar horario")
        
        new_state = {
            "step": "waiting_time",
            "data": {
                **data,
                "available_slots": slots,
                "time_options_data": time_options_data
            }
        }
        
        return (new_state, response, False)

    async def _process_time_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Procesa la selección de horario y muestra confirmación."""
        time_options_data = data.get("time_options_data", [])
        
        # Extraer selección
        selected_option = self._extract_user_selection(message, time_options_data)
        
        if selected_option is None:
            return (
                {"step": "waiting_time", "data": data},
                "Por favor selecciona un horario válido de las opciones mostradas.",
                False
            )
        
        selected_slot = selected_option['data']
        data["selected_slot"] = selected_slot
        
        # Mostrar resumen de confirmación con botones
        professional = data["selected_professional"]
        service = data["selected_service"]
        selected_date = data["selected_date"]
        
        prof_name = professional.get('VcName')
        service_name = service.get('VcName')
        service_duration = service.get('NnDuration', '')
        service_price = service.get('DcPrice', '')
        start_time = selected_slot.get('start_time', selected_slot.get('hora_inicio'))
        end_time = selected_slot.get('end_time', selected_slot.get('hora_fin'))
        
        # Formatear fecha
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y - %A')
        except:
            formatted_date = selected_date
        
        text = "✅ *CONFIRMACIÓN DE CITA*\n\n"
        text += f"👨‍⚕️ *Profesional:* {prof_name}\n"
        text += f"💼 *Servicio:* {service_name}"
        if service_duration:
            text += f" ({service_duration} min)"
        text += "\n"
        text += f"📅 *Fecha:* {formatted_date}\n"
        text += f"🕐 *Horario:* {start_time}"
        if end_time:
            text += f" - {end_time}"
        text += "\n"
        if service_price:
            text += f"💰 *Precio:* ${service_price}\n"
        
        text += "\n¿Confirmas esta cita?"
        
        # Crear botones de confirmación
        buttons = [
            {
                "id": "confirm_yes",
                "title": "✅ Sí, confirmar",
                "description": "Crear la cita"
            },
            {
                "id": "confirm_no", 
                "title": "❌ Cancelar",
                "description": "No crear la cita"
            }
        ]
        
        response = self._create_buttons_response(text, buttons)
        
        new_state = {
            "step": "waiting_confirmation",
            "data": data
        }
        
        return (new_state, response, False)

    async def _process_confirmation(self, message: str, data: Dict, contact_id: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """Procesa la confirmación final de la cita."""
        
        if message == "confirm_yes" or message.strip() == "1":
            # Confirmar y crear la cita
            return await self._create_appointment(data, contact_id)
        elif message == "confirm_no" or message.strip() == "2":
            # Cancelar y reiniciar
            return (
                {},
                "Cita cancelada. Si deseas agendar una nueva cita, escribe 'agendar' cuando gustes. 😊",
                True
            )
        else:
            return (
                {"step": "waiting_confirmation", "data": data},
                "Por favor selecciona una opción: confirmar o cancelar la cita.",
                False
            )

    async def _create_appointment(self, data: Dict, contact_id: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """Crea la cita en el sistema."""
        try:
            # Preparar datos para crear la cita
            professional = data["selected_professional"]
            service = data["selected_service"]
            selected_date = data["selected_date"]
            selected_slot = data["selected_slot"]
            
            appointment_data = {
                "contactId": contact_id,
                "professionalId": professional.get('Id'),
                "serviceId": service.get('Id'),
                "date": selected_date,
                "startTime": selected_slot.get('start_time', selected_slot.get('hora_inicio')),
                "endTime": selected_slot.get('end_time', selected_slot.get('hora_fin')),
                "status": "scheduled"
            }
            
            # Crear la cita
            result = await self.boki_api.create_appointment(appointment_data)
            
            if result:
                appointment_id = result.get('Id', 'N/A')
                prof_name = professional.get('VcName')
                service_name = service.get('VcName')
                
                # Formatear fecha para respuesta
                try:
                    date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%d/%m/%Y - %A')
                except:
                    formatted_date = selected_date
                
                start_time = selected_slot.get('start_time', selected_slot.get('hora_inicio'))
                
                response = "🎉 ¡CITA CONFIRMADA EXITOSAMENTE!\n\n"
                response += f"📋 *Número de cita:* {appointment_id}\n"
                response += f"👨‍⚕️ *Profesional:* {prof_name}\n"
                response += f"💼 *Servicio:* {service_name}\n"
                response += f"📅 *Fecha:* {formatted_date}\n"
                response += f"🕐 *Hora:* {start_time}\n\n"
                response += "📱 Recibirás un recordatorio antes de tu cita.\n"
                response += "💬 Si necesitas cancelar o reprogramar, contáctanos con anticipación.\n\n"
                response += "¡Nos vemos pronto! 😊"
                
                return ({}, response, True)
            else:
                logger.error("[APPOINTMENT] Error al crear cita - resultado nulo")
                return (
                    {"step": "waiting_confirmation", "data": data},
                    "Hubo un error al confirmar tu cita. Por favor intenta nuevamente.",
                    False
                )
                
        except Exception as e:
            logger.error(f"[APPOINTMENT] Error creando cita: {e}")
            return (
                {"step": "waiting_confirmation", "data": data},
                "Hubo un error al procesar tu cita. Por favor intenta nuevamente.",
                False
            )

    async def _show_categories(self) -> Tuple[Dict, Union[str, Dict], bool]:
        """Muestra las categorías de servicios disponibles."""
        logger.info("[APPOINTMENT] Obteniendo categorías de servicios")
        
        # Obtener categorías desde la API
        categories = await self.boki_api.get_category_services()
        
        if not categories:
            logger.warning("[APPOINTMENT] No se encontraron categorías")
            return (
                {"step": "error", "data": {}},
                "❌ No hay categorías de servicios disponibles en este momento. Por favor intenta más tarde.",
                True
            )
        
        logger.info(f"[APPOINTMENT] Encontradas {len(categories)} categorías")
        
        # Limpiar datos pesados antes de guardar
        cleaned_categories = self._clean_data_for_storage(categories)
        
        # Preparar opciones para botones con datos limpios
        options_data = []
        for i, category in enumerate(categories, 1):
            options_data.append({
                "button_id": f"cat_id_{category['Id']}",
                "real_id": category['Id'],
                "data": self._clean_data_for_storage(category),
                "index": i
            })
        
        text = "¡Perfecto! Vamos a agendar tu cita. 📅\n\nPrimero, selecciona la categoría de servicio que te interesa:"
        
        # Respetar límite de WhatsApp: máximo 3 botones
        if len(categories) <= 3:
            # Usar botones para 3 o menos categorías
            buttons = []
            for category in categories:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"cat_id_{category['Id']}",
                        "title": category['VcName'][:20]
                    }
                })
            
            response = {
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": text},
                    "action": {"buttons": buttons}
                }
            }
        else:
            # Usar lista para más de 3 categorías
            rows = []
            for category in categories:
                rows.append({
                    "id": f"cat_id_{category['Id']}",
                    "title": category['VcName'][:20],  # ✅ CORREGIDO: máximo 20 caracteres
                    "description": f"Ver servicios de {category['VcName']}"[:72]
                })
            
            response = {
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {"text": text},
                    "action": {
                        "button": "Ver categorías",
                        "sections": [{
                            "title": "Selecciona una categoría",
                            "rows": rows
                        }]
                    }
                }
            }
        
        # Estado inicial con datos limpios
        new_state = {
            "step": "waiting_category",
            "data": {
                "categories": cleaned_categories,
                "options_data": options_data
            }
        }
        
        logger.info(f"[APPOINTMENT] Estado creado con {len(cleaned_categories)} categorías limpias")
        
        return (new_state, response, False)
    
    async def _create_professionals_info_message(self, professionals: List[Dict]) -> str:
        """Crea un mensaje detallado con información de todos los profesionales."""
        
        message = "👥 *NUESTROS PROFESIONALES DISPONIBLES:*\n\n"
        
        for i, professional in enumerate(professionals, 1):
            prof_info = self._format_professional_detailed_info(professional)
            message += f"*{i}.* {prof_info}\n"
            
            if i < len(professionals):
                message += "\n" + "─" * 30 + "\n\n"
        
        message += "\n💡 *Tip:* Si ya conoces a algún profesional, búscalo por su nombre en la lista siguiente."
        
        return message
    
    def _format_professional_detailed_info(self, professional: Dict) -> str:
        """Formatea información detallada del profesional para mostrar."""
        
        name = self._format_professional_name(professional)
        specialization = professional.get('VcSpecialization', '')
        profession = professional.get('VcProfession', '')
        years_exp = professional.get('IYearsOfExperience', 0)
        
        info = f"👨‍⚕️ *{name}*"
        
        # Profesión y especialización
        if specialization and profession:
            if specialization.lower() != profession.lower():
                info += f"\n   📋 {profession} - Especialista en {specialization}"
            else:
                info += f"\n   📋 Especialista en {specialization}"
        elif specialization:
            info += f"\n   📋 Especialista en {specialization}"
        elif profession:
            info += f"\n   📋 {profession}"
        
        # Experiencia
        if years_exp > 0:
            info += f"\n   🎯 {years_exp} años de experiencia"
        
        return info