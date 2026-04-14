# -*- coding: utf-8 -*-
#
# AWL simulator - Wall-clock state and DATE_AND_TIME BCD codec
# shared by clock-related SFCs (read and set).
#
# Copyright 2026 QuackS7 contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.common.compat import *

import datetime


# Siemens DT weekday encoding: 1=Sunday .. 7=Saturday.
# Python datetime.weekday(): 0=Monday .. 6=Sunday.
_PY_TO_DT_WEEKDAY = (2, 3, 4, 5, 6, 7, 1)


def getCurrentDateTime():
	"""Return the current CPU wall-clock time as a Python datetime.

	SFC 1 READ_CLK uses this as its time source. When SFC 0 SET_CLK is
	added, it will extend this function to apply a module-level offset.
	"""
	return datetime.datetime.now()


def datetime_to_dt_bytes(dt):
	"""Encode a Python datetime as the 8-byte BCD DATE_AND_TIME representation.

	Layout matches SFC_e ch 5.2 and awlsim's tryParseImmediate_DT().
	"""
	year = dt.year % 100
	month = dt.month
	day = dt.day
	hour = dt.hour
	minute = dt.minute
	second = dt.second
	msec = dt.microsecond // 1000
	weekday = _PY_TO_DT_WEEKDAY[dt.weekday()]

	def bcd2(v):
		return (v % 10) | (((v // 10) % 10) << 4)

	msec_bcd = (msec % 10) | (((msec // 10) % 10) << 4) | (((msec // 100) % 10) << 8)

	return bytearray((
		bcd2(year), bcd2(month), bcd2(day),
		bcd2(hour), bcd2(minute), bcd2(second),
		(msec_bcd >> 4) & 0xFF,
		((msec_bcd & 0xF) << 4) | weekday,
	))
