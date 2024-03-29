"""
_summary_ 
主要使用gdsfactory定义PISL集成光子使用的device函数
    主要使用package: gdsfactory, gdspy, picwriter
    以后主要使用gdsfactory(功能最全)
device函数说明:

layer层定义:

/*
 * @Author: wenyuchen
 * @Date: 2022-09-06 15:58:05 
 * @Last Modified by: wenyuchen
 * @Last Modified time: 2022-10-04 20:37:35
 */
"""

from audioop import add, cross
from base64 import standard_b64decode
from cgitb import small
from dis import dis
from msilib.schema import Component
from operator import gt
from re import T
from shutil import move
from turtle import distance, pos, right, width
from unicodedata import name
from matplotlib import markers
from matplotlib.pyplot import text
import numpy as np
import gdspy
import gdsfactory as gf
from phidl import Layer
from picwriter import toolkit as tk
from picwriter.components.waveguide import WaveguideTemplate, Waveguide
import picwriter.components as pc
from pyrsistent import s
import sys

# cross_marker标记制作
@gf.cell
def cross_marker(
    width=10, length=1000, cl_position=(0, 0), cr_position=(5000, 5000)
) -> Component:
    """
    cross_marker --> chip四角的十字对准标记: 用于套刻EBL制作金标记

      |             |
    --+--         --+--
      |             |


      |             |
    --+--         --+--
      |             |

    Args:
        width (int, optional): 金标线宽. Defaults to 10.
        length (int, optional): 十字标的长度. Defaults to 1000.
        cl_position (tuple, optional): 左下角十字金标的中心位置. Defaults to (0, 0).
        cr_position (tuple, optional): 右上角十字金标的中心位置. Defaults to (5000, 5000).

    Returns:
        Component: 十字标cell
    """
    c = gf.Component("cross_marker")
    points_1 = np.array(
        [
            (cl_position[0], -length / 2 + cl_position[1]),
            (cl_position[0], length / 2 + cl_position[1]),
        ]
    )
    P1 = gf.Path(points_1)
    points_2 = np.array(
        [
            (-length / 2 + cl_position[0], cl_position[1]),
            (length / 2 + cl_position[0], cl_position[1]),
        ]
    )
    P2 = gf.Path(points_2)
    cross_temp = gf.CrossSection(width=width, layer=gf.LAYER.LABEL, name="cross")
    cross_1 = P1.extrude(cross_section=cross_temp)
    cross_2 = P2.extrude(cross_section=cross_temp)
    cross_union = gf.geometry.boolean(cross_1, cross_2, "A+B", layer=gf.LAYER.TEXT)
    c.add_array(
        component=cross_union,
        spacing=(cr_position[0] - cl_position[0], cr_position[1] - cl_position[1]),
    )
    # c_outline = gf.geometry.outline(c, distance=big_margin, layer=(marker_layer, 0))
    return c


# 矩形光栅带波导
@gf.cell
def rec_gc(
    wg_width=0.5,
    clad_width=3,
    st_length=1000.0,
    taper_length=300.0,
    period_num=20,
    pitch=0.707,
    duty=0.528,
    gt_lambda=0.785,
    gt_width=6.5,
    gt_clad=3,
) -> Component:
    """
    rec_gc --> rec_gt - taper - wg - taper - rec_gt

    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        st_length (float, optional): 中间波导长度. Defaults to 1000.0.
        taper_length (float, optional): taper长度. Defaults to 300.0.
        period_num (int, optional): 光栅周期数. Defaults to 20.
        pitch (float, optional): 光栅周期pitch. Defaults to 0.707.
        duty (float, optional): 占空比. Defaults to 0.528.
        gt_lambda (float, optional): 光栅耦合波长. Defaults to 0.785.
        gt_width (float, optional): 矩形光栅宽度. Defaults to 6.5.
        gt_clad (int, optional): 矩形光栅两边宽度. Defaults to 3.

    Returns:
        Component: _description_
    """
    wg_cross_section = gf.CrossSection(
        radius=50,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(clad_width,),
        name="wg",
        port_names=("o1", "o2"),
    )
    gt_sample = gf.Component()
    right_gt = gf.Component()
    gt_1 = gf.components.grating_coupler_rectangular(
        n_periods=period_num,
        period=pitch,
        fill_factor=duty,
        width_grating=gt_width,
        length_taper=taper_length,
        polarization="te",
        wavelength=gt_lambda,
        layer_slab="SLAB150",
        fiber_marker_layer="TE",
        slab_xmin=0,
        slab_offset=1.0,
        cross_section=wg_cross_section,
    )
    g_box = gf.components.rectangle(
        size=[taper_length + 18, gt_width + 2 * gt_clad],
        layer=gf.LAYER.WGCLAD,
        centered=True,
        port_type="optical",
    )
    right_gt << gt_1
    g_box_ref = right_gt << g_box
    g_box_ref.move(destination=(g_box_ref.size[0] / 2, 0))
    # right_gt = gf.geometry.boolean(g_box_ref, gt_ref, operation="A-B", layer=(0, 0))
    right_gt.add_port("o1", port=gt_1.ports["o1"], width=wg_width)
    right_gt_ref = gt_sample << right_gt
    left_gt = right_gt.mirror()
    left_gt_ref = gt_sample << left_gt
    st1 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
    st1_ref = gt_sample << st1
    right_gt_ref.connect(port="o1", destination=st1_ref.ports["o2"])
    left_gt_ref.connect(port="o1", destination=st1_ref.ports["o1"])
    return gt_sample


# 聚焦光栅
@gf.cell
def gt_focus(
    wg_width=0.5,
    clad_width=3,
    pitch=0.707,
    duty=0.528,
    alpha=np.pi / 7.2,
    radius=15,
    period_num=20,
) -> Component:
    """
    gt_focus --> 聚焦光栅

    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        pitch (float, optional): 光栅周期pitch. Defaults to 0.707.
        duty (float, optional): 占空比. Defaults to 0.528.
        alpha (_type_, optional): 光栅扇形角度. Defaults to np.pi/7.2.
        radius (int, optional): 光栅起始半径（与光栅起始宽度有关）. Defaults to 15.
        period_num (int, optional): 光栅周期数. Defaults to 20.

    Returns:
        Component: 返回单个聚焦光栅
    """
    gt_sample = gf.Component()
    wgt = WaveguideTemplate(
        wg_width=wg_width,
        clad_width=clad_width,
        bend_radius=50.0,
        resist="+",
        fab="ETCH",
        wg_layer=gf.LAYER.WG[0],
        wg_datatype=0,
        clad_layer=gf.LAYER.WGCLAD[0],
        clad_datatype=0,
    )
    gt_foc_1 = pc.GratingCoupler(
        wgt=wgt,
        theta=alpha,
        taper_length=radius,
        length=period_num * pitch + radius,
        period=pitch,
        ridge=False,
        dutycycle=duty,
    )
    gt_foc_2 = gf.read.from_picwriter(gt_foc_1)
    gt_sample << gt_foc_2
    gt_sample.add_port("o1", port=gt_foc_2.ports["o1"])
    return gt_sample


