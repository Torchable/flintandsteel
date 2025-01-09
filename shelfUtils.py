import maya.cmds as cmds
import maya.mel as mel
'''
import maya.cmds as cmds
import flintandsteel.shelfUtils as fasUtil
reload(fasUtil)
fasUtil.group_special()
'''

def create_centered_loc():
    sel = cmds.ls(selection=True)
    # check if the selection has components
    if any('.' in s for s in sel):
        name = sel[0]
        if '.' in name:
            name = name.split('.')[0]

        # create a cluster and return the handle
        cls = cmds.cluster(sel)[1]
        loc = cmds.spaceLocator(name=name + '_LOC')[0]

        # move loc to cluster and delete cluster
        cmds.delete(cmds.parentConstraint(cls, loc), cls)

    # otherwise use transform with a_to_b
    else:
        for s in sel:
            loc = cmds.spaceLocator(name=s + '_LOC')[0]
            a_to_b(is_trans=True, is_rot=True, sel=[loc, s])

def a_to_b(is_trans=True, is_rot=True, sel=None, freeze=False):
    # if selection list is not defined, use selected in scene
    if not sel:
        sel = cmds.ls(selection=True)

    for s in sel:
        # make sure translate/rotate is not locked before moving
        tr_list = []
        if is_trans:
            tr_list.append('translate')
            if any(cmds.getAttr(s + '.translate' + attr, lock=True) for attr in 'XYZ'):
                cmds.error('This will not work if any translate attributes are locked!')
        if is_rot:
            tr_list.append('rotate')
            if any(cmds.getAttr(s + '.rotate' + attr, lock=True) for attr in 'XYZ'):
                cmds.error('This will not work if any rotate attributes are locked!')

        if s != sel[-1]:
            con_list = []
            # check for objects with any transformation connections
            # add them to con_list if a connection exists
            for tr in tr_list:
                con = cmds.listConnections(s + '.' + tr, destination=False,
                                           source=True, plugs=True)
                if con:
                    [con_list.append(c) for c in con]
                for attr in 'XYZ':
                    con = cmds.listConnections(s + '.' + tr + attr,
                                               destination=False, source=True,
                                               plugs=True)
                    if con:
                        [con_list.append(c) for c in con]

            # check for translate/rotate attribute string in lists
            has_trans = any('ranslate' in con for con in con_list)
            has_rot = any('otate' in con for con in con_list)

            # skip if there are connections
            if has_trans and has_rot:
                print(s + ' has incoming translation and rotation connections '\
                      'and was not constrained to destination object.')
                continue
            elif has_trans and not has_rot:
                print(s + ' has incoming translation connections and was not '\
                                      'constrained to destination object.')
                continue
            elif has_rot and not has_trans:
                print(s + ' has incoming rotation connections and was not '\
                                      'constrained to destination object.')
                continue

            # if their attributes are not locked/connected, then let's move them
            else:
                if is_trans:
                    cmds.delete(cmds.pointConstraint(sel[-1], s,
                                                     maintainOffset=False))
                if is_rot:
                    cmds.delete(cmds.orientConstraint(sel[-1], s,
                                                      maintainOffset=False))
        if freeze:
            cmds.makeIdentity(s, apply=True, translate=True, rotate=True,
                              scale=True, normal=False)

# makes one group, matchs pivot/naming of first selected, and adds '_GRP' suffix
def group_special():
    # get selection
    sel = cmds.ls(selection=True)

    # get pivot of last selected object
    last_pos = cmds.xform(sel[-1], query=True, rotatePivot=True,
                          worldSpace=True)

    # group selection, rename, and match pivot
    grp = cmds.group(sel, name=sel[-1] + '_GRP')
    cmds.xform(grp, worldSpace=True, pivots=last_pos)

# group, match pivot, and add '_GRP' suffix to each selected object
def group_all_special():
    # get selection
    sel = cmds.ls(selection=True)

    for s in sel:
        # get selected objects pivot and match group's pivot to it
        piv = cmds.xform(s, query=True, rotatePivot=True, worldSpace=True)
        grp = cmds.group(s, name=s + '_GRP')
        cmds.xform(grp, worldSpace=True, pivots=piv)

