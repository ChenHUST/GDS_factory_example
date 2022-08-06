"""
_summary_
die name: T_2_PEISL
1. 加工有cladding和no_cladding上下两个区
2. 上下区包含两大类：两组螺旋线以及一组耦合长度变化的MZI
 * @Author: wenyu chen
 * @Date: 2022-07-26 15:29:12
 * @Last Modified by: mikey.zhaopeng
 * @Last Modified time: 2022-07-26 15:29:33
 TODO 后续需要更新'+'resist
 """

from audioop import add, cross
from base64 import standard_b64decode
from cgitb import small
from dis import dis
from msilib.schema import Component
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


# 聚焦光栅带有直波导
@gf.cell
def gt_st_gt(
    pitch=0.6887, dutycycle=0.53, wg_width=0.5, st_length=12000.0, t_size=60, g_id=1
):
    """
    借用picwriter中的grating coupler类，其余使用gdsfactory包;
    生成两端gt-st-gt结构
    """
    gt_sample = gf.Component()
    wgt = WaveguideTemplate(
        wg_width=wg_width,
        clad_width=3.0,
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
        theta=np.pi / 6,
        taper_length=25,
        length=50,
        period=pitch,
        ridge=False,
        dutycycle=dutycycle,
    )
    gt_foc_2 = gf.read.from_picwriter(gt_foc_1)
    gt_foc_t = gf.geometry.boolean(
        gt_foc_2.extract(layers=gf.LAYER.WGCLAD),
        gt_foc_2.extract(layers=gf.LAYER.WG),
        "A-B",
        layer=(0, 0),
    )
    gt_text_r = gf.components.text(
        "%d dc: %2s" % (g_id, dutycycle),
        t_size,
        (-500 + st_length / 2, 50),
        layer=gf.LAYER.TEXT,
    )
    gt_text_l = gf.components.text(
        "%d dc: %2s" % (g_id, dutycycle),
        t_size,
        (100 - st_length / 2, 50),
        layer=gf.LAYER.TEXT,
    )
    right_gt_ref = gt_sample << gt_foc_t
    left_gt = gt_foc_t.mirror()
    left_gt_ref = gt_sample << left_gt
    gt_sample << gt_text_r
    gt_sample << gt_text_l
    right_gt_ref.movex(destination=(st_length) / 2)
    left_gt_ref.movex(destination=-(st_length) / 2)
    st1 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
    st1_ref = gt_sample << gf.geometry.boolean(
        st1.extract(layers=gf.LAYER.WGCLAD),
        st1.extract(layers=gf.LAYER.WG),
        operation="A-B",
        layer=(0, 0),
    )
    st1_ref.movex(destination=-(st_length) / 2)
    return gt_sample


@gf.cell
def gt_focus(pitch=0.6887, dutycycle=0.53, wg_width=0.5):
    """
    借用picwriter中的grating coupler类，其余使用gdsfactory包
    生成波导右边的聚焦光栅，port["o1"]
    """
    gt_sample = gf.Component()
    wgt = WaveguideTemplate(
        wg_width=wg_width,
        clad_width=3.0,
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
        theta=np.pi / 6,
        taper_length=25,
        length=50,
        period=pitch,
        ridge=False,
        dutycycle=dutycycle,
    )
    gt_foc_2 = gf.read.from_picwriter(gt_foc_1)
    gt_sample << gt_foc_2
    gt_sample.add_port("o1", port=gt_foc_2.ports["o1"])
    return gt_sample


# s_bend_coupler 设置函数
@gf.cell
def s_bend_coupler(
    cross_section,
    width=0.5,
    mzi_gap=0.2,
    mzi_sbend_seq=40,
    s_bend_length=50,
    coupler_length=14.7,
) -> Component:
    c = gf.Component("s_bend_coupler")
    bottom = gf.Component()
    bend_1 = gf.components.bend_s(
        size=(s_bend_length, (mzi_sbend_seq - (width + mzi_gap)) / 2),
        with_bbox=False,
        cross_section=cross_section,
    )
    bend_2 = gf.functions.mirror(bend_1)
    t_1 = gf.components.straight(length=coupler_length, cross_section=cross_section)
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
def wg_connect(cross_section, l_length=12750.3, s_length=500) -> Component:
    c = gf.Component("wg_connect")
    l_length_io = gf.components.straight(length=l_length, cross_section=cross_section)
    s_length_io = gf.components.straight(length=s_length, cross_section=cross_section)
    eular_bend_1 = gf.components.bend_euler_s(cross_section=cross_section)
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
def mzi_instance(
    cross_section,
    width=0.5,
    mzi_gap=0.2,
    mzi_sbend_seq=40,
    s_bend_length=50,
    coupler_length=14.7,
    s_length=500,
    pitch=0.6887,
    dutycycle=0.53,
) -> Component:
    c = gf.Component("mzi_instance")
    mzi_ex = s_bend_coupler(
        cross_section=cross_section,
        width=width,
        mzi_gap=mzi_gap,
        mzi_sbend_seq=mzi_sbend_seq,
        s_bend_length=s_bend_length,
        coupler_length=coupler_length,
    )
    mzi_ex_ref = c << mzi_ex
    wg_straight_iolength = (
        total_length - mzi_ex_ref.size[0] - 4 * eular_radius - 2 * mzi_iolength
    ) / 2
    wg_connect_tl = wg_connect(
        cross_section=cross_section,
        l_length=wg_straight_iolength,
        s_length=s_length,
    )
    wg_connect_tr = wg_connect_tl.mirror()
    wg_connect_bl = gf.functions.mirror(component=wg_connect_tl, p1=(1, 0), p2=(0, 0))
    wg_connect_br = gf.functions.mirror(component=wg_connect_bl)
    gt_tr = gt_focus(pitch, dutycycle, width)
    gt_br = gt_focus(pitch, dutycycle, width)
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
    c_p = gf.geometry.boolean(
        c.extract(layers=gf.LAYER.WGCLAD),
        c.extract(layers=gf.LAYER.WG),
        "A-B",
        max_points=199,
        layer=(0, 0),
    )
    c << c_p
    return c


