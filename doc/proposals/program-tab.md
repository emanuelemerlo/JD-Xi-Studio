Devono essere mantenuti approcci coerenti con lo stile dell'applicazione, e laddove sia richiesto/possibile in armonia con il manuale utente. 

# SPECIFICA FUNZIONALE E UX
## Revisione della tab Program – JD-Xi Studio

**Branch di riferimento:** `dev/sound-design`  
**Componente principale:** `jdxi_editor/ui/v2/programs.py`  
**Classe principale:** `ProgramEditor`  
**Revisione:** 1.1 (19/11: valutazione e modifiche nel §18, che prevalgono sul testo precedente)  
**Stato:** Approvata con le modifiche del §18; interventi nel registro di `sound-design.md` §12

---

# 1. Obiettivo

Riorganizzare la tab **Program** di JD-Xi Studio per renderla più intuitiva, coerente e funzionale, riducendo la frammentazione delle funzionalità e migliorando la comprensione dello stato del Program gestito.

La revisione deve consentire all'utente di:

1. Consultare e selezionare rapidamente i Program.
2. Distinguere chiaramente i Program Factory da quelli User.
3. Caricare un Program sul sintetizzatore.
4. Comprendere immediatamente la composizione sonora del Program.
5. Accedere direttamente alla modifica delle singole parti.
6. Gestire il Mixer senza navigazioni aggiuntive.
7. Salvare, duplicare e organizzare i Program.
8. Gestire Playlist e Preset senza duplicazioni funzionali.

## 1.1 Principi di progettazione

- **Single point of access:** un'unica Library per tutti i Program.
- **Clear state:** distinzione evidente tra Program selezionato, caricato e modificato.
- **Progressive disclosure:** le funzionalità avanzate non devono occupare spazio nella vista principale.
- **Consistency:** comportamenti coerenti tra Library, editor e finestre secondarie.
- **Reuse:** riutilizzo dei componenti e degli engine esistenti.
- **Safety:** nessuna operazione deve causare perdita involontaria di modifiche.

# 2. Analisi della situazione attuale

La V2 dispone già di una pagina unica che integra:

- Display e informazioni MIDI del Program.
- Library con ricerca, filtro per genere e selezione delle banche A–H.
- Tabella dei Program con ID, nome, genere e Tone associati.
- Pulsante Load Program.
- Tabella Parts of the Program.
- Mixer.
- Sezioni Presets, User Programs, Playlist e Playlist Editor.

La Library supporta già:
- Selezione singola.
- Ricerca per ID e nome.
- Filtro per genere.
- Filtro per banca.
- Caricamento tramite doppio clic.
- Caricamento tramite pulsante dedicato.

La tabella Parts of the Program mostra le quattro parti, i rispettivi Tone e i canali MIDI. Il doppio clic apre l'editor della parte.

## 2.1 Criticità da risolvere

| ID | Criticità | Intervento |
|---|---|---|
| UX-01 | Presets e User Programs sono separati dalla Library | Unificazione |
| UX-02 | Playlist e Playlist Editor sono due sezioni distinte | Integrazione |
| UX-03 | La Library non ricerca nei nomi dei Tone associati | Estensione ricerca |
| UX-04 | La composizione sonora non è immediatamente leggibile | Revisione Parts |
| UX-05 | Selezione e caricamento non sono sufficientemente distinti | Gestione stati |
| UX-06 | Le azioni di salvataggio non hanno una gerarchia uniforme | Revisione comandi |
| UX-07 | Il layout occupa molto spazio verticale | Revisione responsive |
| UX-08 | Il Mixer e la tabella Parts presentano informazioni non coordinate | Razionalizzazione |

# 3. Nuova architettura della pagina

La pagina Program viene organizzata in quattro aree funzionali.

## 3.1 Struttura generale

