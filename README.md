
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

@dataclass
class Server:
    port: int = 8080
    host: str = "localhost"
    users: list[User]

server_config = gifnoc.define(
    field="server",
    model=Server,
    environ={
        APP_PORT="port",
        APP_HOST="host",
    }
)

if __name__ == "__main__":
    with gifnoc.cli(
        # Environment variable for the configuration path (defaults to GIFNOC_FILE)
        envvar="APP_CONFIG",
        # Command-line argument for the configuration path (can give multiple)
        config_argument="--config",
        # You can easily register command-line arguments to parts of the configuration
        options_map={"--port": "server.port"},
    ):
        # The `server_config` object will always refer to the `server` key in the
        # current configuration
        print("Port:", server_config.port)
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
