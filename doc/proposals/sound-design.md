# Specifica: lavoro col JD-Xi in sicurezza e sound design guidato — rev. 2

Branch: `dev/sound-design` (nessuna build su GitHub ai push; una PR finale, preceduta da test
locali completi, in particolare su protocollo SysEx e memoria).
Rev. 1: proposte (17/11). Rev. 2: integra la revisione esterna (17/11) e i vincoli dello strumento
verificati nel codice e nel manuale. Stato: **approvata con le decisioni del §11; sviluppo per fasi**.

Obiettivo: JD-Xi Studio come ambiente di sound design guidato, non solo editor di parametri.
L'utente deve sempre sapere **dove** sta lavorando, **cosa** è salvato e **dove**, e non deve mai
credere che una modifica temporanea sia un suono salvato.

---

## 0. Vincoli dello strumento (fatti, non scelte)

| # | Vincolo | Fonte |
|---|---|---|
| V1 | Le modifiche stanno nell'**area temporanea**: si perdono spegnendo o scegliendo un altro programma | Manuale, «Salvataggio di un suono (WRITE)» |
| V2 | Si salva solo un **programma intero** (4 parti + effetti + arpeggio) con **WRITE** sullo strumento, nei banchi utente **E–H** (64 posti ciascuno); A–D sono di fabbrica | Manuale |
| V3 | **Un tono da solo non si salva** sul JD-Xi (si copia con Pattern Copy › Sound Only) | Manuale, Promemoria |
| V4 | Via SysEx si legge e scrive **solo l'area temporanea**. Un programma salvato si legge solo **selezionandolo** (Program Change), che lo carica nell'area temporanea | Mappa SysEx (MIDI Implementation) |
| V5 | Il WRITE sullo strumento propone come nome quello del programma temporaneo: inviarlo prima via SysEx serve a precompilarlo, non salva nulla | Manuale (schermata nome del WRITE) |
| V6 | Un DT1 non ha conferma di ricezione: si verifica solo rileggendo (RQ1) | MIDI Implementation |
| V7 | I canali delle parti sono fissi (1, 2, 3, 10; programma 16) | Manuale, risoluzione problemi |

## 1. Modello degli stati

### 1.1 Collegamento (macchina a stati centralizzata)

Oggi ogni componente decide da sé se il JD-Xi «c'è» (follower: porta d'uscita presente; A/B:
entrambe le porte aperte; Send all: uscita aperta). Si sostituisce con **un solo oggetto**
(`Connection`), da cui leggono tutte le finestre, principali e secondarie.

| Stato | Significato | Come ci si arriva |
|---|---|---|
| `OFFLINE` | Nessuna porta JD-Xi | Avvio senza JD-Xi; porte chiuse o sparite |
| `DETECTED` | Porte aperte, non ancora verificate | Porte trovate/aperte |
| `VERIFYING` | Identity Request inviata, lettura iniziale in corso | Da `DETECTED` |
| `ONLINE` | Identity ricevuta e lettura iniziale completa | Da `VERIFYING` |
| `UNSTABLE` | Online, ma richieste senza risposta (≥ 2 letture consecutive incomplete) | Da `ONLINE` |

- Transizioni notificate con un segnale unico; ogni comando si abilita in base allo stato
  (non a un booleano).
- Da `UNSTABLE` si torna a `ONLINE` con una lettura completa; a `OFFLINE` se le porte spariscono.
- Le porte vengono controllate periodicamente (≈ 1 s) per accorgersi di scollegamenti fisici.

### 1.2 Tre stati del suono, distinti e mai intercambiabili

| Nome | Cosa contiene | Chi lo aggiorna |
|---|---|---|
| **Last Confirmed State** (LCS) | Ultimo stato **verificato** sul JD-Xi: solo dati **letti** (risposte DT1 a RQ1, o DT1 spontanei dello strumento) | Solo le letture |
| **Working State** (WS) | Ciò che gli editor mostrano e l'utente modifica | Editor, preset, ricette, Init, A/B |
| **Pending Changes** (PC) | Modifiche inviate (DT1) ma non ancora rilette | Invii; si svuotano quando una lettura le conferma (o le smentisce) |

