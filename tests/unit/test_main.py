import os
import tempfile
from unittest import mock

from git import Actor, Repo
from oslotest import base

from reference_transmogrifier import main


class CommitAndPrChanges(base.BaseTestCase):
    @mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token"})
    @mock.patch.object(main, "Github")
    def test_no_pr_without_changes(self, github):
        repo_dir = tempfile.TemporaryDirectory()
        self.addCleanup(repo_dir.cleanup)
        repo = Repo.init(repo_dir.name)
        alice = Actor("alice", "alice@example.org")
        repo.index.commit("initial", author=alice, committer=alice)

        main.commit_and_pr_changes(
            "https://github.com/example/reference-repository.git",
            "master",
            repo_dir.name,
        )

        github.assert_not_called()
        self.assertEqual(["initial"], [c.message for c in repo.iter_commits()])
