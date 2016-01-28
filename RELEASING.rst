Release process
===============

Maintain ``RELEASE_NOTES.rst`` with a list of new features and API changes in each major release.

Major releases:

  1. Create branch release-X from master.
  2. Remove any unfinished features.
  3. Test and fix any problems found.
  4. Tag X.0.

Minor (bugfix) releases:

  1. Backport bugfixes from the master branch or fix bugs specific to old releases into the currently maintained release-X branch(es).
  2. When significant bugs have been fixed, tag X.Y+1.
  3. To help dealing with regressions, no new features or refactorings should be implemented in release-X branches. Those happen in the master branch, and then a new release-X+1 branch is created.
