# Ensayo S17 · 11/11/2026

**Infraestructura desplegada y retirada; clasificación real pendiente de cuota.**
Se mantuvo el plan Free. No se han cambiado cuotas, regiones, facturación
ni los recursos de S16.

## Comprobaciones reales en AWS

| Comprobación | Resultado observado |
|---|---|
| Región y proyecto | eu-north-1; identidad STS comprobada antes de crear |
| Modelo | Nova Lite autorizado/disponible, pero cuotas de inferencia cero |
| Preflight del cliente | Se detiene con salida 2 y guarda el bloqueo, sin inferencia |
| CloudFormation | CREATE_COMPLETE; once recursos declarados |
| Lambda | Python 3.12, 512 MiB, 24 s; hash de aplicación `2a4412e16109` |
| HTTP API | Dos rutas AWS_IAM, integración payload 2.0, 29 s, ritmo/ráfaga 1 |
| IAM | Cliente firmado admitido; función limitada al modelo y sus logs |
| GET /health firmado | HTTP 200, sin llamada al modelo |
| POST sin firma | HTTP 403 Forbidden |
| POST firmado con texto vacío | HTTP 422, sin llamada al modelo |
| POST firmado con texto válido | HTTP 503 `bedrock_sin_cuota_o_limitado` |
| Logs | Respuestas 200/422/503 y REPORT de Lambda conservados localmente |
| Limpieza | Stack, API, función, rol propio y ambos grupos de logs ausentes |

En el primer intento de clasificación de Lambda se observó **Init Duration
443,26 ms**, tiempo de handler 190,02 ms y paso del modelo 189,95 ms. Esa
petición **falló** por cuota: no es una medición de clasificación exitosa.
El tiempo del cliente fue 1.055,35 ms. No se registraron tokens de salida ni
se inventó una respuesta. No hay cinco warm de clasificación ni lote válido.

Antes de desplegar se hizo una prueba directa de Converse con el conector
AWS: falló por tokens diarios y el conector informó tres reintentos propios.
El handler de la demo configura **un intento total** y su ensayo hizo un
solo intento, sin cambio de modelo ni simulación. No se repitieron lotes.

Se guardó evidencia operativa saneada en la carpeta privada
`.build/s17-simple/` del repositorio del profesor. La API temporal ya no existe.
No se ha consultado una factura: el coste del README es una estimación.

## Comprobaciones locales

- Para la publicación se prepararon **veinte pruebas independientes** en
  `tests/test_demo.py`. Pasan desde un entorno limpio con las dependencias
  de `requirements-dev.txt`; también pasan lint, formato y cfn-lint del
  repositorio independiente. No necesitan credenciales ni hacen inferencias.
- **65 tests correctos** en el repositorio, incluidos veinte de la nueva demo.
  Usan dobles y Stubber; no acreditan inferencia real.
- Ruff lint y formato correctos en todos los archivos Python nuevos.
- Validación cfn-lint correcta en las plantillas existentes y la nueva generada;
  ValidateTemplate de AWS también correcto.
- Dependencias de alumno instaladas en un entorno Python 3.12 limpio; calculadora
  offline ejecutada: 0,05722062525 USD parcial para 1.000 solicitudes supuestas.
- El lint global no pasa: 4.744 incidencias en veinte archivos de generadores
  previos de las presentaciones. Ninguna pertenece al código nuevo. El formato
  global también conserva incidencias anteriores; no se han reformateado esas fuentes.
- El aviso previo de Starlette/httpx no impide que terminen las pruebas.

## Pendiente para cerrar el ensayo completo

AWS debe habilitar cuota de Nova Lite manteniendo el plan Free, o confirmar
qué opciones ofrece al proyecto. Véase [cuotas y texto para soporte](docs/cuotas-aws.md).
No se ha enviado una solicitud ni activado el plan de pago.

Después: preflight correcto, despliegue nuevo, hasta seis clasificaciones,
REPORT, cinco warm y cold acreditado o declarado no capturado, estimación
interpretada y retirada. El ensayo de la infraestructura no completa esos pasos.

## Revalidación previa a publicación · 11/11/2026

Se volvieron a leer identidad, plan Free y las cuotas de Nova Lite en
eu-north-1. Solicitudes/minuto, tokens/minuto y tokens/día siguen en cero,
no ajustables. No se repitieron inferencias ni se crearon recursos para
reproducir el mismo bloqueo. La aplicación y la plantilla no han cambiado
desde el ensayo real; se reutiliza su evidencia de despliegue y limpieza.
La publicación incluye este límite de forma destacada en el README.