Cambiamento rispetto a oggi: la `SynthMemory` registra i DT1 **al momento dell'invio**
(mescolando inviato e letto). Va separata: gli invii vanno in PC; entrano in LCS solo dopo una
rilettura che li conferma. Il salvataggio di patch (.msz) usa LCS + PC per le sezioni toccate,
come oggi usa la memoria (nessun cambiamento visibile).

### 1.3 Quattro livelli di persistenza (da mostrare all'utente)

1. Solo nell'app (WS, non inviato) — es. Off-line.
2. Inviato al JD-Xi, **temporaneo** (si perde spegnendo o cambiando programma).
3. Salvato **su file** (.msz programma intero; .syx di una parte; ricetta).
4. Salvato **sul JD-Xi** con WRITE (E–H), verificato.

## 2. Fase 1 — Off-line e stato centralizzato

**Comportamento**
- Senza JD-Xi all'avvio: `OFFLINE`, **finestra di avviso** («Il JD-Xi non è collegato: puoi
  provare tutto, ma niente viene salvato né inviato») e **badge «Off-line»** fisso nella finestra
  principale e in tutte le secondarie (editor staccati, impostazioni, lettore, pattern).
- In `OFFLINE` tutto si muove; **spenti con tooltip** che spiega il motivo: Salva patch, export
  .syx, salva ricetta, salva A/B, Send all, Read, Autotest, scelta programmi/preset,
  Update user programs, richiamo A/B.
- Collegamento del JD-Xi: `DETECTED → VERIFYING → ONLINE`. Se WS ha modifiche fatte in Off-line,
  **avviso esplicito** (senza domanda): «Le modifiche fatte senza JD-Xi vengono abbandonate:
  mostro le impostazioni lette dallo strumento.» Poi lettura completa; WS = LCS.
- `UNSTABLE`: badge «Comunicazione instabile», i comandi che scrivono restano attivi ma ogni
  operazione verifica la lettura; nessuna conferma «verde» finché non torna `ONLINE`.

**Operazioni interrotte** (regola generale): ogni operazione che invia e/o legge (Read, Send all,
richiamo A/B, caricamento patch, ripristino) è una **transazione**: ha un esito esplicito
(completa / parziale / fallita); se il collegamento cade a metà si interrompe, dichiara cosa è
stato fatto e cosa no, e non aggiorna LCS con dati non riletti. Nessuna finestra mostra «salvato»
o «sincronizzato» per una transazione non completa.

## 3. Fase 2 — Rete di sicurezza dopo una riconnessione

Al ritorno da `OFFLINE` (cavo staccato, JD-Xi spento e riacceso, porta persa):

| Esito della lettura completa confrontata con LCS precedente | Comportamento |
|---|---|
| Identica | «Riconnessione riuscita, stato invariato». Nessun intervento. (Non si afferma *perché* si era scollegato: un riavvio può anche ridare lo stesso stato.) |
| Differente, **con modifiche non salvate** (LCS precedente diverso dal riferimento: né su file né con WRITE) | Mostra **quali parti** differiscono (Programma comune, Digital 1, Digital 2, Analog, Drums, Effetti, Arpeggio) e **chiede**: **Ripristina sul JD-Xi** / **Tieni quello che c'è sul JD-Xi** |
| Differente, **senza modifiche a rischio** (lo stato di prima era già salvato) | Nessuna domanda: si tiene lo stato del JD-Xi, con un avviso breve («Il JD-Xi ha un altro stato: mostro quello») |
| Lettura incompleta | Non confronta, non propone il ripristino; nuova lettura |
| Comunicazione instabile | Tiene LCS precedente; chiede una nuova lettura prima di decidere |

- **Ripristino**: invia solo i blocchi delle parti diverse, poi rilegge; esito per parte.
  Se una parte non va a buon fine: «Ripristino **parziale**: Analog ripristinata, Digital 1 no»
  (nessun esito «completo» falso).
- Dopo il ripristino: promemoria che lo stato è di nuovo **temporaneo** (livello 2) → per tenerlo
  serve WRITE (Fase 4).
- **Fuori da questa release**: salvataggio periodico di LCS su disco.

## 4. Fase 3 — Riga di contesto e stato «modificato»

Riga fissa in testa agli editor di tono e alla vista Programma:

> Programma **E-12 «My Bass»** › parte **Analog** › tono «Toxic Bass 1» · origine: preset A-05 · **modificato, temporaneo**

