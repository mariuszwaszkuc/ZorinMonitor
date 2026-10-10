#!/usr/bin/env bash
#
# Instalator Kafelkowego Monitora Pulpitu dla Zorin OS / GNOME
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"

echo "=========================================================="
echo "  Instalacja Kafelkowego Monitora Pulpitu (CPU/RAM/Dysk)  "
echo "=========================================================="

# Nadanie uprawnień wykonywalności
chmod +x "${SCRIPT_DIR}/main.py"
chmod +x "${SCRIPT_DIR}/run.sh"
chmod +x "${SCRIPT_DIR}/stop.sh"
chmod +x "${SCRIPT_DIR}/install.sh"
[ -f "${SCRIPT_DIR}/uninstall.sh" ] && chmod +x "${SCRIPT_DIR}/uninstall.sh"

# Generuje wpis .desktop wskazujący na aktualną lokalizację projektu
write_desktop_entry() {
    cat << EOF > "$1"
[Desktop Entry]
Type=Application
Name=Zorin Desktop Monitor
Name[pl]=Kafelkowy Monitor Pulpitu (CPU, RAM, Dysk)
Comment=Monitor zasobów CPU, RAM i dysku w postaci kafelków na pulpicie
Comment[pl]=Kafelkowy monitor użycia procesora, pamięci RAM i dysku na pulpicie
Exec="${SCRIPT_DIR}/run.sh" --daemon
Icon=${SCRIPT_DIR}/assets/icon.svg
Terminal=false
Categories=System;Monitor;Utility;
Keywords=cpu;ram;dysk;pamięć;procesor;monitor;kafelki;pulpit;
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF
    chmod +x "$1"
}

# Aktualizacja pliku .desktop w katalogu projektu
write_desktop_entry "${SCRIPT_DIR}/zorin-monitor.desktop"

# Utworzenie katalogów jeśli to możliwe
mkdir -p "$APPS_DIR" 2>/dev/null || true
mkdir -p "$AUTOSTART_DIR" 2>/dev/null || true

# Kopiowanie skrótu do menu aplikacji
if [ -d "$APPS_DIR" ] && [ -w "$APPS_DIR" ]; then
    write_desktop_entry "$APPS_DIR/zorin-monitor.desktop"
    echo "✓ Dodano skrót do menu aplikacji: $APPS_DIR/zorin-monitor.desktop"
else
    echo "ℹ Pominięto zapis do $APPS_DIR (brak uprawnień do zapisu w tym środowisku)"
fi

# Kopiowanie skrótu na Pulpit (jeśli istnieje)
DESKTOP_DIR=""
if command -v xdg-user-dir >/dev/null 2>&1; then
    DESKTOP_DIR=$(xdg-user-dir DESKTOP)
fi
if [ -z "$DESKTOP_DIR" ] || [ ! -d "$DESKTOP_DIR" ]; then
    if [ -d "$HOME/Pulpit" ]; then
        DESKTOP_DIR="$HOME/Pulpit"
    elif [ -d "$HOME/Desktop" ]; then
        DESKTOP_DIR="$HOME/Desktop"
    fi
fi

if [ -n "$DESKTOP_DIR" ] && [ -d "$DESKTOP_DIR" ]; then
    write_desktop_entry "$DESKTOP_DIR/zorin-monitor.desktop"
    # Pozwolenie na uruchamianie dla GNOME (gio set)
    if command -v gio >/dev/null 2>&1; then
        gio set "$DESKTOP_DIR/zorin-monitor.desktop" "metadata::trusted" true 2>/dev/null || true
    fi
    echo "✓ Utworzono skrót na Pulpicie: $DESKTOP_DIR/zorin-monitor.desktop"
fi

# Konfiguracja autostartu
if [ -d "$AUTOSTART_DIR" ] && [ -w "$AUTOSTART_DIR" ]; then
    write_desktop_entry "$AUTOSTART_DIR/zorin-monitor.desktop"
    echo "✓ Włączono autostart przy logowaniu: $AUTOSTART_DIR/zorin-monitor.desktop"
else
    echo "ℹ Pominięto konfigurację autostartu (katalog niedostępny do zapisu w tym środowisku)"
fi

# Aktualizacja bazy skrótów jeśli dostępne narzędzie
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

echo ""
echo "Instalacja zakończona sukcesem!"
echo "----------------------------------------------------------"
echo "Możesz uruchomić monitor za pomocą:"
echo "  1. Polecenia: ${SCRIPT_DIR}/run.sh --daemon"
echo "  2. Kliknięcia ikony 'Kafelkowy Monitor Pulpitu' w menu lub na pulpicie"
echo "  3. Automatycznie po każdym restarcie komputera (autostart jest włączony)"
echo ""
echo "Sterowanie:"
echo "  - Przeciąganie: Chwyć lewym przyciskiem myszy i przesuń w dowolne miejsce"
echo "  - Menu opcji: Kliknij prawym przyciskiem myszy na kafelku (ukrywanie kafelków, wybór dysku, blokada pozycji, orientacja, przezroczystość, wykresy)"
echo "----------------------------------------------------------"
