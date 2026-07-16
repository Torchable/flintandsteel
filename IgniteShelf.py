from maya import cmds

# Shelf Def


class igniteShelf(object):
    NAME = 'Ignite'
    ICON_PATH = ''
    DEFAULT_ICON = 'commandButton.png'

    # The button commands are plain python strings on purpose. Maya saves
    # every shelf to prefs/shelves/shelf_Ignite.mel when it closes, and only
    # a string survives that round trip. A python function object gets saved
    # as its repr ("<function ... at 0x...>") and the button is dead the
    # next session.
    SPINE_CMD = '\n'.join([
        'import importlib',
        'import ignite.igniteSpineUI as spineUI',
        'importlib.reload(spineUI)',
        'spineUI.spine_ui()',
    ])

    LIMB_CMD = '\n'.join([
        'import importlib',
        'import ignite.igniteLimbUI as limbUI',
        'importlib.reload(limbUI)',
        'limbUI.limb_ui()',
    ])

    def __init__(self):
        self._reset_shelf()
        self._build()

    def shelf_buttons(self):
        return [
            {'label': 'IgSpine Creator', 'command': self.SPINE_CMD},
            {'label': 'IgLimb Creator', 'command': self.LIMB_CMD},
        ]

    def _reset_shelf(self):
        if cmds.shelfLayout(self.NAME, exists=True):
            cmds.deleteUI(self.NAME)
        cmds.shelfLayout(self.NAME, p='ShelfLayout')

    def _build(self):
        for entry in self.shelf_buttons():
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
            sourceType='python',
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
