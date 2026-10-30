# Contributing

This repository is a template, so changes should keep it small, generic, and
copyable.

## Before you start

1. Run `./init.sh` and confirm the baseline is green.
2. If the change affects behavior or structure, create an OpenSpec change:

   ```text
   /opsx-propose <change-name>
   ```

3. Add the matching feature to `feature_list.json` with status `in_progress`
   and the change name.
4. Keep exactly one active feature and one active change.

## Pull requests

- Explain the problem and the smallest change that fixes it.
- Update the docs and the feature list.
- Run `./init.sh` and paste the result in the PR description.
- Do not add application-specific code to the template.
- Do not weaken a verification check to make CI pass.

## Reporting issues

Open a GitHub issue with:

- what you expected;
- what happened;
- the output of `./init.sh`;
- the output of `node scripts/validate-harness.mjs`.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
