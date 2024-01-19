
# Gifnoc

Gifnoc is a unified configuration system for Python modules.

The main objective of gifnoc is to unify configuration files, environment variables and command-line options, across multiple modules. For example, module A and module B can both define their own configuration models through gifnoc, map some environment variables to keys in that configuration, and then you may configure A and B in the same file.

Gifnoc also aims to validate configuration through a typed model based on dataclasses and implemented by the `apischema` package, a dependency of gifnoc.


## Features

* Typed configuration using dataclasses and `apischema`
* Use a single configuration tree for multiple libraries
* Multiple configuration files can be easily merged
* Easily embed configuration files in each other


## Example

**main.py**

```python
from dataclasses import dataclass
import gifnoc

@dataclass
class User:
    name: str
    email: str
    admin: bool

# The dataclass for the 'server' key in the configuration
@gifnoc.register("server")
@dataclass
class Server:
    port: int = 8080
    host: str = "localhost"
    users: list[User]

# Synchronize a few environment variables to specific configuration values
gifnoc.map_environment_variables(
    APP_PORT="server.port",
    APP_HOST="server.host",
)

# Easily import the server configuration from gifnoc
from gifnoc.config import server as server_config

if __name__ == "__main__":
    with gifnoc.gifnoc(
        # Environment variable for the configuration path
        envvar="APP_CONFIG",
        # Command-line argument for the configuration path (can give multiple)
        config_argument="--config",
        # You can easily register command-line arguments to parts of the configuration
        options_map={"--port": "server.port"},
    ):
        # The `server_config` object will always refer to the `server` key in the
        # current configuration
        print(server_config.port)
```


**config.yaml**

```yaml
server:
  port: 1234
  host: here
  users:
    - name: Olivier
      email: ob@here
      admin: true
    # You can write a file path instead of an object
    - mysterio.yaml
```


**mysterio.yaml**

```yaml
- name: Mysterio
  email: me@myster.io
  admin: false
```


**Usage:**

```bash
python main.py --config config.yaml
APP_CONFIG=config.yaml python main.py
APP_PORT=8903 python main.py --config config.yaml
python main.py --config config.yaml --port 8903
```
