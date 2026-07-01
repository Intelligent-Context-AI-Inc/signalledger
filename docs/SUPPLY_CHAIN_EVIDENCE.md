# Supply Chain Evidence

ECL Trainer can generate a local, metadata-only supply-chain evidence bundle for the SDK, Docker Action, and Intelligent Context Atlas seed manifests.

```bash
ecl-trainer supply-chain-evidence \
  --repository-root . \
  --output-dir .ecl-trainer/supply-chain
```

The command writes:

- `supply-chain-sbom.json`
- `supply-chain-provenance.json`
- `supply-chain-manifest.json`

The bundle contains relative file paths, file sizes, SHA-256 hashes, base image metadata, Atlas seed manifest hashes, and local-only provenance flags. The manifest reports output filenames rather than local absolute paths. It does not include file contents, raw datasets, raw diffs, prompts, token sequences, embeddings, model weights, secrets, or local absolute paths.

The evidence bundle is validated with `NoPayloadValidator` before it is written.
