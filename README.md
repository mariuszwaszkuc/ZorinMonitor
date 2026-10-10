# 🖥️ Zorin Desktop Monitor (Kafelkowy Monitor Pulpitu)

Nowoczesny, lekki i estetyczny widget na pulpit systemu **Zorin OS / GNOME**, wyświetlający w czasie rzeczywistym użycie zasobów **CPU**, **RAM**, **SWAP** i **dysku** w postaci kafelków (*tiles*) – zarówno **procentowo**, jak i **ilościowo**.

---

## ✨ Cechy i wygląd

- 🧊 **Stylistyka Glassmorphism**: Eleganckie, półprzezroczyste kafelki z zaokrąglonymi rogami, dopasowane do nowoczesnego wyglądu Zorin OS.
- 📌 **Widget Pulpitu**: Okno bez ramek, widoczne na wszystkich obszarach roboczych, niewidoczne w pasku zadań i przełączniku Alt+Tab. Opcjonalnie może być trzymane pod oknami aplikacji.
- 👁 **Ukrywanie i odkrywanie kafelków**: Każdy kafelek (CPU, RAM, SWAP, Dysk) można niezależnie ukryć lub przywrócić.
- 🖐️ **Dowolne pozycjonowanie**: Widget można chwycić lewym przyciskiem myszy i przesunąć w dowolne miejsce ekranu.
- 🔒 **Blokada pozycji**: Możliwość zablokowania widgetu, aby zapobiec przypadkowemu przesunięciu.
- 📈 **Wykresy w czasie rzeczywistym (Sparklines)**: Płynne mini-wykresy historii obciążenia renderowane przez bibliotekę Cairo.
- 🎨 **Dynamiczne kolory**: Wskaźniki automatycznie zmieniają barwę przy wysokim obciążeniu (błękit/fiolet ➔ żółty ➔ czerwony).
- ⚙️ **Bogate menu kontekstowe**: Dostępne pod prawym przyciskiem myszy na dowolnym kafelku.

---

## 📊 Wyświetlane informacje

### 1. Kafelek CPU (Procesor)
* **Procentowo**:
  - Główne, czytelne użycie całkowite procesora (np. `14.2%`) z kolorowym wskaźnikiem i paskiem postępu.
* **Ilościowo**:
  - **Taktowanie**: Aktualna częstotliwość pracy procesora w GHz/MHz (np. `2.40 GHz`).
  - **Rdzenie / wątki**: Liczba rdzeni fizycznych i wątków logicznych (np. `14 / 18`).
  - **Najbardziej obciążony rdzeń**: Użycie najbardziej zajętego wątku (np. `63%`).
  - **Średnie obciążenie (Load Average)**: Wartości dla 1, 5 i 15 minut (np. `0.65, 0.92, 1.05`).
  - **Główny proces**: Nazwa i procent procesu najbardziej obciążającego procesor.

### 2. Kafelek RAM (Pamięć operacyjna)
* **Procentowo**:
  - Główne procentowe zużycie pamięci (np. `48.5%`) z kolorowym paskiem postępu.
* **Ilościowo**:
  - **Użycie**: Wykorzystana pamięć RAM w stosunku do całkowitej (np. `7.4 GB / 15.0 GB`).
  - **Dostępna pamięć**: Ilość wolnej pamięci RAM (np. `7.6 GB wolnej`).
  - **Pamięć wymiany (Swap)**: Ilościowe i procentowe zużycie przestrzeni Swap (np. `0.0 GB / 2.0 GB (0%)`).
  - **Główny proces**: Proces zajmujący najwięcej pamięci RAM (np. `gnome-shell (1.1 GB)`).

### 3. Kafelek SWAP (Pamięć wymiany)
* Procentowe i ilościowe zużycie Swap, wolne miejsce, ilość danych zapisanych do Swap oraz status.

### 4. Kafelek DYSK
* **Procentowo**:
  - Zajętość wybranej partycji (domyślnie `/`) z kolorowym paskiem postępu.
