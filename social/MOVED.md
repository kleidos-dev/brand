<!--
SPDX-FileCopyrightText: 2026 José M. Requena Plens
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Moved from kleidos-dev/social

The social pack was the repository `kleidos-dev/social` from 2026-11-18 to 2026-11-24. On 2026-11-24 the owner decided that it moves here, into brand's `social/` folder: every picture of the pack is drawn from brand's files with brand's builder, which the repository read through a submodule of brand, so one repository now holds both. The repository `kleidos-dev/social` is to be deleted once every README reads its banner from here; the deletion is the owner's act, and a mirror of it, with its pull requests, reviews and comments, was kept before the move.

## How it moved

1. **The import.** The pack's files were copied byte for byte from social's `main` at `a87a5f8` (the last commit, 2026-11-24) into `social/`, and each was compared with the original by SHA-256: all 74 identical.
2. **The adaptation**, in the same pull request. The tools read brand from the folder above instead of a submodule (`tools/pack.py`); each picture's record names its address in brand (`https://github.com/kleidos-dev/brand/blob/main/social/...`), brand's `REUSE.toml` for its license and brand's `TRADEMARKS.md` for its terms (`tools/records.py`); the README banners' addresses are `https://raw.githubusercontent.com/kleidos-dev/brand/main/social/svg/readme/<repo>/banner-{dark,light}.svg` (`tools/sync_readme_banners.py`). The whole pack was then exported again with the Chromium `exports.json` records (159.0.8154.6), on the machine that exported it before: every PNG came out with the same pixels and the same image data, byte for byte, and only its metadata changed; every README banner came out with the same drawing, and only its identifier and the address of its terms changed. The kit 2.3.0 copies, the workflows and the configuration that brand already holds did not move (below).
3. **The readers.** Each README that showed a banner from `kleidos-dev/social` is changed in its own repository to read it from here (`python3 social/tools/sync_readme_banners.py --print NAME`); a block that still reads from `kleidos-dev/social` is reported as stale by `--check`.

## What moved, file by file

The SHA-256 is the file's at `a87a5f8` in `kleidos-dev/social`; the state is the file's here.

