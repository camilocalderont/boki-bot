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

    # CONSTANTE PARA LÍMITE DE BOTONES DE WHATSAPP
    MAX_WHATSAPP_BUTTONS = 10

    def __init__(self, boki_api):
        self.boki_api = boki_api
        self.whatsapp_helper = WhatsAppHelper()

    def _extract_iso_date_from_backend_data(self, date_info: Dict) -> Optional[str]:
        """
        Extrae la fecha en formato ISO (YYYY-MM-DD) del objeto del backend.
        Maneja correctamente timezones para evitar problemas de conversión UTC.
        
        Args:
            date_info: Datos de fecha del backend con estructura:
            {
                "fecha": "Jueves 29 de mayo",
                "fechaCompleta": "29/05/2025 00:00"
            }
            
        Returns:
            str: Fecha en formato ISO (2025-05-29) o None si no se puede extraer
        """
        # Obtener fechaCompleta del backend (formato: "29/05/2025 00:00")
        fecha_completa = date_info.get('fechaCompleta')
        
        if fecha_completa:
            try:
                # Extraer solo la parte de fecha (sin hora) para evitar problemas de timezone
                fecha_parte = fecha_completa.split(' ')[0]  # "29/05/2025"
                
                logger.info(f"[DEBUG] Extrayendo fecha de fechaCompleta: {fecha_completa} -> fecha_parte: {fecha_parte}")
                
                # Convertir de DD/MM/YYYY a YYYY-MM-DD
                # IMPORTANTE: Usar la fecha tal como viene del backend sin conversiones de timezone
                dia, mes, año = fecha_parte.split('/')
                iso_date = f"{año}-{mes.zfill(2)}-{dia.zfill(2)}"
                
                logger.info(f"[DEBUG] Fecha convertida: {fecha_completa} -> {iso_date}")
                
                # Validar que la fecha extraída sea correcta
                expected_day = int(dia)
                extracted_day = int(iso_date.split('-')[2])
                
                if expected_day != extracted_day:
                    logger.error(f"[ERROR] Discrepancia en día: esperado {expected_day}, obtenido {extracted_day}")
                
                return iso_date
                
            except Exception as e:
                logger.error(f"Error convirtiendo fechaCompleta '{fecha_completa}': {e}")
        
        # Fallback: intentar extraer de otros campos
        for key in ['date', 'fecha_iso', 'iso_date']:
            value = date_info.get(key)
            if value and self._is_valid_iso_date(value):
                logger.info(f"[DEBUG] Usando fecha de campo {key}: {value}")
                return value
        
        # Último intento: usar el campo 'fecha' para extraer la fecha
        fecha_texto = date_info.get('fecha', '')
        if fecha_texto:
            try:
                logger.info(f"[DEBUG] Intentando extraer fecha del texto: {fecha_texto}")
                # Ejemplo: "Jueves 29 de mayo" -> necesitamos año del fechaCompleta
                if fecha_completa:
                    año_completa = fecha_completa.split('/')[-1].split(' ')[0]  # "2025"
                    # Mapeo básico de meses
                    meses = {
                        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                    }
                    
                    # Extraer día y mes del texto
                    import re
                    match = re.search(r'(\d+) de (\w+)', fecha_texto.lower())
                    if match:
                        dia_texto = match.group(1).zfill(2)
                        mes_texto = meses.get(match.group(2))
                        if mes_texto:
                            iso_date = f"{año_completa}-{mes_texto}-{dia_texto}"
                            logger.info(f"[DEBUG] Fecha extraída del texto: {iso_date}")
                            return iso_date
            except Exception as e:
                logger.warning(f"Error extrayendo fecha del texto '{fecha_texto}': {e}")
        
        logger.error(f"No se pudo extraer fecha ISO de: {date_info}")
        return None

    def _is_valid_iso_date(self, date_str: str) -> bool:
        """Valida que una cadena sea una fecha ISO válida (YYYY-MM-DD)."""
        if not date_str or not isinstance(date_str, str):
            return False
        
        # Patrón básico para fecha ISO
        import re
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        return bool(re.match(pattern, date_str))

    def _ensure_button_limit(self, buttons: List[Dict], max_buttons: int = None) -> List[Dict]:
        """
        Asegura que la lista de botones no exceda el límite de WhatsApp.
        
        Args:
            buttons: Lista de botones
            max_buttons: Límite máximo (por defecto usa MAX_WHATSAPP_BUTTONS)
        
        Returns:
            Lista de botones limitada
        """
        if max_buttons is None:
            max_buttons = self.MAX_WHATSAPP_BUTTONS
        
        if len(buttons) <= max_buttons:
            return buttons
        
        logger.warning(f"Limitando {len(buttons)} botones a {max_buttons} para cumplir con WhatsApp")
        return buttons[:max_buttons]

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
            
            # Preparar opciones - LIMITAR A 10 CATEGORÍAS
            options_data = []
            buttons = []
            
            # Limitar categorías para no exceder botones de WhatsApp
            limited_categories = service_categories[:self.MAX_WHATSAPP_BUTTONS]
            
            for i, category in enumerate(limited_categories, 1):
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
            
            # Mensaje si hay más categorías disponibles
            if len(service_categories) > self.MAX_WHATSAPP_BUTTONS:
                showing_count = len(limited_categories)
                total_count = len(service_categories)
                text = f"¡Perfecto! Vamos a agendar tu cita. 📅\n\nMostrando {showing_count} de {total_count} categorías disponibles.\nSelecciona la categoría de servicio que te interesa:"
            else:
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
            # Limitar categorías en el mensaje de error también
            limited_categories = categories[:self.MAX_WHATSAPP_BUTTONS]
            for category in limited_categories:
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
        
        # Preparar opciones de servicios - LIMITAR A 10
        service_options_data = []
        buttons = []
        
        # Limitar servicios para cumplir con WhatsApp
        limited_services = services[:self.MAX_WHATSAPP_BUTTONS]
        
        logger.info(f"[DEBUG] Mostrando {len(limited_services)} de {len(services)} servicios disponibles")
        
        for i, service in enumerate(limited_services, 1):
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
        
        # Mensaje con información de limitación si aplica
        if len(services) > self.MAX_WHATSAPP_BUTTONS:
            showing_count = len(limited_services)
            total_count = len(services)
            text = f"Servicios disponibles en {selected_category['VcName']}:\n\nMostrando {showing_count} de {total_count} servicios disponibles:"
        else:
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
        
        # Limitar profesionales mostrados en el mensaje informativo
        displayed_professionals = professionals[:self.MAX_WHATSAPP_BUTTONS]
        
        for i, professional in enumerate(displayed_professionals, 1):
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
            if i < len(displayed_professionals):
                message += "\n"
        
        # Mensaje si hay más profesionales disponibles
        if len(professionals) > self.MAX_WHATSAPP_BUTTONS:
            showing_count = len(displayed_professionals)
            total_count = len(professionals)
            message += f"\n\n(Mostrando {showing_count} de {total_count} profesionales disponibles)"
        
        message += "\n\n💡 Selecciona tu profesional de preferencia:"
        
        # Crear datos para la lista de selección - LIMITADO
        prof_options_data = []
        buttons = []
        
        for i, professional in enumerate(displayed_professionals, 1):
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
                "professionals": displayed_professionals,  # Guardar solo los mostrados
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
        
        # Preparar datos de fechas - MOSTRAR 5 FECHAS MÁXIMO + NAVEGACIÓN
        date_options_data = []
        buttons = []
        
        # Reservar espacio para botón de navegación si es necesario
        max_dates_to_show = min(5, self.MAX_WHATSAPP_BUTTONS - 1)  # Reservar 1 para navegación
        displayed_dates = availability[:max_dates_to_show]
        
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
        if len(availability) > max_dates_to_show:
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
        
        # Asegurar que no excedemos el límite
        buttons = self._ensure_button_limit(buttons)
        
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
        
        # Reservar espacio para botones de navegación (2: siguiente y anterior)
        max_dates_to_show = min(5, self.MAX_WHATSAPP_BUTTONS - 2)
        displayed_dates = availability[:max_dates_to_show]
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
        if len(availability) > max_dates_to_show:
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
        
        # Asegurar límite de botones
        buttons = self._ensure_button_limit(buttons)
        
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
        
        # NUEVO FLUJO: Ahora ir a mostrar períodos disponibles
        return await self.show_time_periods(data, selected_date_info)

    # NUEVAS FUNCIONES PARA MANEJO DE PERÍODOS Y HORARIOS

    async def show_time_periods(self, data: Dict, selected_date_info: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 8a: Mostrar períodos del día disponibles."""
        professional = data["selected_professional"]
        service = data["selected_service"]
        
        professional_id = professional.get('Id')
        service_id = service.get('Id')
        
        # CORREGIR: Extraer fecha en formato ISO para el API
        selected_date_iso = self._extract_iso_date_from_backend_data(selected_date_info)
        
        logger.info(f"[DEBUG] show_time_periods - selected_date_info recibido: {selected_date_info}")
        logger.info(f"[DEBUG] show_time_periods - selected_date_iso extraído: {selected_date_iso}")
        
        if not selected_date_iso:
            logger.error(f"No se pudo extraer fecha ISO de: {selected_date_info}")
            return (
                {"step": "waiting_date", "data": data},
                "❌ Error con la fecha seleccionada. Por favor selecciona otra fecha.",
                False
            )
        
        logger.info(f"Obteniendo slots para fecha ISO: {selected_date_iso}")
        
        # Obtener slots disponibles con nueva estructura usando fecha ISO
        slots_data = await self.boki_api.get_available_slots(professional_id, service_id, selected_date_iso)
        
        logger.info(f"[DEBUG] show_time_periods - slots_data recibido: {slots_data}")
        
        if not AppointmentValidators.validate_slots_data(slots_data):
            return (
                {"step": "waiting_date", "data": data},
                "❌ No hay horarios disponibles para esta fecha. Por favor selecciona otra fecha.",
                False
            )
        
        # Guardar fecha seleccionada EN FORMATO ISO para API y datos completos para mostrar
        logger.info(f"[DEBUG] show_time_periods - Asignando selected_date = {selected_date_iso}")
        data["selected_date"] = selected_date_iso  # Para API calls
        data["selected_date_info"] = selected_date_info  # Para mostrar al usuario
        data["available_slots_data"] = slots_data
        
        logger.info(f"[DEBUG] show_time_periods - data['selected_date'] después de asignar: {data.get('selected_date')}")
        
        # Filtrar períodos que tienen horarios disponibles
        period_translations = {
            "mañana": {"emoji": "🌅", "name": "Mañana", "id": "morning"},
            "tarde": {"emoji": "☀️", "name": "Tarde", "id": "afternoon"}, 
            "noche": {"emoji": "🌙", "name": "Noche", "id": "night"}
        }
        
        buttons = []
        for period_key, period_info in period_translations.items():
            slots_in_period = slots_data.get(period_key, [])
            if slots_in_period:  # Solo agregar si hay slots disponibles
                slot_count = len(slots_in_period)
                buttons.append({
                    "id": f"period_{period_info['id']}",
                    "title": f"{period_info['emoji']} {period_info['name']}",
                    "description": f"{slot_count} horarios disponibles"
                })
        
        if not buttons:
            return (
                {"step": "waiting_date", "data": data},
                "❌ No hay horarios disponibles para esta fecha. Por favor selecciona otra fecha.",
                False
            )
        
        # Asegurar límite de botones (aunque períodos son máximo 3)
        buttons = self._ensure_button_limit(buttons)
        
        # Formatear fecha para mostrar al usuario (usando selected_date_info)
        formatted_date = DataFormatter.format_backend_date_for_display_simple(selected_date_info)
        
        text = f"📅 *Fecha seleccionada:* {formatted_date}\n\n🕐 ¿En qué horario prefieres tu cita?"
        
        response = self.whatsapp_helper.create_interactive_response(text, buttons)
        
        new_state = {
            "step": "waiting_period",
            "data": data
        }
        
        return (new_state, response, False)

    async def process_period_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 8b: Procesar selección de período."""
        
        # Extraer período seleccionado del mensaje
        if message.startswith("period_"):
            selected_period = message.replace("period_", "")
            return await self.show_time_slots(data, selected_period)
        else:
            return (
                {"step": "waiting_period", "data": data},
                "❌ Por favor selecciona un período válido de las opciones mostradas.",
                False
            )

    async def show_time_slots(self, data: Dict, selected_period: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 8c: Mostrar horarios específicos del período seleccionado."""
        
        # Mapeo de IDs de período a claves del API
        period_mapping = {
            "morning": "mañana",
            "afternoon": "tarde", 
            "night": "noche"
        }
        
        period_names = {
            "morning": "🌅 Mañana",
            "afternoon": "☀️ Tarde",
            "night": "🌙 Noche"
        }
        
        period_key = period_mapping.get(selected_period)
        if not period_key:
            return (
                {"step": "waiting_period", "data": data},
                "❌ Período seleccionado no válido. Por favor selecciona un horario válido.",
                False
            )
        
        slots_data = data.get("available_slots_data", {})
        period_slots = slots_data.get(period_key, [])
        
        if not period_slots:
            return (
                {"step": "waiting_period", "data": data},
                f"❌ No hay horarios disponibles para {period_names.get(selected_period, 'este período')}. Por favor selecciona otro horario.",
                False
            )
        
        logger.info(f"[DEBUG] show_time_slots - Total de horarios en {period_key}: {len(period_slots)}")
        
        # Preparar datos de horarios
        time_options_data = []
        buttons = []
        
        # CORREGIR: Reservar espacio para botones de navegación
        navigation_buttons_count = 1  # Botón "Cambiar período"
        if len(period_slots) > (self.MAX_WHATSAPP_BUTTONS - navigation_buttons_count):
            navigation_buttons_count = 2  # + botón "Ver más horarios"
        
        max_time_slots = self.MAX_WHATSAPP_BUTTONS - navigation_buttons_count
        displayed_slots = period_slots[:max_time_slots]
        
        logger.info(f"[DEBUG] show_time_slots - Mostrando primeros {len(displayed_slots)} horarios: {displayed_slots}")
        
        for i, time_slot in enumerate(displayed_slots, 1):
            button_id = f"time_{selected_period}_{i}"
            
            option_data = {
                'button_id': button_id,
                'time': time_slot,
                'period': period_key,
                'index': i
            }
            time_options_data.append(option_data)
            
            buttons.append({
                "id": button_id,
                "title": time_slot,
                "description": f"Horario en la {period_key}"
            })
        
        # Si hay más horarios, agregar botón "Ver más horarios"
        if len(period_slots) > max_time_slots:
            buttons.append({
                "id": f"more_times_{selected_period}",
                "title": "🔄 Ver más horarios",
                "description": f"Quedan {len(period_slots) - max_time_slots} horarios más"
            })
        
        # Agregar botón para volver a seleccionar período
        buttons.append({
            "id": "back_to_periods",
            "title": "⬅️ Cambiar período",
            "description": "Volver a seleccionar período"
        })
        
        # FINAL: Asegurar límite de botones
        buttons = self._ensure_button_limit(buttons)
        
        # Formatear fecha y período para mostrar
        formatted_date = DataFormatter.format_backend_date_for_display_simple(data["selected_date_info"])
        period_name = period_names.get(selected_period, period_key)
        
        text = f"📅 *Fecha:* {formatted_date}\n🕐 *Período:* {period_name}\n\n⏰ Selecciona tu horario:"
        
        response = self.whatsapp_helper.create_interactive_response(text, buttons)
        
        new_state = {
            "step": "waiting_time",
            "data": {
                **data,
                "selected_period": selected_period,
                "time_options_data": time_options_data,
                "current_period_slots": period_slots,
                "current_time_page": 0  # Inicializar paginación en 0 (primera página)
            }
        }
        
        return (new_state, response, False)

    async def show_more_time_slots(self, data: Dict, selected_period: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """Mostrar más horarios del período seleccionado."""
        
        # Mapeo de IDs de período a claves del API y nombres
        period_mapping = {
            "morning": "mañana",
            "afternoon": "tarde", 
            "night": "noche"
        }
        
        period_names = {
            "morning": "🌅 Mañana",
            "afternoon": "☀️ Tarde",
            "night": "🌙 Noche"
        }
        
        period_key = period_mapping.get(selected_period)
        if not period_key:
            return (
                {"step": "waiting_period", "data": data},
                "❌ Período seleccionado no válido. Por favor selecciona un horario válido.",
                False
            )
        
        slots_data = data.get("available_slots_data", {})
        all_period_slots = slots_data.get(period_key, [])
        
        if not all_period_slots:
            return (
                {"step": "waiting_period", "data": data},
                f"❌ No hay horarios disponibles para {period_names.get(selected_period, 'este período')}.",
                False
            )
        
        # CORREGIR: Obtener página actual correctamente (iniciando desde 0)
        current_time_page = data.get("current_time_page", 0)
        next_page = current_time_page + 1
        
        # Calcular cuántos horarios se pueden mostrar por página
        navigation_buttons_count = 2  # "Cambiar período" + "Página anterior" 
        slots_per_page = self.MAX_WHATSAPP_BUTTONS - navigation_buttons_count
        
        # CORREGIR: Calcular el rango usando la PRÓXIMA página
        start_idx = next_page * slots_per_page
        end_idx = start_idx + slots_per_page
        
        logger.info(f"[DEBUG] Ver más horarios - Página actual: {current_time_page}, Próxima: {next_page}")
        logger.info(f"[DEBUG] Rango: {start_idx}-{end_idx} de {len(all_period_slots)} horarios")
        
        if start_idx >= len(all_period_slots):
            # Ya no hay más horarios para mostrar
            return (
                {"step": "waiting_time", "data": data},
                f"❌ No hay más horarios disponibles para {period_names.get(selected_period, 'este período')}.",
                False
            )
        
        displayed_slots = all_period_slots[start_idx:end_idx]
        logger.info(f"[DEBUG] Mostrando horarios: {displayed_slots}")
        
        # Preparar datos de horarios
        time_options_data = []
        buttons = []
        
        for i, time_slot in enumerate(displayed_slots, 1):
            # Usar índices únicos que incluyan la página
            button_id = f"time_{selected_period}_p{next_page}_{i}"
            
            option_data = {
                'button_id': button_id,
                'time': time_slot,
                'period': period_key,
                'index': i
            }
            time_options_data.append(option_data)
            
            buttons.append({
                "id": button_id,
                "title": time_slot,
                "description": f"Horario en la {period_key}"
            })
        
        # Agregar botón "Ver más horarios" si hay más páginas
        if end_idx < len(all_period_slots):
            remaining_slots = len(all_period_slots) - end_idx
            buttons.append({
                "id": f"more_times_{selected_period}",
                "title": "🔄 Ver más horarios", 
                "description": f"Quedan {remaining_slots} horarios más"
            })
        
        # Agregar botón para volver a horarios anteriores (siempre que no sea la primera página adicional)
        if next_page > 1:
            buttons.append({
                "id": f"prev_times_{selected_period}",
                "title": "⬅️ Horarios anteriores",
                "description": "Ver horarios previos"
            })
        
        # Agregar botón para cambiar período
        buttons.append({
            "id": "back_to_periods",
            "title": "🔄 Cambiar período",
            "description": "Volver a seleccionar período"
        })
        
        # Asegurar límite de botones
        buttons = self._ensure_button_limit(buttons)
        
        # Formatear mensaje
        formatted_date = DataFormatter.format_backend_date_for_display_simple(data["selected_date_info"])
        period_name = period_names.get(selected_period, period_key)
        
        current_showing = f"{start_idx + 1}-{start_idx + len(displayed_slots)}"
        total_slots = len(all_period_slots)
        
        text = f"📅 *Fecha:* {formatted_date}\n"
        text += f"🕐 *Período:* {period_name}\n"
        text += f"⏰ *Horarios {current_showing} de {total_slots}:*"
        
        response = self.whatsapp_helper.create_interactive_response(text, buttons)
        
        # CORREGIR: Actualizar estado con la nueva página
        new_state = {
            "step": "waiting_time",
            "data": {
                **data,
                "selected_period": selected_period,
                "time_options_data": time_options_data,
                "current_period_slots": all_period_slots,
                "current_time_page": next_page  # Usar next_page directamente
            }
        }
        
        return (new_state, response, False)

    async def show_previous_time_slots(self, data: Dict, selected_period: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """Mostrar horarios anteriores del período seleccionado."""
        
        current_time_page = data.get("current_time_page", 0)
        
        logger.info(f"[DEBUG] Horarios anteriores - Página actual: {current_time_page}")
        
        if current_time_page <= 1:
            # Si estamos en página 1 o menos, volver a la vista inicial (página 0)
            data["current_time_page"] = 0
            return await self.show_time_slots(data, selected_period)
        
        # Ir a la página anterior
        previous_page = current_time_page - 1
        data["current_time_page"] = previous_page - 1  # -1 porque show_more_time_slots suma 1
        
        logger.info(f"[DEBUG] Navegando a página anterior: {previous_page}")
        return await self.show_more_time_slots(data, selected_period)

    async def process_time_selection(self, message: str, data: Dict) -> Tuple[Dict, Union[str, Dict], bool]:
        """Paso 9: Procesar selección de horario."""
        
        # Manejar comandos especiales
        if message == "back_to_periods":
            # Volver a mostrar períodos
            selected_date_info = data.get("selected_date_info", {})
            return await self.show_time_periods(data, selected_date_info)
        elif message.startswith("more_times_"):
            # Extraer el período del mensaje y mostrar más horarios
            selected_period = message.replace("more_times_", "")
            return await self.show_more_time_slots(data, selected_period)
        elif message.startswith("prev_times_"):
            # Volver a horarios anteriores del período
            selected_period = message.replace("prev_times_", "")
            return await self.show_previous_time_slots(data, selected_period)
        
        time_options_data = data.get("time_options_data", [])
        
        # Usar SelectionHandler para extraer selección
        selected_option = SelectionHandler.extract_user_selection(message, time_options_data)
        
        if selected_option is None:
            return (
                {"step": "waiting_time", "data": data},
                "❌ Por favor selecciona un horario válido de las opciones mostradas.",
                False
            )
        
        # Crear objeto de slot compatible con el resto del código
        selected_slot = {
            'start_time': selected_option['time'],
            'hora_inicio': selected_option['time'],  # Compatibilidad con código existente
            'end_time': '',  # Se puede calcular si es necesario
            'hora_fin': ''
        }
        
        data["selected_slot"] = selected_slot
        
        # Mostrar resumen de confirmación
        professional = data["selected_professional"]
        service = data["selected_service"]
        selected_date = data["selected_date"]
        selected_date_info = data.get("selected_date_info", {})
        
        prof_name = DataFormatter.format_professional_name(professional)
        service_name = service.get('VcName')
        service_duration = service.get('NnDuration', '')
        service_price = service.get('DcPrice', '')
        start_time = selected_slot.get('start_time', selected_slot.get('hora_inicio'))
        end_time = selected_slot.get('end_time')
        
        # Formatear fecha (usar campo 'fecha' del backend que ya está formateado)
        try:
            selected_date = data["selected_date"]  # "2025-05-28"
            start_time = selected_slot.get('start_time')
            
            logger.info(f"[DEBUG] Formateando resumen final - fecha: {selected_date}, hora: {start_time}")
            
            # Usar el nuevo método de DataFormatter
            formatted_data = DataFormatter.format_stored_date_for_confirmation(selected_date, start_time)
            formatted_date = formatted_data["fecha_completa"]
            formatted_time = formatted_data["hora_12"]
            
            logger.info(f"[DEBUG] Resumen formateado - fecha: {formatted_date}, hora: {formatted_time}")
            
        except Exception as e:
            logger.error(f"Error formateando fecha/hora para resumen: {e}")
            # Fallback al método original
            formatted_date = data.get("selected_date_info", {}).get('fecha', 'Fecha seleccionada')
            formatted_time = start_time
        
        text = "✅ *CONFIRMACIÓN DE CITA*\n\n"
        text += f"👨‍⚕️ *Profesional:* {prof_name}\n"
        text += f"💼 *Servicio:* {service_name}"
        if service_duration:
            text += f" ({service_duration} min)"
        text += "\n"
        text += f"📅 *Fecha:* {formatted_date}\n"
        text += f"🕐 *Horario:* {formatted_time}\n\n"
        text += "¿Confirmas esta cita?"
        
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
        """Paso 10: Procesar confirmación final con debug completo."""
        logger.info(f"Procesando confirmación: '{message}' para contacto {contact_id}")
        
        # ===== DEBUG COMPLETO =====
        logger.info(f"[DEBUG FULL] data keys: {list(data.keys())}")
        logger.info(f"[DEBUG FULL] selected_date: {data.get('selected_date')}")
        logger.info(f"[DEBUG FULL] selected_date_info: {data.get('selected_date_info')}")
        logger.info(f"[DEBUG FULL] selected_slot: {data.get('selected_slot')}")
        # ===========================
        
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
            # OBTENER DATOS
            professional = data["selected_professional"]
            service = data["selected_service"]
            selected_date = data["selected_date"]
            selected_slot = data["selected_slot"]
            selected_date_info = data.get("selected_date_info", {})
            
            prof_name = DataFormatter.format_professional_name(professional)
            service_name = service.get('VcName')
            start_time = selected_slot.get('start_time', selected_slot.get('hora_inicio'))
            
            # ===== FORMATEO MANUAL DIRECTO =====
            try:
                logger.info(f"[DEBUG] ANTES del formateo manual:")
                logger.info(f"[DEBUG] selected_date = {selected_date}")
                logger.info(f"[DEBUG] start_time = {start_time}")
                
                # EXTRAER DÍA, MES, AÑO de selected_date directamente
                if isinstance(selected_date, str) and "/" in selected_date:
                    # Formato "28/05/2025 19:00" o "28/05/2025"
                    fecha_parte = selected_date.split(' ')[0] if ' ' in selected_date else selected_date
                    dia, mes, año = fecha_parte.split('/')
                    
                    # CREAR FECHA MANUALMENTE
                    from datetime import datetime
                    import pytz
                    
                    dt = datetime(int(año), int(mes), int(dia))
                    local_tz = pytz.timezone('America/Bogota')
                    dt = local_tz.localize(dt)
                    
                    # MAPEO MANUAL DE DÍAS Y MESES
                    days_es = {
                        'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                        'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
                    }
                    
                    months_es = {
                        'January': 'enero', 'February': 'febrero', 'March': 'marzo',
                        'April': 'abril', 'May': 'mayo', 'June': 'junio',
                        'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
                        'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
                    }
                    
                    day_name_en = dt.strftime("%A")
                    month_name_en = dt.strftime("%B")
                    
                    day_name = days_es.get(day_name_en, day_name_en)
                    month_name = months_es.get(month_name_en, month_name_en)
                    
                    formatted_date = f"{day_name} {int(dia)} de {month_name}"
                    
                else:
                    # Si no es el formato esperado, usar fallback
                    formatted_date = "Fecha seleccionada"
                
                # FORMATEAR HORA MANUALMENTE
                if start_time and ('AM' in start_time or 'PM' in start_time):
                    # Ya está en formato 12h
                    formatted_time = start_time
                elif start_time and ':' in start_time:
                    # Convertir de 24h a 12h
                    try:
                        from datetime import datetime
                        time_obj = datetime.strptime(start_time, "%H:%M")
                        formatted_time = time_obj.strftime("%I:%M %p")
                    except:
                        formatted_time = start_time
                else:
                    formatted_time = start_time or "Hora seleccionada"
                
                logger.info(f"[DEBUG] DESPUÉS del formateo manual:")
                logger.info(f"[DEBUG] formatted_date = {formatted_date}")
                logger.info(f"[DEBUG] formatted_time = {formatted_time}")
                
            except Exception as e:
                logger.error(f"[ERROR] Error en formateo manual: {e}")
                formatted_date = "Fecha seleccionada"
                formatted_time = start_time or "Hora seleccionada"
            
            # CREAR MENSAJE
            text = "❌ No entendí tu respuesta.\n\n"
            text += "✅ *CONFIRMACIÓN DE CITA*\n\n"
            text += f"👨‍⚕️ *Profesional:* {prof_name}\n"
            text += f"💼 *Servicio:* {service_name}\n"
            text += f"📅 *Fecha:* {formatted_date}\n"
            text += f"🕐 *Horario:* {formatted_time}\n\n"
            text += "¿Confirmas esta cita?"
            
            # LOGGING FINAL
            logger.info(f"[DEBUG] MENSAJE FINAL generado:")
            logger.info(f"[DEBUG] Fecha en mensaje: {formatted_date}")
            logger.info(f"[DEBUG] Hora en mensaje: {formatted_time}")
            
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
            
            # Obtener información del contacto para el número de teléfono
            contact_info = await self.boki_api.get_contact_by_id(contact_id)
            phone_number = None
            client_id = None
            
            if contact_info:
                phone_number = contact_info.get('phone')
                logger.info(f"Número de teléfono obtenido del contacto: {phone_number}")
                
                # Obtener el cliente asociado usando el número de teléfono
                if phone_number:
                    client_data = await self.boki_api.get_client_by_phone(phone_number)
                    if client_data:
                        client_id = client_data.get('Id')
                        logger.info(f"ID del cliente obtenido: {client_id}")
                    else:
                        logger.warning(f"No se encontró cliente para el teléfono {phone_number}")
                else:
                    logger.warning("No se pudo obtener el número de teléfono del contacto")
            else:
                logger.warning(f"No se pudo obtener información del contacto {contact_id}")
            
            # Validar que tenemos el ID del cliente
            if not client_id:
                logger.error("No se pudo obtener el ID del cliente para crear la cita")
                return (
                    {"step": "waiting_confirmation", "data": data},
                    "❌ Error obteniendo información del cliente. Por favor intenta nuevamente.",
                    False
                )
            
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
            selected_date_info = data.get("selected_date_info", {})
            
            # DEBUG: Logging de valores antes de formatear
            logger.info(f"[DEBUG] Valores antes de formatear:")
            logger.info(f"[DEBUG] selected_date original: {selected_date}")
            logger.info(f"[DEBUG] selected_date_info: {selected_date_info}")
            logger.info(f"[DEBUG] selected_slot: {selected_slot}")
            
            # Usar fechaCompleta de selected_date_info si está disponible
            date_to_format = selected_date_info.get('fechaCompleta', selected_date) if selected_date_info else selected_date
            logger.info(f"[DEBUG] date_to_format elegida: {date_to_format}")
            
            # Formatear valores para la API
            formatted_date = self._format_date_for_api(date_to_format)
            formatted_time = self._format_time_for_api(selected_slot.get('start_time', selected_slot.get('hora_inicio')))
            
            logger.info(f"[DEBUG] Valores después de formatear:")
            logger.info(f"[DEBUG] formatted_date: {formatted_date}")
            logger.info(f"[DEBUG] formatted_time: {formatted_time}")
            
            appointment_data = {
                "ClientId": client_id,
                "ServiceId": service.get('Id'),
                "ProfessionalId": professional.get('Id'),
                "DtDate": formatted_date,
                "TStartTime": formatted_time,
                "BIsCompleted": False,
                "BIsAbsent": False,
                "CurrentStateId": 1
            }
            
            # Agregar número de teléfono si está disponible
            if phone_number:
                appointment_data["phoneNumber"] = phone_number
            
            logger.info(f"Datos de la cita: {appointment_data}")
            
            # Crear la cita
            result = await self.boki_api.create_appointment(appointment_data)
            
            if result and result.get('Id'):
                appointment_id = result.get('Id')
                prof_name = DataFormatter.format_professional_name(professional)
                service_name = service.get('VcName')
                
                # ✅ NUEVO: Formatear fecha y hora correctamente para mensaje final
                try:
                    selected_date = data["selected_date"]
                    start_time = selected_slot.get('start_time', selected_slot.get('hora_inicio'))
                    
                    logger.info(f"[DEBUG] Formateando mensaje final - fecha: {selected_date}, hora: {start_time}")
                    
                    # Usar DataFormatter mejorado
                    formatted_data = DataFormatter.format_stored_date_for_confirmation(selected_date, start_time)
                    formatted_date = formatted_data["fecha_completa"]
                    formatted_time = formatted_data["hora_12"]
                    
                except Exception as e:
                    logger.error(f"Error formateando para mensaje final: {e}")
                    # Fallback
                    formatted_date = data.get("selected_date_info", {}).get('fecha', 'Fecha seleccionada')
                    formatted_time = start_time
                
                response = "🎉 ¡CITA CONFIRMADA EXITOSAMENTE!\n\n"
                response += f"📋 *Número de cita:* {appointment_id}\n"
                response += f"👨‍⚕️ *Profesional:* {prof_name}\n"
                response += f"💼 *Servicio:* {service_name}\n"
                response += f"📅 *Fecha:* {formatted_date}\n"
                response += f"🕐 *Hora:* {formatted_time}\n\n"
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

    def _format_date_for_api(self, date_input: str) -> str:
        """
        Convierte fecha a formato requerido por la API (YYYY-M-D).
        Maneja múltiples formatos de entrada y elimina ceros iniciales.
        
        Args:
            date_input: Fecha en varios formatos:
                       - ISO: "2025-05-07" 
                       - Con hora: "28/05/2025 19:00"
                       - Sin hora: "28/05/2025"
            
        Returns:
            str: Fecha en formato "2025-5-7" (sin ceros iniciales)
        """
        try:
            logger.info(f"[DEBUG] _format_date_for_api - Input recibido: '{date_input}'")
            
            # Caso 1: Formato DD/MM/YYYY HH:MM (con hora) - extraer solo fecha
            if '/' in date_input and ' ' in date_input:
                fecha_parte = date_input.split(' ')[0]  # "28/05/2025"
                logger.info(f"[DEBUG] Detectado formato con hora, extrayendo fecha: {fecha_parte}")
                
                # Convertir DD/MM/YYYY a YYYY-M-D
                dia, mes, año = fecha_parte.split('/')
                formatted_date = f"{año}-{int(mes)}-{int(dia)}"
                
            # Caso 2: Formato DD/MM/YYYY (sin hora)
            elif '/' in date_input and ' ' not in date_input:
                logger.info(f"[DEBUG] Detectado formato DD/MM/YYYY sin hora")
                
                # Convertir DD/MM/YYYY a YYYY-M-D
                dia, mes, año = date_input.split('/')
                formatted_date = f"{año}-{int(mes)}-{int(dia)}"
                
            # Caso 3: Formato ISO YYYY-MM-DD
            elif '-' in date_input:
                logger.info(f"[DEBUG] Detectado formato ISO")
                
                # Dividir la fecha ISO y eliminar ceros iniciales
                year, month, day = date_input.split('-')
                formatted_date = f"{year}-{int(month)}-{int(day)}"
                
            else:
                logger.warning(f"[DEBUG] Formato de fecha no reconocido: {date_input}")
                return date_input  # Fallback: devolver original
            
            logger.info(f"[DEBUG] Fecha convertida para API: {date_input} -> {formatted_date}")
            return formatted_date
            
        except Exception as e:
            logger.error(f"Error formateando fecha para API '{date_input}': {e}")
            return date_input  # Fallback: devolver original

    def _format_time_for_api(self, time_12h: str) -> str:
        """
        Convierte horario de formato 12 horas (AM/PM) a formato 24 horas.
        
        Args:
            time_12h: Hora en formato "1:00 PM" o "8:30 AM"
            
        Returns:
            str: Hora en formato "13:00" o "08:30"
        """
        try:
            from datetime import datetime
            
            # Parsear la hora en formato 12 horas
            time_obj = datetime.strptime(time_12h, "%I:%M %p")
            
            # Convertir a formato 24 horas
            formatted_time = time_obj.strftime("%H:%M")
            
            logger.info(f"[DEBUG] Hora convertida para API: {time_12h} -> {formatted_time}")
            return formatted_time
            
        except Exception as e:
            logger.error(f"Error formateando hora para API '{time_12h}': {e}")
            # Fallback: intentar extraer solo números y asumir formato 24h
            if ":" in time_12h:
                return time_12h.split()[0]  # Tomar solo la parte antes del espacio
            return time_12h