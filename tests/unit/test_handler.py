import base64
import json
from pathlib import Path

import pytest

from hello_world import app

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def reset_contador():
    app.contador = 0
    yield
    app.contador = 0


def make_event(payload, *, is_base64=False, raw_body=None):
    if raw_body is not None:
        body = raw_body
    elif payload is None:
        body = None
    else:
        raw = json.dumps(payload)
        body = base64.b64encode(raw.encode("utf-8")).decode("utf-8") if is_base64 else raw
    return {
        "body": body,
        "isBase64Encoded": is_base64,
        "httpMethod": "POST",
        "path": "/guias",
    }


def test_missing_requisicao_id_returns_400():
    ret = app.lambda_handler(make_event({"hospital": "H-Recife"}), "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 400
    assert ret["headers"]["Content-Type"] == "application/json"
    assert data["erro"] == "requisicaoId obrigatório"


def test_empty_body_returns_400():
    ret = app.lambda_handler(make_event(None), "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 400
    assert ret["headers"]["Content-Type"] == "application/json"
    assert "erro" in data


def test_valid_request_generates_guia_and_increments_counter():
    event = make_event(
        {
            "requisicaoId": "R-001",
            "hospital": "H-Recife",
            "bolsas": ["O-NEG-0142"],
        }
    )

    ret1 = app.lambda_handler(event, "")
    data1 = json.loads(ret1["body"])

    assert ret1["statusCode"] == 201
    assert ret1["headers"]["Content-Type"] == "application/json"
    assert data1 == {
        "guia": "G-R-001",
        "hospital": "H-Recife",
        "bolsas": ["O-NEG-0142"],
        "invocacaoNesteAmbiente": 1,
    }

    ret2 = app.lambda_handler(event, "")
    data2 = json.loads(ret2["body"])

    assert ret2["statusCode"] == 201
    assert data2["invocacaoNesteAmbiente"] == 2


def test_base64_encoded_body_from_sam_generate_event():
    event = make_event(
        {
            "requisicaoId": "R-001",
            "hospital": "H-Recife",
            "bolsas": ["O-NEG-0142"],
        },
        is_base64=True,
    )

    ret = app.lambda_handler(event, "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 201
    assert ret["headers"]["Content-Type"] == "application/json"
    assert data["guia"] == "G-R-001"
    assert data["hospital"] == "H-Recife"
    assert data["bolsas"] == ["O-NEG-0142"]
    assert data["invocacaoNesteAmbiente"] == 1


def test_demorar_flag_sleeps_five_seconds_and_returns_201(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr(app.time, "sleep", lambda sec: sleep_calls.append(sec))

    event = make_event({"requisicaoId": "R-003", "demorar": True})
    ret = app.lambda_handler(event, "")
    data = json.loads(ret["body"])

    assert sleep_calls == [5]
    assert ret["statusCode"] == 201
    assert data["guia"] == "G-R-003"
    assert data["hospital"] is None
    assert data["bolsas"] == []
    assert data["invocacaoNesteAmbiente"] == 1


def test_malformed_json_returns_400():
    ret = app.lambda_handler(make_event(None, raw_body="{quebrado"), "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 400
    assert ret["headers"]["Content-Type"] == "application/json"
    assert "erro" in data


def test_invalid_base64_returns_400():
    ret = app.lambda_handler(make_event(None, is_base64=True, raw_body="!!!invalid-base64!!!"), "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 400
    assert ret["headers"]["Content-Type"] == "application/json"
    assert "erro" in data


@pytest.mark.parametrize("raw_body", ["null", "[]", "123", '["requisicaoId"]'])
def test_non_object_json_returns_400(raw_body):
    ret = app.lambda_handler(make_event(None, raw_body=raw_body), "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 400
    assert ret["headers"]["Content-Type"] == "application/json"
    assert "erro" in data


@pytest.mark.parametrize("bad_id", [None, 123, "", "   "])
def test_invalid_requisicao_id_value_returns_400(bad_id):
    ret = app.lambda_handler(make_event({"requisicaoId": bad_id, "hospital": "H-Recife"}), "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 400
    assert ret["headers"]["Content-Type"] == "application/json"
    assert "erro" in data


def test_pedido_json_fixture_executes_cleanly():
    event = json.loads((REPO_ROOT / "events" / "pedido.json").read_text(encoding="utf-8"))
    ret = app.lambda_handler(event, "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 201
    assert ret["headers"]["Content-Type"] == "application/json"
    assert data == {
        "guia": "G-R-001",
        "hospital": "H-Recife",
        "bolsas": ["O-NEG-0142"],
        "invocacaoNesteAmbiente": 1,
    }