| File (under `social/`) | SHA-256 at a87a5f8 | State here |
| --- | --- | --- |
| `AGENTS.md` | `a96b73c0dbe47ad0177f3c1835452c83f133c3f0bf207eeac92e123197ccda5f` | edited for the pack's place in brand |
| `CLAUDE.md` | `032b24197c670f0fc5c71f3b1954223ae105a4408ada4d1cec0e9c8a24d45c37` | identical |
| `NOTICE.md` | `17bac40f70411e6a85c03800704929debc3b7e66916e7badd0cdd82fed1eb34d` | edited for the pack's place in brand |
| `README.md` | `32905144c9ac1be9b0bcd2d8ffe07a26e590a13df566d5c01209b21b09b8dedf` | edited for the pack's place in brand |
| `exports.json` | `d4499052a35e05a14c62329f45dcc47667faa0055958e8a4d51e86139dfbf636` | written again by the exporter: the new digests, brand's inputs named `../` |
| `pack.json` | `9ef8f2babfde82a07db9c3fb802bfb1889612e52bdacce10af26ae992f96e34f` | identical |
| `png/github/agents.png` | `e9d57e307436993cc68a2a3ecc9102bd75ef1eec2dde110371e0259daed46fab` | pixels and image data identical; metadata names brand |
| `png/github/boards.png` | `fd58f41f2b6b8627d9d1a66c0a97453d7ee1d056140a120ac2a0a7fcb555dd9e` | pixels and image data identical; metadata names brand |
| `png/github/brand.png` | `8878057b48fe00655dc32f7e0f61f0889ea549b21e6a6b1be719f38db4166c62` | pixels and image data identical; metadata names brand |
| `png/github/dot-github.png` | `d79ef02fde4a68a301c68d051aa7dbf1109f7a1eb1dfe0921e2ee987553fa33e` | pixels and image data identical; metadata names brand |
| `png/github/kleidos.png` | `88bed9cc5f3d7237a1b68a4a35544da94f0a3d4cf524bebc3fd94af2aaa1df5f` | pixels and image data identical; metadata names brand |
| `png/github/social.png` | `dcb71c0d505b052a537d0ab7d6bc5b0a8b90954ff6ed28ade15ae57b704bff62` | pixels and image data identical; metadata names brand |
| `png/makertube/avatar.png` | `4829b385d03cf3ff923778f79f38972c1cc280909401c9135ebcf1e9e999e7e1` | pixels and image data identical; metadata names brand |
| `png/makertube/banner.png` | `8e89a4de63f08b184da9612286787750cccd3135181ccd3ad542b257dbfdc474` | pixels and image data identical; metadata names brand |
| `png/youtube/avatar.png` | `2c12587814bcffbd85f1041fa76768c1093aab7a1e5db05bb0fee55609f8ccc9` | pixels and image data identical; metadata names brand |
| `png/youtube/banner.png` | `2256dd7311063be6ebf9b5b6f9f88583f1e5d9ba5b43c9aa71afb5b63fd66e0f` | pixels and image data identical; metadata names brand |
| `png/youtube/thumbnail.png` | `6ebe5a2954947880ee4a9162b37c262d0d6a0fb587fbe49b1cfef980ce4149b7` | pixels and image data identical; metadata names brand |
| `png/youtube/watermark.png` | `816f22582895e9d5a0ff7130b6322e12d59940d3aa4edea1bd07c586eaac838e` | pixels and image data identical; metadata names brand |
| `previews/avatars.png` | `c12e00a0a402940dcd1d0e3496bc066113f942645f473c9582e1f2aaa0bebf10` | pixels and image data identical; metadata names brand |
| `previews/cards.png` | `79fb51949aa9de70a211755b05d323b52944764ef58f093343ddbea5f5e61ee3` | pixels and image data identical; metadata names brand |
| `previews/contact-sheet.png` | `e835846e299aa87e239ce07f912ec623607813b1b1307e9c1bfdb4884c94e2cc` | pixels and image data identical; metadata names brand |
| `previews/makertube-banner.png` | `dded6546690d02eff66e99d4109d6994e9b688d89d843cee9a48059bc6f61cf1` | pixels and image data identical; metadata names brand |
| `previews/readme-banners.png` | `2b47a240f327e8e39d619cbcb2de9f87a019b0aa8e9c22e1097f7903973d31ba` | pixels and image data identical; metadata names brand |
| `previews/youtube-banner.png` | `ca5c05e92478cef03eae56e9642b19d3108697a1ce03277ff6108a903f3a4ea7` | pixels and image data identical; metadata names brand |
| `src/cards/card.svg` | `82b844499ea0d280ef75cdb6a44d6a63c5227c47913534172a054e604c4362dd` | identical |
| `src/cards/motifs/bubbles.svg` | `2f77451df71d2216a3b77cd6bee491e99263bc55e9c0f254d9e23bce549cff51` | identical |
| `src/cards/motifs/checklist.svg` | `4d7d9faa07f829ce86f07d44161b52552225a309ff0a9df3bba8350dae3ecdea` | identical |
| `src/cards/motifs/frames.svg` | `b940985110af1a82b3a6b68d0c817623cc9d676153bd20bf957bd2a03d2cc617` | identical |
| `src/cards/motifs/gauge.svg` | `987812788c384f77049d0c32912ca5e41d2b07e6130ca7ae766d38cfbdf1817d` | identical |
| `src/cards/motifs/reel.svg` | `59f319b7bf65387e1367cb2588d9e61eea722273180d979ef1a0264b325fb16a` | identical |
| `src/cards/motifs/sheets.svg` | `e88bbcea03bde1121296fb7a595c8309385e4c6cd75346cdf2f89fef97e6d00c` | identical |
| `src/cards/motifs/shelf.svg` | `9585a2e2bc6291e2899c8c700e482b576af4175acbe3edf1d70a02d6c06efe80` | identical |
| `src/cards/motifs/swatches.svg` | `0128cfe40dfb6352e72ce716f86f0042477314036da30a4c3e86942e2f9f29f5` | identical |
| `src/cards/motifs/typing.svg` | `616376e22a7952620e60cf242acaf9d1fb2e5d6e61277739fd88933a30c476dc` | identical |
| `src/makertube/banner.svg` | `4cd50a87019e5edd1b07105c7cb322917b7f86bca08b0bc1882d921278a53961` | identical |
| `src/readme/banner.svg` | `fb1a9b6795d1064c5f75df88d0e476a0e58171883110dda6bdd5fb5ae733710b` | identical |
| `src/shared/avatar.svg` | `cb0373e11dca30d7c8f8df952103586034c12da381a9dd68d27861b451bd062c` | identical |
| `src/youtube/banner.svg` | `2d4c7bad81dee55cc32b61fea7d673bb8a979085b5ab9704daae491326ac80a9` | identical |
| `src/youtube/thumbnail.svg` | `01ecd7b8881cadcf3cb9b39fa5e5244bb74a50a17b31098855ee3ad839c8a987` | identical |
| `src/youtube/watermark.svg` | `bf7e3b5dda8b64d6e5e3f6392ed1227790cc4dbf1b068b97f2f20552375f96f3` | identical |
| `svg/readme/agents/banner-dark.svg` | `0a3a7dec93681d46f1512761309edd9c7190cf3dfbe9710b1fb264789445c3a2` | drawing identical; identifier and terms address name brand |
| `svg/readme/agents/banner-light.svg` | `0336e5ce18eff5260159cec93c02fd18325c7a5cbe6eaf213eba220b177393ef` | drawing identical; identifier and terms address name brand |
| `svg/readme/boards/banner-dark.svg` | `155fd17f6114010e94ee54704b49694ecc51616b815a423a8762b2e386b5b627` | drawing identical; identifier and terms address name brand |
| `svg/readme/boards/banner-light.svg` | `c4aabcad45ce65ca9258686e3a3c37e7793859a9ee45464f9578a920847c638b` | drawing identical; identifier and terms address name brand |
| `svg/readme/brand/banner-dark.svg` | `385f75de2c06bd75b7504ae7c61bed95828659a4bdea8441dc4119dd59519d3d` | drawing identical; identifier and terms address name brand |
| `svg/readme/brand/banner-light.svg` | `ab0e8e80907317fcc4a52e54b17d86aa3b9ea322c1a330f84e7c21bf7920a633` | drawing identical; identifier and terms address name brand |
| `svg/readme/dot-github/banner-dark.svg` | `008b1149b498fad468d590266d19c814b25ff614bf59d640201c514876ba2ab4` | drawing identical; identifier and terms address name brand |
| `svg/readme/dot-github/banner-light.svg` | `5a8066ac0b7768dd72b5c6c3dba57fff2380b0775c2b7939747b66a5806da48c` | drawing identical; identifier and terms address name brand |
| `svg/readme/kleidos/banner-dark.svg` | `ce600c0874eccb5a2334711b2aef6588c214382226bf9e7f42638d49befc7a2a` | drawing identical; identifier and terms address name brand |
| `svg/readme/kleidos/banner-light.svg` | `464ec83b033a470c92c95d1ab2872550e3bc4bb63b6ea6953603692e9ca372fa` | drawing identical; identifier and terms address name brand |
| `svg/readme/meter/banner-dark.svg` | `97cc420ab2f76ab0df64caa29b5bbe01808979cfdfc7325e2459e0c658c6691e` | drawing identical; identifier and terms address name brand |
| `svg/readme/meter/banner-light.svg` | `4973b35fdf5ad06263a07fc83ed1800bce07f1a525139d24877172a0efe4369f` | drawing identical; identifier and terms address name brand |
| `svg/readme/posts/banner-dark.svg` | `bff4ddda1c56b4ec0f209301d6935aaa443fed6a01f28b73764822d37c10ca24` | drawing identical; identifier and terms address name brand |
| `svg/readme/posts/banner-light.svg` | `2a0d581e1fd684ab417c521212c5b6e15381d6344b6dfae729bdb6aa5ce2598e` | drawing identical; identifier and terms address name brand |
| `svg/readme/social/banner-dark.svg` | `ab4d2e3ac579a5aed675f9d83f974d1a62f316d7e4f55b943e52a15751c12b47` | drawing identical; identifier and terms address name brand |
| `svg/readme/social/banner-light.svg` | `0e66b6baf8a7c3d547733c4f4488f06a5f726b48ce54869f17ed25b5483d03d6` | drawing identical; identifier and terms address name brand |
| `svg/readme/videos/banner-dark.svg` | `82f071e49b31119b169066a4cc03870a0a5c67635129f74a5f906005719c8f99` | drawing identical; identifier and terms address name brand |
| `svg/readme/videos/banner-light.svg` | `d42eb8a7d8c1477caa19bd6726859dcfee26d7b59475f11a455fe34889c2e672` | drawing identical; identifier and terms address name brand |
| `tests/conftest.py` | `03c70aa175813de6d456cb2a0aac85eb63550b4d4d8de69d7e5931dab41cda25` | edited for the pack's place in brand |
| `tests/test_cards.py` | `567a0cde9a2b5dcaf7fdf77f033952b3a10ebc98b90ade81e07d8f3ad1cdbfe5` | identical |
| `tests/test_checks.py` | `aefe8615ce2f3cdd6e4296d3c5cd523d09468370c89aa0a783d0531bfbc4d260` | edited for the pack's place in brand |
| `tests/test_pictures.py` | `34bd8e1826cbbcd6d65b143d4f377decd3973c00ec4fc047f50a595fc5554be8` | edited for the pack's place in brand |
| `tests/test_previews.py` | `2111bb5cb39ce9e2db5ce905573fc570b596a6ac991a66815977ebdfcdcce5ea` | identical |
| `tests/test_readme_banners.py` | `c3378b74c3d6dbf8e9b4b668c590c09f705b81d5139e55205d344ce64bc38d89` | edited for the pack's place in brand |
| `tools/cards.py` | `f3be6d10f819649de7edf329cb9b3330c1db2a316d34a74d271690ae5898cca0` | identical |
| `tools/check.py` | `18b7797fa315f94b0bc2d8ee648cdfcad4e9b2fba4b00d9ac9e7e6efa8a5cdeb` | edited for the pack's place in brand |
| `tools/check_metadata.py` | `4b1f8da7a09da2dec7bf3fbfa8e5150e492abf8e76c808eb310af95e676150bc` | edited for the pack's place in brand |
| `tools/export.py` | `281f05dc255cf6a4aa3a5f5950ad5e249527b7735b54794598d33ce7b9cbe447` | edited for the pack's place in brand |
| `tools/pack.py` | `c582ea113838053b2e811b5164bbdb6058ae097943978d242201e87fd03d6698` | edited for the pack's place in brand |
| `tools/previews.py` | `a054c0b32fa0d8bde70de146d0474f90d01667057c6b84d5ed38c26e80e13300` | identical |
| `tools/readme_banners.py` | `61e96024bda39b108dd47c5f1c1d220b4cf3c9df4b09300cdf235c224f19b6c6` | edited for the pack's place in brand |
| `tools/records.py` | `5fd1f426aef07983968a7badca474f17d85b242ae2ad921f97a82c8bdad6f28b` | edited for the pack's place in brand |
| `tools/source.py` | `48f1b6f53f2303f15ecafffa66fde3cb8eac5cb13814dfbff49073e7b232cabe` | edited for the pack's place in brand |
| `tools/sync_readme_banners.py` | `e759a302421ed267955a5a202605da75743bc8280498a88d1a4f2ae182f6cdb4` | edited for the pack's place in brand |

