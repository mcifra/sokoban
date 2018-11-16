import sys
import subprocess
from SokobanSolver import SokobanSolver

if len(sys.argv) < 2:
    print('Give me an input file with map\nAborting')
    sys.exit(0)

ss = SokobanSolver(sys.argv[1])
ss.solve()
