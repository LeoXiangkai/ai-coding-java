# MyBatis Dynamic Order

Type: sql-case

Scope: MyBatis XML using dynamic order/group/column names.

## Problem

MyBatis `#{}` cannot parameterize SQL identifiers, so projects sometimes use `${}` for dynamic order fields. Direct user input in `${}` creates SQL injection risk.

## Reusable Fact

`${}` is allowed only after whitelist mapping from external input to known-safe SQL identifiers. The XML or nearby code must make the whitelist path clear.

## Verification Method

1. Locate every `${}` in changed MyBatis XML.
2. Trace the value source.
3. Confirm user input is mapped to a fixed allowed identifier.
4. Reject direct pass-through.

## Applies When

Mapper XML contains `${}`.

