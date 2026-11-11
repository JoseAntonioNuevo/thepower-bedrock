# Prompt · desplegar, validar y limpiar S17

Sustituye los cuatro valores y copia el bloque en tu agente con acceso local y AWS.
La sesión del navegador debe estar iniciada; nunca pegues credenciales en el chat.

```text
Trabaja en la demo S17 de esta carpeta: [RUTA_ABSOLUTA].
Perfil AWS: [PERFIL]. ID de proyecto esperado: [DOCE_DIGITOS].
Región exclusiva: eu-north-1. Stack propio nuevo: s17-[MI_NOMBRE]-ensayo.

Lee README.md, lambda_function.py, plantilla.json y las instrucciones aplicables.
Quiero que prepares, despliegues, valides y retires esta demo pequeña:
cliente SigV4 → HTTP API AWS_IAM → Lambda → Nova Lite en Bedrock.
Puedes crear y borrar solo los recursos de ese stack y realizar como máximo
seis clasificaciones secuenciales de incidencias ficticias, sin reintentos.

1. Verifica STS, perfil, región, nombre, estado previo y dependencias.
   Rechaza otra cuenta/región o un stack existente. No uses el perfil global.
2. Ejecuta el preflight del cliente. Si faltan acceso o cuota, conserva la
   evidencia y termina como bloqueado antes de desplegar. No solicites
   incrementos ni cambies plan, facturación, regiones o modelos sin permiso.
3. Genera la plantilla con preparar.py, valida y despliega con las etiquetas
   Project=thepower-s17 y Purpose=classroom-demo. Registra el inventario propio.
   Prefiere el conector oficial de AWS para infraestructura si está disponible.
4. Comprueba configuración real: Python 3.12, 512 MiB, 24 s, modelo directo
   amazon.nova-lite-v1:0; dos rutas con IAM, rol limitado y logs de tres días.
5. Mide primero para tener oportunidad de capturar frío: como máximo seis
   clasificaciones y parada al primer fallo. No repitas para mejorar la muestra.
   Verifica resultado validado, tokens y tiempos. Une REPORT por request ID.
   Declara si no hay cold o cinco warm; no lo deduzcas de la primera petición.
6. Comprueba salud 200, sin firma 403 y entrada inválida 422. Esas pruebas
   no deben invocar el modelo. No añadas otra clasificación después del lote.
7. Estima 1.000 solicitudes sin ejecutarlas. Distingue medidas, supuestos,
   partidas incluidas y costes que no se han calculado.
8. En cualquier salida, incluso tras fallar, retira solo los recursos que
   acabas de crear. Verifica stack eliminado, API, función, rol y ambos grupos
   de logs ausentes. Conserva perfil, S16 y recursos ajenos.
9. Entrega un informe breve con pruebas reales, bloqueos y limpieza.

No publiques ni imprimas claves, session tokens, Authorization ni headers
firmados. No uses OpenRouter, una simulación o otra región para presentar
como completada una prueba de Bedrock que haya fallado.
```