```text
PROGRAM
│
├── A. PROGRAM CONTEXT
│   ├── Program ID
│   ├── Program Name
│   ├── Bank / Genre / Tempo
│   ├── Connection Status
│   ├── Working State
│   └── Actions
│
├── B. PROGRAM WORKSPACE
│   │
│   ├── B1. LIBRARY
│   │   ├── Search
│   │   ├── Genre Filter
│   │   ├── Bank Selector A-H
│   │   └── Programs Table
│   │
│   └── B2. SOUND CONFIGURATION
│       ├── Digital 1
│       ├── Digital 2
│       ├── Drums
│       ├── Analog
│       └── Mixer
│
└── C. ORGANIZATION
    ├── My Programs
    ├── Playlists
    └── Preset Management
```

La sezione C non deve necessariamente essere sempre visibile. Può essere accessibile tramite una sottopagina o un pannello espandibile.

## 3.2 Layout desktop

La distribuzione consigliata è:

- Library: circa 58–62% della larghezza.
- Sound Configuration: circa 38–42%.
- Program Context: larghezza completa.
- Organization: sezione secondaria.

La Library deve avere la priorità visiva e disporre dello spazio necessario per leggere i nomi dei Program e dei Tone.

La Sound Configuration deve rimanere sempre visibile quando possibile.

## 3.3 Layout compatto

Per finestre con altezza o larghezza limitate:

1. Program Context rimane in testa.
2. Library e Sound Configuration diventano sezioni navigabili.
3. Mixer viene mantenuto accessibile senza occupare permanentemente spazio.
4. Organization viene spostata in una sezione secondaria.

Non devono essere semplicemente ridimensionati i controlli fino a renderli difficili da utilizzare.

# 4. Area A – Program Context

## 4.1 Obiettivo

Fornire una rappresentazione immediata del Program attualmente gestito e del suo stato.

## 4.2 Informazioni visualizzate

| Campo | Descrizione |
|---|---|
| Program ID | Identificativo, ad esempio E01 |
| Program Name | Nome del Program |
| Bank | Banco A–H |
| Type | Factory / User |
| Genre | Genere, se disponibile |
| Tempo | Tempo, se disponibile |
| Connection | Stato della connessione JD-Xi |
| Working State | Stato delle modifiche |

I dati non disponibili devono essere omessi o rappresentati con un valore neutro.

## 4.3 Azioni

| Comando | Comportamento |
|---|---|
| Rename | Rinomina il Program, nel rispetto dei limiti dello strumento |
| Save | Avvia il flusso di salvataggio appropriato |
| Save As | Crea una nuova copia, ove supportato |
| Compare | Accesso al confronto A/B, quando disponibile |
| Advanced | Apre le impostazioni avanzate del Program |

**Nota:** Save e Save As non devono simulare un salvataggio sullo strumento tramite SysEx. Il salvataggio permanente sul JD-Xi deve rispettare il flusso WRITE previsto dalla specifica Sound Design rev. 3.

## 4.4 Indicatore di stato

Devono essere rappresentati separatamente:

- Stato di connessione.
- Stato del Program.
- Stato di persistenza.

Esempi:

| Stato | Indicazione |
|---|---|
| OFFLINE | JD-Xi Off-line |
| ONLINE | JD-Xi Online |
| UNSTABLE | Comunicazione instabile |
| Originale | Nessuna modifica rispetto al riferimento |
| Modificato | Modifiche non ancora salvate |
| Temporaneo | Dati inviati al JD-Xi, non persistenti |
| Salvato su file | File .msz creato |
| Salvato in E01 | WRITE verificato |

Non utilizzare un unico badge per rappresentare condizioni differenti.

# 5. Area B1 – Library

## 5.1 Obiettivo

La Library diventa l'unico punto di accesso ai Program.

Vengono eliminate le distinzioni strutturali tra:

- Presets.
- User Programs.
- Library.

La distinzione Factory/User viene gestita attraverso le banche.

## 5.2 Organizzazione delle banche

| Banche | Tipologia |
|---|---|
| A–D | Factory Programs |
| E–H | User Programs |

La selezione iniziale deve essere All.

I pulsanti delle banche devono evidenziare chiaramente la selezione attiva.

Le informazioni Factory/User devono essere disponibili anche nei tooltip.

## 5.3 Ricerca

La ricerca deve considerare:

- Program ID.
- Program Name.
- Genre.
- Digital 1 Tone.
- Digital 2 Tone.
- Drum Kit.
- Analog Tone.

