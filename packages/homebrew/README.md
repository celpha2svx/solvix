# Homebrew Distribution

Solvix uses the same GitHub Release binaries for Homebrew, npm, and the curl installer.

This package directory does not publish directly to Homebrew by itself. Instead:

1. release binaries are built and uploaded by GitHub Actions
2. a Homebrew formula is generated from the release assets
3. that formula is copied into a tap repository such as `celpha2svx/homebrew-solvix`

The generated formula is emitted as a release asset named `solvix.rb`.

Recommended install path for users:

```bash
brew tap celpha2svx/solvix
brew install solvix
```
