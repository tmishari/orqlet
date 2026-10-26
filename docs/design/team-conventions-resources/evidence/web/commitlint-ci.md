# Guide: CI Setup - commitlint
URL: https://commitlint.js.org/guides/ci-setup.html
Retrieved: 2026-10-26T16:43Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Purpose
Enforce commit conventions with confidence by linting on your CI servers with `commitlint`.

This guide assumes you have already configured `commitlint` for local usage.

## Excerpt 2: Pull request commits on GitHub Actions
      - name: Validate PR commits with commitlint
        if: github.event_name == 'pull_request'
        run: npx commitlint --from ${{ github.event.pull_request.base.sha }} --to ${{ github.event.pull_request.head.sha }} --verbose

## Excerpt 3: Interactive prompt
Help yourself adopting a commit convention by using an interactive commit prompt. Learn how to use `@commitlint/prompt-cli` in the Use prompt guide.
