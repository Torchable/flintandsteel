# Ignite drag and drop installer
#
# Drop this file into a Maya viewport. It puts the ignite folder on the
# python path, writes a startup entry into userSetup.py, and builds the
# Ignite shelf for the current session.

import os
import sys

from maya import cmds

# markers so a reinstall can find and replace the block it wrote before
START_MARKER = '# >>> Ignite auto rigger >>>'
END_MARKER = '# <<< Ignite auto rigger <<<'


def onMayaDroppedPythonFile(*args):
    # this file lives inside the ignite package folder
    src = args[0] if args and args[0] else __file__
    package_dir = os.path.dirname(os.path.abspath(src))
    # imports resolve against the PARENT of the package folder, adding the
    # package folder itself would make "import ignite" fail
    parent_dir = os.path.dirname(package_dir)

    # the folder has to be called ignite for the imports inside the
    # package to resolve
    if os.path.basename(package_dir) != 'ignite':
        cmds.confirmDialog(
            title='Ignite',
            message='The folder holding the ignite files must be named '
                    '"ignite" (it is currently "{}"). Rename the folder '
                    'and drop this file in again.'.format(
                        os.path.basename(package_dir)))
        return

    if parent_dir not in sys.path:
        sys.path.append(parent_dir)

    # persist for future sessions: python path + shelf rebuild
    write_user_setup(parent_dir)

    # build the shelf for this session
    import importlib
    import ignite.IgniteShelf as igshelf
    importlib.reload(igshelf)
    igshelf.install()
    cmds.confirmDialog(title='Ignite', message='Ignite installed!')


def write_user_setup(parent_dir):
    user_setup = os.path.join(cmds.internalVar(userScriptDir=True),
                              'userSetup.py')
    existing = ''
    if os.path.exists(user_setup):
        with open(user_setup) as f:
            existing = f.read()

    # strip anything a previous install wrote so reinstalling from a new
    # location never leaves a stale or broken entry behind
    kept_lines = []
    inside_block = False
    for line in existing.splitlines():
        if line.strip() == START_MARKER:
            inside_block = True
        if not inside_block and not is_legacy_line(line):
            kept_lines.append(line)
        if line.strip() == END_MARKER:
            inside_block = False

    block = [
        START_MARKER,
        'import sys',
        "if r'{0}' not in sys.path:".format(parent_dir),
        "    sys.path.append(r'{0}')".format(parent_dir),
        'from maya import cmds',
        "cmds.evalDeferred('import ignite.IgniteShelf as igshelf; "
        "igshelf.install()')",
        END_MARKER,
    ]

    content = '\n'.join(kept_lines).rstrip()
    if content:
        content += '\n\n'
    content += '\n'.join(block) + '\n'

    with open(user_setup, 'w') as f:
        f.write(content)


def is_legacy_line(line):
    """Spots the lines the first version of this installer wrote, which
    were not wrapped in markers and pointed sys.path one folder too deep."""
    stripped = line.strip()
    if stripped == '# Ignite auto rigger':
        return True
    if 'IgniteShelf' in stripped and 'evalDeferred' in stripped:
        return True
    if stripped.startswith('sys.path.append(') and 'ignite' in stripped.lower():
        return True
    return False
