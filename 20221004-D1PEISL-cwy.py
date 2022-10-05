"""
/* 2X2MMI directional coupler以及grating coupler
 * @Author: wenyuchen 
 * @Date: 2022-10-04 15:25:28 
 * @Last Modified by: wenyuchen
 * @Last Modified time: 2022-10-04 21:18:59
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
import PISL_PDK

###################### photonic integrated circuits 参数定义 ##########################
# 默认单位为1um，精度为1nm
"""
    工艺补偿值
    波导宽度补偿值：+50nm
    gap宽度补偿值：-75nm
    grating_coupler：   duty_cycle 补偿值+0.08
                        pitch 补偿值 0-5nm
"""
width_off = +0.05
gap_off = -0.08
duty_cycle_off = +0.08
pitch_off = 0.005
mmi_width_off = +0.05
mmi_length_off = +0.05

# 工艺设计值
wg_width = 0.5  # 波导宽度
clad_width = 3.0  # 波导刻蚀两边宽度
radius = 30  # 弯曲波导半径
one_side_st = 50  # 单边波导长度
total_length = 160  # 单个mzi块或者mmi块总长

# grating coupelr相关参数
pitch = 0.707  # grating_coupler 周期
duty_cycle = 0.528  # grating_coupler 占空比
period_number = 20  # grating_coupler 周期数
gt_radius = 15  # grating_coupler taper长度
alpha = np.pi / 7.2  # grating_coupler 扇形角度

# mzi相关参数
mzi_gap = 0.2
mzi_sep = 80
mzi_sben_seq = 10
s_bend_length = 20
coupler_length = 8.8
mzi_iolength = 5

# mmi相关参数
mmi_width = 6
mmi_length = 53.568
mmi_sep = 80
wg_seperate = 2.085
taper_width = 1.1
taper_length = 11
mmi_iolength = 0

# 螺旋线相关参数
bend_radius = 30.0  # 螺旋线弯曲半径
origin_point = (0, 0)  # origin_point[0], origin_point[1]
spiral_spacing_length = 300.0  # 起始螺旋线横向长度
spiral_length = 3000.0  # 起始螺旋线长度
spiral_num = 2  # 螺旋线数量
io_gap_y = 250.0  # 波导y方向间距
group_gap = (spiral_num + 1) * io_gap_y  # 组间y方向间距
(street_width, street_length) = (30.0, 300.0)  # die切割的宽度和长度预留

# 标注尺寸相关参数
die_total_length = 3000
text_size = 40.0  # 字体大小
die_text_size = 100

# 工艺补偿值后
wg_width = wg_width + width_off
mzi_gap = mzi_gap + gap_off
duty_cycle = duty_cycle + duty_cycle_off
pitch = pitch
mmi_width = mmi_width + mmi_width_off
mmi_length = mmi_length + mmi_length_off

###c/c################### photonic integrated circuits 参数定义 ##########################

D1PISL = gf.Component("D1PISL")

die = gf.components.die(
    size=(die_total_length + 500, 2500),
    street_width=street_width,
    street_length=street_length,
    die_name="D1PISL",
    text_size=die_text_size,
    text_location="N",
    layer=gf.LAYER.TEXT,
    bbox_layer=4,
    draw_corners=True,
    draw_dicing_lane=False,
)

# mzi group
mzi_1 = PISL_PDK.mzi_oneside(
    wg_width,
    clad_width,
    radius,
    io_gap_y,
    one_side_st,
    mzi_sep,
    mzi_gap,
    mzi_sben_seq,
    s_bend_length,
    coupler_length,
    total_length,
    mzi_iolength,
    pitch,
    duty_cycle,
    alpha,
    gt_radius,
    period_number,
    text_size,
    1,
)
mzi_2 = PISL_PDK.mzi_oneside(
    wg_width,
    clad_width,
    radius,
    io_gap_y,
    one_side_st,
    mzi_sep,
    mzi_gap + 0.01,
    mzi_sben_seq,
    s_bend_length,
    coupler_length,
    total_length,
    mzi_iolength,
    pitch,
    duty_cycle,
    alpha,
    gt_radius,
    period_number,
    text_size,
    2,
)
mzi_3 = PISL_PDK.mzi_oneside(
    wg_width,
    clad_width,
    radius,
    io_gap_y,
    one_side_st,
    mzi_sep,
    mzi_gap + 0.02,
    mzi_sben_seq,
    s_bend_length,
    coupler_length,
    total_length,
    mzi_iolength,
    pitch,
    duty_cycle,
    alpha,
    gt_radius,
    period_number,
    text_size,
    3,
)

# mmi group
mmi_1 = PISL_PDK.mmi2x2_oneside(
    wg_width,
    clad_width,
    radius,
    io_gap_y,
    one_side_st,
    taper_width,
    taper_length,
    mmi_length,
    mmi_width,
    wg_seperate,
    total_length,
    mmi_sep,
    mmi_iolength,
    pitch,
    duty_cycle,
    alpha,
    gt_radius,
    period_number,
    text_size,
    1,
)
mmi_2 = PISL_PDK.mmi2x2_oneside(
    wg_width,
    clad_width,
    radius,
    io_gap_y,
    one_side_st,
    taper_width,
    taper_length,
    mmi_length,
    mmi_width + 0.01,
    wg_seperate,
    total_length,
    mmi_sep,
    mmi_iolength,
    pitch,
    duty_cycle,
    alpha,
    gt_radius,
    period_number,
    text_size,
    2,
)
# spiral group
sp1 = PISL_PDK.spiral_group_oneside(
    wg_width,
    clad_width,
    one_side_st,
    bend_radius,
    pitch,
    duty_cycle,
    alpha,
    gt_radius,
    period_number,
    io_gap_y,
    text_size,
    spiral_spacing_length,
    spiral_length,
    spiral_num,
    group_id=1,
)
sp2 = PISL_PDK.spiral_group_oneside(
    wg_width,
    clad_width,
    one_side_st,
    bend_radius,
    pitch + pitch_off,
    duty_cycle,
    alpha,
    gt_radius,
    period_number,
    io_gap_y,
    text_size,
    spiral_spacing_length,
    spiral_length,
    spiral_num,
    group_id=2,
)

mzi_1_ref = D1PISL << mzi_1
mzi_2_ref = D1PISL << mzi_2
mzi_3_ref = D1PISL << mzi_3
die_ref = D1PISL << die
mzi_1_ref.move(destination=(-125 - 1000, -1000))
mzi_2_ref.move(destination=(-125, -1000))
mzi_3_ref.move(destination=(-125 + 1000, -1000))

mmi_1_ref = D1PISL << mmi_1
mmi_2_ref = D1PISL << mmi_2
mmi_1_ref.move(destination=(-125 - 500, -500))
mmi_2_ref.move(destination=(-125 + 500, -500))

sp_1_ref = D1PISL << sp1
sp_2_ref = D1PISL << sp2
sp_1_ref.move(destination=(0, 0))
sp_2_ref.move(destination=(0, 500))

D1PISL << gf.geometry.boolean(
    D1PISL.extract(layers=gf.LAYER.WGCLAD),
    D1PISL.extract(layers=gf.LAYER.WG),
    "A-B",
    max_points=199,
    layer=(0, 0),
)
D1PISL_2 = D1PISL.copy()
D1PISL_2_ref = D1PISL << D1PISL_2
D1PISL_2_ref.move(destination=(0, -6000))
D1PISL.show()

D1_PEISL = D1PISL.extract(layers=[(0, 0), (66, 0), (10, 0)])
D1_PEISL.write_gds("20221004-D1PISL-cwy.gds")
