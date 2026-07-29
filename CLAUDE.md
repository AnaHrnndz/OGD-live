# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado actual del repositorio

**Este repositorio está en fase de propuesta/planificación: todavía no contiene código fuente.** El único
archivo de contenido es `readme.md` (en español), que describe el objetivo y la arquitectura planeada del
proyecto OGD-live. No existe build system, gestor de dependencias, tests, ni estructura de carpetas de
código todavía. No asumas que existen componentes, endpoints o módulos hasta que se implementen: verifica
siempre el estado real del árbol de archivos antes de referenciar rutas o módulos concretos.

Cuando se empiece a implementar código, esta sección y las siguientes deben actualizarse para reflejar los
comandos reales de build/lint/test y la arquitectura efectiva (no la planeada).

## Objetivo del proyecto

OGD-live busca transformar la herramienta de línea de comandos existente
[OG_Delineation](https://github.com/AnaHrnndz/OG_Delineation) —una herramienta bioinformática que requiere
conocimientos de terminal e instalación local de dependencias— en una **plataforma web interactiva**, de
forma que cualquier investigador pueda ejecutar el análisis, visualizar resultados y exportar datos desde
el navegador, sin instalación local.

## Arquitectura técnica planeada

El diseño propuesto es un **servidor híbrido basado en FastAPI** que atiende dos canales desde un único
punto de entrada:

- **Interfaz web (usuarios humanos):** el investigador sube su árbol filogenético, ajusta parámetros y
  visualiza el resultado mediante un visor integrado de **ETE4 Smartview** (renderizado interactivo vía
  iframe).
- **Interfaz de agente IA (protocolo MCP):** mediante **FastMCP**, la herramienta expone las funciones de
  OG_Delineation como *tools* remotas, permitiendo que asistentes de IA (p. ej. Claude) realicen consultas
  en lenguaje natural sobre los resultados sin scripts adicionales.

### Fases de desarrollo previstas

1. **Backend híbrido:** migrar la lógica de OG_Delineation a FastAPI; implementar las tools bajo el
   estándar FastMCP; integrar ETE4 Smartview para visualización interactiva de árboles.
2. **Contenedorización:** empaquetar la aplicación y sus dependencias bioinformáticas en Docker para
   garantizar reproducibilidad entre entornos.
3. **Despliegue y pruebas:** despliegue inicial en Hugging Face Spaces (hasta 16GB RAM); establecer
   limpieza automática de archivos temporales (`.nwk` y resultados HTML) por privacidad y uso eficiente de
   recursos.

## Notas para el desarrollo futuro

- La lógica de dominio (delineación de grupos ortólogos, análisis filogenético) vive actualmente en el
  repositorio externo `OG_Delineation`; cualquier migración debe preservar su comportamiento funcional.
- Los archivos de entrada/salida esperados son árboles en formato Newick (`.nwk`) y resultados exportados
  como HTML — tenlo en cuenta al diseñar la limpieza de temporales y los límites de tamaño de subida.
- Al introducir FastMCP, las tools expuestas deben mantenerse alineadas con las capacidades de la interfaz
  web para evitar que un canal (humano vs. agente IA) tenga funcionalidad que el otro no puede reproducir.
