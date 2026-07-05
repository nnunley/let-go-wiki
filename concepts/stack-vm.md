---
type: Concept
category: concept
title: "Stack VM"
description: "The stack-based bytecode interpreter: operand-stack frames, the fetch-decode-dispatch loop, and specialized arithmetic opcodes."
tags: [vm, bytecode, runtime, compiler]
resource: "https://github.com/nooga/let-go/tree/main/pkg/vm"
sources: ["repo: nooga/let-go pkg/vm/vm.go (opcodes, CodeChunk, Frame, Frame.Run), 2026-07-05"]
created: "2026-07-01"
updated: "2026-07-05"
status: stable
---

# Stack VM

The [bytecode compiler](bytecode-compiler.md) lowers each function to a `CodeChunk`, and this stack machine executes it. There are no registers: instructions push and pop [values](value-representation.md) on a per-call operand stack, and every instruction operates on the top of that stack. It is the execution substrate for [let-go](../entities/let-go.md) programs once the [IR pipeline](ir-pipeline.md) has emitted their bytecode.

The interpreter lives in `pkg/vm/vm.go`: an opcode table, the `CodeChunk` container, the `Frame` (one per function activation), and `Frame.Run` — the dispatch loop.

# Bytecode encoding

A `CodeChunk` holds a flat `[]int32` instruction array, a constant pool, `maxStack` (the stack depth the compiler computed for the function), a source map, and a local-variable debug table:

```go
type CodeChunk struct {
    maxStack  int
    consts    *Consts
    code      []int32      // opcode words + inline args, packed end to end
    length    int
    sourceMap *SourceMap
    localVars []LocalVar
}
```

Instructions are **variable width**. The first `int32` of each is the opcode word; zero or more `int32` argument words follow:

| Width | Opcodes |
|-------|---------|
| 1 word (no args) | `NOOP`, `POP`, `RETURN`, `THROW`, `TRY_POP`, the arithmetic/comparison ops, … |
| 2 words (1 arg) | `LOAD_CONST`, `LOAD_ARG`, `LOAD_VAR`, `INVOKE`, `JUMP`, `BRANCH_TRUE`/`BRANCH_FALSE`, `POP_N`, `DUP_NTH`, `TAIL_CALL`, … |
| 3 words (2 args) | `TRY_PUSH` (catchOffset, finallyOffset) |
| 4 words (3 args) | `RECUR` (offset, argc, …) |

Only the low byte of the opcode word is the opcode — `inst & 0xff`. The high 16 bits carry a stack-depth hint (`(op >> 16) & 0xffff`), used by the disassembler and tooling. Arguments are indices (into the constant pool or argument vector), branch offsets, or arities. `CodeChunk.Debug` walks the array with exactly this width table to disassemble a chunk.

# Opcode families

The ~37 opcodes group into a small number of roles:

- **Loads** — `LOAD_CONST` (constant pool), `LOAD_ARG` (argument vector), `LOAD_VAR` / `SET_VAR` (var roots), `LOAD_CLOSEDOVER` (captured value).
- **Stack shuffling** — `POP`, `POP_N` (save top, drop n), `DUP_NTH` (duplicate the nth-from-top).
- **Control flow** — `JUMP`, `BRANCH_TRUE`, `BRANCH_FALSE`, all by signed offset.
- **Calls & return** — `INVOKE` (arity arg), `TAIL_CALL` (reuses the frame), `RETURN`, plus `RECUR` / `RECUR_FN` for `loop`/`recur` and self-recursion.
- **Closures** — `MAKE_CLOSURE`, `PUSH_CLOSEDOVER`, `MAKE_MULTI_ARITY`.
- **Exceptions** — `TRY_PUSH`, `TRY_POP`, `THROW`.
- **Specialized arithmetic/comparison** — `ADD`, `SUB`, `MUL`, `LT`, `LTE`, `GT`, `GTE`, `EQ`, `INC`, `DEC`, `QUOT`, `DIV` (see below).

# The frame

Each function activation gets a `Frame`, which owns the operand stack and the interpreter's registers:

```go
type Frame struct {
    stack       []Value      // operand stack (len = maxStack)
    args        []Value      // this call's arguments
    closedOvers []Value      // captured values (closures)
    consts      *Consts      // constant pool
    code        *CodeChunk
    ip          int          // instruction pointer (index into code.code)
    sp          int          // stack pointer (next free slot)
    handlers    []exHandler  // active exception handlers; nil when unused
    ec          *ExecContext // dynamic bindings for this execution
}
```

`push`/`pop`/`nth`/`mult`/`drop` are thin helpers over `stack` and `sp`. Dynamic bindings and function dispatch route through `ec` — the [exec context](exec-context.md).

**Frame pooling.** Frames are reused from a mutex-guarded LIFO (cap 256), not allocated per call. The source comment records why: `sync.Pool` cost ~25% of CPU on `fib(30)` because its per-P bookkeeping dominates let-go's tiny per-call work, so a plain mutex-guarded stack is faster for the common single-goroutine case and still safe across goroutines.

# The dispatch loop

`Frame.Run` is a `for` loop around a `switch inst & 0xff`. Each case does its work, adjusts the stack, and advances `ip` by the instruction's width:

