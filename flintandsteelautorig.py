# Flint and Steel Auto Rigger
#
# By Colin Cheng

# Currently creates an FK IK arm when selecting a set of 3 joints

# Credits to Gnomon Workshop for creating the tutorial that taught me how to start this.
# I included a class containing a few lists to expand this auto rigger to beyond the arm, still a W.I.P however

import maya.cmds as cmds
import math
import importlib
import maya.mel as mm
import flintandsteel.shelfUtils as ScriptUtil

importlib.reload(ScriptUtil)


class body_dict:
    sides = ['L_', 'R_', 'C_']
    arms = ['shoulder', 'elbow', 'wrist']
    legs = ['thigh', 'knee', 'ankle', 'foot', 'toe']
    spine = ['spine', 'pelvis', 'chest']
    hands = ['hand', 'thumb', 'index', 'middle', 'ring', 'pinky']
    neck = ['neck', 'head']

bd = body_dict()

def limb(side=bd.sides[0], part=None, joint_list= None,
         alias_list= None, pole_vector= None,
         remove_guides=None, add_stretch=None, color_dict=None,
         primary_axis=None, up_axis=None):

    if len(joint_list) != 3:
        cmds.error('Must provide three guides to build three joint limb.')
        print('error 1 works')

    if len(alias_list) != 3:
        cmds.error('Must provide three aliases, one for each joint.')
        print('error 2 works')

    if not pole_vector:
        cmds.error('Must provide a pole vector guide.')
        print('error 3 works')

    pa = define_axis(primary_axis)
    ua = define_axis(up_axis)

    # naming convention for limb
    base_name = side + '_' + part

    # creates the FK, IK, bind chain
    ik_chain = create_chain(side, joint_list, alias_list, 'IK')
    fk_chain = create_chain(side, joint_list, alias_list, 'FK')
    bind_chain = create_chain(side, joint_list, alias_list, 'bind')

    # optimize control size by using a fraction of the start-to-end length
    r = distance_between(fk_chain[0], fk_chain[-1]) / float(5)

    # create FK controls and connect to fk joint chain
    fk_ctrls = []
    for i, alias in enumerate(alias_list):
        # create FK controls
        ctrl = cmds.circle(radius=r, normal=pa, degree=3,
                           name='{}_{}_FK_CTRL'.format(side, alias))[0]
        tag_control(ctrl, base_name + '_fk')
        if i != 0:
            # parent to previous control
            cmds.parent(ctrl, par)

        # align control to joint
        ctrl_off = ScriptUtil.align_lras(snap_align=True, sel=[ctrl, fk_chain[i]])
        if i == 0:
            fk_top_grp = ctrl_off

        # define parent control to be used in iterations after the first one
        par = ctrl
        # connect control to joint
        cmds.pointConstraint(ctrl, fk_chain[i])
        cmds.connectAttr(ctrl + '.rotate', fk_chain[i] + '.rotate')
        fk_ctrls.append(ctrl)

    # create IK controls
    world_ctrl = cmds.circle(radius=r * 1.2, normal=pa, degree=1, sections=4,
                             constructionHistory=False,
                             name=base_name + '_IK_CTRL')[0]
    cmds.setAttr(world_ctrl + '.rotate' + primary_axis[-1], 45)
    ScriptUtil.a_to_b(is_trans=True, is_rot=False, sel=[world_ctrl, ik_chain[-1]],
                      freeze=True)
    tag_control(world_ctrl, base_name + '_primary')

    local_ctrl = cmds.circle(radius=r, normal=pa, degree=1, sections=4,
                             name=base_name + '_local_IK_CTRL')[0]
    cmds.setAttr(local_ctrl + '.rotate' + primary_axis[-1], 45)
    cmds.makeIdentity(local_ctrl, apply=True, rotate=True)
    local_off = ScriptUtil.align_lras(snap_align=True,
                                      sel=[local_ctrl, ik_chain[-1]])
    cmds.parent(local_off, world_ctrl)
    tag_control(local_ctrl, base_name + '_secondary')

    # PV scaling + creation 
    loc_points = [[0.0, 1.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 0.0],
                  [-1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                  [0.0, 0.0, -1.0], [0.0, 0.0, 1.0]]
    pv_ctrl = curve_control(loc_points, name=base_name + '_PV_CTRL')
    cmds.setAttr(pv_ctrl + '.scale', r * 0.25, r * 0.25, r * 0.25)
    ScriptUtil.a_to_b(is_trans=True, is_rot=False, sel=[pv_ctrl, pole_vector],
                      freeze=True)
    tag_control(pv_ctrl, base_name + '_pv')

    base_ctrl = cmds.circle(radius=r * 1.2, normal=pa, degree=1,
                            sections=4, constructionHistory=False,
                            name='{}_{}_IK_CTRL'.format(side, alias_list[0]))[0]
    cmds.setAttr(base_ctrl + '.rotate' + primary_axis[-1], 45)
    ScriptUtil.a_to_b(is_trans=True, is_rot=False, sel=[base_ctrl, ik_chain[0]],
                      freeze=True)
    cmds.parentConstraint(base_ctrl, ik_chain[0], mo=True)
    tag_control(base_ctrl, base_name + '_primary')

    # create IKH
    ikh = cmds.ikHandle(name=base_name + 'IK_HDL', startJoint=ik_chain[0],
                        endEffector=ik_chain[-1], sticky='sticky',
                        solver='ikRPsolver', setupForRPsolver=True)[0]
    cmds.parentConstraint(local_ctrl, ikh, mo=True)
    cmds.poleVectorConstraint(pv_ctrl, ikh)

    # FK IK Switch creation 
    plus_points = [[-0.333, 0.333, 0.0], [-0.333, 1.0, 0.0],
                   [0.333, 1.0, 0.0], [0.333, 0.333, 0.0],
                   [1.0, 0.333, 0.0], [1.0, -0.333, 0.0],
                   [0.333, -0.333, 0.0], [0.333, -1.0, 0.0],
                   [-0.333, -1.0, 0.0], [-0.333, -0.333, 0.0],
                   [-1.0, -0.333, 0.0], [-1.0, 0.333, 0.0],
                   [-0.333, 0.333, 0.0]]
    settings_ctrl = curve_control(point_list=plus_points,
                                  name=base_name + '_settings_CTRL')
    tag_control(settings_ctrl, base_name + '_primary')
    settings_off = ScriptUtil.align_lras(snap_align=True,
                                         sel=[settings_ctrl, ik_chain[-1]])
    cmds.setAttr(settings_ctrl + '.scale', r * 0.25, r * 0.25, r * 0.25)
    if up_axis[0] == '-':
        cmds.setAttr(settings_ctrl + '.translate' + up_axis[-1], r * -1.5)
    else:
        cmds.setAttr(settings_ctrl + '.translate' + up_axis[-1], r * 1.5)
    cmds.makeIdentity(settings_ctrl, apply=True, translate=True, rotate=True,
                      scale=True, normal=False)
    cmds.pointConstraint(bind_chain[-1], settings_ctrl, mo=True)

    cmds.addAttr(settings_ctrl, attributeType='double', min=0, max=1,
                 defaultValue=1, keyable=True, longName='fkIk')

    # fk/ik switch with blend color nodes
    blend_chains(base_name, ik_chain, fk_chain, bind_chain)

    # add stretch
    no_xform_list = [ikh]
    if add_stretch:
        ik_stretch = add_ik_stretch(side, part, ik_chain, base_ctrl, local_ctrl,
                                    world_ctrl, primary_axis)
        add_fk_stretch(fk_ctrls, fk_chain, primary_axis)
        no_xform_list += ik_stretch['measure_locs']

    # organize
    fk_ctrl_grp = cmds.group(em=True, name=base_name + '_FK_CTRL_GRP')
    ik_ctrl_grp = cmds.group(em=True, name=base_name + '_IK_CTRL_GRP')
    skeleton_grp = cmds.group(em=True, name=base_name + '_skeleton_GRP')
    no_xform_grp = cmds.group(em=True, name=base_name + '_noXform_GRP')
    limb_rig_grp = cmds.group(em=True, name=base_name + '_rig_GRP')
    all_grp = cmds.group(em=True, name=base_name.upper())

    cmds.parent(world_ctrl, pv_ctrl, base_ctrl, ik_ctrl_grp)
    cmds.parent(fk_top_grp, fk_ctrl_grp)
    cmds.parent(bind_chain[0], skeleton_grp)
    cmds.parent(no_xform_list, no_xform_grp)
    cmds.parent(fk_ctrl_grp, ik_ctrl_grp, no_xform_grp, fk_chain[0],
                ik_chain[0], settings_off, limb_rig_grp)
    cmds.parent(skeleton_grp, limb_rig_grp, all_grp)
    ScriptUtil.transfer_pivots(sel=[bind_chain[0], skeleton_grp, limb_rig_grp,
                                    fk_ctrl_grp, ik_ctrl_grp])
    cmds.hide(no_xform_grp, fk_chain[0], ik_chain[0], bind_chain[0])

    # compensate for global scale
    cmds.addAttr(all_grp, attributeType='double', min=0.001, defaultValue=1,
                 keyable=True, longName='globalScale')
    [cmds.connectAttr(all_grp + '.globalScale',
                      all_grp + '.scale' + axis) for axis in 'XYZ']
    if add_stretch:
        gs_mdl = cmds.createNode('multDoubleLinear',
                                 name=base_name + '_globalScale_MDL')
        cmds.setAttr(gs_mdl + '.input1', ik_stretch['length_total'])
        cmds.connectAttr(all_grp + '.globalScale', gs_mdl + '.input2')
        cmds.connectAttr(gs_mdl + '.output', ik_stretch['mdn'] + '.input2X')
        cmds.connectAttr(gs_mdl + '.output', ik_stretch['cnd'] + '.secondTerm')

    # finalize
    if not color_dict:
        color_dict = {base_name + '_primary': [1, 1, 0],
                      base_name + '_pv': [0, 1, 1],
                      base_name + '_fk': [0, 0, 1],
                      base_name + '_secondary': [0, 0.2, 1]}

    for color_tag in cmds.ls(side + '*.controlType'):
        ctrl = color_tag.split('.')[0]
        ctrl_type = cmds.getAttr(color_tag)
        if base_name in ctrl_type:
            cmds.setAttr(ctrl + '.overrideEnabled', 1)
            cmds.setAttr(ctrl + '.overrideRGBColors', 1)
            cmds.setAttr(ctrl + '.overrideColorRGB',
                         color_dict[ctrl_type][0], color_dict[ctrl_type][1],
                         color_dict[ctrl_type][2])

    # Lock and hide attributes
    lock_and_hide(fk_ctrls, attribute_list=['translate', 'scale', 'visibility'])
    lock_and_hide([world_ctrl, local_ctrl, base_ctrl],
                  attribute_list=['scale', 'visibility'])
    lock_and_hide(pv_ctrl, attribute_list=['rotate', 'scale', 'visibility'])
    lock_and_hide(settings_ctrl)

    # toggle fk/ik visibility
    vis_rev = cmds.createNode('reverse', name=base_name + '_fkIk_vis_REV')
    cmds.connectAttr(settings_ctrl + '.fkIk', vis_rev + '.inputX')
    cmds.connectAttr(settings_ctrl + '.fkIk', ik_ctrl_grp + '.visibility')
    cmds.connectAttr(vis_rev + '.outputX', fk_ctrl_grp + '.visibility')

    pv_gde = add_guide(pv_ctrl, ik_chain)
    cmds.parent(pv_gde[0], no_xform_grp)
    cmds.parent(pv_gde[1], ik_ctrl_grp)

    # remove guide joints
    if remove_guides:
        cmds.delete(joint_list, pole_vector)


def pole_vector(pv_name):
    pv_name = bd.sides[1] + bd.arms[0] + '*_PV_CTRL'


def add_guide(start, end):
    start_pos = cmds.xform(start, query=True, worldSpace=True, rotatePivot=True)
    end_pos = cmds.xform(end, query=True, worldSpace=True, rotatePivot=True)

    gde = curve_control([start_pos, end_pos], name=start + '_GDE')
    start_cls = cmds.cluster(gde + '.cv[0]', name=start + '_CLS')[1]
    end_cls = cmds.cluster(gde + '.cv[1]', name=end + '_CLS')[1]
    cmds.pointConstraint(start, start_cls)
    cmds.pointConstraint(end, end_cls)
    cmds.setAttr(gde + '.template', True)
    cmds.setAttr(gde + '.inheritsTransform', False)

    return [[start_cls, end_cls], gde]


def curve_control(point_list, name, degree=1):
    crv = cmds.curve(degree=degree, editPoint=point_list, name=name)
    shp = cmds.listRelatives(crv, shapes=True)[0]
    cmds.rename(shp, crv + 'Shape')
    return crv


def blend_chains(base_name, ik_chain, fk_chain, bind_chain):
    # hook up switching
    for ik, fk, bind in zip(ik_chain, fk_chain, bind_chain):
        for attr in ['translate', 'rotate', 'scale']:
            bcn = cmds.createNode('blendColors',
                                  name=bind.replace('bind_JNT', attr + '_BCN'))
            cmds.connectAttr(ik + '.' + attr, bcn + '.color1')
            cmds.connectAttr(fk + '.' + attr, bcn + '.color2')
            cmds.connectAttr(base_name + '_settings_CTRL.fkIk', bcn + '.blender')
            cmds.connectAttr(bcn + '.output', bind + '.' + attr)


def add_ik_stretch(side, part, ik_chain, base_ctrl, local_ctrl, world_ctrl,
                   primary_axis):
    base_name = side + '_' + part

    # create measure nodes for stretch
    limb_dist = cmds.createNode('distanceBetween', name=base_name + '_DST')
    limb_cnd = cmds.createNode('condition', name=base_name + '_CND')
    start_loc = cmds.spaceLocator(name=base_name + '_start_LOC')[0]
    end_loc = cmds.spaceLocator(name=base_name + '_end_LOC')[0]
    stretch_mdn = cmds.createNode('multiplyDivide',
                                  name=base_name + '_stretch_MDN')

    # calculate length
    length_a = distance_between(ik_chain[0], ik_chain[1])
    length_b = distance_between(ik_chain[1], ik_chain[2])
    length_total = length_a + length_b

    # measure limb length
    cmds.pointConstraint(base_ctrl, start_loc, maintainOffset=False)
    cmds.pointConstraint(local_ctrl, end_loc, maintainOffset=False)
    cmds.connectAttr(start_loc + '.worldMatrix[0]', limb_dist + '.inMatrix1')
    cmds.connectAttr(end_loc + '.worldMatrix[0]', limb_dist + '.inMatrix2')

    # calculate length ratio
    cmds.connectAttr(limb_dist + '.distance', stretch_mdn + '.input1X')
    cmds.setAttr(stretch_mdn + '.input2X', length_total)
    cmds.setAttr(stretch_mdn + '.operation', 2)

    cmds.connectAttr(limb_dist + '.distance', limb_cnd + '.firstTerm')
    cmds.connectAttr(stretch_mdn + '.outputX', limb_cnd + '.colorIfTrueR')
    cmds.setAttr(limb_cnd + '.secondTerm', length_total)
    cmds.setAttr(limb_cnd + '.operation', 3)

    # add on/off for stretch
    cmds.addAttr(world_ctrl, attributeType='double', min=0, max=1,
                 defaultValue=1, keyable=True, longName='stretch')
    up_name = 'up' + part.title()
    lo_name = 'lo' + part.title()
    cmds.addAttr(world_ctrl, attributeType='double', min=0.001, defaultValue=1,
                 keyable=True, longName=up_name)
    cmds.addAttr(world_ctrl, attributeType='double', min=0.001, defaultValue=1,
                 keyable=True, longName=lo_name)
    stretch_bta = cmds.createNode('blendTwoAttr',
                                  name=base_name + '_stretch_BTA')
    cmds.setAttr(stretch_bta + '.input[0]', 1)
    cmds.connectAttr(limb_cnd + '.outColorR', stretch_bta + '.input[1]')
    cmds.connectAttr(world_ctrl + '.stretch',
                     stretch_bta + '.attributesBlender')
    up_pma = cmds.createNode('plusMinusAverage', name=up_name + '_PMA')
    lo_pma = cmds.createNode('plusMinusAverage', name=lo_name + '_PMA')
    cmds.connectAttr(world_ctrl + '.' + up_name, up_pma + '.input1D[0]')
    cmds.connectAttr(world_ctrl + '.' + lo_name, lo_pma + '.input1D[0]')
    cmds.connectAttr(stretch_bta + '.output', up_pma + '.input1D[1]')
    cmds.connectAttr(stretch_bta + '.output', lo_pma + '.input1D[1]')
    cmds.setAttr(up_pma + '.input1D[2]', -1)
    cmds.setAttr(lo_pma + '.input1D[2]', -1)

    cmds.connectAttr(up_pma + '.output1D',
                     ik_chain[0] + '.scale' + primary_axis[-1])
    cmds.connectAttr(lo_pma + '.output1D',
                     ik_chain[1] + '.scale' + primary_axis[-1])

    # return dictionary to pass arguments into other function
    return_dict = {'measure_locs': [start_loc, end_loc],
                   'length_total': length_total,
                   'mdn': stretch_mdn,
                   'cnd': limb_cnd}

    return return_dict


def add_fk_stretch(fk_ctrls, fk_chain, primary_axis):
    for i, ctrl in enumerate(fk_ctrls):
        if not ctrl == fk_ctrls[-1]:
            cmds.addAttr(ctrl, attributeType='double', min=0.001,
                         defaultValue=1, keyable=True, longName='stretch')
            mdl = cmds.createNode('multDoubleLinear',
                                  name=ctrl.replace('CTRL', '_stretch_MDL'))
            loc = cmds.spaceLocator(name=fk_chain[i + 1].replace(
                'JNT', 'OFF_LOC'))[0]
            cmds.parent(loc, fk_chain[i])
            ScriptUtil.a_to_b(sel=[loc, fk_chain[i + 1]])
            offset_val = cmds.getAttr(loc + '.translate' + primary_axis[-1])
            cmds.setAttr(mdl + '.input1', offset_val)
            cmds.connectAttr(ctrl + '.stretch', mdl + '.input2')
            cmds.connectAttr(mdl + '.output',
                             loc + '.translate' + primary_axis[-1])
            cmds.connectAttr(ctrl + '.stretch',
                             fk_chain[i] + '.scale' + primary_axis[-1])
            if cmds.objExists(fk_ctrls[i + 1] + '.offsetParentMatrix'):
                cmds.connectAttr(loc + '.matrix',
                                 fk_ctrls[i + 1] + '.offsetParentMatrix')
            else:
                dcm = cmds.createNode('decomposeMatrix', name=loc + '_DCM')
                cmds.connectAttr(loc + '.matrix', dcm + '.inputMatrix')
                for attr in ['translate', 'rotate', 'scale']:
                    cmds.connectAttr(dcm + '.output' + attr.title(),
                                     fk_ctrls[i + 1] + '_OFF_GRP.' + attr)


def tag_control(ctrl, tag_name):
    cmds.addAttr(ctrl, ln='controlType', dataType='string')
    cmds.setAttr(ctrl + '.controlType', tag_name, type='string')


def lock_and_hide(nodes, attribute_list=None):
    if not attribute_list:
        attribute_list = ['translate', 'rotate', 'scale', 'visibility']

    if not isinstance(nodes, list):
        nodes = [nodes]

    for node in nodes:
        for attr in attribute_list:
            if any(t == attr for t in ['translate', 'rotate', 'scale']):
                [cmds.setAttr(node + '.' + attr + axis,
                              lock=True, keyable=False) for axis in 'XYZ']
            else:
                cmds.setAttr(node + '.' + attr, lock=True, keyable=False)


def create_chain(side, joint_list, alias_list, suffix):
    chain = []
    for j, a in zip(joint_list, alias_list):
        if j == joint_list[0]:
            par = None
        else:
            par = jnt
        jnt = cmds.joint(par, n='{}_{}_{}_JNT'.format(side, a, suffix))
        ScriptUtil.a_to_b(sel=[jnt, j], freeze=True)
        chain.append(jnt)

    return chain


# Checks distance between point A and point B
def distance_between(node_a, node_b):
    point_a = cmds.xform(node_a, query=True, worldSpace=True, rotatePivot=True)
    point_b = cmds.xform(node_b, query=True, worldSpace=True, rotatePivot=True)

    dist = math.sqrt(sum([pow((b - a), 2) for b, a in zip(point_b, point_a)]))
    return dist

def define_axis(axis):
    if axis[-1] == 'X':
        vector_axis = (1, 0, 0)
    elif axis[-1] == 'Y':
        vector_axis = (0, 1, 0)
    elif axis[-1] == 'Z':
        vector_axis = (0, 0, 1)
    else:
        cmds.error('Must provide either X, Y, or Z for the axis.')

    if '-' in axis:
        vector_axis = tuple(va * -1 for va in vector_axis)
    return vector_axis
