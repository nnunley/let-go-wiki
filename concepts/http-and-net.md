---
type: Concept
category: concept
title: "HTTP and Networking"
description: "The http and net namespaces: the owned-listener server surface, streaming response bodies, the three named client timeout scopes, and how scope cancellation reaches an in-flight request."
tags: [runtime, stdlib, go]
resource: "https://github.com/nooga/let-go/blob/main/docs/guide/http.md"
sources:
  - "doc: nooga/let-go docs/guide/http.md (status: active, last-verified 2026-09-18) @ 36b13f79, 2026-09-20"
  - "repo: nooga/let-go pkg/rt/http.go, pkg/rt/net.go @ 36b13f79, 2026-09-20"
  - "pr: nooga/let-go#898 (http/start, stop, wait), #851 (streaming bodies), #856 (named timeout scopes), #848 (scope cancellation reaches clients), #850 (scope-cancelled?), #896 (net/listen, accept, local-address), #849 (empty :headers), 2026-09-20"
  - "lg -e transcript on lg 1.13.0 (369e2a69): http/start, http/stop, http/wait, http/serve, net/listen, net/accept, net/local-address and scope-cancelled? all resolve, 2026-09-20"
created: "2026-09-20"
updated: "2026-09-20"
status: active
---

# HTTP and Networking

A Ring-style server and a small client, both gated off `tinygo` and
`lg_no_http` builds. `lg_no_http` drops `net/http` from the runtime entirely
(#658), which is one of the larger binary-size levers.

The v1.13.0 range reshaped this surface around a real application — an
`integrant` and SQLite web app — so most of what follows is about holding a
handle instead of calling a function that never returns.

## Serving: an owned listener

`http/serve` blocks. It is now `http/start` plus `http/wait`:

- `http/start` binds and returns a handle. A bad bind address throws **at bind
  time**, rather than surfacing from inside the request loop later.
- `http/wait` blocks on that handle.
- `http/stop` shuts it down.

That split is what lets a supervised component own a server: `integrant`'s
`init-key` can start and return the handle, and `halt-key!` can stop it.

**Streaming bodies.** A response `:body` that is a channel or a lazy seq is
written element by element with a flush after each (#851), which is what makes
SSE and long-polling handlers work.

## The client, and cancellation

`http/get`, `http/post` and `http/request` are the client surface.

**Three named timeout scopes** on `http/request` (#856): connect, request, and
`stream_read`. Each names itself in the resulting error, so a timeout says which
phase expired rather than just that one did.

**Scope cancellation reaches in-flight requests** (#848). Closing the enclosing
scope aborts a running `http/get`, `http/post` or `http/request`, including one
blocked reading a `:as :stream` body. Before this, the request and its goroutine
outlived the scope that started them. `scope-cancelled?` (#850) lets code
distinguish "woke up" from "was cancelled" after a blocking native returns.

See [concurrency model](concurrency-model.md) for what a scope is.

## TCP: `net`

`net/listen`, `net/accept` and `net/local-address` (#896) give TCP the
owned-listener surface the `unix` namespace already had. `net/dial` and
`net/read!` were already present.

An `net/local-address` on a listener bound to port 0 is how a test finds the
port the OS chose.

## Not covered here

Written from the guide and the native surface rather than from having built a
service on it. A worked `integrant` example, the full request and response map
keys, and TLS all belong here and are not yet written.
