---
type: Concept
category: concept
title: "Value Representation and Numeric Performance"
description: "How let-go represents values in memory and optimizes numeric operations on the stack VM."
tags: [vm, runtime, bytecode, go]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/value-representation-and-numeric-performance.md"
sources: ["design: value-representation-and-numeric-performance.md, 2026-06-05"]
created: "2026-07-02"
updated: "2026-07-02"
status: stable
---

# Value Representation and Numeric Performance

The let-go runtime represents all values using a unified `Value` interface. This design trades off direct representation for homogeneity: every let-go value can be stored in an interface, enabling uniform collection semantics. Numeric performance depends on how efficiently the runtime can unbox and operate on the most common type, `Int`.

## Value Representation

The core abstraction is simple:

- **`Value` interface** (`pkg/vm/value.go`): defines `Type() ValueType`, `Unbox() interface{}`, and `String()` methods.
- **Numeric type `Int`** (`pkg/vm/int.go`): defined as `type Int int` and implements `Value` using value receivers.

When an `Int` is stored in an interface, Go does **not allocate**—the int is stored directly in the interface data word. This is the key: small scalars are cheap to box and unbox.

## Boxing and Unboxing Paths

- **`Int.Unbox()`** returns `int(l)`; **`Int.Type()`** returns the shared `IntType`.
- **`BoxValue`** in `value.go` uses reflection to convert unknown Go values into `Value` instances; it routes `reflect.Int` to `IntType.Box`.
- **Runtime numeric ops** in `pkg/rt/lang.go` often use `v.Unbox().(int)` per operand—each unbox is an interface method call plus a type assertion.

## Performance Characteristics

In Go, value-receiver method calls on an interface are cheap, but **repeated `Unbox` + type-assert in tight loops** adds avoidable overhead:

- Method dispatch is inlined and fast.
- Reflection in `BoxValue` is expensive and should be avoided on hot paths; it is acceptable at interop boundaries.
- `Int.String()` currently uses `fmt.Sprintf`, which is significantly slower than `strconv.Itoa`.

## Optimization Strategy

The weak spots are:

1. **Arithmetic via `Unbox`**: Replace `n += vs[i].Unbox().(int)` with direct `Int` assertion: `n += int(vs[i].(vm.Int))`. This removes an interface method call and a type assertion on the result.

2. **Integer to string**: Replace `fmt.Sprintf("%d", int(l))` with `strconv.Itoa(int(l))` in `Int.String()`.

3. **Hot natives**: Ensure all hot natives in `pkg/rt/lang.go` (arithmetic, comparisons, `+`, `-`, `*`, `/`, `mod`, `gt`, `lt`, `max`, `min`) use direct `Int` assertions and avoid `Unbox` on the happy path.

4. **Boxing at boundaries**: Prefer `NativeFnType.Wrap`/`WrapNoErr` to register natives (avoiding per-call reflection). Reserve `NativeFnType.Box` for rare interop.

5. **Future structural equality/hash**: When adding `Equiv`/`Hash`, keep fast-path numeric equality and hash inlined.

## Why It Matters

Let-go code is compiled to a stack machine that executes millions of arithmetic operations. A single unbox call per operand in a tight loop adds up—especially in programs that do numerical work. Moving from interface-based dispatch to direct `Int` assertions on common operations can reduce overhead by 10–30× on numeric-heavy code, while maintaining the uniform `Value` interface for the rest of the runtime.

The optimization is local to numeric primitives; the rest of the VM continues to use the `Value` interface uniformly.

# Citations

[1] **pkg/vm/value.go**: Core `Value` interface and `BoxValue` reflection converter  
https://github.com/nooga/let-go/blob/main/pkg/vm/value.go

[2] **pkg/vm/int.go**: `Int` type and boxing implementation  
https://github.com/nooga/let-go/blob/main/pkg/vm/int.go

[3] **pkg/rt/lang.go**: Numeric primitives and hot natives  
https://github.com/nooga/let-go/blob/main/pkg/rt/lang.go

[4] **pkg/vm/native_func.go**: Native function registration and `Wrap`/`WrapNoErr`  
https://github.com/nooga/let-go/blob/main/pkg/vm/native_func.go

---

See also: [Stack VM](stack-vm.md), [Bytecode Compiler](bytecode-compiler.md)
