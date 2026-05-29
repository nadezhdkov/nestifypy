"""
nestifypy.komodo
--------------
Lombok-style annotation-driven metaprogramming for Python.

Eliminates class boilerplate by generating dunder methods, builders,
accessors, validators, and lifecycle hooks — all via decorators.

Usage:
    from nestifypy.komodo import komodo

    @komodo.data
    class User:
        name: str
        age: int

    @komodo.builder
    class Config:
        host: str = "localhost"
        port: int = 8080
"""

from nestifypy.komodo.core import komodo
from nestifypy.komodo.contract import contract, ContractViolationError
from nestifypy.komodo.inspect import KomodoInspector

__version__ = "0.2.1"

__all__ = [
    "komodo",
    "contract",
    "ContractViolationError",
    "KomodoInspector",
]
