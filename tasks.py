from os.path import expanduser, exists
from os import makedirs

from invoke import run, task

_plugin_file_rootname = 'safety_save'


@task
def install():
    path = expanduser('~/.local/share/gedit/plugins')
    if exists(path) is False:
        print("Create gEdit plugins path: %s" % (path))
        makedirs(path)

    for ext, description in (('plugin', 'plugin info'),
                             ('py', 'plugin code')):
        filename = ('%s.%s' % (_plugin_file_rootname, ext))
        print("Copying %s (%s)." % (filename, description))
        run('cp %s %s' % (filename, path))
