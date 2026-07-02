---
type: Function
category: concept
title: "filter"
description: "Returns a lazy sequence of elements from a collection that satisfy a predicate."
tags: [clojure, stdlib, concept, reference]
resource: "https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg"
sources: ["repo: nooga/let-go pkg/rt/core/core.lg, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

Selects elements from a collection based on a predicate [fn](fn.md), returning a lazy sequence of only those elements for which the predicate returns a truthy value. Use filter when you need to retain only items matching specific criteria.

# Signature

```clojure
(filter [pred] [f xs])
```

# Examples

```clojure
(filter even? [1 2 3 4 5])
;; => (2 4)
```

```clojure
(filter #(> % 2) [1 2 3 4])
;; => (3 4)
```

```clojure
(filter #(not (empty? %)) ["" "hello" "" "world"])
;; => ("hello" "world")
```

# Citations

https://github.com/nooga/let-go/blob/main/pkg/rt/core/core.lg