# 聚焦光栅带有直波导
@gf.cell
def gt_focus_st(
    wg_width=0.5,
    clad_width=3,
    pitch=0.707,
    duty=0.528,
    alpha=np.pi / 7.2,
    radius=15,
    period_num=20,
    st_length=3000.0,
    t_size=40,
) -> Component:
    """
    gt_focus_st --> gt_focus - wg - gt_focus

    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        pitch (float, optional): 光栅周期pitch. Defaults to 0.707.
        duty (float, optional): 占空比. Defaults to 0.528.
        alpha (_type_, optional): 光栅扇形角度. Defaults to np.pi/7.2.
        radius (int, optional): 光栅起始半径（与光栅起始宽度有关）. Defaults to 15.
        period_num (int, optional): 光栅周期数. Defaults to 20.
        st_length (float, optional): 中间波导长度. Defaults to 12000.0.
        t_size (int, optional): 标注文字尺寸. Defaults to 60.

    Returns:
        Component: 返回两边带光栅的波导结构
    """
    gt_sample = gf.Component()
    wgt = WaveguideTemplate(
        wg_width=wg_width,
        clad_width=clad_width,
        bend_radius=50.0,
        resist="+",
        fab="ETCH",
        wg_layer=gf.LAYER.WG[0],
        wg_datatype=0,
        clad_layer=gf.LAYER.WGCLAD[0],
        clad_datatype=0,
    )
    wg_cross_section = gf.CrossSection(
        radius=50,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(3.0,),
        name="wg",
        port_names=("o1", "o2"),
    )
    gt_foc_1 = pc.GratingCoupler(
        wgt=wgt,
        theta=alpha,
        taper_length=radius,
        length=period_num * pitch + radius,
        period=pitch,
        ridge=False,
        dutycycle=duty,
    )
    gt_foc_2 = gf.read.from_picwriter(gt_foc_1)
    gt_text_r = gf.components.text(
        "dc: %2s" % (duty),
        t_size,
        (-500 + st_length / 2, 50),
        layer=gf.LAYER.TEXT,
    )
    gt_text_l = gf.components.text(
        "dc: %2s" % (duty),
        t_size,
        (100 - st_length / 2, 50),
        layer=gf.LAYER.TEXT,
    )
    right_gt_ref = gt_sample << gt_foc_2
    left_gt = gt_foc_2.mirror()
    left_gt_ref = gt_sample << left_gt
    gt_sample << gt_text_r
    gt_sample << gt_text_l
    right_gt_ref.movex(destination=(st_length) / 2)
    left_gt_ref.movex(destination=-(st_length) / 2)
    st1 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
    st1_ref = gt_sample << st1
    st1_ref.movex(destination=-(st_length) / 2)
    return gt_sample


