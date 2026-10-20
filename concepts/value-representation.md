---
type: Concept
category: concept
title: "Value Representation and Numeric Performance"
description: "How let-go represents values in memory and optimizes numeric operations on the stack VM."
tags: [vm, runtime, bytecode, go]
resource: "https://github.com/nooga/let-go/blob/main/docs/design/value-representation-and-numeric-performance.md"
sources: ["design: value-representation-and-numeric-performance.md, 2026-06-05", "repo: nooga/let-go pkg/vm/int.go @ a044ead1, 2026-09-16", "pr: nooga/let-go#859 (vm.Int is int64); issue #867 (Unbox narrows on 32-bit), 2026-09-16", "bench: interface-boxing allocs for type Int int64, go1.26.5 darwin/arm64, 2026-09-17", "repo: nooga/let-go pkg/vm/int.go, pkg/vm/value.go, pkg/vm/native_func.go, pkg/vm/numbers.go, pkg/vm/hash.go, pkg/vm/equals.go, pkg/rt/golower_runtime.go, pkg/rt/lang.go @ b82588292b, 2026-10-19", "pr: nooga/let-go#1001 (NativeFnType.Box stores fast shapes in one allocation); nooga/let-go#569 (strconv for Int.String), checked 2026-10-19; issue #867 still open, checked 2026-10-19"]
created: "2026-07-02"
updated: "2026-10-19"
status: stable
---

# Value Representation and Numeric Performance

The let-go runtime represents all values using a unified `Value` interface. This design trades off direct representation for homogeneity: every let-go value can be stored in an interface, enabling uniform collection semantics. Numeric performance depends on how efficiently the runtime can unbox and operate on the most common type, `Int`.

## Value Representation

The core abstraction is simple:

