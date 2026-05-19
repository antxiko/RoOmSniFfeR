from __future__ import annotations

import httpx

from .base import RomResult, Source

# Sistema -> colecciones de archive.org donde buscar.
# Cada sistema puede mapear a varias colecciones (se combinan con OR).
SYSTEM_COLLECTIONS: dict[str, list[str]] = {
    # --- Consolas Nintendo ---
    "nes": ["consolelivingroom"],
    "snes": ["consolelivingroom"],
    "n64": ["consolelivingroom"],
    "gb": ["consolelivingroom"],
    "gbc": ["consolelivingroom"],
    "gba": ["consolelivingroom"],
    "nds": ["consolelivingroom"],
    "gcn": ["consolelivingroom"],
    "wii": ["consolelivingroom", "redump"],
    # --- Consolas Sega ---
    "md": ["consolelivingroom"],
    "genesis": ["consolelivingroom"],
    "sms": ["consolelivingroom"],
    "saturn": ["redump"],
    "dreamcast": ["redump"],
    # --- Consolas Sony ---
    "ps1": ["redump"],
    "psx": ["redump"],
    "ps2": ["redump"],
    "psp": ["redump"],
    # --- Arcade / MAME ---
    "arcade": ["internetarcade"],
    "mame": ["internetarcade"],
    # --- Ordenadores ---
    "amiga": ["softwarelibrary_amiga"],
    "c64": ["softwarelibrary_c64", "softwarelibrary_c64_games"],
    "apple2": ["softwarelibrary_apple_games"],
    "applegs": ["softwarelibrary_apple2gs", "softwarelibrary_apple2gs_games"],
    "atari": ["softwarelibrary_atari"],
    "atarist": ["softwarelibrary_atari_st_games"],
    "msdos": ["softwarelibrary_msdos_games", "softwarelibrary_msdos"],
    "dos": ["softwarelibrary_msdos_games", "softwarelibrary_msdos"],
    "zx": ["softwarelibrary_zx_spectrum"],
    "spectrum": ["softwarelibrary_zx_spectrum"],
    "zx81": ["softwarelibrary_zx_81"],
    "cpc": ["softwarelibrary_cpc_applications", "softwarelibrary_cpc_pd"],
    "coco": ["softwarelibrary_coco2"],
    "tosec": ["tosec"],
    "pc": ["classicpcgames", "softwarelibrary_msdos_games"],
}

# Sistemas sin colección dedicada: usamos el TOSEC general (cubre casi todos
# los micro-ordenadores 8/16-bit) y añadimos el nombre del sistema al query
# para mejorar relevancia.
SYSTEM_QUERY_HINT: dict[str, str] = {
    "msx": "msx",
    "bbc": "bbc micro",
    "ti99": "ti-99",
    "vectrex": "vectrex",
    "intv": "intellivision",
    "colecovision": "colecovision",
    "vic20": "vic-20",
    "oric": "oric",
    "thomson": "thomson",
    "spectrum128": "spectrum",
    "x68000": "x68000",
    "pc88": "pc-88",
    "pc98": "pc-98",
}

SYSTEMS_USE_TOSEC = set(SYSTEM_QUERY_HINT.keys())

# Palabras que indican que un item NO es una ROM jugable: manuales, escaneos,
# soundtracks, magazines, etc. Si aparece cualquiera en el título lo descartamos.
NOT_ROM_KEYWORDS = (
    "manual", "manuals", "guide", "guidebook", "instructions",
    "magazine", "magasin", "review", "preview",
    "soundtrack", " ost ", " ost-", "ost vol", "ost cd", "ost dvd",
    "music collection", "music ost", "music album",
    "scan ", "scans ", "scanned",
    "wallpaper", "wallpapers",
    "screenshot", "screenshots",
    "cover", "covers", "boxart", "box art",
    "art book", "artbook", "art works", "artworks",
    "trailer", "trailers", "advert", "commercial",
    "promotional", "press kit",
    "fanart", "fan art",
    "ebook", "e-book", " book ",
    "documentary", "documentation",
    "tutorial",
)