# 创建gds文件
# 默认单位为1um，精度为1nmm
MZI_2_PEISL = gdspy.GdsLibrary()
# posutive resist example
# 目标width:500nm
# 设置相关尺寸参数
# TODO 需根据工艺参数对具体参数设置值进行校正(目前设置为理想值)
# ideal_design (no_cladding)
wg_width_nc = 0.5
mzi_gap_nc = 0.2
coupler_length_nc = 14.7
pitch_nc = 0.68411
duty_cycle_nc = 0.73912
# ideal_design (cladding)
wg_width_c = 0.5
mzi_gap_c = 0.2
coupler_length_c = 8.78
pitch_c = 0.6887
duty_cycle_c = 0.53522
# 补偿值
# wg_width = wg_width_nc + width_cp
# mzi_gap = mzi_gap + gap_cp
# duty_cycle = duty_cycle_nc + duty_cp
width_cp = 50.0 / 1000.0
gap_cp = -90.0 / 1000.0
duty_cp = 0.09

small_margin = 3.0
big_margin = 5.0
bend_radius = 50.0  # 螺旋线弯曲半径
spiral_spacing_length = 1000.0  # 起始螺旋线横向长度
spiral_height = 305  # 螺旋线高度(保持不变)
spiral_length = 10000.0  # 起始螺旋线长度
spiral_length_gap = spiral_length  # 3组螺旋线长度的gap
(die_length, die_width) = (10000.0, 10000.0 / 2)  # die长度和宽度1cmX1cm
# total_length/total_width die上可用的总长和总宽
(total_length, total_width) = (die_length, die_width)
waveguide_lengh = total_length  # 中间waveguide长度
origin_point = (0, 0)  # die中间点
pitch_y = 250
group_gap = 1000
text_size = 60
mzi_sbend_length = 50
mzi_sbend_seq = 40
eular_radius = (pitch_y - mzi_sbend_seq) / 4  # 欧拉半径
die_text_size = 100  # die字体大小
mzi_iolength = 500
mzi_length_nc = 2 * mzi_sbend_length + coupler_length_nc + 2 * mzi_iolength
mzi_length_c = 2 * mzi_sbend_length + coupler_length_c + 2 * mzi_iolength

no_cladding = gf.Component("no_cladding")
# 切割die定义
# die.center=(0, 0)

############################# no_cladding #############################
# cross_section样式 gdsfactory
wg_nc = wg_width_nc + width_cp
dc_nc = duty_cycle_nc + duty_cp
wg_csection_nc = gf.CrossSection(
    radius=eular_radius,
    width=wg_nc,
    offset=0,
    layer=gf.LAYER.WG,
    cladding_layers=gf.LAYER.WGCLAD,
    cladding_offsets=(3.0,),
    name="wg",
    port_names=("o1", "o2"),
)
mzi_sample_1 = mzi_instance(
    cross_section=wg_csection_nc,
    width=wg_nc,
    mzi_gap=mzi_gap_nc + gap_cp,
    mzi_sbend_seq=mzi_sbend_seq,
    s_bend_length=mzi_sbend_length,
    coupler_length=coupler_length_nc,
    s_length=mzi_iolength,
    pitch=pitch_nc,
    dutycycle=dc_nc,
)
nc_text = gf.components.text(
    "no cladding",
    100,
    (-400, 900),
    layer=gf.LAYER.TEXT,
)
no_cladding << nc_text

