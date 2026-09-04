# Evidencias de la demostración — ProcuraCL 0.3.0

Estas capturas documentan una ejecución completa en MCP Inspector. Los datos son sintéticos y se
identifican explícitamente mediante `source="demo"`.

## Servidor conectado

ProcuraCL se ejecuta como servidor MCP por entrada y salida estándar (`stdio`).

![ProcuraCL conectado mediante MCP stdio](images/inspector-connected.jpg)

## Catálogo MCP

El servidor publica trece herramientas para descubrimiento, consulta, monitoreo y operación.

![Herramientas publicadas por ProcuraCL](images/inspector-tools.jpg)

## Diagnóstico de la fuente

El diagnóstico confirma que la ejecución utiliza el modo demostración y no consume cuota externa.

![Diagnóstico del modo demostración y presupuesto de solicitudes](images/inspector-status.jpg)

## Búsqueda tipada

La consulta devuelve una oportunidad normalizada con comprador, monto, región, fechas y procedencia.

![Resultado normalizado de una búsqueda de Compra Ágil](images/inspector-search.jpg)

## Primera sincronización

La primera ejecución de la vigilancia registra una oportunidad nueva.

![Primera sincronización persistente de una vigilancia](images/inspector-watchlist-sync.jpg)

## Sincronización idempotente

Una ejecución posterior reconoce el mismo registro y evita crear un duplicado.

![Segunda sincronización sin duplicados](images/inspector-idempotent-sync.jpg)

## Historial persistente

El historial permite recuperar los cambios detectados por una vigilancia.

![Historial de cambios de una vigilancia](images/inspector-watchlist-history.jpg)
