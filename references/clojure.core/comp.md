---
type: Function
category: concept
title: "comp"
description: "Composes functions, returning a new function that applies them from right to left."
tags: [clojure, stdlib, concept, reference]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

Creates a new [fn](fn.md) from multiple functions such that the resulting function applies each function to the result of the previous one, working right-to-left. Useful for building complex transformations from simpler functions.

# Signature

```clojure
(comp [] [f] [f g] [f g & fs])
```

# Examples

```clojure
((comp inc inc) 1)
;; => 3
```

```clojure
((comp #(* 2 %) inc) 3)
;; => 8
```

```clojure
((comp str +) 1 2)
;; => "3"
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
