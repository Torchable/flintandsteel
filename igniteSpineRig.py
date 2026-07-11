# Ignite Spine 
#
# Builds an FK/IK spine for Maya 2024+ from a chain of guide joints.
#
# The build only needs a pelvis guide and a chest guide at minimum. Every
# joint between them in the chain becomes a spine joint, so add as many
# in-between joints as the character needs. The rig you get includes:
#   - an FK control chain and an IK spline setup blended with an fkIk switch
#   - a stretchy chest (stretch attribute on the chest IK control)
#   - twist spread across the in-between joints with spline IK advanced
#     twist, driven by rotating the pelvis/chest IK controls
#   - IK tweak controls between the pelvis and chest to shape the spine

import math
import importlib

import maya.cmds as cmds
import ignite.igUtils as igUtils

importlib.reload(igUtils)


class spine_dict:
    sides = ['C_', 'L_', 'R_']
    spine = ['pelvis', 'spine', 'chest']


FORWARD_AXIS = {'X': 0, 'Y': 2, 'Z': 4}
WORLD_UP_AXIS = {'Y': 0, 'Z': 3, 'X': 6}


def spine(side='C', part='spine', pelvis_guide=None, chest_guide=None,
          remove_guides=False, add_stretch=True, color_dict=None,
          primary_axis='Y', up_axis='Z'):
    #Builds the FK/IK spine rig from the pelvis and chest guide joints.

    #The chest guide must be a descendant of the pelvis guide. Any joints found between the two become the in-between spine (twist) joints.

    if not side:
        side = 'C'
    if not part:
        part = 'spine'
    if not pelvis_guide or not cmds.objExists(pelvis_guide):
        cmds.error('Must provide a pelvis guide joint.')
    if not chest_guide or not cmds.objExists(chest_guide):
        cmds.error('Must provide a chest guide joint.')
    if pelvis_guide == chest_guide:
        cmds.error('Pelvis and chest guides must be two different joints.')
    if primary_axis[-1] == up_axis[-1]:
        cmds.error('Primary and up axis must be different axes.')

    # find every guide joint from the pelvis down to the chest
    guide_list = get_guide_chain(pelvis_guide, chest_guide)
    alias_list = get_alias_list(guide_list)

    pa = define_axis(primary_axis)

    # naming convention for the spine
    base_name = side + '_' + part

    # creates the FK, IK, bind chain
    ik_chain = create_chain(side, guide_list, alias_list, 'IK',
                            primary_axis, up_axis)
    fk_chain = create_chain(side, guide_list, alias_list, 'FK',
                            primary_axis, up_axis)
    bind_chain = create_chain(side, guide_list, alias_list, 'bind',
                              primary_axis, up_axis)

    # optimize control size by using a fraction of the pelvis-to-chest length
    r = distance_between(fk_chain[0], fk_chain[-1]) / float(5)

    # create FK controls and connect to fk joint chain
    fk_ctrls = []
    fk_top_grp = None
    par = None
    for i, alias in enumerate(alias_list):
        ctrl = cmds.circle(radius=r, normal=pa, degree=3,
                           name='{}_{}_FK_CTRL'.format(side, alias))[0]
        tag_control(ctrl, base_name + '_fk')
        if i != 0:
            # parent to previous control
            cmds.parent(ctrl, par)

        # align control to joint
        ctrl_off = igUtils.align_lras(snap_align=True, sel=[ctrl, fk_chain[i]])
        if i == 0:
            fk_top_grp = ctrl_off

        # define parent control to be used in iterations after the first one
        par = ctrl
        # connect control to joint
        cmds.parentConstraint(ctrl, fk_chain[i])
        fk_ctrls.append(ctrl)

    # create the pelvis and chest IK controls
    # (before the spline handle so the freeze inside a_to_b still works on
    # the clean IK joints)
    pelvis_ctrl = diamond_control('{}_{}_IK_CTRL'.format(side, alias_list[0]),
                                  r * 1.4, pa, primary_axis, ik_chain[0])
    tag_control(pelvis_ctrl, base_name + '_primary')

    chest_ctrl = diamond_control('{}_{}_IK_CTRL'.format(side, alias_list[-1]),
                                 r * 1.4, pa, primary_axis, ik_chain[-1])
    tag_control(chest_ctrl, base_name + '_primary')

    # build the spline IK curve through the ik joint positions
    points = [cmds.xform(j, query=True, worldSpace=True, rotatePivot=True)
              for j in ik_chain]
    if len(points) == 2:
        # minimum spine (pelvis + chest only), add a mid point so the tweak
        # control still has a part of the curve to pull on
        mid = [(a + b) * 0.5 for a, b in zip(points[0], points[1])]
        points.insert(1, mid)
    degree = 3 if len(points) > 3 else len(points) - 1
    ik_curve = cmds.curve(degree=degree, editPoint=points,
                          name=base_name + '_ik_CRV')
    crv_shape = cmds.listRelatives(ik_curve, shapes=True)[0]
    crv_shape = cmds.rename(crv_shape, ik_curve + 'Shape')

    # driver joints deform the curve, the controls drive the drivers
    pelvis_drv = create_driver('{}_{}_driver_JNT'.format(side, alias_list[0]),
                               target=ik_chain[0])
    chest_drv = create_driver('{}_{}_driver_JNT'.format(side, alias_list[-1]),
                              target=ik_chain[-1])

    # one tweak driver for every in-between joint, if the spine is only a
    # pelvis and chest then a single tweak driver sits at the mid point
    tweak_data = []
    if len(ik_chain) > 2:
        for i in range(1, len(ik_chain) - 1):
            weight = i / float(len(ik_chain) - 1)
            drv = create_driver('{}_{}_driver_JNT'.format(side, alias_list[i]),
                                target=ik_chain[i])
            tweak_data.append([alias_list[i], weight, drv])
    else:
        drv = create_driver('{}_spine_mid_driver_JNT'.format(side),
                            position=points[1])
        tweak_data.append(['spine_mid', 0.5, drv])

    driver_jnts = [pelvis_drv] + [t[2] for t in tweak_data] + [chest_drv]
    cmds.skinCluster(driver_jnts + [ik_curve], toSelectedBones=True,
                     maximumInfluences=2, name=base_name + '_ik_CRV_SCC')

    cmds.parentConstraint(pelvis_ctrl, pelvis_drv, maintainOffset=True)
    cmds.parentConstraint(chest_ctrl, chest_drv, maintainOffset=True)

    # create the IK tweak controls
    tweak_ctrls = []
    tweak_offs = []
    for alias, weight, drv in tweak_data:
        ctrl = cmds.circle(radius=r * 0.75, normal=pa, degree=3,
                           constructionHistory=False,
                           name='{}_{}_tweak_CTRL'.format(side, alias))[0]
        tag_control(ctrl, base_name + '_tweak')

        off = cmds.group(empty=True, name=ctrl + '_OFF_GRP')
        pos = cmds.xform(drv, query=True, worldSpace=True, rotatePivot=True)
        cmds.xform(off, worldSpace=True, translation=pos)
        cmds.parent(ctrl, off, relative=True)

        # tweaks ride between the pelvis and chest controls, weighted by
        # where they sit along the spine
        pcn = cmds.parentConstraint(pelvis_ctrl, chest_ctrl, off,
                                    maintainOffset=True)[0]
        cmds.setAttr(pcn + '.interpType', 2)
        weight_aliases = cmds.parentConstraint(pcn, query=True,
                                               weightAliasList=True)
        cmds.setAttr('{}.{}'.format(pcn, weight_aliases[0]), 1.0 - weight)
        cmds.setAttr('{}.{}'.format(pcn, weight_aliases[1]), weight)

        cmds.parentConstraint(ctrl, drv, maintainOffset=True)
        tweak_ctrls.append(ctrl)
        tweak_offs.append(off)

    # create the spline IKH
    ikh = cmds.ikHandle(name=base_name + '_ik_HDL', startJoint=ik_chain[0],
                        endEffector=ik_chain[-1], solver='ikSplineSolver',
                        createCurve=False, curve=ik_curve, parentCurve=False,
                        rootOnCurve=True)[0]

    # twist spreads across the in-between joints, rotating the pelvis or
    # chest control around the primary axis twists the spine
    setup_advanced_twist(ikh, pelvis_ctrl, chest_ctrl, primary_axis, up_axis)

    # add stretch
    no_xform_list = [ikh, ik_curve]
    ik_stretch = None
    if add_stretch:
        ik_stretch = add_ik_stretch(base_name, ik_chain, crv_shape,
                                    chest_ctrl, primary_axis)
        add_fk_stretch(fk_ctrls, fk_chain, primary_axis)

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
    settings_off = igUtils.align_lras(snap_align=True,
                                      sel=[settings_ctrl, ik_chain[-1]])
    cmds.setAttr(settings_ctrl + '.scale', r * 0.25, r * 0.25, r * 0.25)
    if up_axis[0] == '-':
        cmds.setAttr(settings_ctrl + '.translate' + up_axis[-1], r * -1.5)
    else:
        cmds.setAttr(settings_ctrl + '.translate' + up_axis[-1], r * 1.5)
    cmds.makeIdentity(settings_ctrl, apply=True, translate=True, rotate=True,
                      scale=True, normal=False)
    cmds.pointConstraint(bind_chain[-1], settings_ctrl, maintainOffset=True)

    cmds.addAttr(settings_ctrl, attributeType='double', min=0, max=1,
                 defaultValue=1, keyable=True, longName='fkIk')

    # fk/ik switch with blend color nodes
    blend_chains(base_name, ik_chain, fk_chain, bind_chain)

    # organize
    fk_ctrl_grp = cmds.group(em=True, name=base_name + '_FK_CTRL_GRP')
    ik_ctrl_grp = cmds.group(em=True, name=base_name + '_IK_CTRL_GRP')
    skeleton_grp = cmds.group(em=True, name=base_name + '_skeleton_GRP')
    drivers_grp = cmds.group(em=True, name=base_name + '_drivers_GRP')
    no_xform_grp = cmds.group(em=True, name=base_name + '_noXform_GRP')
    spine_rig_grp = cmds.group(em=True, name=base_name + '_rig_GRP')
    all_grp = cmds.group(em=True, name=base_name.upper())

    cmds.parent(pelvis_ctrl, chest_ctrl, ik_ctrl_grp)
    cmds.parent(tweak_offs, ik_ctrl_grp)
    cmds.parent(fk_top_grp, fk_ctrl_grp)
    cmds.parent(bind_chain[0], skeleton_grp)
    cmds.parent(driver_jnts, drivers_grp)
    cmds.parent(no_xform_list, no_xform_grp)
    cmds.parent(fk_ctrl_grp, ik_ctrl_grp, drivers_grp, no_xform_grp,
                fk_chain[0], ik_chain[0], settings_off, spine_rig_grp)
    cmds.parent(skeleton_grp, spine_rig_grp, all_grp)
    igUtils.transfer_pivots(sel=[bind_chain[0], skeleton_grp, spine_rig_grp,
                                 fk_ctrl_grp, ik_ctrl_grp])

    # the curve is deformed by the drivers in world space, so its group
    # cannot also inherit the rig group's transforms
    cmds.setAttr(no_xform_grp + '.inheritsTransform', 0)
    cmds.hide(no_xform_grp, drivers_grp, fk_chain[0], ik_chain[0],
              bind_chain[0])

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

    # finalize
    if not color_dict:
        color_dict = {base_name + '_primary': [1, 1, 0],
                      base_name + '_fk': [0, 0, 1],
                      base_name + '_tweak': [0, 1, 1]}

    for color_tag in cmds.ls(side + '_*.controlType'):
        ctrl = color_tag.split('.')[0]
        ctrl_type = cmds.getAttr(color_tag)
        if ctrl_type in color_dict:
            cmds.setAttr(ctrl + '.overrideEnabled', 1)
            cmds.setAttr(ctrl + '.overrideRGBColors', 1)
            cmds.setAttr(ctrl + '.overrideColorRGB',
                         color_dict[ctrl_type][0], color_dict[ctrl_type][1],
                         color_dict[ctrl_type][2])

    # Lock and hide attributes
    lock_and_hide(fk_ctrls, attribute_list=['translate', 'scale',
                                            'visibility'])
    lock_and_hide([pelvis_ctrl, chest_ctrl],
                  attribute_list=['scale', 'visibility'])
    lock_and_hide(tweak_ctrls, attribute_list=['scale', 'visibility'])
    lock_and_hide(settings_ctrl)

    # toggle fk/ik visibility
    vis_rev = cmds.createNode('reverse', name=base_name + '_fkIk_vis_REV')
    cmds.connectAttr(settings_ctrl + '.fkIk', vis_rev + '.inputX')
    cmds.connectAttr(settings_ctrl + '.fkIk', ik_ctrl_grp + '.visibility')
    cmds.connectAttr(vis_rev + '.outputX', fk_ctrl_grp + '.visibility')

    # remove guide joints
    if remove_guides:
        cmds.delete(guide_list[0])

    cmds.select(clear=True)
    print('Ignite: built the {} rig from {} guide joints.'.format(
        base_name, len(guide_list)))

    return {'all_grp': all_grp,
            'settings_ctrl': settings_ctrl,
            'pelvis_ctrl': pelvis_ctrl,
            'chest_ctrl': chest_ctrl,
            'tweak_ctrls': tweak_ctrls,
            'fk_ctrls': fk_ctrls,
            'bind_chain': bind_chain}


