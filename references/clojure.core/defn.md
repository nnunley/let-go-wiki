---
type: Macro
category: concept
title: defn
description: "Defines a named function and binds it to the current namespace."
tags: [clojure, stdlib, lisp, concept, runtime]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

`defn` defines a named function and binds it in the current namespace. Use it to create reusable functions that can be called by name throughout your program. It combines [fn](fn.md) for function creation with binding to a name in the current scope.

# Signature

```clojure
(defn name doc-string? [params*] body)
(defn name doc-string? ([params*] body)+)
```

# Examples

```clojure
(do (defn square [x] (* x x)) (square 5))
;; => 25
```

```clojure
(do (defn add [x y] (+ x y)) (add 2 3))
;; => 5
```

```clojure
(do (defn greet [name] (str "Hello, " name "!")) (greet "World"))
;; => "Hello, World!"
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
