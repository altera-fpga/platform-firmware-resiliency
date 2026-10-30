# Contributing

Thank you for your interest in contributing to `csr-gen`.

We welcome bug fixes, features, documentation, tests, examples, and tooling
improvements. For AI-assisted contribution expectations, see also
[AI_POLICY.md](AI_POLICY.md).

## Expected behavior

Contributors are expected to interact respectfully and professionally with other
members of the community.

## Getting started

Before submitting a contribution:

1. Review existing issues and discussions.
2. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for project direction and
   review expectations.
3. Add or update tests where behavior changes; map features in
   [docs/TEST_PLAN.md](docs/TEST_PLAN.md) when adding user-visible behavior.
4. Update user-facing docs (`README.md` **Key features**) as needed.
5. Verify automated checks (below).

## Development workflow

Full setup and conventions are in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).
Typical checks before opening a pull request:

```sh
make venv
make test-unittests
make test-smoketest
make style-check
```

`make style-format-black` only when you intend to reformat Python (do not invoke
`black` directly).

## AI-assisted contributions

AI-assisted contributions are permitted when used responsibly. Examples include
code, documentation, tests, refactoring, and design exploration. AI use does not
reduce contributor responsibility.

By submitting a contribution, you affirm that:

- You have reviewed the submitted content.
- You understand how the submitted content works.
- You have verified correctness to the best of your ability.
- You have considered security and maintainability implications.
- You have the legal right to contribute the submitted content.
- You are willing to answer questions about the contribution during review.

Contributions that appear to be unreviewed AI output may be rejected. See
[AI_POLICY.md](AI_POLICY.md) for project policy.

## Review expectations

All contributions are reviewed to the same standards regardless of how they were
created. Reviewers may request additional tests, documentation, refactoring,
design justification, or security analysis. Be prepared to explain your changes.

## Licensing

This project is licensed under [MIT-0](LICENSE.md) (MIT No Attribution). By
submitting a contribution, you agree your contribution is licensed under the same
terms. Do not submit third-party or vendor-owned material (for example
proprietary IP-XACT) into the public repository unless you have rights to do so.

## Quality standards

Contributions should be correct, readable, maintainable, well-tested, and
consistent with existing architecture and coding standards.

## Questions

If you are unsure whether a proposed contribution fits, open an issue or
discussion before investing significant effort.