# 两组螺旋线和一条直波导
@gf.cell
def spiral_group(
    wg_width=0.5,
    clad_width=3,
    bend_radius=50,
    st_length=3000.0,
    pitch=0.707,
    duty=0.528,
    alpha=np.pi / 7.2,
    radius=15,
    period_num=20,
    io_gap=250,
    group_id=1,
    t_size=40,
    spiral_spacing_length=500,
    spiral_length=6000,
    spiral_num=2,
) -> Component:
    """
    spiral_group --> 两组螺旋线结构和一组直线两边带gt_focus

    gt_focus -spiral[spiral_num] - gt_focus
    ...
    gt_focus -spiral[2] - gt_focus
    gt_focus -spiral[1] - gt_focus
    gt_focus -wg - gt_focus

    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        bend_radius (int, optional): 螺旋线弯曲半径. Defaults to 50.
        st_length (float, optional): 总长. Defaults to 3000.0.
        pitch (float, optional): 光栅周期pitch. Defaults to 0.707.
        duty (float, optional): 占空比. Defaults to 0.528.
        alpha (_type_, optional): 光栅扇形角度. Defaults to np.pi/7.2.
        radius (int, optional): 光栅起始半径（与光栅起始宽度有关）. Defaults to 15.
        period_num (int, optional): 光栅周期数. Defaults to 20.
        io_gap (int, optional): 螺旋线上下间距. Defaults to 250.
        group_id (int, optional): 组号(text层). Defaults to 1.
        t_size (int, optional): 标注文字尺寸. Defaults to 40.
        spiral_spacing_length (int, optional): 起始螺旋线横向距离. Defaults to 500.
        spiral_length (int, optional): 螺旋线长度. Defaults to 6000.
        spiral_num (int, optional): 螺旋线数量. Defaults to 2.

    Returns:
        Component: 返回一组螺旋线
    """
    t_spiral = gf.Component()
    wg_cross_section = gf.CrossSection(
        radius=bend_radius,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(clad_width,),
        name="wg",
        port_names=("o1", "o2"),
    )
    wgt = WaveguideTemplate(
        wg_width=wg_width,
        clad_width=clad_width,
        bend_radius=bend_radius,
        resist="+",
        fab="ETCH",
        wg_layer=gf.LAYER.WG[0],
        wg_datatype=0,
        clad_layer=gf.LAYER.WGCLAD[0],
        clad_datatype=0,
    )
    gtr1 = gt_focus(wg_width, clad_width, pitch, duty, alpha, radius, period_num)
    gtl1 = gtr1.mirror()
    st1 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
    gtr1_ref = t_spiral << gtr1
    st1_ref = t_spiral << st1
    gtl1_ref = t_spiral << gtl1
    st1_ref.movex(destination=-st_length / 2)
    gtr1_ref.connect("o1", st1_ref.ports["o2"])
    gtl1_ref.connect("o1", st1_ref.ports["o1"])
    # text
    st1_t1 = gf.components.text(
        text="%d W: %dnm" % (group_id, wg_width * 1000),
        size=t_size,
        position=(100, t_size),
        layer=gf.LAYER.TEXT,
    )
    gt_text_r = gf.components.text(
        "%d dc: %2s" % (group_id, duty),
        t_size,
        (-500 + st_length / 2, t_size),
        layer=gf.LAYER.TEXT,
    )
    gt_text_l = gf.components.text(
        "%d dc: %2s" % (group_id, duty),
        t_size,
        (100 - st_length / 2, t_size),
        layer=gf.LAYER.TEXT,
    )
    t_spiral << st1_t1
    t_spiral << gt_text_r
    t_spiral << gt_text_l
    # 三组螺旋线设置
    for i in range(1, spiral_num + 1):
        # 只允许螺旋线水平增加，垂直方向长度和圆角个数不变
        # 螺旋线高度为300um
        # 设置螺旋线的波导参数
        port_y = io_gap * i
        port_spacing = spiral_spacing_length + spiral_length * (i - 1) / 11.0
        spiral_temp = pc.Spiral(
            wgt=wgt,
            width=port_spacing,
            length=spiral_length * i,
            parity=1,
            port=(0, port_y),
            direction="WEST",
        )
        gf_spiral_t = gf.read.from_picwriter(spiral_temp)
        # 两边直波导参数设置
        wg_length1 = st_length / 2 - port_spacing
        wg_length2 = st_length / 2
        waveguide_temp_1 = gf.components.straight(
            length=wg_length1, cross_section=wg_cross_section
        )
        waveguide_temp_2 = gf.components.straight(
            length=wg_length2, cross_section=wg_cross_section
        )
        gtr2_t = gt_focus(wg_width, clad_width, pitch, duty, alpha, radius, period_num)
        gtl2_t = gtr2_t.mirror()
        gf_spiral_ref = t_spiral << gf_spiral_t
        wg1_ref = t_spiral << waveguide_temp_1
        wg2_ref = t_spiral << waveguide_temp_2
        gtr2_ref = t_spiral << gtr2_t
        gtl2_ref = t_spiral << gtl2_t
        wg1_ref.connect("o2", destination=gf_spiral_ref.ports["o1"])
        wg2_ref.connect("o1", destination=gf_spiral_ref.ports["o2"])
        gtr2_ref.connect("o1", wg1_ref.ports["o1"])
        gtl2_ref.connect("o1", wg2_ref.ports["o2"])
        # taper参数设置
        # text文字参数设置
        text_1 = gf.components.text(
            text="%d L: %dum" % (group_id, spiral_length * i / 1000.0),
            size=t_size,
            position=(100, port_y + t_size),
            layer=gf.LAYER.TEXT,
        )
        t_text_r = gf.components.text(
            "%d dc: %2s" % (group_id, duty),
            t_size,
            (-500 + st_length / 2, port_y + t_size),
            layer=gf.LAYER.TEXT,
        )
        t_text_l = gf.components.text(
            "%d dc: %2s" % (group_id, duty),
            t_size,
            (100 - st_length / 2, port_y + t_size),
            layer=gf.LAYER.TEXT,
        )
        t_spiral << text_1
        t_spiral << t_text_r
        t_spiral << t_text_l
    return t_spiral


# 两组螺旋线和一条直波导
@gf.cell
def spiral_group_oneside(
    wg_width=0.5,
    clad_width=3,
    st_length=50,
    radius=30,
    pitch=0.707,
    duty=0.528,
    alpha=np.pi / 7.2,
    gt_radius=15,
    period_num=20,
    io_gap=250,
    t_size=40,
    spiral_spacing_length=300,
    spiral_length=3000,
    spiral_num=2,
    group_id=1,
) -> Component:
    """
    spiral_group --> 两组螺旋线结构和一组直线两边带gt_focus

    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        bend_radius (int, optional): 螺旋线弯曲半径. Defaults to 50.
        st_length (float, optional): 总长. Defaults to 3000.0.
        pitch (float, optional): 光栅周期pitch. Defaults to 0.707.
        duty (float, optional): 占空比. Defaults to 0.528.
        alpha (_type_, optional): 光栅扇形角度. Defaults to np.pi/7.2.
        radius (int, optional): 光栅起始半径（与光栅起始宽度有关）. Defaults to 15.
        period_num (int, optional): 光栅周期数. Defaults to 20.
        io_gap (int, optional): 螺旋线上下间距. Defaults to 250.
        group_id (int, optional): 组号(text层). Defaults to 1.
        t_size (int, optional): 标注文字尺寸. Defaults to 40.
        spiral_spacing_length (int, optional): 起始螺旋线横向距离. Defaults to 500.
        spiral_length (int, optional): 螺旋线长度. Defaults to 6000.
        spiral_num (int, optional): 螺旋线数量. Defaults to 2.

    Returns:
        Component: 返回一组螺旋线
    """
    t_spiral = gf.Component()
    wg_cross_section = gf.CrossSection(
        radius=radius,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(clad_width,),
        name="wg",
        port_names=("o1", "o2"),
    )
    wgt = WaveguideTemplate(
        wg_width=wg_width,
        clad_width=clad_width,
        bend_radius=radius,
        resist="+",
        fab="ETCH",
        wg_layer=gf.LAYER.WG[0],
        wg_datatype=0,
        clad_layer=gf.LAYER.WGCLAD[0],
        clad_datatype=0,
    )
    g1 = gf.functions.rotate90n(
        gt_focus(
            wg_width,
            clad_width,
            pitch,
            duty,
            alpha,
            gt_radius,
            period_num,
        )
    )
    g2 = g1.copy()
    g1_ref = t_spiral << g1
    g1_ref.movex(destination=-1375)
    g2_ref = t_spiral << g2
    st1 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
    st2 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
    st3 = gf.components.straight(
        length=(io_gap * 3 - 2 * radius), cross_section=wg_cross_section
    )
    st1_ref = t_spiral << st1
    st2_ref = t_spiral << st2
    st3_ref = t_spiral << st3
    c1 = gf.components.bend_circular(angle=90, cross_section=wg_cross_section)
    c2 = gf.components.bend_circular(angle=90, cross_section=wg_cross_section)
    c1_ref = t_spiral << c1
    c2_ref = t_spiral << c2
    st1_ref.connect("o1", destination=g1_ref.ports["o1"])
    c1_ref.connect("o2", destination=st1_ref.ports["o2"])
    st3_ref.connect("o1", destination=c1_ref.ports["o1"])
    c2_ref.connect("o2", destination=st3_ref.ports["o2"])
    st2_ref.connect("o1", destination=c2_ref.ports["o1"])
    g2_ref.connect("o1", destination=st2_ref.ports["o2"])

    # 两组螺旋线设置
    for i in range(1, spiral_num + 1):
        # 只允许螺旋线水平增加，垂直方向长度和圆角个数不变
        # 螺旋线高度为300um
        # 设置螺旋线的波导参数
        port_y = io_gap * i
        port_spacing = spiral_spacing_length + spiral_length * (i - 1) / 9.0
        spiral_temp = pc.Spiral(
            wgt=wgt,
            width=port_spacing,
            length=spiral_length * i,
            parity=1,
            port=(0, 0),
            direction="WEST",
        )
        gf_spiral_t = gf.read.from_picwriter(spiral_temp)
        # 两边直波导参数设置
        wg_length1 = (3 * io_gap - 2 * radius - port_spacing) / 2
        st1 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
        st2 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
        st3 = gf.components.straight(length=wg_length1, cross_section=wg_cross_section)
        st4 = gf.components.straight(length=wg_length1, cross_section=wg_cross_section)
        g1 = gf.functions.rotate90n(
            gt_focus(
                wg_width,
                clad_width,
                pitch,
                duty,
                alpha,
                gt_radius,
                period_num,
            )
        )
        g2 = g1.copy()
        c1 = gf.components.bend_circular(angle=90, cross_section=wg_cross_section)
        c2 = gf.components.bend_circular(angle=90, cross_section=wg_cross_section)
        c1_ref = t_spiral << c1
        c2_ref = t_spiral << c2
        gf_spiral_ref = t_spiral << gf_spiral_t
        st1_ref = t_spiral << st1
        st2_ref = t_spiral << st2
        st3_ref = t_spiral << st3
        st4_ref = t_spiral << st4
        g1_ref = t_spiral << g1
        g2_ref = t_spiral << g2
        g1_ref.movex(destination=((-3 * io_gap) / 2 + 1000 * (i - 1)))
        st1_ref.connect("o1", destination=g1_ref.ports["o1"])
        c1_ref.connect("o2", destination=st1_ref.ports["o2"])
        st3_ref.connect("o1", destination=c1_ref.ports["o1"])
        gf_spiral_ref.connect("o1", destination=st3_ref.ports["o2"])
        st4_ref.connect("o1", destination=gf_spiral_ref.ports["o2"])
        c2_ref.connect("o2", destination=st4_ref.ports["o2"])
        st2_ref.connect("o1", destination=c2_ref.ports["o1"])
        g2_ref.connect("o1", destination=st2_ref.ports["o2"])
    t1 = gf.components.text(
        "%d pt: %2s" % (group_id, pitch),
        t_size,
        (-120, 300),
        layer=gf.LAYER.TEXT,
    )
    t_spiral << t1
    return t_spiral


