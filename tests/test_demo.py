"""Demo S17 pequeña: tests offline; ningún resultado acredita inferencia real."""

import importlib.util
import json
import time
from pathlib import Path
from types import SimpleNamespace

import boto3
import pytest
from botocore.stub import Stubber

DEMO = Path(__file__).resolve().parents[1]


def cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, DEMO / archivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def app(monkeypatch):
    cliente = boto3.client(
        "bedrock-runtime",
        region_name="eu-north-1",
        aws_access_key_id="offline",
        aws_secret_access_key="offline",
        aws_session_token="offline",
    )
    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: cliente)
    monkeypatch.setenv("AWS_REGION", "eu-north-1")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    return cargar("s17_simple_app", "lambda_function.py"), cliente


def evento(texto="Incidencia ficticia de acceso"):
    return {
        "version": "2.0",
        "routeKey": "POST /clasificar",
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"texto": texto}),
        "requestContext": {"timeEpoch": int(time.time() * 1000)},
    }


def contexto(margen=24000):
    return SimpleNamespace(
        aws_request_id="offline-request", get_remaining_time_in_millis=lambda: margen
    )


def test_converse_valido_y_validacion_independiente_de_salida(app, capsys):
    modulo, cliente = app
    salida = {
        "stopReason": "tool_use",
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "offline",
                            "name": "emitir_clasificacion",
                            "input": {
                                "categoria": "acceso",
                                "prioridad": "media",
                                "respuesta": "Usa recuperación de acceso.",
                            },
                        }
                    }
                ],
            }
        },
        "usage": {"inputTokens": 12, "outputTokens": 20, "totalTokens": 32},
        "metrics": {"latencyMs": 20},
    }
    with Stubber(cliente) as stub:
        stub.add_response("converse", salida)
        resultado = modulo.lambda_handler(evento(), contexto())
        stub.assert_no_pending_responses()
    datos = json.loads(resultado["body"])
    assert resultado["statusCode"] == 200
    assert datos["resultado"]["categoria"] == "acceso"
    assert datos["metadata"]["consumo"]["inputTokens"] == 12
    assert datos["metadata"]["model_duration_ms"] is not None
    assert "Incidencia ficticia" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "caso,estado",
    [
        ("vacio", 422),
        ("extra", 422),
        ("tipo", 415),
        ("json", 400),
        ("base64", 400),
        ("grande", 413),
        ("tarde", 504),
        ("health", 200),
    ],
)
def test_rechazos_y_salud_no_invocan_bedrock(app, caso, estado):
    modulo, cliente = app
    e = evento("") if caso == "vacio" else evento()
    if caso == "extra":
        e["body"] = '{"texto":"hola","otro":"dato"}'
    if caso == "tipo":
        e["headers"] = {"content-type": "text/plain"}
    if caso == "json":
        e["body"] = "{"
    if caso == "base64":
        e.update(body="%%%", isBase64Encoded=True)
    if caso == "grande":
        e["body"] = "x" * 12000
    if caso == "health":
        e["routeKey"] = "GET /health"
    if caso == "tarde":
        e["requestContext"]["timeEpoch"] -= 10000
    # El Stubber vacío falla si el handler intenta llamar a AWS.
    with Stubber(cliente):
        assert modulo.lambda_handler(e, contexto())["statusCode"] == estado


@pytest.mark.parametrize(
    "codigo,estado",
    [("ThrottlingException", 503), ("AccessDeniedException", 502), ("ModelTimeoutException", 504)],
)
def test_error_no_reintenta_ni_simula_y_conserva_tiempo(app, codigo, estado):
    modulo, cliente = app
    with Stubber(cliente) as stub:
        stub.add_client_error(
            "converse", service_error_code=codigo, service_message="detalle-privado"
        )
        respuesta = modulo.lambda_handler(evento(), contexto())
        stub.assert_no_pending_responses()
    cuerpo = json.loads(respuesta["body"])
    assert respuesta["statusCode"] == estado
    assert "resultado" not in cuerpo and "detalle-privado" not in respuesta["body"]
    assert cuerpo["metadata"]["consumo"] is None
    assert cuerpo["metadata"]["model_duration_ms"] is not None


@pytest.mark.parametrize(
    "resultado",
    [
        {"categoria": "inventada", "prioridad": "media", "respuesta": "x"},
        {"categoria": "acceso", "prioridad": "media", "respuesta": "x", "extra": True},
        {"categoria": "acceso", "prioridad": "media", "respuesta": "x" * 501},
    ],
)
def test_modelo_no_puede_ampliar_el_contrato(app, resultado):
    with pytest.raises(ValueError):
        app[0].validar_resultado(resultado)


