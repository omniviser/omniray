# Security Policy

## Supported Versions

Only the latest released version receives security updates.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email **Bartekdawidflis@gmail.com** or **info@omniviser.ai** with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will review your report and respond as soon as possible.

## Security Considerations

omniwrap applies wrappers to functions via monkey-patching at runtime. Be aware that:

- Wrappers have full access to function arguments and return values
- `log_input` / `log_output` will serialize function I/O to console — ensure secrets are stored in types that redact on serialization (e.g. Pydantic `SecretStr`)
- omniwrap should be initialized early in application startup, before untrusted code runs
