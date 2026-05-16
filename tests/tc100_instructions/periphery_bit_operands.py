from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim_tstlib import *
initTest(__file__)

import os
import shutil
import subprocess
import sys
import tempfile


class Test_PeripheryBitOperands(TestCase):
	def runAwl(self, source, hardware=None, mnemonics="auto",
		   extraPythonPath=None):
		rootdir = os.path.abspath(os.path.join(os.path.dirname(__file__),
						       "..", ".."))
		fd, path = tempfile.mkstemp(prefix="awlsim-periphery-bit-",
					    suffix=".awl")
		try:
			with os.fdopen(fd, "wb") as awlFile:
				awlFile.write(source.encode("ascii"))

			cmd = (
				sys.executable,
				os.path.join(rootdir, "awlsim-test"),
				"--loglevel", "0",
				"--extended-insns",
				"--mnemonics", mnemonics,
				"--cycle-limit", "60",
				"--max-runtime", "5",
			)
			if hardware is None:
				hardware = "debug:inputAddressBase=7:"\
					   "outputAddressBase=8:dummyParam=True"
			if hardware:
				cmd += ("--hardware", hardware)
			cmd += (path, )
			env = os.environ.copy()
			if extraPythonPath:
				env["PYTHONPATH"] = (
					extraPythonPath + os.pathsep +
					env.get("PYTHONPATH", ""))
			proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
						stderr=subprocess.STDOUT,
						env=env)
			output = proc.communicate()[0]
			if proc.returncode:
				self.fail("%s failed with exit code %d\n%s" % (
					" ".join(cmd), proc.returncode,
					output.decode("utf-8", "replace")))
		finally:
			try:
				os.unlink(path)
			except OSError:
				pass

	def makeBitCheckHardware(self):
		root = tempfile.mkdtemp(prefix="awlsim-periphery-bit-hw-")
		packageDir = os.path.join(root, "awlsimhw_peripherybitcheck")
		os.mkdir(packageDir)
		with open(os.path.join(packageDir, "__init__.py"), "w") as f:
			f.write("from __future__ import division, absolute_import, "
				"print_function, unicode_literals\n"
				"from awlsimhw_peripherybitcheck.main import *\n")
		with open(os.path.join(packageDir, "main.py"), "w") as f:
			f.write("""\
from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.core.hardware import AbstractHardwareInterface


class HardwareInterface_PeripheryBitCheck(AbstractHardwareInterface):
	name = "peripherybitcheck"

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self, sim, parameters)
		self.__writes = []

	def directReadInput(self, accessWidth, accessOffset):
		if accessOffset != 10:
			return bytearray()
		if accessWidth != 8:
			self.raiseException("expected byte direct PE access, got width %d" %
					    accessWidth)
		return bytearray((0x04, ))

	def directWriteOutput(self, accessWidth, accessOffset, data):
		if accessOffset != 10:
			return False
		expected = (0xA1, 0xE1)
		index = len(self.__writes)
		if accessWidth != 8:
			self.raiseException("expected byte direct PA access, got width %d" %
					    accessWidth)
		if index >= len(expected):
			self.raiseException("unexpected extra PA write")
		if len(data) != 1 or data[0] != expected[index]:
			self.raiseException("expected PA byte 0x%02X, got %r" %
					    (expected[index], data))
		self.__writes.append(data[0])
		return True


HardwareInterface = HardwareInterface_PeripheryBitCheck
""")
		return root

	def test_PE_bit_operands_read_process_image_bits(self):
		self.runAwl("""\
ORGANIZATION_BLOCK OB 1
BEGIN
\tL\t\tDW#16#87654321
\tT\t\tED 10
\tL\t\tPEB 10
\t__ASSERT==\t__ACCU 1,\tDW#16#00000087
\tL\t\tPEW 10
\t__ASSERT==\t__ACCU 1,\tDW#16#00008765
\tL\t\tPED 10
\t__ASSERT==\t__ACCU 1,\tDW#16#87654321
\tU\t\tPE 10.2
\t__ASSERT==\t__STW VKE,\t1
\tU\t\tPE 10.3
\t__ASSERT==\t__STW VKE,\t0
\tCALL SFC 46 // STOP CPU
END_ORGANIZATION_BLOCK
""")

	def test_PE_PA_bit_operands_use_byte_direct_hardware_access(self):
		hardwarePath = self.makeBitCheckHardware()
		try:
			self.runAwl("""\
ORGANIZATION_BLOCK OB 1
BEGIN
\tL\t\tDW#16#A5A5A5A5
\tT\t\tQD 10
\tA\t\tPI 10.2
\t__ASSERT==\t__STW RLO,\t1
\tA\t\tPI 10.3
\t__ASSERT==\t__STW RLO,\t0
\tCLR
\t=\t\tPQ 10.2
\tL\t\tQD 10
\t__ASSERT==\t__ACCU 1,\tDW#16#A1A5A5A5
\tSET
\t=\t\tPQ 10.6
\tL\t\tQD 10
\t__ASSERT==\t__ACCU 1,\tDW#16#E1A5A5A5
\tCALL SFC 46 // STOP CPU
END_ORGANIZATION_BLOCK
""", hardware="peripherybitcheck", mnemonics="en",
				    extraPythonPath=hardwarePath)
		finally:
			shutil.rmtree(hardwarePath)

	def test_PA_bit_stores_preserve_neighboring_bits(self):
		self.runAwl("""\
ORGANIZATION_BLOCK OB 1
BEGIN
\tL\t\t0
\tT\t\tAD 10
\tL\t\tDW#16#87654321
\tT\t\tPAB 10
\tL\t\tAD 10
\t__ASSERT==\t__ACCU 1,\tDW#16#21000000
\tL\t\t0
\tT\t\tAD 10
\tL\t\tDW#16#87654321
\tT\t\tPAW 10
\tL\t\tAD 10
\t__ASSERT==\t__ACCU 1,\tDW#16#43210000
\tL\t\t0
\tT\t\tAD 10
\tL\t\tDW#16#87654321
\tT\t\tPAD 10
\tL\t\tAD 10
\t__ASSERT==\t__ACCU 1,\tDW#16#87654321
\tL\t\tDW#16#A5A5A5A5
\tT\t\tAD 10
\tCLR
\t=\t\tPA 10.2
\tL\t\tAD 10
\t__ASSERT==\t__ACCU 1,\tDW#16#A1A5A5A5
\tSET
\t=\t\tPA 10.6
\tL\t\tAD 10
\t__ASSERT==\t__ACCU 1,\tDW#16#E1A5A5A5
\tCALL SFC 46 // STOP CPU
END_ORGANIZATION_BLOCK
""")
