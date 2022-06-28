"""
_summary_ 
1. 加工单个和多个级联的MZI
2. 加工grating coupler，实现光耦合
 * @Author: wenyu chen
 * @Date: 2022-06-01 15:29:12 
 * @Last Modified by: mikey.zhaopeng
 * @Last Modified time: 2022-06-15 15:29:33
 TODO 后续需要更新'+'resist
 """

from audioop import add, cross
from base64 import standard_b64decode
from calendar import c
from cgi import test
from cgitb import small
from dis import dis
from importlib.resources import path
from msilib.schema import Component
from re import T

# from readline import set_history_length
from shutil import move
from turtle import distance, pos, width
from unicodedata import name
from matplotlib import markers
from matplotlib.pyplot import connect, text
import numpy as np
import gdspy
import gdsfactory as gf
from phidl import Layer, Port
from picwriter import toolkit as tk
from picwriter.components.waveguide import WaveguideTemplate, Waveguide
import picwriter.components as pc
from pyrsistent import s

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
    bottom.add_port("o1", port=bend_1_ref.ports["o2"], width=wg_width)
    bottom.add_port("o2", port=bend_2_ref.ports["o1"], width=wg_width)
    bottom.show()
    point_1 = (
        bottom.extract(layers=gf.LAYER.WG).center[0],
        bottom.extract(layers=gf.LAYER.WG).ymax + mzi_gap / 2,
    )
    point_2 = (point_1[0] + mzi_gap / 2, point_1[1])
    top = gf.functions.mirror(component=bottom, p1=point_1, p2=point_2)
    top_ref = c << top
    bottom_ref = c << bottom
    c.add_port("o1", port=top_ref.ports["o1"], width=wg_width)
    c.add_port("o2", port=bottom_ref.ports["o1"], width=wg_width)
    c.add_port("o3", port=top_ref.ports["o2"], width=wg_width)
    c.add_port("o4", port=bottom_ref.ports["o2"], width=wg_width)
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
    l_length=12750.3,
    s_length=500,
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
        total_length
        - mzi_ex_ref.size[0]
        - 2 * taper_length
        - 4 * eular_radius
        - 2 * mzi_iolength
    ) / 2
    wg_connect_tl = wg_connect(
        cross_section=cross_section,
        l_length=wg_straight_iolength,
        s_length=s_length,
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
    c.show()
    return c


# 创建gds文件
# 默认单位为1um，精度为1nm
# 晶圆大小为15000um宽 X 15000um长 (1.5cm X 1.5cm)
# 考虑划片机误差(5um)以及deep trench工艺(5um左右)，实际使用宽14990um
mzi_sample = gdspy.GdsLibrary()
# posutive resist example
# 目标width:500nm
# 目标taper_width:100mm
# 设置相关尺寸参数
# TODO 需根据工艺参数对具体参数设置值进行校正(目前设置为理想值)
wg_width = 0.5
mzi_gap = 0.2
coupler_length = 14.7
small_margin = 3.0
big_margin = 5.0
(die_length, die_width) = (15000.0, 15000.0)  # die长度和宽度
(street_width, street_length) = (100.0, 1000.0)  # die切割的宽度和长度预留
lito_taper_length = 10.0  # 预留端部光刻长度
# total_length/total_width die上可用的总长和总宽
total_length = die_length - 2 * street_width - 2 * lito_taper_length
total_width = die_width - 2 * street_width - 2 * lito_taper_length
taper_length = 400.0  # taper的长度
waveguide_lengh = total_length - 2 * taper_length  # 中间waveguide长度
taper_width = 0.1  # taper的宽度
origin_point = (0, 0)  # die中间点
pitch_y = 250
group_gap = 1000
text_size = 60
mzi_sbend_length = 50
mzi_sbend_seq = 40
eular_radius = (pitch_y - mzi_sbend_seq) / 4  # 欧拉半径
die_text_size = 500  # die字体大小
mzi_iolength = 500
mzi_length = 2 * mzi_sbend_length + coupler_length + 2 * mzi_iolength

# layer层定义
wg_layer = 1  # 波导层定义
clad_layer = 2  # cladding层定义
text_layer = 3  # 字体层定义
bbox_layer = 4  # die_box层定义
marker_layer = 5  # marker层定义

# top cell定义
positive = gf.Component("positive")
mzi_cell = gf.Component("mzi")
# 切割die定义
# die.center=(0, 0)
die = gf.components.die(
    size=(die_length, die_width),
    street_width=street_width,
    street_length=street_length,
    die_name="mzi_1 PEISL",
    text_size=die_text_size,
    text_location="N",
    layer=gf.LAYER.TEXT,
    bbox_layer=gf.LAYER.FLOORPLAN,
    draw_dicing_lane=True,
)
positive << die

# 波导样式 picwriter
wgt = WaveguideTemplate(
    wg_width=wg_width,
    clad_width=big_margin,
    bend_radius=eular_radius,
    resist="+",
    fab="ETCH",
    wg_layer=1,
    wg_datatype=0,
    clad_layer=2,
    clad_datatype=0,
    euler_bend=False,
)
# cross_section样式 gdsfactory
wg_cross_section = gf.CrossSection(
    radius=eular_radius,
    width=wg_width,
    offset=0,
    layer=gf.LAYER.WG,
    cladding_layers=gf.LAYER.WGCLAD,
    cladding_offsets=(3.0,),
    name="wg",
    port_names=("o1", "o2"),
)
edge_coupler_custom = gf.partial(
    gf.components.taper, width2=taper_width, length=taper_length, with_two_ports=False
)
taper_in = gf.components.edge_coupler_array(
    edge_coupler=edge_coupler_custom,
    n=4,
    pitch=pitch_y,
    h_mirror=True,
    v_mirror=False,
    text_offset=(-700, 20),
)
taper_in_ref = positive << taper_in
taper_in_ref.movex(destination=(-total_length / 2 - taper_in_ref.xmin))
taper_out = gf.components.edge_coupler_array(
    edge_coupler=edge_coupler_custom,
    n=4,
    pitch=pitch_y,
    h_mirror=False,
    v_mirror=False,
    text_offset=(100, 20),
)
taper_out_ref = positive << taper_out
mzi_sample_1 = mzi_instance(
    cross_section=wg_cross_section,
    width=wg_width,
    mzi_gap=mzi_gap,
    mzi_sbend_seq=mzi_sbend_seq,
    s_bend_length=mzi_sbend_length,
    coupler_length=coupler_length,
    s_length=mzi_iolength,
)
mzi_sample_1_ref = positive << mzi_sample_1
mzi_sample_1_ref.connect("o1", destination=taper_in_ref.ports["o1"])
taper_out_ref.connect("o4", destination=mzi_sample_1_ref.ports["o3"])

mzi_sample_2 = mzi_instance(
    cross_section=wg_cross_section,
    width=wg_width,
    mzi_gap=mzi_gap,
    mzi_sbend_seq=mzi_sbend_seq,
    s_bend_length=mzi_sbend_length,
    coupler_length=20,
    s_length=mzi_iolength,
)
mzi_sample_2_ref = positive << mzi_sample_2
mzi_sample_2_ref.connect("o1", destination=taper_in_ref.ports["o3"])
taper_out_ref.connect("o2", destination=mzi_sample_2_ref.ports["o3"])

# mzi_test_ref.connect('o1', )
# mzi_cell_ref.move(destination=(-mzi_1_ref.center[0], -mzi_1_ref.center[1]))
positive.show()
# 添加top cell并写入gds中
mzi_sample.add(positive)
mzi_sample.write_gds("mzi_sample.gds")
