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

extrac_gds = gf.read.import_gds("")
