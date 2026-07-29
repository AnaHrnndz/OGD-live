1. Resumen y Objetivo del Proyecto

El objetivo de este proyecto es transformar nuestra herramienta actual de línea de comandos, OG_Delineation (https://github.com/AnaHrnndz/OG_Delineation), en una plataforma bioinformática accesible e interactiva llamada OGD-live.

Actualmente, el uso de la herramienta requiere conocimientos técnicos en terminal y la instalación de dependencias, lo cual limita su adopción. OGD-live resolverá esta barrera permitiendo a cualquier investigador ejecutar el análisis, visualizar los resultados y exportar datos a través de un navegador web, sin necesidad de instalación local.

2. Arquitectura Técnica: Un Enfoque Moderno e Híbrido

Para garantizar la máxima eficiencia y escalabilidad, el desarrollo se basará en un servidor híbrido utilizando FastAPI. Esta arquitectura permite atender dos canales de comunicación desde un único punto:

Interfaz Web (Para Usuarios): Una aplicación web donde el investigador sube su árbol, ajusta parámetros y visualiza el resultado mediante un visor integrado de ETE4 Smartview.

Interfaz de Agente IA (Protocolo MCP): Mediante la integración de FastMCP, la herramienta será "IA-ready". Esto permitirá que asistentes inteligentes (como Claude o herramientas de análisis avanzado) utilicen OG_Delineation como una habilidad remota, permitiendo al usuario realizar consultas complejas en lenguaje natural sobre sus resultados sin necesidad de scripts adicionales.

3. Plan de Desarrollo y Faseado

El proyecto se dividirá en tres etapas para asegurar el cumplimiento de hitos:

Fase 1: Desarrollo del Backend Híbrido

Migración de la lógica de OG_Delineation al servidor FastAPI.

Implementación de las herramientas (tools) bajo el estándar FastMCP para la automatización de análisis.

Configuración del motor de visualización con ETE4 Smartview para renderizar árboles de forma interactiva vía iframe.

Fase 2: Contenedorización (Docker)

Encapsulación de toda la aplicación y sus dependencias en un entorno Docker. Esto garantiza que la herramienta funcione de forma idéntica en cualquier entorno de servidor, eliminando problemas de configuración de librerías bioinformáticas.

Fase 3: Despliegue y Pruebas

Despliegue inicial en Hugging Face Spaces, plataforma que ofrece recursos computacionales gratuitos (hasta 16GB de RAM), ideales para manejar árboles filogenéticos pesados.

Establecimiento de una política de limpieza automática de datos temporales (archivos .nwk y resultados HTML) para garantizar la privacidad y el uso eficiente de recursos.

4. Ventajas Estratégicas

Reducción de barreras técnicas: Eliminamos la necesidad de que el usuario gestione dependencias en su entorno local.

Capacidad de procesamiento masivo: La arquitectura permitirá que los usuarios ejecuten análisis complejos desde el navegador, delegando el peso del cómputo a nuestro servidor en la nube.

Posicionamiento de vanguardia: Al adoptar el protocolo MCP, nuestra herramienta será una de las primeras en la comunidad bioinformática capaz de integrarse directamente en flujos de trabajo de IA, lo que aumentará su visibilidad y potencial de citación.

Eficiencia en costes: Mediante el uso de servicios como Hugging Face Spaces o planes gratuitos, el coste de mantenimiento operativo inicial es de 0€.

5. Conclusión

El desarrollo de OGD-live no solo moderniza nuestra herramienta existente, sino que prepara a nuestro laboratorio para la investigación asistida por IA. Esta propuesta combina una interfaz gráfica intuitiva con un backend altamente técnico capaz de integrarse con los estándares más actuales de automatización científica.

Solicitud: Quedo a su disposición para discutir los detalles técnicos de esta implementación o proceder con la creación de un prototipo funcional en las próximas semanas.

