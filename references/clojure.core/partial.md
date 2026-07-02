---
type: Function
category: concept
title: "partial"
description: "Creates a new function with some arguments already supplied."
tags: [clojure, stdlib, concept, reference]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

Returns a new [fn](fn.md) with some arguments pre-filled, useful for creating specialized versions of existing functions. Partial application allows you to fix certain arguments and create reusable functions that accept the remaining arguments.

# Signature

```clojure
(partial [f] [f arg1] [f arg1 arg2] [f arg1 arg2 arg3] [f arg1 arg2 arg3 & more])
```

# Examples

```clojure
((partial + 10) 5)
;; => 15
```

```clojure
((partial * 2 3) 4)
;; => 24
```

```clojure
(let [add10 (partial + 10)] (map add10 [1 2 3]))
;; => (11 12 13)
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
