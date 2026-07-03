---
type: Source
category: source
title: "Carbon Language Semantic IR"
description: "Block-parameter SSA intermediate representation design used as reference for let-go's indexed-RPN IR control flow."
tags: [compiler, bytecode, reference]
resource: "https://github.com/carbon-language/carbon-lang/tree/trunk/toolchain/sem_ir"
sources: ["https://github.com/carbon-language/carbon-lang/tree/trunk/toolchain/sem_ir"]
created: "2026-07-03"
updated: "2026-07-03"
status: speculative
---

# Carbon Language Semantic IR

Carbon's Semantic IR (SEM_IR) is a compiler intermediate representation that uses **block parameters** to handle SSA-style value flow across block boundaries. Instead of explicit φ-functions, values produced in one block and consumed in another are threaded as formal parameters on entry blocks and bound by branch arguments from predecessors.

## Relevance to let-go

The block-parameter control-flow design in let-go's [indexed-rpn-ir](../concepts/indexed-rpn-ir.md) draws on this approach: intra-block computation is encoded as indexed-RPN (postfix notation with positional value numbering), while inter-block value flow uses block parameters—cleanly separating value threading from the linear sequence of operations within each block. Carbon's SEM_IR serves as a reference implementation of this pattern.

## Derived pages

- [indexed-rpn-ir](../concepts/indexed-rpn-ir.md)

## Citations

[1] **Carbon Language Project**  
https://github.com/carbon-language/carbon-lang  
The Carbon programming language and its toolchain.
