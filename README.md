
# Gifnoc

Gifnoc is a unified configuration system for Python modules.

The main objective of gifnoc is to unify configuration files, environment variables and command-line options, across multiple modules. For example, module A and module B can both define their own configuration models through gifnoc, map some environment variables to keys in that configuration, and then you may configure A and B in the same file.

Gifnoc also aims to validate configuration through a typed model based on dataclasses and implemented by the `serieux` package, a dependency of gifnoc.


## Features

* Typed configuration using dataclasses and `serieux`
* Use a single configuration tree for multiple libraries
* Multiple configuration files can be easily merged
* Easily embed configuration files in each other


## Example

**main.py**

```python
from dataclasses import dataclass, field
import gifnoc

@dataclass
class User:
    name: str
    email: str
    admin: bool

@dataclass
class Server:
    # Server post
    port: int = 8080
    # Server hostname
    host: str = "localhost"
    # List of users
    users: list[User] = field(default_factory=list)

# Define a configuration key
server_config = gifnoc.define("server", Server)

if __name__ == "__main__":
    # Load configuration from the file in $APP_CONFIG, if it exists
    # set_sources overrides any previous configuration
    # Each source can be a dictionary, ${envfile:...}, a Path object
    gifnoc.set_sources("${envfile:APP_CONFIG}")

    # Overlay configuration from environment variables
    # add_overlay adds on top of existing configuration
    gifnoc.add_overlay({
        "server.port": "${env:APP_PORT}",
        "server.host": "${env:APP_HOST}",
    })

    # Overlay configuration with --config, add options with mapping
    # --port will automatically use the type and documentation of Server.port
    gifnoc.cli(mapping={"server.port": "--port"})

    # server_config dynamically updates as sources/overlays are changed
    print("Port:", server_config.port)
    print("Host:", server_config.host)

    # You can apply local changes with a context manager, e.g. for testing:
    with gifnoc.overlay({"server.port": 90909}):
        print("Port:", server_config.port)  # Port: 90909
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
name: Mysterio
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