def get_guide_chain(pelvis_guide, chest_guide):
    """Walks up from the chest guide to the pelvis guide and returns the full
    guide chain ordered pelvis first."""
    pelvis_long = cmds.ls(pelvis_guide, long=True)
    chest_long = cmds.ls(chest_guide, long=True)
    if len(pelvis_long) != 1:
        cmds.error('More than one node matches the pelvis guide name, '
                   'please use a unique name.')
    if len(chest_long) != 1:
        cmds.error('More than one node matches the chest guide name, '
                   'please use a unique name.')

    chain = [chest_long[0]]
    current = chest_long[0]
    while current != pelvis_long[0]:
        par = cmds.listRelatives(current, parent=True, fullPath=True,
                                 type='joint')
        if not par:
            cmds.error('The chest guide must be below the pelvis guide in '
                       'the same joint chain.')
        current = par[0]
        chain.append(current)
    chain.reverse()

    return chain


def get_alias_list(guide_list):
    """Pelvis first, chest last, and spine_## for everything in between."""
    alias_list = [spine_dict.spine[0]]
    for i in range(1, len(guide_list) - 1):
        alias_list.append('{}_{:02d}'.format(spine_dict.spine[1], i))
    alias_list.append(spine_dict.spine[2])

    return alias_list


def create_chain(side, guide_list, alias_list, suffix, primary_axis='Y',
                 up_axis='Z'):
    """Creates a joint chain at the guide positions and orients it so the
    primary axis aims down the chain."""
    chain = []
    cmds.select(clear=True)
    for guide, alias in zip(guide_list, alias_list):
        pos = cmds.xform(guide, query=True, worldSpace=True, rotatePivot=True)
        jnt = cmds.joint(position=pos,
                         name='{}_{}_{}_JNT'.format(side, alias, suffix))
        chain.append(jnt)

    oj, sao = orient_strings(primary_axis, up_axis)
    cmds.joint(chain[0], edit=True, orientJoint=oj, secondaryAxisOrient=sao,
               children=True, zeroScaleOrient=True)
    cmds.joint(chain[-1], edit=True, orientJoint='none')
    cmds.select(clear=True)

    return chain


