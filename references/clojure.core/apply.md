---
type: Function
category: concept
title: apply
description: "Applies a function to a sequence of arguments, unpacking the final argument list."
tags: [clojure, stdlib, lisp, concept, runtime]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

`apply` takes a function and a sequence of arguments, unpacking the sequence as the final arguments to the function. Use it when you have arguments collected in a list or vector and need to pass them to a function as individual parameters.

# Signature

```clojure
(apply [f args] [f x args] [f x y args] [f x y z args] [f a b c d & args])
```

# Examples

```clojure
(apply + [1 2 3])
;; => 6
```

```clojure
(apply list 1 [2 3])
;; => (1 2 3)
```

```clojure
(apply str "Hello" [" " "World"])
;; => "Hello World"
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
