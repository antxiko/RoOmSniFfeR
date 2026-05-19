from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from html import escape

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
)

from sources import ALL_SOURCES, RomResult
from sources.base import make_client

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("roomsniffer")

SYSTEMS = [
    # Nintendo
    "nes", "snes", "n64", "gb", "gbc", "gba", "nds", "3ds",
    "gcn", "wii", "fds", "vb",
    # Sega
    "md", "genesis", "sms", "32x", "megacd", "dreamcast", "saturn", "gamegear",
    # Sony / Microsoft / SNK
    "ps1", "psx", "ps2", "psp", "xbox", "x360", "neogeo",
    # Ordenadores
    "amiga", "c64", "msx", "zx", "spectrum", "spectrum128", "zx81",
    "atari", "atarist", "apple2", "applegs", "cpc", "coco",
    "msdos", "dos", "pc", "bbc", "ti99", "vic20", "oric",
    "thomson", "x68000", "pc88", "pc98", "fmtowns", "vic20",
    # Ordenadores adicionales
    "atari8", "electron", "archimedes", "samcoupe", "ql", "dragon32",
    "enterprise", "jupiterace", "memotech", "pc6001", "mz700", "mz800",
    "x1", "tatung", "camputers", "p2000", "exidy", "nascom", "trs80",
    "fm7", "bbcmaster",
    # Consolas misceláneas
    "vectrex", "intv", "colecovision", "pcengine", "wonderswan", "3do",
    "atari2600", "atari5200", "atari7800", "jaguar", "lynx", "channelf",
    "gameandwatch", "ps3",
    # Handhelds raros
    "ngpc", "ngp", "pokemini", "gamecom", "megaduck", "gameking",
    "supervision", "gp32", "gp2x", "caanoo", "ngage", "vmu", "pico",
    "vsmile", "leapster", "didj",
    # Consolas asiáticas / oscuras
    "casioloopy", "cdi", "cdtv", "playdia", "pippin", "arcadia",
    "astrocade", "odyssey2", "aquarius", "sordm5", "crvision",
    "vc4000", "gx4000", "vis", "gamate", "pcfx",
    # Calculadoras
    "ti83",
    # Arcade
    "arcade", "mame",
]