Due informazioni distinte:
- **Origine** (storica, non cambia con le modifiche): preset Xnn, ricetta «…», Init, programma
  Xnn, file «…», A/B.
- **Stato**, sempre rispetto al **riferimento attuale**:
  - *originale* (= riferimento), *modificato* (≠ riferimento), *inviato, temporaneo* (livello 2),
    *salvato su file* (livello 3, con nome file), *salvato in E-12* (livello 4).
  - Il riferimento è l'ultimo caricamento o salvataggio: caricato A-05 → riferimento A-05;
    salvato in E-12 → riferimento E-12 (l'origine resta «preset A-05»).
- **Avviso uniforme** di abbandono modifiche (stesso testo e stesse scelte: *Salva prima… /
  Scarta / Annulla*) in tutti i punti: cambio programma o preset, chiusura, finestre secondarie,
  caricamento patch, Init, ricetta.

## 5. Fase 4 — «Salva sul JD-Xi» guidato

Il salvataggio vero lo fa il WRITE dello strumento (V2, V4): l'app lo prepara, guida e verifica.

1. **Nome** (12 caratteri): inviato via SysEx come nome del programma temporaneo, con la frase
   «Nome preparato sul JD-Xi: **non è ancora salvato**» (V5).
2. **Posto**: elenco E–H dalla libreria dei nomi già nell'app (Update user programs); i nomi
   possono essere vecchi → indicati con la data dell'ultimo aggiornamento. **Liberi** sono i posti
   col nome di fabbrica di un programma vuoto («Init Program» / «Init Tone», senza distinzione di
   maiuscole): l'app propone il primo. L'utente può comunque **sceglierne uno qualsiasi** da
   sovrascrivere (sacrificare), con la conferma esplicita del punto 3.
3. **Sovrascrittura esplicita**: se il posto contiene un programma, l'utente deve confermare
   con nome e posizione («Sostituire **E-13 “Dark Pad”**?»); pulsante distinto, non predefinito.
4. **Istruzioni** precise: «Sul JD-Xi: Shift + Menu/Write · scegli **E-13** con Program [-][+] ·
   Enter · Enter». L'app attende la conferma dell'utente («Fatto»).
5. **Verifica** (V4): l'app seleziona E-13 (Program Change; dopo il WRITE coincide con lo stato
   temporaneo, quindi non si perde nulla) e **resta su E-13**, il programma appena salvato su cui
   si sta lavorando; rilegge e confronta col contenuto atteso:
   identificativo, nome, 4 parti, comune, effetti, arpeggio.
   - tutto uguale → «Salvato in E-13 ✓», riferimento = E-13 (Fase 3);
   - diverso o lettura incompleta → **nessuna conferma**: «Non risulta salvato in E-13 (…)»,
     con le differenze; lo stato resta *temporaneo*.
6. **Backup su file**: offerto in parallelo un `.msz` del **programma completo**; per un singolo
   tono resta l'export `.syx` della parte (V3), presentato come tale.

## 6. Fase 5 — «Nuovo suono»

Pannello con tre ingressi, ognuno con una riga di spiegazione:

| Ingresso | Effetto |
|---|---|
| **Da zero (Init)** | Init sulla **sola parte selezionata** |
| **Da un preset** | Tono di fabbrica per categoria; il preset originale non cambia (V1) |
| **Da una ricetta** | Ricetta della libreria (esiste già) |

**Init** — due configurazioni distinte, entro i limiti dei rispettivi parametri:
- *Digital*: partial 1 acceso (2 e 3 spenti), onda a dente di sega, filtro passa-basso aperto,
  inviluppo d'ampiezza A=0 / S=max / R breve, niente LFO, niente modulazioni.
- *Analog*: oscillatore a dente di sega, filtro aperto, stessi inviluppi, LFO a zero.
- Agisce **solo sui parametri del tono della parte** (blocchi Temporary Tone della parte); non
  tocca le altre parti né gli effetti del programma (Effect 1/2, Delay, Reverb); i livelli di
  mandata della parte restano come sono.
- Se la parte ha modifiche: avviso uniforme (Fase 3).
- **Annullabile**: Init e ricette sono modifiche di parametri → un solo passo di Undo.
  Il caricamento di un **preset** è un cambio di tono sullo strumento (non annullabile con Undo):
  prima di caricarlo si suggerisce una foto A/B.

