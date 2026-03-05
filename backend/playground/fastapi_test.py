import sys
from typing import get_type_hints

name: int
age: int = 25

# Wir übergeben das aktuelle Modul an die Funktion
current_module = sys.modules[__name__]
hints = get_type_hints(current_module)

print(hints)
# Output: {'name': <class 'int'>, 'age': <class 'int'>}
