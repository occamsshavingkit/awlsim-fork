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
from awlsim.core.blockinterface import *
from awlsim.core.memory import * #+cimport


class SFC4(SFC): #+cdef
	name = (4, "READ_RTM", "read runtime meter")

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="NR", dataType="BYTE"),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name="RET_VAL", dataType="INT"),
			BlockInterfaceField(name="CQ", dataType="BOOL"),
			BlockInterfaceField(name="CV", dataType="INT"),
		),
	}

	def __init__(self, cpu):
		SFC.__init__(self, cpu)
		# 8 runtime meters, each (running: bool, hours: int).
		# Until SFC 2 SET_RTM / SFC 3 CTRL_RTM are added, every meter
		# reads back (False, 0) — the correct state for a CPU that has
		# never started any runtime meter.
		self.__meters = [[False, 0] for _ in range(8)]

	def run(self): #+cpdef
#@cy		cdef S7StatusWord s
#@cy		cdef uint32_t nr

		s = self.cpu.statusWord

		nr = AwlMemoryObject_asScalar(
			self.fetchInterfaceFieldByName("NR"))

		if nr > 7:
			# Siemens SFC_e §6.5 mandates flat specific code 0x8080 for
			# NR out of range, not the general-code E_RPARM encoding.
			# See docs/siemens/SFC_e (1).pdf §6.5 and rowlf's FLAG-B
			# ruling (2026-04-17, user-ratified).
			self.storeInterfaceFieldByName("RET_VAL",
				make_AwlMemoryObject_fromScalar(0x8080, 16))
			self.storeInterfaceFieldByName("CQ",
				make_AwlMemoryObject_fromScalar(0, 1))
			self.storeInterfaceFieldByName("CV",
				make_AwlMemoryObject_fromScalar(0, 16))
			s.BIE = 0
			return

		running, hours = self.__meters[nr]

		self.storeInterfaceFieldByName("RET_VAL",
			make_AwlMemoryObject_fromScalar(0, 16))
		self.storeInterfaceFieldByName("CQ",
			make_AwlMemoryObject_fromScalar(1 if running else 0, 1))
		self.storeInterfaceFieldByName("CV",
			make_AwlMemoryObject_fromScalar(hours & 0xFFFF, 16))
		s.BIE = 1
