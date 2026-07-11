from maya import cmds

# Callback

def onMayaDroppedPythonFile(*args):
    cmds.confirmDialog(title='Ignite', message='Dropped!')
        
def igspinecreator(*args):
    import ignite.igniteSpineUI as spineUI
    import importlib

    importlib.reload(spineUI)
    spineUI.spine_ui()


def iglimbcreator(*args):
    import ignite.igniteLimbUI as LimbUI
    import importlib

    importlib.reload(LimbUI)
    LimbUI.limb_ui()

# Shelf Def


SHELF_BUTTONS = [
    
    {'label': 'IgSpine Creator', 'command': igspinecreator},
    {'label': 'IgLimb Creator', 'command': iglimbcreator},
]

class igniteShelf(object):
    NAME = 'Ignite'
    ICON_PATH = ''
    DEFAULT_ICON = 'commandButton.png'

    def __init__(self):
        self._reset_shelf()
        self._build()

    def _reset_shelf(self):
        if cmds.shelfLayout(self.NAME, exists=True):
            cmds.deleteUI(self.NAME)
        cmds.shelfLayout(self.NAME, p='ShelfLayout')

    def _build(self):
        for entry in SHELF_BUTTONS:
            if entry.get('separator'):
                self._add_separator()
            else:
                self._add_button(**entry)

    def _add_button(self, label, command, icon=None, **kwargs):
        icon = (self.ICON_PATH + icon) if icon else self.DEFAULT_ICON
        return cmds.shelfButton(
            parent=self.NAME,
            width=37,
            height=37,
            image=icon,
            label=label,
            command=command,
            imageOverlayLabel=label,
        )

    def _add_separator(self):
        cmds.separator(
            parent=self.NAME,
            style='single',
            horizontal=False,
            width=10,
            height=37,
        )


def install():
    igniteShelf()


if __name__ == '__main__':
    install()