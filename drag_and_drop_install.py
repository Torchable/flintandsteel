# Ignite drag and drop installer
#
# Drop this file into a Maya viewport. It puts the ignite folder on the
# python path, writes a startup entry into userSetup.py, and builds the
# Ignite shelf for the current session.

import os
import sys

from maya import cmds


class IgniteInstaller(object):
    # markers so a reinstall can find and replace the block it wrote before
    START_MARKER = '# >>> Ignite auto rigger >>>'
    END_MARKER = '# <<< Ignite auto rigger <<<'
    PACKAGE_NAME = 'ignite'

    def __init__(self, dropped_file):
        # the dropped file lives inside the ignite package folder
        self.package_dir = os.path.dirname(os.path.abspath(dropped_file))
        # imports resolve against the PARENT of the package folder, adding
        # the package folder itself would make "import ignite" fail
        self.parent_dir = os.path.dirname(self.package_dir)

    def install(self):
        # the folder has to be called ignite for the imports inside the
        # package to resolve
        if os.path.basename(self.package_dir) != self.PACKAGE_NAME:
            cmds.confirmDialog(
                title='Ignite',
                message='The folder holding the ignite files must be named '
                        '"{}" (it is currently "{}"). Rename the folder '
                        'and drop this file in again.'.format(
                            self.PACKAGE_NAME,
                            os.path.basename(self.package_dir)))
            return

        if self.parent_dir not in sys.path:
            sys.path.append(self.parent_dir)

        # persist for future sessions: python path + shelf rebuild
        self.write_user_setup()

        # build the shelf for this session
        import importlib
        import ignite.IgniteShelf as igshelf
        importlib.reload(igshelf)
        igshelf.install()
        cmds.confirmDialog(title='Ignite', message='Ignite installed!')

    def write_user_setup(self):
        user_setup = os.path.join(cmds.internalVar(userScriptDir=True),
                                  'userSetup.py')
        existing = ''
        if os.path.exists(user_setup):
            with open(user_setup) as f:
                existing = f.read()

        content = '\n'.join(self.strip_previous_installs(existing)).rstrip()
        if content:
            content += '\n\n'
        content += '\n'.join(self.startup_block()) + '\n'

        with open(user_setup, 'w') as f:
            f.write(content)

    def startup_block(self):
        """The lines userSetup.py runs at startup, path first so the
        deferred shelf import can resolve the package."""
        return [
            self.START_MARKER,
            'import sys',
            "if r'{0}' not in sys.path:".format(self.parent_dir),
            "    sys.path.append(r'{0}')".format(self.parent_dir),
            'from maya import cmds',
            "cmds.evalDeferred('import ignite.IgniteShelf as igshelf; "
            "igshelf.install()')",
            self.END_MARKER,
        ]

    def strip_previous_installs(self, existing):
        """Drops anything a previous install wrote so reinstalling from a
        new location never leaves a stale or broken entry behind."""
        kept_lines = []
        inside_block = False
        for line in existing.splitlines():
            if line.strip() == self.START_MARKER:
                inside_block = True
            if not inside_block and not self.is_legacy_line(line):
                kept_lines.append(line)
            if line.strip() == self.END_MARKER:
                inside_block = False

        return kept_lines

    @staticmethod
    def is_legacy_line(line):
        """Spots the lines the first version of this installer wrote, which
        were not wrapped in markers and pointed sys.path one folder too
        deep."""
        stripped = line.strip()
        if stripped == '# Ignite auto rigger':
            return True
        if 'IgniteShelf' in stripped and 'evalDeferred' in stripped:
            return True
        if (stripped.startswith('sys.path.append(')
                and 'ignite' in stripped.lower()):
            return True
        return False


# maya looks this function up by name when the file is dropped, so it is the
# one thing that has to live at module level
def onMayaDroppedPythonFile(*args):
    src = args[0] if args and args[0] else __file__
    IgniteInstaller(src).install()
