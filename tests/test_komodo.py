"""
tests/test_komodo.py
------------------
Full test suite for nestifypy.komodo

Run with:  python -m pytest tests/test_komodo.py -v
Or simply: python tests/test_komodo.py
"""

from __future__ import annotations

import sys
import os

# ── path setup (adjust if running from repo root) ────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from nestifypy.komodo import komodo, contract, KomodoInspector
from nestifypy.komodo.contract import requires, ensures, invariant, ContractViolationError

import traceback

_PASS = "\033[92m✓\033[0m"
_FAIL = "\033[91m✗\033[0m"
_results: list[tuple[str, bool, str]] = []


def test(name: str):
    def decorator(fn):
        try:
            fn()
            _results.append((name, True, ""))
            print(f"  {_PASS} {name}")
        except Exception as e:
            _results.append((name, False, str(e)))
            print(f"  {_FAIL} {name}")
            traceback.print_exc()
    return decorator


print("\n\033[1m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
print("\033[1m  nestifypy.komodo  —  test suite\033[0m")
print("\033[1m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n")

# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.constructor
# ─────────────────────────────────────────────────────────────────────────────
print("  @komodo.constructor")

@test("generates __init__ from annotations")
def _():
    @komodo.constructor
    class Point:
        x: float
        y: float

    p = Point(1.0, 2.0)
    assert p.x == 1.0
    assert p.y == 2.0


@test("respects default values")
def _():
    @komodo.constructor
    class Server:
        host: str
        port: int = 8080

    s = Server("localhost")
    assert s.host == "localhost"
    assert s.port == 8080

    s2 = Server("0.0.0.0", 443)
    assert s2.port == 443


@test("raises on missing required field")
def _():
    @komodo.constructor
    class DB:
        url: str
        name: str

    try:
        DB(url="sqlite:///test.db")
        assert False, "Should have raised TypeError"
    except TypeError:
        pass


@test("calls __post_init__ if defined")
def _():
    @komodo.constructor
    class Config:
        value: int

        def __post_init__(self):
            self.value_doubled = self.value * 2

    c = Config(21)
    assert c.value_doubled == 42


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.data
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.data")

@test("generates __repr__")
def _():
    @komodo.data
    class Tag:
        name: str

    t = Tag("python")
    assert repr(t) == "Tag(name='python')"


@test("generates __eq__")
def _():
    @komodo.data
    class Color:
        r: int
        g: int
        b: int

    assert Color(255, 0, 0) == Color(255, 0, 0)
    assert Color(255, 0, 0) != Color(0, 0, 255)


@test("generates __hash__")
def _():
    @komodo.data
    class Coord:
        lat: float
        lon: float

    s = {Coord(1.0, 2.0), Coord(1.0, 2.0), Coord(3.0, 4.0)}
    assert len(s) == 2


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.value
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.value")

@test("is immutable after construction")
def _():
    @komodo.value
    class Money:
        amount: float
        currency: str

    m = Money(9.99, "USD")
    try:
        m.amount = 1.0
        assert False, "Should have raised AttributeError"
    except AttributeError:
        pass


@test("supports equality by value")
def _():
    @komodo.value
    class UUID:
        value: str

    assert UUID("abc") == UUID("abc")
    assert UUID("abc") != UUID("xyz")


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.builder
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.builder")

@test("fluent builder constructs instance")
def _():
    @komodo.builder
    class Request:
        url: str
        method: str = "GET"
        timeout: float = 30.0

    req = (
        Request.Builder()
        .with_url("https://api.example.com")
        .with_method("POST")
        .with_timeout(10.0)
        .build()
    )
    assert req.url == "https://api.example.com"
    assert req.method == "POST"
    assert req.timeout == 10.0


@test("builder raises on missing required field")
def _():
    @komodo.builder
    class Payload:
        body: str

    try:
        Payload.Builder().build()
        assert False, "Should raise ValueError"
    except ValueError:
        pass


@test("builder() factory method works")
def _():
    @komodo.builder
    class Item:
        name: str = "unnamed"

    item = Item.builder().with_name("sword").build()
    assert item.name == "sword"


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.logger
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.logger")

@test("injects logger attribute")
def _():
    import logging

    @komodo.logger
    class Service:
        pass

    assert hasattr(Service, "logger")
    assert isinstance(Service.logger, logging.Logger)
    assert "Service" in Service.logger.name


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.non_null
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.non_null")

@test("raises ValueError on None positional arg")
def _():
    @komodo.non_null
    @komodo.constructor
    class User:
        name: str
        email: str

    try:
        User(None, "x@y.z")
        assert False
    except ValueError:
        pass


@test("raises ValueError on None keyword arg")
def _():
    @komodo.non_null
    @komodo.constructor
    class User:
        name: str
        email: str

    try:
        User(name="Alice", email=None)
        assert False
    except ValueError:
        pass


@test("passes when all args are non-null")
def _():
    @komodo.non_null
    @komodo.constructor
    class User:
        name: str

    u = User("Alice")
    assert u.name == "Alice"


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.singleton
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.singleton")

@test("returns same instance on multiple calls")
def _():
    @komodo.singleton
    class AppConfig:
        pass

    a = AppConfig()
    b = AppConfig()
    assert a is b


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.copyable
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.copyable")

@test("copy() returns a shallow duplicate")
def _():
    @komodo.copyable
    @komodo.data
    class Config:
        host: str = "localhost"
        port: int = 8080

    a = Config()
    b = a.copy()
    assert a == b
    assert a is not b


@test("copy_with() produces modified copy")
def _():
    @komodo.copyable
    @komodo.data
    class Config:
        host: str = "localhost"
        port: int = 8080

    base = Config()
    prod = base.copy_with(host="prod.server.com", port=443)
    assert prod.host == "prod.server.com"
    assert prod.port == 443
    assert base.host == "localhost"  # original unchanged


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.validated
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.validated")

@test("raises TypeError on wrong type")
def _():
    @komodo.validated
    @komodo.constructor
    class TypedPoint:
        x: float
        y: float

    raised = False
    try:
        TypedPoint("not_a_float", 1.0)
    except TypeError:
        raised = True
    assert raised, "Expected TypeError was not raised"


@test("passes on correct types")
def _():
    @komodo.validated
    @komodo.constructor
    class TypedPoint2:
        x: float
        y: float

    p = TypedPoint2(1.0, 2.0)
    assert p.x == 1.0


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.observable
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.observable")

@test("notifies listeners on field change")
def _():
    @komodo.observable
    @komodo.constructor
    class Settings:
        theme: str = "dark"

    changes = []
    s = Settings()
    s.on_change(lambda f, old, new: changes.append((f, old, new)))
    s.theme = "light"

    assert len(changes) == 1
    assert changes[0] == ("theme", "dark", "light")


@test("off_change removes listener")
def _():
    @komodo.observable
    @komodo.constructor
    class Model:
        value: int = 0

    calls = []
    cb = lambda f, o, n: calls.append(n)

    m = Model()
    m.on_change(cb)
    m.value = 1
    m.off_change(cb)
    m.value = 2

    assert calls == [1]


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.sealed
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.sealed")

@test("prevents subclassing")
def _():
    @komodo.sealed
    class Token:
        pass

    try:
        class JwtToken(Token):
            pass
        assert False, "Should raise TypeError"
    except TypeError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  @komodo.deprecated
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @komodo.deprecated")

@test("emits DeprecationWarning on instantiation")
def _():
    import warnings

    @komodo.deprecated(reason="Use NewUser instead", since="2.0")
    class OldUser:
        pass

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        OldUser()
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "2.0" in str(w[0].message)


# ─────────────────────────────────────────────────────────────────────────────
#  @contract
# ─────────────────────────────────────────────────────────────────────────────
print("\n  @contract")

@test("requires() blocks invalid input")
def _():
    @contract(
        requires(lambda x: x > 0, "x must be positive"),
    )
    def sqrt(x: float) -> float:
        return x ** 0.5

    try:
        sqrt(-1.0)
        assert False
    except ContractViolationError as e:
        assert e.kind == "precondition"


@test("ensures() validates return value")
def _():
    @contract(
        ensures(lambda r: r >= 0, "result must be non-negative"),
    )
    def broken() -> float:
        return -1.0

    try:
        broken()
        assert False
    except ContractViolationError as e:
        assert e.kind == "postcondition"


@test("invariant() checked before and after")
def _():
    class BankAccount:
        def __init__(self, balance: float):
            self.balance = balance

        @contract(
            invariant(lambda self: self.balance >= 0, "balance must not go negative"),
        )
        def withdraw(self, amount: float) -> None:
            self.balance -= amount

    acct = BankAccount(100.0)
    acct.withdraw(50.0)   # ok

    acct2 = BankAccount(10.0)
    try:
        acct2.withdraw(20.0)  # balance goes negative
        assert False
    except ContractViolationError as e:
        assert e.kind == "invariant"


@test("valid contract passes without error")
def _():
    @contract(
        requires(lambda a, b: b != 0, "divisor must not be zero"),
        ensures(lambda r: isinstance(r, float), "result must be float"),
    )
    def divide(a: float, b: float) -> float:
        return a / b

    result = divide(10.0, 4.0)
    assert result == 2.5


# ─────────────────────────────────────────────────────────────────────────────
#  KomodoInspector
# ─────────────────────────────────────────────────────────────────────────────
print("\n  KomodoInspector")

@test("detects applied features")
def _():
    @komodo.data
    @komodo.builder
    class User:
        name: str
        age: int

    info = KomodoInspector(User)
    assert "data" in info.features
    assert "builder" in info.features


@test("lists fields and defaults")
def _():
    @komodo.constructor
    class Config:
        host: str
        port: int = 8080

    info = KomodoInspector(Config)
    assert "host" in info.fields
    assert "port" in info.defaults
    assert info.defaults["port"] == 8080


@test("summary() produces non-empty output")
def _():
    @komodo.data
    class Entity:
        id: int
        name: str

    info = KomodoInspector(Entity)
    s = info.summary()
    assert "Entity" in s
    assert "data" in s


@test("has_builder and is_immutable flags")
def _():
    @komodo.value
    class Pixel:
        r: int
        g: int
        b: int

    info = KomodoInspector(Pixel)
    assert info.is_immutable is True
    assert info.has_builder is False


# ─────────────────────────────────────────────────────────────────────────────
#  Composition
# ─────────────────────────────────────────────────────────────────────────────
print("\n  Composition")

@test("@komodo.logger + @komodo.data compose cleanly")
def _():
    @komodo.logger
    @komodo.data
    class Service:
        name: str
        version: str = "1.0"

    s = Service("auth")
    assert repr(s) == "Service(name='auth', version='1.0')"
    assert hasattr(Service, "logger")


@test("@komodo.copyable + @komodo.validated compose")
def _():
    @komodo.copyable
    @komodo.validated
    @komodo.constructor
    class Endpoint:
        host: str
        port: int = 443

    e = Endpoint("api.example.com")
    e2 = e.copy_with(port=8443)
    assert e2.port == 8443


# ─────────────────────────────────────────────────────────────────────────────
#  Results
# ─────────────────────────────────────────────────────────────────────────────

passed = sum(1 for _, ok, _ in _results if ok)
failed = sum(1 for _, ok, _ in _results if not ok)
total = len(_results)

print(f"\n\033[1m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
print(f"  Results: \033[92m{passed} passed\033[0m / \033[91m{failed} failed\033[0m / {total} total")

if failed:
    print("\n  Failed tests:")
    for name, ok, err in _results:
        if not ok:
            print(f"    {_FAIL} {name}: {err}")

print(f"\033[1m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n")

sys.exit(0 if failed == 0 else 1)
