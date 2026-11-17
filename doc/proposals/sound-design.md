# Proposte: modalità demo e sound design più semplice

Branch di lavoro: `dev/sound-design` (nessuna build su GitHub ai push; una PR sola alla fine).
Stato: **proposte**, da decidere e poi realizzare dopo il reset dei crediti.

## Cosa dice il JD-Xi (manuale, «Salvataggio di un suono (Programma) (WRITE)»)

- Quello che si modifica sta nell'**area temporanea**: si perde spegnendo lo strumento o scegliendo
  un altro programma.
- Si salva solo un **programma intero** (le 4 parti: Digital 1, Digital 2, Analog, Drums, più
  effetti e arpeggio), con **WRITE** sullo strumento, in uno dei **banchi utente E–H** (64 posti
  ciascuno). I banchi A–D sono di fabbrica e non si sovrascrivono.
- **Un tono da solo non si salva**: per riusarlo in un altro programma si copia con
  Pattern Copy › *Sound Only*.
- Via SysEx l'app può scrivere solo l'area temporanea: il salvataggio vero lo fa il WRITE dello
  strumento (l'app può guidarlo e verificarlo, non sostituirlo).

Da qui la confusione nelle prove: in app non si vede *dove* si sta lavorando né *cosa* succede
al suono originale, e manca il passo finale («ora premi WRITE e scegli E-12»).

## 1. Modalità «Off-line» (senza JD-Xi) — decisa

Principio: senza strumento non si fa sound design «alla cieca»; si può però **provare tutta
l'interfaccia**, sapendo che niente resta. Serve anche per provare l'app senza il synth.

Decisioni (17/11):
- **Parte da sola** quando il JD-Xi non c'è.
- Si chiama **Off-line**: all'ingresso una **finestra di avviso** («Il JD-Xi non è collegato:
  puoi provare tutto, ma niente viene salvato né inviato»), poi un **badge/indicatore «Off-line»**
  sia nella finestra principale sia nelle finestre secondarie (editor staccati, impostazioni…).
- Tutti i controlli si muovono; **spenti** (con tooltip che spiega): Salva patch, export `.syx`,
  salva ricetta, salva A/B, Send all, Read, Autotest, scelta dei programmi.
- **JD-Xi collegato dopo**: si esce da Off-line, l'app **legge le impostazioni dallo strumento e
  ignora le modifiche fatte alla cieca** (avviso breve, nessuna domanda).
- **JD-Xi scollegato o spento durante il lavoro**: si torna in Off-line (badge, comandi spenti);
  quando torna, si rilegge come sopra. Le modifiche fatte mentre era collegato sono già sullo
  strumento (temporanee lì finché non c'è WRITE); quelle fatte durante lo stacco sono alla cieca
  e vengono ignorate. Da verificare sullo strumento: spento e riacceso, il JD-Xi riparte dal
  programma salvato e le modifiche temporanee sono perse — l'app lo deve dire («Il JD-Xi è stato
  riavviato: le modifiche non salvate con WRITE sono perse»), riconoscendolo dal fatto che il
  collegamento è caduto e tornato.
- Risolve anche il problema trovato: oggi le modifiche fatte offline vengono sovrascritte senza
  avviso al collegamento.

Costo: **medio** (una sessione). Tocca: avvio, stato «collegato» centralizzato (oggi ogni parte lo
controlla a modo suo: follower, A/B, Send all), abilitazione dei comandi, avviso, badge, test.

### 1b. JD-Xi spento e riacceso: rete di sicurezza (proposta, da fare con l'Off-line)

L'app tiene già una copia della memoria temporanea del JD-Xi (`SynthMemory`: quello che ha letto e
quello che ha inviato). Usarla come rete di sicurezza invece di limitarsi ad avvisare:

1. Il collegamento cade → Off-line; la copia dell'**ultimo stato confermato** resta (le modifiche
   alla cieca fatte dopo non entrano nella copia).
2. Il JD-Xi torna → l'app lo rilegge e **confronta** con la copia:
   - uguale → era solo il cavo: nessun messaggio;
   - diverso → (quasi sempre spento e riacceso, o modificato sullo strumento intanto) l'app dice
     **cosa** è diverso («Analog e Digital 1 sono diversi da prima») e propone
     **Ripristina sul JD-Xi** (rimanda solo le parti cambiate, rilegge e conferma, come il
     richiamo A/B) oppure **Tieni quello che c'è sul JD-Xi**.
