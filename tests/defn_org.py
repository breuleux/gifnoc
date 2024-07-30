import gifnoc

from .models import Organization

gifnoc.define(
    field="org",
    model=Organization,
)
