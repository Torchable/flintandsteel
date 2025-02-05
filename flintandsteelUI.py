# Flint and Steel Auto Rigger UI
#
# By Colin Cheng

# Creates UI for assigning joints to create a limb

# Credits to Gnomon Workshop for creating the classes that taught me how to start this.

import maya.cmds as cmds
import importlib
import flintandsteel.flintandsteelautorig as faslimb

importlib.reload(faslimb)


def limb_ui():
    # Makes sure only one window is open 
    if cmds.window('limbCreatorUI', exists=True):
        cmds.deleteUI('limbCreatorUI')

    # window creation
    window = cmds.window('limbCreatorUI', title='Limb Creator', width=500, height=540)

    main_layout = cmds.columnLayout(width=500, height=540)

    # add frame layouts
    skeleton_dict = skeleton_setup_frame(window, main_layout)
    data_dict = build_data_frame(window, main_layout)
    arg_dict = build_arguements_frame(window, main_layout)
    color_dict = color_settings_frame(window, main_layout)

    command_dict = data_dict.copy()
    command_dict.update(arg_dict)
    command_dict.update(color_dict)

    # Build function / Close window
    button_grid(window, main_layout, command_dict)

    # Shows window
    cmds.showWindow(window)


def skeleton_setup_frame(window, main_layout):
    skelframe = cmds.frameLayout(label='Skeleton Setup', width=500, height=70,
                                 collapsable=True, parent=main_layout,
                                 collapseCommand=lambda: collapse(window, skelframe, 70),
                                 expandCommand=lambda: expand(window, skelframe, 70))
    srcl = cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 166), (2, 166), (3, 166)],
                                columnOffset=[(2, 'both', 2), (2, 'both', 2), (2, 'both', 2)],
                                parent=skelframe)

    arm_skeleton_setup = cmds.button(label='Load Arm Joints', height=30, parent=srcl, c= lambda x: build_arm())
    leg_skeleton_setup = cmds.button(label='Load Leg Joints', height=30, parent=srcl, c=lambda x: build_leg())
    
    return_dict = {'legs_skeleton_setup': build_arm,
                   'arms_skeleton_setup': build_leg, } 
    return return_dict

# Frame setup
def build_data_frame(window, main_layout):
    dataframe = cmds.frameLayout(label='Build Data', width=500, height=230,
                                 collapsable=True, parent=main_layout,
                                 collapseCommand=lambda: collapse(window, dataframe, 230),
                                 expandCommand=lambda: expand(window, dataframe, 230))
    rcl = cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 200), (2, 200), (3, 100)],
                               columnOffset=[(1, 'both', 5), (2, 'both', 0), (3, 'both', 5)],
                               parent=dataframe)

    # label text
    cmds.text(label='Alias', align='left', font='boldLabelFont')
    cmds.text(label='Guide', align='left', font='boldLabelFont')
    cmds.text(label='Load', align='left', font='boldLabelFont')

    arm_limb01_alias = cmds.textField(height=30, text='shoulder', parent=rcl)
    arm_limb01_guide = cmds.textField(height=30, parent=rcl)
    arm_limb01_load = cmds.button(label='load selected', height=30, parent=rcl, c=lambda x: sel_load(arm_limb01_guide))

    arm_limb02_alias = cmds.textField(height=30, text='elbow', parent=rcl)
    arm_limb02_guide = cmds.textField(height=30, parent=rcl)
    arm_limb02_load = cmds.button(label='load selected', height=30, parent=rcl, c=lambda x: sel_load(arm_limb02_guide))

    arm_limb03_alias = cmds.textField(height=30, text='wrist', parent=rcl)
    arm_limb03_guide = cmds.textField(height=30, parent=rcl)
    arm_limb03_load = cmds.button(label='load selected', height=30, parent=rcl, c=lambda x: sel_load(arm_limb03_guide))

    arm_pv_limb01_alias = cmds.textField(height=30, text='pole vector', enable=False, parent=rcl)
    arm_pv_limb01_guide = cmds.textField(height=30, parent=rcl)
    arm_pv_limb01_load = cmds.button(label='load selected', height=30, parent=rcl,
                                     c=lambda x: sel_load(arm_pv_limb01_guide))

    cmds.text(label='Side', align='left', font='obliqueLabelFont', height=20, parent=rcl)
    cmds.text(label='Part', align='left', font='obliqueLabelFont', height=20, parent=rcl)
    cmds.text(label='Base Name', align='left', font='obliqueLabelFont', height=20, parent=rcl)

    side_txt = cmds.textField(text=None, height=30, parent=rcl)
    part_txt = cmds.textField(text=None, height=30, parent=rcl)
    base_txt = cmds.textField(text=None, height=30, enable=False, parent=rcl)

    cmds.textField(side_txt, edit=True,
                   changeCommand=lambda x: change_base_name(side_txt, part_txt, base_txt))
    cmds.textField(part_txt, edit=True,
                   changeCommand=lambda x: change_base_name(side_txt, part_txt, base_txt))

    return_dict = {'side': side_txt,
                   'part': part_txt,
                   'joint_list': [arm_limb01_guide, arm_limb02_guide, arm_limb03_guide],
                   'alias_list': [arm_limb01_alias, arm_limb02_alias, arm_limb03_alias],
                   'pole_vector': [arm_pv_limb01_guide]}

    return return_dict


