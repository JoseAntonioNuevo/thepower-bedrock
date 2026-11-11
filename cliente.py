"""Utilidad del aula: comprobar acceso, firmar HTTP y leer evidencia, sin secretos.

La aplicación está en lambda_function.py. Este cliente solo evita copiar
credenciales en curl y automatiza un lote pequeño de mediciones.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import BotoCoreError, ClientError

RAIZ = Path(__file__).resolve().parent
REGION = "eu-north-1"
MODELO = "amazon.nova-lite-v1:0"


def guardar(nombre, datos):
    carpeta = RAIZ / ".demo-aws"
    carpeta.mkdir(exist_ok=True)
    (carpeta / nombre).write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n")


def sesion(args):
    """No elegimos el perfil global ni otra cuenta si falta configuración."""
    if not args.perfil or not re.fullmatch(r"\d{12}", args.cuenta or ""):
        raise ValueError("Configura AWS_PROFILE y S17_ACCOUNT (12 dígitos).")
    if not re.fullmatch(r"s17-[a-z0-9-]{1,50}", args.stack or ""):
        raise ValueError("S17_STACK debe empezar por s17- y usar minúsculas/números/guiones.")
    if os.getenv("AWS_REGION", REGION) != REGION:
        raise ValueError("Esta demo solo admite AWS_REGION=eu-north-1.")
    s = boto3.Session(profile_name=args.perfil, region_name=REGION)
    identidad = s.client("sts").get_caller_identity()
    if identidad["Account"] != args.cuenta:
        raise ValueError("La identidad AWS no coincide con S17_ACCOUNT. No se continúa.")
    return s


def preflight(s):
    """AVAILABLE no basta: las cuotas pueden ser cero aunque haya acceso."""
    b = s.client("bedrock")
    disponibilidad = b.get_foundation_model_availability(modelId=MODELO)
    q = s.client("service-quotas")
    # Códigos del modelo on-demand, NO de su perfil entre regiones.
    cuotas = {
        nombre: q.get_service_quota(ServiceCode="bedrock", QuotaCode=codigo)["Quota"]["Value"]
        for nombre, codigo in {
            "solicitudes_minuto": "L-E386A278",
            "tokens_minuto": "L-70423BF8",
            "tokens_dia": "L-45E0AD92",
        }.items()
    }
    datos = {
        "region": REGION,
        "modelo": MODELO,
        "disponibilidad": disponibilidad,
        "cuotas_bedrock": cuotas,
        "concurrencia_compartida_lambda": s.client("lambda").get_account_settings()["AccountLimit"],
        "inferencia_ejecutada": False,
    }
    guardar("preflight.json", datos)
    print(json.dumps(datos, ensure_ascii=False, indent=2))
    acceso = (
        disponibilidad.get("authorizationStatus") == "AUTHORIZED"
        and disponibilidad.get("regionAvailability") == "AVAILABLE"
        and disponibilidad.get("entitlementAvailability") == "AVAILABLE"
        and disponibilidad.get("agreementAvailability", {}).get("status") == "AVAILABLE"
    )
    if not acceso or any(v <= 0 for v in cuotas.values()):
        raise ValueError(
            "Bedrock no está listo: revisa acceso/cuotas en eu-north-1. "
            "No repitas inferencias ni cambies de región/proveedor para ocultarlo."
        )


def salidas(s, args):
    stack = s.client("cloudformation").describe_stacks(StackName=args.stack)["Stacks"][0]
    etiquetas = {t["Key"]: t["Value"] for t in stack.get("Tags", [])}
    if etiquetas.get("Project") != "thepower-s17":
        raise ValueError("El stack no tiene la etiqueta Project=thepower-s17.")
    if stack["StackStatus"] not in {"CREATE_COMPLETE", "UPDATE_COMPLETE"}:
        raise ValueError(f"Stack aún no preparado: {stack['StackStatus']}")
    valores = {o["OutputKey"]: o["OutputValue"] for o in stack["Outputs"]}
    # La URL viene del stack propio; no firmamos direcciones arbitrarias.
    esperado = f"https://{valores['ApiId']}.execute-api.{REGION}.amazonaws.com"
    if valores["ApiUrl"] != esperado:
        raise ValueError("Endpoint inesperado: no se enviarán credenciales.")
    return valores


class SinRedirecciones(HTTPRedirectHandler):
    """Una redirección nunca debe llevar los headers firmados a otro destino."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def pedir(s, url, texto, *, health=False, sin_firma=False):
    metodo = "GET" if health else "POST"
    cuerpo = None if health else json.dumps({"texto": texto}, ensure_ascii=False).encode()
    headers = {"content-type": "application/json"}
    if not sin_firma:
        credenciales = s.get_credentials().get_frozen_credentials()
        if not credenciales.token:
            raise ValueError("Usa credenciales temporales: aws login o SSO, no claves permanentes.")
        peticion = AWSRequest(method=metodo, url=url, data=cuerpo, headers=headers)
        SigV4Auth(credenciales, "execute-api", REGION).add_auth(peticion)
        headers = dict(peticion.headers)
    inicio = time.perf_counter()
    solicitud = Request(url, data=cuerpo, headers=headers, method=metodo)
    try:
        respuesta = build_opener(SinRedirecciones).open(solicitud, timeout=35)
    except HTTPError as exc:
        respuesta = exc  # Conservamos también el cuerpo de 403, 422 y 503.
    with respuesta:
        datos = respuesta.read(65537)
        if len(datos) > 65536:
            raise ValueError("Respuesta demasiado grande.")
        return {
            "http_status": respuesta.code,
            "http_duration_ms": round((time.perf_counter() - inicio) * 1000, 2),
            "respuesta": json.loads(datos),
        }


