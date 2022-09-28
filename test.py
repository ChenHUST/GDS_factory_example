"""/*
 * @Author: wenyuchen 
 * @Date: 2022-09-08 20:50:15 
 * @Last Modified by:   wenyuchen 
 * @Last Modified time: 2022-09-08 20:50:15 
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


mzi_test = PISL_PDK.mzi_oneside()
mzi_test.show()