def build_arguements_frame(window, main_layout):
    argframe = cmds.frameLayout(label='Build Arguements', width=500, height=180,
                                collapsable=True, parent=main_layout,
                                collapseCommand=lambda: collapse(window, argframe, 180),
                                expandCommand=lambda: expand(window, argframe, 180))

    baf_col = cmds.rowColumnLayout(numberOfColumns=1, columnWidth=[(1, 500)],
                                   columnOffset=[(1, 'both', 0)],
                                   parent=argframe)

    prcl = cmds.rowColumnLayout(numberOfColumns=4, height=60, columnWidth=[(1, 150), (2, 110),
                                                                           (3, 110), (4, 110)],
                                columnOffset=[(1, 'both', 5), (2, 'both', 0),
                                              (3, 'both', 5), (4, 'both', 5)], parent=baf_col)
    # Setting to determine primary axis
    cmds.text(label='Primary Axis', align='left', font='boldLabelFont', height=30, parent=prcl)
    pa_col = cmds.radioCollection(nci=6, parent=prcl)
    px = cmds.radioButton(label='X', parent=prcl)
    py = cmds.radioButton(label='Y', parent=prcl)
    pz = cmds.radioButton(label='Z', parent=prcl)
    cmds.separator(style='none', parent=prcl)
    pnx = cmds.radioButton(label='-X', parent=prcl)
    pny = cmds.radioButton(label='-Y', parent=prcl)
    pnz = cmds.radioButton(label='-Z', parent=prcl)
    cmds.radioCollection(pa_col, edit=True, select=px)
    cmds.separator(style='none', parent=baf_col)

    urcl = cmds.rowColumnLayout(numberOfColumns=4, height=60, columnWidth=[(1, 150), (2, 110),
                                                                           (3, 110), (4, 110)],
                                columnOffset=[(1, 'both', 5), (2, 'both', 0),
                                              (3, 'both', 5), (4, 'both', 5)], parent=baf_col)
    cmds.text(label='Up Axis:', align='left', font='boldLabelFont', height=30, parent=urcl)

    ua_col = cmds.radioCollection(nci=6, parent=prcl)
    ux = cmds.radioButton(label='X', parent=urcl)
    uy = cmds.radioButton(label='Y', parent=urcl)
    uz = cmds.radioButton(label='Z', parent=urcl)
    cmds.separator(style='none', parent=urcl)
    unx = cmds.radioButton(label='-X', parent=urcl)
    uny = cmds.radioButton(label='-Y', parent=urcl)
    unz = cmds.radioButton(label='-Z', parent=urcl)
    cmds.radioCollection(ua_col, edit=True, select=uy)
    cmds.separator(style='none', parent=baf_col)

    cb_grid = cmds.gridLayout(numberOfColumns=2, cellWidthHeight=(250, 30), parent=baf_col)

    stretch_cb = cmds.checkBox(label='- Is Stretchy', value=True, parent=cb_grid)
    remove_cb = cmds.checkBox(label='- removeGuides', value=True, parent=cb_grid)

    return_dict = {'primary_axis': pa_col,
                   'up_axis': ua_col,
                   'remove_guides': remove_cb,
                   'add_stretch': stretch_cb,
                   'remove_stretch': remove_cb}
    return return_dict


