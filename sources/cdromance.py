from __future__ import annotations

from urllib.parse import quote_plus, urlparse

import httpx
from selectolax.parser import HTMLParser

from .base import RomResult, Source

# Slug de categoría -> etiqueta amigable del sistema (para mostrar).
CATEGORY_LABELS: dict[str, str] = {
    "snes-rom": "SNES",
    "nes-roms": "NES",
    "gba-roms": "GBA",
    "gameboy-rom": "GB",
    "gameboy-color-roms": "GBC",
    "n64-roms": "N64",
    "gamecube": "GameCube",
    "wii-iso": "Wii",
    "nds-roms": "NDS",
    "3ds-decrypted-roms": "3DS",
    "famicom_disk_system": "FDS",
    "virtualboy_roms": "Virtual Boy",
    "sega_genesis_roms": "Genesis",
    "sms-rom": "Master System",
    "sega_32x_roms": "32X",
    "sega_cd_isos": "Sega CD",
    "dc-iso": "Dreamcast",
    "sega_saturn_isos": "Saturn",
    "psx-iso": "PS1",
    "psx2psp-eboots": "PSX→PSP",
    "ps2-iso": "PS2",
    "psp-iso": "PSP",
    "xbox-iso": "Xbox",
    "xbox-360-iso": "Xbox 360",
    "neo-geo-roms": "Neo Geo",
}

# Filtros: si el usuario pasa un sistema corto (snes, gba...), solo aceptamos
# resultados cuyo slug coincida con esta tabla.
SYSTEM_TO_CATEGORIES: dict[str, set[str]] = {
    "snes": {"snes-rom"},
    "nes": {"nes-roms"},
    "gba": {"gba-roms"},
    "gb": {"gameboy-rom"},
    "gbc": {"gameboy-color-roms"},
    "n64": {"n64-roms"},
    "gcn": {"gamecube"},
    "wii": {"wii-iso"},
    "nds": {"nds-roms"},
    "3ds": {"3ds-decrypted-roms"},
    "fds": {"famicom_disk_system"},
    "vb": {"virtualboy_roms"},
    "md": {"sega_genesis_roms"},
    "genesis": {"sega_genesis_roms"},
    "sms": {"sms-rom"},
    "32x": {"sega_32x_roms"},
    "megacd": {"sega_cd_isos"},
    "dreamcast": {"dc-iso"},
    "saturn": {"sega_saturn_isos"},
    "ps1": {"psx-iso", "psx2psp-eboots"},
    "psx": {"psx-iso", "psx2psp-eboots"},
    "ps2": {"ps2-iso"},
    "psp": {"psp-iso"},
    "xbox": {"xbox-iso"},
    "x360": {"xbox-360-iso"},
    "neogeo": {"neo-geo-roms"},
}


class CDRomanceSource(Source):
    """Búsqueda en cdromance.com (redirige a .org). Devuelve la página del
    juego — desde ahí el usuario obtiene el botón de descarga."""

    name = "CDRomance"
    base_url = "https://cdromance.com"

    async def search(
        self, client: httpx.AsyncClient, query: str, system: str | None = None
    ) -> list[RomResult]:
        url = f"{self.base_url}/?s={quote_plus(query)}"
        try:
            r = await client.get(url)
            r.raise_for_status()
        except httpx.HTTPError:
            return []

        tree = HTMLParser(r.text)
        for sel in ("nav", "header", "footer", "aside"):
            for n in tree.css(sel):
                n.decompose()

        sys_key = (system or "").lower()
        cat_filter: set[str] | None
        if sys_key:
            cat_filter = SYSTEM_TO_CATEGORIES.get(sys_key)
            if cat_filter is None:
                # CDRomance no cubre este sistema (ej: amiga, msdos, spectrum)
                return []
        else:
            cat_filter = None
        # Agrupamos por URL: cada juego tiene varios <a> al mismo href (imagen,
        # título, categoría); el título "real" es el texto más largo.
        groups: dict[str, dict] = {}
        for a in tree.css("a[href]"):
            href = (a.attributes.get("href") or "").rstrip("/")
            if not href.startswith(("https://cdromance.", "http://cdromance.")):
                continue
            if "#" in href or "?" in href:
                continue
            parts = [p for p in urlparse(href).path.split("/") if p]
            if len(parts) != 2:
                continue
            cat, slug = parts
            if cat not in CATEGORY_LABELS:
                continue
            if cat_filter and cat not in cat_filter:
                continue

            title = ""
            img = a.css_first("img")
            if img:
                title = img.attributes.get("alt") or img.attributes.get("title") or ""
            if not title:
                title = a.text(strip=True)
            # Filtrar textos de placeholder o solo un guión
            if title in ("", "-", "—", "–"):
                title = ""

            g = groups.setdefault(
                href, {"cat": cat, "slug": slug, "titles": []}
            )
            if title:
                g["titles"].append(title)

        results: list[RomResult] = []
        for url, info in list(groups.items())[:10]:
            # filtrar textos que solo sean la etiqueta del sistema
            label = CATEGORY_LABELS.get(info["cat"], info["cat"])
            real_titles = [t for t in info["titles"] if t.lower() != label.lower()]
            best = max(real_titles, key=len, default="")
            if not best:
                # fallback: humanizar el slug
                best = info["slug"].replace("-", " ").title()
            results.append(
                RomResult(
                    title=best[:120],
                    system=label,
                    source=self.name,
                    page_url=url,
                )
            )
        return results
