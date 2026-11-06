
# SIP Tickets Miner (web chat)

Lokalni web chat za PM-a: upiše opis problema klijenta (IT/EN) ili broj tiketa, a chat vraća do 3 kandidata
(ID, naslov, status, istorijski assignee i issue type, kratko obrazloženje). Za opis problema prikazuje i predlog issue type-a i assignee korisnika sa dokazima iz sličnih tiketa. Podaci se čitaju iz `../resources/issues_export.csv`.

## Kako radi

1. Ako poruka sadrži ID (npr. `BTU-4114`) i tiket postoji, prikazuje se prvi. Ako ne postoji, chat to kaže i traži dalje po ostatku teksta.
2. Lokalna BM25 pretraga bira do 30 kandidata iz CSV-a.
3. Copilot CLI (`copilot -p`) rangira kandidate i bira issue type iz svih jedinstvenih `ISSUETYPE` vrednosti u CSV-u. Assignee predlozi dolaze iz rangiranih tiketa i prikazuju ID-jeve koji ih podržavaju; nisu automatska dodela. ID, status, istorijski assignee i issue type kandidata uvek se čitaju iz CSV-a.
4. Ako Copilot ne radi, prikazuju se top 3 lokalna pogotka bez klasifikacije i assignee predloga. Ako ništa ne odgovara: „No matching ticket found“.

Export trenutno sadrži 11 različitih numeričkih `ISSUETYPE` vrednosti, bez šifarnika, pa se prikazuju kao kodovi. Kolona `COMPONENT` je prazna u svim redovima; assignee preporuka zato koristi samo istoriju rangiranih sličnih tiketa, ne vlasništvo sistema.

Svaki upit je nezavistan (nema `--continue`). Labele statusa su u `STATUS_LABELS` u `ticket_lookup.py`
(1/3/4/5/6 prema Jira podrazumevanim vrednostima — PM treba da potvrdi); nepoznati kodovi se prikazuju kao `Status <kod>`.

**Jezik interfejsa:** podrazumevano engleski; dugme `EN`/`IT` gore desno prebacuje na italijanski i izbor se pamti
u browseru (`localStorage`). Tekstovi stranice su u objektu `T` u `static/app.js`, a fiksne napomene chata
(„not found“, „no match“…) u `MESSAGES` u `ticket_lookup.py` (`/api/chat` prima `lang`: `en` ili `it`).
Obrazloženje koje daje Copilot ostaje na jeziku upita.

**Tema:** svetla i tamna (obe prigušene). Pri prvom otvaranju prati sistemsku temu, a ikonica sunca/meseca levo od
izbora jezika je menja; izbor se pamti u browseru. Boje su CSS promenljive u `static/style.css`
(`[data-theme="light"]` / `[data-theme="dark"]`).

**Privatnost:** upit, svi jedinstveni `ISSUETYPE` kodovi i najviše 30 isečaka tiketa (ID, naslov, skraćen opis, status, assignee, issue type) šalju se Copilot servisu.
Pošto je CSV pravi export, to treba odobriti ili podatke anonimizirati pre stvarne upotrebe (vidi `SPEC.md` §10).

## Testovi

```bash
cd chatbot && python3 -m unittest test_ticket_lookup
```

## Fajlovi

- `sip-chatbot-web.py` – lokalni server (samo standardna biblioteka, bez `pip install`)
- `ticket_lookup.py` – učitavanje CSV-a, pretraga i rangiranje
- `test_ticket_lookup.py` – unit testovi
- `sip-chatbot.html` – struktura stranice (HTML); mora biti u istom folderu kao server
- `static/style.css` – stilovi stranice
- `static/app.js` – logika stranice (chat, setup panel, prevodi EN/IT, promena teme)
- `static/theme.js` – primenjuje sačuvanu/sistemsku temu pre iscrtavanja stranice
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

1. **Copilot is not installed** – klikni „Yes, install“. Server izvršava `npm install -g @github/copilot` i uživo prikazuje izlaz.
2. **Not signed in** – klikni „Sign in“. Otvori prikazani link (`https://github.com/login/device`), unesi prikazani kod i odobri pristup. Stranica sama prepozna prijavu.
3. **Spreman** – panel nestaje i možeš da pišeš poruke.

Dok Copilot nije spreman, dugme „Send“ je onemogućeno.

## Korišćenje chata

- Upiši poruku i pritisni Enter ili „Send“.
- Prvi odgovor može da traje desetak sekundi ili duže, jer se za svaku poruku pokreće `copilot`.
- Poruke se šalju jedna po jedna. Svaki upit je nezavistan; prethodne poruke se ne uzimaju u obzir.

## Rešavanje problema

| Problem | Rešenje |
|---|---|
| „Failed to fetch“ / „Server is not reachable“ | Server nije pokrenut ili je ugašen. Pokreni ga ponovo i osveži stranicu. |
| Port 8765 je zauzet | Zatvori drugi program na tom portu ili promeni `PORT` u `sip-chatbot-web.py`. |
| „npm was not found“ | Instaliraj Node.js sa https://nodejs.org pa restartuj terminal. |
| Instaliran, ali „not in PATH“ | Restartuj terminal i server. |
| Prijava ne prolazi | Pokreni `copilot login` ručno u terminalu, ili postavi `GH_TOKEN`/`COPILOT_GITHUB_TOKEN`. |

## Bezbednost

- Server sluša samo na `127.0.0.1`, pa je dostupan samo na tvom računaru.
- Odbijaju se zahtevi sa stranim `Host` i `Origin` zaglavljem.
- Svi upiti idu preko Copilot naloga osobe koja je pokrenula server. Nemoj ga izlagati na internet bez prijave korisnika i ograničenja broja zahteva.