# s_bend_coupler 设置函数
@gf.cell
def s_bend_coupler(
    wg_width=0.5,
    clad_width=3,
    mzi_gap=0.2,
    mzi_sbend_seq=10,
    s_bend_length=20,
    coupler_length=8.8,
) -> Component:
    """
    s_bend_coupler --> directional couypler based S-bend

    o1  ----        ----    o3
            --------
            --------
    o2  ----        ----    o4
    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        mzi_gap (float, optional): direcrional coupler gap. Defaults to 0.2.
        mzi_sbend_seq (int, optional): 输出波导上下间距. Defaults to 10.
        s_bend_length (int, optional): S-bend横向距离. Defaults to 20.
        coupler_length (float, optional): directinal coupler length. Defaults to 8.8.

    Returns:
        Component: 输出单个MZI cell
    """
    c = gf.Component("s_bend_coupler")
    wg_cross_section = gf.CrossSection(
        radius=s_bend_length,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(clad_width,),
        name="wg",
        port_names=("o1", "o2"),
    )
    bottom = gf.Component()
    bend_1 = gf.components.bend_s(
        size=(s_bend_length, (mzi_sbend_seq - (wg_width + mzi_gap)) / 2),
        with_bbox=False,
        cross_section=wg_cross_section,
    )
    bend_2 = gf.functions.mirror(bend_1)
    t_1 = gf.components.straight(length=coupler_length, cross_section=wg_cross_section)
    bend_1_ref = bottom << bend_1
    bend_2_ref = bottom << bend_2
    t_1_ref = bottom << t_1
    t_1_ref.connect("o1", destination=bend_2_ref.ports["o2"])
    bend_1_ref.connect("o1", destination=t_1_ref.ports["o2"])
    bottom.add_port("o1", port=bend_1_ref.ports["o2"], width=width)
    bottom.add_port("o2", port=bend_2_ref.ports["o1"], width=width)
    bottom.show()
    point_1 = (
        bottom.extract(layers=gf.LAYER.WG).center[0],
        bottom.extract(layers=gf.LAYER.WG).ymax + mzi_gap / 2,
    )
    point_2 = (point_1[0] + mzi_gap / 2, point_1[1])
    top = gf.functions.mirror(component=bottom, p1=point_1, p2=point_2)
    top_ref = c << top
    bottom_ref = c << bottom
    c.add_port("o1", port=top_ref.ports["o1"], width=width)
    c.add_port("o2", port=bottom_ref.ports["o1"], width=width)
    c.add_port("o3", port=top_ref.ports["o2"], width=width)
    c.add_port("o4", port=bottom_ref.ports["o2"], width=width)
    return c


# taper和mzi之间的连接波导
@gf.cell
def wg_connect(
    wg_width=0.5,
    clad_width=3,
    eular_bend_length=20,
    l_length=1000,
    s_length=500,
) -> Component:
    """
    wg_connect -->   l_length - eular_bend
                                    |
                                eular_bend - s_length

    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        eular_bend_length (int, optional): eular-bend 半径. Defaults to 20.
        l_length (int, optional): 长波导长度. Defaults to 1000.
        s_length (int, optional): 短波导长度. Defaults to 500.

    Returns:
        Component: 返回波导连接
    """
    wg_cross_section = gf.CrossSection(
        radius=eular_bend_length,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(clad_width,),
        name="wg",
        port_names=("o1", "o2"),
    )
    c = gf.Component("wg_connect")
    l_length_io = gf.components.straight(
        length=l_length, cross_section=wg_cross_section
    )
    s_length_io = gf.components.straight(
        length=s_length, cross_section=wg_cross_section
    )
    eular_bend_1 = gf.components.bend_euler_s(cross_section=wg_cross_section)
    eular_bend_mirror = eular_bend_1.mirror()
    l_length_io_ref = c << l_length_io
    s_length_io_ref = c << s_length_io
    eular_bend_mirror_ref = c << eular_bend_mirror
    eular_bend_mirror_ref.connect(port="o1", destination=l_length_io_ref.ports["o2"])
    s_length_io_ref.connect(port="o1", destination=eular_bend_mirror_ref.ports["o2"])
    c.add_port("o1", port=l_length_io_ref.ports["o1"])
    c.add_port("o2", port=s_length_io_ref.ports["o2"])
    return c