# Aliases: nombre escrito por el usuario -> sistema canónico de la lista.
# Permite que /buscar intellivision foo funcione igual que /buscar intv foo.
SYSTEM_ALIASES: dict[str, str] = {
    "intellivision": "intv",
    "coleco": "colecovision",
    "megadrive": "md",
    "mega-drive": "md",
    "genesis": "md",
    "gameboy": "gb",
    "game-boy": "gb",
    "gameboycolor": "gbc",
    "gameboyadvance": "gba",
    "supernintendo": "snes",
    "snestendo": "snes",
    "nintendo64": "n64",
    "gamecube": "gcn",
    "playstation": "ps1",
    "ps": "ps1",
    "psone": "ps1",
    "playstation2": "ps2",
    "playstation3": "ps3",
    "playstationportable": "psp",
    "turbografx": "pcengine",
    "tg16": "pcengine",
    "pce": "pcengine",
    "ws": "wonderswan",
    "ngp": "wonderswan",
    "amstrad": "cpc",
    "amstradcpc": "cpc",
    "zxspectrum": "spectrum",
    "commodore64": "c64",
    "commodore": "c64",
    "amiga500": "amiga",
    "amiga1200": "amiga",
    "appleii": "apple2",
    "apple": "apple2",
    "appleiigs": "applegs",
    "atarist": "atarist",  # ya es canónico
    "vcs": "atari2600",
    "a2600": "atari2600",
    "mastersystem": "sms",
    "segamastersystem": "sms",
    "segagenesis": "md",
    "segacd": "megacd",
    "segasaturn": "saturn",
    "segadreamcast": "dreamcast",
    "ggear": "gamegear",
    "gg": "gamegear",
    "nintendods": "nds",
    "famicomdisksystem": "fds",
    "famicom": "nes",
    "snk": "neogeo",
    "neogeoaes": "neogeo",
    "neo-geo": "neogeo",
    "virtualboy": "vb",
    "panasonic3do": "3do",
    "panasonic": "3do",
    "fairchild": "channelf",
    "channel-f": "channelf",
    "gameandwatch": "gameandwatch",
    "g&w": "gameandwatch",
    "fmtowns": "fmtowns",
    "fm-towns": "fmtowns",
    "fujitsu": "fmtowns",
    "vic-20": "vic20",
    "trs80": "coco",
    "tandy": "coco",
    "tandycoco": "coco",
    "acorn": "bbc",
    "bbcmicro": "bbc",
    "ti-99": "ti99",
    "ti994a": "ti99",
    "ti-994a": "ti99",
    # Handhelds raros / aliases comunes
    "neogeopocket": "ngp",
    "neo-geo-pocket": "ngp",
    "neogeopocketcolor": "ngpc",
    "pokemonmini": "pokemini",
    "tigergamecom": "gamecom",
    "game.com": "gamecom",
    "wataracsupervision": "supervision",
    "nokian-gage": "ngage",
    "n-gage": "ngage",
    "segavmu": "vmu",
    "dreamcastvmu": "vmu",
    "segapico": "pico",
    "leappad": "leapster",
    "leapfrog": "leapster",
    # Asiáticas / oscuras
    "casio-loopy": "casioloopy",
    "loopy": "casioloopy",
    "cd-i": "cdi",
    "philipscdi": "cdi",
    "commodorecdtv": "cdtv",
    "bandaiplaydia": "playdia",
    "applepippin": "pippin",
    "bandaipippin": "pippin",
    "arcadia2001": "arcadia",
    "ballyastrocade": "astrocade",
    "magnavoxodyssey": "odyssey2",
    "videopac": "odyssey2",
    "mattelaquarius": "aquarius",
    "sord": "sordm5",
    "m5": "sordm5",
    "creativision": "crvision",
    "vtechcreativision": "crvision",
    "interton": "vc4000",
    "amstradgx4000": "gx4000",
    "memorexvis": "vis",
    "vbcorp-gamate": "gamate",
    "necpcfx": "pcfx",
    "pc-fx": "pcfx",
    # Ordenadores 8/16-bit
    "atari800": "atari8",
    "atari-xl": "atari8",
    "atarixe": "atari8",
    "acornelectron": "electron",
    "acornarchimedes": "archimedes",
    "amstradpcw": "pcw",
    "samcoupé": "samcoupe",
    "samcoupe": "samcoupe",
    "sinclairql": "ql",
    "dragondata": "dragon32",
    "dragon": "dragon32",
    "jupiter": "jupiterace",
    "memotechmtx": "memotech",
    "necpc-6001": "pc6001",
    "pc-6001": "pc6001",
    "sharpmz-700": "mz700",
    "sharpmz700": "mz700",
    "sharpmz-800": "mz800",
    "sharpmz800": "mz800",
    "sharpx1": "x1",
    "tatungeinstein": "tatung",
    "camputerslynx": "camputers",
    "philipsp2000": "p2000",
    "exidysorcerer": "exidy",
    "trs-80": "trs80",
    "fujitsufm7": "fm7",
    "bbcmaster": "bbcmaster",
    # Calculadoras
    "ti-83": "ti83",
    "ti83plus": "ti83",
}

HELP_TEXT = (
    "<b>RoOmSniffeR</b> 🐕‍🦺\n\n"
    "Busco enlaces de ROMs en varias fuentes públicas (consolas, ordenadores y arcade).\n\n"
    "<b>Comandos:</b>\n"
    "• <code>/buscar &lt;nombre&gt;</code> — busca en todas las fuentes\n"
    "• <code>/buscar &lt;sistema&gt; &lt;nombre&gt;</code> — filtra por sistema\n"
    "• <code>/sistemas</code> — lista de sistemas soportados\n\n"
    "<b>Ejemplos:</b>\n"
    "<code>/buscar snes super mario</code>\n"
    "<code>/buscar amiga monkey island</code>\n"
    "<code>/buscar msdos doom</code>\n"
    "<code>/buscar arcade pacman</code>\n"
    "<code>/buscar spectrum jet set willy</code>"
)


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_html(HELP_TEXT)


