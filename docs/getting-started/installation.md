# Installation

## Requirements

- Python >= 3.12

## Install

=== "Console tracing"

    ```bash
    pip install omniray
    ```

=== "Console tracing + OpenTelemetry"

    ```bash
    pip install omniray[otel]
    ```

=== "Wrapping engine only"

    ```bash
    pip install omniwrap
    ```

omniray is built on [omniwrap](https://github.com/omniviser/omniray/tree/main/packages/omniwrap) — installing omniray installs both.

## Packages

| Package | What it does |
|---------|-------------|
| [omniray](https://pypi.org/project/omniray/) | Live tracing — console tree + OpenTelemetry |
| [omniwrap](https://pypi.org/project/omniwrap/) | Wrapping engine that omniray is built on |
