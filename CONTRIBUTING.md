# Contributing to Tau's LinkedIn job research MCP

Tau Scout is a local LinkedIn job research MCP server for AI chat. Keep ordinary use conversational. Add research tools only with clear structured input/output, explicit unknowns, and offline tests. Avoid dependencies on Tau's private code, account infrastructure, production prompts or datasets.

For local development, create a virtual environment, install `.[dev]`, and run `python -m pytest -q`. The entry point starts stdio MCP; stdout must remain protocol-only. Build with `python -m build` before changing packaging.

Never commit tokens, `.env` files, real CVs, personal recruiter data, browser profiles or real account fixtures. Synthetic examples and `httpx.MockTransport` should cover provider behavior. Existing tests do not contact Apify or LinkedIn. Do not add a paid live test to the default suite.

Update [the tool contract](docs/tool-contract.md) whenever tool arguments or result semantics change, and coordinate companion Skills instructions. Document source-format changes with public primary evidence and a synthetic fixture. The same prepared plan must remain idempotent across concurrent calls, restarts and uncertain paid starts.

Contributions are provided under the repository's MIT license.

For public descriptions and documentation, use the [search-positioning research](docs/SEARCH_POSITIONING.md) to describe the implemented job-research workflow consistently.
