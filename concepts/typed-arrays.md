---
type: Concept
category: concept
title: "Typed Arrays"
description: "vm.TypedArray, the mutable Go-slice-backed array behind aget/aset, and why the AOT lowering treats it exactly like a persistent collection."
tags: [runtime, vm, compiler, go]
resource: "https://github.com/nooga/let-go/blob/main/pkg/vm/typed_array.go"
sources:
  - "repo: nooga/let-go pkg/vm/typed_array.go, pkg/rt/core/ir/lattice.lg, pkg/rt/lang.go @ a044ead1, 2026-09-17"
  - "lg scripts/lg-compile on an aget/aset kernel @ 9172aa24, 2026-09-15"
  - "pr: nooga/let-go#821 (typed-array backing slices preserved at the reflection boundary), #778 (collections cross the Go boundary as native values); issue #358 (native homogeneous collections, open), 2026-09-17"
created: "2026-09-17"
updated: "2026-09-17"
status: active
---

# Typed Arrays

let-go has mutable, element-typed arrays alongside the persistent collections:
`byte-array`, `int-array`, `long-array`, `float-array`, `double-array` and
`object-array`, read and written with `aget`/`aset` and sized with
`alength`/`aclone`. Unlike a vector, an array is backed by a real Go slice and
mutates in place. That makes it the obvious reach for a numeric kernel — and
today it buys nothing under [AOT lowering](go-backend.md), which is the point
of this page.

## The representation

`vm.TypedArray` is a kind tag plus a Go slice:

```go
// TypedArray is a mutable, typed array backed by a native Go slice.
// Unlike persistent collections, arrays support in-place mutation via Set.
type TypedArray struct {
	kind ArrayKind // ArrayByte | ArrayInt | ArrayFloat | ArrayObject
	data any       // one of: []byte, []int64, []float64, []Value
}
```

Six constructors map onto four kinds: `float-array` is an alias for
`double-array`, and `int-array` and `long-array` both land on `[]int64`. Each
kind coerces on write, so `aset` on a `byte-array` truncates to a byte and on a
`double-array` widens an int to a float.

`Get` dispatches on the kind and boxes the result:

```go
func (a *TypedArray) Get(i int) Value {
	switch a.kind {
	case ArrayByte:
		return MakeInt(int(a.data.([]byte)[i]))
	case ArrayInt:
		return MakeInt64(a.data.([]int64)[i])
	case ArrayFloat:
		return Float(a.data.([]float64)[i])
	case ArrayObject:
		return a.data.([]Value)[i]
	}
	return NIL
}
```

At the Go interop boundary the backing slice survives rather than being copied:
#821 made a compatible `[]byte`/`[]int64`/`[]float64` cross as the same slice,
so a host that writes into it is visible to let-go and vice versa. That is the
reflection boundary, and it is a different boundary from the one below.

## What the lowering does with an array

Nothing that distinguishes it from a vector. A kernel written against arrays:

```clojure
(defn sum-arr [a n]
  (loop [i 0 s 0.0]
    (if (>= i n) s (recur (inc i) (+ s (aget a i))))))
```

lowers to a function taking the array as an opaque value, calling the same
native primitive an interpreted caller would:

```go
func SumArr(ec *vm.ExecContext, arg0 vm.Value, arg1 int64) (vm.Value, error)
    ...
    arg__1, callErr = rt.CoreAgetf(arg0, vm.Int(i))
```

So every access in the loop re-runs the kind switch, re-asserts
`a.data.([]float64)`, indexes, and boxes the result. Three of those four steps
are loop-invariant — only the index changes — and the boxed index itself
allocates once per access above 255 (see
[value representation](value-representation.md)).

## Why it stops there

The [type lattice](type-inference.md) has no way to say "array of double". Its
`kind-bit` map (`pkg/rt/core/ir/lattice.lg`) enumerates eight scalar kinds —
`:nil :true :false :bool :int :float :string :char` — and nothing else. `:vector`
exists as a kind for reasoning about seqs, but carries no native Go type, and
the `ArrayVector` references in `lower_go.lg` are the persistent vector's
backing rather than a typed array. With no type to prove, codegen has nothing
to emit but the generic call, which is the same reason the
[Go backend](go-backend.md) lists its proven types as scalars only.

This is the array half of [#358](https://github.com/nooga/let-go/issues/358).
Arrays are the more tractable half: the element type is fixed at construction
rather than inferred, they are mutable so a Go slice is a faithful
representation, and the representation already exists — what is missing is a
lattice kind naming what `ArrayKind` already tracks, and a lowering that hoists
the invariant switch out of the loop and indexes the slice directly. The
unresolved part is the boundary, where an array escapes into a `vm.Value`
context and has to box again.
