---
type: Source
category: source
title: "Indexed Reverse Polish Notation"
description: "Emir's design for positional value numbering in postfix form, the foundation for let-go's IR encoding."
tags: [compiler, bytecode, reference]
resource: "https://burakemir.ch/post/indexed-rpn/"
sources: ["https://burakemir.ch/post/indexed-rpn/"]
created: "2026-07-03"
updated: "2026-07-03"
status: speculative
---

# Indexed Reverse Polish Notation

Burak Emir's work on **indexed reverse Polish notation (indexed-RPN)** introduces a compact intermediate representation where values are identified by their position on an evaluation stack, rather than by explicit names or SSA renaming. In indexed-RPN, a sequence of postfix operations pop operands and push results; each value's identity is the index of the instruction that produced it. This encoding is SSA-equivalent (each value flows exactly once from producer to consumer) while avoiding the naming overhead of traditional SSA form.

The key insight is that in a linear walk through a program's operations, positional indexing provides implicit producer-consumer links: a consumer simply references the stack position of its operand. This makes indexed-RPN particularly attractive for compact IR design, program analysis, and bytecode generation.

## Relevance to let-go

let-go's [indexed-rpn-ir](../concepts/indexed-rpn-ir.md) adopts this design as its core IR representation. Each operation in let-go's IR catalogue (defined in `pkg/ir/ir_ops.lg`) encodes stack arity (operands popped, results pushed) and purity metadata. Values produced by operations are referenced by their instruction index, enabling SSA-like analysis without explicit renaming. Block-parameter control flow extends this scheme across block boundaries, mirroring φ functions while maintaining the structural clarity of indexed-RPN encoding.

## Derived pages

- [indexed-rpn-ir](../concepts/indexed-rpn-ir.md) — let-go's instantiation of indexed-RPN IR with block-parameter control flow

## Citations

[1] **Burak Emir, "Indexed Reverse Polish Notation, an Alternative to AST"** [2025-12-12]  
https://burakemir.ch/post/indexed-rpn/