# Creates colors for controls
def color_settings_frame(window, main_layout):
    colorframe = cmds.frameLayout(label='Color Settings', width=500, height=90,
                                  collapsable=True, parent=main_layout,
                                  collapseCommand=lambda: collapse(window, colorframe, 90),
                                  expandCommand=lambda: expand(window, colorframe, 90))

    crcl = cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 250), (2, 250)],
                                columnOffset=[(1, 'both', 5)], height=60, parent=colorframe)

    pr_color = cmds.colorSliderGrp(label='Primary:', adjustableColumn=3, height=30, columnWidth3=[60, 40, 150],
                                   columnAlign3=['right', 'left', 'left'], rgb=(1, 1, 0), parent=crcl)

    fk_color = cmds.colorSliderGrp(label='FK:', adjustableColumn=3, height=30, columnWidth3=[60, 40, 150],
                                   columnAlign3=['right', 'left', 'left'], rgb=(0, 0, 1), parent=crcl)

    sc_color = cmds.colorSliderGrp(label='Secondary:', adjustableColumn=3, height=30, columnWidth3=[60, 40, 150],
                                   columnAlign3=['right', 'left', 'left'], rgb=(0, .2, 1), parent=crcl)

    pv_color = cmds.colorSliderGrp(label='PV:', adjustableColumn=3, height=30, columnWidth3=[60, 40, 150],
                                   columnAlign3=['right', 'left', 'left'], rgb=(0, 1, 1), parent=crcl)

    return_dict = {'primary': pr_color,
                   'pv': pv_color,
                   'fk': fk_color,
                   'secondary': sc_color}

    return return_dict


def button_grid(window, main_layout, command_dict):
    btn_col = cmds.rowColumnLayout(numberOfColumns=1, columnWidth=[(1, 500)],
                                   columnOffset=[(1, 'both', 0)], parent=main_layout)

    grid_layout = cmds.gridLayout(numberOfColumns=2, cellWidthHeight=(250, 40), parent=btn_col)

    build_btn = cmds.button(label='Build Limb', height=40, parent=grid_layout,
                            command=lambda x: build_limb_command(command_dict))
    close_btn = cmds.button(label='Close Window', height=40, parent=grid_layout,
                            command=lambda x: cmds.deleteUI(window))


def sel_load(text_field):
    sel = cmds.ls(sl=True)
    if len(sel):
        cmds.textField(text_field, e=True, text=sel[0])


def change_base_name(side_txt, part_txt, base_txt):
    side = cmds.textField(side_txt, query=True, text=True)
    part = cmds.textField(part_txt, query=True, text=True)
    cmds.textField(base_txt, edit=True, text=side + '_' + part)


# Collapsing tab frames
def collapse(window, frame_layout, height):
    window_height = cmds.window(window, query=True, height=True)
    frame_height = cmds.frameLayout(frame_layout, query=True, height=True)
    cmds.window(window, edit=True, height=window_height - height + 30)
    cmds.frameLayout(frame_layout, edit=True, height=frame_height - height + 30)


def expand(window, frame_layout, height):
    window_height = cmds.window(window, query=True, height=True)
    frame_height = cmds.frameLayout(frame_layout, query=True, height=True)
    cmds.window(window, edit=True, height=window_height + height - 30)
    cmds.frameLayout(frame_layout, edit=True, height=frame_height + height - 30)

def build_arm():
    faslimb.arms_skeleton_setup()

def build_leg():
    faslimb.legs_skeleton_setup()

def build_limb_command(command_dict):
    side = cmds.textField(command_dict['side'], query=True, text=True)
    part = cmds.textField(command_dict['part'], query=True, text=True)
    pole_vector = cmds.textField(command_dict['pole_vector'], query=True, text=True)

    alias_list = []
    for a in command_dict['alias_list']:
        alias_list.append(cmds.textField(a, query=True, text=True))

    joint_list = []
    for j in command_dict['joint_list']:
        joint_list.append(cmds.textField(j, query=True, text=True))

    remove_guides = cmds.checkBox(command_dict['remove_guides'], query=True, value=True)

    add_stretch = cmds.checkBox(command_dict['add_stretch'], query=True, value=True)

    pa_active = cmds.radioCollection(command_dict['primary_axis'], query=True, select=True)

    up_active = cmds.radioCollection(command_dict['up_axis'], query=True, select=True)

    primary_axis = cmds.radioButton(pa_active, query=True, label=True)

    up_axis = cmds.radioButton(up_active, query=True, label=True)

    pr_color = cmds.colorSliderGrp(command_dict['primary'], query=True, rgb=True)
    fk_color = cmds.colorSliderGrp(command_dict['fk'], query=True, rgb=True)
    sc_color = cmds.colorSliderGrp(command_dict['secondary'], query=True, rgb=True)
    pv_color = cmds.colorSliderGrp(command_dict['pv'], query=True, rgb=True)

    color_dict = {side + '_' + part + '_primary': pr_color,
                  side + '_' + part + '_fk': fk_color,
                  side + '_' + part + '_secondary': sc_color,
                  side + '_' + part + '_pv': pv_color, }

    faslimb.limb(side=side, part=part, joint_list=joint_list,
                 alias_list=alias_list, pole_vector=pole_vector,
                 remove_guides=remove_guides, add_stretch=add_stretch, color_dict=color_dict,
                 primary_axis=primary_axis, up_axis=up_axis)