st_1 = gt_st_gt(pitch_nc, dc_nc, wg_nc, st_length=waveguide_lengh)
st_1_ref = no_cladding << st_1
mzi_sample_1_ref = no_cladding << mzi_sample_1
mzi_sample_1_ref.move(destination=(-mzi_sample_1_ref.center[0], 105 + 250))
# mzi_test_ref.connect('o1', )
# mzi_cell_ref.move(destination=(-mzi_1_ref.center[0], -mzi_1_ref.center[1]))
# no_cladding.show()

############################# no_cladding #############################
# cladding = gf.Component("cladding")
# 切割die定义
# die.center=(0, 0)
nc_text = gf.components.text(
    "cladding",
    100,
    (-400, -4500),
    layer=gf.LAYER.TEXT,
)
no_cladding << nc_text
# cross_section样式 gdsfactory
wg_c = wg_width_c + width_cp
dc_c = duty_cycle_c + duty_cp
wg_csection_c = gf.CrossSection(
    radius=eular_radius,
    width=wg_width_c + width_cp,
    offset=0,
    layer=gf.LAYER.WG,
    cladding_layers=gf.LAYER.WGCLAD,
    cladding_offsets=(3.0,),
    name="wg",
    port_names=("o1", "o2"),
)
mzi_sample_c1 = mzi_instance(
    cross_section=wg_csection_c,
    width=wg_width_c + width_cp,
    mzi_gap=mzi_gap_c + gap_cp,
    mzi_sbend_seq=mzi_sbend_seq,
    s_bend_length=mzi_sbend_length,
    coupler_length=7,
    s_length=mzi_iolength,
    pitch=pitch_c,
    dutycycle=dc_c,
)
mzi_sample_c2 = mzi_instance(
    cross_section=wg_csection_c,
    width=wg_width_c + width_cp,
    mzi_gap=mzi_gap_c + gap_cp,
    mzi_sbend_seq=mzi_sbend_seq,
    s_bend_length=mzi_sbend_length,
    coupler_length=8,
    s_length=mzi_iolength,
    pitch=pitch_c,
    dutycycle=dc_c,
)
mzi_sample_c3 = mzi_instance(
    cross_section=wg_csection_c,
    width=wg_width_c + width_cp,
    mzi_gap=mzi_gap_c + gap_cp,
    mzi_sbend_seq=mzi_sbend_seq,
    s_bend_length=mzi_sbend_length,
    coupler_length=9,
    s_length=mzi_iolength,
    pitch=pitch_c,
    dutycycle=dc_c,
)

st_c1 = gt_st_gt(pitch_c, dc_c + 0.01, wg_c, st_length=waveguide_lengh, g_id=1)
st_c1_ref = no_cladding << st_c1
st_c1_ref.movey(destination=-5000)
st_c2 = gt_st_gt(pitch_c, dc_c, wg_c, st_length=waveguide_lengh, g_id=2)
st_c2_ref = no_cladding << st_c2
st_c2_ref.movey(destination=-5250)
st_c3 = gt_st_gt(pitch_c, dc_c - 0.01, wg_c, st_length=waveguide_lengh, g_id=3)
st_c3_ref = no_cladding << st_c3
st_c3_ref.movey(destination=-5500)
st_c4 = gt_st_gt(pitch_c, dc_c - 0.02, wg_c, st_length=waveguide_lengh, g_id=4)
st_c4_ref = no_cladding << st_c4
st_c4_ref.movey(destination=-5750)
st_c5 = gt_st_gt(pitch_c, dc_c - 0.03, wg_c, st_length=waveguide_lengh, g_id=5)
st_c5_ref = no_cladding << st_c5
st_c5_ref.movey(destination=-6000)
st_c6 = gt_st_gt(pitch_c, dc_c - 0.04, wg_c, st_length=waveguide_lengh, g_id=6)
st_c6_ref = no_cladding << st_c6
st_c6_ref.movey(destination=-6250)

# mzi_sample_c1_ref = no_cladding << mzi_sample_c1
# mzi_sample_c1_ref.move(destination=(-mzi_sample_1_ref.center[0], 105 + 250 - 1000))
# mzi_sample_c2_ref = no_cladding << mzi_sample_c2
# mzi_sample_c2_ref.move(destination=(-mzi_sample_1_ref.center[0], 105 + 250 - 1500))
# mzi_sample_c3_ref = no_cladding << mzi_sample_c2
# mzi_sample_c3_ref.move(destination=(-mzi_sample_1_ref.center[0], 105 + 250 - 2000))
# mzi_test_ref.connect('o1', )
# mzi_cell_ref.move(destination=(-mzi_1_ref.center[0], -mzi_1_ref.center[1]))
# cladding.show()

# 添加top cell并写入gds中
MZI_2_PEISL.add(no_cladding)

MZI_2_PEISL.write_gds("T_2_PEIS.gds")

T_2_PEISL = no_cladding.extract(layers=[(0, 0), (66, 0)])
T_2_PEISL.write_gds("T_2_PEISL_0728.gds")
