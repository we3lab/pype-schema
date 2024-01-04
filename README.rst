*********************************************
Python for Process Engineering Schema (PyPES)
*********************************************

.. image::
   https://github.com/we3lab/pype-schema/workflows/Build%20Main/badge.svg
   :height: 30
   :target: https://github.com/we3lab/pype-schema/actions
   :alt: Build Status

.. image::
   https://github.com/we3lab/pype-schema/workflows/Documentation/badge.svg
   :height: 30
   :target: https://we3lab.github.io/pype-schema
   :alt: Documentation

.. image::
   https://codecov.io/gh/we3lab/pype-schema/branch/main/graph/badge.svg
   :height: 30
   :target: https://codecov.io/gh/we3lab/pype-schema
   :alt: Code Coverage

A class hierarchy designed to represent configurations of process engineering systems, such as wastewater treatment or desalination plants.

Useful Commands
===============

1. ``pip install -e .``

  This will install your package in editable mode.

2. ``pytest pype_schema/tests --cov=pype_schema --cov-report=html``

  Produces an HTML test coverage report for the entire project which can
  be found at ``htmlcov/index.html``.

3. ``docs/make html``

  This will generate an HTML version of the documentation which can be found
  at ``_build/html/index.html``.

4. ``flake8 pype_schema --count --verbose --show-source --statistics``

  This will lint the code and share all the style errors it finds.

5. ``black pype_schema``

  This will reformat the code according to strict style guidelines.

Legal Documents
===============

- `LICENSE <https://github.com/we3lab/pype-schema/blob/main/LICENSE/>`_
- `CONTRIBUTING <https://github.com/we3lab/pype-schema/blob/main/CONTRIBUTING.rst/>`_
