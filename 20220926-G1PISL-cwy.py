"""
/* Grating coupler耦合效率及波导损耗测试
 * @Author: wenyuchen 
 * @Date: 2022-09-09 09:03:45 
 * @Last Modified by: wenyuchen
 * @Last Modified time: 2022-10-04 19:01:35
 *
 
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
gap_off = -0.075
duty_cycle_off = +0.08
pitch_off = 0.005

# 工艺设计值
wg_width = 0.5  # 波导宽度
clad_width = 3.0  # 波导刻蚀两边宽度
dc_gap = 0.2  # 定向耦合器gap宽度
pitch = 0.707  # grating_coupler 周期
duty_cycle = 0.528  # grating_coupler 占空比
period_number = 20  # grating_coupler 周期数
gt_radius = 15  # grating_coupler taper长度
alpha = np.pi / 7.2  # grating_coupler 扇形角度
total_length = 3500  # 中间波导总长（确定可以容纳两边光纤阵列）

bend_radius = 50.0  # 螺旋线弯曲半径
origin_point = (0, 0)  # origin_point[0], origin_point[1]
spiral_spacing_length = 500.0  # 起始螺旋线横向长度
spiral_length = 6000.0  # 起始螺旋线长度
spiral_num = 2  # 螺旋线数量
io_gap_y = 250.0  # 波导y方向间距
group_gap = (spiral_num + 1) * io_gap_y  # 组间y方向间距
(street_width, street_length) = (30.0, 300.0)  # die切割的宽度和长度预留
text_size = 15.0  # 字体大小
die_text_size = 100

# 工艺补偿值后
wg_width = wg_width + width_off
dc_gap = dc_gap + gap_off
duty_cycle = duty_cycle + duty_cycle_off
pitch = pitch

###################### photonic integrated circuits 参数定义 ##########################

G1PISL = gf.Component("G1PISL")

die = gf.components.die(
    size=(total_length + 500, 3500),
    street_width=street_width,
    street_length=street_length,
    die_name="G1PISL",
    text_size=die_text_size,
    text_location="N",
    layer=gf.LAYER.TEXT,
    bbox_layer=4,
    draw_corners=True,
    draw_dicing_lane=False,
)
sp_group1 = PISL_PDK.spiral_group(
    wg_width=wg_width,
    clad_width=clad_width,
    bend_radius=bend_radius,
    st_length=total_length,
    pitch=pitch,
    duty=duty_cycle,
    alpha=alpha,
    radius=gt_radius,
    period_num=period_number,
    io_gap=io_gap_y,
    group_id=1,
    t_size=text_size,
    spiral_spacing_length=spiral_spacing_length,
    spiral_length=spiral_length,
    spiral_num=spiral_num,
)
sp_group2 = PISL_PDK.spiral_group(
    wg_width=wg_width,
    clad_width=clad_width,
    bend_radius=bend_radius,
    st_length=total_length,
    pitch=pitch + pitch_off,
    duty=duty_cycle,
    alpha=alpha,
    radius=gt_radius,
    period_num=period_number,
    io_gap=io_gap_y,
    group_id=2,
    t_size=text_size,
    spiral_spacing_length=spiral_spacing_length,
    spiral_length=spiral_length,
    spiral_num=spiral_num,
)
mzi_1 = PISL_PDK.mzi_single(
    wg_width=wg_width,
    clad_width=clad_width,
    io_gap=io_gap_y,
    mzi_gap=dc_gap,
    s_bend_length=20,
    coupler_length=8.8,
    pitch=pitch,
    duty=duty_cycle,
    alpha=alpha,
    gt_radius=gt_radius,
    period_num=period_number,
    total_length=total_length,
    mzi_iolength=250,
    t_size=text_size,
    group_id=1,
)
mzi_1_ref = G1PISL << mzi_1
sp_group1_ref = G1PISL << sp_group1
sp_group2_ref = G1PISL << sp_group2
mzi_1_ref.move(destination=(0, -1000))
die_ref = G1PISL << die
sp_group1_ref.move(destination=(0, -group_gap))

# G1PISL.show()

G1_PEISL = G1PISL.extract(layers=[(0, 0), (66, 0), (10, 0)])
G1_PEISL.write_gds("20220926-G1PISL-cwy.gds")
