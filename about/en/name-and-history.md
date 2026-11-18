# Kleidos: the name and how it got here

## Where the name comes from

Kleidos is a Greek word written in Latin letters. In Ancient Greek, κλείς (kleís) is a key, and κλειδός (kleidós) is its genitive: "of the key". The project says its name KLAY-dos (/ˈklei̯.dos/), two syllables with the stress on the first: its own way of saying it, unlike the Greek genitive, which stresses the last. The word did not always mean the key as we know it. Its first sense in the Greek–English lexicon of Liddell, Scott and Jones is the bar or bolt that held a door shut, and only later the key itself; the same word also named the collarbone, probably, the lexicon says, for its hook shape. Greek has kept it: a key in Modern Greek is κλειδί (kleidí), which comes from κλείς through a diminutive, and κλειδί is also the key of a cipher.

The word has relatives in many languages. Latin clavis, a key too, comes from the same Indo-European root as κλείς. From clavis come Spanish llave, French clef and Italian chiave, and from its diminutive clavicula, "small key", the English clavicle.

## Why a Greek word

The project did not start out as Kleidos. At first it was meant only for M5Stack's M5Stick boards, the small sticks with a screen and a few buttons, and the name it was going to carry said just that: StickPass.

Then it grew to other boards, and the name stopped fitting. A pocket computer with a keyboard, a board with a touch screen and one with e-paper are not sticks, and a name tied to one shape of device would have kept telling people the project was for that shape alone. José M. Requena Plens, who makes Kleidos, looked for a name that anybody could say aloud, whatever language they speak, and that would say in some way what the thing is. He settled on a word derived from Greek.

A key fits the job. It keeps a door shut, and it opens it to whoever holds it. Kleidos does the same with your passwords: it keeps them encrypted on the board, and it types one only for the person who has unlocked the board on the board itself. The mark says it too: a keyhole inside a ring.

## From the Sticks to nine boards

The M5Stick boards came first. Today Kleidos runs on nine boards from M5Stack and LILYGO, on two chip families:

- On the ESP32-S3: M5StickS3, M5Stack Cardputer ADV, LILYGO T-Deck Plus, M5Stack CoreS3 SE.
- On the classic ESP32: M5StickC Plus2, M5StickC Plus 1.1, M5StickC Plus SE, M5Stack CoreInk, M5Stack Core2 v1.3.

They differ in almost everything you touch: buttons on a stick, a keyboard, a touch screen, a dial and e-paper. Four of them are still sticks. The name now covers the five that are not.

## Since 2022

José has been trying to build a hardware password manager since 2022, and for years the project went the way side projects often go: started, set aside, picked up again, set aside once more.

In April 2026 development started for good, and this time it kept going. The first working versions came in June and July 2026. The months since have gone into the work that turns a version that works into one you can rely on.

## Why it is not released yet

As of 2026-11-17, Kleidos is still in development and there is nothing to download. That is deliberate: the firmware has to be solid before it is offered to the community. A password manager holds the things you cannot afford to lose or to leak, and one that loses an entry, locks its owner out or gives way to an attacker does more harm than having none. So it waits until it can be trusted with them.

Nobody independent has audited it yet. What remains before a release, and in what order, is on the roadmap: <https://kleidos.dev/roadmap/>. What it protects against, and what it does not, threat by threat: <https://kleidos.dev/security/>.