def create_driver(name, target=None, position=None):
    """Creates a world oriented joint used to skin the spline IK curve."""
    cmds.select(clear=True)
    drv = cmds.joint(name=name)
    if target:
        position = cmds.xform(target, query=True, worldSpace=True,
                              rotatePivot=True)
    cmds.xform(drv, worldSpace=True, translation=position)
    cmds.select(clear=True)

    return drv


def diamond_control(name, radius, pa, primary_axis, target):
    """Creates a four point diamond control and snaps it to the target."""
    ctrl = cmds.circle(radius=radius, normal=pa, degree=1, sections=4,
                       constructionHistory=False, name=name)[0]
    cmds.setAttr(ctrl + '.rotate' + primary_axis[-1], 45)
    igUtils.a_to_b(is_trans=True, is_rot=False, sel=[ctrl, target],
                   freeze=True)

    return ctrl


def curve_control(point_list, name, degree=1):
    crv = cmds.curve(degree=degree, editPoint=point_list, name=name)
    shp = cmds.listRelatives(crv, shapes=True)[0]
    cmds.rename(shp, crv + 'Shape')
    return crv


def setup_advanced_twist(ikh, pelvis_ctrl, chest_ctrl, primary_axis, up_axis):
    """Sets up the spline IK advanced twist so the pelvis and chest controls
    twist the spine, spreading the rotation across the in-between joints."""
    up_vec = define_axis(up_axis)
    cmds.setAttr(ikh + '.dTwistControlEnable', 1)
    # object rotation up (start/end)
    cmds.setAttr(ikh + '.dWorldUpType', 4)
    # the chains are always oriented with the positive primary axis aiming
    # down the chain and the positive up axis pointing at the up vector,
    # so only the axis letters matter here
    cmds.setAttr(ikh + '.dForwardAxis', FORWARD_AXIS[primary_axis[-1]])
    cmds.setAttr(ikh + '.dWorldUpAxis', WORLD_UP_AXIS[up_axis[-1]])
    cmds.setAttr(ikh + '.dWorldUpVector', up_vec[0], up_vec[1], up_vec[2],
                 type='double3')
    cmds.setAttr(ikh + '.dWorldUpVectorEnd', up_vec[0], up_vec[1], up_vec[2],
                 type='double3')
    cmds.connectAttr(pelvis_ctrl + '.worldMatrix[0]', ikh + '.dWorldUpMatrix')
    cmds.connectAttr(chest_ctrl + '.worldMatrix[0]',
                     ikh + '.dWorldUpMatrixEnd')