# print python formatted list
def print_list():
    print("[" + "',\n".join("'" + s for s in cmds.ls(selection=True)) + "']")

# print the selection size
def print_len():
    print(len(cmds.ls(selection=True)))

# copy weights from one object to many, will work with referenced geo that has
# a similar set of joint influences
def copy_referenced_weights():
    # get selection
    sel = cmds.ls(selection=True)

    # use mel command to find first selected's skin cluster
    old_skin = mel.eval('findRelatedSkinCluster ' + sel[0])

    # get the skinning method of source skin cluster
    skin_method = cmds.getAttr(old_skin + '.skinningMethod')

    # make a list of source skin cluster influences
    old_joints = cmds.skinCluster(sel[0], query=True, influence=True)

    # make a new
    new_joints = []
    for jnt in old_joints:
        # strip namespace for the joints we're copying influences to
        new_joints.append(jnt.rpartition(':')[2])

    for s in sel[1:]:
        # bind object to new joints
        new_skin = cmds.skinCluster(new_joints, s,
                                    name=s + '_SCC', toSelectedBones=True)[0]
        # copy skin weights from old skin to new skin
        cmds.copySkinWeights(ss=old_skin, ds=new_skin, nm=True,
                             sa='closestPoint', ia='oneToOne')
        # match the skinning methods
        cmds.setAttr(new_skin + '.skinningMethod', skin_method)

# transfers pivots to either first selected object or origin
def transfer_pivots(origin=False, sel=False):
    # if selection list is not defined, use selected in scene
    if not sel:
        sel = cmds.ls(selection=True)

    # move pivot to origin
    if origin:
        for s in sel:
            cmds.xform(s, worldSpace=True, pivots=(0, 0, 0))

    # move pivot to first selected object
    else:
        # get the rotate pivot
        first_piv = cmds.xform(sel[0], query=True, worldSpace=True,
                               rotatePivot=True)
        for s in sel[1:]:
            # set the rotate and scale pivot simultaneously
            cmds.xform(s, worldSpace=True, pivots=first_piv)

# align local rotation axes of control to the joint
def align_lras(snap_align=False, delete_history=True, sel=None):
    # get selection (first ctrl, then joint)
    if not sel:
        sel = cmds.ls(selection=True)

    if len(sel) <= 1:
        cmds.error('Select the control first, then the joint to align.')
    ctrl = sel[0]
    jnt = sel[1]

    # check to see if the control has a parent
    # if it does, un parent it by parenting it to the world
    parent_node = cmds.listRelatives(ctrl, parent=True)
    if parent_node:
        cmds.parent(ctrl, world=True)

    # store the ctrl/joint's world space position, rotation, and matrix
    jnt_matrix = cmds.xform(jnt, query=True, worldSpace=True, matrix=True)
    jnt_pos = cmds.xform(jnt, query=True, worldSpace=True, rotatePivot=True)
    jnt_rot = cmds.xform(jnt, query=True, worldSpace=True, rotation=True)
    ctrl_pos = cmds.xform(ctrl, query=True, worldSpace=True, rotatePivot=True)
    ctrl_rot = cmds.xform(ctrl, query=True, worldSpace=True, rotation=True)

    # in maya 2020 we can choose to use the offsetParentMatrix instead of
    # using an offset group
    if cmds.objExists(ctrl + '.offsetParentMatrix'):
        off_grp = False
        # ensure offset matrix has default values
        cmds.setAttr(ctrl + '.offsetParentMatrix',
                     [1.0, 0.0, 0.0, 0.0, 0.0,
                      1.0, 0.0, 0.0, 0.0, 0.0,
                      1.0, 0.0, 0.0, 0.0,0.0,
                      1.0], type='matrix')
        reset_to_origin(ctrl)
        # copy joint's matrix to control's offsetParentMatrix
        cmds.setAttr(ctrl + '.offsetParentMatrix', jnt_matrix, type='matrix')

        if parent_node:
            # make temporary joints to help calculate offset matrix
            tmp_parent_jnt = cmds.joint(None, name='tmp_01_JNT')
            tmp_child_jnt = cmds.joint(tmp_parent_jnt, name='tmp_02_JNT')
            a_to_b(sel=[tmp_parent_jnt, parent_node[0]])
            a_to_b(sel=[tmp_child_jnt, jnt])
            cmds.parent(ctrl, parent_node[0])
            reset_transforms(ctrl)

            child_matrix = cmds.getAttr(tmp_child_jnt + '.matrix')
            cmds.setAttr(ctrl + '.offsetParentMatrix', child_matrix, type='matrix')
            cmds.delete(tmp_parent_jnt)

    # Maya 2019 and below
    else:
        reset_to_origin(ctrl)
        # create offset group
        off_grp = cmds.createNode('transform', name=ctrl + '_OFF_GRP')

        # move offset group to joint position, parent ctrl to it, zero channels
        cmds.xform(off_grp, worldSpace=True, translation=jnt_pos, rotation=jnt_rot)
        if parent_node:
            cmds.parent(off_grp, parent_node[0])


    # move the control back into place
    cmds.xform(ctrl, worldSpace=True, translation=ctrl_pos)
    cmds.xform(ctrl, worldSpace=True, rotation=ctrl_rot)

    # parent control to offset group, if it exists
    if off_grp:
        cmds.parent(ctrl, off_grp)

    # freeze transforms again, then move pivot to match joint's
    if snap_align:
        reset_transforms(ctrl)
    else:
        cmds.makeIdentity(ctrl, apply=True, translate=True, rotate=True,
                          scale=False, normal=False)
    cmds.xform(ctrl, worldSpace=True, pivots=jnt_pos)

    # delete construction history
    if delete_history:
        cmds.delete(ctrl, ch=True)

    if off_grp:
        return off_grp
    else:
        return ctrl

