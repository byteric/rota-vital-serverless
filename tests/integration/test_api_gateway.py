import os

import pytest

"""
Execute apenas quando houver uma stack implantada na AWS (Caminho B)
com a variável de ambiente AWS_SAM_STACK_NAME definida.
"""

if not os.environ.get("AWS_SAM_STACK_NAME"):
    pytest.skip(
        "AWS_SAM_STACK_NAME não definida (teste opcional de nuvem / Caminho B)",
        allow_module_level=True,
    )

import boto3  # noqa: E402
import requests  # noqa: E402


class TestApiGateway:

    @pytest.fixture()
    def api_gateway_url(self):
        stack_name = os.environ["AWS_SAM_STACK_NAME"]
        client = boto3.client("cloudformation")
        response = client.describe_stacks(StackName=stack_name)
        stack_outputs = response["Stacks"][0]["Outputs"]
        api_outputs = [output for output in stack_outputs if output["OutputKey"] == "HelloWorldApi"]

        if not api_outputs:
            raise KeyError(f"HelloWorldApi not found in stack {stack_name}")

        return api_outputs[0]["OutputValue"]

    def test_api_gateway_post_guias(self, api_gateway_url):
        response = requests.post(
            api_gateway_url,
            json={"requisicaoId": "R-INT-001", "hospital": "H-Recife"},
            timeout=10,
        )

        assert response.status_code == 201
        assert response.json()["guia"] == "G-R-INT-001"