def blend_chains(base_name, ik_chain, fk_chain, bind_chain):
    # hook up switching
    for ik, fk, bind in zip(ik_chain, fk_chain, bind_chain):
        for attr in ['translate', 'rotate', 'scale']:
            bcn = cmds.createNode('blendColors',
                                  name=bind.replace('bind_JNT', attr + '_BCN'))
            cmds.connectAttr(ik + '.' + attr, bcn + '.color1')
            cmds.connectAttr(fk + '.' + attr, bcn + '.color2')
            cmds.connectAttr(base_name + '_settings_CTRL.fkIk',
                             bcn + '.blender')
            cmds.connectAttr(bcn + '.output', bind + '.' + attr)


# Stretchy chest, the ratio of the deformed curve length against its rest
# length drives the scale of the IK joints
def add_ik_stretch(base_name, ik_chain, crv_shape, chest_ctrl, primary_axis):
    curve_info = cmds.createNode('curveInfo', name=base_name + '_ik_CIN')
    cmds.connectAttr(crv_shape + '.worldSpace[0]', curve_info + '.inputCurve')
    length_total = cmds.getAttr(curve_info + '.arcLength')

    # calculate length ratio
    stretch_mdn = cmds.createNode('multiplyDivide',
                                  name=base_name + '_stretch_MDN')
    cmds.setAttr(stretch_mdn + '.operation', 2)
    cmds.connectAttr(curve_info + '.arcLength', stretch_mdn + '.input1X')
    cmds.setAttr(stretch_mdn + '.input2X', length_total)

    # add on/off for stretch
    cmds.addAttr(chest_ctrl, attributeType='double', min=0, max=1,
                 defaultValue=1, keyable=True, longName='stretch')
    stretch_bta = cmds.createNode('blendTwoAttr',
                                  name=base_name + '_stretch_BTA')
    cmds.setAttr(stretch_bta + '.input[0]', 1)
    cmds.connectAttr(stretch_mdn + '.outputX', stretch_bta + '.input[1]')
    cmds.connectAttr(chest_ctrl + '.stretch',
                     stretch_bta + '.attributesBlender')

    for jnt in ik_chain[:-1]:
        cmds.connectAttr(stretch_bta + '.output',
                         jnt + '.scale' + primary_axis[-1])

    # return dictionary to pass arguments into other function
    return_dict = {'length_total': length_total,
                   'mdn': stretch_mdn,
                   'curve_info': curve_info}

    return return_dict