In all: 22 identical; 18 pixels and image data identical; metadata names brand; 18 drawing identical; identifier and terms address name brand; 15 edited for the pack's place in brand; 1 written again by the exporter: the new digests, brand's inputs named `../`.

## What did not move, and why

| File of `kleidos-dev/social` | Why it is not here |
| --- | --- |
| `.coderabbit.yaml` | merged into brand's: the generated paths of the pack left out of the review and a rule for `social/**` |
| `.coveragerc` | merged into brand's: `social/tools` is a coverage source |
| `.editorconfig` | brand's own applies |
| `.git-blame-ignore-revs` | named a commit of social's history, which did not move |
| `.github/CODEOWNERS` | brand's applies |
| `.github/commit-check/check_commit_msg.py` | kit 2.x copy; kit 3 runs it from the kit |
| `.github/dependabot.yml` | brand's covers the same ecosystems; the pack has no manifest of its own |
| `.github/quality/SOURCE.json` | a kit 2.3.0 copy or block; kit 3 runs by name and holds none (brand keeps its own base configurations) |
| `.github/quality/agent_docs.py` | a kit 2.3.0 copy or block; kit 3 runs by name and holds none (brand keeps its own base configurations) |
| `.github/quality/check_quality.py` | a kit 2.3.0 copy or block; kit 3 runs by name and holds none (brand keeps its own base configurations) |
| `.github/quality/markdownlint.jsonc` | a kit 2.3.0 copy or block; kit 3 runs by name and holds none (brand keeps its own base configurations) |
| `.github/quality/md_nowrap.py` | a kit 2.3.0 copy or block; kit 3 runs by name and holds none (brand keeps its own base configurations) |
| `.github/quality/mypy_groups.py` | a kit 2.3.0 copy or block; kit 3 runs by name and holds none (brand keeps its own base configurations) |
| `.github/quality/ruff.toml` | a kit 2.3.0 copy or block; kit 3 runs by name and holds none (brand keeps its own base configurations) |
| `.github/quality/spdx_headers.py` | a kit 2.3.0 copy or block; kit 3 runs by name and holds none (brand keeps its own base configurations) |
| `.github/quality/waivers.toml` | a kit 2.3.0 copy or block; kit 3 runs by name and holds none (brand keeps its own base configurations) |
| `.github/workflows/check.yml` | brand's CI runs the pack (the tree job, the tests, the tolerant check, mypy, SonarQube Cloud) |
| `.github/workflows/commit-check-comment.yml` | brand's own caller applies |
| `.github/workflows/commit-check.yml` | kit 2.3.0's caller; brand runs the kit 3 commit check |
| `.github/workflows/quality-drift.yml` | kit 2.x only; kit 3 has no drift job in the repositories |
| `.github/zizmor.yml` | a kit base configuration; brand holds its own at kit 3 |
| `.gitignore` | brand's ignores the same, and `/social/dist/` for the one-off thumbnails |
| `.gitleaks-mac.toml` | a kit base configuration, the same file as brand's (same SHA-256) |
| `.gitleaks.toml` | brand's applies; its allowlist covers the digests of `social/exports.json` |
| `.gitmodules` | the brand submodule is gone: the pack reads brand from its parent folder |
| `.greptile/config.json` | merged into brand's: the same, and `social/AGENTS.md` among the files it reads |
| `.greptile/files.json` | merged into brand's |
| `.markdownlint-cli2.jsonc` | the same file as brand's (same SHA-256) |
| `.markdownlint.json` | brand's applies (the kit's configuration through `.markdownlint-cli2.jsonc`) |
| `.pre-commit-config.yaml` | brand's runs the same hooks at kit 3; the pack's check is brand's `social-check` hook |
| `.python-version` | the same as brand's (3.15) |
| `.typos.toml` | merged into brand's: the `PNGs` exception |
| `LICENSE` | a byte copy of brand's `LICENSE` (same SHA-256) |
| `LICENSES/GPL-3.0-or-later.txt` | a byte copy of brand's (same SHA-256) |
| `LICENSES/MIT.txt` | brand's holds the same text; social's copyright line still carried an e-mail address, which brand's does not |
| `REUSE.toml` | merged into brand's `REUSE.toml`: the pack's artwork and data under the GPL catch-all and the SVG/JSON line, `social/tools/**` and `social/tests/**` under MIT |
| `TRADEMARKS.md` | a byte copy of brand's `TRADEMARKS.md` (same SHA-256), which now covers the pack |
| `brand` | the submodule itself (social pinned brand at ef0d4c5) |
| `pyproject.toml` | merged into brand's: ruff's first-party modules, and mypy as a group of its own (`social`) |
| `requirements.txt` | every pin it held (coverage, pytest-cov, pyyaml) is in brand's `requirements.txt` at the same version and hashes, and the rest it took from brand's |
| `sonar-project.properties` | merged into brand's: `social/tools` and `social/tests` are code and test roots of brand's SonarQube Cloud project |
| `tests/test_quality_kit.py` | kit 2.x drift test; kit 3 holds no copies to test |

