---
type: Macro
category: concept
title: let
description: "Binds local variables to values within a limited scope."
tags: [clojure, stdlib, lisp, concept, runtime]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

`let` creates a new lexical scope and binds symbols to values for use within that scope. Use it to define intermediate variables, break down complex expressions, or avoid repeating calculations.

# Signature

```clojure
(let [bindings & body])
```

# Examples

```clojure
(let [x 5] (+ x 3))
;; => 8
```

```clojure
(let [a 2 b 3] (* a b))
;; => 6
```

```clojure
(let [x 10 y 20 sum (+ x y)] sum)
;; => 30
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
