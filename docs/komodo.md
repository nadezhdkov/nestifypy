# nestifypy.komodo

> Lombok-style annotation-driven metaprogramming for Python.  
> Elimina boilerplate de classes via decorators — sem metaclasses, sem magia opaca.

---

## Índice

- [Instalação](#instalação)
- [Visão Geral](#visão-geral)
- [Referência de Decorators](#referência-de-decorators)
  - [@komodo.constructor](#komodoconstructor)
  - [@komodo.data](#komododata)
  - [@komodo.value](#komodovalue)
  - [@komodo.builder](#komodobuilder)
  - [@komodo.immutable](#komodoimmutable)
  - [@komodo.logger](#komodologger)
  - [@komodo.non_null](#komodonon_null)
  - [@komodo.singleton](#komodosingleton)
  - [@komodo.copyable](#komodocopyable)
  - [@komodo.validated](#komodovalidated)
  - [@komodo.observable](#komodoobservable)
  - [@komodo.sealed](#komodosealed)
  - [@komodo.deprecated](#komododeprecated)
  - [@komodo.accessors()](#komodoaccessors)
  - [@komodo.delegate()](#komododelegate)
  - [@komodo.mixin()](#komodomixin)
- [Design by Contract](#design-by-contract)
  - [@contract](#contract)
  - [requires()](#requires)
  - [ensures()](#ensures)
  - [invariant()](#invariant)
- [KomodoInspector](#komodoinspector)
- [Composição de Decorators](#composição-de-decorators)
- [Comparação com Lombok](#comparação-com-lombok)
- [Notas Técnicas](#notas-técnicas)

---

## Instalação

O package `komodo` faz parte da biblioteca `nestifypy`:

```
nestifypy/
├── __init__.py
├── komodo/
│   ├── __init__.py
│   ├── core.py
│   ├── contract.py
│   └── inspect.py
├── flow.py
└── decorators.py
```

Importação:

```python
from nestifypy.komodo import komodo
from nestifypy.komodo import contract, KomodoInspector
from nestifypy.komodo.contract import requires, ensures, invariant, ContractViolationError
```

---

## Visão Geral

`komodo` é um namespace de decorators de classe que reescrevem a classe **em tempo de definição**, sem metaclasses nem proxies em runtime. Cada decorator é independente e composável.

```python
from nestifypy.komodo import komodo

@komodo.logger
@komodo.copyable
@komodo.data
class User:
    name: str
    email: str
    role: str = "user"

# Tudo gerado automaticamente:
u = User("Alice", "alice@example.com")
print(u)                          # User(name='Alice', email='alice@example.com', role='user')
u2 = u.copy_with(role="admin")
User.logger.info("User created")
```

---

## Referência de Decorators

### @komodo.constructor

Gera `__init__` a partir de `__annotations__`. Campos sem default são argumentos obrigatórios; campos com default são opcionais.

Equivalente Lombok: `@AllArgsConstructor` / `@RequiredArgsConstructor`

```python
@komodo.constructor
class Server:
    host: str
    port: int = 8080
    debug: bool = False

s = Server("localhost")           # port=8080, debug=False
s2 = Server("0.0.0.0", 443)
s3 = Server(host="api.example.com", port=443, debug=True)
```

**`__post_init__`**: se definires este método, é chamado automaticamente no final do `__init__` gerado, similar ao `dataclass`:

```python
@komodo.constructor
class Config:
    host: str
    port: int = 5432

    def __post_init__(self):
        self.url = f"postgresql://{self.host}:{self.port}"

c = Config("db.prod.com")
print(c.url)  # postgresql://db.prod.com:5432
```

---

### @komodo.data

Atalho que aplica `constructor` + `to_str` + `eq` numa só anotação. O equivalente mais próximo ao `@Data` do Lombok.

Gera: `__init__`, `__repr__`, `__str__`, `__eq__`, `__hash__`.

```python
@komodo.data
class Point:
    x: float
    y: float

p1 = Point(1.0, 2.0)
p2 = Point(1.0, 2.0)

print(p1)           # Point(x=1.0, y=2.0)
print(p1 == p2)     # True
points = {p1, p2}   # funciona como chave de set/dict
print(len(points))  # 1
```

---

### @komodo.value

Cria um **objeto de valor imutável** — equivalente ao `@Value` do Lombok ou a uma `NamedTuple` com semântica de classe normal.

Aplica: `data` + `immutable`. Qualquer tentativa de mutação após construção levanta `AttributeError`.

```python
@komodo.value
class Money:
    amount: float
    currency: str

m = Money(9.99, "USD")
print(m)               # Money(amount=9.99, currency='USD')

m.amount = 0.0         # AttributeError: Money is immutable — cannot set attribute 'amount'
```

Útil para DTOs, value objects de domínio, chaves de cache.

---

### @komodo.builder

Adiciona uma inner class `.Builder` com API fluente. Cada campo anotado ganha um método `with_<campo>()`. O método `.build()` valida campos obrigatórios e constrói a instância.

Equivalente Lombok: `@Builder`

```python
@komodo.builder
class HttpRequest:
    url: str
    method: str = "GET"
    timeout: float = 30.0
    headers: dict = None

req = (
    HttpRequest.Builder()
        .with_url("https://api.example.com/users")
        .with_method("POST")
        .with_timeout(10.0)
        .with_headers({"Authorization": "Bearer token"})
        .build()
)

# Também disponível via factory method:
req2 = HttpRequest.builder().with_url("https://example.com").build()
```

Se um campo obrigatório não for setado, `.build()` levanta `ValueError`:

```python
HttpRequest.Builder().build()
# ValueError: HttpRequest.Builder: required field 'url' was not set
```

---

### @komodo.immutable

Previne qualquer mutação de atributo após o `__init__` completar. Usa uma flag interna `_frozen` para distinguir a fase de construção da fase de uso.

Pode ser aplicado a qualquer classe que já tenha um `__init__` próprio ou gerado.

```python
@komodo.immutable
@komodo.constructor
class Coordinate:
    lat: float
    lon: float

coord = Coordinate(38.7, -9.14)
coord.lat = 0.0  # AttributeError: Coordinate is immutable — cannot set attribute 'lat'
del coord.lon    # AttributeError: Coordinate is immutable — cannot delete attribute 'lon'
```

> **Nota**: `@komodo.value` já inclui `@komodo.immutable`. Usa `@komodo.immutable` diretamente quando queres imutabilidade sem os outros features de `@komodo.value`.

---

### @komodo.logger

Injeta um atributo `logger` na classe, pronto para usar como `self.logger` ou `ClassName.logger`. Usa o módulo `logging` da stdlib, com o nome `módulo.NomeDaClasse`.

Equivalente Lombok: `@Slf4j`

```python
@komodo.logger
class AuthService:
    def authenticate(self, user: str) -> bool:
        self.logger.info("Authenticating user: %s", user)
        # ...
        self.logger.warning("Failed attempt for: %s", user)
        return False

svc = AuthService()
svc.authenticate("alice")
# INFO:__main__.AuthService:Authenticating user: alice
# WARNING:__main__.AuthService:Failed attempt for: alice
```

O logger é configurado pelo sistema de logging padrão do Python — aplica handlers e formatters normalmente.

---

### @komodo.non_null

Envolve o `__init__` para levantar `ValueError` se qualquer argumento for `None`, tanto posicionais como keyword.

Equivalente Lombok: `@NonNull` nos parâmetros do construtor.

```python
@komodo.non_null
@komodo.constructor
class DatabaseConfig:
    host: str
    password: str

DatabaseConfig("localhost", "secret")   # OK
DatabaseConfig(None, "secret")          # ValueError: DatabaseConfig: field 'host' must not be None
DatabaseConfig("localhost", None)       # ValueError: DatabaseConfig: field 'password' must not be None
```

> Combina bem com `@komodo.validated` — `non_null` trata especificamente `None`, enquanto `validated` trata tipos incorretos.

---

### @komodo.singleton

Garante que apenas uma instância da classe existe em toda a aplicação. A instância é criada lazily na primeira chamada e reutilizada nas seguintes.

```python
@komodo.singleton
class AppConfig:
    def __init__(self):
        self.debug = False
        self.version = "1.0.0"

a = AppConfig()
b = AppConfig()
assert a is b  # True — mesma instância
```

> **Atenção com composição**: `@komodo.singleton` e `@komodo.constructor` funcionam juntos, mas `@komodo.singleton` deve ser o decorator mais externo (aplicado por último, ou seja, o primeiro na lista):
>
> ```python
> @komodo.singleton        # externo — aplicado último
> @komodo.constructor      # interno — aplicado primeiro
> class Registry:
>     name: str = "default"
> ```

---

### @komodo.copyable

Adiciona dois métodos à classe:

- `.copy()` — retorna uma cópia rasa (shallow copy) da instância
- `.copy_with(**overrides)` — retorna uma nova instância com campos selecionados substituídos

Inspirado no `copy()` das `data class` do Kotlin e no `@With` do Lombok.

```python
@komodo.copyable
@komodo.data
class ServerConfig:
    host: str = "localhost"
    port: int = 8080
    ssl: bool = False

base = ServerConfig()
prod = base.copy_with(host="api.production.com", ssl=True)
staging = base.copy_with(host="api.staging.com", port=8443)

print(base)     # ServerConfig(host='localhost', port=8080, ssl=False)
print(prod)     # ServerConfig(host='api.production.com', port=8080, ssl=True)
print(staging)  # ServerConfig(host='api.staging.com', port=8443, ssl=False)
```

---

### @komodo.validated

Aplica type-checking em runtime sobre os argumentos do `__init__` com base nas `__annotations__`. Levanta `TypeError` com mensagem descritiva se um valor não corresponder ao tipo declarado.

Compatível com `from __future__ import annotations` (PEP 563) — usa `typing.get_type_hints()` internamente para resolver anotações em string.

```python
@komodo.validated
@komodo.constructor
class Rectangle:
    width: float
    height: float

Rectangle(10.0, 5.0)       # OK
Rectangle("largo", 5.0)    # TypeError: Rectangle: field 'width' expected float, got str
Rectangle(10, 5.0)         # OK — int é subclasse de... na verdade não, mas int não é float
                            # Logo: TypeError: field 'width' expected float, got int
```

> **Nota sobre `int` vs `float`**: Python não considera `int` subclasse de `float` para `isinstance()`, embora suporte a conversão implícita. Se precisas aceitar ambos, usa `Union[int, float]` ou `numbers.Real`.

---

### @komodo.observable

Intercepta `__setattr__` para notificar callbacks registados sempre que um campo muda de valor. Implementa o padrão Observer sem herança.

```python
@komodo.observable
@komodo.constructor
class UserSettings:
    theme: str = "dark"
    language: str = "pt"
    notifications: bool = True

settings = UserSettings()

# Registar listener
settings.on_change(lambda field, old, new: print(f"  {field}: {old!r} → {new!r}"))

settings.theme = "light"
# theme: 'dark' → 'light'

settings.language = "en"
# language: 'pt' → 'en'

# Remover listener
def my_callback(f, o, n): ...
settings.on_change(my_callback)
settings.off_change(my_callback)
```

A assinatura do callback é sempre `(field_name: str, old_value: Any, new_value: Any) -> None`.

Campos privados (prefixo `_`) não disparam notificações.

---

### @komodo.sealed

Impede qualquer subclasse. Levanta `TypeError` em tempo de definição da subclasse.

Equivalente: `sealed` do Java 17+ / `final` do Kotlin.

```python
@komodo.sealed
class AuthToken:
    def __init__(self, value: str):
        self._value = value

class JwtToken(AuthToken):   # TypeError: AuthToken is sealed and cannot be subclassed.
    pass
```

---

### @komodo.deprecated

Emite `DeprecationWarning` em cada instanciação da classe. Aceita dois modos:

```python
# Modo simples — sem argumentos
@komodo.deprecated
class OldApiClient:
    pass

# Modo com mensagem — com argumentos keyword
@komodo.deprecated(reason="Use NewApiClient instead.", since="2.0")
class LegacyApiClient:
    pass

import warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    LegacyApiClient()
    print(w[0].message)
# LegacyApiClient is deprecated since v2.0. Use NewApiClient instead.
```

A mensagem fica também disponível em `LegacyApiClient.__deprecated__`.

---

### @komodo.accessors()

Gera Python `property` getters e setters para todos os campos anotados. Os valores são armazenados internamente como `_campo`.

Equivalente Lombok: `@Getter` / `@Setter`

```python
@komodo.accessors()          # readonly=False (default) — getter + setter
class Person:
    name: str
    age: int

p = Person.__new__(Person)
object.__setattr__(p, "_name", "Alice")
object.__setattr__(p, "_age", 30)

print(p.name)   # Alice
p.name = "Bob"  # setter
print(p.name)   # Bob

# Só leitura:
@komodo.accessors(readonly=True)
class ImmutableRecord:
    id: int
    value: str
```

---

### @komodo.delegate()

Delega métodos de um objeto interno para a classe exterior. Os métodos do delegado ficam acessíveis diretamente na instância.

Equivalente Lombok: `@Delegate`

```python
class _EmailSender:
    def send(self, to: str, subject: str) -> None:
        print(f"Sending '{subject}' to {to}")

    def validate(self, email: str) -> bool:
        return "@" in email

@komodo.delegate("_sender", methods=["send", "validate"])
class NotificationService:
    def __init__(self):
        self._sender = _EmailSender()

svc = NotificationService()
svc.send("user@example.com", "Welcome!")  # Delegado para _sender.send()
print(svc.validate("bad-email"))          # False
```

Se `methods=None` (omitido), todos os métodos públicos do delegado são proxied.

---

### @komodo.mixin()

Injeta mixin classes no MRO da classe em tempo de definição. Útil quando as mixins são determinadas programaticamente ou quando queres evitar listá-las nas bases.

```python
class LogMixin:
    def log(self, msg: str) -> None:
        print(f"[{self.__class__.__name__}] {msg}")

class SerializeMixin:
    def to_dict(self) -> dict:
        return vars(self)

@komodo.mixin(LogMixin, SerializeMixin)
@komodo.data
class Product:
    name: str
    price: float

p = Product("Widget", 9.99)
p.log("Product created")      # [Product] Product created
print(p.to_dict())             # {'name': 'Widget', 'price': 9.99}
```

---

## Design by Contract

Inspirado na anotação `@Contract` do IntelliJ IDEA e no modelo Hoare-triple (pré-condição / pós-condição / invariante) de Eiffel.

```python
from nestifypy.komodo import contract
from nestifypy.komodo.contract import requires, ensures, invariant, ContractViolationError
```

### @contract

Decorator que aplica condições declarativas a funções e métodos. Aceita qualquer combinação de `requires()`, `ensures()` e `invariant()`.

```python
@contract(
    requires(lambda x, y: y != 0, "divisor must not be zero"),
    ensures(lambda result: result >= 0, "result must be non-negative"),
)
def safe_divide(x: float, y: float) -> float:
    return abs(x / y)

safe_divide(10.0, 2.0)   # OK → 5.0
safe_divide(10.0, 0.0)   # ContractViolationError: precondition violated in 'safe_divide': divisor must not be zero
```

Em caso de violação, `ContractViolationError` é levantado com:
- `error.kind` — `"precondition"`, `"postcondition"` ou `"invariant"`
- `error.func` — nome qualificado da função
- `error.message` — mensagem declarada

---

### requires()

Declara uma **pré-condição** — verificada *antes* da execução. O predicado recebe os mesmos argumentos que a função decorada.

```python
@contract(
    requires(lambda items: len(items) > 0, "list must not be empty"),
    requires(lambda items: all(isinstance(i, int) for i in items), "all items must be int"),
)
def average(items: list) -> float:
    return sum(items) / len(items)

average([1, 2, 3])   # OK → 2.0
average([])          # ContractViolationError: precondition — list must not be empty
```

---

### ensures()

Declara uma **pós-condição** — verificada *depois* da execução. O predicado recebe o **valor de retorno** como único argumento.

```python
@contract(
    ensures(lambda r: isinstance(r, str), "must return a string"),
    ensures(lambda r: len(r) > 0, "returned string must not be empty"),
)
def get_username(user_id: int) -> str:
    return f"user_{user_id}"

get_username(42)   # OK → "user_42"
```

---

### invariant()

Declara um **invariante** — verificado *antes e depois* da execução. Útil para garantir que o estado do objeto se mantém consistente.

O predicado pode receber `self` (para métodos) ou os argumentos completos:

```python
class BankAccount:
    def __init__(self, balance: float):
        self.balance = balance

    @contract(
        invariant(lambda self: self.balance >= 0, "balance must never be negative"),
    )
    def withdraw(self, amount: float) -> None:
        self.balance -= amount

    @contract(
        requires(lambda self, amount: amount > 0, "deposit must be positive"),
        invariant(lambda self: self.balance >= 0, "balance must never be negative"),
    )
    def deposit(self, amount: float) -> None:
        self.balance += amount

acct = BankAccount(100.0)
acct.deposit(50.0)     # OK
acct.withdraw(30.0)    # OK
acct.withdraw(200.0)   # ContractViolationError: invariant violated (after call)
```

---

## KomodoInspector

Ferramenta de introspecção em runtime para classes decoradas com `komodo`. Útil para debugging, geração de documentação e tooling.

```python
from nestifypy.komodo import KomodoInspector

@komodo.logger
@komodo.copyable
@komodo.builder
@komodo.data
class Order:
    id: int
    product: str
    quantity: int = 1
    status: str = "pending"

info = KomodoInspector(Order)

print(info.features)
# {'data', 'constructor', 'to_str', 'eq', 'builder', 'copyable', 'logger'}

print(info.fields)
# {'id': <class 'int'>, 'product': <class 'str'>, 'quantity': <class 'int'>, 'status': <class 'str'>}

print(info.defaults)
# {'quantity': 1, 'status': 'pending'}

print(info.generated_methods)
# ['__init__', '__repr__', '__str__', '__eq__', '__hash__', 'copy', 'copy_with', 'Builder', 'builder', 'logger']

print(info.has_builder)    # True
print(info.is_immutable)   # False
print(info.is_singleton)   # False
```

### summary()

Imprime um resumo formatado de toda a metadata komodo:

```python
print(info.summary())
```

```
┌──────────────────────────────────────────────────┐
│  komodo.inspect  →  Order                          │
├──────────────────────────────────────────────────┤
│  Features   : builder, constructor, copyable...  │
│  Fields     : id: int, product: str, ...         │
│  Defaults   : quantity=1, status='pending'       │
│  Generated  : __init__, __repr__, copy, ...      │
│  Immutable  : No                                 │
│  Singleton  : No                                 │
│  Has Builder: Yes                                │
└──────────────────────────────────────────────────┘
```

### contract_info()

Retorna a metadata de contrato de um método específico:

```python
info = KomodoInspector(BankAccount)
contracts = info.contract_info("withdraw")
# {
#   'preconditions': [...],
#   'postconditions': [...],
#   'invariants': [(predicate, 'balance must never be negative')]
# }
```

---

## Composição de Decorators

Todos os decorators `komodo` são composáveis. A ordem segue a regra normal do Python: **os decorators são aplicados de baixo para cima** (o decorator mais próximo da classe é aplicado primeiro).

**Ordem recomendada** (de cima para baixo na definição):

```python
@komodo.singleton          # 7. aplicado por último  (mais externo)
@komodo.logger             # 6.
@komodo.deprecated(...)    # 5.
@komodo.copyable           # 4.
@komodo.non_null           # 3.
@komodo.validated          # 2.
@komodo.data               # 1. aplicado primeiro (mais interno, modifica __init__ base)
class MyClass:
    field: type
```

### Exemplos práticos

**Entidade de domínio rica:**

```python
@komodo.logger
@komodo.copyable
@komodo.data
class Product:
    id: int
    name: str
    price: float
    active: bool = True

p = Product(1, "Widget", 9.99)
p2 = p.copy_with(price=7.99)
Product.logger.info("Price updated: %s → %s", p.price, p2.price)
```

**DTO com construção fluente e validação:**

```python
@komodo.builder
@komodo.validated
@komodo.constructor
class CreateUserRequest:
    username: str
    email: str
    role: str = "viewer"

req = (
    CreateUserRequest.Builder()
        .with_username("alice")
        .with_email("alice@example.com")
        .with_role("admin")
        .build()
)
```

**Value object imutável:**

```python
@komodo.value   # = @komodo.data + @komodo.immutable
class Currency:
    code: str    # "USD", "EUR", ...
    symbol: str  # "$", "€", ...

USD = Currency("USD", "$")
EUR = Currency("EUR", "€")
# Imutáveis, hashable, com __eq__ e __repr__
```

**Serviço com lifecycle:**

```python
@komodo.singleton
@komodo.logger
@komodo.constructor
class DatabasePool:
    host: str
    port: int = 5432
    max_connections: int = 10

    def __post_init__(self):
        self.logger.info("Pool initialized: %s:%d", self.host, self.port)
        self._connections = []
```

**Contrato em método crítico:**

```python
from nestifypy.komodo import contract
from nestifypy.komodo.contract import requires, ensures

@komodo.logger
@komodo.constructor
class PaymentService:
    currency: str = "EUR"

    @contract(
        requires(lambda self, amount: amount > 0, "amount must be positive"),
        requires(lambda self, amount: amount <= 10_000, "amount exceeds single-transaction limit"),
        ensures(lambda result: result.get("status") == "ok", "payment must succeed"),
    )
    def process(self, amount: float) -> dict:
        self.logger.info("Processing %.2f %s", amount, self.currency)
        return {"status": "ok", "amount": amount}
```

---

## Comparação com Lombok

| Lombok (Java)              | komodo (Python)                  | Notas                                          |
|----------------------------|--------------------------------|------------------------------------------------|
| `@Data`                    | `@komodo.data`                   | Gera `__init__`, `__repr__`, `__eq__`, `__hash__` |
| `@Value`                   | `@komodo.value`                  | Imutável + todos os métodos de `@data`         |
| `@Builder`                 | `@komodo.builder`                | Inner class `.Builder` com API fluente         |
| `@AllArgsConstructor`      | `@komodo.constructor`            | `__init__` gerado por anotações                |
| `@ToString`                | `@komodo.to_str` (via `@data`)   | `__repr__` e `__str__`                         |
| `@EqualsAndHashCode`       | `@komodo.eq` (via `@data`)       | `__eq__` + `__hash__`                          |
| `@Slf4j`                   | `@komodo.logger`                 | Logger injetado via stdlib `logging`           |
| `@NonNull`                 | `@komodo.non_null`               | Valida `None` em todos os args do `__init__`   |
| `@With`                    | `@komodo.copyable`               | `.copy()` e `.copy_with()`                     |
| `@Delegate`                | `@komodo.delegate(field)`        | Proxy de métodos para objeto interno           |
| `@Singular`                | —                              | Não implementado (idioma menos relevante em Python) |
| `sealed` (Java 17)         | `@komodo.sealed`                 | Bloqueia subclassing                           |
| IntelliJ `@Contract`       | `@contract(requires, ensures)` | Pre/pós condições declarativas                 |
| IntelliJ `@NotNull`        | `@komodo.non_null`               | Validação de nulidade                          |
| IntelliJ `@Immutable`      | `@komodo.immutable` / `@komodo.value` | Freeze após construção                      |

---

## Notas Técnicas

### PEP 563 — Anotações como strings

Quando um ficheiro usa `from __future__ import annotations`, todas as anotações são armazenadas como strings em vez de tipos reais. O `@komodo.validated` e o `@komodo.constructor` lidam com isso automaticamente via `typing.get_type_hints()`.

Se criares um decorator customizado que precise inspecionar anotações, usa sempre:

```python
import typing
hints = typing.get_type_hints(cls)  # em vez de cls.__annotations__
```

### Metadados de komodo

Cada decorator marca a classe com o set de features aplicadas em `cls.__komodo_meta__`. Podes inspecionar diretamente:

```python
@komodo.data
class Foo:
    x: int

print(Foo.__komodo_meta__)  # {'data', 'constructor', 'to_str', 'eq'}
```

### Decorator stacking e `__init__` chains

Quando múltiplos decorators modificam `__init__`, cada um envolve o anterior. A ordem de execução em runtime é do mais externo para o mais interno:

```
@komodo.non_null    → wrapper C (executa primeiro)
@komodo.validated   → wrapper B
@komodo.constructor → wrapper A (executa por último, o __init__ real)
```

Chamar `MyClass(args)` executa: `non_null.__init__` → `validated.__init__` → `constructor.__init__`.

### Performance

Todos os reescritos acontecem uma única vez em tempo de definição da classe (`import time`). Não há overhead em runtime além das chamadas normais a funções Python — sem proxies, sem `__getattr__` dinâmico, sem metaclasses.

### Thread safety

`@komodo.singleton` não é thread-safe por padrão. Para aplicações multi-thread, envolve com um lock:

```python
import threading

@komodo.singleton
class ThreadSafeConfig:
    _lock = threading.Lock()

    def get_setting(self, key: str) -> str:
        with self._lock:
            return ...
```

---

*`nestifypy.komodo` — parte da biblioteca nestifypy.*