SYSTEM_GROUPS: list[tuple[str, list[str]]] = [
    ("Nintendo", ["nes", "fds", "snes", "n64", "gb", "gbc", "gba", "nds",
                  "3ds", "gcn", "wii", "vb", "gameandwatch", "pokemini"]),
    ("Sega", ["sms", "gamegear", "md", "32x", "megacd", "saturn",
              "dreamcast", "pico", "vmu"]),
    ("Sony", ["ps1", "ps2", "ps3", "psp"]),
    ("Microsoft", ["xbox", "x360"]),
    ("SNK / Arcade", ["neogeo", "ngp", "ngpc", "arcade", "mame"]),
    ("Otras consolas", ["3do", "atari2600", "atari5200", "atari7800",
                        "jaguar", "lynx", "pcengine", "pcfx", "wonderswan",
                        "vectrex", "intv", "colecovision", "channelf",
                        "arcadia", "astrocade", "odyssey2", "aquarius",
                        "sordm5", "crvision", "vc4000", "casioloopy",
                        "cdi", "cdtv", "playdia", "pippin",
                        "vis", "gamate", "supervision", "megaduck",
                        "gameking", "gamecom"]),
    ("Handhelds modernos", ["gp32", "gp2x", "caanoo", "ngage", "vsmile",
                            "leapster", "didj"]),
    ("Ordenadores 8/16-bit", ["amiga", "c64", "vic20", "msx", "spectrum",
                              "spectrum128", "zx81", "atari", "atari8",
                              "atarist", "apple2", "applegs", "cpc",
                              "gx4000", "coco", "trs80", "bbc", "bbcmaster",
                              "electron", "archimedes", "samcoupe", "ql",
                              "dragon32", "enterprise", "jupiterace",
                              "memotech", "tatung", "camputers", "p2000",
                              "exidy", "nascom", "oric", "thomson"]),
    ("Ordenadores PC / 16-bit", ["msdos", "dos", "pc", "pc88", "pc98",
                                  "fmtowns", "x68000", "fm7", "mz700",
                                  "mz800", "x1", "pc6001", "ti99"]),
    ("Calculadoras", ["ti83"]),
]


async def systems_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    # Usamos <pre> para que Telegram NO auto-detecte palabras como c64, pc88,
    # ti99 etc. como posibles dominios/tags y las subraye.
    lines = ["<b>Sistemas soportados:</b>"]
    for label, items in SYSTEM_GROUPS:
        lines.append(f"\n<b>{label}</b>")
        lines.append(f"<pre>{', '.join(items)}</pre>")
    lines.append(
        f"\n<i>{len(SYSTEMS)} sistemas · {len(SYSTEM_ALIASES)} aliases reconocidos</i>"
    )
    await update.effective_message.reply_html("\n".join(lines))


def _as_system(word: str) -> str | None:
    """Devuelve el sistema canónico si `word` es un sistema/alias, else None."""
    w = word.lower()
    canonical = SYSTEM_ALIASES.get(w, w)
    return canonical if canonical in SYSTEMS else None


def parse_args(args: list[str]) -> tuple[str | None, str]:
    """Acepta el sistema al principio O al final. Si ambos, gana el primero.
    Ejemplos:
      ["snes","mario"]  -> ("snes", "mario")
      ["mario","snes"]  -> ("snes", "mario")
      ["mario"]         -> (None, "mario")
    """
    if not args:
        return None, ""
    # Probar primera palabra
    sys_first = _as_system(args[0])
    if sys_first:
        return sys_first, " ".join(args[1:]).strip()
    # Probar última palabra (si hay más de una)
    if len(args) >= 2:
        sys_last = _as_system(args[-1])
        if sys_last:
            return sys_last, " ".join(args[:-1]).strip()
    return None, " ".join(args).strip()


async def search_all(query: str, system: str | None) -> list[RomResult]:
    async with make_client() as client:
        coros = [src.search(client, query, system) for src in ALL_SOURCES]
        chunks = await asyncio.gather(*coros, return_exceptions=True)

    results: list[RomResult] = []
    for src, chunk in zip(ALL_SOURCES, chunks):
        if isinstance(chunk, Exception):
            log.warning("%s falló: %s", src.name, chunk)
            continue
        results.extend(chunk)
    return results


