from .base import Source, RomResult
from .archive_org import ArchiveOrgSource
from .archive_packs import ArchivePacksSource
from .cdromance import CDRomanceSource

ALL_SOURCES: list[Source] = [
    ArchivePacksSource(),  # primero: enlaces directos a ROMs individuales dentro de packs
    ArchiveOrgSource(),
    CDRomanceSource(),
]

__all__ = ["Source", "RomResult", "ALL_SOURCES"]
