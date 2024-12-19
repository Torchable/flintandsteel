# Flint and Steel Auto Rigger
# by Colin Cheng 
# 
#  An auto rigger I am currently working on. 
# 

import maya.cmds as cmds
import maya.mel as mm

# I am learning about dictionaries and attempting to place locators as joint markers named by combining values in the dictionary. I could do it with multiple lists, but this seems more interesting.   
body_dict = {'sides_list': ['L_','R_','C_'],
             'arms_list': ['shoulder','elbow','wrist'],
             'legs_list': ['thigh','knee','ankle', 'foot'],
             'spines_list': ['spine','pelvis','chest'],
             'hands_list': ['hand','thumb','index','middle','ring','pinky'],
             'neck_list': ['neck', 'head']} 

# Setting up FK IK Switch. This will later be implemented with the joint markers. 
def fkikbindswitch():
    # Selects fk, ik, and bind joints 
    brigdge_fk = cmds.ls('*_FK_JNT')
    brigdge_ik = cmds.ls('*_IK_JNT')
    brigdge_bind = cmds.ls('*_bind')
    for ik, fk, bind in zip(brigdge_ik, brigdge_fk, brigdge_bind):
        # Connecting translate, rotate, and scale attributes to blendcolor nodes 
        for attr in ['translate', 'rotate', 'scale']:
            bc = cmds.createNode('blendColors', n=bind.replace('bind_JNT', attr + '_BC'))
            cmds.connectAttr(ik + '.' + attr, bc + '.color1')
            cmds.connectAttr(fk + '.' + attr, bc + '.color2')
            cmds.connectAttr('*_switch' + '.FKIKSwitch', bc + '.blender')
            cmds.connectAttr(bc + '.output', bind + '.' + attr)
CreateJoints()
