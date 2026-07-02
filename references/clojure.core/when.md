---
type: Macro
category: concept
title: when
description: "Evaluates body forms only if the condition is truthy, otherwise returns nil."
tags: [clojure, stdlib, lisp, concept, runtime]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

`when` is a conditional macro that evaluates its body only when the condition is truthy. Use it for single-branch conditionals where you want to execute side effects or return a value based on a condition, with nil as the implicit else case.

# Signature

```clojure
(when test & body)
```

# Examples

```clojure
(when true 42)
;; => 42
```

```clojure
(when false 42)
;; => nil
```

```clojure
(let [x 5]
  (when (> x 3)
    (str "x is greater than 3")))
;; => "x is greater than 3"
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
