import logging
from typing import Tuple, Dict, List, Union, Optional
from app.shared.whatsapp.helper import WhatsAppHelper
from .selection_handler import SelectionHandler
from .data_formatter import DataFormatter
from .validators import AppointmentValidators

logger = logging.getLogger(__name__)

class AppointmentSteps:
    """
    Responsabilidad única: Lógica de cada paso del flujo de appointment.
    """

    def __init__(self, boki_api):
        self.boki_api = boki_api
        self.whatsapp_helper = WhatsAppHelper()

    async def show_categories(self) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 1: Mostrar categorías de servicios."""
        try:
            categories = await self.boki_api.get_category_services()
            
            if not AppointmentValidators.validate_categories(categories):
                return (
                    {},
                    "❌ No hay servicios disponibles en este momento.",
                    True
                )
            
            # Filtrar categorías de servicios
            service_categories = [
                cat for cat in categories 
                if cat.get('BIsService', True)
            ]
            
            # Limpiar datos pesados
            cleaned_categories = DataFormatter.clean_data_for_storage(service_categories)
            
            # Preparar opciones
            options_data = []
            buttons = []
            
            for i, category in enumerate(service_categories, 1):
                category_id = category.get('Id')
                category_name = category.get('VcName', 'Servicio')
                button_id = f"cat_id_{category_id}"
                
                options_data.append({
                    'button_id': button_id,
                    'real_id': category_id,
                    'data': DataFormatter.clean_data_for_storage(category),
                    'index': i
                })
                
                buttons.append({
                    "id": button_id,
                    "title": category_name,
                    "description": f"Ver servicios de {category_name}"
                })
            
            text = "¡Perfecto! Vamos a agendar tu cita. 📅\n\nPrimero, selecciona la categoría de servicio que te interesa:"
            
            # Usar helper de WhatsApp para respuesta automática
            response = self.whatsapp_helper.create_interactive_response(text, buttons)
            
            new_state = {
                "step": "waiting_category",
                "data": {
                    "categories": cleaned_categories,
                    "options_data": options_data
                }
            }
            
            return (new_state, response, False)
            
        except Exception as e:
            logger.error(f"Error mostrando categorías: {e}")
            return (
                {},
                "Hubo un error al cargar los servicios. Por favor intenta más tarde.",
                True
            )

    async def process_category_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 2: Procesar selección de categoría."""
        options_data = data.get("options_data", [])
        
        # Usar SelectionHandler para extraer selección
        selected_option = SelectionHandler.extract_user_selection(message, options_data)
        
        if selected_option is None:
            # Error con opciones disponibles
            categories = data.get("categories", [])
            text = f"❌ No pude entender tu selección '{message}'.\n\nPor favor selecciona una categoría:"
            
            buttons = []
            for category in categories:
                buttons.append({
                    "id": f"cat_id_{category['Id']}",
                    "title": category['VcName'],
                    "description": f"Ver servicios de {category['VcName']}"
                })
            
            response = self.whatsapp_helper.create_interactive_response(text, buttons)
            
            return (
                {"step": "waiting_category", "data": data},
                response,
                False
            )
        
        # Categoría seleccionada correctamente
        selected_category = selected_option["data"]
        category_id = selected_category["Id"]
        
        logger.info(f"Categoría seleccionada: {selected_category['VcName']} (ID: {category_id})")
        
        # Obtener servicios de la categoría
        services = await self.boki_api.get_services_by_category(category_id)
        
        if not AppointmentValidators.validate_services(services):
            return (
                {"step": "waiting_category", "data": data},
                f"❌ No hay servicios disponibles para {selected_category['VcName']}.",
                False
            )
        
        return await self._show_services(data, selected_category, services)

    async def _show_services(self, data: Dict, selected_category: Dict, services: List[Dict]) -> Tuple[Dict, Union[str, Dict], bool]:
        """Muestra servicios de una categoría."""
        # Limpiar datos
        cleaned_services = DataFormatter.clean_data_for_storage(services)
        cleaned_category = DataFormatter.clean_data_for_storage(selected_category)
        
        # Preparar opciones de servicios
        service_options_data = []
        buttons = []
        
        for i, service in enumerate(services[:10], 1):  # Limitar a 10
            service_id = service.get('Id')
            service_name = service.get('VcName', 'Servicio')
            price = service.get('IRegularPrice', 0)
            
            button_id = f"srv_id_{service_id}"
            
            service_options_data.append({
                "button_id": button_id,
                "real_id": service_id,
                "data": DataFormatter.clean_data_for_storage(service),
                "index": i
            })
            
            price_text = f"${price:,}" if price else ""
            description = f"{price_text} - {service.get('VcTime', 'N/A')}"
            
            buttons.append({
                "id": button_id,
                "title": service_name,
                "description": description
            })
        
        text = f"Servicios disponibles en {selected_category['VcName']}:"
        response = self.whatsapp_helper.create_interactive_response(text, buttons)
        
        new_state = {
            "step": "waiting_service",
            "data": {
                **data,
                "selected_category": cleaned_category,
                "services": cleaned_services,
                "service_options_data": service_options_data
            }
        }
        
        return (new_state, response, False)

    async def process_service_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 3: Procesar selección de servicio."""
        service_options_data = data.get("service_options_data", [])
        
        # Usar SelectionHandler para extraer selección
        selected_option = SelectionHandler.extract_user_selection(message, service_options_data)
        
        if selected_option is None:
            return (
                {"step": "waiting_service", "data": data},
                "❌ Por favor selecciona un servicio válido de las opciones mostradas.",
                False
            )
        
        selected_service = selected_option['data']
        service_id = selected_option['real_id']
        
        logger.info(f"Servicio seleccionado: {selected_service.get('VcName')} (ID: {service_id})")
        
        # Obtener profesionales para este servicio
        professionals = await self.boki_api.get_professionals_by_service(service_id)
        
        if not AppointmentValidators.validate_professionals(professionals):
            return (
                {"step": "waiting_service", "data": data},
                f"❌ No hay profesionales disponibles para el servicio '{selected_service.get('VcName')}'. Por favor selecciona otro.",
                False
            )
        
        # Agregar servicio seleccionado a los datos
        data["selected_service"] = selected_service
        logger.info(f"Encontrados {len(professionals)} profesionales para servicio {service_id}")
        
        return await self.show_professionals_selection(data, professionals)

    async def show_professionals_selection(self, data: Dict, professionals: List[Dict]) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 4: Mostrar selección de profesionales."""
        # Solo mostrar selección si hay más de 1 profesional
        if len(professionals) <= 1:
            if len(professionals) == 1:
                professional = professionals[0]
                data["selected_professional"] = professional
                
                service_name = data["selected_service"].get('VcName')
                
                logger.info(f"Solo un profesional disponible, saltando a disponibilidad")
                
                # Mensaje informativo con detalles del profesional
                prof_info = DataFormatter.format_professional_detailed_info(professional)
                data["single_professional_message"] = f"✅ *Servicio:* {service_name}\n{prof_info}\n\n"
                
                return await self.show_availability(data)
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
            name = DataFormatter.format_professional_name(professional)
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
            display_name = DataFormatter.format_professional_display_name(professional, 20)
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
        
        response = self.whatsapp_helper.create_interactive_response(message, buttons)
        
        new_state = {
            "step": "waiting_professional",
            "data": {
                **data,
                "professionals": professionals,
                "prof_options_data": prof_options_data
            }
        }
        
        return (new_state, response, False)

    async def process_professional_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 5: Procesar selección de profesional."""
        prof_options_data = data.get("prof_options_data", [])
        
        # Usar SelectionHandler para extraer selección
        selected_option = SelectionHandler.extract_user_selection(message, prof_options_data)
        
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
                prof_name = DataFormatter.format_professional_name(professional)
                prof_specialization = professional.get('VcSpecialization', '')
                
                description = ""
                if prof_specialization:
                    description = f"Especialista en {prof_specialization}"
                
                buttons.append({
                    "id": opt['button_id'],
                    "title": prof_name[:20],
                    "description": description[:72]
                })
            
            response = self.whatsapp_helper.create_interactive_response(text, buttons)
            
            return (
                {"step": "waiting_professional", "data": data},
                response,
                False
            )
        
        selected_professional = selected_option['data']
        prof_name = DataFormatter.format_professional_name(selected_professional)
        
        logger.info(f"Profesional seleccionado: {prof_name} (ID: {selected_professional.get('Id')})")
        
        data["selected_professional"] = selected_professional
        return await self.show_availability(data)

    async def show_availability(self, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 6: Mostrar disponibilidad de fechas (MEJORADO)."""
        professional = data["selected_professional"]
        service = data["selected_service"]
        
        professional_id = professional.get('Id')
        service_id = service.get('Id')
        
        logger.info(f"Obteniendo disponibilidad para profesional {professional_id}, servicio {service_id}")
        
        # Obtener disponibilidad general (primera carga o con startDate si existe)
        start_date = data.get("next_start_date")  # Para paginación
        availability = await self.boki_api.get_general_availability(
            professional_id, 
            service_id,
            start_date=start_date
        )
        
        if not AppointmentValidators.validate_availability(availability):
            return (
                {"step": "waiting_service", "data": data},
                "❌ No hay fechas disponibles para este profesional. Por favor selecciona otro servicio o profesional.",
                False
            )
        
        logger.info(f"Encontradas {len(availability)} fechas disponibles")
        
        # Preparar datos de fechas - MOSTRAR 5 FECHAS
        date_options_data = []
        buttons = []
        
        # Mostrar las primeras 5 fechas (no 3)
        displayed_dates = availability[:5]
        
        for i, date_info in enumerate(displayed_dates, 1):
            button_id = f"date_{i}"
            
            option_data = {
                'button_id': button_id,
                'data': date_info,
                'index': i,
                'backend_date': date_info  # Guardar objeto completo del backend
            }
            date_options_data.append(option_data)
            
            # Usar nuevos formateadores para mejor UX
            formatted_date = DataFormatter.format_backend_date_for_display_simple(date_info)
            description = DataFormatter.format_availability_description(date_info)
            
            buttons.append({
                "id": button_id,
                "title": formatted_date,
                "description": description  # Horarios en lugar de "X horarios disponibles"
            })
        
        # Si hay más fechas disponibles, agregar botón "Ver fechas siguientes"
        if len(availability) >= 5:
            # Calcular fecha para siguiente consulta usando la última fecha mostrada
            last_date_info = displayed_dates[-1]
            next_start_date = DataFormatter.convert_date_for_api(last_date_info)
            
            buttons.append({
                "id": "dates_next",
                "title": "📅 Ver fechas siguientes",
                "description": "Más fechas disponibles"
            })
            
            # Guardar para paginación
            data["next_start_date"] = next_start_date
        
        # Construir mensaje más amigable
        prof_name = DataFormatter.format_professional_name(professional)
        service_name = service.get('VcName')
        
        # Verificar si hay mensaje de profesional único
        single_prof_message = data.get("single_professional_message", "")
        
        if single_prof_message:
            text = single_prof_message
            text += "📅 *Fechas disponibles:*"
        else:
            text = f"¡Excelente! Has seleccionado:\n"
            text += f"👨‍⚕️ *Profesional:* {prof_name}\n"
            text += f"💼 *Servicio:* {service_name}\n\n"
            text += "📅 *Fechas disponibles:*"
        
        response = self.whatsapp_helper.create_interactive_response(text, buttons)
        
        new_state = {
            "step": "waiting_date",
            "data": {
                **data,
                "availability": availability,
                "date_options_data": date_options_data,
                "current_page": data.get("current_page", 1)
            }
        }
        
        return (new_state, response, False)

    async def show_next_dates(self, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Muestra las siguientes fechas disponibles usando startDate."""
        professional = data["selected_professional"]
        service = data["selected_service"]
        
        professional_id = professional.get('Id')
        service_id = service.get('Id')
        next_start_date = data.get("next_start_date")
        
        if not next_start_date:
            return (
                {"step": "waiting_date", "data": data},
                "❌ No hay más fechas disponibles.",
                False
            )
        
        logger.info(f"Obteniendo siguientes fechas desde: {next_start_date}")
        
        # Obtener siguientes fechas usando startDate
        availability = await self.boki_api.get_general_availability(
            professional_id, 
            service_id,
            start_date=next_start_date
        )
        
        if not AppointmentValidators.validate_availability(availability):
            return (
                {"step": "waiting_date", "data": data},
                "❌ No hay más fechas disponibles.",
                False
            )
        
        # Preparar nuevas fechas
        date_options_data = []
        buttons = []
        
        # Mostrar las primeras 5 fechas de esta nueva consulta
        displayed_dates = availability[:5]
        current_page = data.get("current_page", 1) + 1
        
        for i, date_info in enumerate(displayed_dates, 1):
            # Usar índices únicos para evitar conflictos
            button_id = f"date_{current_page}_{i}"
            
            option_data = {
                'button_id': button_id,
                'data': date_info,
                'index': i,
                'backend_date': date_info
            }
            date_options_data.append(option_data)
            
            # Formatear con los nuevos métodos
            formatted_date = DataFormatter.format_backend_date_for_display_simple(date_info)
            description = DataFormatter.format_availability_description(date_info)
            
            buttons.append({
                "id": button_id,
                "title": formatted_date,
                "description": description
            })
        
        # Verificar si hay más fechas
        if len(availability) >= 5:
            last_date_info = displayed_dates[-1]
            next_start_date_new = DataFormatter.convert_date_for_api(last_date_info)
            
            buttons.append({
                "id": "dates_next",
                "title": "📅 Ver más fechas",
                "description": "Continuar viendo fechas"
            })
            
            data["next_start_date"] = next_start_date_new
        
        # Agregar botón para volver a las primeras fechas
        buttons.append({
            "id": "dates_back",
            "title": "⬅️ Fechas anteriores",
            "description": "Volver a fechas iniciales"
        })
        
        prof_name = DataFormatter.format_professional_name(professional)
        service_name = service.get('VcName')
        
        text = f"📅 *Más fechas disponibles:*\n"
        text += f"👨‍⚕️ *Profesional:* {prof_name}\n"
        text += f"💼 *Servicio:* {service_name}"
        
        response = self.whatsapp_helper.create_interactive_response(text, buttons)
        
        new_state = {
            "step": "waiting_date",
            "data": {
                **data,
                "availability": availability,
                "date_options_data": date_options_data,
                    "current_page": current_page
                }
            }
            
        return (new_state, response, False)

    async def process_date_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 7: Procesar selección de fecha (ACTUALIZADO)."""
        
        # Manejar comandos especiales
        if message == "dates_next":
            return await self.show_next_dates(data)
        elif message == "dates_back":
            # Volver a mostrar fechas iniciales
            data.pop("next_start_date", None)  # Limpiar paginación
            data["current_page"] = 1
            return await self.show_availability(data)
        
        date_options_data = data.get("date_options_data", [])
        
        # Usar SelectionHandler para extraer selección
        selected_option = SelectionHandler.extract_user_selection(message, date_options_data)
        
        if selected_option is None:
            return (
                {"step": "waiting_date", "data": data},
                "❌ Por favor selecciona una fecha válida de las opciones mostradas.",
                False
            )
        
        # Usar datos del backend directamente
        selected_date_info = selected_option['backend_date']
        logger.info(f"Fecha seleccionada: {selected_date_info.get('fecha', 'N/A')}")
        
        return await self.show_time_slots(data, selected_date_info)

    async def show_more_dates(self, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Muestra más fechas disponibles."""
        availability = data.get("availability", [])
        
        # Determinar qué fechas mostrar
        if data.get("viewing_extended"):
            additional_dates = availability[8:13]
            start_index = 9
        else:
            additional_dates = availability[3:8]
            start_index = 4
        
        if not additional_dates:
            return (
                {"step": "waiting_date", "data": data},
                "❌ No hay más fechas disponibles.",
                False
            )
        
        text = "📅 *Fechas adicionales disponibles:*"
        
        # Preparar datos de fechas adicionales
        date_options_data = []
        buttons = []
        
        for i, date_info in enumerate(additional_dates, start_index):
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
            
            formatted_date = DataFormatter.format_date_display(date_str)
            
            buttons.append({
                "id": button_id,
                "title": formatted_date,
                "description": f"{available_slots} horarios disponibles"
            })
        
        # Agregar botones de navegación
        if len(availability) > start_index + len(additional_dates):
            buttons.append({
                "id": "date_more",
                "title": "📅 Ver más fechas",
                "description": f"Más fechas disponibles"
            })
        
        buttons.append({
            "id": "date_back",
            "title": "⬅️ Volver",
            "description": "Ver primeras fechas"
        })
        
        response = self.whatsapp_helper.create_interactive_response(text, buttons)
        
        # Actualizar estado
        data["date_options_data"] = date_options_data
        data["viewing_extended"] = True
        
        return (
            {"step": "waiting_date", "data": data},
            response,
            False
        )

    async def show_initial_dates(self, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Muestra las primeras 3 fechas disponibles."""
        availability = data.get("availability", [])
        
        if not availability:
            return (
                {"step": "waiting_professional", "data": data},
                "❌ No hay fechas disponibles. Por favor selecciona otro profesional.",
                False
            )
        
        # Preparar datos de las primeras 3 fechas
        date_options_data = []
        buttons = []
        displayed_dates = availability[:3]
        
        for i, date_info in enumerate(displayed_dates, 1):
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
            
            formatted_date = DataFormatter.format_date_display(date_str)
            
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
        professional = data["selected_professional"]
        service = data["selected_service"]
        prof_name = DataFormatter.format_professional_name(professional)
        service_name = service.get('VcName')
        
        single_prof_message = data.get("single_professional_message", "")
        
        if single_prof_message:
            text = single_prof_message + "📅 Selecciona una fecha disponible:"
        else:
            text = f"¡Excelente! Has seleccionado:\n"
            text += f"👨‍⚕️ *Profesional:* {prof_name}\n"
            text += f"💼 *Servicio:* {service_name}\n\n"
            text += "📅 Selecciona una fecha disponible:"
        
        response = self.whatsapp_helper.create_interactive_response(text, buttons)
        
        # Actualizar estado
        data["date_options_data"] = date_options_data
        data.pop("viewing_extended", None)
        
        new_state = {
            "step": "waiting_date",
            "data": data
        }
        
        return (new_state, response, False)

    async def show_time_slots(self, data: Dict, selected_date_info: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 8: Mostrar horarios disponibles."""
        professional = data["selected_professional"]
        service = data["selected_service"]
        
        professional_id = professional.get('Id')
        service_id = service.get('Id')
        selected_date = selected_date_info.get('date', selected_date_info.get('fecha'))
        
        logger.info(f"Obteniendo slots para fecha {selected_date}")
        
        # Obtener slots disponibles
        slots = await self.boki_api.get_available_slots(professional_id, service_id, selected_date)
        
        if not AppointmentValidators.validate_slots(slots):
            return (
                {"step": "waiting_date", "data": data},
                "❌ No hay horarios disponibles para esta fecha. Por favor selecciona otra fecha.",
                False
            )
        
        logger.info(f"Encontrados {len(slots)} slots disponibles")
        
        # Guardar fecha seleccionada
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
            
            # Formatear tiempo para mostrar
            time_display = start_time
            if end_time and end_time != start_time:
                time_display += f" - {end_time}"
            
            buttons.append({
                "id": button_id,
                "title": time_display,
                "description": "Horario disponible"
            })
        
        # Formatear fecha para mostrar
        formatted_date = DataFormatter.format_full_date_display(selected_date)
        
        text = f"📅 *Fecha seleccionada:* {formatted_date}\n\n🕐 Selecciona tu horario preferido:"
        
        response = self.whatsapp_helper.create_interactive_response(text, buttons)
        
        new_state = {
            "step": "waiting_time",
            "data": {
                **data,
                "available_slots": slots,
                "time_options_data": time_options_data
            }
        }
        
        return (new_state, response, False)

    async def process_time_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 9: Procesar selección de horario."""
        time_options_data = data.get("time_options_data", [])
        
        # Usar SelectionHandler para extraer selección
        selected_option = SelectionHandler.extract_user_selection(message, time_options_data)
        
        if selected_option is None:
            return (
                {"step": "waiting_time", "data": data},
                "❌ Por favor selecciona un horario válido de las opciones mostradas.",
                False
            )
        
        selected_slot = selected_option['data']
        data["selected_slot"] = selected_slot
        
        # Mostrar resumen de confirmación
        professional = data["selected_professional"]
        service = data["selected_service"]
        selected_date = data["selected_date"]
        
        prof_name = DataFormatter.format_professional_name(professional)
        service_name = service.get('VcName')
        service_duration = service.get('NnDuration', '')
        service_price = service.get('DcPrice', '')
        start_time = selected_slot.get('start_time', selected_slot.get('hora_inicio'))
        end_time = selected_slot.get('end_time', selected_slot.get('hora_fin'))
        
        # Formatear fecha
        formatted_date = DataFormatter.format_full_date_display(selected_date)
        
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
        
        response = self.whatsapp_helper.create_interactive_response(text, buttons)
        
        new_state = {
            "step": "waiting_confirmation",
            "data": data
        }
        
        return (new_state, response, False)

    async def process_confirmation(self, message: str, data: Dict, contact_id: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 10: Procesar confirmación final."""
        logger.info(f"Procesando confirmación: '{message}' para contacto {contact_id}")
        
        if message == "confirm_yes" or message.lower() in ["si", "sí", "yes", "1"]:
            # Confirmar y crear la cita
            return await self.create_appointment(data, contact_id)
        elif message == "confirm_no" or message.lower() in ["no", "2", "cancelar"]:
            # Cancelar y terminar flujo
            return (
                {},
                "❌ Cita cancelada. Si deseas agendar una nueva cita, escribe 'agendar' cuando gustes. 😊",
                True
            )
        else:
            # Opción no válida, mostrar botones de nuevo
            professional = data["selected_professional"]
            service = data["selected_service"]
            selected_date = data["selected_date"]
            selected_slot = data["selected_slot"]
            
            prof_name = DataFormatter.format_professional_name(professional)
            service_name = service.get('VcName')
            start_time = selected_slot.get('start_time', selected_slot.get('hora_inicio'))
            
            formatted_date = DataFormatter.format_full_date_display(selected_date)
            
            text = "❌ No entendí tu respuesta.\n\n"
            text += "✅ *CONFIRMACIÓN DE CITA*\n\n"
            text += f"👨‍⚕️ *Profesional:* {prof_name}\n"
            text += f"💼 *Servicio:* {service_name}\n"
            text += f"📅 *Fecha:* {formatted_date}\n"
            text += f"🕐 *Horario:* {start_time}\n\n"
            text += "¿Confirmas esta cita?"
            
            # Recrear botones de confirmación
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
            
            response = self.whatsapp_helper.create_interactive_response(text, buttons)
            
            return (
                {"step": "waiting_confirmation", "data": data},
                response,
                False
            )

    async def create_appointment(self, data: Dict, contact_id: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """Crear la cita en el sistema."""
        try:
            logger.info(f"Iniciando creación de cita para contacto {contact_id}")
            
            # Validar datos antes de crear
            is_valid, missing_fields = AppointmentValidators.validate_appointment_data(data)
            if not is_valid:
                logger.error(f"Campos faltantes para crear cita: {missing_fields}")
                return (
                    {"step": "waiting_confirmation", "data": data},
                    "❌ Faltan datos para crear la cita. Por favor intenta nuevamente.",
                    False
                )
            
            # Extraer datos necesarios
            professional = data["selected_professional"]
            service = data["selected_service"]
            selected_date = data["selected_date"]
            selected_slot = data["selected_slot"]
            
            # Preparar datos para crear la cita
            appointment_data = {
                "contactId": contact_id,
                "professionalId": professional.get('Id'),
                "serviceId": service.get('Id'),
                "date": selected_date,
                "startTime": selected_slot.get('start_time', selected_slot.get('hora_inicio')),
                "endTime": selected_slot.get('end_time', selected_slot.get('hora_fin', '')),
                "status": "scheduled"
            }
            
            logger.info(f"Datos de la cita: {appointment_data}")
            
            # Crear la cita
            result = await self.boki_api.create_appointment(appointment_data)
            
            if result and result.get('Id'):
                appointment_id = result.get('Id')
                prof_name = DataFormatter.format_professional_name(professional)
                service_name = service.get('VcName')
                
                formatted_date = DataFormatter.format_full_date_display(selected_date)
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
                
                logger.info(f"Cita creada exitosamente: {appointment_id}")
                return ({}, response, True)
            else:
                logger.error(f"Error al crear cita - resultado: {result}")
                return (
                    {"step": "waiting_confirmation", "data": data},
                    "❌ Hubo un error al confirmar tu cita. Por favor intenta nuevamente.",
                    False
                )
                    
        except Exception as e:
            logger.error(f"Error inesperado creando cita: {e}", exc_info=True)
            return (
                {"step": "waiting_confirmation", "data": data},
                "❌ Hubo un error técnico al procesar tu cita. Por favor intenta nuevamente.",
                False
            )