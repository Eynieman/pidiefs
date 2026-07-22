# Security Policy

## Framework de Guardrails

### Input (todo lo que entra)
1. Validación
2. Filtración
3. Sanitización

### Output (todo lo que sale)
1. Validación
2. Filtración
3. Sanitización
4. Chequeo de políticas

## Implementación

| Capa | Input | Output |
|------|-------|--------|
| Upload PDF | Validación: extensión, tamaño, magic bytes, MIME, duplicados<br>Filtración: filename sanitizado<br>Sanitización: contenido PDF para LLM | - |
| Query/Pregunta | Validación: Pydantic, longitud, caracteres control, doc_id<br>Filtración: jailbreak, toxicidad, PII<br>Sanitización: trim | Validación: toxicidad, PII, system leakage<br>Filtración: respuestas inseguras<br>Sanitización: rehype-sanitize en Markdown |
| Conversaciones | Validación: Pydantic, role, max_length<br>model_config: extra="forbid" | - |
| API General | CORS, TrustedHost, Content-Type, body size, CSRF, rate limiting | Security headers, X-Request-ID |
| Frontend | CSP nonce, validación upload | rehype-sanitize, Error Boundaries |

## Stack de Seguridad

- **Autenticación**: JWT con tokens Bearer y almacenamiento en localStorage
- **Rate Limiting**: slowapi
- **CSP**: nonce criptográfico por request via Middleware
- **Validación**: Pydantic v2
- **LLM Guardrails**: detección de jailbreak, toxicidad, PII, system leakage
- **XSS Prevention**: rehype-sanitize + CSP
- **Auditoría**: AuditMiddleware con request_id
- **Monitoreo**: MetricsCollector en memoria, alertas de patrones sospechosos
- **Autorización**: Filtrado por user_id en documentos y conversaciones

## Reportar vulnerabilidades
Abrir issue en el repositorio.