* **Ilościowo**:
  - **Użycie**: Zajęte miejsce w stosunku do pojemności (np. `212.4 GB z 468.3 GB`).
  - **Wolne miejsce**: Ilość wolnego miejsca (np. `256.0 GB wolnego`).
  - **Odczyt / Zapis**: Bieżąca prędkość operacji dyskowych (np. `1.2 MB/s / 340 KB/s`).
  - **Partycja**: Urządzenie i system plików (np. `nvme0n1p2 (ext4)`).
* **Wykres**: Pokazuje aktywność dysku (procent czasu zajętości I/O), bo zajętość miejsca zmienia się zbyt wolno, by wykres był czytelny.

---

## 🚀 Szybki start

Wszystkie potrzebne biblioteki (`python3-gi`, `python3-psutil`, `python3-cairo`) są standardowo zainstalowane w Zorin OS.

### 1. Uruchomienie bezpośrednie
```bash
cd ~/Documents/AntyGravity/ZorinMonitor
./run.sh
```
Lub uruchomienie w tle (jako usługa):
```bash
./run.sh --daemon
```

### 2. Zatrzymanie monitora
```bash
./stop.sh
```

### 3. Pełna instalacja (skrót w menu, pulpit, autostart)
Uruchom instalator:
```bash
./install.sh
```
Instalator:
1. Doda skrót **"Kafelkowy Monitor Pulpitu"** do menu programów Zorin OS.
2. Doda ikonę na Pulpit (jeśli katalog istnieje).
3. Włączy automatyczne uruchamianie monitora po zalogowaniu do systemu.

---

## 🖱️ Sterowanie i konfiguracja

Kliknij **prawym przyciskiem myszy** na dowolnym kafelku, aby otworzyć menu podręczne:

| Opcja w menu | Opis działania |
| :--- | :--- |
| **🙈 Ukryj kafelek: …** | Ukrywa kafelek, na którym kliknięto (ostatniego widocznego nie da się ukryć). |
| **👁 Widoczne kafelki** | Zaznaczanie, które kafelki mają być widoczne (CPU, RAM, SWAP, Dysk), oraz opcja **Pokaż wszystkie kafelki**. |
| **💽 Monitorowany dysk** | Wybór partycji pokazywanej na kafelku Dysk (np. `/`, `/home`, dyski zewnętrzne). |
| **🔒 Zablokuj pozycję na pulpicie** | Blokuje możliwość przeciągania myszką (kliknięcia nie przesuwają widgetu). |
| **📌 Zawsze na spodzie (pod oknami)** | Utrzymuje kafelki pod wszystkimi normalnymi oknami jako część tapety/pulpitu. **Uwaga:** przy włączonych ikonach pulpitu kafelki przestają wtedy reagować na mysz — tryb wyłączysz poleceniem `./run.sh --restart --reset-below`. |
| **📈 Pokaż wykresy obciążenia** | Włącza lub wyłącza mini-wykresy historii obciążenia (tryb kompaktowy / rozszerzony). |
| **↔ Układ kafelków** | Wybór między układem **Poziomym** (obok siebie) a **Pionowym** (jeden pod drugim). |
| **🎨 Przezroczystość tła** | Zmiana stopnia przezroczystości (50%, 70%, 85%, 95%). |
| **⏱ Częstotliwość odświeżania** | Wybór interwału próbkowania: 0.5s (płynne), 1.0s (standard), 2.0s (oszczędne). |
| **🚀 Uruchamiaj przy starcie systemu** | Włączanie / wyłączanie autostartu bez konieczności edycji plików. |
| **🔄 Przywróć domyślną pozycję** | Umieszcza widget w prawym górnym rogu ekranu. |
| **❌ Zamknij monitor** | Wyjście z programu i zapisanie aktualnej pozycji. |

Plik konfiguracyjny z zapisaną pozycją i ustawieniami znajduje się w:
`~/.config/zorin-monitor/config.json`