def add_fk_stretch(fk_ctrls, fk_chain, primary_axis):
    for i, ctrl in enumerate(fk_ctrls):
        if not ctrl == fk_ctrls[-1]:
            cmds.addAttr(ctrl, attributeType='double', min=0.001,
                         defaultValue=1, keyable=True, longName='stretch')
            mdl = cmds.createNode('multDoubleLinear',
                                  name=ctrl.replace('_CTRL', '_stretch_MDL'))
            loc = cmds.spaceLocator(name=fk_chain[i + 1].replace(
                'JNT', 'OFF_LOC'))[0]
            cmds.parent(loc, fk_chain[i])
            igUtils.a_to_b(sel=[loc, fk_chain[i + 1]])
            offset_val = cmds.getAttr(loc + '.translate' + primary_axis[-1])
            cmds.setAttr(mdl + '.input1', offset_val)
            cmds.connectAttr(ctrl + '.stretch', mdl + '.input2')
            cmds.connectAttr(mdl + '.output',
                             loc + '.translate' + primary_axis[-1])
            cmds.connectAttr(ctrl + '.stretch',
                             fk_chain[i] + '.scale' + primary_axis[-1])
            cmds.connectAttr(loc + '.matrix',
                             fk_ctrls[i + 1] + '.offsetParentMatrix')


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


