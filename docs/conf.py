# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from pathlib import Path

from unittest.mock import Mock as MagicMock

# -- Mock modules -------------------------------------------------------------



class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return Mock()


MOCK_MODULES = ['numpy', 'matplotlib', 'matplotlib.pyplot', 'pandas', 'netCDF4',
                'pytest', 'pysftp', 'atmoswing_toolbox',
                'atmoswing_toolbox.files.parse.predictors'
                ]

sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)


# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

BASE_PATH = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(BASE_PATH))
sys.path.insert(0, str(BASE_PATH / "atmoswing_vigicrues"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'AtmoSwing Vigicrues'
copyright = '2022, Pascal Horton'
author = 'Pascal Horton'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
]

autosummary_generate = True

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
