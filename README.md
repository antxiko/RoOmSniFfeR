# RoOmSniffeR 🐕‍🦺

Bot de Telegram que olfatea ROMs por internet y te da el enlace de descarga
**directo al archivo individual** — no a la página, no al pack entero, al ROM
concreto. Cubre **120+ sistemas** entre consolas, ordenadores 8/16-bit,
handhelds raros y arcade.

## Qué hace

- `/buscar <sistema> <nombre>` — busca el ROM en varias fuentes a la vez
  y devuelve botones inline que abren el enlace de descarga.
- `/sistemas` — lista de sistemas soportados, agrupados por familia.
- `/help` — ayuda.
- **Modo inline**: escribe `@RoOmSniFfeR_Bot snes mario` desde cualquier
  chat (de Telegram). El bot te ofrece una lista de resultados que puedes
  enviar al chat con un toque, sin abrir el bot.

Para sistemas con **packs monolíticos** (TOSEC en un solo `.zip`), el bot
abre el contenido del ZIP remotamente y devuelve el enlace al juego concreto
dentro del archivo, sin tener que descargarte todo el pack.

## Ejemplos

```
/buscar snes super mario world
/buscar amiga monkey island
/buscar msx metal gear
/buscar arcade sf2
/buscar supervision snake          ← entra dentro del TOSEC.zip
/buscar samcoupe manic miner       ← idem
/buscar arcadia alien invaders
/buscar pico sonic
/buscar pcengine bonk
/buscar megadrive shinobi          ← alias: megadrive → md
/buscar intellivision astrosmash   ← alias: intellivision → intv
```

## Fuentes

| Fuente | Cobertura | Cómo entrega |
|---|---|---|
| **Archive.org packs** | 120+ sistemas con packs curados (mayoría Ghostware/CentralArquivista/TOSEC) | Enlace directo al ROM individual, incluso si está dentro de un `.zip` grande (browse interno via HTML listing) |
| **Internet Archive** | Sistemas con colección dedicada (`softwarelibrary_amiga`, `consolelivingroom`, `internetarcade`, etc.) | Enlace al item descargable |
| **CDRomance** | Consolas modernas (PS1/PS2/PSP, GBA, NDS, Wii, GameCube, etc.) | Enlace a la página del juego |

Cada fuente vive en [sources/](sources/) e implementa la misma interfaz
`Source.search(client, query, system)`. Añadir una fuente nueva es crear un
archivo y registrarlo en [sources/__init__.py](sources/__init__.py).

## Limpieza de resultados

El bot evita el ruido típico de archive.org:

- **Solo ROMs jugables**: filtra por extensión (`.zip`, `.iso`, `.adf`,
  `.d64`, `.tap`, `.stx`, `.cci`, etc. — 80+ extensiones reconocidas).
  No devuelve thumbnails, manuales, scans, soundtracks ni magazines.
- **Sólo el sistema pedido**: si filtras por sistema, no se cuelan resultados
  de otras consolas. Para colecciones genéricas (`consolelivingroom` mezcla
  NES/SNES/N64/etc.), se descarta cualquier resultado cuyo título mencione
  otro sistema (`(SNES)`, `(NES)`, etc.).
- **Sin búsqueda libre**: si pides un sistema raro y no hay colección
  dedicada, el bot no hace búsqueda genérica (que devolvía PC, SNES, etc.
  con el mismo nombre). Solo responde lo que tienen los packs específicos.

## Sistemas soportados

123 sistemas reconocidos, 135+ aliases. Pulsa `/sistemas` en el bot para
verlos agrupados. Algunos destacados:

- **Nintendo**: NES, FDS, SNES, N64, GB, GBC, GBA, NDS, 3DS, GameCube, Wii,
  Virtual Boy, Game & Watch, Pokémon Mini
- **Sega**: Master System, Game Gear, Mega Drive, 32X, Mega CD, Saturn,
  Dreamcast, Pico, VMU
- **Sony**: PS1, PS2, PS3, PSP
- **Microsoft**: Xbox, Xbox 360
- **SNK / arcade**: Neo Geo, NGP, NGPC, MAME, FBN, Naomi, CPS1
- **Otras consolas**: 3DO, Atari 2600/5200/7800, Jaguar, Lynx, PC Engine,
  PC-FX, WonderSwan, Vectrex, Intellivision, ColecoVision, Channel F,
  Arcadia 2001, Bally Astrocade, Magnavox Odyssey 2, Mattel Aquarius,
  Sord M5, CreatiVision, VC 4000, Casio Loopy, Philips CD-i, Commodore CDTV,
  Bandai Playdia, Apple Bandai Pippin, Memorex VIS, Gamate, Watara
  Supervision, Mega Duck, GameKing, Tiger Game.com
