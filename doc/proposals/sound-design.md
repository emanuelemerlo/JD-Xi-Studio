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

## 1. Modalità demo (senza JD-Xi)

Principio: senza strumento non si fa sound design «alla cieca»; si può però **provare tutto**
l'interfaccia, sapendo che niente resta.

- Si entra quando all'avvio il JD-Xi non c'è (o da un pulsante «Prova senza JD-Xi»).
- Una **fascia fissa** in alto: «Modalità demo: puoi provare tutto, ma niente viene salvato né
  inviato. Collega il JD-Xi per lavorare davvero.»
- Tutti i controlli si muovono; **spenti** (con tooltip che spiega): Salva patch, export `.syx`,
  salva ricetta, salva A/B, Send all, Read, Autotest, scelta dei programmi.
- Aprire una patch per guardarla: consentito (in sola lettura del risultato).
- Quando il JD-Xi viene collegato si esce dalla demo: gli editor vengono riletti dallo strumento
  e le modifiche demo si scartano, con un avviso (sono per definizione prove).
- Risolve anche il problema trovato: oggi le modifiche fatte offline vengono sovrascritte senza
  avviso al collegamento.

Costo: **medio** (una sessione). Tocca: avvio, stato «collegato» centralizzato, abilitazione dei
comandi, fascia, test.

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

Da decidere con l'utente prima di partire: i testi della fascia demo, se la demo parte da sola
senza JD-Xi o solo su richiesta, e come deve suonare l'*Init* (onda, filtro, inviluppi).
