import contextlib
import io
import json
import sys
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.check_docs import (
    ConfigError,
    check_classification,
    check_command_contracts,
    check_environment_document,
    check_local_links,
    check_metadata,
    check_runtime_contract,
    check_workflow_inventory,
    discover_environment_names,
    github_slug,
    load_config,
    main as check_docs_main,
    stamp_documents,
)


class DocumentationChecks(TestCase):
    @staticmethod
    def track(root: Path, *relative_paths: str) -> None:
        if not (root / ".git").exists():
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "add", "--", *relative_paths],
            cwd=root,
            check=True,
        )

    def test_missing_local_link_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text("[missing](docs/missing.md)\n", encoding="utf-8")
            errors = check_local_links(root, [page])
            self.assertTrue(any("docs/missing.md" in item.message for item in errors))

    def test_external_link_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text("[site](https://example.com/path)\n", encoding="utf-8")
            self.assertEqual(check_local_links(root, [page]), [])

    def test_link_inside_fenced_code_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text("```markdown\n[example](missing.md)\n```\n", encoding="utf-8")
            self.assertEqual(check_local_links(root, [page]), [])

    def test_link_inside_four_backtick_fence_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "````markdown\n```bash\n[example](missing.md)\n```\n````\n",
                encoding="utf-8",
            )
            self.assertEqual(check_local_links(root, [page]), [])

    def test_link_inside_indented_list_fence_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "1. Example\n   ```markdown\n   [example](missing.md)\n   ```\n",
                encoding="utf-8",
            )
            self.assertEqual(check_local_links(root, [page]), [])

    def test_link_inside_deeply_nested_list_fence_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "1. Example\n     ```markdown\n     [example](missing.md)\n     ```\n",
                encoding="utf-8",
            )
            self.assertEqual(check_local_links(root, [page]), [])

    def test_four_space_indented_backticks_do_not_open_a_fence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "    ```\n[outside](missing.md)\n",
                encoding="utf-8",
            )
            errors = check_local_links(root, [page])
            self.assertTrue(any("missing.md" in item.message for item in errors))

    def test_indented_code_list_marker_does_not_create_list_context(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "    - code, not a list\n      ```\n[outside](missing.md)\n",
                encoding="utf-8",
            )
            errors = check_local_links(root, [page])
            self.assertTrue(any("missing.md" in item.message for item in errors))

    def test_two_blank_lines_end_inferred_list_context(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "1. Example\n\n\n    ```\n[outside](missing.md)\n",
                encoding="utf-8",
            )
            errors = check_local_links(root, [page])
            self.assertTrue(any("missing.md" in item.message for item in errors))

    def test_backtick_in_backtick_fence_info_does_not_open_a_fence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "```bad`info\n[outside](missing.md)\n```\n",
                encoding="utf-8",
            )
            errors = check_local_links(root, [page])
            self.assertTrue(any("missing.md" in item.message for item in errors))

    def test_longer_fence_closes_the_code_block(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "```markdown\n[inside](ignored.md)\n````\n[outside](missing.md)\n",
                encoding="utf-8",
            )
            errors = check_local_links(root, [page])
            self.assertTrue(any("missing.md" in item.message for item in errors))

    def test_missing_heading_fragment_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            target = root / "guide.md"
            page.write_text("[section](guide.md#absent)\n", encoding="utf-8")
            target.write_text("# Present\n", encoding="utf-8")
            errors = check_local_links(root, [page, target])
            self.assertTrue(any("#absent" in item.message for item in errors))

    def test_heading_inside_fenced_code_is_not_an_anchor(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            target = root / "guide.md"
            page.write_text("[fake](guide.md#fake)\n", encoding="utf-8")
            target.write_text("```markdown\n# Fake\n```\n# Real\n", encoding="utf-8")
            errors = check_local_links(root, [page, target])
            self.assertTrue(any("#fake" in item.message for item in errors))

    def test_inline_code_text_is_preserved_in_heading_anchor(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            target = root / "guide.md"
            page.write_text(
                "[role](guide.md#1-residual-analyst--残差)\n", encoding="utf-8"
            )
            target.write_text(
                "## 1. `residual-analyst` — 残差\n", encoding="utf-8"
            )
            self.assertEqual(check_local_links(root, [page, target]), [])

    def test_maintained_document_requires_all_metadata(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text("# Project\n\n> **Status:** Current\n", encoding="utf-8")
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertEqual({item.code for item in errors}, {"missing-scope", "missing-verified-commit"})

    def test_metadata_requires_an_h1_as_the_first_nonblank_line(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "Project\n\n> **Status:** Current\n> **Scope:** Test.\n"
                f"> **Last verified commit:** `{'1' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(any(item.code == "invalid-title" for item in errors))

    def test_metadata_requires_canonical_header_order(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Scope:** Test.\n> **Status:** Current\n"
                f"> **Last verified commit:** `{'1' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(any(item.code == "invalid-metadata-order" for item in errors))

    def test_verified_commit_must_immediately_follow_scope(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current\n> **Scope:** Test.\n"
                "Intervening prose.\n"
                f"> **Last verified commit:** `{'1' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(any(item.code == "invalid-metadata-order" for item in errors))

    def test_stamping_uses_exact_git_sha_argument(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current\n> **Scope:** Test repository.\n",
                encoding="utf-8",
            )
            sha = "1" * 40
            stamp_documents(root, ["README.md"], sha)
            self.assertIn(f"> **Last verified commit:** `{sha}`", page.read_text(encoding="utf-8"))

    def test_stamping_ignores_fenced_and_body_metadata_decoys(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            sha = "1" * 40
            fenced_sha = "2" * 40
            body_sha = "3" * 40
            original = (
                "# Project\n\n"
                "> **Status:** Current\n"
                "> **Scope:** Test repository.\n\n"
                "```markdown\n"
                f"> **Last verified commit:** `{fenced_sha}`\n"
                "```\n\n"
                "Body metadata example:\n"
                f"> **Last verified commit:** `{body_sha}`\n"
            )
            expected = (
                "# Project\n\n"
                "> **Status:** Current\n"
                "> **Scope:** Test repository.\n"
                f"> **Last verified commit:** `{sha}`\n\n"
                "```markdown\n"
                f"> **Last verified commit:** `{fenced_sha}`\n"
                "```\n\n"
                "Body metadata example:\n"
                f"> **Last verified commit:** `{body_sha}`\n"
            )
            page.write_text(original, encoding="utf-8")

            stamp_documents(root, ["README.md"], sha)

            self.assertEqual(page.read_text(encoding="utf-8"), expected)

    def test_stamping_preserves_crlf_bytes_outside_the_header_sha(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            sha = "1" * 40
            old_sha = "2" * 40
            fenced_sha = "3" * 40
            body_sha = "4" * 40
            original = (
                b"# Project\r\n"
                b"\r\n"
                b"> **Status:** Current\r\n"
                b"> **Scope:** Test repository.\r\n"
                + f"> **Last verified commit:** `{old_sha}`\r\n".encode()
                + b"\r\n"
                + b"```markdown\r\n"
                + f"> **Last verified commit:** `{fenced_sha}`\r\n".encode()
                + b"```\r\n"
                + b"\r\n"
                + f"Body decoy `{body_sha}` remains byte-identical.\r\n".encode()
            )
            expected = original.replace(
                old_sha.encode(),
                sha.encode(),
                1,
            )
            self.assertEqual(original.count(b"\r\n"), 11)
            page.write_bytes(original)

            stamp_documents(root, ["README.md"], sha)

            self.assertEqual(page.read_bytes(), expected)

    def test_stamping_rejects_scope_on_the_twelfth_header_line(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            original = (
                "# Project\n\n"
                "> **Status:** Current\n"
                + "\n" * 8
                + "> **Scope:** Too late to stamp safely.\n"
                "Body remains unchanged.\n"
            ).encode()
            page.write_bytes(original)

            with self.assertRaisesRegex(ValueError, "first 12 lines"):
                stamp_documents(root, ["README.md"], "1" * 40)

            self.assertEqual(page.read_bytes(), original)

    def test_metadata_sha_must_resolve_to_an_ancestor_commit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current\n> **Scope:** Test.\n"
                f"> **Last verified commit:** `{'f' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(
                any(item.code == "unresolvable-verified-commit" for item in errors)
            )

    def test_existing_non_ancestor_commit_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Docs Test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "docs@example.test"], cwd=root, check=True)
            (root / "seed.txt").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "add", "seed.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=root, check=True)
            tree = subprocess.run(
                ["git", "rev-parse", "HEAD^{tree}"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            unrelated = subprocess.run(
                ["git", "commit-tree", tree],
                cwd=root,
                check=True,
                input="unrelated\n",
                capture_output=True,
                text=True,
            ).stdout.strip()
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current\n> **Scope:** Test.\n"
                f"> **Last verified commit:** `{unrelated}`\n",
                encoding="utf-8",
            )

            errors = check_metadata(root, ["README.md"], [], [])

            self.assertTrue(
                any(item.code == "unresolvable-verified-commit" for item in errors)
            )

    def test_metadata_must_be_in_document_header(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n" + "\n" * 15
                + "> **Status:** Current\n> **Scope:** Late.\n"
                + f"> **Last verified commit:** `{'1' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(any(item.code == "metadata-not-in-header" for item in errors))

    def test_metadata_example_inside_fence_is_not_late_metadata(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current\n> **Scope:** Test.\n"
                f"> **Last verified commit:** `{'1' * 40}`\n"
                + "context\n" * 10
                + "```markdown\n> **Status:** Current\n> **Scope:** Example.\n```\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertFalse(any(item.code == "metadata-not-in-header" for item in errors))

    def test_maintained_status_must_be_an_exact_allowed_header_value(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current-ish\n> **Scope:** Test.\n"
                f"> **Last verified commit:** `{'1' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(any(item.code == "invalid-status" for item in errors))

    def test_historical_and_archived_words_in_body_do_not_count_as_metadata(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            historical = root / "historical.md"
            archived = root / "archived.md"
            historical.write_text(
                "# Old study\n\nThis body discusses Historical results.\n",
                encoding="utf-8",
            )
            archived.write_text(
                "# Old plan\n\nThis body says it was Archived.\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, [], ["historical.md"], ["archived.md"])
            self.assertTrue(any(item.code == "missing-historical-status" for item in errors))
            self.assertTrue(any(item.code == "missing-archived-status" for item in errors))

    def test_conflicting_historical_status_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "historical.md"
            page.write_text(
                "# Study\n\n"
                "> **Status:** Historical research snapshot; not maintained\n"
                "> **Status:** Current\n"
                "> **Scope:** Test.\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, [], ["historical.md"], [])
            self.assertTrue(any(item.code == "missing-historical-status" for item in errors))

    def test_unknown_environment_name_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = root / "docs" / "configuration.md"
            doc.parent.mkdir()
            doc.write_text("# Configuration\n\n`KNOWN_NAME`\n", encoding="utf-8")
            errors = check_environment_document(root, {"KNOWN_NAME", "MISSING_NAME"}, "docs/configuration.md")
            self.assertTrue(any("MISSING_NAME" in item.message for item in errors))

    def test_indirect_and_yaml_environment_names_are_discovered(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "feed_publication.py").write_text(
                'MANIFEST_ENV = "FEED_PUBLICATION_MANIFEST"\n'
                'value = os.environ.get(MANIFEST_ENV)\n',
                encoding="utf-8",
            )
            (scripts / "run-python311").write_text(
                "docker run --env HOME=/tmp/home python:3.11.15 python\n",
                encoding="utf-8",
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "feed.yaml").write_text(
                "jobs:\n  test:\n    env:\n      PAYLOAD: value\n",
                encoding="utf-8",
            )
            (root / "backend").mkdir()
            (root / "backend" / "Dockerfile").write_text(
                "ENV PORT=8000\n", encoding="utf-8"
            )
            (root / "render.yaml").write_text(
                "services:\n  - envVars:\n      - key: PYTHON_VERSION\n"
                "        value: '3.11.15'\n",
                encoding="utf-8",
            )
            frontend_scripts = root / "frontend" / "scripts"
            frontend_scripts.mkdir(parents=True)
            (frontend_scripts / "smoke-server.mjs").write_text(
                'spawn("node", [], {env: {...process.env, NODE_ENV: "production"}})\n',
                encoding="utf-8",
            )
            self.track(root, ".github/workflows/feed.yaml")
            names = discover_environment_names(root, [])
            self.assertTrue(
                {
                    "FEED_PUBLICATION_MANIFEST",
                    "PAYLOAD",
                    "PORT",
                    "PYTHON_VERSION",
                    "HOME",
                    "NODE_ENV",
                }
                <= names
            )

    def test_workflow_shell_environment_names_are_discovered(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "docs.yml").write_text(
                "jobs:\n  docs:\n    steps:\n      - run: |\n"
                "          echo ok >> \"$GITHUB_OUTPUT\"\n"
                "          cd \"${GITHUB_WORKSPACE}\"\n"
                "          test -d \"$RUNNER_TEMP\"\n"
                "          LOCAL_ONLY=value\n"
                "          echo \"$LOCAL_ONLY\"\n"
                "          THRESH=\"${{ github.event.inputs.threshold }}\"\n"
                "          EXIST=$(gh issue list --limit 1)\n"
                "          PYTHONPATH=. \\\n"
                "            python scripts/check_docs.py\n",
                encoding="utf-8",
            )
            self.track(root, ".github/workflows/docs.yml")
            names = discover_environment_names(root, [])
            self.assertTrue(
                {"GITHUB_OUTPUT", "GITHUB_WORKSPACE", "RUNNER_TEMP", "PYTHONPATH"}
                <= names
            )
            self.assertTrue({"LOCAL_ONLY", "THRESH", "EXIST"}.isdisjoint(names))

    def test_missing_npm_script_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "frontend" / "package.json").write_text('{"scripts":{"lint":"eslint ."}}', encoding="utf-8")
            page = root / "README.md"
            page.write_text("```bash\nnpm run build:static\n```\n", encoding="utf-8")
            contracts = [{"document": "README.md", "cwd": "frontend", "command": "npm run build:static", "kind": "entrypoint", "runtime": "node"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any("build:static" in item.message for item in errors))

    def test_ci_command_missing_from_workflows_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "frontend" / "package.json").write_text('{"scripts":{"lint":"eslint ."}}', encoding="utf-8")
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "name: Tests\njobs:\n  frontend:\n    steps: []\n",
                encoding="utf-8",
            )
            page = root / "README.md"
            page.write_text("```bash\nnpm run lint\n```\n", encoding="utf-8")
            contracts = [{"document": "README.md", "cwd": "frontend", "command": "npm run lint", "kind": "ci", "runtime": "node", "workflow": ".github/workflows/tests.yml", "job": "frontend"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any(item.code == "command-not-in-ci" for item in errors))

    def test_ci_command_in_wrong_workflow_is_not_accepted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "frontend" / "package.json").write_text(
                '{"scripts":{"lint":"next lint"}}', encoding="utf-8"
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "jobs:\n  frontend:\n    steps: []\n", encoding="utf-8"
            )
            (workflows / "deploy.yml").write_text(
                "jobs:\n  deploy:\n    steps:\n      - run: npm run lint\n", encoding="utf-8"
            )
            page = root / "README.md"
            page.write_text("\nnpm run lint\n", encoding="utf-8")
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any(item.code == "command-not-in-ci" for item in errors))

    def test_ci_command_in_comment_or_step_name_is_not_accepted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "frontend" / "package.json").write_text(
                '{"scripts":{"lint":"next lint"}}', encoding="utf-8"
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "jobs:\n  frontend:\n    steps:\n"
                "      - name: npm run lint\n"
                "        run: |\n          # npm run lint\n          echo skipped\n",
                encoding="utf-8",
            )
            page = root / "README.md"
            page.write_text("\nnpm run lint\n", encoding="utf-8")
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any(item.code == "command-not-in-ci" for item in errors))

    def test_ci_command_honors_job_default_working_directory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "frontend" / "package.json").write_text(
                '{"scripts":{"lint":"next lint"}}', encoding="utf-8"
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "jobs:\n  frontend:\n    defaults:\n      run:\n"
                "        working-directory: frontend\n    steps:\n"
                "      - run: npm run lint\n",
                encoding="utf-8",
            )
            page = root / "README.md"
            page.write_text("\nnpm run lint\n", encoding="utf-8")
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"}]
            self.assertEqual(check_command_contracts(root, contracts), [])

    def test_ci_command_in_wrong_working_directory_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "backend").mkdir()
            (root / "frontend" / "package.json").write_text(
                '{"scripts":{"lint":"next lint"}}', encoding="utf-8"
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "jobs:\n  frontend:\n    steps:\n      - run: npm run lint\n"
                "        working-directory: backend\n",
                encoding="utf-8",
            )
            page = root / "README.md"
            page.write_text("\nnpm run lint\n", encoding="utf-8")
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any(item.code == "command-wrong-ci-cwd" for item in errors))

    def test_unhashed_pip_install_contract_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = root / "backend"
            backend.mkdir()
            (backend / "requirements.txt").write_text("package==1 --hash=sha256:abc\n", encoding="utf-8")
            page = backend / "README.md"
            command = "python -m pip install -r requirements.txt"
            page.write_text(f"\n{command}\n", encoding="utf-8")
            contracts = [{"document":"backend/README.md","cwd":"backend","command":command,"kind":"entrypoint","runtime":"python"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any(item.code == "unhashed-pip-install" for item in errors))

    def test_workflow_missing_from_inventory_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text("name: Tests\n", encoding="utf-8")
            inventory = root / "docs" / "operations" / "workflows.md"
            inventory.parent.mkdir(parents=True)
            inventory.write_text("# Workflows\n", encoding="utf-8")
            self.track(root, ".github/workflows/tests.yml")
            errors = check_workflow_inventory(root, "docs/operations/workflows.md")
            self.assertTrue(any("tests.yml" in item.message for item in errors))

    def test_yaml_workflow_is_also_inventoried(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "guard.yaml").write_text("name: Guard\n", encoding="utf-8")
            inventory = root / "docs" / "operations" / "workflows.md"
            inventory.parent.mkdir(parents=True)
            inventory.write_text("# Workflows\n", encoding="utf-8")
            self.track(root, ".github/workflows/guard.yaml")
            errors = check_workflow_inventory(root, "docs/operations/workflows.md")
            self.assertTrue(any("guard.yaml" in item.message for item in errors))

    def test_workflow_basename_in_prose_is_not_an_inventory_row(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text("name: Tests\n", encoding="utf-8")
            inventory = root / "docs" / "operations" / "workflows.md"
            inventory.parent.mkdir(parents=True)
            inventory.write_text(
                "# Workflows\n\nThe `tests.yml` workflow runs tests.\n",
                encoding="utf-8",
            )
            self.track(root, ".github/workflows/tests.yml")
            errors = check_workflow_inventory(root, "docs/operations/workflows.md")
            self.assertTrue(any("tests.yml" in item.message for item in errors))

    def test_untracked_workflow_scratch_is_not_part_of_inventory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text("name: Tests\n", encoding="utf-8")
            (workflows / "scratch.yml").write_text(
                "name: Untracked scratch\n", encoding="utf-8"
            )
            inventory = root / "docs" / "operations" / "workflows.md"
            inventory.parent.mkdir(parents=True)
            inventory.write_text(
                "# Workflows\n\n"
                "| Workflow | Purpose | Trigger | Command | Target | Permissions | Concurrency | Configuration |\n"
                "|---|---|---|---|---|---|---|---|\n"
                "| `tests.yml` | tests | PR | command | none | read | ci | none |\n",
                encoding="utf-8",
            )
            self.track(root, ".github/workflows/tests.yml")
            self.assertEqual(
                check_workflow_inventory(root, "docs/operations/workflows.md"),
                [],
            )

    def test_workflow_inventory_rejects_duplicates_stale_rows_and_wrong_columns(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text("name: Tests\n", encoding="utf-8")
            inventory = root / "docs" / "operations" / "workflows.md"
            inventory.parent.mkdir(parents=True)
            inventory.write_text(
                "# Workflows\n\n"
                "| Workflow | Purpose | Trigger | Command | Target | Permissions | Concurrency | Configuration |\n"
                "|---|---|---|---|---|---|---|---|\n"
                "| `tests.yml` | tests | PR | command | none | read | ci | none |\n"
                "| `tests.yml` | duplicate | PR | command | none | read | ci | none |\n"
                "| `removed.yaml` | stale | PR | command | none | read | ci | none |\n"
                "| `short.yml` | too few | PR |\n",
                encoding="utf-8",
            )
            self.track(root, ".github/workflows/tests.yml")
            errors = check_workflow_inventory(root, "docs/operations/workflows.md")
            codes = {item.code for item in errors}
            self.assertTrue(
                {"duplicate-workflow-row", "stale-workflow-row", "invalid-workflow-row"}
                <= codes
            )

    def test_github_slug_preserves_double_space_as_double_hyphen(self):
        self.assertEqual(
            github_slug("1. 商业化 AI 股票分析平台 / SaaS"),
            "1-商业化-ai-股票分析平台--saas",
        )

    def test_markdown_categories_are_exclusive_and_complete(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.md"
            b = root / "generated" / "b.md"
            b.parent.mkdir()
            a.write_text("# A\n", encoding="utf-8")
            b.write_text("# B\n", encoding="utf-8")
            config = {
                "maintained_documents": ["a.md"],
                "historical_documents": ["a.md"],
                "archived_documents": [],
                "classification_exemptions": ["generated/*.md"],
            }
            errors = check_classification(root, config, [a, b])
            self.assertTrue(any(item.code == "overlapping-document-status" for item in errors))

    def test_classification_exemptions_match_direct_children_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "feed" / "screener" / "direct.md"
            nested = root / "feed" / "screener" / "nested" / "child.md"
            nested.parent.mkdir(parents=True)
            direct.write_text("# Direct\n", encoding="utf-8")
            nested.write_text("# Nested\n", encoding="utf-8")
            config = {
                "maintained_documents": [],
                "historical_documents": [],
                "archived_documents": [],
                "classification_exemptions": ["feed/screener/*.md"],
            }
            errors = check_classification(root, config, [direct, nested])
            self.assertFalse(any(item.path == "feed/screener/direct.md" for item in errors))
            self.assertTrue(
                any(
                    item.path == "feed/screener/nested/child.md"
                    and item.code == "unclassified-markdown"
                    for item in errors
                )
            )

    def _write_valid_config(self, root: Path) -> Path:
        (root / "docs").mkdir(exist_ok=True)
        (root / "docs" / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (root / "feed" / "screener").mkdir(parents=True, exist_ok=True)
        (root / "frontend" / "public" / "feed" / "screener").mkdir(
            parents=True, exist_ok=True
        )
        config = {
            "schema_version": 1,
            "check_all_tracked_markdown": False,
            "archive_date": "2026-07-24",
            "runtime_contract": {
                "node": "20.20.2",
                "npm": "10.8.2",
                "python_primary": "3.11.15",
                "python_compatibility": ["3.12.13"],
            },
            "maintained_documents": ["docs/plan.md"],
            "historical_documents": [],
            "archived_documents": [],
            "classification_exemptions": [
                "feed/screener/*.md",
                "frontend/public/feed/screener/*.md",
            ],
            "environment_document": None,
            "platform_environment_names": [],
            "workflow_inventory_document": None,
            "verified_commands": [],
        }
        path = root / "docs" / "verification.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def test_config_loader_rejects_duplicate_keys_and_nonstandard_constants(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_valid_config(root)
            for raw in (
                '{"schema_version":1,"schema_version":1}',
                '{"schema_version":1,"value":NaN}',
                '{"schema_version":1,"value":Infinity}',
            ):
                with self.subTest(raw=raw):
                    path.write_text(raw, encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(root, path)

    def test_config_loader_rejects_missing_unknown_wrong_type_and_duplicates(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_valid_config(root)
            base = json.loads(path.read_text(encoding="utf-8"))
            cases = []

            missing = json.loads(json.dumps(base))
            missing.pop("verified_commands")
            cases.append(("missing-key", missing))

            unknown = json.loads(json.dumps(base))
            unknown["unknown"] = True
            cases.append(("unknown-key", unknown))

            boolean_schema = json.loads(json.dumps(base))
            boolean_schema["schema_version"] = True
            cases.append(("boolean-schema", boolean_schema))

            wrong_boolean = json.loads(json.dumps(base))
            wrong_boolean["check_all_tracked_markdown"] = "false"
            cases.append(("wrong-boolean", wrong_boolean))

            bad_date = json.loads(json.dumps(base))
            bad_date["archive_date"] = "2026-7-24"
            cases.append(("bad-date", bad_date))

            wrong_canonical_date = json.loads(json.dumps(base))
            wrong_canonical_date["archive_date"] = "2026-07-23"
            cases.append(("wrong-canonical-date", wrong_canonical_date))

            wrong_runtime = json.loads(json.dumps(base))
            wrong_runtime["runtime_contract"]["python_compatibility"] = "3.12.13"
            cases.append(("wrong-runtime-type", wrong_runtime))

            extra_runtime = json.loads(json.dumps(base))
            extra_runtime["runtime_contract"]["extra"] = "not-allowed"
            cases.append(("extra-runtime-key", extra_runtime))

            repeated_compatibility = json.loads(json.dumps(base))
            repeated_compatibility["runtime_contract"]["python_compatibility"] = [
                "3.12.13",
                "3.12.13",
            ]
            cases.append(("duplicate-compatibility", repeated_compatibility))

            primary_is_compatibility = json.loads(json.dumps(base))
            primary_is_compatibility["runtime_contract"]["python_compatibility"] = [
                "3.11.15"
            ]
            cases.append(("primary-is-compatibility", primary_is_compatibility))

            duplicate_document = json.loads(json.dumps(base))
            duplicate_document["maintained_documents"] *= 2
            cases.append(("duplicate-document", duplicate_document))

            overlap = json.loads(json.dumps(base))
            overlap["historical_documents"] = ["docs/plan.md"]
            cases.append(("overlapping-document", overlap))

            invalid_environment = json.loads(json.dumps(base))
            invalid_environment["platform_environment_names"] = ["bad-name"]
            cases.append(("invalid-environment", invalid_environment))

            duplicate_environment = json.loads(json.dumps(base))
            duplicate_environment["platform_environment_names"] = ["PORT", "PORT"]
            cases.append(("duplicate-environment", duplicate_environment))

            invalid_exemption = json.loads(json.dumps(base))
            invalid_exemption["classification_exemptions"] = ["feed/**/*.md"]
            cases.append(("recursive-exemption", invalid_exemption))

            for label, value in cases:
                with self.subTest(label=label):
                    path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(root, path)

    def test_config_loader_rejects_paths_outside_the_repository(self):
        with TemporaryDirectory() as tmp:
            outer = Path(tmp)
            root = outer / "repo"
            root.mkdir()
            path = self._write_valid_config(root)
            base = json.loads(path.read_text(encoding="utf-8"))
            outside = outer / "outside.md"
            outside.write_text("# Outside\n", encoding="utf-8")
            link = root / "docs" / "linked.md"
            link.symlink_to(outside)
            for label, relative in (
                ("absolute", str(outside)),
                ("parent", "../outside.md"),
                ("backslash", r"docs\plan.md"),
                ("dot-segment", "docs/./plan.md"),
                ("symlink", "docs/linked.md"),
            ):
                with self.subTest(label=label):
                    value = json.loads(json.dumps(base))
                    value["maintained_documents"] = [relative]
                    path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(root, path)

    def test_config_loader_enforces_command_kind_runtime_and_exact_keys(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_valid_config(root)
            base = json.loads(path.read_text(encoding="utf-8"))
            readme = root / "README.md"
            readme.write_text("# Project\n", encoding="utf-8")
            (root / "frontend").mkdir(exist_ok=True)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "jobs:\n  frontend:\n    steps: []\n", encoding="utf-8"
            )
            base["maintained_documents"].append("README.md")
            valid_ci = {
                "document": "README.md",
                "cwd": "frontend",
                "command": "npm run lint",
                "kind": "ci",
                "runtime": "node",
                "workflow": ".github/workflows/tests.yml",
                "job": "frontend",
            }
            cases = []
            for label, mutation in (
                ("invalid-kind", {"kind": "maybe"}),
                ("non-string-kind", {"kind": []}),
                ("invalid-runtime", {"runtime": "ruby"}),
                ("non-string-runtime", {"runtime": []}),
                ("runtime-mismatch", {"runtime": "python"}),
                ("cwd-escape", {"cwd": "../frontend"}),
                ("workflow-escape", {"workflow": "../tests.yml"}),
                ("invalid-job", {"job": "bad job"}),
                ("extra-key", {"extra": True}),
                ("glued-semicolon", {"command": "npm run lint;echo injected"}),
                ("glued-pipe", {"command": "npm run lint|cat"}),
                ("redirection", {"command": "npm run lint>captured.txt"}),
                ("command-substitution", {"command": "npm run lint$(echo injected)"}),
                ("backtick-substitution", {"command": "npm run lint`echo injected`"}),
            ):
                item = dict(valid_ci)
                item.update(mutation)
                cases.append((label, [item]))
            missing_job = dict(valid_ci)
            missing_job.pop("job")
            cases.append(("ci-missing-job", [missing_job]))
            entrypoint_with_ci_location = dict(valid_ci)
            entrypoint_with_ci_location["kind"] = "entrypoint"
            cases.append(("entrypoint-with-ci-location", [entrypoint_with_ci_location]))
            cases.append(("duplicate-contract", [valid_ci, dict(valid_ci)]))

            for label, commands in cases:
                with self.subTest(label=label):
                    value = json.loads(json.dumps(base))
                    value["verified_commands"] = commands
                    path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(root, path)

    def test_config_loader_accepts_repository_root_command_cwd(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_valid_config(root)
            base = json.loads(path.read_text(encoding="utf-8"))
            base["verified_commands"] = [
                {
                    "document": "docs/plan.md",
                    "cwd": ".",
                    "command": "python scripts/check_docs.py",
                    "kind": "entrypoint",
                    "runtime": "python",
                }
            ]
            path.write_text(json.dumps(base), encoding="utf-8")
            self.assertEqual(load_config(root, path), base)

    def test_runtime_contract_detects_version_and_matrix_drift(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "backend").mkdir()
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (root / ".node-version").write_text("20.20.2\n", encoding="utf-8")
            (root / ".python-version").write_text("3.11.15\n", encoding="utf-8")
            backend_runtime = root / "backend" / "runtime.txt"
            backend_runtime.write_text("python-3.11.15\n", encoding="utf-8")
            dockerfile = root / "backend" / "Dockerfile"
            dockerfile.write_text("FROM python:3.11.15-slim\n", encoding="utf-8")
            render = root / "render.yaml"
            render.write_text(
                'envVars:\n  - key: PYTHON_VERSION\n    value: "3.11.15"\n',
                encoding="utf-8",
            )
            (root / "frontend" / "package.json").write_text(
                json.dumps(
                    {
                        "packageManager": "npm@10.8.2",
                        "engines": {"node": "20.20.2", "npm": "10.8.2"},
                    }
                ),
                encoding="utf-8",
            )
            workflow = workflows / "tests.yml"
            exact_workflow = (
                "jobs:\n"
                "  frontend:\n"
                "    steps:\n"
                "      - uses: actions/setup-node@v7\n"
                "        with:\n"
                "          node-version-file: .node-version\n"
                "      - run: |\n"
                '          test "$(node --version)" = "v20.20.2"\n'
                '          test "$(npm --version)" = "10.8.2"\n'
                "  python:\n"
                "    strategy:\n"
                "      matrix:\n"
                "        include:\n"
                '          - python_version: "3.11.15"\n'
                '          - python_version: "3.12.13"\n'
                "    steps:\n"
                "      - uses: actions/setup-python@v6\n"
                "        with:\n"
                "          python-version: ${{ matrix.python_version }}\n"
            )
            workflow.write_text(exact_workflow, encoding="utf-8")
            deploy = workflows / "deploy-pages.yml"
            exact_deploy = (
                "jobs:\n"
                "  build:\n"
                "    steps:\n"
                "      - uses: actions/setup-node@v7\n"
                "        with:\n"
                "          node-version-file: .node-version\n"
                "      - run: |\n"
                '          test "$(node --version)" = "v20.20.2"\n'
                '          test "$(npm --version)" = "10.8.2"\n'
            )
            deploy.write_text(exact_deploy, encoding="utf-8")
            production = workflows / "alpha-routine.yml"
            exact_production = (
                "jobs:\n"
                "  produce:\n"
                "    steps:\n"
                "      - uses: actions/setup-python@v6\n"
                "        with:\n"
                "          python-version-file: .python-version\n"
            )
            production.write_text(exact_production, encoding="utf-8")
            self.track(
                root,
                ".github/workflows/tests.yml",
                ".github/workflows/deploy-pages.yml",
                ".github/workflows/alpha-routine.yml",
            )
            contract = {
                "node": "20.20.2",
                "npm": "10.8.2",
                "python_primary": "3.11.15",
                "python_compatibility": ["3.12.13"],
            }
            self.assertEqual(check_runtime_contract(root, contract), [])
            mutations = (
                (root / ".node-version", "20.20.3\n"),
                (root / ".python-version", "3.11.14\n"),
                (backend_runtime, "python-3.11.14\n"),
                (dockerfile, "FROM python:3.11.14-slim\n"),
                (
                    render,
                    'envVars:\n  - key: PYTHON_VERSION\n    value: "3.11.14"\n',
                ),
                (
                    render,
                    'envVars:\n'
                    '  - key: PYTHON_VERSION\n'
                    '    value: "3.11.14"\n'
                    '  - key: UNRELATED_VERSION\n'
                    '    value: "3.11.15"\n',
                ),
                (
                    render,
                    'envVars:\n'
                    '  - key: PYTHON_VERSION\n'
                    '    value: "3.11.15"\n'
                    '  - key: PYTHON_VERSION\n'
                    '    value: "3.11.15"\n',
                ),
                (
                    root / "frontend" / "package.json",
                    '{"packageManager":"npm@10.8.1","engines":{"node":"20.20.2","npm":"10.8.1"}}',
                ),
                (
                    workflow,
                    exact_workflow.replace(
                        '          - python_version: "3.12.13"\n', ""
                    ),
                ),
                (
                    deploy,
                    exact_deploy.replace("v20.20.2", "v20.20.1"),
                ),
                (
                    production,
                    exact_production.replace(
                        "python-version-file: .python-version",
                        'python-version: "3.11.14"',
                    ),
                ),
            )
            for target, replacement in mutations:
                with self.subTest(target=target.name):
                    original = target.read_text(encoding="utf-8")
                    target.write_text(replacement, encoding="utf-8")
                    self.assertTrue(check_runtime_contract(root, contract))
                    target.write_text(original, encoding="utf-8")

    def test_runtime_contract_parses_four_space_workflow_indentation(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "backend").mkdir()
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (root / ".node-version").write_text("20.20.2\n", encoding="utf-8")
            (root / ".python-version").write_text("3.11.15\n", encoding="utf-8")
            (root / "backend" / "runtime.txt").write_text(
                "python-3.11.15\n", encoding="utf-8"
            )
            (root / "backend" / "Dockerfile").write_text(
                "FROM python:3.11.15-slim\n", encoding="utf-8"
            )
            (root / "render.yaml").write_text(
                'envVars:\n  - key: PYTHON_VERSION\n    value: "3.11.15"\n',
                encoding="utf-8",
            )
            (root / "frontend" / "package.json").write_text(
                json.dumps(
                    {
                        "packageManager": "npm@10.8.2",
                        "engines": {"node": "20.20.2", "npm": "10.8.2"},
                    }
                ),
                encoding="utf-8",
            )
            (workflows / "tests.yml").write_text(
                "jobs:\n"
                "    frontend:\n"
                "        steps:\n"
                "            - uses: actions/setup-node@v7\n"
                "              with:\n"
                "                  node-version-file: .node-version\n"
                "            - run: |\n"
                '                  test "$(node --version)" = "v20.20.2"\n'
                '                  test "$(npm --version)" = "10.8.2"\n'
                "    python:\n"
                "        strategy:\n"
                "            matrix:\n"
                "                include:\n"
                '                    - python_version: "3.11.15"\n'
                '                    - python_version: "3.12.13"\n'
                "        steps:\n"
                "            - uses: actions/setup-python@v6\n"
                "              with:\n"
                "                  python-version: ${{ matrix.python_version }}\n",
                encoding="utf-8",
            )
            (workflows / "deploy-pages.yml").write_text(
                "jobs:\n"
                "    build:\n"
                "        steps:\n"
                "            - uses: actions/setup-node@v7\n"
                "              with:\n"
                "                  node-version-file: .node-version\n"
                "            - run: |\n"
                '                  test "$(node --version)" = "v20.20.2"\n'
                '                  test "$(npm --version)" = "10.8.2"\n',
                encoding="utf-8",
            )
            (workflows / "alpha-routine.yml").write_text(
                "jobs:\n"
                "    produce:\n"
                "        steps:\n"
                "            - uses: actions/setup-python@v6\n"
                "              with:\n"
                '                  python-version: "3.10.0"\n',
                encoding="utf-8",
            )
            self.track(
                root,
                ".github/workflows/tests.yml",
                ".github/workflows/deploy-pages.yml",
                ".github/workflows/alpha-routine.yml",
            )
            contract = {
                "node": "20.20.2",
                "npm": "10.8.2",
                "python_primary": "3.11.15",
                "python_compatibility": ["3.12.13"],
            }

            errors = check_runtime_contract(root, contract)

            self.assertEqual(
                {item.code for item in errors},
                {"workflow-python-runtime-drift"},
            )

    def test_runtime_contract_rejects_active_drift_hidden_by_yaml_decoys(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "backend").mkdir()
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (root / ".node-version").write_text("20.20.2\n", encoding="utf-8")
            (root / ".python-version").write_text("3.11.15\n", encoding="utf-8")
            (root / "backend" / "runtime.txt").write_text(
                "python-3.11.15\n", encoding="utf-8"
            )
            (root / "backend" / "Dockerfile").write_text(
                "FROM python:3.11.15-slim\n", encoding="utf-8"
            )
            (root / "render.yaml").write_text(
                'envVars:\n  - key: PYTHON_VERSION\n    value: "3.11.15"\n',
                encoding="utf-8",
            )
            (root / "frontend" / "package.json").write_text(
                json.dumps(
                    {
                        "packageManager": "npm@10.8.2",
                        "engines": {"node": "20.20.2", "npm": "10.8.2"},
                    }
                ),
                encoding="utf-8",
            )
            (workflows / "tests.yml").write_text(
                "jobs:\n"
                "  frontend:\n"
                "    env:\n"
                "      ASSERTION_DECOYS: |\n"
                '        test "$(node --version)" = "v20.20.2"\n'
                '        test "$(npm --version)" = "10.8.2"\n'
                "    steps:\n"
                "      - uses: actions/setup-node@v7\n"
                "        with:\n"
                '          node-version: "18"\n'
                "  python:\n"
                "    strategy:\n"
                "      matrix:\n"
                '        python_version: ["3.10.0"]\n'
                "    env:\n"
                "      MATRIX_DECOY: |\n"
                '        - python_version: "3.11.15"\n'
                '        - python_version: "3.12.13"\n'
                "    steps:\n"
                "      - uses: actions/setup-python@v6\n"
                "        with:\n"
                '          python-version: "3.10.0"\n'
                "          # python-version: ${{ matrix.python_version }}\n",
                encoding="utf-8",
            )
            (workflows / "deploy-pages.yml").write_text(
                "jobs:\n"
                "  build:\n"
                "    env:\n"
                "      RUNTIME_DECOYS: |\n"
                "        node-version-file: .node-version\n"
                '        test "$(node --version)" = "v20.20.2"\n'
                '        test "$(npm --version)" = "10.8.2"\n'
                "    steps:\n"
                "      - uses: actions/setup-node@v7\n"
                "        with:\n"
                '          node-version: "18"\n'
                "          # node-version-file: .node-version\n",
                encoding="utf-8",
            )
            (workflows / "alpha-routine.yml").write_text(
                "jobs:\n"
                "  produce:\n"
                "    steps:\n"
                "      - uses: actions/setup-python@v6\n"
                "        with:\n"
                "          python-version-file: .python-version\n",
                encoding="utf-8",
            )
            self.track(
                root,
                ".github/workflows/tests.yml",
                ".github/workflows/deploy-pages.yml",
                ".github/workflows/alpha-routine.yml",
            )
            contract = {
                "node": "20.20.2",
                "npm": "10.8.2",
                "python_primary": "3.11.15",
                "python_compatibility": ["3.12.13"],
            }

            errors = check_runtime_contract(root, contract)
            codes = {item.code for item in errors}

            self.assertTrue(
                {
                    "workflow-runtime-assertion-drift",
                    "python-runtime-matrix-drift",
                    "deployment-runtime-drift",
                    "workflow-python-runtime-drift",
                    "workflow-node-runtime-drift",
                }
                <= codes,
                codes,
            )

    def test_archived_metadata_requires_exact_archive_date(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "archive.md"
            page.write_text(
                "# Archive\n\n"
                "> **Status:** Archived; not current implementation guidance\n"
                "> **Scope:** Historical record.\n",
                encoding="utf-8",
            )
            errors = check_metadata(
                root, [], [], ["archive.md"], archive_date="2026-07-24"
            )
            self.assertTrue(any(item.code == "missing-archive-date" for item in errors))
            page.write_text(
                "# Archive\n\n"
                "> **Status:** Archived; not current implementation guidance\n"
                "> **Scope:** Historical record.\n"
                "> **Archived on:** 2026-07-16\n",
                encoding="utf-8",
            )
            errors = check_metadata(
                root, [], [], ["archive.md"], archive_date="2026-07-24"
            )
            self.assertTrue(any(item.code == "invalid-archive-date" for item in errors))

    def test_cli_rejects_config_path_escape_without_traceback(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            returncode = check_docs_main(["--config", "../outside.json"])
        self.assertEqual(returncode, 2)
        self.assertIn("documentation configuration error:", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    main()
