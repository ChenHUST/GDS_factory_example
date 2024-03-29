"""
_summary_ 
die name: T_1 PEISL
不同长度的波导(Spiral结构)(positive-resist)
主要使用package: gdspy, picwriter, gdsfactory
本版本主要使用picwriter
以后主要使用gdsfactory(功能最全)
layer层定义:
(0, 0):layer中为最终的layer层
gf.LAYER.WG 负胶波导层定义
gf.LAYER.WGCLAD 负胶cladding层定义
gf.LAYER.TEXT
目的:
    1. 根据加工和观察确定->加工尺寸和波导宽度的关系
    2. 加工三条长度不同的结构->确定波导损耗
    3. 确定grating_coupler的耦合效率
    4. 确定弯曲波导的波导损耗
    5. 加工不同间距，不同尺寸的波导并测量，确定需要的mzi的波导尺寸参数
 * @Author: wenyu chen
 * @Date: 2022-07-10 15:29:12 
 * @Last Modified by: wenyu chen
 * @Last Modified time: 2022-07-10 15:29:33
"""

from audioop import add, cross
from base64 import standard_b64decode
from cgitb import small
from dis import dis
from msilib.schema import Component
from re import T
from shutil import move
import statistics
from tokenize import group
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
    width=5, length=200, cl_position=(0, 0), cr_position=(0, 0)
) -> Component:
    c = gf.Component("marker")
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


# 矩形光栅制作
@gf.cell
def gt_my(wg_width=0.5, st_length=12000.0, taper_length=300.0):
    """
    使用gdsfactory中的矩形光栅制作
    """
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
    gt_sample = gf.Component()
    right_gt = gf.Component()
    gt_1 = gf.components.grating_coupler_rectangular(
        n_periods=20,
        period=0.6887,
        fill_factor=0.5352,
        width_grating=15.0,
        length_taper=taper_length,
        polarization="te",
        wavelength=0.785,
        layer_slab="SLAB150",
        fiber_marker_layer="TE",
        slab_xmin=-1.0,
        slab_offset=1.0,
        cross_section=wg_cross_section,
    )
    gt_in = gt_1.extract(layers=(gf.LAYER.WG, gf.LAYER.PORT))
    g_box = gf.components.rectangle(
        size=[taper_length + 20, 22], centered=True, port_type="optical"
    )
    gt_ref = right_gt << gt_in
    g_box_ref = right_gt << g_box
    g_box_ref.move(destination=(g_box_ref.size[0] / 2, 0))
    right_gt = gf.geometry.boolean(g_box_ref, gt_ref, operation="A-B", layer=(0, 0))
    right_gt.add_port("o1", port=gt_1.ports["o1"], width=wg_width)
    right_gt_ref = gt_sample << right_gt
    left_gt = right_gt.mirror()
    left_gt_ref = gt_sample << left_gt
    st1 = gf.components.straight(length=st_length, cross_section=wg_cross_section)
    # st1.movex(-st1.size[0] / 2)
    st1_ref = gt_sample << st1
    right_gt_ref.connect(port="o1", destination=st1_ref.ports["o2"])
    left_gt_ref.connect(port="o1", destination=st1_ref.ports["o1"])
    gt_sample << gf.geometry.boolean(
        st1.extract(layers=gf.LAYER.WGCLAD),
        st1.extract(layers=gf.LAYER.WG),
        operation="A-B",
        layer=(0, 0),
    )
    return gt_sample


# 聚焦光栅带有直波导
@gf.cell
def gt_focus_st(
    pitch=0.6887, dutycycle=0.53, wg_width=0.5, st_length=12000.0, t_size=60, g_id=1
):
    """
    借用picwriter中的grating coupler类，其余使用gdsfactory包
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
        layer=(10, 0),
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
        layer=(10, 0),
    )
    st1_ref.movex(destination=-(st_length) / 2)
    return gt_sample


@gf.cell
def gt_focus(pitch=0.6887, dutycycle=0.53, wg_width=0.5):
    """
    借用picwriter中的grating coupler类，其余使用gdsfactory包
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