@gf.cell
def mzi_single(
    wg_width=0.5,
    clad_width=3,
    io_gap=250,
    mzi_gap=0.2,
    mzi_sbend_seq=10,
    s_bend_length=20,
    coupler_length=8.8,
    pitch=0.707,
    duty=0.528,
    alpha=np.pi / 7.2,
    gt_radius=15,
    period_num=20,
    total_length=3000,
    mzi_iolength=500,
    t_size=40,
    group_id=1,
) -> Component:
    """
    mzi_single --> single mzi

    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        eular_radius (float, optional): eular-bend 半径. Defaults to 52.5.
        mzi_gap (float, optional): direcrional coupler gap. Defaults to 0.2.
        mzi_sbend_seq (int, optional): 输出波导上下间距. Defaults to 10.
        s_bend_length (int, optional): S-bend横向距离. Defaults to 20.
        coupler_length (float, optional): directinal coupler length. Defaults to 8.8.
        pitch (float, optional): 光栅周期pitch. Defaults to 0.707.
        duty (float, optional): 占空比. Defaults to 0.528.
        alpha (_type_, optional): 光栅扇形角度. Defaults to np.pi/7.2.
        gt_radius (int, optional): 光栅起始半径（与光栅起始宽度有关）. Defaults to 15.
        period_num (int, optional): 光栅周期数. Defaults to 20.
        total_length (int, optional): mzi两端输入和输出光栅长度. Defaults to 3000.
        mzi_iolength (int, optional): 输入和输出的波导长度. Defaults to 500.
        t_size (int, optional): 标注文字尺寸. Defaults to 40.
        group_id (int, optional): 组号(text层). Defaults to 1.

    Returns:
        Component: _description_
    """
    c = gf.Component("mzi_instance")
    eular_radius = (io_gap - mzi_sbend_seq) / 4
    wg_cross_section = gf.CrossSection(
        radius=eular_radius,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(clad_width,),
        name="wg",
        port_names=("o1", "o2"),
    )
    mzi_ex = s_bend_coupler(
        wg_width,
        clad_width,
        mzi_gap,
        mzi_sbend_seq,
        s_bend_length,
        coupler_length,
    )
    mzi_ex_ref = c << mzi_ex
    mzi_ex_ref.move(destination=(mzi_ex.size[0] / 2, 0))
    wg_straight_iolength = (
        total_length - mzi_ex_ref.size[0] - 4 * eular_radius - 2 * mzi_iolength
    ) / 2
    wg_connect_tl = wg_connect(
        wg_width, clad_width, eular_radius, mzi_iolength, wg_straight_iolength
    )
    wg_connect_tr = wg_connect_tl.mirror()
    wg_connect_bl = gf.functions.mirror(component=wg_connect_tl, p1=(1, 0), p2=(0, 0))
    wg_connect_br = gf.functions.mirror(component=wg_connect_bl)
    gt_tr = gt_focus(
        wg_width,
        clad_width,
        pitch,
        duty,
        alpha,
        gt_radius,
        period_num,
    )
    gt_br = gt_focus(
        wg_width,
        clad_width,
        pitch,
        duty,
        alpha,
        gt_radius,
        period_num,
    )
    gt_tl = gf.functions.mirror(component=gt_tr, p1=(0, 1), p2=(0, 0))
    gt_bl = gf.functions.mirror(component=gt_br, p1=(0, 1), p2=(0, 0))
    gt_tr_ref = c << gt_tr
    gt_br_ref = c << gt_br
    gt_tl_ref = c << gt_tl
    gt_bl_ref = c << gt_bl
    wg_connect_tl_ref = c << wg_connect_tl
    wg_connect_tr_ref = c << wg_connect_tr
    wg_connect_bl_ref = c << wg_connect_bl
    wg_connect_br_ref = c << wg_connect_br
    wg_connect_tl_ref.connect("o2", destination=mzi_ex_ref.ports["o1"])
    wg_connect_bl_ref.connect("o2", destination=mzi_ex_ref.ports["o2"])
    wg_connect_tr_ref.connect("o2", destination=mzi_ex_ref.ports["o3"])
    wg_connect_br_ref.connect("o2", destination=mzi_ex_ref.ports["o4"])
    gt_tr_ref.connect("o1", destination=wg_connect_tr_ref.ports["o1"])
    gt_br_ref.connect("o1", destination=wg_connect_br_ref.ports["o1"])
    gt_tl_ref.connect("o1", destination=wg_connect_tl_ref.ports["o1"])
    gt_bl_ref.connect("o1", destination=wg_connect_bl_ref.ports["o1"])
    c.add_port("o1", port=wg_connect_tl_ref.ports["o1"])
    c.add_port("o2", port=wg_connect_bl_ref.ports["o1"])
    c.add_port("o3", port=wg_connect_tr_ref.ports["o1"])
    c.add_port("o4", port=wg_connect_br_ref.ports["o1"])
    return c