La ricerca deve essere case-insensitive.

La ricerca non deve modificare i dati originali.

Deve essere possibile combinare ricerca testuale, filtro genere e filtro banca.

Esempio:

```text
Bank: E
Genre: Lead
Search: Super Saw
```

Risultato: Program della banca E, di genere Lead, contenenti il testo ricercato in uno dei campi indicizzati.

## 5.4 Ordinamento

La tabella deve supportare:

- Ordinamento per ID.
- Ordinamento per nome.
- Ordinamento per genere.

Ordinamento predefinito: ID crescente.

## 5.5 Struttura della tabella

Colonne:

| Colonna | Contenuto |
|---|---|
| Bank/No. | Identificativo del Program |
| Program | Nome |
| Genre | Genere |
| Digital 1 | Tone assegnato |
| Digital 2 | Tone assegnato |
| Drums | Drum Kit assegnato |
| Analog | Tone assegnato |

Le colonne delle quattro parti devono essere leggibili anche quando i nomi sono lunghi.

Il tooltip deve mostrare il contenuto completo.

Se lo spazio disponibile è insufficiente, è ammessa una modalità compatta con una colonna aggregata Tones, purché rimanga possibile identificare ogni parte.

## 5.6 Selezione e caricamento

La selezione di un Program nella Library NON deve comportare automaticamente il caricamento sul JD-Xi.

Il comportamento è:

1. L'utente seleziona un Program.
2. La riga viene evidenziata.
3. Il pulsante Load viene abilitato.
4. Il Program selezionato viene mostrato nel pulsante.
5. L'utente conferma il caricamento.

Il doppio clic rimane una scorciatoia per il caricamento diretto.

Esempio:

```text
Selected: E01 – JG Lead

[ Load E01 ]
```

Il Program selezionato e quello effettivamente caricato devono essere distinguibili.

La selezione nella Library non deve modificare lo stato del Program corrente.

## 5.7 Conteggio

In fondo alla Library deve essere visualizzato:

- Numero di Program disponibili.
- Numero di risultati filtrati.

Esempio:

```text
24 of 512 Programs
```

# 6. Area B2 – Sound Configuration

## 6.1 Obiettivo

Mostrare immediatamente la struttura sonora del Program e consentire l'accesso diretto agli editor delle quattro parti.

## 6.2 Rappresentazione delle parti

Le quattro parti devono essere rappresentate attraverso quattro card.

Ogni card deve mostrare:

| Informazione | Descrizione |
|---|---|
| Part Name | Digital 1 / Digital 2 / Drums / Analog |
| Tone Name | Nome del Tone assegnato |
| MIDI Channel | Canale MIDI fisso |
| Volume | Livello, se disponibile e coerente con i dati aggiornati |
| Edit | Apertura dell'editor della parte |

Canali MIDI:

| Parte | Canale |
|---|---:|
| Digital 1 | 1 |
| Digital 2 | 2 |
| Analog | 3 |
| Drums | 10 |

Il canale Program è 16.

## 6.3 Interazione

Il click sulla card o sul comando Edit apre l'editor della parte corrispondente.

Il comportamento deve essere identico a quello già utilizzato da `open_part_editor()`.

Non devono essere create nuove istanze indipendenti degli engine di editing.

## 6.4 Aggiornamento

Quando il nome di un Tone cambia:

- La card corrispondente viene aggiornata.
- Il dato viene aggiornato anche nell'eventuale Library.
- Le finestre secondarie mantengono la coerenza con il Working State.

Non è consentito aggiornare soltanto l'etichetta grafica lasciando incoerenti i dati sottostanti.

# 7. Mixer

## 7.1 Obiettivo

Mantenere il Mixer integrato nella pagina Program.

Il Mixer deve consentire la regolazione dei livelli delle quattro parti attraverso i componenti esistenti.

## 7.2 Organizzazione

Il Mixer deve essere posizionato immediatamente sotto le quattro card oppure in un pannello espandibile.

La seconda soluzione è preferibile quando lo spazio verticale è limitato.

## 7.3 Requisiti