# 三组螺旋线和一条直波导
@gf.cell
def three_spiral(
    wg_width=0.5,
    st_length=12000,
    io_gap=500,
    pitch=0.6887,
    dutycycle=0.53522,
    group_id=1,
):
    t_spiral = gf.Component()
    wg_cross_section = gf.CrossSection(
        radius=bend_radius,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(3.0,),
        name="wg",
        port_names=("o1", "o2"),
    )
    wgt = WaveguideTemplate(
        wg_width=wg_width,
        clad_width=small_margin,
        bend_radius=bend_radius,
        resist="+",
        fab="ETCH",
        wg_layer=gf.LAYER.WG[0],
        wg_datatype=0,
        clad_layer=gf.LAYER.WGCLAD[0],
        clad_datatype=0,
    )
    gtr1 = gt_focus(pitch, dutycycle, wg_width)

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
        text="%d W: %dnm" % (group_id, width * 1000),
        size=text_size,
        position=(100, text_size),
        layer=gf.LAYER.TEXT,
    )
    gt_text_r = gf.components.text(
        "%d dc: %2s" % (group_id, dutycycle),
        text_size,
        (-500 + st_length / 2, text_size),
        layer=gf.LAYER.TEXT,
    )
    gt_text_l = gf.components.text(
        "%d dc: %2s" % (group_id, dutycycle),
        text_size,
        (100 - st_length / 2, text_size),
        layer=gf.LAYER.TEXT,
    )
    t_spiral << st1_t1
    t_spiral << gt_text_r
    t_spiral << gt_text_l
    # 三组螺旋线设置
    for i in range(1, 4):
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
        gtr2_t = gt_focus(pitch, dutycycle, wg_width)
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
            text="%d W: %dnm L: %dcm"
            % (group_id, wg_width * 1000, spiral_length * i / 10000.0),
            size=text_size,
            position=(100, port_y + text_size),
            layer=gf.LAYER.TEXT,
        )
        t_text_r = gf.components.text(
            "%d dc: %2s" % (group_id, dutycycle),
            text_size,
            (-500 + st_length / 2, port_y + text_size),
            layer=gf.LAYER.TEXT,
        )
        t_text_l = gf.components.text(
            "%d dc: %2s" % (group_id, dutycycle),
            text_size,
            (100 - st_length / 2, port_y + text_size),
            layer=gf.LAYER.TEXT,
        )
        t_spiral << text_1
        t_spiral << t_text_r
        t_spiral << t_text_l

    t_spiral_p = gf.geometry.boolean(
        t_spiral.extract(layers=gf.LAYER.WGCLAD),
        t_spiral.extract(layers=gf.LAYER.WG),
        "A-B",
        max_points=199,
        layer=(0, 0),
    )
    t_spiral << t_spiral_p
    return t_spiral


###################### photonic integrated circuits 参数定义 ##########################

# 创建gds文件
# 默认单位为1um，精度为1nm
# 晶圆大小为15000um宽 X 15000um长 (1.5cm X 1.5cm)
# 考虑划片机误差(5um)以及deep trench工艺(5um左右)，实际使用宽14990um
positive = gf.Component("positive")
# posutive resist example
# 目标width:500nm
# 目标taper_width:100mm
# 设置相关尺寸参数
width = 0.40  # 起始波导宽度
small_margin = 3.0  # 波导刻蚀两边宽度
big_margin = 5.0  # 设置taper_in_out波导刻蚀两边的宽度
wg_gap = 0.1
group_number = 9
pitch = 0.6887
# dutycycle = 0.53522   # 在FDTD中仿真后的最佳占空比
(die_length, die_width) = (5000.0, 3000.0)  # die长度和宽度
(street_width, street_length) = (30.0, 300.0)  # die切割的宽度和长度预留
lito_taper_length = 10.0  # 预留端部光刻长度
# total_length/total_width die上可用的总长和总宽
total_length = die_length - 2 * street_width - 2 * lito_taper_length
total_width = die_width - 2 * street_width - 2 * lito_taper_length
wg_lengh = 3000  # 中间波导总长
bend_radius = 50.0  # 螺旋线弯曲半径
origin_point = (0, -(total_width / 2) + 1000)  # origin_point[0], origin_point[1]
spiral_spacing_length = 1000.0  # 起始螺旋线横向长度
spiral_height = 305  # 螺旋线高度(保持不变)
spiral_length = 10000.0  # 起始螺旋线长度
spiral_length_gap = spiral_length  # 3组螺旋线长度的gap
io_gap_y = 500.0  # 波导y方向间距
group_gap = 4 * io_gap_y  # 组间y方向间距
width_gap = 0.020  # 波导间距
wg_gap_gap = 0.020
duty_start = 0.50  # grating coupler起始占空比
duty_gap = 0.01  # grating coupler占空比间隔
text_size = 15.0  # 字体大小
# small_text_size = 30.0
die_text_size = 100  # die字体大小

###################### photonic integrated circuits 参数定义 ##########################


