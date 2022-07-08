******************
WWTP Configuration
******************

Useful Commands
===============

1. ``pip install -e .``

  This will install your package in editable mode.

2. ``pytest tests --cov=wwtp-configuration --cov-report=html``

  Produces an HTML test coverage report for the entire project which can
  be found at ``htmlcov/index.html``.

3. ``docs/make html``

  This will generate an HTML version of the documentation which can be found
  at ``_build/html/index.html``.

4. ``flake8 wwtp_configuration --count --verbose --show-source --statistics``

  This will lint the code and share all the style errors it finds.

5. ``black wwtp_configuration``

  This will reformat the code according to strict style guidelines.
