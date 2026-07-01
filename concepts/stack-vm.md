---
type: Concept
category: concept
title: "Stack VM"
description: "The stack-based virtual machine that executes let-go bytecode."
tags: [vm, bytecode, runtime]
resource: "https://github.com/nooga/let-go/tree/main/pkg/vm"
sources: ["repo: nooga/let-go pkg/vm, 2026-07-01"]
created: "2026-07-01"
updated: "2026-07-01"
status: speculative
---

# Stack VM

The let-go compiler emits bytecode that runs on a stack-based virtual machine.
Values are pushed and popped from an operand stack; instructions operate on the
top of the stack. This is the execution substrate for [let-go](../entities/let-go.md)
programs after compilation.

> status: speculative — verify details against `pkg/vm` before promoting to stable.

# Citations

[1] [pkg/vm](https://github.com/nooga/let-go/tree/main/pkg/vm)
