# Ignite Spine Rigger UI
#
# Creates the UI for assigning guide joints and building the FK/IK spine.
# The UI only gathers the build settings, the actual rig building lives in
# igniteSpineRig.py.
#
# This UI script was built with the assistance of Claude Code

import importlib

from maya import cmds
import ignite.igniteSpineRig as igSpine

importlib.reload(igSpine)


def spine_ui():
    # Makes sure only one window is open
    if cmds.window('spineCreatorUI', exists=True):
        cmds.deleteUI('spineCreatorUI')

    # window creation
    window = cmds.window('spineCreatorUI', title='Ignite Spine Creator',
                         width=500, height=560)

    main_layout = cmds.columnLayout(width=500, height=560)

    # add frame layouts
    skeleton_setup_frame(window, main_layout)
    data_dict = build_data_frame(window, main_layout)
    arg_dict = build_arguments_frame(window, main_layout)
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
    srcl = cmds.rowColumnLayout(numberOfColumns=3,
                                columnWidth=[(1, 230), (2, 60), (3, 190)],
                                columnOffset=[(1, 'both', 5), (2, 'both', 2),
                                              (3, 'both', 5)],
                                parent=skelframe)

    cmds.text(label='Joints between pelvis and chest:', align='left',
              height=30, parent=srcl)
    mid_count = cmds.intField(value=3, minValue=0, height=30, parent=srcl)
    cmds.button(label='Create Spine Guides', height=30, parent=srcl,
                c=lambda x: build_spine_guides(mid_count))

    return_dict = {'mid_count': mid_count}
    return return_dict


# Frame setup
def build_data_frame(window, main_layout):
    dataframe = cmds.frameLayout(label='Build Data', width=500, height=170,
                                 collapsable=True, parent=main_layout,
                                 collapseCommand=lambda: collapse(window, dataframe, 170),
                                 expandCommand=lambda: expand(window, dataframe, 170))
    rcl = cmds.rowColumnLayout(numberOfColumns=3,
                               columnWidth=[(1, 200), (2, 200), (3, 100)],
                               columnOffset=[(1, 'both', 5), (2, 'both', 0),
                                             (3, 'both', 5)],
                               parent=dataframe)

    # label text
    cmds.text(label='Alias', align='left', font='boldLabelFont')
    cmds.text(label='Guide', align='left', font='boldLabelFont')
    cmds.text(label='Load', align='left', font='boldLabelFont')

    # the pelvis and chest guides are the two required joints, every joint
    # between them in the chain is picked up by the build automatically
    spine_pelvis_alias = cmds.textField(height=30, text='pelvis',
                                        enable=False, parent=rcl)
    spine_pelvis_guide = cmds.textField(height=30, parent=rcl)
    spine_pelvis_load = cmds.button(label='load selected', height=30,
                                    parent=rcl,
                                    c=lambda x: sel_load(spine_pelvis_guide))

    spine_chest_alias = cmds.textField(height=30, text='chest',
                                       enable=False, parent=rcl)
    spine_chest_guide = cmds.textField(height=30, parent=rcl)
    spine_chest_load = cmds.button(label='load selected', height=30,
                                   parent=rcl,
                                   c=lambda x: sel_load(spine_chest_guide))

    cmds.text(label='Side', align='left', font='obliqueLabelFont', height=20,
              parent=rcl)
    cmds.text(label='Part', align='left', font='obliqueLabelFont', height=20,
              parent=rcl)
    cmds.text(label='Base Name', align='left', font='obliqueLabelFont',
              height=20, parent=rcl)

    side_txt = cmds.textField(text='C', height=30, parent=rcl)
    part_txt = cmds.textField(text='spine', height=30, parent=rcl)
    base_txt = cmds.textField(text='C_spine', height=30, enable=False,
                              parent=rcl)

    cmds.textField(side_txt, edit=True,
                   changeCommand=lambda x: change_base_name(side_txt, part_txt, base_txt))
    cmds.textField(part_txt, edit=True,
                   changeCommand=lambda x: change_base_name(side_txt, part_txt, base_txt))

    return_dict = {'side': side_txt,
                   'part': part_txt,
                   'pelvis_guide': spine_pelvis_guide,
                   'chest_guide': spine_chest_guide}

    return return_dict


