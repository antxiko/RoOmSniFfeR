"""Búsqueda dentro de packs/colecciones zip de archive.org.

archive.org tiene packs gigantes (MSX Rom Collection By Ghostware, FinalBurn
Neo ROM set, etc.) que contienen miles de ROMs individuales como archivos
.zip/.rom dentro del item. La API de metadata expone la lista completa de
archivos, así podemos buscar por nombre y construir el enlace de descarga
directo del archivo individual.
"""

from __future__ import annotations

import asyncio
from urllib.parse import quote

import httpx
from selectolax.parser import HTMLParser

from .base import RomResult, Source

# Identifier de archive.org -> sistemas que cubre.
# Todos verificados (existen, son items con archivos, no colecciones).
# La serie "Ghostware" cubre casi todo el catálogo retro:
#   https://archive.org/details/@ghostware
PACKS_BY_SYSTEM: dict[str, list[str]] = {
    # ============== Nintendo ==============
    "nes": ["CentralArquivista-NES", "NESROMsGoodNESFC"],
    "fds": ["NESROMsGoodNESFC"],
    "snes": ["CentralArquivista-NintendoSuperNintendo",
             "CentralArquivista-SuperNintendo",
             "nongoodsnes-finale"],
    "n64": ["CentralArquivista-Nintendo64",
            "CentralArquivista-NINTENDO-64"],
    "gb": ["CentralArquivista-GameBoy"],
    "gbc": ["CentralArquivista-GameBoyColor"],
    "gba": ["GameboyAdvanceRomCollectionByGhostware"],
    "nds": ["nds_apfix"],
    "3ds": ["xenoblade-chronicles-3-d-korea-en-e-shop-decrypted",
            "3ds-cia-eshop",
            "CentralArquivista-Nintendo3DS-JP"],
    "gcn": ["GamecubeCollectionByGhostware",
            "AsiaGamecubeCollectionByGhostware"],
    "wii": ["Wii_ISO"],
    "vb": ["CentralArquivista-NintendoVirtualBoy",
           "CentralArquivista-NintendoVirtualBoy-NaoOficial"],
    "gameandwatch": ["GameWatchRomCollectionByGhostware"],

    # ============== Sega ==============
    "sms": ["SegaMasterSystemCollectionByGhostware",
            "CentralArquivista-SegaMasterSystem"],
    "gamegear": ["SegaGameGearCollectionByGhostware"],
    "md": ["SegaGenesisMegaDriveRomCollectionByGhostware",
           "sega-genesis-romset-ultra-usa"],
    "32x": ["CentralArquivista-32X"],
    "megacd": ["SegaMegaCDEuropeCollectionByGhostware",
               "SegaMegaCDAsiaCollectionByGhostware",
               "CentralArquivista-SegaCD32x"],
    "saturn": ["SegaSaturnRomCollectionByGhostware",
               "chd_saturn",
               "sega-saturn-1g1r-chd-perfect-collection_202306"],
    "dreamcast": ["DreamcastCollectionByGhostwareMulti-region",
                  "SegaDreamcastNTSC-JPRomCollectionByGhostware",
                  "RedumpSegaDreamcast20160613"],

    # ============== Sony ==============
    "ps1": ["PlaystationNorthAmericaCollectionByGhostware", "chd_psx"],
    "psx": ["PlaystationNorthAmericaCollectionByGhostware", "chd_psx"],
    "ps2": ["PS2CollectionPart1ByGhostware",
            "TextsPS2CollectionPart3ByGhostware",
            "ps2usaredump1"],
    "ps3": ["PSNCollectionByGhostware"],
    "psp": ["rr-sony-playstation-portable", "PSNCollectionByGhostware"],

    # ============== Microsoft ==============
    "xbox": ["XBOX_HDD_READY",
             "XBOX_HDD_READY_2",
             "XBOX_HDD_READY_2_201710",
             "XBOX_HDD_READY_3",
             "mxogcx-xbox-ztm",
             "mxogcxpt2-xbox-ztm"],
    "x360": ["XBOX_360_1",
             "msx360gcdlc",
             "CentralArquivista-XBOX360-part1",
             "CentralArquivista-XBOX360-part2",
             "CentralArquivista-XBOX360-part3",
             "CentralArquivista-XBOX360-part4"],

    # ============== SNK / Arcade ==============
    "neogeo": ["NeoGeoRomCollectionByGhostware",
               "Neo-geoRomCollectionByGhostware",
               "neo-geo-aes-romset"],
    "arcade": ["MAME0.139RomCollectionByGhostware",
               "MAME0.37b5RomCollectionByGhostware",
               "fbnarcade-fullnonmerged",
               "2020_01_06_fbn",
               "CapcomCPS1ByGhostware",
               "NaomiRomsReuploadByGhostware",
               "FinalBurnAlphaReuploadByGhostware"],
    "mame": ["MAME0.139RomCollectionByGhostware",
             "MAME0.37b5RomCollectionByGhostware",
             "fbnarcade-fullnonmerged",
             "2020_01_06_fbn",
             "CapcomCPS1ByGhostware",
             "NaomiRomsReuploadByGhostware"],

    # ============== Otras consolas ==============
    "wonderswan": ["WonderswanRomCollectionByGhostware",
                   "WonderswanColorRomCollectionByGhostware"],
    "3do": ["Panasonic3DOEuropeRomCollectionByGhostware", "rr-3do"],
    "atari2600": ["goodsets-all-2013-sep-28"],
    "atari5200": ["nointro.atari-5200", "goodsets-all-2013-sep-28"],
    "atari7800": ["goodsets-all-2013-sep-28"],
    "jaguar": ["AtariJaguarReuploadByGhostware",
               "CentralArquivista-AtariJaguar"],
    "lynx": ["AtariLynxRomCollectionByGhostware",
             "CentralArquivista-AtariLynx"],
    "pcengine": ["NECPCEGhostwareReuploadaca",
                 "CentralArquivista-NecPcEngine"],
    "vectrex": ["CentralArquivista-GCEVectrex"],
    "channelf": ["Fairchild_VES_and_Channel_F_TOSEC_2012_04_23"],
    "intv": ["CentralArquivista-Intellivision",
             "MattelIntellivision2014ReferenceSet-CompleteTosecRomCollection"],
    "colecovision": ["CentralArquivista-ColecoVision"],

    # ============== Ordenadores ==============
    "msx": ["MSXRomCollectionByGhostware", "MSX2RomCollectionByGhostware"],
    "amiga": ["AmigaRomCollectionByGhostware_201711",
              "AmigaSingleRomsA-ZReuploadByGhostware",
              "super-skidmarks-v-2.2-cd"],
    "atarist": ["AtariSTRomsetByGhostware2018"],
    "atari": ["Atari800RomCollectionByGhostware"],
    "c64": ["C64RomCollectionByGhostware",
            "c64-dreams-v0.60",
            "Ultimate_Tape_Archive_V4.0"],
    "vic20": ["CommodoreVIC20CollectionByGhostware"],
    "x68000": ["SharpX68000RomCollectionByGhostware"],
    "cpc": ["pack-roms-amstrad-cpc"],
    "spectrum": ["ZXSpectrumTOSECSetV20171101LadyEklipse",
                 "zx_spectrum_tosec_set_september_2023"],
    "zx": ["ZXSpectrumTOSECSetV20171101LadyEklipse"],
    "spectrum128": ["ZXSpectrumTOSECSetV20171101LadyEklipse"],
    "zx81": ["Sinclair_ZX81_TOSEC_2012_04_23"],
    "bbc": ["AcornBBCMicroRomCollectionByGhostware"],
    "apple2": ["Antoine_Applesauce_Vignau", "Apple_2_TOSEC_2012_04_23"],
    "applegs": ["Apple_II_GS_TOSEC_2012_04_23",
                "Antoine_Vignau_3.5_Floppies_Flux_May_2019_Batch"],
    "ti99": ["Texas_Instruments_TI-99_4a_TOSEC_2012_04_23"],
    "oric": ["Tangerine_Oric_1_and_Atmos_TOSEC_2012_04_23"],
    "thomson": ["Thomson_M05_TOSEC_2012_04_23",
                "Thomson_TO7_TOSEC_2012_04_23",
                "Thomson_TO8_TOSEC_2012_04_23"],
    "coco": ["Tandy_TRS80_Color_Computer_TOSEC_2012_04_23"],
    "msdos": ["DOSGamesCollection2015"],
    "dos": ["DOSGamesCollection2015"],
    "pc88": ["pc-8801-rom-1240", "pc88-rom1900-300docs"],
    "pc98": ["NeoKobe-NecPc-98012017-11-17"],
    "fmtowns": ["fujitsu_fm_towns_series",
                "neo_kobe_fujitsu_fm_towns_2016-02-25-repack_20200803"],

    # ============== Handhelds raros / portables ==============
    "ngpc": ["SNK_NeoGeo_Pocket_TOSEC_2012_04_23"],
    "ngp": ["SNK_NeoGeo_Pocket_TOSEC_2012_04_23"],
    "pokemini": ["nintendo-pokemon-mini-champion-collection"],
    "gamecom": ["gamecom_202211", "Tiger_Game_Com_TOSEC_2012_04_23"],
    "megaduck": ["Creatronic_Mega_Duck_and_Cougar_Boy_TOSEC_2012_04_23"],
    "gameking": ["game_king_rom_set_analogue_pocket"],
    "supervision": ["Watara_Supervision_TOSEC_2012_04_23"],
    "gp32": ["openhandhelds032019"],
    "gp2x": ["openhandhelds032019"],
    "caanoo": ["openhandhelds032019"],
    "ngage": ["ngagecrackedgamescollection"],
    "vmu": ["segavmu"],
    "pico": ["sega-pico-tosec", "Sega_Pico_TOSEC_2012_04_13"],
    "vsmile": ["vsmile_202401", "VSmile_201809"],
    "leapster": ["leapster-explorer-roms", "LeapfrogLeapsterLearningGameSystem"],
    "didj": ["didj-roms"],

    # ============== Consolas asiáticas / oscuras ==============
    "casioloopy": ["casio-loopy-roms-complete-set-verified-2023"],
    "cdi": ["philips-cd-i_tosec-2012-07-13",
            "philips-cd-i-1g1r-chd-perfect-collection",
            "cdi-chd"],
    "cdtv": ["Amiga_CDTV_TOSEC_2009_04_18"],
    "playdia": ["bandai_playdia_quick_interactive_system"],
    "pippin": ["non-redump_apple-bandai_pippin"],
    "arcadia": ["Emerson_Arcadia_2001_TOSEC_2012_04_23"],
    "astrocade": ["Bally_Professional_Arcade_and_Astrocade_TOSEC_2012_04_23"],
    "odyssey2": ["Magnavox_Odyssey_2_TOSEC_2012_04_23"],
    "aquarius": ["Mattel_Aquarious_TOSEC_2012_04_23"],
    "sordm5": ["Sord_M5_TOSEC_2012_04_23"],
    "crvision": ["VTech_Laser_2001_and_CreatiVision_TOSEC_2012_04_23"],
    "vc4000": ["IVC4000_BT"],
    "gx4000": ["Amstrad_GX4000_TOSEC_2012_04_23",
               "amstrad-gx4000-champion-collection"],
    "vis": ["memorex_visual_information_system"],
    "gamate": ["58GamateROMsGamateBIOS"],
    "pcfx": ["game-pce-pcfx-collection"],

    # ============== Ordenadores 8/16-bit adicionales ==============
    "atari8": ["Atari800RomCollectionByGhostware",
               "Atari_8_bit_TOSEC_2012_04_23"],
    "electron": ["Acorn_Electronic_TOSEC_2012_04_23",
                 "acorn-electron-games-uef"],
    "archimedes": ["Acorn_Archimedes_TOSEC_2012_04_23",
                   "acorn_archimedes"],
    "samcoupe": ["Sam_Coupe_TOSEC_2012_04_23"],
    "ql": ["Sinclair_QL_TOSEC_2012_04_23"],
    "dragon32": ["Dragon_Data_Dragon_TOSEC_2012_04_23"],
    "enterprise": ["Enterprise_64_and_128_TOSEC_2012_04_23"],
    "jupiterace": ["Jupiter_Cantab_Jupiter_Ace_TOSEC_2012_04_23"],
    "memotech": ["Memotech_MTX_MTX_512_TOSEC_2012_04_23"],
    "pc6001": ["Neo_Kobe_NEC_PC-6001_2016-02-25",
               "NEC_PC_6001_TOSEC_2012_04_23"],
    "mz700": ["Sharp_MZ-700_TOSEC_2012_04_23"],
    "mz800": ["Sharp_MZ-800_and_MZ-1500_TOSEC_2012_04_23"],
    "x1": ["Sharp_X1_TOSEC_2012_04_23"],
    "tatung": ["Tatung_Einstein_TC-01_TOSEC_2012_04_23"],
    "camputers": ["Camputers_Lynx_TOSEC_2012_04_23"],
    "p2000": ["Philips_P2000_TOSEC_2012_04_23"],
    "exidy": ["Exidy_Sorcerer_TOSEC_2012_04_23"],
    "nascom": ["NASCOM_1_and_2_TOSEC_2012_04_23"],
    "trs80": ["Tandy_TRS80_Color_Computer_TOSEC_2012_04_23"],
    "fm7": ["Fujitsu_FM-7_TOSEC_2012_04_23"],
    "bbcmaster": ["Acorn_BBC_TOSEC_2012_04_23"],

    # ============== Calculadoras programables ==============
    "ti83": ["ti83p-calculator"],
}