- **Handhelds modernos**: GP32, GP2X, Caanoo, Nokia N-Gage, V.Smile,
  Leapster, Didj
- **Ordenadores 8/16-bit**: Amiga, C64, VIC-20, MSX/MSX2, ZX Spectrum,
  ZX81, Atari 800, Atari ST, Apple II/IIgs, Amstrad CPC/GX4000, Tandy CoCo,
  TRS-80, BBC Micro/Master, Acorn Electron, Archimedes, SAM Coupé,
  Sinclair QL, Dragon 32, Enterprise, Jupiter Ace, Memotech, Tatung
  Einstein, Camputers Lynx, Philips P2000, Exidy Sorcerer, NASCOM, Oric,
  Thomson MO5/TO7/TO8
- **PC / 16-bit**: MS-DOS, PC-88, PC-98, FM Towns, Sharp X1, X68000, FM-7,
  MZ-700, MZ-800, NEC PC-6001, TI-99/4A
- **Calculadoras**: TI-83 Plus

## Setup (local)

```bash
git clone https://github.com/antxiko/RoOmSniFfeR.git
cd RoOmSniFfeR
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# pega el token de @BotFather en .env
python bot.py
```

Requisitos: Python 3.10+ (probado en 3.14), token de bot de Telegram.

### Activar modo inline (opcional pero recomendado)

En [@BotFather](https://t.me/BotFather):

1. `/setinline` → elige tu bot
2. Escribe un placeholder, ej: `sistema juego`
3. Listo — ya puedes usar `@TuBot zelda n64` desde cualquier chat

## Desplegar en VPS (Linux + systemd)

Ver [deploy/INSTALL.md](deploy/INSTALL.md) para la guía paso a paso. Incluye:

- Usuario dedicado sin shell
- Service unit con auto-reinicio y hardening (`ProtectSystem`, `NoNewPrivileges`, etc.)
- Logs en journald
- Procedimiento de actualización con `git pull` + `systemctl restart`

## Estructura

```
RoOmSniFfeR/
├── bot.py                    # handlers (/buscar /sistemas /help + inline), parser, aliases
├── sources/
│   ├── __init__.py           # registro ALL_SOURCES
│   ├── base.py               # Source ABC, RomResult, make_client
│   ├── archive_org.py        # API JSON archive.org con filtro por colección
│   ├── archive_packs.py      # browse interno de packs y zips TOSEC
│   └── cdromance.py          # scraping cdromance.com por categoría
├── deploy/
│   ├── roomsniffer.service   # systemd unit file
│   └── INSTALL.md            # guía despliegue en VPS
├── requirements.txt
├── .env.example
├── LICENSE                   # GPL-3.0
└── README.md
```

## Cómo funciona el browse interno de ZIPs

Cuando un pack es un único `.zip` grande (típico TOSEC de sistemas oscuros),
el bot llama a `archive.org/download/<id>/<zip>/` que devuelve el HTML con
el listado del contenido del ZIP. Parsea la tabla, cachea en memoria, y
construye URLs del tipo:

```
https://archive.org/download/<id>/<zipfile>/Carpeta%2FJuego.zip
```

archive.org sirve el archivo extraído al vuelo desde dentro del ZIP. La
primera búsqueda por sistema descarga ~150 KB de HTML; las siguientes son
instantáneas (cache en memoria por sesión).

## Caveats

- La primera búsqueda a sistemas con packs grandes (xbox, x360, arcade)
  tarda 4-7 s mientras descarga el metadata; después está cacheada.
- Algunos juegos están catalogados en TOSEC con su nombre original
  (japonés/literal) y no coinciden con la búsqueda en castellano/inglés
  común. Ejemplo: en MSX `Knightmare` figura como `Majyo Densetsu`.
- Myrient (myrient.erista.me) **cerró el 31-mar-2026**. No se usa como
  fuente.
- Vimm's Lair cambió su endpoint y empezó a devolver 404 en `?p=list`.
  Tampoco se usa.

## Stack

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 21.x
- [httpx](https://www.python-httpx.org) — HTTP async
- [selectolax](https://github.com/rushter/selectolax) — parser HTML rápido
  (lexbor)
- [python-dotenv](https://github.com/theskumar/python-dotenv) — `.env`

## Licencia

[GPL-3.0](LICENSE).

## Aviso legal

Este bot indexa enlaces públicos que ya existen en internet. No aloja
contenido. El estado de copyright de los ROMs depende del título y la
jurisdicción del usuario. Úsalo con cabeza.
