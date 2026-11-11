"""Estima 1.000 peticiones SIN ejecutarlas: cantidades por tarifas públicas."""

import argparse
import json
import statistics
import sys
from decimal import Decimal
from pathlib import Path

from cliente import resumen_mediciones

RAIZ = Path(__file__).resolve().parent


def D(numero):
    return Decimal(str(numero))


def calcular(cantidades, tarifas):
    n = D(1000)
    memoria_gb = D(cantidades["memory_mb"]) / D(1024)
    fraccion = D(cantidades["cold_fraction"])
    duracion = (
        (1 - fraccion) * D(cantidades["warm_billed_ms"])
        + fraccion * D(cantidades["cold_billed_ms"])
    ) / D(1000)
    r = {k: D(v["usd"]) for k, v in tarifas["rates"].items()}
    partidas = {
        "lambda_duracion": n * memoria_gb * duracion * r["lambda_gbs"],
        "lambda_solicitudes": n * r["lambda_request"],
        "api_gateway": n * r["api_request"],
        "bedrock_entrada": n * D(cantidades["input_tokens"]) / D(1000) * r["input_1k"],
        "bedrock_salida": n * D(cantidades["output_tokens"]) / D(1000) * r["output_1k"],
        # Los 0,002 GB supuestos incluyen logs de Lambda y de la API.
        "logs_ingesta": D("0.002") * r["logs_ingest_gb"],
        "logs_3_dias": D("0.002") * D(3) / D(30) * r["logs_store_gb_month"],
    }
    return {
        "region": tarifas["region"],
        "modelo": tarifas["model_id"],
        "fecha_tarifas": tarifas["fecha_lectura"],
        "peticiones_estimadas": 1000,
        "cantidades": cantidades,
        "partidas_usd": {k: str(v) for k, v in partidas.items()},
        "total_parcial_usd": str(sum(partidas.values())),
        "limites": "Sin tráfico de salida, impuestos ni descuentos/créditos. "
        "Frecuencia fría y volumen de logs son supuestos. No es una factura.",
        "inferencias_ejecutadas_por_este_comando": 0,
    }


def desde_mediciones(datos, fraccion):
    resumen = resumen_mediciones(datos)
    if datos.get("region") != "eu-north-1" or datos.get("modelo") != "amazon.nova-lite-v1:0":
        raise ValueError("Modelo o región distintos de las tarifas.")
    if len(datos["peticiones"]) != 6 or resumen["clasificaciones_reales"] != 6:
        raise ValueError("Se necesitan seis clasificaciones reales correctas, sin fallos ocultos.")
    if resumen["calientes_acreditadas"] < 5:
        raise ValueError("Faltan cinco warm con REPORT. Relee logs sin repetir inferencia.")
    for fila in datos["peticiones"]:
        report = fila.get("report") or {}
        consumo = fila["respuesta"].get("metadata", {}).get("consumo")
        if report.get("memory_mb") != 512 or report.get("billed_ms") is None:
            raise ValueError("Falta REPORT de 512 MiB; no se inventa la duración.")
        if not consumo or any(
            type(consumo.get(k)) is not int for k in ("inputTokens", "outputTokens")
        ):
            raise ValueError("Faltan tokens reales; no se sustituyen por cero.")
    frias = [p for p in datos["peticiones"] if p["report"].get("init_ms") is not None]
    calientes = [
        p
        for p in datos["peticiones"]
        if p["report"].get("init_ms") is None
        and p["respuesta"]["metadata"].get("first_in_environment") is False
    ]
    if not frias and fraccion != 0:
        raise ValueError("No se capturó frío. Usa --fraccion-fria 0 para un escenario solo warm.")
    return {
        "origen": "duraciones_y_tokens_medidos; frecuencia_fria_y_logs_son_supuestos",
        "memory_mb": 512,
        # Billed Duration YA incluye INIT: no se suma init_ms otra vez.
        "warm_billed_ms": statistics.mean(p["report"]["billed_ms"] for p in calientes),
        "cold_billed_ms": statistics.mean(p["report"]["billed_ms"] for p in frias) if frias else 0,
        "cold_fraction": fraccion,
        "input_tokens": statistics.mean(
            p["respuesta"]["metadata"]["consumo"]["inputTokens"] for p in datos["peticiones"]
        ),
        "output_tokens": statistics.mean(
            p["respuesta"]["metadata"]["consumo"]["outputTokens"] for p in datos["peticiones"]
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mediciones", type=Path)
    p.add_argument("--fraccion-fria", type=float, default=0.05)
    args = p.parse_args()
    try:
        if not 0 <= args.fraccion_fria <= 1:
            raise ValueError("La fracción fría debe estar entre 0 y 1.")
        cantidades = {
            "origen": "supuestos_docentes_no_mediciones",
            "memory_mb": 512,
            "warm_billed_ms": 1500,
            "cold_billed_ms": 1800,
            "cold_fraction": args.fraccion_fria,
            "input_tokens": 250,
            "output_tokens": 100,
        }
        if args.mediciones:
            cantidades = desde_mediciones(
                json.loads(args.mediciones.read_text()), args.fraccion_fria
            )
        print(
            json.dumps(
                calcular(cantidades, json.loads((RAIZ / "tarifas.json").read_text())),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except (ValueError, OSError) as exc:
        print(f"Estimación no completada: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
