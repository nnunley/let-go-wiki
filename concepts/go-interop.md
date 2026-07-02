---
type: Concept
category: concept
title: "Go Interop"
description: "Two-way Go ↔ let-go interoperability: calling Go from let-go, embedding let-go in Go, struct/channel roundtripping, and code generation."
tags: [go, interop, runtime]
resource: "https://github.com/nooga/let-go/tree/main/pkg/api"
sources: ["repo: nooga/let-go pkg/api, pkg/vm (struct registration), docs/guide/embedding-in-go.md, 2026-07-02"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# Go Interop

let-go provides two-way interoperability with Go: embed let-go as a scripting layer in Go programs, call Go functions from let-go code, pass Go structs as records, and share channels between systems. The interop layer uses Go reflection and type registration to bridge the two runtimes seamlessly.

## Embedding let-go in Go

Use `pkg/api.NewLetGo` to create a let-go runtime instance, define Go values as let-go variables, and execute let-go code:

```go
import "github.com/nooga/let-go/pkg/api"

c, _ := api.NewLetGo("myapp")

// Define Go functions and values
c.Def("greet", func(name string) string {
    return "Hello, " + name
})
c.Def("x", 42)

// Execute let-go code against these definitions
v, _ := c.Run(`(greet "world")`)  // => "Hello, world"
v, _ := c.Run(`(+ x 8)`)           // => 50
```

Each `LetGo` instance has its own namespace (`"myapp"`), constant pool, and compiler context. Multiple instances can run concurrently in different goroutines (with caveats; see below).

## Go Functions as let-go Functions

Go functions passed via `Def` are wrapped as let-go native functions. They are callable using the normal invocation syntax:

```clojure
(defn compute [a b]
  (my-fn a b))

(my-fn 10 20)
```

The let-go runtime uses Go reflection to:
- Inspect the function signature (arity, parameter types)
- Convert let-go arguments to Go types on the call
- Box the Go result back to a let-go `Value`

Type conversions follow these rules:
- Numeric types (`int`, `float64`, `int64`, etc.) convert bidirectionally
- Strings convert to/from let-go strings
- Slices of `T` convert to/from let-go sequences; lazy seqs are realized automatically
- Maps convert to/from let-go maps (keyed by string or keyword)

## Go Structs as Records

Register a Go struct type once, then pass instances to let-go and work with them as records:

```go
type Item struct {
    Name  string
    Price float64
    Qty   int
}

vm.RegisterStruct[Item]("myapp/Item")

c.Def("item", Item{Name: "Widget", Price: 9.99, Qty: 5})
```

In let-go:
```clojure
(:name item)           ; => "Widget"
(:price item)          ; => 9.99
(assoc item :qty 10)   ; => new record with Qty=10
(count item)           ; => 3 (field count)
(contains? item :name) ; => true
```

**Unmutated roundtrip**: When a struct is passed to let-go and returned unchanged, it is unboxed directly via `Unbox()` (fast path).

**Mutated roundtrip**: When a struct is modified in let-go (e.g., via `assoc`), the resulting record is reconstructed back to Go via `vm.ToStruct[T]` on the Go side:

```go
v, _ := c.Run(`(assoc item :qty 10)`)
mutated, _ := vm.ToStruct[Item](v.(*vm.Record))
fmt.Println(mutated.Qty) // 10
```

## Go Channels as let-go Channels

Go channels and let-go channels are mutually transparent. Define a channel in Go and use it in let-go's `go` / `<!` / `>!`:

```go
inch := make(chan int)
outch := make(vm.Chan)
c.Def("in", inch)
c.Def("out", outch)

c.Run(`
  (go (loop [i (<! in)]
        (when i
          (>! out (inc i))
          (recur (<! in)))))
`)

go func() {
    for i := range 10 {
        inch <- i
    }
    close(inch)
}()

for v := range outch {
    fmt.Println(v)  // 1, 2, 3, ..., 10
}
```

Channels are first-class in let-go's `core.async` and integrate naturally with goroutines spawned by `go` blocks.

## I/O Customization

The `pkg/api` Options pattern allows embedders to customize I/O and runtime behavior per instance:

- `WithStdout(w)` / `WithStderr(w)`: Route output to custom writers (capture, logging, etc.)
- `WithEmit(fn)`: Handle `(js/emit event-name data)` calls from guest code
- `WithKeySource(ks)`: Supply keyboard input for terminal programs without a real terminal
- `WithStorage(store)`: Provide backend storage for `(storage/...)` calls

Each option is pushed as a dynamic binding during `Run()` and popped afterward. This allows different embedder instances to have different I/O routing without global state.

### Concurrency Caveat

let-go's `Var` bindings are stored in a process-global binding stack. If two goroutines call `Run` on different `LetGo` instances concurrently, their I/O bindings will interleave on the same stack. For deterministic isolation, serialize `Run` calls or run instances in separate processes.

## lginterop Code Generator

For large Go packages, hand-wrapping every function and struct is tedious. The `lginterop` tool generates let-go bindings from Go source:

```
lginterop -pkg mypackage -output mypackage.lg
```

This produces a `.lg` file with wrapped functions and struct registrations, reducing boilerplate.

# Citations

[1] **pkg/api** — embedding API and options  
https://github.com/nooga/let-go/tree/main/pkg/api

[2] **pkg/api/interop_test.go** — comprehensive interop examples  
https://github.com/nooga/let-go/blob/main/pkg/api/interop_test.go

[3] **docs/guide/embedding-in-go.md** — embedding guide  
https://github.com/nooga/let-go/blob/main/docs/guide/embedding-in-go.md

[4] **pkg/vm** — type registration and struct roundtripping  
https://github.com/nooga/let-go/tree/main/pkg/vm

[5] **README.md** — interop overview  
https://github.com/nooga/let-go#embedding-in-go

---

See also: [let-go](../entities/let-go.md), [Stack VM](stack-vm.md)
