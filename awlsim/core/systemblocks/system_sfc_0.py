# -*- coding: utf-8 -*-
#
# AWL simulator - SFCs
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.exceptions import *
from awlsim.common.util import *

from awlsim.core.systemblocks.systemblocks import * #+cimport
from awlsim.core.systemblocks.system_clock_state import (
	dt_bytes_to_datetime,
	setWallClock,
)
from awlsim.core.blockinterface import *
from awlsim.core.memory import * #+cimport


class SFC0(SFC): #+cdef
	name = (0, "SET_CLK", "set system clock")

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="PDT", dataType="DATE_AND_TIME"),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name="RET_VAL", dataType="INT"),
		),
	}

	def run(self): #+cpdef
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord

		pdt_bytes = AwlMemoryObject_asBytes(
			self.fetchInterfaceFieldByName("PDT"))
		dt, err = dt_bytes_to_datetime(pdt_bytes)

		if err != 0:
			# 0x8080 = invalid date, 0x8081 = invalid time (SFC_e ch 5.1).
			self.storeInterfaceFieldByName("RET_VAL",
				make_AwlMemoryObject_fromScalar(err, 16))
			s.BIE = 0
			return

		setWallClock(dt)

		self.storeInterfaceFieldByName("RET_VAL",
			make_AwlMemoryObject_fromScalar(0, 16))
		s.BIE = 1
