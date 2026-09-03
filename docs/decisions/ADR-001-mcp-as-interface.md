# ADR-001: MCP is an interface

Status: accepted

ProcuraCL keeps MCP registration separate from application and domain logic. This lets the same use
cases support FastAPI, a CLI and background synchronization later. It also keeps protocol concerns
out of upstream API translation and testing.

