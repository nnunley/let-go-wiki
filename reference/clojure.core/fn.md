---
type: Macro
category: concept
title: fn
description: "Creates an anonymous function with specified parameters and body."
tags: [clojure, stdlib, lisp, concept, runtime]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

`fn` creates an anonymous function or named function. Use it to define functions inline without assigning them to a name (useful for higher-order functions like [apply](apply.md) or [map](map.md)), or define a named function for recursion. `fn` supports both single-arity and multi-arity definitions.

# Signature

```clojure
(fn [params*] body)
(fn name [params*] body)
(fn ([params*] body) ([params*] body) ...)
```

# Examples

```clojure
((fn [x] (+ x 1)) 5)
;; => 6
```

```clojure
((fn [x y] (* x y)) 3 4)
;; => 12
```

```clojure
(let [adder (fn [x y] (+ x y))]
  (adder 10 20))
;; => 30
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
