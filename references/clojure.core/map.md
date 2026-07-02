---
type: Function
category: concept
title: "map"
description: "Returns a lazy sequence of results applying a function to elements of one or more collections."
tags: [clojure, stdlib, concept, reference]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

Applies a function to corresponding elements across one or more collections, returning a lazy sequence of results. When applied to a single collection, it transforms each element; when applied to multiple collections, it applies the [fn](fn.md) to one element from each collection.

# Signature

```clojure
(map [f] [f coll] [f c1 c2] [f c1 c2 & colls])
```

# Examples

```clojure
(map inc [1 2 3])
;; => (2 3 4)
```

```clojure
(map + [1 2] [10 20])
;; => (11 22)
```

```clojure
(map #(* % 2) [1 2 3 4 5])
;; => (2 4 6 8 10)
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