def test_primera_peticion_sin_report_no_acredita_cold(monkeypatch):
    monkeypatch.syspath_prepend(str(DEMO))
    cliente = cargar("s17_simple_cliente", "cliente.py")
    datos = {
        "peticiones": [
            {
                "http_status": 200,
                "respuesta": {
                    "modo": "real",
                    "resultado": {},
                    "metadata": {"first_in_environment": True},
                },
            }
        ]
    }
    resumen = cliente.resumen_mediciones(datos)
    assert resumen["frias_acreditadas"] == resumen["calientes_acreditadas"] == 0
    assert resumen["cold_start"] == "no_capturado"


def test_report_asociado_por_id_y_cinco_warm_sin_inferencias(monkeypatch, tmp_path):
    cliente = cargar("s17_simple_evidencia", "cliente.py")
    monkeypatch.setattr(cliente, "RAIZ", tmp_path)
    filas, eventos = [], []
    for i in range(6):
        filas.append(
            {
                "http_status": 200,
                "respuesta": {
                    "modo": "real",
                    "resultado": {"categoria": "acceso"},
                    "metadata": {"request_id": f"offline-{i}", "first_in_environment": i == 0},
                },
            }
        )
        linea = (
            f"REPORT RequestId: offline-{i}\tDuration: 192.37 ms\t"
            "Billed Duration: 636 ms\tMemory Size: 512 MB\tMax Memory Used: 87 MB"
        )
        eventos.append({"message": linea + ("\tInit Duration: 443.26 ms" if i == 0 else "")})
    paginator = SimpleNamespace(paginate=lambda **kwargs: [{"events": eventos}])
    session = SimpleNamespace(
        client=lambda name: SimpleNamespace(get_paginator=lambda name: paginator)
    )
    datos = {"inicio_ms": 1, "peticiones": filas}
    cliente.leer_logs(session, {"LogsLambda": "/offline"}, datos)
    resumen = cliente.resumen_mediciones(datos)
    assert resumen["calientes_acreditadas"] == 5 and resumen["frias_acreditadas"] == 1
    assert datos["peticiones"][0]["report"]["billed_ms"] == 636
    assert datos["peticiones"][0]["report"]["init_ms"] == 443.26


def test_redireccion_no_puede_llevar_la_firma_a_otro_destino():
    cliente = cargar("s17_simple_redireccion", "cliente.py")
    assert (
        cliente.SinRedirecciones().redirect_request(
            None, None, 302, "redirect", {}, "https://otro.example"
        )
        is None
    )


def test_coste_rechaza_muestra_incompleta_y_suma_partidas(monkeypatch):
    monkeypatch.syspath_prepend(str(DEMO))
    coste = cargar("s17_simple_coste", "coste.py")
    with pytest.raises(ValueError):
        coste.desde_mediciones(
            {"region": "eu-north-1", "modelo": "amazon.nova-lite-v1:0", "peticiones": []}, 0
        )
    cantidades = {
        "memory_mb": 512,
        "warm_billed_ms": 1500,
        "cold_billed_ms": 1800,
        "cold_fraction": 0.05,
        "input_tokens": 250,
        "output_tokens": 100,
    }
    calculo = coste.calcular(cantidades, json.loads((DEMO / "tarifas.json").read_text()))
    assert calculo["total_parcial_usd"] == "0.05722062525000"
    assert calculo["inferencias_ejecutadas_por_este_comando"] == 0


def test_plantilla_no_abre_rutas_sin_iam_ni_pide_reserva_imposible():
    plantilla = json.loads((DEMO / "plantilla.json").read_text())
    recursos = plantilla["Resources"]
    for recurso in recursos.values():
        if recurso["Type"] == "AWS::ApiGatewayV2::Route":
            assert recurso["Properties"]["AuthorizationType"] == "AWS_IAM"
    assert "ReservedConcurrentExecutions" not in recursos["Funcion"]["Properties"]
    rol = recursos["RolLambda"]["Properties"]["Policies"][0]["PolicyDocument"]
    assert rol["Statement"][0]["Action"] == "bedrock:InvokeModel"
    assert "nova-lite-v1:0" in rol["Statement"][0]["Resource"]["Fn::Sub"]