# Extensiones administrativas a ignorar
_IGNORE_SUFFIX = (
    "_files.xml",
    "_meta.xml",
    "_meta.sqlite",
    "_reviews.xml",
    ".torrent",
    ".sqlite",
)

# Extensiones consideradas ROM/ISO/disco/cinta jugables. Filtramos por estas
# para no devolver thumbnails (png/jpg), manuales (pdf), etc.
ROM_EXTS = frozenset({
    # genéricos
    "zip", "7z", "rar", "gz", "tar", "lzh", "lha", "rom", "bin", "img", "iso",
    # discos
    "cue", "chd", "rvz", "nkit", "wbfs", "wad", "cdi", "gdi", "mds", "mdf",
    # nintendo
    "nes", "fds", "unf", "unif", "smc", "sfc", "fig",
    "n64", "z64", "v64", "ndd",
    "gb", "gbc", "gba", "agb", "elf", "dol",
    "nds", "dsi", "cia", "3ds", "cci", "cxi",
    # sega
    "sms", "gg", "md", "smd", "gen", "32x", "sg",
    # snk / nec / bandai
    "neo", "pce", "tg16", "ngp", "ngc", "ws", "wsc",
    # atari
    "a26", "a52", "a78", "lnx", "lyx", "j64", "jag",
    # otros consolas
    "vb", "vec", "int", "col", "vcs", "min", "pico", "tgc", "vmu",
    "isz", "i01", "i02", "i03", "i04",  # PC-FX
    "83p", "83g", "89p", "89g", "tig",  # calculadoras TI
    # microsoft
    "xbe", "xex",
    # micro-ordenadores
    "adf", "adz", "ipf", "lzx", "dms",
    "tap", "tzx", "z80", "sna", "scl", "trd", "dsk", "mgt",
    "d64", "d71", "d81", "t64", "prg", "crt", "g64",
    "cdt", "cpc", "voc",
    "st", "stt", "stx", "msa", "ima",
    "do", "po", "2mg", "woz", "hdv", "nib", "a2r",
    "ssd", "dsd", "uef",
    "exe", "com", "bat",
})

