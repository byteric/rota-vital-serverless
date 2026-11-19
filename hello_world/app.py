import base64
import binascii
import json
import time
from typing import Any

contador = 0  # variável global: só sobrevive se o ambiente for reaproveitado

JSON_HEADERS = {"Content-Type": "application/json"}


def _json_response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": JSON_HEADERS,
        "body": json.dumps(payload),
    }


def _parse_body(event: dict[str, Any]) -> dict[str, Any] | None:
    raw_body = event.get("body") or "{}"
    if not isinstance(raw_body, str):
        return None
    if event.get("isBase64Encoded") and raw_body != "{}":
        try:
            raw_body = base64.b64decode(raw_body, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return None
    try:
        parsed = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    global contador
    contador += 1

    pedido = _parse_body(event)
    if pedido is None:
        return _json_response(400, {"erro": "corpo JSON inválido"})

    requisicao_id = pedido.get("requisicaoId")
    if not isinstance(requisicao_id, str) or not requisicao_id.strip():
        return _json_response(400, {"erro": "requisicaoId obrigatório"})

    if pedido.get("demorar"):
        time.sleep(5)  # passa do Timeout inicial de 3 s

    guia = {
        "guia": f"G-{requisicao_id}",
        "hospital": pedido.get("hospital"),
        "bolsas": pedido.get("bolsas", []),
        "invocacaoNesteAmbiente": contador,
    }
    return _json_response(201, guia)
