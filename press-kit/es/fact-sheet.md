# Kleidos: hoja de datos

A 17 de noviembre de 2026.

## Qué es

Kleidos es un firmware libre y gratuito que convierte una de las placas ESP32 pequeñas en las que funciona, de M5Stack y LILYGO, en un gestor de contraseñas por hardware. Tus contraseñas se quedan cifradas en la placa, que escribe por Bluetooth en tu ordenador o tu móvil la que elijas, y solo después de que la hayas desbloqueado en la propia placa.

## Datos

| | |
| --- | --- |
| Estado | En desarrollo. Sin publicar: todavía no hay nada que descargar. |
| Placas | Nueve, con el ESP32-S3 y con el ESP32 clásico: M5StickS3, M5Stack Cardputer ADV, LILYGO T-Deck Plus, M5Stack CoreS3 SE; M5StickC Plus2, M5StickC Plus 1.1, M5StickC Plus SE, M5Stack CoreInk, M5Stack Core2 v1.3 |
| Enlace con el ordenador o el móvil | Un teclado Bluetooth LE: envía pulsaciones y no lee nada |
| Cifrado | AES-256-CBC + HMAC-SHA256, con la clave derivada de tu PIN o tu contraseña de desbloqueo mediante PBKDF2-SHA256 |
| Capacidad | De 90 a 500 credenciales y de 30 a 50 códigos 2FA (TOTP), según la placa |
| Servidor, cuenta, aplicación | Ninguno |
| Coste | Nada que pagar al proyecto ni cuenta que abrir; compras la placa a quien la venda |
| Licencia | Licencia Pública General de GNU, versión 3 o cualquier versión posterior (GPL-3.0-or-later). El código es privado hasta que se abra el repositorio, un paso de la hoja de ruta |
| Lo hace | José M. Requena Plens (sin tilde: Jose M. Requena Plens), él solo; <https://github.com/jmrplens> |
| Nombre | Del griego antiguo κλειδός (kleidós), «de la llave», genitivo de κλείς (kleís), «llave». Mientras el proyecto estaba pensado solo para las placas M5Stick, iba a llamarse StickPass; pasó a ser Kleidos al llegar a otras placas |
| Pronunciación | «kléi-dos» (/ˈklei̯.dos/): dos sílabas, con el acento en la primera. Es la pronunciación propia del proyecto; el genitivo griego, kleidós, lleva el acento en la última |
| Historia | Primeros intentos en 2022, con el proyecto aparcado y retomado más de una vez; el desarrollo empezó en abril de 2026; primeras versiones que funcionan en junio y julio de 2026; sigue en desarrollo, porque el firmware tiene que ser sólido antes de ofrecérselo a la comunidad. La historia completa: [`about/es/name-and-history.md`](../../about/es/name-and-history.md) |
| Web | <https://kleidos.dev/es/> |
| Contacto | mail@kleidos.dev |

## Cómo se escribe el nombre

«Kleidos»: la K mayúscula y nada más en mayúsculas. Ni «KLEIDOS», ni «KleidOS», ni «Kleidos OS». La dirección kleidos.dev va en minúsculas. Kleidos no es una marca registrada, así que no lleva ningún signo de marca al lado.

## Qué no escribir

- Que está publicado: todavía no hay nada que descargar ni instalar (a 17 de noviembre de 2026).
- Que es un producto que se compra: es un firmware para una placa que compras a quien la venda. El proyecto no vende nada.
- Que es una llave de seguridad FIDO2 o U2F: es un gestor de contraseñas, y no hace FIDO2, U2F, PIV ni OpenPGP.
- Que M5Stack o LILYGO lo fabrican, lo patrocinan o lo avalan. Kleidos es un proyecto independiente, sin relación con M5Stack ni con LILYGO.
- Que registra o lee lo que tecleas: envía pulsaciones y no lee nada.
- Que está auditado: no lo ha auditado nadie independiente.

De qué protege y de qué no, amenaza por amenaza: <https://kleidos.dev/security/>. En qué punto está el proyecto: <https://kleidos.dev/roadmap/>.

## Imágenes

Las nueve placas a la misma escala, cada una con su pantalla de desbloqueo, bajo el logotipo: [`../images/kleidos-boards-16x9-es-1920.png`](../images/kleidos-boards-16x9-es-1920.png) (16:9) y [`../images/kleidos-boards-4x5-es.png`](../images/kleidos-boards-4x5-es.png) (4:5), también sobre blanco. Una fotografía de cuatro placas con una versión anterior de Kleidos (la M5Stack Cardputer ADV, la M5Stack Core2 v1.3, la M5StickS3 y la LILYGO T-Deck Plus): [`../photos/kleidos-photo-four-boards-1920.jpg`](../photos/kleidos-photo-four-boards-1920.jpg), también a 1200 px y a resolución completa; crédito «Foto: José M. Requena Plens». El logotipo y las demás imágenes: [`../README.md`](../README.md).

## Enlaces

- <https://kleidos.dev/es/>
- <https://github.com/kleidos-dev>
- <https://www.youtube.com/@kleidos>
- <https://makertube.net/c/kleidos>
