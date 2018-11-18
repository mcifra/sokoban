import sys
import subprocess
from SokobanSolver import SokobanSolver

if len(sys.argv) < 2:
    print('Give me an input file with map\nAborting')
    sys.exit(0)

ss = SokobanSolver(sys.argv[1])

if len(sys.argv) == 3:
    try:
        limit = int(sys.argv[2])
        if limit > 0:
            ss.set_limit(limit)
            print('Limit set to {}'.format(limit))
        else:
            raise Exception()
    except ValueError:
        print('Limit must be an integer. Continuing with default limit.')
    except Exception:
        print('Limit must be greater than zero. Continuing with default limit.')

ss.solve()