@gf.cell
def mzi_block(
    wg_width=0.5,
    clad_width=3,
    mzi_sep=100,
    mzi_gap=0.2,
    mzi_sbend_seq=10,
    s_bend_length=20,
    coupler_length=8.8,
    total_length=3000,
    mzi_iolength=500,
    t_size=40,
    group_id=1,
) -> Component:
    """
    mzi_single --> single mzi

    Args:

        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        mzi_sep (float, optional): MZI输出波导上下间距. Defaults to 100.
        mzi_gap (float, optional): direcrional coupler gap. Defaults to 0.2.
        mzi_sbend_seq (int, optional): 输出波导上下间距. Defaults to 10.
        s_bend_length (int, optional): S-bend横向距离. Defaults to 20.
        coupler_length (float, optional): directinal coupler length. Defaults to 8.8.
        total_length (int, optional): mzi两端输入和输出长度. Defaults to 3000.
        mzi_iolength (int, optional): 输入和输出的波导长度. Defaults to 500.
        t_size (int, optional): 标注文字尺寸. Defaults to 40.
        group_id (int, optional): 组号(text层). Defaults to 1.

    Returns:
        Component: _description_
    """
    c = gf.Component("mzi_block")
    eular_radius = (mzi_sep - mzi_sbend_seq) / 4
    mzi_ex = s_bend_coupler(
        wg_width,
        clad_width,
        mzi_gap,
        mzi_sbend_seq,
        s_bend_length,
        coupler_length,
    )
    mzi_ex_ref = c << mzi_ex
    mzi_ex_ref.move(destination=(mzi_ex.size[0] / 2, 0))
    wg_straight_iolength = (
        total_length - mzi_ex_ref.size[0] - 4 * eular_radius - 2 * mzi_iolength
    ) / 2
    wg_connect_tl = wg_connect(
        wg_width, clad_width, eular_radius, mzi_iolength, wg_straight_iolength
    )
    wg_connect_tr = wg_connect_tl.mirror()
    wg_connect_bl = gf.functions.mirror(component=wg_connect_tl, p1=(1, 0), p2=(0, 0))
    wg_connect_br = gf.functions.mirror(component=wg_connect_bl)
    wg_connect_tl_ref = c << wg_connect_tl
    wg_connect_tr_ref = c << wg_connect_tr
    wg_connect_bl_ref = c << wg_connect_bl
    wg_connect_br_ref = c << wg_connect_br
    wg_connect_tl_ref.connect("o2", destination=mzi_ex_ref.ports["o1"])
    wg_connect_bl_ref.connect("o2", destination=mzi_ex_ref.ports["o2"])
    wg_connect_tr_ref.connect("o2", destination=mzi_ex_ref.ports["o3"])
    wg_connect_br_ref.connect("o2", destination=mzi_ex_ref.ports["o4"])
    c.add_port("o1", port=wg_connect_tl_ref.ports["o1"])
    c.add_port("o2", port=wg_connect_bl_ref.ports["o1"])
    c.add_port("o3", port=wg_connect_tr_ref.ports["o1"])
    c.add_port("o4", port=wg_connect_br_ref.ports["o1"])
    return c


@gf.cell
def mzi_oneside(
    wg_width=0.5,
    clad_width=3,
    radius=30,
    io_gap=250,
    st_length=100,
    mzi_sep=80,
    mzi_gap=0.2,
    mzi_sbend_seq=10,
    s_bend_length=20,
    coupler_length=8.8,
    total_length=160,
    mzi_iolength=5,
    pitch=0.707,
    duty=0.528,
    alpha=np.pi / 7.2,
    gt_radius=15,
    period_num=20,
    t_size=40,
    group_id=1,
) -> Component:
    """
    mzi_oneside --> 输入和输出光栅在一边的mzi

    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        radius (int, optional): 波导半径. Defaults to 30.
        io_gap (int, optional): 输入输出光纤间距. Defaults to 250.
        st_length (int, optional): 竖向波导长度. Defaults to 100.
        mzi_sep (int, optional): MZI输出波导上下间距. Defaults to 80.
        mzi_gap (float, optional): direcrional coupler gap. Defaults to 0.2.
        mzi_sbend_seq (int, optional): 输出波导上下间距. Defaults to 10.
        s_bend_length (int, optional): S-bend横向距离. Defaults to 20.
        coupler_length (float, optional): directinal coupler length. Defaults to 8.8.
        total_length (int, optional): mzi两端输入和输出长度. Defaults to 160.
        mzi_iolength (int, optional): 输入和输出的波导长度. Defaults to 5.
        pitch (float, optional): 光栅周期pitch. Defaults to 0.707.
        duty (float, optional): 占空比. Defaults to 0.528.
        alpha (_type_, optional): 光栅扇形角度. Defaults to np.pi/7.2.
        gt_radius (int, optional): 光栅起始半径（与光栅起始宽度有关）. Defaults to 15.
        period_num (int, optional): 光栅周期数. Defaults to 20.
        t_size (int, optional): _description_. Defaults to 40.
        group_id (int, optional): _description_. Defaults to 1.

    Returns:
        Component: _description_
    """
    c = gf.Component("mzi_oneside")
    in_1 = gf.Component("in1")
    in_2 = gf.Component("in2")
    g1 = gf.functions.rotate90n(
        gt_focus(
            wg_width,
            clad_width,
            pitch,
            duty,
            alpha,
            gt_radius,
            period_num,
        )
    )
    g2 = g1.copy()
    dc_1 = mzi_block(
        wg_width,
        clad_width,
        mzi_sep,
        mzi_gap,
        mzi_sbend_seq,
        s_bend_length,
        coupler_length,
        total_length,
        mzi_iolength,
        t_size,
        group_id,
    )
    wg_cross_section = gf.CrossSection(
        radius=radius,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(3.0,),
        name="wg",
        port_names=("o1", "o2"),
    )
    dc_1_ref = c << dc_1
    g1_ref = in_1 << g1
    g2_ref = in_2 << g2
    g2_ref.movex(destination=-250)
    st1 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
    st2 = gf.components.straight(
        length=st_length + mzi_sep, cross_section=wg_cross_section
    )
    st3 = gf.components.straight(
        length=(io_gap - 2 * radius - dc_1.size[0]) / 2, cross_section=wg_cross_section
    )
    st4 = gf.components.straight(
        length=(3 * io_gap - 2 * radius - dc_1.size[0]) / 2,
        cross_section=wg_cross_section,
    )
    st1_ref = in_1 << st1
    st2_ref = in_2 << st2
    st1_ref.connect("o1", destination=g1_ref.ports["o1"])
    st2_ref.connect("o1", destination=g2_ref.ports["o1"])
    st3_ref = in_1 << st3
    st4_ref = in_2 << st4
    c1 = gf.components.bend_circular(angle=-90, cross_section=wg_cross_section)
    c2 = gf.components.bend_circular(angle=-90, cross_section=wg_cross_section)
    c1_ref = in_1 << c1
    c2_ref = in_2 << c2
    c1_ref.connect("o1", destination=st1_ref.ports["o2"])
    c2_ref.connect("o1", destination=st2_ref.ports["o2"])
    st3_ref.connect("o1", destination=c1_ref.ports["o2"])
    st4_ref.connect("o1", destination=c2_ref.ports["o2"])
    dc_1_ref.connect("o2", destination=st3_ref.ports["o2"])
    in_1_mirror = gf.functions.mirror(
        in_1,
        (dc_1_ref.center[0], dc_1_ref.center[1]),
        (dc_1_ref.center[0], dc_1_ref.center[1] - 1),
    )
    in_2_mirror = gf.functions.mirror(
        in_2,
        (dc_1_ref.center[0], dc_1_ref.center[1]),
        (dc_1_ref.center[0], dc_1_ref.center[1] - 1),
    )
    text = gf.components.text(
        "dc %d" % group_id,
        t_size,
        (dc_1.size[0] - 100, dc_1.size[1] + 100),
        layer=gf.LAYER.TEXT,
    )
    c << text
    c << in_1
    c << in_2
    c << in_1_mirror
    c << in_2_mirror
    return c