3. Dopo il ripristino ricorda che è di nuovo solo temporaneo: per tenerlo serve WRITE (punto 4).

Estensione possibile: la copia salvata anche su disco ogni tanto, per ritrovare lo stato di lavoro
dopo una chiusura improvvisa dell'app.

Costo: **medio**, da fare insieme all'Off-line (stessi punti del codice). Riusa la copia della
memoria e il meccanismo «invia e rileggi» del confronto A/B.

## 2. Partire da un suono: tre porte d'ingresso chiare

Un pannello **«Nuovo suono»** (dalla scheda Programmi o da un pulsante in ogni editor di tono)
con tre scelte, ognuna spiegata in una riga:

| Scelta | Cosa fa | Per chi |
|---|---|---|
| **Da zero** | Mette nella parte un tono *Init* (forma d'onda semplice, filtro aperto, niente modulazioni) | Chi vuole capire e costruire passo passo |
| **Da un preset** | Sceglie un tono di fabbrica (per categoria: Bass, Lead, Pad…) come punto di partenza | Il caso più comune |
| **Da una ricetta** | Usa una ricetta della libreria (già c'è) | Chi cerca un tipo di suono preciso |

In tutti e tre i casi l'app dice chiaramente: «Stai modificando una **copia temporanea**: il
preset di fabbrica non cambia. Per tenerlo dovrai salvarlo (vedi sotto).»

Costo: **medio-basso** (Init per Digital e Analog va definito; le altre due porte esistono già,
vanno solo riunite).

## 3. Sapere sempre dove si è e cosa succede

Una **riga di contesto** fissa in testa agli editor, per esempio:

> Programma **E-12 «My Bass»** › parte **Analog** › tono «Toxic Bass 1» (dal preset A-05) · **● modificato, non salvato**

- Dice da dove viene il suono e se è stato modificato rispetto all'originale.
- Se si sceglie un altro programma con modifiche non salvate: «Le modifiche andranno perse sul
  JD-Xi: Salva prima / Scarta / Annulla» (in parte già c'è: va resa visibile e uniforme).

Costo: **basso-medio**.

## 4. Salvare: una procedura guidata «Salva sul JD-Xi»

Siccome il salvataggio vero lo fa il WRITE dello strumento, l'app lo guida:

1. Chiede il nome del programma (12 caratteri) e lo scrive già nel JD-Xi (via SysEx).
2. Mostra i **posti liberi/occupati** dei banchi E–H (i nomi li legge già «Update user programs»)
   e suggerisce il primo libero; avvisa se il posto scelto sovrascrive un programma esistente.
3. Dice esattamente cosa premere: «Sul JD-Xi: tieni premuto Shift e premi Menu/Write, scegli
   **E-13** con Program [-] [+], premi Enter due volte.»
4. Dopo, rilegge il programma E-13 e conferma: «Salvato in E-13 ✓» (o avvisa se non lo trova).
5. In parallelo offre la **copia su file** (`.msz`) come backup sul computer.

Per un tono da solo: spiegare che si salva dentro un programma, e proporre il `.syx` della parte
(già c'è) per riusarlo altrove.

Costo: **medio** (lettura dei banchi utente e verifica dopo il WRITE vanno provati sullo strumento).

## 5. Piccole cose che aiutano chi impara

- Nei pannelli degli editor un **«?»** per sezione con due righe di spiegazione (cosa fa
  l'oscillatore, il filtro…) e il rimando alla pagina del Parameter Guide (il riferimento c'è già).
- Il confronto **A/B** (già fatto) come strumento didattico: «prima / dopo» ogni modifica.

## Ordine suggerito

1. Modalità demo (chiude anche il buco delle modifiche offline perse).
2. Riga di contesto + avviso uniforme sulle modifiche non salvate.
3. «Salva sul JD-Xi» guidato.
4. Pannello «Nuovo suono» con Init.
5. Aiuti per sezione.

Deciso: Off-line parte da sola (vedi punto 1). *Init*: nessuna preferenza dell'utente; proposta:
onda a dente di sega, filtro aperto, inviluppo d'ampiezza semplice (attacco 0, sustain pieno,
rilascio breve), niente LFO né effetti — il suono più neutro da cui costruire.
