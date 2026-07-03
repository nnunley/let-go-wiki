---
type: Idea
category: idea
title: "Clojure at Your Go Dayjob"
description: "Make it feasible and idiomatic to write Clojure code in Go codebases via two-way interop and single-binary deployment."
tags: [clojure, go, interop]
resource: "https://github.com/nooga/let-go#goals"
sources: ["repo: nooga/let-go README (Goals), docs/guide/embedding-in-go.md, docs/guide/clojure-compatibility.md, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: speculative
---

# Clojure at Your Go Dayjob

## What It Is

The north-star aspiration for let-go: enable developers to write idiomatic Clojure within Go organizations and codebases, without requiring special approval, separate JVM processes, or language/deployment friction. A Go shop should be able to embed let-go for scripting, business logic, or data processing, and have Clojure code execute as fast, simple single-binary deployments as the rest of the Go application.

## Why It Matters

- **Language expressiveness**: Clojure's immutable data structures, higher-order functions, and macro system are powerful tools for certain domains (data transformation, configuration, rule engines). Developers should not have to choose between these tools and the simplicity of Go deployment.
- **Hiring and retention**: Teams that use multiple languages can often attract talent more easily. A Go shop with Clojure capability doesn't require all logic to be written in Go, opening space for polyglot teams.
- **Pragmatism**: Not all problems are best solved in Go. Being able to reach for Clojure for specific tasks (e.g., a complex ETL pipeline, a domain-specific language interpreter) without operational overhead makes Go projects more flexible.
- **Single binary**: The absence of JVM dependencies means Clojure code can coexist in a Go binary and be deployed with the same simplicity and speed as native Go code.

## Building Blocks in Place

- **[Go Interop](../concepts/go-interop.md)**: let-go has two-way Go interoperability. Clojure code can call Go functions, and Go code can embed the let-go VM and call Clojure functions.
- **[Embedding in Go](https://github.com/nooga/let-go/blob/main/docs/guide/embedding-in-go.md)**: let-go can be embedded as a scripting and extension layer in Go programs. Go structs roundtrip as records, channels are first-class, and functions are callable in both directions.
- **[Single-Binary Deployment](../concepts/wasm-compilation.md)** (partial): let-go compiles to standalone binaries (native or WASM). A Go app that embeds let-go can ship the VM and user-supplied Clojure code as one binary.
- **[Clojure Compatibility](../entities/let-go.md)**: let-go passes the jank-lang Clojure test suite and supports most of Clojure (persistent data structures, lazy seqs, transducers, protocols, multimethods, core.async, BigInts). Idiomatic Clojure code often runs unmodified.

## Remaining Gaps

The vision is not yet complete; realization requires:

- **Library ecosystem**: Most real Clojure projects depend on libraries. let-go can load Babashka pods, but reaching parity with the JVM ecosystem is not feasible. Developers must adapt or write new implementations.
- **Familiarity in Go teams**: Clojure is not mainstream in Go-centric teams. Adoption requires education, mentorship, and cultural willingness to use another language.
- **Organizational policy**: Some organizations have explicit rules against certain languages. let-go's embedding story must be compelling enough that teams advocate for policy changes.
- **Debugging and observability**: Let-go's debugging experience (especially in embedded scenarios) lags the JVM. Better nREPL integration, stack traces, and profiling would help.

## Roadmap Motivation

From the README Goals: `[ ] Make it legal to write Clojure at your Go dayjob`. This is the project's guiding aspiration, reflecting the author's original joke-turned-useful goal: "an elaborate excuse to write Clojure while pretending to write Go."

Achieving this goal makes let-go not just a language implementation, but a tool for cultural and organizational shift within Go shops—proving that systems languages and expressive, functional languages can coexist in production.

---

# Citations

[1] **README Goals** — the unchecked roadmap item and project vision  
https://github.com/nooga/let-go#goals

[2] **docs/guide/embedding-in-go.md** — embedding let-go as a scripting layer  
https://github.com/nooga/let-go/blob/main/docs/guide/embedding-in-go.md

[3] **docs/guide/clojure-compatibility.md** — compatibility and gaps  
https://github.com/nooga/let-go/blob/main/docs/guide/clojure-compatibility.md

[4] **Go Interop** (this wiki)  
[go-interop.md](../concepts/go-interop.md)

[5] **let-go** (this wiki)  
[let-go.md](../entities/let-go.md)

---

See also: [let-go](../entities/let-go.md), [Go Interop](../concepts/go-interop.md)