@gf.cell
def mmi2X2(
    wg_width=0.5,
    clad_width=3,
    taper_width=1.1,
    taper_length=11,
    mmi_length=53.7,
    mmi_width=6,
    wg_seperate=2.1,
    t_size=40,
    group_id=1,
) -> Component:
    """
    mmi2X2_block --> 单独的2X2 MMI
                   mmi_length
                    <------>
                    ________
                   |        |
                __/          \__
            o1  __            __  o3
                  \          /
                  |         |
                __/          \__
            o2  __            __  o4
                  \          /
                   |________|

                <->
            taper_length


    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        taper_width (float, optional): taper宽度. Defaults to 1.1.
        taper_length (int, optional): taper长度. Defaults to 11.
        mmi_length (float, optional): MMI长度. Defaults to 53.7.
        mmi_width (int, optional): MMI宽度. Defaults to 6.
        wg_seperate (float, optional): 两边波导分离值. Defaults to 2.1.
        t_size (int, optional): _description_. Defaults to 40.
        group_id (int, optional): _description_. Defaults to 1.

    Returns:
        Component: _description_
    """
    c = gf.Component("mmi2X2_block")
    wgt = WaveguideTemplate(
        wg_width=0,
        clad_width=clad_width,
        resist="+",
        fab="ETCH",
        wg_layer=gf.LAYER.WG[0],
        wg_datatype=0,
        clad_layer=gf.LAYER.WGCLAD[0],
        clad_datatype=0,
    )
    wg_cross_section = gf.CrossSection(
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(clad_width,),
        name="wg",
        port_names=("o1", "o2"),
    )
    pc_mmi = pc.MMI2x2(
        wgt=wgt,
        length=mmi_length,
        width=mmi_width,
        angle=0,
        wg_sep=wg_seperate,
    )
    mmi_1 = gf.read.from_picwriter(pc_mmi)
    taper_1 = gf.components.taper(
        length=taper_length,
        width1=taper_width,
        width2=wg_width,
        cross_section=wg_cross_section,
    )
    taper_2 = taper_1.copy()
    taper_3 = taper_1.copy()
    taper_4 = taper_1.copy()
    taper_1_ref = c << taper_1
    taper_2_ref = c << taper_2
    taper_3_ref = c << taper_3
    taper_4_ref = c << taper_4
    mmi_1_ref = c << mmi_1
    taper_1_ref.connect("o1", destination=mmi_1_ref.ports["o1"])
    taper_2_ref.connect("o1", destination=mmi_1_ref.ports["o2"])
    taper_3_ref.connect("o1", destination=mmi_1_ref.ports["o3"])
    taper_4_ref.connect("o1", destination=mmi_1_ref.ports["o4"])
    c.add_port("o1", port=taper_2_ref.ports["o2"])
    c.add_port("o2", port=taper_1_ref.ports["o2"])
    c.add_port("o3", port=taper_3_ref.ports["o2"])
    c.add_port("o4", port=taper_4_ref.ports["o2"])
    return c


@gf.cell
def mmi2X2_block(
    wg_width=0.5,
    clad_width=3,
    taper_width=1.1,
    taper_length=11,
    mmi_length=53.7,
    mmi_width=6,
    wg_seperate=2.1,
    total_length=160,
    mmi_sep=80,
    mmi_iolength=0,
    t_size=40,
    group_id=1,
) -> Component:
    """
    mmi2X2_block --> 单独的2X2 MMI
                   mmi_length
                    <------>
                    ________
                   |        |
                __/          \__
            o1  __            __  o3
                  \          /
                  |         |
                __/          \__
            o2  __            __  o4
                  \          /
                   |________|

                <->
            taper_length


    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        taper_width (float, optional): taper宽度. Defaults to 1.1.
        taper_length (int, optional): taper长度. Defaults to 11.
        mmi_length (float, optional): MMI长度. Defaults to 53.7.
        mmi_width (int, optional): MMI宽度. Defaults to 6.
        wg_seperate (float, optional): 两边波导分离值. Defaults to 2.1.
        t_size (int, optional): _description_. Defaults to 40.
        group_id (int, optional): _description_. Defaults to 1.

    Returns:
        Component: _description_
    """
    c = gf.Component("mmi2X2_block")
    eular_radius = (mmi_sep - wg_seperate) / 4
    mmi_1 = mmi2X2(
        wg_width,
        clad_width,
        taper_width,
        taper_length,
        mmi_length,
        mmi_width,
        wg_seperate,
        t_size,
        group_id,
    )
    mmi_1_ref = c << mmi_1
    wg_straight_iolength = (
        total_length - mmi_1.size[0] - 4 * eular_radius - 2 * mmi_iolength
    ) / 2
    # tl -> top left ; tr -> top right ; bl -> bottom left ; br -> bottom right
    wg_connect_tl = wg_connect(
        wg_width, clad_width, eular_radius, mmi_iolength, wg_straight_iolength
    )
    wg_connect_tr = wg_connect_tl.mirror()
    wg_connect_bl = gf.functions.mirror(component=wg_connect_tl, p1=(1, 0), p2=(0, 0))
    wg_connect_br = gf.functions.mirror(component=wg_connect_bl)
    wg_connect_tl_ref = c << wg_connect_tl
    wg_connect_tr_ref = c << wg_connect_tr
    wg_connect_bl_ref = c << wg_connect_bl
    wg_connect_br_ref = c << wg_connect_br
    wg_connect_tl_ref.connect("o2", destination=mmi_1_ref.ports["o1"])
    wg_connect_bl_ref.connect("o2", destination=mmi_1_ref.ports["o2"])
    wg_connect_tr_ref.connect("o2", destination=mmi_1_ref.ports["o3"])
    wg_connect_br_ref.connect("o2", destination=mmi_1_ref.ports["o4"])
    c.add_port("o1", port=wg_connect_tl_ref.ports["o1"])
    c.add_port("o2", port=wg_connect_bl_ref.ports["o1"])
    c.add_port("o3", port=wg_connect_tr_ref.ports["o1"])
    c.add_port("o4", port=wg_connect_br_ref.ports["o1"])
    return c