def orient_strings(primary_axis, up_axis):
    """Turns the primary/up axis picks into the orientJoint and
    secondaryAxisOrient strings the joint command wants."""
    p = primary_axis[-1].lower()
    u = up_axis[-1].lower()
    third = (set('xyz') - {p, u}).pop()
    orient_joint = p + u + third
    sec_axis_orient = u + ('down' if '-' in up_axis else 'up')

    return orient_joint, sec_axis_orient


# Creates the spine guide joints for the build setup. The pelvis sits at the
# origin with the chest on top, move the guides to fit the character before
# building. Only their positions are read by the build.
def spine_skeleton_setup(num_mid_joints=3):
    num_mid_joints = max(0, int(num_mid_joints))
    cmds.select(clear=True)

    pelvis_joint_setup = cmds.joint(position=(0, 0, 0),
                                    name='{}_{}_JNT'.format(
                                        spine_dict.spine[0], 1))
    for i in range(num_mid_joints):
        cmds.joint(position=(0, i + 1, 0),
                   name='{}_{}_JNT'.format(spine_dict.spine[1], i + 2))
    chest_joint_setup = cmds.joint(position=(0, num_mid_joints + 1, 0),
                                   name='{}_{}_JNT'.format(
                                       spine_dict.spine[2],
                                       num_mid_joints + 2))
    cmds.group(pelvis_joint_setup, name='spine_set_GRP')
    cmds.select(pelvis_joint_setup)

    return pelvis_joint_setup, chest_joint_setup