def build_arguments_frame(window, main_layout):
    argframe = cmds.frameLayout(label='Build Arguments', width=500, height=180,
                                collapsable=True, parent=main_layout,
                                collapseCommand=lambda: collapse(window, argframe, 180),
                                expandCommand=lambda: expand(window, argframe, 180))

    baf_col = cmds.rowColumnLayout(numberOfColumns=1, columnWidth=[(1, 500)],
                                   columnOffset=[(1, 'both', 0)],
                                   parent=argframe)

    prcl = cmds.rowColumnLayout(numberOfColumns=4, height=60,
                                columnWidth=[(1, 150), (2, 110),
                                             (3, 110), (4, 110)],
                                columnOffset=[(1, 'both', 5), (2, 'both', 0),
                                              (3, 'both', 5), (4, 'both', 5)],
                                parent=baf_col)
    # Setting to determine primary axis (aims down the chain, default Y for
    # a spine that runs up the character)
    cmds.text(label='Primary Axis', align='left', font='boldLabelFont',
              height=30, parent=prcl)
    pa_col = cmds.radioCollection(nci=6, parent=prcl)
    px = cmds.radioButton(label='X', parent=prcl)
    py = cmds.radioButton(label='Y', parent=prcl)
    pz = cmds.radioButton(label='Z', parent=prcl)
    cmds.separator(style='none', parent=prcl)
    pnx = cmds.radioButton(label='-X', parent=prcl)
    pny = cmds.radioButton(label='-Y', parent=prcl)
    pnz = cmds.radioButton(label='-Z', parent=prcl)
    cmds.radioCollection(pa_col, edit=True, select=py)
    cmds.separator(style='none', parent=baf_col)

    urcl = cmds.rowColumnLayout(numberOfColumns=4, height=60,
                                columnWidth=[(1, 150), (2, 110),
                                             (3, 110), (4, 110)],
                                columnOffset=[(1, 'both', 5), (2, 'both', 0),
                                              (3, 'both', 5), (4, 'both', 5)],
                                parent=baf_col)
    cmds.text(label='Up Axis:', align='left', font='boldLabelFont', height=30,
              parent=urcl)

    ua_col = cmds.radioCollection(nci=6, parent=urcl)
    ux = cmds.radioButton(label='X', parent=urcl)
    uy = cmds.radioButton(label='Y', parent=urcl)
    uz = cmds.radioButton(label='Z', parent=urcl)
    cmds.separator(style='none', parent=urcl)
    unx = cmds.radioButton(label='-X', parent=urcl)
    uny = cmds.radioButton(label='-Y', parent=urcl)
    unz = cmds.radioButton(label='-Z', parent=urcl)
    cmds.radioCollection(ua_col, edit=True, select=uz)
    cmds.separator(style='none', parent=baf_col)

    cb_grid = cmds.gridLayout(numberOfColumns=2, cellWidthHeight=(250, 30),
                              parent=baf_col)

    stretch_cb = cmds.checkBox(label='- Is Stretchy', value=True,
                               parent=cb_grid)
    remove_cb = cmds.checkBox(label='- removeGuides', value=True,
                              parent=cb_grid)

    return_dict = {'primary_axis': pa_col,
                   'up_axis': ua_col,
                   'remove_guides': remove_cb,
                   'add_stretch': stretch_cb}
    return return_dict