# Cache en memoria por sesión: identifier -> lista de archivos
_FILE_CACHE: dict[str, list[dict]] = {}

# Cache del listado interno de cada ZIP grande:
#   "<identifier>::<zipname>" -> [{"name": <internal path>, "url": ..., "size": ...}]
_ZIP_BROWSE_CACHE: dict[str, list[dict]] = {}


class ArchivePacksSource(Source):
    name = "Archive.org packs"
    base_url = "https://archive.org"

    async def search(
        self, client: httpx.AsyncClient, query: str, system: str | None = None
    ) -> list[RomResult]:
        if not system:
            return []
        ids = PACKS_BY_SYSTEM.get(system.lower())
        if not ids:
            return []

        chunks = await asyncio.gather(
            *(self._files(client, ident) for ident in ids),
            return_exceptions=True,
        )

        q_low = query.lower()
        results: list[RomResult] = []
        # Para packs monolíticos (single-zip TOSEC), recogemos los zips
        # principales para luego browse-arlos en paralelo.
        monolithic_targets: list[tuple[str, dict]] = []
        monolithic_fallback: list[RomResult] = []

        for ident, files in zip(ids, chunks):
            if isinstance(files, Exception):
                continue
            is_monolithic = 0 < len(files) <= 5
            for f in files:
                name = f.get("name", "")
                if not name:
                    continue
                size = f.get("size")
                result = RomResult(
                    title=name[:120],
                    system=system.upper(),
                    source=f"{self.name} ({ident})",
                    page_url=f"{self.base_url}/details/{ident}",
                    download_url=f"{self.base_url}/download/{ident}/{quote(name)}",
                    size=_human_size(size) if size else None,
                )
                if q_low in name.lower():
                    results.append(result)
                    if len(results) >= 15:
                        return results
                elif is_monolithic:
                    monolithic_fallback.append(result)
                    # Si es un .zip grande, lo marcamos para browse interno.
                    if name.lower().endswith(".zip") and _is_big(size):
                        monolithic_targets.append((ident, f))

        # Browse interno de los zips monolíticos: nos da los juegos sueltos.
        if monolithic_targets and len(results) < 15:
            browse_chunks = await asyncio.gather(
                *(self._browse_zip(client, ident, f["name"])
                  for ident, f in monolithic_targets),
                return_exceptions=True,
            )
            for (ident, _zip), entries in zip(monolithic_targets, browse_chunks):
                if isinstance(entries, Exception):
                    continue
                for e in entries:
                    name = e["name"]
                    if q_low not in name.lower():
                        continue
                    leaf = name.rsplit("/", 1)[-1]
                    if leaf.rsplit(".", 1)[-1].lower() not in ROM_EXTS:
                        continue
                    results.append(RomResult(
                        title=leaf[:120],
                        system=system.upper(),
                        source=f"{self.name} ({ident}/zip)",
                        page_url=f"{self.base_url}/details/{ident}",
                        download_url=e["url"],
                        size=_human_size(e["size"]) if e["size"] else None,
                    ))
                    if len(results) >= 15:
                        return results

        # Rellenar con el pack entero como último recurso
        if len(results) < 15 and monolithic_fallback:
            results.extend(monolithic_fallback[: 15 - len(results)])
        return results

    async def _browse_zip(
        self, client: httpx.AsyncClient, identifier: str, zipname: str
    ) -> list[dict]:
        """Lista los archivos dentro de un .zip alojado en archive.org.
        Usa el endpoint /download/<id>/<zip>/ que devuelve HTML con la tabla
        de contenidos."""
        key = f"{identifier}::{zipname}"
        if key in _ZIP_BROWSE_CACHE:
            return _ZIP_BROWSE_CACHE[key]

        url = f"{self.base_url}/download/{identifier}/{quote(zipname)}/"
        try:
            r = await client.get(url, timeout=60)
            r.raise_for_status()
        except httpx.HTTPError:
            return []

        tree = HTMLParser(r.text)
        entries: list[dict] = []
        for a in tree.css("table a[href]"):
            href = a.attributes.get("href", "")
            if "/download/" not in href:
                continue
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://archive.org" + href
            name = a.text(strip=True)
            if not name:
                continue
            # Tamaño está en <td id="size"> del mismo <tr>
            tr = a.parent
            for _ in range(4):
                if tr is None or tr.tag == "tr":
                    break
                tr = tr.parent
            size = None
            if tr is not None and tr.tag == "tr":
                size_td = tr.css_first('td[id="size"]')
                if size_td:
                    size = size_td.text(strip=True)
            entries.append({"name": name, "url": href, "size": size})

        _ZIP_BROWSE_CACHE[key] = entries
        return entries

    async def _files(self, client: httpx.AsyncClient, identifier: str) -> list[dict]:
        if identifier in _FILE_CACHE:
            return _FILE_CACHE[identifier]
        try:
            r = await client.get(f"{self.base_url}/metadata/{identifier}")
            r.raise_for_status()
            files = r.json().get("files", [])
        except (httpx.HTTPError, ValueError):
            return []

        roms = [
            f
            for f in files
            if (n := f.get("name", ""))
            and not n.startswith("__")
            and not n.endswith(_IGNORE_SUFFIX)
            and n.rsplit(".", 1)[-1].lower() in ROM_EXTS
        ]
        _FILE_CACHE[identifier] = roms
        return roms


def _is_big(size, threshold_bytes: int = 100_000) -> bool:
    """True si el archivo es lo bastante grande para que valga la pena
    browse-arlo (típicamente un .zip TOSEC con muchos juegos dentro)."""
    try:
        return float(size) >= threshold_bytes
    except (TypeError, ValueError):
        return False


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