- Mantenere i controlli esistenti.
- Mantenere la compatibilità MIDI.
- Mantenere gli aggiornamenti bidirezionali previsti dal modello dati.
- Non duplicare i controlli di volume.
- Non introdurre una seconda gestione dei parametri.

Le etichette delle parti già presenti nel Mixer possono essere eliminate soltanto se le stesse informazioni sono chiaramente disponibili nelle card.

# 8. Area C – Organization

## 8.1 Obiettivo

Raggruppare le funzionalità di organizzazione senza confonderle con la selezione e la modifica del Program corrente.

La sezione deve essere accessibile attraverso una voce Organization o un pannello secondario.

## 8.2 My Programs

Contiene i Program User delle banche E–H.

Non deve essere una seconda Library.

Deve essere una vista filtrata della Library principale.

Funzionalità:

- Visualizzazione dei soli Program User.
- Ricerca.
- Rinomina.
- Duplicazione, ove supportata.
- Esportazione.
- Accesso alle operazioni di salvataggio sul JD-Xi.

La gestione delle sovrascritture deve rispettare i vincoli del dispositivo.

## 8.3 Playlists

Le Playlist devono consentire di organizzare i Program per utilizzo musicale.

Funzionalità:

- Creazione Playlist.
- Rinomina.
- Eliminazione.
- Aggiunta Program.
- Rimozione Program.
- Riordino degli elementi.
- Selezione di un Program dalla Playlist.
- Caricamento del Program selezionato.

La Playlist deve mantenere un riferimento al Program, non una copia indipendente del suo contenuto sonoro.

## 8.4 Playlist Editor

Il Playlist Editor non deve più essere una tab indipendente.

Deve diventare una modalità di modifica della Playlist selezionata.

La vista deve consentire:

- Modifica del nome.
- Modifica della sequenza.
- Inserimento e rimozione dei Program.
- Riordino.
- Salvataggio della Playlist.

L'attuale componente `playlist_editor_widget` deve essere riutilizzato, adattandone il contenitore e la navigazione.

## 8.5 Preset Management

La gestione dei preset non deve essere confusa con la Library dei Program.

I preset sono risorse utilizzabili durante il sound design.

La funzionalità deve quindi rimanere accessibile come strumento secondario, senza occupare una tab permanente nella pagina Program.

Non devono essere modificati i comportamenti di caricamento dei preset già implementati.

# 9. Gestione delle modifiche e protezione dei dati

Questa sezione è vincolante e deve essere coerente con `doc/proposals/sound-design.md`, revisione 3.

## 9.1 Stati distinti

La pagina Program deve rispettare il modello:

- Last Confirmed State (LCS).
- Working State (WS).
- Pending Changes (PC).

La UI non deve confondere un invio MIDI con un salvataggio permanente.

## 9.2 Cambio Program

Se l'utente tenta di caricare un altro Program mentre sono presenti modifiche a rischio, deve essere mostrato l'avviso uniforme:

- Salva prima.
- Scarta.
- Annulla.

L'avviso deve essere coerente con quello utilizzato negli altri editor.

## 9.3 Selezione Library

La semplice selezione di una riga non deve attivare l'avviso di perdita delle modifiche.

L'avviso viene attivato soltanto quando l'utente richiede un'operazione che comporta effettivamente l'abbandono o la sostituzione del Working State.

## 9.4 Salvataggio

Il flusso deve distinguere:

1. Modifica nell'app.
2. Invio al JD-Xi.
3. Salvataggio su file.
4. Salvataggio permanente sul JD-Xi tramite WRITE.
5. Verifica del salvataggio mediante rilettura.

Un messaggio di successo deve essere mostrato soltanto quando l'operazione è stata verificata.

## 9.5 Connessione

La pagina deve mostrare lo stato centralizzato della connessione:

- OFFLINE.
- DETECTED.
- VERIFYING.
- ONLINE.
- UNSTABLE.

I comandi devono essere abilitati o disabilitati in funzione dello stato effettivo.

Non introdurre controlli locali indipendenti per determinare la disponibilità del dispositivo.

# 10. Menu contestuale della Library

Il menu contestuale deve essere introdotto come funzionalità aggiuntiva.

Voci previste:

| Comando | Disponibilità |
|---|---|
| Load | Tutti i Program |
| Rename | Secondo i permessi e i vincoli |
| Duplicate | Secondo le capacità implementate |
| Add to Playlist | Tutti i Program |
| Export | Secondo il formato disponibile |
| Delete | Solo operazioni consentite sui Program User |

Le operazioni non supportate devono essere disabilitate, non simulate.

Il menu contestuale non deve sostituire il pulsante Load.

# 11. Aspetti grafici e UX

## 11.1 Gerarchia visiva

Ordine di importanza:

1. Program corrente e relativo stato.
2. Library.
3. Parti del Program.
4. Mixer.
5. Organization.

## 11.2 Coerenza grafica

Mantenere:

- Tema V2.
- Accento cromatico verde già utilizzato.
- Tipografia esistente.
- Stile delle card.
- Spaziature coerenti con il modulo `density`.

Non introdurre un nuovo sistema grafico.

## 11.3 Feedback

Ogni operazione deve fornire un feedback appropriato:

- Selezione: evidenziazione.
- Caricamento: indicatore di operazione.
- Errore MIDI: messaggio esplicito.
- Modifica: indicatore Modified.
- Salvataggio: conferma verificata.
- Comunicazione instabile: avviso persistente.

Evitare notifiche ridondanti.

# 12. Architettura tecnica e vincoli di implementazione

## 12.1 File principale

`jdxi_editor/ui/v2/programs.py`

La classe `ProgramEditor` deve mantenere la compatibilità con il sistema di registrazione e individuazione già presente.

Non rinominare la classe senza una verifica completa dei riferimenti.

## 12.2 Componenti esistenti da riutilizzare

- `ProgramLibrary`
- `ProgramEditor`
- `program_group_widget`
- `mixer_panel`
- `mixer_widget`
- `user_programs_widget`
- `playlist_widget`
- `playlist_editor_widget`
- `preset` widget

## 12.3 Principi architetturali

- Non duplicare gli engine MIDI.
- Non duplicare la gestione del Working State.
- Non introdurre una seconda fonte dei dati Program.
- Non modificare il protocollo SysEx per esigenze esclusivamente grafiche.
- Conservare la compatibilità con gli editor esistenti.
- Evitare dipendenze circolari tra Library, Program Editor e Playlist.
- Separare presentazione, modello dati e operazioni MIDI.

## 12.4 Gestione della Library

La Library deve continuare a utilizzare i dati Program già forniti dall'editor originale.

L'estensione della ricerca deve utilizzare i campi già presenti nell'oggetto Program:

- `id`
- `name`
- `genre`
- `digital_1`
- `digital_2`
- `drums`
- `analog`

Non introdurre un modello dati parallelo.

# 13. Criteri di accettazione

| ID | Scenario | Risultato atteso |
|---|---|---|
| PR-01 | Apertura Program | Tutte le aree principali sono visibili |
| PR-02 | Selezione Program | Evidenziazione senza caricamento MIDI |
| PR-03 | Caricamento tramite pulsante | Caricamento del Program selezionato |
| PR-04 | Doppio clic | Caricamento diretto |
| PR-05 | Filtro banca | Visualizzazione dei soli Program della banca |
| PR-06 | Filtro genere | Risultati corretti |
| PR-07 | Ricerca nome | Ricerca corretta |
| PR-08 | Ricerca Tone | Individuazione dei Program contenenti il Tone |
| PR-09 | Filtri combinati | Risultati coerenti |
| PR-10 | Ordinamento | Ordinamento corretto per ID, nome e genere |
| PR-11 | Selezione User | Distinzione rispetto ai Factory |
| PR-12 | Apertura editor parte | Apertura dell'editor corretto |
| PR-13 | Modifica Tone | Aggiornamento della card corrispondente |
| PR-14 | Mixer | Funzionamento invariato |
| PR-15 | Playlist | Gestione completa dalla nuova sezione |
| PR-16 | Preset Management | Funzionamento invariato |
| PR-17 | Cambio Program con modifiche | Avviso uniforme |
| PR-18 | OFFLINE | Comandi di comunicazione disabilitati |
| PR-19 | ONLINE | Comandi disponibili |
| PR-20 | UNSTABLE | Stato e feedback coerenti |
| PR-21 | Salvataggio WRITE | Nessuna conferma prima della verifica |
| PR-22 | Layout compatto | Nessun controllo essenziale inaccessibile |
| PR-23 | Program Factory | Nessuna operazione distruttiva non consentita |
| PR-24 | Program User | Operazioni consentite correttamente |