########################### 切割die定义 ##########################
# die.center=(0, 0)
die = gf.components.die(
    size=(die_length, die_width),
    street_width=street_width,
    street_length=street_length,
    die_name="T_1 PEISL",
    text_size=die_text_size,
    text_location="N",
    layer=gf.LAYER.TEXT,
    bbox_layer=4,
    draw_corners=True,
    draw_dicing_lane=False,
)
positive << die

########################### 切割die定义 ##########################


########################### 尺寸测试光栅 ##########################
# 0.4-0.56um宽度的waveguide
s1 = []
for i in range(group_number):
    wg_width = width + i * width_gap
    offset = i * small_margin
    s1.append(gf.Section(width=wg_width, offset=offset, layer=gf.LAYER.WG))
wg_cross_section = gf.CrossSection(
    radius=bend_radius,
    width=width + (group_number - 1) / 2 * width_gap,
    offset=small_margin * (group_number - 1) / 2,
    layer=gf.LAYER.WG,
    cladding_layers=gf.LAYER.WGCLAD,
    cladding_offsets=(15.0,),
    name="wg",
    port_names=("o1", "o2"),
    sections=s1,
)
wg_test = gf.components.straight(length=wg_lengh, cross_section=wg_cross_section)
wg_test_ref = positive << wg_test
wg_test_ref.move(destination=(-wg_lengh / 2, 700))
wg_text = gf.components.text(
    "wg: 0.4-0.56", text_size, (-100, 730), layer=gf.LAYER.TEXT
)
positive << wg_text
positive.show()

# 0.1-0.3um宽度的gap
s2 = []
for i in range(group_number):
    wg_width = 0.5
    offset = wg_width + wg_gap + i * wg_gap_gap
    s2.append(gf.Section(width=wg_width, offset=offset, layer=gf.LAYER.WG))
    gap_cross_section = gf.CrossSection(
        radius=bend_radius,
        width=wg_width,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(3.0,),
        name="wg",
        port_names=("o1", "o2"),
        sections=[s2[i]],
    )
    gap_test = gf.components.straight(length=wg_lengh, cross_section=gap_cross_section)
    gap_test_ref = positive << gap_test
    gap_test_ref.movey(destination=-small_margin * i)
    gap_test_ref.move(destination=(-wg_lengh / 2, 0))
gap_text = gf.components.text(
    "gap: 0.1-0.26", text_size, (-100, 30), layer=gf.LAYER.TEXT
)
positive << gap_text
positive.show()


# duty_cycle:0.50-0.59的grating_coupler
for i in range(group_number):
    duty_cycle = duty_start + i * duty_gap
    gc_cross_section = gf.CrossSection(
        radius=50,
        width=pitch * duty_cycle,
        offset=0,
        layer=gf.LAYER.WG,
        cladding_layers=gf.LAYER.WGCLAD,
        cladding_offsets=(3.0,),
        name="wg",
        port_names=("o1", "o2"),
    )
    wg_t = gf.components.straight(length=100, cross_section=gc_cross_section)
    gc_1 = gf.components.straight_array(
        n=10, spacing=pitch * (1 - duty_cycle), straigth=wg_t
    )
    gc_1_ref = positive << gc_1
    gc_1_ref.move(destination=(-(wg_lengh / 2 - i * 200), -600))
    gc_text = gf.components.text(
        "dc: %.4s" % duty_cycle,
        text_size,
        (-(wg_lengh / 2 - i * 200), -570),
        layer=gf.LAYER.TEXT,
    )
    positive << gc_text

########################### 尺寸测试光栅 ##########################


########################## 添加cross_marker并写入 #########################

positive << cross_marker(
    cl_position=(-(total_length / 2) + 200, -(total_width / 2) + 200),
    cr_position=((total_length / 2) - 200, (total_width / 2) - 200),
)

gc_coupler = gt_focus_st(
    pitch=0.6887,
    dutycycle=0.535,
    wg_width=0.5,
    st_length=3000,
    t_size=text_size,
    g_id=1,
)
gc_coupler_ref = positive << gc_coupler
gc_coupler_ref.move(destination=(0, -800))
p_resist = gf.geometry.boolean(
    positive.extract(layers=gf.LAYER.WGCLAD),
    positive.extract(layers=gf.LAYER.WG),
    "A-B",
    layer=(0, 0),
)
positive << p_resist
positive.show()

positive.write_gds("waveguide_v4.gds")
gdspy.LayoutViewer(cells=positive)

########################## 添加cross_marker并写入 #########################

T_1_PEISL = positive.extract(layers=[(0, 0), (66, 0), (10, 0)])
T_1_PEISL.write_gds("test.gds")


