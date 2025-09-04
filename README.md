# TP0: Docker + Comunicaciones + Concurrencia

En el presente repositorio se provee un esqueleto básico de cliente/servidor, en donde todas las dependencias del mismo se encuentran encapsuladas en containers. Los alumnos deberán resolver una guía de ejercicios incrementales, teniendo en cuenta las condiciones de entrega descritas al final de este enunciado.

El cliente (Golang) y el servidor (Python) fueron desarrollados en diferentes lenguajes simplemente para mostrar cómo dos lenguajes de programación pueden convivir en el mismo proyecto con la ayuda de containers, en este caso utilizando [Docker Compose](https://docs.docker.com/compose/).

#### Índice

1. [Instrucciones de uso](#Instrucciones-de-uso)
   1. [Servidor](#Servidor)
   1. [Cliente](#Cliente)
   1. [Ejemplo](#Ejemplo)
1. [Parte 1: Introducción a Docker](#Parte-1-Introducción-a-Docker)
   1. [Ejercicio N°1](#Ejercicio-N1)
   1. [Ejercicio N°2](#Ejercicio-N2)
   1. [Ejercicio N°3](#Ejercicio-N3)
   1. [Ejercicio N°4](#Ejercicio-N4)
1. [Parte 2: Repaso de Comunicaciones](#Parte-2-Repaso-de-Comunicaciones)
   1. [Ejercicio N°5](#Ejercicio-N5)
   1. [Ejercicio N°6](#Ejercicio-N6)
   1. [Ejercicio N°7](#Ejercicio-N7)
1. [Parte 3: Repaso de Concurrencia](#Parte-3-Repaso-de-Concurrencia)
   1. [Ejercicio N°8](#Ejercicio-N8)
1. [Condiciones de Entrega](#Condiciones-de-Entrega)
1. [Entrega](#Entrega)
   1. [Sobre el Ejercicio N°1](#Sobre-el-Ejercicio-N1)
   1. [Sobre el Ejercicio N°2](#Sobre-el-Ejercicio-N2)
   1. [Sobre el Ejercicio N°3](#Sobre-el-Ejercicio-N3)
   1. [Sobre el Ejercicio N°4](#Sobre-el-Ejercicio-N4)
   1. [Sobre el Ejercicio N°5](#Sobre-el-Ejercicio-N5)
   1. [Sobre el Ejercicio N°6](#Sobre-el-Ejercicio-N6)
   1. [Sobre el Ejercicio N°7](#Sobre-el-Ejercicio-N7)
   1. [Sobre el Ejercicio N°8](#Sobre-el-Ejercicio-N8)

## Instrucciones de uso

El repositorio cuenta con un **Makefile** que incluye distintos comandos en forma de targets. Los targets se ejecutan mediante la invocación de: **make \<target\>**. Los target imprescindibles para iniciar y detener el sistema son **docker-compose-up** y **docker-compose-down**, siendo los restantes targets de utilidad para el proceso de depuración.

Los targets disponibles son:

| target                | accion                                                                                                                                                                                                                                                                                                                                                                |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docker-compose-up`   | Inicializa el ambiente de desarrollo. Construye las imágenes del cliente y el servidor, inicializa los recursos a utilizar (volúmenes, redes, etc) e inicia los propios containers.                                                                                                                                                                                   |
| `docker-compose-down` | Ejecuta `docker-compose stop` para detener los containers asociados al compose y luego `docker-compose down` para destruir todos los recursos asociados al proyecto que fueron inicializados. Se recomienda ejecutar este comando al finalizar cada ejecución para evitar que el disco de la máquina host se llene de versiones de desarrollo y recursos sin liberar. |
| `docker-compose-logs` | Permite ver los logs actuales del proyecto. Acompañar con `grep` para lograr ver mensajes de una aplicación específica dentro del compose.                                                                                                                                                                                                                            |
| `docker-image`        | Construye las imágenes a ser utilizadas tanto en el servidor como en el cliente. Este target es utilizado por **docker-compose-up**, por lo cual se lo puede utilizar para probar nuevos cambios en las imágenes antes de arrancar el proyecto.                                                                                                                       |
| `build`               | Compila la aplicación cliente para ejecución en el _host_ en lugar de en Docker. De este modo la compilación es mucho más veloz, pero requiere contar con todo el entorno de Golang y Python instalados en la máquina _host_.                                                                                                                                         |

### Servidor

Se trata de un "echo server", en donde los mensajes recibidos por el cliente se responden inmediatamente y sin alterar.

Se ejecutan en bucle las siguientes etapas:

1. Servidor acepta una nueva conexión.
2. Servidor recibe mensaje del cliente y procede a responder el mismo.
3. Servidor desconecta al cliente.
4. Servidor retorna al paso 1.

### Cliente

se conecta reiteradas veces al servidor y envía mensajes de la siguiente forma:

1. Cliente se conecta al servidor.
2. Cliente genera mensaje incremental.
3. Cliente envía mensaje al servidor y espera mensaje de respuesta.
4. Servidor responde al mensaje.
5. Servidor desconecta al cliente.
6. Cliente verifica si aún debe enviar un mensaje y si es así, vuelve al paso 2.

### Ejemplo

Al ejecutar el comando `make docker-compose-up` y luego `make docker-compose-logs`, se observan los siguientes logs:

```
client1  | 2024-08-21 22:11:15 INFO     action: config | result: success | client_id: 1 | server_address: server:12345 | loop_amount: 5 | loop_period: 5s | log_level: DEBUG
client1  | 2024-08-21 22:11:15 INFO     action: receive_message | result: success | client_id: 1 | msg: [CLIENT 1] Message N°1
server   | 2024-08-21 22:11:14 DEBUG    action: config | result: success | port: 12345 | listen_backlog: 5 | logging_level: DEBUG
server   | 2024-08-21 22:11:14 INFO     action: accept_connections | result: in_progress
server   | 2024-08-21 22:11:15 INFO     action: accept_connections | result: success | ip: 172.25.125.3
server   | 2024-08-21 22:11:15 INFO     action: receive_message | result: success | ip: 172.25.125.3 | msg: [CLIENT 1] Message N°1
server   | 2024-08-21 22:11:15 INFO     action: accept_connections | result: in_progress
server   | 2024-08-21 22:11:20 INFO     action: accept_connections | result: success | ip: 172.25.125.3
server   | 2024-08-21 22:11:20 INFO     action: receive_message | result: success | ip: 172.25.125.3 | msg: [CLIENT 1] Message N°2
server   | 2024-08-21 22:11:20 INFO     action: accept_connections | result: in_progress
client1  | 2024-08-21 22:11:20 INFO     action: receive_message | result: success | client_id: 1 | msg: [CLIENT 1] Message N°2
server   | 2024-08-21 22:11:25 INFO     action: accept_connections | result: success | ip: 172.25.125.3
server   | 2024-08-21 22:11:25 INFO     action: receive_message | result: success | ip: 172.25.125.3 | msg: [CLIENT 1] Message N°3
client1  | 2024-08-21 22:11:25 INFO     action: receive_message | result: success | client_id: 1 | msg: [CLIENT 1] Message N°3
server   | 2024-08-21 22:11:25 INFO     action: accept_connections | result: in_progress
server   | 2024-08-21 22:11:30 INFO     action: accept_connections | result: success | ip: 172.25.125.3
server   | 2024-08-21 22:11:30 INFO     action: receive_message | result: success | ip: 172.25.125.3 | msg: [CLIENT 1] Message N°4
server   | 2024-08-21 22:11:30 INFO     action: accept_connections | result: in_progress
client1  | 2024-08-21 22:11:30 INFO     action: receive_message | result: success | client_id: 1 | msg: [CLIENT 1] Message N°4
server   | 2024-08-21 22:11:35 INFO     action: accept_connections | result: success | ip: 172.25.125.3
server   | 2024-08-21 22:11:35 INFO     action: receive_message | result: success | ip: 172.25.125.3 | msg: [CLIENT 1] Message N°5
client1  | 2024-08-21 22:11:35 INFO     action: receive_message | result: success | client_id: 1 | msg: [CLIENT 1] Message N°5
server   | 2024-08-21 22:11:35 INFO     action: accept_connections | result: in_progress
client1  | 2024-08-21 22:11:40 INFO     action: loop_finished | result: success | client_id: 1
client1 exited with code 0
```

## Parte 1: Introducción a Docker

En esta primera parte del trabajo práctico se plantean una serie de ejercicios que sirven para introducir las herramientas básicas de Docker que se utilizarán a lo largo de la materia. El entendimiento de las mismas será crucial para el desarrollo de los próximos TPs.

### Ejercicio N°1:

Definir un script de bash `generar-compose.sh` que permita crear una definición de Docker Compose con una cantidad configurable de clientes. El nombre de los containers deberá seguir el formato propuesto: client1, client2, client3, etc.

El script deberá ubicarse en la raíz del proyecto y recibirá por parámetro el nombre del archivo de salida y la cantidad de clientes esperados:

`./generar-compose.sh docker-compose-dev.yaml 5`

Considerar que en el contenido del script pueden invocar un subscript de Go o Python:

```
#!/bin/bash
echo "Nombre del archivo de salida: $1"
echo "Cantidad de clientes: $2"
python3 mi-generador.py $1 $2
```

En el archivo de Docker Compose de salida se pueden definir volúmenes, variables de entorno y redes con libertad, pero recordar actualizar este script cuando se modifiquen tales definiciones en los sucesivos ejercicios.

### Ejercicio N°2:

Modificar el cliente y el servidor para lograr que realizar cambios en el archivo de configuración no requiera reconstruír las imágenes de Docker para que los mismos sean efectivos. La configuración a través del archivo correspondiente (`config.ini` y `config.yaml`, dependiendo de la aplicación) debe ser inyectada en el container y persistida por fuera de la imagen (hint: `docker volumes`).

### Ejercicio N°3:

Crear un script de bash `validar-echo-server.sh` que permita verificar el correcto funcionamiento del servidor utilizando el comando `netcat` para interactuar con el mismo. Dado que el servidor es un echo server, se debe enviar un mensaje al servidor y esperar recibir el mismo mensaje enviado.

En caso de que la validación sea exitosa imprimir: `action: test_echo_server | result: success`, de lo contrario imprimir:`action: test_echo_server | result: fail`.

El script deberá ubicarse en la raíz del proyecto. Netcat no debe ser instalado en la máquina _host_ y no se pueden exponer puertos del servidor para realizar la comunicación (hint: `docker network`). `

### Ejercicio N°4:

Modificar servidor y cliente para que ambos sistemas terminen de forma _graceful_ al recibir la signal SIGTERM. Terminar la aplicación de forma _graceful_ implica que todos los _file descriptors_ (entre los que se encuentran archivos, sockets, threads y procesos) deben cerrarse correctamente antes que el thread de la aplicación principal muera. Loguear mensajes en el cierre de cada recurso (hint: Verificar que hace el flag `-t` utilizado en el comando `docker compose down`).

## Parte 2: Repaso de Comunicaciones

Las secciones de repaso del trabajo práctico plantean un caso de uso denominado **Lotería Nacional**. Para la resolución de las mismas deberá utilizarse como base el código fuente provisto en la primera parte, con las modificaciones agregadas en el ejercicio 4.

### Ejercicio N°5:

Modificar la lógica de negocio tanto de los clientes como del servidor para nuestro nuevo caso de uso.

#### Cliente

Emulará a una _agencia de quiniela_ que participa del proyecto. Existen 5 agencias. Deberán recibir como variables de entorno los campos que representan la apuesta de una persona: nombre, apellido, DNI, nacimiento, numero apostado (en adelante 'número'). Ej.: `NOMBRE=Santiago Lionel`, `APELLIDO=Lorca`, `DOCUMENTO=30904465`, `NACIMIENTO=1999-03-17` y `NUMERO=7574` respectivamente.

Los campos deben enviarse al servidor para dejar registro de la apuesta. Al recibir la confirmación del servidor se debe imprimir por log: `action: apuesta_enviada | result: success | dni: ${DNI} | numero: ${NUMERO}`.

#### Servidor

Emulará a la _central de Lotería Nacional_. Deberá recibir los campos de la cada apuesta desde los clientes y almacenar la información mediante la función `store_bet(...)` para control futuro de ganadores. La función `store_bet(...)` es provista por la cátedra y no podrá ser modificada por el alumno.
Al persistir se debe imprimir por log: `action: apuesta_almacenada | result: success | dni: ${DNI} | numero: ${NUMERO}`.

#### Comunicación:

Se deberá implementar un módulo de comunicación entre el cliente y el servidor donde se maneje el envío y la recepción de los paquetes, el cual se espera que contemple:

- Definición de un protocolo para el envío de los mensajes.
- Serialización de los datos.
- Correcta separación de responsabilidades entre modelo de dominio y capa de comunicación.
- Correcto empleo de sockets, incluyendo manejo de errores y evitando los fenómenos conocidos como [_short read y short write_](https://cs61.seas.harvard.edu/site/2018/FileDescriptors/).

### Ejercicio N°6:

Modificar los clientes para que envíen varias apuestas a la vez (modalidad conocida como procesamiento por _chunks_ o _batchs_).
Los _batchs_ permiten que el cliente registre varias apuestas en una misma consulta, acortando tiempos de transmisión y procesamiento.

La información de cada agencia será simulada por la ingesta de su archivo numerado correspondiente, provisto por la cátedra dentro de `.data/datasets.zip`.
Los archivos deberán ser inyectados en los containers correspondientes y persistido por fuera de la imagen (hint: `docker volumes`), manteniendo la convencion de que el cliente N utilizara el archivo de apuestas `.data/agency-{N}.csv` .

En el servidor, si todas las apuestas del _batch_ fueron procesadas correctamente, imprimir por log: `action: apuesta_recibida | result: success | cantidad: ${CANTIDAD_DE_APUESTAS}`. En caso de detectar un error con alguna de las apuestas, debe responder con un código de error a elección e imprimir: `action: apuesta_recibida | result: fail | cantidad: ${CANTIDAD_DE_APUESTAS}`.

La cantidad máxima de apuestas dentro de cada _batch_ debe ser configurable desde config.yaml. Respetar la clave `batch: maxAmount`, pero modificar el valor por defecto de modo tal que los paquetes no excedan los 8kB.

Por su parte, el servidor deberá responder con éxito solamente si todas las apuestas del _batch_ fueron procesadas correctamente.

### Ejercicio N°7:

Modificar los clientes para que notifiquen al servidor al finalizar con el envío de todas las apuestas y así proceder con el sorteo.
Inmediatamente después de la notificacion, los clientes consultarán la lista de ganadores del sorteo correspondientes a su agencia.
Una vez el cliente obtenga los resultados, deberá imprimir por log: `action: consulta_ganadores | result: success | cant_ganadores: ${CANT}`.

El servidor deberá esperar la notificación de las 5 agencias para considerar que se realizó el sorteo e imprimir por log: `action: sorteo | result: success`.
Luego de este evento, podrá verificar cada apuesta con las funciones `load_bets(...)` y `has_won(...)` y retornar los DNI de los ganadores de la agencia en cuestión. Antes del sorteo no se podrán responder consultas por la lista de ganadores con información parcial.

Las funciones `load_bets(...)` y `has_won(...)` son provistas por la cátedra y no podrán ser modificadas por el alumno.

No es correcto realizar un broadcast de todos los ganadores hacia todas las agencias, se espera que se informen los DNIs ganadores que correspondan a cada una de ellas.

## Parte 3: Repaso de Concurrencia

En este ejercicio es importante considerar los mecanismos de sincronización a utilizar para el correcto funcionamiento de la persistencia.

### Ejercicio N°8:

Modificar el servidor para que permita aceptar conexiones y procesar mensajes en paralelo. En caso de que el alumno implemente el servidor en Python utilizando _multithreading_, deberán tenerse en cuenta las [limitaciones propias del lenguaje](https://wiki.python.org/moin/GlobalInterpreterLock).

## Condiciones de Entrega

Se espera que los alumnos realicen un _fork_ del presente repositorio para el desarrollo de los ejercicios y que aprovechen el esqueleto provisto tanto (o tan poco) como consideren necesario.

Cada ejercicio deberá resolverse en una rama independiente con nombres siguiendo el formato `ej${Nro de ejercicio}`. Se permite agregar commits en cualquier órden, así como crear una rama a partir de otra, pero al momento de la entrega deberán existir 8 ramas llamadas: ej1, ej2, ..., ej7, ej8.
(hint: verificar listado de ramas y últimos commits con `git ls-remote`)

Se espera que se redacte una sección del README en donde se indique cómo ejecutar cada ejercicio y se detallen los aspectos más importantes de la solución provista, como ser el protocolo de comunicación implementado (Parte 2) y los mecanismos de sincronización utilizados (Parte 3).

Se proveen [pruebas automáticas](https://github.com/7574-sistemas-distribuidos/tp0-tests) de caja negra. Se exige que la resolución de los ejercicios pase tales pruebas, o en su defecto que las discrepancias sean justificadas y discutidas con los docentes antes del día de la entrega. El incumplimiento de las pruebas es condición de desaprobación, pero su cumplimiento no es suficiente para la aprobación. Respetar las entradas de log planteadas en los ejercicios, pues son las que se chequean en cada uno de los tests.

La corrección personal tendrá en cuenta la calidad del código entregado y casos de error posibles, se manifiesten o no durante la ejecución del trabajo práctico. Se pide a los alumnos leer atentamente y **tener en cuenta** los criterios de corrección informados [en el campus](https://campusgrado.fi.uba.ar/mod/page/view.php?id=73393).

## Entrega

| Alumno               | Padrón | Email           |
| -------------------- | ------ | --------------- |
| Diem, Walter Gabriel | 105618 | wdiem@fi.uba.ar |

### Sobre el Ejercicio N°1

Se hizo un bash script para generar el archivo de configuración de Docker Compose en formato YAML, de esta manera para hacer la generación no hace falta tener dependencias instaladas, solamente `bash`.

La forma de uso es la siguiente:

```bash
./generar-compose.sh <OUTPUT_FILENAME> <NUMBER_OF_CLIENTS>
```

Por ejemplo:

```bash
./generar-compose.sh docker-compose-dev.yaml 5
```

Por defecto el target del Makefile `docker-compose-up` busca el archivo de Docker Compose con nombre `docker-compose-dev.yaml` por lo que si se le cambiara el nombre a este, requeriría ajustar también el Makefile. Así se puede seguir ejecutando para levantar los containers:

```bash
make docker-compose-up
```

Se agregó un flush de logs en el cliente antes de finalizar el proceso, con el objetivo de asegurar que todo el contenido pendiente en los buffers de `stdout` y `stderr` sea enviado, de modo que el logger de Docker pueda recibirlo correctamente.

Ya que se encontró el `TODO` y se considera esencial para el funcionamiento de aplicaciones conectadas mediante red que no exista short-read ni short-write, además de para asegurar la correcta ejecución ejecución de las pruebas ahora y en los ejercicios siguientes. Para ello, en el caso de recepción de mensaje de itera sobre el socket hasta recibir el delimitador `\n` y para el caso de envío se utilizó la función de `socket` de Python `sendAll` y para el caso de Go se iteró hasta escribir todos los bytes en la conexión `conn`.

### Sobre el Ejercicio N°2

Para lograr que no sea necesario reconstruir las imágenes de Docker se utilizaron dos artefactos: volúmenes (`docker volumes`) y `.dockerignore`.

Se crearon los archivos `.dockerignore` para evitar incluir determinados archivos o carpetas en el build context de Docker, uno para el cliente que ignore el archivo `config.yaml` y uno para el server que ignore el archivo `config.ini`. Adicionalmente, se decidió excluir el mismo `.dockerignore` y `Dockerfile`, además del directorio `__pycache__`, ya que no son necesarios en el build context.

Se editó el script generador del YAML de Docker Compose, donde se agregó la montura de los archivos de configuración como volumen que comprende a sólo dichos archivos. Para el caso de los clientes, cabe aclarar que todos los clientes comparten el mismo archivo de configuración.

### Sobre el Ejercicio N°3

Para la implementación del validador del echo server se utilizó la imagen de Docker `busybox`, primeramente porque ya tiene incorporado la utilidad de netcat y además ya se encuentra descargada al correr el proyecto por lo que no es necesario hacer pull de una nueva imagen.

Se corre un container basado en la imagen `busybox` con el agregado de la red `tp0_testing_net` que se crea al levantar los containers con Docker Compose. De esta manera, el container puede mandar el mensaje mediante netcat hacia el echo server y recibir la respuesta, que posteriormente se verifica en el bash script e imprime el log correspondiente.

Para ejecutarlo basta con correr el script como ejecutable sin argumentos:

```bash
./validar-echo-server.sh
```

### Sobre el Ejercicio N°4

Inicialmente se hizo un approach overengineered para esta instancia y los problemas a resolver aquí.

- En el **server**: se dejó el signal handling con la clase SignalHandler en el main thread, ya que allí es donde llegan las signals en Python y al server se lo colocó en un proceso distinto, tomando un approach multiprocessing para evitar interrupciones del sistema operativo y que pueda operar con fluidez. Para loggear de manera segura se hizo un logger multiprocess-safe con una Queue de mensajes que era consumida por un listener e imprimía los logs correspondientes.

- En el **cliente**: se agregó el manejo de señales necesario utilizando channels, `for-select` y un contexto que en la siguiente iteración de la implementación resultó innecesario. También se apalancó el uso de la keyword `defer` para asegurar el cierre apropiado del socket.

Tanto en el cliente como en el server las señales manejadas eran `SIGTERM` (pedido por la consigna y enviado por `docker stop` luego del timeout) y `SIGINT` (para tener en cuenta el caso del <kbd>CTRL+C</kbd>).

El enfoque previamente mencionado se descartó parcialmente en una segunda iteración de la solución, con la solución final de la siguiente manera:

- En el **server** el approach anterior generó un delay de arranque que genera constantemente que los primeros clientes no puedan conectarse y lancen un log de error. Se volvió a un modelo single-threaded, donde el logger, el server y los signal handlers están en el main thread. El `SignalHandler` para al server una vez ejecutado.

- En el **cliente**: se pudo simplificar manteniendo la funcionalidad, dejando de lado el uso de `context` y solamente usando channels y signals. Agregando encapsulamiento en `Client` haciendo que este contenga a dicho channel. Se utilizó un `select` antes de comenzar cada iteración para verificar por signals y al momento de ejecutar el sleep se utilizó `time.After` en un `select` con la signal, de esta manera no hace falta finalizar el `sleep` para comenzar el shutdown.

### Sobre el Ejercicio N°5

Se agregó en el generador de YAML de Docker Compose las variables de entorno con los valores dados de ejemplo en la consigna para los clientes. La firma del script no cambió, por lo que se puede ejecutar de la misma manera.

En el cliente se implementó una interfaz de proveedor de apuestas BetProvider para no quedar atado a las variables de entorno teniendo en cuenta que esto cambiará en el futuro. Además, se eliminó la funcionalidad anterior de sleep y mandado de mensajes en loop con diferentes IDs de mensaje.

En el proceso de separación de capas se generaron nuevos módulos para cada capa y que las incumbencias queden separadas. Para la serialización de mensajes se utilizó interfaces donde cada tipo de mensaje sabe cómo serializarse (función `ToBytes()`). Esta separación hizo que se tenga que ajustar un poco el manejo de signals, utilizando `select` y `context` para desbloquear apropiadamente

En el servidor se imitó el approach ejecutado en el cliente, con la separación de capas y que cada mensaje sepa serializarse. Se usó la función proveída en el módulo `utils` para guardar las apuestas. Además, se eliminó la funcionalidad anterior de ser un echo server.

#### Protocolo

- **Cliente**: Agencia de quiniela
- **Servidor**: Central de Lotería Nacional
- **Tipo de comunicación**: Socket TCP para comunicaciones confiables
- **Encoding de datos**: binario, tipo TLV (Type-Length-Value) para soportar datos variables de manera extensible
- **Serialización**: uso de BigEndian ya que es el endianness de la red

| Mensaje               | Emisor   | Receptor | Payload                                                                                                                | Propósito                                                                                                                              |
| --------------------- | -------- | -------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **RegisterBet**       | Cliente  | Servidor | `AGENCIA: int`,<br> `NOMBRE: str`,<br> `APELLIDO: str`,<br> `DOCUMENTO: int`,<br> `NACIMIENTO: int`,<br> `NUMERO: int` | Registrar una apuesta que vincula a un número<br> con una persona en particular                                                        |
| **RegisterBetOk**     | Servidor | Cliente  | `DOCUMENTO: int`, <br> `NUMERO: int`                                                                                   | Informar que operación **RegisterBet** fue exitosa.<br> El payload sirve para identificar la apuesta                                   |
| **RegisterBetFailed** | Servidor | Cliente  | `DOCUMENTO: int`, <br> `NUMERO: int`, <br> `ERROR: int`                                                                | Informar que operación **RegisterBet** fue errónea.<br> El payload sirve para identificar la apuesta.<br> Se provee un código de error |

#### Formato de paquetes:

El campo `msg_type` se encuentra como los primeros 2 bytes de todo paquete para distinguir el tipo de paquete y luego hacer el decoding correcto.

**_RegisterBet_**

Una `Bet` puede ser de longitud variable ya que los strings pueden ser de longitud variable, por lo tanto todo el payload puede ser de longitud variable.

```
| msg_type (2 bytes) | bet_len (8 bytes) | bet (bet_len bytes) |
```

La `Bet` tiene la siguiente forma:

```
| agency      (4 bytes) |
| name_len    (4 bytes) | name    (name_len bytes)    |
| surname_len (4 bytes) | surname (surname_len bytes) |
| dni         (4 bytes) |
| birthdate   (8 bytes) |
| number      (4 bytes) |
```

> Nota: `birthdate` es un Unix Timestamp.

**_RegisterBetOk_**

```
| msg_type (2 bytes) | dni (4 bytes) | number (4 bytes) |
```

**_RegisterBetFailed_**

```
| msg_type (2 bytes) | dni (4 bytes) | number (4 bytes) | error_code (2 bytes) |
```

El `error_code` permite dar un motivo al cliente de por qué se rechazó.

#### Abstracción en capas

Tanto para el cliente como para el servidor se separó la lógica de negocio del protocolo y la serialización, resultando en las siguientes capas, donde una capa se comunica con la de abajo:

```
--------------------------
|    LÓGICA DE NEGOCIO   |
--------------------------
|        PROTOCOLO       |
--------------------------
| SOCKET / SERIALIZACIÓN |
--------------------------
```

### Sobre el Ejercicio N°6

Se eliminó del generador de YAML de Docker Compose las variables de entorno con los valores dados de ejemplo en la consigna para los clientes. La firma del script no cambió, por lo que se puede ejecutar de la misma manera. Se agregó el uso de volumen para el archivo CSV, para no persistir el archivo en el container, el cual debe estar ubicado en la carpeta `.data` del root del proyecto, los archivos descomprimidos con el nombre acordado por la consigna.

Apalancando el uso de la interfaz de `BetProvider` hecha antes de creó un `CsvBetProvider` para leer línea a línea el archivo, generar las apuestas y los batches y así no cargarlo todo en memoria. Se itera por los registros del CSV hasta llenar el paquete ya sea por la cantidad máxima de elementos en un batch o por ajustarse a los 8KB de tamaño (incluyendo overhead del protocolo TLV).

Hubo que ajustar el protocolo para enviar varias apuestas en un mismo mensaje. Se eliminó código innecesario que se había agregado por motivo de completitud en el ejercicio anterior (decoding en el cliente de mensajes que sólo los decodea el servidor) y datos innecesarios de los mensajes de confirmación.

#### Protocolo

Se agregó un mensaje más al protocolo para confirmar la recepción del servidor de cada batch y así asegurar la correcta recepción antes de cerrar los sockets.

| Mensaje               | Emisor   | Receptor | Payload                                                                                                                              | Propósito                                                                             |
| --------------------- | -------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| **RegisterBets**      | Cliente  | Servidor | Array de:<br> `AGENCIA: int`,<br> `NOMBRE: str`,<br> `APELLIDO: str`,<br> `DOCUMENTO: int`,<br> `NACIMIENTO: int`,<br> `NUMERO: int` | Registrar un batch de apuestas                                                        |
| **RegisterBetOk**     | Servidor | Cliente  |                                                                                                                                      | Informar que operación **RegisterBets** fue exitosa.                                  |
| **RegisterBetFailed** | Servidor | Cliente  | `ERROR: int`                                                                                                                         | Informar que operación **RegisterBets** fue errónea.<br> Se provee un código de error |
| **Ack**               | Cliente  | Servidor |                                                                                                                                      | Informar recepción de mensaje                                                         |

### Sobre el Ejercicio N°7

Se agregó una variable de entorno llamada `NUM_AGENCIES`, utilizada por el servidor para saber la cantidad máxima de agencias que están involucradas en el sorteo, de esa manera puede saber cuando se llega a ese número de agencias que enviaron todas sus apuestas y así iniciar el sorteo entre ellas. La variable fue agregada al generador de YAML de Docker Compose, teniendo el valor de la cantidad de clientes que se especifica en el argumento de entrada. La firma del bash script no cambió así que se usa de la misma manera.

Se extendió el protocolo para soportar la notificación de finalización de envío de apuestas (`AllBetsSent`), separado del pedido de ganadores del sorteo (`InformWinners`) y el envío del servidor a las correspondientes agencias de sus ganadores (`InformWinners`).

En el cliente se agregó el manejo de los mensajes mencionados, además de sumar un último ACK al final de la transmisión para informar que se recibió correctamente los DNIs de los ganadores.

En el servidor, manteniendo la propiedad de single-thread pero avanzando el trabajo haciendo multitasking contra múltiples clientes, dado como entendido que el paralelismo se reserva para el ejercicio 8, y habiendo utilizado extensamente la keyword `select` de Go en el cliente, se optó por un esquema de uso de `select` bloqueante, del módulo homónimo de Python, sobre distintos sockets (los sockets de los clientes). El resultado de `select` es iterado para consumir y procesar toda la información disponible en el momento (conexiones nuevas o datos enviados de los clientes) y luego se bloquea de nuevo en el `select`.

Con el uso de `select` naturalmente los clientes que ya enviaron todas sus apuestas y están esperando la información de los ganadores quedan en estado de espera del lado del servidor, mientras el servidor sigue procesando los mensajes de las demás agencias que estén activas enviando apuestas. El estado de las agencias que ya están listas se mantiene en un diccionario basado en el ID de las mismas. Cuando se detecta que la última agencia informa que ya envío todas sus apuestas, se lleva a cabo el sorteo y notificación de ganadores a los ganadores de cada agencia que haya solicitado consultar por los ganadores, sin hacer broadcast de todos los ganadores a todas las agencias, incluso si todas solicitaron conocer los ganadores.

#### Protocolo

Nuevos mensajes agregados para manejar la nueva lógica de negocio:

| Mensaje               | Emisor   | Receptor | Payload                                                                                                                              | Propósito                                                                             |
| --------------------- | -------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| **RegisterBets**      | Cliente  | Servidor | Array de:<br> `AGENCIA: int`,<br> `NOMBRE: str`,<br> `APELLIDO: str`,<br> `DOCUMENTO: int`,<br> `NACIMIENTO: int`,<br> `NUMERO: int` | Registrar un batch de apuestas                                                        |
| **RegisterBetOk**     | Servidor | Cliente  |                                                                                                                                      | Informar que operación **RegisterBets** fue exitosa.                                  |
| **RegisterBetFailed** | Servidor | Cliente  | `ERROR: int`                                                                                                                         | Informar que operación **RegisterBets** fue errónea.<br> Se provee un código de error |
| **Ack**               | Cliente  | Servidor |                                                                                                                                      | Informar recepción de mensaje                                                         |
| **AllBetsSent**       | Cliente  | Servidor |                                                                                                                                      | Informar que todas las apuestas de la agencia se enviaron                             |
| **RequestWinners**    | Cliente  | Servidor |                                                                                                                                      | Solicitar información de los ganadores de la lotería de la misma agencia              |
| **InformWinners**     | Servidor | Cliente  | Array de:<br>`DOCUMENTO: int`                                                                                                        | Dar información de los ganadores de la lotería de la misma agencia                    |

### Sobre el Ejercicio N°8