## The history of kleidos-dev/social

20 commits on `main` from 2026-11-18 to 2026-11-24, 17 pull requests (all closed, 16 merged), no issue, no tag and no release. The history did not move: the import is one commit here.

| Commit | Date | Subject |
| --- | --- | --- |
| `e1e6a5f` | 2026-11-18 | Publish the profile images and repository cards |
| `072449b` | 2026-11-18 | Move brand to its latest release stack (#1) |
| `bfdbb09` | 2026-11-19 | Embed brand's metadata profile in every picture (#2) |
| `1bda087` | 2026-11-19 | Move brand to its WebP and opaque renditions (#3) |
| `05b7972` | 2026-11-19 | Add a README banner for every repository (#4) |
| `459dd15` | 2026-11-20 | Serve README banners from social and set each name once (#5) |
| `3906739` | 2026-11-20 | Run the cheap checks first and name the CI job (#6) |
| `4d13e1f` | 2026-11-22 | Configure the review bots and the SonarCloud job |
| `182de4a` | 2026-11-22 | Analyse with SonarCloud without a stored token |
| `f99d35a` | 2026-11-23 | Format the Python with ruff format (#7) |
| `6204fd2` | 2026-11-23 | Ask the maintainers team to review every pull request |
| `e9104bc` | 2026-11-23 | Adopt the quality kit and run every check from it (#8) |
| `0361b9c` | 2026-11-23 | Sync the quality kit to quality-v1.1.0 (#9) |
| `02a1666` | 2026-11-23 | Take quality kit 2.0.0 and brand's newest commit (#10) |
| `5b9f130` | 2026-11-23 | Bring the agent files to the organization standard (#11) |
| `7d0e7fe` | 2026-11-23 | Move the brand submodule to brand's main (b28ef5b) (#12) |
| `df84133` | 2026-11-23 | Pin social's own Python pins with hashes, brand's at dee16c7 (#13) |
| `841abfa` | 2026-11-23 | Take quality kit 2.2.0 (#15) |
| `911509d` | 2026-11-23 | Take quality kit 2.3.0 (#16) |
| `a87a5f8` | 2026-11-24 | Write a one-off thumbnail under dist/ only (#17) |

| Pull request of kleidos-dev/social | Merged | Title |
| --- | --- | --- |
| 1 | 2026-11-18 | Move brand to its latest release stack |
| 2 | 2026-11-19 | Embed brand's metadata profile in every picture |
| 3 | 2026-11-19 | Move brand to its WebP and opaque renditions |
| 4 | 2026-11-19 | Add a README banner for every repository |
| 5 | 2026-11-20 | Serve README banners from social and set each name once |
| 6 | 2026-11-20 | Run the cheap checks first and name the CI job |
| 7 | 2026-11-23 | Format the Python with ruff format |
| 8 | 2026-11-23 | Adopt the quality kit and run every check from it |
| 9 | 2026-11-23 | Sync the quality kit to quality-v1.1.0 |
| 10 | 2026-11-23 | Take quality kit 2.0.0 and brand's newest commit |
| 11 | 2026-11-23 | Bring the agent files to the organization standard |
| 12 | 2026-11-23 | Move the brand submodule to brand's main (b28ef5b) |
| 13 | 2026-11-23 | Pin social's own Python pins with hashes, brand's at dee16c7 |
| 14 | not merged | Move the brand submodule to brand's main (8798fb5) |
| 15 | 2026-11-23 | Take quality kit 2.2.0 |
| 16 | 2026-11-23 | Take quality kit 2.3.0 |
| 17 | 2026-11-24 | Fix the analyzer's open finding |