def leer_logs(s, valores, mediciones=None):
    eventos = []
    desde = (mediciones or {}).get("inicio_ms", int((time.time() - 1800) * 1000))
    paginador = s.client("logs").get_paginator("filter_log_events")
    for pagina in paginador.paginate(logGroupName=valores["LogsLambda"], startTime=desde):
        eventos.extend(pagina.get("events", []))
    reports = {}
    for evento in eventos:
        linea = evento["message"]
        if not linea.startswith("REPORT RequestId:"):
            continue
        identificador = re.search(r"RequestId:\s*(\S+)", linea).group(1)

        def numero(nombre, linea=linea):
            valor = re.search(rf"{nombre}:\s*([\d.]+)", linea)
            return float(valor.group(1)) if valor else None

        reports[identificador] = {
            "billed_ms": numero("Billed Duration"),
            "init_ms": numero("Init Duration"),
            "memory_mb": numero("Memory Size"),
        }
    guardar("logs.json", eventos)
    if mediciones is not None:
        for fila in mediciones["peticiones"]:
            meta = fila["respuesta"].get("metadata", {})
            fila["report"] = reports.get(meta.get("request_id"))
        guardar("mediciones.json", mediciones)
        resumen = resumen_mediciones(mediciones)
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
    else:
        for evento in eventos:
            print(evento["message"].rstrip())


def resumen_mediciones(datos):
    correctas = [
        p
        for p in datos["peticiones"]
        if p["http_status"] == 200
        and p["respuesta"].get("modo") == "real"
        and "resultado" in p["respuesta"]
    ]
    frias = [p for p in correctas if (p.get("report") or {}).get("init_ms") is not None]
    calientes = [
        p
        for p in correctas
        if p.get("report")
        and p["report"].get("init_ms") is None
        and p["respuesta"].get("metadata", {}).get("first_in_environment") is False
    ]
    return {
        "intentos": len(datos["peticiones"]),
        "clasificaciones_reales": len(correctas),
        "calientes_acreditadas": len(calientes),
        "frias_acreditadas": len(frias),
        "cold_start": "capturado" if frias else "no_capturado",
        "cinco_warm_completadas": len(calientes) >= 5,
        "nota": "Si faltan REPORT, relee logs; no repitas las inferencias.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("accion", choices=["preflight", "estado", "probar", "medir", "logs"])
    p.add_argument("--perfil", default=os.getenv("AWS_PROFILE"))
    p.add_argument("--cuenta", default=os.getenv("S17_ACCOUNT"))
    p.add_argument("--stack", default=os.getenv("S17_STACK"))
    p.add_argument("--texto", default="No puedo entrar en mi cuenta ficticia")
    p.add_argument("--health", action="store_true")
    p.add_argument("--sin-firma", action="store_true")
    p.add_argument(
        "--execute", action="store_true", help="Autoriza las peticiones HTTP de esta ejecución"
    )
    args = p.parse_args()
    try:
        if args.accion in {"probar", "medir"} and not args.execute:
            raise ValueError("Añade --execute: una clasificación válida consume Bedrock.")
        s = sesion(args)
        if args.accion == "preflight":
            preflight(s)
            return 0
        valores = salidas(s, args)
        if args.accion == "estado":
            print(json.dumps(valores, indent=2))
        elif args.accion == "probar":
            ruta = "/health" if args.health else "/clasificar"
            resultado = pedir(
                s,
                valores["ApiUrl"] + ruta,
                args.texto,
                health=args.health,
                sin_firma=args.sin_firma,
            )
            guardar("ultima-peticion.json", resultado)
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return 0 if resultado["http_status"] == 200 else 1
        elif args.accion == "medir":
            preflight(s)  # Si hay cuota cero no se lanza ni la primera inferencia.
            datos = {
                "region": REGION,
                "modelo": MODELO,
                "stack": args.stack,
                "inicio_ms": int(time.time() * 1000),
                "peticiones": [],
            }
            for i in range(6):
                resultado = pedir(s, valores["ApiUrl"] + "/clasificar", args.texto)
                datos["peticiones"].append(resultado)
                guardar("mediciones.json", datos)  # Cada intento queda guardado.
                print(f"Petición {i + 1}/6: HTTP {resultado['http_status']}")
                if resultado["http_status"] != 200:
                    return 1  # No reintentar fallos ni rellenar la muestra.
                if i < 5:
                    time.sleep(1.1)
            leer_logs(s, valores, datos)
        elif args.accion == "logs":
            archivo = RAIZ / ".demo-aws/mediciones.json"
            datos = json.loads(archivo.read_text()) if archivo.exists() else None
            if datos and (datos.get("stack") != args.stack or datos.get("region") != REGION):
                raise ValueError("Las mediciones pertenecen a otro stack o región.")
            leer_logs(s, valores, datos)
        return 0
    except (ValueError, BotoCoreError, ClientError, OSError) as exc:
        # Ningún error provoca una segunda inferencia o un cambio de proveedor.
        print(f"No completado: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