def reset_to_origin(node, node_pos=False):
    # get the node's position if it is not provided
    if not node_pos:
        node_pos = cmds.xform(node, query=True, worldSpace=True, rotatePivot=True)

    # translate control to origin
    # ensure translation is frozen
    cmds.makeIdentity(node, apply=True, translate=True, rotate=False,
                      scale=False, normal=False)

    # offset to origin
    node_offset = [p * -1 for p in node_pos]
    cmds.xform(node, worldSpace=True, translation=node_offset)

    # zero rotates, then freeze all transforms
    cmds.setAttr(node + '.rotate', 0, 0, 0)
    cmds.makeIdentity(node, apply=True, translate=True, rotate=True,
                      scale=False, normal=False)

def reset_transforms(nodes):
    if not nodes:
        nodes = cmds.ls(selection=True)

    # if nodes isn't a list, make it one
    if not isinstance(nodes, list):
        nodes = [nodes]

    for node in nodes:
        cmds.setAttr(node + '.translate', 0, 0, 0)
        cmds.setAttr(node + '.rotate', 0, 0, 0)
        cmds.setAttr(node + '.scale', 1, 1, 1)


# Simple Rigging Automation Pt. 1
# Creates necessary groups for starting the rigging process
# Colin Cheng
#
# Input: Prefix name
# Output: Multiple categorized groups for beginning the rigging process
#
# 1/20/24

def riggroups(groups):
    # User input for prefix name
    x = cmds.promptDialog(title='RIG Group Setup', message='Insert Prefix Name')
    if x == 'Confirm':
        x = cmds.promptDialog(query=True, text=True)

    elif x == 'dismiss':
        return

    # Checks if a rig group already exists and deletes it
    rigListexist = cmds.ls('*_RIG')
    if len(rigListexist) > 0:
        cmds.delete(rigListexist)
    groups(x)


# Creation of groups
def groups(x):
    CTRL = cmds.group(em=True, n=x + '_CTRL_GRP')
    GEO = cmds.group(em=True, n=x + '_GEO_GRP')
    JNT = cmds.group(em=True, n=x + '_JNT_GRP')
    notouch = cmds.group(em=True, n=x + '_notouch_GRP')
    DEF = cmds.group(em=True, n=x + '_DEF_GRP')
    IK = cmds.group(em=True, n=x + '_IK_GRP')

    # Creation of rig group
    RIG = cmds.group(CTRL, GEO, JNT, notouch, DEF, IK, n=x + '_RIG')