- **`Value` interface** (`pkg/vm/value.go`): defines `Type() ValueType`, `Unbox() interface{}`, and `String()` methods.
- **Numeric type `Int`** (`pkg/vm/int.go`): defined as `type Int int64` and implements `Value` using value receivers. It was host-width `int` until [#859](https://github.com/nooga/let-go/pull/859); widening it made let-go integers 64-bit on 32-bit targets (wasm, `linux/386`, `linux/arm`) as well. `Int` also implements the `Hashable` interface (`Hash() uint32`, via `hashUint64`; `pkg/vm/int.go`, `pkg/vm/hash.go` at b82588292b).

Storing an `Int` in an interface allocates, but only above a threshold. Go keeps a static array of boxed small integers (`runtime.staticuint64s`), so boxing an `Int` in 0-255 costs nothing; any larger value heap-allocates eight bytes. Measured on go1.26.5 darwin/arm64:

| boxed value | ns/op | allocs/op |
|---|---|---|
| `Int(i % 256)` | 2.0 | 0 |
| `Int(i + 100000)` | 8.2 | 1 (8 B) |

This page previously said boxing never allocates, on the reasoning that the int sits in the interface data word directly. That is not how Go stores non-pointer types in an interface. The practical consequence is that small-integer work boxes free while indices and counters past 255 do not, which is exactly the shape a hot loop over a long collection has.

## Boxing and Unboxing Paths

- **`Int.Unbox()`** returns `int(l)`; **`Int.Type()`** returns the shared `IntType`. `Unbox` still narrows to host width, so on a 32-bit target it truncates a wide `Int`. The source comment now says this is deliberate for Go interop (reflect proxies, struct mapping), and that `ToInt64` returns the full value (`pkg/vm/int.go`, `pkg/vm/numbers.go` at b82588292b). The defect is still open as [#867](https://github.com/nooga/let-go/issues/867) (checked 2026-10-19), which covers the collection, math and interop boundaries that unbox this way.
- **`BoxValue`** in `value.go` uses reflection to convert unknown Go values into `Value` instances. Its switch no longer goes through `IntType.Box`: `reflect.Int` through `reflect.Int64` become `Int(v.Int())` and the unsigned kinds become `Int(v.Uint())` directly (`pkg/vm/value.go:189-193` at b82588292b).
- **Numeric operators** no longer read operands through `Unbox`. The arithmetic and comparison primitives in `pkg/vm/numbers.go` (`NumAdd`, `NumLt`, and the rest) type-assert `Int`, `Float` and `*BigInt` directly, and the natives in `pkg/rt/lang.go` call them. The lowered comparison helpers `LtValue`, `LeValue`, `GtValue` and `GeValue` in `pkg/rt/golower_runtime.go` check `vm.Int` on both operands before falling back to `NumLt` and the others. A search of `pkg/` at b82588292b finds no `Unbox().(int)` operand read; the one remaining hit is in `pkg/vm/vm_test.go`.

## Performance Characteristics

In Go, value-receiver method calls on an interface are cheap, but **repeated `Unbox` + type-assert in tight loops** adds avoidable overhead:

- Method dispatch is inlined and fast.
- Reflection in `BoxValue` is expensive and should be avoided on hot paths; it is acceptable at interop boundaries.
- `Int.String()` uses `strconv.FormatInt(int64(l), 10)` (`pkg/vm/int.go` at b82588292b). An earlier version used `fmt.Sprintf`; [#569](https://github.com/nooga/let-go/pull/569) moved it to `strconv`.

## Optimization Strategy

The weak spots are:

1. **Arithmetic via `Unbox`** (done): Operands were read as `n += vs[i].Unbox().(int)`. The pattern to keep is the direct `Int` assertion, `n += int(vs[i].(vm.Int))`, which removes an interface method call and a type assertion. The numeric operators now use it (`pkg/vm/numbers.go`), and no `Unbox().(int)` operand read remains under `pkg/` at b82588292b.

2. **Integer to string** (done): `Int.String()` uses `strconv.FormatInt`. [#569](https://github.com/nooga/let-go/pull/569) moved it from `fmt.Sprintf` to `strconv.Itoa`, and [#859](https://github.com/nooga/let-go/pull/859) switched it to `FormatInt` when `Int` was widened to 64 bits (`pkg/vm/int.go` at b82588292b, line 71).

3. **Hot natives**: The numeric natives in `pkg/rt/lang.go` (`+`, `-`, `*`, `/`, `mod`, `<`, and the comparisons) call `vm.NumAdd`, `vm.NumSub`, `vm.NumMul`, `vm.NumDiv`, `vm.NumMod`, `vm.NumLt`, `vm.NumGt`, `vm.NumGe` and `vm.NumLe` (`pkg/rt/lang.go:1986` (`>`), `:2005` (`<`), `:2024` (`>=`), `:2043` (`<=`), `:5190`–`:5250`, `:5551` at b82588292b). `max` and `min` reach `vm.NumGt` and `vm.NumLt` at `pkg/rt/lang.go:6523` and `:6548` (`CoreMax`, `CoreMin`), through the adapters in `pkg/rt/zz_primitives_generated.go`, so they take the same route. Hot paths in lowered code use the `golower_runtime.go` helpers listed above. Keep the happy path free of `Unbox`.

4. **Boxing at boundaries**: Prefer `NativeFnType.Wrap`/`WrapNoErr` to register natives (`pkg/vm/native_func.go`). Reflection is no longer the cost of `NativeFnType.Box` for common shapes: since [#1001](https://github.com/nooga/let-go/pull/1001), `Box` stores a fast-shape Go func (`func` of zero to four `Value` arguments returning `Value` or `(Value, error)`, and `func(...Value) (Value, error)`) in one allocation, and `callFast` dispatches it by type switch with no reflection and no adapter closure. Only other shapes take the reflect proxy (`boxReflectFunc`). `Wrap` is still the clearer choice for new natives, but the reason is the explicit error and arity shape, not per-call reflection on `Box`.

5. **Structural equality and hash**: `Int` already implements `Hash()`. Equality for non-scalar values goes through `vm.ValueEquals`, a function variable set by the `rt` package (`pkg/vm/equals.go`). The lowered `=` routes through `EqValue` whenever an operand may be a collection, and concrete comparable scalars keep native Go `==` (`pkg/rt/golower_runtime.go`). Keep the numeric fast path inlined when this grows.

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

[4] **pkg/vm/native_func.go**: Native function registration, `Box` fast shapes (`callFast`), and `Wrap`/`WrapNoErr`  
https://github.com/nooga/let-go/blob/main/pkg/vm/native_func.go

[5] **pkg/vm/numbers.go**: Numeric promotion and arithmetic (`NumAdd`, `NumLt`, …) with direct type assertions  
https://github.com/nooga/let-go/blob/main/pkg/vm/numbers.go

[6] **pkg/rt/golower_runtime.go**: Lowered comparison helpers (`LtValue`, `LeValue`, `GtValue`, `GeValue`, `EqValue`)  
https://github.com/nooga/let-go/blob/main/pkg/rt/golower_runtime.go

[7] **pkg/vm/equals.go** and **pkg/vm/hash.go**: `ValueEquals` hook and the `Hashable` interface  
https://github.com/nooga/let-go/blob/main/pkg/vm/equals.go

---

See also: [Stack VM](stack-vm.md), [Bytecode Compiler](bytecode-compiler.md)