## 7. Fase 6 — Aiuti per sezione

Un «?» per sezione (oscillatore, filtro, amplificatore, LFO, effetti) con tre righe: **cosa
modifica**, **come cambia il suono**, **un esempio pratico**; più la pagina del Parameter Guide
(il riferimento c'è già). L'A/B resta lo strumento «prima/dopo» (confronto temporaneo); il
salvataggio A/B su file è un'altra cosa e resta separato.

## 8. Criteri di accettazione

Automatici con JD-Xi simulato (come `tests/test_ab_compare.py`) **e** sullo strumento (piano di
prova hardware, nuova sezione).

| ID | Scenario | Risultato atteso |
|---|---|---|
| SD-01 | Avvio senza JD-Xi | `OFFLINE`, avviso, badge in tutte le finestre, comandi che scrivono/leggono spenti |
| SD-02 | Collegamento del JD-Xi | `DETECTED → VERIFYING → ONLINE` solo dopo Identity e lettura completa |
| SD-03 | Modifiche in Off-line, poi collegamento | Avviso esplicito; WS = stato letto |
| SD-04 | Scollegamento durante una modifica | `OFFLINE`; LCS conservato; le modifiche successive non entrano in LCS |
| SD-05 | JD-Xi spento e riacceso | Lettura completa e confronto con LCS |
| SD-06 | Stato diverso alla riconnessione | Parti diverse elencate; Ripristina / Tieni |
| SD-07 | Ripristino interrotto | Esito per parte, «parziale» dichiarato |
| SD-08 | Caricamento preset e modifica | Preset di fabbrica invariato; origine e riferimento corretti |
| SD-09 | Init | Cambia solo la parte selezionata; annullabile con un Undo |
| SD-10 | Cambio programma con modifiche | Avviso uniforme (Salva prima / Scarta / Annulla) |
| SD-11 | WRITE eseguito | Verifica sul contenuto riletto; «Salvato in Xnn ✓»; riferimento = Xnn |
| SD-12 | WRITE non eseguito o su altro posto | Nessuna conferma falsa; stato resta temporaneo |
| SD-13 | Finestre secondarie | Stesso stato e badge della principale, aggiornati insieme |
| SD-14 | Riconnessioni ripetute (5 volte di fila) | Nessuno stato incoerente, nessun doppio avviso |
| SD-15 | Comunicazione instabile (risposte perse) | `UNSTABLE`; nessuna conferma verde; ritorno a `ONLINE` dopo lettura completa |
| SD-16 | Invio interrotto (Send all, patch, A/B) | Transazione «parziale/fallita»; LCS non aggiornato con dati non riletti |

## 9. Fuori da questa release

Salvataggio periodico di LCS su disco; Undo/Redo del programma intero; evoluzioni delle
ricette; nuove funzioni A/B; cambi sostanziali al layout degli editor.

## 10. Ordine di sviluppo

| Fase | Contenuto | Note |
|---|---|---|
| 1 | Stato centralizzato e Off-line (§1.1, §2) | Fondamento |
| 2 | LCS / WS / PC separati e rete di sicurezza (§1.2, §3) | Protezione del lavoro |
| 3 | Riga di contesto e avviso uniforme (§4) | Le fasi 1–3 sono un unico intervento funzionale, anche in più commit |
| 4 | Salva sul JD-Xi guidato (§5) | Da provare a fondo sullo strumento |
| 5 | Nuovo suono / Init (§6) | |
| 6 | Aiuti per sezione (§7) | |

Ogni fase: test automatici col JD-Xi simulato, suite completa in locale, poi passi hardware.

## 11. Decisioni (17/11)

1. **Ripristino alla riconnessione**: si chiede solo se ci sono modifiche non salvate che
   andrebbero perse; altrimenti si tiene lo stato del JD-Xi con un avviso (§3).
2. **Dopo la verifica del WRITE** si resta sul programma appena salvato (§5, punto 5).
3. **Posti liberi**: nome «Init Program» / «Init Tone»; l'utente può sceglierne qualsiasi altro da
   sovrascrivere, con conferma esplicita (§5, punti 2–3).