```go
for {
    inst := f.code.code[f.ip]
    switch inst & 0xff {
    case OP_LOAD_CONST:
        idx := f.code.code[f.ip+1]
        f.push(f.consts.get(int(idx)))
        f.ip += 2
    case OP_LOAD_ARG:
        idx := f.code.code[f.ip+1]
        f.push(f.args[idx])
        f.ip += 2
    case OP_RETURN:
        return f.pop()
    // ...
    }
}
```

`OP_INVOKE` reads the arity, pops that many arguments plus the callee, dispatches through `f.ec.Invoke`, drops the consumed slots, and pushes the result. `OP_RETURN` pops the top value and returns it, ending the frame. Branch opcodes assign `f.ip` directly instead of stepping.

# Specialized fast-path opcodes

The compiler emits the dedicated arithmetic/comparison opcodes for known binary calls to core operators, so hot code skips generic function dispatch. Each inlines the `int64` path and falls back to the boxed numeric tower only for other types. `OP_ADD`:

```go
case OP_ADD:
    b := f.stack[f.sp-1]
    a := f.stack[f.sp-2]
    if ai, ok := a.(Int); ok {
        if bi, ok := b.(Int); ok {
            r, ok := checkedAddInt(ai, bi)   // overflow-checked
            if !ok { /* raise integer overflow */ }
            f.stack[f.sp-2] = r
            f.sp--
            f.ip++
            continue
        }
    }
    r, err := NumAdd(a, b)                    // generic numeric tower
    // ...
```

These opcodes avoid `NativeFn.Invoke`, interface boxing, and panic-based error recovery on the common path. The `int64` path is overflow-checked, but overflow does **not** promote: `ADD`, `SUB`, `MUL`, `INC`, and `DEC` raise an `"integer overflow"` error. Promotion to the wider numeric tower happens only when an operand is not an `Int`, via the generic `NumXxx` fallback.

# Recursion, tail calls, and exceptions

- **`recur`** compiles to `RECUR` for a `loop` back-edge and to `RECUR_FN` for function self-recursion — either way a slot-rebinding jump, so iteration runs in constant stack space rather than growing Go frames.
- **`TAIL_CALL`** reuses the current `Frame` only when the callee is a direct `*Func`; other callable types (native fns, and anything else) still dispatch through `ec.Invoke` and get their own frame.
- **Exceptions** use a per-frame handler stack. `TRY_PUSH` records a catch IP and the stack pointer to restore. When an error surfaces at a site that consults the handler stack, the loop unwinds to the innermost handler *in this frame*, resets `sp` to `savedSP`, pushes the error value, and jumps to the catch IP — no Go-stack unwinding within the frame. Two caveats: an error raised in a nested call propagates the ordinary way (each `Invoke` returns it up the Go stack) until some frame's handler catches it, so cross-frame propagation *does* unwind Go frames; and not every interpreter error consults the handler stack — some (e.g. out-of-bounds const/arg lookups) return directly.

# Debug info

`CodeChunk` carries a `SourceMap` (`ip` → source location), which error construction consults via `LookupSource` to attach source positions to crash traces — including for code loaded from a precompiled bundle under WASM. It also carries a `localVars` table (stack slot → binding name); that table is compiled and serialized into the [lgb format](lgb-bytecode-format.md), but the runtime does not yet read it when formatting errors — only the `SourceMap` is consumed today, so traces name source positions but not local variables. See [debug info & source maps](debug-info.md).

# Examples

Values the VM computes, via `lg -e`:

```clojure
(+ 1 2)
;; => 3          ; OP_LOAD_CONST 1, OP_LOAD_CONST 2, OP_ADD, OP_RETURN
```

```clojure
(defn add [a b] (+ a b))
(add 3 4)
;; => 7          ; OP_LOAD_ARG 0, OP_LOAD_ARG 1, OP_ADD, OP_RETURN
```

```clojure
(loop [i 0 acc 0]
  (if (< i 5) (recur (inc i) (+ acc i)) acc))
;; => 10         ; OP_LT + OP_BRANCH_FALSE drive the loop; OP_RECUR is the back-edge
```

```clojure
(let [f ((fn [x] (fn [y] (+ x y))) 10)] (f 5))
;; => 15         ; inner fn is a closure over x; x arrives via OP_LOAD_CLOSEDOVER
```

# Citations

[1] **pkg/vm** (VM package)
https://github.com/nooga/let-go/tree/main/pkg/vm

[2] **pkg/vm/vm.go** — opcode table, `CodeChunk`, `Frame`, `Frame.Run`
https://github.com/nooga/let-go/blob/main/pkg/vm/vm.go

[3] **Bytecode Compiler** (this wiki)
[bytecode-compiler.md](bytecode-compiler.md)

[4] **IR Pipeline** (this wiki)
[ir-pipeline.md](ir-pipeline.md)

[5] **Exec Context** (this wiki)
[exec-context.md](exec-context.md)

---

See also: [Bytecode Compiler](bytecode-compiler.md), [IR Pipeline](ir-pipeline.md), [Indexed-RPN IR](indexed-rpn-ir.md), [lgb Bytecode Format](lgb-bytecode-format.md), [Value Representation](value-representation.md), [Debug Info](debug-info.md), [let-go](../entities/let-go.md)
