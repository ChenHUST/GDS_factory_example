"""
_summary_ 
不同长度的波导(Spiral结构)
本版本主要使用gdspy
目的:
    1. 根据加工和观察确定->加工尺寸和波导宽度的关系
    2. 加工三条长度不同的结构->确定波导损耗
    3. 确定水平耦合的耦合效率
    4. 确定弯曲波导的波导损耗
 * @Author: wenyu chen
 * @Date: 2022-06-01 15:29:12 
 * @Last Modified by: mikey.zhaopeng
 * @Last Modified time: 2022-06-01 15:29:33
 """

from audioop import add
from base64 import standard_b64decode
from turtle import distance, width
from matplotlib.patches import Polygon
from matplotlib.pyplot import text
import numpy as np
import gdspy
import gdsfactory as gf
from phidl import Layer

if __name__ == "__main__":
    # 创建gds文件
    # 默认单位为1um，精度为1nm
    # 晶圆大小为15000um X 15000um (1.5cm X 1.5cm)
    # 考虑划片机误差(5um)以及deep trench工艺(5um左右)，实际使用面积14990um X 14990um
    waveguide = gdspy.GdsLibrary()

    # posutive resist example
    # 目标width:500nm
    # 目标taper_width:100mm
    width = 0.46
    small_margin = 3.0
    big_margin = 5.0
    total_length = 14990.0
    taper_length = 400.0
    waveguide_lengh = total_length - 2 * taper_length
    taper_width = 0.06
    bend_radius = 50.0
    origin_point = (0, 0)
    spiral_spacing_length = 1000.0
    spiral_length = 10000.0
    spiral_length_gap = spiral_length
    io_gap_y = 500
    group_gap = 1000
    width_gap = 0.020
    taper_gap = width_gap
    spiral_height = 305
    width = width - width_gap
    taper_width = taper_width - taper_gap
    text_size = 50

    positive = waveguide.new_cell("positive")
    three_spiral = {}
    waveguide_temp = {}
    taper_temp = {}
    text_temp = {}

    for j in range(8):
        width = width + width_gap
        small_margin = small_margin + width_gap
        big_margin = big_margin + width_gap
        taper_width = taper_width + taper_gap
        # 直波导，设置wafer中心x为0
        straight_waveguide = gdspy.Path(
            width=small_margin,
            initial_point=(-waveguide_lengh / 2, j * (group_gap + io_gap_y * 3)),
            number_of_paths=2,
            distance=width + small_margin,
        ).segment(length=waveguide_lengh, direction="+x")
        taper1 = gdspy.Path(
            width=small_margin,
            initial_point=(waveguide_lengh / 2, j * (group_gap + io_gap_y * 3)),
            number_of_paths=2,
            distance=small_margin + width,
        ).segment(
            length=taper_length,
            direction="+x",
            final_width=2 * big_margin,
            final_distance=2 * big_margin + 0.1,
        )
        taper2 = gdspy.Path(
            width=small_margin,
            initial_point=(-waveguide_lengh / 2, j * (group_gap + io_gap_y * 3)),
            number_of_paths=2,
            distance=small_margin + width,
        ).segment(
            length=taper_length,
            direction="-x",
            final_width=2 * big_margin,
            final_distance=2 * big_margin + 0.1,
        )
        straight_waveguide_total = gdspy.boolean(
            gdspy.boolean(straight_waveguide, taper1, "or"), taper2, "or"
        )
        positive.add(straight_waveguide_total)

        positive.add(
            gdspy.Text(
                text="%d W:%dnm" % (j, width * 1000),
                size=text_size,
                position=(100, j * (group_gap + io_gap_y * 3) + text_size),
                layer=1,
                datatype=0,
            )
        )

        # 每组三条螺旋线波导
        three_spiral[j] = waveguide.new_cell("three_spiral_% d" % j)
        waveguide_temp[j] = waveguide.new_cell("waveguide_temp_% d" % j)
        taper_temp[j] = waveguide.new_cell("taper_temp_% d" % j)
        text_temp[j] = waveguide.new_cell("text_temp_% d" % j)
        for i in range(1, 4):
            # 只允许螺旋线水平增加，垂直方向长度和圆角个数不变
            # 螺旋线高度为300um
            port_y = j * (group_gap + io_gap_y * 3) + io_gap_y * i
            port_spacing = spiral_spacing_length + spiral_length * (i - 1) / 9.0
            c = gf.components.spiral(
                port_spacing=port_spacing,
                length=spiral_length * i,
                parity=1,
                port=(0, port_y),
                direction="WEST",
                layer="WG",
                layer_cladding="WGCLAD",
                cladding_offset=small_margin,
                wg_width=width,
                radius=bend_radius,
            )
            polygon = c.get_polygons(by_spec=True)
            inner_c = polygon[gf.LAYER.WG]
            # rec_c = polygon[gf.LAYER.WGCLAD]
            rec_c = gdspy.Rectangle(
                (small_margin, -small_margin - width / 2 + port_y),
                (
                    -(spiral_spacing_length + spiral_length * (i - 1) / 9.0),
                    spiral_height + port_y,
                ),
            )
            three_spiral[j].add(
                gdspy.boolean(
                    gdspy.boolean(rec_c, inner_c, "not", max_points=8192),
                    gdspy.Path(
                        width=width, initial_point=(0, port_y), number_of_paths=1
                    ).segment(length=small_margin, direction="+x"),
                    "not",
                    max_points=8192,
                )
            )

            waveguide_temp_1 = gdspy.Path(
                width=small_margin,
                initial_point=(small_margin, port_y),
                number_of_paths=2,
                distance=small_margin + width,
            ).segment(length=waveguide_lengh / 2 - small_margin, direction="+x")
            waveguide_temp_2 = gdspy.Path(
                width=small_margin,
                initial_point=(-port_spacing, port_y),
                number_of_paths=2,
                distance=small_margin + width,
            ).segment(length=waveguide_lengh / 2 - port_spacing, direction="-x")
            waveguide_temp[j].add((waveguide_temp_1, waveguide_temp_2))

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
            text_temp_1 = gdspy.Text(
                text="%d W:%dnm L:%dcm"
                % (j, width * 1000, spiral_length * i / 10000.0),
                size=text_size,
                position=(100, port_y + text_size),
                layer=1,
                datatype=0,
            )
            text_temp_2 = gdspy.Text(
                text="%d Taper_W:%dnm" % (j, taper_width * 1000),
                size=text_size,
                position=(-7000, port_y + text_size),
                layer=1,
                datatype=0,
            )
            text_temp_3 = gdspy.Text(
                text="%d Taper_W:%dnm" % (j, taper_width * 1000),
                size=text_size,
                position=(6000, port_y + text_size),
                layer=1,
                datatype=0,
            )
            text_temp[j].add((text_temp_1, text_temp_2, text_temp_3))

        # gdspy.boolean(gdspy.boolean(three_spiral[j], taper_temp[j], 'or'), waveguide_temp[j], 'or')
        positive.add(three_spiral[j])
        positive.add(taper_temp[j])
        positive.add(waveguide_temp[j])
        positive.add(text_temp[j])

    waveguide.write_gds("waveguide.gds")
    gdspy.LayoutViewer(library=waveguide)
