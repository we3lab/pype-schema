******************
WWTP Configuration
******************

.. image::
   https://github.com/we3lab/wwtp-configuration/workflows/Build%20Main/badge.svg
   :height: 30
   :target: https://github.com/we3lab/wwtp-configuration/actions
   :alt: Build Status

.. image::
   https://github.com/we3lab/wwtp-configuration/workflows/Documentation/badge.svg
   :height: 30
   :target: https://we3lab.github.io/wwtp-configuration
   :alt: Documentation

.. image::
   https://codecov.io/gh/we3lab/wwtp-configuration/branch/main/graph/badge.svg
   :height: 30
   :target: https://codecov.io/gh/we3lab/wwtp-configuration
   :alt: Code Coverage

A class hierarchy designed to represent a wastewater treatment plant's configuration.

Useful Commands
===============

1. ``pip install -e .``

  This will install your package in editable mode.

2. ``pytest wwtp_configuration/tests --cov=wwtp_configuration --cov-report=html``

  Produces an HTML test coverage report for the entire project which can
  be found at ``htmlcov/index.html``.

3. ``docs/make html``

  This will generate an HTML version of the documentation which can be found
  at ``_build/html/index.html``.

4. ``flake8 wwtp_configuration --count --verbose --show-source --statistics``

  This will lint the code and share all the style errors it finds.

5. ``black wwtp_configuration``

  This will reformat the code according to strict style guidelines.

Legal Documents
===============

- `LICENSE <https://github.com/we3lab/wwtp-configuration/blob/main/LICENSE/>`_
- `CONTRIBUTING <https://github.com/we3lab/wwtp-configuration/blob/main/CONTRIBUTING.rst/>`_
