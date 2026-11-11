# Cuota de Bedrock · eu-north-1

## Comprobación del proyecto del profesor · 11/11/2026

- Plan Free activo; región seleccionada eu-north-1.
- Nova Lite (`amazon.nova-lite-v1:0`) figura autorizado y disponible.
- Solicitudes/minuto, tokens/minuto y tokens/día on-demand: **0**.
- La llamada real devolvió `ThrottlingException: Too many tokens per day`.
- Cuota de Lambda: diez ejecuciones simultáneas compartidas; ninguna función previa.

Los códigos de Nova Lite son `L-E386A278`, `L-70423BF8` y `L-45E0AD92`.
AWS los devuelve como **Adjustable=false** en este proyecto. No se han cambiado
plan, facturación, regiones ni cuotas, y no se ha enviado una solicitud a soporte.

## Revisión con AWS

En AWS Settings comprueba el proyecto y su plan Free. En Service Quotas elige
Amazon Bedrock y Estocolmo. Si no hay solicitud de incremento disponible,
consulta a soporte desde la vía habilitada para el proyecto. Texto preparado:

> Uso la nueva experiencia de AWS, plan Free y región eu-north-1. Quiero
> realizar una demo docente pequeña con Lambda, HTTP API y Amazon Nova Lite
> (`amazon.nova-lite-v1:0`) mediante Converse, sin inferencia entre regiones.
> GetFoundationModelAvailability devuelve AUTHORIZED/AVAILABLE, pero las
> cuotas L-E386A278, L-70423BF8 y L-45E0AD92 son cero y no ajustables. Una
> inferencia devuelve ThrottlingException por tokens diarios. ¿Podéis
> confirmar si se puede habilitar una cuota pequeña manteniendo Free y qué
> trámite requiere? El ensayo tendrá como máximo seis clasificaciones
> secuenciales, maxTokens=300 y sin reintentos. No autorizo cambiar el plan.

Añade el ID de tu proyecto únicamente en el formulario privado de AWS.
No adjuntes claves ni tokens. El saldo de créditos no demuestra que exista
cuota. No se garantiza que pasar a pago resuelva el problema automáticamente.

Cuando AWS indique que está habilitado, ejecuta `python cliente.py preflight`.
Solo si termina correctamente procede a desplegar y medir. Para dar por
cerrada la demo hacen falta inferencia real, cinco warm/REPORT (o declarar
muestra incompleta), coste interpretado y limpieza verificada.