def render_results(results: list[RomResult], query: str) -> tuple[str, InlineKeyboardMarkup | None]:
    if not results:
        q = escape(query)
        return (
            f"😶 Sin resultados para <b>{q}</b>.\n"
            f"Prueba con otro nombre o añade el sistema delante "
            f"(ej: <code>/buscar gba {q}</code>).",
            None,
        )

    lines = [f"🔎 <b>{len(results)}</b> resultados para <b>{escape(query)}</b>:\n"]
    buttons: list[list[InlineKeyboardButton]] = []
    for i, r in enumerate(results[:20], 1):
        size = f" · {r.size}" if r.size else ""
        direct = " 📎" if r.has_direct_download else ""
        lines.append(
            f"<b>{i}.</b> {escape(r.title)}\n"
            f"   <i>{escape(r.system)} · {escape(r.source)}{escape(size)}</i>{direct}"
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{i}. {r.title[:40]}",
                    url=r.best_url,
                )
            ]
        )

    lines.append("\n📎 = enlace de descarga directo · 🔗 = página del juego")
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    system, query = parse_args(context.args or [])
    if not query:
        await update.effective_message.reply_html(
            "Uso: <code>/buscar &lt;sistema&gt; &lt;nombre&gt;</code>\n"
            "Ej: <code>/buscar snes chrono trigger</code>\n"
            "También vale al final: <code>/buscar chrono trigger snes</code>"
        )
        return
    if not system:
        await update.effective_message.reply_html(
            f"🤔 Necesito un sistema para buscar <b>{escape(query)}</b>.\n\n"
            f"Ejemplos:\n"
            f"• <code>/buscar snes {escape(query)}</code>\n"
            f"• <code>/buscar {escape(query)} gba</code>\n\n"
            f"Lista de sistemas: /sistemas"
        )
        return

    msg = await update.effective_message.reply_html(f"🐕‍🦺 Olfateando <i>{escape(query)}</i>…")
    try:
        results = await search_all(query, system)
    except Exception as e:
        log.exception("búsqueda falló")
        await msg.edit_text(f"💥 Error: {e}")
        return

    text, kb = render_results(results, query)
    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True)


async def inline_query(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Modo inline: @RoOmSniFfeR_Bot <sistema> <juego> desde cualquier chat."""
    iq = update.inline_query
    if iq is None:
        return
    text = (iq.query or "").strip()

    if not text:
        # Mensaje de ayuda cuando aún no han escrito nada
        help_article = InlineQueryResultArticle(
            id="help",
            title="Escribe sistema y juego",
            description="Ej: snes mario · gba zelda · arcade pacman",
            input_message_content=InputTextMessageContent(
                "Uso: <code>@RoOmSniFfeR_Bot &lt;sistema&gt; &lt;juego&gt;</code>",
                parse_mode=ParseMode.HTML,
            ),
        )
        await iq.answer([help_article], cache_time=10, is_personal=False)
        return

    system, query = parse_args(text.split())
    if not query:
        await iq.answer([], cache_time=10, is_personal=False)
        return
    if not system:
        hint = InlineQueryResultArticle(
            id="nosys",
            title="Falta el sistema",
            description=f"Añade el sistema. Ej: snes {query}",
            input_message_content=InputTextMessageContent(
                f"Para buscar <b>{escape(query)}</b> indica un sistema "
                f"(ej: <code>snes {escape(query)}</code>).",
                parse_mode=ParseMode.HTML,
            ),
        )
        await iq.answer([hint], cache_time=10, is_personal=False)
        return

    try:
        # Telegram da 10s de timeout para inline; le dejamos 8s a las fuentes.
        results = await asyncio.wait_for(search_all(query, system), timeout=8.0)
    except asyncio.TimeoutError:
        log.info("inline timeout para %r/%r", system, query)
        results = []
    except Exception:
        log.exception("inline search falló")
        results = []

    articles: list[InlineQueryResultArticle] = []
    seen_ids: set[str] = set()
    for r in results[:30]:
        rid = hashlib.sha1(r.best_url.encode()).hexdigest()[:16]
        if rid in seen_ids:
            continue
        seen_ids.add(rid)
        size = f" · {r.size}" if r.size else ""
        direct = " 📎" if r.has_direct_download else ""
        message = (
            f"<b>{escape(r.title)}</b>\n"
            f"<i>{escape(r.system)} · {escape(r.source)}{escape(size)}</i>{direct}\n"
            f"{r.best_url}"
        )
        articles.append(
            InlineQueryResultArticle(
                id=rid,
                title=r.title[:60],
                description=f"{r.system} · {r.source}{size}"[:80],
                input_message_content=InputTextMessageContent(
                    message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                ),
            )
        )

    if not articles:
        articles = [
            InlineQueryResultArticle(
                id="noresults",
                title="Sin resultados",
                description=f"Nada encontrado para «{query}»",
                input_message_content=InputTextMessageContent(
                    f"Sin resultados para «{escape(query)}»."
                ),
            )
        ]

    await iq.answer(articles, cache_time=300, is_personal=False)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("excepción no manejada", exc_info=context.error)


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN (cópialo de BotFather al .env)")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("sistemas", systems_cmd))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_error_handler(on_error)

    log.info("Bot iniciado")
    # PTB 21.x usa asyncio.get_event_loop() y Python 3.14 ya no lo crea solo.
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
