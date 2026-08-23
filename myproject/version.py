"""Single source of truth for YASAFlaskified version string."""
__version__ = "0.33.1"


def _psgscoring_version() -> str:
    """De WERKELIJK geinstalleerde psgscoring, niet een bijgehouden getal.

    Dit stond hier als handmatige constante en is twee releases achterop
    geraakt: hij zei 0.24.0 terwijl 0.26.0 draaide. Het rapport vermeldt zijn
    eigen herkomst, dus dat is geen cosmetisch verschil -- een klinisch
    document noemde een scoringsbibliotheek die het niet gebruikt had.

    Handmatig bijhouden faalt op precies de momenten dat het ertoe doet: bij
    een release, als er veel tegelijk verandert. Uitlezen kan niet vergeten
    worden.
    """
    try:
        from importlib.metadata import version as _v
        return _v("psgscoring")
    except Exception:
        pass
    try:
        import psgscoring
        return getattr(psgscoring, "__version__", "onbekend")
    except Exception:
        return "onbekend"


PSGSCORING_VERSION = _psgscoring_version()
