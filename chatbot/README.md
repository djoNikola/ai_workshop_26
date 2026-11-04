
# Copilot CLI Web Chat

Lokalni web chat koji šalje poruke Copilot CLI-ju (`copilot -p ...`) i prikazuje odgovore u browseru.

## Fajlovi

- `sip-chatbot-web.py` – lokalni server (samo standardna biblioteka, bez `pip install`)
- `sip-chatbot.html` – stranica sa chatom; mora biti u istom folderu kao server
- `sip-chatbot.py` – originalna Tkinter verzija (opciono)

## Preduslovi

- Python 3
- Node.js sa `npm` (potreban samo ako Copilot CLI još nije instaliran)
- GitHub nalog sa aktivnom Copilot pretplatom

## Pokretanje servera

```powershell
python sip-chatbot-web.py
```

Ako `python` nije dostupan u PATH-u, koristi `py sip-chatbot-web.py` ili punu putanju do `python.exe`.

Server sluša na `http://localhost:8765/` i sam otvara browser. Prozor sa serverom ostavi otvoren dok koristiš chat. `Ctrl+C` gasi server.

Stranicu otvaraj uvek preko `http://localhost:8765/`. Dvoklik na HTML fajl ne radi, jer tada nema servera.

## Prvo korišćenje

Gore na stranici se prikazuje panel sa trenutnim stanjem:

1. **Copilot nije instaliran** – klikni „Da, instaliraj“. Server izvršava `npm install -g @github/copilot` i uživo prikazuje izlaz.
2. **Nisi prijavljen** – klikni „Prijavi se“. Otvori prikazani link (`https://github.com/login/device`), unesi prikazani kod i odobri pristup. Stranica sama prepozna prijavu.
3. **Spreman** – panel nestaje i možeš da pišeš poruke.

Dok Copilot nije spreman, dugme „Pošalji " je onemogućeno.

## Korišćenje chata

- Upiši poruku i pritisni Enter ili „Pošalji ".
- Prvi odgovor može da traje desetak sekundi ili duže, jer se za svaku poruku pokreće `copilot`.
- Poruke se šalju jedna po jedna. Posle prve se koristi `--continue`, pa razgovor ima kontekst prethodnih poruka.
- Restart servera počinje novi razgovor.

## Rešavanje problema

| Problem | Rešenje |
|---|---|
| „Failed to fetch“ / „Server nije dostupan“ | Server nije pokrenut ili je ugašen. Pokreni ga ponovo i osveži stranicu. |
| Port 8765 je zauzet | Zatvori drugi program na tom portu ili promeni `PORT` u `sip-chatbot-web.py`. |
| „npm nije pronađen“ | Instaliraj Node.js sa https://nodejs.org pa restartuj terminal. |
| Instaliran, ali „nije u PATH-u“ | Restartuj terminal i server. |
| Prijava ne prolazi | Pokreni `copilot login` ručno u terminalu, ili postavi `GH_TOKEN`/`COPILOT_GITHUB_TOKEN`. |

## Bezbednost

- Server sluša samo na `127.0.0.1`, pa je dostupan samo na tvom računaru.
- Odbijaju se zahtevi sa stranim `Host` i `Origin` zaglavljem.
- Svi upiti idu preko Copilot naloga osobe koja je pokrenula server. Nemoj ga izlagati na internet bez prijave korisnika i ograničenja broja zahteva.
