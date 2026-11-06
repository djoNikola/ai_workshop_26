
# SIP Ticket Lookup (web chat)

Lokalni web chat za PM-a: upiše opis problema klijenta (IT/EN) ili broj tiketa, a chat vraća do 3 kandidata
(ID, naslov, status, assignee, kratko obrazloženje). Podaci se čitaju iz `../resources/issues_export.csv`.

## Kako radi

1. Ako poruka sadrži ID (npr. `BTU-4114`) i tiket postoji, prikazuje se prvi. Ako ne postoji, chat to kaže i traži dalje po ostatku teksta.
2. Lokalna BM25 pretraga bira do 30 kandidata iz CSV-a.
3. Copilot CLI (`copilot -p`) rangira te kandidate i vraća JSON; ID, status i assignee uvek se čitaju iz CSV-a.
4. Ako Copilot ne radi, prikazuju se top 3 lokalna pogotka uz napomenu. Ako ništa ne odgovara: „No matching ticket found“.

Svaki upit je nezavistan (nema `--continue`). Labele statusa su u `STATUS_LABELS` u `ticket_lookup.py`
(1/3/4/5/6 prema Jira podrazumevanim vrednostima — PM treba da potvrdi); nepoznati kodovi se prikazuju kao `Status <kod>`.

**Privatnost:** upit i najviše 30 isečaka tiketa (ID, naslov, skraćen opis, status, assignee) šalju se Copilot servisu.
Pošto je CSV pravi export, to treba odobriti ili podatke anonimizirati pre stvarne upotrebe (vidi `SPEC.md` §10).

## Testovi

Kategorizacija: `http://localhost:8765/categorize` predlaže `ISSUETYPE` za novi tiket na osnovu sličnih tiketa (labele u `ISSUETYPE_LABELS` u `ticket_lookup.py`; nepoznati kodovi se prikazuju kao `Type <kod>`). Stranica: `sip-categorize.html`.

```bash
cd chatbot && python3 -m unittest test_ticket_lookup
```

## Fajlovi

- `sip-chatbot-web.py` – lokalni server (samo standardna biblioteka, bez `pip install`)
- `ticket_lookup.py` – učitavanje CSV-a, pretraga i rangiranje
- `test_ticket_lookup.py` – unit testovi
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
- Poruke se šalju jedna po jedna. Svaki upit je nezavistan; prethodne poruke se ne uzimaju u obzir.

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

Preporuka osoba: `http://localhost:8765/recommend` na osnovu 5 najsličnijih tiketa sa dodeljenim assignee-jem preporučuje 2-3 osobe (kolona `ASSIGNEE`). Radi lokalno, bez Copilota. Stranica: `sip-recommend.html`. Sve tri stranice imaju linkove jedna na drugu.
