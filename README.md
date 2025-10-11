This is Flint and Steel, an auto rigger for building limbs! To install, download all the .py files and put them in a folder called flintandsteel. Take the flintandsteel folder and place it in your ../maya/2024/scripts . 

Compatible with Maya 2024 

Run this script to start it:

import flintandsteel.flintandsteelUI as fasUI
import importlib

importlib.reload(fasUI)
fasUI.limb_ui()