# 14. Strategia di implementazione

L'implementazione deve essere incrementale.

| Fase | Attività | Priorità |
|---|---|---|
| 1 | Revisione layout generale | P1 |
| 2 | Unificazione Library, Presets e User Programs | P1 |
| 3 | Miglioramento ricerca e filtri | P1 |
| 4 | Revisione Sound Configuration | P1 |
| 5 | Distinzione stati selezione/caricamento | P1 |
| 6 | Integrazione Playlist e Playlist Editor | P2 |
| 7 | Revisione Organization | P2 |
| 8 | Menu contestuale | P3 |
| 9 | Ottimizzazione responsive | P2 |
| 10 | Rifiniture grafiche | P3 |

Le fasi devono mantenere funzionanti i test esistenti.

# 15. Test di regressione

Oltre ai nuovi test, devono essere mantenuti e verificati:

- `tests/test_v2_programs.py`
- `tests/test_v2_program.py`
- `tests/test_jdxi_program.py`
- Test di gestione Playlist.
- Test di connessione MIDI.
- Test della macchina a stati Sound Design.
- Test di salvataggio e verifica WRITE.

I test grafici devono verificare la presenza dei componenti, le relazioni tra essi e i comportamenti principali.

I test MIDI devono verificare che la riorganizzazione grafica non modifichi i messaggi inviati allo strumento.

# 16. Fuori ambito

Non fanno parte di questa revisione:

- Riscrittura degli editor Digital, Analog e Drums.
- Modifiche al protocollo SysEx.
- Modifiche ai parametri sonori.
- Modifiche al motore MIDI.
- Nuove funzionalità A/B.
- Nuove funzionalità di sound design.
- Modifiche al modello di persistenza.
- Introduzione di un nuovo database Program.

Le funzionalità di confronto A/B potranno essere integrate successivamente nel Program Context senza modificare la struttura principale.

# 17. Risultato atteso

La nuova tab Program deve diventare un ambiente di lavoro unitario, nel quale l'utente possa:

- Individuare un Program.
- Caricarlo sul JD-Xi.
- Comprenderne la composizione.
- Modificarne le parti.
- Regolarne il mix.
- Organizzarlo nelle Playlist.
- Gestirne il salvataggio.

La riduzione delle tab non deve comportare perdita di funzionalità.

Il risultato deve essere un'interfaccia più semplice da comprendere, con una distinzione netta tra consultazione, modifica, organizzazione e persistenza dei Program.

**Principio conclusivo:** la pagina Program deve rappresentare il Program come un'entità musicale completa, non come un insieme di funzionalità tecniche separate.

---

# 18. Valutazione e modifiche (19/11)

Verificato sul codice di `dev/sound-design`. Dove questo paragrafo contraddice i precedenti,
vale questo paragrafo.

## 18.1 Già presente (non va rifatto)

- Selezione distinta dal caricamento (§5.6): la selezione non carica; il pulsante diventa
  «Carica E01»; il doppio clic carica. Resta da rendere visibile **quale** programma è caricato
  (riga marcata nella Library e nel contesto), non solo quello selezionato.
- Filtro All / banche A–H con tooltip Preset/User, filtro genere, conteggio programmi.
- Ricerca per ID e nome. **Da estendere** ai quattro Tone e al genere (§5.3): i campi
  `digital_1`, `digital_2`, `drums`, `analog` esistono già nell'oggetto Program.
- `user_programs_widget` cerca già per ID, nome, genere e Tone: la sua logica di ricerca si riusa
  nella Library.

## 18.2 Correzioni alla specifica

