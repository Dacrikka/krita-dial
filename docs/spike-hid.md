# Spike HID xPress Multimedia Controller (27/10/2026)

Dispositivo: `VID_0B33&PID_0020`, product string `ShuttleXpress`, usage page `000C` (consumer) usage `0001`.
Windows non lo blocca (non è tastiera/mouse): `CreateFile` in lettura condivisa funziona senza driver.
Codice: `krita_dial/hid_device.py` (ctypes puro), dump grezzo: `spike/hid_dump.py` → `spike/hid_dump.log`.

## Formato report (6 byte, inviato solo quando cambia qualcosa)

| Byte | Contenuto |
|---|---|
| 0 | report ID (`00`) |
| 1 | anello, signed −7..+7, 0 = rilasciato |
| 2 | contatore jog 0–255, ciclico, 1 per scatto |
| 3 | inutilizzato |
| 4 | tasti 1–4: bit `0x10`, `0x20`, `0x40`, `0x80` |
| 5 | tasto 5: bit `0x01` |

## Comportamenti da gestire

- Il contatore jog parte da un valore qualsiasi: il primo report fa solo da riferimento (`Decoder`).
- Nessun report ripetuto mentre l'anello è tenuto fermo: la ripetizione la fa il controller con un timer.
- Rilasciando l'anello, il ritorno a 0 passa per tutte le posizioni in ~20 ms: il controller non deve
  eseguire l'azione a ogni cambio di posizione (corretto in `Controller.on_ring`).
- Nel dump c'è una pressione accidentale del tasto 3 mentre si girava l'anello: con la presa normale capita.

## Da verificare

- Convivenza col software Contour: durante il test non era in esecuzione. Se gira, anche lui
  legge il dispositivo e invia le sue scorciatoie → azioni doppie. Va provato e scritto nel README.
