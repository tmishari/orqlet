# DORA | Capabilities: Trunk-based development
URL: https://dora.dev/capabilities/trunk-based-development/
Retrieved: 2026-10-26T16:43Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Two patterns
The second pattern is known as trunk-based development, where each developer divides their own work into small batches and merges that work into trunk at least once (and potentially several times) a day. The key difference between these approaches is scope. Feature branches typically involve multiple developers and take days or even weeks of work. In contrast, branches in trunk-based development typically last no more than a few hours, with many developers merging their individual changes into trunk frequently.

## Excerpt 2: What DORA data shows
Analysis of DORA data from 2016 (PDF) and 2017 (PDF) shows that teams achieve higher levels of software delivery and operational performance (delivery speed, stability, and availability) if they follow these practices:

- Have three or fewer active branches in the application’s code repository.
- Merge branches to trunk at least once a day.
- Don’t have code freezes and don’t have integration phases.

## Excerpt 3: Heavy review as a pitfall
An overly heavy code-review process. Many organizations have a heavyweight code review process that requires multiple approvals before changes can be merged into trunk. When code review is laborious and takes hours or days, developers avoid working in small batches and instead batch up many changes.

## Excerpt 4: Tests before commit
Not running automated tests before committing code. In order to ensure trunk is kept in a working state, it’s essential that tests are run against code changes before commit.

## Excerpt 5: Protect branches
- Implement comprehensive automated testing. Make sure that you have a comprehensive and meaningful suite of automated unit tests. and that these are run before every commit. For example, if you’re using GitHub, you can protect branches to only allow pull request merges when all tests have passed.
