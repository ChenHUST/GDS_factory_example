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
from turtle import distance, left, pos, width
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

wg_width = 0.5
st_length = 12000.0
taper_length = 300.0

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


@gf.cell
def gt_rec(wg_width=0.5, st_length=12000.0, taper_length=300.0):
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
    st1.movex(-st1.size[0] / 2)
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


@gf.cell
def gt_focus(pitch=0.6887, dutycycle=0.53522, wg_width=0.5, st_length=12000.0):
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
        period=0.6887,
        ridge=False,
        dutycycle=0.53522,
    )
    gt_foc_2 = gf.read.from_picwriter(gt_foc_1)
    gt_foc_t = gf.geometry.boolean(
        gt_foc_2.extract(layers=gf.LAYER.WGCLAD),
        gt_foc_2.extract(layers=gf.LAYER.WG),
        "A-B",
        layer=(0, 0),
    )

    right_gt_ref = gt_sample << gt_foc_t
    left_gt = gt_foc_t.mirror()
    left_gt_ref = gt_sample << left_gt
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


# c = gf.components.grating_coupler_elliptical_arbitrary(
#     gaps=(0.32, 0.32) * 10,
#     widths=(0.3686, 0.3686) * 10,
#     taper_length=25,
#     taper_angle=50.0,
#     wavelength=0.785,
#     fiber_angle=16.8652,
#     neff=1,
#     nclad=1,
#     layer_slab="SLAB150",
#     slab_xmin=-25.0,
#     polarization="te",
#     fiber_marker_width=4.4,
#     fiber_marker_layer="TE",
#     spiked=True,
#     bias_gap=0,
#     cross_section=wg_cross_section,
# )
# c_in = c.extract(layers=gf.LAYER.WG)
# c = gf.components.grating_coupler_loss_fiber_single(
#     grating_coupler=c, cross_section=wg_cross_section, min_input_to_output_spacing=10000
# )
# wgt = WaveguideTemplate(
#     wg_width=0.5,
#     clad_width=3,
#     bend_radius=50,
#     resist="+",
#     fab="ETCH",
#     wg_layer=gf.LAYER.WG[0],
#     wg_datatype=0,
#     clad_layer=gf.LAYER.WGCLAD[0],
#     clad_datatype=0,
# )
# wg_cross_section = gf.CrossSection(
#     radius=50,
#     width=wg_width,
#     offset=0,
#     layer=gf.LAYER.WG,
#     cladding_layers=gf.LAYER.WGCLAD,
#     cladding_offsets=(3.0,),
#     name="wg",
#     port_names=("o1", "o2"),
# )
# st1 = gf.components.straight(length=100, cross_section=wg_cross_section)
# positive = gf.Component("top")
# positive << st1
c = gf.Component("ding0628")
d = gf.Component("ding0629")
c1 = c << gf.components.circle(radius=10, layer=(1, 0))
r1 = c << gf.components.rectangle(size=[20, 8], layer=(1, 0))
r1.move([100, -4])
ta1 = c << gf.components.taper(length=40, width1=15, width2=8, port=None, layer=(1, 0))
ta1.move([20, 10])
gf.functions.extract()
t = d << gf.geometry.boolean([c1, r1], operation="A+B", layer=(1, 0))
d.show()
# positive.show()
# positive.write_gds("test.gds")
# gdspy.LayoutViewer(cells=positive)
