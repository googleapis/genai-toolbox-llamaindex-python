# GenAI Toolbox SDK

This SDK allows you to seamlessly integrate the functionalities of
[Toolbox](https://github.com/googleapis/genai-toolbox) into your LLM
applications, enabling advanced orchestration and interaction with GenAI models.

<!-- TOC ignore:true -->
## Table of Contents
<!-- TOC -->

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Loading Tools](#loading-tools)
    - [Load a toolset](#load-a-toolset)
    - [Load a single tool](#load-a-single-tool)
- [Use with LlamaIndex](#use-with-llamaindex)
- [Manual usage](#manual-usage)
- [Authenticating Tools](#authenticating-tools)
    - [Supported Authentication Mechanisms](#supported-authentication-mechanisms)
    - [Configure Tools](#configure-tools)
    - [Configure SDK](#configure-sdk)
        - [Add An Auth Token to a Tool](#add-an-auth-token-to-a-tool)
        - [Add An Auth Token While Loading](#add-an-auth-token-while-loading)
    - [Complete Example](#complete-example)
- [Binding Parameter Values](#binding-parameter-values)
    - [Binding Parameters to a Tool](#binding-parameters-to-a-tool)
    - [Binding Parameters While Loading](#binding-parameters-while-loading)
    - [Binding Dynamic Values](#binding-dynamic-values)
- [Error Handling](#error-handling)

<!-- /TOC -->

## Installation

> [!IMPORTANT]
> This SDK is not yet available on PyPI. For now, install it from source by
> following these [installation instructions](DEVELOPER.md).

You can install the Toolbox SDK for LlamaIndex using `pip`.

```bash
pip install toolbox-llamaindex
```

## Quickstart

Here's a minimal example to get you started:

```py
from llama_index.llms.vertex import Vertex
from llama_index.core.agent import ReActAgent
from toolbox_llamaindex import ToolboxClient

toolbox = ToolboxClient("http://127.0.0.1:5000")
tools = toolbox.load_toolset()

model = Vertex(model="gemini-1.5-pro-002")
agent = ReActAgent.from_tools(tools, llm=model, verbose=True)
response = agent.query("Get some response from the agent.")
print(response)
```

## Usage

Import and initialize the toolbox client.

```py
from toolbox_llamaindex import ToolboxClient

# Replace with your Toolbox service's URL
toolbox = ToolboxClient("http://127.0.0.1:5000")
```

## Loading Tools

### Load a toolset

A toolset is a collection of related tools. You can load all tools in a toolset
or a specific one:

```py
# Load all tools
tools = toolbox.load_toolset()

# Load a specific toolset
tools = toolbox.load_toolset("my-toolset")
```

### Load a single tool

```py
tool = toolbox.load_tool("my-tool")
```

Loading individual tools gives you finer-grained control over which tools are
available to your LLM agent.

## Use with LlamaIndex

LlamaIndex's agents can dynamically choose and execute tools based on the user
input. Include tools loaded from the Toolbox SDK in the agent's toolkit:

```py
from llama_index.llms.vertex import Vertex
from llama_index.core.agent import ReActAgent

model = Vertex(model="gemini-1.5-pro-002")

# Initialize agent with tools
agent = ReActAgent.from_tools(tools, llm=model, verbose=True)

# Query the agent
response = agent.query("Get some response from the agent.")
```

## Manual usage

Execute a tool manually using the `call` method:

```py
result = tools[0].call({"name": "Alice", "age": 30})
```

This is useful for testing tools or when you need precise control over tool
execution outside of an agent framework.

## Authenticating Tools

> [!WARNING]
> Always use HTTPS to connect your application with the Toolbox service,
> especially when using tools with authentication configured. Using HTTP exposes
> your application to serious security risks.

Some tools require user authentication to access sensitive data.

### Supported Authentication Mechanisms
Toolbox currently supports authentication using the [OIDC
protocol](https://openid.net/specs/openid-connect-core-1_0.html) with [ID
tokens](https://openid.net/specs/openid-connect-core-1_0.html#IDToken) (not
access tokens) for [Google OAuth
2.0](https://cloud.google.com/apigee/docs/api-platform/security/oauth/oauth-home).

### Configure Tools

Refer to [these
instructions](../../docs/tools/README.md#authenticated-parameters) on
configuring tools for authenticated parameters.

### Configure SDK

You need a method to retrieve an ID token from your authentication service:

```py
async def get_auth_token():
    # ... Logic to retrieve ID token (e.g., from local storage, OAuth flow)
    # This example just returns a placeholder. Replace with your actual token retrieval.
    return "YOUR_ID_TOKEN" # Placeholder
```

#### Add an Auth Token to a Tool

```py
toolbox = ToolboxClient("http://127.0.0.1:5000")
tools = toolbox.load_toolset()

auth_tool = tools[0].add_auth_token("my_auth", get_auth_token) # Single token

multi_auth_tool = tools[0].add_auth_tokens({"my_auth", get_auth_token}) # Multiple tokens

# OR

auth_tools = [tool.add_auth_token("my_auth", get_auth_token) for tool in tools]
```

#### Add an Auth Token While Loading

```py
auth_tool = toolbox.load_tool(auth_tokens={"my_auth": get_auth_token})

auth_tools = toolbox.load_toolset(auth_tokens={"my_auth": get_auth_token})
```

> [!NOTE]
> Adding auth tokens during loading only affect the tools loaded within
> that call.

### Complete Example

```py
import asyncio
from toolbox_llamaindex import ToolboxClient

async def get_auth_token():
    # ... Logic to retrieve ID token (e.g., from local storage, OAuth flow)
    # This example just returns a placeholder. Replace with your actual token retrieval.
    return "YOUR_ID_TOKEN" # Placeholder

toolbox = ToolboxClient("http://127.0.0.1:5000")
tool = toolbox.load_tool("my-tool")

auth_tool = tool.add_auth_token("my_auth", get_auth_token)
result = auth_tool.call({"input": "some input"})
print(result)
```

## Binding Parameter Values

Predetermine values for tool parameters using the SDK. These values won't be
modified by the LLM. This is useful for:

* **Protecting sensitive information:**  API keys, secrets, etc.
* **Enforcing consistency:** Ensuring specific values for certain parameters.
* **Pre-filling known data:**  Providing defaults or context.

### Binding Parameters to a Tool

```py
toolbox = ToolboxClient("http://127.0.0.1:5000")
tools = toolbox.load_toolset()

bound_tool = tool[0].bind_param("param", "value") # Single param

multi_bound_tool = tools[0].bind_params({"param1": "value1", "param2": "value2"}) # Multiple params

# OR

bound_tools = [tool.bind_param("param", "value") for tool in tools]
```

### Binding Parameters While Loading

```py
bound_tool = toolbox.load_tool(bound_params={"param": "value"})

bound_tools = toolbox.load_toolset(bound_params={"param": "value"})
```

> [!NOTE]
> Bound values during loading only affect the tools loaded in that call.

### Binding Dynamic Values

Use a function to bind dynamic values:

```py
def get_dynamic_value():
  # Logic to determine the value
  return "dynamic_value"

dynamic_bound_tool = tool.bind_param("param", get_dynamic_value)
```

> [!IMPORTANT]
> You don't need to modify tool configurations to bind parameter values.

## Asynchronous Usage

For better performance through [cooperative
multitasking](https://en.wikipedia.org/wiki/Cooperative_multitasking), you can
use the asynchronous interfaces of the `ToolboxClient`.

> [!Note]
> Asynchronous interfaces like `aload_tool` and `aload_toolset` require an
> asynchronous environment. For guidance on running asynchronous Python
> programs, see [asyncio
> documentation](https://docs.python.org/3/library/asyncio-runner.html#running-an-asyncio-program).

```py
import asyncio
from toolbox_llamaindex import ToolboxClient

async def main():
    toolbox = ToolboxClient("http://127.0.0.1:5000")
    tool = await toolbox.aload_tool("my-tool")
    tools = await toolbox.aload_toolset()
    response = await tool.ainvoke()

if __name__ == "__main__":
    asyncio.run(main())
```