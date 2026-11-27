# Piano di test con il JD-Xi collegato

La verifica di ogni rilascio sullo strumento vero. La prima parte la fa uno script
(`scripts/hardware_check.py`); il resto è una sequenza a mano, pensata per essere eseguita con
calma, ascoltando: ogni passo dice cosa fare, cosa deve succedere e dove guardare se non succede.

**Durata**: circa 75 minuti la prima volta, 45 dalle successive (con *Rapido* solo i passi
segnati ★: circa 20 minuti).

**Come segnare**: per ogni passo **OK**, **KO** (con una nota: cosa è successo, su quale schermo)
o **—** (non eseguito). Un KO non ferma la sequenza, salvo dove è scritto. A fine sessione copia
la tabella del [resoconto](#resoconto) nella issue o nella PR del rilascio, con il file dello
script e, se ci sono KO, il log (Strumenti › Visualizzatore log, Ctrl+Maiusc+L, scheda *Avvisi ed errori*).

---

## 0. Preparazione (10 minuti)

| | Cosa | Perché |
|---|---|---|
| 0.1 | JD-Xi acceso, collegato via **USB** al PC; driver Roland installato (Windows) | Le porte MIDI "JD-Xi" devono comparire |
| 0.2 | **Salva sul JD-Xi** (WRITE) quello che ti serve: i test cambiano programma e suoni temporanei | Nulla viene scritto nella memoria utente, ma il suono corrente si perde |
| 0.3 | Cuffie o monitor a volume **basso**, poi lo alzi | Alcuni passi cambiano livelli e filtri |
| 0.4 | Installa il rilascio da verificare (Windows: installer o portatile; macOS: il `.dmg`; Linux: il `.deb` con `sudo apt install ./…`) e annota versione, sistema e schermo (risoluzione e scala) | Il resoconto deve dire *cosa* è stato provato *dove* |
| 0.5 | Tieni a portata: un file `.jsz` o `.syx` di prova, un file MIDI breve, una ricetta (`JD-Xi recipe - example.csv`) | Servono nelle sezioni 7, 9, 10 |

---

## 1. Parte automatica — script (5 minuti) ★

Con **JD-Xi Studio chiuso** (su Windows una porta MIDI può essere aperta da un solo programma):

```
python scripts/hardware_check.py
```

Lo script, da solo:

1. trova le porte del JD-Xi e chiede l'identità (Identity Request): deve rispondere un JD-Xi. La *revisione* nella risposta non è la versione del firmware: quella si legge sul display del JD-Xi all'accensione e va annotata a mano nel resoconto;
2. legge le aree temporanee di Programma, Digital 1, Digital 2, Analog, Drums (RQ1 → DT1) e ne mostra i nomi;
3. per ogni area scrive un parametro (livello −5), lo rilegge, lo **rimette com'era** e lo rilegge ancora;

poi ti guida, aspettando le tue risposte:

4. suona tre note su ogni parte (Drums: kick, snare, charleston) e chiede se le hai sentite;
5. abbassa e rialza il livello di Digital 1 e sposta il cutoff (CC 74): chiede se hai sentito la differenza;
6. **solo se rispondi sì**, cambia programma (A01, poi A02) e verifica che i nomi letti cambino.

Il resoconto va in `~/.jdxi_studio/hardware-checks/<data>-<versione>.md`.
Senza domande (solo i punti 1–3): `--auto`. Solo le porte: `--list`.

**Se fallisce il punto 1**: cavo, driver, un altro programma che tiene aperta la porta
(DAW, un'altra copia di JD-Xi Studio). Inutile proseguire finché non passa.

---

## 1a. Prove automatiche sul JD-Xi (5 minuti) ★

Sempre con JD-Xi Studio chiuso, dalla cartella del progetto:

```
pytest -m hardware tests/test_jdxi_checks.py
```

Le stesse prove girano a ogni modifica sul JD-Xi simulato; qui sullo strumento vero. Ognuna salva il
programma temporaneo del JD-Xi prima di cominciare e lo rimette com'era alla fine. Controllano da
sole: l'identità (collegato solo se risponde un JD-Xi, passo 2.9), la lettura completa del
programma, una modifica «inviata» finché non viene riletta, la riconnessione senza cambiamenti
(2.10) e con una parte cambiata e ripristinata (2.11), Init dell'Analog e il suo Annulla sullo
strumento (6b.1).

Il salvataggio con WRITE (6.8) chiede una mano sul JD-Xi e un posto che si può sovrascrivere:

```
JDXI_WRITE_SLOT=H64 pytest -m hardware -s tests/test_jdxi_checks.py -k write
```

La prova prepara il nome, dice cosa premere sul JD-Xi, aspetta Invio e verifica rileggendo il posto.
Copia nel resoconto la riga finale di pytest (es. «7 passed, 1 skipped»).

## 1b. Autotest dentro l'app (5 minuti) ★

JD-Xi › **Autotest…** › Avvia. L'app carica un programma e dei toni, modifica e
annulla un valore, cambia ottava e suona una nota, verificando ogni risultato sul JD-Xi; poi ti
chiede di agire sul JD-Xi (TONE, OCTAVE, qualche nota) e controlla che la finestra segua. Alla
fine ricarica il programma iniziale e salva un resoconto in `~/.jdxi_studio/reports`: allegalo
al tuo resoconto.

---

## 2. Avvio e collegamento (5 minuti) ★

| | Fai | Deve succedere |
|---|---|---|
| 2.1 | Avvia JD-Xi Studio | Splash con il logo, la versione (es. «Versione 1.0.0») uguale a quella installata; nessun messaggio d'errore |
| 2.2 | Finestra MIDI all'avvio (o JD-Xi › Configurazione MIDI) | Ingresso e uscita **JD-Xi** già scelti; la finestra è davanti alle altre, anche con la tastiera fissata in primo piano |
| 2.3 | Guarda la barra in alto a destra dell'editor | «JD-Xi collegato» in verde; il nome del programma corrente del JD-Xi nel display |
| 2.4 | Strumenti › Visualizzatore log | Il log di questa sessione (con data e ora nel nome); scheda *Avvisi ed errori* vuota o quasi; **nessuna** riga «MIDI output port is not open» o «No reply to RQ1» |
| 2.5 | Cambia programma **dal JD-Xi** (manopola PROGRAM) | Il display dell'app segue entro un secondo |
| 2.6 ★ | Avvia l'app **senza** JD-Xi (cavo staccato) | Lo splash arriva in fondo; poi, dopo lo splash, l'avviso «JD-Xi non collegato» (una volta sola) e il badge **Off-line** sotto MIDI IN/OUT e in alto a destra negli editor |
| 2.7 | Off-line: passa il mouse su «Salva sul JD-Xi…», su un tono nel mixer, su File › Patch › Salva | Spenti, il tooltip dice perché |
| 2.8 ★ | Off-line: cambia il cutoff in Digital 1, poi collega il JD-Xi | «Verifica del JD-Xi…», poi verde; avviso «Le modifiche fatte senza JD-Xi vengono abbandonate» con **Salva come file…**; dopo, l'editor mostra i valori del JD-Xi |
| 2.9 | Configurazione MIDI: scegli due porte che **non** sono il JD-Xi (es. un'altra interfaccia) | Mai «JD-Xi collegato»: resta «Verifica del JD-Xi…» |
| 2.10 ★ | Collegato, modifica un suono senza salvare; **stacca e riattacca** il cavo USB | Off-line, poi di nuovo collegato: «Ricollegato: il JD-Xi contiene quello che conteneva prima» |
| 2.11 ★ | Come 2.10, ma da staccato **spegni e riaccendi** il JD-Xi e cambia programma prima di ricollegarlo | Domanda con le parti diverse: **Ripristina sul JD-Xi** riporta il tuo suono (e lo dice parte per parte); **Tieni quello che ha il JD-Xi** lascia quello nuovo |

---

## 3. Finestra tastiera (5 minuti)

| | Fai | Deve succedere |
|---|---|---|
| 3.1 | Clicca i tasti a schermo | Suona la parte selezionata |
| 3.2 | Part Select: Digital 1, Digital 2, Drums, Analog | Si accende il tasto della parte e si apre la scheda giusta nella finestra degli editor; mai due tasti accesi |
| 3.3 | Clicca il display | Si apre *Programmi*; nessun tasto Part Select resta acceso |
| 3.4 | Octave −/+ e Arpeggio on/off | Il JD-Xi segue (LED sul pannello) |
| 3.5 | Spillo nella barra della finestra: fissa in primo piano, poi chiudi e riapri il programma | Fissata durante la sessione; alla riapertura **non** fissata |
| 3.6 | All'avvio, senza toccare nulla | Entro 2–3 secondi il display mostra il programma e il tono della parte del JD-Xi (non «Init Tone»); gli slider del pannello sono sui valori del tono |
| 3.7 | Scegli la parte nell'app, poi cambia tono **dal JD-Xi** | Entro ~2 secondi il display mostra il nuovo tono e gli slider si spostano sui suoi valori |
| 3.8 | OCTAVE −/+ **sul JD-Xi** | Entro ~2 secondi si accende Octave − o + nell'app |
| 3.9 | Finestre su due monitor (o sovrapposte): **Editor** nella barra dei menu della tastiera, poi **Tastiera** in alto a destra negli editor; ripeti con lo spillo attivo | Ogni pulsante porta l'altra finestra davanti, sul suo monitor, senza Alt+Tab; con lo spillo gli editor vengono avanti ma, dove si sovrappongono, restano sotto la tastiera |
| 3.10 | JD-Xi scollegato: apri i menu File e JD-Xi | Spenti, con il motivo nel suggerimento: Patch › Salva…, MIDI Player › Salva / Salva con nome (finché non apri un file), Salva il programma, Invia tutto, Leggi i programmi utente, Autotest |
| 3.9 | Suona sulla tastiera del JD-Xi, poi ripeti con OCTAVE +1 e −1 | Nella finestra si illuminano i tasti nella stessa posizione di quelli premuti, a ogni ottava (anche il Do più alto e il più basso); rilasciati, si spengono |
| 3.9a | Muovi la leva pitch e la rotella mod del JD-Xi; poi muovi quelle della finestra e lasciale | Le rotelle della finestra seguono quelle del JD-Xi; la leva pitch della finestra, lasciata, torna al centro e il suono torna intonato; la mod resta dove la lasci |
| 3.9b | Con Digital 1 mostrato, gira sul JD-Xi Cutoff, Resonance, Level, LFO Rate e le manopole degli effetti (Reverb, Delay) | Gli slider della finestra si muovono subito con le manopole (non dopo un paio di secondi) |
| 3.10 | Nella scheda di un tono, frecce ‹ › del pannello preset | Il JD-Xi carica subito il tono (come i suoi tasti); cliccando più volte di fila viene caricato solo quello su cui ti fermi |

---

## 4. Editor dei suoni (20 minuti) ★

Per ognuno: apri la scheda, aspetta la lettura (i controlli si allineano allo strumento), poi
**suona dal JD-Xi** mentre cambi i valori. Il suono deve cambiare *mentre* muovi il controllo.

| | Editor | Fai | Deve succedere |
|---|---|---|---|
| 4.1 ★ | **Digital 1** | Scegli un preset dalla lista (categoria, poi suono) | Il JD-Xi cambia suono; display e scheda della categoria si aggiornano |
| 4.2 ★ | Digital 1 | Cutoff e Resonance del FILTER di un partial; trascina un punto dell'inviluppo nel grafico | Lo senti cambiare subito; il grafico e le manopole restano allineati |
| 4.3 | Digital 1 | Partial 2 e 3 on/off; selezione del partial | Si sentono/spariscono gli strati; le schede *OSC · FILTER · AMP* / *LFO · MOD LFO · MISC* (schermo basso) restano sulla stessa per tutti i partial |
| 4.4 | Digital 2 | Come 4.1 su Digital 2 | Cambia solo Digital 2 (canale 2) |
| 4.4a ★ | Digital 1 | Partial 1 e 2 accesi, 3 spento; **Collega 1·2·3** (lega i tre partial di questa parte, non Digital 1 con Digital 2); gira il Cutoff del partial 1; poi Annulla | Il Cutoff cambia anche sul partial 2 (si sente su entrambi), non sul 3; forma d'onda e pitch restano diversi; un solo Annulla riporta tutti e due |
| 4.4b | Digital 1 › Digital 2 | **Partial ▾ › Copia sezione › Filtro** su Digital 1; in Digital 2 **Partial ▾ › Incolla**; poi **Scambia con il partial 2** | Il filtro di Digital 2 diventa quello copiato; lo scambio inverte i due partial; ognuna è un Annulla |
| 4.4c ★ | Digital 1 | Partial su **PCM**, clic su *Wave Number*; famiglia *Campane e metallici*, **Prova** acceso; scorri con le frecce; Annulla, poi riapri e OK | Ogni onda suona un C4 breve sul canale 1; Annulla rimette l'onda di prima; OK tiene quella scelta |
| 4.4d | Digital 1 | **Partial ▾ › Casuale…**: Sezione Filtro, Poco; poi Tutto il tono, Molto; premi più volte; Annulla | Il suono cambia ma resta udibile; nome e categoria non cambiano; Annulla torna indietro di una pressione |
| 4.4e | Digital 1 | MISC › *Loop Mode* TEMPO-SYNC, *Sync Note* 1/4 | Sui grafici di FILTER e AMP l'attacco-decadimento si ripete con «loop 1/4»; lo senti pulsare a tempo |
| 4.5 ★ | **Analog** | Preset, poi Cutoff, Resonance, LFO Rate; trascina il grafico del filtro; Annulla (Ctrl+Z); scrivi un nome in *Tone Name* | Lo senti cambiare e tornare indietro con Annulla; badge «ANALOG» in alto a sinistra; il nuovo nome sul display del JD-Xi |
| 4.6 ★ | **Drums** | Scegli un kit; clicca un pad, cambia Pitch e Level del pad | Suona il pad scelto e cambia solo lui |
| 4.7 | Effetti | Effect 1 su Distortion, poi Thru; Delay Time; Reverb tipo HALL1 | Lo senti; il riquadro di Effect 1 è alto quanto il tipo scelto (Thru: piccolo) |
| 4.8 | Effetto voce | Vocoder on, Auto Pitch con un tipo e una tonalità (serve un microfono sul JD-Xi) | Senza microfono: annota **—** |
| 4.9 | Arpeggio | Arpeggio on dal pannello dell'app, Style e Grid; tieni un accordo | L'arpeggio segue i cambi |
| 4.10 | Leggi dal JD-Xi | Cambia un valore **sul JD-Xi** (una manopola), poi *Leggi dal JD-Xi* nell'editor | Il controllo dell'app mostra il nuovo valore |

---

## 5. Annulla, Ripeti, Reload e modifiche non salvate (10 minuti) ★

In **Digital 1**, con un preset appena caricato:

| | Fai | Deve succedere |
|---|---|---|
| 5.1 ★ | Muovi il Cutoff (un trascinamento solo) | Compare **● Modificato** accanto al nome e un pallino sulla scheda; Annulla e Reload attivi |
| 5.2 ★ | **Ctrl+Z** | Il Cutoff torna indietro in un passo solo e **lo senti** tornare; *Modificato* sparisce; Reload si spegne |
| 5.3 | **Ctrl+Y** | Il Cutoff torna al valore modificato e lo senti |
| 5.4 | Trascina un punto dell'inviluppo che muove due valori (Decay e Sustain), poi Ctrl+Z | Tornano indietro **entrambi** in un passo |
| 5.5 ★ | Fai 4–5 modifiche diverse, poi **Reload** (⟳) › conferma | Tutti i valori tornano come al caricamento del preset; lo senti; nessun *Modificato* |
| 5.6 ★ | Modifica di nuovo, poi scegli un **altro preset** | Domanda *Modifiche non salvate*: prova **Annulla** (resta tutto com'era), poi **Scarta** (cambia preset) |
| 5.7 | Modifica, poi *Salva su file…* dalla domanda; salva; rifai il cambio di preset | Dopo il salvataggio non chiede più; il file esiste |
| 5.8 | Modifica Digital 1, poi cambia preset di **Analog** | **Nessuna** domanda (riguarda solo la parte che cambia) |
| 5.9 | Modifica, cambia un valore **sul JD-Xi** dello stesso parametro, poi Ctrl+Z | Ctrl+Z non riporta il valore vecchio su quel parametro |
| 5.10 | Con una modifica non salvata, chiudi il programma | Domanda; *Annulla* lo tiene aperto |
| 5.11 | Ctrl+Z con la scheda **Programmi** visibile | Non succede nulla (non annulla in un editor nascosto) |

---

## 5b. Confronto A/B (10 minuti) ★

In Digital 1 (poi ripeti in breve per Digital 2 e Analog). Tra parentesi il caso della matrice
TC-xx della proposta; gli stessi casi girano in automatico con un JD-Xi simulato
(`tests/test_ab_compare.py`).

| | Fai | Deve succedere |
|---|---|---|
| 5b.1 ★ | Scegli **A** (vuota, bordo tratteggiato) e premi la **fotocamera** | «A acquisita»; il JD-Xi viene riletto prima (TC-01) |
| 5b.2 ★ | Cambia Cutoff e un'onda; scegli **B** e premi la fotocamera | «B acquisita»; A e B si sentono diverse (TC-02) |
| 5b.3 ★ | Suona una frase; premi A, risuonala; premi **⇄** (o Ctrl+Shift+A), risuonala; ripeti 4-5 volte | Ogni volta il suono e l'editor passano a quello giusto in meno di un secondo; lo slot attivo è pieno del colore della scheda (TC-03, 04, 05) |
| 5b.4 | Con A attiva, gira una manopola (nella finestra o sul JD-Xi) | Compare il pallino su A; ripremendo A torna il suono di A (TC-06, 07) |
| 5b.5 | Con B attiva premi il **dischetto**, dai un nome; poi lo stesso con A | Due file .syx; l'Import dell'editor li legge e il display del JD-Xi mostra il nome (TC-08, 09, 10) |
| 5b.6 | In Digital 1 richiama A mentre Digital 2, Analog e Drums suonano un pattern | Cambia solo Digital 1 (TC-11, 12, 13) |
| 5b.7 | Richiama B e stacca il cavo USB durante il richiamo; poi lascia il cavo staccato | Avviso «Tone incerto», nessuno slot pieno; ⇄ spento; ricollegato, B si richiama (TC-14) |
| 5b.8 | Cambia programma sul JD-Xi, poi premi A | Prima di inviare chiede conferma (TC-15) |
| 5b.9 | Scegli A (già piena, mai salvata) e premi la fotocamera | Chiede: Salva prima… / Sostituisci / Annulla (TC-16) |
| 5b.10 | Chiudi e riapri JD-Xi Studio | A e B ci sono ancora per ogni parte; non viene inviato nulla finché non premi A o B (TC-17) |
| 5b.11 | Dopo un richiamo: cambia un valore, Annulla, Ripeti, Reload | Funzionano come sempre (TC-18) |
| 5b.12 ★ | Con A e B piene e diverse, B attiva: il pulsante **Prendi** (due frecce che si uniscono), da A spunta solo *FILTER P1* | Il filtro del partial 1 diventa quello di A, il resto resta B; un Annulla lo toglie |

---

## 6. Programmi (5 minuti)

| | Fai | Deve succedere |
|---|---|---|
| 6.1 ★ | Libreria: cerca un nome, filtra per genere, banco B | La lista si filtra; doppio clic carica il programma sul JD-Xi; display aggiornato |
| 6.2 | Le quattro parti nel mixer | I quattro toni corrispondono a quelli mostrati dal JD-Xi |
| 6.3 | Mixer: abbassa Digital 1, muta Drums | Lo senti; il JD-Xi segue |
| 6.4 | Libreria: cerca il nome di un **tono** (es. «Saw»), ordina per nome, allarga la colonna Nome | Trova i programmi che lo usano; i toni colorati come le parti; la barra orizzontale se non entrano |
| 6.5 | Carica un programma, poi selezionane un altro | Il caricato resta marcato ▶ in grassetto; il pulsante dice «Carica» + quello selezionato; la riga di contesto dice «Programma A11 «…» · originale» |
| 6.6 | Nel mixer: clic sul nome di un tono | Si apre la scelta dei toni di **quella** parte; scegline uno: lo senti, l'origine nella riga di contesto diventa «preset …» |
| 6.7 | Organizza: crea una playlist, aggiungi un programma **A–D** e uno **E–H**, avvia | Entrambi in lista; mentre suona la riga di stato e le barre dicono quale brano |
| 6.8 ★ | **Salva sul JD-Xi…**: nome, posto proposto («probabilmente libero»), Avanti; fai sul JD-Xi i passi indicati (Shift + Menu/Write, scegli il posto, Enter, Enter), poi **Fatto** | «Salvato in E.. ✓»; il JD-Xi resta su quel posto; la riga di contesto dice «salvato in E..» |
| 6.9 ★ | Come 6.8, ma **non** premere WRITE sul JD-Xi prima di Fatto | Nessuna conferma: «Non risulta salvato…», con le parti diverse |
| 6.10 | Come 6.8 scegliendo un posto con un programma tuo | Prima la domanda «Sostituire E.. «…»?», con Annulla predefinito |
| 6.13 | Nel mixer sposta il fader di Digital 1, poi apri la scheda Digital 1; torna in Programmi e premi **Annulla** | Il Tone Level di Digital 1 segue il fader e la scheda ha la matita; Annulla (suggerimento «Annulla: Tone Level (Digital 1)») riporta fader, manopola e suono com'erano |
| 6.11 ★ | Carica un programma; nel mixer guarda Pan, Delay e Reverb di ogni parte, poi gira il Pan di Digital 1 e il Reverb di Drums | All'avvio i valori sono quelli del JD-Xi; lo senti spostarsi e cambiare; **Impostazioni programma** (subito dopo Programmi) mostra gli stessi valori |
| 6.12 | In **Impostazioni programma › Principale** metti il Part Output di Analog su REV, poi DIR | Nel mixer, con REV il Delay di Analog si spegne; con DIR anche il Reverb |

## 6b. Nuovo suono e aiuti (5 minuti)

| | Fai | Deve succedere |
|---|---|---|
| 6b.1 ★ | Digital 1: Nuovo suono › Da zero (Init) | Un dente di sega semplice, filtro aperto; le altre parti e gli effetti non cambiano; **un** Annulla riporta il suono di prima |
| 6b.2 | Analog: Nuovo suono › Da zero (Init) | Come sopra, per l'Analog |
| 6b.3 | Ricette: applica un passo che tocca più editor, poi Annulla in uno solo | Tornano indietro tutti gli editor toccati dal passo |
| 6b.4 | Il «?» di OSC, FILTER, AMP, LFO, EFFECT | Nel pannello informativo: cosa modifica, come cambia il suono, un esempio |

---

## 7. File: patch e SysEx (5 minuti)

| | Fai | Deve succedere |
|---|---|---|
| 7.1 ★ | File › Patch › Salva… (`.jsz`) | Il file viene creato; i *Modificato* spariscono |
| 7.2 ★ | Cambia suoni, poi File › Patch › Apri… dello stesso file | Il suono torna quello salvato (ascolta) |
| 7.3 | Salva come `.syx`, ricarica | Come 7.2 |

---

## 8. Pattern (5 minuti)

| | Fai | Deve succedere |
|---|---|---|
| 8.1 | Accendi alcuni passi nelle quattro righe; Play | Il JD-Xi suona il pattern al BPM indicato; Stop lo ferma |
| 8.2 | Tap tempo, Passi 32, Aggiungi misura | Il pattern segue |
| 8.3 | Clic destro su un passo | Le note del passo; modificabili |

---

## 9. File MIDI (5 minuti)

| | Fai | Deve succedere |
|---|---|---|
| 9.1 | Apri un file MIDI breve; Play | Suona sul JD-Xi con le parti assegnate; **nessuna** domanda sulle modifiche non salvate durante la riproduzione |
| 9.2 | Mute di una traccia, Stop, ripresa | Come atteso; nessuna nota appesa dopo Stop |
| 9.3 ★ | **Registratore USB** (cavo USB, nessun cavo audio): la porta proposta è l'**ingresso** del JD-Xi (non «Speakers»), con «(stereo)»; scegli il file, spunta **Registra a ogni Play**; Play di 20–30 secondi, Stop | Un `.wav` stereo, 16 bit, che si sente come il JD-Xi: suono **non** solo a sinistra, panning ed effetti stereo presenti; dopo lo Stop si chiude entro un secondo (non 10 secondi dopo) |
| 9.4 | Come 9.3 con una playlist di due brani brevi | Due `.wav`, uno per brano; il primo si chiude quando parte il secondo |
| 9.5 ★ | Un file MIDI «generale» (molte tracce, canali oltre il 3): **Adatta al JD-Xi › Assegna le tracce alle parti…**, controlla la proposta, Applica; Play | La riga dice quante tracce non si sentono prima, «Pronto» o meno dopo; batteria su Drums, una traccia per Digital 1, Digital 2, Analog; nessuna nota appesa |
| 9.6 | **Suoni di partenza**, poi Play | Digital 1 Picked Bass, Digital 2 Piano, Analog JP8 Strings (un preset Digital sulla parte Analog) |
| 9.7 | Un file grande (40+ tracce): Carica | Il display mostra «Caricamento: traccia N di M», nessuna finestrella; pochi secondi |
| 9.8 | Un file in 3/4 o con un cambio di tempo musicale: guarda il **righello** mentre suona | Le misure del righello sono quelle della posizione (misura / movimento); dove cambia il tempo musicale c'è scritto (es. «9  3/4»); con **Aggancia alle misure** A e B cadono sulle linee del righello |
| 9.9 ★ | Riproduzione › **Tastiera**: Analog; Play | Sulla tastiera della finestra principale si accendono, nel colore dell'Analog, i tasti delle note della parte Analog (all'ottava della parte: cambia Octave sul JD-Xi e i tasti si spostano); un triangolo sul primo o sull'ultimo tasto se ci sono note oltre; Stop: si spengono. Torna a **Nessuna** |

---

## 10. Ricette (5 minuti)

| | Fai | Deve succedere |
|---|---|---|
| 10.1 | Ricette › **Importa ricetta…** › `JD-Xi recipe - example.csv`; nel controllo **Importa la ricetta** | La ricetta compare in «Le mie ricette», scelta, con i suoi passi |
| 10.2 | **Apri la guida**; applica due passi | I valori del JD-Xi accanto a quelli della ricetta; ✓ sui passi applicati; lo senti |
| 10.3 | **+ Nuova ricetta › Con un'IA**: descrivi un suono, **Copia la richiesta**, incollala in una chat di IA; copia la risposta e **Incolla la risposta** | Il controllo con le righe della risposta; nessuna da correggere, o quasi |
| 10.4 | Nell'editor: rinomina un passo, sposta una riga, regola un valore sul JD-Xi e **Prendi i valori dal JD-Xi**; **Salva ricetta** | «● non salvata» finché non salvi; il valore nuovo nella riga |

---

## 11. Impostazioni, log, chiusura (5 minuti)

| | Fai | Deve succedere |
|---|---|---|
| 11.1 | Preferenze (Ctrl+, oppure File › Preferenze): livello di log WARNING, OK; riaprile | Resta WARNING; dopo il riavvio il log contiene solo avvisi ed errori |
| 11.2 | Riporta il livello a INFO | — |
| 11.3 | Strumenti › Visualizzatore log, scheda *Avvisi ed errori* | Annota ogni riga presente: è la lista dei problemi visti dal programma |
| 11.4 | Finestra degli editor: **◂** su Impostazioni; poi clic sulla barretta; riduci Ricette, chiudi e riapri il programma | La scheda diventa una barretta colorata (il nome passando il mouse) e il programma passa a un'altra scheda; un clic la riapre; alla riapertura le schede sono come le avevi lasciate |
| 11.5 | Chiudi il programma | Si chiude entro qualche secondo; la porta MIDI torna libera (lo script `--list` la vede) |

---

## 12. Schermo (solo se cambi monitor o scala; 5 minuti)

Ripeti 4.1, 4.5, 4.7, 6.1 e 8.1 su ogni schermo che usi (es. 1080p al 125%, 2496x1664 al 175%,
4K al 150%):

| | Deve succedere |
|---|---|
| 12.1 | Nessuno scorrimento orizzontale in nessuna scheda |
| 12.2 | Testo leggibile, manopole usabili col mouse (sullo schermo basso sono più piccole) |
| 12.3 | Scorrimento verticale al massimo in Digital, Analog e Pattern, e breve |

---

## Resoconto

Copia e compila (una riga per passo eseguito):

```
Versione: 1.0.0         Data:            Schermo: 1920x1080 125%   Firmware JD-Xi:
Script: OK __ / KO __ / saltati __        (allega il file .md)

| Passo | Esito | Note |
|-------|-------|------|
| 2.1   | OK    |      |
| 4.2   | KO    | Cutoff partial 2: nessun cambio udibile, il log dice ... |
```

Un rilascio passa se: lo script non ha KO nei punti 1–3, e tutti i passi ★ sono OK.
