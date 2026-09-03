# Guion de presentación — ProcuraCL MCP

Duración objetivo: 90 segundos.

## 1. Problema — 15 segundos

“Las oportunidades de compra pública existen en APIs distintas, con contratos y filtros diferentes.
Para una pyme o un analista, encontrar procesos relevantes y recordar qué cambió requiere trabajo
manual y conocimiento técnico.”

## 2. Solución — 15 segundos

“ProcuraCL convierte Mercado Público y Compra Ágil en herramientas MCP tipadas. Un agente puede
buscar oportunidades, consultar compradores y crear vigilancias persistentes usando lenguaje
estructurado, sin recibir ni manipular la credencial de ChileCompra.”

## 3. Demostración — 35 segundos

1. Abrir `get_data_source_status` y mostrar que el modo demo está identificado explícitamente.
2. Ejecutar `search_agile_purchases` con `automatización`, estado `open` y Región Metropolitana.
3. Mostrar el resultado `DEMO-202-AG26`, su comprador, monto, fechas y procedencia.
4. Crear la vigilancia “Demo portafolio ProcuraCL 0.3.0”.
5. Sincronizar: se detecta una oportunidad nueva.
6. Sincronizar otra vez: se registra como sin cambios y no se duplica.
7. Abrir `list_watchlist_changes` para mostrar el historial persistente.

## 4. Decisiones técnicas — 15 segundos

“La arquitectura separa MCP, casos de uso, dominio, persistencia y adaptadores externos. SQLite
aporta historial, caché y presupuesto atómico de solicitudes. El modo real aísla Mercado Público v1
y Compra Ágil v2, normaliza sus respuestas y conserva la procedencia de cada dato.”

## 5. Cierre — 10 segundos

“El resultado es un MVP instalable, probado y listo para conectar un ticket personal. Demuestra
diseño de producto, integración de APIs públicas, MCP, tipado, seguridad de secretos, persistencia e
ingeniería orientada a pruebas.”

## Evidencia verificable

- 13 herramientas MCP, 2 recursos y 1 prompt.
- 24 pruebas automatizadas y 79% de cobertura de sentencias.
- Ruff, mypy estricto, lockfile y CI verificados.
- Demo sin red y live mode probado contra ambos endpoints oficiales.
- `.env` y `data/` excluidos del repositorio.
