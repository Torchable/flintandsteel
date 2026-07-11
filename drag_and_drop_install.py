import os
import sys
from maya import cmds

def onMayaDroppedPythonFile(*args):
    # folder containing the ignite package
    src = args[0] if args and args[0] else __file__
    install_dir = os.path.dirname(os.path.abspath(src))
    if install_dir not in sys.path:
        sys.path.append(install_dir)

    # persist for future sessions: path + shelf rebuild
    user_setup = os.path.join(cmds.internalVar(userScriptDir=True),
                              'userSetup.py')
    lines = ("\n# Ignite auto rigger\n"
             "import sys\n"
             "sys.path.append(r'{}')\n"
             "from maya import cmds\n"
             "cmds.evalDeferred("
             "'import ignite.IgniteShelf as igshelf; igshelf.install()')\n"
             ).format(install_dir)
    existing = ''
    if os.path.exists(user_setup):
        with open(user_setup) as f:
            existing = f.read()
    if install_dir not in existing:
        with open(user_setup, 'a') as f:
            f.write(lines)

    # build shelf session
    import ignite.IgniteShelf as igshelf
    igshelf.install()
    cmds.confirmDialog(title='Ignite', message='Ignite installed!')