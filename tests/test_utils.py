# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import json
import re
import warnings
from typing import Union
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from pydantic import BaseModel

from toolbox_llamaindex.utils import (
    ParameterSchema,
    _convert_none_to_empty_string,
    _get_auth_headers,
    _invoke_tool,
    _load_manifest,
    _parse_type,
    _schema_to_model,
)

URL = "https://my-toolbox.com/test"
MOCK_MANIFEST = """
{
  "serverVersion": "0.0.1",
  "tools": {
    "test_tool": {
      "summary": "Test Tool",
      "description": "This is a test tool.",
      "parameters": [
        {
          "name": "param1",
          "type": "string",
          "description": "Parameter 1"
        },
        {
          "name": "param2",
          "type": "integer",
          "description": "Parameter 2"
        }
      ]
    }
  }
}
"""


class TestUtils:
    @pytest.fixture(scope="module")
    def mock_manifest(self):
        return aiohttp.ClientResponse(
            method="GET",
            url=aiohttp.client.URL(URL),
            writer=None,
            continue100=None,
            timer=None,
            request_info=None,
            traces=None,
            session=None,
            loop=asyncio.get_event_loop(),
        )

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_load_manifest(self, mock_get, mock_manifest):
        mock_manifest.raise_for_status = Mock()
        mock_manifest.text = AsyncMock(return_value=MOCK_MANIFEST)

        mock_get.return_value = mock_manifest
        session = aiohttp.ClientSession()
        manifest = await _load_manifest(URL, session)
        await session.close()
        mock_get.assert_called_once_with(URL)

        assert manifest.serverVersion == "0.0.1"
        assert len(manifest.tools) == 1

        tool = manifest.tools["test_tool"]
        assert tool.description == "This is a test tool."
        assert tool.parameters == [
            ParameterSchema(name="param1", type="string", description="Parameter 1"),
            ParameterSchema(name="param2", type="integer", description="Parameter 2"),
        ]

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_load_manifest_invalid_json(self, mock_get, mock_manifest):
        mock_manifest.raise_for_status = Mock()
        mock_manifest.text = AsyncMock(return_value="{ invalid manifest")
        mock_get.return_value = mock_manifest

        with pytest.raises(Exception) as e:
            session = aiohttp.ClientSession()
            await _load_manifest(URL, session)

        mock_get.assert_called_once_with(URL)
        assert isinstance(e.value, json.JSONDecodeError)
        assert (
            str(e.value)
            == "Failed to parse JSON from https://my-toolbox.com/test: Expecting property name enclosed in double quotes: line 1 column 3 (char 2): line 1 column 3 (char 2)"
        )

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_load_manifest_invalid_manifest(self, mock_get, mock_manifest):
        mock_manifest.raise_for_status = Mock()
        mock_manifest.text = AsyncMock(return_value='{ "something": "invalid" }')
        mock_get.return_value = mock_manifest

        with pytest.raises(Exception) as e:
            session = aiohttp.ClientSession()
            await _load_manifest(URL, session)

        mock_get.assert_called_once_with(URL)
        assert isinstance(e.value, ValueError)
        assert re.match(
            r"Invalid JSON data from https://my-toolbox.com/test: 2 validation errors for ManifestSchema\nserverVersion\n  Field required \[type=missing, input_value={'something': 'invalid'}, input_type=dict]\n    For further information visit https://errors.pydantic.dev/\d+\.\d+/v/missing\ntools\n  Field required \[type=missing, input_value={'something': 'invalid'}, input_type=dict]\n    For further information visit https://errors.pydantic.dev/\d+\.\d+/v/missing",
            str(e.value),
        )

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_load_manifest_api_error(self, mock_get, mock_manifest):
        error = aiohttp.ClientError("Simulated HTTP Error")
        mock_manifest.raise_for_status = Mock()
        mock_manifest.text = AsyncMock(side_effect=error)
        mock_get.return_value = mock_manifest

        with pytest.raises(aiohttp.ClientError) as exc_info:
            session = aiohttp.ClientSession()
            await _load_manifest(URL, session)
        mock_get.assert_called_once_with(URL)
        assert exc_info.value == error

    def test_schema_to_model(self):
        schema = [
            ParameterSchema(name="param1", type="string", description="Parameter 1"),
            ParameterSchema(name="param2", type="integer", description="Parameter 2"),
        ]
        model = _schema_to_model("TestModel", schema)
        assert issubclass(model, BaseModel)

        assert model.model_fields["param1"].annotation == str
        assert model.model_fields["param1"].description == "Parameter 1"
        assert model.model_fields["param2"].annotation == int
        assert model.model_fields["param2"].description == "Parameter 2"

    def test_schema_to_model_empty(self):
        model = _schema_to_model("TestModel", [])
        assert issubclass(model, BaseModel)
        assert len(model.model_fields) == 0

    @pytest.mark.parametrize(
        "parameter_schema, expected_type",
        [
            (ParameterSchema(name="foo", description="bar", type="string"), str),
            (ParameterSchema(name="foo", description="bar", type="integer"), int),
            (ParameterSchema(name="foo", description="bar", type="float"), float),
            (ParameterSchema(name="foo", description="bar", type="boolean"), bool),
            (
                ParameterSchema(
                    name="foo",
                    description="bar",
                    type="array",
                    items=ParameterSchema(
                        name="foo", description="bar", type="integer"
                    ),
                ),
                list[int],
            ),
        ],
    )
    def test_parse_type(self, parameter_schema, expected_type):
        assert _parse_type(parameter_schema) == expected_type

    @pytest.mark.parametrize(
        "fail_parameter_schema",
        [
            (ParameterSchema(name="foo", description="bar", type="invalid")),
            (
                ParameterSchema(
                    name="foo",
                    description="bar",
                    type="array",
                    items=ParameterSchema(
                        name="foo", description="bar", type="invalid"
                    ),
                )
            ),
        ],
    )
    def test_parse_type_invalid(self, fail_parameter_schema):
        with pytest.raises(ValueError):
            _parse_type(fail_parameter_schema)

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_invoke_tool(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"key": "value"})
        mock_post.return_value.__aenter__.return_value = mock_response

        result = await _invoke_tool(
            "http://localhost:8000",
            aiohttp.ClientSession(),
            "tool_name",
            {"input": "data"},
            {},
        )

        mock_post.assert_called_once_with(
            "http://localhost:8000/api/tool/tool_name/invoke",
            json=_convert_none_to_empty_string({"input": "data"}),
            headers={},
        )
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_invoke_tool_unsecure_with_auth(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"key": "value"})
        mock_post.return_value.__aenter__.return_value = mock_response

        with pytest.warns(
            UserWarning,
            match="Sending ID token over HTTP. User data may be exposed. Use HTTPS for secure communication.",
        ):
            result = await _invoke_tool(
                "http://localhost:8000",
                aiohttp.ClientSession(),
                "tool_name",
                {"input": "data"},
                {"my_test_auth": lambda: "fake_id_token"},
            )

        mock_post.assert_called_once_with(
            "http://localhost:8000/api/tool/tool_name/invoke",
            json=_convert_none_to_empty_string({"input": "data"}),
            headers={"my_test_auth_token": "fake_id_token"},
        )
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_invoke_tool_secure_with_auth(self, mock_post):
        session = aiohttp.ClientSession()
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"key": "value"})
        mock_post.return_value.__aenter__.return_value = mock_response

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = await _invoke_tool(
                "https://localhost:8000",
                session,
                "tool_name",
                {"input": "data"},
                {"my_test_auth": lambda: "fake_id_token"},
            )

        mock_post.assert_called_once_with(
            "https://localhost:8000/api/tool/tool_name/invoke",
            json=_convert_none_to_empty_string({"input": "data"}),
            headers={"my_test_auth_token": "fake_id_token"},
        )
        assert result == {"key": "value"}

    def test_convert_none_to_empty_string(self):
        input_dict = {"a": None, "b": 123}
        expected_output = {"a": "", "b": 123}
        assert _convert_none_to_empty_string(input_dict) == expected_output

    def test_get_auth_headers_deprecation_warning(self):
        """Test _get_auth_headers deprecation warning."""
        with pytest.warns(
            DeprecationWarning,
            match=r"Call to deprecated function \(or staticmethod\) _get_auth_headers\. \(Please use `_get_auth_tokens` instead\.\)$",
        ):
            _get_auth_headers({"auth_source1": lambda: "test_token"})
