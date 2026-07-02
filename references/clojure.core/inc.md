---
type: Function
category: concept
title: "inc"
description: "Returns the next integer, adding 1 to the argument."
tags: [clojure, stdlib, concept, reference]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

Increments a number by adding 1 to it. A convenience [fn](fn.md) commonly used with [map](map.md) and other higher-order functions to transform sequences of numbers.

# Signature

```clojure
(inc [x])
```

# Examples

```clojure
(inc 5)
;; => 6
```

```clojure
(map inc [1 2 3 4])
;; => (2 3 4 5)
```

```clojure
((comp inc inc) 10)
;; => 12
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