# Hints para detectar que un título es de un sistema distinto al buscado
# (sólo se aplica para colecciones genéricas que mezclan consolas, como
# `consolelivingroom`).
SYSTEM_TITLE_HINTS: dict[str, tuple[str, ...]] = {
    "nes": ("nes", "famicom", "nintendo entertainment"),
    "snes": ("snes", "super nintendo", "super famicom"),
    "n64": ("n64", "nintendo 64"),
    "gb": ("game boy", "gameboy", "(gb)"),
    "gbc": ("game boy color", "gameboy color", "(gbc)"),
    "gba": ("game boy advance", "gameboy advance", "(gba)"),
    "nds": ("nintendo ds", "(nds)", "(ds)"),
    "gcn": ("gamecube", "game cube"),
    "wii": ("wii"),
    "md": ("genesis", "mega drive", "megadrive"),
    "sms": ("master system", "sms"),
    "saturn": ("saturn",),
    "dreamcast": ("dreamcast",),
    "ps1": ("playstation", "(ps)", "(ps1)", "(psx)"),
    "ps2": ("playstation 2", "(ps2)"),
}

# Colecciones que mezclan varias consolas: para éstas SI aplicamos el filtro
# por hint de sistema. Las colecciones específicas (softwarelibrary_amiga, etc.)
# ya están focalizadas y no necesitan filtro extra.
GENERIC_COLLECTIONS = {"consolelivingroom", "redump", "tosec"}


class ArchiveOrgSource(Source):
    """Búsqueda en archive.org. Si se da un sistema, restringe a las colecciones
    relevantes (No-Intro/Redump/Software Library/MAME) para resultados limpios.
    Si no se da sistema, búsqueda libre con la pista 'rom'."""

    name = "Internet Archive"
    base_url = "https://archive.org"

    async def search(
        self, client: httpx.AsyncClient, query: str, system: str | None = None
    ) -> list[RomResult]:
        sys_key = (system or "").lower()
        collections = SYSTEM_COLLECTIONS.get(sys_key, [])
        title_clause = f"title:({query})"

        if collections:
            coll_clause = " OR ".join(f'collection:{c}' for c in collections)
            q = f"{title_clause} AND ({coll_clause})"
        elif sys_key in SYSTEMS_USE_TOSEC:
            # Sistemas sin colección dedicada: query libre con el nombre del
            # sistema como hint, restringido a 'software' para evitar videos.
            hint = SYSTEM_QUERY_HINT[sys_key]
            q = f"{title_clause} AND ({hint}) AND mediatype:software"
        else:
            # Sistema sin colección ni hint, o sin sistema: no hacemos
            # búsqueda libre (devolvía resultados de cualquier consola).
            # El bot exige sistema antes de llegar aquí.
            return []

        params = {
            "q": q,
            "fl[]": ["identifier", "title", "item_size", "collection", "downloads"],
            "sort[]": "downloads desc",
            "rows": "10",
            "page": "1",
            "output": "json",
        }
        try:
            r = await client.get(
                f"{self.base_url}/advancedsearch.php", params=params
            )
            r.raise_for_status()
            docs = r.json().get("response", {}).get("docs", [])
        except (httpx.HTTPError, ValueError):
            return []

        # Hints de otros sistemas (para descartar resultados que se cuelan
        # de colecciones genéricas como consolelivingroom).
        wrong_system_hints: set[str] = set()
        if sys_key and collections and any(c in GENERIC_COLLECTIONS for c in collections):
            for other_sys, hints in SYSTEM_TITLE_HINTS.items():
                if other_sys == sys_key:
                    continue
                wrong_system_hints.update(h.lower() for h in hints)
            # Pero quitamos las hints del sistema actual para no auto-descartar
            for h in SYSTEM_TITLE_HINTS.get(sys_key, ()):
                wrong_system_hints.discard(h.lower())

        results: list[RomResult] = []
        for d in docs:
            ident = d.get("identifier")
            if not ident:
                continue
            title = str(d.get("title", ident))
            title_low = title.lower()

            # Descartar manuales, scans, soundtracks, etc.
            if any(kw in title_low for kw in NOT_ROM_KEYWORDS):
                continue
            # Descartar resultados de OTRO sistema cuando la colección es
            # genérica (consolelivingroom mezcla NES/SNES/N64/etc).
            if wrong_system_hints and any(h in title_low for h in wrong_system_hints):
                continue

            size = d.get("item_size")
            sys_label = _format_system(system, d.get("collection"))
            results.append(
                RomResult(
                    title=title[:120],
                    system=sys_label,
                    source=self.name,
                    page_url=f"{self.base_url}/details/{ident}",
                    download_url=f"{self.base_url}/download/{ident}",
                    size=_human_size(size) if size else None,
                )
            )
        return results


def _format_system(system: str | None, collections) -> str:
    if system:
        return system.upper()
    if not collections:
        return "?"
    if isinstance(collections, str):
        collections = [collections]
    return collections[0]


def _human_size(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return ""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.0f} PB"
