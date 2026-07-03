---
type: Concept
category: concept
title: "Pods"
description: "Babashka-compatible external process integration for let-go: loading pods and accessing libraries like SQLite, AWS, Docker, and file watching."
tags: [interop, tooling, runtime]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/pods.md"
sources: ["docs/design/pods.md"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# Pods

let-go loads **Babashka pods** — external processes that expose Clojure functions over a simple EDN-based RPC protocol. Pods open the whole pod ecosystem (SQLite, AWS, Docker, file watching, and more) without requiring JVM interop or shipping as a monolithic binary.

## What are pods?

A pod is an external process speaking the Babashka pods protocol: stdio-based EDN message exchange with a request/response model. The host (let-go) spawns a pod, asks it to describe its exported namespaces and functions, and then invokes those functions on demand. Data flows as EDN (vectors, maps, keywords, symbols) serialized to newline-delimited JSON or EDN.

## Protocol

Pods communicate via newline-delimited EDN messages:

- **`:describe` operation** → pod returns a map of namespaces, each with vars, arglists, and optional metadata.
- **`:invoke` operation** → caller sends `{:op :invoke :var "ns/name" :args [...] :id N}`, pod responds with `{:id N :value result}` or `{:id N :ex error-type :err message}`.
- **`:shutdown` operation** → graceful pod termination.

let-go maintains request/response correlation by ID, enforces timeouts, and maps results back to let-go values.

## Loading pods

```clojure
(require '[pods :as pods])

; Load a pod from a local path or URL
(pods/load "/path/to/sqlite-pod")

; Invoke a function from the pod's exposed namespace
(sqlite/query "SELECT * FROM table")

; List active pods
(pods/list)

; Unload and stop a pod
(pods/unload "sqlite-alias")
```

## Data mapping

| EDN type | let-go type |
|----------|-------------|
| `nil`, booleans, ints, strings, chars | scalars (identity mapping) |
| Keywords, symbols | keywords, symbols |
| Vectors, lists | `PersistentVector`, `List` |
| Maps (string/keyword/symbol keys) | `PersistentHashMap` |
| Sets | `PersistentHashSet` |
| Errors | let-go exceptions with pod-provided message and optional data |

## Host architecture

**Pod manager** (`pkg/rt/pods.go`):
- `Start(path, opts)` spawns the pod process with pipes, sends a `:describe` request, and installs proxy vars.
- Maintains a background goroutine reading and dispatching responses by ID.
- Each request carries a timeout context; cancellation sends SIGTERM to the pod.
- `Stop()` (graceful) and `Kill()` (forceful) handle shutdown.

**Proxy namespace**:
- For each function described by the pod, a let-go `Var` is installed that acts as an `Fn`.
- Invoking the proxy serializes arguments to EDN, sends an `:invoke` request, awaits the response (or timeout), and returns the mapped result.
- Errors are raised as let-go exceptions.

## Ergonomics

The `pods` namespace provides:

- `(pods/load path & {:as opts})` — loads and installs a pod; returns or assigns an alias namespace.
- `(pods/unload alias)` — stops the pod and removes proxies.
- `(pods/list)` — returns active pods with PIDs and descriptors.

CLI helpers (planned):

- `lg pods describe <path>` — prints the pod's descriptor.
- `lg pods run <path> -- <args>` — quick test runner.

## Security and resource limits

Pods run as external processes, so they inherit OS-level isolation:

- Allowlist/denylist of pod executables to prevent arbitrary code execution.
- Resource limits per pod (CPU timeout, memory soft limits, max concurrent calls).
- For stricter sandboxing, pods can be run in containers (Docker, VM, etc.).

## Why pods

- **Ecosystem reuse**: Babashka's growing pod collection is instantly available.
- **No JVM dependency**: let-go stays a lean single binary; interop code runs in a separate process.
- **Safe isolation**: each pod is a process boundary; failures are contained.
- **Portable**: EDN + stdio means pods can be written in any language.

## Planned extensions

- **TCP transport** for remote pods.
- **Streaming and binary encoding** (transit) for large payloads.
- **Retry logic and reconnection** for resilient long-running pods.

# Citations

[1] **pkg/rt/pods.go**: Pod manager, stdio transport, request/response routing  
https://github.com/nooga/let-go/blob/main/pkg/rt/pods.go

[2] **docs/design/pods.md**: Detailed design, protocol spec, implementation plan  
https://github.com/nooga/let-go/blob/main/docs/design/pods.md

[3] **Babashka pods**: Protocol documentation and existing pod ecosystem  
https://github.com/babashka/pods

[4] **let-go** (this wiki)  
[../entities/let-go.md](../entities/let-go.md)

---

See also: [go-interop](go-interop.md), [stack-vm](stack-vm.md)
