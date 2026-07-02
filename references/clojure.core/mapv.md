---
type: Function
category: concept
title: "mapv"
description: "Like map, but returns a vector instead of a lazy sequence."
tags: [clojure, stdlib, concept, reference]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

Applies a [fn](fn.md) to elements of one or more collections, returning results as a vector rather than a lazy sequence. Use mapv when you need to eagerly realize all results immediately, such as when the result will be used multiple times or when side effects during evaluation matter.

# Signature

```clojure
(mapv [f coll] [f c1 & colls])
```

# Examples

```clojure
(mapv inc [1 2 3])
;; => [2 3 4]
```

```clojure
(mapv + [1 2 3] [10 20 30])
;; => [11 22 33]
```

```clojure
(mapv #(* % 2) [1 2 3 4])
;; => [2 4 6 8]
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