# Creates colors for controls
def color_settings_frame(window, main_layout):
    colorframe = cmds.frameLayout(label='Color Settings', width=500, height=90,
                                  collapsable=True, parent=main_layout,
                                  collapseCommand=lambda: collapse(window, colorframe, 90),
                                  expandCommand=lambda: expand(window, colorframe, 90))

    crcl = cmds.rowColumnLayout(numberOfColumns=2,
                                columnWidth=[(1, 250), (2, 250)],
                                columnOffset=[(1, 'both', 5)], height=60,
                                parent=colorframe)

    pr_color = cmds.colorSliderGrp(label='Primary:', adjustableColumn=3,
                                   height=30, columnWidth3=[60, 40, 150],
                                   columnAlign3=['right', 'left', 'left'],
                                   rgb=(1, 1, 0), parent=crcl)

    fk_color = cmds.colorSliderGrp(label='FK:', adjustableColumn=3,
                                   height=30, columnWidth3=[60, 40, 150],
                                   columnAlign3=['right', 'left', 'left'],
                                   rgb=(0, 0, 1), parent=crcl)

    tw_color = cmds.colorSliderGrp(label='Tweak:', adjustableColumn=3,
                                   height=30, columnWidth3=[60, 40, 150],
                                   columnAlign3=['right', 'left', 'left'],
                                   rgb=(0, 1, 1), parent=crcl)

    return_dict = {'primary': pr_color,
                   'fk': fk_color,
                   'tweak': tw_color}

    return return_dict


def button_grid(window, main_layout, command_dict):
    btn_col = cmds.rowColumnLayout(numberOfColumns=1, columnWidth=[(1, 500)],
                                   columnOffset=[(1, 'both', 0)],
                                   parent=main_layout)

    grid_layout = cmds.gridLayout(numberOfColumns=2, cellWidthHeight=(250, 40),
                                  parent=btn_col)

    build_btn = cmds.button(label='Build Spine', height=40, parent=grid_layout,
                            command=lambda x: build_spine_command(command_dict))
    close_btn = cmds.button(label='Close Window', height=40,
                            parent=grid_layout,
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
    # set the collapsed size outright instead of subtracting from the
    # current size, the relative math drifts whenever the queried height
    # is not exactly what the last click set and the spacing grows forever
    cmds.frameLayout(frame_layout, edit=True, height=30)
    fit_window(window, frame_layout)


def expand(window, frame_layout, height):
    # restore the frame's full design height outright
    cmds.frameLayout(frame_layout, edit=True, height=height)
    fit_window(window, frame_layout)


def fit_window(window, frame_layout):
    # size the main column and the window to what the frames actually
    # measure right now, so repeated collapsing and expanding can never
    # leave extra spacing behind
    main_layout = cmds.frameLayout(frame_layout, query=True, parent=True)
    total = 0
    for child in cmds.layout(main_layout, query=True, childArray=True):
        total += cmds.control(child, query=True, height=True)
    cmds.layout(main_layout, edit=True, height=total)
    cmds.window(window, edit=True, height=total)


def build_spine_guides(mid_count_field):
    count = cmds.intField(mid_count_field, query=True, value=True)
    igSpine.spine_skeleton_setup(count)


def build_spine_command(command_dict):
    side = cmds.textField(command_dict['side'], query=True, text=True)
    part = cmds.textField(command_dict['part'], query=True, text=True)
    pelvis_guide = cmds.textField(command_dict['pelvis_guide'], query=True,
                                  text=True)
    chest_guide = cmds.textField(command_dict['chest_guide'], query=True,
                                 text=True)

    remove_guides = cmds.checkBox(command_dict['remove_guides'], query=True,
                                  value=True)

    add_stretch = cmds.checkBox(command_dict['add_stretch'], query=True,
                                value=True)

    pa_active = cmds.radioCollection(command_dict['primary_axis'], query=True,
                                     select=True)

    up_active = cmds.radioCollection(command_dict['up_axis'], query=True,
                                     select=True)

    primary_axis = cmds.radioButton(pa_active, query=True, label=True)

    up_axis = cmds.radioButton(up_active, query=True, label=True)

    pr_color = cmds.colorSliderGrp(command_dict['primary'], query=True,
                                   rgb=True)
    fk_color = cmds.colorSliderGrp(command_dict['fk'], query=True, rgb=True)
    tw_color = cmds.colorSliderGrp(command_dict['tweak'], query=True, rgb=True)

    color_dict = {side + '_' + part + '_primary': pr_color,
                  side + '_' + part + '_fk': fk_color,
                  side + '_' + part + '_tweak': tw_color}

    igSpine.spine(side=side, part=part, pelvis_guide=pelvis_guide,
                  chest_guide=chest_guide, remove_guides=remove_guides,
                  add_stretch=add_stretch, color_dict=color_dict,
                  primary_axis=primary_axis, up_axis=up_axis)
