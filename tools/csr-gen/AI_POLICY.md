# AI-Assisted Development Policy

Contributor workflow and licensing: [CONTRIBUTING.md](CONTRIBUTING.md).
License terms: [LICENSE.md](LICENSE.md).

## Purpose

This document describes how artificial intelligence (AI) tools are used within this project and the standards applied to AI-generated content.

The goal is to maintain transparency while ensuring that engineering quality remains the primary criterion for inclusion in the repository.

## Philosophy

We view AI tools as engineering productivity tools, similar to:

- Compilers
- Code generators
- Static analysis tools
- IDEs
- Documentation generators
- Test generation frameworks

The quality of the final deliverable is more important than the mechanism used to create it.

## How AI Is Used

AI tools may be used for:

- Source code generation
- Documentation generation
- Unit test generation
- Integration test generation
- Refactoring assistance
- API design exploration
- Architecture brainstorming
- Example creation
- Code review assistance

AI-generated content may appear throughout the repository.

## Human Responsibility

Humans remain responsible for:

- Project architecture
- Technical direction
- Design decisions
- Security review
- Validation and testing
- Code acceptance decisions
- Release management

No AI-generated content is accepted solely because it was generated.

All content is subject to review and acceptance by project maintainers.

## Review Requirements

Generated content should be evaluated for:

### Correctness

The implementation should behave as intended and satisfy documented requirements.

### Security

The implementation should not introduce known vulnerabilities or unsafe behavior.

### Maintainability

Generated code should be understandable and maintainable by future contributors.

### Testing

Appropriate tests should accompany significant functionality.

### Documentation

Public APIs and user-facing functionality should be documented.

## Code Provenance

AI systems generate content based on patterns learned from large training datasets.

As with any software project, complete historical provenance of every individual line of code cannot be guaranteed.

The project maintainers make reasonable efforts to:

- Review generated content
- Remove obviously problematic content
- Avoid inclusion of copied third-party material
- Ensure consistency with project licensing requirements

Third-party register descriptions (for example vendor IP-XACT used only in private
integration tests) are not redistributed in this repository. Import such files in
your own environment; do not commit them unless you have distribution rights.

However, users should perform their own due diligence when evaluating the software.

## Contributor Expectations

Contributors using AI tools should:

- Understand generated content before submission
- Verify functionality
- Verify tests
- Review generated documentation
- Evaluate security implications
- Avoid submitting content they cannot explain

Submitting large volumes of unreviewed AI-generated content is discouraged.

## Transparency

This project openly acknowledges the use of AI-assisted development.

The maintainer developed most of this codebase through **vibe coding** (see
[README.md](README.md)): short, conversation-driven loops with AI assistants,
with a human author directing design, reviewing diffs, and running tests.
That workflow does not change contributor or review expectations below.

We believe transparency benefits:

- Contributors
- Users
- Organizations evaluating adoption
- Future maintainers

The presence of AI-generated content should not be interpreted as a reduction in engineering rigor.

## Disclaimer

License and warranty terms are in [LICENSE.md](LICENSE.md). AI-assisted
development may introduce defects, inaccuracies, omissions, or unintended
behaviors despite review efforts.

Users are responsible for determining whether the software is suitable for their intended use case, particularly in environments involving safety, security, financial, medical, or other high-consequence applications.

## Continuous Improvement

This policy may evolve as AI-assisted development practices, tools, and industry standards mature.

Maintainers reserve the right to update this policy as needed to reflect current best practices.
