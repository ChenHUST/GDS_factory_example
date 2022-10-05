"""/*
 * @Author: wenyuchen 
 * @Date: 2022-09-08 20:50:15 
 * @Last Modified by:   wenyuchen 
 * @Last Modified time: 2022-09-08 20:50:15 
 */
"""
from audioop import add, cross
from base64 import standard_b64decode
from cgi import test
from cgitb import small
from dis import dis
from msilib.schema import Component
from operator import gt
from re import T
from shutil import move
from turtle import distance, pos, right, width
from unicodedata import mirrored, name
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

wg_cross_section = gf.CrossSection(
    radius=30,
    width=0.5,
    offset=0,
    layer=gf.LAYER.WG,
    cladding_layers=gf.LAYER.WGCLAD,
    cladding_offsets=(3,),
    name="wg",
    port_names=("o1", "o2"),
)
wgt = WaveguideTemplate(
    wg_width=0.5,
    clad_width=3,
    bend_radius=30,
    resist="+",
    fab="ETCH",
    wg_layer=gf.LAYER.WG[0],
    wg_datatype=0,
    clad_layer=gf.LAYER.WGCLAD[0],
    clad_datatype=0,
)

spiral_temp = pc.Spiral(
    wgt=wgt,
    width=300,
    length=3000,
    parity=1,
    port=(0, 0),
    direction="WEST",
)
gf_spiral_t = gf.read.from_picwriter(spiral_temp)

# c1 = gf.components.bend_circular(angle=90, cross_section=wg_cross_section)
gf_spiral_t.show()
