import configparser
import os.path
import sys
from pkg_resources import get_distribution

topdir = os.path.abspath('..')
sys.path.insert(0, topdir)

config = configparser.ConfigParser()
config.read(os.path.join(topdir, 'setup.cfg'))

project = config['metadata']['name']
author = config['metadata']['author']
copyright = config['metadata']['copyright']
release = get_distribution(project).version
version = release

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
]

source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build']
pygments_style = None

html_theme = 'alabaster'
html_theme_options = {
    'description': config['metadata']['description'],
    'github_user': 'unipartdigital',
    'github_repo': project,
    'github_button': True,
}
