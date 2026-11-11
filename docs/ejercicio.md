# Práctica opcional S17 · API de clasificación con Bedrock

Construye el mismo recorrido de la demo con tu propia configuración:
**cliente SigV4 → HTTP API con IAM → Lambda → Bedrock → JSON validado**.
Trabaja solo con incidencias ficticias.

1. Lee `lambda_function.py` y explica validación, llamada Converse y respuesta.
2. Comprueba perfil, ID del proyecto, región, disponibilidad y cuotas.
3. Despliega una Lambda y una HTTP API con autorización IAM.
4. Prueba 200 en salud, 403 sin firma, 422 con entrada vacía y una clasificación real.
5. Solicita un JSON estructurado y valida categoría, prioridad y respuesta.
6. Documenta entrada, tokens, reintentos, concurrencia y timeouts.
7. Recoge hasta seis peticiones secuenciales. Acredita cinco warm y un cold con
   REPORT, o declara que no se capturó frío; si falta muestra, indícalo.
8. Estima 1.000 solicitudes sin ejecutarlas, con región, fecha, tarifas y supuestos.
9. Explica brevemente alternativas en Azure/Google y cuándo elegirías otra arquitectura.
10. Elimina tus recursos y conserva evidencia saneada de la retirada.

Entrega el código, configuración sin secretos, peticiones, resultados, medidas,
estimación y limpieza. La práctica es opcional según la aclaración de Laura
del 04/11; la dedicación orientativa del enunciado es de 4–6 horas con accesos preparados.

La referencia enviada en septiembre era Nova 2 Lite mediante un perfil europeo.
Esta adaptación usa **Nova Lite dentro de eu-north-1** por las restricciones
del proyecto del aula. Se conserva el objetivo y el recorrido del ejercicio,
pero el cambio de modelo es explícito y exige tarifas y permisos propios.
La concurrencia se documenta con la cuota compartida real; esta cuenta no
permite la reserva de dos del paquete avanzado anterior.

Si Bedrock tiene cuota cero, conserva el preflight y el error como bloqueo:
**eso no cuenta como clasificación real ni como práctica completada**.
No sustituye Bedrock una respuesta fija o una llamada a OpenRouter.

Ampliación opcional: streaming con modelo, transporte y permisos compatibles.
RAG, LangGraph, bases de datos y AgentCore no son requisitos de este ejercicio.
