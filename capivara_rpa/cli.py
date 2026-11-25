"""CLI pública da biblioteca Capivara."""

from __future__ import annotations

import argparse

from capivara_rpa import __all__, __version__


def main(argv: list[str] | None = None) -> int:
    """Executa a CLI ``capivara``."""
    parser = argparse.ArgumentParser(
        prog="capivara",
        description="Capivara — RPA low-code em Python, 100% em português.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Lista os módulos e funções públicas da biblioteca.",
    )

    args = parser.parse_args(argv)

    if args.listar:
        for nome in sorted(__all__):
            print(nome)
        return 0

    parser.print_help()
    return 0
