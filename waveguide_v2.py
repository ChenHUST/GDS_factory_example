"""
_summary_ 
不同长度的波导(Spiral结构)(positive-resist)
主要使用package: gdspy, picwriter, gdsfactory
本版本主要使用picwriter
以后主要使用gdsfactory(功能最全)
目的:
    1. 根据加工和观察确定->加工尺寸和波导宽度的关系
    2. 加工三条长度不同的结构->确定波导损耗
    3. 确定水平耦合的耦合效率
    4. 确定弯曲波导的波导损耗
    5. 加工不同间距，不同尺寸的波导并测量，确定需要的mzi的波导尺寸参数
 * @Author: wenyu chen
 * @Date: 2022-06-01 15:29:12 
 * @Last Modified by: wenyu chen
 * @Last Modified time: 2022-06-15 15:29:33
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

# cross_marker标记制作
@gf.cell
def cross_marker(
    width=5, length=500, cl_position=(0, 0), cr_position=(0, 0)
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
    cross_temp = gf.CrossSection(width=width, layer=(marker_layer, 0), name="cross")
    cross_1 = P1.extrude(cross_section=cross_temp)
    cross_2 = P2.extrude(cross_section=cross_temp)
    cross_union = gf.geometry.boolean(
        A=cross_1, B=cross_2, operation="A+B", layer=(5, 0)
    )
    c.add_array(
        component=cross_union,
        spacing=(cr_position[0] - cl_position[0], cr_position[1] - cl_position[1]),
    )
    # c_outline = gf.geometry.outline(c, distance=big_margin, layer=(marker_layer, 0))
    return c


@gf.cell
def gt_my(wg_width=0.5, st_length=12000.0, taper_length=300.0):
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


# 创建gds文件
# 默认单位为1um，精度为1nm
# 晶圆大小为15000um宽 X 25000um长 (1.5cm X 2.5cm)
# 考虑划片机误差(5um)以及deep trench工艺(5um左右)，实际使用宽14990um
waveguide = gdspy.GdsLibrary()
# posutive resist example
# 目标width:500nm
# 目标taper_width:100mm
# 设置相关尺寸参数
width = 0.46  # 起始波导宽度
small_margin = 3.0  # 波导刻蚀两边宽度
big_margin = 5.0
(die_length, die_width) = (15000.0, 15000.0)  # die长度和宽度
(street_width, street_length) = (100.0, 1000.0)  # die切割的宽度和长度预留
lito_taper_length = 10.0  # 预留端部光刻长度
# total_length/total_width die上可用的总长和总宽
total_length = die_length - 2 * street_width - 2 * lito_taper_length
total_width = die_width - 2 * street_width - 2 * lito_taper_length
taper_length = 400.0  # fiber-to-waveguide coupler长度
taper_width = 0.06  # fiber-to-waveguide coupler宽度
waveguide_lengh = total_length - 2 * taper_length  # 中间waveguide长度
bend_radius = 50.0  # 螺旋线弯曲半径
origin_point = (0, -(total_width / 2) + 1000)  # origin_point[0], origin_point[1]
spiral_spacing_length = 1000.0  # 起始螺旋线横向长度
spiral_height = 305  # 螺旋线高度(保持不变)
spiral_length = 10000.0  # 起始螺旋线长度
spiral_length_gap = spiral_length  # 3组螺旋线长度的gap
io_gap_y = 500.0  # 波导y方向间距
group_gap = 500.0  # 组件y方向间距
width_gap = 0.020  # 波导间距
taper_gap = width_gap  # taper间距
width = width - width_gap  # 重新调整波导和taper的宽度
taper_width = taper_width - taper_gap
text_size = 50.0  # 字体大小
small_text_size = 30.0
die_text_size = 500  # die字体大小

# layer层定义
wg_layer = 1  # 波导层定义
text_layer = 3  # 字体层定义
bbox_layer = 4  # die_box层定义
marker_layer = 5  # marker层定义

# positive = waveguide.new_cell("positive")
# cell定义
positive = gf.Component("positive")
three_spiral_array = gf.Component("three_spiral")
waveguide_temp_array = gf.Component("waveguide_temp")
taper_temp_array = gf.Component("taper_temp")
text_temp_array = gf.Component("text_temp")

three_spiral = {}
waveguide_temp = {}
taper_temp = {}
text_temp = {}

# 切割die定义
# die.center=(0, 0)
die = gf.components.die(
    size=(die_length, die_width),
    street_width=street_width,
    street_length=street_length,
    die_name="wg_1 PEISL",
    text_size=die_text_size,
    text_location="N",
    layer=text_layer,
    bbox_layer=bbox_layer,
    draw_dicing_lane=True,
)
tk.add(positive, die)

# 0.1-0.9um宽度的waveguide
s_1 = []
# center_1 = [-(total_width / 2) + 100, -(total_width / 2) + 100]
center_1 = [0, -(total_width / 2) + 100]
P1 = gf.Path((center_1, (center_1[0] + 1000, center_1[1])))
for i in range(41):
    gt_width = 0.1
    s_1.append(
        gf.Section(
            width=gt_width + i * width_gap,
            offset=-i * 2,
            layer=(0, 0),
        )
    )
cross_1 = gf.CrossSection(width=0.1, name="wg", sections=s_1)
grating_1 = gf.path.extrude(P1, cross_1)
grating_text_1 = gf.components.text(
    text="'-' wg: 0.1-0.9",
    size=small_text_size,
    position=(grating_1.center[0] - 100, grating_1.center[1] + 60),
    layer=(text_layer, 0),
)
positive.add_ref(grating_1)
positive.add_ref(grating_text_1)

# 0.1-1.1um宽度的gap，波导宽度0.5um不变
s_2 = []
center_2 = [center_1[0], center_1[1] + 200]
grating_2 = gf.Component(name="'-'gap")
P2 = gf.Path((center_2, (center_2[0] + 1000, center_2[1])))
cross_2 = gf.CrossSection(width=0.5, name="wg")
wg_2 = gf.path.extrude(P2, layer=(0, 0), width=0.5)
grating_text_2 = gf.components.text(
    text="'-' gap: 0.1-1.1",
    size=small_text_size,
    position=(wg_2.center[0] - 100, wg_2.center[1] + 80),
    layer=(text_layer, 0),
)
for i in range(52):
    gt_gap_gap = 0.020
    gt_gap = 0.1 - gt_gap_gap
    grating_2.add_ref(wg_2).movey(i * (0.5 + gt_gap + (i + 1) * gt_gap_gap / 2))

grating_2.add_ref(grating_text_2)
positive.add_ref(grating_2)

# '+'resist 0.1-0.9um宽度的waveguide
grating_1_copy = grating_1.copy().move((0, 400))
grating_1_positive = gf.geometry.boolean(
    A=gf.components.rectangle(centered=True, size=(1010, 90), layer=(0, 0)).move(
        (grating_1_copy.center[0], grating_1_copy.center[1])
    ),
    B=grating_1_copy,
    operation="A-B",
    layer=(0, 0),
    name="'+'wg",
)
grating_1_text_positive = gf.components.text(
    text="'+' wg: 0.1-0.9",
    size=small_text_size,
    position=(grating_1_copy.center[0] - 100, grating_1_copy.center[1] + 60),
    layer=(text_layer, 0),
)
positive.add_ref(grating_1_positive)
positive.add_ref(grating_1_text_positive)

# '+' resist gap:0.1-1.1
grating_2_copy = grating_2.copy().move((0, 400))
grating_2_positive = gf.geometry.boolean(
    A=gf.components.rectangle(centered=True, size=(1010, 60), layer=(0, 0)).move(
        (grating_2_copy.center[0], grating_2_copy.center[1] - 30)
    ),
    B=grating_2_copy,
    operation="A-B",
    layer=(0, 0),
    name="'+'gap",
)
grating_2_text_positive = gf.components.text(
    text="'+' gap: 0.1-1.1",
    size=small_text_size,
    position=(grating_2_copy.center[0] - 100, grating_2_copy.center[1] + 40),
    layer=(text_layer, 0),
)
positive.add_ref(grating_2_positive)
positive.add_ref(grating_2_text_positive)

for j in range(6):
    width = width + width_gap
    small_margin = small_margin + width_gap
    big_margin = big_margin + width_gap
    taper_width = taper_width + taper_gap
    straight_point_y = j * (group_gap + io_gap_y * 3) + origin_point[1]
    # 直波导，设置wafer中心x为0
    straight_waveguide = gdspy.Path(
        width=small_margin,
        initial_point=(-waveguide_lengh / 2, straight_point_y),
        number_of_paths=2,
        distance=width + small_margin,
    ).segment(length=waveguide_lengh, direction="+x")
    taper1 = gdspy.Path(
        width=small_margin,
        initial_point=(waveguide_lengh / 2, straight_point_y),
        number_of_paths=2,
        distance=small_margin + width,
    ).segment(
        length=taper_length,
        direction="+x",
        final_width=2 * big_margin,
        final_distance=2 * big_margin + taper_width,
    )
    taper2 = gdspy.Path(
        width=small_margin,
        initial_point=(-waveguide_lengh / 2, straight_point_y),
        number_of_paths=2,
        distance=small_margin + width,
    ).segment(
        length=taper_length,
        direction="-x",
        final_width=2 * big_margin,
        final_distance=2 * big_margin + taper_width,
    )
    straight_waveguide_total = gdspy.boolean(
        gdspy.boolean(straight_waveguide, taper1, "or"), taper2, "or"
    )
    positive.add(straight_waveguide_total)
    positive.add(
        gdspy.Text(
            text="%d W:%dnm" % (j, width * 1000),
            size=text_size,
            position=(100, straight_point_y + text_size),
            layer=text_layer,
            datatype=0,
        )
    )
    # 每组三条螺旋线波导
    three_spiral[j] = gdspy.Cell("three_spiral_% d" % j)
    waveguide_temp[j] = gdspy.Cell("waveguide_temp_% d" % j)
    taper_temp[j] = gdspy.Cell("taper_temp_% d" % j)
    text_temp[j] = gdspy.Cell("text_temp_% d" % j)

    for i in range(1, 4):
        # 只允许螺旋线水平增加，垂直方向长度和圆角个数不变
        # 螺旋线高度为300um
        # 设置螺旋线的波导参数
        wgt = WaveguideTemplate(
            wg_width=width,
            clad_width=small_margin,
            bend_radius=bend_radius,
            resist="+",
            fab="ETCH",
            wg_layer=1,
            wg_datatype=0,
            clad_layer=2,
            clad_datatype=0,
        )
        port_y = j * (group_gap + io_gap_y * 3) + io_gap_y * i + origin_point[1]
        port_spacing = spiral_spacing_length + spiral_length * (i - 1) / 9.0
        spiral_temp = pc.Spiral(
            wgt=wgt,
            width=port_spacing,
            length=spiral_length * i,
            parity=1,
            port=(0, port_y),
            direction="WEST",
        )
        tk.add(three_spiral[j], spiral_temp)
        tk.build_mask(three_spiral[j], wgt, final_layer=0, final_datatype=0)
        # 两边直波导参数设置
        waveguide_temp_1 = gdspy.Path(
            width=small_margin,
            initial_point=(0, port_y),
            number_of_paths=2,
            distance=small_margin + width,
        ).segment(length=waveguide_lengh / 2, direction="+x")
        waveguide_temp_2 = gdspy.Path(
            width=small_margin,
            initial_point=(-port_spacing, port_y),
            number_of_paths=2,
            distance=small_margin + width,
        ).segment(length=waveguide_lengh / 2 - port_spacing, direction="-x")
        waveguide_temp[j].add((waveguide_temp_1, waveguide_temp_2))
        # taper参数设置
        taper_temp_1 = gdspy.Path(
            width=small_margin,
            initial_point=(waveguide_lengh / 2, port_y),
            number_of_paths=2,
            distance=small_margin + width,
        ).segment(
            length=taper_length,
            direction="+x",
            final_width=2 * big_margin,
            final_distance=2 * big_margin + taper_width,
        )
        taper_temp_2 = gdspy.Path(
            width=small_margin,
            initial_point=(-(waveguide_lengh / 2), port_y),
            number_of_paths=2,
            distance=small_margin + width,
        ).segment(
            length=taper_length,
            direction="-x",
            final_width=2 * big_margin,
            final_distance=2 * big_margin + taper_width,
        )
        taper_temp[j].add((taper_temp_1, taper_temp_2))
        # text文字参数设置
        text_temp_1 = gdspy.Text(
            text="%d W:%dnm L:%dcm" % (j, width * 1000, spiral_length * i / 10000.0),
            size=text_size,
            position=(100, port_y + text_size),
            layer=text_layer,
            datatype=0,
        )
        text_temp_2 = gdspy.Text(
            text="%d Taper_W:%dnm" % (j, taper_width * 1000),
            size=text_size,
            position=(-7000, port_y + text_size),
            layer=text_layer,
            datatype=0,
        )
        text_temp_3 = gdspy.Text(
            text="%d Taper_W:%dnm" % (j, taper_width * 1000),
            size=text_size,
            position=(6000, port_y + text_size),
            layer=text_layer,
            datatype=0,
        )
        text_temp[j].add((text_temp_1, text_temp_2, text_temp_3))

    # 使用tk.add()可以构建cell层级关系，但注意positive是gdspy.Cell类
    tk.add(three_spiral_array, three_spiral[j])
    tk.add(taper_temp_array, taper_temp[j])
    tk.add(waveguide_temp_array, waveguide_temp[j])
    tk.add(text_temp_array, text_temp[j])

# 最后向gds文件中添加顶部的cell
tk.add(positive, three_spiral_array)
tk.add(positive, taper_temp_array)
tk.add(positive, waveguide_temp_array)
tk.add(positive, text_temp_array)

positive.add_ref(
    cross_marker(
        cl_position=(-(total_length / 2) + 500, -(total_width / 2) + 500),
        cr_position=((total_length / 2) - 500, (total_width / 2) - 500),
    )
)


gt_my_temp = gt_my()
gt_my_temp_ref = positive << gt_my_temp
gt_my_temp_ref.move(destination=(-6000, 5800))
waveguide.add(positive)

waveguide.write_gds("waveguide_v2.gds")
gdspy.LayoutViewer(cells=positive)
