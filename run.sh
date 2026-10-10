#!/usr/bin/env bash
#
# Skrypt uruchamiający Kafelkowy Monitor Zasobów Pulpitu (Zorin Desktop Monitor)
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$HOME/.config/zorin-monitor"
if ! mkdir -p "$PID_DIR" 2>/dev/null; then
    PID_DIR="/tmp/zorin-monitor-${USER}"
    mkdir -p "$PID_DIR" 2>/dev/null || PID_DIR="/tmp"
fi
PID_FILE="${PID_DIR}/zorin-monitor.pid"

# Sprawdź czy proces już działa
check_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            return 0
        fi
    fi
    # Sprawdź też przez pgrep dla pewności
    PG_PID=$(pgrep -f "${SCRIPT_DIR}/main.py" | head -n 1)
    if [ -n "$PG_PID" ]; then
        echo "$PG_PID" > "$PID_FILE"
        return 0
    fi
    return 1
}

# Zatrzymaj monitor: najpierw SIGTERM (zapis konfiguracji), po 3 s SIGKILL
stop_monitor() {
    pkill -TERM -f "${SCRIPT_DIR}/main.py" 2>/dev/null || return 0
    for _ in $(seq 1 30); do
        pgrep -f "${SCRIPT_DIR}/main.py" >/dev/null || return 0
        sleep 0.1
    done
    pkill -KILL -f "${SCRIPT_DIR}/main.py" 2>/dev/null || true
}

# Analiza argumentów
IS_DAEMON=0
IS_RESTART=0
IS_STOP=0

for arg in "$@"; do
    case "$arg" in
        --daemon|-d) IS_DAEMON=1 ;;
        --restart|restart) IS_RESTART=1 ;;
        --stop|stop) IS_STOP=1 ;;
        --reset-below) IS_RESET_BELOW=1 ;;
    esac
done

# Awaryjne wyłączenie trybu "Zawsze na spodzie" (widget nie reaguje wtedy na mysz)
if [ "${IS_RESET_BELOW:-0}" -eq 1 ]; then
    stop_monitor
    rm -f "$PID_FILE"
    CONFIG_FILE="$HOME/.config/zorin-monitor/config.json"
    [ -f "$CONFIG_FILE" ] && sed -i 's/"keep_below": true/"keep_below": false/' "$CONFIG_FILE"
    echo "[ZorinMonitor] Wyłączono tryb „Zawsze na spodzie”."
fi

# Obsługa argumentu zatrzymania
if [ "$IS_STOP" -eq 1 ]; then
    echo "[ZorinMonitor] Zatrzymywanie procesu..."
    stop_monitor
    rm -f "$PID_FILE"
    echo "[ZorinMonitor] Monitor został zatrzymany."
    exit 0
fi

# Obsługa restartu
if [ "$IS_RESTART" -eq 1 ]; then
    echo "[ZorinMonitor] Restartowanie monitora..."
    stop_monitor
    rm -f "$PID_FILE"
fi

# Jeśli już działa i nie był restart, poinformuj użytkownika
if check_running; then
    PID=$(cat "$PID_FILE")
    echo "[ZorinMonitor] Monitor już działa w tle (PID: $PID)."
    exit 0
fi

LOG_FILE="/tmp/zorin-monitor.log"

# Ustawienie backendu GDK dla wsparcia warstwy pulpitu w Zorin OS / GNOME
export GDK_BACKEND="x11"

# Uruchomienie w tle (tryb daemon / autostart)
if [ "$IS_DAEMON" -eq 1 ]; then
    echo "[ZorinMonitor] Uruchamianie w tle..."
    setsid python3 -u "${SCRIPT_DIR}/main.py" >> "$LOG_FILE" 2>&1 &
    PID=$!
    disown $PID 2>/dev/null || true
    echo "$PID" > "$PID_FILE"
    echo "[ZorinMonitor] Uruchomiono pomyślnie w tle (PID: $PID)."
    exit 0
fi

# Domyślne uruchomienie (skrypt czeka na zakończenie monitora)
python3 -u "${SCRIPT_DIR}/main.py" >> "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"
echo "[ZorinMonitor] Kafelkowy monitor uruchomiony (PID: $PID)."
trap 'kill -TERM "$PID" 2>/dev/null' INT TERM
wait "$PID" 2>/dev/null
wait "$PID" 2>/dev/null   # ponownie, jeśli pierwszy wait przerwał sygnał
rm -f "$PID_FILE"
