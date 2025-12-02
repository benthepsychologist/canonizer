"""Tests for canonizer init CLI command."""

import json
import tempfile
from pathlib import Path

import yaml

from canonizer.local.config import (
    CANONIZER_DIR,
    CONFIG_FILENAME,
    LOCK_FILENAME,
    REGISTRY_DIR,
    SCHEMAS_DIR,
    TRANSFORMS_DIR,
)


class TestInitCommand:
    """Tests for the init command functionality."""

    def test_init_creates_directory_structure(self):
        """Test that init creates the full directory structure."""
        from typer.testing import CliRunner

        from canonizer.cli.main import app

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", tmpdir])

            # Check exit code
            assert result.exit_code == 0, f"Output: {result.stdout}"

            # Check directories created
            canonizer_dir = Path(tmpdir) / CANONIZER_DIR
            assert canonizer_dir.exists()
            assert (canonizer_dir / REGISTRY_DIR).exists()
            assert (canonizer_dir / REGISTRY_DIR / SCHEMAS_DIR).exists()
            assert (canonizer_dir / REGISTRY_DIR / TRANSFORMS_DIR).exists()

    def test_init_creates_config_yaml(self):
        """Test that init creates a valid config.yaml."""
        from typer.testing import CliRunner

        from canonizer.cli.main import app

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", tmpdir])
            assert result.exit_code == 0

            config_path = Path(tmpdir) / CANONIZER_DIR / CONFIG_FILENAME
            assert config_path.exists()

            # Verify it's valid YAML
            with open(config_path) as f:
                config = yaml.safe_load(f)

            assert "registry" in config
            assert config["registry"]["mode"] == "local"
            assert config["registry"]["root"] == "registry"

    def test_init_creates_lock_json(self):
        """Test that init creates a valid lock.json."""
        from typer.testing import CliRunner

        from canonizer.cli.main import app

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", tmpdir])
            assert result.exit_code == 0

            lock_path = Path(tmpdir) / CANONIZER_DIR / LOCK_FILENAME
            assert lock_path.exists()

            # Verify it's valid JSON
            with open(lock_path) as f:
                lock = json.load(f)

            assert lock["version"] == "1"
            assert "schemas" in lock
            assert "transforms" in lock
            assert lock["schemas"] == {}
            assert lock["transforms"] == {}

    def test_init_creates_gitignore(self):
        """Test that init creates .gitignore for registry."""
        from typer.testing import CliRunner

        from canonizer.cli.main import app

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", tmpdir])
            assert result.exit_code == 0

            gitignore_path = Path(tmpdir) / CANONIZER_DIR / ".gitignore"
            assert gitignore_path.exists()

            content = gitignore_path.read_text()
            assert "registry/" in content

    def test_init_current_directory(self):
        """Test that init works in current directory."""
        import os

        from typer.testing import CliRunner

        from canonizer.cli.main import app

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory and run init without path argument
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init"])
                assert result.exit_code == 0

                canonizer_dir = Path(tmpdir) / CANONIZER_DIR
                assert canonizer_dir.exists()
            finally:
                os.chdir(original_cwd)

    def test_init_fails_if_exists_without_force(self):
        """Test that init fails if .canonizer/ already exists."""
        from typer.testing import CliRunner

        from canonizer.cli.main import app

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .canonizer/ first
            canonizer_dir = Path(tmpdir) / CANONIZER_DIR
            canonizer_dir.mkdir()

            # Should fail without --force
            result = runner.invoke(app, ["init", tmpdir])
            assert result.exit_code == 1
            assert "already exists" in result.stdout

    def test_init_succeeds_with_force(self):
        """Test that init succeeds with --force even if directory exists."""
        from typer.testing import CliRunner

        from canonizer.cli.main import app

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .canonizer/ with some content
            canonizer_dir = Path(tmpdir) / CANONIZER_DIR
            canonizer_dir.mkdir()
            (canonizer_dir / "old_file.txt").write_text("old content")

            # Should succeed with --force
            result = runner.invoke(app, ["init", tmpdir, "--force"])
            assert result.exit_code == 0

            # New files should be created
            assert (canonizer_dir / CONFIG_FILENAME).exists()
            assert (canonizer_dir / LOCK_FILENAME).exists()

    def test_init_fails_for_nonexistent_path(self):
        """Test that init fails if target directory doesn't exist."""
        from typer.testing import CliRunner

        from canonizer.cli.main import app

        runner = CliRunner()

        result = runner.invoke(app, ["init", "/nonexistent/path/that/doesnt/exist"])
        assert result.exit_code == 1
        assert "does not exist" in result.stdout

    def test_init_output_messages(self):
        """Test that init shows appropriate output messages."""
        from typer.testing import CliRunner

        from canonizer.cli.main import app

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", tmpdir])

            assert result.exit_code == 0
            assert "Initializing" in result.stdout
            assert "config.yaml" in result.stdout
            assert "lock.json" in result.stdout
            assert ".gitignore" in result.stdout
            assert "Initialized" in result.stdout
            assert "Next steps" in result.stdout


class TestInitIntegration:
    """Integration tests for init command with other components."""

    def test_init_config_loadable(self):
        """Test that created config.yaml is loadable by CanonizerConfig."""
        from typer.testing import CliRunner

        from canonizer.cli.main import app
        from canonizer.local.config import CanonizerConfig

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", tmpdir])
            assert result.exit_code == 0

            config_path = Path(tmpdir) / CANONIZER_DIR / CONFIG_FILENAME
            config = CanonizerConfig.load(config_path)

            assert config.registry.mode.value == "local"

    def test_init_lock_loadable(self):
        """Test that created lock.json is loadable by LockFile."""
        from typer.testing import CliRunner

        from canonizer.cli.main import app
        from canonizer.local.lock import LockFile

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", tmpdir])
            assert result.exit_code == 0

            lock_path = Path(tmpdir) / CANONIZER_DIR / LOCK_FILENAME
            lock = LockFile.load(lock_path)

            assert lock.version == "1"
            assert len(lock.schemas) == 0
            assert len(lock.transforms) == 0
