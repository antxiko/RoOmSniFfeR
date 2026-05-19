# Despliegue en VPS Linux (systemd)

Asume Debian/Ubuntu o similar con `systemd`. Adapta paths/usuarios a tu gusto.

## 1. Preparar usuario y directorio

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin roomsniffer
sudo mkdir -p /opt/roomsniffer
sudo chown roomsniffer:roomsniffer /opt/roomsniffer
```

## 2. Clonar y crear venv

```bash
sudo -u roomsniffer git clone https://github.com/antxiko/RoOmSniFfeR.git /opt/roomsniffer
cd /opt/roomsniffer
sudo -u roomsniffer python3 -m venv .venv
sudo -u roomsniffer .venv/bin/pip install --upgrade pip
sudo -u roomsniffer .venv/bin/pip install -r requirements.txt
```

## 3. Configurar token

```bash
sudo -u roomsniffer cp .env.example .env
sudo -u roomsniffer nano .env   # pega el token de @BotFather
sudo chmod 600 /opt/roomsniffer/.env
```

## 4. Instalar el service

```bash
sudo cp /opt/roomsniffer/deploy/roomsniffer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now roomsniffer
```

## 5. Verificar

```bash
sudo systemctl status roomsniffer
sudo journalctl -u roomsniffer -f
```

## Actualizar a una versión nueva

```bash
cd /opt/roomsniffer
sudo -u roomsniffer git pull
sudo -u roomsniffer .venv/bin/pip install -r requirements.txt
sudo systemctl restart roomsniffer
```

## Notas

- El `EnvironmentFile=` carga `.env` directamente (formato `KEY=VALUE` por
  línea, sin comillas). systemd se queja si el archivo tiene comentarios
  raros.
- Si el bot crashea, systemd lo reinicia automáticamente a los 5 segundos.
- El service incluye hardening: no puede modificar el sistema, no tiene
  privilegios extra, sandbox de procesos.
- Logs van a journald: `journalctl -u roomsniffer -n 200 --no-pager`.
