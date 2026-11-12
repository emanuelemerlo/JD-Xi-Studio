"""Project metadata and version information for JD-Xi Editor."""

__version__ = "1.0.0a2"  # PEP 440; the release tag is v1.0.0-alpha.2
__program__ = "JD-Xi Editor"  # also the key of the saved settings: kept
# The name shown in the interface: an independent edition of JDXI-Editor by
# Mark Brooks, named apart so the two are not confused (installer, exe and
# settings keep the original names)
__display_name__ = "JD-Xi Studio"
__origin__ = "JDXI-Editor by Mark Brooks"
__origin_author__ = "Mark Brooks"
__maintainer__ = "Emanuele Merlo"  # this edition (JD-Xi Studio)
__origin_url__ = "https://github.com/markxbrooks/JDXI-Editor"
__home_url__ = "https://github.com/emanuelemerlo/JD-Xi-Studio"
__project__ = "JD-Xi Editor"
__author__ = "Emanuele Merlo, Mark Brooks"
__package_name__ = "jdxi_editor"
__organization_name__ = "mabsoft"


def release_name(version: str = __version__) -> str:
    """The version as the release tag writes it: 1.0.0a1 -> 1.0.0-alpha.1, 1.0.0 -> 1.0.0."""
    import re

    match = re.fullmatch(r"(\d+\.\d+\.\d+)(a|b|rc)(\d+)", version)
    if not match:
        return version
    kind = {"a": "alpha", "b": "beta", "rc": "rc"}[match.group(2)]
    return f"{match.group(1)}-{kind}.{match.group(3)}"
