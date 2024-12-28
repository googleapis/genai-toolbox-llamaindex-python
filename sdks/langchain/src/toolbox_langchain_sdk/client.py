import asyncio
from typing import Any, Callable, Optional, Type
from warnings import warn

from aiohttp import ClientSession
from deprecated import deprecated
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from .utils import ManifestSchema, _invoke_tool, _load_yaml, _schema_to_model


class ToolboxClient:
    def __init__(self, url: str, session: Optional[ClientSession] = None):
        """
        Initializes the ToolboxClient for the Toolbox service at the given URL.

        Args:
            url: The base URL of the Toolbox service.
            session: The HTTP client session.
                Default: None
        """
        self._url: str = url
        self._should_close_session: bool = session != None
        self._session: ClientSession = session or ClientSession()

    async def close(self) -> None:
        """
        Close the Toolbox client and its tools.
        """
        # We check whether _should_close_session is set or not since we do not
        # want to close the session in case the user had passed their own
        # ClientSession object, since then we expect the user to be owning its
        # lifecycle.
        if self._session and self._should_close_session:
            await self._session.close()

    def __del__(self):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
            else:
                loop.run_until_complete(self.close())
        except Exception:
            # We "pass" assuming that the exception is thrown because  the event
            # loop is no longer running, but at that point the Session should
            # have been closed already anyway.
            pass

    async def _load_tool_manifest(self, tool_name: str) -> ManifestSchema:
        """
        Fetches and parses the YAML manifest for the given tool from the Toolbox
        service.

        Args:
            tool_name: The name of the tool to load.

        Returns:
            The parsed Toolbox manifest.
        """
        url = f"{self._url}/api/tool/{tool_name}"
        return await _load_yaml(url, self._session)

    async def _load_toolset_manifest(
        self, toolset_name: Optional[str] = None
    ) -> ManifestSchema:
        """
        Fetches and parses the YAML manifest from the Toolbox service.

        Args:
            toolset_name: The name of the toolset to load.
                Default: None. If not provided, then all the available tools are
                loaded.

        Returns:
            The parsed Toolbox manifest.
        """
        url = f"{self._url}/api/toolset/{toolset_name or ''}"
        return await _load_yaml(url, self._session)

    def _generate_tool(
        self, tool_name: str, manifest: ManifestSchema
    ) -> StructuredTool:
        """
        Creates a StructuredTool object and a dynamically generated BaseModel
        for the given tool.

        Args:
            tool_name: The name of the tool to generate.
            manifest: The parsed Toolbox manifest.

        Returns:
            The generated tool.
        """
        tool_schema = manifest.tools[tool_name]
        tool_model: BaseModel = _schema_to_model(
            model_name=tool_name, schema=tool_schema.parameters
        )

        async def _tool_func(**kwargs) -> dict:
            return await _invoke_tool(self._url, self._session, tool_name, kwargs)

        return StructuredTool.from_function(
            coroutine=_tool_func,
            name=tool_name,
            description=tool_schema.description,
            args_schema=tool_model,
        )

    def _process_auth_params(self, manifest: ManifestSchema) -> None:
        """
        Extracts parameters requiring authentication from the manifest.
        Verifies each parameter has at least one valid auth source.

        Args:
            manifest: The manifest to validate and modify.

        Warns:
            UserWarning: If a parameter in the manifest has no valid sources.
        """
        for tool_name, tool_schema in manifest.tools.items():
            non_auth_params = []
            for param in tool_schema.parameters:

                # Extract auth params from the tool schema.
                #
                # These parameters are removed from the manifest to prevent data
                # validation errors since their values are inferred by the
                # Toolbox service, not provided by the user.
                #
                # Store the permitted authentication sources for each parameter
                # in '_tool_param_auth' for efficient validation in
                # '_validate_auth'.
                if not param.authSources:
                    non_auth_params.append(param)
                    continue

                self._tool_param_auth.setdefault(tool_name, {})[
                    param.name
                ] = param.authSources

            tool_schema.parameters = non_auth_params

            # If none of the permitted auth sources of a parameter are
            # registered, raise a warning message to the user.
            if not self._validate_auth(tool_name):
                warn(
                    f"Some parameters of tool {tool_name} require authentication, but no valid auth sources are registered. Please register the required sources before use."
                )

    @deprecated("Please use `add_auth_token` instead.")
    def add_auth_header(
        self, auth_source: str, get_id_token: Callable[[], str]
    ) -> None:
        self.add_auth_token(auth_source, get_id_token)

    def add_auth_token(self, auth_source: str, get_id_token: Callable[[], str]) -> None:
        """
        Registers a function to retrieve an ID token for a given authentication
        source.

        Args:
            auth_source : The name of the authentication source.
            get_id_token: A function that returns the ID token.
        """
        self._id_token_getters[auth_source] = get_id_token

    async def load_tool(
        self,
        tool_name: str,
        auth_tokens: dict[str, Callable[[], str]] = {},
        auth_headers: Optional[dict[str, Callable[[], str]]] = None,
    ) -> StructuredTool:
        """
        Loads the tool, with the given tool name, from the Toolbox service.

        Args:
            tool_name: The name of the tool to load.
            auth_tokens: A mapping of authentication source names to
                functions that retrieve ID tokens. If provided, these will
                override or be added to the existing ID token getters.
                Default: Empty.

        Returns:
            A tool loaded from the Toolbox
        """
        if auth_headers:
            if auth_tokens:
                warn(
                    "Both `auth_tokens` and `auth_headers` are provided. `auth_headers` is deprecated, and `auth_tokens` will be used.",
                    DeprecationWarning,
                )
            else:
                warn(
                    "Argument `auth_headers` is deprecated. Use `auth_tokens` instead.",
                    DeprecationWarning,
                )
                auth_tokens = auth_headers

        for auth_source, get_id_token in auth_tokens.items():
            self.add_auth_token(auth_source, get_id_token)

        manifest: ManifestSchema = await self._load_tool_manifest(tool_name)
        return self._generate_tool(tool_name, manifest)

    async def load_toolset(
        self,
        toolset_name: Optional[str] = None,
        auth_tokens: dict[str, Callable[[], str]] = {},
        auth_headers: Optional[dict[str, Callable[[], str]]] = None,
    ) -> list[StructuredTool]:
        """
        Loads tools from the Toolbox service, optionally filtered by toolset
        name.

        Args:
            toolset_name: The name of the toolset to load.
                Default: None. If not provided, then all the tools are loaded.
            auth_tokens: A mapping of authentication source names to
                functions that retrieve ID tokens. If provided, these will
                override or be added to the existing ID token getters.
                Default: Empty.

        Returns:
            A list of all tools loaded from the Toolbox.
        """
        if auth_headers:
            if auth_tokens:
                warn(
                    "Both `auth_tokens` and `auth_headers` are provided. `auth_headers` is deprecated, and `auth_tokens` will be used.",
                    DeprecationWarning,
                )
            else:
                warn(
                    "Argument `auth_headers` is deprecated. Use `auth_tokens` instead.",
                    DeprecationWarning,
                )
                auth_tokens = auth_headers

        for auth_source, get_id_token in auth_tokens.items():
            self.add_auth_token(auth_source, get_id_token)

        tools: list[StructuredTool] = []
        manifest: ManifestSchema = await self._load_toolset_manifest(toolset_name)
        for tool_name in manifest.tools:
            tools.append(self._generate_tool(tool_name, manifest))
        return tools
