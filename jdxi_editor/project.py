"""Project metadata and version information for JD-Xi Studio."""

__version__ = "1.0.0rc1"  # PEP 440; the release tag is v1.0.0-rc.1
# An independent edition of JDXI-Editor by Mark Brooks, with a name of its own
# everywhere (interface, installer, settings, user folder), so the two can be
# installed side by side and are never confused
__program__ = "JD-Xi Studio"  # also the key of the saved settings
__display_name__ = "JD-Xi Studio"
__origin__ = "JDXI-Editor by Mark Brooks"
__origin_author__ = "Mark Brooks"
__maintainer__ = "Emanuele Merlo"  # this edition (JD-Xi Studio)
__origin_url__ = "https://github.com/markxbrooks/JDXI-Editor"
__home_url__ = "https://github.com/emanuelemerlo/JD-Xi-Studio"
__project__ = "JD-Xi Studio"
__author__ = "Emanuele Merlo, Mark Brooks"
__package_name__ = "jdxi_editor"  # the Python package (code), not a user-facing name
__organization_name__ = "JD-Xi Studio"
# The user's folder: ~/.jdxi_studio (settings files, programs, recipes, logs)
__data_name__ = "jdxi_studio"
# What JD-Xi Studio used before 1.0.0a3 (the original program's names): copied
# once into the new places at the first start (jdxi_editor/migrate.py)
LEGACY_ORGANIZATION = "mabsoft"
LEGACY_PROGRAM = "JD-Xi Editor"
LEGACY_DATA_NAME = "jdxi_editor"


def release_name(version: str = __version__) -> str:
    """The version as the release tag writes it: 1.0.0a1 -> 1.0.0-alpha.1, 1.0.0 -> 1.0.0."""
    import re

    match = re.fullmatch(r"(\d+\.\d+\.\d+)(a|b|rc)(\d+)", version)
    if not match:
        return version
    kind = {"a": "alpha", "b": "beta", "rc": "rc"}[match.group(2)]
    return f"{match.group(1)}-{kind}.{match.group(3)}"


def package_version(version: str = __version__) -> str:
    """
    The version for the Linux packages (.deb, .rpm, AppImage names).

    dpkg and rpm order «1.0.0rc1» and «1.0.0b2» *after* «1.0.0»: a release
    candidate or a beta installed from a package would never be offered the
    finished release. A «~» sorts before anything, so a pre-release becomes
    «1.0.0~rc1», «1.0.0~b2», «1.0.0~dev3»; a final version stays as it is.

    :param version: a PEP 440 version (default: this one)
    :return: str the same version, pre-releases with «~»
    """
    import re

    match = re.fullmatch(r"(\d+(?:\.\d+)*)((?:a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?", version)
    if match is None:
        return version
    base, pre, post, dev = match.groups()
    result = base
    if pre:
        result += "~" + pre
    if post:
        result += "+" + post[1:]
    if dev:
        result += "~" + dev[1:]
    return result
