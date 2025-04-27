from contextvars import ContextVar
from pathlib import Path

import pytest

from gifnoc.registry import Registry

from .models import Organization

here = Path(__file__).parent


@pytest.fixture
def configs():
    return here / "configs"


@pytest.fixture
def registry():
    return Registry(context_var=ContextVar("active", default=None))


@pytest.fixture
def org(registry):
    return registry.define(
        field="org",
        model=Organization,
        defaults={
            "name": "${env:ORG_NAME}",
            "nonprofit": "${env:NONPROFIT}",
        },
    )
