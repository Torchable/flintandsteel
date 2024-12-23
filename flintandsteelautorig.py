#Flint and Steel Auto Rigger 
# by Colin Cheng 

# Current a W.I.P, but learning how to make my own auto-rigger 

import maya.cmds as cmds
import maya.mel as mm
import math
import bRIGdgeScript.shelfUtils as shelfutils
               
def limb(side = 'L', part = 'arm', joint_list = ['L_shoulder_gde_JNT', 'L_elbow_gde_JNT', 'L_wrist_gde_JNT'], 
         alias_list=['shoulder', 'elbow', 'wrist'],
         pole_vector = 'L_shoulder_pv_gde_LOC', remove_guides=False,
         add_stretch=False, color_dict=False, primary_axis = 'X', up_axis = 'Y'): 
         # limb naming convention     
         base_name =  side + '_' + part 
         #creating fk, ik and bind chain 
         ik_chain = create_chain(side, joint_list, alias_list, 'IK')
         fk_chain = create_chain(side, joint_list, alias_list, 'FK')
         bind_chain = create_chain(side, joint_list, alias_list, 'bind')
         
         #fk ik switch with blend color nodes 
         blend_chains(base_name, ik_chain, fk_chain, bind_chain)
         
         #For setting axis of control 
         pa = define_axis(primary_axis)  
                
         fk_ctrls = []
         for i, alias in enumerate(alias_list):
             ctrl = cmds.circle(radius=r, normal=pa, degree=3, name='{}_{}_FK_CTRL'.format(side, alias))[0]
             
             if i != 0:
                 cmds.parent(ctrl, par)
         
         # align control to joint 
             ctrl_off = limb.align_lras(snap_align = True, sel=[ctrl], fk_chain[i]) 
             if i==0:
                 fk_top_grp = ctrl_off
             par = ctrl
             # connecting control to joint 
             cmds.parentConstraint(ctrl, fkchain[i])
             fk_ctrls.append(ctrl)
         
         # error response 
         if len(joint_list) != 3:
             print('must provide 3 guides')
         
         if len(alias_list) != 3: 
             print('must provide 3 aliases')
         
         if not pole_vector: 
             print('not a pole vector')
         
def loc_creation(body_dict):
    #Dictionary for calling locators  
    body_dict = {'sides_list': ['L_','R_','C_'],
                 'arms_list': ['shoulder','elbow','wrist'],
                 'legs_list': ['thigh','knee','ankle', 'foot', 'toe'],
                 'spines_list': ['spine','pelvis','chest'],
                 'hands_list': ['hand','thumb','index','middle','ring','pinky'],
                 'neck_list': ['neck', 'head']}
    #Creates locators for each item in the dictionary 
    for key, value in body_dict.items():
        x = 0
        y = 0
        z = 2
        for item in value:
            if item in body_dict['spines_list']:
                cmds.spaceLocator(n = body_dict['sides_list'][z] + body_dict['spines_list'][x] + '_LOC')
                x = x + 1
                    
            elif item in body_dict['neck_list']:
                cmds.spaceLocator(n = body_dict['sides_list'][z] + body_dict['neck_list'][x] + '_LOC')
                x = x + 1

            elif item in body_dict['arms_list']:
                cmds.spaceLocator(n = body_dict['sides_list'][y] + body_dict['arms_list'][x] + '_LOC')
                cmds.spaceLocator(n = body_dict['sides_list'][y + 1] + body_dict['arms_list'][x] + '_LOC')
                x = x + 1   
            elif item in body_dict['legs_list']:
                cmds.spaceLocator(n = body_dict['sides_list'][y] + body_dict['legs_list'][x] + '_LOC')
                cmds.spaceLocator(n = body_dict['sides_list'][y + 1] + body_dict['legs_list'][x] + '_LOC')
                x = x + 1
            elif item in body_dict['hands_list']:
                cmds.spaceLocator(n = body_dict['sides_list'][y] + body_dict['hands_list'][x] + '_LOC')
                cmds.spaceLocator(n = body_dict['sides_list'][y + 1] + body_dict['hands_list'][x] + '_LOC')
                x = x + 1
    #jointset = []
    #for i, alias in enumerate(body_dict):
             
                        
def fkikbindswitch():
    #combines fk and ik to the bind for switching 
    brigdge_fk = cmds.ls('*_FK_JNT')
    brigdge_ik = cmds.ls('*_IK_JNT')
    brigdge_bind = cmds.ls('*_bind')
    brigdge_switch = cmds.ls('*_switch')
    for ik, fk, bind in zip(brigdge_ik, brigdge_fk, brigdge_bind):
        for attr in ['translate', 'rotate', 'scale']:
            bc = cmds.createNode('blendColors', n=bind.replace('bind_JNT', attr + '_BC'))
            cmds.connectAttr(ik + '.' + attr, bc + '.color1')
            cmds.connectAttr(fk + '.' + attr, bc + '.color2')
            cmds.connectAttr('*_switch' + '.FKIKSwitch', bc + '.blender')
            cmds.connectAttr(bc + '.output', bind + '.' + attr)
            
def blend_chain(base_name, ik_chain, fk_chain, bind_chain):
    #hook up switching
    for ik, fk , bind in zip(ik_chain, fk_chain, bind_chain): 
        for attr in ['translate', 'rotate', 'scale']: 
            bcn = cmds.createNode('blendColors', n= bind.replace('bind_JNT', attr +'_BCN'))
            cmds.connectAttr(ik + '.' + attr, bcn + '.color1')
            cmds.connectAttr(fk + '.' + attr, bcn + '.color2')
            cmds.connectAttr(base_name + '_settings_CTRL.fkIk', bcn + '.blender')
            cmds.connectAttr(bcn + 'output', bind + '.' + attr)  
             
def create_chain(side, joint_list, alias_list, suffix):
    #builds fk ik bind chain 
    chain = []
    for j, a in zip(joint_list, alias_list):
        if j == joint_list[0]:
            par = None
        else:
            par = jnt
        jnt = cmds.joint(par, n= '{}_{}_{}_JNT'.format(side, a, suffix))
        shelfutils.a_to_b(sel=[jnt, j], freeze=True)
        chain.append(jnt)
    return chain
          
def define_axis(axis):
    if axis[-1] == 'X': 
        vector_axis = (1,0,0)
        
    elif axis[-1] == 'Y': 
        vector_axis = (0,1,0) 
           
    elif axis[-1] == 'Z':
        vector_axis = (0,0,1)
    else:
        cmds.error('Error in defining axis') 
        
    if '-' in axis:
        vector_axis = tuple(va * -1 for va in vector_axis)
    return vector_axis
    
def distance_between(node_a, node_b):
    #calculates the distance between points to create stretchy arm 
    point_a = cmds.xform(node_a,query = True, worldSpace = True, rotatePivot = True)
    point_b = cmds.xform(node_b,query = True, worldSpace = True, rotatePivot = True)
    
    dist = math.sqrt(sum([pow((b-a), 2) for b, a in zip(point_b, point_a)]))
    return dist

def curve_control(point_list, name, degree = 1):
    crv = cmds.curve(degree=degree, editpoint = point_list, name=name)
    shp = cmds.listRelatives(shapes = True)[0]
    cmds.rename(shp, crv + 'shape')
    return crv           
 
