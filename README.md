# Toolbox LLamaIndex SDK

This SDK allows you to seamlessly integrate the functionalities of
[Toolbox](https://github.com/googleapis/genai-toolbox) into your LLM
applications, enabling advanced orchestration and interaction with GenAI models.

## Table of Contents

## Getting Started

### Installing the server
<!-- {x-release-please-start-version} -->
For the latest version, check the [releases page][releases] and use the
following instructions for your OS and CPU architecture.

<details open>
<summary>Binary</summary>


[releases]: https://github.com/googleapis/genai-toolbox/releases

```sh
# see releases page for other versions
curl https://storage.googleapis.com/genai-toolbox/v0.0.1/linux/amd64/toolbox
chmod +x toolbox
```

</details>

<details>
<summary>Container Images</summary>
You can also install Toolbox as a container: 

```sh
# see releases page for other versions
docker pull us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:$VERSION
```
</details>

<details>
<summary>Compile from source</summary>

To install from source, ensure you have the latest version of 
[Go installed](https://go.dev/doc/install).

```sh
go install github.com/googleapis/genai-toolbox@v0.0.1
```
</details>
<!-- {x-release-please-end} -->

### Running the server
[Configure](#configuration) a `tools.yaml` to define your tools, and then execute `toolbox` to
start the server:

```sh
./toolbox --tools_file "tools.yaml"
```

You can use `toolbox help` for a full list of flags! 

### Using with Client SDKs

Once your server is up and running, you can load the tools into your
application. See below the list of Client SDKs for using various frameworks:

<details open>
<summary>LangChain / LangGraph</summary>
Once you've installed the Toolbox LangChain SDK, you can load tools: 

```python
from toolbox_langchain_sdk import ToolboxClient

# update the url to point to your server
client = ToolboxClient("http://127.0.0.1:5000")

# these tools can be passed to your application! 
tools = await client.load_toolset()
```

</details>

<details open>

<summary>LlamaIndex</summary>
Once you've installed the Toolbox LlamaIndex SDK, you can load tools: 

```python
from toolbox_llamaindex_sdk import ToolboxClient

# update the url to point to your server
client = ToolboxClient("http://127.0.0.1:5000")

# these tools can be passed to your application! 
tools = await client.load_toolset()
```

</details>

## Configuration

You can configure what tools are available by updating the `tools.yaml` file. If
you have multiple files, you can tell toolbox which to load with the
`--tools_file tools.yaml` flag. 

### Sources

The `sources` section of your `tools.yaml` defines what data sources your
Toolbox should have access to. Most tools will have at least one source to
execute against.

```yaml
sources:
    my-cloud-sql-source:
        kind: cloud-sql-postgres
        project: my-project-name
        region: us-central1
        instance: my-instance-name
        user: my-user
        password: my-password
        database: my_db
```

For more details on configuring different types of sources, see the [Source
documentation.](docs/sources/README.md)


### Tools

The `tools` section of your `tools.yaml` define your tools: what kind of tool it
is, which source it affects, what parameters it takes, etc. 

```yaml
tools:
    get_flight_by_id:
        kind: postgres-sql
        source: my-pg-instance
        description: >
            Use this tool to list all airports matching search criteria. Takes 
            at least one of country, city, name, or all and returns all matching
            airports. The agent can decide to return the results directly to 
            the user.
        statement: "SELECT * FROM flights WHERE id = $1"
        parameters:
        - name: id
            type: int
            description: 'id' represents the unique ID for each flight. 
```


### Toolsets

The `toolsets` section of your `tools.yaml` allows you to define groups of tools
that you want to be able to load together. This can be useful for defining
different groups based on agent or application. 

```yaml
toolsets:
    my_first_toolset:
        - my_first_tool
        - my_second_tool
    my_second_toolset:
        - my_second_tool
        - my_third_tool
```

You can load toolsets by name:
```python
# This will load all tools
all_tools = await client.load_toolset()

# This will only load the tools listed in 'my_second_toolset'
my_second_toolset = await client.load_toolset("my_second_toolset")
```


## Versioning

This project uses [semantic versioning](https://semver.org/), and uses the
following lifecycle regarding support for a major version.

## Contributing

Contributions to this library are always welcome and highly encouraged.

See [CONTRIBUTING](CONTRIBUTING.md) for more information how to get started.

Please note that this project is released with a Contributor Code of Conduct. By participating in
this project you agree to abide by its terms. See [Code of Conduct](CODE_OF_CONDUCT.md) for more
information.

## License

Apache 2.0 - See [LICENSE](LICENSE) for more information.