1. **«Presets» non sono Program (UX-01 vs §8.5).** La sotto-tab Presets (`PresetWidget`) sceglie
   un **Tone preset per una parte** (Digital 1/2, Analog, Drums), non un programma: non si può
   unificare con la Library. Invece la scelta del Tone diventa un'azione della **card della parte**
   (§6): clic sul nome del Tone → selettore dei Tone di quella parte (componente esistente). Così
   sparisce la sotto-tab e la funzione sta dove l'utente la cerca. UX-01 vale solo per **User
   Programs** (→ filtro E–H della Library, §8.2).
2. **Card delle parti e Mixer uniti (§6, §7, UX-08).** Invece di quattro card **e** un mixer con
   le stesse quattro parti, ogni **striscia del mixer è la card della parte**: nome e colore della
   parte, Tone (cliccabile, punto 1), canale, fader di livello, mute, «Modifica». Il **Master**
   resta una striscia a parte. Nessun controllo di volume duplicato, molto meno spazio verticale,
   una sola fonte dei dati (gli stessi controlli di `mixer_panel`).
3. **Colori (§11.2, richiesta del 19/11).** Ogni parte usa il **colore della sua tab** in tutta
   l'app (titolo, fader, valore, icona): Digital 1 rosso `#eb5757`, Digital 2 arancio `#f2994a`,
   Drums viola `#a78bfa`, Analog blu `#3fa7f5`. Il **Master** si distingue con un neutro chiaro
   (argento/bianco), non con un colore di parte né col verde della tab Programmi (che resta per
   titoli e azioni). L'icona del Master (oggi una tastiera nera quasi invisibile) diventa un
   simbolo di uscita/somma, chiaro come il fader.
4. **Comandi coerenti con lo strumento (§4.3, §10).** Il JD-Xi salva solo con WRITE in E–H e non
   cancella programmi:
   - **Salva** = WRITE guidato (Fase 4 di `sound-design.md`); **Salva su file** = .msz.
   - **Salva come / Duplica** = WRITE guidato in un **altro** posto (stessa procedura): non un
     comando separato.
   - **Rinomina** vale solo per il programma **caricato** (il nome diventa permanente con WRITE);
     nel menu contestuale è attiva solo sulla riga caricata.
   - **Elimina: tolto.** Un programma User non si cancella; al massimo si sovrascrive con un Init
     tramite WRITE, cosa già coperta da «Nuovo suono» + Salva.
   - **Esporta**: .msz o .syx del programma caricato; per gli altri, dopo il caricamento.
5. **Contesto del programma (§4) = riga di contesto di `sound-design.md` §4.** Un solo componente,
   usato anche negli editor e nelle finestre staccate; stessi stati (collegamento, modifiche,
   persistenza), senza badge duplicati (decisione 8 di `sound-design.md`).
6. **Colonne della Library (§5.5).** Quattro colonne Tone nella larghezza del 60% troncano i nomi:
   predefinita la colonna unica «Tones» con i quattro nomi colorati come le parti e tooltip
   completo; quattro colonne quando la finestra è larga. Ordinamento per ID, nome, genere
   (oggi assente).
7. **Playlist (§8.3–8.4)**: d'accordo; l'editor di playlist diventa la modalità «Modifica» della
   playlist selezionata, riusando `playlist_editor_widget`.
8. **Ordine di sviluppo.** La parte grafica (Library, card/mixer, colori, playlist) non dipende
   dalla Connection e può partire subito dopo la Fase 0. Stati di collegamento (§9.5, PR-18…20) e
   Salva/WRITE (PR-21) seguono le Fasi 1 e 4 di `sound-design.md`: fino ad allora i comandi usano
   le verifiche attuali.

## 18.3 Criteri di accettazione aggiunti

| ID | Scenario | Risultato atteso |
|---|---|---|
| PR-25 | Clic sul Tone di una parte | Selettore dei Tone di quella parte; la scelta si riflette su striscia, Library e editor |
| PR-26 | Colori | Ogni parte ha il colore della sua tab ovunque; il Master è neutro e distinguibile |
| PR-27 | Programma caricato vs selezionato | Riconoscibili entrambi nella Library |
| PR-28 | Menu contestuale su un programma non caricato | Rinomina/Esporta spenti con motivo nel tooltip; nessun Elimina |

