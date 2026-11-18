# Kleidos

Kleidos es un firmware libre y gratuito que convierte una de las placas ESP32 pequeñas en las que funciona, de M5Stack y LILYGO, en un gestor de contraseñas por hardware. Tus contraseñas se quedan cifradas en la placa, que escribe por Bluetooth en tu ordenador o tu móvil la que elijas, y solo después de que la hayas desbloqueado en la propia placa.

## Cómo se usa

Desbloqueas la placa en la propia placa, con un PIN o una contraseña de desbloqueo. Eliges una entrada en su pantalla. La placa la escribe en tu ordenador o tu móvil como un teclado Bluetooth LE: envía pulsaciones y no lee nada. Antes de que un ordenador o un móvil nuevo reciba una sola pulsación, confirmas un número de seis cifras en la pantalla de la propia placa.

## De qué prescinde

No hay servidor ni cuenta: no se guarda ninguna copia de tus contraseñas fuera de la placa, salvo una copia de seguridad que exportes tú. No hay aplicación que instalar ni nube en la que confiar. No hay nada que pagar al proyecto: compras la placa a quien la venda.

## Las placas

Una placa, aquí, es un aparato ESP32 de bolsillo que M5Stack o LILYGO venden terminado, con carcasa y pantalla propias. Kleidos funciona en nueve.

- Con el ESP32-S3: M5StickS3, M5Stack Cardputer ADV, LILYGO T-Deck Plus, M5Stack CoreS3 SE.
- Con el ESP32 clásico: M5StickC Plus2, M5StickC Plus 1.1, M5StickC Plus SE, M5Stack CoreInk, M5Stack Core2 v1.3.

Kleidos es un proyecto independiente, sin relación con M5Stack ni con LILYGO. Los nombres de producto son marcas de sus propietarios.

## En qué punto está

En desarrollo. Sin publicar: todavía no hay nada que descargar (a 17 de noviembre de 2026). No lo ha auditado nadie independiente. La hoja de ruta dice en qué punto está el proyecto: <https://kleidos.dev/roadmap/>. De qué protege y de qué no, amenaza por amenaza: <https://kleidos.dev/security/>.

## Quién lo hace

José M. Requena Plens hace Kleidos él solo (<https://github.com/jmrplens>). El nombre viene de la palabra griega que significa «llave»; la historia del nombre y el camino desde los primeros intentos, en 2022, hasta hoy están en [`name-and-history.md`](name-and-history.md).

## Licencia

Licencia Pública General de GNU, versión 3 o cualquier versión posterior (GPL-3.0-or-later). El código es privado hasta que se abra el repositorio, un paso de la hoja de ruta. Kleidos no es una marca registrada; cómo pueden usarse el nombre y el logotipo está en [`TRADEMARKS.md`](../../TRADEMARKS.md).

## Contacto y enlaces

- mail@kleidos.dev (huella OpenPGP `94765B19FB505392C68AED600535C714FCEF3BC3`)
- <https://kleidos.dev/es/>
- <https://github.com/kleidos-dev>
- <https://www.youtube.com/@kleidos>
- <https://makertube.net/c/kleidos>
