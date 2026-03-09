"""
Registry de converters — auto-descubrimiento.
Responsabilidad: Descubrir, registrar y proveer el converter correcto
según la extensión del archivo.

Para agregar un nuevo formato solo hay que crear un nuevo archivo
*_converter.py en la carpeta converters/. Este registry lo encontrará
automáticamente al iniciar la app.
"""

import importlib
import pkgutil
from pathlib import Path

from converters.base import BaseConverter

# Diccionario interno:  extensión -> instancia de converter
_registry: dict[str, BaseConverter] = {}


def _discover_converters() -> None:
    """
    Recorre todos los módulos en el paquete converters/ cuyo nombre
    termine en '_converter' y registra cada uno.
    """
    package_dir = Path(__file__).resolve().parent

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if not module_info.name.endswith("_converter"):
            continue

        module = importlib.import_module(f"converters.{module_info.name}")

        # Buscar clases que hereden de BaseConverter
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseConverter)
                and attr is not BaseConverter
            ):
                instance = attr()
                for ext in instance.supported_extensions():
                    _registry[ext.lower()] = instance


def get_converter(extension: str) -> BaseConverter | None:
    """Retorna el converter adecuado para la extensión dada (sin punto)."""
    if not _registry:
        _discover_converters()
    return _registry.get(extension.lower())


def get_supported_extensions() -> list[str]:
    """Retorna todas las extensiones soportadas actualmente."""
    if not _registry:
        _discover_converters()
    return sorted(_registry.keys())


def reload_registry() -> None:
    """Fuerza el re-descubrimiento de converters (útil para hot-reload)."""
    _registry.clear()
    _discover_converters()
