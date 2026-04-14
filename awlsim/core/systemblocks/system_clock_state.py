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


# Offset added to wall-clock reads. SFC 0 SET_CLK installs an offset such
# that the next datetime.now() + offset equals the requested clock value.
# Module-level rather than per-CPU because the upstream awlsim CPU class
# is intentionally untouched in this fork.
_wallClockOffset = datetime.timedelta(0)


def getCurrentDateTime():
	"""Return the current CPU wall-clock time as a Python datetime.

	Applies the SFC 0 SET_CLK offset so that SFC 1 READ_CLK and all
	other clock-reading SFCs see the time the user installed.
	"""
	return datetime.datetime.now() + _wallClockOffset


def setWallClock(dt):
	"""Install a wall-clock offset so that the next getCurrentDateTime()
	call returns `dt`.
	"""
	global _wallClockOffset
	_wallClockOffset = dt - datetime.datetime.now()


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


def _bcd2_to_int(byte):
	"""Decode one BCD byte. Returns -1 if either nibble is not 0..9."""
	hi = (byte >> 4) & 0xF
	lo = byte & 0xF
	if hi > 9 or lo > 9:
		return -1
	return hi * 10 + lo


def dt_bytes_to_datetime(bs):
	"""Decode an 8-byte BCD DATE_AND_TIME into a Python datetime.

	Returns (datetime, 0) on success.
	On invalid date components returns (None, 0x8080).
	On invalid time components returns (None, 0x8081).

	Year window matches awlsim's tryParseImmediate_DT(): BCD year
	90-99 maps to 19yy, 00-89 maps to 20yy. The weekday nibble
	supplied by the caller is ignored — Siemens recomputes it from
	the date.
	"""
	if len(bs) < 8:
		return (None, 0x8080)

	yy = _bcd2_to_int(bs[0])
	mo = _bcd2_to_int(bs[1])
	da = _bcd2_to_int(bs[2])
	hh = _bcd2_to_int(bs[3])
	mm = _bcd2_to_int(bs[4])
	ss = _bcd2_to_int(bs[5])

	# msec is 12 bits across bytes 6 and the high nibble of byte 7
	ms_hi = _bcd2_to_int(bs[6])
	ms_lo_nib = (bs[7] >> 4) & 0xF
	if ms_hi < 0 or ms_lo_nib > 9:
		return (None, 0x8081)
	msec = ms_hi * 10 + ms_lo_nib

	if yy < 0 or mo < 0 or da < 0:
		return (None, 0x8080)
	year = 1900 + yy if yy >= 90 else 2000 + yy

	try:
		date_part = datetime.date(year, mo, da)
	except ValueError:
		return (None, 0x8080)

	if hh < 0 or mm < 0 or ss < 0:
		return (None, 0x8081)
	if hh > 23 or mm > 59 or ss > 59 or msec > 999:
		return (None, 0x8081)

	return (datetime.datetime(year, mo, da, hh, mm, ss, msec * 1000), 0)