@gf.cell
def mmi2x2_oneside(
    wg_width=0.5,
    clad_width=3,
    radius=30,
    io_gap=250,
    st_length=100,
    taper_width=1.1,
    taper_length=11,
    mmi_length=53.7,
    mmi_width=6,
    wg_seperate=2.1,
    total_length=160,
    mmi_sep=80,
    mmi_iolength=0,
    pitch=0.707,
    duty=0.528,
    alpha=np.pi / 7.2,
    gt_radius=15,
    period_num=20,
    t_size=40,
    group_id=1,
) -> Component:
    """
    mzi_oneside --> 输入和输出光栅在一边的2x2mmi

    Args:
        wg_width (float, optional): 波导宽度. Defaults to 0.5.
        clad_width (int, optional): 波导两边宽度. Defaults to 3.
        radius (int, optional): 波导半径. Defaults to 30.
        io_gap (int, optional): 输入输出光纤间距. Defaults to 250.
        st_length (int, optional): 竖向波导长度. Defaults to 100.
        mzi_sep (int, optional): MZI输出波导上下间距. Defaults to 80.
        mzi_gap (float, optional): direcrional coupler gap. Defaults to 0.2.
        mzi_sbend_seq (int, optional): 输出波导上下间距. Defaults to 10.
        s_bend_length (int, optional): S-bend横向距离. Defaults to 20.
        coupler_length (float, optional): directinal coupler length. Defaults to 8.8.
        total_length (int, optional): mzi两端输入和输出长度. Defaults to 160.
        mzi_iolength (int, optional): 输入和输出的波导长度. Defaults to 5.
        pitch (float, optional): 光栅周期pitch. Defaults to 0.707.
        duty (float, optional): 占空比. Defaults to 0.528.
        alpha (_type_, optional): 光栅扇形角度. Defaults to np.pi/7.2.
        gt_radius (int, optional): 光栅起始半径（与光栅起始宽度有关）. Defaults to 15.
        period_num (int, optional): 光栅周期数. Defaults to 20.
        t_size (int, optional): _description_. Defaults to 40.
        group_id (int, optional): _description_. Defaults to 1.

    Returns:
        Component: _description_
    """
    c = gf.Component("mmi2x2_oneside")
    in_1 = gf.Component("in1")
    in_2 = gf.Component("in2")
    g1 = gf.functions.rotate90n(
        gt_focus(
            wg_width,
            clad_width,
            pitch,
            duty,
            alpha,
            gt_radius,
            period_num,
        )
    )
    g2 = g1.copy()
    mmi2X2_1 = mmi2X2_block(
        wg_width,
        clad_width,
        taper_width,
        taper_length,
        mmi_length,
        mmi_width,
        wg_seperate,
        total_length,
        mmi_sep,
        mmi_iolength,
        t_size,
        group_id,
    )
    wg_cross_section = gf.CrossSection(
        radius=radius,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(3.0,),
        name="wg",
        port_names=("o1", "o2"),
    )
    mmi2X2_1_ref = c << mmi2X2_1
    g1_ref = in_1 << g1
    g2_ref = in_2 << g2
    g2_ref.movex(destination=-250)
    st1 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
    st2 = gf.components.straight(
        length=st_length + mmi_sep, cross_section=wg_cross_section
    )
    st3 = gf.components.straight(
        length=(io_gap - 2 * radius - mmi2X2_1.size[0]) / 2,
        cross_section=wg_cross_section,
    )
    st4 = gf.components.straight(
        length=(3 * io_gap - 2 * radius - mmi2X2_1.size[0]) / 2,
        cross_section=wg_cross_section,
    )
    st1_ref = in_1 << st1
    st2_ref = in_2 << st2
    st1_ref.connect("o1", destination=g1_ref.ports["o1"])
    st2_ref.connect("o1", destination=g2_ref.ports["o1"])
    st3_ref = in_1 << st3
    st4_ref = in_2 << st4
    c1 = gf.components.bend_circular(angle=-90, cross_section=wg_cross_section)
    c2 = gf.components.bend_circular(angle=-90, cross_section=wg_cross_section)
    c1_ref = in_1 << c1
    c2_ref = in_2 << c2
    c1_ref.connect("o1", destination=st1_ref.ports["o2"])
    c2_ref.connect("o1", destination=st2_ref.ports["o2"])
    st3_ref.connect("o1", destination=c1_ref.ports["o2"])
    st4_ref.connect("o1", destination=c2_ref.ports["o2"])
    mmi2X2_1_ref.connect("o2", destination=st3_ref.ports["o2"])
    in_1_mirror = gf.functions.mirror(
        in_1,
        (mmi2X2_1_ref.center[0], mmi2X2_1_ref.center[1]),
        (mmi2X2_1_ref.center[0], mmi2X2_1_ref.center[1] - 1),
    )
    in_2_mirror = gf.functions.mirror(
        in_2,
        (mmi2X2_1_ref.center[0], mmi2X2_1_ref.center[1]),
        (mmi2X2_1_ref.center[0], mmi2X2_1_ref.center[1] - 1),
    )
    text = gf.components.text(
        "mmi %d" % group_id,
        t_size,
        (mmi2X2_1.size[0] - 100, mmi2X2_1.size[1] + 100),
        layer=gf.LAYER.TEXT,
    )
    c << text
    c << in_1
    c << in_2
    c << in_1_mirror
    c << in_2_mirror
    return c


if __name__ == "__main__":
    PDK_test = gf.Component("PDK_test")
    mmi2X2_instance = spiral_group_oneside(wg_width=0.55)
    PDK_test << mmi2X2_instance
    PDK_test << gf.geometry.boolean(
        PDK_test.extract(layers=gf.LAYER.WGCLAD),
        PDK_test.extract(layers=gf.LAYER.WG),
        "A-B",
        max_points=199,
        layer=(0, 0),
    )
    PDK_test.show()
